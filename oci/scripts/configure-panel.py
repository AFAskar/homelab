#!/usr/bin/env python3
"""Enroll the four Terraform-managed nodes in the pinned Panel release.

Uses the same validated models/user service as that release's artisan commands.
Passwords and generated Wings tokens travel over kubectl stdin/stdout, never argv.
Run only after the approved Panel deployment and Linux provisioning plan.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--admin-email', required=True)
parser.add_argument('--initialize', action='store_true', help='Initialize the configured SQLite schema on first deployment.')
parser.add_argument('--test-games', action='store_true', help='Create the pinned native Mindustry acceptance server on each node.')
args = parser.parse_args()
root = Path(__file__).resolve().parents[2]
private = root / 'oci/ansible/secrets'
os.umask(0o077)
private.mkdir(parents=True, exist_ok=True)
(root / 'oci/inventory').mkdir(parents=True, exist_ok=True)


def run(command, *, timeout=120, **kwargs):
    try:
        return subprocess.run(command, timeout=timeout, **kwargs)
    except subprocess.TimeoutExpired:
        raise SystemExit(f'{command[0]} timed out after {timeout} seconds. '
                         'The remote operation may still be running; inspect it before retrying.') from None


def panel(code, data):
    bootstrap = ("require 'vendor/autoload.php'; $app=require 'bootstrap/app.php'; "
                 "$app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); "
                 "$data=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR); ")
    result = run(['kubectl', '-n', 'pelican', 'exec', '-i', 'deployment/pelican',
                             '-c', 'panel', '--', 'php', '-r', bootstrap + code],
                            input=json.dumps(data), text=True, capture_output=True, timeout=300)
    if result.returncode:
        log = root / 'oci/inventory/panel-configure-error.log'
        log.write_text(result.stdout + result.stderr)
        log.chmod(0o600)
        raise SystemExit('Panel command failed; inspect ignored panel-configure-error.log privately.')
    return json.loads(result.stdout)


if args.initialize:
    panel('$p=config("database.connections.sqlite.database"); '
          'if(config("database.default")!=="sqlite" || $p!=="/pelican-data/database/database.sqlite") '
          'throw new RuntimeException("Unexpected database configuration"); '
          'if(!is_dir(dirname($p))) mkdir(dirname($p),0770,true); '
          'if(!file_exists($p)){ $f=fopen($p,"x"); fclose($f); } echo "true";', {})
    result = run(['kubectl', '-n', 'pelican', 'exec', 'deployment/pelican', '-c', 'panel',
                             '--', 'php', 'artisan', 'migrate', '--seed', '--force'], capture_output=True, timeout=900)
    log = root / 'oci/inventory/panel-migrations.log'
    log.write_bytes(result.stdout + result.stderr)
    log.chmod(0o600)
    if result.returncode:
        raise SystemExit('Schema initialization failed; inspect ignored panel-migrations.log privately.')

credentials = private / 'panel-admin.json'
existing = panel('$u=App\\Models\\User::where("email",$data["email"])->first(); '
                 'echo json_encode(["exists"=>(bool)$u,"admin"=>$u?->isRootAdmin()??false]);',
                 {'email': args.admin_email})
if existing['exists']:
    if not existing['admin']:
        raise SystemExit('Existing account is not a root administrator; no role or password changed.')
    print('Existing administrator preserved; no password reset.')
else:
    if credentials.exists():
        admin = json.loads(credentials.read_text())
        if admin['email'] != args.admin_email:
            raise SystemExit('Stored bootstrap administrator email differs; review before proceeding.')
    else:
        admin = {'email': args.admin_email, 'username': 'homelab-admin',
                 'password': secrets.token_urlsafe(32), 'root_admin': True}
        with credentials.open('x') as output:
            json.dump(admin, output)
        credentials.chmod(0o600)
    panel('config(["panel.email.send_account_created_notification"=>false]); '
          '$u=$app->make(App\\Services\\Users\\UserCreationService::class)->handle($data); '
          'echo json_encode(["id"=>$u->id]);', admin)
    print('Administrator created; credential saved only in ignored panel-admin.json (0600).')

nodes = json.loads(run(
    ['terraform', '-chdir=' + str(root / 'oci/terraform'), 'output', '-json', 'wings_instances'],
    capture_output=True, check=True).stdout)
if set(nodes) != {f'wings-{n:02}' for n in range(1, 5)}:
    raise SystemExit('Expected exactly four Terraform-managed Wings identities.')
for name, instance in sorted(nodes.items()):
    retained = name == 'wings-04'
    desired = {'name': name, 'fqdn': name + '.oci.home.internal', 'scheme': 'https',
               'public': True, 'behind_proxy': False, 'maintenance_mode': False,
               'memory': 20480 if retained else 14336, 'memory_overallocate': 0,
               'disk': 81920 if retained else 184320, 'disk_overallocate': 0,
               'cpu': 400, 'cpu_overallocate': 0, 'upload_size': 256,
               'daemon_base': '/var/lib/pelican/volumes' if retained else '/srv/pelican/volumes',
               'daemon_listen': 8080, 'daemon_connect': 8080, 'daemon_sftp': 2022}
    config = panel(
        '$n=App\\Models\\Node::firstOrCreate(["name"=>$data["node"]["name"]],$data["node"]); '
        'foreach(["fqdn","scheme","daemon_base"] as $k){ '
        'if($n->$k!==$data["node"][$k]) throw new RuntimeException("Existing node differs: ".$k); } '
        'App\\Models\\Allocation::firstOrCreate(["node_id"=>$n->id,"ip"=>$data["ip"],"port"=>25565],'
        '["ip_alias"=>$data["public_ip"]]); echo $n->getJsonConfiguration();',
        {'node': desired, 'ip': instance['private_ip'], 'public_ip': instance['public_ip']})
    config['api']['ssl'].update({'cert': '/etc/pelican/tls/tls.crt', 'key': '/etc/pelican/tls/tls.key'})
    directory = private / name
    directory.mkdir(mode=0o700, exist_ok=True)
    path = directory / 'config.yml'
    path.write_text(json.dumps(config, indent=2) + '\n')  # JSON is also valid YAML.
    path.chmod(0o600)
    print(name + ': enrolled; private configuration refreshed without rotating node tokens.')

panel('$writer=new class {use App\\Traits\\EnvironmentWriterTrait;}; '
      '$writer->writeToEnvironment(["APP_INSTALLED"=>"true"]); echo "true";', {})
print('Database/admin/node setup complete; web installer disabled using the release environment writer.')

if args.test_games:
    egg = json.loads((root / 'oci/pelican/egg-mindustry-acceptance.json').read_text())
    result = panel(
        '$e=App\\Models\\Egg::where("uuid",$data["egg"]["uuid"])->first(); '
        '$e=$app->make(App\\Services\\Eggs\\Sharing\\EggImporterService::class)->fromContent('
        'json_encode($data["egg"]),App\\Enums\\EggFormat::JSON,$e); '
        '$owner=App\\Models\\User::where("email",$data["email"])->firstOrFail(); $result=[]; '
        'foreach(App\\Models\\Node::whereIn("name",$data["nodes"])->get() as $n){ '
        '$name="mindustry-".$n->name; '
        '$s=App\\Models\\Server::where("node_id",$n->id)->where("name",$name)->first(); '
        'if(!$s){$a=$n->allocations()->where("port",25565)->whereNull("server_id")->firstOrFail(); '
        '$s=$app->make(App\\Services\\Servers\\ServerCreationService::class)->handle(['
        '"name"=>$name,"node_id"=>$n->id,"owner_id"=>$owner->id,"egg_id"=>$e->id,'
        '"allocation_id"=>$a->id,"memory"=>2048,"swap"=>0,"disk"=>2048,"io"=>500,'
        '"cpu"=>200,"threads"=>null,"oom_killer"=>true,"backup_limit"=>1,'
        '"skip_scripts"=>false,"start_on_completion"=>true,'
        '"environment"=>["SERVER_NAME"=>$name,"MAPNAME"=>"Tendrils"]]); } '
        '$result[]=["node"=>$n->name,"id"=>$s->id,"uuid"=>$s->uuid,"status"=>$s->status]; } '
        'echo json_encode($result);',
        {'egg': egg, 'email': args.admin_email, 'nodes': sorted(nodes)})
    print(json.dumps(result, indent=2))
