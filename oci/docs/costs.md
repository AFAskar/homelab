# Infrastructure costs — 2026-10-28

**Baseline: $247.76 USD list / €230.42 EUR list per 730-hour month. This is a conditional list-price estimate, not verified all-in spending or a credit balance.** Windows is modelled at 120 running hours. Storage persists for the full month including Windows stopped hours. Windows licensing is outside this analysis.

[Machine-readable estimate](cost-estimate.json) and `oci/scripts/estimate-cost.sh` fetch Oracle’s official [USD tariff](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD), [EUR tariff](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=EUR) and [ECB daily XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml). Retrieved October 28 UTC / October 29 Riyadh; both catalogs last updated October 8. **Use the native EUR tariff for this EUR-billed tenancy.** ECB October 28: €1 = $1.1133. Converting the USD list total at that spot rate gives €222.55 for comparison, but that is not the EUR billing estimate. This corrects the earlier €222.55 baseline. The [Oracle price list](https://www.oracle.com/cloud/price-list/) and [E6 announcement](https://blogs.oracle.com/cloud-infrastructure/oci-launches-e6-standard-compute-powered-by-amd) corroborate units. OCPU and vCPU billing are different.

| SKU | Component | USD list rate | EUR list rate |
|---|---|---:|---:|
| B111129 | E6 OCPU-hour | 0.0300 | 0.0279 |
| B111130 | E6 GB-hour RAM | 0.0020 | 0.00186 |
| B93113 | E4 OCPU-hour | 0.0250 | 0.02325 |
| B93114 | E4 GB-hour RAM | 0.0015 | 0.001395 |
| B91961 | Block capacity GB-month | 0.0255 | 0.023715 |
| B91962 | VPU per GB-month | 0.0017 | 0.001581 |
| B91628 | Standard Object Storage GB-month beyond free tiers | 0.0255 | 0.023715 |

Each E6 compute: `(2×0.03 + 16×0.002) × 730 = $67.16`. E4 compute: `(2×0.025 + 16×0.0015) × 120 = $8.88`. Balanced storage: `$0.0255 + 10×0.0017 = $0.0425/GB-month`. The native EUR calculations use the same quantities: each E6 compute is €62.4588, its disk pair €9.88125, E4 compute €8.2584, and Windows boot €3.9525. Each Wings disk pair costs $10.625, Windows boot costs $4.25 in the separate USD tariff. The 850 GB paid total costs **$36.125/month**. Rounded row totals may differ by cents from the unrounded sum.

| Service | USD list/month | EUR list/month |
|---|---:|---:|
| wings-01 compute | 67.16 | 62.46 |
| wings-01 250GB balanced | 10.62 | 9.88 |
| wings-02 compute | 67.16 | 62.46 |
| wings-02 250GB balanced | 10.62 | 9.88 |
| wings-03 compute | 67.16 | 62.46 |
| wings-03 250GB balanced | 10.62 | 9.88 |
| win11 compute | 8.88 | 8.26 |
| win11 100GB balanced, including stopped hours | 4.25 | 3.95 |
| 50GB backups, no free allowance deducted | 1.28 | 1.19 |
| **Baseline total (unrounded inputs)** | **247.76** | **230.42** |

## Existing free resources and unresolved entitlements

Thor's actual allocation is A1 4 OCPUs / 24 GB and 100 GB boot, unchanged. Current Oracle price API SKUs B93297/B93298 show first **3000 OCPU-hours / 18000 GB-hours** at zero, then $0.01/OCPU-hour and $0.0015/GB-hour. At 730 hours Thor uses 2920 OCPU-hours / 17520 GB-hours; at 744 hours, 2976 / 17856. Historical terminated-instance use also shares monthly allowances. Successful Usage API reads currently report zero computed EUR cost for Compute, Block Storage and VCN usage on October 28; billing can lag.

However, the current [Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) states **1500 OCPU-hours / 9000 GB-hours**. This conflicts with the price API. **Account-specific entitlement must be confirmed** before deployment. Do not resize or delete Thor to resolve this discrepancy. At the smaller allowance, continuous 4/24 operation would add `(2920−1500)×0.01 + (17520−9000)×0.0015 = $26.98 / €25.09` per month. Baseline then becomes **$274.74 / €255.51**, exceeding €250 by **€5.51 before image/other costs**. With no applicable compute allowance, Thor compute adds $55.48 / €51.60; any non-free boot storage adds up to $4.25 / €3.95. These are scenarios, not observed invoices.

General free block storage allowance is 200 GB shared across boot and block disks in the home region. Keep Thor's 100 GB free entitlement reserved; **no remaining allowance is deducted from the 850 GB paid estimate** until account usage is confirmed. Do not count the same allowance twice. Standard Object Storage pricing includes a first 10 GB tariff tier and Always Free documentation may provide additional eligible allocation; the estimate conservatively charges all 50 GB pending namespace/usage access.

## Additional infrastructure costs

- Backup bucket: modelled at 50 GB average; no automatic paid snapshots. Retention has no automatic deletion, so unbounded backups will increase costs. Operator reviews a 14-day rolling set, excludes unselected game data, and requests approval before deletion.
- Custom Windows image and uploaded import source **both incur storage**. They are not part of the 850 GB instance disks. At an illustrative 80 GB each (the source virtual capacity), together add $4.08 / €3.79 per full month, raising baseline to **$251.84 / €234.21** (or **€259.30**, €9.30 above budget, with the smaller A1 allowance). The MPMB source is now an 80 GiB virtual / approximately 26.5 GiB allocated local checkpoint clone (the running source currently allocates about 33 GiB); it is unprepared and no OCI custom image exists yet. Final compressed upload/import billable size remains unknown. Temporary download media stays local. Pass measured sizes with `--image-gb` and `--upload-gb`.
- A 31-day month (744 continuous hours) adds $3.864 / €3.59 to paid compute. Recalculate with `--hours 744`. Actual Windows hours are independent of that assumption.
- Existing IGW, NAT and service gateway are reused; no additional router VM, load balancer or paid monitoring host is added. No separate gateway processing fee is modelled; ordinary transfer charges still apply.
- OCI network API tier for Middle East/Africa SKU B93456: first 10240 GB/month outbound is zero, then $0.05/GB. This is shared tenancy use, not 10 TB per VM. Excess 1 TB is $51.20 / €47.62. Regional/cross-region transfer, replication, internet game traffic, backups and existing workloads must be measured. Avoid cross-region state/backups.
- Object requests: B91627 first 50000/month zero, then $0.0034 per 10000. State versions, locks, backup requests and state-bucket storage are extra, normally small but not measured. Taxes/contract adjustments are unverified. `--extra-eur` includes measured EUR charges; `--extra-usd` converts genuinely USD-billed extras at the cited ECB rate.

## Credits, duration and alerts

EUR billing and PAYG upgrade status were verified through OSP/Usage APIs. **€250 EUR is now confirmed as the total commitment by the user-provided OCI subscription details, not as an unused balance.** Detailed credit ledger endpoints returned HTTP 401. PAYG may charge the payment method when credit is exhausted; budgets are not limits.

With a full €250 available, no previous spending and the baseline conditions: **€19.58 remains after 730 hours**, with **33.00 days** at average burn. Including illustrative 80 GB custom + 80 GB source storage: €15.79 remains, about 32.47 days. These are upper-bound durations until actual existing charges, images and traffic are known. No firm exhaustion date is supportable without actual remaining credits and deployment start. For a purely illustrative start of 2026-10-28, baseline arithmetic reaches roughly 2026-11-30; promotion expiry may occur earlier.

[Free-trial terms](https://www.oracle.com/cloud/free/faq/) generally expire credits after 30 days or consumption, whichever occurs first. Earlier API discovery returned an organization subscription end of **2026-11-21 23:59:59.999 UTC / November 22 02:59:59.999 Riyadh**. The user-provided Console summary instead labels November 21 as **renewal**, and its detail view has a blank End date. Neither a renewal date nor that earlier API field establishes promotional-credit expiry. Confirm the actual credit/promotion term before treating it as an expiration deadline; PAYG status alone does not establish credit lifetime.

Terraform creates a tenancy-wide monthly €250 budget in the home region, with ACTUAL ABSOLUTE alerts at **€200, €225, €240**. EUR billing means conversion factor 1. USD accounts must supply a verified dated units-per-EUR value. The API has no currency selector; currency follows billing. A monthly budget resets and does not track a cumulative grant across months. Reconcile daily Usage API totals against the actual promotion balance separately. Notifications may lag and **do not enforce a hard cap**.

If all-in spend exceeds €250, do not apply. Options requiring approval: shorten the evaluation duration, reduce approved Windows hours, revise approved storage/performance choices, or fund additional credits. The requested four continuously running nodes and their allocations remain unchanged in code. Resolving a free-entitlement mismatch requires billing confirmation before considering any resource change.

The Windows import guide's 256 GB statement conflicts with the [current boot-volume rules](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumes.htm#Custom), which use the image default or 50 GB and reserve 256 GB for older Windows images. A 256 GB minimum is therefore not established for this 80 GiB source image. Keep the requested 100 GB; verify imported-image metadata after an approved import. No increase is currently requested. Any later evidence requiring a larger volume must be reviewed before changing the allocation; size changes would not resolve TPM/firmware compatibility.

On 2026-10-28 the user authorized reducing only the proposed Windows boot disk from 200 GB to **100 GB** if worthwhile. At the selected 10 VPU tier, this saves **$4.25 / €3.95 per month**, including stopped hours (€47.43/year at the native EUR tariff). It halves Windows boot-storage cost from $8.50 to $4.25/month and reduces paid instance storage from 950 to **850 GB**. The existing 80 GiB source fits in the proposed 100 GB virtual capacity without shrinking its filesystem; actual OCI imported-image minimum and boot compatibility remain unverified. No existing local or OCI disk has been resized.

User-provided subscription evidence (2026-10-28): subscription 100001000344740, Infrastructure, Active, original/start date October 23, 2026 at 03:00 AST; renewal shown as November 21, 2026; detailed total commitment **€250.00**, currency EUR, End date blank. The copied summary table says €0.00 while the detailed view says €250.00; record the detailed amount as commitment evidence without inferring the reason for the table discrepancy. Credits used/remaining and promotional expiry were not included. This resolves the commitment/currency question, not the unused-balance or free-allowance questions.
