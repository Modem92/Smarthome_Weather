"""Hidden real-Tk rendering with synthetic fixtures and no network or credentials."""
import tempfile
import gc
import tkinter as tk
import unittest
import http.client
import json
import ssl
from http.cookies import SimpleCookie
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, Mock

from PIL import Image
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.maps.radar_map import RadarMapResult, MapPosition
from wetterstation.mobile.mobile_settings import MobileSettingsServer, COOKIE_NAME, PAIR_COOKIE


class TkPreviewTests(unittest.TestCase):
    def tearDown(self):
        # Dispose Tk reference cycles on the UI thread before the next test
        # starts TLS workers, which must never finalize Tk variables.
        gc.collect()



    def test_midnight_display_refresh_never_calls_weather_http(self):
        root = tk.Tk()
        root.withdraw()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            with patch("wetterstation.ui.app.ApiKeyStore", return_value=ApiKeyStore(path=Path(folder) / "settings.json")):
                preview = WeatherPreview(root, mock_preview=True)
            preview.mock_preview = False
            tasks = []
            try:
                with patch.object(preview.weather_client, "budget_status_text", return_value="Heute 0/999"), patch.object(preview.weather_client, "_request", side_effect=AssertionError("no weather HTTP")) as request, patch.object(preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
                    preview._refresh_budget_at_midnight()
                    tasks[0]()
                    preview._results.get(timeout=2)()
                    self.assertEqual(preview.budget_status, "Heute 0/999")
                    request.assert_not_called()
            finally:
                root.update_idletasks()
                preview.close()

    def test_midnight_timer_handles_summer_and_winter_clock_changes(self):
        preview = object.__new__(WeatherPreview)
        preview.root = Mock()
        preview._closed = preview.mock_preview = False
        # The midnight after a clock-change day is 23 or 25 actual hours away.
        for moment, hours in ((datetime(2026, 3, 28, 23, tzinfo=timezone.utc), 23),
                              (datetime(2026, 10, 24, 22, tzinfo=timezone.utc), 25)):
            with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
                clock.now.return_value = moment
                preview._schedule_budget_midnight()
            self.assertEqual(preview.root.after.call_args.args[0], hours * 60 * 60 * 1000 + 20)

    @staticmethod
    def button(parent, text):
        for child in parent.winfo_children():
            if isinstance(child, tk.Button) and child.cget("text") == text:
                return child
            found = TkPreviewTests.button(child, text)
            if found is not None:
                return found
        return None



    def test_late_radar_result_is_discarded_after_location_change(self):
        root = tk.Tk()
        root.withdraw()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            with patch("wetterstation.ui.app.ApiKeyStore", return_value=ApiKeyStore(path=Path(folder) / "settings.json")):
                preview = WeatherPreview(root, mock_preview=True)
            preview.mock_preview = False
            tasks = []
            places = {"Berlin": {"name": "Berlin", "country": "DE", "lat": 52.52, "lon": 13.405},
                      "Hamburg": {"name": "Hamburg", "country": "DE", "lat": 53.55, "lon": 9.99}}
            try:
                preview.settings.location = "Berlin"
                with patch.object(preview.weather_client, "load_resolved_place", side_effect=lambda query: places.get(query.split(",")[0])), patch.object(preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)), patch.object(preview.radar_client, "fetch", return_value=Mock()) as fetch:
                    preview.refresh_radar()
                    preview.settings.location = "Hamburg"
                    tasks[0]()
                    preview._results.get(timeout=2)()
                    self.assertIsNone(preview.radar_result)
                    self.assertEqual(fetch.call_args.args[2], MapPosition("Berlin", "Berlin", 52.52, 13.405))
                    self.assertEqual(preview._map_position().name, "Hamburg")
                    preview.settings.location = "Wien"
                    self.assertIsNone(preview._map_position())
            finally:
                root.update_idletasks()
                preview.close()

    def test_mobile_https_save_updates_the_ui_without_starting_weather_http(self):
        root = tk.Tk()
        root.withdraw()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix="mobile-ui-") as folder:
            store = ApiKeyStore(path=Path(folder) / "settings.json")
            store.save_configuration("Potsdam, 14467, Deutschland", "dummy-old-key")
            with patch("wetterstation.ui.app.ApiKeyStore", return_value=store):
                preview = WeatherPreview(root, mock_preview=True)
            preview.mock_preview = False
            service = MobileSettingsServer(store, on_change=lambda changed: preview._results.put(lambda: preview._apply_mobile_settings(changed)))
            try:
                service.start("127.0.0.1", 0)
                context = ssl.create_default_context(cafile=str(service.certificate_path))
                port = service._server.server_port
                def request(method, path, data=None, headers=None):
                    conn = http.client.HTTPSConnection("127.0.0.1", port, context=context, timeout=3)
                    try:
                        conn.request(method, path, json.dumps(data).encode() if data is not None else None,
                                     {"Origin": service.url, "Content-Type": "application/json", **(headers or {})})
                        response = conn.getresponse()
                        return response.status, dict(response.getheaders()), json.loads(response.read())
                    finally:
                        conn.close()
                _, pair_headers, _ = request("POST", "/api/pairing/start", {})
                pair_cookie = SimpleCookie(pair_headers["Set-Cookie"])
                status, headers, _ = request("POST", "/api/login", {"code": service.pairing_display()["code"]},
                    {"Cookie": f"{PAIR_COOKIE}={pair_cookie[PAIR_COOKIE].value}"})
                self.assertEqual(status, 200)
                cookies = SimpleCookie(headers["Set-Cookie"])
                cookie = {"Cookie": f"{COOKIE_NAME}={cookies[COOKIE_NAME].value}"}
                _, _, snapshot = request("GET", "/api/settings", headers=cookie)
                with patch("wetterstation.weather.weather_service.OpenWeatherClient._request", side_effect=AssertionError("no provider request")) as weather:
                    status, _, _ = request("POST", "/api/settings", {"location": "Potsdam", "api_key": "dummy-new-key"},
                                           {**cookie, "X-CSRF-Token": snapshot["csrf"]})
                    self.assertEqual(status, 200)
                    with patch.object(root, "after", wraps=root.after) as scheduled:
                        preview._results.get(timeout=2)()
                    weather.assert_not_called()
                    self.assertFalse(any(call.args[1] in (preview.refresh_weather, preview.refresh_radar)
                                         for call in scheduled.call_args_list if len(call.args) > 1))
                self.assertEqual(preview.settings.location, "Potsdam")
                self.assertEqual(preview.location_var.get(), "Potsdam")
                self.assertIsNone(preview.weather_record)
                self.assertIsNone(preview.forecast_record)
                self.assertEqual(store.load_api_key(), "dummy-new-key")
            finally:
                service.stop()
                root.update_idletasks()
                preview.close()


    def test_all_pages_and_scaled_gray_map_render_without_network(self):
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk display unavailable")
        root.withdraw()
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            store = ApiKeyStore(path=Path(folder) / "settings.json")
            with patch("wetterstation.ui.app.ApiKeyStore", return_value=store):
                with patch("wetterstation.weather.weather_service.urllib.request.OpenerDirector.open", side_effect=AssertionError("no weather HTTP")):
                    with patch("wetterstation.maps.radar_map.urllib.request.urlopen", side_effect=AssertionError("no map HTTP")):
                        preview = WeatherPreview(root, mock_preview=True)
                        preview.weather_client.cache_dir = Path(folder) / "weather"
                        preview.radar_client.cache_dir = Path(folder) / "radar"
                        errors = []
                        root.report_callback_exception = lambda *args: errors.append(args[1])
                        try:
                            for width, height in ((1000, 650), (1280, 800)):
                                preview.canvas.winfo_width = lambda: width
                                preview.canvas.winfo_height = lambda: height
                                preview.mock_preview = True
                                for page in range(4):
                                    preview.page = page
                                    preview.draw()
                                base, radar = BytesIO(), BytesIO()
                                Image.new("RGBA", (770, 489), "#dddddd").save(base, format="PNG")
                                Image.new("RGBA", (770, 489), (0, 0, 0, 0)).save(radar, format="PNG")
                                now = datetime.now(timezone.utc)
                                preview.radar_result = RadarMapResult(base.getvalue(), radar.getvalue(), now, now)
                                preview.radar_error = ""
                                preview.page = 2
                                preview.mock_preview = False
                                preview.draw()
                                self.assertIsNotNone(preview.radar_result)
                                while preview._radar_render_active is not None:
                                    preview._results.get(timeout=10)()
                                self.assertEqual(preview.radar_photo.width(), width)
                                self.assertEqual(preview.radar_overlay.height(), height)
                            root.update_idletasks()
                            self.assertEqual(errors, [])
                        finally:
                            preview.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
