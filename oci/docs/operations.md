# Operations and recovery

Use the same Terraform root, OCI profile/region and private DNS for all operations. Obtain the applicable approval before billable or destructive actions.

## Private administration and DNS

Thor's key is available through Bitwarden; run `python3 oci/scripts/select-ssh-agent-key.py`. Bootstrap with explicit `IdentityAgent` and the selected public key at `ubuntu@100.89.233.80`. The private key stays in Bitwarden. Thor uses both private and tailnet SSH listeners. During a rebuild, use `bootstrap-router.yaml` over the existing tailnet path to restore the private listener before switching administration to 10.10.50.10. Other Linux private IPs and Windows IP come from `terraform output`. Administrators accept the approved OCI routes (`tailscale set --accept-routes=true` on Linux). Only the router runs Tailscale; Wings peers and Windows do not.

The policy source is `ansible/tailscale/policy.hujson`. Maintain the following scoped grants and their embedded acceptance/denial tests:

| Source | Destination | Permitted traffic |
|---|---|---|
| azoz-laptop + freyr | pos, optiplex, Thor/router | OpenSSH TCP/22 |
| azoz-laptop | freyr | SSH TCP/22 and RDP TCP/3389 |
| Both admin clients | pos/optiplex tailnet and known LAN addresses | HTTP/HTTPS TCP/80,443 |
| Owner iPhone (100.88.31.107) | pos/optiplex tailnet addresses | HTTP/HTTPS TCP/80,443 |
| Owner iPhone | Wings subnet | HTTPS Wings browser console and API endpoints TCP/8080 |
| Both admin clients | pos tailnet/known LAN address | Kubernetes API 6443, AdGuard UI 3000, DNS TCP/UDP 5353 |
| Both admin clients | 10.10.50.0/24 Wings subnet | SSH 22, Wings API 8080, SFTP 2022, metrics 9100 |
| Both admin clients | wings-02 private IP | TCP/3389 to the nested guest only |
| pos + optiplex | Wings subnet and router tailnet address/tag | TCP/8080,9100 only |
| Thor/router tag | pos tailnet address | TCP/8443, authenticated Panel daemon API only |
| Other tailnet devices | Infrastructure | No grant; default denied |

`azoz-laptop` (100.66.202.74) and `freyr` (100.82.125.5) are the trusted admin clients. The verified tailnet owner account can assign `tag:oci-router`, but owning a device does not automatically grant it network administration access. The owner's iPhone can reach homelab web services and the Wings HTTPS listener on TCP/8080, including browser-console and API paths such as `/api/system`. Tailscale filters addresses and ports, not HTTP paths; Wings authentication still governs those API requests. The phone's SSH, SFTP, metrics, Kubernetes API, AdGuard UI, RDP and the dedicated callback listener remain denied. Other members' devices and the old home-router device have no application or administration grant. Tailnet members retain TCP/UDP 53 to pos for the existing `home.internal` split-DNS resolver; pos redirects that traffic to AdGuard on 5353. This DNS-only exception does not grant server administration. Align the router's `router_tailnet_admin_sources` with these two admin IPs. Review this trust choice before applying.

On the iPhone, connect Tailscale and enable its DNS settings before opening `https://pelican.home.internal`. Install the public `pki/homelab-root-ca.crt` certificate as an iOS configuration profile and enable it under Settings → General → About → Certificate Trust Settings. Transfer only this public certificate; never a CA private key. A certificate warning after connectivity works requires checking this trust setting and the hostname, rather than bypassing TLS.

This is an IPv4 management policy; native IPv6 and ICMP are not granted. Use the documented IPv4 private/tailnet addresses for connection checks; routing health probes use TCP rather than ping. Known homelab LAN /32 rules only authorize traffic: they do not create a home subnet route or revive the offline home router. Public game clients use public OCI game addresses and are outside these tailnet grants. Kubernetes node-to-node LAN/CNI traffic is not altered by a tailnet policy.

