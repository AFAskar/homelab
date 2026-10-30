# Validation and acceptance — 2026-10-29

## Current status

Infrastructure/provisioning/GitOps code is implemented. Local Windows acquisition, sanitization, generalization and isolated first-boot/NLA tests are complete. The user approved **only state/image preparation up to €5**. That stage created private state/image storage, imported the approved Windows disk and configured/read back its image capabilities. **No OCI VM was created or booted.**

- Private Standard `homelab-tfstate`: versioning Enabled; the real OCI Terraform backend initializes successfully.
- Private Standard `homelab-win11-images`: versioning Disabled, Terraform-managed with prevent_destroy. Its authoritative bootstrap apply added exactly one bucket, changed/deleted nothing and imported no retained resource.
- Uploaded source: **17,315,330,048 bytes**, SHA256 metadata matches the approved `c74d180aefb54a0e02c45bc4a16c2ab2403b6cbb32332675c9882edcf52a7881`.
- OCI image: **AVAILABLE**, OS **Windows / Windows11**, **81,920 MB**, PARAVIRTUALIZED. E4 compatibility entry and image UEFI/Secure Boot capability configuration were accepted and read back. Actual API evidence (local report: `oci/inventory/reports/windows-oci-import.json`).
- The first CreateImage call rejected Windows11 source-version metadata. The corrected importer reused the completed upload, imported without OS metadata, then successfully updated Windows/Windows11 after availability, following Oracle's documented sequence. No second upload or duplicate image was created.
- `windows_compatibility_verified`, `discovery_reviewed` and `private_access_verified` remain false. No retained-resource authoritative import, compute deployment, live tailnet-policy change, OCI guest provisioning, Argo sync, cleanup or merge occurred.

Image metadata acceptance does **not** establish a supported regular Compute Secure Boot launch or successful Windows boot/RDP. The regular Compute restriction below remains unresolved.

## Checks executed

| Check | Result and limit |
|---|---|
| Terraform fmt/init/validate | Pass on the actual `oci/terraform/` root, pinned OCI 9.11.0 and Tailscale 0.29.3 providers. Remote OCI backend initialization also passes after approved bootstrap |
| Preservation diagnostic plan | **12 imports, 0 additions/changes/deletions**; every retained-resource action is no-op. Private diagnostic copy used because state bootstrap had not happened then. Summary (local report: `oci/inventory/reports/import-plan-summary.json`). No retained-resource import applied |
| Image bucket | Diagnostic and real-backend plans verified exactly one private bucket addition; approved apply succeeded. Diagnostic summary (local report: `oci/inventory/reports/image-bucket-plan-summary.json`). A subsequent real-backend targeted bucket reconciliation returns exit 0/no changes. This is not a full environment plan |
| Full deployment gates | Un-targeted diagnostic plans deliberately fail while discovery/Windows gates are false. No approved executable full compute plan exists |
| Tailnet policy | Real API validation passes **13** embedded tests; isolated targeted plan proposes one policy import/update, zero adds/destroys. A deliberately forbidden `pos:2375` acceptance test was rejected. Summary (local report: `oci/inventory/reports/tailscale-plan-summary.json`). Live allow-all policy unchanged |
| OCI preflight | Selected Ubuntu 26.04 x86-64 image is E6-compatible; E6/E4 quota headroom checked. Capacity is not reserved |
| Docker packages | Official signed Ubuntu Resolute repositories contain the pinned Docker CE/containerd versions for amd64 and arm64 |
| Kustomize/KSOPS | Argo root and Panel builds pass with the existing authorized SOPS identity; generated public CA matches the sole PKI source |
| Kubernetes validation | Refreshed KSOPS build and API dry run pass with node/proxy Certificates included: Kubeconform 9 valid, 0 invalid/errors, 8 CRD schemas skipped; all 16 namespaced objects admitted in an existing default namespace validation copy. No live Panel deployment or runtime test |
| Ansible | Playbook syntax and production-profile lint pass. Homelab read-only hostname checks pass using retained SSH aliases. Live provisioning/idempotence remains untested |
| Shell/Python/PowerShell | ShellCheck and Python compilation pass. All four delivered PowerShell scripts parse using Windows PowerShell without running preparation on the original VM |
| Local Windows capture | Final standalone compressed 80 GiB QCOW2 passes qemu-img check/hash. A separate copy completes fresh Secure Boot/TPM2 first boot with signed VirtIO disk/NIC; winlab NLA correct password exits 0, wrong password 134. TLS fingerprint pinned. Evidence (local report: `oci/inventory/reports/windows-image-validation.json`). This is not OCI/Tailscale RDP |
| Windows import/configuration | Live import, post-import Windows11 metadata update, candidate schema and E4 entry succeed. Offline cases cover source/object/image reuse, empty list output, checksum rejection, clean OCID stdout, missing global schema, existing-schema preservation and oversized-image rejection |
| Windows lifecycle | Six offline safety checks pass, including start approval, exact managed identity, idempotence and graceful SOFTSTOP. No live OCI start/stop/RDP test |
| Spending | DAILY month-to-date query and subscription lookup succeed. Pagination, separate currencies and null/incomplete totals tested with synthetic rows. Credit projections record their starting balance and an independent 730-hour billing period; zero Wings runtime still includes storage/Windows costs |
| Secrets | Redacted Gitleaks scan of tracked OCI/Panel/AGENTS delivery passes. Credentials, raw inventory, state/plans, age identity and disk images remain ignored |
| Public ingress | New public game rule is TCP/25565 only; no new public SSH/RDP/API rule. Existing public SSH remains until verified private/recovery access; final lockdown is not claimed |

