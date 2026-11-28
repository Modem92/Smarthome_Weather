# Decisions (newest first)

Carried over on 27.11.2026 from PROJEKTPLAN.md, AGENTS.md, the old CLAUDE.md and docs/ (original wording in the Git history, commit `bbc838e`).

## 2026-11-28: Keep Python/Tk for 24/7 operation, optimise the platform instead
- Decision: no rewrite in another language. Resource work targets (1) the display: E-Ink without backlight, rendered with Pillow straight to the panel so the Pi can run without a desktop session; (2) idle wakeups of the display process (#18); (3) a long-term RSS/CPU/SD-write measurement on the Pi as part of #5.
- Why: measured idle cost of the app is ~1 % of one core and ~66 MB RSS (docs/OPTIMIZATION.md) on a 512 MB Pi 3 A+; the power draw is dominated by the board itself, the LCD backlight and the desktop session, not by the interpreter. Python matches the Waveshare driver (Python) and keeps one codebase for PC and Pi with 389 tests. A rewrite would save a few tens of MB and well under 1 W·h/day while risking layout compatibility.
- Rejected: Rust/Go/C rewrite (8,000+ lines plus tests, PC designer and phone editor share the model; saving negligible); MicroPython/microcontroller (no Tk/Pillow/HTTPS pairing as built); Qt on the Pi (heavier than Tk).
- Status: valid

## 2026-11-28: E-Ink maintenance tool standalone, not in the Pi package
- Decision: `raspberry_pi/eink_maintenance.py` is copied by hand to `~/eink-tools/` on the Pi with two desktop launchers ("E-Ink löschen", "E-Ink einlagern"); it is not listed in `FILES` of `tools/pi/update.py`. It uses the Waveshare driver from the user's `~/e-Paper` clone. Each clear pass is init → full refresh → deep sleep (power off), passes wait ≥180 s apart (timestamp persisted across runs and written before the refresh starts), the first pass always waits the full 180 s (another program may have refreshed without a timestamp), and the tool refuses to run, or aborts before the next pass, while another process holds `/dev/spidev0.0` or the "E-Ink Bilderrahmen" program runs. If `sleep()` fails, `epdconfig.module_exit()` switches the HAT off; SIGTERM/SIGHUP (shutdown, closed terminal) are turned into Ctrl+C so cleanup always runs.
- Why: the user asked for a desktop tool now; E-Ink in the weather station is not approved, and the tool must work independently of the program folder (e.g. during a broken update). Waveshare recommends "clear several times" but also ≥180 s between refreshes; the user made the 3-minute rule mandatory, so safety wins over speed. Sleeping between passes keeps the panel off high voltage during the waits.
- Rejected: shipping via the updater (would tie a hardware tool to the weather package and need a full update run); clearing back-to-back without pause (violates the 3-minute rule); vendoring the Waveshare driver (licence/maintenance, already present on the Pi).
- Status: valid

## 2026-11-27: Private facts in CLAUDE.local.md, pre-commit leak guard
- Decision: real Pi target, location and private file locations go into gitignored `CLAUDE.local.md` (auto-loaded by Claude Code). A versioned pre-commit hook (`tools/git-hooks/pre-commit`, activated via `core.hooksPath`) runs `tools/check_private_leaks.py`, which blocks added lines and file names containing values from the gitignored `private/leak-denylist.txt` plus key/location/Pi target read from the live `private/*.json` (`dir:` line). Hits print file:line and source, never the value. Without a denylist (other clones, CI) the check passes with a warning.
- Why: the user had these facts in a plaintext desktop file and wants sessions to use them without ever publishing them (public repo). Reading the key from settings.json avoids a second plaintext copy; the denylist itself stays private because the values are private.
- Rejected: committing the denylist hashed (substring matching on hashes is impractical); a Claude-only hook (would miss the user's own commits); CI check (CI has no access to the private values).
- Status: valid

## 2026-11-27: Development venv at `%LOCALAPPDATA%/Smarthome_Weather/venv`
- Decision: Windows starters look there first, then at the old `%LOCALAPPDATA%/Wetterstation/venv`, then bundled runtime, `py`, PATH. Budget root and designer runtime stay under `Wetterstation`.
- Why: user named the folder after the repo. The old path stays as fallback so existing PCs keep working; the budget identity must not move (see stable `private/` path decision).
- Rejected: moving the whole `Wetterstation` folder (would change the budget identity).
- Status: valid

## 2026-11-27: Ruleset "Protect main" on GitHub
- Decision: main only changes via pull request (no required approval), no force-push, no deletion, squash merge only; branches are deleted after merge. CI as a required check follows with #12.
- Why: user request; matches part A (never push to main, never force-push). No required approval because Claude merges its own PRs (part A) and GitHub does not let the author approve.
- Rejected: required approval (would block merging by Claude); classic branch protection (rulesets are the current GitHub mechanism).
- Status: valid

## 2026-11-27: Repository language English, UI stays German
- Decision: docs, ai/, CLAUDE.md part B, GitHub issues and Windows starter file names are English (`Start weather station.cmd`, `Design weather station.cmd`, `Widget demo.cmd`, `Update Pi.cmd`, `Set up SSH once.cmd`). UI texts on display, phone and designer stay German. Section headings of CLAUDE.md part B and ai/STATUS.md stay German (with English gloss in STATUS) because part A refers to them by name.
- Why: user request, matching the workflow rule "code, comments, commits in English"; the users of the device read German.
- Rejected: translating UI texts too (not wanted); keeping German starter names (user accepted that existing shortcuts break).
- Status: valid

## 2026-11-27: Planning docs moved into CLAUDE.md and ai/, old files deleted
- Why: 13 files with duplicated and partly contradictory states. Future sessions need one source for stable facts (CLAUDE.md), current state (ai/STATUS.md) and reasons (here).
- Rejected: keeping the files marked as "historical" (because they would still be maintained twice). The deleted Pi docs are listed in `RETIRED_FILES` so they are also removed on the Pi at the next update.
- Status: valid

## 2026-11-26: Public GitHub repo with a cleaned-up version
- Why: user request. Device-specific values, private data and the old local Git history stay local; example location Potsdam.
- Rejected: private repo with Codex Cloud (idea from 24.10., never approved).
- Status: valid

## 2026-10-28: Optimization for Pi and OneDrive
- Why: on 26.10. the user reported CPU spikes and multi-second stuttering on the first page switch on the Pi. Requirement: measure first, then decide; do not abolish the phone connection in advance.
- Implementation: the browser computes drag/scale locally and sends only after the gesture is finished; polling pause after 60 s of inactivity; server idle 500 ms; image preparation in the background, adopted only in the Tk main thread; image cache limited; designer runtime and check copies outside OneDrive.
- Higher memory use is accepted (price for reused font/rendering data). ImageTk failure: fall back to native Tk PNG instead of new system packages.
- Status: valid (measurements in docs/OPTIMIZATION.md)

## 2026-10-28: Securing designer operation
- Why: accidental value changes and data loss.
- Mouse wheel locked on input fields; protected data blocks cannot be deleted; invalid input keeps the last valid draft.
- Status: valid

## 2026-10-27: Graphical designer, design format 4
- Why: the user wants to design widgets themselves, without code or AI.
- Format 4 adds freely editable content blocks, widgets keep their type and data binding; formats 2 and 3 are read losslessly; incompatible Pi programs must not accept designs.
- Qt (PySide6) only on the PC, Tk on the Pi (the Pi gets no Qt dependency); shared Pillow renderer.
- Phone changes are limited arrangement operations with version check, so the PC design is never replaced. Import/export without keys and counters.
- Rejected: extended design editor on the phone (user: PC application is enough).
- Status: valid

## 2026-10-27: Additional time series only after per-device approval
- Why: a copied design must not trigger additional requests. Base supply (3 requests/5 min) and 24 reserve requests take priority.
- Open proposal from the spec: minute rain every 30 min, quarter-hour weather every 60 min.
- Status: valid

## 2026-10-26: Update window with clear states
- Why: the user took the indeterminate progress bar after success for a hang. Running, success and error must be distinguishable at once.
- Status: valid

## 2026-10-25: Shared program core and manual double-click updater
- Why: the folder was to be organized by core, starters, tools, tests and docs without moving private data or the budget identity → `paths.py` determines the existing project folder.
- Updater: test and package a frozen state offline, upload it completely, then stop the running app in an orderly way, back up, install, verify; restart only if it was running before, in the previous mode. Pi layout and private data are kept.
- `tools/pi/update.py` uses only the standard library, so recovery works from the Pi staging folder. Recovery does not reset counters, caches or certificates (no budget rollback).
- SSH key outside OneDrive in the Windows key service; registration by script via stdin (PowerShell 5.1 stripped embedded quotation marks).
- Process check inspects only possible weather station processes (`/proc/…/cwd` of foreign processes was not readable).
- Rejected: automatic updates, updater autostart, schedules, operating system/library updates.
- Status: valid

## 2026-10-24: Passive display, operation via phone pairing
- Why: the user wants a calm display without local buttons and fields.
- Each browser requests its own one-time code, which appears only on the display; valid for 2 minutes, max. 4 waiting requests, 8 sessions until logout or restart, all in memory only. TLS, secure cookies, host/origin check, CSRF protection and attempt limits remain.
- Replaces: local settings dialogs, manual phone activation, 20-minute sessions, "connection stays active after closing the dialog" (18.10.).
- Status: valid

## 2026-10-24: HTTPS only on a real home-network IPv4
- Why: on the Pi the user was shown a `127…` address. Read the active interfaces, never loopback or wildcard; without a home-network address, no start.
- Rejected: firewall/router changes, automatic certificate trust, public exposure.
- Status: valid

## 2026-10-24: International locations, local time and map
- Why: user request; replaces the restriction to Germany from 18.10.
- Location and ISO country are stored together; geocoding limited to the country; weather/location cache separated by location and country, late results discarded (same-named places must not share data).
- Clock and calendar in the weather location's local time, labeled UTC if the time zone is unknown.
- Germany: BKG/DWD. Abroad: OSM + RainViewer at fixed zoom 7, only needed tiles, HTTP cache (≥ 7 days if no freshness is given), application identifier, no prefetching. Coverage mask: missing radar is never shown as dry. Sources always visible on international maps (OSM license requirement).
- Rain-movement arrows only for DWD.
- Status: valid

## 2026-10-24: Widget pages
- 12×8 grid per page, 1–12 pages, four start pages; saving right after each gesture (no apply button), 20 undo steps; on collision the last valid arrangement stays.
- The device switches pages only manually; automatic switching is just an idea.
- Status: valid

## 2026-10-24: Forecasts in a single row, content centered
- Eight hours and five days each in one row of equally wide columns; separator lines only between forecast columns; widget frame 2 px at 1024×600, scaling.
- Status: valid

## 2026-10-23: One Call 4.0 on a fixed five-minute grid, limit 1000
- Why: by the user's own statement they set the One Call subscription to 1000/day (account not verified by us).
- 3 requests per run (`current`, `timeline/1h`, `timeline/1day`) at fixed German-time slots; manual fetches do not shift the grid; no catch-up burst after standby; never follow `next`/`prev` pagination.
- Limit 1000 per German calendar day and per UTC provider day, without resetting counter history. Replaces the earlier limit of 999.
- The rain map uses the same grid; replaces the 5/15-minute cycle and the reload on page switch.
- Status: valid

## 2026-10-23: Map style after image reference
- Light colored BKG street map, soft transparent DWD radar areas; location name and orange-white marker above the radar.
- Replaces: DOP20 aerial image (until 18.10.) and gray base map (18.–23.10.). Rejected: relief map with contour lines, separate label layer, legend.
- Source line on the German map hidden at the user's request; sources and licenses are in the README. A legal exemption is not confirmed by this.
- Status: valid

## 2026-10-23: Rain movement from two DWD images
- At most 3 subtle, static arrows; direction only, no speed, legend or surface-wind substitute. Correlation ≥ 0.85 and 120 km/h serve only as plausibility filters. The map appears without waiting for the analysis.
- Status: valid

## 2026-10-23: Image preparation in the background
- Why: every draw decoded both PNGs (366.9 ms → 0.20 ms).
- Reuse finished image pairs; Tk images only in the UI thread; at most one preparation plus one current follow-up job; discard outdated jobs after a location/size change.
- Status: valid

## 2026-10-19: Display size 1024×600
- Start in fullscreen, F11 switches to windowed; size changes trigger no fetches.
- Status: valid

## 2026-10-18: Error handling and backoff
- 401/403: pause until the key is changed. 429: all endpoints wait `Retry-After` (min. 60 s, otherwise 15 min). Network/5xx: only the affected endpoint, 60 s to 30 min.
- Weather cache max. 6 h, radar fallback max. 60 min. Operation is reliably released after errors.
- Status: valid

## 2026-10-18: Local budget counter, fail-closed
- Why: reserve before every HTTP fetch so that no crash makes fetches uncountable. Additionally a UTC provider day, because otherwise usage beyond the provider limit could be allowed. If the prior daily usage is unknown (initial setup), block.
- Counter per device, because OneDrive provides no cross-device atomic counting → PC live and Pi live never at the same time.
- The starter sets `WETTERSTATION_BUDGET_ROOT` only for its own process (a redirected AppData path led to a different counter). Rejected: global environment variable.
- Status: valid

## 2026-10-18: Settings and key under `private/` in the project
- Why: explicit user wish; same project-relative path on all PCs; OneDrive may sync the folder including the unencrypted file. `private/` is Git-ignored.
- Rejected: environment variable for the key, storage in the user folder (old device keys migrated once, never overwritten).
- A stored key does not enable live fetches.
- Status: valid

## 2026-10-18: Development principles
- First on the Windows PC with a virtual display, Python as the base; Pi with power supply (more frugal options open); existing LCD before E-Ink.
- First a functional skeleton; the final UI is designed by the user.
- Within approved features the technical implementation is free; new features and account actions are not.
- Status: valid
