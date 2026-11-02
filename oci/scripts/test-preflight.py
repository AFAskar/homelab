#!/usr/bin/env python3
"""Quota regressions using plan/live API fixtures; no OCI credentials required."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('preflight.py'))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)
SHAPE = 'VM.Standard.E6.Flex'


def node(name, cores, memory, existing=False, actions=None):
    after = {'shape': SHAPE, 'compartment_id': 'compartment', 'availability_domain': 'ad',
             'shape_config': [{'ocpus': cores, 'memory_in_gbs': memory}]}
    before = None
    if existing:
        before = {'id': 'ocid.' + name}
        after['id'] = before['id']
    return {'address': 'oci_core_instance.wings["' + name + '"]', 'type': 'oci_core_instance',
            'change': {'before': before, 'after': after,
                       'actions': actions or (['no-op'] if existing else ['create'])}}


def live(cores, memory, shape=SHAPE):
    return NS(data=NS(shape=shape, compartment_id='compartment', availability_domain='ad',
                      lifecycle_state='RUNNING', shape_config=NS(ocpus=cores, memory_in_gbs=memory)))


class QuotaPreflight(unittest.TestCase):
    def checks(self, resources, instances=None, available=0):
        compute = Mock()
        compute.get_instance.side_effect = lambda instance_id: (instances or {})[instance_id]
        limits = Mock()
        limits.get_resource_availability.return_value = NS(data=NS(fractional_availability=None, available=available))
        pools = preflight.requirements({'resource_changes': resources}, compute, 'compartment', 'ad')
        return preflight.quota_checks(pools, limits, 'compartment', 'ad'), limits

    def test_fresh_layout_needs_66_gb_and_no_e4(self):
        checks, limits = self.checks([node('one', 4, 32), node('two', 2, 34)], available=48)
        memory = next(c for c in checks if c['limit'].endswith('memory-count'))
        self.assertEqual((memory['desired'], memory['needed'], memory['pass']), (66, 66, False))
        self.assertEqual({c['limit'] for c in checks}, {'standard-e6-core-count', 'standard-e6-memory-count'})
        self.assertEqual(limits.get_resource_availability.call_count, 2)

    def test_sufficient_e6_passes_without_any_e4_headroom(self):
        checks, limits = self.checks([node('one', 4, 32), node('two', 2, 34)], available=66)
        self.assertTrue(all(c['pass'] for c in checks))
        self.assertTrue(all('e6' in call.args[1] for call in limits.get_resource_availability.call_args_list))

    def test_existing_fleet_needs_no_extra_headroom(self):
        checks, limits = self.checks([node('one', 4, 32, True), node('two', 2, 34, True)],
                                    {'ocid.one': live(4, 32), 'ocid.two': live(2, 34)})
        self.assertEqual([c['needed'] for c in checks], [0, 0])
        self.assertTrue(all(c['pass'] for c in checks))
        limits.get_resource_availability.assert_not_called()

    def test_stopped_instance_still_counts_as_allocated(self):
        instance = live(2, 34)
        instance.data.lifecycle_state = 'STOPPED'
        checks, limits = self.checks([node('two', 2, 34, True)], {'ocid.two': instance})
        self.assertTrue(all(c['needed'] == 0 and c['pass'] for c in checks))
        limits.get_resource_availability.assert_not_called()

    def test_unknown_headroom_fails_for_new_capacity(self):
        checks, _ = self.checks([node('one', 4, 32)], available=None)
        self.assertFalse(any(c['pass'] for c in checks))

    def test_resize_uses_live_allocation_not_a_stale_before_value(self):
        resource = node('two', 2, 34, True, ['update'])
        resource['change']['before']['shape_config'] = [{'ocpus': 2, 'memory_in_gbs': 8}]
        checks, _ = self.checks([resource], {'ocid.two': live(2, 16)}, available=18)
        self.assertEqual([c['needed'] for c in checks], [0, 18])
        self.assertTrue(all(c['pass'] for c in checks))

    def test_planned_downsize_cannot_fund_another_resize(self):
        checks, _ = self.checks([node('one', 4, 16, True, ['update']), node('two', 2, 50, True, ['update'])],
                               {'ocid.one': live(4, 32), 'ocid.two': live(2, 34)}, available=15)
        self.assertEqual(checks[1]['needed'], 16)
        self.assertFalse(checks[1]['pass'])

    def test_replacement_requires_full_capacity(self):
        checks, _ = self.checks([node('two', 2, 34, True, ['create', 'delete'])], available=18)
        self.assertEqual(checks[1]['needed'], 34)
        self.assertFalse(checks[1]['pass'])

    def test_other_shape_allocation_is_not_credited(self):
        checks, _ = self.checks([node('two', 2, 34, True, ['update'])],
                               {'ocid.two': live(2, 34, 'VM.Standard.E4.Flex')}, available=18)
        self.assertEqual(checks[1]['needed'], 34)
        self.assertFalse(checks[1]['pass'])

    def test_fractional_availability_takes_precedence(self):
        pools = preflight.requirements({'resource_changes': [node('one', 1, 2)]}, Mock(), 'compartment', 'ad')
        limits = Mock()
        limits.get_resource_availability.return_value = NS(data=NS(fractional_availability=0.5, available=2))
        checks = preflight.quota_checks(pools, limits, 'compartment', 'ad')
        self.assertFalse(any(c['pass'] for c in checks))

    def test_scope_mismatch_and_unknown_values_fail_closed(self):
        resource = node('one', 4, 32)
        resource['change']['after']['availability_domain'] = 'another-ad'
        with self.assertRaisesRegex(ValueError, 'scope differs'):
            self.checks([resource])
        resource = node('one', 4, 32)
        resource['change']['after']['shape_config'] = []
        with self.assertRaisesRegex(ValueError, 'Unknown planned allocation'):
            self.checks([resource])


if __name__ == '__main__':
    unittest.main()
