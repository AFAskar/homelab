# OCI game nodes and nested Windows lab

Manage three Ubuntu 26.04 LTS hosts with one Terraform root at `oci/terraform/`:

| Host | Shape / architecture | OCPUs / RAM | Boot / data |
|---|---|---|---|
| wings-01 | E6.Flex / amd64 | 4 / 32 GB | 50 / 400 GB |
| wings-02 | E6.Flex / amd64 | 2 / 34 GB | 50 / 200 GB |
| wings-04 / Thor | Existing A1 / arm64 | 4 / 24 GB | Existing 100 GB |

Pelican Panel runs in the existing homelab Kubernetes cluster. All hosts run Wings continuously. Wings-02 also runs KVM/libvirt for on-demand Windows guests; no fourth OCI instance is needed. Windows disks, firmware variables, TPM state and saved RAM live under `/srv/pelican/lab` on the existing data volume. A guest start/save never stops or reboots the Linux host.

The native OCI Windows-image workflow is not needed for nested guests. Existing imported-image/source objects remain private and retained; do not delete them without reviewing recovery needs and obtaining cleanup approval. The original MPMB VM is preserved.

## Terraform and preservation

1. Configure an OCI CLI/API-key profile and install the pinned Terraform/provider versions from `terraform/versions.tf`. Inspect the tenancy with `scripts/inventory.sh` before changing retained resources.
2. Copy `terraform/terraform.tfvars.example` only when a private variable file does not already exist. Reconcile discovered OCIDs, SSH public key, recipients and EUR billing currency. Never put private keys, OAuth secrets or Windows passwords in Terraform variables/user-data.
3. Follow [migration](docs/migration.md) for the existing private versioned backend, imports, state access and the Always Free preservation checks. Import shared resources before updating them; reject unintended replacement. Keep backend configuration, state, plans and raw inventory private.
4. Load the existing Tailscale OAuth credential by file reference and validate the complete root:

```bash
export TAILSCALE_OAUTH_CLIENT_ID=file:$PWD/oci/ansible/secrets/tailscale-client-id
export TAILSCALE_OAUTH_CLIENT_SECRET=file:$PWD/oci/ansible/secrets/tailscale-client-secret
terraform -chdir=oci/terraform init -lockfile=readonly
terraform -chdir=oci/terraform fmt -check
terraform -chdir=oci/terraform validate
umask 077
terraform -chdir=oci/terraform plan -out=../inventory/review.tfplan
```

Review actual actions, pricing and access dependencies before an approved apply. Never merge or delete unrelated resources as an implicit deployment step. Preserve Thor's shape, storage and working access.

## Configure hosts and Panel

Run Ansible from `oci/ansible/` with the existing collection requirements and private `inventory.yaml`. `python3 oci/scripts/render-inventory.py` refreshes operator inventory and monitoring targets from Terraform outputs; review before deployment.

- `bootstrap-router.yaml` and `homelab-routes.yaml` establish the private subnet-router/pod path. Approve only required routes; retain the last working administrative listener until private access is tested.
- `dns.yaml` imports the [rootless AdGuard Quadlet deployment](../docs/dns-adguardhome.md).
- `callback-firewall.yaml` and `tailscale/panel-proxy.yaml` isolate cloud callbacks from shared homelab web services. Follow [callback security](docs/callback-security.md) in order.
- Sync the existing Argo applications manually. Panel uses `kubernetes/pelican/manifests`, the existing homelab CA and encrypted secrets. Run `python3 oci/scripts/export-node-certificates.py` and `python3 oci/scripts/configure-panel.py --initialize --admin-email YOUR_ADMIN_EMAIL` from the repository root. Existing users, passwords and node tokens are preserved.
- Run `ansible-playbook site.yaml` for Wings and the router. Never authorize filesystem initialization on an existing volume.
- Run `ansible-playbook lab.yaml` to configure nested KVM on wings-02. This reuses the existing data mount and adds only bridge-scoped firewall chains alongside Docker/Wings.

Panel budgets on wings-02 reserve 4 GiB for the host and 16 GiB for a Windows guest, leaving 14 GiB for Wings. It reserves 120 GiB of the existing data volume for guest disks/checkpoints, leaving a 60 GiB Wings allocation budget. These are allocation budgets, not separate partitions; use real per-server limits and monitor free space. CPU is shared. The import/start tools reject insufficient space/RAM and never stop game servers to make room.

## Send and run a Windows guest

Create bundles only in an ignored private directory. A plain QCOW2 is a cold-boot disk; preserving a desktop/RAM session requires its matching domain, disk, firmware/NVRAM, TPM state and compatible CPU/QEMU machine type.

```bash
mkdir -p oci/windows/work/bundles
# An existing libvirt guest must already be shut off:
python3 oci/windows/guest-bundle.py export mpmb-windows11 oci/windows/work/bundles/mpmb
# Or explicitly suspend/save it for transfer, leaving the source off:
python3 oci/windows/guest-bundle.py export mpmb-windows11 oci/windows/work/bundles/mpmb-saved --save
# For a prepared, offline QCOW2 without a saved session:
python3 oci/windows/guest-bundle.py image /private/windows.qcow2 oci/windows/work/bundles/new-win --name win11-lab

oci/scripts/send-guest.sh oci/windows/work/bundles/mpmb
oci/scripts/start-windows.sh mpmb-windows11
oci/scripts/status-windows.sh mpmb-windows11
oci/scripts/stop-windows.sh mpmb-windows11
```

Connect through Tailscale to the private address from `terraform output -json lab_host`, TCP/3389. Only one nested guest runs at a time behind this endpoint. Keep Secure Boot and TPM 2.0 enabled. Configure guest RDP/NLA and its firewall to permit the nested gateway `192.168.124.1`; retrieve credentials from your password manager, not Git. `windows/first-boot.ps1` can configure that scope from an elevated guest console with `-RouterPrivateIPs 192.168.124.1` and a securely supplied password.

If an export fails after `--save`, keep the recovery file and resume the original with `virsh -c qemu:///session restore /private/bundle/state.save`; its original disk paths remain embedded in that checkpoint. Never delete the only saved RAM copy to resolve an export error.

RAM restore is conditional on compatibility. The tools fail rather than discarding the checkpoint or silently cold-booting. Source MPMB currently uses host-passthrough CPU; a common CPU profile is preferable for repeatable transfers, and a guest cold boot can be needed to establish it. No OCI image import, host reboot or new OCI VM is required for each guest. An exported saved session must remain paired with its captured disks; resuming the source and later reusing the RAM file with modified disks is unsafe.

Stopping Windows saves its RAM while the shared host/Wings stay running; it does not reduce OCI compute charges. Use the [operations guide](docs/operations.md), [acceptance checks](docs/validation.md), [architecture](docs/architecture.md), [inventory](docs/existing-infrastructure.md) and [cost model](docs/costs.md) for access, recovery, backups and spending.
