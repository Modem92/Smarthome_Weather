import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "eink_maintenance", ROOT / "raspberry_pi" / "eink_maintenance.py")
eink = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(eink)


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self.now = start

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeEPD:
    def __init__(self, clock, fail_clear=False, init_result=0):
        self.clock = clock
        self.calls = []
        self.clear_times = []
        self.fail_clear = fail_clear
        self.init_result = init_result

    def init(self):
        self.calls.append("init")
        return self.init_result

    def Clear(self):
        self.calls.append("clear")
        if self.fail_clear:
            raise OSError("SPI failure")
        self.clock.now += 25  # a full refresh takes some time
        self.clear_times.append(self.clock.now)

    def sleep(self):
        self.calls.append("sleep")


class EinkMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state" / "last-refresh"
        self.clock = FakeClock()
        self.messages = []

    def make(self, epd):
        return eink.Maintenance(epd, state_file=self.state, clock=self.clock.time,
                                sleep=self.clock.sleep, report=self.messages.append)

    def test_each_pass_is_init_clear_sleep(self):
        epd = FakeEPD(self.clock)
        self.make(epd).run(3)
        self.assertEqual(epd.calls, ["init", "clear", "sleep"] * 3)

    def test_refreshes_are_at_least_three_minutes_apart(self):
        epd = FakeEPD(self.clock)
        self.make(epd).run(3)
        gaps = [b - a for a, b in zip(epd.clear_times, epd.clear_times[1:])]
        self.assertTrue(all(gap >= eink.MIN_REFRESH_INTERVAL_S for gap in gaps), gaps)

    def test_respects_refresh_from_an_earlier_run(self):
        eink.write_last_refresh(self.state, self.clock.now - 60)
        epd = FakeEPD(self.clock)
        start = self.clock.now
        self.make(epd).run(1)
        self.assertGreaterEqual(epd.clear_times[0] - 25 - start, 120)

    def test_clock_moved_backwards_waits_full_interval(self):
        self.assertEqual(eink.seconds_until_refresh_allowed(2000.0, 1000.0), 180.0)
        self.assertEqual(eink.seconds_until_refresh_allowed(None, 1000.0), 0.0)
        self.assertEqual(eink.seconds_until_refresh_allowed(1000.0, 1500.0), 0.0)

    def test_display_sleeps_even_when_clear_fails(self):
        epd = FakeEPD(self.clock, fail_clear=True)
        with self.assertRaises(OSError):
            self.make(epd).run(2)
        self.assertEqual(epd.calls, ["init", "clear", "sleep"])
        self.assertIsNone(eink.read_last_refresh(self.state))

    def test_failed_init_still_sleeps(self):
        epd = FakeEPD(self.clock, init_result=-1)
        with self.assertRaises(RuntimeError):
            self.make(epd).run(1)
        self.assertEqual(epd.calls, ["init", "sleep"])

    def test_find_display_users(self):
        proc = Path(self.tmp.name) / "proc"
        links = {}

        def add(pid, cmdline, fd_target=None):
            d = proc / str(pid)
            (d / "fd").mkdir(parents=True)
            (d / "cmdline").write_bytes(cmdline.encode() + b"\0")
            if fd_target:
                fd = d / "fd" / "3"
                fd.write_text("")
                links[str(fd)] = fd_target

        add(10, "python3\0/home/x/EInk-Bilderrahmen/app.py")
        add(11, "python3\0other.py", "/dev/spidev0.0")
        add(12, "bash", "/dev/null")
        add(13, "python3\0eink_maintenance.py", "/dev/spidev0.0")  # ourselves
        (proc / "self").mkdir()

        def readlink(path):
            return links[str(Path(path))]

        users = eink.find_display_users(proc, own_pid=13, readlink=readlink)
        self.assertEqual(sorted(users), [10, 11])


if __name__ == "__main__":
    unittest.main()
