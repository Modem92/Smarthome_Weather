"""Installation migration with dummy secrets and isolated counters only."""
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.openweather_budget import OpenWeatherBudget, _atomic_json, BudgetUnavailable, BudgetLimitReached
from tools.legacy.pi_live_transfer import export_bundle, import_bundle


class PiTransferTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.source, self.target = folder / "pc", folder / "pi"
        self.local = folder / "pi-local"
        self.budget = OpenWeatherBudget(project_private=self.source / "private", local_root=folder / "pc-local")
        self.primary, self.mirror, _ = self.budget._paths()
        now = datetime.now(timezone.utc)
        self.state = {"schema": 2, "device_id": self.budget._get_device_id(), "revision": 7,
            "day": now.date().isoformat(), "count": 17, "recent_attempts": [now.isoformat()],
            "local_zone": "Europe/Berlin", "local_day": now.astimezone(ZoneInfo("Europe/Berlin")).date().isoformat(),
            "local_count": 17, "blocked_until": None, "updated_at": now.isoformat()}
        for path in (self.primary, self.mirror):
            _atomic_json(path, self.state)
        ApiKeyStore(path=self.source / "private/settings.json").save_api_key("dummy-not-a-real-key")

    def test_move_preserves_identity_counts_revision_and_source(self):
        before = [path.read_bytes() for path in (self.primary, self.mirror)]
        export_bundle(self.source, self.budget)
        bundle = self.source / "private/pi-live-transfer.zip"
        import_bundle(self.target, bundle, self.local)
        target = OpenWeatherBudget(project_private=self.target / "private", local_root=self.local)
        self.assertEqual(target._get_device_id(), self.state["device_id"])
        for path in target._paths()[:2]:
            self.assertEqual(json.loads(path.read_text()), self.state)
        self.assertEqual(before, [path.read_bytes() for path in (self.primary, self.mirror)])
        self.assertFalse(bundle.exists())
        self.assertEqual(target.reserve_call(), 18)

    def test_existing_pi_identity_is_never_overwritten(self):
        export_bundle(self.source, self.budget)
        self.local.mkdir()
        identity = self.local / "device-id.txt"
        identity.write_text("a" * 32)
        with self.assertRaises(ValueError):
            import_bundle(self.target, self.source / "private/pi-live-transfer.zip", self.local)
        self.assertEqual(identity.read_text(), "a" * 32)
        self.assertFalse((self.target / "private/settings.json").exists())

    def test_existing_pi_settings_are_never_overwritten(self):
        export_bundle(self.source, self.budget)
        store = ApiKeyStore(path=self.target / "private/settings.json")
        store.save_api_key("another-dummy")
        original = store.path.read_bytes()
        with self.assertRaises(ValueError):
            import_bundle(self.target, self.source / "private/pi-live-transfer.zip", self.local)
        self.assertEqual(original, store.path.read_bytes())
        self.assertFalse((self.local / "device-id.txt").exists())

    def test_mirror_rollback_blocks_export(self):
        _atomic_json(self.mirror, {**self.state, "revision": 8, "count": 18})
        with self.assertRaises(BudgetUnavailable):
            export_bundle(self.source, self.budget)
        self.assertFalse((self.source / "private/pi-live-transfer.zip").exists())

    def test_exhausted_budget_stays_exhausted_after_move(self):
        for path in (self.primary, self.mirror):
            _atomic_json(path, {**self.state, "count": 1000, "local_count": 1000})
        export_bundle(self.source, self.budget)
        import_bundle(self.target, self.source / "private/pi-live-transfer.zip", self.local)
        target = OpenWeatherBudget(project_private=self.target / "private", local_root=self.local)
        self.assertEqual(target.status()["remaining"], 0)
        with self.assertRaises(BudgetLimitReached):
            target.reserve_call()

    def test_existing_start_guard_is_preserved(self):
        blocked = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        for path in (self.primary, self.mirror):
            _atomic_json(path, {**self.state, "blocked_until": blocked})
        export_bundle(self.source, self.budget)
        import_bundle(self.target, self.source / "private/pi-live-transfer.zip", self.local)
        target = OpenWeatherBudget(project_private=self.target / "private", local_root=self.local)
        for path in target._paths()[:2]:
            self.assertEqual(json.loads(path.read_text())["blocked_until"], blocked)


if __name__ == "__main__":
    unittest.main()
