#!/usr/bin/env python3
"""Read-only route/TLS/service probes. A success here is not a Panel/game acceptance test."""
import concurrent.futures, json, pathlib, subprocess, socket, ssl, sys, urllib.request, urllib.error
root = pathlib.Path(__file__).resolve().parents[1]
d = json.loads(subprocess.check_output(['terraform', '-chdir='+str(root/'terraform'), 'output', '-json']))
context = ssl.create_default_context(cafile=str(root.parent/'pki/homelab-root-ca.crt'))
def probe(item):
    name, v = item
    ip = v['private_ip']
    result = {'node': name, 'private_ip': ip}
    for port in [22, 8080, 9100]:
        try:
            with socket.create_connection((ip, port), timeout=5): pass
            result[str(port)] = 'reachable'
        except OSError as e: result[str(port)] = str(e)
    # DNS must resolve the private FQDN; CA and hostname are verified.
    try:
        urllib.request.urlopen('https://'+name+'.oci.home.internal:8080/api/system', context=context, timeout=8)
        result['wings_tls'] = 'verified'
    except urllib.error.HTTPError as e:
        result['wings_tls'] = 'verified, API requires enrollment/authentication' if e.code in [401, 403] else str(e)
    except Exception as e: result['wings_tls'] = str(e)
    return result
results=list(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(probe,d['wings_instances']['value'].items()))
print(json.dumps(results,indent=2))
if any(any(r[str(p)] != 'reachable' for p in [22,8080,9100]) or not r['wings_tls'].startswith('verified') for r in results): sys.exit(1)
