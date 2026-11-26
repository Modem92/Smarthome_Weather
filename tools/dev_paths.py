"""PC-only dependency and scratch paths; never redirects private device data."""
import os
from pathlib import Path
import sys


def local_root():
    # Use the normal profile even when a launcher redirects LOCALAPPDATA.
    home = Path(os.environ.get('USERPROFILE', str(Path.home())))
    return home / 'AppData/Local/Wetterstation' if sys.platform == 'win32' else Path.home() / '.cache/wetterstation'


def scratch_root():
    path = local_root() / 'checks'
    path.mkdir(parents=True, exist_ok=True)
    return path


def designer_runtime(root):
    external = local_root() / 'designer-runtime'
    return external if (external / 'PySide6/__init__.py').is_file() else Path(root) / 'build/designer-runtime'


def use_designer_runtime(root):
    path = designer_runtime(root)
    if path.is_dir():
        sys.path.insert(0, str(path))
    return path
