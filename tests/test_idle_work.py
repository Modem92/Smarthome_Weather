"""Idle work regression checks, isolated storage and simulated clocks."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from wetterstation.lifecycle import AppSession
from wetterstation.mobile.mobile_settings import MobileSettingsServer
from wetterstation.ui.app import WeatherPreview
from wetterstation.designer import model, runtime
from wetterstation.designer.render import demo_data
from queue import SimpleQueue
from types import SimpleNamespace


class IdleWorkTests(unittest.TestCase):
    def test_frame_preparation_keeps_only_latest_request_and_rejects_old_result(self):
        document=model.from_layout();data=demo_data();jobs=[]
        canvas=Mock();canvas.winfo_width.return_value=1024;canvas.winfo_height.return_value=600;canvas.find_withtag.return_value=()
        preview=SimpleNamespace(dashboard=document,canvas=canvas,_closed=False,_pairing_screen=None,
            _current_page=lambda:document['pages'][preview.page],page=0,
            api_key_store=SimpleNamespace(path=Path('dummy/settings.json')),_results=SimpleQueue(),
            _start_worker=lambda work,error,name:jobs.append(work),_publish_dashboard=Mock())
        from PIL import Image
        frame=tuple(Image.new('RGBA',(8,8)) for _ in range(3))
        with patch.object(runtime,'display_data',return_value=data),patch.object(runtime,'prepare_frame',return_value=frame),patch.object(runtime,'_show_frame') as show:
            runtime.draw(preview)
            preview.page=1;runtime.draw(preview)
            self.assertEqual(len(jobs),1)
            jobs.pop(0)();preview._results.get()()
            show.assert_not_called();self.assertEqual(len(jobs),1)
            jobs.pop(0)();preview._results.get()()
            show.assert_called_once()
            self.assertEqual(show.call_args.args[1][2],document['pages'][1]['id'])

    def test_session_writes_only_changed_state_but_keeps_stop_check(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root, preview = Mock(), Mock(_closed=False)
            session = AppSession(Path(folder), root, preview, [])
            with patch('wetterstation.lifecycle.process_start', return_value='123'), \
                 patch('wetterstation.lifecycle.os.fsync') as sync:
                session._write(False)
                for _ in range(20):
                    session._poll()
                self.assertEqual(sync.call_count, 2)
                self.assertEqual(root.after.call_count, 20)
                session.stop = True
                session._poll()
                preview.close.assert_called_once()
                self.assertEqual(sync.call_count, 2)

    def preview(self, service):
        preview = object.__new__(WeatherPreview)
        preview.root = Mock()
        preview._closed = False
        preview._pairing_screen = None
        preview.mobile_service = service
        preview.draw = Mock()
        return preview

    def test_no_pairing_means_no_timer_or_redraw(self):
        service = MobileSettingsServer(Mock())
        preview = self.preview(service)
        preview._check_pairing()
        preview.root.after.assert_not_called()
        preview.draw.assert_not_called()

    def test_pairing_has_one_expiry_timer_and_clears_without_polling(self):
        service = MobileSettingsServer(Mock())
        preview = self.preview(service)
        with patch('wetterstation.mobile.mobile_settings.time.monotonic', return_value=100), \
             patch('time.monotonic', return_value=100):
            service.request_pairing('', '127.0.0.1')
            preview._pairing_changed()
            self.assertEqual(preview.root.after.call_args.args[0], 120001)
            self.assertIsNotNone(preview._pairing_screen)
        preview.root.after.reset_mock()
        with patch('time.monotonic', return_value=221):
            preview._check_pairing()
            self.assertIsNone(preview._pairing_screen)
            preview.root.after.assert_not_called()


if __name__ == '__main__':
    unittest.main()
