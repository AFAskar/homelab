#!/usr/bin/env python3
"""Offline regression: a nested guest must never power off its shared Wings host."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        programs = {
            'terraform': '''#!/usr/bin/env python3
import json,os,sys
v=sys.argv[-1]
if v=='lab_host': print(json.dumps({'id':'ocid1.instance.oc1.test.wings02','private_ip':'10.10.50.146','shared_with_wings':os.environ.get('TEST_SHARED','yes')=='yes'}))
else: print({'region':'me-riyadh-1','oci_profile':'TEST'}[v])
''',
            'oci': '''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['TEST_CALL_LOG'],'a') as f:f.write(json.dumps({'tool':'oci','argv':sys.argv[1:]})+'\\n')
print(os.environ.get('TEST_STATE','RUNNING'))
''',
            'ssh': '''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['TEST_CALL_LOG'],'a') as f:f.write(json.dumps({'tool':'ssh','argv':sys.argv[1:]})+'\\n')
print('guest operation accepted')
''',
        }
        for name, code in programs.items():
            path = self.path / name
            path.write_text(code)
            path.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(PATH=str(self.path) + os.pathsep + self.env['PATH'], TEST_CALL_LOG=str(self.path / 'calls'))

    def tearDown(self):
        self.tmp.cleanup()

    def invoke(self, command, name='mpmb-windows11'):
        return subprocess.run([str(SCRIPTS / (command + '-windows.sh')), name], env=self.env, capture_output=True, text=True)

    def calls(self):
        path = self.path / 'calls'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def assert_no_host_action(self):
        self.assertFalse(any(c['tool'] == 'oci' and 'action' in c['argv'] for c in self.calls()))

    def test_start_only_starts_the_named_guest(self):
        self.assertEqual(self.invoke('start').returncode, 0)
        call = self.calls()[-1]
        self.assertEqual(call['tool'], 'ssh')
        self.assertIn('ubuntu@10.10.50.146', call['argv'])
        self.assertEqual(call['argv'][-1], "sudo /usr/local/sbin/lab-guest start 'mpmb-windows11'")
        self.assert_no_host_action()

    def test_stop_saves_ram_and_never_stops_wings(self):
        self.assertEqual(self.invoke('stop').returncode, 0)
        self.assertEqual(self.calls()[-1]['argv'][-1], "sudo /usr/local/sbin/lab-guest save 'mpmb-windows11'")
        self.assert_no_host_action()

    def test_old_billable_start_flag_cannot_trigger_a_host_action(self):
        self.env['OCI_APPROVE_BILLABLE_START'] = 'yes'
        self.assertEqual(self.invoke('start').returncode, 0)
        self.assert_no_host_action()

    def test_wrong_host_type_is_rejected(self):
        self.env['TEST_SHARED'] = 'no'
        self.assertNotEqual(self.invoke('start').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_invalid_guest_name_is_not_passed_to_a_shell(self):
        self.assertNotEqual(self.invoke('start', 'bad;command').returncode, 0)
        self.assertEqual(self.calls(), [])

    def test_status_of_a_stopped_host_is_read_only(self):
        self.env['TEST_STATE'] = 'STOPPED'
        self.assertEqual(self.invoke('status').returncode, 0)
        self.assertFalse(any(c['tool'] == 'ssh' for c in self.calls()))
        self.assert_no_host_action()


if __name__ == '__main__':
    unittest.main()
