# One policy owner for the whole existing tailnet; import before any update.
# Provider 0.29.3 validates policy syntax/tests during plan, but updates have no
# ETag guard. Serialize writers and invalidate ALL saved plans after console
# recovery edits; follow the policy recovery procedure in docs/operations.md.
resource "tailscale_acl" "tailnet" {
  acl                        = file("${path.module}/../ansible/tailscale/policy.hujson")
  overwrite_existing_content = false
  reset_acl_on_destroy       = false

  lifecycle {
    prevent_destroy = true
  }
}

data "tailscale_device" "homelab_dns_replica" {
  hostname = "rpi4-dns"
}

locals {
  dns_replica_ipv4 = [
    for address in data.tailscale_device.homelab_dns_replica.addresses : address
    if can(cidrnetmask("${address}/32"))
  ]
}

import {
  to = tailscale_dns_split_nameservers.home_internal
  id = "home.internal"
}

resource "tailscale_dns_split_nameservers" "home_internal" {
  domain = "home.internal"
  nameservers = [
    jsondecode(file("${path.module}/../ansible/tailscale/policy.hujson")).hosts.pos,
    try(one(local.dns_replica_ipv4), null),
  ]

  lifecycle {
    prevent_destroy = true

    precondition {
      condition = (
        data.tailscale_device.homelab_dns_replica.authorized &&
        !data.tailscale_device.homelab_dns_replica.blocks_incoming_connections &&
        contains(data.tailscale_device.homelab_dns_replica.tags, "tag:homelab-dns") &&
        length(local.dns_replica_ipv4) == 1
      )
      error_message = "Enroll and authorize rpi4-dns with tag:homelab-dns, inbound connections enabled, and one tailnet IPv4 address before applying split DNS."
    }
  }
}
