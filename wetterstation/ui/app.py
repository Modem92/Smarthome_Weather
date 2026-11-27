"""Desktop preview with current weather and radar observations."""

from __future__ import annotations

import sys
import threading
import queue
import tempfile
from pathlib import Path
from contextlib import nullcontext
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime, timezone, timedelta
from dataclasses import replace
from tkinter import ttk
from zoneinfo import ZoneInfo

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.mobile.mobile_settings import MobileSettingsServer, MobileSettingsError, local_addresses
from wetterstation.storage.settings import DisplaySettings
from wetterstation.weather.countries import COUNTRIES, country_code
from wetterstation.weather.location_time import weather_zone, local_now
from wetterstation.ui.dashboard import DashboardMixin
from wetterstation.maps.radar_map import RadarMapClient, RadarMapResult, RadarMapError, MapPosition, POTSDAM, MAX_RADAR_CACHE_AGE
from wetterstation.maps.radar_render import RadarRenderRequest, prepare_radar_layers
from wetterstation.maps.radar_motion import RadarMotion, analyse_motion, fresh_source, usable_pair, project_vectors
from wetterstation.weather.weather_service import (OpenWeatherClient, WeatherRecord, ForecastEntry, ForecastRecord,
                             WeatherServiceError, normalize_query)


BG = "#ffffff"
PANEL = "#ffffff"
PANEL_LIGHT = "#182941"
TEXT = "#111111"
MUTED = "#404040"
ACCENT = "#73d4c2"
YELLOW = "#ffd166"
BLUE = "#7eb6ff"
ORANGE = "#ff9c72"
GREEN = "#9bd89e"

WEATHER_REFRESH_SECONDS = 5 * 60
LOCAL_ZONE = ZoneInfo("Europe/Berlin")


