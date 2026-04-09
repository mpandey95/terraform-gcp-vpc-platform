# Firewall to allow SSH via Identity-Aware Proxy (IAP) - GCP Best Practice
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-${var.prefix}-${var.ssh_tag}"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.ssh_port]
  }

  source_ranges = var.iap_source_ranges
  description   = "Allow SSH from Identity-Aware Proxy to instances"
  target_tags   = [var.ssh_tag]
}

# Firewall to allow Frontend traffic from the Internet
resource "google_compute_firewall" "allow_frontend_react" {
  name    = "allow-${var.prefix}-${var.frontend_tag}"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.frontend_port]
  }

  source_ranges = var.frontend_source_ranges
  description   = "Allow inbound traffic to frontend application on port ${var.frontend_port}"
  target_tags   = [var.frontend_tag]
}

# Firewall to allow Backend Express.js traffic from within the VPC
resource "google_compute_firewall" "allow_backend_express" {
  name    = "allow-${var.prefix}-${var.backend_tag}"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.backend_port]
  }

  source_ranges = var.backend_source_ranges
  description   = "Allow inbound traffic to Express.js backend on port ${var.backend_port} from within VPC"
  target_tags   = [var.backend_tag]
}

# Firewall to allow Python application traffic from within the VPC
resource "google_compute_firewall" "allow_python_app" {
  name    = "allow-${var.prefix}-${var.python_tag}"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.python_port]
  }

  source_ranges = var.python_source_ranges
  description   = "Allow inbound traffic to Python app on port ${var.python_port} from within VPC"
  target_tags   = [var.python_tag]
}

# Firewall to allow MongoDB traffic from within the VPC
resource "google_compute_firewall" "allow_mongodb" {
  name    = "allow-${var.prefix}-${var.mongodb_tag}"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.mongodb_port]
  }

  source_ranges = var.mongodb_source_ranges
  description   = "Allow inbound traffic to MongoDB on port ${var.mongodb_port} from within VPC"
  target_tags   = [var.mongodb_tag]
}
