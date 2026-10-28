#!/usr/bin/env python3
"""Generate ignored local inventory and a DNS host mapping from real TF outputs."""
import ipaddress, json, os, pathlib, subprocess
import yaml
root = pathlib.Path(__file__).resolve().parents[1]
d = json.loads(subprocess.check_output(['terraform', '-chdir='+str(root/'terraform'), 'output', '-json']))
get = lambda k: d[k]['value']
inv = yaml.safe_load((root/'ansible/inventory.example.yaml').read_text())
net = get('network')
router = str(ipaddress.IPv4Address(net['router_private_ip']))
routes = [str(ipaddress.IPv4Network(cidr)) for cidr in net['advertised_routes']]
if not routes: raise SystemExit('Terraform must supply at least one actual OCI route.')
inv['all']['vars']['router_private_ip'] = router
inv['all']['vars']['admin_source_cidrs'] = [router+'/32']
inv['all']['vars']['router_source_cidrs'] = [router+'/32']
children = inv['all']['children']
lines = []
for name, v in get('wings_instances').items():
    ip = str(ipaddress.IPv4Address(v['private_ip']))
    children['wings']['hosts'][name]['ansible_host'] = ip
    lines.append(f'{ip} {name}.oci.home.internal')
children['subnet_routers']['hosts']['wings-04']['tailscale_routes'] = routes
children['homelab']['vars']['oci_subnet_cidrs'] = routes
os.umask(0o077)
path=root/'ansible/inventory.yaml'
if path.exists():
    existing = yaml.safe_load(path.read_text())
    current = existing['all']['children']
    for group in ['subnet_routers', 'thor_bootstrap']:
        for host in current.get(group, {}).get('hosts', {}).values():
            host['tailscale_routes'] = routes
    current['homelab'].setdefault('vars', {})['oci_subnet_cidrs'] = routes
    path.write_text(yaml.safe_dump(existing, sort_keys=False))
    print('Reconciled generated OCI subnet routes; kept operator settings. Review instance addresses manually.')
else:
    path.write_text(yaml.safe_dump(inv,sort_keys=False))
    print('Wrote private inventory; review package versions, users, TLS paths and preservation gates.')
(root/'inventory').mkdir(exist_ok=True)
(root/'inventory/wings.hosts').write_text('\n'.join(lines)+'\n')
print('Refreshed private DNS mapping from Terraform outputs.')

# Write actual monitoring targets for subsequent reviewed GitOps commit/sync.
endpoint_path=root.parent/'kubernetes/pelican/manifests/wings-endpoints.yaml'
e=yaml.safe_load(endpoint_path.read_text())
e['endpoints']=[{'addresses':[str(ipaddress.IPv4Address(v['private_ip']))], 'hostname':name, 'conditions':{'ready':True}} for name,v in get('wings_instances').items()]
endpoint_path.write_text(yaml.safe_dump(e,sort_keys=False))
print('Updated tracked monitoring EndpointSlice: review and commit the actual targets before sync.')
