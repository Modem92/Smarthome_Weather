"""Real Tk geometry: one-row forecasts and centered contents, isolated demo data."""
import gc
import tempfile
import tkinter as tk
import unittest
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.ui.widgets import CATALOG, new_widget


class WidgetAlignmentTests(unittest.TestCase):
    def test_fast_linux_font_search_still_fits_actual_tk_bounds(self):
        self.preview._font_family='DejaVu Sans'
        self.canvas.delete('all')
        rows=[('Übersicht mit langen Wetterbeschreibungen',1,False,True,()),('25,5 °C',2.4,True,False,())]
        with patch('sys.platform','linux'):
            self.preview._fit_columns([rows],20,20,420,220)
        items=self.canvas.find_withtag('widget-text')
        self.assertEqual(len(items),2)
        for item in items:
            left,top,right,bottom=self.canvas.bbox(item)
            self.assertGreaterEqual(left,20)
            self.assertLessEqual(right,440)
            self.assertGreaterEqual(top,20)
            self.assertLessEqual(bottom,240)
        self.assertTrue(any(key[-1] is True for key in self.preview._font_measure_cache))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.store = ApiKeyStore(Path(self.temp.name)/"settings.json")
        self.store.save_configuration("Testort", "dummy-alignment-key")
        self.root = tk.Tk()
        self.root.withdraw()
        self.preview = WeatherPreview(self.root, widget_demo=True, settings_store=self.store)
        self.canvas = self.preview.canvas
        self.original_settings = self.store.path.read_bytes()

    def tearDown(self):
        self.assertEqual(self.store.path.read_bytes(), self.original_settings)
        self.preview.close()
        del self.preview
        gc.collect()
        self.temp.cleanup()

    def draw(self, item, width=1024, height=600):
        self.preview.dashboard = {"version": 2, "pages": [{"id": "p", "title": "Test", "widgets": [item]}]}
        self.canvas.winfo_width = lambda: width
        self.canvas.winfo_height = lambda: height
        before = deepcopy(self.preview.dashboard)
        self.preview.draw()
        self.assertEqual(self.preview.dashboard, before)

    def assert_forecast(self, item):
        entries = getattr(self.preview.forecast_record, item["type"])
        count = len(entries)
        headings = self.canvas.find_withtag("forecast-heading")
        separators = self.canvas.find_withtag("forecast-separator")
        self.assertEqual(len(headings), count)
        self.assertEqual(len(separators), count-1)
        positions = [self.canvas.coords(text) for text in headings]
        self.assertEqual(len({point[1] for point in positions}), 1, "A forecast must have only one row")
        self.assertEqual([p[0] for p in positions], sorted(p[0] for p in positions))
        expected = [datetime.fromisoformat(entry.timestamp).astimezone(self.preview._display_zone())
                    for entry in entries]
        labels = [stamp.strftime("%H:%M") if item["type"] == "hourly" else
                  f"{('Mo','Di','Mi','Do','Fr','Sa','So')[stamp.weekday()]} {stamp:%d.%m.}" for stamp in expected]
        self.assertEqual([self.canvas.itemcget(text, "text") for text in headings], labels)
        cell_width = positions[1][0]-positions[0][0]
        for index, separator in enumerate(separators):
            left, top, right, bottom = self.canvas.coords(separator)
            self.assertEqual(left, right)
            self.assertGreater(bottom, top)
            self.assertAlmostEqual(left, (positions[index][0]+positions[index+1][0])/2)
        for index in range(count):
            items = self.canvas.find_withtag(f"forecast-column-{item['id']}-{index}")
            self.assertEqual(len(items), 1+len(item["fields"]))
            card = self.canvas.bbox("widget-"+item["id"])
            entry = entries[index]
            expected_values = {"temp": f"{entry.temp:.0f}°" if item["type"] == "hourly" else
                f"{entry.temp_max:.0f}° / {entry.temp_min:.0f}°", "rain": f"Regen {entry.precipitation_probability:.0%}",
                "description": entry.description, "wind": f"Wind {entry.wind_speed:.1f} m/s"}
            for field, text in zip(item["fields"], items[1:]):
                self.assertEqual("".join(self.canvas.itemcget(text,"text").split()), "".join(expected_values[field].split()))
            for first, second in zip(items, items[1:]):
                self.assertLessEqual(self.canvas.bbox(first)[3], self.canvas.bbox(second)[1])
            for text in items:
                box = self.canvas.bbox(text)
                self.assertEqual(self.canvas.itemcget(text, "anchor"), "center")
                self.assertEqual(self.canvas.itemcget(text, "justify"), "center")
                self.assertAlmostEqual((box[0]+box[2])/2, positions[index][0], delta=1)
                self.assertGreaterEqual(box[0], positions[index][0]-cell_width/2+2)
                self.assertLessEqual(box[2], positions[index][0]+cell_width/2-2)
                self.assertGreaterEqual(box[1], card[1])
                self.assertLessEqual(box[3], card[3])
                self.assertTrue(self.canvas.itemcget(text, "text"))
        # All columns use a common row center and type size for each field.
        for field in ["heading", *item["fields"]]:
            items = self.canvas.find_withtag("forecast-field-"+field)
            self.assertEqual(len({self.canvas.coords(text)[1] for text in items}), 1)
            self.assertEqual(len({self.canvas.itemcget(text, "font") for text in items}), 1)

    def test_forecasts_stay_in_one_row_at_all_shapes_and_minimum_sizes(self):
        for kind in ("hourly", "daily"):
            for width, height in ((1024,600), (1600,800), (600,900), (360,600)):
                for span in ((12,8), (6,4)):
                    for fields in (["temp","rain"], list(CATALOG[kind]["fields"]), ["description"]):
                        with self.subTest(kind=kind, size=(width,height), span=span, fields=fields):
                            item = new_widget(kind, "forecast", w=span[0], h=span[1])
                            item["fields"] = fields
                            self.draw(item, width, height)
                            self.assert_forecast(item)

    def test_wrapped_descriptions_preserve_text_and_shared_positions(self):
        entries = tuple(replace(entry, description="Vereinzelte Schauer mit länger anhaltendem Regen" if i%2 else "Heiter")
                        for i, entry in enumerate(self.preview.forecast_record.hourly))
        self.preview.forecast_record = replace(self.preview.forecast_record, hourly=entries)
        item = new_widget("hourly", "forecast", w=12, h=8)
        item["fields"] = ["temp", "description", "rain", "wind"]
        self.draw(item)
        self.assert_forecast(item)
        for entry, text in zip(entries, self.canvas.find_withtag("forecast-field-description")):
            self.assertEqual(" ".join(self.canvas.itemcget(text,"text").split()), entry.description)

    def test_dst_duplicate_hours_are_not_dropped_or_sorted_by_local_label(self):
        start = datetime(2026,10,25,0,tzinfo=timezone.utc)
        entries = tuple(replace(entry, timestamp=(start+timedelta(hours=i)).isoformat())
                        for i, entry in enumerate(self.preview.forecast_record.hourly))
        self.preview.forecast_record = replace(self.preview.forecast_record, hourly=entries)
        item = new_widget("hourly", "forecast")
        self.draw(item)
        self.assert_forecast(item)
        labels = [self.canvas.itemcget(i,"text") for i in self.canvas.find_withtag("forecast-heading")]
        self.assertEqual(labels[:2], ["02:00", "02:00"])

    def test_all_widget_contents_are_centered_without_other_inner_lines(self):
        for kind, spec in CATALOG.items():
            with self.subTest(kind=kind):
                item = new_widget(kind, "check", w=spec["min_width"], h=spec["min_height"])
                item["fields"] = list(spec["fields"])
                self.draw(item)
                frame = self.canvas.find_withtag("widget-card")[0]
                xs = self.canvas.coords(frame)[::2]
                center = (min(xs)+max(xs))/2
                for text in self.canvas.find_withtag("widget-content-check"):
                    if self.canvas.type(text) != "text":
                        continue
                    self.assertEqual(self.canvas.itemcget(text,"justify"), "center")
                    if kind not in ("hourly", "daily"):
                        bounds = self.canvas.bbox(text)
                        self.assertAlmostEqual((bounds[0]+bounds[2])/2, center, delta=1)
                if kind not in ("hourly", "daily"):
                    self.assertFalse(self.canvas.find_withtag("forecast-separator"))
                    self.assertFalse(any(self.canvas.type(i)=="line" for i in self.canvas.find_all()))

    def test_clock_tick_and_hidden_fields_keep_center_and_frame_geometry(self):
        item = new_widget("clock", "clock")
        self.draw(item)
        frame = self.canvas.coords(self.canvas.find_withtag("widget-card")[0])
        before = len(self.canvas.find_all())
        self.preview._tick_widgets()
        self.assertEqual(len(self.canvas.find_all()), before)
        for text in self.canvas.find_withtag("clock-content-clock"):
            box = self.canvas.bbox(text)
            self.assertAlmostEqual((box[0]+box[2])/2, self.canvas.coords(text)[0], delta=1)
        item["fields"] = ["time"]
        self.preview.draw()
        self.assertFalse(self.canvas.find_withtag("clock-clock-date"))
        self.assertEqual(self.canvas.coords(self.canvas.find_withtag("widget-card")[0]), frame)
        item["fields"] = []
        self.preview.draw()
        self.assertFalse(self.canvas.find_withtag("clock-content-clock"))
        self.assertEqual(self.canvas.coords(self.canvas.find_withtag("widget-card")[0]), frame)

    def test_border_is_two_pixels_at_reference_and_scales_on_larger_displays(self):
        for size in ((1024,600), (1600,900)):
            item = new_widget("clock", "clock")
            self.draw(item, *size)
            frame = self.canvas.find_withtag("widget-card")[0]
            self.assertEqual(self.canvas.itemcget(frame,"outline"), "#606060")
            self.assertAlmostEqual(float(self.canvas.itemcget(frame,"width")), max(2,2*min(size[0]/1024,size[1]/600)))

    def test_map_messages_sources_and_full_page_frame_are_centered(self):
        self.draw(new_widget("radar", "radar"))
        frame = self.canvas.find_withtag("widget-card")[0]
        self.assertEqual(float(self.canvas.itemcget(frame,"width")), 2)
        self.assertEqual(self.canvas.coords("radar-notice")[0], 512)
        self.preview._map_attribution(10, 520, "OpenStreetMap · RainViewer", width=1004)
        text = next(i for i in self.canvas.find_withtag("map-attribution") if self.canvas.type(i)=="text")
        self.assertEqual(self.canvas.itemcget(text,"justify"), "center")
        self.assertEqual(self.canvas.coords(text)[0], 512)
        self.preview._map_notice(1024,600,"Zwischengespeichert\nRadarversorgung fehlt")
        self.assertEqual(self.canvas.coords(self.canvas.find_withtag("radar-notice")[-1])[0], 512)
        self.assertEqual(self.canvas.itemcget(self.canvas.find_withtag("radar-notice")[-1],"justify"), "center")
        self.assertEqual(self.canvas.coords("radar-time")[0], 512)


if __name__ == "__main__":
    unittest.main()
