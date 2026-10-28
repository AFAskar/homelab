# Existing infrastructure — 2026-10-28

Discovery used the local checkout, `kubectl`, SSH to `pos`/`optiplex`, Tailscale status, OCI CLI 3.95.1 and OCI Python SDK 2.189.0. Raw responses remain in ignored `oci/inventory/`, not in Git. No infrastructure has been removed or resized. Some OCI endpoints returned authentication errors; successful reads and blocked reads are distinguished below.

## Identity, location and permissions

- Tenancy `afbinaskar`: `ocid1.tenancy.oc1..aaaaaaaajtikdhgav7o7uksgc56xmuuvhx56pdunebmt4qlpzlltrkvxvbea`.
- Only subscribed region: `me-riyadh-1`, also the home region. AD: `jRPH:ME-RIYADH-1-AD-1`.
- Accessible compartment `Ymir`: `ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq`.
- Root policy `Tenant Admin Policy`: `ALLOW GROUP Administrators to manage all-resources IN TENANCY`. API-user group membership could not be established: `ListGroups` returned HTTP 401 `IdcsConversionError: Client is unauthorized`. Do not infer write permission from the policy's existence.
- Dynamic-group listing later succeeded with no dynamic groups; identity-domain user/group membership remains unresolved.
- Compute/network/volume/image/shape/limits and usage-cost reads succeeded. OCI Run Command returned 404 `NotAuthorizedOrNotFound`. Initial Object Storage `GetNamespace` calls returned HTTP 401 `NotAuthenticated`; later reads succeeded with namespace `axh0rk0bydbu`, and explicit bucket lists returned empty for root and Ymir. Subscription/OSP reads established EUR billing and PAYG upgraded account status. Detailed subscription credits/usage-ledger calls returned HTTP 401; actual remaining credit is unverified.
- Organization subscription start: 2026-10-23, end: 2026-11-21T23:59:59.999Z. This is an observed subscription end field, not proof of the credit expiration contract. Verify promotion details in the Console. No payment/address data is committed.

## Compute and storage

| Resource | State | Shape / CPU / RAM | OS / architecture | Storage | Decision |
|---|---|---|---|---|---|
| Thor → logical wings-04 | RUNNING | VM.Standard.A1.Flex / 4 OCPUs / 24 GB | Canonical Ubuntu 26.04 Minimal aarch64 | 100 GB boot, 10 VPUs; no separate block volumes found | Retain and import without resize/rename/reimage |
| Utgard-Loki | TERMINATED before discovery | VM.Standard.A1.Flex / 4 OCPUs / 24 GB | Same platform image | 50 GB boot also TERMINATED | Historical record; no deletion action |

Thor instance OCID: `ocid1.instance.oc1.me-riyadh-1.anqwuljrcxr7q4yceguaprmui5mfmmyk3t3sznfxlinck3p2bcz3y6krpgaq`.

Thor boot volume: `ocid1.bootvolume.oc1.me-riyadh-1.abqwuljruatmalgpfpro2ov5firdjn53exqjn6mv2e4z2gakty5gkbjdvbpa`. Existing boot attachment is ATTACHED; volume AVAILABLE. The boot volume carries `orcl-cloud.free-tier-retained=true`; this alone does not establish compute/free-tier entitlement for every future billing period. Preserve its 100 GB and current VPUs.

Image: `ocid1.image.oc1.me-riyadh-1.aaaaaaaas6b6g7oq4dylol5jwv252dk2jjphtpbrswe3coadkhmqrwxtdm5q`, `Canonical-Ubuntu-26.04-Minimal-aarch64-2026.08.17-0`. Firmware UEFI64, paravirtualized boot/network; IMDS legacy endpoints disabled.

Thor's guest data, filesystem layout, Docker conflicts, host firewall, effective services, sudo and recovery access remain **unverified**. SSH `ubuntu@100.89.233.80` rejected available identities; none of the local public keys matches launch metadata. Run Command fallback was denied. No packages or firewall changes were attempted on Thor. Do not mark its data review complete until a working guest identity is supplied.

## Network dependency graph

