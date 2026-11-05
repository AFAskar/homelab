#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: send-guest.sh PRIVATE_BUNDLE_DIRECTORY' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
python3 "$root/windows/guest-bundle.py" check "$1"
# shellcheck source=oci/scripts/lab-common.sh
source "$(dirname "$0")/lab-common.sh"
transfer=$(python3 -c 'import hashlib,pathlib,sys; print(hashlib.sha256(pathlib.Path(sys.argv[1],"manifest.json").read_bytes()).hexdigest()[:32])' "$1")
needed=$(python3 -c 'import pathlib,sys; print(sum(p.stat().st_size for p in pathlib.Path(sys.argv[1]).rglob("*") if p.is_file()) + 1073741824)' "$1")
active=$("${lab_ssh[@]}" 'sudo virsh -c qemu:///system list --name')
[[ -z $active ]] || { echo 'Save the active guest before transferring another.' >&2; exit 2; }
free=$("${lab_ssh[@]}" "stat -f --format='%a %S' /srv/pelican/lab" | python3 -c 'import sys; a,b=map(int,sys.stdin.read().split()); print(a*b)')
[[ $free -ge $needed ]] || { echo 'Not enough free guest storage; nothing uploaded.' >&2; exit 2; }
remote="/srv/pelican/lab/incoming/$transfer"
"${lab_ssh[@]}" "mkdir -p -m 0700 '$remote'"
# Quote the SSH transport for rsync; source file arguments are never evaluated as code.
rsh=$(python3 -c 'import shlex,sys; print(shlex.join(["ssh","-i",sys.argv[1],"-o","IdentitiesOnly=yes","-o","BatchMode=yes"]))' "${LAB_SSH_KEY:-$HOME/.ssh/KaliVM}")
rsync -aS --partial --protect-args -e "$rsh" -- "$1/" "ubuntu@$lab_ip:$remote/"
"${lab_ssh[@]}" "sudo /usr/local/sbin/lab-guest import '$remote'"
echo 'Guest imported, not started. Use start-windows.sh GUEST_NAME.'
