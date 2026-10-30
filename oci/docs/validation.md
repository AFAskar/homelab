# Deployment checks

Run checks from the repository root after an approved change. Store raw plans,
logs, billing snapshots and reports under ignored `oci/inventory/`. Record
change-specific results and limitations in the PR, not in this runbook.

## Source and Terraform

Load the OCI profile, backend configuration and scoped Tailscale OAuth file
references described in the README. Load the existing SOPS age identity for
Kubernetes builds and DNS deployment.

```bash
terraform -chdir=oci/terraform fmt -check
terraform -chdir=oci/terraform init -backend-config=backend.hcl -lockfile=readonly
terraform -chdir=oci/terraform validate
terraform -chdir=oci/terraform plan -out=review.tfplan
terraform -chdir=oci/terraform show -json review.tfplan | python3 oci/scripts/check-plan.py
python3 oci/scripts/test-lifecycle.py
```

Review every replacement, deletion, shape/storage change and public ingress
change before applying. Retained imports must propose no unintended resource
changes. If the Windows compatibility prerequisite is unresolved, a full-root
plan must fail its Windows precondition. Use only an explicitly reviewed,
approved staged plan for independent non-Windows work; a targeted check is
not a clean full-environment plan. After applying, generate a fresh plan and
explain any difference before making another change.

Build the Panel, Traefik and Argo roots with the authorized KSOPS environment:

```bash
(
  set -e
  umask 077
  validation_dir=$(mktemp -d)
  trap 'rm -rf -- "$validation_dir"' EXIT
  kustomize build --enable-alpha-plugins --enable-exec kubernetes/pelican/manifests > "$validation_dir/panel.yaml"
  kustomize build --enable-alpha-plugins --enable-exec kubernetes/traefik/manifests > "$validation_dir/traefik.yaml"
  kustomize build --enable-alpha-plugins --enable-exec kubernetes/argocd/manifests > "$validation_dir/argocd.yaml"
  kubeconform -strict -summary -ignore-missing-schemas "$validation_dir/"*.yaml
  kubectl apply --server-side --force-conflicts --dry-run=server -f "$validation_dir"
)
```

The temporary files can contain decrypted Secrets; keep them private. The API
dry run validates custom resources whose schemas Kubeconform does not have.
Server-side apply avoids the client-side annotation size limit on large CRDs;
`--force-conflicts` here applies only to the dry run. Run Ansible syntax/
production lint, ShellCheck, Python compilation and a redacted secret scan for
changed files before committing.

## DNS and private access

```bash
ansible-playbook -i pos, docker/adguardhome/deploy.yaml
dig @192.168.1.28 github.com
dig +tcp @192.168.1.28 pelican.home.internal
dig @100.114.113.82 wings-01.oci.home.internal
python3 oci/scripts/healthcheck.py
```

Each Wings FQDN must return exactly its private VNIC address. Verify fresh
key-authenticated SSH to all Linux private addresses and sudo where needed.
Check both approved OCI subnet routes, router forwarding/SNAT, and pod access
from both Kubernetes hosts. A tailnet peer being online is not a subnet-route
test. Keep a working recovery path before changing listeners or ingress.
Use [callback checks](callback-security.md) to confirm Thor can reach only the
authenticated Panel daemon API on the dedicated listener.

## Panel, games and storage

```bash
kubectl -n argocd get application pelican traefik-config
kubectl -n pelican get pods,pvc,certificates
kubectl -n pelican exec deployment/pelican -c panel -- supervisorctl status
python3 oci/scripts/check-games.py
```

Require Synced/Healthy applications, Ready certificates, a Bound retained PVC,
and running queue/scheduler processes. In Panel, check all four nodes and a
browser console/WebSocket round trip. Test each game's actual public protocol
and an external game client where applicable. The supplied game probe checks
Mindustry TCP/UDP discovery and public-admin port denial; adapt probes for
other games instead of treating an open TCP socket as gameplay acceptance.

For each node, inspect Docker/Wings service state, native image architecture,
disk space and the data mount. Paid data must mount by UUID at `/srv/pelican`;
Thor keeps `/var/lib/pelican/volumes` on its retained root disk. During an
approved reboot test, reboot one node at a time, router last. Require fresh
private access, automatic service/game recovery, unchanged data markers and
correct mounts. Never initialize an existing disk to fix a missing mount.

Select free allocations from the TCP/UDP 25565–25765 pool when adding games.
An unassigned allocation need not answer probes. Test a listener or actual
game at the chosen port; keep administrative services out of the public pool.

## Backups and monitoring

Follow [backup capture and restore](operations.md#backups-and-restores).
Download a named encrypted object, verify stored/local SHA256, decrypt into
new empty directories, check every member, SQLite integrity, APP_KEY and
selected saved worlds. Confirm previously running games resume after capture.
Archive checks alone do not prove complete host-loss recovery.

In the existing Prometheus UI, check private exporter `up`, Wings/systemd
state, disk/memory/CPU metrics and `probe_success{job="oci-public-games"}`.
Confirm the private path from both homelab nodes and the public game path.
Test notification delivery separately from rule installation. Read usage and
promotion balance with `spend-status.py`, compare with the cost model and
check promotion expiry; budget notifications do not cap spending.

## Windows acceptance

Before launch, obtain technical confirmation for the exact regular E4 Windows
11 custom-image/UEFI/Secure Boot/TPM configuration and review the imported
image's boot minimum. Preserve the approved 2 OCPU/16 GB/100 GB allocation and
security requirements. Image metadata acceptance or local QEMU tests do not
establish OCI boot compatibility. Obtain launch approval for the saved plan.

After launch, check actual guest Secure Boot/TPM, private RDP/NLA, a rejected
wrong-password attempt and the start/stop/status scripts. Recheck Terraform
for unintended lifecycle changes, verify persistent boot storage, and leave
the VM stopped after testing. Diagnose failure using private access or console
recovery; never open public RDP or disable security requirements as a shortcut.
