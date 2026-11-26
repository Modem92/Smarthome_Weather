"""Automatic LAN lifecycle with simulated discovery and no real server."""
import gc
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview


class MobileAddressDialogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root = tk.Tk()
        self.root.withdraw()
        self.preview = WeatherPreview(self.root, widget_demo=True,
                                      settings_store=ApiKeyStore(path=Path(self.temp.name) / "settings.json"))
        self.jobs = []
        self.worker = patch.object(self.preview, "_start_worker", side_effect=lambda task, error, name: self.jobs.append((task, error, name)))
        self.worker.start()

    def tearDown(self):
        self.worker.stop()
        self.root.update_idletasks()
        self.preview.close()
        self.jobs.clear()
        del self.worker, self.preview, self.root
        gc.collect()
        self.temp.cleanup()

    def resolve(self, values, service=None, error=None):
        task, _, name = self.jobs.pop(0)
        self.assertEqual(name, "mobile-auto-start")
        with patch("wetterstation.ui.app.local_addresses", return_value=values), patch("wetterstation.ui.app.MobileSettingsServer", return_value=service):
            if error:
                service.start.side_effect=error
            task()
        self.preview._results.get(timeout=2)()

    def test_discovery_is_background_and_ignores_loopback(self):
        from unittest.mock import Mock
        service=Mock(running=False,url="")
        self.preview._maintain_mobile_connection()
        self.assertTrue(self.preview._mobile_start_pending)
        self.assertIsNone(self.preview.mobile_service)
        self.resolve(["192.168.42.10","127.0.0.1"],service)
        service.start.assert_called_once_with("192.168.42.10")
        self.assertFalse(self.preview._mobile_start_pending)

    def test_missing_network_retries_without_binding_or_blocking_display(self):
        self.preview._maintain_mobile_connection()
        with patch.object(self.root,'after',wraps=self.root.after) as schedule:
            self.resolve(["127.0.0.1"])
        self.assertIsNone(self.preview.mobile_service)
        self.assertIn('Keine Heimnetz',self.preview._mobile_start_error)
        self.assertTrue(any(c.args==(10000,self.preview._maintain_mobile_connection) for c in schedule.call_args_list))

    def test_port_or_certificate_failure_retries_with_sanitized_error(self):
        from unittest.mock import Mock
        from wetterstation.mobile.mobile_settings import MobileSettingsError
        service=Mock(running=False,url="")
        self.preview._maintain_mobile_connection()
        self.resolve(["192.168.42.10"],service,MobileSettingsError("Verbindung momentan nicht verfügbar"))
        self.assertFalse(self.preview._mobile_start_pending)
        self.assertIn('nicht verfügbar',self.preview._mobile_start_error)

    def test_running_service_keeps_sessions_and_changed_address_rebinds(self):
        from unittest.mock import Mock
        active=Mock(running=True,url="https://192.168.42.10:8765")
        self.preview.mobile_service=active
        self.preview._maintain_mobile_connection()
        self.resolve(["192.168.42.10"])
        active.stop.assert_not_called()
        replacement=Mock(running=False,url="")
        self.preview._maintain_mobile_connection()
        self.resolve(["192.168.42.11"],replacement)
        active.stop.assert_called_once()
        replacement.start.assert_called_once_with("192.168.42.11")

    def test_close_during_start_cancels_background_binding(self):
        from unittest.mock import Mock
        service=Mock(running=False,url="")
        self.preview._maintain_mobile_connection()
        self.preview._mobile_cancel.set()
        self.resolve(["192.168.42.10"],service)
        service.start.assert_not_called()

    def test_read_only_mock_never_starts_discovery(self):
        self.preview.widget_demo=False
        self.preview._maintain_mobile_connection()
        self.assertFalse(self.jobs)


if __name__=='__main__':
    unittest.main()
