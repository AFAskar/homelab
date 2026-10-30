#!/usr/bin/env python3
"""Capture Panel and explicitly selected game servers into an age-encrypted tar.

Runs on the trusted operator laptop with existing kubectl, SSH and age access.
Only previously running selected games are stopped/restarted. No OCI credential
is copied to guests. Upload the result using backup.sh.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--server-uuid', action='append', default=[], type=lambda s: str(uuid.UUID(s)))
parser.add_argument('--save-command', help='Optional game console command before graceful stop, e.g. save homelab-backup')
parser.add_argument('output', type=Path, help='New encrypted .age output; existing files are refused')
args = parser.parse_args()
args.server_uuid = list(dict.fromkeys(args.server_uuid))
root = Path(__file__).resolve().parents[2]
os.umask(0o077)
if args.output.exists():
    raise SystemExit('Output already exists; no game state changed.')
if not args.output.parent.is_dir():
    raise SystemExit('Create the private output directory first; no game state changed.')
recipient = re.search(r'age1[a-z0-9]+', (root / '.sops.yaml').read_text()).group()
kubectl = ['kubectl', '-n', 'pelican', 'exec', 'deployment/pelican', '-c', 'panel', '--']
bootstrap = ('require "vendor/autoload.php"; $app=require "bootstrap/app.php"; '
             '$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); '
             '$data=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR); ')


def panel(code, data):
    return json.loads(subprocess.check_output(
        kubectl[:4] + ['-i'] + kubectl[4:] + ['php', '-r', bootstrap + code],
        input=json.dumps(data), text=True))


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


servers = panel('$result=[]; foreach($data as $id){$s=App\\Models\\Server::where("uuid",$id)->firstOrFail(); '
                '$r=$app->make(App\\Repositories\\Daemon\\DaemonServerRepository::class)->setServer($s); '
                '$result[]=["uuid"=>$s->uuid,"node"=>$s->node->name,"base"=>$s->node->daemon_base,'
                '"state"=>$r->getDetails(5)["state"]];} echo json_encode($result);', args.server_uuid)
nodes = json.loads(subprocess.check_output(
    ['terraform', '-chdir=' + str(root / 'oci/terraform'), 'output', '-json', 'wings_instances']))
for server in servers:
    expected = '/var/lib/pelican/volumes' if server['node'] == 'wings-04' else '/srv/pelican/volumes'
    if server['node'] not in nodes or server['base'] != expected:
        raise SystemExit('Server is outside the discovered backup scope.')

stopped = []
try:
    for server in servers:
        if server['state'] != 'running':
            if server['state'] != 'offline':
                raise SystemExit('Selected server must be running or offline before backup.')
            continue
        stopped.append(server['uuid'])
        panel('$s=App\\Models\\Server::where("uuid",$data["uuid"])->firstOrFail(); '
              '$r=$app->make(App\\Repositories\\Daemon\\DaemonServerRepository::class)->setServer($s); '
              'if($data["save"]){$r->getHttpClient()->post("/api/servers/{$s->uuid}/commands",'
              '["commands"=>[$data["save"]]])->throw(); usleep(2000000);} '
              '$r->power("stop")->throw(); echo "true";',
              {'uuid': server['uuid'], 'save': args.save_command})
    for _ in range(30):
        states = panel('$states=[];foreach($data as $id){$s=App\\Models\\Server::where("uuid",$id)->firstOrFail();'
                       '$r=$app->make(App\\Repositories\\Daemon\\DaemonServerRepository::class)->setServer($s);'
                       '$states[]=$r->getDetails(5)["state"];} echo json_encode($states);', args.server_uuid)
        if all(state == 'offline' for state in states):
            break
        time.sleep(2)
    else:
        raise SystemExit('Graceful stop timed out; no live game files archived and no force stop attempted.')

    with tempfile.TemporaryDirectory(prefix='homelab-backup-') as temporary:
        staging = Path(temporary)
        snapshot = '/tmp/oci-backup-' + str(uuid.uuid4()) + '.sqlite'
        panel('if(config("database.default")!=="sqlite") throw new RuntimeException("Expected SQLite"); '
              '$source=new SQLite3(config("database.connections.sqlite.database"),SQLITE3_OPEN_READONLY); '
              '$target=new SQLite3($data); if(!$source->backup($target)) throw new RuntimeException("SQLite backup failed"); '
              '$target->close();$source->close();chmod($data,0600);echo "true";', snapshot)
        try:
            with (staging / 'panel.tar.gz').open('wb') as output:
                subprocess.run(kubectl + ['tar', '-czf', '-', '-C', '/pelican-data', '.env', 'storage', 'plugins',
                                          '-C', '/tmp', Path(snapshot).name], stdout=output, check=True)
        finally:
            subprocess.run(kubectl + ['rm', '-f', snapshot], check=True)
        shutil.copyfile(root / 'kubernetes/pelican/manifests/panel.secret.sops.yaml', staging / 'panel.secret.sops.yaml')
        actual_secret = json.loads(subprocess.check_output(
            ['kubectl', '-n', 'pelican', 'get', 'secret', 'pelican-env', '-o', 'json']))
        (staging / 'panel-env.json').write_text(json.dumps({
            'apiVersion': 'v1', 'kind': 'Secret', 'type': 'Opaque',
            'metadata': {'name': 'pelican-env', 'namespace': 'pelican'}, 'data': actual_secret['data']}))
        for server in servers:
            name = server['node']
            ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes']
            if name == 'wings-04':
                ssh += ['-o', 'IdentityAgent=' + str(Path.home() / '.var/app/com.bitwarden.desktop/data/.bitwarden-ssh-agent.sock'),
                        '-o', 'HostKeyAlias=100.89.233.80', '-i', str(root / 'oci/inventory/thor-agent.pub')]
            else:
                ssh += ['-i', str(Path.home() / '.ssh/KaliVM')]
            command = 'sudo tar -czf - -C ' + shlex.quote(server['base']) + ' ' + shlex.quote(server['uuid'])
            with (staging / (server['uuid'] + '.tar.gz')).open('wb') as output:
                subprocess.run(ssh + ['ubuntu@' + nodes[name]['private_ip'], command], stdout=output, check=True)
        checksums = {p.name: checksum(p) for p in staging.iterdir()}
        (staging / 'manifest.json').write_text(json.dumps({'servers': servers, 'sha256': checksums}, indent=2))
        tar = subprocess.Popen(['tar', '-cf', '-', '-C', str(staging), '.'], stdout=subprocess.PIPE)
        encrypted = subprocess.run(['age', '-r', recipient, '-o', str(args.output)], stdin=tar.stdout)
        tar.stdout.close()
        if tar.wait() or encrypted.returncode:
            raise SystemExit('Encryption failed; retain no incomplete archive as a valid backup.')
    digest = checksum(args.output)
    args.output.with_suffix(args.output.suffix + '.sha256').write_text(digest + '  ' + args.output.name + '\n')
    print(f'Encrypted consistent backup: {args.output} SHA256 {digest}')
finally:
    restart_errors = []
    for identifier in stopped:
        try:
            panel('$s=App\\Models\\Server::where("uuid",$data)->firstOrFail(); '
                  '$app->make(App\\Repositories\\Daemon\\DaemonServerRepository::class)->setServer($s)->power("start")->throw();'
                  'echo "true";', identifier)
        except subprocess.CalledProcessError:
            restart_errors.append(identifier)
    if restart_errors:
        raise SystemExit('Could not restart selected games; inspect these UUIDs: ' + ', '.join(restart_errors))
