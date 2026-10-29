terraform {
  required_version = ">= 1.12.0, < 2.0.0"
  required_providers {
    tailscale = {
      source  = "tailscale/tailscale"
      version = "0.29.3"
    }
    oci = {
      source  = "oracle/oci"
      version = "9.11.0"
    }
  }
  backend "oci" {}
}
