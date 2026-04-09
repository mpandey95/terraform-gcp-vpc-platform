variable "twingate_api_token" {
  description = "Twingate API token for authentication"
  type        = string
  sensitive   = true
}

variable "twingate_network" {
  description = "Twingate network ID"
  type        = string
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-south1"
}

variable "connector_name" {
  description = "Name for the Twingate connector"
  type        = string
  default     = "gcp-platform-connector"
}

variable "remote_network_name" {
  description = "Name for the remote network in Twingate"
  type        = string
  default     = "platform-vpc-network"
}

variable "connector_vm_name" {
  description = "Name for the Twingate connector VM"
  type        = string
  default     = "twingate-connector-vm"
}

variable "connector_machine_type" {
  description = "Machine type for the Twingate connector VM"
  type        = string
  default     = "e2-micro"
}

variable "connector_zone_suffix" {
  description = "Zone suffix for the Twingate connector VM (e.g., 'a' for region-a)"
  type        = string
  default     = "a"
}

variable "connector_image" {
  description = "OS image for the Twingate connector VM"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "connector_tags" {
  description = "Network tags for the Twingate connector VM"
  type        = list(string)
  default     = ["twingate-connector", "ssh-enabled"]
}
