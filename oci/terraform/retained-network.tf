# Exact discovered dependency graph. Import preservation phase; no live mutation.
# Existing settings are frozen until the access migration is reviewed.
resource "oci_core_vcn" "retained_vcn_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "Jotunheim"
  cidr_block     = "10.10.0.0/16"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_subnet" "retained_subnet_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "private subnet-Jotunheim"
  cidr_block     = "10.10.10.0/24"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_subnet" "retained_subnet_1" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "public subnet-Jotunheim"
  cidr_block     = "10.10.50.0/24"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_route_table" "retained_route_table_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "route table for private private subnet-Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_route_table" "retained_route_table_1" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "default route table for Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_security_list" "retained_security_list_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "security list for private subnet-Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  ingress_security_rules {
    protocol    = "6"
    source      = var.private_access_verified ? "${var.router_private_ip}/32" : "10.10.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  ingress_security_rules {
    protocol    = "1"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      code = 4
      type = 3
    }
  }
  ingress_security_rules {
    protocol    = "1"
    source      = "10.10.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      type = 3
    }
  }
  egress_security_rules {
    protocol         = "all"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [defined_tags, freeform_tags]
  }
}

resource "oci_core_security_list" "retained_security_list_1" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "Default Security List for Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  ingress_security_rules {
    protocol    = "6"
    source      = var.private_access_verified ? "${var.router_private_ip}/32" : "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    tcp_options {
      max = 22
      min = 22
    }
  }
  ingress_security_rules {
    protocol    = "1"
    source      = "0.0.0.0/0"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      code = 4
      type = 3
    }
  }
  ingress_security_rules {
    protocol    = "1"
    source      = "10.10.0.0/16"
    source_type = "CIDR_BLOCK"
    stateless   = false
    icmp_options {
      type = 3
    }
  }
  egress_security_rules {
    protocol         = "all"
    destination      = "0.0.0.0/0"
    destination_type = "CIDR_BLOCK"
    stateless        = false
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [defined_tags, freeform_tags]
  }
}

resource "oci_core_internet_gateway" "retained_internet_gateway_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "Internet gateway-Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  enabled        = true
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_nat_gateway" "retained_nat_gateway_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "NAT gateway-Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
resource "oci_core_service_gateway" "retained_service_gateway_0" {
  compartment_id = "ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq"
  display_name   = "Service gateway-Jotunheim"
  vcn_id         = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
  services {
    service_id = "ocid1.service.oc1.me-riyadh-1.aaaaaaaah72tb7hewca5waqjanan6qhetoe2dx6g7wdis4sut6vobacfccjq"
  }
  lifecycle {
    prevent_destroy = true
    ignore_changes  = all
  }
}
