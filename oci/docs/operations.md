# Operations and recovery

These are procedures to run after prerequisites/approval; they are not evidence of deployment. Use the same root, OCI profile/region and private DNS for all operations.

## Private administration and DNS

Thor's key is available through Bitwarden; run `python3 oci/scripts/select-ssh-agent-key.py`. Bootstrap with explicit `IdentityAgent` and the selected public key at `ubuntu@100.89.233.80`. The private key stays in Bitwarden. Thor currently binds SSH only on that tailnet IP. Use the reviewed `bootstrap-router.yaml` to add 10.10.50.10 alongside it; use `ssh ubuntu@10.10.50.10` only after listener and route verification. Other Linux private IPs and Windows IP come from `terraform output`. Administrators accept the approved OCI routes (`tailscale set --accept-routes=true` on Linux). Only the router runs Tailscale; Wings peers and Windows do not.

The proposed actual policy is `ansible/tailscale/policy.hujson`, using Tailscale's current grants syntax. The user reports the existing policy is allow-all and requested a restrictive replacement. The file uses observed IPv4 identities with no placeholders or catch-all grant:

| Source | Destination | Permitted traffic |
|---|---|---|
| azoz-laptop + freyr | pos, optiplex, Thor/router | OpenSSH TCP/22 |
| azoz-laptop | freyr | SSH TCP/22 and RDP TCP/3389 |
| Both admin clients | pos/optiplex tailnet and known LAN addresses | HTTP/HTTPS TCP/80,443 |
| Both admin clients | pos tailnet/known LAN address | Kubernetes API 6443, AdGuard UI 3000, DNS TCP/UDP 5353 |
| Both admin clients | 10.10.50.0/24 Wings subnet | SSH 22, Wings API 8080, SFTP 2022, metrics 9100 |
| Both admin clients | 10.10.10.0/24 Windows subnet | TCP/3389 only |
| pos + optiplex | Wings subnet and router tailnet address/tag | TCP/8080,9100 only |
| Thor/router tag | pos tailnet address | TCP/8443, authenticated Panel daemon API only |
| Other tailnet devices | Infrastructure | No grant; default denied |

`azoz-laptop` (100.66.202.74) and `freyr` (100.82.125.5) are the proposed trusted admin clients. The verified tailnet owner account can assign `tag:oci-router`, but owning a device does not automatically grant it network administration access. Other members' devices, the owner's phone and the old home-router device are denied administrative/application access unless a later explicit rule is reviewed. Tailnet members retain TCP/UDP 53 to pos for the existing `home.internal` split-DNS resolver; pos redirects that traffic to AdGuard on 5353. This DNS-only exception does not grant server administration. Align the router's `router_tailnet_admin_sources` with these two admin IPs. Review this trust choice before applying.

This is an IPv4 management policy; native IPv6 and ICMP are not granted. Use the documented IPv4 private/tailnet addresses for connection checks; routing health probes use TCP rather than ping. Known homelab LAN /32 rules only authorize traffic: they do not create a home subnet route or revive the offline home router. Public game clients use public OCI game addresses and are outside these tailnet grants. Kubernetes node-to-node LAN/CNI traffic is not altered by a tailnet policy.

Before saving, back up the current policy, preserve any unrelated DNS/nodeAttrs/settings, and **remove the old allow-all ACL/grants**. Adding this policy's scoped grants alongside allow-all does not restrict anything because grants are additive. The explicit empty `acls` and `ssh` sections remove legacy blanket network/Tailscale-SSH rules; normal OpenSSH still uses the TCP/22 grants and existing SSH keys. Validate the complete candidate with the `tailscale_acl.tailnet` Terraform plan and require its embedded `tests` to pass, including denied ordinary users and denied server-to-admin SSH. Local JSON/selector checks do not replace that control-plane validation. The policy is managed from the existing OCI Terraform root; bootstrap the scoped OAuth credential as described in the README and keep routine policy changes in Git. Do not save the browser preview to bypass Terraform. Probe addresses ending in .20 in the tests exercise subnet rules; they are not invented VM assignments.

### Policy writer and recovery procedure

