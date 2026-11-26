"""Manual PC designer entry; no automatic installation or weather starts."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
# The isolated development dependency folder is optional, never part of Pi packages.
from tools.dev_paths import use_designer_runtime
use_designer_runtime(ROOT)


def main():
    try:import PySide6
    except ImportError:
        message=('Die PC-Gestaltungsbibliothek fehlt. Python 3.11 oder neuer mit den '
                 'Projektbibliotheken und requirements-designer.txt verwenden. '
                 'Anleitung: docs/DESIGNER.md. Es wird nichts automatisch installiert.')
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,message,'Wetterstation gestalten',0x40)
        else:print(message)
        return 1
    try:
        from wetterstation.designer.app import main as run
        run()
    except Exception:
        message='Der Konfigurator konnte nicht gestartet werden. Gespeicherte Daten bleiben erhalten. Pythonbibliotheken und docs/DESIGNER.md prüfen.'
        if sys.platform=='win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0,message,'Wetterstation gestalten',0x10)
        else:print(message)
        return 1


if __name__=='__main__':sys.exit(main())
