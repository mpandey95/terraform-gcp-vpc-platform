# ─── Frontend Subnet (Public) ─────────────────────────────────────────────────
resource "google_compute_subnetwork" "frontend" {
  name                     = "${var.prefix}-vpc-frontend"
  ip_cidr_range            = var.frontend_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.main.id
  private_ip_google_access = true # Allows VMs to reach GCP services without an external IP

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# ─── Backend Subnet (Private) ─────────────────────────────────────────────────
resource "google_compute_subnetwork" "backend" {
  name                     = "${var.prefix}-vpc-backend"
  ip_cidr_range            = var.backend_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.main.id
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# ─── VPC Connector Subnet (Serverless VPC Access) ────────────────────────────
resource "google_compute_subnetwork" "vpc_connector" {
  name                     = "${var.prefix}-vpc-connector-subnet"
  ip_cidr_range            = var.vpc_connector_subnet_cidr
  region                   = var.region
  network                  = google_compute_network.main.id
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}
