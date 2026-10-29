# Existing infrastructure — 2026-10-28

Discovery used the local checkout, `kubectl`, SSH to `pos`/`optiplex`, Tailscale status, OCI CLI 3.95.1 and OCI Python SDK 2.189.0. Raw responses remain in ignored `oci/inventory/`, not in Git. No infrastructure has been removed or resized. Some OCI endpoints returned authentication errors; successful reads and blocked reads are distinguished below.

## Identity, location and permissions

- Tenancy `afbinaskar`: `ocid1.tenancy.oc1..aaaaaaaajtikdhgav7o7uksgc56xmuuvhx56pdunebmt4qlpzlltrkvxvbea`.
- Only subscribed region: `me-riyadh-1`, also the home region. AD: `jRPH:ME-RIYADH-1-AD-1`.
- Accessible compartment `Ymir`: `ocid1.compartment.oc1..aaaaaaaavoznuamfvzwjj2n4ae3xbtgxkskv7kuqexsu4oqp3jxjmrj4proq`.
- Root policy `Tenant Admin Policy`: `ALLOW GROUP Administrators to manage all-resources IN TENANCY`. The classic `ListGroups` API returned HTTP 401 `IdcsConversionError`, but subsequent read-only Identity Domains SCIM queries confirmed that the configured OCI API user is a member of the Default domain Administrators group. The matching root policy grants that group management of all tenancy resources. No permission-policy change is needed on the evidence obtained; write operations remain unexercised until approval.
- Dynamic-group listing later succeeded with no dynamic groups; Identity Domains SCIM membership is now confirmed as Administrators for the configured API user.
- Compute/network/volume/image/shape/limits and usage-cost reads succeeded. OCI Run Command returned 404 `NotAuthorizedOrNotFound`. Initial Object Storage `GetNamespace` calls returned HTTP 401 `NotAuthenticated`; later reads succeeded with namespace `axh0rk0bydbu`, and explicit bucket lists returned empty for root and Ymir. Subscription/OSP reads established EUR billing and PAYG upgraded account status. Initial detailed credit calls returned HTTP 401; retrying OneSubscription with classic numeric subscription ID 100001000344740 succeeded. The subscription list reports B88385 promotion ACTIVE, €250 available and €0 used, with expiry November 21 at 23:59:59 UTC. Its account rate card confirms A1 free tiers of 3000 OCPU-hours / 18000 GB-hours for the current term. Sanitized evidence is in billing-evidence.json; raw billing data remains ignored.
- Organization subscription start: 2026-10-23, end: 2026-11-21T23:59:59.999Z. This is an observed subscription end field, not proof of the credit expiration contract. The user later provided Console details confirming €250 total commitment in EUR, with November 21 shown as renewal and End date blank. This does not establish unused credit or promotional expiry. No payment/address data is committed.

## Compute and storage

| Resource | State | Shape / CPU / RAM | OS / architecture | Storage | Decision |
|---|---|---|---|---|---|
| Thor → logical wings-04 | RUNNING | VM.Standard.A1.Flex / 4 OCPUs / 24 GB | Canonical Ubuntu 26.04 Minimal aarch64 | 100 GB boot, 10 VPUs; no separate block volumes found | Retain and import without resize/rename/reimage |
| Utgard-Loki | TERMINATED before discovery | VM.Standard.A1.Flex / 4 OCPUs / 24 GB | Same platform image | 50 GB boot also TERMINATED | Historical record; no deletion action |

Thor instance OCID: `ocid1.instance.oc1.me-riyadh-1.anqwuljrcxr7q4yceguaprmui5mfmmyk3t3sznfxlinck3p2bcz3y6krpgaq`.

Thor boot volume: `ocid1.bootvolume.oc1.me-riyadh-1.abqwuljruatmalgpfpro2ov5firdjn53exqjn6mv2e4z2gakty5gkbjdvbpa`. Existing boot attachment is ATTACHED; volume AVAILABLE. The boot volume carries `orcl-cloud.free-tier-retained=true`; this alone does not establish compute/free-tier entitlement for every future billing period. Preserve its 100 GB and current VPUs.

Image: `ocid1.image.oc1.me-riyadh-1.aaaaaaaas6b6g7oq4dylol5jwv252dk2jjphtpbrswe3coadkhmqrwxtdm5q`, `Canonical-Ubuntu-26.04-Minimal-aarch64-2026.08.17-0`. Firmware UEFI64, paravirtualized boot/network; IMDS legacy endpoints disabled.

Thor guest inventory subsequently succeeded through the Bitwarden agent using the user-confirmed fingerprint `SHA256:2fArxE1VX5fSceDUZt37ZXIYBAB9rsPKGuRdbwXwVAo`, account `ubuntu`, tailnet IP 100.89.233.80. The calling shell had selected an empty system agent; explicitly selecting the Bitwarden Flatpak socket fixed authentication without changing any guest key. Passwordless sudo works. Private key material remained in Bitwarden; only an ignored public-key selector was saved locally.