| Resource | CIDR / address | OCID suffix / decision |
|---|---|---|
| Jotunheim VCN | 10.10.0.0/16 | `…emok7wuydq`; retain/import |
| public subnet-Jotunheim | 10.10.50.0/24 | `…oyg2kc7efq`; Wings + existing router; retain/import |
| private subnet-Jotunheim | 10.10.10.0/24 | `…22h3lk4qva`; Windows; retain/import |
| Thor primary VNIC | private 10.10.50.10, public 84.13.136.92 | `…o72dg3nja`; retain, no NSGs currently |
| Internet gateway | public default route 0.0.0.0/0 | `…n5wvqxda`; retain/import |
| NAT gateway | 84.13.133.208 | `…ed7ndqna`; private default route; retain/import |
| Service gateway | all-ruh-services-in-oracle-services-network | `…33ddvfa`; private service route; retain/import |
| Two route tables / security lists | public and private subnets | retain/import; exact OCIDs in Terraform import blocks |

The public subnet's default security list currently allows TCP/22 from **0.0.0.0/0**. The private list permits SSH from the entire VCN. Both include ICMP path-MTU/unreachable rules and outbound access. No NSGs were returned. Regional public-IP listing found the NAT IP; Thor's public IP is separately verified from its VNIC. Do not delete the NAT, service gateway, IGW, public IPs, routes, DHCP or security lists as “unused.” Windows and Wings depend on them.

The preservation imports freeze shared settings except security-list rules: `private_access_verified=false` retains exact observed rules; switching it to true scopes SSH to `10.10.50.10/32` **only after route verification**. NSGs are additive and cannot cancel broad security-list allows. No public RDP rule was found. Apply final lockdown before paid Wings launch. Existing DHCP/default network objects remain referenced rather than individually managed; their removal is forbidden while dependent resources remain.

No independently attached block volumes were found in either compartment. Initial namespace queries failed, but later authenticated calls recovered namespace `axh0rk0bydbu` and returned zero buckets in root and Ymir. No existing state or backup bucket was found; bootstrap requires approval. Retain any later-discovered object dependencies pending review. No deletion candidate is approved.

## Homelab and tailnet

Both k3s nodes Ready: `pos` 192.168.1.28 / 100.114.113.82 (AlmaLinux 10.2), `optiplex` 192.168.1.27 / 100.77.7.115 (Alpine 3.24, use doas). Cluster version v1.36.2+k3s1. Pod CIDRs 10.42.0.0/24 and 10.42.1.0/24; Services observed in 10.43.0.0/16. Storage: local-path RWO, Delete reclaim, no expansion. Existing Prometheus stack, Traefik and homelab-ca issuer are healthy.

Thor is online in the tailnet at 100.89.233.80. No OCI subnet route is advertised in the observed peer list. Existing 192.168.1.0/24 route belongs to an offline Windows peer; neither Kubernetes node accepts subnet routes. OCI subnets do not overlap observed LAN/pod/service/tailnet/Docker ranges; check any unseen remote sites before advertisement. Do not advertise the whole 10.10/16 by default.

## Availability, quota and compatibility

OCI ListShapes returned E6.Flex and E4.Flex in Riyadh. Resource availability reported E6: 83 OCPUs / 1250 GB available, E4: 100 OCPUs / 1666 GB, A1: used 4 / 24 GB. These exceed the requested 6 E6 OCPUs / 48 GB and 2 E4 OCPUs / 16 GB. Quota headroom does not reserve launch capacity. No compartment quotas returned. Block-storage limits report 61,440 GB/AD and 10,000 volumes, with 200 GB free-storage limits; Object Storage reports 10,000 buckets. Actual available storage headroom, custom-image count and launch capacity still require deployment preflight.

Ubuntu E6-compatible image selected: `ocid1.image.oc1.me-riyadh-1.aaaaaaaaacwhx5w63nxioye4qlniyr7yfaeunzu6tv352anqqvwfznzzlqba` (`Canonical-Ubuntu-26.04-2026.10.27-0`). GetImageShapeCompatibilityEntry explicitly returned E6.Flex. Docker's signed-package indices contain CE `5:29.9.2-1~ubuntu.26.04~resolute` and containerd `2.4.2-3~ubuntu.26.04~resolute` for both amd64 and arm64; those versions are in the example inventory. Guest install/run remains untested.

E4 shape advertises secure/measured boot and TPM options. However [OCI shielded-instance restrictions](https://docs.oracle.com/en-us/iaas/Content/Compute/References/shielded-instances.htm) explicitly exclude custom images, and [Windows 11 requires TPM2 and UEFI](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements). A supported Windows 11 custom-image launch path is not established. This is an image/security capability blocker, not a missing-image shortcut or evidence that E4 CPUs cannot run Windows. No security requirement bypass or Windows Server substitution is included.
