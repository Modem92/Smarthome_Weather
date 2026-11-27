# Weather station designer

## Assignment of 27.10.2026

The basis was the plan agreed in chat, "Weather station designer with PC design
and phone arrangement", including its graphical extension. Both are
implemented; the architecture decisions are in `ai/DECISIONS.md`, and the
original wording is in the Git history (commit `bbc838e`).
The implementation is local and offline;
new real weather requests and the first transfer to the Pi must be accepted separately.

## Acceptance checklist

- [x] PC: two tabs, shared draft, selection, multi-editing, keyboard,
  context menus, 100 undo/redo steps, adjustable sidebars, light/dark.
- [x] Grid 1–128 per axis, exact positions/sizes, locking, no overlap,
  lossless grid suggestions and an explicitly automatic arrangement.
- [x] Profiles 1024×600, 800×480, custom dimensions, separate landscape/portrait
  variants, output 0/90/180/270 degrees.
- [x] Styles: fills/images/gradients, transparency, borders/sides/dashing,
  individual corner radii including zero, shadows, spacing, alignments.
- [x] Content: custom texts, images, shapes, data bindings, free positioning,
  rotation/layers, font import, formats, units, global inheritance/overrides.
- [x] Save, transfer and reset templates/styles/grids; images/fonts
  in the key-free import/export package.
- [x] Additional live connection with explicit device activation: minute/
  15-minute values within the normal weather cycle; transport and switches verified offline.
- [x] Time-series acceptance with simulated responses: minute/15-minute/hourly/daily values, free selection,
  cards/table/line/bars, gaps/DST, no interpolation.
- [x] Offline budget check for additional requests: regular 3/5-minute requests preserved, both budget days,
  24 reserve requests, pagination limits, shared caches, no HTTP while designing.
- [x] Phone: existing functions, variable active grid, targeted changes,
  preservation of all details, version conflicts, direct display confirmation.
- [x] Drafts automatic, crash recovery, explicit apply, old
  layouts preserved, protection of settings/keys/budget.
- [x] Pi transfer simulated in isolation: existing SSH, compatibility, staging/assets, backup, atomic
  switch, confirmation, conflicts/connection loss, a closed app stays closed.
- [x] Offline tests and visual/usability acceptance including 100/150/200 %.

## Limits

No hardware drivers, historical measurement archives, new accounts, publication
or changes to the existing location/key management. Qt is only needed on the PC.

## Current status

The configurator and the explicitly approved live connection are
implemented. Additional requests are switched off by default. Only a
confirmed activation on the respective device allows them in normal live operation.
Development and acceptance use simulated responses exclusively;
new real weather requests and the first real transfer to the Pi are still outstanding.

## Starting and using it

Double-click `windows/Design weather station.cmd`. The configurator works
with clearly marked sample data and starts no phone server or
weather request. It opens the active design as a draft or restores the most recently
auto-saved draft. The active display only changes via **Anwenden → Am PC anwenden**
(Apply → Apply on this PC) or **An Pi übertragen** (Transfer to Pi).

1. **Widgets anordnen** (arrange widgets): Choose a page, drag a widget, or enter width/height and cell
   on the right. Change the grid size and check the suggestion. Red outlines
   mark overlaps; these must be fixed before applying. The
   eight handles on the selected widget resize it at its corners and sides.
2. **Erweiterte Gestaltung** (advanced design): Select a widget or content item. At the top right, switch between
   display, page, widget and content. Search for settings, expand
   groups and change values. Blue property names mark individual deviations;
   the reset arrow reverts to the parent default.
3. **Arrange content directly:** Click and drag titles, values, images and shapes;
   resize them with the eight handles. In this tab the whole widget is moved
   by its frame. An ordinary weather widget keeps its type
   and its data bindings. A card, chart or table remains a content block.
   The content list on the left helps with overlapping elements. Ctrl+click selects several
   content items of the same widget; "Ausrichten" (align) offers text alignment as well as, separately,
   positioning and even distribution of content areas.
