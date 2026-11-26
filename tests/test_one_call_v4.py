"""Mock-only contract tests for the One Call API 4.0 client."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from wetterstation.storage.openweather_budget import OpenWeatherBudget, _atomic_json, MAX_CALLS_PER_MINUTE
from wetterstation.weather.weather_service import (
    FORECAST_DAILY_COUNT, FORECAST_HOURLY_COUNT, OpenWeatherClient,
    WeatherServiceError,
)


class FakeResponse:
    def __init__(self, value):
        self.body = json.dumps(value).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]


class OneCallV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix="weatherstation-v4-tests-")
        cls.temp_parent = Path(cls.workspace.name)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.temp_parent)
        self.root = Path(self.temp.name)
        self.cache = self.root / "cache"
        self.private = self.root / "private"
        self.local = self.root / "local"
        self.client = OpenWeatherClient(cache_dir=self.cache)
        self.client.budget = OpenWeatherBudget(project_private=self.private,
                                               device_id="a" * 32,
                                               local_root=self.local)
        self.seed_budget()
        self.query = "Potsdam, 14467, Deutschland"
        self.place = {"name": "Potsdam", "country": "DE", "lat": 52.4, "lon": 13.1}
        self.client._save(self.query.casefold(), "place", {
            "query": self.query.casefold(), "place": self.place,
        })
        self.calls = []

    def tearDown(self):
        self.temp.cleanup()

    def seed_budget(self, count=0, recent_attempts=None):
        moment = datetime.now(timezone.utc)
        primary, mirror, _lock = self.client.budget._paths()
        state = {
            "schema": 1, "device_id": self.client.budget._get_device_id(),
            "revision": 1, "day": moment.date().isoformat(), "count": count,
            "recent_attempts": list(recent_attempts or []), "blocked_until": None,
            "updated_at": moment.isoformat(timespec="seconds"),
        }
        _atomic_json(primary, state)
        _atomic_json(mirror, state)

    @staticmethod
    def current_payload():
        stamp = int(datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc).timestamp())
        return {"lat": 52.4, "lon": 13.1, "timezone": "Europe/Berlin",
                "timezone_offset": 7200, "data": [{
                    "dt": stamp, "temp": 12.5, "feels_like": 11.0,
                    "humidity": 68, "pressure": 1014, "wind_speed": 2.4,
                    "weather": [{"description": "leichter Regen"}],
                }]}

    @staticmethod
    def hourly_payload(count=12):
        start = int(datetime(2026, 10, 17, 13, 0, tzinfo=timezone.utc).timestamp())
        data = [{"dt": start + i * 3600, "temp": 10 + i / 2, "pop": i / 20,
                 "wind_speed": 2.5, "weather": [{"description": "leicht bewölkt"}]}
                for i in range(count)]
        return {"timezone": "Europe/Berlin", "timezone_offset": 7200,
                "data": data, "next": "https://example.invalid/steal-key"}

    @staticmethod
    def daily_payload(count=7):
        start = int(datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc).timestamp())
        data = [{"dt": start + i * 86400, "temp": {"min": 5 + i, "max": 15 + i, "day": 12 + i},
                 "pop": 0.2, "wind_speed": 3.0,
                 "weather": [{"description": "sonnig"}]}
                for i in range(count)]
        return {"timezone": "Europe/Berlin", "timezone_offset": 7200,
                "data": data, "next": "https://example.invalid/steal-key"}

    def respond(self, request, timeout):
        self.calls.append(request.full_url)
        if request.full_url.startswith("https://api.openweathermap.org/data/4.0/onecall/current?"):
            return FakeResponse(self.current_payload())
        if "/timeline/1h?" in request.full_url:
            return FakeResponse(self.hourly_payload())
        if "/timeline/1day?" in request.full_url:
            return FakeResponse(self.daily_payload())
        if "/geo/1.0/zip?" in request.full_url:
            return FakeResponse(self.place)
        raise AssertionError("unexpected endpoint")

    def test_complete_refresh_uses_three_calls_and_five_minute_cache(self):
        from datetime import timedelta
        moment = datetime.now(timezone.utc).replace(microsecond=0)
        with patch("wetterstation.weather.weather_service.datetime", wraps=datetime) as clock, patch.object(
                self.client._opener, "open", side_effect=self.respond):
            clock.now.return_value = moment
            self.client.fetch(self.query, "dummy-key")
            self.client.fetch_forecast(self.query, "dummy-key")
            self.assertEqual(len(self.calls), 3)
            clock.now.return_value = moment + timedelta(minutes=4, seconds=59)
            self.client.fetch(self.query, "dummy-key")
            self.client.fetch_forecast(self.query, "dummy-key")
            self.assertEqual(len(self.calls), 3)
            clock.now.return_value = moment + timedelta(minutes=5)
            self.client.fetch(self.query, "dummy-key")
            self.client.fetch_forecast(self.query, "dummy-key")
            self.assertEqual(len(self.calls), 6)
            # A scheduled/manual refresh bypasses a fresh cache for all sections.
            self.client.fetch(self.query, "dummy-key", force=True)
            self.client.fetch_forecast(self.query, "dummy-key", force=True)
            self.assertEqual(len(self.calls), 9)
        self.assertEqual(self.client.budget.status()["count"], 9)

    def test_current_endpoint_uses_v4_schema_metric_units_and_local_time(self):
        with patch.object(self.client._opener, "open", side_effect=self.respond):
            record = self.client.fetch(self.query, "dummy-key", force=True)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("/data/4.0/onecall/current?", self.calls[0])
        self.assertIn("units=metric", self.calls[0])
        self.assertEqual(record.source, "OpenWeather One Call 4.0")
        self.assertEqual(record.temp, 12.5)
        self.assertTrue(record.observed_at.endswith("+02:00"))
        self.assertEqual(self.client.load_cached(self.query), record)

    def test_resolved_place_from_disk_is_reused_without_more_file_reads(self):
        place = self.client.load_resolved_place(self.query)
        self.assertEqual(place, self.place)
        place["name"] = "Changed copy"
        with patch.object(self.client, "_load_json", side_effect=AssertionError("no repeated disk reads")):
            self.assertEqual(self.client.load_resolved_place(self.query), self.place)
        with patch.object(self.client, "_load_json", return_value=None):
            self.assertIsNone(self.client.load_resolved_place("Berlin"))

    def test_forecast_is_bounded_to_eight_hours_and_five_days_and_ignores_pagination(self):
        with patch.object(self.client._opener, "open", side_effect=self.respond) as outbound:
            forecast = self.client.fetch_forecast(self.query, "dummy-key", force=True)
        self.assertEqual(outbound.call_count, 2)
        self.assertIn("/timeline/1h?", self.calls[0])
        self.assertIn("/timeline/1day?", self.calls[1])
        self.assertEqual(len(forecast.hourly), FORECAST_HOURLY_COUNT)
        self.assertEqual(len(forecast.daily), FORECAST_DAILY_COUNT)
        self.assertAlmostEqual(forecast.hourly[2].precipitation_probability, 0.1)
        self.assertEqual(forecast.daily[0].temp_min, 5)
        self.assertEqual(forecast.daily[0].temp_max, 15)
        self.assertIsNotNone(forecast.hourly_retrieved_at)
        self.assertIsNotNone(forecast.daily_retrieved_at)
        self.assertEqual(self.client.load_cached_forecast(self.query), forecast)
        self.assertFalse(any("example.invalid" in url for url in self.calls))

    def test_one_complete_refresh_costs_four_calls_only_when_geocoding_is_needed(self):
        self.client._cache_path(self.query, "place").unlink(missing_ok=True)
        with patch.object(self.client._opener, "open", side_effect=self.respond):
            self.client.fetch(self.query, "dummy-key", force=True)
            self.client.fetch_forecast(self.query, "dummy-key", force=True)
        self.assertEqual(len(self.calls), 4)
        self.assertIn("/geo/1.0/zip?", self.calls[0])
        self.assertIn("/data/4.0/onecall/current?", self.calls[1])
        self.assertIn("/timeline/1h?", self.calls[2])
        self.assertIn("/timeline/1day?", self.calls[3])
        self.assertEqual(self.client.budget.status()["count"], 4)

    def test_current_and_forecast_have_separate_reusable_cache_files(self):
        with patch.object(self.client._opener, "open", side_effect=self.respond):
            current = self.client.fetch(self.query, "dummy-key", force=True)
            forecast = self.client.fetch_forecast(self.query, "dummy-key", force=True)
        restarted = OpenWeatherClient(cache_dir=self.cache)
        self.assertEqual(restarted.load_cached(self.query), current)
        self.assertEqual(restarted.load_cached_forecast(self.query), forecast)
        files = {path.name.rsplit("-", 1)[0] for path in self.cache.glob("*.json")}
        self.assertTrue({"current", "forecast-hourly", "forecast-daily", "place"}.issubset(files))

    def test_partial_forecast_rows_are_kept_without_inventing_missing_values(self):
        with patch.object(self.client._opener, "open", side_effect=[
            FakeResponse({"timezone": "Europe/Berlin", "data": [
                {"dt": 1792243200, "temp": 8, "weather": [{"description": "klar"}]},
                {"dt": 1792246800, "weather": [{"description": "fehlt Temperatur"}]},
            ]}),
            FakeResponse({"timezone": "Europe/Berlin", "data": [
                {"dt": 1792195200, "temp": {"min": 4, "max": 12},
                 "weather": [{"description": "wolkenlos"}]},
            ]}),
        ]):
            forecast = self.client.fetch_forecast(self.query, "dummy-key", force=True)
        self.assertEqual(len(forecast.hourly), 1)
        self.assertEqual(len(forecast.daily), 1)
        self.assertEqual(forecast.hourly[0].precipitation_probability, 0)
        self.assertEqual(forecast.daily[0].temp, 12)

    def test_empty_or_malformed_forecast_reports_provider_error(self):
        with patch.object(self.client._opener, "open", side_effect=[
            FakeResponse({"timezone": "Europe/Berlin", "data": []}),
            FakeResponse({"timezone": "Europe/Berlin", "data": []}),
        ]):
            with self.assertRaisesRegex(WeatherServiceError, "keine Vorhersagezeiträume"):
                self.client.fetch_forecast(self.query, "dummy-key", force=True)

    def test_provider_timeout_counts_call_and_keeps_error_sanitized(self):
        with patch.object(self.client._opener, "open", side_effect=[
            TimeoutError("private details"), TimeoutError("private details"),
        ]):
            with self.assertRaisesRegex(WeatherServiceError, "nicht erreichbar") as caught:
                self.client.fetch_forecast(self.query, "dummy-key", force=True)
        self.assertNotIn("private details", str(caught.exception))
        self.assertEqual(self.client.budget.status()["count"], 2)

    def test_one_endpoint_error_keeps_other_endpoint_data_and_reports_partial_state(self):
        with patch.object(self.client._opener, "open", side_effect=[
            TimeoutError("hourly unavailable"), FakeResponse(self.daily_payload(2)),
        ]):
            forecast = self.client.fetch_forecast(self.query, "dummy-key", force=True)
        self.assertEqual(forecast.hourly, ())
        self.assertEqual(len(forecast.daily), 2)
        self.assertTrue(forecast.errors)
        self.assertIn("hourly", forecast.errors[0])
        cached = self.client.load_cached_forecast(self.query)
        self.assertIsNotNone(cached)
        self.assertEqual(cached.hourly, ())
        self.assertEqual(len(cached.daily), 2)

    def test_each_v4_endpoint_is_blocked_before_transport_at_daily_limit(self):
        self.seed_budget(count=1000)
        with patch.object(self.client._opener, "open") as outbound:
            for call in (
                lambda: self.client._request("https://api.openweathermap.org/geo/1.0/zip?zip=14467%2CDE&appid=dummy"),
                lambda: self.client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy"),
                lambda: self.client._request("https://api.openweathermap.org/data/4.0/onecall/timeline/1h?appid=dummy"),
                lambda: self.client._request("https://api.openweathermap.org/data/4.0/onecall/timeline/1day?appid=dummy"),
            ):
                with self.assertRaises(WeatherServiceError):
                    call()
        outbound.assert_not_called()

    def test_hourly_and_daily_calls_share_the_minute_budget(self):
        moment = datetime.now(timezone.utc)
        recent = [(moment.replace(microsecond=0)).isoformat(timespec="seconds")]
        # The first accepted request becomes the 60th attempt; the next must be blocked.
        self.seed_budget(count=59, recent_attempts=recent * (MAX_CALLS_PER_MINUTE - 1))
        with patch.object(self.client._opener, "open", side_effect=self.respond) as outbound:
            self.client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
            with self.assertRaises(WeatherServiceError):
                self.client._request("https://api.openweathermap.org/data/4.0/onecall/timeline/1h?appid=dummy")
        self.assertEqual(outbound.call_count, 1)
        self.assertEqual(self.client.budget.status()["count"], 60)

    def test_location_change_uses_only_matching_place_and_weather_cache(self):
        other = "Nürnberg, 90402, Deutschland"
        with patch.object(self.client._opener, "open", side_effect=self.respond):
            original = self.client.fetch(self.query, "dummy-key", force=True)
        calls_before = len(self.calls)
        def respond_other(request, timeout):
            self.calls.append(request.full_url)
            if "/geo/1.0/zip?" in request.full_url:
                return FakeResponse({"name": "Nürnberg", "country": "DE", "lat": 49.45, "lon": 11.08})
            data = self.current_payload()
            data["lat"], data["lon"] = 49.45, 11.08
            data["data"][0]["temp"] = 8.0
            return FakeResponse(data)
        with patch.object(self.client._opener, "open", side_effect=respond_other):
            changed = self.client.fetch(other, "dummy-key", force=True)
        self.assertEqual(len(self.calls) - calls_before, 2)
        self.assertEqual(changed.name, "Nürnberg")
        self.assertEqual(changed.temp, 8.0)
        self.assertEqual(self.client.load_cached(self.query), original)
        self.assertEqual(self.client.load_cached(other), changed)

    def test_external_redirect_is_not_followed(self):
        error = HTTPError("https://api.openweathermap.org/data/4.0/onecall/current",
                          302, "redirect", {"Location": "https://example.invalid/?appid=dummy"}, None)
        with patch.object(self.client._opener, "open", side_effect=error) as outbound:
            with self.assertRaises(WeatherServiceError):
                self.client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_called_once()
        self.assertEqual(self.client.budget.status()["count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
