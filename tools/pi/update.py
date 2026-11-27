"""Prepare a public release and apply it later to an existing, stopped Pi install.

No weather clients, key migration, package installation or automatic app start.
The installer/restore path is standalone stdlib so it can run from staging.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
import zipfile
from zoneinfo import ZoneInfo

TARGET = "pi@wetterstation-pi"
RELATIVE_TARGET = "wetterstation/Wetterstation"
MARKER = ".pi-update-in-progress.json"
RETIRED_FILES = (
    'countries.py', 'countries.json', 'international_map.py', 'location_time.py',
    'api_key_store.py', 'dashboard.py', 'file_io.py', 'mobile_settings.py',
    'openweather_budget.py', 'radar_map.py', 'radar_motion.py', 'radar_render.py',
    'settings.py', 'weather_service.py', 'widgets.py', 'pi_desktop_icon.py',
    'pi_live_transfer.py', 'start_preview.cmd', 'start_widget_demo.cmd',
    'prepare_pi_update.cmd', 'transfer_pi_update.cmd', 'prepare_pi_live.cmd',
    'install_pi_desktop_icon.cmd',
    'mobile_web/index.html', 'mobile_web/style.css', 'mobile_web/app.js', 'mobile_web/layout.js',
    # Planning docs moved to CLAUDE.md/ai/ (not shipped). Listed here so updates
    # remove them on the Pi and restores of older backups still accept them.
    'AGENTS.md', 'PROJEKTPLAN.md', 'PI_UPDATE.md', 'RASPBERRY_PI.md',
    'docs/FEATURE_STATUS.md', 'docs/HISTORY.md', 'docs/PI_UPDATE.md', 'docs/RASPBERRY_PI.md',
    'docs/DESIGNER_SPEC.md', 'docs/GRAPHICAL_DESIGNER_SPEC.md',
)
FILES = ('README.md', 'app.py', 'docs/STRUCTURE.md', 'docs/UPDATE.md', 'pi_preflight.py', 'pi_update.py', 'pyproject.toml', 'raspberry_pi/start_pi_demo.sh', 'raspberry_pi/start_pi_live.sh', 'raspberry_pi/start_pi_widget_demo.sh', 'requirements.txt', 'start_pi_demo.sh', 'start_pi_live.sh', 'start_pi_widget_demo.sh', 'tools/__init__.py', 'tools/pi/__init__.py', 'tools/pi/controller.py', 'tools/pi/desktop_icon.py', 'tools/pi/preflight.py', 'tools/pi/update.py', 'wetterstation/__init__.py', 'wetterstation/__main__.py', 'wetterstation/lifecycle.py', 'wetterstation/maps/__init__.py', 'wetterstation/maps/international_map.py', 'wetterstation/maps/radar_map.py', 'wetterstation/maps/radar_motion.py', 'wetterstation/maps/radar_render.py', 'wetterstation/mobile/__init__.py', 'wetterstation/mobile/mobile_settings.py', 'wetterstation/mobile/web/app.js', 'wetterstation/mobile/web/index.html', 'wetterstation/mobile/web/layout.js', 'wetterstation/mobile/web/style.css', 'wetterstation/paths.py', 'wetterstation/storage/__init__.py', 'wetterstation/storage/api_key_store.py', 'wetterstation/storage/file_io.py', 'wetterstation/storage/openweather_budget.py', 'wetterstation/storage/settings.py', 'wetterstation/ui/__init__.py', 'wetterstation/ui/app.py', 'wetterstation/ui/dashboard.py', 'wetterstation/ui/widgets.py', 'wetterstation/weather/__init__.py', 'wetterstation/weather/countries.json', 'wetterstation/weather/countries.py', 'wetterstation/weather/location_time.py', 'wetterstation/weather/weather_service.py')


FILES = FILES + ('wetterstation/designer/icons/chevron.svg','wetterstation/designer/icons/check.svg')
FILES = FILES + ('docs/OPTIMIZATION.md',)
FILES = FILES + ('wetterstation/ui/tk_images.py',)
FILES = FILES + ('docs/DESIGNER.md', 'requirements-designer.txt', 'tools/pi/design.py') + tuple(
    'wetterstation/designer/'+name+'.py' for name in
    ('__init__','model','storage','render','runtime','series','timeline_client','content','interaction','theme','activation','live_timelines','session','app','deploy','transfer')
) + tuple('wetterstation/designer/fonts/'+name for name in (
    'LICENSE_DEJAVU','DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSans-Oblique.ttf',
    'DejaVuSans-BoldOblique.ttf','DejaVuSansDisplay.ttf','DejaVuSansMono.ttf',
    'DejaVuSansMono-Bold.ttf','DejaVuSansMono-Oblique.ttf','DejaVuSansMono-BoldOblique.ttf',
    'DejaVuSerif.ttf','DejaVuSerif-Bold.ttf','DejaVuSerif-Italic.ttf',
    'DejaVuSerif-BoldItalic.ttf','DejaVuSerifDisplay.ttf'))


class UpdateError(Exception):
    """Only curated, secret-free messages may be shown by the CLI."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2)+"\n").encode("utf-8")


