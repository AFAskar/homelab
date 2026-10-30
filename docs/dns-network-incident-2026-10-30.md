# DNS / homelab reachability investigation — October 30, 2026

During the OCI game-pool verification, the operator laptop could no longer
reach pos at 192.168.1.28:22/53/5353. Both pos and optiplex appeared offline
in its Tailscale peer status. Public DNS through 1.1.1.1 and the OCI Wings
nodes remained reachable. Local DNS failure then prevented Terraform from
reading its OCI state backend and initially prevented a normal Git push.

## Findings

- Neither homelab host rebooted: pos had more than a day of uptime; optiplex
  more than 20 days. No kernel link-reset or OOM event was logged on pos in
  the examined 10:45–11:20 UTC window (13:45–14:20 Riyadh).
- AdGuard's container started October 29 at 16:22 UTC and was still running
  after recovery, with restart count zero. No container restart explained
  the outage, and its work/config volumes remained intact.
- Pos's tailscaled logged repeated unanswered DNS requests to 192.168.1.1
  beginning at 11:05:38 UTC (14:05:38 Riyadh), and a control connection reset
  at 11:16:10 UTC. Router DNS timeouts also appeared after reachability
  recovered, so these messages alone do not establish the outage's cause.
- Pos/optiplex, LAN DNS and Panel recovered without an operator-requested
  container restart. The subsequent game-pool Terraform reconciliation
  returned exit 0/no changes; private Wings health and Panel HTTPS passed.

The retained evidence establishes a reachability failure and no observed
host/container crash. It does **not** identify the physical/router/AP trigger
or prove that AdGuard's upstream provider caused it. Router/switch/AP logs
are still needed for that conclusion. A router login tab was available, but
an extension popup blocked automation; router log inspection awaits access.
No router settings were changed.

Raw logs and generated check results remain in ignored
`oci/inventory/dns-investigation/`; they are not repository source.
