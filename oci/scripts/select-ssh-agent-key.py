#!/usr/bin/env python3
"""Select only a matching agent public key; never export private key material."""
import argparse, base64, binascii, hashlib, os, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('--socket', default=str(pathlib.Path.home()/'.var/app/com.bitwarden.desktop/data/.bitwarden-ssh-agent.sock'))
p.add_argument('--fingerprint', default='SHA256:2fArxE1VX5fSceDUZt37ZXIYBAB9rsPKGuRdbwXwVAo')
p.add_argument('--output', default=str(pathlib.Path(__file__).resolve().parents[1]/'inventory/thor-agent.pub'))
a=p.parse_args()
result = subprocess.run(['ssh-add', '-L'], env=dict(os.environ, SSH_AUTH_SOCK=a.socket), text=True, capture_output=True)
if result.returncode:
    raise SystemExit('Agent is unavailable or has no identities; unlock/configure the intended agent.')
for line in result.stdout.splitlines():
    fields = line.split()
    if len(fields) < 2:
        continue
    try:
        key_bytes = base64.b64decode(fields[1], validate=True)
    except (ValueError, binascii.Error):
        continue
    fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(key_bytes).digest()).decode().rstrip('=')
    if fingerprint==a.fingerprint:
        os.umask(0o077)
        output=pathlib.Path(a.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(line+'\n')
        print('Selected matching public key. Use IdentityAgent with IdentitiesOnly=yes; private key remains in the agent.')
        break
else: raise SystemExit('Requested fingerprint is not available; unlock/configure the intended agent.')
