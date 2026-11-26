"""Maintenance only touches allowlisted outputs, after archive verification."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock
import zipfile
from tools.workspace_maintenance import archive_outputs,candidates,migrate_runtime,hashes


class WorkspaceMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.base=Path(self.temp.name);self.root=self.base/'workspace';self.root.mkdir()

    def tearDown(self):self.temp.cleanup()

    def test_copy_verify_before_switch_never_overwrites_different_runtime(self):
        source=self.root/'build/designer-runtime';source.mkdir(parents=True);(source/'library').write_bytes(b'dummy-runtime')
        target=self.base/'outside/runtime';check=Mock()
        migrate_runtime(self.root,target,check)
        self.assertEqual(hashes(source),hashes(target));check.assert_called_once_with(target)
        (target/'library').write_bytes(b'other-runtime')
        with self.assertRaises(ValueError):migrate_runtime(self.root,target,check)
        self.assertTrue(source.exists())

    def test_archive_preserves_bytes_and_unknown_directories(self):
        known=self.root/'build/checks/designer-frozen-fixture';known.mkdir(parents=True);(known/'sample').write_bytes(b'dummy-data')
        unknown=self.root/'build/checks/my-own-files';unknown.mkdir();(unknown/'keep').write_bytes(b'keep')
        paths=candidates(self.root);self.assertEqual(paths,[known])
        output=archive_outputs(self.root,paths)
        with zipfile.ZipFile(output) as archive:self.assertEqual(archive.read('build/checks/designer-frozen-fixture/sample'),b'dummy-data')
        self.assertFalse(known.exists());self.assertTrue((unknown/'keep').exists())

    def test_private_target_is_never_removed(self):
        private=self.root/'private';private.mkdir();(private/'dummy').write_bytes(b'keep')
        with self.assertRaises(ValueError):archive_outputs(self.root,[private])
        self.assertTrue((private/'dummy').exists())
