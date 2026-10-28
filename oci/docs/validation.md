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
| Ansible syntax checks | Pass for Wings/router, bootstrap-router, homelab routes and callback proxy playbooks, with pinned collections |
| Ansible lint | Pass at production profile; dependency deprecation messages only. In-guest idempotence is not yet tested |
| ShellCheck | Pass for all delivered shell scripts, including sourced Windows helper |
| Windows PowerShell syntax | Both inspect-source.ps1 and first-boot.ps1 parsed successfully using the source guest PowerShell parser, without executing first-boot changes |
| Python compilation | Pass for delivered Python scripts |
| Windows source follow-up | Read-only guest inspection passed; offline checkpoint hash verified; independent local 80 GiB QCOW2 clone passed `qemu-img check`. No source alteration, generalization, import or OCI boot |
| Windows lifecycle safety regression | Six offline tests pass: approval required for start, correct managed identity/profile/region, already-running/stopped idempotence, graceful SOFTSTOP, read-only status. **Not live OCI or RDP tests** |
| Secret scan | Gitleaks redacted scan of new delivery passed; large ignored provider binary excluded. Plaintext credentials, age key and raw billing/inventory are not committed |
| Public ingress review | New public NSG game rule is TCP/25565 only. No new public SSH/RDP/API ingress. Existing public SSH remains until a verified route/recovery path; final lockdown is NOT claimed |
| Spending read | Usage API currently reports zero EUR computed cost for Compute, Block Storage, VCN. Credit balance still unverified; usage may lag |

Provider/backend diagnostics and raw plans contain infrastructure details and remain outside Git. The real root keeps the secure OCI backend; the temporary diagnostic copy is neither a second maintained environment nor an approved deployment path. Only a sanitized import summary is committed. Remote state must be initialized in the real root and safe plans regenerated after prerequisites are resolved.

## Deployment and unresolved prerequisites

Nothing in this delivery has been deployed. No Terraform apply, authoritative state import, paid upload, image import, resource cleanup, guest provisioning, Argo sync or merge was performed. Only OCI reads, a denied attempt to run a read-only agent inventory, Kubernetes dry-runs and local code/validation operations were used.

1. **Thor access migration/recovery**: the Bitwarden agent identity was recovered and read-only guest/data inventory succeeded with sudo. Docker/containerd/Tailscale versions, root UUID, ample resources and absence of game containers/data were checked. SSH currently listens only on its tailnet IP; private listener, router advertisement/grants, persistent firewall, secure configuration backup and OCI console recovery remain pending. `bootstrap-router.yaml` preserves the tailnet listener while preparing private SSH. No live host change was made.
2. **Windows 11 OCI image/security/boot-volume path**: local MPMB Windows 11 Pro source was inspected and a hash-verified 80 GiB offline-checkpoint clone passed `qemu-img check`. Current source guest reports TPM2 and Secure Boot enabled; installer bypass flags are also present. Signed VirtIO drivers are staged in the current guest, but not boot-tested on the clone. OCI excludes custom images from shielded instances; BIOS/MBR versus GPT/UEFI import preparation needs verification. Its import guide says 256 GB but its linked boot-volume guide says the image default or 50 GB for current images, so the earlier hard 256 GB claim is withdrawn. Keep 100 GB and verify the actual imported-image minimum. Source acquisition is resolved; clone sanitization, driver boot verification, generalization, import and live OCI RDP remain incomplete. No source VM mutation, security bypass or allocation substitution was made.
3. **State/backup/IAM bootstrap**: namespace eventually recovered as axh0rk0bydbu; root and Ymir bucket lists are empty. Need approved private versioned state bucket plus bucket-scoped operator identities. State-bucket creation/storage and subsequent backup/image storage require approval. Group/domain listing and agent permissions need reconciliation.
4. **Actual credits/free entitlement/expiry**: EUR/PAYG and subscription dates verified, remaining balance inaccessible. Official A1 allowance sources conflict. Under the smaller documented allowance, the current baseline is €246.78 before images/other costs; the illustrative image scenario exceeds €250. Confirm effective account tariffs and promotion terms before approving spend.
5. **Tailnet policy, routes, DNS and certificates**: the user confirms the current policy is allow-all. A concrete restrictive IPv4 policy with observed identities/subnets and embedded accept/deny tests is now prepared at `ansible/tailscale/policy.hujson`. It still needs Tailscale control-plane validation and approval before replacing the live allow-all rules. Neither homelab host currently accepts routes. Private DNS, TLS renewal, callback proxy, pod route tests and VNIC additive NSGs remain to be deployed/verified.
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

## CodeRabbit review follow-up

Accepted the functional findings with focused commits: application readiness, SSH validation before restart, callback tailnet grant, refreshable exporter inventory, clear locked-agent errors, retry-safe Windows import, JSON tfvars exclusion, Caddy 2.6.2 trust syntax, CA/DNS before any Wings start, bootstrap/Panel/certificate prerequisites, private-port range exclusions, EndpointSlice discovery and partition-signature guards. Also accepted the small `nofail` recovery and IMDSv2-only improvements. `AGENTS.md` now requires atomic commits and validation.

