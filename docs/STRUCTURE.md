# Structure and development

## One program, two startup environments

`wetterstation/ui` contains the Tk display and widgets, `weather` the weather/location logic,
`maps` the map processing, `storage` settings and budget protection, and `mobile`
the phone interface including web files. `paths.py` determines the unchanged
project folder centrally; moving modules does not change any private storage path.

Windows starters are under `windows`, Pi starters under `raspberry_pi`.
`tools/pi/update.py` stays runnable with the standard library alone, so that
backup and restore also work from the Pi intermediate folder.
`tools/pi/controller.py` controls only explicitly started update operations.
`tools/legacy` contains the earlier one-time key/counter migration; it is not an update path.

The root files `app.py`, `pi_update.py`, `pi_preflight.py` and the old starters are
compatibility entry points. There is no second copy of the program logic.
Pi package format 2 contains an explicit file list. During the conversion,
only named old program files are removed after backup. Unknown files are kept.

## Runtime and tests

The optimization and the check mode for secured cleanup are described in
[OPTIMIZATION.md](OPTIMIZATION.md). The designer runtime and new
frozen check working copies are located outside OneDrive. Only checked packages and
acceptance reports are kept in the project. Shared resolution: `tools/dev_paths.py`.

Use Python >=3.11 with Tkinter and the libraries from `requirements.txt`.
Windows first looks for a local environment under `%LOCALAPPDATA%/Smarthome_Weather/venv`
(older setups: `%LOCALAPPDATA%/Wetterstation/venv`),
then the existing bundled runtime, and then Python via `py` or PATH.
Nothing is installed automatically. Keep virtual environments outside OneDrive.
`python -m wetterstation --widget-demo` starts a labeled demo.

`python tools/offline_tests.py` runs all automated Python/Tk/HTTPS tests
with external connections blocked. Start Windows multi-process tests from this saved
file, not via PowerShell standard input.

For browser acceptance, start `python tests/widget_demo.py` as an isolated local HTTPS server;
then, with an existing Node/Playwright environment, run
`node tests/widget_browser_check.cjs` and `node tests/pairing_browser_check.cjs`.
The browser checks block external page access. `tests/international_visual_check.py`
and `tests/international_browser_check.cjs` similarly check international sample data.
`tests/display_visual_check.py` generates synthetic display images. The outputs are
under `build/checks/`; personal settings are not changed.

## GitHub and local project data

Source code, tests, documentation, package definition and line-ending settings are prepared for a
shared repository. `private`, `build`, `archive`, old `transfer` folders,
Python caches, environments and runtime identifiers are excluded.
Before the first commit, check the actually intended file selection for confidential content.
Before an upload, additionally check the complete Git history.
The public repository contains a checked source state with a neutral sample configuration.

OneDrive may synchronize the entire folder, including the unencrypted settings.
The exclusion from Git does not change that. Set the project folder on
this PC to "Immer auf diesem Gerät behalten" (Always keep on this device). Do not work at the same time on several
computers in the same synchronized Git working folder.
With regular GitHub use, use your own local working copies outside OneDrive.

The backup from before the reorganization is under `archive/before-restructure-*/workspace.zip`.
It also contains confidential files and the previous Git state. Old transfer packages
are under `archive/transfer-*`. Archives are not deleted automatically.
