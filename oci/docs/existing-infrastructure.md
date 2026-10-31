# OCI resource inventory

Use this resource map when importing, rebuilding or planning removal. Refresh
live details before changing resources. Load the OCI profile and set
`OCI_TENANCY_OCID` from the table below first; generated inventory is private:

```bash
oci/scripts/inventory.sh
terraform -chdir=oci/terraform output -json wings_instances
terraform -chdir=oci/terraform output -json network
terraform -chdir=oci/terraform output -json data_volumes
terraform -chdir=oci/terraform state list
```

## Tenancy and permissions

| Setting | Value |
|---|---|
| Tenancy | afbinaskar |
| Tenancy OCID | `ocid1.tenancy.oc1..aaaaaaaajtikdhgav7o7uksgc56xmuuvhx56pdunebmt4qlpzlltrkvxvbea` |
| Home/subscribed region | me-riyadh-1 |
| Availability domain | jRPH:ME-RIYADH-1-AD-1 |
| Compartment | Ymir: `ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq` |
| Object namespace | axh0rk0bydbu |

The configured API user belongs to the Default-domain Administrators group;
the root Tenant Admin Policy grants that group management of tenancy
resources. Use narrower bucket/operator policies where described in the
README. Keep API keys, identity-domain responses and billing records private.
Check current quota/image compatibility with `oci/scripts/preflight.py`
(`--help` lists the required compartment, AD and Ubuntu image inputs).
Quota headroom does not reserve capacity. Recheck Always Free entitlements,
prices and promotional expiry using the [cost procedure](costs.md).

## Retained resources

Thor is logical wings-04. Preserve its A1 4 OCPU/24 GB allocation, Ubuntu
26.04 ARM64 installation and 100 GB boot volume at 10 VPUs. Its game data is
`/var/lib/pelican/volumes` on that retained root volume. Do not resize,
reimage, format or relocate it as part of paid-node provisioning.

- Instance: `ocid1.instance.oc1.me-riyadh-1.anqwuljrcxr7q4yceguaprmui5mfmmyk3t3sznfxlinck3p2bcz3y6krpgaq`.
- Boot volume: `ocid1.bootvolume.oc1.me-riyadh-1.abqwuljruatmalgpfpro2ov5firdjn53exqjn6mv2e4z2gakty5gkbjdvbpa`.
- Private/public/tailnet addresses: 10.10.50.10 / 84.13.136.92 / 100.89.233.80.
- Ubuntu account/key: `ubuntu`, Bitwarden-backed SSH identity selected with
  `select-ssh-agent-key.py`. Preserve authorized keys, network configuration
  and `/var/lib/tailscale` when recovering the guest.
- SSH listens on the private and tailnet addresses; subnet-router SNAT and
  tag `tag:oci-router` support private administration and Panel callbacks.

| Shared resource | Address / purpose | Ownership |
|---|---|---|
| Jotunheim VCN | 10.10.0.0/16 | Retain/import |
| Public subnet-Jotunheim | 10.10.50.0/24; Wings/router | Retain/import |
| Private subnet-Jotunheim | 10.10.10.0/24; Windows | Retain/import |
| Internet gateway | Public default route | Retain/import |
| NAT gateway | Private default route; 84.13.133.208 | Retain/import |
| Service gateway | Regional Oracle services | Retain/import |
| Two route tables/security lists | Public/private subnet dependencies | Retain/import |

Exact retained identifiers and official import blocks are in
`oci/terraform/imports.tf`. Imported preservation freezes deliberately retain
existing settings; inspect them before expecting ordinary drift correction.
Security-list SSH sources are scoped to the router private /32. NSGs are
additive: they cannot revoke a broad security-list allow. Preserve the
shared gateways, routes, DHCP defaults and Thor VNIC/storage dependencies.

## Managed resources and data

| Resource | Allocation / data | Recovery source |
|---|---|---|
| wings-01 | E6 4 OCPUs/32 GB, Ubuntu 26.04 amd64, 50 GB boot + 400 GB balanced data | Terraform + Wings role; retain data disk |
| wings-02 | E6 2 OCPUs/16 GB, Ubuntu 26.04 amd64, 50 GB boot + 200 GB balanced data | Terraform + Wings role; retain data disk |
| Paid Wings data | ext4 UUID mounts at `/srv/pelican`; games under `volumes/` | Selected encrypted backups |
| State bucket | Private Standard `homelab-tfstate`, versioned | Bootstrap prerequisite outside this root |
| Image-source bucket | Private `homelab-win11-images` | Terraform bucket; import tooling owns source objects/images |
| Backup bucket | Private `homelab-pelican-backups` | Terraform + capture/upload procedures |
| Wings/router/Windows NSGs | Public game pool; private administration/callbacks | Terraform |
| Budget | Native EUR monthly actual-spend alerts | Terraform; alerts do not cap spending |
| Windows image | Windows/Windows11, 81,920 MB, prepared from a sanitized 80 GiB clone | Import/configuration scripts |
| Windows VM | Required E4 2 OCPUs/16 GB/100 GB | Launch only after technical verification and approval |

Windows source/custom-image artifacts remain billable independently of an
instance. Preserve the MPMB reference VM; prepare/generalize only a separate
clone. Keep Secure Boot/TPM requirements and the Terraform compatibility gate
intact; use the [Windows procedure](operations.md#windows-lifecycle).

## Homelab dependencies

- pos: AlmaLinux, LAN 192.168.1.28, tailnet 100.114.113.82; k3s control-plane/
  agent and rootless AdGuard Quadlet. Use [DNS operations](../../docs/dns-adguardhome.md).
- optiplex: Alpine, LAN 192.168.1.27, tailnet 100.77.7.115; k3s agent, use doas.
- Pod CIDRs: 10.42.0.0/24 and 10.42.1.0/24; services: 10.43.0.0/16.
- Panel: Traefik/cert-manager with the existing homelab CA, SOPS APP_KEY and
  local-path PVC on optiplex. Preserve SQLite, APP_KEY and storage together;
  the Panel PV uses Retain. Local-path storage is not replicated.
- Both hosts accept the OCI routes with scoped pod SNAT. Advertise only
  10.10.50.0/24 and 10.10.10.0/24 from the router. Check overlap before adding
  another remote site. See [callback routing](callback-security.md).
- The public game pool is TCP/UDP 25565–25765 per Wings node. Administrative
  SSH/RDP/API/SFTP/metrics paths stay private.

## Removal decisions

Retain Thor, its boot/data/access dependencies and shared Jotunheim networking.
The obsolete Utgard-Loki instance and 50 GB boot volume were terminated before
this environment's discovery; they are not live cleanup targets. There is no
authorized live deletion set. Refresh attachments/reverse dependencies, verify
backups and replacement access, and obtain an OCID-specific deletion approval
before cleanup. Removing Terraform state alone does not remove billing.