## Non-Windows readiness refresh

The actual-backend staging preview (local report: `oci/inventory/reports/linux-readiness-plan-summary.json`) proposes **13 imports, 28 creates, 1 update, 0 destroys/replacements**. Twelve OCI preservation imports are no-op; the thirteenth is the existing Tailscale policy, which changes to the scoped policy. The 28 creates include two Terraform gate records, three E6 nodes, three 200 GB data volumes and attachments, three NSGs and their rules, one backup bucket and four budget/alert resources. Windows is excluded by explicit resource targeting; its compatibility gate remains false. This exceptional staged preview is not a full environment plan. `discovery_reviewed=true` was supplied for planning only and not persisted; no apply occurred. Refresh/review each stage immediately before its approved execution, especially the tailnet policy.

Fresh preflight confirms Ubuntu 26.04 image compatibility and E6 headroom (83 OCPUs / 1250 GB available against 6 / 48 required) and E4 headroom (100 / 1666 against 2 / 16). Capacity is not reserved. Both Kubernetes nodes are Ready and the existing CA issuer is Ready. Read-only SSH works to pos, optiplex and Thor; actual node/pod/OCI routes do not overlap. Thor retains its tailnet-only SSH listener and no advertised subnets; Kubernetes hosts have not yet enabled route acceptance. Its encrypted recovery archive remains available.

Current OCI usage reports zero EUR charged and €250 available, with the verified November 21 UTC expiry; billing can lag. Refreshed official EUR rates give €232.88/month for the full requested configuration, or **€220.67/month before Windows compute/boot storage**, including the existing image/source objects and 50 GB selected backups. Both exclude unmeasured state/API/egress/tax. This is a runtime estimate, not an approved spending limit or a hard cap.

Separate Wings/proxy leaf Certificates now use the existing cert-manager issuer. The export helper passed valid-chain/SAN/key and private-permission checks with locally generated fixtures, and rejected a mismatched key before replacement. Live issuance/export awaits approved Panel deployment. A registry manifest inspection confirms the official `ghcr.io/pelican-eggs/yolks:java_21` image offers both linux/amd64 and linux/arm64; a compatible Java game egg, native game boot and public connection still require live acceptance.

The non-Windows deployment/access stage has been presented for explicit approval under the original billable-apply restriction. The latest “continue” instruction authorizes continued preparation; it has not been treated as an unspecified billable apply or merger authorization. Execution order: safe retained imports and no-replacement reconciliation; reviewed policy and access recovery; router route/listener setup and approval; private SSH and homelab pod reachability; paid Linux resources; Panel/certificates/proxy/Wings enrollment; private/public game tests, reboot persistence, backups/restores and monitoring; public-admin lockdown only after replacement access is verified. Windows, cleanup and merge remain excluded. Until that approval and live verification occur, the Oracle ticket is **not yet the sole remaining blocker**.

