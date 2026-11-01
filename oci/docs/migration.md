# Preservation and deployment sequence

Use this sequence for importing retained resources or recreating the environment.
Check `terraform -chdir=oci/terraform state list` before each stage so completed
imports or existing resources are not repeated. Refresh the [inventory](existing-infrastructure.md),
read the [cost model](costs.md), and use the [acceptance checklist](validation.md).
Keep state/plans private, retain a working access path, and obtain approval
before billable, destructive or irreversible operations.

## Bootstrap protected state

Create the dedicated private versioned `homelab-tfstate` bucket only after bootstrap approval. Use the existing tenancy namespace and Ymir compartment. Grant state operators only the required bucket-read, object read/write and lock-object operations, scoped to this state bucket; keep bucket creation and legacy image-artifact permissions separate. Do not create public access or a PAR for state.

Copy `terraform/backend.hcl.example` to ignored `terraform/backend.hcl` only if absent, reconcile bucket/namespace/home-region/profile and initialize the real root. Credentials stay in the OCI profile or environment. The backend's native lock must be respected; never delete another operation's lock or force-push state to bypass concurrency.

The private Windows image/source bucket is retained recovery storage. Nested KVM does not require a new OCI image import for each guest. Existing OCI image metadata is not proof of native Windows Compute support and is not used by the shared-host design.

## 1. Establish protected state and access

1. Use Thor's confirmed Ubuntu account with the Bitwarden agent and `select-ssh-agent-key.py`; the private key must stay in the agent. Preserve the existing Tailscale-only SSH listener and run the reviewed `bootstrap-router.yaml` through 100.89.233.80 to add the private listener before switching inventory to 10.10.50.10. Do not remove current keys or Tailscale connectivity. Record `lsblk -f`, `findmnt`, `du`, running containers/services, firewall rules, `/etc/fstab`, game/data directories and dependency owners. Do not print secrets. Securely back up important data before installing packages; obtain approval for any paid backup storage. Confirm Docker CE package conflicts before change.
2. Confirm IAM group/domain access, Object Storage namespace, actual credits, trial terms and free allowances. Bootstrap an approved private versioned state bucket with least-privilege access. Do not create a PAR for state. Initialize the single real root with `backend.hcl`; do not use local state for deployment.
3. Inspect the exact selected ARM64/amd64 package and Wings binary digests. Cloud-init does not rerun on imported Thor; all post-import provisioning uses Ansible. Never change its 4/24 shape or 100 GB boot disk to fit a guess about free allowances.

## 2. Import-only reconciliation

Official `import` blocks map Thor, its boot volume, Jotunheim VCN, both subnets, both route tables, both security lists, IGW, NAT and service gateway. Their real OCIDs are in `imports.tf`. Configurations freeze retained launch/network fields; existing attachments and DHCP remain in place and are referenced. Imported blocks are idempotent when already in state.

Plan just the retained graph to prepare a review. Exceptional resource targeting is justified for preservation-only review; it is not a full deployment plan. A diagnostic copy with a temporary local backend was used for read-only planning in this task because its required private state bucket did not yet exist; it is never used to deploy or maintain a second environment. Re-run after any configuration/discovery changes.

After approval and state initialization, the simplest state-only path is official CLI imports, one dependency at a time:

```bash
terraform -chdir=oci/terraform import oci_core_instance.wings_04 "$EXISTING_INSTANCE_OCID"
terraform -chdir=oci/terraform import oci_core_boot_volume.wings_04 "$EXISTING_BOOT_OCID"
# Repeat each exact address/OCID in imports.tf for the retained network graph.
# If real data volumes are discovered, fill retained_data_volumes and import them too.
terraform -chdir=oci/terraform plan -out=review.tfplan
terraform -chdir=oci/terraform show -json review.tfplan | python3 oci/scripts/check-plan.py
```

Do not apply the entire root just to import: it also contains paid creates. Stop on any replacement, deletion, disk-size/VPU/shape change, unexpected route/NSG change or data discrepancy. Retain imported snapshots and review `ignore_changes=all` before any future reconciliation; these preservation freezes deliberately do not promise ongoing drift correction. `prevent_destroy` remains on compute, volumes, bucket and retained network resources.

## 3. Establish subnet routing before lockdown

Before the first bootstrap, copy `oci/ansible/inventory.example.yaml` to ignored `inventory.yaml` if it does not already exist, select the Bitwarden public identity with `select-ssh-agent-key.py`, and review the `thor_bootstrap` inputs. Confirm `tag:oci-router` ownership, merge the required admin/node/callback grants, and verify recovery access before the role changes Thor's tags. Only after review/approval, set `enable_private_ssh_listener: true` for `thor-bootstrap` and run `ansible-playbook bootstrap-router.yaml` from `oci/ansible/`; both the copied and generated examples deliberately leave this flag false.

