#!/usr/bin/env python3
"""Evaluate the real Ansible migration guards against foreign and fresh state."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]


class MigrationGuards(unittest.TestCase):
    def test_foreign_state_and_sd_requirements(self):
        play = yaml.safe_load((ROOT / 'homelab/ansible/cluster.yaml').read_text())[0]
        assertions = {task['name']: task['ansible.builtin.assert']['that']
                      for task in play['tasks'] if 'ansible.builtin.assert' in task}
        server = assertions['Refuse a foreign standalone server datastore']
        agent = assertions['Refuse a foreign agent installation']
        unidentified = assertions['Refuse unidentified existing server state']
        storage = assertions['Refuse embedded etcd on the Pi SD card']
        cases = [
            ('foreign server', server, False,
             {'ha_server_ca': {'stat': {'exists': True, 'checksum': 'foreign'}}}),
            ('same cluster server', server, True,
             {'ha_server_ca': {'stat': {'exists': True, 'checksum': 'production'}}}),
            ('fresh server', server, True,
             {'ha_server_ca': {'stat': {'exists': False}}}),
            ('foreign agent', agent, False,
             {'ha_agent_ca': {'stat': {'exists': True, 'checksum': 'foreign'}}}),
            ('same cluster agent', agent, True,
             {'ha_agent_ca': {'stat': {'exists': True, 'checksum': 'production'}}}),
            ('unidentified datastore', unidentified, False,
             {'ha_datastore': {'stat': {'exists': True}}, 'ha_server_ca': {'stat': {'exists': False}}}),
            ('unapproved SD', storage, False,
             {'ha_storage': {'stdout': '/dev/mmcblk0p2 ext4'}, 'ha_allow_sdcard': False}),
            ('selected SD', storage, True,
             {'ha_storage': {'stdout': '/dev/mmcblk0p2 ext4'}, 'ha_allow_sdcard': True}),
            ('SSD', storage, True,
             {'ha_storage': {'stdout': '/dev/sda1 ext4'}, 'ha_allow_sdcard': False}),
        ]
        tasks = [{'name': name, 'vars': variables,
                  'ansible.builtin.assert': {'that': expression if expected else 'not (' + expression + ')'}}
                 for name, expression, expected, variables in cases]
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            inventory = {'all': {'hosts': {
                'rpi4': {'ansible_connection': 'local'},
                'pos': {'ha_server_ca': {'stat': {'exists': True, 'checksum': 'production'}}}}}}
            (directory / 'inventory.yaml').write_text(yaml.safe_dump(inventory))
            (directory / 'test.yaml').write_text(yaml.safe_dump([{
                'name': 'Offline migration policy tests', 'hosts': 'rpi4',
                'gather_facts': False, 'vars': {'k3s_bootstrap_host': 'pos'}, 'tasks': tasks}]))
            executable = Path(sys.executable).with_name('ansible-playbook')
            result = subprocess.run([str(executable), '-i', str(directory / 'inventory.yaml'),
                                     str(directory / 'test.yaml')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
