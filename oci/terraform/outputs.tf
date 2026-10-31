output "wings_instances" {
  value = merge({ for k, v in oci_core_instance.wings : k => { id = v.id, private_ip = v.private_ip, public_ip = v.public_ip, boot_volume_id = v.boot_volume_id } }, {
    "wings-04" = { id = oci_core_instance.wings_04.id, private_ip = oci_core_instance.wings_04.private_ip, public_ip = oci_core_instance.wings_04.public_ip, boot_volume_id = var.retained_boot_volume_ocid }
  })
}
output "windows_instance_id" { value = oci_core_instance.windows.id }
output "windows_private_ip" { value = oci_core_instance.windows.private_ip }
output "data_volumes" { value = { for k, v in oci_core_volume.wings : k => { id = v.id, device = oci_core_volume_attachment.wings[k].device } } }
output "network" {
  value = { vcn_id = var.vcn_ocid, wings_subnet_id = var.wings_subnet_ocid, windows_subnet_id = var.windows_subnet_ocid, advertised_routes = distinct([data.oci_core_subnet.wings.cidr_block, data.oci_core_subnet.windows.cidr_block]), router_private_ip = var.router_private_ip }
}
output "backup_bucket" { value = { name = oci_objectstorage_bucket.backups.name, namespace = oci_objectstorage_bucket.backups.namespace } }
output "retained_data_volumes" { value = var.retained_data_volumes }
output "region" { value = var.region }
output "oci_profile" { value = var.oci_profile }
output "router_additive_nsg_ids" {
  value = [oci_core_network_security_group.wings.id, oci_core_network_security_group.router.id]
}

output "windows_image_bucket" {
  value = {
    namespace = oci_objectstorage_bucket.windows_images.namespace
    name      = oci_objectstorage_bucket.windows_images.name
  }
}

output "wings_capacity" {
  description = "Desired paid-node capacity for provisioning, Panel limits and cost estimates."
  value       = local.paid_wings
}