Read-only findings: Ubuntu 26.04.1 LTS, aarch64; ~23 GiB available RAM, no swap; `/dev/sda1` ext4 root UUID `7045f85b-12db-48df-827b-eb38d90e931e`, 96 GiB filesystem, 2.5 GiB used / 94 GiB available. Existing `/boot` and EFI partitions remain unchanged. Docker CE 29.9.2 and containerd.io 2.4.2-3 already match the selected versions, native arm64, Docker root `/var/lib/docker` and containerd root `/var/lib/containerd`. Zero containers and volumes; one hello-world image. No `/etc/pelican` or `/var/lib/pelican` found. `/home` is 64 KiB, `/srv` 4 KiB, `/opt` 16 KiB; no game data found in these inspected locations. Preserve both users' SSH access, system/network configuration and `/var/lib/tailscale` state; no backup has yet been taken.

Tailscale 1.104.4 and Docker are enabled/active; Wings is absent. IPv4 forwarding is already 1, route acceptance true, subnet SNAT enabled, no advertised routes or tags. Interface is `enp0s6`; Docker bridge 172.17.0.0/16. Resources are adequate for the proposed router, pending actual routed traffic tests.

**Access migration detail:** SSH is socket-activated and explicitly bound only to `100.89.233.80` by `/etc/ssh/sshd_config.d/70-tailscale-only.conf`. Password and keyboard-interactive authentication are disabled. There is currently no listener on 10.10.50.10. UFW denies incoming/routed traffic except tailscale0, and OCI-image iptables chains contain earlier ACCEPT/REJECT rules. `bootstrap-router.yaml` adds a private VCN listener while retaining the existing tailnet listener and a persistent tailscale0 private-SSH rule; do not just switch the inventory to private IP first. The callback proxy needs an explicit private :443 host ACCEPT before the existing REJECT, now included in the router firewall template. These changes are implemented but have not been applied. OCI serial-console recovery remains untested.

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

E4 advertises secure/measured boot and TPM options. Oracle’s [Windows 11 image workflow](https://docs.oracle.com/en-us/iaas/secure-desktops/windows-image.htm) explicitly describes UEFI custom images, Windows11 OS metadata, Secure Boot image capabilities and shielded instances, and recommends a manual Compute-instance test. This conflicts with the [generic shielded-instance restrictions](https://docs.oracle.com/en-us/iaas/Content/Compute/References/shielded-instances.htm), which exclude custom images. Therefore a documented candidate workflow exists; do not treat Windows 11 as impossible or require a hosting change. Actual custom-image capability acceptance and E4 boot/TPM/RDP verification remain pending approved image import and launch. No security bypass or Windows Server substitution is included.


## Existing Windows image source — follow-up discovery

The user authorized reuse of the local MPMB VM. `qemu:///session` contains running `mpmb-windows11`; its live system disk is `/home/azoz-laptop/VirtualMachines/mpmb-windows11/system.qcow2`, an 80 GiB QCOW2 (approximately 33 GiB allocated). The VM currently has 4 vCPUs / 4 GiB RAM, UEFI Secure Boot firmware, TPM-CRB backed by a TPM2 emulator, a SATA disk and e1000e networking. The running reference VM, its firmware/TPM state, and its MPMB files were not modified.

Read-only SSH inspection through localhost:2222 confirmed **Windows 11 Pro, build 26200, x64**, GPT system disk, NTFS C:, BitLocker fully decrypted/protection off. Windows reports TPM present/ready/enabled/activated, SpecVersion 2.0, and `Confirm-SecureBootUEFI=True`. Installer registry overrides `BypassTPMCheck`, `BypassSecureBootCheck`, `BypassRAMCheck`, `BypassCPUCheck` are 1. Those prior installer flags do not mean the current guest lacks TPM/Secure Boot, and they are not adopted as a new deployment workaround. Current guest driver store contains Red Hat viostor, vioscsi, NetKVM, vioser, balloon, RNG and display drivers; a clone boot on paravirtualized storage/network is still required to prove operational compatibility. The offline checkpoint can differ from the currently running guest, so repeat guest checks on a preparation clone before importing.

A retained clean offline checkpoint `candidate-p3-4g-1793001620` was used instead of copying the live disk. `windows/clone-checkpoint.py` verified its recorded SHA256, cloned its standalone disk using a local Btrfs reflink, and ran `qemu-img check` successfully. The local candidate is at ignored `oci/windows/work/mpmb-source.qcow2`, virtual capacity **85,899,345,920 bytes (80 GiB)**, with an ignored provenance report alongside it. No source VM stop, snapshot, restore, sysprep, live-disk copy or OCI upload was performed. This is an **unprepared local source clone**, not a generalized or OCI-booted image. Before export, sanitize only the disposable clone: remove MPMB private/paid fixtures and unrelated user data/access, remove unneeded installer overrides, verify signed drivers and guest security, provision new credentials, generalize, and cleanly shut down. Never sanitize/generalize the reference VM itself.

Oracle's [Windows import guide](https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/importingcustomimagewindows.htm) states a 256 GB minimum and BIOS/MBR preparation, but the linked [boot-volume guide](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumes.htm#Custom) says current Linux/Windows custom volumes use the image default or 50 GB (whichever is higher), with 256 GB specifically for older Windows platform images / Server 2012 R2. These sources conflict. The earlier claim that 200 GB is definitely blocked was too strong: no OCI image import or launch has tested it. Keep the requested 100 GB; the local source is only 80 GiB, and the actual imported-image minimum/firmware capabilities must be verified after an approved import. No increase is requested solely on the older import-guide wording. The custom-image TPM restriction remains an independent unresolved issue.
