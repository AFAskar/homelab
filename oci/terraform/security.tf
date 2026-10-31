resource "oci_core_network_security_group" "wings" {
  compartment_id = var.compartment_ocid
  vcn_id         = var.vcn_ocid
  display_name   = "pelican-wings"
  freeform_tags  = local.tags
}
resource "oci_core_network_security_group" "windows" {
  compartment_id = var.compartment_ocid
  vcn_id         = var.vcn_ocid
  display_name   = "win11-private-rdp"
  freeform_tags  = local.tags
}
locals {
  private_wings_rules = { for pair in setproduct(local.router_cidrs, [22, 8080, 2022, 9100]) : "${pair[0]}:${pair[1]}" => { source = pair[0], port = pair[1] } }
}
resource "oci_core_network_security_group_security_rule" "wings_private" {
  for_each                  = local.private_wings_rules
  network_security_group_id = oci_core_network_security_group.wings.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value.source
  tcp_options {
    destination_port_range {
      min = each.value.port
      max = each.value.port
    }
  }
}
resource "oci_core_network_security_group_security_rule" "games" {
  for_each                  = var.game_ports
  network_security_group_id = oci_core_network_security_group.wings.id
  direction                 = "INGRESS"
  protocol                  = each.value.protocol
  source                    = "0.0.0.0/0"
  dynamic "tcp_options" {
    for_each = each.value.protocol == "6" ? [each.value] : []
    content {
      destination_port_range {
        min = tcp_options.value.min
        max = tcp_options.value.max
      }
    }
  }
  dynamic "udp_options" {
    for_each = each.value.protocol == "17" ? [each.value] : []
    content {
      destination_port_range {
        min = udp_options.value.min
        max = udp_options.value.max
      }
    }
  }
}
resource "oci_core_network_security_group_security_rule" "rdp" {
  for_each                  = local.router_cidrs
  network_security_group_id = oci_core_network_security_group.windows.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  tcp_options {
    destination_port_range {
      min = 3389
      max = 3389
    }
  }
}
resource "oci_core_network_security_group_security_rule" "egress" {
  for_each                  = { wings = oci_core_network_security_group.wings.id, windows = oci_core_network_security_group.windows.id }
  network_security_group_id = each.value
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
}
# OCI security lists and NSGs are additive. These NSGs do not remove legacy
# 0.0.0.0/0 SSH/RDP rules; migration.md requires verified route access first.
# Router's existing VNIC/NSGs stay untouched until inventory and access review.

# Attach additively to the discovered retained router VNIC after import review;
# preserve every existing NSG until private administration has been verified.
resource "oci_core_network_security_group" "router" {
  compartment_id = var.compartment_ocid
  vcn_id         = var.vcn_ocid
  display_name   = "pelican-panel-callback-proxy"
  freeform_tags  = local.tags
}
resource "oci_core_network_security_group_security_rule" "panel_callback" {
  for_each                  = toset([data.oci_core_subnet.wings.cidr_block])
  network_security_group_id = oci_core_network_security_group.router.id
  direction                 = "INGRESS"
  protocol                  = "6"
  source                    = each.value
  tcp_options {
    destination_port_range {
      min = 443
      max = 443
    }
  }
}
