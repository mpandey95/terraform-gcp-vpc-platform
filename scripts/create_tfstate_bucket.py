import argparse
import subprocess
import sys
from utils import get_project_id, get_tfstate_bucket_name, get_tfstate_bucket_region

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

def create_tfstate_bucket(project_id, bucket_name, region="asia-south1"):
    """
    Creates a Google Cloud Storage bucket for storing Terraform state files.
    """
    bucket_url = f"gs://{bucket_name}"

    print(f"Checking if bucket {bucket_url} already exists...", flush=True)
    try:
        subprocess.run(
            ["gcloud", "storage", "ls", bucket_url, f"--project={project_id}"],
            check=True,
        )
        print(f"Bucket {bucket_url} already exists. Skipping creation.", flush=True)
    except subprocess.CalledProcessError:
        print(f"Creating bucket {bucket_url} in region {region}...", flush=True)
        try:
            subprocess.run(
                ["gcloud", "storage", "buckets", "create", bucket_url,
                 f"--project={project_id}",
                 f"--location={region}",
                 "--uniform-bucket-level-access"],
                check=True,
                text=True,
            )
            print(f"✅ Successfully created bucket {bucket_url}")

            print("Enabling versioning on the bucket...")
            subprocess.run(
                ["gcloud", "storage", "buckets", "update", bucket_url, "--versioning"],
                check=True,
                text=True,
            )
            print("✅ Successfully enabled versioning.")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create or configure the bucket: {e}")
            sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Create a GCS bucket for Terraform state.")
    parser.add_argument("--project-id", help="GCP project ID")
    parser.add_argument("--bucket-name", help="Terraform state bucket name")
    parser.add_argument("--region", help="GCP region to create the bucket in")
    parser.add_argument("--tfvars-path", default=None, help="Path to terraform.tfvars file")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    project_id = args.project_id or get_project_id(args.tfvars_path)
    bucket_name = get_tfstate_bucket_name(project_id, args.bucket_name)
    region = args.region or get_tfstate_bucket_region(args.tfvars_path)
    create_tfstate_bucket(project_id, bucket_name, region)
