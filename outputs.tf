output "vpc_id" {
  description = "The ID of the VPC"
  value       = google_compute_network.main.id
}

output "frontend_subnet_id" {
  description = "The ID of the frontend subnet"
  value       = google_compute_subnetwork.frontend.id
}

output "backend_subnet_id" {
  description = "The ID of the backend subnet"
  value       = google_compute_subnetwork.backend.id
}

output "nat_ip" {
  description = "The external IP address for the Cloud NAT"
  value       = google_compute_address.nat_ip.address
}
