variable "project_id" {
  description = "The GCP Project ID where resources will be deployed"
  type        = string
}

variable "region" {
  description = "The default GCP region to deploy into"
  type        = string
  default     = "asia-south1"
}

variable "prefix" {
  description = "A prefix used for all resources in this example"
  type        = string
  default     = "platform"
}

variable "state_bucket_region" {
  description = "GCP region for the Terraform state bucket"
  type        = string
  default     = "asia-south1"
}

variable "ssh_tag" {
  description = "Firewall target tag for SSH access"
  type        = string
  default     = "ssh-enabled"
}

variable "ssh_port" {
  description = "Port to allow for SSH access via IAP"
  type        = string
  default     = "22"
}

variable "iap_source_ranges" {
  description = "Source ranges allowed for Identity-Aware Proxy"
  type        = list(string)
  default     = ["35.235.240.0/20"]
}

variable "frontend_tag" {
  description = "Firewall target tag for the frontend application"
  type        = string
  default     = "frontend-react"
}

variable "frontend_port" {
  description = "Port to expose for the frontend application"
  type        = string
  default     = "3000"
}

variable "frontend_source_ranges" {
  description = "Source CIDR ranges allowed for frontend traffic"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "backend_tag" {
  description = "Firewall target tag for the backend Express.js application"
  type        = string
  default     = "backend-express"
}

variable "backend_port" {
  description = "Port to expose for the backend Express.js application"
  type        = string
  default     = "4000"
}

variable "backend_source_ranges" {
  description = "Source CIDR ranges allowed for backend traffic"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "python_tag" {
  description = "Firewall target tag for the Python application"
  type        = string
  default     = "python-app"
}

variable "python_port" {
  description = "Port to expose for the Python application"
  type        = string
  default     = "8000"
}

variable "python_source_ranges" {
  description = "Source CIDR ranges allowed for Python application traffic"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "mongodb_tag" {
  description = "Firewall target tag for the MongoDB database"
  type        = string
  default     = "mongodb-db"
}

variable "mongodb_port" {
  description = "Port to expose for MongoDB"
  type        = string
  default     = "27017"
}

variable "mongodb_source_ranges" {
  description = "Source CIDR ranges allowed for MongoDB traffic"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "frontend_subnet_cidr" {
  description = "CIDR block for the frontend subnet"
  type        = string
  default     = "10.0.1.0/24"
}

variable "backend_subnet_cidr" {
  description = "CIDR block for the backend subnet"
  type        = string
  default     = "10.0.4.0/24"
}

variable "vpc_connector_subnet_cidr" {
  description = "CIDR block for the Serverless VPC Access connector subnet"
  type        = string
  default     = "10.0.5.0/28"
}
