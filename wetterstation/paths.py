"""One stable project root for code, private data and the budget identity."""
from pathlib import Path


def project_root(anchor=None):
    path = Path(anchor or __file__).resolve()
    if anchor is None:
        return path.parents[1]
    for parent in path.parents:
        if parent.name == 'wetterstation':
            return parent.parent
    # Compatibility entry points and isolated tests may live directly at root.
    return path.parent
