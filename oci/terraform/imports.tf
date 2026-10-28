# Official config-driven imports. DO NOT apply the full root to import only.
# Follow migration.md: CLI imports mutate state only, then review a full plan.
import {
  to = oci_core_instance.wings_04
  id = var.existing_instance_ocid
}
import {
  to = oci_core_boot_volume.wings_04
  id = var.retained_boot_volume_ocid
}
import {
  for_each = var.retained_data_volumes
  to       = oci_core_volume.wings_04[each.key]
  id       = each.value
}


import {
  to = oci_core_vcn.retained_vcn_0
  id = "ocid1.vcn.oc1.me-riyadh-1.amaaaaaacxr7q4yaqvniywct7uarhvswzla6xt7ftycmadz6raemok7wuydq"
}
import {
  to = oci_core_subnet.retained_subnet_0
  id = "ocid1.subnet.oc1.me-riyadh-1.aaaaaaaayhfi44i2eetqrk6rcebtpeuyva6v2t74ahwwwdc4ki22h3lk4qva"
}
import {
  to = oci_core_subnet.retained_subnet_1
  id = "ocid1.subnet.oc1.me-riyadh-1.aaaaaaaabntumthbgvuoafso256p6hmd24hysr44rkj7ocf5opoyg2kc7efq"
}
import {
  to = oci_core_route_table.retained_route_table_0
  id = "ocid1.routetable.oc1.me-riyadh-1.aaaaaaaaf6alhpk4gaw3wqwesttzcdiam5pnipurnk64n7iyukmheoyugrha"
}
import {
  to = oci_core_route_table.retained_route_table_1
  id = "ocid1.routetable.oc1.me-riyadh-1.aaaaaaaafmqcvjpavgjsuohq54ntaet5tw4vnpyvnqrk4avpfxgipcbzawdq"
}
import {
  to = oci_core_security_list.retained_security_list_0
  id = "ocid1.securitylist.oc1.me-riyadh-1.aaaaaaaaofsfw2fd6s27jdn3y3zi6icd6bpbcqjivrye5nekfip6uc7y55oa"
}
import {
  to = oci_core_security_list.retained_security_list_1
  id = "ocid1.securitylist.oc1.me-riyadh-1.aaaaaaaadupeob7mk3bsewhwi7pihw4yrynuhbyizjse24rknwgijabldraa"
}
import {
  to = oci_core_internet_gateway.retained_internet_gateway_0
  id = "ocid1.internetgateway.oc1.me-riyadh-1.aaaaaaaahd63qxm7ptnmxg4v4gqt7wrwc2yh6yd3gnhhswnyp7cnj5wvqxda"
}
import {
  to = oci_core_nat_gateway.retained_nat_gateway_0
  id = "ocid1.natgateway.oc1.me-riyadh-1.aaaaaaaatom4s4gbw42tlkt3vgdqtud6bjaecd4paykx5txjmvo5ed7ndqna"
}
import {
  to = oci_core_service_gateway.retained_service_gateway_0
  id = "ocid1.servicegateway.oc1.me-riyadh-1.aaaaaaaaugi4cb44fwy3a7ir2jgnhd7n3wgwzi55izvc346wxg4f733ddvfa"
}
