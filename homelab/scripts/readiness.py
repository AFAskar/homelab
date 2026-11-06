#!/usr/bin/env python3
"""Read-only k3s/DNS candidate checks over existing SSH aliases; no root secrets."""
import argparse
import json
import subprocess


PROBE = r'''
emit() { printf '%s=%s\n' "$1" "$2"; }
emit hostname "$(hostname)"
emit architecture "$(uname -m)"
emit memory_kib "$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
emit memory_controller "$(cat /sys/fs/cgroup/cgroup.controllers 2>/dev/null)"
emit root_device "$(awk '$2 == "/" {print $1}' /proc/mounts)"
emit data_device "$(df -P /var/lib/rancher/k3s 2>/dev/null | tail -1 | awk '{print $1}')"
emit kernel_cmdline "$(cat /proc/cmdline)"
emit ethernet_carrier "$(cat /sys/class/net/eth0/carrier 2>/dev/null)"
emit lan_route "$(/sbin/ip route get 192.168.1.28 2>/dev/null | head -1)"
emit wired_ipv4 "$(/sbin/ip -o -4 addr show dev eth0 2>/dev/null | awk '{print $4}')"
emit k3s_version "$(/usr/local/bin/k3s --version 2>/dev/null | head -1)"
emit existing_service "$(test -f /etc/init.d/k3s && echo k3s)"
emit python "$(command -v python3)"
emit privilege "$(if doas -n true 2>/dev/null; then echo ready; else echo interactive; fi)"
emit temperature_millidegrees "$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null)"
'''


def assess(facts, expected_version):
    """Distinguish DNS provisioning blockers from embedded-etcd blockers."""
    common = []
    server = []
    if facts.get('architecture') != 'aarch64':
        common.append('Expected ARM64 Raspberry Pi OS')
    if int(facts.get('memory_kib') or 0) < 1800000:
        server.append('Less than the 2 GB server baseline')
    if 'memory' not in facts.get('memory_controller', '').split():
        server.append('Memory cgroup controller is unavailable')
    if expected_version not in facts.get('k3s_version', '').split():
        server.append('Installed k3s version does not match POS')
    if facts.get('privilege') != 'ready':
        common.append('doas requires authentication; use Ansible --ask-become-pass')
    if not facts.get('python'):
        common.append('Install python3 for Ansible modules after authenticated bootstrap')
    if facts.get('ethernet_carrier') != '1':
        common.append('Ethernet link is down')
    if 'dev eth0' not in facts.get('lan_route', ''):
        common.append('LAN traffic does not prefer the Ethernet interface')
    if facts.get('data_device', '').startswith('/dev/mmcblk'):
        server.append('k3s data is on SD; prepare persistent SSD storage for etcd')
    if facts.get('existing_service'):
        server.append('Existing standalone k3s must be inventoried and backed up before joining POS')
    return {'dns_prerequisites': common, 'control_plane_prerequisites': common + server}


def main():
    """Print a redacted JSON report without modifying the remote host."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='rpi4')
    parser.add_argument('--version', default='v1.36.2+k3s1')
    args = parser.parse_args()
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                             args.host, 'sh -s'], input=PROBE, text=True,
                            capture_output=True, timeout=30, check=True)
    facts = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    report = {'host': args.host, 'facts': facts, **assess(facts, args.version)}
    print(json.dumps(report, indent=2))
    return int(bool(report['control_plane_prerequisites']))


if __name__ == '__main__':
    raise SystemExit(main())
