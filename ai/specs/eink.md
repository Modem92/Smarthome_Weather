# E-Ink display (idea, not approved)

Status: noted on 26.10.2026. Display owned since 28.11.2026. No approval for implementation yet.

## Goal
Adapt the program to the "Waveshare 7.3inch E Ink Spectra 6 (E6) Full Color E-Paper Display" with 800 × 480 pixels (model and resolution as stated by the user). The PC preview and the 1024×600 LCD are kept.

## To be decided before implementation (interview)
- Scope of the display adaptation (layouts for 800×480, Spectra 6 color palette)
- Display driver (driver, library, connection to the Pi)
- Refresh behavior (refresh interval, partial/full refresh) and interplay with the five-minute grid
- Relation to the open questions about input buttons and the power-saving concept

## Hardware constraints (Waveshare precautions, given by the user on 28.11.2026)
The user now owns the display (28.11.2026); implementation is still not approved.
Why: violating these can permanently damage the panel (high voltage) or degrade the image.
- Refresh interval at least 180 s, and at least one refresh every 24 h. Consequence: the five-minute grid (300 s) fits; a per-minute clock or seconds display is not possible on E-Ink.
- Partial refresh (only on panels that support it) must be followed by a full refresh after a few cycles. Spectra 6 panels are expected to support full refresh only; verify against the datasheet.
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
