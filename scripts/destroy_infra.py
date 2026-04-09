#!/usr/bin/env python3
"""
destroy_infra.py — Destroy ALL infrastructure in the correct dependency order.

Usage:
    python3 scripts/destroy_infra.py

Destroy order (avoids "resource in use" GCP errors):
    Phase 1 : Twingate connector VM + Twingate resources  (auto-skipped if no creds)
    Phase 2 : VPC Access Connector                        (uses connector subnet — wait for full drain)
    Phase 3 : Cloud NAT                                   (uses router + static IP)
    Phase 4 : Static NAT IP address                       (released AFTER NAT is gone)
    Phase 5 : Cloud Router                                (uses VPC — wait for NAT to drain)
    Phase 6 : Firewall rules                              (use VPC network)
    Phase 7 : Subnets                                     (use VPC — wait for connector to drain)
    Phase 8 : VPC Network                                 (last)

Options:
    --skip-twingate   Skip Twingate teardown even if credentials exist
    --keep-state      Preserve the GCS Terraform state bucket after teardown
    --verbose         Print commands before executing
    --no-refresh      Skip terraform refresh (faster but may miss state drift)
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from utils import get_project_id, get_tfstate_bucket_name

ROOT_DIR   = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent

# ─── GCP Destroy Dependency Order ───────────────────────────────────────────
#
# IMPORTANT ordering rules:
#   1. VPC Access Connector  → must be FULLY deleted before its subnet is touched
#   2. Cloud NAT             → must go before static IP (NAT holds the IP reservation)
#   3. Static NAT IP         → must go AFTER NAT, BEFORE Router (router references it)
#   4. Cloud Router          → can only be removed after NAT + IP are gone
#   5. Firewall rules        → independent of NAT/Router; can go in parallel conceptually
#   6. Subnets               → ONLY after connector is fully deleted (GCP async drain)
#   7. VPC Network           → always last
#
# Each tuple: (terraform resource address, human-readable label, post-destroy wait seconds)
VPC_DESTROY_ORDER = [
    # ── Serverless VPC Access Connector ──────────────────────────────────────
    # GCP takes 2-5 min to fully release the connector's subnet reservation.
    # We'll do a longer sleep *after* this step (see CONNECTOR_DRAIN_WAIT).
    ('google_vpc_access_connector.connector',           'VPC Access Connector',      10),
    # ── Cloud NAT (must go before Static IP and Router) ───────────────────────
    ('google_compute_router_nat.main',                  'Cloud NAT',                 15),
    # ── Static NAT IP (released after NAT, before Router) ─────────────────────
    ('google_compute_address.nat_ip',                   'Static NAT IP',             10),
    # ── Cloud Router (after NAT + IP are fully gone) ──────────────────────────
    ('google_compute_router.main',                      'Cloud Router',              10),
    # ── Firewall rules (safe to destroy now — VPC network still exists) ────────
    ('google_compute_firewall.allow_iap_ssh',           'Firewall: IAP SSH',          5),
    ('google_compute_firewall.allow_frontend_react',    'Firewall: Frontend React',   5),
    ('google_compute_firewall.allow_backend_express',   'Firewall: Backend Express',  5),
    ('google_compute_firewall.allow_python_app',        'Firewall: Python App',       5),
    ('google_compute_firewall.allow_mongodb',           'Firewall: MongoDB',          5),
    # ── Subnets (only AFTER connector has fully drained — see run logic below) ─
    ('google_compute_subnetwork.vpc_connector',         'Subnet: VPC Connector',     10),
    ('google_compute_subnetwork.backend',               'Subnet: Backend',           10),
    ('google_compute_subnetwork.frontend',              'Subnet: Frontend',          10),
    # ── VPC Network (always last) ──────────────────────────────────────────────
    ('google_compute_network.main',                     'VPC Network',                5),
]

# How long (seconds) to wait after the VPC Access Connector is destroyed
# before proceeding with subnet teardown. GCP needs time to release the
# IP range reservation the connector holds on the subnet.
CONNECTOR_DRAIN_WAIT = 90   # seconds — conservative; increase to 120 if still failing


# ─── Helpers ────────────────────────────────────────────────────────────────

def load_dotenv(dotenv_path=None):
    """Load .env file into os.environ (no third-party libs required)."""
    if dotenv_path is None:
        dotenv_path = ROOT_DIR / '.env'
    dotenv_path = Path(dotenv_path)
    if not dotenv_path.exists():
        return
    with open(dotenv_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, value = stripped.split('=', 1)
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def set_tfvar(name, value):
    if value is not None:
        os.environ[f'TF_VAR_{name}'] = str(value)


def run_cmd(command, label, fail_on_error=True, verbose=False, retries=3, retry_wait=30):
    """
    Run a shell command with robust retry logic for GCP "resource in use" errors.

    GCP error patterns that trigger a retry (transient, not real failures):
      - resourceInUse / RESOURCE_IN_USE / resource_in_use
      - still in use / is still in use / is being used / currently being used
      - has subnetworks (VPC deletion before subnets are gone)
      - Please remove
      - IN_USE_BY_ANOTHER_RESOURCE
      - NETWORK_IN_USE
      - SUBNET_IN_USE / subnetworkInUse
      - resourceNotReady (GCP propagation lag)
    """
    print(f'\n---> {label}...', flush=True)
    if verbose:
        print(f'     Command: {" ".join(command)}', flush=True)

    transient_errors = [
        'resourceInUse',
        'resource_in_use',
        'RESOURCE_IN_USE',
        'IN_USE_BY_ANOTHER_RESOURCE',
        'NETWORK_IN_USE',
        'SUBNET_IN_USE',
        'subnetworkInUse',
        'still in use',
        'is still in use',
        'is being used',
        'currently being used',
        'has subnetworks',
        'Please remove',
        'resourceNotReady',
        'RESOURCE_NOT_READY',
        'The resource is not ready',
    ]

    for attempt in range(1, retries + 2):   # +2 → initial attempt + N retries
        result = subprocess.run(command, text=True, capture_output=True)

        if result.returncode == 0:
            print(f'✅  {label}', flush=True)
            return True

        stderr = result.stderr or ''
        stdout = result.stdout or ''
        output = stderr + stdout

        # Always print command output so the user can see what happened
        if stdout:
            print(stdout, end='', flush=True)
        if stderr:
            print(stderr, end='', flush=True)

        is_transient = any(err in output for err in transient_errors)

        if is_transient and attempt <= retries:
            wait = retry_wait * attempt   # exponential back-off: 30s, 60s, 90s …
            print(
                f'\n⚠️  Resource in use — waiting {wait}s before retry '
                f'({attempt}/{retries})...', flush=True
            )
            time.sleep(wait)
            continue

        # Non-transient error, or retries exhausted
        print(f'❌  Failed: {label}', flush=True)
        if fail_on_error:
            sys.exit(result.returncode)
        return False

    return False


def terraform_refresh(var_file=None, verbose=False):
    """
    Sync the Terraform state with real GCP state before destroying.
    Prevents ghost-resource errors caused by resources already deleted outside TF.
    """
    cmd = ['terraform', 'refresh']
    if var_file:
        cmd += [f'-var-file={var_file}']
    return run_cmd(
        cmd,
        'Refresh: sync Terraform state with GCP',
        fail_on_error=False,
        verbose=verbose,
        retries=1,
        retry_wait=10,
    )


def terraform_targeted_destroy(resource_addr, label, var_file=None, verbose=False):
    """Destroy a single Terraform resource by address, with aggressive retry."""
    cmd = ['terraform', 'destroy', '-auto-approve', f'-target={resource_addr}']
    if var_file:
        cmd += [f'-var-file={var_file}']
    return run_cmd(
        cmd,
        label,
        fail_on_error=False,
        verbose=verbose,
        retries=4,          # up to 4 retries for targeted destroys
        retry_wait=30,      # 30s / 60s / 90s / 120s back-off
    )


def countdown(seconds, message):
    """Print a live countdown so the user knows the script is still working."""
    print(f'\n⏳  {message}', flush=True)
    for remaining in range(seconds, 0, -10):
        print(f'    ... {remaining}s remaining', flush=True)
        time.sleep(min(10, remaining))
    print('    ... done waiting.\n', flush=True)


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description='Destroy ALL GCP infrastructure in safe dependency order.',
    )
    parser.add_argument('--project-id',    help='GCP project ID (default: from terraform.tfvars)')
    parser.add_argument('--bucket-name',   help='Terraform state bucket name')
    parser.add_argument('--tfvars-path',   default=None, help='Path to terraform.tfvars')
    parser.add_argument('--var-file',      default='terraform.tfvars', help='Terraform variable file')
    parser.add_argument('--skip-twingate', action='store_true', help='Skip Twingate teardown even if credentials exist')
    parser.add_argument('--keep-state',    action='store_true', help='Preserve the GCS Terraform state bucket')
    parser.add_argument('--verbose',       action='store_true', help='Print commands before running')
    parser.add_argument('--no-refresh',    action='store_true', help='Skip terraform refresh (faster, less safe)')
    return parser.parse_args()


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    args     = parse_args()
    verbose  = args.verbose
    var_file = args.var_file

    load_dotenv()

    project_id  = args.project_id or get_project_id(args.tfvars_path)
    bucket_name = get_tfstate_bucket_name(project_id, args.bucket_name)

    # Auto-detect Twingate credentials
    twingate_token   = os.getenv('TWINGATE_API_TOKEN')
    twingate_network = os.getenv('TWINGATE_NETWORK')
    destroy_twingate = (
        not args.skip_twingate
        and bool(twingate_token)
        and bool(twingate_network)
    )

    set_tfvar('project_id', project_id)
    if twingate_token:
        set_tfvar('twingate_api_token', twingate_token)
    if twingate_network:
        set_tfvar('twingate_network', twingate_network)

    # ── Banner ──────────────────────────────────────────────────────────────
    print('\n' + '=' * 60, flush=True)
    print('   💥  Destroy ALL Infrastructure — Safe Order    ', flush=True)
    print('=' * 60, flush=True)
    print(f'   Project   : {project_id}', flush=True)
    print(f'   State     : gs://{bucket_name}', flush=True)
    print(f'   Twingate  : {"🗑️  Will destroy" if destroy_twingate else "⏭️  Skipped (no credentials)"}', flush=True)
    print(f'   Refresh   : {"⏭️  Skipped (--no-refresh)" if args.no_refresh else "✅  Enabled"}', flush=True)
    print(f'   State Bkt : {"✋ Preserved" if args.keep_state else "ℹ️  Left in place"}', flush=True)
    print('=' * 60 + '\n', flush=True)

    # ── Phase 1: Twingate VM + connector (must go before VPC subnets) ───────
    if destroy_twingate:
        twingate_dir = ROOT_DIR / 'twingate'
        if not twingate_dir.is_dir():
            print('⚠️  twingate/ not found — skipping Twingate teardown.', flush=True)
        else:
            print('\n📦  Phase 1: Twingate teardown', flush=True)
            original_cwd = Path.cwd()
            os.chdir(twingate_dir)
            try:
                run_cmd(
                    ['terraform', 'init', f'-backend-config=bucket={bucket_name}'],
                    'Phase 1 / Step 1: terraform init (Twingate)',
                    fail_on_error=False, verbose=verbose,
                )
                # Destroy Twingate VM first (it lives in the backend subnet)
                run_cmd(
                    ['terraform', 'destroy', '-auto-approve',
                     '-target=google_compute_instance.twingate_connector'],
                    'Phase 1 / Step 2: Destroy Twingate connector VM',
                    fail_on_error=False, verbose=verbose, retries=4, retry_wait=30,
                )
                # Destroy remaining Twingate resources (secrets, remote network, tokens)
                run_cmd(
                    ['terraform', 'destroy', '-auto-approve'],
                    'Phase 1 / Step 3: Destroy remaining Twingate resources',
                    fail_on_error=False, verbose=verbose, retries=3, retry_wait=30,
                )
            finally:
                os.chdir(original_cwd)
    else:
        print('ℹ️  Phase 1: Twingate skipped (no credentials in .env).', flush=True)

    # ── Phase 2–8: VPC resources in dependency order ─────────────────────────
    print('\n📦  Phase 2–8: VPC teardown (dependency order)', flush=True)

    run_cmd(
        ['terraform', 'init', f'-backend-config=bucket={bucket_name}'],
        'VPC / Step 1: terraform init',
        verbose=verbose,
    )

    # Refresh Terraform state to catch any drift (e.g., manually deleted resources)
    if not args.no_refresh:
        print('\n🔄  Refreshing Terraform state before destroy...', flush=True)
        terraform_refresh(var_file=var_file, verbose=verbose)

    # Wait for GCP to release Twingate VM resources before touching shared subnets
    if destroy_twingate:
        countdown(20, 'Waiting for GCP to release Twingate VM resources...')

    # ── Targeted destroys in strict dependency order ──────────────────────────
    connector_destroyed = False
    step = 2

    for resource_addr, label, post_wait in VPC_DESTROY_ORDER:
        success = terraform_targeted_destroy(
            resource_addr,
            f'VPC / Step {step}: Destroy {label}',
            var_file=var_file,
            verbose=verbose,
        )
        step += 1

        # Track connector deletion — subnets depend on it being fully gone
        if resource_addr == 'google_vpc_access_connector.connector':
            connector_destroyed = True

        # If this was the connector, do a longer drain wait before subnets
        if connector_destroyed and resource_addr == 'google_vpc_access_connector.connector':
            countdown(
                CONNECTOR_DRAIN_WAIT,
                f'Waiting {CONNECTOR_DRAIN_WAIT}s for GCP to release VPC connector '
                f'subnet reservation (prevents "resource in use" on subnets)...'
            )
            connector_destroyed = False   # Reset so we don't wait again

        # After NAT is removed, wait for GCP to release Router's NAT binding
        elif resource_addr == 'google_compute_router_nat.main':
            countdown(20, 'Waiting for GCP to release Cloud Router NAT binding...')

        # After Static IP is removed, brief pause before Router
        elif resource_addr == 'google_compute_address.nat_ip':
            countdown(15, 'Waiting for GCP to release static IP reservation...')

        # Standard small pause between all other steps
        elif post_wait > 0:
            time.sleep(post_wait)

    # ── Final sweep — catch anything missed by targeted destroys ──────────────
    print('\n🧹  Final sweep: terraform destroy (catch-all)', flush=True)
    run_cmd(
        ['terraform', 'destroy', '-auto-approve', f'-var-file={var_file}'],
        'VPC / Final: terraform destroy (catch-all)',
        fail_on_error=False, verbose=verbose, retries=3, retry_wait=40,
    )

    # ── Done ─────────────────────────────────────────────────────────────────
    print('\n' + '=' * 60, flush=True)
    print('   ✨  Teardown Complete!                          ', flush=True)
    print('=' * 60, flush=True)
    if destroy_twingate:
        print('   Twingate  → Destroyed', flush=True)
    print('   VPC       → Destroyed', flush=True)
    if args.keep_state:
        print(f'   State Bkt → Preserved: gs://{bucket_name}', flush=True)
    else:
        print(f'\n   ℹ️  State bucket still exists: gs://{bucket_name}', flush=True)
        print(f'   Delete manually if desired:', flush=True)
        print(f'     gsutil rm -r gs://{bucket_name}', flush=True)
    print('=' * 60 + '\n', flush=True)


if __name__ == '__main__':
    main()
