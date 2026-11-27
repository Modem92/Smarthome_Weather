"""Block commits that would publish private values (keys, device address, real location).

The public repo must never contain device data. The values to block are private
themselves, so they are not in this file: they come from a gitignored denylist
(``private/leak-denylist.txt`` by default) and from the private settings files it
points to. Hits are reported as file:line plus the source label, never the value.

Denylist format (one entry per line, ``#`` starts a comment):
    some literal text        blocked case-insensitively
    dir: <path>              also read secrets from settings.json / pi-update.json there

Exit codes: 0 clean or no denylist (warning), 1 hit found, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DENYLIST = ROOT / 'private' / 'leak-denylist.txt'
ENV_DENYLIST = 'WETTERSTATION_LEAK_DENYLIST'
# Shorter entries would match ordinary words and code and make the hook useless.
MIN_LENGTH = 4
# Fields in private JSON files whose values must never be published.
SECRET_FIELDS = {
    'settings.json': ('openweather_api_key', 'location'),
    'pi-update.json': ('host', 'relative_target'),
}


def load_denylist(path: Path) -> list[tuple[str, str]]:
    """Return (value, label) pairs; labels name the source, not the value."""
    entries: list[tuple[str, str]] = []
    for number, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        if line.lower().startswith('dir:'):
            entries.extend(_secrets_from_dir(Path(os.path.expandvars(line[4:].strip()))))
        else:
            entries.append((line, f'{path.name} line {number}'))
    unique: dict[str, str] = {}
    for value, label in entries:
        if len(value) >= MIN_LENGTH:
            unique.setdefault(value.lower(), label)
    return [(value, label) for value, label in unique.items()]


def _secrets_from_dir(folder: Path) -> list[tuple[str, str]]:
    found = []
    for name, fields in SECRET_FIELDS.items():
        try:
            data = json.loads((folder / name).read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            continue
        for field in fields:
            value = data.get(field) if isinstance(data, dict) else None
            if isinstance(value, str) and value.strip():
                found.append((value.strip(), f'{name}:{field}'))
    return found


def scan_lines(lines, entries):
    """Yield (line_number, label) for every line containing a denied value."""
    for number, line in lines:
        lowered = line.lower()
        for value, label in entries:
            if value in lowered:
                yield number, label


def staged_added_lines(cwd: Path):
    """Yield (path, [(line_number, text)]) for lines added in the index."""
    diff = _git(cwd, 'diff', '--cached', '--no-color', '--no-ext-diff', '-U0', '--diff-filter=ACMR')
    path, number, lines = None, 0, []
    for line in diff.splitlines():
        if line.startswith('+++ '):
            if path is not None:
                yield path, lines
            target = line[4:]
            path = target[2:] if target.startswith('b/') else None
            lines = []
        elif line.startswith('@@'):
            match = re.search(r'\+(\d+)', line)
            number = int(match.group(1)) if match else 0
        elif line.startswith('+') and path is not None:
            lines.append((number, line[1:]))
            number += 1
    if path is not None:
        yield path, lines


def staged_paths(cwd: Path):
    return [p for p in _git(cwd, 'diff', '--cached', '--name-only', '--diff-filter=ACMR').splitlines() if p]


def tracked_files(cwd: Path):
    for name in _git(cwd, 'ls-files').splitlines():
        try:
            text = (cwd / name).read_text(encoding='utf-8', errors='ignore')
        except OSError:
            continue
        yield name, list(enumerate(text.splitlines(), 1))


def history_hits(cwd: Path, entries):
    """Return (commit:path, label) for every denied value anywhere in Git history."""
    hits = []
    revisions = _git(cwd, 'rev-list', '--all').split()
    for value, label in entries:
        for revision in revisions:
            result = subprocess.run(['git', 'grep', '-l', '-i', '-F', '-e', value, revision],
                                    cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.stdout.strip():
                first = result.stdout.splitlines()[0]
                hits.append((f'{revision[:7]}:{first.split(":", 1)[1]}', label))
                break
    return hits


def _git(cwd: Path, *args) -> str:
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True,
                          text=True, encoding='utf-8', errors='replace').stdout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--staged', action='store_true', help='check lines added in the index (default, used by the hook)')
    mode.add_argument('--tracked', action='store_true', help='check all tracked files in the working tree')
    mode.add_argument('--history', action='store_true', help='check every commit reachable from any ref')
    parser.add_argument('--denylist', type=Path)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    denylist = args.denylist or Path(os.environ.get(ENV_DENYLIST) or DEFAULT_DENYLIST)
    if not denylist.is_file():
        print(f'private-leak check skipped: no denylist at {denylist}', file=sys.stderr)
        return 0
    entries = load_denylist(denylist)

    hits: list[tuple[str, str]] = []
    if args.history:
        hits = history_hits(args.repo, entries)
    else:
        files = tracked_files(args.repo) if args.tracked else staged_added_lines(args.repo)
        for path, lines in files:
            hits.extend((f'{path}:{number}', label) for number, label in scan_lines(lines, entries))
        if not args.tracked:
            hits.extend((path, label) for path, label in scan_lines([(path, path) for path in staged_paths(args.repo)], entries))

    if hits:
        print('Private values found (values not shown):', file=sys.stderr)
        for where, label in hits:
            print(f'  {where}  <- {label}', file=sys.stderr)
        print('Remove them; replace with the public sample (Potsdam) or a placeholder.', file=sys.stderr)
        return 1
    print(f'private-leak check passed ({len(entries)} entries)', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
