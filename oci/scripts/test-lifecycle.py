#!/usr/bin/env python3
"""Offline safety regression: exact managed identity, graceful stop, approval gate."""
import json, os, pathlib, subprocess, tempfile, unittest
SCRIPTS=pathlib.Path(__file__).resolve().parent
class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)
        for name,code in {
            'terraform': '''#!/usr/bin/env python3
import sys
print({'windows_instance_id':'ocid1.instance.oc1.test.managed','region':'me-riyadh-1','oci_profile':'TEST'}[sys.argv[-1]])
''',
            'oci': '''#!/usr/bin/env python3
import json,os,sys
with open(os.environ['TEST_CALL_LOG'],'a') as f:f.write(json.dumps({'argv':sys.argv[1:],'region':os.environ.get('OCI_CLI_REGION'),'profile':os.environ.get('OCI_CLI_PROFILE')})+'\\n')
if 'get' in sys.argv: print(os.environ.get('TEST_STATE','STOPPED'))
'''
        }.items():
            p=self.path/name;p.write_text(code);p.chmod(0o755)
        self.env=os.environ.copy();self.env.update(PATH=str(self.path)+os.pathsep+self.env['PATH'],TEST_CALL_LOG=str(self.path/'calls'))
        self.env.pop('OCI_APPROVE_BILLABLE_START',None)
    def tearDown(self):self.tmp.cleanup()
    def run_script(self,name):return subprocess.run([str(SCRIPTS/(name+'-windows.sh'))],env=self.env,capture_output=True,text=True)
    def calls(self):return [json.loads(x) for x in (self.path/'calls').read_text().splitlines()]
    def test_start_requires_approval(self):
        self.assertNotEqual(self.run_script('start').returncode,0)
        self.assertTrue(all('action' not in c['argv'] for c in self.calls()))
    def test_approved_start_uses_managed_identity_and_region(self):
        self.env['OCI_APPROVE_BILLABLE_START']='yes';self.assertEqual(self.run_script('start').returncode,0)
        call=self.calls()[-1];self.assertIn('START',call['argv']);self.assertIn('ocid1.instance.oc1.test.managed',call['argv']);self.assertEqual(call['region'],'me-riyadh-1');self.assertEqual(call['profile'],'TEST')
    def test_already_running_does_not_start_again(self):
        self.env['TEST_STATE']='RUNNING';self.assertEqual(self.run_script('start').returncode,0)
        self.assertEqual(len(self.calls()),1)
    def test_stop_is_graceful(self):
        self.env['TEST_STATE']='RUNNING';self.assertEqual(self.run_script('stop').returncode,0)
        self.assertIn('SOFTSTOP',self.calls()[-1]['argv']);self.assertNotIn('STOP',self.calls()[-1]['argv'])
    def test_already_stopped_is_read_only(self):
        self.assertEqual(self.run_script('stop').returncode,0);self.assertEqual(len(self.calls()),1)
    def test_status_is_read_only(self):
        self.assertEqual(self.run_script('status').returncode,0);self.assertEqual(len(self.calls()),1);self.assertNotIn('action',self.calls()[0]['argv'])
if __name__=='__main__':unittest.main()
