# GCP Secret Manager Secrets for Twingate
# Sensitive Twingate credentials are stored securely in Secret Manager and populated from TF_VAR values.
resource "google_secret_manager_secret" "twingate_api_token" {
  secret_id = "twingate-api-token"

  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "twingate_api_token" {
  secret      = google_secret_manager_secret.twingate_api_token.id
  secret_data = var.twingate_api_token
}

resource "google_secret_manager_secret" "twingate_network" {
  secret_id = "twingate-network"

  replication {
    auto {
    }
  }
}

resource "google_secret_manager_secret_version" "twingate_network" {
  secret      = google_secret_manager_secret.twingate_network.id
  secret_data = var.twingate_network
}

# Data sources to reference existing VPC resources
data "google_compute_network" "platform_vpc" {
  name = "platform-vpc"
}

data "google_compute_subnetwork" "backend_subnet" {
  name   = "platform-vpc-backend"
  region = var.region
}

# Twingate Remote Network
resource "twingate_remote_network" "platform" {
  name = var.remote_network_name
}

# Twingate Connector
resource "twingate_connector" "platform" {
  remote_network_id = twingate_remote_network.platform.id
  name              = var.connector_name
}

# Twingate Connector Tokens (for installation)
resource "twingate_connector_tokens" "platform" {
  connector_id = twingate_connector.platform.id
}

# GCP VM for Twingate Connector
resource "google_compute_instance" "twingate_connector" {
  name         = var.connector_vm_name
  machine_type = var.connector_machine_type
  zone         = "${var.region}-${var.connector_zone_suffix}"

  boot_disk {
    initialize_params {
      image = var.connector_image
    }
  }

  network_interface {
    network    = data.google_compute_network.platform_vpc.self_link
    subnetwork = data.google_compute_subnetwork.backend_subnet.self_link

    access_config {
      // Ephemeral public IP for outbound connectivity
    }
  }

  metadata_startup_script = templatefile("${path.module}/twingate-connector-setup.sh", {
    ACCESS_TOKEN  = twingate_connector_tokens.platform.access_token
    REFRESH_TOKEN = twingate_connector_tokens.platform.refresh_token
    NETWORK       = var.twingate_network
  })

  service_account {
    scopes = ["cloud-platform"]
  }

  tags = var.connector_tags

  depends_on = [
    twingate_connector_tokens.platform
  ]
}
