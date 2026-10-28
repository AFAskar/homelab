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
p.add_argument('--existing-charge-eur', type=D, default=D(0))
p.add_argument('--extra-eur', type=D, default=D(0))
p.add_argument('--output')
a = p.parse_args()
api = 'https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode='
prices = {currency:json.load(urllib.request.urlopen(api+currency, timeout=60)) for currency in ['USD','EUR']}
def rate(part, currency):
 product=next(x for x in prices[currency]['items'] if x['partNumber']==part)
 entries=next(x['prices'] for x in product['currencyCodeLocalizations'] if x['currencyCode']==currency)
 return max(D(str(x['value'])) for x in entries if x['model']=='PAY_AS_YOU_GO')
fx_url='https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
fx=ET.fromstring(urllib.request.urlopen(fx_url, timeout=30).read())
fx_day=next(x.attrib['time'] for x in fx.iter() if 'time' in x.attrib)
usd_per_eur=next(D(x.attrib['rate']) for x in fx.iter() if x.attrib.get('currency')=='USD')
def calculate(currency):
 r=lambda part:rate(part,currency)
 rows={}
 for n in range(1,4):
  rows[f'wings-0{n} compute']=D(a.hours)*(2*r('B111129')+16*r('B111130'))
  rows[f'wings-0{n} 250GB balanced']=250*(r('B91961')+10*r('B91962'))
 rows['win11 compute']=D(a.windows_hours)*(2*r('B93113')+16*r('B93114'))
 rows['win11 100GB balanced, including stopped hours']=100*(r('B91961')+10*r('B91962'))
 rows['50GB backups, no free allowance deducted']=50*r('B91628')
 rows['custom image storage']=a.image_gb*r('B91628')
 rows['uploaded source image storage']=a.upload_gb*r('B91628')
 rows['existing non-free resources']=a.existing_charge_usd+a.existing_charge_eur*usd_per_eur if currency=='USD' else a.existing_charge_eur+a.existing_charge_usd/usd_per_eur
 rows['other measured charges']=a.extra_usd+a.extra_eur*usd_per_eur if currency=='USD' else a.extra_eur+a.extra_usd/usd_per_eur
 return rows
usd_rows=calculate('USD');eur_rows=calculate('EUR')
total=sum(usd_rows.values());eur=sum(eur_rows.values())
result={'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pricing_sources':{c:api+c for c in prices},'prices_updated':{c:prices[c].get('lastUpdated') for c in prices},'fx_source':fx_url,'fx_date':fx_day,'usd_per_eur':str(usd_per_eur),'runtime_hours':a.hours,'windows_hours':a.windows_hours,'billing_currency':'EUR','rows':{k:{'USD':str(v.quantize(D('.01'))),'EUR':str(eur_rows[k].quantize(D('.01')))} for k,v in usd_rows.items()},'total_usd':str(total),'total_eur':str(eur.quantize(D('.01'))),'usd_list_converted_to_eur_for_comparison_only':str((total/usd_per_eur).quantize(D('.01'))),'remaining_after_month_eur':str((a.remaining_eur-eur).quantize(D('.01'))),'credit_days_at_average_burn':str((a.remaining_eur/eur*D(a.hours)/24).quantize(D('.01'))),'assumptions':['USD and EUR use their own official list tariffs; EUR credit consumption is not spot-converted USD','No free storage allowance double-counted','wings-04 assumes retained eligibility; smaller documented allowance must be evaluated separately','Image/source storage sizes unknown unless supplied','Egress and other tenancy spend unknown; supply measured extras','Trial expiration and actual credit balance unknown','Taxes and account contract discounts not established']}
print(json.dumps(result,indent=2))
if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
