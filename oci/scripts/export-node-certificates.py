#!/usr/bin/env python3
"""Export cert-manager leaf certificates to the ignored Ansible secret paths."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
destination = root / 'oci/ansible/secrets'
ca = root / 'pki/homelab-root-ca.crt'
nodes = [(f'wings-{n:02}', f'wings-{n:02}.oci.home.internal') for n in range(1, 5)]
nodes.append(('panel-proxy', 'pelican.home.internal'))
os.umask(0o077)

# Validate every bundle before replacing any local files. No CA key is exported.
with tempfile.TemporaryDirectory(prefix='homelab-leaf-certs-') as staging:
    bundles = []
    for name, hostname in nodes:
        subprocess.run(['kubectl', '-n', 'pelican', 'wait', '--for=condition=Ready',
                        f'certificate/{name}', '--timeout=60s'], check=True,
                       stdout=subprocess.DEVNULL)
        secret = json.loads(subprocess.check_output(
            ['kubectl', '-n', 'pelican', 'get', 'secret', name + '-tls', '-o', 'json']))
        directory = Path(staging) / name
        directory.mkdir()
        for field in ['tls.crt', 'tls.key']:
            (directory / field).write_bytes(base64.b64decode(secret['data'][field], validate=True))
        cert, key = directory / 'tls.crt', directory / 'tls.key'
        subprocess.run(['openssl', 'verify', '-CAfile', str(ca), '-untrusted', str(cert),
                        '-verify_hostname', hostname, str(cert)], check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(['openssl', 'x509', '-in', str(cert), '-noout', '-checkend', '604800'],
                       check=True, stdout=subprocess.DEVNULL)
        cert_pub = subprocess.check_output(['openssl', 'x509', '-in', str(cert), '-pubkey', '-noout'])
        key_pub = subprocess.check_output(['openssl', 'pkey', '-in', str(key), '-pubout'])
        if cert_pub != key_pub:
            raise SystemExit(f'{name}: certificate/key mismatch')
        bundles.append((name, directory))
    for name, directory in bundles:
        target = destination / name
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.chmod(0o700)
        # Stage both files and rollback copies before touching the current pair.
        # Run the exporter to completion before invoking either guest playbook.
        with tempfile.TemporaryDirectory(prefix='.tls-export-', dir=target) as transaction:
            transaction = Path(transaction)
            fields = ['tls.crt', 'tls.key']
            existed = {}
            for field in fields:
                (transaction / field).write_bytes((directory / field).read_bytes())
                existed[field] = (target / field).exists()
                if existed[field]:
                    (transaction / (field + '.previous')).write_bytes((target / field).read_bytes())
            try:
                for field in fields:
                    os.replace(transaction / field, target / field)
            except OSError:
                for field in fields:
                    if existed[field]:
                        os.replace(transaction / (field + '.previous'), target / field)
                    else:
                        (target / field).unlink(missing_ok=True)
                raise
        print(f'{name}: verified TLS bundle exported to ignored Ansible secrets')