## Preservation and recovery evidence

Thor's actual ARM64 A1 4 OCPU/24 GB/100 GB configuration and working Bitwarden-backed SSH were discovered. Its Docker/Tailscale versions, root filesystem, available capacity and absence of game containers/data were checked. It still listens for SSH on its tailnet address; no guest configuration has been changed.

An age-encrypted configuration/access archive was captured outside Git to the existing recovery recipient. A streamed decryption/tar integrity test passed without writing a plaintext archive or age identity. It contains SSH/netplan/Docker/systemd/authorized_keys and Tailscale state; it is a configuration backup, not a full disk snapshot.

Original MPMB disk/NVRAM/TPM were preserved. With explicit permission it was temporarily managed-saved while disposable clones were tested, then resumed from saved RAM with its Acrobat desktop retained. It is running again. Clone sanitization removed its copied source profile/fixtures and SSH keys, cleared free clusters and offline NTFS metadata, and Sysprep generalized/shut down before capture. No security bypass was introduced.

## Remaining support constraint and prerequisites

Oracle's [regular Compute image-capability reference](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/configuringimagecapabilities.htm) excludes Secure Boot for custom images. The [Secure Desktops Windows guide](https://docs.oracle.com/en-us/iaas/secure-desktops/windows-image.htm) configures shielded **desktop-pool** instances; its manual Compute smoke-test recommendation does not establish a supported regular E4 Secure Boot launch. API acceptance of the image schema/shape entry alone cannot open the Windows gate.

Keep the exact requested shape, 2 OCPUs/16 GB, 100 GB boot and Secure Boot/TPM settings. Before opening `windows_compatibility_verified`, obtain current Oracle documentation or technical support confirmation covering that regular Compute configuration. Otherwise present a supported service/image alternative for separate user approval. Do not silently switch service/OS, disable security checks or resize storage. The 80 GiB image fits within the planned capacity by size; a real launch has not verified the boot-volume minimum.

Oracle Support [SR 4-0004170294](https://support.oracle.com/support/?SR=4-0004170294&page=sptemplate&sptemplate=sr-activities) was created through the authenticated portal on October 29 as OCI Compute General Guidance / severity 4. Kumar Anurag acknowledged it and is reviewing the exact regular E4 / Windows 11 / UEFI / Secure Boot / TPM / 100 GB question. Last verified status: **Operations Working**; no technical confirmation or requested customer action yet. The support API's earlier `403 AUTHZ_FAILED` did not prevent portal submission. No support purchase was made.

Other pending work: reviewed Thor private-listener/router migration and console recovery, route approval, homelab pod routing/TLS/callback deployment, safe retained imports, full launch plan, Panel setup/enrollment, public game tests, backups/restores and monitoring/alert delivery. Existing credentials work; no new private key or Windows source material is requested.

## Costs, approvals and review

Verified subscription evidence records €250 initially unused, expiry **November 21 at 23:59:59 UTC / November 22 at 02:59:59 Riyadh**, and current A1 free tiers covering Thor. Native EUR baseline is €230.42 per 730-hour month with 120 Windows hours and 50 GB backups; conservative image/source storage gives €232.88 before unmeasured state/API/egress/taxes. Billing can lag. Refresh costs/balance at launch approval and recheck rates at term rollover; continuing beyond expiry needs a funding/duration decision. Alerts do not cap spending.

State/image operations only are approved up to €5. Compute launches, live ACL/access changes, retained-resource imports, backup storage, cleanup and merge require their applicable further approvals. No deletion is currently proposed. Full acceptance remains pending: all four Wings online, architecture-compatible games publicly reachable, reboot-persistent services/data, private SSH/RDP through approved subnet routing, public admin ingress removed after recovery checks, live Windows lifecycle tests ending STOPPED, clean full state plan, restore tests and monitoring.

CodeRabbit findings are evaluated individually and fixed in atomic commits where useful. The latest OCID-output/approval-scope finding is fixed with passing fresh/reuse/checksum regressions. This status document now records current import completion rather than mixing historical checkpoints with current prerequisites. The completed review of `4ecaa15` reported no actionable comments. Subsequent certificate automation and readiness documentation require a new review; the prior result does not cover those changes.
