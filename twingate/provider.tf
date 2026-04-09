terraform {
  required_providers {
    twingate = {
      source  = "Twingate/twingate"
      version = "~> 0.2"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  backend "gcs" {
    # bucket is passed at `terraform init` time via -backend-config=bucket=<name>
    # This is handled automatically by scripts/create_infra.py and scripts/destroy_infra.py
    # To init manually: terraform init -backend-config="bucket=YOUR_PROJECT_ID-tfstate"
    prefix = "terraform/twingate"
  }
}

provider "twingate" {
  api_token = var.twingate_api_token
  network   = var.twingate_network
}

provider "google" {
  project = var.project_id
  region  = var.region
}