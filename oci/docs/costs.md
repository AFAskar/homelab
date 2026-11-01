# Infrastructure costs

## Recalculate the shared-host budget

The three Linux hosts run continuously. Wings-01 uses E6 4 OCPUs/32 GB, wings-02 E6 2 OCPUs/34 GB, and Thor retains its existing A1/free entitlement. Nested Windows shares wings-02 compute and its existing data volume: Windows runtime does not add another OCI compute/storage line. Saving Windows does not stop the shared host or reduce its OCI bill. Windows licensing is outside this analysis.

At official native EUR list rates retrieved November 1, 2026, the desired allocation projects **€243.14 per 730-hour month** or **€247.20 per 744-hour month**. The conservative 31-day projection leaves **€2.80 below €250**, before unmeasured state/requests/egress/taxes. This is an estimate, not a hard cap. The RAM increase from 16 to 34 GB adds €24.44 per 730 hours. No new OCI instance or volume is added; paid block storage remains 700 GB plus Thor's separate 100 GB.

The estimate includes balanced 10 VPU storage, 50 GB backups, and retained Windows artifacts rounded to 86 GB image + 18 GB source upload. The legacy image/source remain billable even though nested KVM does not require OCI image import; do not remove recovery artifacts without approved cleanup.

From the repository root:

```bash
umask 077
mkdir -p oci/inventory/reports
python3 oci/scripts/estimate_cost.py --hours 744 --image-gb 86 --upload-gb 18 \
  --output oci/inventory/reports/cost-estimate.json
# After apply, estimate the actual managed capacity rather than proposed defaults:
terraform -chdir=oci/terraform output -json wings_capacity >oci/inventory/capacity.json
python3 oci/scripts/estimate_cost.py --capacity-json oci/inventory/capacity.json \
  --hours 744 --image-gb 86 --upload-gb 18
python3 oci/scripts/spend-status.py --subscription-id 100001000344740
```

Use native [EUR tariffs](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=EUR) for this EUR-billed tenancy. The script also fetches the separate [USD tariff](https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD) and [ECB daily exchange rate](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml). The latest business-day FX on November 1 is October 30, €1 = $1.1172; it is for USD comparison, not EUR billing. The 744-hour USD-list total is $265.805. Runtime affects compute rows only; storage remains monthly and credit-days keeps its fixed 730-hour projection basis.

| SKU | Component | USD list rate | EUR list rate |
|---|---|---:|---:|
| B111129 | E6 OCPU-hour | 0.0300 | 0.0279 |
| B111130 | E6 GB-hour RAM | 0.0020 | 0.00186 |
| B93113 | E4 OCPU-hour | 0.0250 | 0.02325 |
| B93114 | E4 GB-hour RAM | 0.0015 | 0.001395 |
| B91961 | Block capacity GB-month | 0.0255 | 0.023715 |
| B91962 | VPU per GB-month | 0.0017 | 0.001581 |
| B91628 | Standard Object Storage GB-month beyond free tiers | 0.0255 | 0.023715 |


## Allowances, variable charges and credit expiry

Reserve Thor's existing free storage eligibility. The subscription-specific A1 rate card read October 29 provided 3000 OCPU-hours/18000 GB-hours at zero for the current term, enough for Thor's 4/24 at 730 or 744 hours. Historical instance usage shares allowances. Re-read account entitlements at term rollover; do not assume the generic Free Tier allowance or count free storage twice. No further free storage deduction is used in this estimate.

At a hypothetical unused €250 balance, a 730-hour month leaves €6.86, and the normalized average burn is about 31.27 days. That is not the current remaining balance after running resources. Supply current available credit with `--remaining-eur`; the default €250 represents the original grant. The verified promotion expires November 21, 2026 at 23:59:59 UTC / November 22 at 02:59:59 Riyadh, regardless of unused balance. Re-read the promotion before relying on it; PAYG resources continue billing afterward and do not stop automatically.

Measure additional backup/image growth, request counts, state versions, network transfer and taxes. Middle East/Africa outbound SKU B93456 lists the first 10240 GB/month at zero, then $0.05/GB, shared tenancy-wide; object-request SKU B91627 lists the first 50000/month at zero, then $0.0034 per 10000. Use native EUR rates for actual additions. Add measured extras with `--extra-eur`; near-budget allocation leaves little room for unmeasured charges. Existing gateways/router/monitoring are reused and no extra paid routing instance is needed.

Retain only selected encrypted backups within the reviewed storage budget; imported VM images and RAM checkpoints use existing block capacity. Before importing/starting a VM, check free space and the reserved guest budget rather than automatically expanding a volume. Data disks cannot be shrunk after an expansion.

Terraform's tenancy-wide monthly budget has actual absolute alerts at €200, €225 and €240. Alerts can lag, do not impose a spending cap, and reset monthly rather than tracking a cumulative promotion. Reconcile usage, balance and expiry separately. If measured total or a new plan exceeds the approved ceiling, stop before increasing paid allocations and review capacity or duration.
