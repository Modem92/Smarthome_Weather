"""Responsive real-Tk layout using isolated mock data, without HTTP."""
import gc
import tempfile
import tkinter as tk
import tkinter.font as tkfont
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch, Mock

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview


class ResponsiveDisplayTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = tk.Tk()
        self.root.withdraw()
        with patch("wetterstation.ui.app.ApiKeyStore", return_value=ApiKeyStore(path=Path(self.folder.name) / "settings.json")):
            self.preview = WeatherPreview(self.root, mock_preview=True)
        self.errors = []
        self.root.report_callback_exception = lambda *args: self.errors.append(args[1])

    def tearDown(self):
        self.root.update_idletasks()
        self.preview.close()
        del self.preview
        gc.collect()
        self.folder.cleanup()

    def draw_at(self, width, height, page):
        self.preview.canvas.winfo_width = lambda: width
        self.preview.canvas.winfo_height = lambda: height
        self.preview.page = page
        self.preview.draw()

    def test_all_pages_fit_reference_display_without_scrolling(self):
        for page in (0, 1, 3):
            with self.subTest(page=page):
                self.draw_at(1024, 600, page)
                c = self.preview.canvas
                self.assertEqual(tuple(map(float, c.cget("scrollregion").split())), (0, 0, 1024, 600))
                self.assertFalse(self.preview.scrollbar.winfo_manager())
                for item in c.find_withtag("widget-text"):
                    left, top, right, bottom = c.bbox(item)
                    self.assertGreaterEqual(left, 0)
                    self.assertLessEqual(right, 1024)
                    self.assertLessEqual(bottom, 600)
                if page == 1:
                    self.assertEqual(len(c.find_withtag("forecast-heading")), 13)



    def test_widget_cards_keep_grid_without_overlap_on_every_page(self):
        for size in ((1024,600),(600,1024),(360,600)):
            for page in (0,1,3):
                self.draw_at(*size,page)
                c=self.preview.canvas
                cards=[c.bbox(item) for item in c.find_withtag("widget-card")]
                self.assertEqual(len(cards),len(self.preview._current_page()["widgets"]))
                for i,(left,top,right,bottom) in enumerate(cards):
                    for a,b,d,e in cards[i+1:]:
                        self.assertFalse(left<d and right>a and top<e and bottom>b)
                if page==1:self.assertEqual(len(c.find_withtag("forecast-heading")),13)

    def test_long_notices_do_not_grow_or_scroll_fixed_pages(self):
        self.preview.location_notice="Ein sehr langer Ortsname mit einem ausführlichen Hinweis. "*8
        self.preview.weather_status="Abruf fehlgeschlagen. "*35
        self.preview.budget_status="Die geschützte Begrenzung bleibt erhalten. "*30
        self.draw_at(600,480,0)
        c=self.preview.canvas
        self.assertEqual(float(c.cget("scrollregion").split()[3]),480)
        self.assertFalse(self.preview.scrollbar.winfo_manager())
        for item in c.find_withtag("widget-text"):
            self.assertLessEqual(c.bbox(item)[2],600)
        self.preview.page=2
        self.preview.draw()
        self.assertFalse(self.preview.scrollbar.winfo_manager())
        self.assertEqual(c.yview()[0],0)

    def test_fullscreen_toggle_and_pixel_fonts(self):
        self.assertEqual(self.preview._toggle_fullscreen(), "break")
        self.assertTrue(self.root.attributes("-fullscreen"))
        self.preview._toggle_fullscreen()
        self.assertFalse(self.root.attributes("-fullscreen"))
        self.draw_at(1024, 600, 0)
        for item in self.preview.canvas.find_withtag("widget-text"):
            self.assertLess(int(self.root.tk.splitlist(self.preview.canvas.itemcget(item,"font"))[1]), 0)

    def test_font_pixels_stay_stable_under_dpi_changes(self):
        self.draw_at(1024, 600, 1)
        before = [self.preview.canvas.bbox(item) for item in self.preview.canvas.find_withtag("widget-text")]
        scaling = self.root.tk.call("tk", "scaling")
        try:
            self.root.tk.call("tk", "scaling", 2.5)
            self.draw_at(1024, 600, 1)
            after = [self.preview.canvas.bbox(item) for item in self.preview.canvas.find_withtag("widget-text")]
            self.assertEqual(before, after)
        finally:
            self.root.tk.call("tk", "scaling", scaling)


    def test_cached_forecast_without_daily_extremes_and_startup_fullscreen(self):
        forecast = self.preview.forecast_record
        self.preview.forecast_record = replace(forecast, daily=tuple(replace(item, temp_max=None, temp_min=None) for item in forecast.daily))
        self.preview.mock_preview = False
        with patch.object(self.preview, "schedule_radar_refresh"), patch.object(self.preview, "_start_worker") as workers:
            self.draw_at(1024, 600, 1)
            workers.assert_not_called()
        import wetterstation.ui.app as app
        with patch.object(app.tk, "Tk", return_value=self.root), patch.object(app, "WeatherPreview"), patch.object(self.root, "mainloop"):
            app.main()
        self.assertTrue(self.root.attributes("-fullscreen"))



    def test_passive_display_has_no_controls_or_removed_status_text(self):
        for shape in ((1024,600),(1920,1080),(600,1024)):
            self.draw_at(*shape, 0)
            c=self.preview.canvas
            self.assertEqual(c.cget('bg'),'#ffffff')
            self.assertFalse(any(c.type(i)=='window' for i in c.find_all()))
            self.assertFalse(any(isinstance(w,(tk.Button,tk.Entry,tk.Toplevel)) for w in c.winfo_children()))
            labels=' '.join(c.itemcget(i,'text') for i in c.find_withtag('widget-text'))
            for removed in ('Gewählter Ort:', 'Übernehmen', 'Seite wechseln', 'Widgets am Handy bearbeiten'):
                self.assertNotIn(removed, labels)
            self.assertFalse(hasattr(self.preview,'refresh_button'))
            self.assertFalse(hasattr(self.preview,'location_entry'))

    def test_grid_reaches_right_and_bottom_at_every_aspect_ratio(self):
        for width,height in ((1024,600),(1920,1080),(1280,800),(600,1024)):
            self.draw_at(width,height,0)
            c=self.preview.canvas
            boxes=[c.bbox(i) for i in c.find_withtag('widget-card')]
            margin=12*max(.5,min(width/1024,height/600))
            self.assertAlmostEqual(max(b[2] for b in boxes),width-margin,delta=3)
            self.assertAlmostEqual(max(b[3] for b in boxes),height-margin,delta=3)
            self.assertEqual(self.preview._display_viewport['width'],width)
            self.assertEqual(self.preview._display_viewport['height'],height)

    def test_clock_refits_after_hiding_date_and_on_tick(self):
        self.draw_at(1024,600,0)
        c=self.preview.canvas
        pixel=lambda:int(self.root.tk.splitlist(c.itemcget('clock-clock-time','font'))[1])*-1
        combined=pixel()
        geometry=c.coords(c.find_withtag('widget-clock')[0])
        item=self.preview.dashboard['pages'][0]['widgets'][0]
        item['fields']=['time'];self.preview.draw()
        alone=pixel();self.assertGreater(alone,combined);self.assertGreater(alone,46)
        self.assertEqual(geometry,c.coords(c.find_withtag('widget-clock')[0]))
        count=len(c.find_all())
        self.preview._tick_widgets()
        self.assertEqual(count,len(c.find_all()))
        item['fields']=['time','date'];self.preview.draw()
        self.assertEqual(pixel(),combined)

    def test_pairing_screen_is_passive_and_returns_to_selected_page(self):
        self.preview.page=1
        self.preview._pairing_screen={'label':'Anfrage 01','code':'DUMMY-CODE-ONLY','url':'https://127.0.0.1:8765'}
        self.draw_at(1024,600,1)
        c=self.preview.canvas
        self.assertEqual(c.itemcget('pairing-code','text'),'DUMMY-CODE-ONLY')
        self.assertFalse(c.find_withtag('widget-card'))
        self.assertEqual(self.preview.page,1)
        self.preview._pairing_screen=None;self.preview.draw()
        self.assertEqual(self.preview._current_page()['id'],'forecast')
        self.assertFalse(c.find_withtag('pairing-code'))
        self.assertEqual(len(c.find_withtag('forecast-heading')),13)

if __name__ == "__main__":
    unittest.main()