The [pinned provider's Update implementation](https://github.com/tailscale/terraform-provider-tailscale/blob/v0.29.3/tailscale/resource_acl.go#L122) replaces the whole policy without an ETag. `overwrite_existing_content=false` only guards creation; Terraform state locking cannot serialize console edits. Enforce a single operator/writer: no concurrent console, CLI, CI or second-root policy writes, and no unattended apply. Keep the authenticated admin-console recovery path available while testing.

Before any emergency console recovery edit, stop/cancel pending policy applies and suspend further Terraform writes. Invalidate **all** saved plans containing the tailnet policy, including full infrastructure plans, and mark the incident time. Preserve a private copy of the live policy for recovery; restore only the access required. Never resume a pre-incident plan. Reconcile the recovered live policy into `policy.hujson`, retain and rerun its access tests, and obtain a fresh Terraform plan with refresh enabled. Review its complete policy diff and approval again, then apply promptly with exclusive writer ownership. If another edit occurs during review or apply, stop and regenerate; do not overwrite the newer recovery policy. This procedure is the concurrency protection for this provider version, not an automatic ETag guarantee.

No autoApprovers are included. After the reviewed router bootstrap advertises them, approve **only** `10.10.50.0/24` and `10.10.10.0/24` on Thor in Machines → Subnets → Edit. Route approval and access grants are separate. Manage device expiry and persist tailscaled. Use a tagged scoped one-use authentication key only if enrollment is necessary; the existing authenticated Thor should not need one. Standard subnet-router SNAT means OCI targets see router source 10.10.50.10/32; no return route to the tailnet is required. No default/exit-node route is granted. The reviewed policy is applied live; Thor advertises both approved routes.


`render-inventory.py` refreshes the desired monitoring EndpointSlice from Terraform outputs. The complete [AdGuard deployment](../../docs/dns-adguardhome.md) derives the exact Wings DNS rules from that tracked desired configuration. Run `ansible-playbook dns.yaml` from `oci/ansible/`; it imports the single authoritative deployment for encrypted settings, Compose, boot and firewall configuration. There is no separate live-config patcher. CoreDNS continues forwarding this zone to pos:5353. The existing `home.internal` catch-all rules exclude `oci.home.internal`, so each Wings name returns only its private address. Test pod and browser resolution after an address change.

Use `./remotepod.sh` for Compose operations. The named connection `pos` retains its existing SSH identity. The deployment supplies address variables, and Compose also has the current explicit defaults.

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

The four private node names use HTTPS 8080 and SFTP 2022. Paid nodes reserve RAM/disk headroom with Panel limits of 14 GiB / 180 GiB; Thor uses 20 GiB / 80 GiB of its existing capacity. Paid game data is `/srv/pelican/volumes`; Thor uses `/var/lib/pelican/volumes`. Root CA trust, per-node certificates and non-overlapping Docker networks remain prerequisites. Config export uses `/etc/pelican/tls/` and the private Panel URL. No enrollment token is committed.

The approved public game pool is **25565–25765 inclusive**, TCP and UDP, on every Wings node: 201 port numbers per node. `configure-panel.py` idempotently reserves that pool using each node's actual private VNIC IP, preserving occupied allocations. The existing acceptance game uses 25565; the other 200 allocations per node start free. OCI public IP is external NAT, not the Linux bind address. Store mappings from Panel allocation to public endpoint; ephemeral paid public IPs may change on replacement. For a new game inside this pool, select free primary/additional allocations in Panel, choose a compatible egg/runtime and resource limits, then install/start it. No further OCI or host-firewall change is needed for ports within the pool. Games needing ports outside it require a reviewed Terraform/Ansible update. The pool is shared on all four nodes; do not use its public ports for RCON or other administrative listeners. Port numbers may be reused on different nodes, but two servers cannot own the same node/IP/port allocation. SSH/RDP/API/exporter/SFTP stay private. Verify public games using an external client independent of the tailnet. Check native ARM manifest/egg for Thor; x86-only games belong on paid AMD nodes.

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

The save command above is Mindustry-specific; use the selected game's supported command or omit it when graceful shutdown saves the game. Outputs and temporary plaintext use private permissions; plaintext staging is removed after encryption to the existing repository recovery recipient. Keep the recovery identity separately. Upload uses the Terraform-managed private bucket and attaches SHA256 metadata as well as printing a local checksum. The deployed operator can upload/restore with existing credentials. Use bucket-scoped writer/reader roles for any future automation; never install tenancy-wide credentials on Wings.

Retention target: 14 daily selected backups, with a weekly size check to stay near 50 GB average. No recurring capture scheduler or automatic deletion/locked retention is installed. Schedule on an approved existing operator host if wanted; the capture requires its SSH agent and Kubernetes access. Growing data changes cost, and object deletion requires approval. Persist archive checksums outside the bucket. Selected game data, not every disk, is protected by this procedure.

Restore into a **new empty staging directory**: download the named object with `oci os object get`; compare its SHA256 to both the local record and `opc-meta-sha256` from `oci os object head`; age-decrypt and extract the outer archive; verify every member against `manifest.json`. Extract `panel.tar.gz` into another fresh directory, run SQLite `PRAGMA integrity_check`, and recover the effective APP_KEY with that database and application storage. Extract each selected game archive separately and check saved worlds/binaries. For an actual recovery, stop the affected server/Panel first, review destination ownership and only then restore files and the Secret together. Never overwrite live data merely to test recovery.

The deployed acceptance backup was uploaded, downloaded and restored into disposable directories: encrypted hash and inner checksums matched, SQLite integrity was `ok`, APP_KEY matched, and all four saved Mindustry worlds plus pinned binaries verified. Games resumed after capture. This tests archive recovery, not a complete Kubernetes-host-loss recovery or a full boot-volume restore. Generated run reports remain private under `oci/inventory/reports/`.

Paid game data survives reboot through an ext4 UUID mount. Wings RequiresMountsFor prevents accidental use of an unmounted boot directory. Compute/volume prevent_destroy guards against accidental Terraform destruction; preservation imports do not relocate existing Thor data. Rebuilding a paid node requires a reviewed instance-only replacement while preserving data/boot disks, then reattachment and UUID remount; do not remove protection or recreate disks blindly. Reuse discovered filesystems and never format an existing disk. Full disaster recreation requires network import/state recovery first and a confirmed Windows image workflow; imported freeze rules must be reconciled before claiming a complete greenfield recreation.

## Windows lifecycle

No Windows instance exists in OCI. The local 80 GiB MPMB checkpoint clone has been sanitized, generalized and captured; its digest and local validation evidence are in `oci/inventory/reports/windows-image-validation.json`. The original MPMB disk, firmware and TPM are retained. `import-image.sh` requires explicit image/storage approval and `OCI_APPROVED_IMAGE_SHA256` matching that reviewed final disk; a changed disk is rejected before OCI calls. Keep the requested 100 GB boot allocation and verify imported-image metadata rather than assuming the generic guide's 256 GB value applies.

`first-boot.ps1` configures the isolated build clone's Windows 11/TPM/Secure Boot, NLA and router-scoped RDP firewall. Generalization creates the persistent `winlab` administrator through the protected answer file, since Sysprep disables the built-in Administrator. Keep its bootstrap credential in the password manager, rotate it after deployment, and never rely on OCI Windows Server password retrieval for this custom Windows 11 image. Only the prepared private image contains the temporary credential; no password is committed or passed to Terraform. Restrict image/bucket access and remove cached answer files during SetupComplete.

```bash
oci/scripts/status-windows.sh
OCI_APPROVE_BILLABLE_START=yes oci/scripts/start-windows.sh # only after explicit approval
oci/scripts/stop-windows.sh # graceful SOFTSTOP, never terminate/reset
```

These read the exact identity/profile/region from Terraform outputs, not display-name search. Terraform deliberately omits instance `state` so stops are not undone by a later apply. Use RDP to the **private** Windows IP. Verify interactive login and NLA before accepting deployment, test start/stop/status, then leave STOPPED. The 100 GB boot disk, source upload and custom image keep accruing storage charges while stopped. SOFTSTOP waits for guest shutdown and never falls back to a forced stop. Rebuild/wiping requires explicit approval, a reviewed volume/image plan, and password rotation; “stop” does not wipe data.

## Monitoring and troubleshooting

Existing Prometheus is reused. Ansible enables node-exporter systemd metrics for Wings/Docker/tailscaled/Caddy and bounded journald logs (200 MB/14 days). The monitoring manifests provide the private exporter ServiceMonitor, public-game TCP Probe and alerts. The small blackbox exporter runs in the existing cluster; no paid monitoring VM is added. Run `render-inventory.py` after approved OCI changes, review its EndpointSlice and Probe target updates, then commit/sync those desired monitoring manifests. They are GitOps deployment inputs consumed by Prometheus; transient query results and validation reports stay in the ignored inventory. The deployed targets currently cover four private exporters, four Wings services and four public game allocations, all observed healthy. TCP monitoring does not replace the application-level UDP checks in `check-games.py`. `healthcheck.py` checks actual private TCP routes and certificate-verified Wings API responses; it does not register nodes or prove game availability. Run it from the administrator and repeat equivalent tests inside Panel pods on **both** k3s nodes. Monitor disk space, load/memory and systemd services, plus actual endpoint/game probes. Tailnet peer “online” alone does not prove subnet-route reachability.

Inspect `tailscale status`, approved routes/grants, `ip route get <private-ip>`, then router `sysctl net.ipv4.ip_forward`, `iptables-save`, destination security lists/NSGs and host rules. On Kubernetes, inspect node route acceptance, scoped pod MASQUERADE, CNI policies and DNS. For Wings, inspect `systemctl status docker wings`, `journalctl -u wings`, `findmnt /srv/pelican`, `blkid`, certificate SAN/expiry, Panel FQDN, callback proxy and websocket errors. A 401/403 from Wings can prove verified TLS reachability but not correct Panel enrollment.

For RDP, verify Windows RUNNING, subnet route TCP/3389, NLA, TermService, router-scoped Windows Firewall rule and private NSG. Do not add public RDP to debug. For games, confirm listening allocation, private bind IP, external public IP, OCI protocol/port, DOCKER-USER rules, native image architecture and an actual external client connection.

Reconcile Usage API cost daily against the credit Console, account for reporting lag and trial expiration, and use `estimate-cost.sh` for allocation changes. Budgets alert monthly actual spend at €200/225/240, not remaining credit or lifetime consumption. A scheduled daily credit/lifecycle probe and actual alert delivery remain pending credentials/approval. Follow the validation checklist before marking monitoring accepted.

## Access recovery and teardown

If Thor fails, use OCI serial console/recovery access (requires an authorized console key and IAM) to repair its Tailscale/service/network settings while preserving disks and public rules. Private SSH was verified before public SSH ingress was removed; Thor retains its direct tailnet SSH listener. Console boot logs were captured, but interactive serial-console recovery has not been exercised. After lockdown, do not reopen world-wide SSH/RDP; use approved console recovery. As an optional failover, run the same router role on an existing paid Wings node, approve the same subnets, tag it, and add its private /32 to all OCI/host access rules. Before switching the callback proxy, update `callback-firewall.yaml` to admit the replacement router's discovered Tailscale `/32` on `tailscale0` alongside Thor's, then rerun it on **both** k3s hosts. The OCI private `/32` and the Tailscale `/32` are distinct sources. Verify authenticated callbacks through the replacement and confirm unrelated paths stay blocked before retiring Thor's source rule. The replacement must receive `tag:oci-router` and its scoped pos:8443 grant. Use matching split DNS/callback proxy failover; do not advertise a second router without testing SNAT sources and route selection. No extra paid router is required.

Restore state from the versioned state bucket only with no active writer and after inspecting lineage/serial. Do not force-push state or delete lock objects to bypass another operation. `terraform destroy` is intentionally blocked by retention protections. Safe teardown needs an explicit OCID-level approval: stop games, export consistent data, verify restores, migrate tailnet access first, stop Windows, then review per-resource destruction. Retain Thor, its disk, shared networking and state/backup buckets unless expressly included in the approved plan. Untracked/orphaned volumes and imported-image objects can continue billing; state removal alone does not stop charges.


### Windows clone driver preparation

The retained offline checkpoint uses old VirtIO 100.74.104.14100 packages. On the isolated clone, its storage driver failed Windows signature verification (Device Manager Code 52), causing `INACCESSIBLE_BOOT_DEVICE` when selected for boot. Do not disable Secure Boot or signature enforcement.

Download upstream stable [VirtIO-Win 0.1.302-1](https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/archive-virtio/virtio-win-0.1.302-1/virtio-win-gt-x64.msi) locally. Run `windows/extract-virtio.sh downloaded.msi new-driver-directory`; it checks the pinned SHA256 and requires host `7z`. Copy that directory to the isolated clone while it still boots from SATA. Run `windows/install-virtio.ps1 -DriverDirectory C:\path\to\drivers` from an elevated PowerShell session whose execution policy permits your reviewed local script. It validates the three driver catalogs and uses PnP installation, preserving Windows signature checks. Attach a disposable empty VirtIO test disk, confirm storage devices report OK, shut down, then change only the clone's boot disk/NIC to VirtIO. Remove the test disk and confirm an independent boot. The source MPMB VM is never generalized, sanitized or changed by these scripts.

Local validation confirms Windows 11 Pro build 26200, TPM ready/enabled, Secure Boot true and working VirtIO storage/network with SSH over an isolated host port. This does not establish OCI boot/RDP compatibility. The final generalized capture remains private. Local verification does not authorize an OCI upload/import.


### Windows clone generalization and capture

These destructive guest steps apply **only to the disposable checkpoint clone**. Keep the source checkpoint, XML, NVRAM and TPM intact. Run `clone-checkpoint.py` first; never point the preparation scripts at the source VM. Install the signed drivers above, configure RDP with `first-boot.ps1`, then disable the copied source account's automatic login and reboot the clone. Log in as its built-in Administrator and verify the copied source profile is unloaded. Keep network isolation while building.

Copy `generalize-clone.ps1` and `unattend.xml.template` together into the clone. In elevated PowerShell, call the script with `-ExpectedCloneUUID`, the distinct `-SourceUUID`, `-SourceAccount` and `-LabPassword (Read-Host -AsSecureString)`. The UUID guard rejects the source. It removes the copied profile/fixtures and SSH keys, clears free clusters, removes installer bypass flags, writes a protected answer file with a `winlab` administrator, and runs Sysprep with shutdown. Check Panther logs for successful generalization. The English locale and explicit OOBE configuration allow unattended first boot without inheriting a source user.

On the host, convert the shut-down generalized clone into a new raw file (`qemu-img convert -O raw`), then use `7z` to extract its Windows NTFS partition to a private regular file. Run `wipe-ntfs-copy.sh` on that **extracted offline copy** to clear unused MFT records, directory/log/pagefile data and file tails; free-cluster clearing alone can retain deleted resident credentials. Run `assemble-sanitized-image.py original.raw sanitized-partition.ntfs new-sanitized.raw` to substitute exactly the matching GPT partition into a new disk, retaining EFI/recovery. It refuses an existing output and leaves inputs unchanged. Finally run `prepare-image.sh new-sanitized.raw new-import.qcow2`; record `qemu-img check`, size and SHA256. Use mode 0700 work directories and 0600 images/credentials; keep all intermediates outside Git. Avoid uploading earlier unsanitized captures.

Test a separate copy of the final capture with fresh Secure Boot NVRAM and TPM 2.0. Verify first boot and NLA authentication as `winlab`, including a wrong-password rejection. This local test uses a private isolated virtual network whose gateway matches router SNAT 10.10.50.10; it does not prove OCI or Tailscale reachability. Leave the upload capture unbooted. The private image retains a temporary bootstrap secret: rotate it at deployment and before reusing the image for another machine.


After an explicitly approved image import, `OCI_APPROVE_IMAGE_IMPORT=yes oci/windows/configure-image.sh "$IMAGE_OCID"` applies the [Windows 11-specific OCI image settings](https://docs.oracle.com/en-us/iaas/secure-desktops/windows-image.htm) and E4 compatibility entry. It requires `OCI_APPROVE_IMAGE_IMPORT=yes`, rejects another OS or an image larger than 100 GiB, and preserves other capability overrides. Review its output before setting the Terraform compatibility gate. Live image import and candidate capability API checks now pass; see oci/inventory/reports/windows-oci-import.json. Regular Compute support and actual secure E4 boot remain unverified. Keep the compatibility gate false until the documented support constraint in validation.md is resolved. Secure Boot, measured boot and TPM stay enabled in Terraform. Do not replace these checks with registry bypasses.


Terraform policy validation passed against the authenticated tailnet with all 13 test cases. An isolated diagnostic plan proposes importing the current policy and one update, with no adds/destroys or OCI changes. A deliberately forbidden `pos:2375` acceptance test was rejected by the API, confirming failed tests block planning; the valid candidate was restored. See `oci/inventory/reports/tailscale-plan-summary.json`. The restrictive live policy now uses the dedicated callback port and denies Thor shared HTTPS access. Native Tailscale SSH is disabled on pos, optiplex and Thor; private OpenSSH keys remain the administration path. If optiplex LAN SSH is unavailable, use its existing SSH alias with `-o HostName=100.77.7.115` to retain the configured identity.

The homelab inventory retains the existing `pos`/`optiplex` SSH aliases so their configured keys are used. Optiplex has a tailnet HostName override because its recorded LAN SSH address was unreachable during discovery. This Ansible project disables SSH multiplexing: the pos check failed with a reused connection and succeeded with ordinary SSH. Both homelab `hostname` checks passed without guest changes. Reconcile an existing private inventory with these connection settings before provisioning.

## Dedicated callback listener

Thor now reaches only pos:8443 over the tailnet. The dedicated Traefik listener
routes only `pelican.home.internal/api/remote/…`; Panel continues validating
node tokens. Shared pos:443, UI/admin paths, other hostnames and the alternate
NodePort are unavailable to Thor. See [callback security](callback-security.md)
for the source/destination matrix, persistent host firewall, staging/recovery
sequence and live verification evidence (local report: `oci/inventory/reports/callback-isolation-evidence.json`).
