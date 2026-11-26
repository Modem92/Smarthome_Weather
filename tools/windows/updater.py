"""Manually launched desktop updater; no scheduled tasks, weather or key export."""
import base64
import ast
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
import uuid

from tools.pi import update
from tools.dev_paths import scratch_root
from wetterstation.paths import project_root


def snapshot(root, destination):
    """Copy only sources/tests, then re-read originals to detect concurrent edits."""
    paths = set(update.FILES) | {'tools/offline_tests.py'}
    for folder in ('tools', 'windows'):
        paths.update(p.relative_to(root).as_posix() for p in (root / folder).rglob('*')
                     if p.is_file() and p.suffix in ('.py', '.cmd', '.ps1'))
    paths.update(p.relative_to(root).as_posix() for p in (root / 'tests').glob('*')
                 if p.is_file() and p.suffix in ('.py', '.cjs'))
    hashes = {}
    for name in sorted(paths):
        source = update.safe_path(root, name)
        data = source.read_bytes()
        hashes[name] = update.digest(data)
        update.atomic_bytes(destination / name, data, 0o755 if name.endswith('.sh') else 0o644)
    if any(update.digest(update.safe_path(root, name).read_bytes()) != sha for name, sha in hashes.items()):
        raise update.UpdateError('Projekt wurde beim Kopieren geaendert. Bitte nach dem Speichern erneut starten.')
    return hashes


def configuration(root):
    path = root / 'private/pi-update.json'
    if not path.is_file():
        raise update.UpdateError('Bitte zuerst windows/SSH einmalig einrichten.cmd ausfuehren.')
    value = update.read_json(path, 8000)
    if (value.get('schema') != 1 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.:-]*', value.get('host', ''))
            or not re.fullmatch(r'[a-z_][a-z0-9_-]*', value.get('user', ''))):
        raise update.UpdateError('Ungueltige Pi-Verbindungseinstellungen.')
    # This release targets the existing, approved installation.
    if value.get('user') != 'pi' or value.get('relative_target') != update.RELATIVE_TARGET:
        raise update.UpdateError('Die Konfiguration gehoert nicht zur vorhandenen Pi-Installation.')
    public = Path(value.get('public_key', '')).expanduser().resolve()
    if not public.is_file() or public.suffix != '.pub' or public.is_relative_to(root.resolve()):
        raise update.UpdateError('Oeffentlicher Anmeldeschluessel fehlt. Bitte SSH-Einrichtung pruefen.')
    return value, public


def ssh_options(public):
    return ['-i', str(public), '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes',
            '-o', 'PasswordAuthentication=no', '-o', 'KbdInteractiveAuthentication=no',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=10',
            '-o', 'ServerAliveInterval=10', '-o', 'ServerAliveCountMax=3']


def run_remote(config, public, arguments, *, copy=False, timeout=60):
    target = config['user'] + '@' + config['host']
    binary = 'scp.exe' if copy else 'ssh.exe'
    if copy:
        command = [binary, *ssh_options(public), str(arguments[0]), target + ':' + shlex.quote(arguments[1])]
    else:
        command = [binary, *ssh_options(public), target, ' '.join(shlex.quote(a) for a in arguments)]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except (OSError, subprocess.TimeoutExpired):
        raise update.UpdateError('Pi-Verbindung fehlt oder Zeitlimit erreicht. Bei Unterbrechung waehrend der Installation zuerst den Pi-Stand pruefen.') from None
    if result.returncode:
        # Only our standalone controller produces curated diagnostics. Never
        # display arbitrary SSH/server output, remote environments or settings.
        safe = result.stderr.strip()
        known = ('Aeltere Pi-Version:', 'Programmupdate installiert;', 'Pi-Laufzustand',
                 'Die laufende Wetterstation', 'Wetterstation beendet sich', 'Aktualisierung fehlgeschlagen.',
                 'Aktualisierung unterbrochen;', 'Vorheriges Update unvollstaendig;',
                 'Nicht genug freier Speicher', 'Keine wiederverwendbare Pi-Desktopsitzung')
        if not copy and len(safe) < 500 and safe.startswith(known) and '\n' not in safe:
            raise update.UpdateError(safe)
        raise update.UpdateError('Pi-Verbindung oder Zielpruefung fehlgeschlagen. Erreichbarkeit, SSH-Einrichtung und bekannte Geraeteidentitaet pruefen; kein Passwortdialog.')
    return result.stdout


