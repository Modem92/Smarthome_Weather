"""One-time move of an existing installation; never reset or waive API limits."""
import argparse
import json
import os
from pathlib import Path
import sys
import zipfile

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.openweather_budget import OpenWeatherBudget, _local_data_root


def export_bundle(root: Path, budget=None):
    store = ApiKeyStore(path=root / "private" / "settings.json")
    if not store.has_api_key():
        raise ValueError("Kein gespeicherter Projektschluessel vorhanden.")
    budget = budget or OpenWeatherBudget(project_private=root / "private")
    # Reconcile the real user's local mirror before taking a locked snapshot.
    budget.status()
    primary, mirror, lock = budget._with_lock()
    with lock:
        state = budget._read_json(primary)
        budget._validate(state, budget._get_device_id())
        if state != budget._read_json(mirror):
            raise ValueError("Zaehler und Pruefspeicher stimmen nicht ueberein.")
        if state["day"] is None:
            raise ValueError("Kein bestehender Abrufverlauf fuer die Uebernahme vorhanden.")
        payload = {"schema": 1, "settings": store._read_settings(), "budget": state}
        target = root / "private" / "pi-live-transfer.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("installation.json", json.dumps(payload))
        if os.name != "nt":
            target.chmod(0o600)
    print("Uebernahmepaket erstellt. Zaehlerhistorie und Begrenzungen bleiben erhalten.")


def import_bundle(root: Path, bundle: Path, local_root=None):
    if bundle.stat().st_size > 128_000:
        raise ValueError("Uebernahmepaket ist ungueltig.")
    with zipfile.ZipFile(bundle) as archive:
        info = archive.getinfo("installation.json")
        if info.file_size > 128_000:
            raise ValueError("Uebernahmepaket ist ungueltig.")
        payload = json.loads(archive.read(info))
    if payload.get("schema") != 1:
        raise ValueError("Uebernahmepaket ist ungueltig.")
    state, settings = payload["budget"], payload["settings"]
    identity = state["device_id"]
    if not isinstance(identity, str) or len(identity) != 32 or any(c not in "0123456789abcdef" for c in identity):
        raise ValueError("Ungueltige Installationskennung.")
    if not isinstance(settings, dict) or not isinstance(settings.get("openweather_api_key"), str) or not settings["openweather_api_key"].strip():
        raise ValueError("Keine gueltigen Projekteinstellungen vorhanden.")
    local_root = Path(local_root) if local_root is not None else _local_data_root()
    private = root / "private"
    budget = OpenWeatherBudget(project_private=private, device_id=identity, local_root=local_root)
    budget._validate(state, identity)
    if state["day"] is None:
        raise ValueError("Keine bestehende Zaehlerhistorie vorhanden.")
    primary, mirror, lock = budget._with_lock()
    identity_path = local_root / "device-id.txt"
    settings_path = private / "settings.json"
    # Never replace an existing Pi identity or settings, even after a partial import.
    if identity_path.exists() or settings_path.exists() or any((private / "openweather_budget").glob("*.json")):
        raise ValueError("Auf dem Pi existieren bereits Einstellungen oder Zaehler. Nichts ueberschrieben.")
    local_root.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        private.chmod(0o700)
    # Exclusive files and the regular budget lock fail closed on interrupted imports.
    with identity_path.open("x", encoding="ascii") as stream:
        stream.write(identity + "\n")
    if os.name != "nt":
        identity_path.chmod(0o600)
    with lock:
        for path in (primary, mirror, settings_path):
            if path.exists():
                raise ValueError("Zieldatei existiert bereits. Uebernahme angehalten.")
        for path, value in ((primary, state), (mirror, state), (settings_path, settings)):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as stream:
                if os.name != "nt":
                    os.fchmod(stream.fileno(), 0o600)
                json.dump(value, stream)
                stream.flush()
                os.fsync(stream.fileno())
    bundle.unlink()
    print("Einstellungen, Zaehlerhistorie und Pruefspeicher uebernommen.")
    print(budget.status_text())
    print("Keine Wetterabfrage gesendet. Windows-Wetterprogramm waehrend des Pi-Betriebs geschlossen lassen.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("export", "import"))
    args = parser.parse_args()
    from wetterstation.paths import project_root
    root = project_root()
    try:
        if args.action == "export":
            export_bundle(root)
        else:
            import_bundle(root, root / "private" / "pi-live-transfer.zip")
    except Exception:
        # Never echo imported configuration or raw exceptions containing secrets.
        print("Uebernahme angehalten. Einstellungen und Zaehler bitte pruefen; keine Wetterabfrage gesendet.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
