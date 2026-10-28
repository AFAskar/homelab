#!/usr/bin/env python3
"""Read reported OCI cost totals; does not claim to read remaining promotional credits."""
import datetime as dt, json, os
import oci
from oci import usage_api
c=oci.config.from_file(profile_name=os.environ.get('OCI_CLI_PROFILE','DEFAULT'))
now=dt.datetime.now(dt.timezone.utc)
start=dt.datetime(now.year,now.month,1,tzinfo=dt.timezone.utc)
end=(now+dt.timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
request=usage_api.models.RequestSummarizedUsagesDetails(tenant_id=c['tenancy'],time_usage_started=start,time_usage_ended=end,granularity='MONTHLY',query_type='COST',group_by=['currency','service'])
rows=usage_api.UsageapiClient(c).request_summarized_usages(request).data.items
print(json.dumps({'period_start':start.isoformat(),'period_end':end.isoformat(),'reported_costs':[{'service':x.service,'currency':x.currency,'amount':x.computed_amount} for x in rows],'notice':'Usage can lag. Monthly cost is not the remaining promotional credit balance; check the credit Console and expiry.'},indent=2))
