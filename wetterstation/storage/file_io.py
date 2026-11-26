"""Bounded handling of transient Windows file sharing during atomic replacement."""
import os
import time


def replace_file(source, target) -> None:
    for delay in (0.02, 0.05, 0.1, 0.2, None):
        try:
            os.replace(source, target)
            return
        except OSError as exc:
            if delay is None or getattr(exc, "winerror", None) not in (5, 32, 33):
                raise
            time.sleep(delay)


class SettingsFileLock:
    """Serialize settings updates across local processes, with a short deadline."""
    def __init__(self, path):
        self.path = path
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open("a+b")
        try:
            self.stream.seek(0, os.SEEK_END)
            if self.stream.tell() == 0:
                self.stream.write(b"\0")
                self.stream.flush()
            deadline = time.monotonic() + 2
            while True:
                self.stream.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return self
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Einstellungen werden gerade in einer anderen Vorschau gespeichert.") from None
                    time.sleep(0.025)
        except Exception:
            self.stream.close()
            raise

    def __exit__(self, *_args):
        try:
            self.stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        finally:
            self.stream.close()
