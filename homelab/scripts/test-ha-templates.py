#!/usr/bin/env python3
"""Exercise rendered HA firewall/service templates without changing host rules."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import jinja2
import yaml

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = ROOT / 'homelab/ansible/templates'


class TemplateTests(unittest.TestCase):
    def render(self, name, **extra):
        values = {'node_ip': '192.168.1.23', 'node_interface': 'eth0',
                  'ha_virtual_ip': '192.168.1.250', 'ha_virtual_prefix': 24,
                  'ha_virtual_router_id': 61, 'ha_priority': 100,
                  'inventory_hostname': 'rpi4',
                  'groups': {'api_frontends': ['pos', 'rpi4']},
                  'hostvars': {'pos': {'node_ip': '192.168.1.28'},
                               'rpi4': {'node_ip': '192.168.1.23'}},
                  'adguard_version': 'v0.107.78',
                  'adguard_config_directory': '/etc/adguardhome',
                  'adguard_work_directory': '/var/lib/adguardhome',
                  'pi_wifi_recovery_address': '192.168.1.18', 'pi_wired_static': False}
        values.update(extra)
        return jinja2.Environment(undefined=jinja2.StrictUndefined).from_string(
            (TEMPLATES / name).read_text()).render(**values)

    def test_all_shell_templates_parse(self):
        for name in ['dns-firewall.sh.j2', 'k3s.openrc.j2', 'adguardhome.openrc.j2']:
            with self.subTest(template=name):
                subprocess.run(['sh', '-n'], input=self.render(name), text=True, check=True)

    def test_vrrp_is_unicast_and_faults_on_failed_service_health(self):
        config = self.render('keepalived.conf.j2')
        self.assertIn('unicast_src_ip 192.168.1.23', config)
        self.assertIn('192.168.1.28', config)
        self.assertIn('track_script', config)
        # An unweighted failed track script enters FAULT; a priority decrease
        # alone can leave the failed node owning the VIP.
        self.assertNotIn('weight ', config)
        self.assertIn('nopreempt', config)

    def test_dns_health_rejects_errors_and_accepts_duplicate_expected_answers(self):
        play = yaml.safe_load((ROOT / 'homelab/ansible/api-endpoint.yaml').read_text())[0]
        source = next(t['ansible.builtin.copy']['content'] for t in play['tasks']
                      if t.get('ansible.builtin.copy', {}).get('dest') == '/usr/local/sbin/homelab-ha-health')
        script = jinja2.Template(source).render(node_ip='192.168.1.23', hostvars={'pos': {'node_ip': '192.168.1.28'}})
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'k3s').write_text('#!/bin/sh\nexit 0\n')
            (directory / 'dig').write_text('#!/bin/sh\nprintf "%s\\n" "$DNS_ANSWER"\nexit "$DNS_STATUS"\n')
            for executable in directory.iterdir():
                executable.chmod(0o755)
            script = script.replace('/usr/local/bin/k3s', str(directory / 'k3s'))
            for status, answer, success in [(9, ';; no servers could be reached', False),
                                            (0, '', False), (0, '192.168.1.99', False),
                                            (0, '192.168.1.28\n192.168.1.28', True)]:
                with self.subTest(status=status, answer=answer):
                    environment = dict(os.environ, PATH=str(directory) + os.pathsep + os.environ['PATH'],
                                       DNS_STATUS=str(status), DNS_ANSWER=answer)
                    result = subprocess.run(['sh'], input=script, text=True, env=environment, capture_output=True)
                    self.assertEqual(result.returncode == 0, success)

    def test_firewall_preserves_other_chains_and_translates_vip_to_bound_listener(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            calls, rules = directory / 'calls', directory / 'rules'
            (directory / 'iptables').write_text(
                '#!/usr/bin/env python3\nimport json,os,sys\n'
                'with open(os.environ["CALL_LOG"],"a") as f:f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                'sys.exit(1 if "-C" in sys.argv else 0)\n')
            (directory / 'iptables-restore').write_text(
                '#!/usr/bin/env python3\nimport os,sys\n'
                'with open(os.environ["RULE_LOG"],"a") as f:f.write(sys.stdin.read())\n')
            for name in ['iptables', 'iptables-restore']:
                (directory / name).chmod(0o755)
            environment = dict(os.environ, PATH=str(directory) + os.pathsep + os.environ['PATH'],
                               CALL_LOG=str(calls), RULE_LOG=str(rules))
            subprocess.run(['sh'], input=self.render('dns-firewall.sh.j2'),
                           text=True, env=environment, check=True)
            generated = rules.read_text()
            self.assertIn('-d 192.168.1.250/32 -p udp --dport 53 -j DNAT --to-destination 192.168.1.23:5353', generated)
            self.assertIn('-A HOMELAB-DNS-IN -s 10.42.0.0/16', generated)
            self.assertNotIn('-F INPUT', generated)
            self.assertNotIn('-F PREROUTING', generated)
            self.assertNotIn('DOCKER', generated)
            for call in map(json.loads, calls.read_text().splitlines()):
                self.assertNotIn('-F', call)


if __name__ == '__main__':
    unittest.main()
