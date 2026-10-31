provider "oci" {
  region              = var.region
  config_file_profile = var.oci_profile
}
provider "oci" {
  alias               = "home"
  region              = var.home_region
  config_file_profile = var.oci_profile
}

# Authentication comes from TAILSCALE_OAUTH_CLIENT_ID/SECRET (or API_KEY),
# never Terraform variables, user_data, committed files or outputs.
provider "tailscale" {}
