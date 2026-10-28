resource "oci_core_volume" "wings" {
  for_each            = local.paid_wings
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "${each.key}-data"
  size_in_gbs         = 200
  vpus_per_gb         = 10
  freeform_tags       = local.tags
  lifecycle { prevent_destroy = true }
}
resource "oci_core_volume_attachment" "wings" {
  for_each        = local.paid_wings
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.wings[each.key].id
  volume_id       = oci_core_volume.wings[each.key].id
  device          = "/dev/oracleoci/oraclevdb"
  is_read_only    = false
}
resource "oci_core_boot_volume" "wings_04" {
  source_details {
    type = "bootVolume"
    id   = var.retained_boot_volume_ocid
  }
  availability_domain = data.oci_core_boot_volume.retained.availability_domain
  compartment_id      = data.oci_core_boot_volume.retained.compartment_id
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_volume" "wings_04" {
  for_each            = var.retained_data_volumes
  availability_domain = data.oci_core_volume.retained[each.key].availability_domain
  compartment_id      = data.oci_core_volume.retained[each.key].compartment_id
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_objectstorage_bucket" "backups" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.this.namespace
  name           = var.backup_bucket_name
  access_type    = "NoPublicAccess"
  storage_tier   = "Standard"
  versioning     = "Disabled"
  freeform_tags  = local.tags
  lifecycle { prevent_destroy = true }
}
# No immutable retention lock and no automatic expiration/deletion. Review
# size/retention externally; automatic deletion needs explicit authorization.
