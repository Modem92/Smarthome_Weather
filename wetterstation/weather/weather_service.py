"""OpenWeather One Call 4.0 current conditions and bounded forecasts."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import time
from email.utils import parsedate_to_datetime
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from wetterstation.storage.api_key_store import default_settings_path
from wetterstation.storage.file_io import replace_file
from wetterstation.storage.openweather_budget import BudgetError, OpenWeatherBudget
from wetterstation.weather.countries import split_query

GEO = "https://api.openweathermap.org/geo/1.0"
ONE_CALL = "https://api.openweathermap.org/data/4.0/onecall"
ALLOWED_HOST = "api.openweathermap.org"
FORECAST_HOURLY_COUNT = 8
FORECAST_DAILY_COUNT = 5
CURRENT_CACHE_TTL = 5 * 60
FORECAST_CACHE_TTL = 5 * 60
MAX_CACHE_AGE = 6 * 60 * 60
MAX_RESPONSE_BYTES = 2_000_000


def aware_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return stamp


def number(value: Any, low: float = -math.inf, high: float = math.inf) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a measurement")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError("invalid measurement")
    return result


def validate_place(place: dict[str, Any]) -> None:
    number(place["lat"], -90, 90)
    number(place["lon"], -180, 180)
    for field in ("name", "country"):
        if not isinstance(place[field], str) or not place[field].strip():
            raise ValueError("invalid place")


def normalize_query(query: str) -> str:
    return " ".join(query.casefold().split())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class WeatherRecord:
    query: str
    name: str
    country: str
    lat: float
    lon: float
    timezone: str
    observed_at: str
    retrieved_at: str
    temp: float
    feels_like: float
    humidity: int
    pressure: int
    wind_speed: float
    description: str
    source: str = "OpenWeather One Call 4.0"
    warnings: tuple[str, ...] = ()

    def __post_init__(self):
        validate_place(asdict(self))
        aware_time(self.observed_at)
        aware_time(self.retrieved_at)
        number(self.temp)
        number(self.feels_like)
        number(self.humidity, 0, 100)
        number(self.pressure, 0)
        number(self.wind_speed, 0)
        if not isinstance(self.description, str) or not isinstance(self.timezone, str):
            raise ValueError("invalid weather text")
        for field in ("temp", "feels_like", "humidity", "pressure", "wind_speed"):
            object.__setattr__(self, field, number(getattr(self, field)))
        object.__setattr__(self, "humidity", int(self.humidity))
        object.__setattr__(self, "pressure", int(self.pressure))
        object.__setattr__(self, "warnings", tuple(self.warnings))


@dataclass(frozen=True)
class ForecastEntry:
    timestamp: str
    temp: float
    description: str
    precipitation_probability: float
    wind_speed: float
    temp_min: float | None = None
    temp_max: float | None = None

    def __post_init__(self):
        aware_time(self.timestamp)
        number(self.temp)
        number(self.precipitation_probability, 0, 1)
        number(self.wind_speed, 0)
        if not isinstance(self.description, str):
            raise ValueError("invalid weather text")
        for value in (self.temp_min, self.temp_max):
            if value is not None:
                number(value)
        if self.temp_min is not None and self.temp_max is not None and self.temp_min > self.temp_max:
            raise ValueError("invalid temperature range")
        for field in ("temp", "precipitation_probability", "wind_speed", "temp_min", "temp_max"):
            if getattr(self, field) is not None:
                object.__setattr__(self, field, number(getattr(self, field)))


@dataclass(frozen=True)
class ForecastRecord:
    query: str
    name: str
    country: str
    lat: float
    lon: float
    timezone: str
    retrieved_at: str
    hourly: tuple[ForecastEntry, ...]
    daily: tuple[ForecastEntry, ...]
    hourly_retrieved_at: str | None = None
    daily_retrieved_at: str | None = None
    errors: tuple[str, ...] = ()
    source: str = "OpenWeather One Call 4.0"


class WeatherServiceError(Exception):
    """Sanitized user-facing error; never includes request URLs or secrets."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Treat redirects as errors so a provider URL cannot leak the key elsewhere."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OpenWeatherClient:
    def __init__(self, cache_dir: str | Path | None = None, timeout: float = 15):
        self.cache_dir = Path(cache_dir) if cache_dir else default_settings_path().parent / "cache" / "weather"
        self.timeout = timeout
        self.budget = OpenWeatherBudget()
        self._opener = urllib.request.build_opener(_NoRedirect())
        self._key_token = None
        self._auth_error = None
        self._cooldowns: dict[str, tuple[float, str]] = {}
        self._failures: dict[str, int] = {}
        self._places: dict[str, dict[str, Any]] = {}
        self.storage_warning = ""
        self._volatile: dict[Path, dict[str, Any]] = {}

    def reset_request_pause(self) -> None:
        """Explicitly saving a credential permits another check, without sending it."""
        self._auth_error = None
        self._cooldowns.clear()
        self._failures.clear()

    def _pause_endpoint(self, endpoint: str, message: str) -> None:
        failures = min(6, self._failures.get(endpoint, 0) + 1)
        self._failures[endpoint] = failures
        self._cooldowns[endpoint] = (time.monotonic() + min(1800, 60 * 2**(failures-1)), message)

    @staticmethod
    def _retry_seconds(value: str | None) -> float:
        try:
            seconds = float(value)
            return max(60, seconds) if math.isfinite(seconds) else 900
        except (ValueError, TypeError):
            try:
                return max(60, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                return 900

    def budget_status_text(self) -> str:
        return self.budget.status_text()

    def _request(self, url: str, *, protected: int = 0) -> dict[str, Any] | list[Any]:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.username or parsed.password:
            raise WeatherServiceError("OpenWeather-Anfrageziel wurde aus Sicherheitsgründen abgewiesen.")
        secret = urllib.parse.parse_qs(parsed.query).get("appid", [""])[0]
        token = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if token != self._key_token:
            self.reset_request_pause()
            self._key_token = token
        if self._auth_error:
            raise WeatherServiceError(self._auth_error)
        for scope in ("*", parsed.path):
            until, message = self._cooldowns.get(scope, (0, ""))
            if time.monotonic() < until:
                raise WeatherServiceError(f"{message} Anfragepause: noch {math.ceil(until-time.monotonic())} Sekunden.")
        try:
            if protected:
                self.budget.reserve_call(protected=protected)
            else:
                self.budget.reserve_call()
        except BudgetError as exc:
            raise WeatherServiceError(str(exc)) from None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Wetterstation/1.0"})
            with self._opener.open(req, timeout=self.timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("oversized response")
                decoded = body.decode("utf-8")
                if secret:
                    decoded = decoded.replace(secret, "[entfernt]")
                payload = json.loads(decoded)
        except urllib.error.HTTPError as exc:
            code = exc.code
            messages = {
                401: "OpenWeather hat den Schlüssel abgelehnt (401). Bitte Schlüssel und Aktivierung prüfen.",
                403: "OpenWeather verweigert den Zugriff (403). Bitte One-Call-Abo und Tarif prüfen.",
                404: "OpenWeather hat für diesen Ort keine Daten gefunden (404).",
                429: "OpenWeather meldet zu viele Anfragen (429). Bitte später erneut versuchen.",
            }
            message = messages.get(code, f"OpenWeather-Abruf fehlgeschlagen (HTTP {code}).")
            if code in (401, 403):
                self._auth_error = message + " Weitere Abrufe pausieren bis zum erneuten Speichern des Schlüssels oder Neustart."
            elif code == 429:
                self._cooldowns["*"] = (time.monotonic() + self._retry_seconds(exc.headers.get("Retry-After") if exc.headers else None), message)
            elif code >= 500:
                self._pause_endpoint(parsed.path, message)
            exc.close()
            raise WeatherServiceError(message) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            message = "OpenWeather ist momentan nicht erreichbar."
            self._pause_endpoint(parsed.path, message)
            raise WeatherServiceError(message) from None
        except (ValueError, UnicodeError, TypeError, RecursionError):
            raise WeatherServiceError("OpenWeather hat eine ungültige Antwort geliefert.") from None
        except Exception:
            self._pause_endpoint(parsed.path, "OpenWeather-Abruf unerwartet fehlgeschlagen.")
            raise WeatherServiceError("OpenWeather-Abruf unerwartet fehlgeschlagen; bitte später erneut versuchen.") from None
        if not isinstance(payload, (dict, list)):
            raise WeatherServiceError("OpenWeather hat eine ungültige Antwort geliefert.")
        self._failures.pop(parsed.path, None)
        self._cooldowns.pop(parsed.path, None)
        return payload

    def _resolve(self, query: str, key: str) -> dict[str, Any]:
        try:
            base, country = split_query(query)
        except ValueError as exc:
            raise WeatherServiceError(str(exc)) from None
        # Postal codes may contain letters, spaces and hyphens (GB, CA, JP...).
        # For a combined old input, use the component containing the postal code.
        patterns = {"DE": r"\d{5}", "FR": r"\d{5}", "US": r"\d{5}(?:-\d{4})?",
                    "AT": r"\d{4}", "CH": r"\d{4}", "AU": r"\d{4}", "NZ": r"\d{4}",
                    "GB": r"(?:[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}|GIR\s*0AA)",
                    "JP": r"\d{3}-?\d{4}", "CA": r"[A-Z]\d[A-Z]\s*\d[A-Z]\d",
                    "NL": r"\d{4}\s*[A-Z]{2}"}
        pattern = patterns.get(country)
        if pattern:
            match = re.search(r"(?<![\w-])(" + pattern + r")(?![\w-])", base, re.I)
            postal = match[1].upper() if match else None
        else:
            # General postal components also preserve alphabetic prefixes (MT, LV,
            # etc.). Do not turn a number inside an ordinary town name into a ZIP.
            postal = next((part.strip().upper() for part in base.split(',')
                           if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 -]{1,15}", part.strip())
                           and any(c.isdigit() for c in part)
                           and all(len(word) <= 4 for word in re.findall(r"[A-Za-z]+", part))), None)
        if postal:
            params = {"zip": f"{postal},{country}", "appid": key}
            result = self._request(GEO + "/zip?" + urllib.parse.urlencode(params))
            if not isinstance(result, dict) or str(result.get("country", "")).upper() != country:
                raise WeatherServiceError("Die Postleitzahl wurde keinem passenden Land zugeordnet.")
            validate_place(result)
            return result
        params = {"q": f"{base},{country}", "limit": 5, "appid": key}
        results = self._request(GEO + "/direct?" + urllib.parse.urlencode(params))
        if not isinstance(results, list) or not results:
            raise WeatherServiceError("Für diesen Ort wurde kein eindeutiger Treffer gefunden.")
        results = [r for r in results if isinstance(r, dict) and str(r.get("country", "")).upper() == country]
        for result in results:
            validate_place(result)
        unique = {(round(float(r["lat"]), 4), round(float(r["lon"]), 4), r.get("country")): r
                  for r in results if isinstance(r, dict) and "lat" in r and "lon" in r}
        if not unique:
            raise WeatherServiceError("Für diesen Ort wurde kein Treffer im angegebenen Land gefunden.")
        if len(unique) != 1:
            names = sorted({str(r.get("name", "Ort")) + (", " + str(r.get("state")) if r.get("state") else "") for r in unique.values()})
            raise WeatherServiceError("Der Ort ist im gewählten Land mehrdeutig. Bitte eine Postleitzahl oder Region ergänzen: " + "; ".join(names[:5]))
        return next(iter(unique.values()))

    def _query_hash(self, query: str) -> str:
        return hashlib.sha256(normalize_query(query).encode("utf-8")).hexdigest()

    @staticmethod
    def _country_matches(query, place):
        try:
            return split_query(query)[1] == place["country"].upper()
        except (ValueError, TypeError, KeyError, AttributeError):
            return False

    def _cache_path(self, query: str, kind: str) -> Path:
        return self.cache_dir / f"{kind}-{self._query_hash(query)}.json"

    def _legacy_current_path(self, query: str) -> Path:
        return self.cache_dir / f"{self._query_hash(query)}.json"

    def _place_path(self, query: str) -> Path:
        return self.cache_dir / f"place-{self._query_hash(query)}.json"

    def _load_json(self, path: Path) -> dict[str, Any] | None:
        if path in self._volatile:
            return self._volatile[path]
        try:
            if path.stat().st_size > MAX_RESPONSE_BYTES:
                return None
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, ValueError, TypeError, RecursionError):
            return None

    def _read_legacy_place(self, query: str) -> dict[str, Any] | None:
        """Reuse old coordinates for lookup only; legacy observations are never displayed."""
        data = self._load_json(self._legacy_current_path(query))
        if not data or data.get("query") != normalize_query(query):
            return None
        try:
            return {"name": str(data["name"]), "country": str(data["country"]),
                    "lat": float(data["lat"]), "lon": float(data["lon"])}
        except (KeyError, TypeError, ValueError):
            return None

    def load_cached(self, query: str) -> WeatherRecord | None:
        data = self._load_json(self._cache_path(query, "current"))
        if not data or data.get("query") != normalize_query(query):
            return None
        try:
            record = WeatherRecord(**data)
            if self._age_seconds(record.retrieved_at) > MAX_CACHE_AGE or not self._country_matches(query, data):
                return None
            return record
        except (TypeError, ValueError, KeyError, OverflowError):
            return None

    def load_cached_forecast(self, query: str) -> ForecastRecord | None:
        parts = {kind: self._load_forecast_part(query, kind)
                 for kind in ("hourly", "daily")}
        parts = {kind: value for kind, value in parts.items()
                 if value and value.get("query") == normalize_query(query)}
        if not parts:
            return None
        try:
            first = next(iter(parts.values()))
            hourly_data, daily_data = parts.get("hourly"), parts.get("daily")
            return ForecastRecord(
                query=normalize_query(query), name=str(first["name"]), country=str(first["country"]),
                lat=float(first["lat"]), lon=float(first["lon"]),
                timezone=str(first["timezone"]),
                retrieved_at=max(str(value["retrieved_at"]) for value in parts.values()),
                hourly=tuple(ForecastEntry(**entry) for entry in (hourly_data or {}).get("entries", [])),
                daily=tuple(ForecastEntry(**entry) for entry in (daily_data or {}).get("entries", [])),
                hourly_retrieved_at=(str(hourly_data["retrieved_at"]) if hourly_data else None),
                daily_retrieved_at=(str(daily_data["retrieved_at"]) if daily_data else None),
                errors=tuple(dict.fromkeys(value["_storage_warning"] for value in parts.values()
                                          if value.get("_storage_warning"))))
        except (TypeError, ValueError, KeyError, OverflowError):
            return None

    def _load_forecast_part(self, query: str, kind: str) -> dict[str, Any] | None:
        data = self._load_json(self._cache_path(query, f"forecast-{kind}"))
        if data and data.get("query") == normalize_query(query) and isinstance(data.get("entries"), list):
            try:
                validate_place(data)
                if not self._country_matches(query, data):
                    return None
                if not isinstance(data.get("timezone"), str) or self._age_seconds(data["retrieved_at"]) > MAX_CACHE_AGE:
                    return None
                entries = []
                for row in data["entries"][:FORECAST_DAILY_COUNT if kind == "daily" else FORECAST_HOURLY_COUNT]:
                    try:
                        entry = ForecastEntry(**row)
                        if kind == "daily" and (entry.temp_min is None or entry.temp_max is None):
                            continue
                        entries.append(asdict(entry))
                    except (ValueError, TypeError, KeyError, OverflowError):
                        continue
                return {**data, "entries": entries} if entries else None
            except (ValueError, TypeError, KeyError, OverflowError):
                return None
        return None

    def _save_forecast_part(self, query: str, kind: str, *, place: dict[str, Any],
                            timezone_name: str, entries: tuple[ForecastEntry, ...]) -> dict[str, Any]:
        data = {
            "query": normalize_query(query), "name": str(place.get("name") or query),
            "country": str(place.get("country") or ""), "lat": float(place["lat"]),
            "lon": float(place["lon"]), "timezone": timezone_name,
            "retrieved_at": utc_now(), "entries": [asdict(entry) for entry in entries],
        }
        self._safe_save(query, f"forecast-{kind}", data)
        return data

    def _safe_save(self, query: str, kind: str, data: dict[str, Any]) -> None:
        try:
            self._save(query, kind, data)
            self._volatile.pop(self._cache_path(query, kind), None)
        except OSError:
            self.storage_warning = "Lokaler Cache konnte nicht gespeichert werden; neue Daten gelten nur für diese Sitzung."
            volatile = dict(data)
            if kind == "current":
                volatile["warnings"] = (self.storage_warning,)
            elif kind.startswith("forecast-"):
                volatile["_storage_warning"] = self.storage_warning
            self._volatile[self._cache_path(query, kind)] = volatile

    def _save(self, query: str, kind: str, data: dict[str, Any]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_path(query, kind)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                             prefix=f"{kind}-", suffix=".tmp", delete=False) as handle:
                temp_path = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            replace_file(temp_path, path)
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

    def _place(self, query: str, key: str) -> dict[str, Any]:
        normalized = normalize_query(query)
        if normalized in self._places:
            place = self._places[normalized]
            if self._country_matches(query, place):
                return place
        cached_place = self._load_json(self._place_path(query))
        if cached_place and cached_place.get("query") == normalize_query(query):
            place = cached_place.get("place")
            try:
                validate_place(place)
                if self._country_matches(query, place):
                    self._places[normalized] = place
                    return place
            except (ValueError, TypeError, KeyError, OverflowError):
                pass
        current = self.load_cached(query)
        if current:
            return {"name": current.name, "country": current.country, "lat": current.lat,
                    "lon": current.lon, "timezone": current.timezone}
        cached_forecast = self.load_cached_forecast(query)
        if cached_forecast:
            place = {"name": cached_forecast.name, "country": cached_forecast.country,
                     "lat": cached_forecast.lat, "lon": cached_forecast.lon,
                     "timezone": cached_forecast.timezone}
            self._safe_save(normalize_query(query), "place", {"query": normalize_query(query), "place": place})
            return place
        legacy = self._read_legacy_place(query)
        if legacy and self._country_matches(query, legacy):
            place = legacy
        else:
            place = self._resolve(query, key)
        validate_place(place)
        if not self._country_matches(query, place):
            raise WeatherServiceError("Die Ortsposition passt nicht zum ausgewählten Land.")
        self._places[normalized] = place
        self._safe_save(normalize_query(query), "place", {"query": normalize_query(query), "place": place})
        return place

    def load_resolved_place(self, query: str) -> dict[str, Any] | None:
        """Reuse the weather position without geocoding or consuming an API slot."""
        normalized = normalize_query(query)
        place = self._places.get(normalized)
        if place is None:
            data = self._load_json(self._place_path(query))
            if data and data.get("query") == normalized:
                place = data.get("place")
        try:
            validate_place(place)
            if not self._country_matches(query, place):
                raise ValueError("wrong country in place cache")
            self._places[normalized] = dict(place)
            return dict(place)
        except (ValueError, TypeError, KeyError, OverflowError):
            pass
        record = self.load_cached(query) or self.load_cached_forecast(query)
        if record:
            place = {"name": record.name, "country": record.country, "lat": record.lat, "lon": record.lon}
            self._places[normalized] = place
            return dict(place)
        return None

    def has_resolved_place(self, query: str) -> bool:
        return self.load_resolved_place(query) is not None

    @staticmethod
    def _local_iso(timestamp: Any, timezone_name: str, offset: Any = 0) -> str:
        dt = datetime.fromtimestamp(number(timestamp, 0), timezone.utc)
        try:
            zone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, TypeError, ValueError):
            zone = timezone.utc
        return dt.astimezone(zone).isoformat(timespec="minutes")

    @staticmethod
    def _description(record: dict[str, Any]) -> str:
        weather = record.get("weather")
        if not isinstance(weather, list) or not weather or not isinstance(weather[0], dict):
            return "Beschreibung fehlt"
        return " ".join(str(weather[0].get("description") or "Beschreibung fehlt").split())[:160].capitalize()

    def fetch(self, query: str, key: str, *, force: bool = False) -> WeatherRecord:
        if not key:
            raise WeatherServiceError("OpenWeather-Schlüssel fehlt. Bitte unter Einstellungen speichern.")
        normalized = normalize_query(query)
        if not normalized:
            raise WeatherServiceError("Bitte einen Ort eingeben.")
        cached = self.load_cached(query)
        if cached and not force and self._age_seconds(cached.retrieved_at) < CURRENT_CACHE_TTL:
            return cached
        try:
            self.storage_warning = ""
            place = self._place(query, key)
            params = {"lat": place["lat"], "lon": place["lon"], "appid": key, "units": "metric", "lang": "de"}
            payload = self._request(ONE_CALL + "/current?" + urllib.parse.urlencode(params))
            rows = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
                raise WeatherServiceError("OpenWeather hat unvollständige aktuelle Wetterdaten geliefert.")
            data = rows[0]
            timezone_name = str(payload.get("timezone") or place.get("timezone") or "")
            timezone_offset = payload.get("timezone_offset", 0)
            name = str(place.get("name") or query)
            country = str(place.get("country") or "")
            retrieved = utc_now()
            record = WeatherRecord(
                query=normalized, name=name, country=country, lat=float(place["lat"]), lon=float(place["lon"]),
                timezone=timezone_name, observed_at=self._local_iso(data["dt"], timezone_name, timezone_offset),
                retrieved_at=retrieved, temp=number(data["temp"]), feels_like=number(data["feels_like"]),
                humidity=int(number(data["humidity"], 0, 100)), pressure=int(number(data["pressure"], 0)),
                wind_speed=number(data["wind_speed"], 0), description=self._description(data))
            self._safe_save(normalized, "current", asdict(record))
            return replace(record, warnings=(self.storage_warning,)) if self.storage_warning else record
        except WeatherServiceError:
            raise
        except OSError:
            raise WeatherServiceError("Der lokale Wettercache konnte nicht gespeichert werden.") from None
        except (KeyError, TypeError, ValueError, OverflowError):
            raise WeatherServiceError("OpenWeather hat unvollständige aktuelle Wetterdaten geliefert.") from None

    def fetch_forecast(self, query: str, key: str, *, force: bool = False) -> ForecastRecord:
        if not key:
            raise WeatherServiceError("OpenWeather-Schlüssel fehlt. Bitte unter Einstellungen speichern.")
        normalized = normalize_query(query)
        if not normalized:
            raise WeatherServiceError("Bitte einen Ort eingeben.")
        try:
            self.storage_warning = ""
            place = self._place(query, key)
            params = {"lat": place["lat"], "lon": place["lon"], "appid": key, "units": "metric", "lang": "de"}
            base = f"{ONE_CALL}/timeline"
            cached = self.load_cached_forecast(query)
            hourly_part, daily_part = self._load_forecast_part(query, "hourly"), self._load_forecast_part(query, "daily")
            errors: list[str] = []
            timezone_name = str(place.get("timezone") or (cached.timezone if cached else ""))
            entries_by_kind = {"hourly": cached.hourly if cached else (),
                               "daily": cached.daily if cached else ()}
            for kind, path, ttl, daily in (
                ("hourly", "/1h", FORECAST_CACHE_TTL, False),
                ("daily", "/1day", FORECAST_CACHE_TTL, True),
            ):
                part = hourly_part if kind == "hourly" else daily_part
                if part and not force and self._age_seconds(part.get("retrieved_at", "")) < ttl:
                    continue
                try:
                    payload = self._request(base + path + "?" + urllib.parse.urlencode(params))
                    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                        raise WeatherServiceError("OpenWeather hat unvollständige Vorhersagedaten geliefert.")
                    timezone_name = str(payload.get("timezone") or timezone_name)
                    offset = payload.get("timezone_offset", 0)
                    # The first page is enough for the display; never follow next/prev links.
                    entries = tuple(self._parse_rows(payload["data"], timezone_name, offset, daily=daily))
                    if not entries:
                        raise WeatherServiceError("OpenWeather hat keine Vorhersagezeiträume geliefert.")
                    # Keep the complete already-paid first page for custom timelines.
                    # Store normalized values and a timestamp, never the keyed next URL.
                    from wetterstation.designer.timeline_client import snapshot
                    try:
                        self._safe_save(query, 'timeline-base-'+path[1:],
                                        snapshot(payload, path[1:], query, datetime.now(timezone.utc)))
                    except (ValueError, TypeError):
                        pass  # A malformed continuation must not break the base forecast.
                    if len(entries) < len(payload["data"]):
                        errors.append(f"{kind}: Ungültige Vorhersagezeilen wurden ausgelassen.")
                    max_items = FORECAST_DAILY_COUNT if daily else FORECAST_HOURLY_COUNT
                    entries_by_kind[kind] = entries[:max_items]
                    saved_part = self._save_forecast_part(query, kind, place=place,
                                                         timezone_name=timezone_name, entries=entries_by_kind[kind])
                    if kind == "hourly":
                        hourly_part = saved_part
                    else:
                        daily_part = saved_part
                except WeatherServiceError as exc:
                    errors.append(f"{kind}: {exc}")
            if not entries_by_kind["hourly"] and not entries_by_kind["daily"]:
                if errors:
                    raise WeatherServiceError("Vorhersage nicht verfügbar · " + " · ".join(errors))
                raise WeatherServiceError("OpenWeather hat keine Vorhersagezeiträume geliefert.")
            if self.storage_warning:
                errors.append(self.storage_warning)
            retrieved_values = [str(part["retrieved_at"]) for part in (hourly_part, daily_part) if part]
            retrieved_at = max(retrieved_values) if retrieved_values else utc_now()
            return ForecastRecord(
                query=normalized, name=str(place.get("name") or query),
                country=str(place.get("country") or ""), lat=float(place["lat"]), lon=float(place["lon"]),
                timezone=timezone_name, retrieved_at=retrieved_at,
                hourly=entries_by_kind["hourly"], daily=entries_by_kind["daily"],
                hourly_retrieved_at=(str(hourly_part["retrieved_at"]) if hourly_part else None),
                daily_retrieved_at=(str(daily_part["retrieved_at"]) if daily_part else None),
                errors=tuple(errors))
        except WeatherServiceError:
            raise
        except OSError:
            raise WeatherServiceError("Der lokale Vorhersagecache konnte nicht gespeichert werden.") from None
        except (KeyError, TypeError, ValueError, OverflowError):
            raise WeatherServiceError("OpenWeather hat unvollständige Vorhersagedaten geliefert.") from None

    @classmethod
    def _parse_rows(cls, rows: list[Any], timezone_name: str, offset: Any, *, daily: bool) -> list[ForecastEntry]:
        parsed = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            try:
                parsed.append(cls._parse_entry(row, timezone_name, offset, daily=daily))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        return parsed

    @classmethod
    def _parse_entry(cls, row: dict[str, Any], timezone_name: str, offset: Any, *, daily: bool) -> ForecastEntry:
        if daily:
            temps = row.get("temp")
            if not isinstance(temps, dict) or "min" not in temps or "max" not in temps:
                raise ValueError("daily temperatures missing")
            temp = number(temps.get("day", temps["max"]))
            temp_min, temp_max = number(temps["min"]), number(temps["max"])
        else:
            temp = number(row["temp"])
            temp_min = temp_max = None
        return ForecastEntry(
            timestamp=cls._local_iso(row["dt"], timezone_name, offset), temp=temp,
            description=cls._description(row),
            precipitation_probability=number(row.get("pop", 0), 0, 1),
            wind_speed=number(row.get("wind_speed", 0), 0), temp_min=temp_min, temp_max=temp_max)

    @staticmethod
    def _age_seconds(timestamp: str) -> float:
        try:
            retrieved = aware_time(timestamp)
            age = (datetime.now(timezone.utc) - retrieved.astimezone(timezone.utc)).total_seconds()
            return max(0.0, age) if age >= -300 else float("inf")
        except (TypeError, ValueError, OverflowError):
            return float("inf")