def program_bytes(path):
    """Normalize source line endings, preserve portable font binaries exactly."""
    return (path.read_bytes() if path.suffix.lower() in ('.ttf', '.otf') else
            path.read_text(encoding='utf-8-sig').replace('\r\n', '\n').encode('utf-8'))


def read_json(path, limit=1_000_000):
    if path.stat().st_size > limit:
        raise UpdateError("Eine Eingabedatei ist zu gross.")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_bytes(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".pi-update-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


@contextmanager
def file_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        if stream.seek(0, 2) == 0:
            stream.write(b"\0"); stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise UpdateError("Eine andere Aktualisierung ist noch aktiv.") from None
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def safe_path(root, relative):
    if not isinstance(relative, str):
        raise UpdateError("Ungueltiger Paketpfad.")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or "\\" in relative or ":" in relative or str(posix) != relative:
        raise UpdateError("Ungueltiger Paketpfad.")
    path = root.joinpath(*posix.parts)
    if not path.resolve().is_relative_to(root.resolve()):
        raise UpdateError("Ein Zielpfad verlaesst den Programmordner.")
    cursor = root
    for part in posix.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise UpdateError("Symbolische Verknuepfung im Programmordner; Aktualisierung angehalten.")
    return path


def widget_api(folder):
    spec = importlib.util.spec_from_file_location("_pi_update_widgets", folder / "wetterstation/ui/widgets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def export_layout(root, api):
    settings_file = safe_path(root, "private/settings.json")
    settings = read_json(settings_file, 8_500_000) if settings_file.exists() else {}
    if not isinstance(settings, dict):
        raise UpdateError("Die PC-Einstellungen sind ungueltig.")
    layout = api.load_layout(settings.get("dashboard"))
    return {"schema": 1, "layout": layout, "revision": api.revision(layout)}


def build(root, release=None, *, keep_layout=False):
    root = root.resolve()
    release = release or datetime.now(ZoneInfo("Europe/Berlin")).strftime("%Y-%m-%d-%H%M%S")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-zA-Z0-9_-]{1,40}", release):
        raise UpdateError("Ungueltige Versionskennung.")
    payload, entries = {}, []
    for name in FILES:
        source = safe_path(root, name)
        if not source.is_file():
            raise UpdateError("Das Programm ist unvollstaendig; Paket nicht erstellt.")
        data = program_bytes(source)
        if name.endswith(".py"):
            ast.parse(data.decode(), filename=name, feature_version=(3, 11))
        mode = 0o755 if name.endswith(".sh") else 0o644
        payload[name] = data
        entries.append({"path": name, "size": len(data), "sha256": digest(data), "mode": mode})
    manifest = {"schema": 2, "release": release, "python_syntax": "3.11", "files": entries}
    # A repair must not read/export the PC settings or replace the Pi layout.
    layout = None if keep_layout else export_layout(root, widget_api(root))
    output = root / "build/pi"
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"Wetterstation-Pi-Update-{release}.zip"
    if archive.exists():
        raise UpdateError("Dieses Updatepaket existiert bereits. Bitte eine neue Versionskennung verwenden.")
    with tempfile.TemporaryDirectory(prefix="pi-package-", dir=output) as work:
        temp = Path(work) / "program.zip"
        with zipfile.ZipFile(temp, "w", zipfile.ZIP_DEFLATED) as bundle:
            for name, data in payload.items():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFREG | (0o755 if name.endswith(".sh") else 0o644)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                bundle.writestr(info, data)
            bundle.writestr("MANIFEST.json", json_bytes(manifest))
        verify_archive(temp)
        os.replace(temp, archive)
    if not keep_layout:
        layout_path = safe_path(root, f"private/pi-update-layout-{release}.json")
        atomic_bytes(layout_path, json_bytes(layout))
    atomic_bytes(output / f"{archive.name}.sha256", f"{digest(archive.read_bytes())}  {archive.name}\n".encode(), 0o644)
    atomic_bytes(output / f"{archive.stem}-INHALT.json", json_bytes(manifest), 0o644)
    ready = {"schema": 1, "release": release, "archive": archive.relative_to(root).as_posix(),
             "sha256": digest(archive.read_bytes()),
             "target": TARGET, "directory": RELATIVE_TARGET}
    if keep_layout:
        ready["keep_layout"] = True
    else:
        ready.update(layout=layout_path.relative_to(root).as_posix(),
                     layout_sha256=digest(layout_path.read_bytes()), layout_revision=layout["revision"])
    atomic_bytes(output / "pi-update-ready.json", json_bytes(ready), 0o644)
    return ready


def verify_archive(archive, expected_sha=None):
    if archive.stat().st_size > 10_000_000 or (expected_sha and digest(archive.read_bytes()) != expected_sha):
        raise UpdateError("Die Archiv-Pruefsumme stimmt nicht.")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)) or set(names) != set(FILES) | {"MANIFEST.json"}:
            raise UpdateError("Das Archiv ist unvollstaendig oder enthaelt unerwartete Dateien.")
        if any(info.file_size > 1_000_000 for info in bundle.infolist()):
            raise UpdateError("Eine Archivdatei ist zu gross.")
        manifest = json.loads(bundle.read("MANIFEST.json"))
        if not isinstance(manifest, dict) or manifest.get("schema") != 2:
            raise UpdateError("Ungueltiges Inhaltsverzeichnis.")
        if not isinstance(manifest.get("release"), str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-zA-Z0-9_-]{1,40}", manifest["release"]):
            raise UpdateError("Ungueltige Versionskennung im Archiv.")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != len(FILES) or {e["path"] for e in entries} != set(FILES):
            raise UpdateError("Das Inhaltsverzeichnis ist unvollstaendig.")
        for entry in entries:
            name = entry["path"]
            data = bundle.read(name)
            expected_mode = 0o755 if name.endswith(".sh") else 0o644
            if entry.get("mode") != expected_mode or entry.get("size") != len(data) or entry.get("sha256") != digest(data):
                raise UpdateError("Eine Programmdatei hat eine abweichende Pruefsumme.")
            if stat.S_IFMT(bundle.getinfo(name).external_attr >> 16) not in (0, stat.S_IFREG):
                raise UpdateError("Unerlaubter Dateityp im Archiv.")
            if name.endswith(".sh") and (b"\r" in data or not data.startswith(b"#!/bin/sh\n")):
                raise UpdateError("Ein Linux-Starter hat ungueltige Zeilenenden.")
            if name.endswith(".py"):
                ast.parse(data.decode("utf-8"), filename=name, feature_version=(3, 11))
        return manifest


