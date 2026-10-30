# Validation and acceptance

## Current status — October 30, 2026

The user approved the non-Windows deployment and access migration. That stage
is deployed. Windows is required but remains blocked by Oracle's regular
Compute Secure Boot/TPM support question. No Windows VM has been launched;
merge, destructive cleanup and Windows launch remain unapproved.

Generated reports, plans, billing snapshots and raw logs stay in ignored
`oci/inventory/`, with reports under `oci/inventory/reports/`. They are local
run artifacts, not source configuration or substitutes for fresh checks.
No secrets, raw state, images or decrypted manifest builds belong in Git.

## Deployed and verified

| Area | Evidence and limits |
|---|---|
| Retained OCI resources | 12 authoritative imports; import apply added/changed/destroyed nothing. Thor remains A1 ARM64 4 OCPUs/24 GB/100 GB, with original storage and direct tailnet SSH preserved. Shared networking retained |
| Paid Linux | Three Ubuntu 26.04 E6.Flex nodes at exactly 2 OCPUs/16 GB, 50 GB boot + 200 GB data each. Data mounted ext4 by UUID; initialization disabled after the new disks were prepared |
| State and plans | Real private versioned OCI backend works. Non-Windows targeted reconciliation reported no changes. Full-root planning correctly fails the Windows compatibility precondition; a clean full environment plan is not claimed |
| Private access | Fresh private SSH to all four nodes passed. Thor's two advertised OCI subnet routes are approved, SNAT/forwarding persist, and pos/optiplex accept routes with scoped pod SNAT. Pod TLS reachability passed from both Kubernetes hosts |
| Tailnet policy | Restricted grants applied and API-validated with 13 embedded tests. Administrator sources, node API/metrics, DNS and callback paths are explicit; allow-all removed. Native Tailscale SSH is not used |
| Callback isolation | Thor reaches pos:8443 only. Dedicated Traefik routing permits the Panel hostname and `/api/remote/…`; all four node-token requests returned 200, missing credentials 401, unrelated hosts/paths and traversal probes 404. Thor's shared pos:443/:80 and alternate NodePort connections were denied. LAN callback/NodePort probes were blocked. See [callback security](callback-security.md) |
| Public ingress | All four games answered public TCP and real Mindustry UDP discovery. Public 22/2022/3389/8080/9100 probes were blocked. OCI security lists no longer allow world SSH; Docker forwarding rules enforce selected game ports. Interactive player gameplay is not claimed |
| Panel | Official pinned rc.2 image deployed in existing k3s, SQLite/file sessions/database queue. Queue worker and supercronic were RUNNING. PVC is Bound on optiplex with PV reclaim Retain; no HA replication is claimed. Four enrolled nodes responded to authenticated Panel management requests |
| TLS | Panel, four Wings endpoints and callback proxy use the existing homelab PKI. Six Certificates Ready; leaf chain/SAN/key/expiry validated. No extra root CA or CA private-key export. Browser console/WebSocket round trip passed |
| Wings/games | Docker and pinned native Wings services enabled on all four. Pinned Mindustry v160.7 workloads run with amd64 runtimes on E6 and arm64 on Thor; no emulation. All four hosts rebooted successfully, retaining data markers, paid UUID mounts and restarted services/games |
| Idempotence | All-four Wings provisioning rerun changed zero resources. DNS rerun changed zero. Callback firewall on both hosts and router proxy rerun changed zero. Panel helper rerun preserved administrator credentials and node tokens |
| Backups | Selected four-game/Panel capture encrypted, uploaded to private Object Storage, downloaded, hash-checked and decrypted into new directories. Inner checksums, SQLite integrity, APP_KEY and four saved worlds/pinned game binaries verified. Games resumed. Panel-only capture also retested. No complete host-loss recovery or recurring scheduler is claimed |
| Monitoring/budgets | Existing Prometheus observed four exporters, four active Wings services and four public TCP probes healthy. Small blackbox exporter runs in existing k3s, not another OCI VM. Native EUR actual-spend alerts at 200/225/240 accepted. Alert delivery has not been triggered/tested; alerts are not spending caps |

## Code checks

- Terraform fmt and validate pass on the sole `oci/terraform/` root. Backend
  initialization and pinned provider installation previously passed. Fresh
  game-rule and final-policy targeted plans reported no changes; these are
  scoped staged checks, not full-root acceptance.
- Panel, Argo and Traefik Kustomize/KSOPS builds pass with the authorized age
  identity kept in memory. Panel build: Kubeconform 12 valid, zero invalid or
  errors, 10 missing CRD schemas skipped; Argo: 57 valid, zero invalid/errors,
  four skipped. API server dry runs validate the custom resources too.
  Argo's large CRD exceeds client-side last-applied annotation limits, so its
  successful dry run uses server-side apply; no Argo installation was applied.
- Ansible production-profile lint, relevant syntax checks, Python compilation,
  ShellCheck and redacted secret scans pass. New Panel directory/error and
  forced-timeout paths were checked in isolation; real helper rerun passes.
- Local Windows image/import/lifecycle regression checks previously passed.
  They do not establish OCI Windows launch/RDP acceptance.

## Windows and remaining approvals

The approved state/image stage completed: one sanitized 17,315,330,048-byte
source upload, SHA256
`c74d180aefb54a0e02c45bc4a16c2ab2403b6cbb32332675c9882edcf52a7881`, and an
AVAILABLE Windows/Windows11 image of 81,920 MB. Candidate E4 compatibility and
UEFI/Secure Boot schema settings were accepted and read back. The original
MPMB VM is preserved and running; local tests used separate clones.

Oracle's [regular Compute image-capability reference](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/configuringimagecapabilities.htm)
excludes custom-image Secure Boot, while its
[Secure Desktops Windows guide](https://docs.oracle.com/en-us/iaas/secure-desktops/windows-image.htm)
enables shielded desktop-pool instances. API acceptance is not technical
confirmation for the exact regular E4/Windows 11/Secure Boot/TPM configuration.
Keep `windows_compatibility_verified=false`, the 2 OCPU/16 GB/100 GB allocation,
and the security requirements intact. Do not silently change service or OS.

[Oracle SR 4-0004170294](https://support.oracle.com/support/?SR=4-0004170294&page=sptemplate&sptemplate=sr-activities)
was last verified Operations Working, assigned to Kumar Anurag, with an
acknowledgement but no technical answer or requested customer action. This
is a last-observed status, not an assertion of continuous portal monitoring.
After technical confirmation, prepare and review a Windows launch plan and
obtain separate approval. Actual OCI boot, TPM/Secure Boot, private RDP and
start/stop/status tests ending STOPPED remain pending.

Current list-price model is €220.67/month for deployed non-Windows scope,
or €232.88 for the full requested infrastructure, before unmeasured charges;
see [cost assumptions](costs.md). The promotion expires November 21 at
23:59:59 UTC. Recheck usage/balance and funding before continuing beyond it.

No legacy resource deletion is proposed. The exact authorized deletion set
is empty. Merge remains a separate human decision. Post-merge removal of the
narrow Argo revision staging exception is described in callback-security.md.