Before saving, back up the current policy, preserve any unrelated DNS/nodeAttrs/settings, and **remove the old allow-all ACL/grants**. Adding this policy's scoped grants alongside allow-all does not restrict anything because grants are additive. The explicit empty `acls` and `ssh` sections remove legacy blanket network/Tailscale-SSH rules; normal OpenSSH still uses the TCP/22 grants and existing SSH keys. Validate the complete candidate with the `tailscale_acl.tailnet` Terraform plan and require its embedded `tests` to pass, including denied ordinary users and denied server-to-admin SSH. Local JSON/selector checks do not replace that control-plane validation. The policy is managed from the existing OCI Terraform root; bootstrap the scoped OAuth credential as described in the README and keep routine policy changes in Git. Do not save the browser preview to bypass Terraform. Probe addresses ending in .20 in the tests exercise subnet rules; they are not invented VM assignments.

### Policy writer and recovery procedure

The [pinned provider's Update implementation](https://github.com/tailscale/terraform-provider-tailscale/blob/v0.29.3/tailscale/resource_acl.go#L122) replaces the whole policy without an ETag. `overwrite_existing_content=false` only guards creation; Terraform state locking cannot serialize console edits. Enforce a single operator/writer: no concurrent console, CLI, CI or second-root policy writes, and no unattended apply. Keep the authenticated admin-console recovery path available while testing.

Before any emergency console recovery edit, stop/cancel pending policy applies and suspend further Terraform writes. Invalidate **all** saved plans containing the tailnet policy, including full infrastructure plans, and mark the incident time. Preserve a private copy of the live policy for recovery; restore only the access required. Never resume a pre-incident plan. Reconcile the recovered live policy into `policy.hujson`, retain and rerun its access tests, and obtain a fresh Terraform plan with refresh enabled. Review its complete policy diff and approval again, then apply promptly with exclusive writer ownership. If another edit occurs during review or apply, stop and regenerate; do not overwrite the newer recovery policy. This procedure is the concurrency protection for this provider version, not an automatic ETag guarantee.

No autoApprovers are included. After the reviewed router bootstrap advertises them, approve **only** `10.10.50.0/24` and `10.10.10.0/24` on Thor in Machines → Subnets → Edit. Route approval and access grants are separate. Manage device expiry and persist tailscaled. Use a tagged scoped one-use authentication key only if enrollment is necessary; the existing authenticated Thor should not need one. Standard subnet-router SNAT means OCI targets see router source 10.10.50.10/32; no return route to the tailnet is required. No default/exit-node route is granted. The reviewed policy is applied live; Thor advertises both approved routes.


`render-inventory.py` refreshes the desired monitoring EndpointSlice from Terraform outputs. The complete [AdGuard deployment](../../docs/dns-adguardhome.md) derives the exact Wings DNS rules from that tracked desired configuration. Run `ansible-playbook dns.yaml` from `oci/ansible/`; it imports the single authoritative deployment for encrypted settings, Quadlet, boot and firewall configuration. There is no separate live-config patcher. CoreDNS continues forwarding this zone to pos:5353. The existing `home.internal` catch-all rules exclude `oci.home.internal`, so each Wings name returns only its private address. Test pod and browser resolution after an address change.

Manage DNS through `ssh pos 'systemctl --user status adguardhome.service'` and the AdGuard Ansible deployment. Its rootless Quadlet owns startup, ports and restart policy; the Compose wrapper is for other Compose workloads.

`pelican.home.internal` resolves to Traefik at home and to 10.10.50.10 only on OCI guests. The callback proxy connects directly to pos’s tailnet IP with verified TLS SNI; no home LAN subnet route is required.

The Panel Kustomize base includes separate cert-manager Certificates for each Wings hostname and the callback proxy, issued by the existing `homelab-ca` ClusterIssuer. After the approved GitOps deployment, run `python3 oci/scripts/export-node-certificates.py` from the repository root. It waits for Ready, validates the CA chain, hostname, key match and at least seven days of remaining validity, then exports only leaf TLS bundles to ignored `oci/ansible/secrets/<node>/` with private permissions. The proxy has its own key even though it shares Panel's hostname. No CA private key leaves the cluster or existing PKI workflow. Store Panel-generated Wings configs in the same private directories. For renewal, rerun the helper and the Wings/proxy playbooks; cert-manager renewal alone does not refresh guest files.

Install the homelab root CA on browser clients. Panel mounts a trusted CA bundle; Wings installs the root to Ubuntu trust. Do not use `curl -k`, PHP `verify=false`, browser certificate bypass or plaintext Wings for acceptance. Verify websocket console connections after renewal. Existing PKI recovery procedures remain in `docs/pki-bootstrap.md`.

## Panel and Wings enrollment

Manually sync Argo `pelican` after approval; no automated sync/prune is enabled. Check PVC placement and set its PV reclaim policy to Retain. SQLite, `.env`, application storage and logs use the 10 GiB PVC. The SOPS-managed Kubernetes Secret supplies APP_KEY; include the effective Secret as well as SQLite in off-node backups.

From the repository root, initialize the pinned release through its supported schema/models/services:

```bash
python3 oci/scripts/export-node-certificates.py
python3 oci/scripts/configure-panel.py --initialize --admin-email YOUR_ADMIN_EMAIL
```

Use `--initialize` on first setup or a reviewed schema update; it runs the release migrations and seeds without dropping tables. Ordinary reruns can omit it. The helper preserves existing administrator passwords, refuses to promote an existing non-admin account, preserves node tokens, checks existing node hostname/TLS/data paths, and saves secrets only in ignored mode-0600 files. Retrieve the bootstrap password privately from `oci/ansible/secrets/panel-admin.json` and store it in the password manager. It disables the web installer after initialization. The official image’s bundled queue worker and scheduler are reused; verify `queue-worker` and `supercronic` with `supervisorctl status`.

The active private node names use HTTPS 8080 and SFTP 2022. Paid nodes reserve 2 GiB RAM and 10% disk headroom: wings-01 allows 30 GiB / 360 GiB and 800% CPU, wings-02 allows 14 GiB / 60 GiB and 400% shared CPU after reserving Windows/host capacity; Thor uses 20 GiB / 80 GiB of its existing capacity. Paid game data is `/srv/pelican/volumes`; Thor uses `/var/lib/pelican/volumes`. Root CA trust, per-node certificates and non-overlapping Docker networks remain prerequisites. Config export uses `/etc/pelican/tls/` and the private Panel URL. No enrollment token is committed.

The approved public game pool is **25565–25765 inclusive**, TCP and UDP, on every Wings node: 201 port numbers per node. `configure-panel.py` idempotently reserves that pool using each node's actual private VNIC IP, preserving occupied allocations. The existing acceptance game uses 25565; the other 200 allocations per node start free. OCI public IP is external NAT, not the Linux bind address. Store mappings from Panel allocation to public endpoint; ephemeral paid public IPs may change on replacement. For a new game inside this pool, select free primary/additional allocations in Panel, choose a compatible egg/runtime and resource limits, then install/start it. No further OCI or host-firewall change is needed for ports within the pool. Games needing ports outside it require a reviewed Terraform/Ansible update. The pool is available on every active node; do not use its public ports for RCON or other administrative listeners. Port numbers may be reused on different nodes, but two servers cannot own the same node/IP/port allocation. SSH/RDP/API/exporter/SFTP stay private. Verify public games using an external client independent of the tailnet. Check native ARM manifest/egg for Thor; x86-only games belong on paid AMD nodes.

For Simple Voice Chat, assign an additional allocation to the Minecraft server
(for example UDP 25566), set `port=25566` in
`config/voicechat/voicechat-server.properties`, then gracefully restart that game
server after saving the world. Editing the file or reserving an allocation does
not move the running listener. Check the startup log for `Voice chat server
started` and the selected port. Connect players using the node's public game
address; the private subnet's administration grants do not include game ports.

`Test-NetConnection -Port` tests TCP, so a failed TCP test on a UDP-only voice
port is expected. Use the [official Simple Voice Chat UDP tester](https://github.com/henkelmax/svc-cli-utils)
with `svc ping PUBLIC_IP:25566`, or run `/voicechat test PLAYERNAME` in-game.
A valid UDP reply verifies the game path; a Docker port mapping alone does not
prove that the application listens behind it.

For a fresh Chunky job that must stop when players return, install
`oci/scripts/chunky-until-player.py` as `/usr/local/sbin/chunky-until-player`
on the Wings host (root-owned, mode 0700). It requires the host's Python/PyYAML,
Wings configuration, and trusted node TLS certificate. Start it as a transient
service, substituting the server UUID, certificate DNS name, spawn X/Z and radius:

```bash
sudo systemd-run --unit=dndmc-chunky-until-player --collect --property=Restart=no \
  /usr/bin/python3 -u /usr/local/sbin/chunky-until-player \
  --server-uuid SERVER_UUID --tls-name NODE_CERTIFICATE_DNS_NAME \
  --center SPAWN_X SPAWN_Z --radius 5000
sudo journalctl -u dndmc-chunky-until-player -n 20 --no-pager
```

Run `chunky spawn` in the game console to read the current spawn center first.
The watcher verifies an empty server before starting, follows player-join log
messages, and polls `list` as a fallback. The first player join pauses the
Overworld task and ends the watcher. It also attempts to pause if its player-count
checks fail. It neither resumes after players leave nor starts after a host reboot.
Use `chunky progress` to check the task and `chunky continue` to resume it manually;
manual continuation does not reinstall the watcher. Do not run a second generator
alongside Chunky or use this fresh-task command to replace a saved task.


For the deployed acceptance workload, run `python3 oci/scripts/configure-panel.py --admin-email YOUR_ADMIN_EMAIL --test-games` from the repository root. The optional flag imports the reviewed declarative `oci/pelican/egg-mindustry-acceptance.json` and creates one server per node only if absent; it preserves existing servers. The pinned Mindustry v160.7 JAR and multiarch runtime run natively on both architectures. Run `python3 oci/scripts/check-games.py` from an external client to check TCP, real UDP discovery responses and absence of public administrative listeners. This verifies protocol responses, not an interactive player session.

## Backups and restores

No automatic paid snapshots are enabled. From the trusted operator laptop, `capture-backup.py` makes a consistent SQLite online backup and includes Panel storage, plugins, `.env`, the effective Kubernetes APP_KEY Secret and its SOPS source. For explicitly selected game UUIDs it optionally sends a save command, gracefully stops running games, archives only their data and attempts to restart every previously running selected game, including on failure. It refuses forced shutdown and archives no running selected game. No game UUID means Panel-only backup without game interruption. It requires Python 3.11+, kubectl, age, tar and the existing verified SSH identities; no OCI private key is copied to a guest.

```bash
mkdir -p oci/inventory/backups
chmod 700 oci/inventory/backups
# Add --server-uuid UUID for each deliberately selected game.
python3 oci/scripts/capture-backup.py \
  --server-uuid YOUR_GAME_UUID --save-command 'save homelab-backup' \
  oci/inventory/backups/selected.tar.age
BACKUP_QUIESCED=yes oci/scripts/backup.sh oci/inventory/backups/selected.tar.age
```

The save command above is Mindustry-specific; use the selected game's supported command or omit it when graceful shutdown saves the game. Outputs and temporary plaintext use private permissions; plaintext staging is removed after encryption to the existing repository recovery recipient. Ciphertext is staged privately on the output filesystem and published only after tar/encryption succeed, without overwriting another writer's output. Failed encryption removes the partial ciphertext instead of leaving a misleading final archive. Keep the recovery identity separately. Upload uses the Terraform-managed private bucket and attaches SHA256 metadata as well as printing a local checksum. The deployed operator can upload/restore with existing credentials. Use bucket-scoped writer/reader roles for any future automation; never install tenancy-wide credentials on Wings.

Retention target: 14 daily selected backups, with a weekly size check to stay near 50 GB average. No recurring capture scheduler or automatic deletion/locked retention is installed. Schedule on an approved existing operator host if wanted; the capture requires its SSH agent and Kubernetes access. Growing data changes cost, and object deletion requires approval. Persist archive checksums outside the bucket. Selected game data, not every disk, is protected by this procedure.

Restore into a **new empty staging directory**: download the named object with `oci os object get`; compare its SHA256 to both the local record and `opc-meta-sha256` from `oci os object head`; age-decrypt and extract the outer archive; verify every member against `manifest.json`. Extract `panel.tar.gz` into another fresh directory, run SQLite `PRAGMA integrity_check`, and recover the effective APP_KEY with that database and application storage. Extract each selected game archive separately and check saved worlds/binaries. For an actual recovery, stop the affected server/Panel first, review destination ownership and only then restore files and the Secret together. Never overwrite live data merely to test recovery.

Paid game data survives reboot through an ext4 UUID mount. Wings RequiresMountsFor prevents accidental use of an unmounted boot directory. Compute/volume prevent_destroy guards against accidental Terraform destruction; preservation imports do not relocate existing Thor data. Rebuilding a paid node requires a reviewed instance-only replacement while preserving data/boot disks, then reattachment and UUID remount; do not remove protection or recreate disks blindly. Reuse discovered filesystems and never format an existing disk. Full disaster recreation requires network import/state recovery first and a confirmed Windows image workflow; imported freeze rules must be reconciled before claiming a complete greenfield recreation.

## Nested Windows lifecycle on wings-02

Use `ansible-playbook lab.yaml` from `oci/ansible/` after the reviewed host resize and network policy. It installs native KVM/libvirt, OVMF and swtpm without formatting or enlarging the existing data volume. Inspect `systemctl status libvirtd lab-firewall`, `/dev/kvm`, `virsh -c qemu:///system list --all`, `findmnt /srv/pelican` and `/srv/pelican/lab`.

Follow the [bundle workflow](../README.md#send-and-run-a-windows-guest). A bundle contains matching disks, domain XML, firmware, NVRAM and TPM state; `--save` also captures RAM and leaves the source stopped. Never copy a running disk by bypassing QEMU locks. Do not resume the original and later reuse its checkpoint with modified disks. A plain QCOW2 image cold-boots Windows; it cannot preserve an unsaved desktop by itself.

```bash
oci/scripts/send-guest.sh oci/windows/work/bundles/mpmb
oci/scripts/start-windows.sh mpmb-windows11
oci/scripts/status-windows.sh mpmb-windows11
oci/scripts/stop-windows.sh mpmb-windows11
```

The tools read the exact shared host's private IP/profile from Terraform and use SSH; none issues an OCI host start/stop action. Stopping Windows saves RAM and preserves its disk/TPM/NVRAM while Wings keeps running. A successful restore consumes the cloud working checkpoint; retain exported sending-side bundles as immutable recovery points. A failed restore leaves the checkpoint intact and does not silently cold-boot.

For the prepared `win11-lab` guest, retrieve the login from ignored `oci/ansible/secrets/windows-lab.json` (mode 0600) and store it in your password manager. Do not paste its contents into chat, command arguments or Git. Imported personal guests retain their own accounts.

The RDP endpoint is wings-02's private IP, TCP/3389, through Thor. Only the two admin clients receive this grant. The host DNATs to the one active guest at 192.168.124.10 and SNATs to bridge gateway 192.168.124.1. Configure Windows Firewall to allow that gateway, NLA enabled, and confirm `Get-Tpm` and `Confirm-SecureBootUEFI` from an elevated guest console. Use private libvirt/SPICE over SSH for first-boot repair; never expose public RDP, VNC or libvirt TCP. Keep passwords in the password manager and never in a command argument, Terraform state or Git.

CPU/QEMU machine/firmware/TPM compatibility determines whether saved RAM can move between hosts. For repeated transfers use a common CPU profile; changing the source profile requires a guest cold boot, not a Linux host reboot. The import tool validates files and rejects unsupported devices, remote backing files, insufficient space/RAM and another active guest. It does not stop games to make room. Only one nested guest runs at a time behind the stable RDP endpoint.

Disk/state backups contain credentials and keys: use private 0700 directories and encrypted off-node storage. Do not copy an active TPM directory or modify a guest disk while it has a pending RAM checkpoint. A node rebuild must preserve `/srv/pelican/lab`, then reinstall the role and re-register existing domain XML. A checkpoint may need its original QEMU/firmware versions; diagnose restore errors before choosing an explicitly approved cold boot. Never reset TPM or Secure Boot to make a state restore pass.

## Monitoring and troubleshooting

Existing Prometheus is reused. Ansible enables node-exporter systemd metrics for Wings/Docker/tailscaled/Caddy and bounded journald logs (200 MB/14 days). The monitoring manifests provide the private exporter ServiceMonitor, public-game TCP Probe and alerts. The small blackbox exporter runs in the existing cluster; no paid monitoring VM is added. Run `render-inventory.py` after approved OCI changes, review its EndpointSlice and Probe target updates, then commit/sync those desired monitoring manifests. They are GitOps deployment inputs consumed by Prometheus; transient query results and validation reports stay in the ignored inventory. Keep exporter and public-game targets aligned with the active Terraform instances; remove probes for deleted game servers. TCP monitoring does not replace the application-level UDP checks in `check-games.py`. `healthcheck.py` checks actual private TCP routes and certificate-verified Wings API responses; it does not register nodes or prove game availability. Run it from the administrator and repeat equivalent tests inside Panel pods on **both** k3s nodes. Monitor disk space, load/memory and systemd services, plus actual endpoint/game probes. Tailnet peer “online” alone does not prove subnet-route reachability.

Inspect `tailscale status`, approved routes/grants, `ip route get <private-ip>`, then router `sysctl net.ipv4.ip_forward`, `iptables-save`, destination security lists/NSGs and host rules. On Kubernetes, inspect node route acceptance, scoped pod MASQUERADE, CNI policies and DNS. For Wings, inspect `systemctl status docker wings`, `journalctl -u wings`, `findmnt /srv/pelican`, `blkid`, certificate SAN/expiry, Panel FQDN, callback proxy and websocket errors. A 401/403 from Wings can prove verified TLS reachability but not correct Panel enrollment.

For RDP, verify Windows RUNNING, subnet route TCP/3389, NLA, TermService, router-scoped Windows Firewall rule and private NSG. Do not add public RDP to debug. For games, confirm listening allocation, private bind IP, external public IP, OCI protocol/port, DOCKER-USER rules, native image architecture and an actual external client connection.

Reconcile Usage API cost daily against the credit Console, account for reporting lag and trial expiration, and use `estimate-cost.sh` for allocation changes. Budgets alert monthly actual spend at €200/225/240, not remaining credit or lifetime consumption. A scheduled daily credit/lifecycle probe and actual alert delivery remain pending credentials/approval. Follow the validation checklist before marking monitoring accepted.

## Access recovery and teardown

If Thor fails, use OCI serial console/recovery access (requires an authorized console key and IAM) to repair its Tailscale/service/network settings while preserving disks and public rules. Private SSH was verified before public SSH ingress was removed; Thor retains its direct tailnet SSH listener. Console boot logs were captured, but interactive serial-console recovery has not been exercised. After lockdown, do not reopen world-wide SSH/RDP; use approved console recovery. As an optional failover, run the same router role on an existing paid Wings node, approve the same subnets, tag it, and add its private /32 to all OCI/host access rules. Before switching the callback proxy, update `callback-firewall.yaml` to admit the replacement router's discovered Tailscale `/32` on `tailscale0` alongside Thor's, then rerun it on **both** k3s hosts. The OCI private `/32` and the Tailscale `/32` are distinct sources. Verify authenticated callbacks through the replacement and confirm unrelated paths stay blocked before retiring Thor's source rule. The replacement must receive `tag:oci-router` and its scoped pos:8443 grant. Use matching split DNS/callback proxy failover; do not advertise a second router without testing SNAT sources and route selection. No extra paid router is required.

Restore state from the versioned state bucket only with no active writer and after inspecting lineage/serial. Do not force-push state or delete lock objects to bypass another operation. `terraform destroy` is intentionally blocked by retention protections. Safe teardown needs an explicit OCID-level approval: stop games, export consistent data, verify restores, migrate tailnet access first, stop Windows, then review per-resource destruction. Retain Thor, its disk, shared networking and state/backup buckets unless expressly included in the approved plan. Untracked/orphaned volumes and imported-image objects can continue billing; state removal alone does not stop charges.


### Prepared-image recovery

Retain the existing private sanitized source/image artifacts until replacement guest access and backups are verified. If rebuilding a source clone, use the pinned signed VirtIO driver tooling under `oci/windows/`; preserve Secure Boot and TPM and leave the original MPMB VM unchanged. The native OCI image-import scripts are retained artifact/recovery tools, not prerequisites for nested guests. Rotate any temporary bootstrap credential from a prepared image after first boot.

## Dedicated callback listener

Thor now reaches only pos:8443 over the tailnet. The dedicated Traefik listener
routes only `pelican.home.internal/api/remote/…`; Panel continues validating
node tokens. Shared pos:443, UI/admin paths, other hostnames and the alternate
NodePort are unavailable to Thor. See [callback security](callback-security.md)
for the source/destination matrix, persistent host firewall, staging/recovery
sequence and access-check procedure.

## Resize a paid Wings node and retire an empty node

1. List Panel servers, game containers and data directories on the candidate node. Stop if any workload or unreviewed data remains. Do not infer that a node is empty from Panel alone.
2. Check regional image/shape compatibility, available capacity, quota and `docs/costs.md`. Update the desired per-node allocation in `oci/terraform/main.tf`; stable map keys preserve existing resource identities.
3. Back up Panel and all affected games with `capture-backup.py`, verify the encrypted archive and use `backup.sh` to store it off-node. Obtain approval for graceful game downtime, the reviewed Terraform changes and the exact storage deletions. Do not force-stop a saving game.
4. Put the resized node in maintenance mode, gracefully stop running games through Panel, and shut down its guest. Apply only the reviewed current plan. An E6 shape update can restart the instance. A volume expansion cannot be reversed by shrinking it.
5. After OCI finishes and the guest returns, run `render-inventory.py`. Review the private inventory; keep `wings_initialize_empty_volume: false`. Run `ansible-playbook site.yaml --limit wings-01 -e wings_expand_filesystem=true` from `oci/ansible/`. The role rescans the stable device, verifies expected whole-disk ext4 capacity and grows the existing filesystem. It preserves the UUID and never formats an existing filesystem. Confirm `lsblk`, `findmnt`, `df -h /srv/pelican`, `nproc` and `free -h` before starting games.
6. From the repository root run `python3 oci/scripts/configure-panel.py --admin-email YOUR_ADMIN_EMAIL` to reconcile active node capacity. This updates node-level RAM/disk/CPU capacity; it does not change existing game-server resource limits. Review each game's limits separately. Restart previously running games and verify their console and public connection.
7. Delete the retired Panel node only after it has no servers. Remove its DNS/monitoring targets and private Ansible inventory entry; sync the reviewed manifests and run `dns.yaml`. Retain its TLS material until recovery is no longer needed.
8. Terraform preserves boot disks on termination. Review the detached boot-volume OCID and dependencies before separately approving its deletion. Existing backup objects are not implicitly deleted. Restore `prevent_destroy = true` for paid instances and data volumes immediately after the approved retirement is complete, then verify the remaining configuration has no changes.

If resizing fails, keep the old node/data intact and inspect OCI's work request before retrying. Return the VM's compute allocation to its previous values if required; never attempt to shrink the expanded disk. Restore game data only from a verified backup and only onto an explicitly selected destination.
