"""Recalculate from official Oracle list-price API + ECB XML, without credentials."""
import argparse, datetime, decimal, json, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path
D = decimal.Decimal
p = argparse.ArgumentParser()
p.add_argument('--hours', type=int, default=730)
p.add_argument('--windows-hours', type=int, default=120)
p.add_argument('--image-gb', type=int, default=0, help='Measured custom image GB; unknown is zero, report separately')
p.add_argument('--upload-gb', type=int, default=0)
p.add_argument('--existing-charge-usd', type=D, default=D(0), help='Verified non-free existing resources only')
p.add_argument('--remaining-eur', type=D, default=D(250))
p.add_argument('--extra-usd', type=D, default=D(0), help='Egress/API requests/state storage/tax if applicable')
p.add_argument('--output')
a = p.parse_args()
api = 'https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD'
prices = json.load(urllib.request.urlopen(api, timeout=60))
parts = {x['partNumber']:x for x in prices['items']}
def rate(part):
 entries=parts[part]['currencyCodeLocalizations'][0]['prices']
 return max(D(str(x['value'])) for x in entries if x['model']=='PAY_AS_YOU_GO')
fx_url='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
fx=ET.fromstring(urllib.request.urlopen(fx_url, timeout=30).read())
fx_day=next(x.attrib['time'] for x in fx.iter() if 'time' in x.attrib)
usd_per_eur=next(D(x.attrib['rate']) for x in fx.iter() if x.attrib.get('currency')=='USD')
rows={}
for n in range(1,4):
 rows[f'wings-0{n} compute']=D(a.hours)*(2*rate('B111129')+16*rate('B111130'))
 rows[f'wings-0{n} 250GB balanced']=250*(rate('B91961')+10*rate('B91962'))
rows['win11 compute']=D(a.windows_hours)*(2*rate('B93113')+16*rate('B93114'))
rows['win11 200GB balanced, including stopped hours']=200*(rate('B91961')+10*rate('B91962'))
rows['50GB backups, no free allowance deducted']=50*rate('B91628')
rows['custom image storage'] = a.image_gb*rate('B91628')
rows['uploaded source image storage'] = a.upload_gb*rate('B91628')
rows['existing non-free resources'] = a.existing_charge_usd
rows['other measured charges'] = a.extra_usd
total=sum(rows.values())
eur=total/usd_per_eur
result={'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pricing_source':api,'prices_updated':prices.get('lastUpdated'),'fx_source':fx_url,'fx_date':fx_day,'usd_per_eur':str(usd_per_eur),'runtime_hours':a.hours,'windows_hours':a.windows_hours,'rows':{k:{'USD':str(v.quantize(D('.01'))),'EUR':str((v/usd_per_eur).quantize(D('.01')))} for k,v in rows.items()},'total_usd':str(total),'total_eur':str(eur.quantize(D('.01'))),'remaining_after_month_eur':str((a.remaining_eur-eur).quantize(D('.01'))),'credit_days_at_average_burn':str((a.remaining_eur/eur*D(a.hours)/24).quantize(D('.01'))),'assumptions':['No free storage allowance double-counted','wings-04 costs unknown until inventory; assumes eligibility retained','Image/source storage sizes unknown unless supplied','Egress and other tenancy spend unknown; extra-usd must include them','Trial expiration and actual credit balance unknown','Taxes and regional contract prices not established']}
print(json.dumps(result,indent=2))
if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
