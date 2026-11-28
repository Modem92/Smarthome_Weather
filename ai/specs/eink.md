# E-Ink display (idea, not approved)

Status: noted on 26.10.2026. Display owned since 28.11.2026. No approval for implementation yet.

## Goal
Adapt the program to the "Waveshare 7.3inch E Ink Spectra 6 (E6) Full Color E-Paper Display" with 800 × 480 pixels (model and resolution as stated by the user). The PC preview and the 1024×600 LCD are kept.

## To be decided before implementation (interview)
- Scope of the display adaptation (layouts for 800×480, Spectra 6 color palette)
- Display driver (driver, library, connection to the Pi)
- Refresh behavior (refresh interval, partial/full refresh) and interplay with the five-minute grid
- Relation to the open questions about input buttons and the power-saving concept
- Resource hint (24/7 requirement): with E-Ink, render with Pillow directly to the panel and run the Pi without a desktop session (no X/Wayland, no Tk window); this saves more RAM/power than any language change (see DECISIONS.md, 28.11.2026).

## Hardware constraints (Waveshare precautions, given by the user on 28.11.2026)
The user now owns the display (28.11.2026): Waveshare 7.3inch e-Paper HAT (E), 800×480, on the Raspberry Pi 3 Model A+. Waveshare driver `epd7in3e` is in the user's clone `~/e-Paper` on the Pi (not part of our package). Implementation in the weather station is still not approved.
Why: violating these can permanently damage the panel (high voltage) or degrade the image.
- MUST: at least 3 minutes (180 s) between two refreshes, and at least one refresh every 24 h (user's explicit requirement). Consequence: the five-minute grid (300 s) fits; a per-minute clock or seconds display is not possible on E-Ink.
- No partial refresh on this panel (confirmed by the user); every update is a full refresh (~20–30 s).
- Another program of the user ("E-Ink Bilderrahmen", `~/EInk-Bilderrahmen`) drives the same panel; never run two display programs at once.
- Maintenance tool: `raspberry_pi/eink_maintenance.py` (clear N times / prepare for storage), launchers on the Pi desktop.
- Never leave the panel powered/high-voltage between refreshes: after every refresh put it into sleep mode or power it off. After sleep, image data is ignored until the panel is initialised again (driver must re-init before each refresh).
- Clear the screen before long storage or long unused periods; clear several times before first use. Multi-color batches may differ slightly in color.
- Border color via register 0x3C or 0x50 (datasheet). Wrong image output: check width/height settings first.
- Supply 3.3 V; driver board V2.1+ also accepts 5 V (check the version printed under the board name).
- FPC cable and glass are fragile: no bending along the vertical axis or toward the front, no repeated bending; fixed wiring during development.
- Start with the Waveshare sample program on the Pi to verify the hardware before integrating our own driver.

## Out of scope
- Hardware purchase, sensors, changes to the budget or fetch grid

## Substeps, done criteria, end-to-end check
Fill in only after approval and interview.
