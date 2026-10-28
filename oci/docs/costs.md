# Infrastructure costs — 2026-10-28

**Baseline: $247.76 / €222.55 per 730-hour month. This is a conditional list-price estimate, not verified all-in spending or a credit balance.** Windows is modelled at 120 running hours. Storage persists for the full month including Windows stopped hours. Windows licensing is outside this analysis.

[Machine-readable estimate](cost-estimate.json) and `oci/scripts/estimate-cost.sh` fetch Oracle's official [price API](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD) and [ECB daily XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml). Retrieved 2026-10-28; price catalog last updated 2026-10-08. ECB 2026-10-28: **€1 = $1.1133**, hence USD / 1.1133 = EUR. The [Oracle price list](https://www.oracle.com/cloud/price-list/) and [E6 announcement](https://blogs.oracle.com/cloud-infrastructure/oci-launches-e6-standard-compute-powered-by-amd) corroborate units. Do not confuse vCPU prices with OCPU billing.

| SKU | Component | USD list rate |
|---|---|---:|
| B111129 | E6 OCPU-hour | 0.0300 |
| B111130 | E6 GB-hour RAM | 0.0020 |
| B93113 | E4 OCPU-hour | 0.0250 |
| B93114 | E4 GB-hour RAM | 0.0015 |
| B91961 | Block capacity GB-month | 0.0255 |
| B91962 | VPU per GB-month | 0.0017 |
| B91628 | Standard Object Storage GB-month beyond free tiers | 0.0255 |

Each E6 compute: `(2×0.03 + 16×0.002) × 730 = $67.16`. E4 compute: `(2×0.025 + 16×0.0015) × 120 = $8.88`. Balanced storage: `$0.0255 + 10×0.0017 = $0.0425/GB-month`. Each Wings disk pair costs $10.625, Windows boot costs $4.25. The 850 GB paid total costs **$36.125/month**. Rounded row totals may differ by cents from the unrounded sum.

| Service | USD/month | EUR/month |
|---|---:|---:|
| wings-01 compute | 67.16 | 60.33 |
| wings-01 250GB balanced | 10.62 | 9.54 |
| wings-02 compute | 67.16 | 60.33 |
| wings-02 250GB balanced | 10.62 | 9.54 |
| wings-03 compute | 67.16 | 60.33 |
| wings-03 250GB balanced | 10.62 | 9.54 |
| win11 compute | 8.88 | 7.98 |
| win11 100GB balanced, including stopped hours | 4.25 | 3.82 |
| 50GB backups, no free allowance deducted | 1.28 | 1.15 |
| **Baseline total (unrounded inputs)** | **247.76** | **222.55** |

## Existing free resources and unresolved entitlements

Thor's actual allocation is A1 4 OCPUs / 24 GB and 100 GB boot, unchanged. Current Oracle price API SKUs B93297/B93298 show first **3000 OCPU-hours / 18000 GB-hours** at zero, then $0.01/OCPU-hour and $0.0015/GB-hour. At 730 hours Thor uses 2920 OCPU-hours / 17520 GB-hours; at 744 hours, 2976 / 17856. Historical terminated-instance use also shares monthly allowances. Successful Usage API reads currently report zero computed EUR cost for Compute, Block Storage and VCN usage on October 28; billing can lag.

However, the current [Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) states **1500 OCPU-hours / 9000 GB-hours**. This conflicts with the price API. **Account-specific entitlement must be confirmed** before deployment. Do not resize or delete Thor to resolve this discrepancy. At the smaller allowance, continuous 4/24 operation would add `(2920−1500)×0.01 + (17520−9000)×0.0015 = $26.98 / €24.23` per month. Baseline then becomes **$274.74 / €246.78**, leaving **€3.22 before image/other costs**. With no applicable compute allowance, Thor compute adds $55.48 / €49.83; any non-free boot storage adds up to $4.25 / €3.82. These are scenarios, not observed invoices.

General free block storage allowance is 200 GB shared across boot and block disks in the home region. Keep Thor's 100 GB free entitlement reserved; **no remaining allowance is deducted from the 850 GB paid estimate** until account usage is confirmed. Do not count the same allowance twice. Standard Object Storage pricing includes a first 10 GB tariff tier and Always Free documentation may provide additional eligible allocation; the estimate conservatively charges all 50 GB pending namespace/usage access.

## Additional infrastructure costs

