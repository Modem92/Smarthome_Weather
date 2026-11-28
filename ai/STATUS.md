# Status
## Phase und Ziel (phase and goal)
- Public version on GitHub since 26.11.2026. Functional state 28.10.2026: display, phone pairing, international locations, designer and optimization accepted offline (389 tests); Pi set up for live operation.
- Goal now: finish open live and device checks, then robustness.

## Nächste Schritte (next steps)
1. Offline suite is green on Windows (389 tests, Python 3.15 in `%LOCALAPPDATA%/Smarthome_Weather/venv`). Still open in #8: the Linux/Xvfb anomalies; then CI (#12, blocked by #8).
2. Approval-dependent acceptance: extra time series and design transfer (#1), live restart (#3), international live test (#4).
3. Device checks: SSH after Windows restart (#2), desktop icon (#6), autostart/long-term operation (#5).
4. Cleanup: Pi libraries vs. requirements.txt (#9), Pi target in the updater (#10), leftover doc references (#11), double-click crash on another PC (#7).

## Offene Probleme / Fragen an mich (open problems / questions)
- Input buttons, power-saving concept and E-Ink connection (draft spec: ai/specs/eink.md) are undecided. E-Ink display is now owned (28.11.2026); Waveshare hardware constraints are in the spec; clear/storage desktop tool on the Pi (`raspberry_pi/eink_maintenance.py`), first run on the device still open; weather station on E-Ink not approved.
- OpenWeather account limit of 1000/day is only per the user's statement, never independently verified.
- Sensors (hardware, protocol) and long-term data storage: no solution chosen.
- Ideas without approval: automatic page switching (optional), highlighting unusual readings, data analysis, cloud/ML.

## Zuletzt erledigt (recently done, max. 5 lines)
- 27.11.2026: leak guard (pre-commit hook + gitignored denylist) and gitignored CLAUDE.local.md with device/location facts; repo and history audited clean.
- 27.11.2026: settings.json and part A synced with template (merge approval, CI rule). main protected by ruleset (PR only, squash). Repo switched to English (docs, ai/, issues, starter names; UI stays German).
- 27.11.2026: workflow template introduced, planning docs moved into CLAUDE.md and ai/, 11 issues created.
- 28.10.2026: optimization for Pi and OneDrive, designer fixes.
