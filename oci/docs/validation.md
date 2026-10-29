# Validation and acceptance — 2026-10-29

## Implemented

One OCI Terraform root, provider 9.11.0 with lockfile, exact requested paid matrix, protected/imported Thor and shared-network definitions, UUID data-volume provisioning, private NSGs, security-list hardening switch, EUR budget alerts, cloud-init and Ansible Wings/Tailscale/firewall roles, private callback proxy, pod-route configuration, Panel GitOps manifests, SOPS APP_KEY, private monitoring, inventory/cost/backup/health/spend/Windows scripts and preservation/deletion/recovery documentation.

“Imported definitions” means import blocks are present, not that authoritative state has been changed. Preservation freezes intentionally defer complete drift reconciliation. Local Windows acquisition, sanitization and generalization are complete; OCI upload/import and live guest acceptance remain pending.

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
| Windows source follow-up | Read-only inspection and checkpoint hash passed. Independent 80 GiB clone boots Windows 11 with TPM/Secure Boot and updated VirtIO disk/NIC; guest SSH succeeds over an isolated host port. Sysprep/generalization and local NLA authentication pass; no OCI import or boot |
| Windows lifecycle safety regression | Six offline tests pass: approval required for start, correct managed identity/profile/region, already-running/stopped idempotence, graceful SOFTSTOP, read-only status. **Not live OCI or RDP tests** |
| Secret scan | Gitleaks redacted scan of new delivery passed; large ignored provider binary excluded. Plaintext credentials, age key and raw billing/inventory are not committed |
| Public ingress review | New public NSG game rule is TCP/25565 only. No new public SSH/RDP/API ingress. Existing public SSH remains until a verified route/recovery path; final lockdown is NOT claimed |
| Spending read | Usage API currently reports zero EUR computed cost for Compute, Block Storage, VCN. OneSubscription separately confirms €250 available, €0 used and expiry November 21 at 23:59:59 UTC; usage/balance may lag |

Provider/backend diagnostics and raw plans contain infrastructure details and remain outside Git. The real root keeps the secure OCI backend; the temporary diagnostic copy is neither a second maintained environment nor an approved deployment path. Only a sanitized import summary is committed. Remote state must be initialized in the real root and safe plans regenerated after prerequisites are resolved.

## Deployment and unresolved prerequisites

Nothing in this delivery has been deployed. No Terraform apply, authoritative state import, paid upload, image import, resource cleanup, guest provisioning, Argo sync or merge was performed. OCI access remained read-only. Authorized destructive Windows preparation was limited to disposable local clones; the original MPMB VM was resumed from managed-save. Kubernetes checks were dry-runs.

1. **Thor access migration/recovery**: the Bitwarden agent identity was recovered and read-only guest/data inventory succeeded with sudo. Docker/containerd/Tailscale versions, root UUID, ample resources and absence of game containers/data were checked. SSH currently listens only on its tailnet IP; private listener, router advertisement/grants, persistent firewall and OCI console recovery remain pending. An age-encrypted configuration/access backup was captured outside Git before migration. `bootstrap-router.yaml` preserves the tailnet listener while preparing private SSH. No live host change was made.
2. **Windows 11 OCI image/security/boot-volume path**: local MPMB Windows 11 Pro source was inspected and a hash-verified 80 GiB offline-checkpoint clone passed `qemu-img check`. Current source guest reports TPM2 and Secure Boot enabled; installer bypass flags are also present. Old staged storage drivers produced Code 52 and failed boot on the clone. Updated signed VirtIO 0.1.302 drivers now boot with Secure Boot and TPM enabled. The Windows 11-specific Oracle guide documents UEFI/Secure Boot custom-image preparation, conflicting with generic shielded restrictions; actual image/E4 compatibility still needs approved testing. Its import guide says 256 GB but its linked boot-volume guide says the image default or 50 GB for current images, so the earlier hard 256 GB claim is withdrawn. Keep 100 GB and verify the actual imported-image minimum. Source acquisition, clone sanitization and generalization are complete. OCI import and live private RDP remain pending approval. No source VM mutation, security bypass or allocation substitution was made.
3. **State/backup/IAM bootstrap**: namespace eventually recovered as axh0rk0bydbu; root and Ymir bucket lists are empty. Need approved private versioned state bucket plus bucket-scoped operator identities. State-bucket creation/storage and subsequent backup/image storage require approval. Default-domain Administrators membership and its matching root all-resources policy are now verified through read-only SCIM queries; no further user credential is needed on that evidence. OCI agent Run Command remains unavailable, but native SSH already works.
4. **Billing resolved for current term:** authenticated subscription discovery confirms €250 available, €0 used, promotion expiry November 21 at 23:59:59 UTC / November 22 at 02:59:59 Riyadh, and account-specific A1 3000 OCPU-hour / 18000 GB-hour free tiers. Native EUR paid rates are corroborated by the account rate card. Recalculate actual start/image/traffic costs before approval and recheck rates at term rollover. No further billing information is currently requested from the user.
5. **Tailnet policy, routes, DNS and certificates**: the user confirms the current policy is allow-all. A concrete restrictive IPv4 policy with observed identities/subnets and embedded accept/deny tests is now prepared at `ansible/tailscale/policy.hujson`. Control-plane validation passes all 13 tests through Terraform; applying the policy still needs approval. Neither homelab host currently accepts routes. Private DNS, TLS renewal, callback proxy, pod route tests and VNIC additive NSGs remain to be deployed/verified.
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

