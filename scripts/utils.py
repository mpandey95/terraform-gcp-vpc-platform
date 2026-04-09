import ast
import os
import sys
from typing import Any, Dict, Optional

def load_tfvars(tfvars_path: Optional[str] = None) -> Dict[str, Any]:
    if tfvars_path is None:
        tfvars_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'terraform.tfvars')

    if not os.path.exists(tfvars_path):
        return {}

    tfvars: Dict[str, Any] = {}
    with open(tfvars_path, 'r') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            if '=' not in stripped:
                continue

            name, value = stripped.split('=', 1)
            name = name.strip()
            raw_value = value.strip()
            if '#' in raw_value:
                raw_value = raw_value.split('#', 1)[0].strip()

            try:
                parsed_value = ast.literal_eval(raw_value)
            except (ValueError, SyntaxError):
                parsed_value = raw_value.strip().strip('"').strip("'")

            tfvars[name] = parsed_value

    return tfvars


def get_tfvar(name: str, default: Any = None, tfvars_path: Optional[str] = None) -> Any:
    return load_tfvars(tfvars_path).get(name, default)


def get_project_id(tfvars_path: Optional[str] = None) -> str:
    project_id = get_tfvar('project_id', None, tfvars_path)
    if not project_id:
        print('❌ Error: Could not find project_id in terraform.tfvars.')
        print('Make sure terraform.tfvars exists and contains project_id = "your-project-id"')
        sys.exit(1)
    return project_id


def get_region(tfvars_path: Optional[str] = None) -> str:
    return get_tfvar('region', 'asia-south1', tfvars_path)


def get_tfstate_bucket_name(project_id: str, bucket_name: Optional[str] = None) -> str:
    return bucket_name or f"{project_id}-tfstate"


def get_tfstate_bucket_region(tfvars_path: Optional[str] = None) -> str:
    return get_tfvar('state_bucket_region', get_region(tfvars_path), tfvars_path)


def get_secret_value(project_id: str, secret_name: str) -> str:
    """
    Retrieves the latest version of a secret from Google Cloud Secret Manager.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["gcloud", "secrets", "versions", "access", "latest",
             f"--secret={secret_name}", f"--project={project_id}"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to retrieve secret '{secret_name}': {e}")
        print("Ensure the secret exists and you have 'roles/secretmanager.secretAccessor' permission.")
        sys.exit(1)