The Panel CA copy was byte-identical to `pki/homelab-root-ca.crt`. It has been removed: a shared `pki/kustomization.yaml` generates the ConfigMap from that sole existing public certificate, respecting Kustomize loading restrictions without maintaining a duplicate CA file.

Validation of the review fixes:

- Panel/Kustomize/KSOPS build succeeds; the generated CA data exactly matches the PKI source. Kubeconform reports 9 valid objects, 3 CRDs skipped, no invalid objects; live Kubernetes API dry-run validates those CRDs as well in the existing default namespace. Nothing is persisted.
- Ansible syntax/lint passes. The callback Caddyfile validates with the exact Caddy 2.6.2 upstream binary (publisher SHA512 verified), using disposable local test certificates; Thor's archive candidate is 2.6.2-14. No Caddy package was installed on Thor.
- Non-modifying signature probes distinguish blank, GPT and ext4 disposable files and preserve their SHA256 values. Formatting remains gated; no live disk was formatted. `nofail` keeps the host bootable, while Wings still requires the data mount.
- Terraform formatting/validation passes. Diagnostic console checks accept TCP/25565 and reject individual private ports 2022/3389/8080/9100 and ranges 2000–3000 / 9000–10000; no API write or apply occurs.
- Offline tests preserve an existing private inventory while refreshing all four synthetic exporter/DNS targets. Empty/malformed agents produce clear failures without a traceback or output key.
- Offline Windows import tests cover a fresh upload, empty CLI list output, existing import reuse, existing upload reuse and checksum-mismatch rejection. No OCI upload/import was performed. Existing-import polling uses supported CLI commands; concurrent imports of the same source must still be serialized by the operator.
- ShellCheck, Python compilation, six lifecycle regression tests and redacted secret scanning pass.

Findings intentionally not applied:

- Redacting every live address/OCID from the discovery record would remove the exact inventory requested by the user, while those identifiers remain required in the import definitions. Public certificates, addresses and resource OCIDs are not authentication credentials. Raw inventories, private keys, credentials, billing personal data, state and plans remain excluded from Git.
- The three new exporter IPs cannot be added before those instances exist. The renderer already derives all four targets from actual Terraform outputs and can now refresh them without discarding operator inventory. No fictional addresses are added.
- A read-only root filesystem is not applied blindly to the official Panel image, which writes runtime application/plugin/cache files. Its UID/capability restrictions remain; changing its filesystem layout warrants application testing beyond this focused fix.

## What the user needs to decide or provide

1. **Windows hosting/requirements:** confirm whether Windows 11 must remain on OCI. Custom-image shielded/TPM support is still unresolved. Oracle’s two boot-size documents conflict; 256 GB is not a confirmed requirement for this image, so no size increase is currently requested. A full OCI deployment requires a confirmed compatible Windows workflow, or an explicitly approved different Windows hosting arrangement. The local source image is already available; no replacement media/key is needed from the user.
2. **Credits:** confirm the Console's actual remaining credit, promotion expiry, and effective A1 free allowance for this account. The queried price API and narrative free-tier documentation conflict; the smaller allowance would leave only €3.22 before image/other costs (the illustrative image scenario exceeds €250). Reported zero cost is not a credit-balance proof. Do not send billing/payment secrets.
3. **Tailnet administration:** approve/apply the reviewed tag ownership, scoped grants and the two advertised subnet routes in the existing tailnet, or provide access to an authenticated admin session. Do not replace the existing policy wholesale. Existing OCI and Bitwarden credentials work; no new private SSH key is needed.
4. **Deployment approval:** after these decisions, approve the concrete saved plans for private versioned state-bucket bootstrap, safe imports/access migration and billable resources/image storage. The agent can prepare and execute the technical steps; the user need not manually create VMs, certificates or the Panel. Billable applies, access-cutting changes, cleanup and merging remain withheld until the applicable explicit approvals.

## Windows disk reduction — 2026-10-28

User-authorized planned Windows boot capacity is now 100 GB instead of the original 200 GB. Wings data disks remain 200 GB each; Thor remains unchanged. Fresh official-price/ECB calculation gives $4.25 / €3.82 monthly savings and a new conditional baseline of $247.76 / €222.55, with 850 GB paid instance storage. Terraform formatting/validation and estimator consistency checks pass. This changes configuration only; no local disk resize, OCI apply or billable action occurred.

## Concrete tailnet policy — user-requested hardening

The example with placeholders has been replaced by `ansible/tailscale/policy.hujson`. Admin clients are the observed laptop and freyr; servers get only the required API/metrics/callback paths, and other members/owner devices receive no infrastructure grant. Router host-firewall admin sources match. Eleven embedded Tailscale accept/deny tests cover admin access, service paths, denied lateral administration and non-admin devices. Local JSON/selector/port structure checks pass; official control-plane test evaluation and live connectivity have not been run. No live policy, route approval or host change was made.