def extract_checked(archive, destination, manifest):
    destination.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as bundle:
        for entry in manifest["files"]:
            path = safe_path(destination, entry["path"])
            atomic_bytes(path, bundle.read(entry["path"]), entry["mode"])


def running_processes(root, proc=Path("/proc")):
    if not proc.is_dir():
        raise UpdateError("Prozesspruefung nur auf dem Linux-Pi moeglich.")
    found = []
    for process in proc.iterdir():
        if not process.name.isdigit():
            continue
        try:
            args = (process / "cmdline").read_bytes().split(b"\0")
            args = [arg.decode("utf-8", "replace") for arg in args if arg]
            possible = any(Path(arg).name in ("app.py", "start_pi_live.sh", "start_pi_demo.sh", "start_pi_widget_demo.sh")
                           or (arg in ("app", "wetterstation") and args[index-1] == "-m")
                           for index, arg in enumerate(args[1:], 1))
            if not possible:
                continue
            cwd = (process / "cwd").resolve(strict=True)
        except (FileNotFoundError, ProcessLookupError):
            continue
        except PermissionError:
            # Other users cannot own this user's normal desktop app. Own
            # processes must remain inspectable, otherwise fail closed.
            try:
                if process.stat().st_uid == os.getuid():
                    raise UpdateError("Ein eigener Prozess konnte nicht sicher geprueft werden.")
            except FileNotFoundError:
                pass
            continue
        for index, arg in enumerate(args[1:], 1):
            if arg in ("app", "wetterstation") and args[index-1] == "-m" and cwd == root:
                found.append(int(process.name)); break
            if Path(arg).name in ("app.py", "start_pi_live.sh", "start_pi_demo.sh", "start_pi_widget_demo.sh"):
                path = Path(arg) if Path(arg).is_absolute() else cwd / arg
                if path.resolve() in {root / 'app.py', root / 'wetterstation/ui/app.py',
                                      root / 'start_pi_live.sh', root / 'start_pi_demo.sh', root / 'start_pi_widget_demo.sh',
                                      root / 'raspberry_pi/start_pi_live.sh', root / 'raspberry_pi/start_pi_demo.sh',
                                      root / 'raspberry_pi/start_pi_widget_demo.sh'}:
                    found.append(int(process.name)); break
    return found


