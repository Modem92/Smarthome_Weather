"""Install an opt-in Pi desktop launcher; never start weather or read credentials."""
from __future__ import annotations

import argparse
import base64
from datetime import datetime
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

TARGET = "pi@wetterstation-pi"
RELATIVE_PROJECT = "wetterstation/Wetterstation"
ICON = '''<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
<rect x="2" y="2" width="124" height="124" rx="29" fill="#f1f5fb"/>
<g stroke="#f4b544" stroke-width="6" stroke-linecap="round">
<path d="M77 18v6m0 50v6m-31-31h6m50 0h6M55 27l4 4m36 36 4 4m0-44-4 4"/>
</g><circle cx="77" cy="49" r="18" fill="#ffc64c"/>
<path d="M31 99a19 19 0 0 1-1-38 26 26 0 0 1 49-1 20 20 0 0 1 15 39Z" fill="#69a9e9"/>
<path d="M31 90a11 11 0 0 1-1-22l6 1 1-6a18 18 0 0 1 35-1l2 7 7-1a12 12 0 0 1 12 22Z" fill="#d9edff"/>
</svg>'''


def exec_quote(text):
    text = text.replace("%", "%%")
    for char in ("\\", '"', "$", "`"):
        text = text.replace(char, "\\"+char)
    return '"'+text+'"'


def entry(project, icon):
    return ("[Desktop Entry]\nVersion=1.0\nType=Application\nName=Wetterstation\n"
            "Comment=Echte Wetterdaten und Regenkarte\n"
            "Exec=/bin/sh "+exec_quote(str(project / "start_pi_live.sh"))+"\n"
            "Path="+str(project)+"\nIcon="+str(icon)+"\n"
            "Terminal=false\nStartupNotify=false\nCategories=Utility;\n")


def write_atomic(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".wetterstation-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def desktop_directory(home):
    try:
        result = subprocess.run(["xdg-user-dir", "DESKTOP"], check=True, capture_output=True, text=True)
        desktop = Path(result.stdout.strip())
        if not desktop.is_absolute():
            raise ValueError("Ungueltiger Desktop-Pfad.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        desktop = next((home / name for name in ("Desktop", "Schreibtisch") if (home/name).is_dir()), home/"Desktop")
    if desktop.resolve() == home.resolve() or not desktop.resolve().is_relative_to(home.resolve()) or desktop.is_symlink():
        raise ValueError("Der Desktop-Ordner konnte nicht sicher bestimmt werden.")
    return desktop


def install(home=None, desktop=None):
    home = Path.home().resolve() if home is None else home.resolve()
    project = home / RELATIVE_PROJECT
    if project.is_symlink() or not project.resolve().is_relative_to(home):
        raise ValueError("Ungueltiger Programmordner.")
    for name in ("app.py", "start_pi_live.sh"):
        if not (project / name).is_file():
            raise ValueError("Die vorhandene Pi-Wetterstation wurde nicht gefunden.")
    if (project / ".pi-update-in-progress.json").exists():
        raise ValueError("Unvollstaendiges Update: zuerst wiederherstellen.")
    desktop = desktop_directory(home) if desktop is None else desktop
    if desktop.is_symlink() or not desktop.resolve().is_relative_to(home) or desktop.resolve() == home:
        raise ValueError("Ungueltiger Desktop-Ordner.")
    desktop.mkdir(parents=True, exist_ok=True)
    icon = project / "desktop-assets/wetterstation.svg"
    launcher = desktop / "Wetterstation.desktop"
    for path in (icon.parent, icon, launcher):
        if path.is_symlink():
            raise ValueError("Verknuepfte Zieldatei: Installation angehalten.")
    ElementTree.fromstring(ICON)
    content = entry(project, icon).encode("utf-8")
    if launcher.exists() and launcher.read_bytes() != content:
        backups = project / "private/desktop-shortcut-backups"
        if backups.is_symlink() or (project / "private").is_symlink():
            raise ValueError("Ungueltiger Sicherungsordner.")
        backups.mkdir(parents=True, exist_ok=True, mode=0o700)
        backups.chmod(0o700)
        name = "Wetterstation-"+datetime.now().strftime("%Y-%m-%d-%H%M%S-%f")+".desktop"
        write_atomic(backups / name, launcher.read_bytes(), 0o600)
    write_atomic(icon, ICON.encode("utf-8"), 0o644)
    write_atomic(launcher, content, 0o755)
    # Desktop environments may ask the user to allow the launcher on first use.
    # Do not change security/trust metadata or execute the new shortcut here.
    return launcher


def remote_install():
    source = Path(__file__).read_bytes()
    encoded = base64.b64encode(source).decode("ascii")
    code = "import base64,sys; sys.argv=['pi_desktop_icon.py','--install']; exec(compile(base64.b64decode("+repr(encoded)+"),'pi_desktop_icon.py','exec'))"
    command = " ".join(shlex.quote(value) for value in ("python3", "-c", code))
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10", TARGET, command], check=True)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--remote", action="store_true")
    group.add_argument("--install", action="store_true")
    args = parser.parse_args()
    try:
        if args.remote:
            remote_install()
        else:
            if sys.platform != "linux":
                raise ValueError("Die Desktop-Verknuepfung wird auf dem Linux-Pi angelegt.")
            path = install()
            print("Desktop-Verknuepfung erstellt und geprueft: "+str(path))
            print("Startet start_pi_live.sh mit vorhandenen Pi-Einstellungen. Noch kein Programmstart und keine Wetterabrufe.")
            print("Vor dem Doppelklick eine laufende Demo schliessen. Beim ersten Sicherheitsdialog selbst Ausfuehren bestaetigen.")
    except ValueError as error:
        print(str(error), file=sys.stderr); return 1
    except Exception:
        print("Desktop-Verknuepfung nicht bestaetigt. Bitte SSH-Anmeldung, Programmordner und Desktop pruefen.", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
