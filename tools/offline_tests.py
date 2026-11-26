"""Local audit runner: external sockets blocked, Windows spawn supported."""
import ipaddress
import argparse
from contextlib import nullcontext
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

def offline_guard(event, args):
    if event == "socket.connect" and isinstance(args[1], tuple):
        host = str(args[1][0])
        try:
            allowed = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            allowed = False
        if not allowed:
            raise RuntimeError("Externe Verbindung im Offline-Audit gesperrt")

sys.addaudithook(offline_guard)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    parser.add_argument('names', nargs='*')
    args = parser.parse_args()
    suite = (unittest.defaultTestLoader.loadTestsFromNames(args.names) if args.names
             else unittest.defaultTestLoader.discover(str(ROOT / "tests")))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('w', encoding='utf-8', buffering=1) if args.report else nullcontext(sys.stderr) as stream:
        result = unittest.TextTestRunner(verbosity=2, stream=stream).run(suite)
    print(f'Offline tests: {result.testsRun}; failures: {len(result.failures)}; errors: {len(result.errors)}; skipped: {len(result.skipped)}')
    sys.exit(not result.wasSuccessful())
