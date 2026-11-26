"""Small in-memory view of the shared, project-persisted display settings."""

from dataclasses import dataclass
from wetterstation.weather.countries import location_query


@dataclass
class DisplaySettings:
    """Display settings loaded from and saved to project-private configuration."""

    location: str = "Potsdam, 14467, Deutschland"
    country_code: str = "DE"

    @property
    def query(self) -> str:
        return location_query(self.location, self.country_code)

    def set_location(self, value: str) -> bool:
        """Normalize and store a non-empty place name; return False if empty."""
        normalized = " ".join(value.split())
        if not normalized:
            return False
        self.location = normalized[:80]
        return True
