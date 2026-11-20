# Homelab control-plane and DNS failover

Ansible manages the three k3s servers and the native Pi resolver. Argo manages
CoreDNS. POS retains its existing AdGuard Quadlet. Keepalived on POS and rpi4
moves the shared LAN address only while local API and DNS health checks pass.

## Addresses and prerequisites

| Host | OS / architecture | Wired IP | SSH / privilege |
|---|---|---|---|
| pos | AlmaLinux / amd64 | 192.168.1.28 | `pos`, sudo |
| optiplex | Alpine / amd64 | 192.168.1.27 | `optiplex`, doas |
| rpi4 | Alpine / arm64, about 4 GB RAM | 192.168.1.23 | `rpi4`, doas |
| Shared API/DNS | POS or Pi | 192.168.1.250 | API 6443; DNS TCP/UDP 53 |

Use stable node addresses and keep the shared address outside dynamic address
allocation.

`homelab/ansible/inventory.yaml` holds the selected addresses, k3s version and
three-server topology. Embedded etcd tolerates one failed server when two voters
remain healthy. The existing Pi SD card is selected explicitly; prefer SSD
storage when available. Keep snapshots and the matching server token off-node.
See [k3s HA](https://docs.k3s.io/datastore/ha-embedded) and
[backup/restore](https://docs.k3s.io/datastore/backup-restore).

The Pi's infrastructure taint keeps ordinary applications off it. Control-plane
HA does not replicate local-path PVCs; recover application data separately.

## Prepare or replace the Pi

Use the existing SSH key and doas. For a lost password, repair access from the
card on a trusted Linux machine; a reimage is unnecessary solely for account
recovery. A foreign standalone cluster must be explicitly retired before joining
POS. The join preflight refuses a different server/agent CA or unidentified
existing datastore; it never runs an uninstall or cluster-reset script.

A replacement Pi also needs the ARM64 k3s binary at `/usr/local/bin/k3s` before
running the cluster play. On the Pi, download the version selected in inventory
and verify the release checksum before installing it (do not start a standalone
cluster):

```sh
doas apk add --no-cache curl
version='v1.36.2+k3s1' # Keep aligned with k3s_version in inventory.yaml.
workdir=$(mktemp -d)
cd "$workdir"
curl -fLO "https://github.com/k3s-io/k3s/releases/download/$version/k3s-arm64"
curl -fLO "https://github.com/k3s-io/k3s/releases/download/$version/sha256sum-arm64.txt"
grep ' k3s-arm64$' sha256sum-arm64.txt | sha256sum -c - &&
  doas install -m 0755 k3s-arm64 /usr/local/bin/k3s
/usr/local/bin/k3s --version
cd / && rm -rf "$workdir"
```

From the repository root, using the Python environment where Ansible is installed:

```sh
export ANSIBLE_CONFIG="$PWD/homelab/ansible/ansible.cfg"
ansible-galaxy collection install -r oci/ansible/requirements.yaml
ansible-playbook homelab/ansible/prepare-pi.yaml
ansible-playbook homelab/ansible/network.yaml -e pi_network_apply=true
# Reboot only the Pi when applying a changed static address:
ansible-playbook homelab/ansible/network.yaml -e pi_network_apply=true -e pi_network_reboot=true
python3 homelab/scripts/readiness.py --allow-sdcard
```

Add `--ask-become-pass` if doas needs authentication. The preparation installs
Python/SFTP tools, enables cgroups at boot and creates the empty join directory.
The network play prefers Ethernet and keeps Wi-Fi recovery at 192.168.1.18.
Loose reverse-path validation supports both interfaces on the same subnet.
The Alpine server unit makes its root mount shared before k3s starts, as required
by the node exporter's read-only HostToContainer mount.

## Deploy and reconcile

Load the SOPS age identity through the existing PKI recovery procedure. Both
resolvers use the same encrypted settings and derived OCI records. Keep DHCP
disabled on both AdGuard instances. The Pi uses a digest-pinned ARM64 binary,
an explicit unprivileged account/group and an OpenRC service.

```sh
# Run from the repository root, including in a new shell.
export ANSIBLE_CONFIG="$PWD/homelab/ansible/ansible.cfg"
ansible-playbook homelab/ansible/cluster.yaml
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
ansible-playbook homelab/ansible/dns-secondary.yaml
ansible-playbook homelab/ansible/api-endpoint.yaml
```

The cluster play checks all hosts before changing POS, fetches an offline
SQLite/token/configuration archive into ignored `homelab/private/backups`, then
converts POS with `cluster-init`. It preserves the existing CA and token,
promotes Optiplex without uninstalling its agent, and joins the Pi last. Each
server must be Ready before proceeding; do not interrupt the temporary
two-voter stage. Reruns reconcile configuration rather than repeat conversion.

Keepalived uses unicast VRRP (IP protocol 112) between the two frontends. Its
health script requires authenticated local API readiness and the exact local
`pos.home.internal` DNS answer. The unconditional record also works with POS's
rootless networking; client-scoped wildcard answers are unsuitable for a local
probe. On POS, only this root-owned script receives the persistent keepalived
SELinux execution label. SELinux stays enforcing.

The CoreDNS Application uses `kubernetes/coredns/overlays/ha`: two private-zone
upstreams and an HPA maintaining at least two replicas. During pre-merge testing,
the live child Application can be pinned to the reviewed PR revision; the
parent's existing `RespectIgnoreDifferences` setting permits a scoped exception
for this child's source path/revision. After merging:

```sh
kubectl -n argocd patch application coredns-config --type=merge \
  -p '{"spec":{"source":{"targetRevision":"main","path":"kubernetes/coredns/overlays/ha"}}}'
# Remove only coredns-config's temporary source exception; retain other entries.
kubectl -n argocd edit application homelab
```

Configure LAN clients or DHCP DNS options to use the shared address after checks
pass. Do not advertise a public resolver as fallback for private names.

## Tailnet split DNS

Deploy the native Pi resolver first. Follow the
[tailnet policy procedure](../oci/docs/operations.md) and load the Terraform
credential. The full root looks up the enrolled Pi, so bootstrap the DNS tag
with a policy-only plan. From the repository root:

```sh
umask 077
terraform -chdir=oci/terraform plan -target=tailscale_acl.tailnet -out=tailnet-dns-bootstrap.tfplan
terraform -chdir=oci/terraform show tailnet-dns-bootstrap.tfplan
```

Confirm that the plan only adds the DNS tag and its scoped TCP and UDP port 53
grant and policy tests. Apply the reviewed plan before enrolling the Pi:

```sh
terraform -chdir=oci/terraform apply tailnet-dns-bootstrap.tfplan
```

Generate a one-time, non-ephemeral Tailscale auth key for
`tag:homelab-dns` and save it in a private local file. From the repository
root, run:

```sh
ansible-playbook -i homelab/ansible/inventory.yaml homelab/ansible/dns-tailnet.yaml \
  -e dns_tailnet_auth_key_file=/private/path/to/one-time-key
ssh rpi4 'doas -n tailscale ip -4'
```

The enrollment uses hostname `rpi4-dns` and leaves the Pi's host DNS
configuration in place. Approve the device if the tailnet requires it.
Remove the one-time key file after enrollment. Test the Pi's tailnet address
from a member device using both transports before changing split DNS:

```sh
dig @PI_TAILNET_IP pelican.home.internal
dig +tcp @PI_TAILNET_IP pelican.home.internal
dig @PI_TAILNET_IP wings-01.oci.home.internal
```

After enrollment and the direct DNS checks, resume full-root planning with a
Terraform credential with policy access, DNS write access, and device read
access. Review the split DNS change before applying it. The import block
adopts the existing split DNS entry. Review the plan for the two resolver
addresses on `home.internal`. After applying, check `tailscale dns status` and
resolve both names using the client's normal lookup path. Test resolver failover
by stopping POS AdGuard, checking both lookups from a tailnet client, then
restoring POS and checking it directly. Repeat with the Pi resolver stopped.
Tailnet Kubernetes API access and application availability depend on their own
endpoints and access policy.

## Checks and recovery

```sh
kubectl --server=https://192.168.1.250:6443 get nodes -o wide
dig @192.168.1.250 github.com
dig +tcp @192.168.1.250 pelican.home.internal
kubectl -n kube-system get pods -l k8s-app=kube-dns -o wide
ssh pos 'sudo /usr/local/bin/k3s etcd-snapshot save --name homelab-ha'
```

Test one failure at a time. Stop the active frontend's DNS service, confirm the
VIP moves, and repeat authenticated API read/write and UDP/TCP DNS checks.
Restore it before testing a server/API outage; require two healthy etcd voters
throughout. Keep direct-node kubeconfigs and SSH available for recovery.

Use `systemctl --user status adguardhome.service` on POS, and
`doas /sbin/rc-service adguardhome status` on the Pi. Inspect `keepalived` logs
and `/usr/local/sbin/homelab-ha-health` when a healthy frontend does not own the
VIP. With `nopreempt`, either healthy frontend can remain the active owner.

For a failed join, inspect `journalctl -u k3s` on POS or `/var/log/k3s.log` on
Alpine. Never reset a healthy surviving quorum or discard its token. Before
restoring the pre-etcd SQLite archive, stop and isolate all converted servers;
do not run two clusters with the same identity. Keep datastore snapshots
separate from application/PV backups.