def next_weather_refresh(now: datetime) -> datetime:
    """Next five-minute boundary; UTC arithmetic handles both DST folds."""
    stamp = (int(now.timestamp()) // WEATHER_REFRESH_SECONDS + 1) * WEATHER_REFRESH_SECONDS
    return datetime.fromtimestamp(stamp, LOCAL_ZONE)


class WeatherPreview(DashboardMixin):
    """A resizable canvas UI; page state is independent from page rendering."""

    def __init__(self, root: tk.Tk, *, mock_preview: bool = False,
                 widget_demo: bool = False, settings_store: ApiKeyStore | None = None) -> None:
        if widget_demo and settings_store is None:
            raise ValueError("Die Widget-Demo benötigt getrennten Einstellungsspeicher.")
        self.root = root
        self._closed = False
        self._results = queue.SimpleQueue()
        self._workers = set()
        self._result_job = root.after(100, self._drain_results)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.report_callback_exception = self._callback_error
        self.widget_demo = widget_demo
        self.mock_preview = mock_preview or widget_demo
        self.root.title("Wetterstation · Widget-Demo · temporär" if widget_demo else "Wetterstation · Displayvorschau · MOCK-TEST" if mock_preview else "Wetterstation · Displayvorschau")
        self.root.configure(bg=BG)
        self.root.geometry("1024x600")
        self.root.minsize(360, 300)
        self._layout_page = None
        self.page = 0
        self.content_offset_y = 0
        self.api_key_store = settings_store if settings_store is not None else ApiKeyStore()
        self.settings_load_error = False
        self._init_dashboard()
        try:
            initial_location, initial_country = self.api_key_store.load_location_country()
        except (OSError, ValueError):
            initial_location = DisplaySettings().location
            initial_country = ""
            self.settings_load_error = True
        self.settings = DisplaySettings(location=initial_location, country_code=initial_country)
        self.radar_client = RadarMapClient()
        self.weather_client = OpenWeatherClient()
        self.weather_record: WeatherRecord | None = None
        self.forecast_record: ForecastRecord | None = None
        self.weather_status = "Wetterdaten werden geladen …"
        self.weather_status_color = MUTED
        self.forecast_status = "Vorhersage wird geladen …"
        self.forecast_status_color = MUTED
        self.weather_generation = 0
        self.weather_download_running = False
        self.weather_refresh_pending = False
        self.weather_active_query: str | None = None
        self.weather_refresh_job: str | None = None
        self.budget_status = "API-Budget wird beim Wetterabruf geprüft."
        self.budget_refresh_job: str | None = None
        self.radar_result: RadarMapResult | None = None
        self.radar_error = "Karte wird geladen …"
        self.radar_requested_size: tuple[int, int] | None = None
        self.radar_photo: tk.PhotoImage | None = None
        self.radar_overlay: tk.PhotoImage | None = None
        self._radar_frame: RadarRenderRequest | None = None
        self._radar_render_active: RadarRenderRequest | None = None
        self._radar_render_pending: RadarRenderRequest | None = None
        self._radar_render_epoch = 0
        self._radar_motion: RadarMotion | None = None
        self._radar_motion_active = None
        self._radar_motion_pending = None
        self._radar_motion_history = []
        self._radar_motion_bootstrap_attempt = None
        self.radar_generation = 0
        self.radar_refresh_job: str | None = None
        self.radar_refresh_due: datetime | None = None
        self.radar_download_running = False
        self.mobile_service: MobileSettingsServer | None = None
        self._mobile_cancel = threading.Event()
        self._mobile_start_pending = False
        self._mobile_start_error = ""
        self._pairing_screen = None
        self.location_var = tk.StringVar(master=root, value=self.settings.location)
        self.country_var = tk.StringVar(master=root, value=COUNTRIES.get(initial_country, {}).get("name", ""))
        self.location_notice = (
            "Projekteinstellungen konnten nicht gelesen werden · Ort gilt nur für diese Sitzung"
            if self.settings_load_error else self.location_message()
        )
        self.location_notice_color = ORANGE if self.settings_load_error else MUTED
        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.scrollbar = tk.Scrollbar(root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<MouseWheel>", self._scroll_page)
        self.canvas.bind("<Button-4>", lambda event: self._scroll_page(event, -1))
        self.canvas.bind("<Button-5>", lambda event: self._scroll_page(event, 1))
        self.canvas.bind("<Configure>", self.draw)
        root.bind("<Escape>", self._handle_map_escape, add="+")
        root.bind("<F11>", self._toggle_fullscreen, add="+")
        root.bind_all("<Left>", lambda event: self.handle_page_key(event, -1))
        root.bind_all("<Right>", lambda event: self.handle_page_key(event, 1))
        root.bind_all("<Up>", lambda event: self.handle_page_key(event, -1))
        root.bind_all("<Down>", lambda event: self.handle_page_key(event, 1))
        if self.mock_preview:
            self._load_mock_preview_data()
        self.draw()
        if not self.mock_preview:
            root.after(100, self.refresh_weather)
            root.after(250, self.refresh_radar)
            self._schedule_budget_midnight()

    def _drain_results(self) -> None:
        if self._closed:
            return
        try:
            for _ in range(20):
                try:
                    callback = self._results.get_nowait()
                except queue.Empty:
                    break
                try:
                    callback()
                except Exception:
                    self._callback_error(None, None, None)
        finally:
            if not self._closed:
                if (self._radar_motion is not None and not fresh_source(self._radar_motion.source)):
                    self._radar_motion = None
                    self.canvas.delete("radar-motion")
                self._result_job = self.root.after(100, self._drain_results)

    def _start_worker(self, task, on_error, name: str) -> None:
        self._workers={worker for worker in self._workers if worker.is_alive()}
        def run():
            try:
                task()
            except Exception:
                # Never print exception details: a transport may include a key.
                self._results.put(on_error)
        try:
            worker=threading.Thread(target=run, name=name, daemon=True)
            self._workers.add(worker)
            worker.start()
        except Exception:
            if 'worker' in locals():self._workers.discard(worker)
            on_error()

    def _callback_error(self, *_args) -> None:
        if self._closed:
            return
        self.location_notice = "Ein interner Fehler ist aufgetreten. Bitte erneut versuchen oder die Vorschau neu starten."
        self.location_notice_color = ORANGE
        self.root.title("Wetterstation · Anzeigefehler, bitte Programm neu starten")

    def close(self) -> None:
        if self._closed:return
        self._closed = True
        self._clear_radar_frame()
        self._radar_render_active = None
        self._mobile_cancel.set()
        if self.mobile_service:
            self.mobile_service.stop()
            self.mobile_service = None
        # Include short one-shot refreshes queued by location changes as well.
        for job in self.root.tk.splitlist(self.root.tk.call("after", "info")):
            if job is not None:
                try:
                    self.root.after_cancel(job)
                except tk.TclError:
                    pass
        # Pure image jobs must release their UI-owner references before Tcl is
        # destroyed. Joining never executes their queued callbacks or network work.
        import time
        deadline=time.monotonic()+5
        for worker in list(self._workers):
            worker.join(timeout=max(0,deadline-time.monotonic()))
        self._finish_close()

    def _finish_close(self):
        self._workers={worker for worker in self._workers if worker.is_alive()}
        if self._workers:
            self.root.after(50,self._finish_close)
            return
        while not self._results.empty():
            self._results.get_nowait()
        for name in ('_fit_fonts','_designer_patch_photos'):
            values=getattr(self,name,None)
            if values is not None:values.clear()
        self._designer_photo=None
        self.location_var=None
        self.country_var=None
        if 'report_callback_exception' in vars(self.root):
            del self.root.report_callback_exception
        self.root.destroy()

    def _load_mock_preview_data(self) -> None:
        """Supply clearly labeled display data without reading keys or making requests."""
        utc_now = datetime.now(timezone.utc)
        zone = ZoneInfo("Europe/Berlin")
        local_now = utc_now.astimezone(zone)
        query = normalize_query(self.settings.location)
        self.weather_record = WeatherRecord(
            query=query, name=f"{self.settings.location} · Demo", country="DE", lat=52.3989, lon=13.0657,
            timezone="Europe/Berlin", observed_at=local_now.isoformat(timespec="minutes"),
            retrieved_at=utc_now.isoformat(timespec="seconds"), temp=17.4,
            feels_like=17.0, humidity=63, pressure=1016, wind_speed=2.8,
            description="Leicht bewölkt", source="DEMO / MOCKDATEN")
        start_hour = local_now.replace(minute=0, second=0, microsecond=0)
        hourly = tuple(ForecastEntry(
            timestamp=(start_hour + timedelta(hours=index + 1)).isoformat(timespec="minutes"),
            temp=16.5 - index * 0.6,
            description="Leicht bewölkt" if index % 3 else "Heiter",
            precipitation_probability=0.05 + index * 0.04,
            wind_speed=2.2 + index * 0.15) for index in range(8))
        first_day = local_now.replace(hour=12, minute=0, second=0, microsecond=0)
        daily = tuple(ForecastEntry(
            timestamp=(first_day + timedelta(days=index)).isoformat(timespec="minutes"),
            temp=17.0 - index * 0.8, temp_min=9.0 - index * 0.3,
            temp_max=19.0 - index * 0.7,
            description="Leicht bewölkt" if index % 2 == 0 else "Vereinzelte Schauer",
            precipitation_probability=0.1 + index * 0.12,
            wind_speed=2.5 + index * 0.2) for index in range(5))
        retrieved = utc_now.isoformat(timespec="seconds")
        self.forecast_record = ForecastRecord(
            query=query, name=f"{self.settings.location} · Demo", country="DE", lat=52.3989, lon=13.0657,
            timezone="Europe/Berlin", retrieved_at=retrieved, hourly=hourly, daily=daily,
            hourly_retrieved_at=retrieved, daily_retrieved_at=retrieved,
            source="DEMO / MOCKDATEN")
        self.weather_status = "DEMO / MOCKDATEN · kein Wetterabruf"
        self.weather_status_color = ORANGE
        self.forecast_status = "DEMO / MOCKDATEN · kein Wetterabruf"
        self.forecast_status_color = ORANGE
        self.radar_error = "TESTANSICHT · Kartenabrufe deaktiviert"

    def location_message(self) -> str:
        location = self.settings.location
        if len(location) > 42:
            location = location[:39].rstrip() + "…"
        country = COUNTRIES.get(self.settings.country_code, {}).get("name", "Bitte Land auswählen")
        return f"Gewählter Ort: {location} · {country}"

    def _weather_query(self):
        # Invalid legacy country values cannot resolve or load another place's cache.
        return self.settings.query if self.settings.country_code else ""

    def _display_zone(self):
        return weather_zone(self.weather_record, self.forecast_record)[0]

    def _utc_suffix(self):
        return "" if weather_zone(self.weather_record, self.forecast_record)[1] else " UTC"

    def _clock_text(self, field, fields):
        from wetterstation.ui.dashboard import clock_text
        now, known = local_now(self.weather_record, self.forecast_record)
        return clock_text(field, fields, now) + ("" if known else " UTC")

    def apply_location(self, *, persist: bool = True, refresh: bool = True) -> None:
        if self.mock_preview:
            return
        previous_location = (self.settings.location, self.settings.country_code)
        code = country_code(self.country_var.get())
        if not code:
            self.location_notice = "Bitte ein Land aus der Länderauswahl wählen."
            self.location_notice_color = ORANGE
            self.draw()
            return
        if not self.settings.set_location(self.location_var.get()):
            self.location_var.set(self.settings.location)
            self.location_notice = "Eingabe leer · bisheriger Ort bleibt aktiv"
            self.location_notice_color = ORANGE
        else:
            self.settings.country_code = code
            self.country_var.set(COUNTRIES[code]["name"])
            self.location_var.set(self.settings.location)
            if (self.settings.location, self.settings.country_code) != previous_location:
                self.weather_generation += 1
                self.weather_record = None
                self.forecast_record = None
                self.weather_status = "Wetterdaten werden geladen …"
                self.weather_status_color = MUTED
                self.forecast_status = "Vorhersage wird geladen …"
                self.forecast_status_color = MUTED
                if refresh:
                    self.root.after(10, self.refresh_weather)
                else:
                    self.weather_status = self.forecast_status = "Ort gespeichert · nächste geplante Aktualisierung oder manuell."
                self.radar_generation += 1
                self.radar_requested_size = None
                self.radar_result = None
                self._clear_radar_frame()
                if refresh:
                    self.radar_error = "Karte wartet auf die eindeutige Ortsposition aus dem Wetterabruf."
                    self.root.after(10, self.refresh_radar)
                else:
                    self.radar_error = "Ort gespeichert · nächste geplante Kartenaktualisierung oder manuell."
            try:
                if persist:
                    self.api_key_store.save_configuration(self.settings.location, country_code=self.settings.country_code)
            except (OSError, ValueError):
                self.location_notice = "Ort übernommen · Speichern im OneDrive-Projekt fehlgeschlagen"
                self.location_notice_color = ORANGE
            else:
                self.location_notice = self.location_message() + " · im Projekt gespeichert"
                self.location_notice_color = MUTED
        self.draw()

    def _apply_mobile_settings(self, key_changed: bool) -> None:
        if self._closed:
            return
        try:
            location, code = self.api_key_store.load_location_country()
        except (OSError, ValueError):
            self.location_notice = "Handy-Einstellungen gespeichert, aber am PC momentan nicht lesbar."
            self.location_notice_color = ORANGE
            self.draw()
            return
        if key_changed:
            self.weather_client.reset_request_pause()
        self.location_var.set(location)
        self.country_var.set(COUNTRIES.get(code, {}).get("name", ""))
        self.apply_location(persist=False, refresh=False)
        self.location_notice = "Vom Handy gespeichert · Schlüssel nicht geprüft · kein zusätzlicher Wetterabruf"
        self.location_notice_color = ACCENT
        self.draw()

    def _check_pairing(self):
        job = getattr(self, '_pairing_expiry_job', None)
        self._pairing_expiry_job = None
        if job is not None:
            self.root.after_cancel(job)
        if self._closed:
            return
        snapshot = self.mobile_service.pairing_display() if self.mobile_service else None
        if snapshot != self._pairing_screen:
            self._pairing_screen = snapshot
            self.draw()
        deadline = self.mobile_service.pairing_deadline() if self.mobile_service else None
        if deadline is not None:
            import time
            self._pairing_expiry_job = self.root.after(max(1, int((deadline-time.monotonic())*1000)+1), self._check_pairing)

    def _maintain_mobile_connection(self):
        """Discover/rebind without blocking Tk; no service is started by construction."""
        if self._closed or (self.mock_preview and not self.widget_demo):
            return
        if self._mobile_start_pending:
            return
        self._mobile_start_pending = True
        cancel = self._mobile_cancel

        def finish(error):
            self._mobile_start_pending = False
            self._mobile_start_error = error
            if not self._closed:
                self.root.after(10000, self._maintain_mobile_connection)

        def prepare():
            error = ""
            try:
                addresses = [a for a in local_addresses() if not a.startswith("127.")]
                service = self.mobile_service
                active_host = service.url.split("://", 1)[-1].split(":", 1)[0] if service and service.running else ""
                if active_host not in addresses:
                    if service:
                        service.stop()
                    if not addresses:
                        error = "Keine Heimnetz-Verbindung. WLAN oder LAN prüfen."
                    elif not cancel.is_set():
                        service = MobileSettingsServer(self.api_key_store,
                            on_change=lambda changed: self._results.put(lambda: self._apply_mobile_settings(changed)),
                            on_layout_change=lambda layout, page_id: self._results.put(lambda: self._apply_mobile_dashboard(layout, page_id)),
                            on_page_change=lambda page_id: self._results.put(lambda: self._show_mobile_page(page_id)),
                            on_pairing_change=lambda: self._results.put(self._pairing_changed),
                            layout_only=self.widget_demo)
                        self._publish_to_new_service(service)
                        self.mobile_service = service
                        service.start(addresses[0])
                        if cancel.is_set():
                            service.stop()
            except MobileSettingsError as exc:
                error = str(exc)
            except Exception:
                error = "Handy-Verbindung momentan nicht verfügbar. Erneuter Versuch folgt."
            self._results.put(lambda: finish(error))

        self._start_worker(prepare, lambda: finish("Handy-Verbindung momentan nicht verfügbar."), "mobile-auto-start")

    def _pairing_changed(self):
        if not self._closed:
            self._check_pairing()

    def handle_page_key(self, event: tk.Event, step: int) -> str | None:
        if isinstance(event.widget, (tk.Entry, ttk.Combobox)):
            return None
        return self.change_page(step)

    def change_page(self, step: int) -> str:
        self.page = (self.page + step) % len(self.dashboard["pages"])
        if self._page_has_radar():
            self.canvas.focus_set()
        self.draw()
        return "break"

    def _handle_map_escape(self, _event: tk.Event) -> str | None:
        if self._page_has_radar():
            self.page = 0
            self.canvas.focus_set()
            self.draw()
            return "break"
        return None

    def _toggle_fullscreen(self, _event=None):
        self.root.attributes("-fullscreen", not bool(self.root.attributes("-fullscreen")))
        return "break"

    def _scroll_page(self, event, direction=None):
        if not self._page_has_radar() and self.scrollbar.winfo_manager():
            self.canvas.yview_scroll(direction if direction is not None else (-1 if event.delta > 0 else 1), "units")
            return "break"

    def _flow_text(self, x, y, text, width, size=13, color=TEXT, weight="normal"):
        """Wrap text and measure its actual height before placing the next item."""
        item = self.canvas.create_text(self.x(x), self.x(y), text=text, fill=color,
            font=("Segoe UI", -max(10, round(size * self.s)), weight),
            anchor="nw", width=self.x(width), tags=("layout-text",))
        bounds = self.canvas.bbox(item)
        return y + ((bounds[3] - bounds[1]) / self.s if bounds else 0)

    def draw(self, _event=None):
        self.draw_dashboard()

    def _last_weather_update_text(self) -> str:
        if self.weather_record is None:
            return "Noch nicht aktualisiert"
        stamp = datetime.fromisoformat(self.weather_record.retrieved_at).astimezone(self._display_zone())
        today = datetime.now(timezone.utc).astimezone(self._display_zone()).date()
        return stamp.strftime("%H:%M" if stamp.date() == today else "%d.%m.%Y %H:%M") + self._utc_suffix()

    def x(self, value: float) -> float:
        return value * self.s

    def y(self, value: float) -> float:
        return self.x(value + self.content_offset_y)

    def rr(self, x1: float, y1: float, x2: float, y2: float,
           radius: float, fill: str, outline: str = "", *, border_width: float = 1) -> None:
        x1, x2, r = map(self.x, (x1, x2, radius))
        y1, y2 = self.y(y1), self.y(y2)
        c = self.canvas
        c.create_polygon(x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
                         x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
                         x1, y2, x1, y2-r, x1, y1+r, x1, y1,
                         smooth=True, fill=fill, outline=outline, width=self.x(border_width))

    @staticmethod
    def _cache_age_text(retrieved_at: str) -> str:
        try:
            retrieved = datetime.fromisoformat(retrieved_at)
            if retrieved.tzinfo is None:
                retrieved = retrieved.replace(tzinfo=timezone.utc)
            seconds = max(0, (datetime.now(timezone.utc) - retrieved.astimezone(timezone.utc)).total_seconds())
            return f"vor {seconds / 3600:.1f} Std." if seconds >= 3600 else f"vor {seconds / 60:.0f} Min."
        except (TypeError, ValueError):
            return "Zeit unbekannt"

    def refresh_weather(self, *, force: bool = False) -> None:
        if self.mock_preview or self._closed:
            return
        if not self.settings.country_code:
            self.weather_status = self.forecast_status = "Bitte zuerst ein Land auswählen."
            self.weather_status_color = self.forecast_status_color = ORANGE
            self.draw()
            self._schedule_weather_refresh()
            return
        if self.weather_download_running:
            # Duplicate triggers share this run; a new place needs its own result.
            if normalize_query(self._weather_query()) != self.weather_active_query:
                self.weather_refresh_pending = True
            return
        self.weather_download_running = True
        self.weather_active_query = normalize_query(self._weather_query())
        if self.weather_refresh_job is not None:
            try:
                self.root.after_cancel(self.weather_refresh_job)
            except tk.TclError:
                pass
            self.weather_refresh_job = None
        self.weather_generation += 1
        generation = self.weather_generation
        query = self._weather_query()
        cached = self.weather_client.load_cached(query)
        self.weather_record = cached
        cached_forecast = self.weather_client.load_cached_forecast(query)
        self.forecast_record = cached_forecast
        self.weather_status = (f"Zwischenspeicher · {self._cache_age_text(cached.retrieved_at)} · wird geprüft …"
                               if cached else "One Call 4.0 · aktuelle Daten werden geladen …")
        self.weather_status_color = ORANGE if cached else MUTED
        self.forecast_status = (f"Zwischenspeicher · {self._cache_age_text(cached_forecast.retrieved_at)} · wird geprüft …"
                                if cached_forecast else "One Call 4.0 · Vorhersage wird geladen …")
        self.forecast_status_color = ORANGE if cached_forecast else MUTED
        self.draw()

        def fetch() -> None:
            key = None
            try:
                key = self.api_key_store.load_api_key()
                record = self.weather_client.fetch(query, key or "", force=force)
                if not force and cached and record == cached:
                    status, color = f"Cache · {self._cache_age_text(record.retrieved_at)} · One Call 4.0", MUTED
                else:
                    status = f"Live · One Call 4.0 · {record.retrieved_at}"
                    color = ACCENT
                if record.warnings:
                    status += " · " + " · ".join(record.warnings)
                    color = ORANGE
            except (WeatherServiceError, OSError, ValueError) as exc:
                record = self.weather_client.load_cached(query)
                message = str(exc) if isinstance(exc, WeatherServiceError) else "Projekteinstellungen konnten nicht gelesen werden."
                if record:
                    status = f"Cache · {self._cache_age_text(record.retrieved_at)} · {message}"
                else:
                    status = message + " Kein gültiger Cache (Höchstalter 6 Stunden)."
                color = ORANGE
            if not self.weather_client.has_resolved_place(query) and not cached_forecast:
                forecast = None
                forecast_status = "Ausgelassen · Ort nicht aufgelöst; Geocoding wird nicht doppelt angefragt."
                forecast_color = ORANGE
            else:
                try:
                    forecast = self.weather_client.fetch_forecast(query, key or "", force=force)
                    if forecast.errors:
                        forecast_status = "Teilweise · " + " · ".join(forecast.errors)
                        forecast_color = ORANGE
                    elif not force and cached_forecast and forecast == cached_forecast:
                        forecast_status = f"Cache · {self._cache_age_text(forecast.retrieved_at)} · One Call 4.0"
                        forecast_color = MUTED
                    elif (not force and cached_forecast
                          and (forecast.hourly_retrieved_at == cached_forecast.hourly_retrieved_at
                               or forecast.daily_retrieved_at == cached_forecast.daily_retrieved_at)):
                        forecast_status = ("Teilweise aktualisiert · Stunden- und Tagescache haben getrennte Zeitstempel. "
                                           f"One Call 4.0 · {forecast.retrieved_at}")
                        forecast_color = ORANGE
                    else:
                        forecast_status = f"Live · One Call 4.0 · {forecast.retrieved_at}"
                        forecast_color = ACCENT
                except (WeatherServiceError, OSError, ValueError) as exc:
                    forecast = self.weather_client.load_cached_forecast(query)
                    message = str(exc) if isinstance(exc, WeatherServiceError) else "Vorhersage konnte nicht verarbeitet werden."
                    forecast_status = (f"Cache · {self._cache_age_text(forecast.retrieved_at)} · {message}"
                                       if forecast else message + " Kein gültiger Cache (Höchstalter 6 Stunden).")
                    forecast_color = ORANGE
            designer_series, designer_notices = {}, {}
            try:
                active_design = self.api_key_store.load_dashboard()
                if active_design.get('version') in (3,4):
                    from wetterstation.designer.live_timelines import collect
                    designer_series, designer_notices = collect(
                        self.weather_client, self.api_key_store, active_design, query, key,
                        current=lambda: (not self._closed and generation == self.weather_generation
                                         and normalize_query(query) == normalize_query(self._weather_query())))
            except (OSError, ValueError, TypeError):
                # Extra-source failure never interrupts the regular three requests.
                designer_notices = {s:'Zusatzdaten derzeit nicht verfügbar' for s in ('1min','15min','1h','1day')}
            budget_status = self.weather_client.budget_status_text()
            def finish() -> None:
                self.weather_download_running = False
                self.budget_status = budget_status
                # Schedule before rendering, so a display error cannot stop refreshes.
                if self.weather_refresh_pending:
                    self.weather_refresh_pending = False
                    self.root.after(10, self.refresh_weather)
                else:
                    self._schedule_weather_refresh()
                if generation == self.weather_generation and normalize_query(query) == normalize_query(self._weather_query()):
                    self.weather_record = record
                    self.weather_status = status
                    self.weather_status_color = color
                    self.forecast_record = forecast
                    self.forecast_status = forecast_status
                    self.forecast_status_color = forecast_color
                    self._designer_series = designer_series
                    self._designer_series_query = normalize_query(query)
                    self._designer_series_notices = designer_notices
                    position = self._map_position()
                    if self.radar_result is not None and self.radar_result.position != position:
                        self.radar_generation += 1
                        self.radar_result = None
                        self._clear_radar_frame()
                    self.draw()
                    if self.radar_result is None and position is not None:
                        self.root.after(10, self.refresh_radar)
            self._results.put(finish)

        def unexpected_failure() -> None:
            self.weather_download_running = False
            self._schedule_weather_refresh()
            if generation == self.weather_generation:
                self.weather_status = self.forecast_status = "Aktualisierung unerwartet fehlgeschlagen; bitte erneut versuchen."
                self.weather_status_color = self.forecast_status_color = ORANGE
                self.draw()
            if self.weather_refresh_pending:
                self.weather_refresh_pending = False
                self.root.after(10, self.refresh_weather)
        self._start_worker(fetch, unexpected_failure, "current-weather-download")

    def _schedule_weather_refresh(self) -> None:
        if self._closed or self.mock_preview:
            return
        if self.weather_refresh_job is not None:
            self.root.after_cancel(self.weather_refresh_job)
        now = datetime.now(timezone.utc)
        due = next_weather_refresh(now)
        delay = max(1, int((due.timestamp() - now.timestamp()) * 1000 + .999))
        self.weather_refresh_job = self.root.after(delay, self._scheduled_weather_refresh)

    def _scheduled_weather_refresh(self) -> None:
        self.weather_refresh_job = None
        self.refresh_weather(force=True)

    def _schedule_budget_midnight(self) -> None:
        """Refresh only the counter at local midnight, without weather HTTP."""
        if self._closed or self.mock_preview:
            return
        now = datetime.now(timezone.utc)
        local = now.astimezone(ZoneInfo("Europe/Berlin"))
        midnight = (local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        delay = max(1, int((midnight.timestamp() - now.timestamp()) * 1000) + 20)
        self.budget_refresh_job = self.root.after(delay, self._refresh_budget_at_midnight)

    def _refresh_budget_at_midnight(self) -> None:
        self.budget_refresh_job = None
        if self._closed:
            return
        self._schedule_budget_midnight()
        def read_status():
            status = self.weather_client.budget_status_text()
            def finish():
                self.budget_status = status
                self.draw()
            self._results.put(finish)
        def failed():
            self.budget_status = "Budgetstand derzeit nicht lesbar; Wetterabrufe bleiben geschützt."
            self.draw()
        self._start_worker(read_status, failed, "budget-midnight-refresh")

    def _map_position(self) -> MapPosition | None:
        place = self.weather_client.load_resolved_place(self._weather_query()) if self.settings.country_code else None
        if isinstance(place, dict):
            try:
                if place["country"] != self.settings.country_code:
                    return None
                return MapPosition(self.settings.location, place["name"], float(place["lat"]), float(place["lon"]), place["country"])
            except (KeyError, TypeError, ValueError):
                return None
        # Keep the previously verified start position available without geocoding.
        if self.settings.country_code == "DE" and self.radar_client.is_verified_start_location(self.settings.location):
            return POTSDAM
        return None

    def _map_notice(self, width: int, height: int, text: str, *, centered: bool = False) -> None:
        """A compact exception notice, never a permanent sidebar."""
        scale = max(.8, min(width / 1024, height / 600))
        x, y = (width / 2, height / 2) if centered else (width / 2, 16 * scale)
        item = self.canvas.create_text(
            x, y, text=text, anchor="center" if centered else "n",
            fill=TEXT, font=(self._font_family, -round(14 * scale)), justify="center",
            width=max(1, min(600 * scale, width - 48 * scale)), tags=("radar-notice",))
        bounds = self.canvas.bbox(item)
        if bounds:
            left, top, right, bottom = bounds
            background = self.canvas.create_rectangle(
                left - 10, top - 8, right + 10, bottom + 8,
                fill=PANEL, outline="", tags=("radar-notice-background",))
            self.canvas.tag_lower(background, item)

    def _clear_radar_frame(self) -> None:
        self._radar_render_epoch += 1
        self._radar_frame = self._radar_render_pending = None
        self.radar_photo = self.radar_overlay = None
        self._radar_motion = self._radar_motion_pending = None
        self._radar_motion_history.clear()
        self._radar_motion_bootstrap_attempt = None

    def _queue_radar_motion(self, source: RadarMapResult) -> None:
        if source.provider != "dwd":
            return
        if self._closed or self.mock_preview or not fresh_source(source):
            self._radar_motion = self._radar_motion_pending = None
            return
        previous = next((p for p in reversed(self._radar_motion_history) if usable_pair(source, p)), None)
        previous = previous or self.radar_client.previous_observation(source)
        self._radar_motion_history = [p for p in self._radar_motion_history
                                      if usable_pair(source, p)] + [source]
        self._radar_motion_history = self._radar_motion_history[-3:]
        if previous is None:
            attempt = (source.position, source.observed_at, int(source.fetched_at.timestamp()) // 300)
            if attempt == self._radar_motion_bootstrap_attempt:
                return
            self._radar_motion_bootstrap_attempt = attempt
        self._radar_motion_pending = (source, previous, self._radar_render_epoch)
        self._start_radar_motion()

    def _start_radar_motion(self) -> None:
        if self._closed or self._radar_motion_active is not None or self._radar_motion_pending is None:
            return
        job = self._radar_motion_pending
        self._radar_motion_pending = None
        self._radar_motion_active = job
        source, previous, epoch = job

        def calculate():
            older = previous if previous is not None else self.radar_client.fetch_previous(source)
            motion = analyse_motion(source, older)
            self._results.put(lambda: finish(motion))

        def finish(motion=None):
            self._radar_motion_active = None
            if self._closed:
                return
            if (source is self.radar_result and epoch == self._radar_render_epoch
                    and source.position == self._map_position()):
                self._radar_motion = motion if fresh_source(source) else None
                if self._page_has_radar():
                    self.draw()
            self._start_radar_motion()

        self._start_worker(calculate, finish, "radar-motion-prepare")

    def _draw_radar_motion(self, width: int, height: int) -> None:
        motion, frame = self._radar_motion, self._radar_frame
        if (motion is None or frame is None or motion.source is not frame.result
                or not fresh_source(frame.result) or self.radar_result is None or self.radar_result.stale):
            return
        scale = max(.8, min(width / 1024, height / 600))
        protected = []
        for tag in ("radar-location", "radar-place-label-background", "radar-notice-background", "radar-info"):
            bounds = self.canvas.bbox(tag)
            if bounds:
                l, t, r, b = bounds
                protected.append((l - 12 * scale, t - 12 * scale, r + 12 * scale, b + 12 * scale))
        offset = ((width - frame.size[0]) / 2, (height - frame.size[1]) / 2)
        # Also clip retained, centered old-size frames against the new window edges.
        protected.extend(((-10000, -10000, 0, 10000), (width, -10000, 10000, 10000),
                          (-10000, -10000, 10000, 0), (-10000, height, 10000, 10000)))
        for coords in project_vectors(motion, frame.size, offset=offset, protected=protected):
            self.canvas.create_line(*coords, fill="#ffffff", width=4 * scale,
                arrow="last", arrowshape=(11 * scale, 13 * scale, 6 * scale),
                capstyle="round", tags=("radar-motion", "radar-motion-halo"))
            self.canvas.create_line(*coords, fill="#34454c", width=2 * scale,
                arrow="last", arrowshape=(9 * scale, 11 * scale, 4 * scale),
                capstyle="round", tags=("radar-motion", "radar-motion-arrow"))

    def _current_radar_render(self) -> RadarRenderRequest | None:
        if self._closed or self.mock_preview or self.radar_result is None:
            return None
        size = (self.canvas.winfo_width(), self.canvas.winfo_height())
        if min(size) <= 1 or self.radar_result.position != self._map_position():
            return None
        return RadarRenderRequest(self.radar_result, size,
                                  normalize_query(self._weather_query()), self._radar_render_epoch)

    def _queue_radar_render(self) -> None:
        request = self._current_radar_render()
        if request is not None and request.matches(self._radar_frame):
            # Identical, already displayed pixels need no preparation, but may have new metadata.
            self._radar_frame = request
            self._radar_render_pending = None
            return
        if request is None or request.matches(self._radar_render_active):
            self._radar_render_pending = None
            return
        # Bound work and memory: one active preparation and only the latest desired view.
        self._radar_render_pending = request
        if self._radar_render_active is not None:
            return
        self._radar_render_active = request
        self._radar_render_pending = None

        def prepare() -> None:
            layers = prepare_radar_layers(request)
            self._results.put(lambda: self._finish_radar_render(request, layers))

        self._start_worker(prepare, lambda: self._finish_radar_render(request, None), "radar-image-prepare")

    def _finish_radar_render(self, request: RadarRenderRequest,
                             layers: tuple[bytes, bytes] | None) -> None:
        if self._closed:
            return
        self._radar_render_active = None
        if request.matches(self._current_radar_render()):
            try:
                if layers is None:
                    raise ValueError("invalid map layers")
                # Tk objects are constructed together, exclusively on the UI thread.
                photos = tuple(tk.PhotoImage(master=self.root, data=data, format="png") for data in layers)
                self.radar_photo, self.radar_overlay = photos
                self._radar_frame = request
            except Exception:
                # A bad new image must not destroy an earlier valid same-place frame.
                previous = self._radar_frame
                self.radar_result = previous.result if previous and previous.result.position == request.result.position else None
                self.radar_result = self._retained_radar(request.result.position)
                if self.radar_result is None:
                    self._clear_radar_frame()
                self.radar_error = "Das Kartenbild konnte nicht angezeigt werden."
            if self._page_has_radar():
                self.draw()
        # Re-evaluate current state: obsolete resizes/locations never enqueue a backlog.
        self._queue_radar_render()

    def _last_radar_update_text(self) -> str:
        # Only a displayed, prepared image may advance the timestamp.
        if self._radar_frame is None or not self.canvas.find_withtag("radar-base"):
            return "Noch nicht aktualisiert"
        stamp = self._radar_frame.result.fetched_at.astimezone(self._display_zone())
        today = datetime.now(timezone.utc).astimezone(self._display_zone()).date()
        return stamp.strftime("%H:%M" if stamp.date() == today else "%d.%m.%Y %H:%M") + self._utc_suffix()

    def _draw_radar_info(self, width: int, height: int) -> None:
        scale = max(.8, min(width / 1024, height / 600))
        text = self._last_radar_update_text()
        font = (self._font_family, -max(14, round(16 * scale)))
        label = self.canvas.create_text(width/2, height-12, text=text, font=font,
            fill=TEXT, anchor="s", justify="center", tags=("radar-info", "radar-time"))
        box = self.canvas.bbox(label)
        background = self.canvas.create_rectangle(box[0]-7, box[1]-5, box[2]+7, box[3]+5,
            fill="#ffffff", outline="#b8b8b8", tags=("radar-info",))
        self.canvas.tag_lower(background, label)
        self._draw_radar_motion(width, height)

    def _draw_radar_location(self, width: int, height: int, name: str) -> None:
        c = self.canvas
        scale = max(.8, min(width / 1024, height / 600))
        cx, cy = width / 2, height / 2
        radius = min(14, 10 * scale)
        c.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                      fill="#f17647", outline="#ffffff", width=max(2, round(3 * scale)), tags=("radar-location",))
        label = c.create_text(cx, cy - radius - 12 * scale, text=name, anchor="s",
                              font=("Segoe UI", -max(12, round(16 * scale))), fill="#252b2c",
                              width=min(340 * scale, width - 40 * scale), justify="center",
                              tags=("radar-place-label",))
        left, top, right, bottom = c.bbox(label)
        left -= 10 * scale
        right += 10 * scale
        top -= 6 * scale
        bottom += 6 * scale
        r = 6 * scale
        background = c.create_polygon(
            left+r, top, right-r, top, right, top, right, top+r,
            right, bottom-r, right, bottom, right-r, bottom,
            left+r, bottom, left, bottom, left, bottom-r, left, top+r, left, top,
            smooth=True, splinesteps=18, fill="#ffffff", outline="",
            tags=("radar-place-label-background",))
        c.tag_lower(background, label)

    def draw_rain_map(self, width: int, height: int) -> None:
        c = self.canvas
        c.create_rectangle(0, 0, width, height, fill=BG, outline="", tags=("radar-background",))
        if self.mock_preview:
            self._map_notice(width, height, "DEMO / TESTANSICHT\nKartenabrufe sind deaktiviert.", centered=True)
            return
        position = self._map_position()
        if position is None:
            self._map_notice(width, height,
                             "Noch keine eindeutige Kartenposition.\nOrt und Land am Smartphone prüfen.", centered=True)
            return
        result = self.radar_result
        if result is not None and result.position != position:
            self._map_notice(width, height, "Karte für den gewählten Ort wird geladen …", centered=True)
            return
        if result is None:
            message = self.radar_error or "Regenkarte wird geladen …"
            self._map_notice(width, height, message, centered=True)
            return
        self._queue_radar_render()
        frame = self._radar_frame
        if (frame is None or frame.result.position != position or frame.epoch != self._radar_render_epoch
                or self.radar_photo is None or self.radar_overlay is None):
            self._map_notice(width, height, "Regenkarte wird vorbereitet …", centered=True)
            return
        if not frame.matches(self._current_radar_render()):
            now = datetime.now(timezone.utc)
            if any(not 0 <= (now - stamp).total_seconds() <= MAX_RADAR_CACHE_AGE
                   for stamp in (frame.result.observed_at, frame.result.fetched_at)):
                self._map_notice(width, height, "Regenkarte wird vorbereitet …", centered=True)
                return
        # The previous pair stays centered during a resize, without distorting either layer.
        offset_x, offset_y = (width - frame.size[0]) / 2, (height - frame.size[1]) / 2
        c.create_image(offset_x, offset_y, image=self.radar_photo, anchor="nw", tags=("radar-base",))
        c.create_image(offset_x, offset_y, image=self.radar_overlay, anchor="nw", tags=("radar-overlay",))
        self._draw_radar_location(width, height, position.name)
        if result.attribution:
            self._map_attribution(10, height - 59, result.attribution, width=width-20)
        notices = []
        if result.coverage_status != "full":
            notices.append("Keine Radarversorgung · schraffierte Flächen sind unbekannt" if result.coverage_status == "none"
                           else "Teilweise Radarversorgung · schraffierte Flächen sind unbekannt")
        age_minutes = (datetime.now(timezone.utc) - result.observed_at).total_seconds() / 60
        if result.stale:
            notices.append("Zwischengespeicherte Karte · Aktualisierung fehlgeschlagen")
        if age_minutes > 15:
            notices.append(f"Radarbild {age_minutes:.0f} Minuten alt")
        if result.warning and not result.stale:
            notices.append(result.warning)
        if self.radar_error and not self.radar_download_running:
            notices.append(self.radar_error)
        if notices:
            self._map_notice(width, height, "\n".join(dict.fromkeys(notices)))

    def _map_attribution(self, x, y, text, *, width=None):
        label = self.canvas.create_text(x+width/2 if width else x, y, anchor="n", justify="center", text=text, fill="#303640",
                    font=(self._font_family, -11), width=width or 0, tags=("map-attribution",))
        box = self.canvas.bbox(label)
        if box:
            background = self.canvas.create_rectangle(box[0]-3, box[1]-2, box[2]+3, box[3]+2,
                            fill="#ffffff", outline="", tags=("map-attribution",))
            self.canvas.tag_lower(background, label)

    def schedule_radar_refresh(self) -> None:
        if self._closed or self.mock_preview or self.radar_download_running:
            return
        if self.radar_refresh_job is not None or self._map_position() is None:
            return
        now = datetime.now(timezone.utc)
        self.radar_refresh_due = next_weather_refresh(now)
        delay = max(1, int((self.radar_refresh_due.timestamp() - now.timestamp()) * 1000 + .999))
        self.radar_refresh_job = self.root.after(delay, self._scheduled_radar_refresh)

    def _scheduled_radar_refresh(self) -> None:
        self.radar_refresh_job = None
        due, self.radar_refresh_due = self.radar_refresh_due, None
        if self._closed or self.mock_preview:
            return
        now = datetime.now(timezone.utc)
        if due is not None and now.timestamp() < due.timestamp():
            # A backwards clock adjustment must not cause an early request.
            self.radar_refresh_due = due
            delay = max(1, int((due.timestamp() - now.timestamp()) * 1000 + .999))
            self.radar_refresh_job = self.root.after(delay, self._scheduled_radar_refresh)
            return
        self.refresh_radar()

    def _retained_radar(self, position: MapPosition) -> RadarMapResult | None:
        """Keep a valid displayed map across failed refreshes after a resize."""
        previous = self.radar_result
        if previous is None or previous.position != position:
            return None
        now = datetime.now(timezone.utc)
        try:
            if any(stamp.tzinfo is None or not 0 <= (now - stamp).total_seconds() <= MAX_RADAR_CACHE_AGE
                   for stamp in (previous.observed_at, previous.fetched_at)):
                return None
        except (TypeError, AttributeError):
            return None
        return replace(previous, stale=True,
            warning="Aktualisierung fehlgeschlagen; letzte gültige Karte bleibt sichtbar (höchstens 60 Minuten alt).")

    def refresh_radar(self) -> None:
        if self._closed or self.mock_preview or self.radar_download_running:
            return
        if self.radar_refresh_job is not None:
            try:
                self.root.after_cancel(self.radar_refresh_job)
            except tk.TclError:
                pass
        self.radar_refresh_job = None
        self.radar_refresh_due = None
        position = self._map_position()
        if position is None:
            self.radar_error = "Karte benötigt eine eindeutige Ortsposition im gewählten Land aus dem Wetterabruf."
            if self._page_has_radar():
                self.draw()
            return
        width, height = RadarMapClient.image_size(self.canvas.winfo_width(), self.canvas.winfo_height())
        self.radar_requested_size = (width, height)
        self.radar_generation += 1
        generation = self.radar_generation
        query = normalize_query(self._weather_query())
        self.radar_download_running = True
        self.radar_error = "Regenkarte wird aktualisiert …"
        visible_map = self._page_has_radar() and any(
            item["type"] == "radar" and "map" in item["fields"]
            for item in self._current_page()["widgets"])
        if self._page_has_radar():
            self.draw()

        def download() -> None:
            try:
                if position.country == "DE":
                    result = self.radar_client.fetch(width, height, position)
                else:
                    result = self.radar_client.fetch(width, height, position, allow_basemap_download=visible_map)
                error = ""
            except RadarMapError as exc:
                result, error = None, str(exc)

            def finish() -> None:
                if self._closed:
                    return
                self.radar_download_running = False
                self.schedule_radar_refresh()
                if (generation != self.radar_generation or query != normalize_query(self._weather_query())
                        or position != self._map_position()):
                    if self._map_position() is not None:
                        self.root.after(10, self.refresh_radar)
                    return
                self.radar_result = result if result is not None else self._retained_radar(position)
                self.radar_error = error.replace("; kein gültiger Karten-Cache.", ".") if self.radar_result is not None else error
                if self.radar_result is not None:
                    self._queue_radar_motion(self.radar_result)
                self.draw()

            self._results.put(finish)

        def unexpected_failure() -> None:
            if self._closed:
                return
            self.radar_download_running = False
            self.schedule_radar_refresh()
            if generation == self.radar_generation:
                self.radar_result = self._retained_radar(position)
                self.radar_error = "Kartenaktualisierung unerwartet fehlgeschlagen; bitte später erneut versuchen."
                self.draw()
            elif self._map_position() is not None:
                self.root.after(10, self.refresh_radar)
        self._start_worker(download, unexpected_failure, "radar-map-download")


def main() -> None:
    from wetterstation.paths import project_root
    from wetterstation.lifecycle import AppSession
    project = project_root(__file__)
    if (project / ".pi-update-in-progress.json").exists():
        print("Unvollstaendiges Pi-Update. Bitte zuerst nach docs/UPDATE.md wiederherstellen.", file=sys.stderr)
        raise SystemExit(1)
    # Keep Tk's coordinates aligned with actual pixels on high-DPI Windows
    # displays so the preview scales to the visible window rather than past it.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    root.attributes("-fullscreen", True)
    demo = "--widget-demo" in sys.argv[1:]
    context = nullcontext(None)
    if demo:
        demo_parent = project / "private" / "widget-demo"
        demo_parent.mkdir(parents=True, exist_ok=True)
        context = tempfile.TemporaryDirectory(prefix="session-", dir=demo_parent, ignore_cleanup_errors=True)
    with context as folder, AppSession(project, root, None, sys.argv[1:]) as session:
        store = ApiKeyStore(path=Path(folder) / "settings.json") if folder else None
        preview = WeatherPreview(root, mock_preview="--mock-preview" in sys.argv[1:], widget_demo=demo, settings_store=store)
        session.preview = preview
        if "--show-rain-map" in sys.argv[1:]:
            preview.page = next((i for i,p in enumerate(preview.dashboard["pages"]) if any(w["type"] == "radar" for w in p["widgets"])), 0)
            preview.draw()
        if not preview.mock_preview or preview.widget_demo:
            root.after_idle(preview._maintain_mobile_connection)
            root.after_idle(preview._check_pairing)
        root.mainloop()


if __name__ == "__main__":
    main()

