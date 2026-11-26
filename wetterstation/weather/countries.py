"""Offline ISO 3166-1 country catalogue and explicit location identities."""
import json
import re
from pathlib import Path

COUNTRIES = json.loads(Path(__file__).with_name("countries.json").read_text(encoding="utf-8"))
_NAMES = {str(value).casefold(): code for code, row in COUNTRIES.items()
          for value in (code, row["name"], row["english"])}
_NAMES.update({"usa": "US", "uk": "GB", "großbritannien": "GB", "england": "GB",
               "vereinigte staaten von amerika": "US", "türkei": "TR"})


def country_code(value):
    return _NAMES.get(value.strip().casefold(), "") if isinstance(value, str) else ""


def require_country(value):
    code = country_code(value)
    if not code:
        raise ValueError("Bitte ein Land aus der Länderauswahl wählen.")
    return code


def legacy_country(location):
    """Old unsuffixed German places stay German; unknown country suffixes need input."""
    tail = location.rsplit(",", 1)[-1].strip()
    code = country_code(tail)
    if code:
        return code
    return "DE" if "," not in location or re.fullmatch(r"\d{5}", tail) else ""


def location_query(location, code):
    code = require_country(code)
    parts = [part.strip() for part in location.split(",") if part.strip()]
    if len(parts) > 1 and country_code(parts[-1]):
        parts.pop()
    if not parts:
        raise ValueError("Bitte einen Ort oder eine Postleitzahl eingeben.")
    return ", ".join(parts + [code])


def split_query(query):
    parts = [part.strip() for part in query.split(",") if part.strip()]
    code = country_code(parts[-1]) if len(parts) > 1 else ""
    if not code:
        raise ValueError("Bitte zuerst ein Land auswählen.")
    return ", ".join(parts[:-1]), code
