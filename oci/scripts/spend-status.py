#!/usr/bin/env python3
"""Read OCI costs and optional subscription-specific promotional credit balance."""
import argparse, datetime as dt, json, os
import oci
from oci import usage_api
p=argparse.ArgumentParser()
p.add_argument('--subscription-id', default=os.environ.get('OCI_SUBSCRIPTION_ID'), help='Classic numeric subscription ID, not the organizationssubscription OCID')
a=p.parse_args()
c=oci.config.from_file(profile_name=os.environ.get('OCI_CLI_PROFILE','DEFAULT'))
now=dt.datetime.now(dt.timezone.utc)
start=dt.datetime(now.year,now.month,1,tzinfo=dt.timezone.utc)
end=(now+dt.timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
request=usage_api.models.RequestSummarizedUsagesDetails(tenant_id=c['tenancy'],time_usage_started=start,time_usage_ended=end,granularity='DAILY',query_type='COST',group_by=['currency','service'])
client=usage_api.UsageapiClient(c)
rows=[]
page=None
while True:
 response=client.request_summarized_usages(request,page=page)
 rows.extend(response.data.items)
 page=response.next_page
 if not page:
  break
totals={}
incomplete=set()
for row in rows:
 key=(row.currency,row.service)
 if row.computed_amount is None:
  totals.setdefault(key,None)
  incomplete.add(key)
 else:
  totals[key]=(totals.get(key) or 0)+row.computed_amount
reported=[{'service':service,'currency':currency,'amount':amount,'complete':(currency,service) not in incomplete} for (currency,service),amount in sorted(totals.items(),key=lambda item:tuple(v or '' for v in item[0]))]
result={'period_start':start.isoformat(),'period_end':end.isoformat(),'reported_costs':reported,'costs_complete':not incomplete,'notice':'Usage and credit ledgers can lag. An incomplete total contains only known amounts, or null if all amounts are unknown. Promotion expiry can precede arithmetic credit exhaustion; budgets do not stop charges.'}
if a.subscription_id:
 subscriptions=oci.onesubscription.SubscriptionClient(c).list_subscriptions(c['tenancy'],subscription_id=a.subscription_id,is_commit_info_required=True).data
 result['promotions']=[{'currency':sub.currency.iso_code,'status':service.status,'used':service.used_amount,'available':service.available_amount,'expires_utc':service.time_end.isoformat() if service.time_end else None} for sub in subscriptions for service in sub.subscribed_services if service.product.part_number=='B88385']
else:
 result['notice']+=' Supply --subscription-id to read the actual promotional balance.'
print(json.dumps(result,indent=2))
