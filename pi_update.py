"""Compatibility entry point; implementation lives in the organized package."""
import importlib
import sys
_implementation = importlib.import_module("tools.pi.update")
if __name__ == "__main__":
    sys.exit(_implementation.main())
else:
    sys.modules[__name__] = _implementation
