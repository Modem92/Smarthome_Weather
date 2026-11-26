"""Fixed-page widget display. Editing and layout persistence belong to the phone."""
from datetime import datetime, timezone
import tkinter as tk
import tkinter.font as tkfont

from wetterstation.ui.widgets import CATALOG, default_layout, revision, validate_layout
from wetterstation.maps.radar_render import RadarRenderRequest, prepare_radar_layers
from wetterstation.weather.weather_service import normalize_query
from wetterstation.weather.location_time import weather_zone

INK, SUBTLE, CARD, BACKGROUND = "#111111", "#404040", "#ffffff", "#ffffff"


def clock_text(field, fields, now=None):
    now = now or datetime.now(timezone.utc)
    if field == "time":
        return now.strftime("%H:%M:%S" if "seconds" in fields else "%H:%M")
    if field == "seconds":
        return now.strftime("%S")
    return f"{('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')[now.weekday()]}, {now:%d.%m.%Y}"


class DashboardMixin:
    def _init_dashboard(self):
        available = set(tkfont.families(self.root))
        self._font_family = next((name for name in ("Segoe UI", "DejaVu Sans", "Liberation Sans", "Arial")
                                  if name in available), "TkDefaultFont")
        try:
            self.dashboard = self.api_key_store.load_dashboard()
        except (OSError, ValueError):
            self.dashboard = default_layout()
            self.settings_load_error = True
        self._widget_map_cache = {}
        self._widget_map_source = None
        self._widget_map_active = False
        self._widget_map_wanted = []
        self._widget_errors = set()
        self.root.after(1000, self._tick_widgets)
        from wetterstation.designer.runtime import poll
        self.root.after(1000, lambda: poll(self))

    def _current_page(self):
        return self.dashboard["pages"][self.page % len(self.dashboard["pages"])]

    def _is_full_radar_page(self):
        items = self._current_page()["widgets"]
        return len(items) == 1 and items[0]["type"] == "radar" and items[0]["w"] == 12 and items[0]["h"] == 8 and "map" in items[0]["fields"]

    def _page_has_radar(self):
        return any(i["type"] == "radar" and i["fields"] for i in self._current_page()["widgets"])

    def _tick_widgets(self):
        if self._closed:
            return
        # Refitting is needed for changing digit widths and date rollover. Only redraw
        # clock contents, leaving prepared maps and other widgets untouched.
        if self.dashboard.get('version') not in (3,4) and not getattr(self, "_pairing_screen", None):
            for widget in self._current_page()["widgets"]:
                if widget["type"] in ("clock", "date") and widget["fields"]:
                    bounds = getattr(self, "_text_boxes", {}).get(widget["id"])
                    if bounds:
                        tokens=getattr(self,'_legacy_clock_tokens',None)
                        if tokens is None:self._legacy_clock_tokens={};tokens=self._legacy_clock_tokens
                        token=tuple(self._widget_lines(widget))
                        key=(self._current_page()['id'],widget['id'],bounds)
                        if tokens.get(key)==token:continue
                        tokens[key]=token
                        self.canvas.delete("clock-content-" + widget["id"])
                        self._draw_values(widget, *bounds)
        self.root.after(1000, self._tick_widgets)

    def _publish_dashboard(self, error=None):
        service = getattr(self, "mobile_service", None)
        if service:
            if self.dashboard.get('version') in (3,4) and error is None:
                ready=getattr(self,'_designer_runtime_key',None)
                if (not ready or ready[:2]!=(revision(self.dashboard),self._current_page()['id'])
                        or not self.canvas.find_withtag('designer-display')):
                    return  # Background preparation has not reached the display yet.
            service.publish_display(self._current_page()["id"], revision(self.dashboard), error,
                viewport=getattr(self, "_display_viewport", None))

    def _publish_to_new_service(self, service):
        ready=getattr(self,'_designer_runtime_key',None)
        current=revision(self.dashboard)
        if self.dashboard.get('version') in (3,4) and (not ready or ready[:2]!=(current,self._current_page()['id'])):
            current=None
        service.publish_display(self._current_page()["id"], current,
                                viewport=getattr(self, "_display_viewport", None))

    def _apply_mobile_dashboard(self, layout=None, page_id=None):
        if self._closed:
            return
        old_id = self._current_page()["id"]
        conflict = False
        try:
            self.dashboard = validate_layout(layout) if layout is not None else self.api_key_store.load_dashboard()
            if layout is not None:
                persisted = self.api_key_store.load_dashboard()
                if (self.dashboard.get('version') in (3,4) or persisted.get('version') in (3,4)) and revision(self.dashboard) != revision(persisted):
                    self.dashboard = persisted
                    conflict = True
        except (OSError, ValueError):
            self._publish_dashboard("Widget-Layout momentan nicht lesbar. Bitte neu laden.")
            return
        ids = [p["id"] for p in self.dashboard["pages"]]
        wanted = page_id or old_id
        self.page = ids.index(wanted) if wanted in ids else 0
        self.draw()
        self._publish_dashboard('Gestaltung wurde inzwischen geändert. Bitte den aktuellen Stand neu laden.' if conflict else None)

    def _show_mobile_page(self, page_id):
        if self._closed:
            return
        ids = [p["id"] for p in self.dashboard["pages"]]
        if page_id not in ids:
            self._publish_dashboard("Die gewählte Seite ist nicht mehr verfügbar.")
            return
        self.page = ids.index(page_id)
        self.draw()
        self._publish_dashboard()

    def _widget_text(self, x, y, text, width, size=14, color=INK, bold=False, tags=(), wrap=False, *, centered=True):
        font = tkfont.Font(root=self.root, family=self._font_family, size=-max(6, round(size*self.s)), weight="bold" if bold else "normal")
        text = str(text)
        limit = max(0, self.x(width)-2)
        if wrap:
            words, lines, line = text.split(), [], ""
            for word in words:
                trial = (line+" "+word).strip()
                if font.measure(trial) <= limit:
                    line = trial
                else:
                    lines.append(line)
                    line = word
            if line:
                lines.append(line)
            if len(lines) > 2:
                lines = [lines[0], " ".join(lines[1:])+"…"]
            for i, line in enumerate(lines):
                while line and font.measure(line) > limit:
                    line = line[:-2]+"…" if len(line)>2 else ""
                lines[i] = line
            text = "\n".join(lines)
        else:
            while text and font.measure(text) > limit:
                text = text[:-2]+"…" if len(text)>2 else ""
        return self.canvas.create_text(self.x(x+width/2 if centered else x), self.x(y),
            anchor="n" if centered else "nw", justify="center" if centered else "left", text=text,
            font=(self._font_family, font.cget("size"), font.cget("weight")), fill=color, width=limit if wrap else 0, tags=("widget-text", *tags))

    def draw_dashboard(self):
        if self.dashboard.get('version') in (3,4) and not getattr(self, '_pairing_screen', None):
            from wetterstation.designer.runtime import draw
            draw(self)
            return
        c = self.canvas
        w, h = max(1, c.winfo_width()), max(1, c.winfo_height())
        if w <= 1 or h <= 1:
            return
        self.page %= len(self.dashboard["pages"])
        c.delete("all")
        c.configure(bg=BACKGROUND, scrollregion=(0, 0, w, h))
        c.yview_moveto(0)
        self.scrollbar.pack_forget()
        self.content_offset_y = 0
        # Dashboard coordinates are native pixels. Geometry fills both axes;
        # glyphs themselves are never stretched with the window aspect ratio.
        self.s = 1
        scale = max(.5, min(w/1024, h/600))
        self._widget_border_width = max(2, 2*scale)
        margin, gap = 12*scale, max(6, 8*scale)
        top = 52*scale
        self._display_viewport = {"width": w, "height": h,
            "grid": {"x": margin, "y": top, "width": w-2*margin, "height": h-top-margin, "gap": gap}}
        self._text_boxes = {}
        page = self._current_page()
        if getattr(self, "_pairing_screen", None):
            self._draw_pairing_screen(w, h)
        elif self._is_full_radar_page():
            fields = page["widgets"][0]["fields"]
            self.draw_rain_map(w, h)
            if "place" not in fields:
                for tag in ("radar-location", "radar-place-label", "radar-place-label-background"):
                    c.delete(tag)
            if "updated" in fields:
                self._draw_radar_info(w, h)
            else:
                self._draw_radar_motion(w, h)
            border = self._widget_border_width
            self.canvas.create_rectangle(border/2, border/2, w-border/2, h-border/2,
                outline="#606060", width=border,
                tags=("widget-card", "widget-"+page["widgets"][0]["id"], "widget-frame"))
        else:
            self._widget_text(margin, 12*scale, page["title"],
                              w*.55-margin if self.mock_preview else w-2*margin, 22*scale, INK, True, centered=False)
            if self.mock_preview:
                badge = "WIDGET-DEMO · Beispieldaten" if self.widget_demo else "DEMO / MOCKDATEN"
                self._widget_text(w*.58, 16*scale, badge, w*.42-margin, 12*scale, INK, centered=False)
            self._dashboard_layout(margin, top, w-2*margin, h-top-margin, gap)
        self._publish_dashboard()
        if not self.mock_preview:
            self._queue_radar_render()
            self.schedule_radar_refresh()
            if (self._page_has_radar() and self.settings.country_code != "DE" and self.radar_result is None
                    and not self.radar_download_running and not getattr(self, "_international_visible", False)):
                self._international_visible = True
                self.root.after(10, self.refresh_radar)
            if not self._page_has_radar():
                self._international_visible = False

    def _draw_pairing_screen(self, width, height):
        pair = self._pairing_screen
        inset = max(16, min(width, height)*.06)
        rows = [("Mit dem Smartphone verbinden", 1, True, False, ()),
                (pair["label"]+(" · DEMO" if self.mock_preview else ""), .8, False, False, ()),
                (pair["code"], 2.6, True, False, ("pairing-code",)),
                ("Diesen Code am Smartphone eingeben.", .7, False, True, ()),
                (pair["url"], .65, False, False, ())]
        self._fit_rows(rows, inset, inset, width-2*inset, height-2*inset, centered=True)

    def _fit_rows(self, rows, x, y, width, height, *, centered=True):
        self._fit_columns([rows], x, y, width, height, centered=centered, cell_padding=1)

    def _fit_columns(self, columns, x, y, width, height, *, centered=True, cell_padding=None):
        """Fit unabridged text with common fonts and row centers across columns."""
        if not columns or not columns[0] or width <= 4 or height <= 4:
            return
        count, row_count = len(columns), len(columns[0])
        cw = width/count
        inset = min(8, max(3, cw*.06)) if cell_padding is None else cell_padding
        limit = cw-2*inset-2
        if limit <= 0:
            return
        fonts=getattr(self,'_fit_fonts',None)
        if fonts is None:self._fit_fonts={};fonts=self._fit_fonts
        if len(fonts)>256:fonts.clear()
        gap = min(10, height*.025)
        cache = getattr(self, '_font_measure_cache', None)
        if cache is None:self._font_measure_cache={};cache=self._font_measure_cache
        if len(cache)>4096:cache.clear()

        import sys
        quick = sys.platform=='linux' and self._font_family=='DejaVu Sans'

        def measure(row, size, exact=True):
            text, _weight, bold, wrap, _tags = row
            text = str(text)
            key = self._font_family, limit, text, size, bold, wrap, exact
            if key in cache:
                return cache[key]
            font=None
            if quick and not exact:
                try:
                    from wetterstation.designer.render import get_font
                    from types import SimpleNamespace
                    probe=get_font('Sans',size,bold)
                    font=SimpleNamespace(measure=probe.getlength)
                    line_height=sum(probe.getmetrics())
                except (OSError,AttributeError):pass
            if font is None:
                font_key=self._font_family,size,bold
                if font_key not in fonts:
                    instance=tkfont.Font(root=self.root,family=self._font_family,size=-size,weight='bold' if bold else 'normal')
                    fonts[font_key]=instance,instance.metrics('linespace')
                font,line_height=fonts[font_key]
            lines = [text]
            if wrap:
                lines, current = [], ""
                for word in text.split():
                    # Prefer complete words. The fit search reduces the font
                    # before ever splitting a long weather description mid-word.
                    if size > 1 and font.measure(word) > limit:
                        cache[key] = None
                        return None
                    trial = (current+" "+word).strip()
                    if current and font.measure(trial) > limit:
                        lines.append(current); current = word
                    else:
                        current = trial
                    while current and font.measure(current) > limit:
                        n = 1
                        while n < len(current) and font.measure(current[:n+1]) <= limit:
                            n += 1
                        lines.append(current[:n]); current = current[n:]
                if current:
                    lines.append(current)
                lines = lines or [""]
            result = ("\n".join(lines), line_height*len(lines)+2)
            if any(font.measure(line) > limit for line in lines):
                result = None
            cache[key] = result
            return result

        def layout(base,exact=True):
            fitted, heights = [], [0]*row_count
            for column in columns:
                items = []
                for index, row in enumerate(column):
                    size = max(1, int(base*row[1]))
                    measured = measure(row, size, exact)
                    if measured is None:
                        return None
                    text, row_height = measured
                    heights[index] = max(heights[index], row_height)
                    items.append((text, size, row[2], row[4]))
                fitted.append(items)
            total = sum(heights)+gap*(row_count-1)
            return (fitted, heights, total) if total <= height-2 else None

        low, high, best, best_base = 1, max(1, int(height)), None, 1
        while low <= high:
            base = (low+high)//2
            result = layout(base,exact=not quick)
            if result:
                best = result; best_base=base; low = base+1
            else:
                high = base-1
        if best is None:
            return
        if quick:
            # Pillow only narrows the search. Native Tk metrics decide every
            # displayed size, including wrapping and the largest fitting row.
            while best_base>=1:
                best=layout(best_base)
                if best is not None:break
                best_base-=1
            if best is None:return
            while best_base<int(height):
                candidate=layout(best_base+1)
                if candidate is None:break
                best=candidate;best_base+=1
        fitted, heights, total = best
        # A long secondary label cannot cap a short main value. Grow that row
        # consistently in every column using the height left by the whole table.
        for index, row in enumerate(columns[0]):
            if row[1] <= 1 or not row[2] or any("\n" in col[index][0] for col in fitted):
                continue
            old_height = heights[index]
            size = fitted[0][index][1]
            low, high, chosen = size, size+int(height-total)*2, None
            while low <= high:
                candidate = (low+high)//2
                measurements = [measure(col[index], candidate) for col in columns]
                new_height = max((m[1] for m in measurements if m is not None), default=0)
                if all(m is not None for m in measurements) and total-old_height+new_height <= height-2:
                    chosen = candidate, new_height, measurements
                    low = candidate+1
                else:
                    high = candidate-1
            if chosen:
                size, new_height, measurements = chosen
                total += new_height-old_height
                heights[index] = new_height
                for col, measured in zip(fitted, measurements):
                    col[index] = measured[0], size, col[index][2], col[index][3]
        top = y+(height-total)/2
        for number, column in enumerate(fitted):
            cy = top
            for index, (text, size, bold, tags) in enumerate(column):
                self.canvas.create_text(x+(number+.5)*cw if centered else x+number*cw+inset,
                    cy+heights[index]/2, text=text, anchor="center" if centered else "w", fill=INK,
                    font=(self._font_family, -size, "bold" if bold else "normal"),
                    justify="center" if centered else "left", tags=("widget-text", *tags))
                cy += heights[index]+gap

    def _draw_values(self, widget, x, y, width, height):
        rows = []
        lines = self._widget_lines(widget)
        main = bool(lines) and lines[0][1] in ("time", "temp", "value", "seconds") and widget["type"] != "description"
        for i, (value, field) in enumerate(lines):
            tags = ("widget-content-"+widget["id"],)
            if widget["type"] in ("clock", "date"):
                tags += ("clock-content-"+widget["id"], f"clock-{widget['id']}-{field}")
            rows.append((value, 2.4 if main and i == 0 else 1, main and i == 0,
                field in ("date", "description") or not (main and i == 0), tags))
        self._fit_rows(rows, x, y, width, height)

    def _widget_lines(self, widget):
        kind, fields, r = widget["type"], widget["fields"], self.weather_record
        fields = [f for f in CATALOG[kind]["fields"] if f in fields]
        if kind == "clock":
            return [(self._clock_text(f,fields),f) for f in fields if f!="seconds" or "time" not in fields]
        if kind == "date":
            return [(self._clock_text("date",[]),"date")] if fields else []
        weather = {"temp":f"{r.temp:.1f} °C" if r else "—", "description":r.description if r else "Noch keine Wetterdaten",
            "feels_like":f"Gefühlt {r.feels_like:.1f} °C" if r else "—", "humidity":f"Luftfeuchte {r.humidity} %" if r else "—",
            "wind":f"Wind {r.wind_speed:.1f} m/s" if r else "—", "pressure":f"Luftdruck {r.pressure} hPa" if r else "—"}
        sensors = {"temp":"16,8 °C","humidity":"Luftfeuchte 64 %","pressure":"Luftdruck 1012 hPa","wind":"Wind 3,2 m/s"}
        if kind in ("weather","metrics"):
            values=weather
        elif kind in ("sensors","indoor"):
            values=sensors if kind=="sensors" else dict(sensors,temp="21,5 °C",humidity="Luftfeuchte 45 %")
        elif kind.startswith("sensor_"):
            values={"value":sensors[kind.removeprefix("sensor_")]}
        else:
            values={"value":weather[kind]}
        if kind not in ("weather", "metrics", "sensors", "indoor"):
            values = {key: value.removeprefix("Luftfeuchte ").removeprefix("Luftdruck ").removeprefix("Wind ").removeprefix("Gefühlt ") for key, value in values.items()}
        return [(values[f],f) for f in fields]

    def _dashboard_layout(self, x, y, width, height, gap=8):
        desired = []
        for widget in self._current_page()["widgets"]:
            wx, wy = x+widget["x"]*(width+gap)/12, y+widget["y"]*(height+gap)/8
            ww, wh = widget["w"]*(width+gap)/12-gap, widget["h"]*(height+gap)/8-gap
            pad = max(self._widget_border_width+3, min(14, max(5, min(ww, wh)*.065)))
            before = set(self.canvas.find_all())
            self.rr(wx, wy, wx+ww, wy+wh, min(14, wh*.12), CARD, "#606060",
                    border_width=self._widget_border_width)
            for item in set(self.canvas.find_all())-before:
                self.canvas.addtag_withtag("widget-card", item)
                self.canvas.addtag_withtag("widget-"+widget["id"], item)
            fields, kind = widget["fields"], widget["type"]
            if not fields:
                continue
            title_size = min(18, max(10, wh*.085))
            title_height = title_size*1.5
            self._widget_text(wx+pad, wy+pad, CATALOG[kind]["title"], ww-2*pad, title_size, SUBTLE, True)
            content = (wx+pad, wy+pad+title_height, ww-2*pad, wh-2*pad-title_height)
            if kind in ("hourly", "daily"):
                self._widget_forecast(widget, *content)
            elif kind == "radar":
                request = self._widget_radar(widget, *content)
                if request:
                    desired.append(request)
            else:
                demo = kind in ("indoor", "sensors") or kind.startswith("sensor_")
                cx, cy, cw, ch = content
                if demo:
                    demo_size = min(12, max(7, wh*.06))
                    ch -= demo_size*1.6
                    self._widget_text(cx, wy+wh-pad-demo_size*1.3, "DEMO · keine Sensoren verbunden", cw, demo_size, INK)
                self._text_boxes[widget["id"]] = (cx, cy, cw, ch)
                self._draw_values(widget, cx, cy, cw, ch)
            for item in set(self.canvas.find_all())-before:
                self.canvas.addtag_withtag("widget-content-"+widget["id"], item)
        self._widget_map_wanted = desired
        self._prepare_widget_maps()
        if not self._current_page()["widgets"]:
            self._fit_rows([("Dein Dashboard ist leer.", 1.4, True, True, ()),
                ("Füge am Handy dein erstes Widget hinzu.", 1, False, True, ())], x+20, y+20, width-40, height-40)

    def _widget_forecast(self, widget, x, y, width, height):
        hourly = widget["type"] == "hourly"
        entries = getattr(self.forecast_record, "hourly" if hourly else "daily", ()) if self.forecast_record else ()
        if not entries:
            self._fit_rows([("Noch keine Vorhersage", 1, False, True, ())], x, y, width, height)
            return
        fields = [f for f in CATALOG[widget["type"]]["fields"] if f in widget["fields"]]
        count = len(entries)
        cw = width/count
        for index in range(1, count):
            px = x+index*cw
            self.canvas.create_line(px, y+2, px, y+height-2, fill="#808080",
                width=max(1, self._widget_border_width/2),
                tags=("forecast-separator", "forecast-separator-"+widget["id"]))
        columns = []
        for index, entry in enumerate(entries):
            dt = datetime.fromisoformat(entry.timestamp).astimezone(self._display_zone())
            heading = dt.strftime("%H:%M") if hourly else f"{('Mo','Di','Mi','Do','Fr','Sa','So')[dt.weekday()]} {dt:%d.%m.}"
            if not weather_zone(self.weather_record, self.forecast_record)[1]:
                heading += " UTC"
            values = {"temp": f"{entry.temp:.0f}°" if hourly else f"{entry.temp_max:.0f}° / {entry.temp_min:.0f}°" if entry.temp_max is not None and entry.temp_min is not None else "—",
                "rain": f"Regen {entry.precipitation_probability:.0%}", "description": entry.description, "wind": f"Wind {entry.wind_speed:.1f} m/s"}
            cell_tag = f"forecast-column-{widget['id']}-{index}"
            items = [(heading, .85, False, False, ("forecast-heading", cell_tag, "forecast-field-heading"))]
            items += [(values[f], 1.8 if f == "temp" else 1, f == "temp", f != "temp",
                       (cell_tag, "forecast-field-"+f)) for f in fields]
            columns.append(items)
        self._fit_columns(columns, x, y, width, height)

    def _widget_radar(self,widget,x,y,width,height):
        fields,result=widget["fields"],self.radar_result
        position=self._map_position() if not self.mock_preview else None
        valid=result is not None and position==result.position and all(0<=(datetime.now(timezone.utc)-stamp).total_seconds()<=3600 for stamp in (result.fetched_at,result.observed_at))
        size=(max(1,round(self.x(width))),max(1,round(self.x(height-23 if "updated" in fields else height))))
        key=(id(result),size,self._radar_render_epoch)
        photos=self._widget_map_cache.get(key) if self._widget_map_source is result else None
        if "map" in fields:
            if valid and photos:
                for photo in photos:
                    self.canvas.create_image(self.x(x),self.x(y),image=photo,anchor="nw",tags=("widget-map",))
            else:
                message="DEMO · Kartenabrufe deaktiviert" if self.mock_preview else "Karte wird vorbereitet …" if valid else self.radar_error or "Noch keine aktuelle Karte"
                if key in self._widget_errors:
                    message="Karte konnte nicht vorbereitet werden"
                self._widget_text(x,y+28,message,width,12,SUBTLE,wrap=True)
        if "place" in fields:
            name=position.name if position else self.settings.location
            label=self._widget_text(x+8,y+7,name,width-16,13,INK,True)
            if "map" in fields and valid and photos:
                box=self.canvas.bbox(label)
                background=self.canvas.create_rectangle(box[0]-5,box[1]-3,box[2]+5,box[3]+3,fill="#ffffff",outline="")
                self.canvas.tag_lower(background,label)
                cx,cy=self.x(x)+size[0]/2,self.x(y)+size[1]/2
                self.canvas.create_oval(cx-6,cy-6,cx+6,cy+6,fill="#f17647",outline="#ffffff",width=2)
        if "map" in fields and valid and photos:
            self._widget_motion(result,size,x,y)
            if result.attribution:
                # Attribution and coverage cannot be disabled through widget field choices.
                self._map_attribution(self.x(x+5), self.x(y)+size[1]-30, result.attribution, width=size[0]-10)
            if result.coverage_status != "full":
                self._widget_text(x+6,y+30,"Keine Radarversorgung" if result.coverage_status == "none" else "Teilweise Radarversorgung",width-12,12,"#865725")
        if "updated" in fields:
            stamp=result.fetched_at.astimezone(self._display_zone()).strftime("%d.%m. %H:%M") if valid and (photos or "map" not in fields) else "Noch nicht aktualisiert"
            if valid and not weather_zone(self.weather_record, self.forecast_record)[1]:
                stamp += " UTC"
            notices=[]
            if valid and photos:
                if result.stale:
                    notices.append("zwischengespeichert")
                if (datetime.now(timezone.utc)-result.observed_at).total_seconds()>900:
                    notices.append("Radar älter als 15 Min.")
                if result.warning or (self.radar_error and not self.radar_download_running):
                    notices.append("Aktualisierung eingeschränkt")
            self._widget_text(x,y+height-17," · ".join([stamp,*notices]),width,11,SUBTLE)
        elif "map" in fields and valid and photos and (result.stale or (datetime.now(timezone.utc)-result.observed_at).total_seconds()>900 or result.warning or (self.radar_error and not self.radar_download_running)):
            label=self._widget_text(x+6,y+height-20,"Zwischengespeichert / Aktualisierung eingeschränkt",width-12,11,"#865725")
            box=self.canvas.bbox(label)
            background=self.canvas.create_rectangle(box[0]-4,box[1]-2,box[2]+4,box[3]+2,fill="#fffaf1",outline="")
            self.canvas.tag_lower(background,label)
        return (key,size) if valid and "map" in fields else None

    def _widget_motion(self,result,size,x,y):
        from wetterstation.maps.radar_motion import fresh_source,project_vectors
        motion=self._radar_motion
        if not motion or motion.source is not result or result.stale or not fresh_source(result):
            return
        protected=((size[0]/2-20,size[1]/2-20,size[0]/2+20,size[1]/2+20),(0,0,size[0],30),(0,size[1]-30,size[0],size[1]))
        for vector in project_vectors(motion,size,protected=protected):
            # Same geographic crop as the prepared layers. Arrows stay in the widget.
            sx,sy,ex,ey=vector
            self.canvas.create_line(self.x(x)+sx,self.x(y)+sy,self.x(x)+ex,self.x(y)+ey,fill="#4b5359",width=2,arrow="last",tags=("widget-motion",))

    def _prepare_widget_maps(self):
        result=self.radar_result
        if self._widget_map_source is not result:
            self._widget_map_source,self._widget_map_cache,self._widget_errors=result,{},set()
        wanted=dict(self._widget_map_wanted)
        # Keep a bounded set through page switches, including failed keys.
        if len(self._widget_map_cache)>24:
            self._widget_map_cache={k:v for k,v in self._widget_map_cache.items() if k in wanted}
        missing=[(k,s) for k,s in wanted.items() if k not in self._widget_map_cache]
        if not missing or self._widget_map_active or self.mock_preview:
            return
        self._widget_map_active=True
        query,epoch=normalize_query(self._weather_query()),self._radar_render_epoch
        def finish(prepared):
            self._widget_map_active=False
            if self._closed:
                return
            if result is self.radar_result and epoch==self._radar_render_epoch:
                for key,data in prepared:
                    try:
                        self._widget_map_cache[key]=tuple(tk.PhotoImage(master=self.root,data=d,format="png") for d in data) if data else None
                    except Exception:
                        self._widget_map_cache[key]=None
                    if self._widget_map_cache[key] is None:
                        self._widget_errors.add(key)
            self.draw()
        def work():
            prepared=[]
            for key,size in missing:
                try:
                    data=prepare_radar_layers(RadarRenderRequest(result,size,query,epoch))
                except Exception:
                    data=None
                prepared.append((key,data))
            self._results.put(lambda:finish(prepared))
        self._start_worker(work,lambda:finish([(k,None) for k,s in missing]),"widget-map-prepare")
