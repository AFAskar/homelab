#!/usr/bin/env python3
"""Read quota headroom and E6 Ubuntu image compatibility before approving a plan."""
import argparse, json, os
import oci
p=argparse.ArgumentParser()
p.add_argument('--compartment',required=True)
p.add_argument('--ad',required=True)
p.add_argument('--ubuntu-image',required=True)
a=p.parse_args()
c=oci.config.from_file(profile_name=os.environ.get('OCI_CLI_PROFILE','DEFAULT'))
co=oci.core.ComputeClient(c);li=oci.limits.LimitsClient(c)
image=co.get_image(a.ubuntu_image).data
if image.operating_system != 'Canonical Ubuntu' or image.operating_system_version != '26.04' or 'aarch64' in image.display_name:
    raise SystemExit('Expected exact Ubuntu 26.04 x86-64 image; no fallback permitted.')
co.get_image_shape_compatibility_entry(a.ubuntu_image,'VM.Standard.E6.Flex')
checks=[]
for name,needed in [('standard-e6-core-count',6),('standard-e6-memory-count',48),('standard-e4-core-count',2),('standard-e4-memory-count',16)]:
    r=li.get_resource_availability('compute',name,a.compartment,availability_domain=a.ad).data
    available=r.fractional_availability if r.fractional_availability is not None else r.available
    checks.append({'limit':name,'needed':needed,'available':available,'pass':available is not None and available>=needed})
print(json.dumps({'image':image.display_name,'quota_checks':checks,'notice':'Does not reserve capacity, prove Windows compatibility, establish free entitlements, or authorize deployment.'},indent=2))
if not all(x['pass'] for x in checks):raise SystemExit(1)
