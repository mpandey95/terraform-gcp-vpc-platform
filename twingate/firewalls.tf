# Firewall rule to allow Twingate connector outbound traffic
resource "google_compute_firewall" "allow_twingate_outbound" {
  name    = "allow-twingate-connector-outbound"
  network = data.google_compute_network.platform_vpc.self_link

  direction = "EGRESS"

  allow {
    protocol = "tcp"
    ports    = ["443", "80"]
  }

  destination_ranges = ["0.0.0.0/0"]
  target_tags        = ["twingate-connector"]
  description        = "Allow Twingate connector outbound access to Twingate service"
}