Image upload/import is a separate billable approval stage that precedes the complete launch plan. Review the finalized image digest, bounded storage estimate and state-bucket bootstrap first; after API compatibility acceptance, regenerate and review the full compute plan. Obtain separate explicit approval for access-cutting/destructive cleanup and any requirements change. Do not merge this draft PR without the user's explicit instruction.

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

1. **Windows image/deployment approval:** no source media or hosting decision is currently needed. Oracle’s Windows 11-specific guide supplies a candidate UEFI/Secure Boot custom-image workflow; generic documentation conflicts, so actual image capability acceptance and E4 boot still need testing after an approved import. Local clone sanitization/generalization are complete; approved image import and first launch establish actual OCI compatibility. No size increase or security bypass is requested.
2. **Credits:** no additional information is needed now: account API discovery confirms the unused €250 promotion, actual expiry and A1 free tiers. The agent will include the expiry-limited cost forecast in the concrete deployment approval. Continuing PAYG operation after expiry needs an explicit funding/duration decision.
3. **Tailnet administration:** the supplied OAuth credential now validates the reviewed policy through Terraform. Approve its reviewed replacement of the existing allow-all policy; route approval is a separate admin operation after the router advertises the two required subnets. Existing OCI and Bitwarden credentials work; no new private SSH key is needed.
4. **Deployment approval:** after these decisions, approve the concrete saved plans for private versioned state-bucket bootstrap, safe imports/access migration and billable resources/image storage. The agent can prepare and execute the technical steps; the user need not manually create VMs, certificates or the Panel. Billable applies, access-cutting changes, cleanup and merging remain withheld until the applicable explicit approvals.

## Windows disk reduction — 2026-10-28

User-authorized planned Windows boot capacity is now 100 GB instead of the original 200 GB. Wings data disks remain 200 GB each; Thor remains unchanged. Direct official USD/EUR tariffs give $4.25 / €3.95 monthly savings and a conditional baseline of $247.76 USD list / €230.42 EUR list; the earlier €222.55 spot-converted estimate is superseded, with 850 GB paid instance storage. Terraform formatting/validation and estimator consistency checks pass. This changes configuration only; no local disk resize, OCI apply or billable action occurred.

## Concrete tailnet policy — user-requested hardening

The example with placeholders has been replaced by `ansible/tailscale/policy.hujson`. Admin clients are the observed laptop and freyr; servers get only the required API/metrics/callback paths, and other members/owner devices receive no infrastructure grant. Router host-firewall admin sources match. Thirteen embedded Tailscale accept/deny tests cover admin access, service paths, denied lateral administration and non-admin devices. Local JSON/selector/port structure checks pass; official control-plane evaluation now passes; live routed connectivity remains pending. No live policy, route approval or host change was made.


## Local Windows clone verification — 2026-10-29

With explicit permission, MPMB was managed-saved, the isolated clone was tested, then MPMB resumed from saved RAM. Its original Acrobat desktop remained open and its guest agent responded after resume. Only clone disks/NVRAM/TPM and disposable test media were modified. No source shutdown, sysprep or storage resize was performed.

The clone independently booted its sole 80 GiB system disk through VirtIO with a VirtIO NIC, TPM ready and Secure Boot enabled. SSH over isolated localhost port 2223 succeeded. Old driver Code 52 was fixed by installing catalog-verified VirtIO-Win 0.1.302 packages; no signature/Secure Boot bypass was used. `install-virtio.ps1` passed the Windows PowerShell parser; extraction and all Windows shell scripts passed ShellCheck. The clone was shut down afterward. The clone was subsequently sanitized and generalized; the finalized image has its own validation evidence.

