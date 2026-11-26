"""Fixed-clock scheduling and overview contracts, without network or real settings."""
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from wetterstation.ui.app import WeatherPreview, next_weather_refresh
from wetterstation.storage.settings import DisplaySettings


class WeatherScheduleTests(unittest.TestCase):
    def preview(self):
        preview = object.__new__(WeatherPreview)
        preview.root = Mock()
        preview._closed = preview.mock_preview = False
        preview.weather_refresh_job = None
        return preview

    def test_fixed_slots_include_midnight_and_both_clock_changes(self):
        cases = (
            ("2026-10-23T23:59:59+02:00", "2026-10-24T00:00:00+02:00"),
            ("2026-10-24T00:00:00+02:00", "2026-10-24T00:05:00+02:00"),
            ("2026-10-24T00:05:00+02:00", "2026-10-24T00:10:00+02:00"),
            ("2026-03-29T01:59:59+01:00", "2026-03-29T03:00:00+02:00"),
            ("2026-10-25T02:59:59+02:00", "2026-10-25T02:00:00+01:00"),
            ("2026-10-25T02:59:59+01:00", "2026-10-25T03:00:00+01:00"),
        )
        for before, after in cases:
            with self.subTest(before=before):
                self.assertEqual(next_weather_refresh(datetime.fromisoformat(before)).isoformat(), after)

    def test_radar_and_weather_use_identical_slots_at_midnight_and_clock_changes(self):
        for value in ("2026-10-23T23:59:59+02:00", "2026-10-24T00:00:00+02:00",
                      "2026-03-29T01:59:59+01:00", "2026-10-25T02:59:59+02:00"):
            preview = self.preview()
            preview.radar_refresh_job = None
            preview.radar_download_running = False
            preview._map_position = Mock(return_value=object())
            with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
                clock.now.return_value = datetime.fromisoformat(value)
                preview._schedule_weather_refresh()
                weather_delay = preview.root.after.call_args.args[0]
                preview.schedule_radar_refresh()
                self.assertEqual(preview.root.after.call_args.args[0], weather_delay)
                self.assertEqual(preview.radar_refresh_due, next_weather_refresh(clock.now.return_value))

    def test_manual_completion_and_standby_keep_grid_without_backlog(self):
        preview = self.preview()
        for value, delay in (("2026-10-23T12:02:12+02:00", 168000),
                             ("2026-10-23T12:05:08+02:00", 292000),
                             ("2026-10-23T15:43:00+02:00", 120000)):
            with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
                clock.now.return_value = datetime.fromisoformat(value)
                preview._schedule_weather_refresh()
            self.assertEqual(preview.root.after.call_args.args, (delay, preview._scheduled_weather_refresh))
        self.assertEqual(preview.root.after.call_count, 3)
        self.assertEqual(preview.root.after_cancel.call_count, 2)

    def test_scheduled_slot_bypasses_cache_and_duplicate_trigger_is_coalesced(self):
        preview = self.preview()
        preview.refresh_weather = Mock()
        preview._scheduled_weather_refresh()
        preview.refresh_weather.assert_called_once_with(force=True)
        del preview.refresh_weather
        preview.weather_download_running = True
        preview.weather_active_query = "potsdam, de"
        preview.settings = DisplaySettings(location="Potsdam")
        preview.weather_refresh_pending = False
        preview.refresh_weather(force=True)
        self.assertFalse(preview.weather_refresh_pending)
        preview.root.after.assert_not_called()
        preview.settings.location = "Berlin"
        preview.refresh_weather(force=True)
        self.assertTrue(preview.weather_refresh_pending)

    def test_date_format_rolls_over_without_changing_success_timestamp(self):
        preview = self.preview()
        preview.forecast_record = None
        preview.weather_record = SimpleNamespace(retrieved_at="2026-10-23T21:55:00+00:00", timezone="Europe/Berlin")
        for now, expected in (("2026-10-23T21:59:59+00:00", "23:55"),
                              ("2026-10-23T22:00:00+00:00", "23.10.2026 23:55")):
            with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
                clock.now.return_value = datetime.fromisoformat(now)
                self.assertEqual(preview._last_weather_update_text(), expected)
        preview.weather_record = None
        self.assertEqual(preview._last_weather_update_text(), "Noch nicht aktualisiert")

    def test_closed_preview_never_starts_or_schedules_requests(self):
        preview = self.preview()
        preview._closed = True
        preview._schedule_weather_refresh()
        preview._scheduled_weather_refresh()
        preview.root.after.assert_not_called()


if __name__ == "__main__":
    unittest.main()