def require_stopped(root, probe):
    if probe(root):
        raise UpdateError("Die Pi-Wetterstation laeuft noch. Bitte schliessen und erneut versuchen.")


def check_target(root, probe=running_processes):
    if root.is_symlink() or not root.is_dir():
        raise UpdateError("Der vorhandene Pi-Programmordner wurde nicht gefunden.")
    root = root.resolve()
    if not safe_path(root, "app.py").is_file() or not safe_path(root, "private/settings.json").is_file():
        raise UpdateError("Keine bestehende eingerichtete Pi-Installation gefunden.")
    settings = read_json(root / "private/settings.json", 8_500_000)
    if not isinstance(settings, dict) or not isinstance(settings.get("openweather_api_key"), str) or not settings["openweather_api_key"].strip():
        raise UpdateError("Die vorhandenen Pi-Einstellungen sind ungueltig.")
    require_stopped(root, probe)
    return root


def tree_hashes(root, *, private_only=False):
    base = root / "private" if private_only else root
    result = {}
    for path in base.rglob("*"):
        name = path.relative_to(root).as_posix()
        safe_path(root, name)
        if path.is_file():
            result[name] = digest(path.read_bytes())
        elif not path.is_dir():
            raise UpdateError("Ungewoehnlicher Dateityp im Programmordner.")
    return result


def backup_install(root, manifest, layout):
    before = tree_hashes(root)
    total = sum((root / name).stat().st_size for name in before)
    if shutil.disk_usage(root.parent).free < total*2+20_000_000:
        raise UpdateError("Zu wenig freier Speicher fuer Sicherung und Aktualisierung.")
    parent = root.parent / "Wetterstation-Backups"
    if parent.is_symlink():
        raise UpdateError("Der Sicherungsordner darf keine Verknuepfung sein.")
    parent.mkdir(mode=0o700, exist_ok=True); parent.chmod(0o700)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    backup = parent / f"{stamp}-{uuid.uuid4().hex[:8]}"
    backup.mkdir(mode=0o700)
    shutil.copytree(root, backup / "installation")
    if tree_hashes(backup / "installation") != before:
        raise UpdateError("Die Sicherung konnte nicht vollstaendig bestaetigt werden.")
    plan = {"schema": 1, "target": str(root), "release": manifest["release"],
            "files": [{"path": e["path"], "old": before.get(e["path"]), "new": e["sha256"]} for e in manifest["files"]]
                     + [{"path": name, "old": before[name], "new": None} for name in RETIRED_FILES if name in before],
            "original_hashes": before, "new_layout": layout, "status": "backed_up"}
    atomic_bytes(backup / "restore.json", json_bytes(plan))
    return backup, plan


