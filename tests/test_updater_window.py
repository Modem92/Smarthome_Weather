"""Real Tk terminal-state checks; update work is simulated, never SSH."""
import time
import tkinter as tk
import unittest
from unittest.mock import patch

from tools.windows.updater import UpdateWindow
from tools.pi.update import UpdateError


class UpdaterWindowTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk(); self.root.withdraw()
        self.window = UpdateWindow(self.root)
        self.result = {'release': 'DEMO', 'state': 'closed',
                       'backup': '/home/pi/wetterstation/Wetterstation-Backups/DEMO'}

    def tearDown(self):
        self.window.bar.stop()
        self.root.update_idletasks()
        self.root.destroy()

    def test_success_is_explicit_full_and_closable_instead_of_stopped_busy_bar(self):
        self.window.consume('success', self.result)
        self.assertFalse(self.window.active)
        self.assertIn('Update abgeschlossen', self.root.title())
        self.assertIn('Update abgeschlossen', self.window.heading.cget('text'))
        self.assertEqual(str(self.window.bar.cget('mode')), 'determinate')
        self.assertEqual(float(self.window.bar.cget('value')), 100)
        self.assertEqual(str(self.window.done.cget('state')), 'normal')
        self.assertIn('jetzt schließen', self.window.message.get())
        self.assertIn('Desktop-Symbol', self.window.detail.get())
        self.assertIn(self.result['backup'], self.window.detail.get())

    def test_restart_success_is_reported_as_restarted(self):
        self.window.consume('success', {**self.result, 'state': 'restarted'})
        self.assertIn('wieder gestartet', self.window.detail.get())
        self.assertNotIn('bleibt geschlossen', self.window.detail.get())

    def test_error_has_explicit_terminal_state_without_green_progress(self):
        self.window.consume('error', 'Verbindung unterbrochen; Pi-Stand prüfen.')
        self.assertFalse(self.window.active)
        self.assertIn('Fehler beendet', self.window.heading.cget('text'))
        self.assertNotEqual(self.window.bar.winfo_manager(), 'pack')
        self.assertEqual(float(self.window.bar.cget('value')), 0)
        self.assertEqual(str(self.window.done.cget('state')), 'normal')
        self.assertNotIn('Update abgeschlossen', self.root.title())
        self.assertIn('Pi-Stand prüfen', self.window.detail.get())

    def test_running_phase_does_not_imply_completion_or_enable_close(self):
        self.window.consume('progress', 'Pi sichern …')
        self.assertTrue(self.window.active)
        self.assertEqual(str(self.window.bar.cget('mode')), 'indeterminate')
        self.assertEqual(str(self.window.done.cget('state')), 'disabled')
        self.assertIn('läuft noch', self.window.message.get())

    def test_late_progress_cannot_overwrite_finished_state(self):
        self.window.consume('success', self.result)
        self.window.consume('progress', 'Pi sichern …')
        self.assertIn('Update abgeschlossen', self.window.heading.cget('text'))
        self.assertIn('Version DEMO', self.window.detail.get())
        self.assertEqual(float(self.window.bar.cget('value')), 100)

    def run_worker(self, **mock_options):
        with patch('tools.windows.updater.perform', **mock_options):
            self.window.start()
            self.window.worker.join(timeout=2)
            deadline = time.monotonic() + 2
            while self.window.active and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
        self.assertFalse(self.window.active)

    def test_background_success_reaches_gui_through_real_event_loop(self):
        self.run_worker(return_value=self.result)
        self.assertIn('Update abgeschlossen', self.root.title())
        self.assertEqual(float(self.window.bar.cget('value')), 100)

    def test_background_expected_error_reaches_gui_as_failure(self):
        self.run_worker(side_effect=UpdateError('Anmeldung fehlgeschlagen.'))
        self.assertIn('Fehler beendet', self.root.title())
        self.assertIn('Anmeldung fehlgeschlagen', self.window.detail.get())

    def test_background_unknown_error_never_leaks_exception_or_looks_successful(self):
        self.run_worker(side_effect=RuntimeError('dummy-sensitive-details'))
        self.assertIn('Fehler beendet', self.root.title())
        self.assertNotIn('dummy-sensitive', self.window.detail.get())

    def test_incomplete_completion_response_is_never_shown_as_success(self):
        self.run_worker(return_value={'state': 'closed'})
        self.assertIn('Fehler beendet', self.root.title())
        self.assertIn('Abschluss konnte nicht bestätigt', self.window.detail.get())
        self.assertEqual(float(self.window.bar.cget('value')), 0)


if __name__ == '__main__':
    unittest.main()
