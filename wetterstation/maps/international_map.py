"""Demand-loaded Web Mercator OSM/RainViewer layers, with bounded private caches.

Only tiles intersecting the requested viewport are loaded. Radar and coverage use
exactly the same XYZ tile geometry as the basemap. No account or key is involved.
"""
import hashlib
import json
import math
import re
import urllib.request
import urllib.error
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path

from wetterstation.maps.radar_map import RadarMapClient, RadarMapResult, RadarMapError, MAX_RADAR_CACHE_AGE

METADATA_URL = "https://api.rainviewer.com/public/weather-maps.json"
OSM_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ZOOM = 7
MERCATOR_LIMIT = 85.0511287798066
USER_AGENT = "WetterstationPreview/2.0 (private desktop weather display)"


def viewport(width, height, position):
    if abs(position.lat) > MERCATOR_LIMIT:
        raise RadarMapError("Für diesen Breitengrad ist keine Straßen-/Regenkarte darstellbar (Grenze ±85,051°).")
    world = 256 * 2**ZOOM
    cx = (position.lon + 180) / 360 * world
    cy = (1 - math.asinh(math.tan(math.radians(position.lat))) / math.pi) / 2 * world
    left, top = math.floor(cx - width / 2), math.floor(cy - height / 2)
    tiles = [(x, y) for y in range(top // 256, (top + height - 1) // 256 + 1)
             for x in range(left // 256, (left + width - 1) // 256 + 1) if 0 <= y < 2**ZOOM]
    return left, top, tiles


def png(image):
    with BytesIO() as stream:
        image.save(stream, "PNG")
        return stream.getvalue()


class InternationalMapClient:
    def __init__(self, cache_dir):
        self.cache_dir = Path(cache_dir)
        self.timeout = 10
        self._memory = {}

    def _download(self, url, headers=None):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        # Do not follow provider-controlled redirects to arbitrary destinations.
        from wetterstation.weather.weather_service import _NoRedirect
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as response:
                body = response.read(2_000_001)
                if len(body) > 2_000_000:
                    raise ValueError("oversized map response")
                return body, dict(response.headers), response.status
        except urllib.error.HTTPError as exc:
            if exc.code == 304:
                return b"", dict(exc.headers), 304
            raise

    def _tile(self, url, *, osm=False, allow_download=True):
        key = hashlib.sha256(url.encode()).hexdigest()
        folder = self.cache_dir / "tiles"
        image_path, meta_path = folder / f"{key}.png", folder / f"{key}.json"
        now = datetime.now(timezone.utc).timestamp()
        meta, cached = {}, None
        try:
            if meta_path.stat().st_size < 16000 and image_path.stat().st_size <= 2_000_000:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                cached = image_path.read_bytes()
                RadarMapClient._validate_png(cached, (256, 256))
                if hashlib.sha256(cached).hexdigest() != meta["digest"]:
                    raise ValueError("cache checksum")
                if 0 <= now - meta["stored_at"] and now < meta["expires_at"]:
                    return cached
        except (OSError, ValueError, KeyError, TypeError):
            meta, cached = {}, None
        if not allow_download:
            raise RadarMapError("Internationale Grundkarte wird erst beim Anzeigen geladen.")
        headers = {}
        if cached:
            for field, header in (("etag", "If-None-Match"), ("last_modified", "If-Modified-Since")):
                if meta.get(field):
                    headers[header] = meta[field]
        body, response_headers, status = self._download(url, headers)
        response_headers = {k.lower(): v for k, v in response_headers.items()}
        if status == 304:
            if cached is None:
                raise ValueError("304 without cache")
            body = cached
        RadarMapClient._validate_png(body, (256, 256))
        control = response_headers.get("cache-control", "")
        max_age = re.search(r"(?:^|,)\s*max-age=(\d+)", control)
        ttl = 7 * 86400 if osm else (86400 if "/coverage/" in url else 7200)
        if max_age:
            ttl = max(0, int(max_age[1]) - int(response_headers.get("age", "0")))
        elif response_headers.get("expires"):
            try:
                ttl = max(0, parsedate_to_datetime(response_headers["expires"]).timestamp() - now)
            except (ValueError, TypeError, OverflowError):
                pass
        if "no-cache" in control:
            ttl = 0
        if "no-store" not in control:
            metadata = {"stored_at": now, "expires_at": now + ttl,
                        "digest": hashlib.sha256(body).hexdigest(),
                        "etag": response_headers.get("etag", meta.get("etag")),
                        "last_modified": response_headers.get("last-modified", meta.get("last_modified"))}
            try:
                folder.mkdir(parents=True, exist_ok=True)
                RadarMapClient._atomic_write(image_path, body)
                RadarMapClient._atomic_write(meta_path, json.dumps(metadata).encode())
            except OSError:
                pass  # Current images remain usable; persistent frame reports storage errors.
        return body

    def _metadata(self):
        data, _, _ = self._download(METADATA_URL)
        meta = json.loads(data)
        host = meta["host"]
        if host != "https://tilecache.rainviewer.com":
            raise ValueError("unrecognized RainViewer tile host")
        frames = meta["radar"]["past"]
        if not isinstance(frames, list) or not 1 <= len(frames) <= 100:
            raise ValueError("invalid observations")
        frame = max(frames, key=lambda row: int(row["time"]))
        observed = datetime.fromtimestamp(int(frame["time"]), timezone.utc)
        if not 0 <= (datetime.now(timezone.utc) - observed).total_seconds() <= MAX_RADAR_CACHE_AGE:
            raise ValueError("expired radar frame")
        if frame["path"] != f"/v2/radar/{int(frame['time'])}":
            raise ValueError("invalid radar path")
        return host, frame["path"], observed

    @staticmethod
    def _key(width, height, position):
        return hashlib.sha256(f"rv1|{ZOOM}|{width}|{height}|{position.identity}".encode()).hexdigest()[:24]

    @staticmethod
    def _valid(result, position):
        return result is not None and result.position == position and all(
            0 <= (datetime.now(timezone.utc) - stamp).total_seconds() <= MAX_RADAR_CACHE_AGE
            for stamp in (result.fetched_at, result.observed_at))

    def _save(self, key, result):
        folder = self.cache_dir / "frames"
        folder.mkdir(parents=True, exist_ok=True)
        files = {}
        for kind in ("basemap", "radar", "coverage"):
            body = getattr(result, kind)
            name = f"{key}-{kind}-{hashlib.sha256(body).hexdigest()}.png"
            RadarMapClient._atomic_write(folder / name, body)
            files[kind] = name
        meta = {"identity": result.position.identity, "files": files,
                "observed": result.observed_at.isoformat(), "fetched": result.fetched_at.isoformat(),
                "coverage_status": result.coverage_status}
        RadarMapClient._atomic_write(folder / f"{key}.json", json.dumps(meta).encode())

    def _cached(self, key, width, height, position):
        result = self._memory.get(key)
        if self._valid(result, position):
            return result
        try:
            folder = self.cache_dir / "frames"
            path = folder / f"{key}.json"
            if path.stat().st_size > 16000:
                return None
            meta = json.loads(path.read_text(encoding="utf-8"))
            if meta["identity"] != position.identity or meta["coverage_status"] not in {"full", "partial", "none"}:
                return None
            images = {}
            for kind in ("basemap", "radar", "coverage"):
                name = meta["files"][kind]
                if not re.fullmatch(re.escape(f"{key}-{kind}-") + r"[a-f0-9]{64}\.png", name):
                    return None
                if (folder / name).stat().st_size > 15_000_000:
                    return None
                body = (folder / name).read_bytes()
                RadarMapClient._validate_png(body, (width, height))
                if hashlib.sha256(body).hexdigest() not in name:
                    return None
                images[kind] = body
            result = RadarMapResult(images["basemap"], images["radar"],
                datetime.fromisoformat(meta["observed"]), datetime.fromisoformat(meta["fetched"]),
                position=position, provider="rainviewer", coverage=images["coverage"], coverage_status=meta["coverage_status"])
            return result if self._valid(result, position) else None
        except Exception:
            return None

    def fetch(self, width, height, position, *, allow_basemap_download=True):
        from PIL import Image
        width, height = RadarMapClient.image_size(width, height)
        left, top, tiles = viewport(width, height, position)
        key = self._key(width, height, position)
        cached = self._cached(key, width, height, position)
        try:
            host, path, observed = self._metadata()
            if cached and observed == cached.observed_at:
                # A successful metadata check does not change the image retrieval time.
                return replace(cached, stale=False, warning="")
            layers = [Image.new("RGBA", (width, height), color) for color in
                      ((245, 244, 238, 255), (0, 0, 0, 0), (0, 0, 0, 255))]
            for x, y in tiles:
                tx = x % 2**ZOOM  # Wrap at the international date line.
                urls = (OSM_URL.format(z=ZOOM, x=tx, y=y),
                        f"{host}{path}/256/{ZOOM}/{tx}/{y}/2/1_0.png",
                        f"{host}/v2/coverage/0/256/{ZOOM}/{tx}/{y}/0/0_0.png")
                for index, url in enumerate(urls):
                    body = self._tile(url, osm=index == 0, allow_download=index != 0 or allow_basemap_download)
                    with Image.open(BytesIO(body)) as tile:
                        layers[index].paste(tile.convert("RGBA"), (x * 256 - left, y * 256 - top))
            alpha = layers[2].getchannel("A")
            low, high = alpha.getextrema()
            coverage = "full" if high == 0 else "none" if low == 255 else "partial"
            result = RadarMapResult(png(layers[0]), png(layers[1]), observed, datetime.now(timezone.utc),
                position=position, provider="rainviewer", coverage=png(layers[2]), coverage_status=coverage)
            try:
                self._save(key, result)
            except OSError:
                result = replace(result, warning="Neue Karte nur für diese Sitzung: Cache konnte nicht gespeichert werden.")
            self._memory[key] = result
            return result
        except Exception:
            if cached:
                return replace(cached, stale=True, warning="Internationaler Kartendienst ausgefallen; gültige Karte desselben Orts (höchstens 60 Minuten alt).")
            raise RadarMapError("Internationale Karte oder Radar-Abdeckungsmaske nicht verfügbar; kein gültiger Karten-Cache.") from None
