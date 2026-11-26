"""Versioned, bounded widget pages and deterministic collision-free placement."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

COLUMNS, ROWS, MAX_PAGES, MAX_WIDGETS = 12, 8, 12, 16


def spec(title, fields, width=4, height=3, minimum=(3, 2)):
    return {"title": title, "fields": dict(fields), "width": width, "height": height,
            "min_width": minimum[0], "min_height": minimum[1]}


CATALOG = {
    "clock": spec("Uhrzeit", [("time", "Uhrzeit"), ("date", "Datum"), ("seconds", "Sekunden")]),
    "date": spec("Datum", [("value", "Datum")]),
    "weather": spec("Draußen · Wetter", [("temp", "Temperatur"), ("description", "Wetterlage"), ("feels_like", "Gefühlte Temperatur"), ("humidity", "Luftfeuchte"), ("wind", "Wind"), ("pressure", "Luftdruck")], minimum=(4, 3)),
    "temp": spec("Temperatur", [("value", "Temperatur")]),
    "feels_like": spec("Gefühlte Temperatur", [("value", "Gefühlte Temperatur")]),
    "description": spec("Wetterlage", [("value", "Wetterlage")]),
    "humidity": spec("Luftfeuchte", [("value", "Luftfeuchte")]),
    "wind": spec("Wind", [("value", "Windgeschwindigkeit")]),
    "pressure": spec("Luftdruck", [("value", "Luftdruck")]),
    "metrics": spec("Wetterdetails", [("humidity", "Luftfeuchte"), ("wind", "Wind"), ("pressure", "Luftdruck")]),
    "hourly": spec("Nächste 8 Stunden", [("temp", "Temperatur"), ("description", "Wetterlage"), ("rain", "Regenwahrscheinlichkeit"), ("wind", "Wind")], 12, 4, (6, 4)),
    "daily": spec("Nächste 5 Tage", [("temp", "Höchst-/Tiefsttemperatur"), ("description", "Wetterlage"), ("rain", "Regenwahrscheinlichkeit"), ("wind", "Wind")], 12, 4, (6, 4)),
    "radar": spec("Regenkarte", [("map", "Kartenbild"), ("place", "Ortsname / Marker"), ("updated", "Abrufzeit")], 12, 8, (6, 4)),
    "sensors": spec("Eigene Sensoren · Demo", [("temp", "Außentemperatur"), ("humidity", "Luftfeuchte"), ("pressure", "Luftdruck"), ("wind", "Windgeschwindigkeit")], 4, 4, (3, 3)),
    "indoor": spec("Drinnen · Demo", [("temp", "Temperatur"), ("humidity", "Luftfeuchte")]),
}
for _key, _title in (("temp", "Außentemperatur"), ("humidity", "Luftfeuchte"), ("pressure", "Luftdruck"), ("wind", "Windgeschwindigkeit")):
    CATALOG["sensor_"+_key] = spec(_title+" · Demo", [("value", _title)], 6, 4)


class LayoutConflict(ValueError):
    pass


class NoSpace(ValueError):
    pass


def new_widget(kind, identity, x=0, y=0, *, w=None, h=None):
    item = CATALOG[kind]
    fields = list(item["fields"])
    if kind == "clock":
        fields.remove("seconds")
    if kind == "weather":
        fields = ["temp", "description", "humidity"]
    if kind in ("hourly", "daily"):
        fields = ["temp", "rain"]
    return {"id": identity, "type": kind, "x": x, "y": y,
            "w": item["width"] if w is None else w, "h": item["height"] if h is None else h, "fields": fields}


def default_layout():
    return {"version": 2, "pages": [
        {"id": "overview", "title": "Wetterübersicht", "widgets": [new_widget("clock", "clock"), new_widget("weather", "weather", 4), new_widget("metrics", "metrics", 8), new_widget("hourly", "overview-hourly", 0, 3, h=5)]},
        {"id": "forecast", "title": "Vorhersage", "widgets": [new_widget("hourly", "hourly"), new_widget("daily", "daily", 0, 4)]},
        {"id": "rain", "title": "Regenkarte", "widgets": [new_widget("radar", "radar")]},
        {"id": "sensors", "title": "Sensoren", "widgets": [new_widget("sensor_"+kind, "sensor-"+kind, (i%2)*6, (i//2)*4) for i, kind in enumerate(("temp", "humidity", "pressure", "wind"))]},
    ]}


def overlaps(a, b):
    return a["x"] < b["x"]+b["w"] and b["x"] < a["x"]+a["w"] and a["y"] < b["y"]+b["h"] and b["y"] < a["y"]+a["h"]


def _identity(value, seen):
    if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}", value) or value in seen:
        raise ValueError("Ungültige oder doppelte Kennung.")
    seen.add(value)


def validate_layout(value, *, collisions=True):
    if isinstance(value, dict) and value.get('version') in (3,4):
        from wetterstation.designer.model import validate
        return validate(value, collisions=collisions)
    if not isinstance(value, dict) or set(value) != {"version", "pages"} or type(value["version"]) is not int or value["version"] != 2:
        raise ValueError("Ungültiges Widget-Layout.")
    pages = value["pages"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise ValueError("Eine bis zwölf Seiten sind möglich.")
    page_ids, widget_ids = set(), set()
    for page in pages:
        if not isinstance(page, dict) or set(page) != {"id", "title", "widgets"}:
            raise ValueError("Ungültige Seite.")
        _identity(page["id"], page_ids)
        title, items = page["title"], page["widgets"]
        if not isinstance(title, str) or not title.strip() or len(title) > 40 or any(ord(c) < 32 for c in title):
            raise ValueError("Ungültiger Seitenname.")
        if not isinstance(items, list) or len(items) > MAX_WIDGETS:
            raise ValueError("Zu viele Widgets auf einer Seite.")
        for i, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"id", "type", "x", "y", "w", "h", "fields"}:
                raise ValueError("Ungültiges Widget.")
            _identity(item["id"], widget_ids)
            kind = item["type"]
            if not isinstance(kind, str) or kind not in CATALOG:
                raise ValueError("Unbekanntes Widget.")
            meta = CATALOG[kind]
            if any(type(item[k]) is not int for k in ("x", "y", "w", "h")):
                raise ValueError("Ungültige Widget-Größe.")
            if not (meta["min_width"] <= item["w"] <= COLUMNS and meta["min_height"] <= item["h"] <= ROWS and 0 <= item["x"] <= COLUMNS-item["w"] and 0 <= item["y"] <= ROWS-item["h"]):
                raise ValueError("Das Widget liegt außerhalb des Rasters oder ist zu klein.")
            fields = item["fields"]
            if not isinstance(fields, list) or any(not isinstance(f, str) or f not in meta["fields"] for f in fields) or len(fields) != len(set(fields)):
                raise ValueError("Ungültige Widget-Inhalte.")
            if collisions and any(overlaps(item, other) for other in items[:i]):
                raise NoSpace("Widgets überlappen sich.")
    return deepcopy(value)


def arrange_page(items, pinned=None, compact=False):
    """Bounded backtracking preserves the moved item and prefers old positions."""
    result = deepcopy(items)
    if sum(i["w"]*i["h"] for i in items) > COLUMNS*ROWS:
        raise NoSpace("Auf dieser Seite ist kein Platz.")
    order = sorted(result, key=lambda i: (i["id"] != pinned, -i["w"]*i["h"], i["y"], i["x"]))
    attempts, failed = 0, set()
    def solve(index, occupied):
        nonlocal attempts
        attempts += 1
        if attempts > 50000:
            return False
        if index == len(order):
            return True
        state = (index, occupied)
        if state in failed:
            return False
        item = order[index]
        positions = [(x,y) for y in range(ROWS-item["h"]+1) for x in range(COLUMNS-item["w"]+1)]
        if item["id"] == pinned:
            positions = [(item["x"],item["y"])]
        elif not compact:
            positions.sort(key=lambda p: (p != (item["x"],item["y"]), abs(p[0]-item["x"])+abs(p[1]-item["y"]), p[1],p[0]))
        for x,y in positions:
            if x < 0 or y < 0 or x+item["w"] > COLUMNS or y+item["h"] > ROWS:
                continue
            mask = sum(((1<<item["w"])-1) << (r*COLUMNS+x) for r in range(y,y+item["h"]))
            if not occupied & mask:
                item.update(x=x, y=y)
                if solve(index+1, occupied | mask):
                    return True
        failed.add(state)
        return False
    if not solve(0,0):
        raise NoSpace("Auf dieser Seite ist kein Platz.")
    return result


def arrange_layout(value, pinned=None, compact=False):
    result = validate_layout(value, collisions=False)
    for page in result["pages"]:
        page["widgets"] = arrange_page(page["widgets"], pinned, compact)
    return validate_layout(result)


def load_layout(value):
    if isinstance(value, dict) and value.get('version') in (3,4):
        return validate_layout(value)
    if value is None:
        return default_layout()
    if isinstance(value, dict) and value.get("version") == 1 and isinstance(value.get("widgets"), list):
        # Preserve an early single-page draft without writing or dropping widgets.
        result = {"version": 2, "pages": [{"id": "migrated", "title": "Meine Widgets", "widgets": []}]}
        for old in value["widgets"]:
            item = deepcopy(old)
            if not isinstance(item, dict) or set(item) != {"id", "type", "x", "y", "w", "h", "fields"} or not isinstance(item.get("type"), str) or item["type"] not in CATALOG:
                raise ValueError("Ungültiger alter Widget-Entwurf.")
            if any(type(item.get(k)) is not int for k in ("w", "h", "x", "y")):
                raise ValueError("Ungültige Größe im alten Widget-Entwurf.")
            meta = CATALOG[item["type"]]
            item["w"] = max(meta["min_width"], min(COLUMNS, item["w"]))
            item["h"] = max(meta["min_height"], min(ROWS, item["h"]))
            item["x"], item["y"] = min(max(0,item["x"]),COLUMNS-item["w"]), min(max(0,item["y"]),ROWS-item["h"])
            validate_layout({"version": 2, "pages": [{"id": "legacy", "title": "Entwurf", "widgets": [item]}]})
            page = result["pages"][-1]
            try:
                page["widgets"] = arrange_page(page["widgets"]+[item])
            except NoSpace:
                result["pages"].append({"id": "migrated-"+str(len(result["pages"])), "title": "Weitere Widgets", "widgets": [dict(item,x=0,y=0)]})
        return validate_layout(result)
    return validate_layout(value)


def revision(layout):
    return hashlib.sha256(json.dumps(layout, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
