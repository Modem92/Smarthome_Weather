"""Behavioral deployment checks; dummy files and mocked processes, never SSH."""
import json
import ast
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from tools.pi import controller, update
from tools.windows import updater
from wetterstation.paths import project_root
from wetterstation.storage.api_key_store import default_settings_path
from wetterstation.lifecycle import AppSession


class DeploymentWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.base = Path(self.temp.name)
        self.root = self.base / 'pi'; self.root.mkdir()
        self.proc = self.base / 'proc'; self.proc.mkdir()
        self.record = {'schema': 1, 'root': str(self.root.resolve()), 'pid': 42,
                       'start': '123', 'nonce': 'old-nonce', 'args': ['--widget-demo'],
                       'orderly_stop': True, 'ready': True}
        process = self.proc / '42'; process.mkdir()
        (process / 'stat').write_text('42 (weather app) S ' + '0 '*18 + '123')
        (process / 'environ').write_bytes(b'DISPLAY=:0\0API_KEY=dummy-never-copy\0XAUTHORITY=/home/pi/.Xauthority\0')

    def tearDown(self):
        self.temp.cleanup()

    def test_nested_code_keeps_original_settings_and_budget_root(self):
        actual = Path(__file__).resolve().parents[1]
        self.assertEqual(default_settings_path(), actual / 'private/settings.json')
        self.assertEqual(project_root(actual / 'wetterstation/ui/app.py'), actual)
        self.assertEqual(project_root(self.root / 'app.py'), self.root.resolve())

    def test_snapshot_has_no_private_archives_or_budget_and_is_independent(self):
        actual = Path(__file__).resolve().parents[1]
        hashes = updater.snapshot(actual, self.root)
        self.assertFalse((self.root / 'private').exists())
        self.assertFalse((self.root / 'archive').exists())
        self.assertFalse((self.root / '.git').exists())
        self.assertTrue((self.root / 'tools/legacy/pi_live_transfer.py').is_file())
        source_hash = update.digest((actual / 'app.py').read_bytes())
        (self.root / 'app.py').write_text('# snapshot only')
        self.assertEqual(update.digest((actual / 'app.py').read_bytes()), source_hash)
        self.assertEqual(hashes['app.py'], source_hash)

    def test_identity_rejects_legacy_app_duplicate_processes_and_pid_reuse(self):
        with patch.object(controller.os, 'getuid', return_value=0, create=True):
            self.assertEqual(controller.identity(self.root, self.record, [42], self.proc), 42)
            for record, pids in ((None, [42]), (self.record, [42, 43]),
                                 ({**self.record, 'start': 'reused'}, [42]),
                                 ({**self.record, 'args': ['--unknown']}, [42])):
                with self.assertRaises(update.UpdateError):
                    controller.identity(self.root, record, pids, self.proc)

    def test_restart_copies_only_desktop_environment(self):
        env = controller.environment(42, self.proc)
        self.assertEqual(env, {'DISPLAY': ':0', 'XAUTHORITY': '/home/pi/.Xauthority'})
        self.assertNotIn('API_KEY', env)

    def test_no_desktop_session_is_rejected_before_stopping(self):
        (self.proc / '42/environ').write_bytes(b'API_KEY=dummy\0')
        with self.assertRaisesRegex(update.UpdateError, 'Desktopsitzung'):
            controller.environment(42, self.proc)

    def test_changed_session_never_signals_any_process(self):
        with patch.object(controller, 'session', return_value=self.record), \
             patch.object(controller, 'identity', return_value=42), \
             patch.object(update, 'running_processes', return_value=[42]), \
             patch.object(controller.os, 'kill') as kill:
            with self.assertRaises(update.UpdateError):
                controller.stop(self.root, {**self.record, 'running': True, 'nonce': 'different'})
            kill.assert_not_called()

    def test_closed_program_is_never_restarted(self):
        with patch.object(controller.subprocess, 'Popen') as launch:
            self.assertEqual(controller.restart(self.root, {'running': False}), 'closed')
            launch.assert_not_called()

    def test_failed_install_never_restarts(self):
        with patch.object(update, 'verify_archive'), \
             patch.object(controller, 'check', return_value={'running': False}), \
             patch.object(controller, 'stop'), \
             patch.object(update, 'install', side_effect=update.UpdateError('failed')), \
             patch.object(controller, 'restart') as launch:
            with self.assertRaises(update.UpdateError):
                controller.transaction(self.root, self.base/'package.zip', 'dummy', {'running': False})
            launch.assert_not_called()

    def test_successful_update_restarts_only_after_install_and_reports_backup(self):
        calls = []
        before = {'running': True}
        with patch.object(update, 'verify_archive', return_value={'release': 'test'}), \
             patch.object(controller, 'check', return_value=before), \
             patch.object(controller, 'stop', side_effect=lambda *_: calls.append('stop')), \
             patch.object(update, 'install', side_effect=lambda *a, **k: calls.append('install') or self.base/'backup'), \
             patch.object(controller, 'restart', side_effect=lambda *_: calls.append('restart') or 'restarted'):
            result = controller.transaction(self.root, self.base/'package.zip', 'dummy', before)
        self.assertEqual(calls, ['stop', 'install', 'restart'])
        self.assertEqual(result['state'], 'restarted')
        self.assertEqual(result['backup'], str(self.base/'backup'))

    def test_failed_restart_reports_installed_version_and_backup(self):
        with patch.object(update, 'verify_archive'), \
             patch.object(controller, 'check', return_value={'running': False}), \
             patch.object(controller, 'stop'), \
             patch.object(update, 'install', return_value=self.base/'backup'), \
             patch.object(controller, 'restart', side_effect=update.UpdateError('start failed')):
            with self.assertRaisesRegex(update.UpdateError, 'Programmupdate installiert;.*backup'):
                controller.transaction(self.root, self.base/'package.zip', 'dummy', {'running': False})

    def test_stale_or_failed_restart_never_counts_as_ready(self):
        child = Mock(pid=43); child.poll.return_value = 1
        with patch.object(update, 'running_processes', return_value=[]), \
             patch.object(controller.subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(update.UpdateError, 'Wiederstart'):
                controller.restart(self.root, {**self.record, 'running': True, 'env': {'DISPLAY': ':0'}})

    def test_verified_child_restarts_in_original_mode_and_desktop(self):
        child = Mock(pid=43); child.poll.return_value = None
        after = {**self.record, 'pid': 43, 'nonce': 'new-nonce'}
        with patch.object(update, 'require_stopped'), \
             patch.object(update, 'running_processes', return_value=[43]), \
             patch.object(controller.subprocess, 'Popen', return_value=child) as launch, \
             patch.object(controller, 'session', return_value=after), \
             patch.object(controller, 'start_token', return_value='123'), \
             patch.object(controller, 'identity', return_value=43):
            state = controller.restart(self.root, {**self.record, 'running': True, 'env': {'DISPLAY': ':7'}})
        self.assertEqual(state, 'restarted')
        self.assertEqual(launch.call_args.args[0][-1], '--widget-demo')
        self.assertEqual(launch.call_args.kwargs['env']['DISPLAY'], ':7')
        self.assertTrue(launch.call_args.kwargs['start_new_session'])

    def test_ssh_never_prompts_for_password_or_accepts_changed_host(self):
        config = {'user': 'pi', 'host': '192.0.2.5'}
        with patch.object(updater.subprocess, 'run', return_value=Mock(returncode=0, stdout='ok')) as run:
            self.assertEqual(updater.run_remote(config, self.base/'key.pub', ['true']), 'ok')
        args = run.call_args.args[0]
        for required in ('BatchMode=yes', 'IdentitiesOnly=yes', 'PasswordAuthentication=no', 'StrictHostKeyChecking=yes'):
            self.assertIn(required, args)

    def test_unknown_ssh_errors_are_sanitized(self):
        with patch.object(updater.subprocess, 'run', return_value=Mock(returncode=255, stderr='dummy-sensitive-untrusted-server-output')):
            with self.assertRaises(update.UpdateError) as error:
                updater.run_remote({'user':'pi','host':'192.0.2.5'}, self.base/'key.pub', ['true'])
            self.assertNotIn('dummy-sensitive', str(error.exception))

    def test_staged_workflow_probes_read_only_and_uploads_before_applying(self):
        actual = Path(__file__).resolve().parents[1]
        frozen = self.base / 'snapshot'; frozen.mkdir()
        updater.snapshot(actual, frozen)
        ready = update.build(frozen, '2026-10-25-probe-test', keep_layout=True)
        commands = []
        def remote(config, public, args, **kwargs):
            commands.append((args, kwargs))
            if len(commands) == 1:
                source = args[2]
                # Compile and execute the exact non-mutating bootstrap. Replace
                # only its final check call; the real Pi is never contacted.
                tree = ast.parse(source)
                with patch.dict(sys.modules):
                    namespace = {}
                    exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), '<probe>', 'exec'), namespace)
                    self.assertTrue(callable(namespace['c']['check']))
                cmdline = subprocess.list2cmdline(['ssh.exe', *updater.ssh_options(public), 'pi@192.0.2.5', ' '.join(__import__('shlex').quote(a) for a in args)])
                self.assertLess(len(cmdline), 32700)
                return json.dumps({'running': False})
            if args[0] == 'python3' and args[1].endswith('/controller.py'):
                return json.dumps({'state': 'closed', 'backup': '/dummy/backup', 'release': 'test'})
            return ''
        config = {'user': 'pi', 'host': '192.0.2.5', 'relative_target': update.RELATIVE_TARGET}
        with patch.object(updater, 'configuration', return_value=(config, self.base/'key.pub')), \
             patch.object(updater, 'run_remote', side_effect=remote):
            result = updater.deploy(self.root, frozen, ready, lambda _: None)
        self.assertEqual(result['state'], 'closed')
        self.assertEqual(sum(bool(options.get('copy')) for _, options in commands), 4)
        self.assertIn('apply', commands[-1][0])
        self.assertFalse((frozen/'private').exists())

    def test_missing_setup_never_connects(self):
        with patch.object(updater.subprocess, 'run') as run:
            with self.assertRaisesRegex(update.UpdateError, 'Set up SSH once.cmd'):
                updater.perform(self.root, lambda _: None)
            run.assert_not_called()

    def test_linux_signal_handler_only_requests_orderly_tk_close(self):
        window, preview = Mock(), Mock()
        session = AppSession(self.root, window, preview, [])
        session._signal()
        preview.close.assert_not_called()
        window.destroy.assert_not_called()
        session._poll()
        preview.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
