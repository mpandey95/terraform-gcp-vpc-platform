import argparse
import subprocess
import sys
from utils import get_project_id

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

def enable_gcp_apis(project_id, apis):
    """
    Enables a list of GCP APIs for a given project using the gcloud CLI.
    """
    print(f"Enabling APIs for project: {project_id}...\n", flush=True)

    for api in apis:
        print(f"Enabling {api}...", flush=True)
        try:
            subprocess.run(
                ["gcloud", "services", "enable", api, f"--project={project_id}"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"✅ Successfully enabled {api}", flush=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to enable {api}")
            if e.stderr:
                print(f"Error details:\n{e.stderr}", flush=True)
            sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Enable required GCP APIs for the project.")
    parser.add_argument("--project-id", help="GCP project ID")
    parser.add_argument("--tfvars-path", default=None, help="Path to terraform.tfvars file")
    parser.add_argument("--apis", nargs="+", help="Optional list of APIs to enable")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    project_id = args.project_id or get_project_id(args.tfvars_path)
    required_apis = args.apis or [
        "compute.googleapis.com",
        "vpcaccess.googleapis.com",
        "secretmanager.googleapis.com",
    ]

    enable_gcp_apis(project_id, required_apis)
    print("\nAll required APIs are enabled!")
