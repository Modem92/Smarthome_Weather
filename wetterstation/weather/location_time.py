"""Weather-place civil time, independent of refresh and budget clocks."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def weather_zone(weather=None, forecast=None):
    for record in (weather, forecast):
        if record:
            try:
                return ZoneInfo(record.timezone), True
            except (ZoneInfoNotFoundError, ValueError, TypeError):
                pass
    return timezone.utc, False


def local_now(weather=None, forecast=None):
    zone, known = weather_zone(weather, forecast)
    return datetime.now(timezone.utc).astimezone(zone), known
