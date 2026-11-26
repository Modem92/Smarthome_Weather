"""Failure recovery with dummy credentials and isolated files; never live HTTP."""
import json
import queue
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from wetterstation.ui.app import WeatherPreview
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.openweather_budget import OpenWeatherBudget, BudgetUnavailable, _atomic_json
from wetterstation.maps.radar_map import (RadarMapClient, RadarMapError, BASEMAP_LAYER, BASEMAP_URL,
                       RADAR_URL, MAX_RADAR_CACHE_AGE, MapPosition)
from wetterstation.weather.weather_service import MAX_CACHE_AGE, MAX_RESPONSE_BYTES, OpenWeatherClient, WeatherServiceError
from test_one_call_v4 import FakeResponse
import test_one_call_v4 as contracts


class WeatherRecoveryTests(unittest.TestCase):
    def test_map_reuses_resolved_weather_place_without_api_request(self):
        query = "Berlin, DE"
        place = {"name": "Berlin", "country": "DE", "lat": 52.52, "lon": 13.405}
        self.client._places[query.casefold()] = place
        with patch.object(self.client, "_request", side_effect=AssertionError("no extra API request")) as request:
            self.assertEqual(self.client.load_resolved_place(query), place)
            self.client._save(query, "place", {"query": query.casefold(), "place": place})
            self.client._places.clear()
            self.assertEqual(self.client.load_resolved_place(query), place)
            self.assertIsNone(self.client.load_resolved_place("unresolved dummy place"))
            request.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix="weatherstation-recovery-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.client = OpenWeatherClient(self.root / "cache")
        self.client.budget = OpenWeatherBudget(project_private=self.root / "private",
                                               local_root=self.root / "local", device_id="a" * 32)
        self.query = "Potsdam, 14467, Deutschland"
        self.place = {"name": "Potsdam", "country": "DE", "lat": 52.4, "lon": 13.1}
        self.client._save(self.query, "place", {"query": self.query.casefold(), "place": self.place})
        now = datetime.now(timezone.utc)
        state = {"schema": 1, "device_id": "a" * 32, "revision": 1,
                 "day": now.date().isoformat(), "count": 0, "recent_attempts": [],
                 "blocked_until": None, "updated_at": now.isoformat()}
        for path in self.client.budget._paths()[:2]:
            _atomic_json(path, state)
        self.current_url = "https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy-key"

    def error(self, status, headers=None):
        return HTTPError(self.current_url, status, "dummy-key must never be shown", headers or {}, None)

    def fetch_current(self):
        return self.client.fetch(self.query, "dummy-key", force=True)

    def fetch_forecast(self):
        return self.client.fetch_forecast(self.query, "dummy-key", force=True)

    def test_auth_failure_stops_remaining_endpoints_without_spending_slots(self):
        for code in (401, 403):
            with self.subTest(code=code):
                self.client.reset_request_pause()
                before = self.client.budget.status()["count"]
                with patch.object(self.client._opener, "open", side_effect=self.error(code)) as transport:
                    with self.assertRaises(WeatherServiceError):
                        self.fetch_current()
                    with self.assertRaises(WeatherServiceError) as failure:
                        self.fetch_forecast()
                self.assertEqual(transport.call_count, 1)
                self.assertEqual(self.client.budget.status()["count"], before + 1)
                self.assertNotIn("dummy-key", str(failure.exception))

    def test_explicit_credential_save_or_changed_key_allows_another_check(self):
        with patch.object(self.client._opener, "open", side_effect=self.error(401)):
            with self.assertRaises(WeatherServiceError):
                self.fetch_current()
        self.client.reset_request_pause()
        with patch.object(self.client._opener, "open", return_value=FakeResponse({})) as transport:
            self.client._request(self.current_url)
            self.client._request(self.current_url.replace("dummy-key", "other-dummy"))
        self.assertEqual(transport.call_count, 2)

    def test_429_retry_after_blocks_every_endpoint_even_manual_refresh(self):
        with patch("wetterstation.weather.weather_service.time", SimpleNamespace(monotonic=lambda: 1000)):
            with patch.object(self.client._opener, "open", side_effect=self.error(429, {"Retry-After": "120"})) as transport:
                with self.assertRaises(WeatherServiceError):
                    self.fetch_current()
                with self.assertRaises(WeatherServiceError):
                    self.fetch_forecast()
                self.assertEqual(transport.call_count, 1)
        with patch("wetterstation.weather.weather_service.time", SimpleNamespace(monotonic=lambda: 1121)):
            with patch.object(self.client._opener, "open", return_value=FakeResponse({})) as transport:
                self.client._request(self.current_url)
                transport.assert_called_once()
        self.assertEqual(self.client.budget.status()["count"], 2)

    def test_retry_after_accepts_http_date_and_defaults_on_invalid_headers(self):
        self.assertGreater(self.client._retry_seconds("Sun, 18 Oct 2037 12:00:00 GMT"), 60)
        for invalid in (None, "garbage", "nan", "inf"):
            self.assertEqual(self.client._retry_seconds(invalid), 900)

    def test_timeout_and_server_failure_pause_only_the_failed_endpoint(self):
        for error in (TimeoutError("dummy-key"), self.error(503)):
            with self.subTest(error=type(error).__name__):
                self.client.reset_request_pause()
                with patch.object(self.client._opener, "open", side_effect=error) as transport:
                    for _ in range(2):
                        with self.assertRaises(WeatherServiceError):
                            self.fetch_current()
                    self.assertEqual(transport.call_count, 1)
                with patch.object(self.client._opener, "open", side_effect=[
                    FakeResponse(contracts.OneCallV4Tests.hourly_payload()), FakeResponse(contracts.OneCallV4Tests.daily_payload()),
                ]):
                    self.assertEqual(len(self.fetch_forecast().daily), 5)

    def test_oversized_or_unexpected_transport_response_is_safe(self):
        oversized = Mock()
        oversized.__enter__ = Mock(return_value=oversized)
        oversized.__exit__ = Mock(return_value=False)
        oversized.read.return_value = b" " * (MAX_RESPONSE_BYTES + 1)
        for response in (oversized, FakeResponse("invalid root")):
            with patch.object(self.client._opener, "open", return_value=response):
                with self.assertRaises(WeatherServiceError):
                    self.fetch_current()
        with patch.object(self.client._opener, "open", side_effect=RuntimeError("dummy-key")):
            with self.assertRaises(WeatherServiceError) as caught:
                self.fetch_current()
        self.assertNotIn("dummy-key", str(caught.exception))

    def test_invalid_numbers_do_not_replace_good_current_cache(self):
        with patch.object(self.client._opener, "open", return_value=FakeResponse(contracts.OneCallV4Tests.current_payload())):
            original = self.fetch_current()
        for value in (float("nan"), float("inf"), True, {}, None):
            payload = contracts.OneCallV4Tests.current_payload()
            payload["data"][0]["temp"] = value
            with patch.object(self.client._opener, "open", return_value=FakeResponse(payload)):
                with self.assertRaises(WeatherServiceError):
                    self.fetch_current()
            self.assertEqual(self.client.load_cached(self.query), original)

    def test_empty_forecast_preserves_good_cache_and_reports_error(self):
        with patch.object(self.client._opener, "open", side_effect=[
            FakeResponse(contracts.OneCallV4Tests.hourly_payload()), FakeResponse(contracts.OneCallV4Tests.daily_payload()),
        ]):
            original = self.fetch_forecast()
        with patch.object(self.client._opener, "open", return_value=FakeResponse({"data": []})):
            recovered = self.fetch_forecast()
        self.assertEqual(recovered.hourly, original.hourly)
        self.assertEqual(recovered.daily, original.daily)
        self.assertEqual(len(recovered.errors), 2)
        self.assertEqual(self.client.load_cached_forecast(self.query), original)

    def test_broken_hourly_cache_does_not_hide_good_daily_cache(self):
        with patch.object(self.client._opener, "open", side_effect=[
            FakeResponse(contracts.OneCallV4Tests.hourly_payload()), FakeResponse(contracts.OneCallV4Tests.daily_payload()),
        ]):
            self.fetch_forecast()
        self.client._cache_path(self.query, "forecast-hourly").write_text('[]', encoding="utf-8")
        cached = self.client.load_cached_forecast(self.query)
        self.assertEqual(cached.hourly, ())
        self.assertEqual(len(cached.daily), 5)

    def test_daily_cache_missing_temperature_range_cannot_break_the_overview(self):
        with patch.object(self.client._opener, "open", side_effect=[
            FakeResponse(contracts.OneCallV4Tests.hourly_payload()), FakeResponse(contracts.OneCallV4Tests.daily_payload()),
        ]):
            self.fetch_forecast()
        path = self.client._cache_path(self.query, "forecast-daily")
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            entry.pop("temp_min")
        path.write_text(json.dumps(data), encoding="utf-8")
        cached = self.client.load_cached_forecast(self.query)
        self.assertEqual(len(cached.hourly), 8)
        self.assertEqual(cached.daily, ())

    def test_old_future_and_corrupt_current_cache_are_rejected(self):
        with patch.object(self.client._opener, "open", return_value=FakeResponse(contracts.OneCallV4Tests.current_payload())):
            self.fetch_current()
        path = self.client._cache_path(self.query, "current")
        original = path.read_bytes()
        for hours in (-7, 2):
            data = json.loads(original)
            data["retrieved_at"] = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
            path.write_text(json.dumps(data), encoding="utf-8")
            self.assertIsNone(self.client.load_cached(self.query))
        for body in (b'[]', b'\xff', b'{"query":'):
            path.write_bytes(body)
            self.assertIsNone(self.client.load_cached(self.query))

    def test_disk_failure_keeps_new_weather_and_forecast_with_warning(self):
        with patch.object(self.client, "_save", side_effect=PermissionError("dummy-key")):
            with patch.object(self.client._opener, "open", side_effect=[
                FakeResponse(contracts.OneCallV4Tests.current_payload()),
                FakeResponse(contracts.OneCallV4Tests.hourly_payload()), FakeResponse(contracts.OneCallV4Tests.daily_payload()),
            ]):
                current = self.fetch_current()
                forecast = self.fetch_forecast()
        self.assertTrue(current.warnings)
        self.assertEqual(len(forecast.hourly), 8)
        self.assertEqual(len(forecast.daily), 5)
        self.assertTrue(forecast.errors)
        self.assertIsNotNone(forecast.hourly_retrieved_at)
        self.assertNotIn("dummy-key", " ".join(forecast.errors))
        self.assertEqual(self.client.load_cached(self.query), current)
        self.assertEqual(self.client.load_cached_forecast(self.query), forecast)

    def test_malformed_budget_is_fail_closed_without_http(self):
        primary, mirror, _ = self.client.budget._paths()
        original = json.loads(primary.read_text(encoding="utf-8"))
        for changes in ({"day": "garbage"}, {"count": True}, {"schema": True},
                        {"recent_attempts": ["2026-10-18T12:00:00"]}, {"updated_at": 12}):
            for path in (primary, mirror):
                _atomic_json(path, {**original, **changes})
            with patch.object(self.client._opener, "open") as transport:
                with self.assertRaises(WeatherServiceError):
                    self.fetch_current()
                transport.assert_not_called()


