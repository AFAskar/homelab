# OCI Pelican infrastructure

**Review branch, not a deployed environment.** Start with [discovery](docs/existing-infrastructure.md), [migration](docs/migration.md), [costs](docs/costs.md), and [validation](docs/validation.md). Windows 11 has a locally verified VirtIO/Secure Boot/TPM build path; actual OCI image/shape compatibility and RDP remain unverified. The user-approved €5 state/image stage has created private state and image buckets; the Windows upload is active and Compute image import is queued behind upload completion. No compute, live ACL change, retained-resource import, OCI guest provisioning, cleanup or merge has been performed.

One Terraform root lives in `oci/terraform/`. It preserves Thor as logical `wings-04`, its 100 GB boot disk, and the existing Jotunheim network. Three paid E6 nodes have exactly 2 OCPUs, 16 GB RAM, 50 GB boot and 200 GB data each. Windows is a required E4 instance (2 OCPUs, 16 GB RAM, 100 GB boot), guarded against deployment without verified Windows 11 compatibility. No other paid router or new network is introduced.

## Tooling and authentication

Use Terraform 1.12+ (OCI backend locking), OCI provider 9.11.0 and Tailscale provider 0.29.3 (lockfile committed), OCI CLI, Python 3 with `oci` and `PyYAML`, Ansible with the pinned collections, kubectl, Kustomize/KSOPS 4.5.1, SOPS and age. `oci setup config` configures the default API-key profile; keep `~/.oci` and its private key readable only by you. The profile needs read access to identity, compute, networks, volumes, images, limits, budgets, usage and storage. Deployment additionally needs their create/update rights in Ymir. API tests do not prove all write permissions. Do not commit keys, raw discovery, plans, state, tfvars, images or Wings tokens.

```bash
export OCI_TENANCY_OCID=... # profile tenancy OCID
oci/scripts/inventory.sh
cp oci/terraform/terraform.tfvars.example oci/terraform/terraform.tfvars
cp oci/terraform/backend.hcl.example oci/terraform/backend.hcl
terraform -chdir=oci/terraform init -backend-config=backend.hcl
terraform -chdir=oci/terraform fmt -check
terraform -chdir=oci/terraform validate
terraform -chdir=oci/terraform plan -out=review.tfplan
terraform -chdir=oci/terraform show -json review.tfplan | python3 oci/scripts/check-plan.py
```

The approved bootstrap created the private, versioned `homelab-tfstate` bucket; the real root now initializes against it. For recreation, supply an approved private versioned bucket first. State is encrypted at rest by OCI. Use a dedicated bucket with bucket-scoped IAM, no public/PAR access, versioning, audit logging, and backend locks. Never share plan/state artifacts publicly. Bucket policy needs `OBJECT_INSPECT`, `OBJECT_READ`, `OBJECT_CREATE`, `OBJECT_DELETE` for the state and lock objects; separate administrators manage the bucket. Do not disable locking or force-unlock another writer. No credentials belong in `backend.hcl`; backend configuration itself is cached under `.terraform`.

Example policy, replace group/compartment/bucket names:

```text
Allow group HomelabTerraform to manage objects in compartment Ymir where target.bucket.name = 'homelab-tfstate'
Allow group HomelabTerraform to read buckets in compartment Ymir where target.bucket.name = 'homelab-tfstate'
Allow group HomelabTerraform to read buckets in compartment Ymir where target.bucket.name = 'homelab-win11-images'
Allow group HomelabTerraform to {OBJECT_CREATE, OBJECT_OVERWRITE, OBJECT_INSPECT, OBJECT_READ} in compartment Ymir where target.bucket.name = 'homelab-win11-images'
```

The image grant supports hash/object inspection, multipart upload and image-source reading without object-deletion permission. OCI requires OBJECT_CREATE and OBJECT_OVERWRITE for multipart parts, and BUCKET_READ plus OBJECT_READ to commit them; see the [official operation permissions](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/objectstoragepolicyreference.htm). CLI `--no-overwrite` and the digest guard still protect the selected source object. Bucket creation/management and Compute image import require separate compartment-scoped rights; this example covers storage objects, not a complete Terraform deployment role.

The state bucket is a bootstrap prerequisite outside this root so it survives infrastructure teardown. Reuse an approved existing bucket if available. Backup-bucket access belongs to a separate bucket-scoped writer/restore-reader identity, not public access keys or tenancy-wide credentials on Wings.

## Tailnet policy as code

The same Terraform root manages the existing tailnet’s complete policy using `tailscale_acl.tailnet`, with `ansible/tailscale/policy.hujson` as its single reviewed source. Provider 0.29.3 validates syntax and embedded tests against the Tailscale API during planning. An import block reads the existing policy before proposing a change; creation without import is disabled. `prevent_destroy` and `reset_acl_on_destroy=false` protect against deleting ownership or restoring a default allow-all policy. Do not manage this same policy from a second root or an automatic console/GitOps writer.

Bootstrap one OAuth trust credential in the existing tailnet with **Policy File read/write only**. Save its Client ID and secret in the ignored, owner-only `oci/ansible/secrets/tailscale-client-id` and `tailscale-client-secret` files (mode 0600), then configure the provider without putting secrets in Terraform inputs/state:

```bash
export TAILSCALE_OAUTH_CLIENT_ID="file:$PWD/oci/ansible/secrets/tailscale-client-id"
export TAILSCALE_OAUTH_CLIENT_SECRET="file:$PWD/oci/ansible/secrets/tailscale-client-secret"
terraform -chdir=oci/terraform plan -target=tailscale_acl.tailnet -out=policy-review.tfplan
```

Use the protected OCI backend before authoritative import/apply. An isolated targeted policy plan may be reviewed before the full OCI deployment is ready; this is a bootstrap exception, not the routine deployment workflow. An ACL plan is validation/review only. Obtain access-change approval before applying its policy update. The browser is used for initial credential bootstrap and recovery, not routine policy edits. Provider 0.29.3 has no ETag guard on policy updates; `overwrite_existing_content=false` protects creation only. Use one operator/writer at a time. Before a console recovery edit, stop pending applies and invalidate every saved plan containing this policy. Reconcile the recovery policy into Git and generate/review a fresh plan before resuming. Follow the recovery procedure in operations.md; never apply a pre-recovery plan. Its unsaved preview was discarded; the live allow-all policy is unchanged.

## Guest configuration and GitOps

Cloud-init only bootstraps new Ubuntu instances. Follow this order after the applicable import/deployment approvals:

1. Prepare the existing router inventory before paid nodes exist:

   ```bash
   cd oci/ansible
   ansible-galaxy collection install -r requirements.yaml
   cp inventory.example.yaml inventory.yaml # only if no private inventory exists
   python3 ../scripts/select-ssh-agent-key.py
   ```

   Review `thor_bootstrap` in the private inventory. Confirm the administrator can apply `tag:oci-router`, validate `tailscale/policy.hujson` as the replacement for allow-all (including router-to-pos TCP/443), and verify recovery access **before tagging Thor**. After the access-change review/approval, set `enable_private_ssh_listener: true` for `thor-bootstrap`, then run `ansible-playbook bootstrap-router.yaml` over its existing tailnet address. Approve advertised subnet routes and verify private SSH; preserve the current tailnet listener.
2. After paid nodes are provisioned through an approved plan, run `python3 ../scripts/render-inventory.py` to refresh DNS/monitoring targets and create an inventory if absent. It preserves any existing private inventory; reconcile instance addresses manually. Review actual subnet sources and run `ansible-playbook homelab-routes.yaml` to establish Kubernetes pod access.
3. Manually sync Argo application `pelican`, finish its official `/installer`, create wings-01 through wings-04 in Panel, and save their generated configs at the `wings_config_local` paths in the ignored secrets directory. Complete DNS and issue per-node Wings TLS certificates from the existing homelab CA.
4. Issue a callback-proxy certificate with SAN `pelican.home.internal`. Put its full chain and private key at `secrets/panel-proxy/tls.crt` and `secrets/panel-proxy/tls.key`, or override `panel_proxy_certificate_local` and `panel_proxy_key_local` in the private inventory. Confirm `homelab_ca_local` points to the existing public root certificate. Run `ansible-playbook tailscale/panel-proxy.yaml`.
5. Only after those Panel configs/certificates and callback access exist, run `ansible-playbook --syntax-check site.yaml` and `ansible-playbook site.yaml` to provision Wings. Verify enrollment, browser console and game access.

Existing Thor data requires `retained_data_reviewed: true` after backup/review. New blank data disks require explicit `wings_initialize_empty_volume: true` after confirming attachment identity. Private firewall lockdown remains off until private access is verified. No existing data or Docker root is migrated automatically.

Panel manifests live at `kubernetes/pelican/`, following the existing layout, CA, SOPS recipient and application-of-applications integration. Its Argo application has **manual sync**. Build with `kustomize build --enable-alpha-plugins --enable-exec kubernetes/pelican/manifests` using the authorized SOPS age key. The APP_KEY is encrypted to the existing repository recipient; protect its backup. Keep the installer private.

[Operations](docs/operations.md) covers private TLS/DNS, enrollment, backups, monitoring, Windows tooling and recovery. [Architecture](docs/architecture.md) records network flows and ARM limitations. Billable deployment, cleanup and merge require explicit approval; a passing static check is not deployment approval.

Windows source follow-up: the existing MPMB Windows 11 Pro VM was inspected and a verified offline checkpoint was cloned locally outside Git (the test clone is under `~/VirtualMachines/oci-win11-validation/`). `windows/clone-checkpoint.py` reproduces this without touching the running VM; `windows/inspect-source.ps1` records read-only guest checks. The clone has been sanitized and Sysprep shut down; its final offline capture and local validation are recorded in [windows-image-validation.json](docs/windows-image-validation.json). No OCI import or boot has occurred. Oracle's Windows import guide states 256 GB, but its [boot-volume guide](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumes.htm#Custom) states the image default or 50 GB for current images, reserving 256 GB for older Windows images. This documentation conflict is not a proven 100 GB launch failure. Keep the requested 100 GB and check imported-image metadata before deployment.
