# Validation and acceptance — 2026-10-28

## Implemented

One OCI Terraform root, provider 9.11.0 with lockfile, exact requested paid matrix, protected/imported Thor and shared-network definitions, UUID data-volume provisioning, private NSGs, security-list hardening switch, EUR budget alerts, cloud-init and Ansible Wings/Tailscale/firewall roles, private callback proxy, pod-route configuration, Panel GitOps manifests, SOPS APP_KEY, private monitoring, inventory/cost/backup/health/spend/Windows scripts and preservation/deletion/recovery documentation.

“Imported definitions” means import blocks are present, not that authoritative state has been changed. Preservation freezes intentionally defer complete drift reconciliation. Windows conversion/import scripts are stages, not completed media acquisition or guest installation.

## Checks executed

| Check | Result and limit |
|---|---|
| `terraform fmt -check` | Pass on actual `oci/terraform/` root |
| `terraform init -backend=false -input=false` | Pass; official provider downloaded, lockfile committed. No real remote state bucket is available yet |
| `terraform validate` | Pass on actual root |
| Preservation plan against live OCI | Pass in private temporary diagnostic copy using local backend and **exceptional retained-resource targets**: **12 imports, 0 additions, 0 changes, 0 deletions**. All 12 resource actions are `no-op`. [Sanitized summary](import-plan-summary.json). No apply/import executed |
| Plan destruction guard | Pass on preservation plan JSON |
| Full un-targeted diagnostic plan | Expected blocked result, exit 1: `discovery_reviewed=false`. Not an executable approved deployment plan |
| Windows gate diagnostic | With only discovery gate overridden in a temporary read-only plan, expected exit 1 at `windows_compatibility_verified=false`. No gate override is saved in deployment inputs |
| Live image/shape compatibility | OCI `GetImageShapeCompatibilityEntry` confirmed the selected Ubuntu 26.04 image and E6.Flex; E6/E4 limits have headroom. This is not a capacity reservation or guest boot test |
| Docker package availability | Official Resolute signed-package index contains pinned Docker CE/containerd versions for amd64 and arm64 |
| Argo app root build | `kubectl kustomize kubernetes` passes |
| Panel Kustomize/KSOPS | Pass using existing authorized Argo SOPS key without printing decrypted secrets; 12 resources rendered |
| Kubeconform strict validation | 9 valid, 0 invalid/errors, 3 CRDs skipped due missing downloaded schemas |
| Kubernetes server dry-run | Pass for all 11 namespaced rendered objects, including cert-manager and Prometheus CRDs, using **existing default namespace in a temporary validation copy**. Namespace object dry-run passes separately. Actual pelican namespace is absent; no live resource created. This validates API admission, not scheduling, storage, container startup or functionality |
| Ansible syntax checks | Pass for Wings/router, homelab routes and callback proxy playbooks, with pinned collections |
| Ansible lint | Pass at production profile; dependency deprecation messages only. In-guest idempotence is not yet tested |
| ShellCheck | Pass for all delivered shell scripts, including sourced Windows helper |
| Python compilation | Pass for delivered Python scripts |
| Windows lifecycle safety regression | Six offline tests pass: approval required for start, correct managed identity/profile/region, already-running/stopped idempotence, graceful SOFTSTOP, read-only status. **Not live OCI or RDP tests** |
| Secret scan | Gitleaks redacted scan of new delivery passed; large ignored provider binary excluded. Plaintext credentials, age key and raw billing/inventory are not committed |
| Public ingress review | New public NSG game rule is TCP/25565 only. No new public SSH/RDP/API ingress. Existing public SSH remains until a verified route/recovery path; final lockdown is NOT claimed |
| Spending read | Usage API currently reports zero EUR computed cost for Compute, Block Storage, VCN. Credit balance still unverified; usage may lag |

Provider/backend diagnostics and raw plans contain infrastructure details and remain outside Git. The real root keeps the secure OCI backend; the temporary diagnostic copy is neither a second maintained environment nor an approved deployment path. Only a sanitized import summary is committed. Remote state must be initialized in the real root and safe plans regenerated after prerequisites are resolved.