def deploy(root, frozen, ready, report, expected_config=None):
    config, public = configuration(root)
    if expected_config is not None and (config, public) != expected_config:
        raise update.UpdateError('Pi-Verbindungseinstellungen wurden waehrend der Pruefung geaendert; bitte neu starten.')
    target = '/home/' + config['user'] + '/' + config['relative_target']
    stage = '/home/' + config['user'] + '/wetterstation/.Wetterstation-update-staging/' + ready['release'] + '-' + uuid.uuid4().hex[:8]
    # The read-only probe does not rely on helpers already installed on the Pi.
    sources = {name: (frozen / ('tools/pi/' + name + '.py')).read_bytes() for name in ('update', 'controller')}
    # Keep the read-only probe below Windows' command-line size limit. Select
    # only the inspection functions from the frozen source, never live imports.
    source = sources['update'].decode('utf-8')
    needed = {'UpdateError', 'read_json', 'safe_path', 'running_processes'}
    definitions = [ast.get_source_segment(source, node) for node in ast.parse(source).body
                   if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in needed]
    sources['update'] = ('import json,os\nfrom pathlib import Path,PurePosixPath\nMARKER=".pi-update-in-progress.json"\n'
                         + '\n\n'.join(definitions)).encode()
    probe = ("import base64,types,sys;u=types.ModuleType('update');sys.modules['update']=u;"
             "exec(compile(base64.b64decode(" + repr(base64.b64encode(sources['update']).decode()) + "),'update.py','exec'),u.__dict__);"
             "c={'__name__':'staged_controller'};exec(compile(base64.b64decode(" + repr(base64.b64encode(sources['controller']).decode()) + "),'controller.py','exec'),c);"
             "print(__import__('json').dumps(c['check'](__import__('pathlib').Path(" + repr(target) + "))))")
    report('Pi-Ziel, Bibliotheken, Speicher und Laufzustand pruefen …')
    before = json.loads(run_remote(config, public, ['python3', '-c', probe]))
    make = "import pathlib; p=pathlib.Path(" + repr(stage) + "); assert not p.parent.is_symlink(); p.parent.mkdir(mode=0o700,exist_ok=True);p.parent.chmod(0o700);p.mkdir(mode=0o700)"
    run_remote(config, public, ['python3', '-c', make])
    report('Geprueftes Paket vollstaendig bereitstellen …')
    for name in ('update', 'controller'):
        run_remote(config, public, [frozen / ('tools/pi/' + name + '.py'), stage + '/' + name + '.py'], copy=True, timeout=120)
    run_remote(config, public, [frozen / ready['archive'], stage + '/program.zip'], copy=True, timeout=120)
    state_file = frozen / 'build/pi/run-state.json'
    update.atomic_bytes(state_file, update.json_bytes(before))
    run_remote(config, public, [state_file, stage + '/state.json'], copy=True)
    report('Pi sichern, geordnet aktualisieren und bisherigen Laufzustand wiederherstellen …')
    result = json.loads(run_remote(config, public, ['python3', stage + '/controller.py', 'apply',
            '--target', target, '--archive', stage + '/program.zip', '--sha256', ready['sha256'],
            '--state', stage + '/state.json'], timeout=300))
    return result


