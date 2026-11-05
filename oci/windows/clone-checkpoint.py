#!/usr/bin/env python3
"""Clone a verified offline MPMB checkpoint, leaving its running VM untouched.

This creates a local preparation candidate, not an OCI-ready generalized image.
No source disk, VM definition, TPM, NVRAM or managed-save state is modified.
"""
import argparse, hashlib, json, os, pathlib, subprocess
p=argparse.ArgumentParser()
p.add_argument('--checkpoint',type=pathlib.Path,required=True)
p.add_argument('--output',type=pathlib.Path,required=True)
a=p.parse_args()
checkpoint=a.checkpoint.resolve()
manifest=json.loads((checkpoint/'manifest.json').read_text())
if manifest.get('name')!='mpmb-windows11': raise SystemExit('Unexpected source VM manifest.')
entry=next((x for x in manifest['entries'] if not x['directory'] and pathlib.Path(x['source']).name=='system.qcow2'),None)
if not entry: raise SystemExit('Checkpoint does not contain the expected system disk.')
source=(checkpoint/entry['backup']).resolve()
if source.parent!=checkpoint or source==pathlib.Path(entry['source']).resolve():
    raise SystemExit('Refusing the live system disk or a checkpoint path escape.')
if a.output.exists():raise SystemExit('Refusing to overwrite destination.')
info=json.loads(subprocess.check_output(['qemu-img','info','--output=json',str(source)]))
if info['format']!='qcow2' or info.get('backing-filename'):raise SystemExit('Require a standalone QCOW2 checkpoint.')
print('Verifying checkpoint disk SHA256 before cloning...',flush=True)
h=hashlib.sha256()
with source.open('rb') as f:
    for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
if h.hexdigest()!=entry['sha256']['.']:raise SystemExit('Checkpoint hash mismatch; source left unchanged.')
os.umask(0o077)
a.output.parent.mkdir(parents=True,exist_ok=True)
subprocess.run(['cp','--reflink=auto','--sparse=always','--no-clobber',str(source),str(a.output)],check=True)
a.output.chmod(0o600)
subprocess.run(['qemu-img','check',str(a.output)],check=True)
report={'source_vm':'mpmb-windows11','checkpoint':str(checkpoint),'disk_sha256':h.hexdigest(),'output':str(a.output.resolve()),'virtual_size_bytes':info['virtual-size'],'state':'local unprepared clone; not generalized, sanitized, driver-verified, OCI-imported or boot-tested','source_vm_modified':False}
a.output.with_suffix('.source.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
