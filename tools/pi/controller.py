"""Standalone staged Pi transaction, including verified stop and desktop restart."""
from contextlib import contextmanager
import argparse
import getpass
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time

try:
    from . import update
except ImportError:
    import update

SESSION = '.wetterstation-session.json'
FLAGS = {'--mock-preview', '--widget-demo', '--show-rain-map', '--open-settings'}
DESKTOP_ENV = {'DISPLAY', 'WAYLAND_DISPLAY', 'XAUTHORITY', 'XDG_RUNTIME_DIR',
               'DBUS_SESSION_BUS_ADDRESS', 'XDG_SESSION_TYPE'}


def start_token(pid, proc=Path('/proc')):
    return (proc / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]


def session(root):
    path = update.safe_path(root, SESSION)
    if not path.is_file():
        return None
    value = update.read_json(path, 16_000)
    if not isinstance(value, dict) or value.get('schema') != 1:
        raise update.UpdateError('Ungueltige Programm-Laufzeitkennung.')
    return value


def identity(root, record, pids, proc=Path('/proc')):
    if not record or type(record.get('pid')) is not int or record['pid'] <= 1:
        raise update.UpdateError('Aeltere Pi-Version: Wetterstation fuer die erste Umstellung bitte einmal selbst schliessen.')
    pid = record['pid']
    if pids != [pid] or record.get('root') != str(root.resolve()) or record.get('orderly_stop') is not True:
        raise update.UpdateError('Die laufende Wetterstation konnte nicht eindeutig zugeordnet werden.')
    if (proc / str(pid)).stat().st_uid != os.getuid() or record.get('start') != start_token(pid, proc):
        raise update.UpdateError('Die Prozessidentitaet hat sich geaendert.')
    args = record.get('args')
    if not isinstance(args, list) or any(not isinstance(a, str) or a not in FLAGS for a in args):
        raise update.UpdateError('Unbekannter Startmodus; kein automatisches Beenden.')
    return pid


def environment(pid, proc=Path('/proc')):
    env = {}
    for item in (proc / str(pid) / 'environ').read_bytes().split(b'\0'):
        key, sep, value = item.partition(b'=')
        name = key.decode('utf-8', 'strict')
        if sep and name in DESKTOP_ENV:
            text = value.decode('utf-8', 'strict')
            if len(text) > 4096 or '\n' in text or '\r' in text:
                raise update.UpdateError('Ungueltige Desktopsitzung.')
            env[name] = text
    if not env.get('DISPLAY') and not env.get('WAYLAND_DISPLAY'):
        raise update.UpdateError('Keine wiederverwendbare Pi-Desktopsitzung erkannt.')
    return env


def check(root, user='pi'):
    if sys.platform != 'linux' or sys.version_info < (3, 11) or getpass.getuser() != user:
        raise update.UpdateError('Falsches Pi-Zielsystem oder Python-Version.')
    home = Path.home().resolve()
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.resolve().is_relative_to(home):
        raise update.UpdateError('Ungueltiger Pi-Installationspfad.')
    root = root.resolve()
    for name in ('app.py', 'private/settings.json'):
        if not update.safe_path(root, name).is_file():
            raise update.UpdateError('Bestehende Pi-Installation fehlt.')
    if (root / update.MARKER).exists():
        raise update.UpdateError('Vorheriges Update unvollstaendig; zuerst wiederherstellen.')
    import tkinter
    import PIL
    import cryptography
    from zoneinfo import ZoneInfo
    ZoneInfo('Europe/Berlin')
    total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
    if shutil.disk_usage(root.parent).free < total * 2 + 40_000_000:
        raise update.UpdateError('Nicht genug freier Speicher fuer Paket und Sicherung.')
    pids = update.running_processes(root)
    if pids:
        record = session(root)
        pid = identity(root, record, pids)
        return {'running': True, 'pid': pid, 'start': record['start'],
                'nonce': record['nonce'], 'args': record['args'], 'env': environment(pid)}
    return {'running': False}


def stop(root, before, timeout=30):
    if not before['running']:
        update.require_stopped(root, update.running_processes)
        return
    record = session(root)
    pid = identity(root, record, update.running_processes(root))
    if any(record.get(k) != before.get(k) for k in ('pid', 'start', 'nonce', 'args')):
        raise update.UpdateError('Programm wurde zwischenzeitlich neu gestartet; Update angehalten.')
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not update.running_processes(root):
            return
        time.sleep(.2)
    raise update.UpdateError('Wetterstation beendet sich nicht geordnet. Kein erzwungenes Beenden; nichts installiert.')


def restart(root, before, timeout=30):
    if not before['running']:
        return 'closed'
    update.require_stopped(root, update.running_processes)
    env = os.environ.copy()
    env.update(before['env'])
    child = subprocess.Popen([sys.executable, str(root / 'app.py'), *before['args']],
                             cwd=root, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True, close_fds=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if child.poll() is not None:
            break
        record = session(root)
        if (record and record.get('pid') == child.pid and record.get('nonce') != before['nonce']
                and record.get('ready') is True and record.get('start') == start_token(child.pid)):
            identity(root, record, update.running_processes(root))
            return 'restarted'
        time.sleep(.25)
    raise update.UpdateError('Programmupdate installiert; Wiederstart konnte nicht bestaetigt werden. Bitte am Pi pruefen.')


def transaction(root, archive, sha, before):
    # Verify and check dependencies/storage before taking the display down.
    update.verify_archive(archive, sha)
    current = check(root)
    if current != before:
        raise update.UpdateError('Pi-Laufzustand hat sich geaendert; nichts installiert.')
    # Separate orchestration lock covers stop, install and restart; install has
    # its own lock and checks for starts racing with the transaction.
    with update.file_lock(root.parent / '.Wetterstation-deploy.lock'):
        stop(root, before)
        backup = update.install(root, archive, None, sha, None, keep_layout=True)
        try:
            state = restart(root, before)
        except Exception:
            raise update.UpdateError('Programmupdate installiert; Wiederstart nicht bestaetigt. Sicherung: ' + str(backup)) from None
        return {'backup': str(backup), 'state': state,
                'release': update.verify_archive(archive, sha)['release']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('check', 'apply'))
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--state', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'check':
            result = check(args.target)
        else:
            if args.archive is None or args.sha256 is None or args.state is None:
                raise update.UpdateError('Unvollstaendiger Updateauftrag.')
            result = transaction(args.target.resolve(), args.archive, args.sha256,
                                 update.read_json(args.state, 16_000))
        print(json.dumps(result), flush=True)
        return 0
    except update.UpdateError as error:
        print(str(error), file=sys.stderr)
    except Exception:
        print('Pi-Pruefung oder Update angehalten. Keine Passwort- oder Schluesseldaten ausgegeben.', file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
