"""Real Tk map layout and navigation using synthetic images, never live data."""
import gc
import tempfile
import threading
import tkinter as tk
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview, LOCAL_ZONE
from wetterstation.maps.radar_map import RadarMapClient, RadarMapResult, RadarMapError, MapPosition
from wetterstation.weather.weather_service import OpenWeatherClient
from wetterstation.maps.radar_render import prepare_radar_layers
from wetterstation.maps.radar_motion import RadarMotion, RainVector


class FullWindowMapTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix="map-layout-")
        self.root = tk.Tk()
        self.root.withdraw()
        directory = Path(self.folder.name)
        with patch("wetterstation.ui.app.ApiKeyStore", return_value=ApiKeyStore(path=directory / "settings.json")):
            self.preview = WeatherPreview(self.root, mock_preview=True)
        self.preview.weather_client = OpenWeatherClient(cache_dir=directory / "weather")
        self.preview.radar_client = RadarMapClient(cache_dir=directory / "radar")
        self.preview.mock_preview = False
        self.preview.page = 2
        self.preview.radar_error = ""
        self.preview.radar_result = self.fixture()
        self.canvas = self.preview.canvas
        self.real_start_worker = self.preview._start_worker

    def tearDown(self):
        self.wait_for_frames()
        self.root.update_idletasks()
        self.preview.close()
        del self.preview
        gc.collect()
        self.folder.cleanup()

    @staticmethod
    def fixture():
        images = []
        for background, circle in (((255, 255, 255, 255), (255, 0, 0, 255)),
                                   ((0, 0, 0, 0), (0, 153, 52, 255))):
            image = Image.new("RGBA", (360, 240), background)
            ImageDraw.Draw(image).ellipse((150, 90, 210, 150), fill=circle)
            output = BytesIO()
            image.save(output, format="PNG")
            images.append(output.getvalue())
        now = datetime.now(timezone.utc)
        return RadarMapResult(*images, now, now)

    def wait_for_frames(self):
        while self.preview._radar_render_active is not None:
            self.preview._results.get(timeout=10)()

    def capture_downloads(self, tasks, *, with_errors=False):
        def dispatch(task, failed, name):
            if name == "radar-image-prepare":
                self.real_start_worker(task, failed, name)
            else:
                tasks.append((task, failed, name) if with_errors else task)
        return dispatch

    def draw_at(self, width=1000, height=650):
        self.canvas.winfo_width = lambda: width
        self.canvas.winfo_height = lambda: height
        self.preview.draw()
        self.wait_for_frames()

    def notices(self):
        return [self.canvas.itemcget(item, "text") for item in self.canvas.find_withtag("radar-notice")]

    def test_map_fills_every_window_shape_without_stretch_or_resize_requests(self):
        with patch.object(self.preview, "_start_worker", wraps=self.real_start_worker) as workers, patch.object(self.preview.radar_client, "fetch") as fetch:
            for width, height in ((800, 560), (1000, 650), (1280, 800), (1920, 1080), (3440, 1440), (800, 1100)):
                with self.subTest(size=(width, height)):
                    self.draw_at(width, height)
                    self.assertEqual((self.preview.radar_photo.width(), self.preview.radar_photo.height()), (width, height))
                    self.assertEqual((self.preview.radar_overlay.width(), self.preview.radar_overlay.height()), (width, height))
                    for tag in ("radar-base", "radar-overlay"):
                        self.assertEqual(self.canvas.coords(self.canvas.find_withtag(tag)[0]), [0, 0])
                    self.assertFalse(self.notices())
                    self.assertEqual([self.canvas.itemcget(item, "window") for item in self.canvas.find_all()
                                      if self.canvas.type(item) == "window"], [])
                    radius = min(14, 10 * max(.8, min(width / 1024, height / 600)))
                    self.assertEqual(self.canvas.coords(self.canvas.find_withtag("radar-location")[0]),
                                     [width / 2 - radius, height / 2 - radius, width / 2 + radius, height / 2 + radius])
            # A circular feature must remain circular after a portrait crop.
            photo = self.preview.radar_photo
            is_red = lambda pixel: pixel[0] > 200 and pixel[1] < 50
            horizontal = [x for x in range(800) if is_red(photo.get(x, 550))]
            vertical = [y for y in range(1100) if is_red(photo.get(400, y))]
            self.assertLessEqual(abs(len(horizontal) - len(vertical)), 2)
            overlay = self.preview.radar_overlay
            blue = [x for x in range(800) if not overlay.transparency_get(x, 550)]
            self.assertLessEqual(abs((blue[0] + blue[-1]) - (horizontal[0] + horizontal[-1])), 2)
            self.assertTrue(all(call.args[2] == "radar-image-prepare" for call in workers.call_args_list))
            fetch.assert_not_called()


    def test_notices_only_for_problems_and_explicit_demo(self):
        original = self.preview.radar_result
        self.draw_at()
        self.assertFalse(self.notices())
        for result, expected in ((replace(original, stale=True), "Zwischengespeicherte"),
                                 (replace(original, observed_at=original.observed_at - timedelta(minutes=20)), "20 Minuten alt"),
                                 (replace(original, warning="Speichern fehlgeschlagen"), "Speichern fehlgeschlagen")):
            self.preview.radar_result = result
            self.draw_at()
            self.assertIn(expected, " ".join(self.notices()))
        self.preview.radar_result = None
        self.preview.radar_error = "Karte wird geladen …"
        self.draw_at()
        self.assertIn("geladen", " ".join(self.notices()))
        self.preview.radar_error = "Kartendienst nicht erreichbar."
        self.draw_at()
        self.assertIn("nicht erreichbar", " ".join(self.notices()))
        self.preview.radar_result = original
        with patch.object(self.preview, "_map_position", return_value=None):
            self.draw_at()
            self.assertFalse(self.canvas.find_withtag("radar-base"))
            self.assertIn("Kartenposition", " ".join(self.notices()))
        with patch.object(self.preview, "_map_position", return_value=MapPosition("Berlin", "Berlin", 52.52, 13.405)):
            self.draw_at()
            self.assertFalse(self.canvas.find_withtag("radar-base"))
            self.assertIn("gewählten Ort", " ".join(self.notices()))
        self.preview.radar_result = replace(original, basemap=b"broken image")
        self.draw_at()
        self.assertTrue(self.preview.radar_result.stale)
        self.assertTrue(self.canvas.find_withtag("radar-base"))
        self.assertIn("Kartenbild", " ".join(self.notices()))
        self.preview.mock_preview = True
        self.draw_at()
        self.assertIn("DEMO", " ".join(self.notices()))
        self.assertFalse(self.canvas.find_withtag("radar-base"))

    def test_next_manual_request_uses_current_proportional_viewport(self):
        self.canvas.winfo_width = lambda: 3840
        self.canvas.winfo_height = lambda: 2160
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks)), patch.object(self.preview.radar_client, "fetch", return_value=self.fixture()) as fetch:
            self.preview.refresh_radar()
            tasks.pop()()
            self.assertEqual(fetch.call_args.args[:2], (1800, 1012))
            self.assertEqual(self.preview.radar_requested_size, (1800, 1012))
            self.preview._results.get(timeout=2)()
            self.draw_at(800, 2000)
            self.assertEqual(fetch.call_count, 1)
            self.preview.refresh_radar()
            tasks.pop()()
            self.assertEqual(fetch.call_args.args[:2], (440, 1100))

    def test_failed_refresh_after_resize_retains_valid_map_and_recovers(self):
        original = self.preview.radar_result
        self.draw_at(1024, 600)
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks, with_errors=True)), patch.object(self.preview.radar_client, "fetch", side_effect=RadarMapError("DWD-Metadaten momentan nicht erreichbar; kein gültiger Karten-Cache.")):
            self.preview.refresh_radar()
            tasks.pop()[0]()
            self.preview._results.get(timeout=2)()
        self.assertFalse(self.preview.radar_download_running)
        self.assertTrue(self.preview.radar_result.stale)
        self.assertEqual(self.preview.radar_result.basemap, original.basemap)
        self.assertTrue(self.canvas.find_withtag("radar-base"))
        self.assertIn("letzte gültige Karte", self.preview.radar_result.warning)
        self.assertIn("Zwischengespeicherte Karte", " ".join(self.notices()))
        self.assertNotIn("kein gültiger Karten-Cache", " ".join(self.notices()))
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks, with_errors=True)), patch.object(self.preview.radar_client, "fetch", return_value=original):
            self.preview.refresh_radar()
            tasks.pop()[0]()
            self.preview._results.get(timeout=2)()
        self.assertFalse(self.preview.radar_result.stale)
        self.assertFalse(self.notices())

    def test_retained_map_never_uses_expired_future_or_other_place_data(self):
        original = self.preview.radar_result
        for invalid in (replace(original, observed_at=original.observed_at - timedelta(hours=2)),
                        replace(original, fetched_at=original.fetched_at - timedelta(hours=2)),
                        replace(original, observed_at=original.observed_at + timedelta(hours=1)),
                        replace(original, position=MapPosition("Berlin", "Berlin", 52.52, 13.405)), None):
            self.preview.radar_result = invalid
            self.assertIsNone(self.preview._retained_radar(original.position))

    def test_unexpected_refresh_failure_also_retains_valid_map(self):
        self.draw_at(1024, 600)
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks, with_errors=True)):
            self.preview.refresh_radar()
            tasks.pop()[1]()
        self.assertFalse(self.preview.radar_download_running)
        self.assertTrue(self.preview.radar_result.stale)
        self.assertTrue(self.canvas.find_withtag("radar-base"))

    def test_ready_map_reuses_both_photos_across_page_switches(self):
        self.draw_at(1024, 600)
        photos = (self.preview.radar_photo, self.preview.radar_overlay)
        with patch("wetterstation.ui.app.prepare_radar_layers", side_effect=AssertionError("no image preparation")), patch(
                "wetterstation.ui.app.tk.PhotoImage", side_effect=AssertionError("no Tk image recreation")), patch.object(
                self.preview.radar_client, "fetch", side_effect=AssertionError("no downloads")):
            for _ in range(12):
                self.preview.change_page(-1)
                self.preview.change_page(1)
                self.assertIs(self.preview.radar_photo, photos[0])
                self.assertIs(self.preview.radar_overlay, photos[1])
                self.assertFalse(self.notices())

    def motion_fixture(self, source=None):
        source = source or self.preview.radar_result
        return RadarMotion(source, source.observed_at - timedelta(minutes=5), source.observed_at,
            (360, 240), tuple(RainVector(x, y, 2, -1, .99) for x, y in
                              ((50, 70), (130, 80), (250, 160), (180, 120), (345, 230))))

    def test_motion_placement_reuse_no_network_or_recalculation_on_navigation_resize(self):
        self.draw_at(1024, 600)
        self.preview._radar_motion = self.motion_fixture()
        photos = self.preview.radar_photo, self.preview.radar_overlay
        with patch("wetterstation.ui.app.analyse_motion", side_effect=AssertionError("no recalculation")), patch.object(
                self.preview.radar_client, "fetch_previous", side_effect=AssertionError("no history download")), patch.object(
                self.preview.radar_client, "fetch", side_effect=AssertionError("no map download")):
            for _ in range(3):
                self.preview.draw()
                arrows = self.canvas.find_withtag("radar-motion-arrow")
                self.assertGreater(len(arrows), 0)
                self.assertLessEqual(len(arrows), 3)
                protected = [self.canvas.bbox(tag) for tag in ("radar-location", "radar-place-label-background", "radar-info")]
                for arrow in arrows:
                    l, t, r, b = self.canvas.bbox(arrow)
                    self.assertEqual(self.canvas.itemcget(arrow, "fill"), "#34454c")
                    for ll, tt, rr, bb in protected:
                        self.assertFalse(l < rr and r > ll and t < bb and b > tt)
                self.preview.change_page(-1)
                self.preview.change_page(1)
                self.assertEqual((self.preview.radar_photo, self.preview.radar_overlay), photos)
            for width, height in ((480, 800), (360, 300), (800, 1100)):
                self.draw_at(width, height)
                self.assertLessEqual(len(self.canvas.find_withtag("radar-motion-arrow")), 3)
                self.assertTrue(self.canvas.find_withtag("radar-info"))

    def test_motion_is_bound_to_displayed_image_and_hidden_on_stale_cache(self):
        self.draw_at(1024, 600)
        self.preview._radar_motion = self.motion_fixture()
        self.preview.draw()
        self.assertTrue(self.canvas.find_withtag("radar-motion-arrow"))
        self.preview.radar_result = replace(self.preview.radar_result, stale=True)
        self.preview.draw()
        self.assertFalse(self.canvas.find_withtag("radar-motion"))
        self.preview.radar_result = self.fixture()
        self.draw_at(1024, 600)
        self.assertFalse(self.canvas.find_withtag("radar-motion"))
        self.assertTrue(self.canvas.find_withtag("radar-base"))

    def test_motion_worker_background_latest_only_and_atomic_source_binding(self):
        self.draw_at(1024, 600)
        tasks = []
        first = self.preview.radar_result
        self.preview.page = 0
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, fail, name: tasks.append((task, fail, name))), patch.object(
                self.preview.radar_client, "fetch_previous", return_value=replace(first, observed_at=first.observed_at - timedelta(minutes=5))) as fetch, patch(
                "wetterstation.ui.app.analyse_motion", side_effect=lambda source, old: self.motion_fixture(source)) as analyse:
            self.preview._queue_radar_motion(first)
            # Current map is ready before any motion work has run.
            self.assertIs(self.preview._radar_frame.result, first)
            second = replace(first, observed_at=first.observed_at + timedelta(seconds=1))
            third = replace(first, observed_at=first.observed_at + timedelta(seconds=2))
            with patch("wetterstation.ui.app.fresh_source", return_value=True):
                self.preview._queue_radar_motion(second)
                self.preview._queue_radar_motion(third)
                self.assertEqual(len(tasks), 1)
                self.assertIs(self.preview._radar_motion_pending[0], third)
                self.preview.radar_result = third
                tasks.pop(0)[0]()
                self.preview._results.get(timeout=2)()
                self.assertIsNone(self.preview._radar_motion)
                self.assertEqual(len(tasks), 1)
                tasks.pop(0)[0]()
                self.preview._results.get(timeout=2)()
            self.assertIs(self.preview._radar_motion.source, third)
            self.assertEqual(analyse.call_count, 2)
            self.assertIsNone(self.preview._radar_motion_active)

    def test_regular_motion_reuses_previous_and_failure_has_no_immediate_retry(self):
        self.draw_at(1024, 600)
        first = self.preview.radar_result
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, fail, name: tasks.append((task, fail))), patch.object(
                self.preview.radar_client, "fetch_previous", side_effect=RadarMapError("history failed")) as fetch, patch(
                "wetterstation.ui.app.analyse_motion", side_effect=lambda source, old: self.motion_fixture(source)) as analyse:
            self.preview._queue_radar_motion(first)
            tasks.pop()[1]()
            self.preview._queue_radar_motion(first)
            self.assertFalse(tasks)
            # Five-minute observation interval, still before now to keep a fixed valid clock.
            second = replace(first, observed_at=first.observed_at - timedelta(minutes=5))
            self.preview._radar_motion_history = [second]
            self.preview._radar_motion_bootstrap_attempt = None
            self.preview._queue_radar_motion(first)
            tasks.pop()[0]()
            self.preview._results.get(timeout=2)()
            fetch.assert_not_called()
            self.assertIs(analyse.call_args.args[1], second)
            self.assertEqual(self.preview._last_radar_update_text(), first.fetched_at.astimezone(LOCAL_ZONE).strftime("%H:%M"))

    def test_late_motion_after_location_change_or_close_is_discarded(self):
        self.draw_at(1024, 600)
        first = self.preview.radar_result
        for closed in (False, True):
            self.preview._closed = False
            self.preview._radar_motion_bootstrap_attempt = None
            tasks = []
            with patch.object(self.preview, "_start_worker", side_effect=lambda task, fail, name: tasks.append(fail)):
                self.preview._queue_radar_motion(first)
            self.preview._clear_radar_frame()
            self.preview._closed = closed
            with patch.object(self.preview, "draw", side_effect=AssertionError("no stale UI update")):
                tasks.pop()(self.motion_fixture(first))
            self.assertIsNone(self.preview._radar_motion)
        self.preview._closed = False

    def test_motion_expiry_uses_existing_ui_poll_and_demo_never_queues(self):
        self.draw_at(1024, 600)
        self.preview._radar_motion = self.motion_fixture()
        self.preview.draw()
        with patch("wetterstation.ui.app.fresh_source", return_value=False):
            self.preview._drain_results()
        self.assertFalse(self.canvas.find_withtag("radar-motion"))
        self.preview.mock_preview = True
        with patch.object(self.preview, "_start_worker", side_effect=AssertionError("demo network disabled")):
            self.preview._queue_radar_motion(self.preview.radar_result)

    def test_selected_place_label_and_orange_white_marker_are_above_rain(self):
        self.draw_at(1024, 600)
        marker = self.canvas.find_withtag("radar-location")[0]
        label = self.canvas.find_withtag("radar-place-label")[0]
        background = self.canvas.find_withtag("radar-place-label-background")[0]
        overlay = self.canvas.find_withtag("radar-overlay")[0]
        order = list(self.canvas.find_all())
        self.assertEqual(self.canvas.itemcget(marker, "fill"), "#f17647")
        self.assertEqual(self.canvas.itemcget(marker, "outline"), "#ffffff")
        self.assertEqual(self.canvas.itemcget(label, "text"), "Potsdam")
        self.assertEqual(self.canvas.itemcget(background, "fill"), "#ffffff")
        self.assertLess(order.index(overlay), order.index(marker))
        self.assertLess(order.index(overlay), order.index(background))
        self.assertLess(order.index(background), order.index(label))
        left, top, right, bottom = self.canvas.bbox(background)
        self.assertGreater(left, 0)
        self.assertLess(right, 1024)
        self.assertGreater(top, 0)
        self.assertLess(bottom, 300)

    def test_background_download_prepares_images_before_first_map_visit(self):
        self.canvas.winfo_width = lambda: 1024
        self.canvas.winfo_height = lambda: 600
        self.preview.page = 0
        self.preview.radar_result = None
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks)), patch.object(
                self.preview.radar_client, "fetch", return_value=self.fixture()):
            self.preview.refresh_radar()
            tasks.pop()()
            self.preview._results.get(timeout=5)()
            self.wait_for_frames()
        self.assertEqual(self.preview._radar_frame.size, (1024, 600))
        with patch("wetterstation.ui.app.prepare_radar_layers", side_effect=AssertionError("already prepared")):
            self.preview.page = 1
            self.preview.change_page(1)
        self.assertTrue(self.canvas.find_withtag("radar-base"))

    def test_resize_keeps_old_pair_and_only_prepares_latest_requested_size(self):
        self.draw_at(1024, 600)
        original = self.preview.radar_photo
        self.preview.radar_result = self.fixture()
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
            self.preview.draw()
            for width in (800, 900, 1000):
                self.canvas.winfo_width = lambda width=width: width
                self.canvas.winfo_height = lambda: 700
                self.preview.draw()
            self.assertEqual(len(tasks), 1)
            self.assertIs(self.preview.radar_photo, original)
            self.assertEqual(self.canvas.coords(self.canvas.find_withtag("radar-base")[0]), [-12, 50])
            tasks.pop(0)()
            self.preview._results.get(timeout=5)()
            self.assertIs(self.preview.radar_photo, original)
            self.assertEqual(len(tasks), 1)
            self.assertEqual(self.preview._radar_render_active.size, (1000, 700))
            tasks.pop(0)()
            self.preview._results.get(timeout=5)()
        self.assertEqual(self.preview._radar_frame.size, (1000, 700))
        self.assertIsNone(self.preview._radar_render_active)
        self.assertIsNone(self.preview._radar_render_pending)

    def test_late_preparation_after_location_change_never_creates_old_tk_images(self):
        self.canvas.winfo_width = lambda: 1024
        self.canvas.winfo_height = lambda: 600
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
            self.preview.draw()
            self.preview._clear_radar_frame()
            self.preview.settings.location = "Berlin"
            berlin = MapPosition("Berlin", "Berlin", 52.52, 13.405)
            self.preview.radar_result = replace(self.fixture(), position=berlin)
            with patch.object(self.preview, "_map_position", return_value=berlin):
                self.preview.draw()
                tasks.pop(0)()
                with patch("wetterstation.ui.app.tk.PhotoImage", side_effect=AssertionError("obsolete result")):
                    self.preview._results.get(timeout=5)()
                self.assertIsNone(self.preview.radar_photo)
                tasks.pop(0)()
                self.preview._results.get(timeout=5)()
                self.assertEqual(self.preview._radar_frame.result.position, berlin)

    def test_layers_prepare_on_worker_but_tk_images_are_created_on_ui_thread(self):
        main_thread = threading.get_ident()
        prepare_threads, tk_threads = [], []
        original_photo = tk.PhotoImage
        def prepare(request):
            prepare_threads.append(threading.get_ident())
            return prepare_radar_layers(request)
        def photo(*args, **kwargs):
            tk_threads.append(threading.get_ident())
            return original_photo(*args, **kwargs)
        with patch("wetterstation.ui.app.prepare_radar_layers", side_effect=prepare), patch("wetterstation.ui.app.tk.PhotoImage", side_effect=photo):
            self.draw_at(1024, 600)
        self.assertEqual(len(prepare_threads), 1)
        self.assertNotEqual(prepare_threads[0], main_thread)
        self.assertEqual(tk_threads, [main_thread, main_thread])

    def test_invalid_first_image_fails_once_without_retry_loop(self):
        self.preview.radar_result = replace(self.fixture(), radar=b"invalid PNG")
        with patch("wetterstation.ui.app.prepare_radar_layers", wraps=prepare_radar_layers) as prepare:
            self.draw_at(1024, 600)
            self.preview.draw()
            self.assertEqual(prepare.call_count, 1)
        self.assertIsNone(self.preview.radar_result)
        self.assertIn("Kartenbild", " ".join(self.notices()))

    def test_second_tk_image_failure_keeps_entire_previous_pair(self):
        self.draw_at(1024, 600)
        photos = self.preview.radar_photo, self.preview.radar_overlay
        self.preview.radar_result = self.fixture()
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
            self.preview.draw()
            tasks.pop()()
            with patch("wetterstation.ui.app.tk.PhotoImage", side_effect=[object(), RuntimeError("private details")]):
                self.preview._results.get(timeout=5)()
        self.assertIs(self.preview.radar_photo, photos[0])
        self.assertIs(self.preview.radar_overlay, photos[1])
        self.assertTrue(self.preview.radar_result.stale)
        self.assertNotIn("private details", " ".join(self.notices()))

    def test_completion_after_close_has_no_tk_calls(self):
        self.canvas.winfo_width = lambda: 1024
        self.canvas.winfo_height = lambda: 600
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
            self.preview.draw()
        tasks.pop()()
        callback = self.preview._results.get(timeout=5)
        self.preview._closed = True
        try:
            with patch("wetterstation.ui.app.tk.PhotoImage", side_effect=AssertionError("window closed")):
                callback()
        finally:
            self.preview._radar_render_active = None
            self.preview._closed = False

    def test_expired_previous_frame_is_not_retained_after_bad_new_image(self):
        self.draw_at(1024, 600)
        frame = self.preview._radar_frame
        self.preview._radar_frame = replace(frame, result=replace(
            frame.result, observed_at=frame.result.observed_at - timedelta(hours=2)))
        self.preview.radar_result = replace(self.fixture(), radar=b"broken")
        self.draw_at(1024, 600)
        self.assertIsNone(self.preview.radar_photo)
        self.assertIsNone(self.preview.radar_result)

    def test_info_field_is_bottom_centered_and_fits_narrow_portrait_windows(self):
        self.preview.radar_result = replace(self.fixture(), fetched_at=datetime(2026, 10, 22, 21, 55, tzinfo=timezone.utc))
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 23, 8, tzinfo=timezone.utc)
            for width, height in ((1024, 600), (600, 800), (360, 600)):
                self.draw_at(width, height)
                item = self.canvas.find_withtag("radar-info")[0]
                left, top, right, bottom = self.canvas.bbox(item)
                self.assertGreaterEqual(left, 0)
                self.assertGreaterEqual(top, 0)
                self.assertLess(right, width)
                self.assertLess(bottom, height)
                self.assertAlmostEqual((left+right)/2, width/2, delta=1)
                self.assertLessEqual(height - bottom, 15)
                self.assertEqual(self.canvas.itemcget("radar-time", "text"), "22.10.2026 23:55")

    def test_radar_time_uses_fetch_time_and_gains_date_at_local_midnight(self):
        fetched = datetime(2026, 10, 23, 8, 5, tzinfo=timezone.utc)
        self.preview.radar_result = replace(self.fixture(), fetched_at=fetched, observed_at=fetched - timedelta(minutes=20))
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock:
            clock.now.return_value = fetched + timedelta(minutes=1)
            self.draw_at(1024, 600)
            self.assertEqual(self.canvas.itemcget("radar-time", "text"), "10:05")
            previous = self.preview.radar_photo
            clock.now.return_value = datetime(2026, 10, 23, 22, tzinfo=timezone.utc)
            self.preview.draw()
            self.assertEqual(self.canvas.itemcget("radar-time", "text"), "23.10.2026 10:05")
            self.assertIs(self.preview.radar_photo, previous)

    def test_radar_timestamp_advances_only_when_prepared_pair_is_shown(self):
        fetched = datetime.now(timezone.utc).replace(second=0, microsecond=0) - timedelta(minutes=5)
        self.preview.radar_result = replace(self.fixture(), fetched_at=fetched)
        self.draw_at(1024, 600)
        previous = self.canvas.itemcget("radar-time", "text")
        self.preview.radar_result = replace(self.fixture(), fetched_at=fetched + timedelta(minutes=5))
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=lambda task, *_: tasks.append(task)):
            self.preview.draw()
            self.assertEqual(self.canvas.itemcget("radar-time", "text"), previous)
            tasks.pop()()
            self.preview._results.get(timeout=5)()
        self.assertNotEqual(self.canvas.itemcget("radar-time", "text"), previous)
        self.assertEqual(self.preview._radar_frame.result.fetched_at, self.preview.radar_result.fetched_at)

    def test_same_pixel_objects_can_update_metadata_without_recreating_images(self):
        self.draw_at(1024, 600)
        previous = self.preview.radar_photo
        fetched = self.preview.radar_result.fetched_at - timedelta(minutes=1)
        self.preview.radar_result = replace(self.preview.radar_result, fetched_at=fetched)
        with patch("wetterstation.ui.app.prepare_radar_layers", side_effect=AssertionError("identical pixels")):
            self.preview.draw()
        self.assertIs(self.preview.radar_photo, previous)
        self.assertEqual(self.preview._radar_frame.result.fetched_at, fetched)

    def test_info_field_remains_visible_without_position_or_after_error_and_in_demo(self):
        self.preview.radar_result = None
        self.draw_at(1024, 600)
        self.assertTrue(self.canvas.find_withtag("radar-info"))
        self.assertEqual(self.canvas.itemcget("radar-time", "text"), "Noch nicht aktualisiert")
        self.preview.radar_error = "Kartendienst nicht erreichbar."
        with patch.object(self.preview, "_map_position", return_value=None):
            self.preview.draw()
            self.assertTrue(self.canvas.find_withtag("radar-info"))
        self.preview.mock_preview = True
        with patch.object(self.preview.radar_client, "fetch") as fetch:
            self.preview.draw()
            fetch.assert_not_called()


    def test_failed_manual_refresh_keeps_timestamp_and_rearms_fixed_slot(self):
        moment = datetime(2026, 10, 23, 12, 4, 30, tzinfo=timezone.utc)
        self.preview.radar_result = replace(self.fixture(), fetched_at=moment - timedelta(minutes=5),
                                             observed_at=moment - timedelta(minutes=5))
        tasks = []
        with patch("wetterstation.ui.app.datetime", wraps=datetime) as clock, patch.object(
                self.preview, "_start_worker", side_effect=self.capture_downloads(tasks)), patch.object(
                self.preview.radar_client, "fetch", side_effect=RadarMapError("DWD nicht erreichbar")):
            clock.now.return_value = moment
            self.draw_at(1024, 600)
            timestamp = self.canvas.itemcget("radar-time", "text")
            self.preview.refresh_radar()
            self.preview.refresh_radar()
            self.assertEqual(len(tasks), 1)
            tasks.pop()()
            clock.now.return_value = moment + timedelta(seconds=15)
            self.preview._results.get(timeout=5)()
            self.assertEqual(self.canvas.itemcget("radar-time", "text"), timestamp)
            self.assertEqual(self.preview.radar_refresh_due.minute, 5)
            self.assertEqual(self.preview.radar_refresh_due.second, 0)
            self.assertTrue(self.preview.radar_result.stale)

    def test_actual_wms_client_refresh_never_uses_weather_transport_or_budget(self):
        self.draw_at(1024, 600)
        images = []
        for color in ((210, 210, 210, 255), (0, 0, 0, 0)):
            output = BytesIO()
            Image.new("RGBA", (1024, 600), color).save(output, format="PNG")
            images.append(output.getvalue())
        tasks = []
        with patch.object(self.preview, "_start_worker", side_effect=self.capture_downloads(tasks)), patch.object(
                self.preview.radar_client, "_radar_timestamp", return_value=datetime.now(timezone.utc)) as metadata, patch.object(
                self.preview.radar_client, "_request", side_effect=images) as maps, patch.object(
                self.preview.weather_client, "_request", side_effect=AssertionError("no OpenWeather")) as weather, patch.object(
                self.preview.weather_client.budget, "reserve_call", side_effect=AssertionError("no budget")) as budget:
            self.preview.refresh_radar()
            tasks.pop()()
            self.preview._results.get(timeout=5)()
            self.wait_for_frames()
            self.assertEqual(metadata.call_count, 1)
            self.assertEqual(maps.call_count, 2)
            weather.assert_not_called()
            budget.assert_not_called()


if __name__ == "__main__":
    unittest.main()
