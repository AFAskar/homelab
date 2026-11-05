#!/usr/bin/env python3
"""Exercise failed-save recovery without running or changing a real guest."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('guest_bundle', Path(__file__).with_name('guest-bundle.py'))
guest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guest)


class FailedSave(unittest.TestCase):
    def exercise(self, payload):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'test-guest'
            directory.mkdir()
            checkpoint = directory / 'state.save'

            def run(*args, **kwargs):
                if args[0] == 'domstate':
                    return 'running\n'
                if args[0] == 'save':
                    checkpoint.write_bytes(payload)
                    raise subprocess.CalledProcessError(1, ['virsh', 'save'])
                self.fail('Unexpected libvirt operation: ' + args[0])

            with patch.object(guest, 'ROOT', root), patch.object(guest, 'host_only'), patch.object(guest, 'run', side_effect=run), patch.object(guest.shutil, 'chown'):
                with self.assertRaises(subprocess.CalledProcessError):
                    guest.lifecycle(SimpleNamespace(name='test-guest', command='save'))
            return checkpoint.exists(), checkpoint.read_bytes() if checkpoint.exists() else None

    def test_empty_placeholder_is_removed(self):
        self.assertEqual(self.exercise(b''), (False, None))

    def test_nonempty_recovery_data_is_preserved(self):
        self.assertEqual(self.exercise(b'possible RAM recovery'), (True, b'possible RAM recovery'))


class HostSerialization(unittest.TestCase):
    def test_overlapping_guest_mutations_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(guest, 'LOCKFILE', Path(temporary) / 'guest.lock'), patch.object(guest.os, 'geteuid', return_value=0):
                with guest.exclusive_host_operation():
                    with self.assertRaisesRegex(ValueError, 'Another guest'):
                        with guest.exclusive_host_operation():
                            self.fail('Concurrent guest mutation was admitted')
                with guest.exclusive_host_operation():
                    pass


if __name__ == '__main__':
    unittest.main()
