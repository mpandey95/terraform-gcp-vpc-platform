#!/usr/bin/env python3
"""
deploy_all.py — Deploy ALL infrastructure in one command.

Usage:
    python3 scripts/create_infra.py

What it does:
    Step 1  : Enable required GCP APIs
    Step 2  : Create Terraform remote state bucket (GCS)
    Step 3  : terraform init
    Step 4  : terraform fmt -recursive
    Step 5  : terraform validate
    Step 6  : terraform plan  (VPC)
    Step 7  : terraform apply (VPC)
    Step 8-12: Deploy Twingate connector (auto-skipped if no credentials found)
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from utils import (
    get_project_id,
    get_region,
    get_tfstate_bucket_name,
    get_tfstate_bucket_region,
)

ROOT_DIR   = Path(__file__).resolve().parent.parent
SCRIPT_DIR = Path(__file__).resolve().parent


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


def fetch_secret(project_id, secret_name):
    """Try to fetch a secret from GCP Secret Manager; return None on failure."""
    if not project_id:
        return None
    from utils import get_secret_value
    try:
        return get_secret_value(project_id, secret_name)
    except SystemExit:
        return None


def run_step(command, step_name, fail_on_error=True, verbose=False):
    print(f'\n---> {step_name}...', flush=True)
    if verbose:
        print(f'     Command: {" ".join(command)}', flush=True)
    try:
        subprocess.run(command, check=True, text=True)
        print(f'✅  {step_name}', flush=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'❌  Failed: {step_name} — {e}', flush=True)
        if fail_on_error:
            sys.exit(e.returncode)
        return False


# ─── CLI ────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description='Deploy ALL GCP VPC infrastructure (+ Twingate if credentials are present).',
    )
    parser.add_argument('--project-id',   help='GCP project ID (default: read from terraform.tfvars)')
    parser.add_argument('--bucket-name',  help='Terraform state bucket name (default: <project-id>-tfstate)')
    parser.add_argument('--bucket-region',help='GCP region for the state bucket (default: from terraform.tfvars)')
    parser.add_argument('--tfvars-path',  default=None, help='Path to terraform.tfvars file')
    parser.add_argument('--var-file',     default='terraform.tfvars', help='Terraform variable file')
    parser.add_argument('--skip-twingate',action='store_true', help='Skip Twingate deployment even if credentials exist')
    parser.add_argument('--verbose',      action='store_true', help='Print commands before running')
    return parser.parse_args()


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    verbose = args.verbose

    # Load .env first so credentials are available
    load_dotenv()

    # Resolve config
    project_id    = args.project_id   or get_project_id(args.tfvars_path)
    bucket_name   = get_tfstate_bucket_name(project_id, args.bucket_name)
    bucket_region = args.bucket_region or get_tfstate_bucket_region(args.tfvars_path)
    region        = get_region(args.tfvars_path)
    var_file      = args.var_file

    # Auto-detect Twingate credentials (.env → Secret Manager)
    twingate_token   = os.getenv('TWINGATE_API_TOKEN') or fetch_secret(project_id, 'twingate-api-token')
    twingate_network = os.getenv('TWINGATE_NETWORK')   or fetch_secret(project_id, 'twingate-network')
    deploy_twingate  = (
        not args.skip_twingate
        and bool(twingate_token)
        and bool(twingate_network)
    )

    # Export TF_VARs
    set_tfvar('project_id', project_id)
    set_tfvar('region', region)
    if deploy_twingate:
        set_tfvar('twingate_api_token', twingate_token)
        set_tfvar('twingate_network', twingate_network)

    # Banner
    print('\n' + '=' * 52, flush=True)
    print('   🚀  Deploy ALL Infrastructure — One Command   ', flush=True)
    print('=' * 52, flush=True)
    print(f'   Project   : {project_id}', flush=True)
    print(f'   Region    : {region}', flush=True)
    print(f'   State     : gs://{bucket_name}', flush=True)
    print(f'   Twingate  : {"✅ Will deploy" if deploy_twingate else "⏭️  Skipped (no credentials)"}', flush=True)
    print('=' * 52 + '\n', flush=True)

    # ── Phase 1: GCP prerequisites ──────────────────────────────────────────

    enable_cmd = [sys.executable, str(SCRIPT_DIR / 'enable_apis.py'), '--project-id', project_id]
    if args.tfvars_path:
        enable_cmd += ['--tfvars-path', str(args.tfvars_path)]
    run_step(enable_cmd, 'Step 1: Enable required GCP APIs', verbose=verbose)

    bucket_cmd = [
        sys.executable, str(SCRIPT_DIR / 'create_tfstate_bucket.py'),
        '--project-id', project_id,
        '--bucket-name', bucket_name,
        '--region', bucket_region,
    ]
    if args.tfvars_path:
        bucket_cmd += ['--tfvars-path', str(args.tfvars_path)]
    run_step(bucket_cmd, 'Step 2: Create Terraform state bucket (GCS)', verbose=verbose)

    # ── Phase 2: VPC deployment ──────────────────────────────────────────────

    run_step(
        ['terraform', 'init', f'-backend-config=bucket={bucket_name}', '-migrate-state', '-force-copy'],
        'Step 3: terraform init (VPC)', verbose=verbose,
    )
    run_step(['terraform', 'fmt', '-recursive'], 'Step 4: terraform fmt', verbose=verbose)
    run_step(['terraform', 'validate'],          'Step 5: terraform validate', verbose=verbose)

    plan_cmd = ['terraform', 'plan', '-out=tfplan']
    if var_file:
        plan_cmd += ['-var-file', var_file]
    run_step(plan_cmd, 'Step 6: terraform plan (VPC)', verbose=verbose)

    run_step(['terraform', 'apply', '-auto-approve', 'tfplan'], 'Step 7: terraform apply (VPC)', verbose=verbose)

    # ── Phase 3: Twingate deployment (auto-skipped if no creds) ─────────────

    if deploy_twingate:
        twingate_dir = ROOT_DIR / 'twingate'
        if not twingate_dir.is_dir():
            print(f'\n⚠️  twingate/ directory not found at {twingate_dir}. Skipping.', flush=True)
        else:
            original_cwd = Path.cwd()
            os.chdir(twingate_dir)
            try:
                run_step(
                    ['terraform', 'init', f'-backend-config=bucket={bucket_name}'],
                    'Step 8: terraform init (Twingate)', verbose=verbose,
                )
                run_step(['terraform', 'fmt', '-recursive'], 'Step 9: terraform fmt (Twingate)',     verbose=verbose)
                run_step(['terraform', 'validate'],          'Step 10: terraform validate (Twingate)',verbose=verbose)
                run_step(['terraform', 'plan', '-out=tfplan'],'Step 11: terraform plan (Twingate)',   verbose=verbose)
                run_step(
                    ['terraform', 'apply', '-auto-approve', 'tfplan'],
                    'Step 12: terraform apply (Twingate)', verbose=verbose,
                )
            finally:
                os.chdir(original_cwd)
    else:
        print('\nℹ️  Twingate skipped. Set TWINGATE_API_TOKEN + TWINGATE_NETWORK in .env to enable.', flush=True)

    # ── Done ─────────────────────────────────────────────────────────────────

    print('\n' + '=' * 52, flush=True)
    print('   ✨  Deployment Complete!                       ', flush=True)
    print('=' * 52, flush=True)
    print(f'   VPC    → Deployed in {region}', flush=True)
    if deploy_twingate:
        print('   Twingate → Connector deployed', flush=True)
    print('\n   Next steps:', flush=True)
    print('   • Check outputs : terraform output', flush=True)
    print('   • SSH to VMs    : Use IAP (gcloud compute ssh)', flush=True)
    if deploy_twingate:
        print('   • App access    : Connect via Twingate client', flush=True)
    print('=' * 52 + '\n', flush=True)


if __name__ == '__main__':
    main()