Configure Thor as router only after guest/data/resource checks. It already runs Tailscale; authenticate only if necessary using a short-lived scoped key provided through an environment lookup and a transient mode-0600 file. The role never logs the key. Advertise `10.10.50.0/24` and `10.10.10.0/24` with SNAT. Validate `ansible/tailscale/policy.hujson`, remove the existing allow-all network rules, and approve those routes in the existing tailnet; advertising alone does not authorize traffic. Review existing route conflicts and ownership first.

Enable route acceptance on administrators and existing Kubernetes hosts; apply scoped pod SNAT using `homelab-routes.yaml`. Test private SSH to Thor's **10.10.50.10**, including a fresh independent session and sudo, plus node and pod traffic. Only then set Terraform `private_access_verified=true` and Ansible `private_access_verified=true` / `apply_private_firewall=true`. The security-list plan must replace broad SSH sources with the router /32 and retain required ICMP/egress. Keep the existing SSH session open and OCI recovery access ready during transition. Any potentially access-cutting operation needs the user's approval after this concrete plan and verification.

Router host INPUT must allow explicit tailnet administrator sources for SSH, and pos/optiplex tailnet addresses for API/metrics. Update `router_tailnet_admin_sources`/service source entries to the reviewed policy. Add the generated Wings and callback NSGs to the router VNIC **additively** after reading its current NSG set; never overwrite unrelated NSGs. No automatic VNIC mutation is included because full guest/access reconciliation remains pending.

## 4. Review the shared-host allocation

Use the full Terraform root to review paid-node capacity, existing VNIC NSGs and the scoped tailnet policy. Wings-02 hosts nested KVM on the same Ubuntu release as Wings-01. It remains a continuously running Wings node; no native Windows OCI instance or extra disk is added. Review the 744-hour cost projection, host/guest reservations and private RDP path before an approved apply. Reject any unexpected replacement or deletion.

Before a compute resize, inventory the target's Panel servers, containers, mounts and data. Back up important data and arrange a graceful stop of any affected game. Resize in place, restart the Linux host if OCI requires it, then verify private access, unchanged data/UUIDs and services. Never resize Thor or format an existing filesystem to fit the design.

After the host is ready, run `render-inventory.py`, `configure-panel.py` and `ansible-playbook lab.yaml` in the documented directories. The role configures only the shared host's KVM services, guest storage subdirectory and bridge-scoped firewall. New guest imports/start/save do not reboot the host.

## 5. Guest setup and GitOps acceptance

Deploy Panel manually through the existing Argo application, finish the official installer and recover/backup its APP_KEY. Run `python3 oci/scripts/export-node-certificates.py` from the repository root after the included Certificates are Ready. Create the active node records and save their generated Wings configs in the private inventory secrets directory. Configure the router callback proxy and split DNS/CA trust, including its explicit proxy certificate/key inputs. Only then run Wings provisioning idempotently on all active private hosts with matching data paths and private TLS. Run node and pod connection tests before creating game servers. Preserve working administration throughout.

Verify Docker/Wings, UUID mounts and selected game workloads survive a planned reboot, one node at a time (router last, recovery ready). Verify an ARM64 game on Thor using a native image digest. Verify private RDP with Windows running and the Windows lifecycle scripts, then leave it stopped. Review a clean full post-deployment plan; explain imported frozen fields and any remaining drift. Restore a backup into an empty test destination and compare checksums before claiming backup acceptance.

## Exact cleanup plan

**Current authorized deletion set: empty.** The only obsolete instance found, Utgard-Loki, and its 50 GB boot volume were already TERMINATED before discovery. They cannot be reclaimed by deleting a live replacement and do not justify deleting any Jotunheim resource.

Protect Thor instance `…cz3y6krpgaq`, its boot `…gkbjdvbpa`, VNIC `…o72dg3nja`, 10.10.50.10 and its public IP; both subnets/security lists/routes; Jotunheim VCN/DHCP; IGW/NAT/service gateway; all current game data; backup/state buckets; and Tailscale router/access dependencies. No bucket exists in the successful current listing; recheck before any future cleanup.

If later inventory finds a live deletion candidate: record its exact OCID, owner, attachments, routes, data retention and reverse dependencies; prove replacement SSH/RDP/game/backup access; take any approved backup; prepare a saved destroy plan limited to the named resource. Ask approval for that exact dependency-ordered set. Detach only unused storage/interfaces first, remove unused instances only after data checks, then unused security/routes/subnets/gateways, and VCN last **only if no retained dependency remains**. Current shared network is retained, so those network deletions are forbidden. Remove lifecycle protection only in a separately reviewed change; state removal is not resource deletion and does not end billing.
