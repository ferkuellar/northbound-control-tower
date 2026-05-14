output "request_code" {
  description = "Northbound provisioning request code."
  value       = var.request_code
}

output "validation_marker" {
  description = "Marker proving this template performs no cloud operations."
  value       = terraform_data.request.output.source
}
