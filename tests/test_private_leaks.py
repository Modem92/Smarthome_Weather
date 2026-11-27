"""Leak guard: denylist loading and staged/tracked/history scans with sample data only."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from tools import check_private_leaks as leaks

SAMPLE_KEY = 'dummy0000key1111sample2222value33'
SAMPLE_HOST = '198.51.100.23'  # documentation range (RFC 5737), never a real device


def git(repo, *args):
    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True)


class LeakGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.private = base / 'private'
        self.private.mkdir()
        (self.private / 'settings.json').write_text(json.dumps({
            'openweather_api_key': SAMPLE_KEY, 'location': 'Musterdorf, 99999', 'dashboard': {}}), encoding='utf-8')
        (self.private / 'pi-update.json').write_text(json.dumps({
            'host': SAMPLE_HOST, 'relative_target': 'sample-dir/Station', 'user': 'pi'}), encoding='utf-8')
        self.denylist = self.private / 'leak-denylist.txt'
        self.denylist.write_text(f'# comment\nMusterdorf\nabc\ndir: {self.private}\n', encoding='utf-8')
        self.repo = base / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.email', 'test@example.invalid')
        git(self.repo, 'config', 'user.name', 'Test')
        git(self.repo, 'config', 'core.hooksPath', str(base / 'no-hooks'))

    def tearDown(self):
        self.tmp.cleanup()

    def run_check(self, *mode):
        return leaks.main([*mode, '--denylist', str(self.denylist), '--repo', str(self.repo)])

    def write(self, name, text):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def test_denylist_reads_literals_and_private_json_without_short_entries(self):
        entries = dict(leaks.load_denylist(self.denylist))
        self.assertEqual(entries['musterdorf'], 'leak-denylist.txt line 2')
        self.assertEqual(entries[SAMPLE_KEY], 'settings.json:openweather_api_key')
        self.assertEqual(entries[SAMPLE_HOST], 'pi-update.json:host')
        self.assertIn('sample-dir/station', entries)
        self.assertNotIn('abc', entries)  # too short, would match ordinary code
        self.assertNotIn('pi', entries)   # user field is not collected

    def test_staged_secret_is_blocked_and_value_not_printed(self):
        self.write('a.txt', 'clean\n')
        git(self.repo, 'add', 'a.txt')
        git(self.repo, 'commit', '-qm', 'init')
        self.write('a.txt', f'clean\nkey = "{SAMPLE_KEY.upper()}"\n')
        git(self.repo, 'add', 'a.txt')
        with mock.patch('sys.stderr') as stderr:
            code = self.run_check('--staged')
        output = ''.join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(code, 1)
        self.assertIn('a.txt:2', output)
        self.assertIn('settings.json:openweather_api_key', output)
        self.assertNotIn(SAMPLE_KEY.lower(), output.lower())

    def test_clean_change_passes_but_touched_file_with_old_leak_is_blocked(self):
        self.write('docs/x.md', 'Ort: Musterdorf\n')
        self.write('docs/y.md', 'Ort: Potsdam\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'old leak already in history')
        self.write('docs/y.md', 'Ort: Potsdam\nmore\n')
        git(self.repo, 'add', '.')
        self.assertEqual(self.run_check('--staged'), 0)
        self.write('docs/x.md', 'Ort: Musterdorf\nOrt: Potsdam\n')
        git(self.repo, 'add', '.')
        self.assertEqual(self.run_check('--staged'), 1)

    def test_non_ascii_path_and_plus_prefixed_lines_are_checked(self):
        # Git quotes umlaut paths and shows "++ x" as "+++ x"; neither may hide a leak.
        self.write('docs/Übersicht.md', f'++ note\nssh {SAMPLE_HOST}\n')
        git(self.repo, 'add', '.')
        self.assertEqual(self.run_check('--staged'), 1)

    def test_utf16_content_is_checked(self):
        (self.repo / 'export.ps1').write_bytes(f'$k = "{SAMPLE_KEY}"\r\n'.encode('utf-16'))
        git(self.repo, 'add', '.')
        self.assertEqual(self.run_check('--staged'), 1)

    def test_missing_dir_warns(self):
        self.denylist.write_text(f'dir: {self.private / "moved"}\n', encoding='utf-8')
        with mock.patch('sys.stderr') as stderr:
            entries = leaks.load_denylist(self.denylist)
        output = ''.join(call.args[0] for call in stderr.write.call_args_list)
        self.assertEqual(entries, [])
        self.assertIn('WARNING', output)

    def test_file_name_is_checked(self):
        self.write('notes/musterdorf.txt', 'harmless\n')
        git(self.repo, 'add', '.')
        self.assertEqual(self.run_check('--staged'), 1)

    def test_tracked_and_history_modes(self):
        self.write('b.txt', f'ssh {SAMPLE_HOST}\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'leak')
        self.assertEqual(self.run_check('--tracked'), 1)
        self.write('b.txt', 'ssh <pi-address>\n')
        git(self.repo, 'commit', '-qam', 'fix')
        self.assertEqual(self.run_check('--tracked'), 0)
        self.assertEqual(self.run_check('--history'), 1)

    def test_missing_denylist_skips_with_success(self):
        code = leaks.main(['--denylist', str(self.private / 'missing.txt'), '--repo', str(self.repo)])
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
