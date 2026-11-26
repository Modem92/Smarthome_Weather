"""Render isolated, clearly labelled UI samples without binding a server or HTTP."""
import gc
import sys
import tempfile
import tkinter as tk
from pathlib import Path

from PIL import ImageGrab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.ui.widgets import CATALOG, new_widget


def main():
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    output = Path(__file__).resolve().parents[1] / "build" / "checks" / "display-check"
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
        root = tk.Tk()
        preview = WeatherPreview(root, widget_demo=True,
            settings_store=ApiKeyStore(path=Path(folder) / "settings.json"))
        errors = []
        root.report_callback_exception = lambda *_args: errors.append("Tk callback error")

        def capture(name, width=1024, height=600):
            root.geometry(f"{width}x{height}+0+0")
            root.update()
            preview.draw()
            root.update()
            # Wait for this window's compositor frame, not a desktop screenshot.
            if sys.platform == "win32":
                ctypes.windll.dwmapi.DwmFlush()
            # Capture this test window only, even when another app is foreground.
            picture = ImageGrab.grab(window=root.winfo_id())
            picture.save(output / name)

        capture("overview.png")
        preview.dashboard["pages"][0]["widgets"][0]["fields"] = ["time"]
        capture("clock-only.png")
        capture("wide.png", 1600, 800)
        capture("portrait.png", 600, 900)
        preview.page = 1
        capture("forecast.png")
        hourly = new_widget("hourly", "hourly-check", w=12, h=8)
        hourly["fields"] = list(CATALOG["hourly"]["fields"])
        preview.dashboard = {"version": 2, "pages": [{"id": "check", "title": "Vorhersage · Demo", "widgets": [hourly]}]}
        preview.page = 0
        capture("hourly-all-fields.png")
        hourly["w"], hourly["h"] = 6, 4
        capture("hourly-minimum.png")
        daily = new_widget("daily", "daily-check", w=6, h=4)
        daily["fields"] = list(CATALOG["daily"]["fields"])
        preview.dashboard["pages"][0]["widgets"] = [daily]
        capture("daily-minimum.png")
        preview._pairing_screen = {"label": "Anfrage 01 · DEMO",
            "code": "DEMO-ONLY-1234", "url": "https://127.0.0.1:8765"}
        capture("pairing.png")
        preview.close()
        del preview
        gc.collect()
        assert not errors, errors
    print("Display samples checked: build/checks/display-check (demo data, no network)")


if __name__ == "__main__":
    main()
