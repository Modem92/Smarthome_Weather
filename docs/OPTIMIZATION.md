# Optimization of 28 Oct 2026

## Final result

Final version installed on the Pi: `2026-10-28-optimization-174804`, SHA-256
`<internal checksum>`.
389 tests passed on the frozen state. The widget demo was restarted in an orderly
way. User acceptance: "Everything fits, and it also runs smoothly."

| Measurement | Before | Final |
|---|---:|---:|
| CPU, 10-second demo sample, one core | 21.1 % | 1.1 % |
| Disk write bytes in this sample | 65,536 | 0 |
| RSS of the same demo | 45,324 KiB | 66,328 KiB |
| Overview, first computation | 4,031 ms | 1,163 ms |
| Overview, median of three repetitions | 3,927 ms | 84 ms |
| Forecast, first computation | 3,691 ms | 524 ms |
| Forecast, median of three repetitions | 3,640 ms | 65 ms |
| Sensor page, first computation | 859 ms | 293 ms |
| Sensor page, median of three repetitions | 474 ms | 73 ms |

The rain demo page stayed at roughly 10–14 ms. The render values come from
the identical separate 1024×600 test with standard demo data and include
the Tk preparation, not the complete physical display latency. The
memory increase is the price for reused font/rendering data.
The samples are not a long-term measurement. No live operation was started for these
tests; external weather requests were blocked by the render probe.
The states of a real phone browser were not remotely monitored in the process measurement.
Browser idle pause, resume, no transmission while
dragging and exactly one afterwards were demonstrated separately with isolated browser/timing checks;
operation on the Pi was additionally confirmed by the user.

The existing saved Pi layout has the same SHA-256 value before and after the takeover.
The demo stays open. Final backup:
`~/wetterstation/Wetterstation-Backups/<timestamp>`.
The known working state before the first optimization also remains
backed up in `~/wetterstation/Wetterstation-Backups/<timestamp>`.
The first state with the failed start is explicitly under
`archive/failed-start-packages`, not among the two current checked packages.

After cleanup and new check evidence, build contains about 7.9 MiB/109 files
instead of about 341 MiB/5,186 files. Old evidence was kept compressed, not
deleted without replacement. The additional archives still use OneDrive storage.
The following sections document the approach and interim states chronologically.

## Checked structure

The shared codebase, compatibility entry points, tests and recovery paths
are kept. Personal settings, drafts, layouts, certificates,
caches and budget identities were not changed by the cleanup.

The PC designer runtime was copied completely and byte-identically to
`%USERPROFILE%/AppData/Local/Wetterstation/designer-runtime`. An isolated
Qt start succeeded. Starter and Qt check use `tools/dev_paths.py`;
the old search path remains as a fallback for workstations not yet converted.
The local substitute runtime was removed after checksum and process checks.
New frozen check copies are likewise located outside OneDrive.

Known old check outputs are fully backed up, with content checksums, in
`archive/optimization-20261028T165303357535Z.zip`.
Windows write protection caused an abort on the first removal; the second
run checked the remaining files against the same archive and continued.
Unknown leftover folders are kept. The additional project plan is in the archive
byte-identically; its differing sections have been merged into `ai/DECISIONS.md`.

Check mode: `python tools/workspace_maintenance.py`. Only `--apply` changes anything.
The options `--resume-archive` and `--retire-runtime` support the secured
continuation. `--prune-packages` keeps the two newest content-checked packages
and moves older ones with checksums to `archive/retired-pi-packages`.

## Runtime and operation

- HTTPS stays reachable; when idle, the server waits with a 500 ms check interval
  instead of 100 ms. An incoming socket is processed immediately.
- Browser polling pauses after 60 seconds without interaction, when the tab is hidden,
  or on loss of focus. Before further changes, the display state is checked.
  A differing revision blocks editing, but not reload/sign-out.
- Moving, collision preview and resizing run in the browser. Nothing is saved
  while dragging, and exactly once after release.
  Visible content, colors and fonts are edited in the PC designer.
- Sessions, one-time codes, and TLS, origin and CSRF protection are kept.
- The runtime file is written only on a state change. Stop requests
  are still checked regularly, unchanged. Without a pending login there is no
  login timer; pending codes get targeted expiry times.
- Legacy displays use reusable font instances and measurements;
  unchanged clock texts are not recomputed.
- Designed pages are prepared by a single background job.
  Only the current job may be adopted on the Tk display. Tk images
  stay in the main thread. Confirmation happens only after actual display
  with valid geometry. Page and widget caches are each limited to 16 MiB.

## Acceptance and limits

The first local full check consisted of 386 Python tests. Subsequent
fixes and additional regressions are checked again by the final
frozen acceptance. The reports under
`build/reports/` and `build/checks/designer-acceptance.json` are authoritative.
Normal arrangement, multi-browser sign-in and design-format browser checks as well as
18 PC designer UI checks passed with dummy data and no external requests.

Before the takeover, the Pi was checked read-only: old program state without
designer runtime, existing layout format 2. The widget demo started by the user
used, in a 10-second sample, 21.1 % of one CPU core,
45,324 KiB RSS and 522 write system calls. Write system calls include
socket communication as well and are not equivalent to SD card writes.

A separate invisible test with temporary standard demo data on the same
Pi gave, before the optimization, roughly 4.03/3.93 seconds for the overview and
3.69/3.64 seconds for the forecast (first computation/median of three repetitions).
It does not change the running demo and blocks provider calls. This test
measures computation including Tk preparation, not the complete physical
display latency. The raw evidence is under `build/reports/pi-*-before*.json`.

Secured takeover and the after-measurement follow only after the frozen
offline acceptance. A PC test result is not a Pi performance proof. Weather grid,
budget protection, local time and source attribution are unchanged.

The first takeover passed installation but could not start the demo:
Debian provides `PIL.ImageTk` as an optional separate package, which is missing on this
Pi. The fix uses the existing Tkinter with PNG transfer as a fallback,
without package installation. It is explicitly checked without ImageTk for color content, size
and transparency; the Pi pre-check now also imports the display path.
On closing, image jobs are ended and Tk resources are released in the main thread.
The renewed frozen state is checked completely offline before a corrected takeover.
The original demo is to be restored afterwards; no switch to live operation.

The corrected version was then accepted with 388 tests, installed
successfully and the original widget demo restarted. In the same
10-second sample, CPU usage fell from 21.1 to 1.6 % of one core;
disk write bytes from 65,536 to 0, RSS rose from 45,324 to 50,864 KiB.
The existing Pi layout remained unchanged by SHA-256. Repeated synthetic
page computation fell to roughly 87 ms (overview) and 64 ms (forecast).

The first computation initially stayed too slow at 2.69 and 1.38 seconds.
A further Linux optimization narrows the font size search using the bundled
DejaVu fonts; the final line breaks, sizes and limits are
still checked with actual Tk metrics. A separate test of this
additional code in the Pi's memory gave 1.18 and 0.53 seconds for first
computations and unchanged roughly 86/65 ms for repetitions. Before installing
this addition as well, the complete frozen acceptance follows again.
