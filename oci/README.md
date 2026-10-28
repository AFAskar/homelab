# OCI Pelican infrastructure

**Review branch, not a deployed environment.** Start with [discovery](docs/existing-infrastructure.md), [migration](docs/migration.md), [costs](docs/costs.md), and [validation](docs/validation.md). Windows 11 has an unresolved custom-image/TPM support blocker. No billable apply, authoritative import, guest provisioning, cleanup, or merge has been performed.

One Terraform root lives in `oci/terraform/`. It preserves Thor as logical `wings-04`, its 100 GB boot disk, and the existing Jotunheim network. Three paid E6 nodes have exactly 2 OCPUs, 16 GB RAM, 50 GB boot and 200 GB data each. Windows is a required E4 instance (2 OCPUs, 16 GB RAM, 200 GB boot), guarded against deployment without verified Windows 11 compatibility. No other paid router or new network is introduced.

## Tooling and authentication

Use Terraform 1.12+ (OCI backend locking), OCI provider 9.11.0 (lockfile committed), OCI CLI, Python 3 with `oci` and `PyYAML`, Ansible with the pinned collections, kubectl, Kustomize/KSOPS 4.5.1, SOPS and age. `oci setup config` configures the default API-key profile; keep `~/.oci` and its private key readable only by you. The profile needs read access to identity, compute, networks, volumes, images, limits, budgets, usage and storage. Deployment additionally needs their create/update rights in Ymir. API tests do not prove all write permissions. Do not commit keys, raw discovery, plans, state, tfvars, images or Wings tokens.

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

Supply a private **existing, versioned** state bucket first; none was discovered. Creating it and any storage charge needs approval. State is encrypted at rest by OCI. Use a dedicated bucket with bucket-scoped IAM, no public/PAR access, versioning, audit logging, and backend locks. Never share plan/state artifacts publicly. Bucket policy needs `OBJECT_INSPECT`, `OBJECT_READ`, `OBJECT_CREATE`, `OBJECT_DELETE` for the state and lock objects; separate administrators manage the bucket. Do not disable locking or force-unlock another writer. No credentials belong in `backend.hcl`; backend configuration itself is cached under `.terraform`.

Example policy, replace group/compartment/bucket names:

```text
Allow group HomelabTerraform to manage objects in compartment Ymir where target.bucket.name = 'homelab-tfstate'
Allow group HomelabTerraform to read buckets in compartment Ymir where target.bucket.name = 'homelab-tfstate'
```

The state bucket is a bootstrap prerequisite outside this root so it survives infrastructure teardown. Reuse an approved existing bucket if available. Backup-bucket access belongs to a separate bucket-scoped writer/restore-reader identity, not public access keys or tenancy-wide credentials on Wings.

## Guest configuration and GitOps

Cloud-init only bootstraps new Ubuntu instances. Run Ansible against actual private addresses after reviewed imports, attached volumes and approved routing:

```bash
cd oci/ansible
ansible-galaxy collection install -r requirements.yaml
# inventory.example.yaml documents all inputs. Or generate inventory from state:
python3 ../scripts/render-inventory.py
ansible-playbook --syntax-check site.yaml
ansible-playbook site.yaml
ansible-playbook homelab-routes.yaml
ansible-playbook tailscale/panel-proxy.yaml
```

Review the generated inventory before use. Existing Thor data requires `retained_data_reviewed: true`. New blank data disks require explicit `wings_initialize_empty_volume: true` after confirming attachment identity. Private firewall lockdown remains off until private access is verified. No existing data or Docker root is migrated automatically.

Panel manifests live at `kubernetes/pelican/`, following the existing repository layout, CA, SOPS recipient, and application-of-applications integration. Its Argo application has **manual sync**. Build with `kustomize build --enable-alpha-plugins --enable-exec kubernetes/pelican/manifests` using the authorized SOPS age key. A generated APP_KEY is already encrypted to the repository recipient; protect its backup. Finish the official `/installer` before node enrollment. Do not expose the installer publicly.

[Operations](docs/operations.md) covers private TLS/DNS, enrollment, backups, monitoring, Windows tooling and recovery. [Architecture](docs/architecture.md) records network flows and ARM limitations. Billable deployment, cleanup and merge require explicit approval; a passing static check is not deployment approval.