def merge_layout(root, layout):
    path = safe_path(root, "private/settings.json")
    with file_lock(root / "private/settings.lock"):
        settings = read_json(path, 8_500_000)
        old = deepcopy(settings)
        settings["dashboard"] = layout
        atomic_bytes(path, json_bytes(settings))
        actual = read_json(path, 8_500_000)
        if actual.get("dashboard") != layout or {k:v for k,v in actual.items() if k != "dashboard"} != {k:v for k,v in old.items() if k != "dashboard"}:
            raise UpdateError("Die Pi-Einstellungen konnten nicht sicher zusammengefuehrt werden.")


def restore(root, backup, *, probe=running_processes):
    root = root.resolve(); backup = backup.resolve()
    parent = root.parent / "Wetterstation-Backups"
    if backup.parent != parent or backup.is_symlink():
        raise UpdateError("Die Sicherung liegt nicht im vorgesehenen Sicherungsordner.")
    plan = read_json(backup / "restore.json")
    if plan.get("schema") != 1 or plan.get("target") != str(root):
        raise UpdateError("Die Sicherung gehoert nicht zu dieser Installation.")
    require_stopped(root, probe)
    # Never restore complete private trees: budget counters and TLS files may
    # have advanced since the backup. Only program files and the layout change.
    for entry in plan["files"]:
        if entry["path"] not in FILES and entry["path"] not in RETIRED_FILES:
            raise UpdateError("Ungueltige Wiederherstellungsdatei.")
        path = safe_path(root, entry["path"])
        actual = digest(path.read_bytes()) if path.exists() else None
        if actual not in (entry["old"], entry["new"]):
            raise UpdateError("Programmdateien wurden anderweitig geaendert; Wiederherstellung angehalten.")
        if entry["old"]:
            source = safe_path(backup / "installation", entry["path"])
            if digest(source.read_bytes()) != entry["old"]:
                raise UpdateError("Die Sicherung ist beschaedigt.")
    original_path = safe_path(backup / "installation", "private/settings.json")
    if digest(original_path.read_bytes()) != plan["original_hashes"]["private/settings.json"]:
        raise UpdateError("Die gesicherten Einstellungen sind beschaedigt.")
    original = read_json(original_path, 8_500_000)
    # Persist the guard before any restore mutation, also after a successful
    # update when the user requests a later rollback.
    atomic_bytes(root / MARKER, json_bytes({"backup": str(backup), "status": "restoring"}))
    keep_layout = plan.get("keep_layout", False)
    with nullcontext() if keep_layout else file_lock(root / "private/settings.lock"):
        if not keep_layout:
            current_path = safe_path(root, "private/settings.json")
            current = read_json(current_path, 8_500_000)
            if current.get("dashboard") not in (original.get("dashboard"), plan["new_layout"]):
                raise UpdateError("Das Widget-Layout wurde inzwischen geaendert; Wiederherstellung angehalten.")
        for entry in plan["files"]:
            path = safe_path(root, entry["path"])
            if entry["old"]:
                source = safe_path(backup / "installation", entry["path"])
                atomic_bytes(path, source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
            else:
                path.unlink(missing_ok=True)
        if not keep_layout:
            if "dashboard" in original:
                current["dashboard"] = original["dashboard"]
            else:
                current.pop("dashboard", None)
            # Preserve later changes to location/key/other fields, if any.
            data = original_path.read_bytes() if current == original else json_bytes(current)
            atomic_bytes(current_path, data)
    plan["status"] = "restored"
    atomic_bytes(backup / "restore.json", json_bytes(plan))
    (root / MARKER).unlink(missing_ok=True)


def offline_check(root):
    result = subprocess.run([sys.executable, "pi_preflight.py"], cwd=root, capture_output=True, text=True)
    if result.returncode:
        raise UpdateError("Die Offline-Pruefung am Pi ist fehlgeschlagen.")


def install(root, archive, layout_file, expected_sha, layout_sha, *, probe=running_processes,
            postcheck=offline_check, writer=atomic_bytes, keep_layout=False):
    root = check_target(root, probe)
    if (root / MARKER).exists():
        raise UpdateError("Eine vorherige Aktualisierung ist unvollstaendig. Bitte zuerst wiederherstellen.")
    manifest = verify_archive(archive, expected_sha)
    if keep_layout and (layout_file is not None or layout_sha is not None):
        raise UpdateError("Layoutimport und Layouterhalt duerfen nicht kombiniert werden.")
    if not keep_layout and (layout_file is None or layout_sha is None or digest(layout_file.read_bytes()) != layout_sha):
        raise UpdateError("Die Layout-Pruefsumme stimmt nicht.")
    with file_lock(root.parent / ".Wetterstation-update.lock"):
        require_stopped(root, probe)
        with tempfile.TemporaryDirectory(prefix="pi-update-check-", dir=archive.parent) as work:
            payload = Path(work) / "payload"
            extract_checked(archive, payload, manifest)
            layout = None
            if not keep_layout:
                api = widget_api(payload)
                export = read_json(layout_file, 8_500_000)
                if not isinstance(export, dict) or set(export) != {"schema", "layout", "revision"} or export["schema"] != 1:
                    raise UpdateError("Ungueltige separate Layoutdatei.")
                layout = api.validate_layout(export["layout"])
                if api.revision(layout) != export["revision"]:
                    raise UpdateError("Ungueltige Layoutkennung.")
            backup, plan = backup_install(root, manifest, layout)
            if keep_layout:
                plan["keep_layout"] = True
                atomic_bytes(backup / "restore.json", json_bytes(plan))
            original_private = tree_hashes(root, private_only=True)
            try:
                atomic_bytes(root / MARKER, json_bytes({"backup": str(backup), "status": "installing"}))
            except Exception:
                raise UpdateError("Die Startsperre konnte nicht angelegt werden. Programm und Einstellungen wurden nicht veraendert.") from None
            try:
                require_stopped(root, probe)
                for entry in manifest["files"]:
                    path = safe_path(root, entry["path"])
                    writer(path, safe_path(payload, entry["path"]).read_bytes(), entry["mode"])
                for entry in plan['files']:
                    if entry['new'] is None:
                        path = safe_path(root, entry['path'])
                        if digest(path.read_bytes()) != entry['old']:
                            raise UpdateError('Alte Programmdatei wurde gleichzeitig geaendert.')
                        path.unlink()
                require_stopped(root, probe)
                if not keep_layout:
                    merge_layout(root, layout)
                for entry in manifest["files"]:
                    if digest(safe_path(root, entry["path"]).read_bytes()) != entry["sha256"]:
                        raise UpdateError("Die installierten Programmdateien sind unvollstaendig.")
                actual_private = tree_hashes(root, private_only=True)
                ignored = set() if keep_layout else {"private/settings.json", "private/settings.lock"}
                if {k:v for k,v in original_private.items() if k not in ignored} != {k:v for k,v in actual_private.items() if k not in ignored}:
                    raise UpdateError("Private Pi-Dateien haben sich unerwartet geaendert.")
                postcheck(root)
                plan["status"] = "installed"
                atomic_bytes(backup / "restore.json", json_bytes(plan))
                (root / MARKER).unlink()
                return backup
            except Exception:
                try:
                    restore(root, backup, probe=probe)
                except Exception:
                    raise UpdateError("Aktualisierung unterbrochen; Startsperre bleibt aktiv. Sicherung im Ordner Wetterstation-Backups, bitte Wiederherstellungsanleitung verwenden.") from None
                raise UpdateError("Aktualisierung fehlgeschlagen. Der vorherige Programmstand und das Layout wurden wiederhergestellt; kein Programmstart.") from None


# Executed read-only over the existing SSH connection before staging is created.
REMOTE_CHECK = r'''
import getpass,json,os,pathlib,sys
assert sys.version_info >= (3,11), 'Python 3.11 erforderlich'
assert sys.platform == 'linux' and getpass.getuser() == 'pi', 'Falsches Zielsystem'
home=pathlib.Path.home().resolve()
root=home/'wetterstation'/'Wetterstation'
assert not root.is_symlink() and root.resolve().is_relative_to(home), 'Ungueltiger Zielpfad'
assert (root/'app.py').is_file() and (root/'private'/'settings.json').is_file(), 'Pi-Installation nicht gefunden'
assert not (root/'private').is_symlink() and not (root/'private'/'settings.json').is_symlink(), 'Ungueltiger privater Zielpfad'
assert not (root/'.pi-update-in-progress.json').exists(), 'Unvollstaendiges Update zuerst wiederherstellen'
for process in pathlib.Path('/proc').iterdir():
 if not process.name.isdigit(): continue
 try:
  args=[a.decode('utf-8','replace') for a in (process/'cmdline').read_bytes().split(b'\0') if a]
  possible=any(pathlib.Path(a).name in ('app.py','start_pi_live.sh','start_pi_demo.sh','start_pi_widget_demo.sh') or (a=='app' and args[i-1]=='-m') for i,a in enumerate(args[1:],1))
  if not possible: continue
  cwd=(process/'cwd').resolve(strict=True)
 except (FileNotFoundError,ProcessLookupError): continue
 except PermissionError:
  assert process.stat().st_uid != os.getuid(), 'Eigener Prozess nicht pruefbar'
  continue
 for i,arg in enumerate(args[1:],1):
  candidate=pathlib.Path(arg)
  if not candidate.is_absolute(): candidate=cwd/candidate
  assert not ((pathlib.Path(arg).name in ('app.py','start_pi_live.sh','start_pi_demo.sh','start_pi_widget_demo.sh') and candidate.resolve().parent == root.resolve()) or (arg=='app' and args[i-1]=='-m' and cwd==root.resolve())), 'Pi-Wetterstation laeuft noch'
print(json.dumps({'root':str(root.resolve())}))
'''


def remote_command(code, *args):
    return " ".join(shlex.quote(a) for a in ("python3", "-c", code, *args))


def transfer(root):
    """Explicit user-run action only. Never invoked by build or local checks."""
    root = root.resolve()
    ready = read_json(root / "build/pi/pi-update-ready.json")
    if ready.get("target") != TARGET or ready.get("directory") != RELATIVE_TARGET:
        raise UpdateError("Das vorbereitete Ziel ist ungueltig.")
    archive = safe_path(root, ready["archive"])
    keep_layout = ready.get("keep_layout", False)
    if not isinstance(keep_layout, bool) or (keep_layout and any(key in ready for key in ("layout", "layout_sha256", "layout_revision"))):
        raise UpdateError("Die Layoutvorgabe des Pakets ist widerspruechlich.")
    manifest = verify_archive(archive, ready["sha256"])
    if ready.get("release") != manifest["release"] or ready["archive"] != f"build/pi/Wetterstation-Pi-Update-{manifest['release']}.zip":
        raise UpdateError("Die Paketbeschreibung passt nicht zum Update.")
    if not keep_layout:
        layout = safe_path(root, ready["layout"])
        export = read_json(layout, 8_500_000)
        expected_export = export_layout(root, widget_api(root))
        if ready["layout"] != f"private/pi-update-layout-{manifest['release']}.json":
            raise UpdateError("Die Paketbeschreibung passt nicht zum Update.")
        if export != expected_export or digest(layout.read_bytes()) != ready["layout_sha256"] or expected_export["revision"] != ready["layout_revision"]:
            raise UpdateError("Das PC-Layout hat sich geaendert. Bitte das Paket neu vorbereiten.")
    for entry in manifest["files"]:
        data = program_bytes(safe_path(root, entry["path"]))
        if digest(data) != entry["sha256"]:
            raise UpdateError("Der Programmstand ist neuer als das Paket. Bitte neu vorbereiten.")
    print("Programmreparatur: vorhandenes Pi-Layout bleibt erhalten." if keep_layout else "Programmupdate: PC-Widget-Layout wird uebernommen.", flush=True)
    options = ["-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10"]
    # Keep SSH's terminal/password prompt and diagnostics visible to the user.
    # Only stdout is captured for the small, secret-free target JSON response.
    check = subprocess.run(["ssh", *options, TARGET, remote_command(REMOTE_CHECK)], stdout=subprocess.PIPE, text=True)
    if check.returncode:
        raise UpdateError("Pi-Ziel nicht bestaetigt. Bitte SSH-Identitaet, Anmeldung, Programmordner und geschlossene Pi-Anwendung pruefen. Es wurde nichts uebertragen.")
    target = Path(json.loads(check.stdout)["root"]).as_posix()
    # Remote paths use POSIX strings even when this controller runs on Windows.
    stage = str(PurePosixPath(target).parent / ".Wetterstation-update-staging" / (ready["release"]+"-"+uuid.uuid4().hex[:8]))
    make_stage = "import pathlib,sys; p=pathlib.Path(sys.argv[1]); p.parent.mkdir(mode=0o700,exist_ok=True); assert not p.parent.is_symlink(); p.parent.chmod(0o700); p.mkdir(mode=0o700)"
    subprocess.run(["ssh", *options, TARGET, remote_command(make_stage, stage)], check=True)
    copies = [(archive, "program.zip")]
    if not keep_layout:
        copies.append((layout, "widget-layout.json"))
    copies.append((root / "tools/pi/update.py", "pi_update.py"))
    for local, name in copies:
        subprocess.run(["scp", *options, str(local), TARGET+":"+shlex.quote(stage+"/"+name)], check=True)
    args = ["python3", stage+"/pi_update.py", "install", "--target", target, "--archive", stage+"/program.zip", "--sha256", ready["sha256"]]
    if keep_layout:
        args.append("--keep-layout")
    else:
        args.extend(["--layout", stage+"/widget-layout.json", "--layout-sha256", ready["layout_sha256"]])
    subprocess.run(["ssh", *options, TARGET, " ".join(shlex.quote(a) for a in args)], check=True)


def main():
    parser = argparse.ArgumentParser(description="Wetterstation: Programmupdate ohne Schluessel-/Zaehlerimport")
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("build")
    command.add_argument("--release")
    command.add_argument("--keep-layout", action="store_true")
    sub.add_parser("verify").add_argument("archive", type=Path)
    sub.add_parser("transfer")
    command = sub.add_parser("install")
    for name in ("target", "archive"):
        command.add_argument("--"+name, type=Path, required=True)
    command.add_argument("--layout", type=Path)
    command.add_argument("--sha256", required=True); command.add_argument("--layout-sha256")
    command.add_argument("--keep-layout", action="store_true")
    command = sub.add_parser("restore")
    command.add_argument("--target", type=Path, required=True); command.add_argument("--backup", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2] if Path(__file__).parent.name == "pi" else Path(__file__).resolve().parents[2] if Path(__file__).parent.name == "pi" else Path(__file__).resolve().parent
    try:
        if args.action == "build":
            ready = build(root, args.release, keep_layout=args.keep_layout)
            print("Vollstaendiges Paket vorbereitet: "+ready["archive"])
            print("Vorhandenes Pi-Layout bleibt erhalten; kein PC-Layout exportiert." if args.keep_layout else "Widget-Layout separat vorbereitet: "+ready["layout"])
            print("SHA-256: "+ready["sha256"])
            print("Keine Pi-Verbindung, keine Wetterabrufe, keine Schluessel oder Zaehler exportiert.")
        elif args.action == "verify":
            manifest = verify_archive(args.archive)
            print(f"Paket geprueft: {len(manifest['files'])} Dateien, Python-3.11-Syntax und Linux-Starter OK.")
        elif args.action == "transfer":
            transfer(root)
            print("Update und Offline-Pruefung abgeschlossen. Noch kein Programmstart. Bitte Widget-Demo am Pi pruefen.")
        elif args.action == "install":
            backup = install(args.target, args.archive, args.layout, args.sha256, args.layout_sha256, keep_layout=args.keep_layout)
            print("Update und Offline-Pruefung erfolgreich. Sicherung: "+str(backup))
            print("Kein automatischer Programmstart. Ort, Schluessel, Zertifikate und Zaehler erhalten.")
        elif args.action == "restore":
            with file_lock(args.target.resolve().parent / ".Wetterstation-update.lock"):
                restore(args.target, args.backup)
            print("Vorheriger Programmstand und Widget-Layout wiederhergestellt. Zaehler nicht zurueckgesetzt; kein Programmstart.")
    except UpdateError as error:
        print(str(error), file=sys.stderr); return 1
    except Exception:
        print("Vorgang angehalten. Keine Anwendung gestartet. Bitte Paket, Zugriff und Wiederherstellungsanleitung pruefen.", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
