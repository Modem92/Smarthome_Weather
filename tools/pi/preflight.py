"""Offline Pi checks: synthetic images, temporary TLS files, no weather requests."""
from io import BytesIO
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo


def main():
    from PIL import Image, ImageOps
    from wetterstation.maps.radar_map import RadarMapClient
    from wetterstation.mobile.mobile_settings import local_tls, MobileSettingsServer
    from wetterstation.storage.file_io import SettingsFileLock
    from wetterstation.storage.api_key_store import ApiKeyStore
    from wetterstation.ui.widgets import default_layout, validate_layout, revision, arrange_page, new_widget
    from wetterstation.designer import runtime
    from wetterstation.ui.tk_images import photo_image

    ZoneInfo("Europe/Berlin")
    image = ImageOps.fit(Image.new("RGBA", (320, 240), "gray"), (1024, 600),
                        method=Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="PNG")
    RadarMapClient._validate_png(output.getvalue(), (1024, 600))
    print("Bildverarbeitung: OK", flush=True)
    with tempfile.TemporaryDirectory(prefix="pi-preflight-", dir=Path(__file__).resolve().parent) as directory:
        folder = Path(directory)
        local_tls(folder / "tls", "127.0.0.1")
        # Exercise certificate reuse, including the older Debian cryptography API.
        local_tls(folder / "tls", "127.0.0.1")
        print("Lokale HTTPS-Zertifikate: OK", flush=True)
        with SettingsFileLock(folder / "dummy.lock"):
            pass
        print("Dateisperren: OK", flush=True)
        layout = default_layout()
        validate_layout(layout)
        widgets = arrange_page([new_widget("clock", "a"), new_widget("clock", "b")], pinned="a")
        validate_layout({"version": 2, "pages": [{"id": "p", "title": "Test", "widgets": widgets}]})
        clock = layout["pages"][0]["widgets"][0]
        geometry = tuple(clock[k] for k in ("x", "y", "w", "h"))
        clock["fields"] = []
        assert tuple(clock[k] for k in ("x", "y", "w", "h")) == geometry
        store = ApiKeyStore(path=folder / "dummy-settings.json")
        store.save_configuration("Testort", "dummy-preflight-key")
        store.save_dashboard(layout, revision(store.load_dashboard()))
        assert store.load_dashboard() == layout
        assert store.load_api_key() == "dummy-preflight-key"
        print("Widget-Seiten, Kollisionen und private Layoutspeicherung: OK", flush=True)
        from wetterstation.designer.model import from_layout, validate
        from wetterstation.designer.render import render_page, demo_data
        design = validate(from_layout(layout))
        rendered, _, _ = render_page(design, data=demo_data(), assets=folder)
        assert rendered.size == (1024, 600)
        print('Gestaltungsformat 3 und portable Schrift-/Bilddarstellung: OK', flush=True)
        service = MobileSettingsServer(store)
        pending, state = service.request_pairing("", "127.0.0.1")
        shown = service.pairing_display()
        assert state["state"] == "active" and "code" not in state
        token, _ = service.login(shown["code"], "127.0.0.1", pending)
        assert service.session(token) is not None and service.pairing_display() is None
        service.stop()
        assert service.session(token) is None
        assert store.load_api_key() == "dummy-preflight-key"
        print("Browsergebundener Einmalcode und Sitzungswiderruf (ohne Serverstart): OK", flush=True)
    print("Pi-Vorabpruefung bestanden. Keine Wetterabrufe, keine echten Schluessel verwendet.")


if __name__ == "__main__":
    main()
