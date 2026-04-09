# ─── Serverless VPC Access Connector ─────────────────────────────────────────
# Enables Cloud Run / Cloud Functions to reach resources in the private VPC
resource "google_vpc_access_connector" "connector" {
  name   = "${var.prefix}-vpc-cx"
  region = var.region

  subnet {
    name = google_compute_subnetwork.vpc_connector.name
  }
}
