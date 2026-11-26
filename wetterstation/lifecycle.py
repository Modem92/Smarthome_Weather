"""Linux desktop lifecycle for explicitly requested, orderly application updates."""
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import uuid

SESSION = '.wetterstation-session.json'
ALLOWED_ARGS = {'--mock-preview', '--widget-demo', '--show-rain-map', '--open-settings'}


def process_start(pid, proc=Path('/proc')):
    return (proc / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[19]


class AppSession:
    def __init__(self, project, root, preview, args):
        self.project, self.root, self.preview = Path(project), root, preview
        self.enabled = sys.platform == 'linux' and Path('/proc/self/stat').exists()
        self.args = list(args)
        self.stop = False
        self.nonce = uuid.uuid4().hex
        self._written_record = None

    def _write(self, ready):
        record = {'schema': 1, 'root': str(self.project.resolve()), 'pid': os.getpid(),
                  'start': process_start(os.getpid()), 'nonce': self.nonce,
                  'args': self.args, 'ready': ready, 'orderly_stop': True}
        if record == self._written_record:
            return
        with tempfile.NamedTemporaryFile(dir=self.project, prefix='.session-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(record).encode()); stream.flush(); os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, self.project / SESSION)
        self._written_record = record

    def __enter__(self):
        if not self.enabled:
            return self
        import fcntl
        self.lock = (self.project / '.wetterstation-app.lock').open('a+b')
        try:
            fcntl.flock(self.lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            if (self.project / '.pi-update-in-progress.json').exists():
                raise RuntimeError('Aktualisierung aktiv; Programmstart gesperrt.')
            self.previous = signal.getsignal(signal.SIGTERM)
            signal.signal(signal.SIGTERM, self._signal)
            self._write(False)
            self.root.after(250, self._poll)
        except BaseException:
            self.lock.close()
            raise
        return self

    def _signal(self, *_):
        # A signal handler must never call Tk or terminate an in-progress file write.
        self.stop = True

    def _poll(self):
        if self.preview is None:
            self.root.after(100, self._poll)
            return
        if self.stop:
            self.preview.close()
            return
        if self.preview._closed:
            return
        self._write(True)
        self.root.after(500, self._poll)

    def __exit__(self, *_):
        if not self.enabled:
            return
        signal.signal(signal.SIGTERM, self.previous)
        path = self.project / SESSION
        try:
            if json.loads(path.read_text()).get('nonce') == self.nonce:
                path.unlink()
        except FileNotFoundError:
            pass
        finally:
            self.lock.close()
