resource "oci_core_instance" "wings" {
  for_each            = local.paid_wings
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = each.key
  shape               = "VM.Standard.E6.Flex"
  shape_config {
    ocpus         = 2
    memory_in_gbs = 16
  }
  create_vnic_details {
    subnet_id        = var.wings_subnet_ocid
    assign_public_ip = true
    hostname_label   = each.key
    nsg_ids          = [oci_core_network_security_group.wings.id]
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
resource "oci_core_instance" "windows" {
  compartment_id      = var.compartment_ocid
  availability_domain = var.availability_domain
  display_name        = "win11-lab"
  shape               = "VM.Standard.E4.Flex"
  shape_config {
    ocpus         = 2
    memory_in_gbs = 16
  }
  create_vnic_details {
    subnet_id        = var.windows_subnet_ocid
    assign_public_ip = false
    hostname_label   = "win11-lab"
    nsg_ids          = [oci_core_network_security_group.windows.id]
  }
  source_details {
    source_type             = "image"
    source_id               = var.windows_image_ocid
    boot_volume_size_in_gbs = 200
    boot_volume_vpus_per_gb = 10
  }
  launch_options {
    firmware         = "UEFI_64"
    boot_volume_type = "PARAVIRTUALIZED"
    network_type     = "PARAVIRTUALIZED"
  }
  platform_config {
    type                               = "AMD_VM"
    is_secure_boot_enabled             = true
    is_measured_boot_enabled           = true
    is_trusted_platform_module_enabled = true
  }
  preserve_boot_volume = true
  freeform_tags        = local.tags
  depends_on           = [terraform_data.review_gate, terraform_data.network_gate]
  lifecycle {
    prevent_destroy = true
    precondition {
      condition     = var.windows_compatibility_verified
      error_message = "Windows 11 blocked: OCI shielded instances exclude custom images. Obtain a supported TPM2/UEFI deployment path before proceeding."
    }
    # Do not manage state=RUNNING: CLI start/stop must not be undone by Terraform.
  }
}