4. **Landscape/portrait:** Choose the profile at the top. The arrangements stay
   separate. The additional output rotation accounts for how the display is mounted;
   it does not change any operating system setting.

Under **Innenraster** (inner grid) a shared cell spacing applies to all widgets, initially
8 logical display pixels, adjustable from 1 to 128. The origin lies within
the widget padding. Display and snapping can be switched separately; **Alt**
suspends snapping while dragging. Existing content is not moved by
a grid change. The inner grid appears only in the editor.
When a widget is enlarged, content positions and areas grow proportionally;
text follows its existing automatic size adjustment.
The position lock protects the outer widget frame; its content
remains editable.

During a movement the preview shows the result together with guide lines and
position/size readout. **Escape** discards the movement in progress. Only on
release is a single combined undo step created; invalid widget positions
keep the last valid state. Number fields are updated after the movement.

Graphical content changes and inner grid settings use **format 4**.
Formats 2 and 3 remain readable; merely opening or selecting does not change
the active state or how it is displayed. New format 4 packages require
the current program version on the Pi; "Stand prüfen" (check state) rejects older programs.
The interface uses light/dark surfaces, vector icons and, on Windows, preferably
Segoe UI. The fonts of the designed weather display are independent of this.

Ctrl+Z/Ctrl+Y: undo/redo; Ctrl+C/Ctrl+V: copy/paste widgets;
Ctrl+D: duplicate. Ctrl+click selects several widgets. Arrow keys move
the selection by one cell, Shift+arrow by five. Draft and history are
shared by both tabs. Arranging on the phone preserves the PC design,
including when undoing deleted widgets.

In the **Entwurf** (draft) menu: import images/TTF/OTF fonts, export/import design packages
with files, load PNG preview and an earlier backup.
In the **Vorlagen** (templates) menu: predefined design as well as custom styles, widgets and grids.
In the **Ansicht** (view) menu: grid, sidebars, tool color and test scenarios.

## Explicitly activating additional data

First design the time series and choose **Am PC anwenden** (apply on this PC). Under **Datenquellen →
Zusatzabrufe auf diesem PC aktivieren** (data sources → enable additional requests on this PC), check the demand and the daily load and
confirm. The next regular live update can then
request the additional sources. The configurator itself stays with sample data and starts neither
the display nor a weather request. **Zusatzabrufe auf diesem PC ausschalten**
(disable additional requests on this PC) revokes this approval. An HTTP request that is already running may still finish;
before every follow-up page the approval is checked again.

On the Pi, in the transfer dialog, first choose **Stand prüfen** and then
**Zusatzabrufe am Pi aktivieren** (enable additional requests on the Pi). What is confirmed is the checked, active
Pi demand. **Zusatzabrufe am Pi ausschalten** (disable additional requests on the Pi) ends the approval. A pure
design transfer does not activate additional data; closed programs stay
closed. This procedure has not yet been run on the real Pi.

The device approval is stored separately from the design and contains no keys.
An export or a OneDrive copy does not activate any other device. Changes to the
request demand require re-activation; colors, borders and positions
do not affect the approval. Hourly/daily series use the complete first
response pages that are loaded anyway. Further pages and minute/quarter-hour
values share source caches and request intervals. Missing values remain gaps.
The regular three requests every five minutes, both protected budget days and
24 reserve requests take priority. Notes in the widget mark switched-off
or incomplete additional data.

## Installation on other PCs

Only the configurator additionally needs `requirements-designer.txt`
(PySide6-Essentials). The starter uses the existing project Python environment;
missing libraries are reported and never installed automatically.
For this local development the Qt libraries are kept in isolation under
`%USERPROFILE%/AppData/Local/Wetterstation/designer-runtime` (outside OneDrive,
see `tools/dev_paths.py`; `build/designer-runtime/` is now only a fallback).
This folder is not included in Pi packages.
On other PCs, install the additional libraries explicitly in the desired local
Python environment, preferably the existing one under
`%LOCALAPPDATA%/Wetterstation/venv`. The display on the Pi does not need Qt.