Offline post-import configuration checks pass for fresh schema creation, existing-schema reuse/preservation (including CLI response/input key conversion) and rejection of an oversized image before mutation. Installed OCI CLI help and provider/SDK schema were inspected. No metadata write, image upload/import, OCI boot or private RDP test occurred.


## Second CodeRabbit review

Fixed all five new findings in separate commits: restart Wings after CA rotation only after its unit exists; reconcile generated routes in existing operator inventory; require the approved final image SHA256; handle the OCI CLI object-list `data` array and missing empty data; and put Windows OS metadata inside the supported image-source details. The exact import invocation passes the installed CLI parser using offline skeleton generation. Retry regression fixtures now match the actual CLI response shape, checked against its installed implementation. Inventory preservation/reconciliation and production Ansible lint pass. No OCI writes occurred.

The native EUR tariff was independently retrieved and now drives credit-consumption estimates: €230.42 conditional baseline, €19.58 remaining from a full €250 after 730 hours, about 33.00 days. USD spot conversion remains a labelled comparison, not the EUR billing estimate. The smaller disputed A1 allowance raises the baseline to €255.51 before images/other costs; do not apply that over-budget scenario without an approved change.


## Billing discovery resolved — 2026-10-29

The classic numeric subscription ID works with OneSubscription list APIs. Direct response evidence confirms the separate B88385 promotional service has €250 available / €0 used and ends November 21 at 23:59:59 UTC. Account-specific A1 tiers are 3000 OCPU-hours / 18000 GB-hours at zero cost for the current term. The earlier unverified-credit and smaller-A1-allowance blockers are superseded by this evidence. Selected non-personal billing facts are in billing-evidence.json; raw responses remain private. `spend-status.py --subscription-id 100001000344740` successfully reproduces the available-credit/expiry check. No billing change or paid operation occurred.


## Tailnet policy Terraform ownership — 2026-10-29

Added the pinned official Tailscale provider 0.29.3 and `tailscale_acl.tailnet` in the existing OCI root, plus an official import block. The resource reads the existing policy before change, validates syntax/tests through the API during planning, prevents destruction and disables default-policy reset on destroy. Provider credentials are file-backed environment settings, not Terraform variables or outputs. No second root or CI writer was introduced. Provider installation, formatting and Terraform validation pass. The user supplied an owner-only OAuth credential with Policy File read/write scope. The isolated targeted plan passes API validation with 13 tests and proposes one import/one update/no adds or destroys. A deliberately forbidden acceptance test was rejected by the control plane, and the valid candidate was restored. The authenticated browser verified the current allow-all policy; its unsaved candidate preview was discarded and no live policy was saved. Native Tailscale SSH is disabled on pos, optiplex and Thor; optiplex was verified over its tailnet IP when LAN SSH was unavailable. The current split-DNS dependency is preserved with a DNS-only member grant.


## Final Windows capture and third review fixes — 2026-10-29

The independent clone was sanitized, Sysprep generalized and shut down. Its copied source profile/private fixtures, SSH keys and installer bypass flags were removed. Free clusters and offline NTFS MFT/directory/log/pagefile/tail data were cleared in disposable copies. The final standalone compressed 80 GiB QCOW2 passed `qemu-img check`. A separate copy booted with fresh Secure Boot firmware and TPM 2.0, VirtIO disk/NIC, completed unattended setup and authenticated the persistent `winlab` administrator over NLA. Correct-password authentication returned 0; a wrong password returned 134. TLS was pinned to the test server certificate. This tests the final sanitized capture locally, not OCI or Tailscale RDP. See [artifact and acceptance evidence](windows-image-validation.json). The original MPMB VM is resumed after testing; the unbooted upload capture remains private.

The third review's functional findings are addressed: projection fields record their starting balance, image schema descriptors specify IMAGE source, schema creation discovers/passes the required global version, and a post-Sysprep `winlab` account is created and locally authenticated. The licensing request was declined under the user's explicit scope. No OCI upload, import or launch occurred.


## State/image bootstrap review

The image source bucket is defined in the same Terraform root, with NoPublicAccess, Standard storage, no redundant object versioning and prevent_destroy. Its isolated diagnostic target plan contains exactly one bucket creation and no imports/updates/deletions or compute/network changes. `image-bucket-plan-summary.json` records the result. The migration guide identifies the finalized image hash, private state/image bucket identities, separate approval stages and a proposed €5 storage/request ceiling before any compute launch; no stage has been applied.

Thor's age-encrypted configuration/access archive was captured outside Git using the existing repository recipient. Decryption and tar integrity were verified through a stream without writing a plaintext archive or age identity. SSH/netplan/Docker/systemd/authorized_keys and Tailscale state are included; this is a configuration recovery backup, not a full disk snapshot. The source was read only.
