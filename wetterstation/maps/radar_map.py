"""Bounded public WMS downloads: a light street basemap with DWD observations."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, replace
from io import BytesIO
from datetime import datetime, timezone, timedelta
from pathlib import Path

from wetterstation.storage.api_key_store import default_settings_path
from wetterstation.storage.file_io import replace_file
from wetterstation.weather.countries import COUNTRIES


LATITUDE = 52.39890000
LONGITUDE = 13.06570000
LOCATION_ID = "potsdam-14467"
RADAR_URL = "https://maps.dwd.de/geoserver/wms"
RADAR_LAYER = "dwd:Radar_wn-analysis_1x1km_ger"
RADAR_STYLE = "radar_wn-analysis_1x1km_ger"
# GeoServer's layer-scoped capabilities avoid downloading every DWD layer.
RADAR_METADATA_URL = "https://maps.dwd.de/geoserver/dwd/Radar_wn-analysis_1x1km_ger/wms"
BASEMAP_URL = "https://sgx.geodatenzentrum.de/wms_basemapde"
BASEMAP_LAYER = "de_basemapde_web_raster_farbe"
BASEMAP_STYLE = "default"
BASEMAP_ATTRIBUTION = "© GeoBasis-DE / BKG 2026 · CC BY 4.0"
ATTRIBUTION = BASEMAP_ATTRIBUTION + " · Radar: Deutscher Wetterdienst"
MAX_RADAR_CACHE_AGE = 60 * 60
RADAR_LAT_SPAN = .26


class RadarMapError(Exception):
    """Only fixed, safe messages cross the worker/UI boundary."""


@dataclass(frozen=True)
class MapPosition:
    query: str
    name: str
    lat: float
    lon: float
    country: str = "DE"

    def __post_init__(self):
        if (not self.query.strip() or not self.name.strip() or self.country not in COUNTRIES
                or isinstance(self.lat, bool) or isinstance(self.lon, bool)
                or not math.isfinite(self.lat) or not math.isfinite(self.lon)
                or not -90 <= self.lat <= 90 or not -180 <= self.lon <= 180
                or (self.country == "DE" and not (47 <= self.lat <= 56 and 5 <= self.lon <= 16))):
            raise ValueError("Keine gültige bestätigte Kartenposition.")

    @property
    def identity(self) -> str:
        return f"{' '.join(self.query.casefold().split())}|{self.lat:.8f}|{self.lon:.8f}|{self.country}"


POTSDAM = MapPosition(LOCATION_ID, "Potsdam", LATITUDE, LONGITUDE)


@dataclass(frozen=True)
class RadarMapResult:
    basemap: bytes
    radar: bytes
    observed_at: datetime
    fetched_at: datetime
    stale: bool = False
    warning: str = ""
    position: MapPosition = POTSDAM
    provider: str = "dwd"
    coverage: bytes = b""
    coverage_status: str = "full"

    @property
    def attribution(self):
        return "© OpenStreetMap-Mitwirkende · RainViewer" if self.provider == "rainviewer" else ""


class RadarMapClient:
    """A small, timeout-bounded client for the two approved public WMS services."""

    def __init__(self, cache_dir: str | Path | None = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else default_settings_path().parent / "cache" / "radar"
        self.timeout = 10
        self._memory: dict[str, RadarMapResult] = {}
        self._previous: RadarMapResult | None = None
        self._radar_available_from: datetime | None = None

    @staticmethod
    def image_size(width: int, height: int) -> tuple[int, int]:
        width, height = max(1, int(width)), max(1, int(height))
        scale = min(1, 1800 / width, 1100 / height)
        return max(320, round(width * scale)), max(240, round(height * scale))

    @staticmethod
    def _validate_png(data: bytes, size: tuple[int, int] | None = None) -> None:
        from PIL import Image
        if len(data) > 15_000_000:
            raise ValueError("oversized image")
        with Image.open(BytesIO(data)) as image:
            if image.format != "PNG" or image.width * image.height > 4_000_000:
                raise ValueError("invalid image")
            if size is not None and image.size != size:
                raise ValueError("incorrect image size")
            image.load()

    @staticmethod
    def is_verified_start_location(location: str) -> bool:
        normalized = re.sub(r"[^a-z0-9]+", " ", location.casefold()).strip()
        return normalized in {
            "potsdam", "potsdam 14467", "14467 potsdam",
            "potsdam 14467 deutschland", "14467 potsdam deutschland",
        }

    @staticmethod
    def bbox(width: int, height: int, position: MapPosition = POTSDAM) -> str:
        # Preserve map scale: longitude degrees are shorter than latitude degrees.
        import math
        lat_span = RADAR_LAT_SPAN
        lon_span = lat_span * (width / height) / math.cos(math.radians(position.lat))
        return ",".join(f"{v:.8f}" for v in (
            position.lon - lon_span / 2, position.lat - lat_span / 2,
            position.lon + lon_span / 2, position.lat + lat_span / 2,
        ))

    def _request(self, url: str) -> bytes:
        request = urllib.request.Request(url, headers={"User-Agent": "WetterstationPreview/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            content_type = response.headers.get_content_type()
            data = response.read(15_000_001)
        if len(data) > 15_000_000:
            raise ValueError("Kartendienst hat ein zu großes Bild geliefert.")
        if content_type not in {"image/png", "application/vnd.ogc.se_xml"}:
            raise ValueError("Kartendienst hat kein PNG-Bild geliefert.")
        if content_type != "image/png" or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Kartendienst meldet einen Kartenfehler statt eines Bildes.")
        self._validate_png(data)
        return data

    @staticmethod
    def _url(base: str, parameters: dict[str, str]) -> str:
        return base + "?" + urllib.parse.urlencode(parameters)

    def _radar_timestamp(self) -> datetime:
        url = self._url(RADAR_METADATA_URL, {"SERVICE": "WMS", "REQUEST": "GetCapabilities", "VERSION": "1.3.0"})
        request = urllib.request.Request(url, headers={"User-Agent": "WetterstationPreview/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            data = response.read(2_000_001)
        if len(data) > 2_000_000:
            raise ValueError("DWD-Metadatenantwort ist unerwartet groß.")
        root = ET.fromstring(data)
        target = None
        for layer in root.iter():
            if layer.tag.rsplit("}", 1)[-1] != "Layer":
                continue
            name = next((child.text for child in layer if child.tag.rsplit("}", 1)[-1] == "Name"), None)
            # Layer-scoped GeoServer responses omit the workspace prefix.
            if name in {RADAR_LAYER, RADAR_LAYER.split(":", 1)[-1]}:
                target = layer
                break
        if target is None:
            raise ValueError("Der aktuelle DWD-Beobachtungs-Layer ist nicht verfügbar.")
        for dimension in target:
            if dimension.tag.rsplit("}", 1)[-1] in {"Dimension", "Extent"} and dimension.attrib.get("name", "").casefold() == "time":
                value = dimension.attrib.get("default", "")
                if value.casefold() == "current":
                    value = (dimension.text or "").split("/")[1:2]
                    value = value[0] if value else ""
                if not value:
                    value = (dimension.text or "").split("/")[1:2]
                    value = value[0] if value else ""
                stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=timezone.utc)
                stamp = stamp.astimezone(timezone.utc)
                if stamp > datetime.now(timezone.utc):
                    raise ValueError("DWD meldet einen Beobachtungszeitpunkt in der Zukunft.")
                self._radar_available_from = None
                try:
                    parts = (dimension.text or "").strip().split("/")
                    if len(parts) == 3 and parts[2] == "PT5M":
                        start = datetime.fromisoformat(parts[0].replace("Z", "+00:00"))
                        if start.tzinfo is not None and start <= stamp:
                            self._radar_available_from = start
                except ValueError:
                    pass
                return stamp
        raise ValueError("Der DWD-Layer liefert keinen Beobachtungszeitpunkt.")

    def _map_url(self, base: str, layer: str, style: str, bbox: str,
                 width: int, height: int, transparent: bool) -> str:
        return self._url(base, {
            "SERVICE": "WMS", "VERSION": "1.1.1", "REQUEST": "GetMap",
            "LAYERS": layer, "STYLES": style, "SRS": "EPSG:4326", "BBOX": bbox,
            "WIDTH": str(width), "HEIGHT": str(height), "FORMAT": "image/png",
            "TRANSPARENT": "TRUE" if transparent else "FALSE",
        })

    def _cache_key(self, width: int, height: int, position: MapPosition = POTSDAM) -> str:
        material = f"v3|{position.identity}|{self.bbox(width, height, position)}|EPSG:4326|{width}x{height}|{RADAR_LAYER}|{RADAR_STYLE}|{BASEMAP_URL}|{BASEMAP_LAYER}|{BASEMAP_STYLE}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:20]

    def _write_cache(self, key: str, result: RadarMapResult, width: int, height: int) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        values = {
            "location_id": result.position.identity, "bbox": self.bbox(width, height, result.position), "crs": "EPSG:4326",
            "width": width, "height": height, "radar_layer": RADAR_LAYER,
            "radar_style": RADAR_STYLE, "observed_at": result.observed_at.isoformat(),
            "fetched_at": result.fetched_at.isoformat(),
            "basemap_url": BASEMAP_URL, "basemap_layer": BASEMAP_LAYER,
        }
        files = {}
        for suffix, body in (("base", result.basemap), ("radar", result.radar)):
            filename = f"{key}.{suffix}.{hashlib.sha256(body).hexdigest()[:20]}.png"
            self._atomic_write(self.cache_dir / filename, body)
            files[suffix] = filename
        values["files"] = files
        self._atomic_write(self.cache_dir / f"{key}.json", json.dumps(values).encode("utf-8"))

    @staticmethod
    def _atomic_write(target: Path, body: bytes) -> None:
        # The manifest is replaced last; interrupted writes cannot mix images.
        fd, temporary = tempfile.mkstemp(prefix="radar-", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            replace_file(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def _read_cache(self, key: str, width: int, height: int, position: MapPosition = POTSDAM) -> RadarMapResult | None:
        try:
            manifest = self.cache_dir / f"{key}.json"
            if manifest.stat().st_size > 32_000:
                return None
            meta = json.loads(manifest.read_text(encoding="utf-8"))
            if (not isinstance(meta, dict) or meta.get("location_id") != position.identity
                    or meta.get("bbox") != self.bbox(width, height, position) or meta.get("crs") != "EPSG:4326"
                    or meta.get("width") != width or meta.get("height") != height
                    or meta.get("radar_layer") != RADAR_LAYER or meta.get("radar_style") != RADAR_STYLE
                    or meta.get("basemap_url") != BASEMAP_URL or meta.get("basemap_layer") != BASEMAP_LAYER):
                return None
            observed = datetime.fromisoformat(meta["observed_at"])
            fetched = datetime.fromisoformat(meta["fetched_at"])
            now = datetime.now(timezone.utc)
            if any(stamp.tzinfo is None or not 0 <= (now-stamp).total_seconds() <= MAX_RADAR_CACHE_AGE for stamp in (observed, fetched)):
                return None
            images = []
            for kind in ("base", "radar"):
                filename = meta["files"][kind]
                if not isinstance(filename, str) or not re.fullmatch(re.escape(key) + r"\." + kind + r"\.[0-9a-f]{20}\.png", filename):
                    return None
                path = self.cache_dir / filename
                if path.stat().st_size > 15_000_000:
                    return None
                body = path.read_bytes()
                if hashlib.sha256(body).hexdigest()[:20] not in filename:
                    return None
                self._validate_png(body, (width, height))
                images.append(body)
            return RadarMapResult(*images, observed, fetched, True, position=position)
        except Exception:
            return None

    def fetch(self, width: int, height: int, position: MapPosition = POTSDAM, *, allow_basemap_download=True) -> RadarMapResult:
        if position.country != "DE":
            if not hasattr(self, "_international"):
                from wetterstation.maps.international_map import InternationalMapClient
                self._international = InternationalMapClient(self.cache_dir / "international")
            return self._international.fetch(width, height, position, allow_basemap_download=allow_basemap_download)
        width, height = self.image_size(width, height)
        bbox, key = self.bbox(width, height, position), self._cache_key(width, height, position)
        stage = "DWD-Metadaten"
        try:
            observed_at = self._radar_timestamp()
            stage = "Helle Grundkarte"
            base = self._request(self._map_url(BASEMAP_URL, BASEMAP_LAYER, BASEMAP_STYLE, bbox, width, height, False))
            self._validate_png(base, (width, height))
            stage = "DWD-Radar"
            radar_url = self._map_url(RADAR_URL, RADAR_LAYER, RADAR_STYLE, bbox, width, height, True)
            radar_url += "&" + urllib.parse.urlencode({"TIME": observed_at.isoformat().replace("+00:00", "Z")})
            radar = self._request(radar_url)
            self._validate_png(radar, (width, height))
            result = RadarMapResult(base, radar, observed_at, datetime.now(timezone.utc), position=position)
            previous = self._memory.get(key) or self._read_cache(key, width, height, position)
            if (previous is not None and previous.position == position
                    and (observed_at - previous.observed_at).total_seconds() in (300, 600)):
                self._previous = previous
            try:
                self._write_cache(key, result, width, height)
            except OSError:
                result = replace(result, warning="Neue Karte nur für diese Sitzung: Speichern des Caches fehlgeschlagen.")
            self._memory[key] = result
            return result
        except Exception as exc:
            cached = self._memory.get(key)
            if cached is not None and any(not 0 <= (datetime.now(timezone.utc)-stamp).total_seconds() <= MAX_RADAR_CACHE_AGE
                                          for stamp in (cached.observed_at, cached.fetched_at)):
                cached = None
            cached = cached or self._read_cache(key, width, height, position)
            if cached is not None:
                return replace(cached, stale=True, warning="Aktueller Kartenabruf fehlgeschlagen; Cache höchstens 60 Minuten alt.")
            if isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionError)):
                raise RadarMapError(f"{stage} momentan nicht erreichbar; kein gültiger Karten-Cache.") from None
            if isinstance(exc, ImportError):
                raise RadarMapError("Kartenanzeige benötigt die Bildbibliothek Pillow.") from None
            detail = "Antwort oder Zeitangabe ungültig" if stage == "DWD-Metadaten" else "Abruf oder Bildprüfung fehlgeschlagen"
            raise RadarMapError(f"{stage}: {detail}; kein gültiger Karten-Cache.") from None

    def previous_observation(self, current: RadarMapResult) -> RadarMapResult | None:
        """Memory-only lookup; safe for the UI, including repeated manual refreshes."""
        if (current.provider == "dwd" and self._previous is not None and self._previous.position == current.position
                and (current.observed_at - self._previous.observed_at).total_seconds() in (300, 600)):
            return self._previous
        return None

    def fetch_previous(self, current: RadarMapResult) -> RadarMapResult:
        """Reuse an observation, or fetch one older radar PNG. Never replace the live cache."""
        if current.stale or current.provider != "dwd":
            raise RadarMapError("Kein passendes Radarvergleichsbild verfügbar.")
        previous = self.previous_observation(current)
        if previous is not None:
            return previous
        observed = current.observed_at - timedelta(minutes=5)
        if (current.stale or self._radar_available_from is None
                or observed < self._radar_available_from):
            raise RadarMapError("Kein passendes Radarvergleichsbild verfügbar.")
        try:
            from PIL import Image
            with Image.open(BytesIO(current.radar)) as image:
                width, height = image.size
            url = self._map_url(RADAR_URL, RADAR_LAYER, RADAR_STYLE,
                                self.bbox(width, height, current.position), width, height, True)
            url += "&" + urllib.parse.urlencode({"TIME": observed.isoformat().replace("+00:00", "Z")})
            radar = self._request(url)
            self._validate_png(radar, (width, height))
            result = replace(current, radar=radar, observed_at=observed)
            self._previous = result
            return result
        except Exception:
            raise RadarMapError("Radarvergleichsbild momentan nicht verfügbar.") from None
