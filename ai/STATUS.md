# Status
## Phase and goal
- Public version on GitHub since 26.11.2026. Functional state 28.10.2026: display, phone pairing, international locations, designer and optimization accepted offline (389 tests); Pi set up for live operation.
- Goal now: finish open live and device checks, then robustness.

## Next steps
1. Make the offline test suite run on this PC and get it green (issue #8). Python is currently missing on the Windows PC.
2. Approval-dependent acceptance: extra time series and design transfer (#1), live restart (#3), international live test (#4).
3. Device checks: SSH after Windows restart (#2), desktop icon (#6), autostart/long-term operation (#5).
4. Cleanup: Pi libraries vs. requirements.txt (#9), Pi target in the updater (#10), leftover doc references (#11), double-click crash on another PC (#7).

## Open problems / questions for the user
- Input buttons, power-saving concept and E-Ink connection (draft spec: ai/specs/eink.md) are undecided.
- OpenWeather account limit of 1000/day is only per the user's statement, never independently verified.
- Sensors (hardware, protocol) and long-term data storage: no solution chosen.
- Ideas without approval: automatic page switching (optional), highlighting unusual readings, data analysis, cloud/ML.

## Recently done (max. 5 lines)
- 27.11.2026: repo switched to English (docs, ai/, issues, starter names; UI stays German), CLAUDE.md part A synced with template.
- 27.11.2026: workflow template introduced, planning docs moved into CLAUDE.md and ai/, 11 issues created.
- 28.10.2026: optimization for Pi and OneDrive, designer fixes.
