# Create a Cloud Router for the region to handle NAT
resource "google_compute_router" "main" {
  name    = "${var.prefix}-router"
  network = google_compute_network.main.id
  region  = var.region
}

# Create a static external IP address for Cloud NAT
resource "google_compute_address" "nat_ip" {
  name   = "${var.prefix}-nat-static-ip"
  region = var.region
}

# Create Cloud NAT to provide secure outbound internet access for private instances
resource "google_compute_router_nat" "main" {
  name                               = "${var.prefix}-nat-gw"
  router                             = google_compute_router.main.name
  region                             = google_compute_router.main.region
  nat_ip_allocate_option             = "MANUAL_ONLY"
  nat_ips                            = [google_compute_address.nat_ip.self_link]
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"
  enable_dynamic_port_allocation     = true
  min_ports_per_vm                   = 1024
  max_ports_per_vm                   = 65536

  # We apply NAT to instances in the Backend subnet (Private)
  subnetwork {
    name                    = google_compute_subnetwork.backend.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  # Apply NAT to Serverless VPC Access connector
  subnetwork {
    name                    = google_compute_subnetwork.vpc_connector.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}
