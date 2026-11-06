# Homelab control-plane and DNS failover

Use Ansible for host changes and the existing Argo application for Kubernetes
DNS. The intended embedded-etcd membership is POS, Optiplex and rpi4. POS and
rpi4 also serve AdGuard independently and share a reserved LAN virtual IP
through unicast Keepalived. The Pi has an infrastructure taint to keep ordinary
application workloads off it.

## Inventory and prerequisites

| Host | OS / architecture | Wired address | SSH / privilege |
|---|---|---|---|
| pos | AlmaLinux / amd64 | 192.168.1.28 | `pos`, sudo |
| optiplex | Alpine / amd64 | 192.168.1.27 | `optiplex`, doas |
| rpi4 | Alpine / arm64, about 4 GB RAM | 192.168.1.23 | `rpi4`, doas |

The Pi's existing Wi-Fi recovery address is 192.168.1.18. Keep its
wpa_supplicant configuration until wired access has been tested. Reserve the
wired address in the router; do not turn an arbitrary DHCP lease into a static
server address without excluding/reserving it first.

Embedded etcd needs three voters to tolerate one server failure. Its writes
benefit from SSD storage; the Pi's SD card requires an explicit
`ha_allow_sdcard: true` choice. Keep POS and Optiplex on their existing disks.
Do not take either of those two servers offline while the Pi is unhealthy.
See the official [etcd HA guide](https://docs.k3s.io/datastore/ha-embedded) and
[hardware requirements](https://docs.k3s.io/installation/requirements).

Keep the pinned k3s version in `homelab/ansible/inventory.yaml` aligned with the
existing cluster. This migration uses existing binaries and does not perform
a Kubernetes upgrade. Preserve the POS cluster identity, server token, node
passwords, data directory and application volumes.

From the repository root:

```sh
ansible-galaxy collection install -r oci/ansible/requirements.yaml
python3 homelab/scripts/readiness.py --host rpi4
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/prepare-pi.yaml --ask-become-pass
```

Use `--ask-become-pass` when doas requires authentication. If the password is
lost, power off the Pi and attach its card to a trusted Linux machine. Identify
the card by its partition UUID and Alpine filesystem, back up its configuration,
and repair doas access for the existing SSH administrator. Avoid reformatting a
working filesystem merely to recover a password. Set a new account password
with `doas passwd rpi4` after recovery; keep it in the password manager.

## Select the failover address

Reserve a currently unused address in 192.168.1.0/24 outside the dynamic DHCP
pool. Check the router's leases and ARP table and probe for conflicts from the
wired network before using it. Do not reuse a host address, gateway, network or
broadcast address. The shared VIP serves TCP/6443 for Kubernetes and TCP/UDP 53
for DNS. POS and rpi4 need unicast VRRP (IP protocol 112) to each other.

Create an ignored operator file, `homelab/private/ha.yaml`, with the selected
address and completed preparation choices:

```yaml
ha_virtual_ip: YOUR_RESERVED_LAN_IPV4
ha_topology_reviewed: true
dns_wired_address_reserved: true
ha_allow_sdcard: true # Only when intentionally using the existing SD card.
pi_wired_static: true # Set only after reserving the Ethernet address.
```

Leave deployment gates closed until those facts are established. The committed
inventory deliberately contains no invented VIP.

## Prepare the Pi without losing its existing cluster

The Pi may already be a standalone k3s server. Never point that datastore at
POS, run an uninstall script, or erase its state as an implicit join step.
Inventory its namespaces, workloads, PVs, mounted application paths and node
configuration using its local kubeconfig:

```sh
ssh rpi4 'doas /usr/local/bin/k3s kubectl get nodes,pv -o wide'
ssh rpi4 'doas /usr/local/bin/k3s kubectl get pods,pvc -A -o wide'
```

Export application data that must survive separately from the database.
Gracefully stop those workloads, then stop only the standalone server. Create
an offline archive of `/var/lib/rancher/k3s`, `/etc/rancher/k3s`,
`/etc/rancher/node`, `/etc/init.d/k3s` and its configuration/environment files.
Copy it off the Pi, verify its checksum and record how to restore it. Keep the
archive private: it includes cluster credentials. Inspect any hostPath or local
PV data outside those paths and back that up separately.

After explicitly retiring that standalone cluster, move its state and
configuration into a private recovery directory; do not delete it. The new
join must start with no foreign server/agent CA, no old datastore and no old
`/etc/rancher/node/password`. The playbook checks CA identity before changing
POS and refuses foreign state. It does not automate retiring another cluster.

If using an SSD, mount its existing prepared filesystem persistently at the
selected data path and verify it after reboot before joining. With an SD card,
keep enough free space for both the recovery copy and new datastore; move the
archive off-node rather than retaining multiple large copies on the card.

Stage and apply wired networking while retaining Wi-Fi recovery:

```sh
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/network.yaml \
  -e @homelab/private/ha.yaml
# Apply Ethernet preference while retaining Wi-Fi recovery.
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/network.yaml \
  -e @homelab/private/ha.yaml -e pi_network_apply=true
# Apply the reserved static address during a Pi-only reboot.
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/network.yaml \
  -e @homelab/private/ha.yaml -e pi_network_reboot=true
ssh rpi4 'ip route get 192.168.1.28'
ssh -i ~/.ssh/KaliVM rpi4@192.168.1.23 hostname
```

Before reservation, the network play can retain Ethernet DHCP by keeping
`pi_wired_static: false`. Wi-Fi's default and connected routes use metric 600
so Ethernet is preferred. `readiness.py --allow-sdcard` evaluates the selected
SD-card setup without treating the absence of an SSD as an unresolved choice.

## Deploy independent DNS

Load the SOPS age identity through the existing PKI recovery procedure. Both
resolvers use the same encrypted desired settings and derived OCI records.
Keep DHCP disabled on the replicas. POS retains its rootless Quadlet; Alpine
uses a native unprivileged AdGuard binary supervised by OpenRC, since Alpine
does not run systemd/Quadlet. The ARM64 release archive is pinned by SHA256.

```sh
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/dns-secondary.yaml \
  -e @homelab/private/ha.yaml
dig @192.168.1.28 pelican.home.internal
dig +tcp @192.168.1.23 pelican.home.internal
dig @192.168.1.23 wings-01.oci.home.internal
```

The Pi binds DNS to its wired IP at 5353 and its authenticated UI to that IP
at 3000. Its own firewall redirects LAN port 53 and restricts DNS/UI sources.
Settings, filters and credentials are reconciled from Git; query history and
statistics remain local to each resolver. Apply settings through Ansible rather
than independently editing the two UIs.

## Convert and join the control plane

Verify fresh SSH and administration on all three hosts before starting.
Review the existing POS service arguments and critical k3s settings, including
cluster/service CIDRs, domain, Flannel backend and disabled components. All
servers must agree; the inspected cluster uses the k3s defaults. If those
settings have changed, reconcile them in inventory/playbooks before migration.
Keep LAN 6443, inter-server 2379/2380, Flannel UDP 8472 and kubelet 10250
available between the three hosts. Do not expose those ports publicly or
disable host firewalls as a shortcut.

```sh
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/cluster.yaml \
  -e @homelab/private/ha.yaml
kubectl get nodes -o wide
ssh pos 'sudo /usr/local/bin/k3s etcd-snapshot save --name initial-three-server'
```

The playbook preflights every host before touching POS. It briefly stops POS
for an offline archive, fetches that archive into ignored private storage, then
converts SQLite with `cluster-init`. It preserves the original CA/token and
promotes Optiplex without uninstalling its agent or deleting its volumes. The
Pi joins last. Each server must become Ready before proceeding. A two-voter
intermediate cluster cannot tolerate a failure; complete the third join before
performing any availability test.

Default k3s etcd snapshots stay local to each server. Copy snapshots and the
matching server token to encrypted off-node backup storage. A snapshot without
the token cannot recover the cluster's bootstrap data. Test restoration on
isolated infrastructure; keep snapshot archives separate from application/PV
backups.

## Activate API and DNS failover

```sh
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/api-endpoint.yaml \
  -e @homelab/private/ha.yaml
```

Keepalived advertises the shared IP only when the local authenticated Kubernetes
API and local DNS both pass health checks. It uses a local API directly on
6443; it does not proxy control-plane traffic through a single host. The VIP
is included in every server's API certificate. Update the administrator
kubeconfig endpoint to `https://VIP:6443` and verify CA-authenticated access.
Keep direct node kubeconfigs for recovery. Configure new agents to register
through that endpoint with the existing cluster token.

Advertise the shared DNS IP through LAN DHCP. Alternatively, clients that
support multiple resolvers can use POS and Pi directly. Verify both UDP and
TCP queries during failover. Do not add a public fallback resolver for
`home.internal`; it cannot answer the private zone.

After both independent resolvers pass checks, change the existing
`coredns-config` Argo application's source path from
`kubernetes/coredns/manifests` to `kubernetes/coredns/overlays/ha`, review its
diff and sync. Commit that Application path change when activating the overlay
so the parent GitOps root does not revert it. The overlay forwards the private
zone to both resolvers and maintains at least two CoreDNS replicas through an
HPA. Inspect placement to ensure Ready endpoints are on different nodes.
The current base remains active until the Pi resolver is ready.

The LAN VIP is not automatically reachable through Tailscale. Before claiming
remote DNS/API failover, enroll the Pi in the existing tailnet, obtain its real
tailnet address, add only the required DNS/administration grants and configure
both actual tailnet resolver addresses in split DNS. Preserve unrelated tailnet
settings and use the existing Terraform policy owner. Do not invent a tailnet
IP or advertise a whole home subnet merely to make this VIP reachable.

## Checks and recovery

During an approved maintenance test, stop only one frontend's Keepalived
service and confirm the VIP moves to the other host. Run authenticated
`kubectl get nodes` through the VIP and repeat public/private DNS lookups.
Test one server outage at a time; require two healthy etcd voters throughout.
Restore the service and verify it rejoins before testing another host.

Control-plane and DNS HA do not replicate local-path application volumes.
Inspect PVC node affinity before expecting a workload to move off POS or
Optiplex. Use each application's data backup/recovery procedure separately.

For a failed join, keep the preserved files and inspect logs: `journalctl -u
k3s` on POS, `/var/log/k3s.log` on Alpine, and `rc-service k3s status`. Do not
run `cluster-reset` on a healthy surviving cluster or delete a member's state
while it still belongs to etcd. Follow the official
[etcd backup/restore procedure](https://docs.k3s.io/datastore/backup-restore).

Before any rollback to the pre-etcd SQLite archive, stop all new servers and
isolate them from the old cluster. Restore the original POS state and service
configuration from the verified archive. Never run a restored SQLite cluster
alongside the converted etcd cluster with the same identity.

For Pi DNS configuration recovery, stop `adguardhome`, restore its private
configuration backup, then start it and query its wired address directly. POS
DNS remains independently operated through its existing Quadlet runbook.
