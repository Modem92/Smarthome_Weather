"""LAN-only HTTPS settings with browser-bound, display-only pairing codes."""
from __future__ import annotations

import ipaddress
import json
import os
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.file_io import replace_file
from wetterstation.ui.widgets import CATALOG, revision, LayoutConflict
from wetterstation.weather.countries import COUNTRIES

WEB_ROOT = Path(__file__).resolve().parent / "web"
SESSION_SECONDS = 365 * 24 * 60 * 60  # Cookie only; server sessions end at process exit.
COOKIE_NAME = "__Host-wetterstation"
PAIR_COOKIE = "__Host-wetterstation-pair"
PAIR_SECONDS = 120
PRIVATE_NETWORKS = tuple(ipaddress.ip_network(value) for value in
                         ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8"))


class MobileSettingsError(Exception):
    """Safe user-facing message, never a raw server or credential exception."""


def private_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
        return address.version == 4 and any(address in network for network in PRIVATE_NETWORKS)
    except ValueError:
        return False


def local_addresses() -> list[str]:
    """Prefer assigned Linux interface addresses over hostname/hosts entries.

    Debian often resolves its own hostname to 127.0.1.1. Loopback remains
    available to isolated tests, but callers offering phone access must hide it.
    This function can block briefly and belongs on a worker, not the Tk thread.
    """
    addresses = []
    def add(value):
        if isinstance(value, str) and private_address(value) and not value.startswith("127.") and value not in addresses:
            addresses.append(value)

    if sys.platform == "linux":
        try:
            result = subprocess.run(["ip", "-j", "-4", "address", "show", "up", "scope", "global"],
                                    capture_output=True, text=True, encoding="utf-8", check=True, timeout=2)
            interfaces = json.loads(result.stdout)
            if isinstance(interfaces, list):
                for interface in interfaces:
                    if not isinstance(interface, dict) or not isinstance(interface.get("addr_info"), list):
                        continue
                    for info in interface["addr_info"]:
                        if isinstance(info, dict) and info.get("family") == "inet" and info.get("scope") == "global":
                            add(info.get("local"))
        except (OSError, subprocess.SubprocessError, ValueError, UnicodeError):
            pass
        if addresses:
            return addresses + ["127.0.0.1"]
    try:
        for row in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            add(row[4][0])
    except OSError:
        pass
    return addresses + ["127.0.0.1"]


def _atomic_bytes(path: Path, body: bytes) -> None:
    temporary = None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix="tls-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            temporary.chmod(0o600)
        replace_file(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def local_tls(folder: Path, host: str) -> tuple[ssl.SSLContext, str, Path]:
    """Create a local identity; never add it to an OS/browser trust store."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

    cert_path, key_path = folder / "certificate.pem", folder / "certificate-key.pem"
    now = datetime.now(timezone.utc)
    renew = not (cert_path.exists() and key_path.exists())
    if not renew:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        # Compatible with older bundled cryptography versions as well.
        expiry = cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after.replace(tzinfo=timezone.utc)
        renew = ipaddress.ip_address(host) not in sans.get_values_for_type(x509.IPAddress) or expiry <= now + timedelta(days=1)
    if renew:
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Wetterstation im Heimnetz")])
        ips = list(dict.fromkeys([host, *local_addresses()]))
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5)).not_valid_after(now + timedelta(days=365))
                .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip)) for ip in ips]), critical=False)
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .sign(key, hashes.SHA256()))
        _atomic_bytes(key_path, key.private_bytes(serialization.Encoding.PEM,
                                                serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        _atomic_bytes(cert_path, cert.public_bytes(serialization.Encoding.PEM))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_path, key_path)
    fingerprint = ":".join(f"{value:02X}" for value in cert.fingerprint(hashes.SHA256()))
    return context, fingerprint, cert_path


class _LocalServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False
    request_queue_size = 8

    def __init__(self, address, context, owner):
        self.context, self.owner = context, owner
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, _Handler)

    def process_request(self, request, client_address):
        if not private_address(client_address[0]) or not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            self.shutdown_request(request)

    def process_request_thread(self, request, client_address):
        try:
            request.settimeout(5)
            with self.context.wrap_socket(request, server_side=True) as secured:
                self.finish_request(secured, client_address)
        except Exception:
            pass  # No tracebacks or HTTP request bodies in logs.
        finally:
            self.shutdown_request(request)
            self.slots.release()

    def handle_error(self, *_args):
        pass


class MobileSettingsServer:
    def __init__(self, store: ApiKeyStore, *, on_change=None, on_layout_change=None, on_page_change=None, on_pairing_change=None, layout_only=False):
        self.store = store
        self.layout_only = layout_only
        self.on_change = on_change or (lambda _changed: None)
        self.on_layout_change = on_layout_change or (lambda *_args: None)
        self.on_page_change = on_page_change or (lambda *_args: None)
        self.on_pairing_change = on_pairing_change or (lambda: None)
        self._lock = threading.RLock()
        self._display_state = {"page_id": None, "revision": None, "error": None}
        self._sessions = {}
        self._attempts = deque(maxlen=20)
        self._pair_attempts = deque(maxlen=20)
        self._pairings = {}
        self._pair_number = 0
        self._server = None
        self._thread = None
        self._stopping = False
        self.url = self.fingerprint = ""
        self.certificate_path = None

    @property
    def running(self) -> bool:
        return self._server is not None and not self._stopping

    def publish_display(self, page_id, layout_revision, error=None, *, viewport=None):
        with self._lock:
            self._display_state = {"page_id": page_id, "revision": layout_revision, "error": error}
            if viewport:
                self._display_state["viewport"] = viewport

    def display_state(self):
        with self._lock:
            return dict(self._display_state)

    def start(self, host: str, port: int = 8765) -> None:
        if not private_address(host) or host not in local_addresses():
            raise MobileSettingsError("Bitte eine lokale Heimnetz-Adresse auswählen.")
        if self.running:
            raise MobileSettingsError("Die Handy-Verbindung ist bereits eingeschaltet.")
        server = None
        try:
            context, fingerprint, certificate = local_tls(self.store.path.parent / "mobile", host)
            server = _LocalServer((host, port), context, self)
            with self._lock:
                self.fingerprint, self.certificate_path = fingerprint, certificate
                self.url = f"https://{host}:{server.server_port}"
                self._stopping = False
                self._sessions.clear()
                self._attempts.clear()
                self._pairings.clear()
                self._pair_attempts.clear()
                thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5},
                                          name="mobile-settings", daemon=True)
                thread.start()
                self._thread, self._server = thread, server
        except Exception:
            if server:
                server.server_close()
            self._server = None
            raise MobileSettingsError("Handy-Verbindung konnte nicht gestartet werden. Bitte Netzwerkadresse, freien Port und Schreibzugriff prüfen.") from None

    def stop(self) -> None:
        with self._lock:
            self._stopping = True
            self._sessions.clear()
            self._pairings.clear()
            server, self._server = self._server, None
        if server:
            server.shutdown()
            server.server_close()
        self.on_pairing_change()

    def _expire_pairings(self):
        if len(self._sessions) >= 8:
            self._pairings.clear()
            return
        now = time.monotonic()
        for token, pair in list(self._pairings.items()):
            if now >= (pair["expires"] if pair["expires"] is not None else pair["created"] + PAIR_SECONDS*4):
                del self._pairings[token]
        if self._pairings:
            first = next(iter(self._pairings.values()))
            if first["expires"] is None:
                first["expires"] = now + PAIR_SECONDS

    def request_pairing(self, token: str, address: str):
        """Return an opaque browser cookie and public status, never the code."""
        with self._lock:
            self._expire_pairings()
            if self._stopping:
                return "stopped", {}
            if token in self._pairings:
                return token, self.pairing_status(token)
            if len(self._sessions) >= 8:
                return "full", {}
            now = time.monotonic()
            while self._pair_attempts and now - self._pair_attempts[0][0] >= 60:
                self._pair_attempts.popleft()
            if len(self._pairings) >= 4 or len(self._pair_attempts) >= 8 or sum(ip == address for _, ip in self._pair_attempts) >= 4:
                return "limited", {}
            self._pair_attempts.append((now, address))
            token = secrets.token_urlsafe(32)
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            raw = "".join(secrets.choice(alphabet) for _ in range(12))
            self._pair_number += 1
            self._pairings[token] = {"label": f"Anfrage {self._pair_number:02d}",
                "code": "-".join(raw[i:i+4] for i in range(0, 12, 4)), "created": now, "expires": None}
            self._expire_pairings()
            self.on_pairing_change()
            return token, self.pairing_status(token)

    def pairing_status(self, token: str):
        with self._lock:
            self._expire_pairings()
            pair = self._pairings.get(token)
            if not pair:
                return {"state": "full" if len(self._sessions) >= 8 else "expired"}
            position = list(self._pairings).index(token)
            return {"state": "active" if position == 0 else "waiting", "label": pair["label"],
                "position": position, "remaining": max(0, int(pair["expires"] - time.monotonic())) if position == 0 else None}

    def pairing_display(self):
        """Internal UI snapshot. This method must never back an HTTP response."""
        with self._lock:
            self._expire_pairings()
            if not self._pairings or self._stopping:
                return None
            pair = next(iter(self._pairings.values()))
            return {"label": pair["label"], "code": pair["code"], "url": self.url}

    def pairing_deadline(self):
        """Next internal expiry, without exposing codes or scheduling idle work."""
        with self._lock:
            self._expire_pairings()
            return min((p['expires'] if p['expires'] is not None else p['created'] + PAIR_SECONDS*4
                        for p in self._pairings.values()), default=None)

    def login(self, code: str, address: str, pairing_token: str = "") -> tuple[str, str]:
        with self._lock:
            now = time.monotonic()
            while self._attempts and now - self._attempts[0][0] >= 60:
                self._attempts.popleft()
            if len(self._attempts) >= 20 or sum(ip == address for _, ip in self._attempts) >= 5:
                return "limited", ""
            self._attempts.append((now, address))
            normalized = "".join(code.upper().split()).replace("-", "")
            self._expire_pairings()
            pair = self._pairings.get(pairing_token)
            expected = pair["code"].replace("-", "") if pair and next(iter(self._pairings)) == pairing_token else ""
            if self._stopping or not expected or not secrets.compare_digest(normalized.encode(), expected.encode()):
                return "denied", ""
            if len(self._sessions) >= 8:
                return "full", ""
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            self._sessions[token] = (None, csrf)
            del self._pairings[pairing_token]
            self._expire_pairings()
            self.on_pairing_change()
            return token, csrf

    def session(self, token: str):
        with self._lock:
            session = self._sessions.get(token)
            if self._stopping or not session or (session[0] is not None and session[0] <= time.monotonic()):
                self._sessions.pop(token, None)
                return None
            return session


class _Handler(BaseHTTPRequestHandler):
    server_version = "Wetterstation"

    def log_message(self, *_args):
        pass

    @property
    def owner(self):
        return self.server.owner

    def _response(self, status: int, body, content_type="application/json; charset=utf-8", cookie=None):
        # Closing TLS with an unread POST body can discard the error response.
        # Drain only a small, unambiguous body; never trust an unlimited length.
        if self.command == "POST" and not getattr(self, "_body_read", False):
            self._body_read = True
            lengths = self.headers.get_all("Content-Length", [])
            try:
                length = int(lengths[0]) if len(lengths) == 1 else 0
                if not self.headers.get("Transfer-Encoding") and 0 < length <= 65536:
                    self.rfile.read(length)
            except (ValueError, OSError):
                pass
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if status == 429:
            self.send_header("Retry-After", "60")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        self._response(code, {"error": "Anfrage konnte nicht verarbeitet werden."})

    def _allowed(self, *, write=False):
        hosts = self.headers.get_all("Host", [])
        expected = self.owner.url.split("://", 1)[1]
        if len(hosts) != 1 or hosts[0] != expected or self.owner._stopping:
            self._response(403, {"error": "Anfrageziel nicht freigegeben."})
            return False
        if write and self.headers.get("Origin") != self.owner.url:
            self._response(403, {"error": "Bitte die Seite direkt an der angezeigten Adresse öffnen."})
            return False
        return True

    def _session(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie[COOKIE_NAME].value if COOKIE_NAME in cookie else ""
        except CookieError:
            token = ""
        return token, self.owner.session(token)

    def _pair_cookie(self):
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            return cookie[PAIR_COOKIE].value if PAIR_COOKIE in cookie else ""
        except CookieError:
            return ""

    def do_GET(self):
        if not self._allowed():
            return
        try:
            if self.path == "/api/pairing":
                self._response(200, self.owner.pairing_status(self._pair_cookie()))
                return
            if self.path == "/api/display":
                _, session = self._session()
                if not session:
                    self._response(401, {"error": "Bitte mit dem Zugangscode vom PC anmelden."})
                    return
                self._response(200, self.owner.display_state())
                return
            if self.path == "/api/dashboard":
                _, session = self._session()
                if not session:
                    self._response(401, {"error": "Bitte mit dem Zugangscode vom PC anmelden."})
                    return
                layout = self.owner.store.load_dashboard()
                catalog = CATALOG
                if layout.get('version') in (3,4):
                    from wetterstation.designer.model import KINDS
                    catalog = {key: dict(value, min_width=1, min_height=1) for key, value in KINDS.items()}
                self._response(200, {"layout": layout, "revision": revision(layout), "catalog": catalog,
                                     "display": self.owner.display_state(), "demo": self.owner.layout_only})
                return
            if self.path == "/api/settings":
                _, session = self._session()
                if not session:
                    self._response(401, {"error": "Bitte mit dem Zugangscode vom PC anmelden."})
                    return
                # Only these values are ever returned; never serialize settings.
                location, code = self.owner.store.load_location_country()
                self._response(200, {"location": location,
                                     "country_code": code,
                                     "countries": [{"code": code, "name": row["name"]} for code, row in COUNTRIES.items()],
                                     "api_key_configured": self.owner.store.has_api_key(),
                                     "csrf": session[1]})
                return
            files = {"/": ("index.html", "text/html; charset=utf-8"),
                     "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                     "/layout.js": ("layout.js", "text/javascript; charset=utf-8"),
                     "/style.css": ("style.css", "text/css; charset=utf-8")}
            if self.path not in files:
                self._response(404, {"error": "Seite nicht gefunden."})
                return
            filename, content_type = files[self.path]
            self._response(200, (WEB_ROOT / filename).read_bytes(), content_type)
        except Exception:
            self._response(503, {"error": "Die lokalen Einstellungen oder die Seite konnten nicht gelesen werden."})

    def do_POST(self):
        self._body_read = False
        if not self._allowed(write=True):
            return
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") or len(lengths) != 1 or self.headers.get_content_type() != "application/json":
                raise ValueError
            length = int(lengths[0])
            limit = 32768 if self.path in ("/api/dashboard", "/api/dashboard/arrange") else 4096
            if not 0 < length <= limit:
                raise ValueError
            self._body_read = True
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError
            data = json.loads(body.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError
        except Exception:
            self._response(400, {"error": "Ungültige oder zu große Eingabe."})
            return
        if self.path == "/api/pairing/start":
            if data:
                self._response(400, {"error": "Ungültige Anmeldeanforderung."})
                return
            _, session = self._session()
            if session:
                self._response(200, {"state": "authenticated"})
                return
            token, state = self.owner.request_pairing(self._pair_cookie(), self.client_address[0])
            if token in ("limited", "full", "stopped"):
                self._response(409 if token == "full" else 429, {"error":
                    "Acht Browser sind bereits verbunden. Bitte einen davon abmelden." if token == "full" else
                    "Die Anmeldung ist momentan belegt. Bitte in einer Minute erneut versuchen."})
                return
            self._response(200, state, cookie=f"{PAIR_COOKIE}={token}; Path=/; Max-Age=600; Secure; HttpOnly; SameSite=Strict")
            return
        if self.path == "/api/login":
            if set(data) != {"code"} or not isinstance(data["code"], str) or len(data["code"]) > 64:
                self._response(400, {"error": "Bitte den Zugangscode vom PC eingeben."})
                return
            token, _ = self.owner.login(data["code"], self.client_address[0], self._pair_cookie())
            if token in ("limited", "denied", "full"):
                self._response(409 if token == "full" else 429 if token == "limited" else 401,
                               {"error": "Acht Browser sind bereits verbunden." if token == "full" else
                                "Zu viele Versuche. Bitte eine Minute warten." if token == "limited" else "Der Zugangscode stimmt nicht oder ist nicht mehr aktiv."})
                return
            self._response(200, {"ok": True}, cookie=f"{COOKIE_NAME}={token}; Path=/; Max-Age={SESSION_SECONDS}; Secure; HttpOnly; SameSite=Strict")
            return
        token, session = self._session()
        if not session:
            self._response(401, {"error": "Anmeldung abgelaufen. Bitte den Zugangscode erneut eingeben."})
            return
        if not secrets.compare_digest(self.headers.get("X-CSRF-Token", "").encode(), session[1].encode()):
            self._response(403, {"error": "Bitte die Einstellungsseite neu laden."})
            return
        if self.path == "/api/logout":
            with self.owner._lock:
                self.owner._sessions.pop(token, None)
            self._response(200, {"ok": True}, cookie=f"{COOKIE_NAME}=; Path=/; Max-Age=0; Secure; HttpOnly; SameSite=Strict")
            return
        if self.path == "/api/display/page":
            if set(data) != {"page_id", "revision"} or not isinstance(data["page_id"], str) or not isinstance(data["revision"], str):
                self._response(400, {"error": "Ungültige Seite."})
                return
            try:
                layout = self.owner.store.load_dashboard()
                if data["revision"] != revision(layout):
                    self._response(409, {"error": "Das Layout wurde inzwischen geändert. Bitte neu laden."})
                    return
                if data["page_id"] not in [page["id"] for page in layout["pages"]]:
                    self._response(400, {"error": "Diese Seite gibt es nicht mehr."})
                    return
                self.owner.on_page_change(data["page_id"])
                self._response(200, {"ok": True})
            except Exception:
                self._response(503, {"error": "Die Seite konnte nicht am Display angezeigt werden."})
            return
        if self.path == '/api/dashboard/arrange':
            if set(data) != {'operations', 'revision', 'page_id'} or not isinstance(data['revision'], str) or not isinstance(data['page_id'], str):
                self._response(400, {'error': 'Ungültiger Anordnungsbefehl.'})
                return
            try:
                # Page identity is checked before committing a potentially valid command list.
                from wetterstation.designer.model import arrangement
                current = self.owner.store.load_dashboard()
                proposed = self.owner.store.propose_arrangement(data['operations'], data['revision'])
                if data['page_id'] not in [p['id'] for p in proposed['pages']]:
                    raise ValueError('Seite fehlt.')
                layout = self.owner.store.arrange_dashboard(data['operations'], data['revision'])
            except LayoutConflict:
                self._response(409, {'error': 'Die Gestaltung wurde inzwischen geändert. Bitte neu laden.'})
                return
            except ValueError:
                self._response(400, {'error': 'Anordnung ungültig oder Widget gesperrt.'})
                return
            except Exception:
                self._response(503, {'error': 'Anordnung konnte nicht gespeichert werden.'})
                return
            try:
                self.owner.on_layout_change(layout, data['page_id'])
            except Exception:
                self._response(200, {'layout': layout, 'revision': revision(layout), 'message': 'Gespeichert; Displayübernahme noch nicht bestätigt.'})
                return
            self._response(200, {'layout': layout, 'revision': revision(layout), 'message': 'Anordnung gespeichert.'})
            return
        if self.path == "/api/dashboard":
            if set(data) != {"layout", "revision", "page_id"} or not isinstance(data["revision"], str) or not isinstance(data["page_id"], str):
                self._response(400, {"error": "Ungültiges Widget-Layout."})
                return
            try:
                if self.owner.store.load_dashboard().get('version') in (3,4):
                    raise ValueError('Für diese Gestaltung nur Anordnungsbefehle verwenden.')
                if not isinstance(data["layout"], dict) or not isinstance(data["layout"].get("pages"), list) or data["page_id"] not in [p.get("id") for p in data["layout"]["pages"] if isinstance(p, dict)]:
                    raise ValueError("invalid page")
                layout = self.owner.store.save_dashboard(data["layout"], data["revision"])
            except LayoutConflict:
                self._response(409, {"error": "Das Layout wurde inzwischen geändert. Lade es neu, bevor du weiterbearbeitest."})
                return
            except ValueError:
                self._response(400, {"error": "Ungültiges Widget-Layout. Bitte Größe und Inhalte prüfen."})
                return
            except Exception:
                self._response(503, {"error": "Das Widget-Layout konnte nicht gespeichert werden."})
                return
            try:
                self.owner.on_layout_change(layout, data["page_id"])
            except Exception:
                self._response(200, {"layout": layout, "revision": revision(layout), "message": "Gespeichert. Bitte die Vorschau neu starten."})
                return
            self._response(200, {"layout": layout, "revision": revision(layout), "message": "Layout gespeichert und an die Wetterstation gesendet."})
            return
        if self.path != "/api/settings":
            self._response(404, {"error": "Funktion nicht gefunden."})
            return
        if self.owner.layout_only:
            self._response(403, {"error": "Die Widget-Demo erlaubt nur Layoutänderungen; Ort und Schlüssel bleiben unberührt."})
            return
        if set(data) - {"location", "country_code", "api_key"} or "location" not in data:
            self._response(400, {"error": "Bitte nur Ort und optional einen neuen Schlüssel angeben."})
            return
        try:
            changed = self.owner.store.save_configuration(data["location"], data.get("api_key", ""),
                                                         country_code=data.get("country_code"))
        except ValueError:
            self._response(400, {"error": "Bitte Ort (höchstens 80 Zeichen), ein gültiges Land und einen gültigen Schlüssel eingeben."})
            return
        except Exception:
            self._response(503, {"error": "Speichern fehlgeschlagen. Die Einstellungen wurden nicht übernommen."})
            return
        try:
            self.owner.on_change(changed)
        except Exception:
            self._response(200, {"ok": True, "message": "Gespeichert. Bitte die PC-Vorschau neu laden."})
            return
        self._response(200, {"ok": True, "message": "Gespeichert. Ein vorhandener Schlüssel bleibt bei leerem Feld erhalten. Die API-Gültigkeit wurde nicht geprüft."})
