"""Crash-safe, per-device OpenWeather request budget.

The authoritative counter is project-relative under private/. A local mirror detects
rollback by an older OneDrive copy on this same device. Neither file coordinates
other computers or other programs using the same API key.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from wetterstation.storage.api_key_store import default_settings_path, legacy_settings_path
from wetterstation.storage.file_io import replace_file

MAX_DAILY_CALLS = 1000
MAX_CALLS_PER_MINUTE = 60  # rolling 60-second window, shared by every OpenWeather endpoint
RESET_GUARD_MINUTE_UTC = 5  # FAQ says provider resets sometime between 00:00 and 00:05 UTC
SCHEMA = 2
LOCAL_DAY_ZONE = ZoneInfo("Europe/Berlin")


class BudgetError(Exception):
    """Safe message for a blocked request; never includes a key or URL."""


class BudgetLimitReached(BudgetError):
    pass


class BudgetUnavailable(BudgetError):
    pass


_thread_locks: dict[str, threading.RLock] = {}
_thread_locks_guard = threading.Lock()


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _next_safe_reset(now: datetime) -> datetime:
    now = now.astimezone(timezone.utc)
    reset = now.replace(hour=0, minute=RESET_GUARD_MINUTE_UTC, second=0, microsecond=0)
    if now >= reset:
        reset += timedelta(days=1)
    return reset


def _local_data_root() -> Path:
    if sys.platform == "win32":
        pinned = os.environ.get("WETTERSTATION_BUDGET_ROOT")
        if pinned:
            root = Path(pinned)
            if not root.is_absolute():
                raise BudgetUnavailable("OpenWeather ist gesperrt: Der vom Starter gewählte Budgetordner ist ungültig.")
            return root
        # Resolve the Windows user folder independently of LOCALAPPDATA.
        # A temporary launcher environment must not invent a device.
        return legacy_settings_path().parent / "openweather-budget"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Wetterstation" / "openweather-budget"
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "Wetterstation" / "openweather-budget"


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix="budget-", suffix=".tmp",
                                         delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            temp_path.chmod(0o600)
        replace_file(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class OpenWeatherBudget:
    """Serialize and reserve every outbound OpenWeather request before sending it."""

    def __init__(self, *, project_private: str | Path | None = None,
                 device_id: str | None = None, local_root: str | Path | None = None):
        self.project_private = Path(project_private) if project_private else default_settings_path().parent
        self._provided_device_id = device_id
        self._local_root_override = Path(local_root) if local_root else None
        self._device_id_cache: str | None = None

    def _get_device_id(self) -> str:
        if self._provided_device_id:
            return self._provided_device_id
        if self._device_id_cache:
            return self._device_id_cache
        root = self._local_root_override or _local_data_root()
        path = root / "device-id.txt"
        try:
            root.mkdir(parents=True, exist_ok=True)
            try:
                with path.open("x", encoding="ascii") as stream:
                    stream.write(uuid.uuid4().hex + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
            except FileExistsError:
                pass
            value = path.read_text(encoding="ascii").strip()
            if len(value) != 32 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("invalid device id")
        except (OSError, ValueError):
            raise BudgetUnavailable("OpenWeather ist gesperrt: Das lokale Budget kann nicht sicher initialisiert werden.") from None
        self._device_id_cache = value
        return value

    def _paths(self) -> tuple[Path, Path, Path]:
        device_id = self._get_device_id()
        project_token = hashlib.sha256(str(self.project_private.resolve()).casefold().encode("utf-8")).hexdigest()[:20]
        primary = self.project_private / "openweather_budget" / f"{device_id}.json"
        mirror_root = (self._local_root_override or _local_data_root()) / "mirrors" / project_token
        mirror = mirror_root / f"{device_id}.json"
        return primary, mirror, primary.with_suffix(".lock")

    @staticmethod
    def _thread_lock_for(path: Path) -> threading.RLock:
        key = str(path.resolve()).casefold()
        with _thread_locks_guard:
            return _thread_locks.setdefault(key, threading.RLock())

    class _FileLock:
        def __init__(self, path: Path):
            self.path = path
            self.stream = None
            self.thread_lock = OpenWeatherBudget._thread_lock_for(path)

        def __enter__(self):
            self.thread_lock.acquire()
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.stream = self.path.open("a+b")
                self.stream.seek(0, os.SEEK_END)
                if self.stream.tell() == 0:
                    self.stream.write(b"\0")
                    self.stream.flush()
                self.stream.seek(0)
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if os.name == "nt":
                            import msvcrt
                            msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        return self
                    except (OSError, BlockingIOError):
                        if time.monotonic() >= deadline:
                            raise BudgetUnavailable("OpenWeather ist gesperrt: Eine andere Vorschau hält den Budgetzähler belegt.") from None
                        time.sleep(0.05)
            except BudgetUnavailable:
                if self.stream:
                    self.stream.close()
                    self.stream = None
                self.thread_lock.release()
                raise
            except OSError:
                if self.stream:
                    self.stream.close()
                    self.stream = None
                self.thread_lock.release()
                raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler kann nicht sicher gesperrt werden.") from None

        def __exit__(self, *_exc):
            try:
                if self.stream:
                    self.stream.seek(0)
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
                    self.stream.close()
            finally:
                self.thread_lock.release()

    def _read_json(self, path: Path) -> dict[str, Any] | None:
        try:
            if path.stat().st_size > 256_000:
                raise ValueError("oversized counter")
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, RecursionError):
            raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler ist beschädigt oder nicht lesbar.") from None
        if not isinstance(value, dict):
            raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler hat ein ungültiges Format.")
        return value

    def _validate(self, state: dict[str, Any], device_id: str) -> None:
        try:
            if (type(state.get("schema")) is not int or state.get("schema") not in (1, SCHEMA) or state.get("device_id") != device_id
                    or type(state.get("revision")) is not int or state["revision"] < 0
                    or type(state.get("count")) is not int or not 0 <= state["count"] <= MAX_DAILY_CALLS
                    or not isinstance(state.get("recent_attempts"), list)
                    or len(state["recent_attempts"]) > MAX_CALLS_PER_MINUTE
                    or (state.get("day") is not None and not isinstance(state["day"], str))):
                raise ValueError
            if state["day"] is not None and date.fromisoformat(state["day"]).isoformat() != state["day"]:
                raise ValueError
            if state["day"] is None and state["count"] != 0:
                raise ValueError
            if state["schema"] == SCHEMA:
                if (state.get("local_zone") != "Europe/Berlin"
                        or not isinstance(state.get("local_day"), str)
                        or date.fromisoformat(state["local_day"]).isoformat() != state["local_day"]
                        or type(state.get("local_count")) is not int
                        or not 0 <= state["local_count"] <= MAX_DAILY_CALLS):
                    raise ValueError
            blocked = state.get("blocked_until")
            for item in [state["updated_at"], *state["recent_attempts"], *([blocked] if blocked is not None else [])]:
                if not isinstance(item, str) or datetime.fromisoformat(item).tzinfo is None:
                    raise ValueError
        except (ValueError, TypeError, KeyError, OverflowError):
            raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler ist ungültig; er wird nicht zurückgesetzt.") from None

    def _load_or_init(self, primary: Path, mirror: Path, device_id: str,
                      now: datetime) -> dict[str, Any]:
        state = self._read_json(primary)
        local = self._read_json(mirror)
        if state is None and local is not None:
            raise BudgetUnavailable("OpenWeather ist gesperrt: Die synchronisierte Budgetdatei fehlt oder wurde zurückgesetzt.")
        if state is None:
            state = {"schema": SCHEMA, "device_id": device_id, "revision": 0,
                     "day": None, "count": 0, "recent_attempts": [],
                     "local_zone": "Europe/Berlin", "local_day": now.astimezone(LOCAL_DAY_ZONE).date().isoformat(),
                     "local_count": 0,
                     "blocked_until": _utc_iso(_next_safe_reset(now)), "updated_at": _utc_iso(now)}
            _atomic_json(primary, state)
            _atomic_json(mirror, state)
            return state
        self._validate(state, device_id)
        if local is None:
            if state["revision"] != 0:
                raise BudgetUnavailable("OpenWeather ist gesperrt: Für den synchronisierten Zähler fehlt der lokale Prüfspeicher.")
            self._validate(state, device_id)
            _atomic_json(mirror, state)
            return state
        self._validate(local, device_id)
        if state["revision"] < local["revision"]:
            raise BudgetUnavailable("OpenWeather ist gesperrt: OneDrive enthält einen älteren Zählerstand; es wurde nichts überschrieben.")
        if state["revision"] == local["revision"] and state != local:
            raise BudgetUnavailable("OpenWeather ist gesperrt: Projektdatei und lokaler Prüfspeicher weichen voneinander ab.")
        if state["revision"] > local["revision"]:
            _atomic_json(mirror, state)
        return state

    @staticmethod
    def _day_state(state: dict[str, Any], now: datetime) -> tuple[str, int, datetime | None]:
        now = now.astimezone(timezone.utc)
        today = now.date().isoformat()
        reset_today = now.replace(hour=0, minute=RESET_GUARD_MINUTE_UTC, second=0, microsecond=0)
        if state.get("blocked_until"):
            blocked_until = datetime.fromisoformat(state["blocked_until"]).astimezone(timezone.utc)
            if now < blocked_until:
                return "initializing", 0, blocked_until
        if now < reset_today and state.get("day") != today:
            return "reset_wait", 0, reset_today
        stored_day = state.get("day")
        if stored_day and stored_day > today:
            return "clock_rollback", state["count"], None
        if stored_day == today:
            return "ready", state["count"], None
        return "ready", 0, None

    def _with_lock(self):
        primary, mirror, lock_path = self._paths()
        return primary, mirror, self._FileLock(lock_path)

    @staticmethod
    def _local_count(state: dict[str, Any], now: datetime) -> int:
        today = now.astimezone(LOCAL_DAY_ZONE).date().isoformat()
        if state["schema"] == 1:
            # Existing UTC totals cannot be split retrospectively. Preserve all
            # known calls conservatively when migrating during the same UTC day.
            return state["count"] if state["day"] == now.astimezone(timezone.utc).date().isoformat() else 0
        if state["local_day"] > today:
            raise BudgetUnavailable("OpenWeather ist gesperrt: Die Systemzeit liegt vor dem gespeicherten lokalen Budgettag.")
        return state["local_count"] if state["local_day"] == today else 0

    @staticmethod
    def _local_fields(now: datetime, count: int) -> dict[str, Any]:
        return {"schema": SCHEMA, "local_zone": "Europe/Berlin",
                "local_day": now.astimezone(LOCAL_DAY_ZONE).date().isoformat(), "local_count": count}

    def status(self, *, now: datetime | None = None) -> dict[str, Any]:
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        primary, mirror, lock = self._with_lock()
        try:
            with lock:
                state = self._load_or_init(primary, mirror, self._get_device_id(), moment)
                mode, count, reset_at = self._day_state(state, moment)
                if mode == "clock_rollback":
                    raise BudgetUnavailable("OpenWeather ist gesperrt: Die Systemzeit liegt vor dem gespeicherten Budgettag.")
                local_count = self._local_count(state, moment)
                local_fields = self._local_fields(moment, local_count)
                if any(state.get(key) != value for key, value in local_fields.items()):
                    state = {**state, **local_fields, "revision": state["revision"] + 1,
                             "updated_at": _utc_iso(moment)}
                    _atomic_json(primary, state)
                    _atomic_json(mirror, state)
                attempts = [datetime.fromisoformat(value).astimezone(timezone.utc)
                            for value in state["recent_attempts"]]
                active = sum(moment - stamp < timedelta(seconds=60) for stamp in attempts)
                local_now = moment.astimezone(LOCAL_DAY_ZONE)
                local_reset = (local_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                return {"mode": mode, "count": local_count,
                        "remaining": max(0, MAX_DAILY_CALLS-max(count, local_count)),
                        "provider_count": count, "local_reset_at": local_reset,
                        "limit": MAX_DAILY_CALLS, "minute_remaining": max(0, MAX_CALLS_PER_MINUTE-active),
                        "reset_at": reset_at, "device_scope": "Dieses Gerät und diese Projektkopie"}
        except BudgetUnavailable:
            raise
        except OSError:
            raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler ist nicht verfügbar.") from None

    def reserve_call(self, *, now: datetime | None = None, protected: int = 0) -> int:
        if type(protected) is not int or protected < 0:
            raise BudgetUnavailable('Ungültige Reserve für zusätzliche Wetteranfragen.')
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        primary, mirror, lock = self._with_lock()
        try:
            with lock:
                device_id = self._get_device_id()
                state = self._load_or_init(primary, mirror, device_id, moment)
                mode, count, reset_at = self._day_state(state, moment)
                if mode == "initializing":
                    raise BudgetLimitReached(f"OpenWeather gesperrt, bis der Tagesreset sicher vorbei ist ({reset_at:%d.%m. %H:%M UTC}). Der heutige Vorverbrauch ist unbekannt.")
                if mode == "reset_wait":
                    raise BudgetLimitReached(f"OpenWeather gesperrt bis {reset_at:%d.%m. %H:%M UTC}; OpenWeather setzt Tageslimits zwischen 00:00 und 00:05 UTC zurück.")
                if mode == "clock_rollback":
                    raise BudgetUnavailable("OpenWeather ist gesperrt: Die Systemzeit liegt vor dem gespeicherten Budgettag.")
                if count >= MAX_DAILY_CALLS:
                    tomorrow_reset = moment.replace(hour=0, minute=RESET_GUARD_MINUTE_UTC, second=0, microsecond=0) + timedelta(days=1)
                    raise BudgetLimitReached(f"OpenWeather-Tageslimit erreicht ({MAX_DAILY_CALLS}/{MAX_DAILY_CALLS}); nächste Freigabe {tomorrow_reset:%d.%m. %H:%M UTC}.")
                local_count = self._local_count(state, moment)
                if local_count >= MAX_DAILY_CALLS:
                    raise BudgetLimitReached(f"Lokales OpenWeather-Tageslimit erreicht ({MAX_DAILY_CALLS}/{MAX_DAILY_CALLS}); nächste Freigabe um 00:00 Uhr deutscher Zeit.")
                if protected and max(count, local_count) + 1 + protected > MAX_DAILY_CALLS:
                    raise BudgetLimitReached('Zusatzanfrage gesperrt: Reguläre Abrufe und Reserve bleiben geschützt.')
                recent = [datetime.fromisoformat(value).astimezone(timezone.utc)
                          for value in state["recent_attempts"]]
                recent = [stamp for stamp in recent if moment - stamp < timedelta(seconds=60)]
                if len(recent) >= MAX_CALLS_PER_MINUTE:
                    wait_until = min(recent).replace(microsecond=0) + timedelta(seconds=60)
                    raise BudgetLimitReached(f"OpenWeather-Aufrufrate lokal begrenzt ({MAX_CALLS_PER_MINUTE}/Minute); bitte ab {wait_until:%H:%M:%S UTC} erneut versuchen.")
                updated = dict(state)
                updated.update(self._local_fields(moment, local_count + 1))
                updated.update({"day": moment.date().isoformat(), "count": count+1,
                                "recent_attempts": [_utc_iso(x) for x in recent] + [_utc_iso(moment)],
                                "blocked_until": None, "revision": state["revision"]+1,
                                "updated_at": _utc_iso(moment)})
                _atomic_json(primary, updated)
                _atomic_json(mirror, updated)
                return updated["count"]
        except BudgetError:
            raise
        except OSError:
            raise BudgetUnavailable("OpenWeather ist gesperrt: Der Budgetzähler konnte nicht dauerhaft gespeichert werden.") from None

    def status_text(self) -> str:
        try:
            state = self.status()
        except BudgetError as exc:
            return str(exc)
        scope = "Nur diese Projektkopie auf diesem PC; andere Apps und PCs zählen nicht mit."
        if state["mode"] == "initializing":
            return (f"OpenWeather gesperrt bis {state['reset_at']:%d.%m. %H:%M UTC} · "
                    f"neuer Zähler: 0/{state['limit']}; heutiger Vorverbrauch ist unbekannt. {scope}")
        if state["mode"] == "reset_wait":
            return (f"OpenWeather wartet bis {state['reset_at']:%d.%m. %H:%M UTC} auf den Tagesreset · "
                    f"danach 0/{state['limit']}. {scope}")
        return (f"OpenWeather heute: {state['count']}/{state['limit']} Anfragen, "
                f"noch {state['remaining']} frei · Reset 00:00 Uhr deutscher Zeit · "
                f"Anbietertag: {state['provider_count']}/{state['limit']} · {scope}")
