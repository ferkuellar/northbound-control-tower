terraform {
  required_version = ">= 1.5.0"
}

resource "terraform_data" "request" {
  input = {
    request_code = var.request_code
    source       = "northbound-control-tower"
  }
}
