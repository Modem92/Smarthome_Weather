"""Register one public key, executed from SSH stdin; never read private keys."""
import argparse
import base64
import getpass
import os
from pathlib import Path
import shlex
import struct
import sys
import tempfile


def register(encoded_key, *, home=None, user=None):
    if (getpass.getuser() if user is None else user) != 'pi':
        raise ValueError('Falscher Pi-Benutzer.')
    key = base64.b64decode(encoded_key, validate=True).decode('utf-8')
    if '\n' in key or '\r' in key or len(key) > 2000:
        raise ValueError('Ungueltiger oeffentlicher Schluessel.')
    fields = key.split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519':
        raise ValueError('Ed25519-Schluessel erforderlich.')
    blob = base64.b64decode(fields[1], validate=True)
    prefix = struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32)
    if len(blob) != len(prefix) + 32 or not blob.startswith(prefix):
        raise ValueError('Ungueltiger Ed25519-Schluessel.')
    home = (Path.home() if home is None else Path(home)).resolve()
    folder = home / '.ssh'
    if folder.is_symlink():
        raise ValueError('Verknuepfter SSH-Ordner; nichts ersetzt.')
    folder.mkdir(mode=0o700, exist_ok=True)
    folder.chmod(0o700)
    path = folder / 'authorized_keys'
    if path.is_symlink():
        raise ValueError('Verknuepfte SSH-Datei; nichts ersetzt.')
    old = path.read_bytes() if path.exists() else b''
    for line in old.decode('utf-8').splitlines():
        try:
            tokens = shlex.split(line, comments=True)
        except ValueError:
            continue
        for index in (0, 1):
            if tokens[index:index+2] == fields[:2]:
                path.chmod(0o600)
                return False
    data = old + (b'' if not old or old.endswith(b'\n') else b'\n')
    data += ('restrict ' + key + '\n').encode('utf-8')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=folder, prefix='.wetterstation-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key-base64', required=True)
    args = parser.parse_args()
    try:
        added = register(args.key_base64)
        print('Wetterstation-Schluessel eingerichtet.' if added else 'Wetterstation-Schluessel bereits vorhanden.')
        print('Kein Programmstart.')
        return 0
    except Exception:
        print('Pi-Schluesselregistrierung angehalten; vorhandene SSH-Dateien und Benutzer pruefen.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
