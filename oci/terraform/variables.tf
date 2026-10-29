variable "region" { type = string }
variable "home_region" { type = string }
variable "oci_profile" {
  type    = string
  default = "DEFAULT"
}
variable "tenancy_ocid" { type = string }
variable "compartment_ocid" { type = string }
variable "vcn_ocid" { type = string }
variable "wings_subnet_ocid" { type = string }
variable "windows_subnet_ocid" { type = string }
variable "availability_domain" { type = string }
variable "ubuntu_image_ocid" {
  description = "Region-specific Canonical Ubuntu 26.04 x86_64 image verified against E6.Flex. No automatic latest/fallback."
  type        = string
}
variable "windows_image_ocid" {
  description = "Imported Windows 11 image OCID; review accepted firmware, TPM and E4 capabilities before the approved first launch."
  type        = string
}
variable "ssh_public_key" {
  type = string
  validation {
    condition     = can(regex("^ssh-(ed25519|rsa) ", var.ssh_public_key))
    error_message = "Supply an SSH public key, never a private key."
  }
}
variable "existing_instance_ocid" { type = string }
variable "retained_boot_volume_ocid" { type = string }
variable "retained_data_volumes" {
  description = "Actual discovered block-volume OCIDs keyed by a stable local name. No invented storage."
  type        = map(string)
  default     = {}
}
variable "router_private_ip" {
  description = "Discovered wings-04 VCN IP; subnet-router SNAT source for private administration."
  type        = string
  validation {
    condition     = can(cidrnetmask("${var.router_private_ip}/32"))
    error_message = "Supply a single private IPv4 address."
  }
}
variable "extra_router_private_ips" {
  type    = set(string)
  default = []
}
variable "game_ports" {
  description = "Explicit public allocations, shared on each Wings host. Add only ports allocated in Panel."
  type        = map(object({ protocol = string, min = number, max = number }))
  default     = { minecraft = { protocol = "6", min = 25565, max = 25565 } }
  validation {
    condition     = alltrue([for p in values(var.game_ports) : contains(["6", "17"], p.protocol) && p.min >= 1024 && p.max <= 65535 && p.min <= p.max && alltrue([for private_port in [2022, 3389, 8080, 9100] : !(p.min <= private_port && p.max >= private_port)])])
    error_message = "TCP/UDP game ranges must exclude private SFTP (2022), RDP (3389), Wings API (8080) and exporter (9100) ports."
  }
}
variable "backup_bucket_name" { type = string }
variable "budget_recipients" {
  description = "Comma-separated verified notification email addresses."
  type        = string
}
variable "billing_currency" {
  type = string
  validation {
    condition     = contains(["EUR", "USD"], var.billing_currency)
    error_message = "Verify tenancy billing currency; this configuration supports EUR or USD."
  }
}
variable "billing_units_per_eur" {
  description = "1 for EUR billing; verified dated USD/EUR conversion for USD billing. Budgets API uses billing currency."
  type        = number
  validation {
    condition     = var.billing_units_per_eur > 0 && (var.billing_currency != "EUR" || var.billing_units_per_eur == 1)
    error_message = "A positive verified conversion is required; EUR must use 1."
  }
}
variable "discovery_reviewed" {
  description = "Set only after inventory, quota, free eligibility, ingress and non-overlap reviews."
  type        = bool
  default     = false
}
variable "windows_compatibility_verified" {
  description = "Set after reviewing accepted Windows 11 image/E4 TPM2/UEFI capabilities and the 100GB boot minimum; live boot/RDP acceptance follows the approved first launch."
  type        = bool
  default     = false
}

variable "private_access_verified" {
  description = "Set only after private SSH through the approved subnet route succeeds; scopes retained SSH security-list rules to router IP."
  type        = bool
  default     = false
}