def perform(root, report):
    config, public = configuration(root)
    root = root.resolve()
    build = root / 'build'
    build.mkdir(exist_ok=True)
    with update.file_lock(build / 'desktop-update.lock'):
        with tempfile.TemporaryDirectory(prefix='pi-snapshot-', dir=scratch_root()) as temporary:
            frozen = Path(temporary)
            report('Aktuellen Programmstand einfrieren …')
            hashes = snapshot(root, frozen)
            report('Isolierte Offline-Tests pruefen; das kann einige Minuten dauern …')
            result = subprocess.run([sys.executable, str(frozen / 'tools/offline_tests.py')],
                    cwd=frozen, capture_output=True, text=True, timeout=600,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            reports = build / 'reports'; reports.mkdir(exist_ok=True)
            (reports / 'last-update-tests.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
            if result.returncode:
                raise update.UpdateError('Offline-Tests fehlgeschlagen. Nichts an den Pi uebertragen; Bericht unter build/reports/last-update-tests.txt.')
            if any(update.digest((frozen / name).read_bytes()) != sha for name, sha in hashes.items()):
                raise update.UpdateError('Eine Pruefung hat Quelldateien veraendert; nichts uebertragen.')
            package = subprocess.run([sys.executable, '-m', 'tools.pi.update', 'build', '--keep-layout'],
                    cwd=frozen, capture_output=True, text=True, timeout=60,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if package.returncode:
                raise update.UpdateError('Paketbau aus dem geprueften Stand fehlgeschlagen; nichts uebertragen.')
            ready = update.read_json(frozen / 'build/pi/pi-update-ready.json')
            update.verify_archive(frozen / ready['archive'], ready['sha256'])
            # Preserve exactly the tested artifact for diagnosis/recovery.
            output = root / ready['archive']; output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise update.UpdateError('Versionskennung bereits vorhanden; bitte erneut starten.')
            shutil.copyfile(frozen / ready['archive'], output)
            update.atomic_bytes(output.with_suffix('.zip.sha256'), (ready['sha256'] + '  ' + output.name + '\n').encode(), 0o644)
            result = deploy(root, frozen, ready, report, (config, public))
            update.atomic_bytes(build / 'pi/last-success.json', update.json_bytes(result), 0o644)
            return result


class UpdateWindow:
    """Distinct running/success/error states; a stopped busy bar is never a result."""
    def __init__(self, root):
        self.root = root
        self.active = True
        self.events = queue.Queue()
        root.title('Wetterstation · Update läuft')
        root.geometry('760x380'); root.minsize(680, 360)
        frame = ttk.Frame(root, padding=24); frame.pack(fill='both', expand=True)
        self.heading = ttk.Label(frame, text='Update läuft …', font=('Segoe UI', 19, 'bold'))
        self.heading.pack(anchor='w')
        self.message = tk.StringVar(value='Bitte warten – das Update läuft noch.')
        ttk.Label(frame, textvariable=self.message, wraplength=700).pack(anchor='w', pady=(12, 10))
        self.detail = tk.StringVar(value='Update wird vorbereitet …')
        self.detail_label = ttk.Label(frame, textvariable=self.detail, wraplength=700)
        self.detail_label.pack(fill='x', anchor='w')
        self.bar = ttk.Progressbar(frame, mode='indeterminate', maximum=100)
        self.bar.pack(fill='x', pady=22); self.bar.start()
        self.done = ttk.Button(frame, text='Fenster schließen', command=root.destroy, state='disabled')
        self.done.pack(side='bottom', anchor='e')
        root.protocol('WM_DELETE_WINDOW', lambda: None if self.active else root.destroy())
        frame.bind('<Configure>', lambda event: self.detail_label.configure(wraplength=max(250, event.width - 48)))

    def consume(self, kind, payload):
        if not self.active:
            return
        if kind == 'progress':
            self.detail.set(payload)
            return
        self.active = False
        self.bar.stop()
        self.bar.configure(mode='determinate', value=100 if kind == 'success' else 0)
        self.done.configure(state='normal')
        if kind == 'success':
            self.root.title('Wetterstation · Update abgeschlossen')
            self.heading.configure(text='✓ Update abgeschlossen', foreground='#16713d')
            self.message.set('Fertig. Du kannst dieses Fenster jetzt schließen.')
            state = ('Die Wetterstation wurde wieder gestartet.' if payload['state'] == 'restarted'
                     else 'Die Wetterstation bleibt geschlossen. Du kannst sie am Pi über das Desktop-Symbol starten.')
            self.detail.set('Version ' + payload['release'] + ' ist installiert.\n' + state
                            + '\n\nSicherung der vorherigen Version:\n' + payload['backup'])
        else:
            self.root.title('Wetterstation · Update mit Fehler beendet')
            self.heading.configure(text='Update mit Fehler beendet', foreground='#b42318')
            self.message.set('Der Vorgang läuft nicht weiter. Bitte den Hinweis beachten.')
            self.detail.set(payload)
            self.bar.pack_forget()

    def start(self):
        def work():
            try:
                result = perform(project_root(), lambda text: self.events.put(('progress', text)))
                if (not isinstance(result, dict) or result.get('state') not in ('closed', 'restarted')
                        or any(not isinstance(result.get(key), str) or not result[key] for key in ('release', 'backup'))):
                    raise update.UpdateError('Der Abschluss konnte nicht bestätigt werden. Bitte den Pi-Stand prüfen, bevor du erneut aktualisierst.')
                self.events.put(('success', result))
            except update.UpdateError as error:
                self.events.put(('error', str(error)))
            except Exception:
                self.events.put(('error', 'Update angehalten. Bei Verbindungsabbruch während der Installation zuerst den Pi-Stand und die Startsperre prüfen.'))
        self.worker = threading.Thread(target=work, daemon=False)
        self.worker.start()
        self.root.after(100, self.poll)

    def poll(self):
        try:
            while True:
                self.consume(*self.events.get_nowait())
        except queue.Empty:
            pass
        if self.active:
            self.root.after(100, self.poll)


def main():
    root = tk.Tk()
    window = UpdateWindow(root)
    window.start()
    root.mainloop()


if __name__ == '__main__':
    main()
