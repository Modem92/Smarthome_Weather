#!/bin/sh
# Run only after configuring the explicitly approved Pi live operation.
set -eu
cd -- "$(dirname -- "$0")/.."
if [ -e .pi-update-in-progress.json ]; then
    echo "Unvollstaendiges Update. Bitte zuerst nach docs/UPDATE.md wiederherstellen." >&2
    exit 1
fi
if ! python3 -c 'import tkinter; import PIL; import cryptography; from zoneinfo import ZoneInfo; ZoneInfo("Europe/Berlin")'; then
    echo "Fehlende Python-Bibliotheken oder Zeitzonendaten: Bitte zuerst die Pi-Einrichtung abschliessen." >&2
    exit 1
fi
exec python3 app.py "$@"
