"""Mock-only tests for the durable OpenWeather request budget."""
import json
import multiprocessing
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from unittest.mock import patch
from urllib.error import HTTPError

from wetterstation.storage.openweather_budget import (
    MAX_DAILY_CALLS, MAX_CALLS_PER_MINUTE, BudgetLimitReached,
    BudgetUnavailable, OpenWeatherBudget, _atomic_json,
)
from wetterstation.weather.weather_service import OpenWeatherClient, WeatherServiceError


def _reserve_in_process(private, local, now_iso, queue):
    try:
        budget = OpenWeatherBudget(project_private=private, device_id="f" * 32,
                                   local_root=local)
        queue.put(("ok", budget.reserve_call(now=datetime.fromisoformat(now_iso))))
    except BudgetLimitReached:
        queue.put(("blocked", None))
    except Exception as exc:
        queue.put(("error", type(exc).__name__))


class OpenWeatherBudgetTests(unittest.TestCase):
    def test_authorized_newer_primary_activation_reconciles_owner_mirror_and_preserves_limits(self):
        for device, count in (("d" * 32, 19), ("e" * 32, 1000)):
            budget = OpenWeatherBudget(project_private=self.private, device_id=device, local_root=self.local)
            self.assertEqual(budget.status(now=self.now)["mode"], "initializing")
            primary, mirror, _ = budget._paths()
            waiting = json.loads(primary.read_text())
            activated = {**waiting, "day": self.now.date().isoformat(), "count": count,
                         "local_count": count, "blocked_until": None,
                         "revision": waiting["revision"] + 1}
            _atomic_json(primary, activated)
            # The owner process, rather than another execution context, updates
            # its existing mirror from the newer validated project counter.
            self.assertIsNotNone(json.loads(mirror.read_text())["blocked_until"])
            status = budget.status(now=self.now)
            self.assertEqual(status["mode"], "ready")
            self.assertEqual(status["count"], count)
            self.assertEqual(json.loads(primary.read_text()), json.loads(mirror.read_text()))
            restarted = OpenWeatherBudget(project_private=self.private, device_id=device, local_root=self.local)
            if count < 1000:
                self.assertEqual(restarted.reserve_call(now=self.now), count + 1)
            else:
                with self.assertRaises(BudgetLimitReached):
                    restarted.reserve_call(now=self.now)

    def test_german_midnight_resets_local_counter_and_keeps_provider_total(self):
        self.seed(count=9)
        self.budget.status(now=self.now)  # Migrate before midnight, retaining calls.
        self.assertEqual(self.budget.status(now=self.now)["count"], 9)
        local_midnight = self.now.replace(hour=22)
        status = self.budget.status(now=local_midnight)
        self.assertEqual(status["count"], 0)
        self.assertEqual(status["provider_count"], 9)
        self.assertEqual(status["remaining"], 991)
        self.assertEqual(self.budget.reserve_call(now=local_midnight), 10)
        restarted = OpenWeatherBudget(project_private=self.private, device_id="a" * 32, local_root=self.local)
        status = restarted.status(now=local_midnight)
        self.assertEqual(status["count"], 1)
        self.assertEqual(status["provider_count"], 10)
        primary, mirror = self.paths()
        saved = json.loads(primary.read_text())
        self.assertEqual(saved["local_day"], "2026-10-18")
        self.assertEqual(saved["local_count"], 1)
        self.assertEqual(saved, json.loads(mirror.read_text()))

    def test_local_midnight_does_not_allow_more_calls_in_same_provider_day(self):
        self.seed(count=1000)
        self.budget.status(now=self.now)
        midnight = self.now.replace(hour=22)
        self.assertEqual(self.budget.status(now=midnight)["count"], 0)
        self.assertEqual(self.budget.status(now=midnight)["remaining"], 0)
        with self.assertRaises(BudgetLimitReached):
            self.budget.reserve_call(now=midnight)

    def test_midnight_refresh_counts_three_then_six_and_keeps_existing_history(self):
        self.seed(count=9)
        self.budget.status(now=self.now)
        midnight = self.now.replace(hour=22)
        for slot, expected in ((midnight, 3), (midnight + timedelta(minutes=5), 6)):
            for _ in range(3):
                self.budget.reserve_call(now=slot)
            status = self.budget.status(now=slot)
            self.assertEqual(status["count"], expected)
            self.assertEqual(status["provider_count"], 9 + expected)

    def test_utc_reset_preserves_local_calls_since_german_midnight(self):
        self.seed(count=9)
        self.budget.status(now=self.now)
        self.budget.reserve_call(now=self.now.replace(hour=22))
        next_provider_day = datetime(2026, 10, 18, 0, 5, tzinfo=timezone.utc)
        self.assertEqual(self.budget.reserve_call(now=next_provider_day), 1)
        status = self.budget.status(now=next_provider_day)
        self.assertEqual(status["count"], 2)
        self.assertEqual(status["provider_count"], 1)

    def test_local_daily_limit_also_applies_after_provider_reset(self):
        primary, mirror, state = self.seed(count=1)
        state.update({"schema": 2, "local_zone": "Europe/Berlin", "local_day": "2026-10-17", "local_count": 1000})
        for path in (primary, mirror):
            _atomic_json(path, state)
        self.assertEqual(self.budget.status(now=self.now)["remaining"], 0)
        with self.assertRaisesRegex(BudgetLimitReached, "00:00"):
            self.budget.reserve_call(now=self.now)
        # German midnight starts the next local day, but retains the UTC total.
        self.assertEqual(self.budget.reserve_call(now=self.now.replace(hour=22)), 2)

    def test_midnight_uses_german_summer_and_winter_time(self):
        for month, utc_hour in ((7, 22), (12, 23)):
            before = datetime(2026, month, 5, utc_hour - 1, 59, 59, tzinfo=timezone.utc)
            midnight = before + timedelta(seconds=1)
            # Use a distinct, isolated budget for each season.
            budget = OpenWeatherBudget(project_private=self.private / str(month),
                                       device_id="e" * 32, local_root=self.local)
            primary, mirror, _ = budget._paths()
            state = {"schema": 1, "device_id": "e" * 32, "revision": 1,
                     "day": before.date().isoformat(), "count": 12, "recent_attempts": [],
                     "blocked_until": None, "updated_at": before.isoformat()}
            _atomic_json(primary, state)
            _atomic_json(mirror, state)
            self.assertEqual(budget.status(now=before)["count"], 12)
            self.assertEqual(budget.status(now=midnight)["count"], 0)
            self.assertEqual(midnight.astimezone(ZoneInfo("Europe/Berlin")).hour, 0)

    def test_malformed_local_count_and_local_clock_rollback_are_blocked(self):
        primary, mirror, _ = self.seed(count=9)
        self.budget.status(now=self.now)
        state = json.loads(primary.read_text())
        for changes in ({"local_count": True}, {"local_count": -1}, {"local_day": "invalid"},
                        {"local_zone": "UTC"}, {"local_day": "2026-10-19"}):
            for path in (primary, mirror):
                _atomic_json(path, {**state, **changes})
            with self.assertRaises(BudgetUnavailable):
                self.budget.reserve_call(now=self.now)

    def test_windows_budget_identity_ignores_launcher_localappdata_redirect(self):
        from wetterstation.storage.openweather_budget import _local_data_root
        with patch("wetterstation.storage.openweather_budget.sys.platform", "win32"), patch("wetterstation.storage.openweather_budget.legacy_settings_path", return_value=self.root / "real-user" / "Wetterstation" / "settings.json"), patch.dict("os.environ", {"LOCALAPPDATA": str(self.root / "temporary-launcher"), "WETTERSTATION_BUDGET_ROOT": ""}):
            self.assertEqual(_local_data_root(), self.root / "real-user" / "Wetterstation" / "openweather-budget")

    def test_starter_pins_existing_device_and_counter_despite_other_profile_paths(self):
        from wetterstation.storage.openweather_budget import _local_data_root
        pinned = self.root / "normal-user" / "Wetterstation" / "openweather-budget"
        pinned.mkdir(parents=True)
        (pinned / "device-id.txt").write_text("a" * 32)
        self.budget = OpenWeatherBudget(project_private=self.private, local_root=pinned)
        self.seed(count=13)
        with patch("wetterstation.storage.openweather_budget.sys.platform", "win32"), patch.dict("os.environ", {
                "WETTERSTATION_BUDGET_ROOT": str(pinned), "USERPROFILE": str(self.root / "different-profile"),
                "LOCALAPPDATA": str(self.root / "different-appdata")}), patch("wetterstation.storage.openweather_budget.legacy_settings_path", side_effect=OSError("different launch context")):
            self.assertEqual(_local_data_root(), pinned)
            restarted = OpenWeatherBudget(project_private=self.private)
            self.assertEqual(restarted._get_device_id(), "a" * 32)
            status = restarted.status(now=self.now)
            self.assertEqual(status["mode"], "ready")
            self.assertEqual(status["count"], 13)
            self.assertEqual(restarted.reserve_call(now=self.now), 14)

    def test_relative_starter_budget_root_fails_closed(self):
        from wetterstation.storage.openweather_budget import _local_data_root
        with patch("wetterstation.storage.openweather_budget.sys.platform", "win32"), patch.dict("os.environ", {"WETTERSTATION_BUDGET_ROOT": "relative-budget"}):
            with self.assertRaises(BudgetUnavailable):
                _local_data_root()

    @classmethod
    def setUpClass(cls):
        cls.workspace = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent, prefix="weatherstation-budget-tests-")
        cls.temp_parent = Path(cls.workspace.name)

    @classmethod
    def tearDownClass(cls):
        cls.workspace.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.temp_parent)
        self.root = Path(self.temp.name)
        self.private = self.root / "project-private"
        self.local = self.root / "local-data"
        self.budget = OpenWeatherBudget(project_private=self.private,
                                        device_id="a" * 32, local_root=self.local)
        self.now = datetime(2026, 10, 17, 21, 0, tzinfo=timezone.utc)
        # Transport calls reserve without an explicit timestamp. Keep them on
        # the same test day as the seeded counter, regardless of the real date.
        clock = patch("wetterstation.storage.openweather_budget.datetime", wraps=datetime)
        self.budget_clock = clock.start()
        self.budget_clock.now.return_value = self.now
        self.addCleanup(clock.stop)

    def tearDown(self):
        self.temp.cleanup()

    def paths(self):
        return self.budget._paths()[:2]

    def seed(self, *, day=None, count=0, revision=1, recent=None):
        primary, mirror = self.paths()
        state = {
            "schema": 1, "device_id": self.budget._get_device_id(), "revision": revision,
            "day": (day or self.now.date()).isoformat(), "count": count,
            "recent_attempts": recent or [], "blocked_until": None,
            "updated_at": self.now.isoformat(),
        }
        _atomic_json(primary, state)
        _atomic_json(mirror, state)
        return primary, mirror, state

    def test_initialization_fails_closed_until_safe_provider_reset(self):
        fresh = OpenWeatherBudget(project_private=self.private, device_id="b" * 32,
                                  local_root=self.local)
        status = fresh.status(now=self.now)
        self.assertEqual(status["mode"], "initializing")
        self.assertEqual(status["remaining"], 1000)
        with self.assertRaises(BudgetLimitReached):
            fresh.reserve_call(now=self.now)
        after_reset = datetime(2026, 10, 18, 0, 5, tzinfo=timezone.utc)
        self.assertEqual(fresh.reserve_call(now=after_reset), 1)

    def test_1000th_is_allowed_and_1001st_is_blocked_and_persists(self):
        self.seed(count=999)
        self.assertEqual(self.budget.reserve_call(now=self.now), 1000)
        with self.assertRaises(BudgetLimitReached):
            self.budget.reserve_call(now=self.now + timedelta(seconds=1))
        restarted = OpenWeatherBudget(project_private=self.private,
                                      device_id="a" * 32, local_root=self.local)
        state = restarted.status(now=self.now + timedelta(seconds=2))
        self.assertEqual(state["count"], MAX_DAILY_CALLS)
        self.assertEqual(state["remaining"], 0)

    def test_daily_boundary_waits_until_0005_utc(self):
        self.seed(day=datetime(2026, 10, 17, tzinfo=timezone.utc).date(), count=12)
        before = datetime(2026, 10, 18, 0, 4, 59, tzinfo=timezone.utc)
        with self.assertRaises(BudgetLimitReached):
            self.budget.reserve_call(now=before)
        at_reset = datetime(2026, 10, 18, 0, 5, tzinfo=timezone.utc)
        self.assertEqual(self.budget.reserve_call(now=at_reset), 1)
        next_before = datetime(2026, 10, 19, 0, 4, tzinfo=timezone.utc)
        with self.assertRaises(BudgetLimitReached):
            self.budget.reserve_call(now=next_before)

    def test_rolling_minute_cap_is_shared_across_concurrent_threads(self):
        self.seed(count=0)
        allowed, blocked = [], []
        guard = threading.Lock()
        def reserve():
            try:
                result = self.budget.reserve_call(now=self.now)
                with guard: allowed.append(result)
            except BudgetLimitReached:
                with guard: blocked.append(True)
        threads = [threading.Thread(target=reserve) for _ in range(70)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(len(allowed), MAX_CALLS_PER_MINUTE)
        self.assertEqual(len(blocked), 70-MAX_CALLS_PER_MINUTE)
        self.assertEqual(self.budget.status(now=self.now)["count"], MAX_CALLS_PER_MINUTE)

    def test_rolling_minute_window_blocks_61st_until_oldest_attempt_expires_after_restart(self):
        recent = [(self.now - timedelta(seconds=59)).isoformat(timespec="seconds")
                  for _ in range(MAX_CALLS_PER_MINUTE)]
        self.seed(count=MAX_CALLS_PER_MINUTE, recent=recent)
        restarted = OpenWeatherBudget(project_private=self.private,
                                      device_id="a" * 32, local_root=self.local)
        with self.assertRaises(BudgetLimitReached):
            restarted.reserve_call(now=self.now)
        # The same recorded attempts are older than 60 seconds across the boundary.
        self.assertEqual(restarted.reserve_call(now=self.now + timedelta(seconds=2)),
                         MAX_CALLS_PER_MINUTE + 1)

    def test_network_timeout_consumes_reserved_slot(self):
        self.seed(count=0)
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        with patch.object(client._opener, "open", side_effect=TimeoutError("hidden")) as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_called_once()
        self.assertEqual(self.budget.status(now=self.now)["count"], 1)

    def test_budget_block_prevents_network_call(self):
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = OpenWeatherBudget(project_private=self.private,
                                          device_id="c" * 32, local_root=self.local)
        with patch.object(client._opener, "open", side_effect=AssertionError("network must not run")) as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_not_called()

    def test_http_error_consumes_reserved_slot(self):
        self.seed(count=0)
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        error = HTTPError("https://invalid.example/?appid=dummy", 429, "blocked", {}, None)
        with patch.object(client._opener, "open", side_effect=error):
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        self.assertEqual(self.budget.status(now=self.now)["count"], 1)

    def test_corrupt_state_fails_closed_without_network(self):
        primary, _, _ = self.seed(count=0)
        primary.write_text("not json", encoding="utf-8")
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        with patch.object(client._opener, "open") as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_not_called()

    def test_unwritable_counter_fails_closed_without_network(self):
        blocked_private = self.root / "not-a-directory"
        blocked_private.write_text("obstruction", encoding="utf-8")
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = OpenWeatherBudget(project_private=blocked_private,
                                          device_id="d" * 32, local_root=self.local)
        with patch.object(client._opener, "open") as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_not_called()

    def test_older_synced_snapshot_is_not_overwritten(self):
        primary, mirror, state = self.seed(count=8, revision=8)
        older = dict(state, count=3, revision=3)
        _atomic_json(primary, older)
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        with patch.object(client._opener, "open") as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_not_called()
        self.assertEqual(json.loads(primary.read_text(encoding="utf-8"))["revision"], 3)



    def test_separate_processes_share_the_same_file_lock_and_counter(self):
        self.budget = OpenWeatherBudget(project_private=self.private,
                                        device_id="f" * 32, local_root=self.local)
        self.seed(count=0)
        ctx = multiprocessing.get_context("spawn")
        queue = ctx.Queue()
        now_iso = self.now.isoformat()
        processes = [ctx.Process(target=_reserve_in_process,
                                 args=(str(self.private), str(self.local), now_iso, queue))
                     for _ in range(6)]
        for process in processes: process.start()
        results = [queue.get(timeout=15) for _ in processes]
        for process in processes: process.join(timeout=15)
        self.assertTrue(all(process.exitcode == 0 for process in processes))
        self.assertEqual(sum(result[0] == "ok" for result in results), 6, repr(results))
        self.assertEqual(self.budget.status(now=self.now)["count"], 6)

    def test_parallel_reservations_cannot_cross_1000(self):
        self.seed(count=999)
        allowed, blocked = [], []
        guard = threading.Lock()
        def reserve():
            try:
                value = self.budget.reserve_call(now=self.now)
                with guard: allowed.append(value)
            except BudgetLimitReached:
                with guard: blocked.append(True)
        threads = [threading.Thread(target=reserve) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(allowed, [1000])
        self.assertEqual(len(blocked), 7)
        self.assertEqual(self.budget.status(now=self.now)["count"], 1000)

    def test_limit_reached_never_calls_transport(self):
        self.seed(count=1000)
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        with patch.object(client._opener, "open") as outbound:
            with self.assertRaises(WeatherServiceError):
                client._request("https://api.openweathermap.org/data/4.0/onecall/current?appid=dummy")
        outbound.assert_not_called()

    def test_geocoding_and_current_weather_share_one_counter(self):
        self.seed(count=0)
        client = OpenWeatherClient(cache_dir=self.root / "cache")
        client.budget = self.budget
        class FakeResponse:
            def __init__(self, payload): self.payload = json.dumps(payload).encode("utf-8")
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, size=-1): return self.payload if size < 0 else self.payload[:size]
        calls = []
        def respond(request, timeout):
            calls.append(request.full_url)
            if "/geo/1.0/zip" in request.full_url:
                return FakeResponse({"name":"Potsdam","country":"DE","lat":52.4,"lon":13.1})
            return FakeResponse({"timezone":"Europe/Berlin","timezone_offset":7200,
                "data":[{"dt":1792261200,"temp":10.0,"feels_like":9.0,"humidity":70,
                "pressure":1013,"wind_speed":2.0,"weather":[{"description":"klar"}]}]})
        with patch.object(client._opener, "open", side_effect=respond):
            client.fetch("Potsdam, 14467, Deutschland", "dummy-key", force=True)
            self.assertEqual(self.budget.status(now=self.now)["count"], 2)
            client.fetch("Potsdam, 14467, Deutschland", "dummy-key", force=True)
        self.assertEqual(len(calls), 3)
        self.assertIn("/geo/1.0/zip", calls[0])
        self.assertIn("/data/4.0/onecall/current", calls[1])
        self.assertIn("/data/4.0/onecall/current", calls[2])
        self.assertEqual(self.budget.status(now=self.now)["count"], 3)

    def test_previous_day_state_does_not_roll_back_if_clock_moves_back(self):
        self.seed(day=datetime(2026, 10, 18, tzinfo=timezone.utc).date(), count=2)
        with self.assertRaises(BudgetUnavailable):
            self.budget.reserve_call(now=self.now)


if __name__ == "__main__":
    unittest.main(verbosity=2)




