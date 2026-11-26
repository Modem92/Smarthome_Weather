"""Project-relative settings for the Wetterstation preview.

Settings live in the OneDrive project under ``private/settings.json``. Git ignores
that directory, while OneDrive can synchronize it with the rest of the project.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from wetterstation.paths import project_root as resolve_project_root
from typing import Any
from wetterstation.storage.file_io import replace_file, SettingsFileLock
from wetterstation.ui.widgets import load_layout, validate_layout, revision, LayoutConflict
from wetterstation.weather.countries import legacy_country, require_country, country_code


API_KEY_FIELD = "openweather_api_key"
LOCATION_FIELD = "location"
DEFAULT_LOCATION = "Potsdam, 14467, Deutschland"
_locks_guard = threading.Lock()
_locks: dict[str, threading.RLock] = {}


def default_settings_path(project_root: str | Path | None = None) -> Path:
    """Return the settings path inside this project, wherever it is located."""
    root = Path(project_root) if project_root is not None else resolve_project_root()
    return root / "private" / "settings.json"


def legacy_settings_path() -> Path:
    """Return the old per-user settings path for one-time migration only."""
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
            ) as key:
                local_app_data = winreg.QueryValueEx(key, "Local AppData")[0]
            base = Path(os.path.expandvars(local_app_data))
        except (ImportError, OSError):
            base = Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "Wetterstation" / "settings.json"


class ApiKeyStore:
    """Read and atomically update settings without displaying secret values."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        legacy_path: str | Path | None = None,
    ) -> None:
        use_project_default = path is None
        self.path = Path(path) if path is not None else default_settings_path()
        old_path = legacy_settings_path() if use_project_default and legacy_path is None else legacy_path
        self.migration_status = "not_needed"
        if old_path is not None:
            self.migrate_legacy_settings(old_path)

    @contextmanager
    def _update_lock(self):
        name = str(self.path.resolve()).casefold()
        with _locks_guard:
            lock = _locks.setdefault(name, threading.RLock())
        with lock:
            with SettingsFileLock(self.path.with_suffix(".lock")):
                yield

    def migrate_legacy_settings(self, source_path: str | Path) -> bool:
        """Copy a valid old settings file once, without replacing an existing target."""
        source = Path(source_path)
        if self.path.exists():
            self.migration_status = "project_settings_already_exist"
            return False
        try:
            settings = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError:
            self.migration_status = "no_legacy_file"
            return False
        except (OSError, ValueError, RecursionError):
            self.migration_status = "legacy_file_invalid_or_unreadable"
            return False

        if not isinstance(settings, dict):
            self.migration_status = "legacy_file_invalid_or_unreadable"
            return False
        if API_KEY_FIELD in settings and settings[API_KEY_FIELD] is not None and not isinstance(settings[API_KEY_FIELD], str):
            self.migration_status = "legacy_file_invalid_or_unreadable"
            return False
        if LOCATION_FIELD in settings and not isinstance(settings[LOCATION_FIELD], str):
            self.migration_status = "legacy_file_invalid_or_unreadable"
            return False
        if not settings:
            self.migration_status = "legacy_file_empty"
            return False

        try:
            created = self._write_settings(settings, overwrite=False)
        except OSError:
            self.migration_status = "migration_failed"
            return False
        self.migration_status = "migrated" if created else "project_settings_already_exist"
        return created

    def _read_settings(self) -> dict[str, Any]:
        try:
            if self.path.stat().st_size > 8_500_000:
                raise ValueError("Die Projekteinstellungen sind unerwartet groß.")
            settings = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (UnicodeError, RecursionError):
            raise ValueError("Die Projekteinstellungen sind beschädigt.") from None
        if not isinstance(settings, dict):
            raise ValueError("Die Projekteinstellungen haben ein ungültiges Format.")
        return settings

    def load_api_key(self) -> str | None:
        """Return the key for a future API client; never use it in UI text."""
        value = self._read_settings().get(API_KEY_FIELD)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def has_api_key(self) -> bool:
        return self.load_api_key() is not None

    def load_location(self, default: str = DEFAULT_LOCATION) -> str:
        value = self._read_settings().get(LOCATION_FIELD, default)
        if not isinstance(value, str):
            raise ValueError("Der gespeicherte Ort hat ein ungültiges Format.")
        normalized = " ".join(value.split())
        return normalized or default

    def save_location(self, value: str) -> None:
        location = " ".join(value.split())
        if not location:
            raise ValueError("Ein leerer Ort kann nicht gespeichert werden.")
        with self._update_lock():
            settings = self._read_settings()
            settings[LOCATION_FIELD] = location[:80]
            self._write_settings(settings)

    def load_country_code(self) -> str:
        return self.load_location_country()[1]

    def load_location_country(self) -> tuple[str, str]:
        """One file snapshot prevents mixing a concurrently changed place and country."""
        settings = self._read_settings()
        value = settings.get(LOCATION_FIELD, DEFAULT_LOCATION)
        if not isinstance(value, str):
            raise ValueError("Der gespeicherte Ort hat ein ungültiges Format.")
        location = " ".join(value.split()) or DEFAULT_LOCATION
        if "country_code" in settings:
            return location, country_code(settings["country_code"])
        return location, legacy_country(location)

    def save_api_key(self, value: str, *, location: str | None = None) -> None:
        key = value.strip()
        if not key:
            raise ValueError("Ein leerer Schlüssel kann nicht gespeichert werden.")
        with self._update_lock():
            settings = self._read_settings()
            settings[API_KEY_FIELD] = key
            if location is not None:
                normalized = " ".join(location.split())
                if not normalized:
                    raise ValueError("Ein leerer Ort kann nicht gespeichert werden.")
                settings[LOCATION_FIELD] = normalized[:80]
            self._write_settings(settings)

    def save_configuration(self, location: str, api_key: str = "", *, country_code: str | None = None) -> bool:
        """Atomically save the mobile form; blank credentials preserve the key."""
        if not isinstance(location, str) or not isinstance(api_key, str):
            raise ValueError("Bitte gültige Texteingaben verwenden.")
        place, key = " ".join(location.split()), api_key.strip()
        if not place or len(place) > 80:
            raise ValueError("Bitte einen Ort mit höchstens 80 Zeichen eingeben.")
        if len(key) > 256 or any(ord(char) < 33 or ord(char) > 126 for char in key):
            raise ValueError("Der Schlüssel enthält ungültige Zeichen oder ist zu lang.")
        with self._update_lock():
            settings = self._read_settings()
            code = require_country(country_code if country_code is not None else legacy_country(place))
            key_changed = bool(key) and settings.get(API_KEY_FIELD) != key
            settings[LOCATION_FIELD] = place
            settings["country_code"] = code
            if key:
                settings[API_KEY_FIELD] = key
            self._write_settings(settings)
        return key_changed

    def delete_api_key(self) -> bool:
        with self._update_lock():
            settings = self._read_settings()
            if API_KEY_FIELD not in settings:
                return False
            settings.pop(API_KEY_FIELD)
            if settings:
                self._write_settings(settings)
            else:
                self.path.unlink(missing_ok=True)
            return True

    def load_dashboard(self) -> dict:
        value = self._read_settings().get("dashboard")
        return load_layout(value)

    def save_dashboard(self, layout: dict, expected_revision: str) -> dict:
        layout = validate_layout(layout)
        with self._update_lock():
            settings = self._read_settings()
            current = settings.get("dashboard")
            current = load_layout(current)
            if expected_revision != revision(current):
                raise LayoutConflict("Das Layout wurde inzwischen geändert. Bitte neu laden.")
            settings["dashboard"] = layout
            self._write_settings(settings)
        return layout

    def arrange_dashboard(self, operations: list, expected_revision: str) -> dict:
        """Only geometry/page commands may arrive from a schema-3 phone client."""
        from wetterstation.designer.model import arrangement
        with self._update_lock():
            settings = self._read_settings()
            current = load_layout(settings.get('dashboard'))
            if current.get('version') not in (3,4):
                raise ValueError('Anordnungsbefehle benötigen Gestaltungsformat 3 oder 4.')
            from wetterstation.designer.storage import read_json, atomic, json_bytes
            archive_path = self.path.parent / 'designer/phone-undo.json'
            try:
                archive = read_json(archive_path, 16_000_000)
                if not isinstance(archive, dict) or set(archive) != {'widgets', 'pages'}:
                    raise ValueError('Handy-Rückgängig-Speicher beschädigt.')
            except FileNotFoundError:
                archive = {'widgets': {}, 'pages': {}}
            result = arrangement(current, operations, expected_revision, archive)
            new_ids = {w['id'] for p in result['pages'] for w in p['widgets']}
            page_ids = {p['id'] for p in result['pages']}
            for page in current['pages']:
                if page['id'] not in page_ids:
                    archive['pages'][page['id']] = {k:v for k,v in page.items() if k != 'widgets'}
                for widget in page['widgets']:
                    if widget['id'] not in new_ids:
                        archive['widgets'][widget['id']] = widget
            # Bounded server-side tombstones preserve appearance during phone Undo.
            while len(archive['widgets']) > 256:
                archive['widgets'].pop(next(iter(archive['widgets'])))
            while len(archive['pages']) > 64:
                archive['pages'].pop(next(iter(archive['pages'])))
            while len(json_bytes(archive)) > 16_000_000 and archive['widgets']:
                archive['widgets'].pop(next(iter(archive['widgets'])))
            atomic(archive_path, json_bytes(archive))
            settings['dashboard'] = result
            self._write_settings(settings)
        return result

    def propose_arrangement(self, operations: list, expected_revision: str) -> dict:
        from wetterstation.designer.model import arrangement
        from wetterstation.designer.storage import read_json
        try:
            archive = read_json(self.path.parent / 'designer/phone-undo.json', 16_000_000)
        except FileNotFoundError:
            archive = None
        return arrangement(self.load_dashboard(), operations, expected_revision, archive)

    def _write_settings(self, settings: dict[str, Any], *, overwrite: bool = True) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", delete=False,
                dir=self.path.parent, prefix="settings-", suffix=".tmp",
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump(settings, temporary, ensure_ascii=False, indent=2)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            if os.name != "nt":
                temporary_path.chmod(0o600)
            if overwrite:
                replace_file(temporary_path, self.path)
            elif os.name == "nt":
                # Windows rename is atomic and fails if the target already exists.
                os.rename(temporary_path, self.path)
            else:
                # A same-volume hard link creates the target atomically and fails
                # if another process or device already created it.
                os.link(temporary_path, self.path)
            return True
        except FileExistsError:
            return False
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