class RadarRecoveryTests(unittest.TestCase):
    def test_map_does_not_request_or_store_legend(self):
        with patch.object(self.client, "_request", return_value=self.png()) as requests:
            self.fetch()
        self.assertEqual(len(requests.call_args_list), 2)
        self.assertTrue(all(parse_qs(urlsplit(call.args[0]).query)["REQUEST"] == ["GetMap"]
                            for call in requests.call_args_list))
        manifest = next(Path(self.temp.name).glob("*.json"))
        self.assertEqual(set(json.loads(manifest.read_text())["files"]), {"base", "radar"})

    def test_old_cache_manifest_with_missing_legend_remains_usable(self):
        original = self.seed()
        key = self.client._cache_key(self.width, self.height)
        manifest = Path(self.temp.name) / f"{key}.json"
        meta = json.loads(manifest.read_text())
        meta["files"]["legend"] = f"{key}.legend.missing.png"
        manifest.write_text(json.dumps(meta), encoding="utf-8")
        recovered = self.client._read_cache(key, self.width, self.height)
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered.basemap, original.basemap)

    def test_other_german_cities_share_weather_position_and_separate_caches(self):
        berlin = MapPosition("Berlin, DE", "Berlin", 52.52, 13.405)
        hamburg = MapPosition("Hamburg, DE", "Hamburg", 53.55, 9.99)
        with patch.object(self.client, "_request", return_value=self.png()) as requests:
            first = self.client.fetch(self.width, self.height, berlin)
            second = self.client.fetch(self.width, self.height, hamburg)
        self.assertEqual(first.position, berlin)
        self.assertEqual(second.position, hamburg)
        boxes = []
        for offset, position in ((0, berlin), (2, hamburg)):
            base, radar = [parse_qs(urlsplit(call.args[0]).query) for call in requests.call_args_list[offset:offset+2]]
            self.assertEqual(base["BBOX"], radar["BBOX"])
            west, south, east, north = map(float, base["BBOX"][0].split(","))
            self.assertAlmostEqual((west + east) / 2, position.lon)
            self.assertAlmostEqual((south + north) / 2, position.lat)
            boxes.append(base["BBOX"])
        self.assertNotEqual(*boxes)
        self.assertNotEqual(self.client._cache_key(320, 240, berlin), self.client._cache_key(320, 240, hamburg))
        self.client._memory.clear()
        with patch.object(self.client, "_request", side_effect=TimeoutError("offline")):
            recovered = self.client.fetch(320, 240, berlin)
        self.assertTrue(recovered.stale)
        self.assertEqual(recovered.position, berlin)
        key = self.client._cache_key(320, 240, berlin)
        self.assertIsNone(self.client._read_cache(key, 320, 240, hamburg))

    def test_other_city_never_falls_back_to_potsdam_cache(self):
        self.seed()
        with patch.object(self.client, "_request", side_effect=TimeoutError("offline")):
            with self.assertRaises(RadarMapError):
                self.client.fetch(320, 240, MapPosition("Berlin", "Berlin", 52.52, 13.405))

    def test_invalid_positions_and_country_codes_are_rejected(self):
        for lat, lon, country in ((48.2, 16.37, "XX"), (90, 11, "DE"),
                                  (float("nan"), 11, "DE"), (True, 11, "DE")):
            with self.assertRaises(ValueError):
                MapPosition("Dummy", "Dummy", lat, lon, country)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix="weatherstation-recovery-")
        self.addCleanup(self.temp.cleanup)
        self.client = RadarMapClient(self.temp.name)
        self.width, self.height = 320, 240
        self.now = datetime.now(timezone.utc) - timedelta(minutes=5)
        self.timestamp = patch.object(self.client, "_radar_timestamp", return_value=self.now)
        self.timestamp.start()
        self.addCleanup(self.timestamp.stop)

    @staticmethod
    def png(width=320, height=240, color=(220, 220, 220, 255)):
        output = BytesIO()
        Image.new("RGBA", (width, height), color).save(output, format="PNG")
        return output.getvalue()

    def fetch(self):
        return self.client.fetch(self.width, self.height)

    def seed(self):
        with patch.object(self.client, "_request", return_value=self.png()):
            return self.fetch()

    def test_color_basemap_and_radar_use_same_geometry_and_new_cache_identity(self):
        with patch.object(self.client, "_request", return_value=self.png()) as requests:
            result = self.fetch()
        urls = [urlsplit(c.args[0]) for c in requests.call_args_list]
        self.assertEqual(urls[0].netloc, urlsplit(BASEMAP_URL).netloc)
        self.assertEqual(parse_qs(urls[0].query)["LAYERS"], ["de_basemapde_web_raster_farbe"])
        base, radar = [parse_qs(url.query) for url in urls[:2]]
        for field in ("BBOX", "WIDTH", "HEIGHT", "SRS", "VERSION"):
            self.assertEqual(base[field], radar[field])
        self.assertEqual(base["SRS"], ["EPSG:4326"])
        self.assertFalse(any("dop20" in url.geturl() for url in urls))
        key = self.client._cache_key(self.width, self.height)
        self.assertEqual(self.client._read_cache(key, self.width, self.height).basemap, result.basemap)
        self.assertFalse(list(Path(self.temp.name).glob("*.ortho.png")))

    def test_network_failure_uses_only_valid_matching_cache(self):
        original = self.seed()
        with patch.object(self.client, "_request", side_effect=TimeoutError("private details")):
            recovered = self.fetch()
        self.assertTrue(recovered.stale)
        self.assertEqual(recovered.basemap, original.basemap)
        self.assertNotIn("private details", recovered.warning)

    def test_old_corrupt_or_wrong_geometry_cache_is_not_displayed(self):
        self.seed()
        key = self.client._cache_key(self.width, self.height)
        manifest = Path(self.temp.name) / f"{key}.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for changes in ({"observed_at": (self.now - timedelta(hours=2)).isoformat()},
                        {"width": 321}, {"crs": "EPSG:3857"}, {"basemap_layer": "old-ortho"},
                        {"basemap_layer": "de_basemapde_web_raster_grau"},
                        {"files": {"base": "../outside.png"}}):
            manifest.write_text(json.dumps({**data, **changes}), encoding="utf-8")
            self.assertIsNone(self.client._read_cache(key, self.width, self.height))
        manifest.write_text('[]', encoding="utf-8")
        self.client._memory.clear()  # Simulate a restart with only damaged disk data.
        with patch.object(self.client, "_request", side_effect=TimeoutError("private")):
            with self.assertRaises(RadarMapError) as caught:
                self.fetch()
        self.assertNotIn("private", str(caught.exception))

    def test_broken_image_and_wrong_dimensions_are_rejected(self):
        for image in (b"\x89PNG\r\n\x1a\n", self.png(20, 20)):
            with patch.object(self.client, "_request", return_value=image):
                with self.assertRaises(RadarMapError):
                    self.fetch()

    def test_cache_write_failure_keeps_new_map_and_warns(self):
        with patch.object(self.client, "_request", return_value=self.png()):
            with patch.object(self.client, "_write_cache", side_effect=OSError("disk full")):
                result = self.fetch()
        self.assertFalse(result.stale)
        self.assertTrue(result.warning)
        with patch.object(self.client, "_request", side_effect=TimeoutError("offline")):
            recovered = self.fetch()
        self.assertTrue(recovered.stale)
        self.assertEqual(recovered.basemap, result.basemap)

    def test_interrupted_image_writes_preserve_previous_manifest(self):
        self.seed()
        key = self.client._cache_key(self.width, self.height)
        manifest = Path(self.temp.name) / f"{key}.json"
        old_manifest = manifest.read_bytes()
        real_write = self.client._atomic_write
        def fail_manifest(target, body):
            if target.suffix == ".json":
                raise OSError("interrupted")
            real_write(target, body)
        with patch.object(self.client, "_request", return_value=self.png(color=(180, 180, 180, 255))):
            with patch.object(self.client, "_atomic_write", side_effect=fail_manifest):
                self.assertTrue(self.fetch().warning)
        self.assertEqual(manifest.read_bytes(), old_manifest)
        self.assertIsNotNone(self.client._read_cache(key, self.width, self.height))


