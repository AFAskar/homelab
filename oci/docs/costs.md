# Infrastructure costs

## Recalculate before applying

Use native EUR tariffs for this EUR-billed tenancy. The desired topology has two continuously running E6 nodes: wings-01 at 4 OCPUs/32 GB and wings-02 at 2 OCPUs/16 GB. Thor stays at its existing Always Free allocation. Windows is modelled at 120 running hours; its 100 GB boot volume remains billable while stopped. All other compute and storage use a 730-hour month. Windows licensing is outside this analysis.

From the repository root:

```bash
umask 077
python3 oci/scripts/estimate_cost.py --image-gb 86 --upload-gb 18 \
  --output oci/inventory/reports/cost-estimate.json
# After applying a capacity change, use the actual managed topology:
terraform -chdir=oci/terraform output -json wings_capacity >oci/inventory/capacity.json
python3 oci/scripts/estimate_cost.py --capacity-json oci/inventory/capacity.json \
  --image-gb 86 --upload-gb 18
python3 oci/scripts/spend-status.py --subscription-id 100001000344740
```

Supply the current remaining credit with `--remaining-eur`; the default €250 is the original grant, not a balance read. Add measured request/egress/tax charges using `--extra-eur`. Use `--hours 744` for a 31-day month. Rates are fetched from the official [EUR catalog](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=EUR) and [USD catalog](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD), refreshed October 31, 2026. [ECB XML](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml) dated October 30 gives €1 = $1.1172; FX is for USD comparison, not EUR billing.

| SKU | Component | USD list rate | EUR list rate |
|---|---|---:|---:|
| B111129 | E6 OCPU-hour | 0.0300 | 0.0279 |
| B111130 | E6 GB-hour RAM | 0.0020 | 0.00186 |
| B93113 | E4 OCPU-hour | 0.0250 | 0.02325 |
| B93114 | E4 GB-hour RAM | 0.0015 | 0.001395 |
| B91961 | Block capacity GB-month | 0.0255 | 0.023715 |
| B91962 | VPU per GB-month | 0.0017 | 0.001581 |
| B91628 | Standard Object Storage GB-month beyond free tiers | 0.0255 | 0.023715 |


## Monthly estimate for the desired allocation

| Service | USD list | EUR list |
|---|---:|---:|
| wings-01 compute | $134.32 | €124.92 |
| wings-01 450GB balanced | $19.12 | €17.79 |
| wings-02 compute | $67.16 | €62.46 |
| wings-02 250GB balanced | $10.62 | €9.88 |
| win11 compute | $8.88 | €8.26 |
| win11 100GB balanced, including stopped hours | $4.25 | €3.95 |
| 50GB backups, no free allowance deducted | $1.28 | €1.19 |
| custom image storage | $2.19 | €2.04 |
| uploaded source image storage | $0.46 | €0.43 |
| Full scope | $248.29 | €230.91 |

The non-Windows projection is **€218.70/month**; the full scope leaves **€19.09** from an illustrative unused €250 grant after 730 hours, before unmeasured charges. The full-scope average burn would consume €250 in about **32.93 days**, subject to the earlier promotion expiry. Removing one 2/16 E6 and adding its compute to wings-01 keeps aggregate compute unchanged. Expanding wings-01 data by 200 GB while deleting wings-03's 200 GB data leaves total data capacity unchanged; deleting wings-03's 50 GB boot saves **€1.98/month**. Retaining that boot disk for recovery instead retains its approximately €1.98/month cost.

Paid Linux disks total 700 GB: 450 GB wings-01 and 250 GB wings-02. Windows adds 100 GB; Thor's existing 100 GB is separate. All block volumes use balanced 10 VPUs/GB. Block disks cannot be shrunk: treat the 400 GB expansion as irreversible. Boot disks remain billable after VM termination when preservation is enabled; explicitly include retained boot disks in spend checks.

## Allowances and additional charges

Reserve Thor's existing 100 GB free storage eligibility; do not subtract additional storage allowances without checking actual tenancy-wide usage. The subscription-specific A1 rate card read October 29 provided 3000 OCPU-hours/18000 GB-hours at zero for the current term, enough for Thor's 4/24 at 730 or 744 hours. Historical terminated-instance usage shares those allowances. Generic [Always Free documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) lists lower allowances; re-read the account's rate card at term rollover instead of assuming renewal preserves the current tier.

The estimate charges all 50 GB selected backups and conservatively rounds the imported 80 GiB Windows image to 86 decimal GB and the 17.315 GB source upload to 18 GB. Both image and source remain stored independently of a Windows VM. Measure backup growth and stored usage; no automatic snapshot schedule or backup deletion is assumed. Review a 14-day rolling backup set before approving deletion.

Existing networks, gateways and the subnet router are reused. No extra paid routing/monitoring instance is needed. Middle East/Africa outbound SKU B93456 lists the first 10240 GB/month at zero and then $0.05/GB, shared tenancy-wide. Object requests SKU B91627 lists the first 50000/month at zero, then $0.0034 per 10000. Cross-region transfer, game egress, API requests, state versions and taxes remain unmeasured; they are not covered by the €230.91 estimate. Use native EUR rates for actual additions.

## Credit expiry and alerts

The October 29 subscription read established an original €250 promotion expiring **2026-11-21 23:59:59 UTC / November 22 02:59:59 Riyadh**. Re-read remaining credit before deployment; the original unused balance is not current after running resources. Unused credit expires, and PAYG resources can charge the payment method afterward. Resources do not stop automatically.

Terraform manages a tenancy-wide monthly €250 budget with actual absolute alerts at **€200, €225 and €240** in EUR billing currency. Alerts can lag and do not impose a hard spending cap. Monthly budget resets do not track a cumulative promotion spanning months. Reconcile usage, remaining promotion credit and expiry separately.

If measured all-in spend exceeds €250 or the available balance, stop before applying and review duration, storage retention, Windows runtime or funding. Do not silently reduce allocations.