- Backup bucket: modelled at 50 GB average; no automatic paid snapshots. Retention has no automatic deletion, so unbounded backups will increase costs. Operator reviews a 14-day rolling set, excludes unselected game data, and requests approval before deletion.
- Custom Windows image and uploaded import source **both incur storage**. They are not part of the 850 GB instance disks. At an illustrative 80 GB each (the source virtual capacity), together add $4.08 / €3.66 per full month, raising baseline to **$251.84 / €226.21** (or **€250.44**, €0.44 above budget, with the smaller A1 allowance). The MPMB source is now an 80 GiB virtual / approximately 26.5 GiB allocated local checkpoint clone (the running source currently allocates about 33 GiB); it is unprepared and no OCI custom image exists yet. Final compressed upload/import billable size remains unknown. Temporary download media stays local. Pass measured sizes with `--image-gb` and `--upload-gb`.
- A 31-day month (744 continuous hours) adds $3.864 / €3.47 to paid compute. Recalculate with `--hours 744`. Actual Windows hours are independent of that assumption.
- Existing IGW, NAT and service gateway are reused; no additional router VM, load balancer or paid monitoring host is added. No separate gateway processing fee is modelled; ordinary transfer charges still apply.
- OCI network API tier for Middle East/Africa SKU B93456: first 10240 GB/month outbound is zero, then $0.05/GB. This is shared tenancy use, not 10 TB per VM. Excess 1 TB is $51.20 / €45.99. Regional/cross-region transfer, replication, internet game traffic, backups and existing workloads must be measured. Avoid cross-region state/backups.
- Object requests: B91627 first 50000/month zero, then $0.0034 per 10000. State versions, locks, backup requests and state-bucket storage are extra, normally small but not measured. Taxes/contract adjustments are unverified. `--extra-usd` includes measured additional charges.

## Credits, duration and alerts

EUR billing and PAYG upgrade status were verified through OSP/Usage APIs. **€250 is the user's stated available credit, not a retrieved remaining balance.** Detailed credit ledger endpoints returned HTTP 401. PAYG may charge the payment method when credit is exhausted; budgets are not limits.

With a full €250 available, no previous spending and the baseline conditions: **€27.45 remains after 730 hours**, with **34.17 days** at average burn. Including illustrative 80 GB custom + 80 GB source storage: €23.79 remains, about 33.62 days. These are upper-bound durations until actual existing charges, images and traffic are known. No firm exhaustion date is supportable without actual remaining credits and deployment start. For a purely illustrative start of 2026-10-28, baseline arithmetic reaches roughly 2026-12-01; promotion expiry may occur earlier.

[Free-trial terms](https://www.oracle.com/cloud/free/faq/) generally expire credits after 30 days or consumption, whichever occurs first. The observed organization subscription end is **2026-11-21 23:59:59.999 UTC / November 22 02:59:59.999 Riyadh**; this could end usable credit earlier than the consumption estimate. Confirm actual promotion expiry in the Console; PAYG subscription status alone does not establish credit lifetime.

Terraform creates a tenancy-wide monthly €250 budget in the home region, with ACTUAL ABSOLUTE alerts at **€200, €225, €240**. EUR billing means conversion factor 1. USD accounts must supply a verified dated units-per-EUR value. The API has no currency selector; currency follows billing. A monthly budget resets and does not track a cumulative grant across months. Reconcile daily Usage API totals against the actual promotion balance separately. Notifications may lag and **do not enforce a hard cap**.

If all-in spend exceeds €250, do not apply. Options requiring approval: shorten the evaluation duration, reduce approved Windows hours, revise approved storage/performance choices, or fund additional credits. The requested four continuously running nodes and their allocations remain unchanged in code. Resolving a free-entitlement mismatch requires billing confirmation before considering any resource change.

The Windows import guide's 256 GB statement conflicts with the [current boot-volume rules](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumes.htm#Custom), which use the image default or 50 GB and reserve 256 GB for older Windows images. A 256 GB minimum is therefore not established for this 80 GiB source image. Keep the requested 100 GB; verify imported-image metadata after an approved import. No increase is currently requested. Any later evidence requiring a larger volume must be reviewed before changing the allocation; size changes would not resolve TPM/firmware compatibility.

On 2026-10-28 the user authorized reducing only the proposed Windows boot disk from 200 GB to **100 GB** if worthwhile. At the selected 10 VPU tier, this saves **$4.25 / €3.82 per month**, including stopped hours (about €45.81/year at the cited exchange rate). It halves Windows boot-storage cost from $8.50 to $4.25/month and reduces paid instance storage from 950 to **850 GB**. The existing 80 GiB source fits in the proposed 100 GB virtual capacity without shrinking its filesystem; actual OCI imported-image minimum and boot compatibility remain unverified. No existing local or OCI disk has been resized.
