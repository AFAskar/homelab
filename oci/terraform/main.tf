locals {
  tags         = { project = "homelab", managed_by = "terraform", service = "pelican" }
  paid_wings   = toset(["wings-01", "wings-02", "wings-03"])
  router_cidrs = toset([for ip in setunion(toset([var.router_private_ip]), var.extra_router_private_ips) : "${ip}/32"])
}
data "oci_objectstorage_namespace" "this" { compartment_id = var.tenancy_ocid }
data "oci_core_instance" "retained" { instance_id = var.existing_instance_ocid }
data "oci_core_boot_volume" "retained" { boot_volume_id = var.retained_boot_volume_ocid }
data "oci_core_volume" "retained" {
  for_each  = var.retained_data_volumes
  volume_id = each.value
}
resource "terraform_data" "review_gate" {
  lifecycle {
    precondition {
      condition     = var.discovery_reviewed
      error_message = "Discovery is incomplete. Review actual tenancy inventory, quotas, existing access and credit balance first."
    }
  }
}