## Files and protection

- `private/designer/draft.json`: auto-saved draft and base revision.
- `private/designer/assets/`: images and fonts, named by content checksum.
- `private/designer/backups/`: design backed up before being replaced.
- `private/designer/phone-undo.json`: limited recovery data for phone undo.
- `private/designer/timeline-activation.json`: separate device approval, absent
  by default; not part of design packages.
- `private/designer/incoming/`: traceable Pi transfer with transaction ID.
- `private/designer/transfer.json` and `transfer-packages/`: local mapping and
  unchanged package for resuming after the transfer dialog is closed.

Design packages contain only the verified design format and
named media. The existing key, location, certificates and counters
are neither exported nor replaced. Private files may, per project decision,
continue to be synchronized unencrypted via OneDrive.

The Pi transfer first checks the target state. An outdated Pi program is updated
via the existing manual updater. Only **Jetzt übertragen** (transfer now)
replaces the design, after a backup. A closed display stays closed;
a running demo keeps its temporary settings. After an unclear connection, use
**Stand prüfen**. The previous design can be restored in the transfer dialog
without resetting other private settings.

An upload first lands in a separate file. Only after the full
checksum is verified is it made available atomically for installation. After reopening,
**Stand prüfen** matches the same transfer again. **Übertragung fortsetzen**
(resume transfer) uses the same stored package and the same ID; an installation that has already been confirmed
is not repeated. **Neue Übertragung vorbereiten** (prepare new transfer) ends an
old open operation under the same lock as the installation and re-reads the
target state. A later retry of the ended operation is rejected.

## Local checks

- `python tools/offline_tests.py --report build/checks/designer-all-tests-final.txt`
- `python tests/designer_scale_check.py`: eighteen Qt usability checks at a simulated
  effective pixel factor of 1, 1.5 and 2; no changes to Windows settings.
  Including all eight widget/content handles at three zoom levels, direct
  selection, Alt/Escape, multi-selection, alignment, pending text input and
  real warning dialogs with continued editing after invalid widget geometry.
- `python tests/widget_demo.py --design`, then
  `node tests/designer_phone_check.cjs`: isolated local HTTPS, dummy key,
  phone sizes 320/375, Tk takeover and arrangement commands only.
  With `python tests/widget_demo.py --design --graphical` the same browser run is checked,
  including preservation of moved content blocks with format 4.
- `python tools/designer_acceptance.py`: complete offline acceptance in a frozen
  source copy, followed by package build and a byte-identical font check of the same state.

Evidence is under `build/checks/`. A real Pi transfer or new real weather requests
cannot be inferred from these checks.

## Corrections of 28.10.2026

New rectangles and ellipses receive visible gray fills and borders and are
immediately selected as content. Existing shapes use their inherited style again;
explicit transparency is preserved. To the right of each content item there is a minus button.
It removes only that content item without confirmation; Ctrl+Z restores it. Protected
card/time-series blocks keep a disabled button with an explanation.
The mouse wheel no longer changes selection, number or slider fields. In the right-hand
area it scrolls the properties instead, even when input fields are focused.


The page grid lies behind the widgets and is visible through transparent areas.
Columns and rows are applied directly to the draft after Enter or when leaving the field;
nothing changes while typing. A grid template changes
both values together. "Auf alle Seiten dieser Variante" (on all pages of this variant) stays selected when the
properties are rebuilt. Ctrl+Z reverts the grid change. Widgets are
scaled proportionally; rounding can produce marked overlaps.
"Automatisch anordnen" (arrange automatically) remains a separate action. The running display only
changes after explicit takeover. The inner grid for content remains separate.
