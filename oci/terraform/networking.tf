# Retain and reference existing shared infrastructure. Import shared networks only
# after their complete dependencies and all security rules have been inventoried.
data "oci_core_vcn" "retained" { vcn_id = var.vcn_ocid }
data "oci_core_subnet" "wings" { subnet_id = var.wings_subnet_ocid }
data "oci_core_subnet" "windows" { subnet_id = var.windows_subnet_ocid }
resource "terraform_data" "network_gate" {
  lifecycle {
    precondition {
      condition     = data.oci_core_subnet.wings.vcn_id == var.vcn_ocid && data.oci_core_subnet.windows.vcn_id == var.vcn_ocid && !data.oci_core_subnet.wings.prohibit_public_ip_on_vnic
      error_message = "Reuse subnets in the retained VCN; Wings needs a public-IP-capable subnet with an existing Internet Gateway route."
    }
  }
}