## Deployment and unresolved prerequisites

Nothing in this delivery has been deployed. No Terraform apply, authoritative state import, paid upload, image import, resource cleanup, guest provisioning, Argo sync or merge was performed. Only OCI reads, a denied attempt to run a read-only agent inventory, Kubernetes dry-runs and local code/validation operations were used.

1. **Thor guest identity**: SSH to its tailnet IP with available keys was rejected; OCI Run Command returned 404 NotAuthorizedOrNotFound. Need working account/key or approved console recovery. Guest data, existing services/firewalls and router suitability remain unverified. Do not install packages, initialize disks or close its existing public SSH access yet.
2. **Windows 11 supported image+TPM path**: OCI custom images are excluded from shielded instances in current documentation; Windows 11 requires TPM2/UEFI. No supported path or booted VM has been evidenced. Image media installation, drivers, generalization, import and RDP acceptance remain incomplete. No shape/OS/security substitution is made.
3. **State/backup/IAM bootstrap**: namespace eventually recovered as axh0rk0bydbu; root and Ymir bucket lists are empty. Need approved private versioned state bucket plus bucket-scoped operator identities. State-bucket creation/storage and subsequent backup/image storage require approval. Group/domain listing and agent permissions need reconciliation.
4. **Actual credits/free entitlement/expiry**: EUR/PAYG and subscription dates verified, remaining balance inaccessible. Official A1 allowance sources conflict. Under the smaller documented allowance the baseline exceeds €250 before image costs. Confirm effective account tariffs and promotion terms before approving spend.
5. **Tailnet policy, routes, DNS and certificates**: existing policy was not readable through an admin API; grants example still needs actual identities/destinations and admin approval. Neither homelab host currently accepts routes. Private DNS, TLS renewal, callback proxy, pod route tests and VNIC additive NSGs remain to be deployed/verified.
6. **Panel and backup/monitoring acceptance**: installer/admin setup, node enrollment, game eggs/images, scheduled quiesced backups, restore test, all exporter endpoints, external game probes and daily credit/lifecycle monitoring still need live configuration. Public CA data and private SOPS key trust were checked locally; application behavior was not.

## Live acceptance checklist — all pending

- [ ] Thor guest/data/recovery inventory complete, preserved ARM64 4/24/100 GB configuration and safe authoritative import verified.
- [ ] Full approved plan applied through protected state; clean subsequent un-targeted plan or reviewed differences.
- [ ] All four Wings nodes online in Panel, correct disks/data paths, Docker/Wings survive reboot.
- [ ] ARM64-compatible game tested on Thor, AMD games tested, public allocation reached from outside tailnet.
- [ ] Approved subnet routes/grants work; administrators privately SSH to each Linux private IP.
- [ ] Both Kubernetes nodes' pods can reach Wings TLS/API; browser websockets/uploads and reverse Panel callbacks succeed.
- [ ] Public SSH/RDP rules removed only after private/recovery verification; host and OCI ingress checked externally.
- [ ] Supported Windows 11 image prepared/imported; guest boots with TPM2/UEFI; private RDP login succeeds.
- [ ] Live Windows start/stop/status test passes, state plan unchanged, VM left stopped.
- [ ] Consistent selected backups uploaded, staged restore and checksums verified, bounded retention reviewed.
- [ ] Service/CPU/RAM/disk/game/route/Windows/credit monitoring and alert delivery verified.
- [ ] Any later exact legacy cleanup approved and executed only after dependency checks; currently deletion set is empty.

## Required approvals

No billable operation is ready for approval while the above blockers prevent a complete safe plan. After resolution, request approval for the concrete state bootstrap and image/storage/compute plan with updated all-in cost. Obtain separate explicit approval for access-cutting/destructive cleanup and any requirements change. Do not merge this draft PR without the user's explicit instruction.
