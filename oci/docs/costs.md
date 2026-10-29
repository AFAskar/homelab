# Infrastructure costs — 2026-10-29

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

## Existing free resources and verified subscription rates

Thor's actual allocation is A1 4 OCPUs / 24 GB and 100 GB boot, unchanged. Current Oracle price API SKUs B93297/B93298 show first **3000 OCPU-hours / 18000 GB-hours** at zero, then $0.01/OCPU-hour and $0.0015/GB-hour. At 730 hours Thor uses 2920 OCPU-hours / 17520 GB-hours; at 744 hours, 2976 / 17856. Historical terminated-instance use also shares monthly allowances. Successful Usage API reads currently report zero computed EUR cost for Compute, Block Storage and VCN usage on October 28; billing can lag.

The generic [Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) states 1500 OCPU-hours / 9000 GB-hours, but the authenticated **subscription-specific rate card now resolves this for the current term**: B93297 has a zero-price tier through 3000 OCPU-hours and B93298 through 18000 GB-hours. Their EUR overage rates are €0.0093 and €0.001395. The current rate card is valid through November 21 at 23:59:59 UTC. [Sanitized billing evidence](billing-evidence.json) also corroborates the paid EUR rates. Preserve Thor's 4/24 shape; no resize is needed. Recheck entitlements when the subscription term changes. The earlier smaller-allowance €255.51 baseline was a cautionary scenario and is superseded for this verified current term. Historical terminated-instance use still shares monthly allowances.

General free block storage allowance is 200 GB shared across boot and block disks in the home region. Keep Thor's 100 GB free entitlement reserved; **no remaining allowance is deducted from the 850 GB paid estimate** until account usage is confirmed. Do not count the same allowance twice. Standard Object Storage pricing includes a first 10 GB tariff tier and Always Free documentation may provide additional eligible allocation; the estimate conservatively charges all 50 GB pending namespace/usage access.

## Additional infrastructure costs

- Backup bucket: modelled at 50 GB average; no automatic paid snapshots. Retention has no automatic deletion, so unbounded backups will increase costs. Operator reviews a 14-day rolling set, excludes unselected game data, and requests approval before deletion.
- Custom Windows image and uploaded import source **both incur storage**. They are not part of the 850 GB instance disks. At an illustrative 80 GB each (the source virtual capacity), together add $4.08 / €3.79 per full month, raising baseline to **$251.84 / €234.21**. The MPMB source is now an 80 GiB virtual / approximately 26.5 GiB allocated local checkpoint clone (the running source currently allocates about 33 GiB); it is unprepared and no OCI custom image exists yet. Final compressed upload/import billable size remains unknown. Temporary download media stays local. Pass measured sizes with `--image-gb` and `--upload-gb`.
- A 31-day month (744 continuous hours) adds $3.864 / €3.59 to paid compute. Recalculate with `--hours 744`. Actual Windows hours are independent of that assumption.
- Existing IGW, NAT and service gateway are reused; no additional router VM, load balancer or paid monitoring host is added. No separate gateway processing fee is modelled; ordinary transfer charges still apply.
- OCI network API tier for Middle East/Africa SKU B93456: first 10240 GB/month outbound is zero, then $0.05/GB. This is shared tenancy use, not 10 TB per VM. Excess 1 TB is $51.20 / €47.62. Regional/cross-region transfer, replication, internet game traffic, backups and existing workloads must be measured. Avoid cross-region state/backups.
- Object requests: B91627 first 50000/month zero, then $0.0034 per 10000. State versions, locks, backup requests and state-bucket storage are extra, normally small but not measured. Taxes/contract adjustments are unverified. `--extra-eur` includes measured EUR charges; `--extra-usd` converts genuinely USD-billed extras at the cited ECB rate.

## Credits, duration and alerts

Authenticated OneSubscription discovery on October 29 confirms a separate **Free Oracle Cloud Promotion - Universal Credits** service (B88385): **€250 original credit, €0 used, €250 available, ACTIVE**, ending **2026-11-21 23:59:59 UTC / November 22 at 02:59:59 Riyadh**. The paid Universal Credits service has zero commitment, explaining the Console summary's €0.00 without negating the separate promotion. This is direct subscribed-service evidence, not an inference from a renewal date or reported usage. Raw billing data remains private; [billing-evidence.json](billing-evidence.json) includes only the necessary rates/balance/dates. `spend-status.py --subscription-id 100001000344740` reproduces the balance read using the classic numeric ID, not the organizationssubscription OCID. Detailed get endpoints still returned errors, but the subscription-list response includes the required commitment/promotion data. PAYG may charge the payment method after credit expires; budgets are not limits.

At the 730-hour monthly baseline, €250 arithmetically covers **33.00 days**, leaving **€19.58 after one month**. With illustrative 80 GB custom + 80 GB uploaded source storage it covers about 32.47 days and leaves €15.79. **The actual promotion expires sooner**, regardless of unused balance; do not present those arithmetic durations as the available trial duration.

For a concrete illustrative deployment start of **October 29 at 07:00 Riyadh / 04:00 UTC**, 572 hours remain before expiry (23.83 days). Three E6 nodes continuously running cost €146.82 compute; all paid-instance/50 GB backup storage prorated at 572/730 costs €27.25; conservatively fitting all 120 Windows hours before expiry adds €8.26. Illustrative 80+80 GB image/upload storage adds €2.97. Total to expiry is **€185.31**, leaving approximately **€64.69** before unmeasured state/API/egress/taxes. Recalculate with the actual approval/start time and measured image sizes. Unused promotional credit expires; it does not extend the service term or stop PAYG resources.

Terraform creates a tenancy-wide monthly €250 budget in the home region, with ACTUAL ABSOLUTE alerts at **€200, €225, €240**. EUR billing means conversion factor 1. USD accounts must supply a verified dated units-per-EUR value. The API has no currency selector; currency follows billing. A monthly budget resets and does not track a cumulative grant across months. Reconcile daily Usage API totals against the actual promotion balance separately. Notifications may lag and **do not enforce a hard cap**.

If all-in spend exceeds €250, do not apply. Options requiring approval: shorten the evaluation duration, reduce approved Windows hours, revise approved storage/performance choices, or fund additional credits. The requested four continuously running nodes and their allocations remain unchanged in code. The current account-specific A1 allowance is verified; recheck it at term rollover before extending operation.

The Windows import guide's 256 GB statement conflicts with the [current boot-volume rules](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/bootvolumes.htm#Custom), which use the image default or 50 GB and reserve 256 GB for older Windows images. A 256 GB minimum is therefore not established for this 80 GiB source image. Keep the requested 100 GB; verify imported-image metadata after an approved import. No increase is currently requested. Any later evidence requiring a larger volume must be reviewed before changing the allocation; size changes would not resolve TPM/firmware compatibility.

On 2026-10-28 the user authorized reducing only the proposed Windows boot disk from 200 GB to **100 GB** if worthwhile. At the selected 10 VPU tier, this saves **$4.25 / €3.95 per month**, including stopped hours (€47.43/year at the native EUR tariff). It halves Windows boot-storage cost from $8.50 to $4.25/month and reduces paid instance storage from 950 to **850 GB**. The existing 80 GiB source fits in the proposed 100 GB virtual capacity without shrinking its filesystem; actual OCI imported-image minimum and boot compatibility remain unverified. No existing local or OCI disk has been resized.

The supplied Console details established €250 total commitment. Subsequent authenticated subscription discovery established the separate unused promotion, actual expiry and A1 tiers; no further screenshot or billing credential is currently required from the user.
