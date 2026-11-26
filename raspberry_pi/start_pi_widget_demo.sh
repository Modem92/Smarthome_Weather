#!/bin/sh
# Automatic LAN phone pairing, synthetic values and separate temporary settings.
set -eu
cd -- "$(dirname -- "$0")/.."
if [ -e .pi-update-in-progress.json ]; then
    echo "Unvollstaendiges Update. Bitte zuerst nach PI_UPDATE.md wiederherstellen." >&2
    exit 1
fi
exec python3 app.py --widget-demo "$@"
