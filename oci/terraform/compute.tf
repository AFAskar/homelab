resource "oci_core_instance" "wings" {
  for_each            = local.paid_wings
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = each.key
  shape               = "VM.Standard.E6.Flex"
  shape_config {
    ocpus         = each.value.ocpus
    memory_in_gbs = each.value.memory_gb
  }
  create_vnic_details {
    subnet_id        = var.wings_subnet_ocid
    assign_public_ip = true
    hostname_label   = each.key
    nsg_ids          = concat([oci_core_network_security_group.wings.id], each.key == "wings-02" ? [oci_core_network_security_group.windows.id] : [])
  }
  source_details {
    source_type             = "image"
    source_id               = var.ubuntu_image_ocid
    boot_volume_size_in_gbs = 50
    boot_volume_vpus_per_gb = 10
  }
  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data           = filebase64("${path.module}/../cloud-init/wings.yaml")
  }
  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }
  preserve_boot_volume = true
  freeform_tags        = local.tags
  depends_on           = [terraform_data.review_gate, terraform_data.network_gate]
  lifecycle { prevent_destroy = true }
}

# Import first. Freeze launch-time fields until a reviewed, zero-replacement plan.
# Existing OS, shape, storage, metadata, VNICs and name are never changed here.
# wings-04 is the logical inventory/Panel name; rename the guest only after review.
resource "oci_core_instance" "wings_04" {
  compartment_id       = data.oci_core_instance.retained.compartment_id
  availability_domain  = data.oci_core_instance.retained.availability_domain
  shape                = data.oci_core_instance.retained.shape
  preserve_boot_volume = true
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
