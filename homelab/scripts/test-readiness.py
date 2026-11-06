#!/usr/bin/env python3
"""Check Pi readiness classification without accessing or changing a host."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('readiness', Path(__file__).with_name('readiness.py'))
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class ReadinessTests(unittest.TestCase):
    def facts(self):
        return {'architecture': 'aarch64', 'memory_kib': '3887800',
                'memory_controller': 'cpuset cpu io memory pids',
                'privilege': 'ready', 'python': '/usr/bin/python3',
                'ethernet_carrier': '1', 'lan_route': '192.168.1.28 dev eth0',
                'data_device': '/dev/sda1', 'k3s_version': 'k3s version v1.36.2+k3s1 (test)'}

    def test_sd_blocks_etcd_without_blocking_dns(self):
        facts = self.facts()
        facts['data_device'] = '/dev/mmcblk0p2'
        result = readiness.assess(facts, 'v1.36.2+k3s1')
        self.assertEqual(result['dns_prerequisites'], [])
        self.assertTrue(any('SD' in item for item in result['control_plane_prerequisites']))

    def test_cgroup_v2_memory_controller_is_authoritative(self):
        facts = self.facts()
        facts['kernel_cmdline'] = 'cgroup_disable=memory cgroup_enable=memory'
        self.assertEqual(readiness.assess(facts, 'v1.36.2+k3s1')['control_plane_prerequisites'], [])

    def test_standalone_cluster_is_never_treated_as_a_fresh_join(self):
        facts = self.facts()
        facts['existing_service'] = 'k3s'
        self.assertTrue(any('standalone' in item for item in readiness.assess(facts, 'v1.36.2+k3s1')['control_plane_prerequisites']))

    def test_wifi_and_missing_privileges_are_reported(self):
        facts = self.facts()
        facts.update(privilege='interactive', lan_route='192.168.1.28 dev wlan0')
        self.assertEqual(len(readiness.assess(facts, 'v1.36.2+k3s1')['dns_prerequisites']), 2)


if __name__ == '__main__':
    unittest.main()