class UiRecoveryTests(unittest.TestCase):
    def preview(self):
        preview = object.__new__(WeatherPreview)
        preview.root = Mock()
        preview._results = queue.SimpleQueue()
        preview._workers = set()
        preview.mock_preview = False
        preview._closed = False
        from wetterstation.storage.settings import DisplaySettings
        preview.settings = DisplaySettings()
        preview.weather_client = Mock()
        preview.weather_client.load_cached.return_value = None
        preview.weather_client.load_cached_forecast.return_value = None
        preview.weather_client.has_resolved_place.return_value = True
        preview.weather_refresh_job = None
        preview.weather_generation = 0
        preview.weather_download_running = False
        preview.weather_refresh_pending = False
        preview.refresh_button = Mock()
        preview.draw = Mock()
        return preview

    def test_thread_start_failure_clears_busy_state_and_schedules_next_refresh(self):
        preview = self.preview()
        with patch("wetterstation.ui.app.threading.Thread.start", side_effect=RuntimeError("private details")):
            preview.refresh_weather(force=True)
        self.assertFalse(preview.weather_download_running)
        self.assertNotIn("private details", preview.weather_status)
        delay, callback = preview.root.after.call_args.args
        self.assertGreater(delay, 0)
        self.assertLessEqual(delay, 300000)
        self.assertEqual(callback, preview._scheduled_weather_refresh)

    def test_unexpected_worker_failure_is_delivered_without_tk_calls_on_worker(self):
        preview = self.preview()
        failure = Mock()
        reached = threading.Event()
        def task():
            reached.set()
            raise RuntimeError("private details")
        preview._start_worker(task, failure, "test-worker")
        self.assertTrue(reached.wait(2))
        callback = preview._results.get(timeout=2)
        failure.assert_not_called()
        preview.root.after.assert_not_called()
        callback()
        failure.assert_called_once()

    def test_unexpected_weather_worker_error_restores_refresh_state(self):
        preview = self.preview()
        preview.api_key_store = SimpleNamespace(load_api_key=lambda: "dummy-key", load_dashboard=lambda: {'version':2,'pages':[]})
        preview.weather_client.fetch.side_effect = RuntimeError("dummy-key")
        preview.refresh_weather(force=True)
        preview._results.get(timeout=2)()
        self.assertFalse(preview.weather_download_running)
        self.assertNotIn("dummy-key", preview.weather_status)

    def test_failed_refresh_retains_successful_data_timestamp_and_fixed_schedule(self):
        preview = self.preview()
        preview._load_mock_preview_data()
        preview.mock_preview = False
        previous = preview.weather_record
        preview.weather_client.load_cached.return_value = previous
        preview.weather_client.load_cached_forecast.return_value = preview.forecast_record
        preview.weather_client.fetch.side_effect = WeatherServiceError("OpenWeather nicht erreichbar")
        preview.weather_client.fetch_forecast.side_effect = WeatherServiceError("OpenWeather nicht erreichbar")
        preview.api_key_store = SimpleNamespace(load_api_key=lambda: "dummy-key", load_dashboard=lambda: {'version':2,'pages':[]})
        preview._map_position = Mock(return_value=None)
        preview.radar_result = None
        with patch.object(preview, "_start_worker", side_effect=lambda task, *_: task()):
            preview.refresh_weather(force=True)
        # A simultaneous request for this place must not enqueue another fetch.
        preview.refresh_weather(force=True)
        self.assertFalse(preview.weather_refresh_pending)
        preview._results.get(timeout=2)()
        self.assertEqual(preview.weather_record.retrieved_at, previous.retrieved_at)
        self.assertFalse(preview.weather_download_running)
        preview.weather_client.fetch.assert_called_once_with(preview.settings.query, "dummy-key", force=True)
        preview.weather_client.fetch_forecast.assert_called_once_with(preview.settings.query, "dummy-key", force=True)

    def radar_preview(self, page=0):
        preview = self.preview()
        preview.page = page
        preview._map_position = Mock(return_value=object())
        preview.radar_refresh_job = None
        preview.radar_refresh_due = None
        preview.radar_download_running = False
        preview.refresh_radar = Mock()
        preview.root.after.return_value = "radar-timer"
        return preview

    def test_radar_schedule_uses_next_fixed_five_minute_boundary_on_every_page(self):
        for page in range(4):
            preview = self.radar_preview(page=page)
            with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
                clock.now.return_value = datetime(2026, 10, 23, 10, 2, 10, tzinfo=timezone.utc)
                preview.schedule_radar_refresh()
            preview.root.after.assert_called_once_with(170000, preview._scheduled_radar_refresh)
            self.assertEqual(preview.radar_refresh_due.minute, 5)

    def test_opening_map_keeps_existing_timer_and_sends_no_extra_request(self):
        preview = self.radar_preview()
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 10, 2, tzinfo=timezone.utc)
            preview.schedule_radar_refresh()
            preview.page = 2
            preview.schedule_radar_refresh()
        preview.root.after.assert_called_once_with(180000, preview._scheduled_radar_refresh)
        preview.root.after_cancel.assert_not_called()
        preview.refresh_radar.assert_not_called()

    def test_leaving_map_keeps_same_deadline(self):
        preview = self.radar_preview(page=2)
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 10, 3, tzinfo=timezone.utc)
            preview.schedule_radar_refresh()
            preview.page = 1
            preview.schedule_radar_refresh()
        preview.root.after.assert_called_once_with(120000, preview._scheduled_radar_refresh)
        preview.root.after_cancel.assert_not_called()

    def test_background_slot_refreshes_and_rearms_from_current_clock(self):
        preview = self.radar_preview()
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 10, 4, tzinfo=timezone.utc)
            preview.schedule_radar_refresh()
            clock.now.return_value = datetime(2026, 10, 23, 10, 5, 18, tzinfo=timezone.utc)
            preview._scheduled_radar_refresh()
            preview.schedule_radar_refresh()
            preview.schedule_radar_refresh()
        preview.refresh_radar.assert_called_once()
        self.assertEqual(preview.root.after.call_count, 2)
        self.assertEqual(preview.root.after.call_args.args[0], 282000)

    def test_standby_does_not_replay_missed_slots(self):
        preview = self.radar_preview()
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 10, 3, tzinfo=timezone.utc)
            preview.schedule_radar_refresh()
            clock.now.return_value = datetime(2026, 10, 23, 14, 43, tzinfo=timezone.utc)
            preview._scheduled_radar_refresh()
            preview.schedule_radar_refresh()
        preview.refresh_radar.assert_called_once()
        self.assertEqual(preview.root.after.call_args.args[0], 120000)

    def test_early_callback_waits_until_its_fixed_due_time(self):
        preview = self.radar_preview()
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 10, 4, tzinfo=timezone.utc)
            preview.schedule_radar_refresh()
            clock.now.return_value = datetime(2026, 10, 23, 10, 4, 59, 500000, tzinfo=timezone.utc)
            preview._scheduled_radar_refresh()
        preview.refresh_radar.assert_not_called()
        self.assertEqual(preview.root.after.call_args.args[0], 500)

    def test_no_timer_without_position_or_during_download_or_after_close(self):
        preview = self.radar_preview()
        preview._map_position.return_value = None
        preview.schedule_radar_refresh()
        preview._map_position.return_value = object()
        preview.radar_download_running = True
        preview.schedule_radar_refresh()
        preview.radar_download_running = False
        preview._closed = True
        preview.schedule_radar_refresh()
        preview.root.after.assert_not_called()

    def test_closed_window_ignores_pending_results(self):
        preview = self.preview()
        preview._closed = True
        callback = Mock()
        preview._results.put(callback)
        preview._drain_results()
        callback.assert_not_called()
        preview.root.after.assert_not_called()


