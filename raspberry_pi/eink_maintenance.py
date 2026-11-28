#!/usr/bin/env python3
"""Clear the Waveshare 7.3inch e-Paper HAT (E) several times or prepare it for storage.

Standalone desktop tool for the Raspberry Pi. It uses the Waveshare driver that the
user cloned to ~/e-Paper (not part of the weather station package, see ai/DECISIONS.md).

Panel rules (ai/specs/eink.md): at least 180 s between two refreshes, at least one
refresh every 24 h, no partial refresh, and sleep/power-off after every refresh,
because a panel left under high voltage is damaged permanently.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Iterable

MIN_REFRESH_INTERVAL_S = 180
DEFAULT_PASSES = 3
MAX_PASSES = 10
SPI_DEVICE = "/dev/spidev0.0"
# Other programs on the Pi that drive the same panel; running in parallel would
# break the 180 s rule and garble the SPI transfer.
OTHER_DISPLAY_PROGRAMS = ("EInk-Bilderrahmen",)
DEFAULT_DRIVER_DIRS = (Path.home() / "e-Paper" / "RaspberryPi_JetsonNano" / "python" / "lib",)
DEFAULT_STATE_FILE = Path.home() / ".local" / "state" / "eink-maintenance" / "last-refresh"
LOCK_FILE = Path("/tmp/eink-maintenance.lock")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BUSY = 2


def read_last_refresh(state_file: Path) -> float | None:
    try:
        return float(state_file.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def write_last_refresh(state_file: Path, timestamp: float) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(f"{timestamp:.0f}\n", encoding="utf-8")


def seconds_until_refresh_allowed(last: float | None, now: float,
                                  min_interval: float = MIN_REFRESH_INTERVAL_S) -> float:
    if last is None:
        return 0.0
    elapsed = now - last
    if elapsed < 0:
        # Clock moved backwards: the real age of the last refresh is unknown.
        return float(min_interval)
    return max(0.0, min_interval - elapsed)


def find_display_users(proc_root: Path = Path("/proc"), device: str = SPI_DEVICE,
                       own_pid: int | None = None,
                       programs: Iterable[str] = OTHER_DISPLAY_PROGRAMS,
                       readlink: Callable[[str], str] = os.readlink) -> list[int]:
    """Return PIDs that hold the SPI device open or belong to another display program."""
    own_pid = os.getpid() if own_pid is None else own_pid
    programs = tuple(programs)
    users: list[int] = []
    try:
        entries = list(os.scandir(proc_root))
    except OSError:
        return users
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == own_pid:
            continue
        pid = int(entry.name)
        try:
            cmdline = (Path(entry.path) / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", "replace")
        except OSError:
            cmdline = ""
        if any(name in cmdline for name in programs):
            users.append(pid)
            continue
        try:
            fds = list(os.scandir(Path(entry.path) / "fd"))
        except OSError:
            continue  # process of another user or already gone
        for fd in fds:
            try:
                if readlink(fd.path) == device:
                    users.append(pid)
                    break
            except OSError:
                continue
    return users


class DisplayBusy(RuntimeError):
    pass


class PowerOffFailed(RuntimeError):
    pass


@contextlib.contextmanager
def interrupts_deferred():
    """Ignore Ctrl+C/SIGTERM/SIGHUP while the panel is being put to sleep."""
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    names = ("SIGINT", "SIGTERM", "SIGHUP")
    previous = {}
    for name in names:
        if hasattr(signal, name):
            sig = getattr(signal, name)
            previous[sig] = signal.signal(sig, signal.SIG_IGN)
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


class Maintenance:
    """Runs clear passes; every pass is init -> full refresh -> deep sleep."""

    def __init__(self, epd, *, power_off: Callable[[], None] | None = None,
                 busy_check: Callable[[], list[int]] = lambda: [],
                 state_file: Path = DEFAULT_STATE_FILE,
                 clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep,
                 report: Callable[[str], None] = print,
                 shield=interrupts_deferred,
                 min_interval: float = MIN_REFRESH_INTERVAL_S) -> None:
        self.epd = epd
        self.power_off = power_off
        self.busy_check = busy_check
        self.state_file = state_file
        self.clock = clock
        self.sleep = sleep
        self.report = report
        self.shield = shield
        self.min_interval = min_interval
        self._not_before = 0.0

    def _remaining(self) -> float:
        now = self.clock()
        from_state = seconds_until_refresh_allowed(
            read_last_refresh(self.state_file), now, self.min_interval)
        return max(from_state, self._not_before - now)

    def _wait_for_interval(self) -> None:
        remaining = self._remaining()
        while remaining > 0:
            self.report(f"Schutzpause: noch {int(remaining + 0.999)} s bis zur nächsten "
                        "Aktualisierung (mindestens 3 Minuten Abstand).")
            self.sleep(min(30.0, remaining))
            remaining = self._remaining()

    def _put_to_sleep(self) -> None:
        with self.shield():
            try:
                self.epd.sleep()
                return
            except Exception as exc:
                error = exc
            # sleep() failed before module_exit(): switch the HAT off directly.
            if self.power_off is not None:
                try:
                    self.power_off()
                    return
                except Exception as exc:
                    error = exc
            raise PowerOffFailed(
                "Display konnte nicht sicher abgeschaltet werden. Bitte den Pi "
                "herunterfahren (sudo poweroff) und vom Strom trennen.") from error

    def _clear_once(self) -> None:
        try:
            if self.epd.init() != 0:
                raise RuntimeError("Display konnte nicht initialisiert werden.")
            # Stamp before refreshing: an aborted refresh still counts for the 3-minute rule.
            write_last_refresh(self.state_file, self.clock())
            self.epd.Clear()  # default 0x11 = white on both pixels of each byte
            write_last_refresh(self.state_file, self.clock())
        finally:
            # Never leave the panel under voltage, also after errors or Ctrl+C.
            self._put_to_sleep()

    def run(self, passes: int = DEFAULT_PASSES) -> None:
        # Another program (e.g. the picture frame) may have refreshed just before us
        # without leaving a timestamp, so the first pass always waits the full interval.
        self._not_before = self.clock() + self.min_interval
        for number in range(1, passes + 1):
            self._wait_for_interval()
            users = self.busy_check()
            if users:
                raise DisplayBusy("Ein anderes Programm benutzt jetzt das Display (Prozess "
                                  f"{', '.join(map(str, users))}). Löschen abgebrochen.")
            self.report(f"Löschdurchgang {number} von {passes} läuft (ca. 30 s) …")
            self._clear_once()
            self.report(f"Löschdurchgang {number} von {passes} fertig, Display schläft.")


def load_driver(driver_dirs: Iterable[Path] = DEFAULT_DRIVER_DIRS):
    for directory in driver_dirs:
        if (directory / "waveshare_epd" / "epd7in3e.py").exists():
            sys.path.insert(0, str(directory))
            from waveshare_epd import epd7in3e, epdconfig  # type: ignore[import-not-found]
            return epd7in3e.EPD(), epdconfig.module_exit
    raise FileNotFoundError("Waveshare-Treiber epd7in3e nicht gefunden (erwartet unter "
                            "~/e-Paper/RaspberryPi_JetsonNano/python/lib).")


def acquire_lock(path: Path = LOCK_FILE):
    import fcntl  # Linux only; imported here so tests run on Windows

    handle = open(path, "w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _raise_interrupt(signum, frame):
    raise KeyboardInterrupt


def install_exit_signal_handlers() -> None:
    """Closing the terminal (SIGHUP) or a shutdown (SIGTERM) would otherwise skip
    every finally block and leave the panel under voltage."""
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _raise_interrupt)


def say(text: str) -> None:
    try:
        print(text, flush=True)
    except (OSError, ValueError):
        pass  # terminal already closed; the panel handling must go on


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E-Ink-Display mehrmals löschen oder einlagern.")
    parser.add_argument("--passes", type=int, default=DEFAULT_PASSES,
                        help=f"Anzahl Löschdurchgänge (1–{MAX_PASSES}, Standard {DEFAULT_PASSES})")
    parser.add_argument("--storage", action="store_true",
                        help="Display für die Lagerung vorbereiten")
    parser.add_argument("--pause", action="store_true",
                        help="Am Ende auf Enter warten (für das Desktop-Symbol)")
    args = parser.parse_args(argv)
    passes = max(1, min(MAX_PASSES, args.passes))

    install_exit_signal_handlers()
    code = EXIT_OK
    lock = None
    try:
        lock = acquire_lock()
        users = find_display_users()
        if lock is None or users:
            say("Das Display wird gerade von einem anderen Programm benutzt"
                + (f" (Prozess {', '.join(map(str, users))})" if users else "")
                + ". Bitte dieses Programm zuerst beenden.")
            code = EXIT_BUSY
        else:
            title = "Display für die Lagerung vorbereiten" if args.storage else "Display löschen"
            say(f"{title}: {passes} Durchgänge, je mindestens 3 Minuten Abstand "
                "(auch vor dem ersten). Bitte nicht abbrechen und das Display nicht abstecken.")
            epd, power_off = load_driver()
            Maintenance(epd, power_off=power_off, busy_check=find_display_users,
                        report=say).run(passes)
            if args.storage:
                say("Fertig: Das Display ist weiß, schläft und ist stromlos.\n"
                    "Jetzt den Pi herunterfahren (sudo poweroff) und erst danach das Display "
                    "abstecken. Lagern: Bildseite nach oben, trocken, nichts darauflegen, "
                    "Flachbandkabel nicht knicken.\n"
                    "Vor der nächsten Benutzung das Display wieder mehrmals löschen.")
            else:
                say("Fertig: Das Display ist weiß und schläft.")
    except KeyboardInterrupt:
        # Reached only after the panel was put to sleep (otherwise PowerOffFailed wins).
        say("Abgebrochen. Das Display schläft.")
        code = EXIT_ERROR
    except DisplayBusy as exc:
        say(str(exc))
        code = EXIT_BUSY
    except Exception as exc:  # report every failure in German, the window stays readable
        say(f"Fehler: {exc}")
        code = EXIT_ERROR
    finally:
        if lock is not None:
            lock.close()
    if args.pause:
        try:
            input("Enter drücken zum Schließen.")
        except (EOFError, OSError, KeyboardInterrupt):
            pass
    return code


if __name__ == "__main__":
    sys.exit(main())
