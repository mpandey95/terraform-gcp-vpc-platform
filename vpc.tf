# ─── Custom VPC Network ───────────────────────────────────────────────────────
resource "google_compute_network" "main" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}
