"""Registration and real Windows PowerShell/native stdin bridge, dummy keys only."""
import base64
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.pi.register_ssh_key import register


def public_key(fill=b'x'):
    blob = struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + fill * 32
    return 'ssh-ed25519 ' + base64.b64encode(blob).decode() + ' dummy-registration-test'


class SSHRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.home = Path(self.temp.name)
        self.key = public_key()
        self.encoded = base64.b64encode(self.key.encode()).decode()
        self.file = self.home / '.ssh/authorized_keys'

    def tearDown(self):
        self.temp.cleanup()

    def run_registration(self, encoded=None, **kwargs):
        return register(self.encoded if encoded is None else encoded, home=self.home, user='pi', **kwargs)

    def test_new_key_is_restricted_and_repeated_setup_preserves_bytes(self):
        self.assertTrue(self.run_registration())
        content = self.file.read_bytes()
        self.assertEqual(content, ('restrict ' + self.key + '\n').encode())
        self.assertFalse(self.run_registration())
        self.assertEqual(self.file.read_bytes(), content)

    def test_existing_entries_and_unicode_comments_remain_byte_identical(self):
        self.file.parent.mkdir()
        original = ('# Gerät mit anderem Schlüssel\r\nrestrict ' + public_key(b'y')).encode()
        self.file.write_bytes(original)
        self.run_registration()
        self.assertEqual(self.file.read_bytes(), original + ('\nrestrict ' + self.key + '\n').encode())

    def test_existing_key_with_or_without_options_is_not_duplicated(self):
        self.file.parent.mkdir()
        for prefix in ('', 'restrict ', 'command="echo hello",no-pty '):
            original = (prefix + self.key + '\n').encode()
            self.file.write_bytes(original)
            self.assertFalse(self.run_registration())
            self.assertEqual(self.file.read_bytes(), original)

    def test_key_in_comment_does_not_count_as_registered(self):
        self.file.parent.mkdir()
        self.file.write_text('# ' + self.key + '\n', encoding='utf-8')
        self.assertTrue(self.run_registration())

    def test_malformed_keys_fail_before_creating_any_ssh_file(self):
        invalid = ['not base64!', base64.b64encode(b'ssh-ed25519 invalid-data').decode(),
                   base64.b64encode((self.key + '\nextra').encode()).decode(),
                   base64.b64encode(b'ssh-rsa aGVsbG8=').decode()]
        for encoded in invalid:
            with self.assertRaises((ValueError, UnicodeError)):
                self.run_registration(encoded)
        self.assertFalse(self.file.parent.exists())

    def test_wrong_user_cannot_change_ssh_files(self):
        with self.assertRaises(ValueError):
            register(self.encoded, home=self.home, user='different-user')
        self.assertFalse(self.file.parent.exists())

    def test_linked_ssh_folder_or_authorized_keys_is_rejected(self):
        original = Path.is_symlink
        for linked in (self.file.parent, self.file):
            with patch.object(Path, 'is_symlink', lambda p: p == linked or original(p)):
                with self.assertRaises(ValueError):
                    self.run_registration()
            self.assertFalse(self.file.exists())

    def test_failed_atomic_replace_preserves_existing_file_and_removes_temporary(self):
        self.file.parent.mkdir()
        old = b'# existing entries\n'
        self.file.write_bytes(old)
        with patch('tools.pi.register_ssh_key.os.replace', side_effect=OSError('dummy write failure')):
            with self.assertRaises(OSError):
                self.run_registration()
        self.assertEqual(self.file.read_bytes(), old)
        self.assertEqual(list(self.file.parent.iterdir()), [self.file])

    @unittest.skipUnless(sys.platform == 'win32', 'Native Windows PowerShell bridge')
    def test_powershell51_native_bridge_preserves_script_and_exit_status_without_ssh(self):
        root = Path(__file__).resolve().parents[1]
        folder = self.home / 'paths with spaces'; folder.mkdir()
        sink, observed, payload, harness = (folder / name for name in ('native_sink.py', 'observed.json', 'payload.py', 'harness.ps1'))
        sink.write_text('import json,sys\nfrom pathlib import Path\n'
                        'data=sys.stdin.buffer.read()\ncompile(data,"<ssh-stdin>","exec")\n'
                        'Path(sys.argv[1]).write_text(json.dumps({"args":sys.argv[2:],"stdin":data.decode()}),encoding="utf-8")\n'
                        'sys.exit(23)\n', encoding='utf-8')
        source = (root / 'tools/pi/register_ssh_key.py').read_text(encoding='utf-8')
        payload.write_text(source, encoding='utf-8')
        quote = lambda value: "'" + str(value).replace("'", "''") + "'"
        harness.write_text("$ErrorActionPreference='Stop'\n. " + quote(root / 'windows/ssh_registration.ps1') + '\n'
                           '$script=Get-Content -LiteralPath ' + quote(payload) + ' -Raw -Encoding UTF8\n'
                           'Invoke-WetterstationKeyRegistration -Target pi@192.0.2.5 -PublicBase64 ' + quote(self.encoded)
                           + ' -RemoteScript $script -SshExecutable ' + quote(sys.executable)
                           + ' -PrefixArguments @(' + quote(sink) + ',' + quote(observed) + ')\n'
                           'exit $LASTEXITCODE\n', encoding='utf-8')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                                 '-File', str(harness)], capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 23, result.stderr.decode(errors='replace'))
        actual = json.loads(observed.read_text(encoding='utf-8'))
        self.assertEqual(actual['args'][-1], 'python3 - --key-base64 ' + self.encoded)
        self.assertIn('StrictHostKeyChecking=yes', actual['args'])
        self.assertEqual(actual['stdin'].replace('\r\n', '\n').rstrip('\n'), source.rstrip('\n'))
        setup = (root / 'windows/setup_ssh.ps1').read_text(encoding='utf-8')
        self.assertIn('Invoke-WetterstationKeyRegistration -Target', setup)
        self.assertNotIn('python3 -c', setup)


if __name__ == '__main__':
    unittest.main()
