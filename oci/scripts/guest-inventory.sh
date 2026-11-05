#!/usr/bin/env bash
# Read-only guest report. SSH host keys remain enforced; no secret file contents.
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: guest-inventory.sh ssh-host-or-user@host' >&2; exit 2; }
ssh -o BatchMode=yes -o ConnectTimeout=10 "$1" bash -s <<'REMOTE'
set -u
hostname
uname -m
cat /etc/os-release
free -m
lsblk -o NAME,SIZE,FSTYPE,UUID,MOUNTPOINTS
findmnt
ip -4 route
command -v docker wings tailscale
systemctl is-active docker wings tailscaled || true
ss -lntup
tailscale status || true
sudo -n du -sh /home /srv /var/lib/docker /var/lib/pelican /etc/pelican 2>/dev/null || true
sudo -n iptables-save || true
REMOTE
