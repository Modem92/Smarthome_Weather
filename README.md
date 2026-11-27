# Weather station

Shared Python program for Windows and Raspberry Pi. Display, weather services,
rain map and the protected phone interface all use the same program version.
The user interface is German.

## Starting

- **Design on the PC:** `windows/Design weather station.cmd` opens the separate
  configurator with sample data. Two tabs for arrangement and advanced design;
  eight resize handles, directly movable content blocks and a shared inner grid.
  The phone editor remains usable for arrangement. Guide and acceptance status:
  [Designer](docs/DESIGNER.md). Additional time series require explicit
  activation per device under **Datenquellen** (data sources) or in the Pi transfer dialog.
  The configurator itself does not request any weather data.

- **Windows:** `windows/Start weather station.cmd` starts normal operation.
  While the Pi uses the same budget identity live, use only
  **`windows/Widget demo.cmd`** with clearly labelled sample data on the PC.
- **Update the Pi:** run `windows/Set up SSH once.cmd` once, then double-click
  **`windows/Update Pi.cmd`**. The updater only starts manually.
- **Pi:** existing desktop icon or `sh start_pi_live.sh` in the Pi project folder.
  `sh start_pi_widget_demo.sh` uses separate temporary sample data.

On the first update to the new structure, close the old Pi weather station yourself
once. Later updates shut down a running new version in an orderly way and restart
the same demo/live mode. A closed application stays closed.
A restart in live mode can trigger regular weather and map requests.

## Folders

| Folder | Content |
|---|---|
| `windows/` | Double-click starters and one-time SSH setup |
| `raspberry_pi/` | Linux starters |
| `wetterstation/` | Shared program core, grouped by task |
| `tools/` | Offline checks, update/backup tools, historical migration |
| `tests/` | Automated tests, browser and display checks |
| `docs/` | Current guides and labelled history |
| `build/` | Generated packages, isolated check images and reports; not in Git |
| `archive/` | Complete confidential backup and old transfer packages; not in Git |
| `private/` | Unchanged settings, keys, certificates, caches and counters; not in Git |

The few starters in the root folder remain as redirects for existing
shortcuts. Program code lives in the corresponding subfolders.

## Guides and checks

- [Folder cleanup, resources and browser idle mode](docs/OPTIMIZATION.md)
- [Pi update and recovery](docs/UPDATE.md)
- [Structure and development](docs/STRUCTURE.md)
- [Designer](docs/DESIGNER.md)
- Decisions with reasons and current status (repository only, not on the Pi):
  [ai/DECISIONS.md](ai/DECISIONS.md), [ai/STATUS.md](ai/STATUS.md)

Python 3.11 or newer with Tkinter is required. `requirements.txt` and
`pyproject.toml` describe the development libraries. The existing Pi installation
is checked functionally; updates do not install libraries or operating system packages.

Isolated offline tests: `python tools/offline_tests.py`. External Python connections
are blocked; local HTTPS tests use dummy data. Browser checks are described
separately and need an installed browser with Playwright.

This public version uses Potsdam as the sample location. Your own settings
are stored locally under `private/`. The widget demo uses sample data.

## Data sources and licences

- **Base map Germany:** [basemap.de WMS](https://sgx.geodatenzentrum.de/wms_basemapde?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.1.1),
  layer `de_basemapde_web_raster_farbe`. Licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/),
  attribution "© GeoBasis-DE / BKG 2026 · CC BY 4.0"; [terms of use](https://basemap.de/produkte-und-dienste/web-raster/).
- **Radar Germany:** [DWD WMS](https://maps.dwd.de/geoserver/wms?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0)
  (WN radar composite), attribution "Datenbasis: Deutscher Wetterdienst"; see
  [DWD geo services](https://www.dwd.de/DE/leistungen/geodienste/help/nutzung_geodienste.html?lsbId=621762)
  and [WN product sheet](https://www.dwd.de/DE/leistungen/radarprodukte/radarkomposit_wn_hdf5.pdf?__blob=publicationFile&v=4).
- **Outside Germany:** tiles from OpenStreetMap ([contributors and licence](https://www.openstreetmap.org/copyright),
  [tile usage policy](https://operations.osmfoundation.org/policies/tiles/)) and radar from
  [RainViewer](https://www.rainviewer.com/api/weather-maps-api.html). International maps always show
  "© OpenStreetMap-Mitwirkende · RainViewer". The client identifies itself as `WetterstationPreview/2.0`,
  uses the HTTP cache (at least seven days without freshness information) and loads only the needed tiles at zoom 7.
- **Weather:** [OpenWeather One Call 4.0](https://openweathermap.org/api/one-call-4) and
  [Geocoding](https://openweathermap.org/api/geocoding-api) with your own key.

At the user's request, the attribution line of the German map is hidden on the display; the details
are listed here. This does not confirm an exception from the terms of use.