class LocalFileRecoveryTests(unittest.TestCase):
    def test_transient_windows_sharing_error_is_retried_without_rewriting_counter(self):
        from wetterstation.storage.file_io import replace_file
        busy = PermissionError("sharing")
        busy.winerror = 32
        with patch("wetterstation.storage.file_io.os.replace", side_effect=[busy, None]) as replace:
            with patch("wetterstation.storage.file_io.time.sleep") as wait:
                replace_file("dummy-source", "dummy-target")
        self.assertEqual(replace.call_count, 2)
        wait.assert_called_once_with(0.02)

    def test_persistent_file_error_remains_an_error_after_bounded_retries(self):
        from wetterstation.storage.file_io import replace_file
        busy = PermissionError("sharing")
        busy.winerror = 32
        with patch("wetterstation.storage.file_io.os.replace", side_effect=busy) as replace:
            with patch("wetterstation.storage.file_io.time.sleep"):
                with self.assertRaises(PermissionError):
                    replace_file("dummy-source", "dummy-target")
        self.assertEqual(replace.call_count, 5)

    def test_corrupt_settings_are_never_overwritten_by_a_save_attempt(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / "settings.json"
            path.write_bytes(b'\xff')
            store = ApiKeyStore(path=path)
            with self.assertRaises(ValueError):
                store.save_api_key("dummy-key")
            self.assertEqual(path.read_bytes(), b'\xff')


if __name__ == "__main__":
    unittest.main(verbosity=2)
