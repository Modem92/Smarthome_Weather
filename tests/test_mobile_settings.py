"""Real local TLS, dummy credentials, isolated storage; never provider HTTP."""
import http.client
import json
import ssl
import socket
import subprocess
import tempfile
import threading
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch, Mock

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.mobile.mobile_settings import PAIR_COOKIE, COOKIE_NAME, MobileSettingsError, MobileSettingsServer, private_address, local_addresses


class AddressDiscoveryTests(unittest.TestCase):
    def hostname_rows(self, *values):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (value, 0)) for value in values]

    def discover(self, output, hostname=("127.0.1.1",)):
        with patch("wetterstation.mobile.mobile_settings.sys.platform", "linux"), \
             patch("wetterstation.mobile.mobile_settings.subprocess.run", return_value=Mock(stdout=json.dumps(output))) as run, \
             patch("wetterstation.mobile.mobile_settings.socket.getaddrinfo", return_value=self.hostname_rows(*hostname)) as lookup:
            addresses = local_addresses()
        run.assert_called_once_with(["ip", "-j", "-4", "address", "show", "up", "scope", "global"],
                                    capture_output=True, text=True, encoding="utf-8", check=True, timeout=2)
        return addresses, lookup

    def test_pi_hostname_loopback_does_not_hide_assigned_wifi(self):
        addresses, lookup = self.discover([{"ifname": "wlan0", "addr_info": [
            {"family": "inet", "scope": "global", "local": "192.168.42.10"}]}])
        self.assertEqual(addresses, ["192.168.42.10", "127.0.0.1"])
        lookup.assert_not_called()

    def test_multiple_interfaces_deduplicate_and_reject_non_lan_values(self):
        values = ["192.168.42.10", "10.2.3.4", "192.168.42.10", "127.0.1.1", "8.8.8.8", "169.254.1.1", None, "bad"]
        rows = [{"addr_info": [{"family": "inet", "scope": "global", "local": v}]} for v in values]
        rows += [{"addr_info": [{"family": "inet6", "scope": "global", "local": "fd00::1"},
                                {"family": "inet", "scope": "host", "local": "172.16.1.2"}]}, None, {"addr_info": None}]
        self.assertEqual(self.discover(rows)[0], ["192.168.42.10", "10.2.3.4", "127.0.0.1"])

    def test_missing_failed_and_timed_out_ip_command_fall_back(self):
        failures = (FileNotFoundError(), subprocess.TimeoutExpired("ip", 2), subprocess.CalledProcessError(1, "ip"))
        for failure in failures:
            with self.subTest(failure=type(failure).__name__), patch("wetterstation.mobile.mobile_settings.sys.platform", "linux"), \
                 patch("wetterstation.mobile.mobile_settings.subprocess.run", side_effect=failure), \
                 patch("wetterstation.mobile.mobile_settings.socket.getaddrinfo", return_value=self.hostname_rows("192.168.42.10")):
                self.assertEqual(local_addresses(), ["192.168.42.10", "127.0.0.1"])

    def test_invalid_json_empty_or_wrong_shape_falls_back_without_crashing(self):
        for output in ("not json", "{}", "null", "[]", '[{"addr_info":null}]'):
            with self.subTest(output=output), patch("wetterstation.mobile.mobile_settings.sys.platform", "linux"), \
                 patch("wetterstation.mobile.mobile_settings.subprocess.run", return_value=Mock(stdout=output)), \
                 patch("wetterstation.mobile.mobile_settings.socket.getaddrinfo", return_value=self.hostname_rows("127.0.1.1")):
                self.assertEqual(local_addresses(), ["127.0.0.1"])

    def test_no_network_and_hostname_lookup_failure_keep_internal_test_address(self):
        with patch("wetterstation.mobile.mobile_settings.sys.platform", "linux"), \
             patch("wetterstation.mobile.mobile_settings.subprocess.run", return_value=Mock(stdout="[]")), \
             patch("wetterstation.mobile.mobile_settings.socket.getaddrinfo", side_effect=socket.gaierror()):
            self.assertEqual(local_addresses(), ["127.0.0.1"])

    def test_windows_hostname_discovery_is_preserved_and_does_not_invoke_ip(self):
        with patch("wetterstation.mobile.mobile_settings.sys.platform", "win32"), patch("wetterstation.mobile.mobile_settings.subprocess.run") as run, \
             patch("wetterstation.mobile.mobile_settings.socket.getaddrinfo", return_value=self.hostname_rows("192.168.1.2", "127.0.0.1", "192.168.1.2")):
            self.assertEqual(local_addresses(), ["192.168.1.2", "127.0.0.1"])
            run.assert_not_called()


class MobileSettingsTests(unittest.TestCase):
    def test_rejected_post_bodies_do_not_truncate_tls_error_responses(self):
        for _ in range(10):
            for headers, raw, expected in (({"Origin": "https://invalid.example"}, b"{}", 403),
                                            ({"Content-Type": "text/plain"}, b"{}", 400),
                                            ({}, b"x" * 4097, 400)):
                status, _, body = self.request("POST", "/api/settings", headers=headers, raw=raw)
                self.assertEqual(status, expected)
                self.assertIn("error", json.loads(body))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix="mobile-tests-")
        self.root = Path(self.temp.name)
        self.store = ApiKeyStore(path=self.root / "private" / "settings.json")
        self.store.save_configuration("Potsdam, 14467, Deutschland", "dummy-original-key")
        self.notifications = []
        self.service = MobileSettingsServer(self.store, on_change=self.notifications.append)
        self.service.start("127.0.0.1", 0)
        self.context = ssl.create_default_context(cafile=str(self.service.certificate_path))
        self.port = self.service._server.server_port
        self.cookie = self.csrf = ""

    def tearDown(self):
        self.service.stop()
        self.temp.cleanup()

    def request(self, method, path, data=None, headers=None, *, raw=None):
        request_headers = {}
        if self.cookie:
            request_headers["Cookie"] = self.cookie
        if method == "POST":
            request_headers.update({"Content-Type": "application/json", "Origin": self.service.url,
                                    "X-CSRF-Token": self.csrf})
        request_headers.update(headers or {})
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        connection = http.client.HTTPSConnection("127.0.0.1", self.port, context=self.context, timeout=3)
        try:
            connection.request(method, path, body=body, headers=request_headers)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def begin_pairing(self):
        status, headers, body = self.request("POST", "/api/pairing/start", {})
        self.assertEqual(status, 200)
        cookie = SimpleCookie(headers["Set-Cookie"])
        self.cookie = f"{PAIR_COOKIE}={cookie[PAIR_COOKIE].value}"
        code = self.service.pairing_display()["code"]
        self.assertNotIn(code.encode(), body)
        return code

    def login(self):
        code = self.begin_pairing()
        status, headers, _ = self.request("POST", "/api/login", {"code": code})
        self.assertEqual(status, 200)
        cookies = SimpleCookie(headers["Set-Cookie"])
        self.cookie = f"{COOKIE_NAME}={cookies[COOKIE_NAME].value}"
        status, _, body = self.request("GET", "/api/settings")
        self.assertEqual(status, 200)
        self.csrf = json.loads(body)["csrf"]
        return headers

    def test_settings_need_login_and_never_return_the_stored_key(self):
        status, _, body = self.request("GET", "/api/settings")
        self.assertEqual(status, 401)
        self.assertNotIn(b"dummy-original-key", body)
        headers = self.login()
        self.assertIn("Secure", headers["Set-Cookie"])
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        _, _, body = self.request("GET", "/api/settings")
        values = json.loads(body)
        self.assertEqual(set(values), {"location", "country_code", "countries", "api_key_configured", "csrf"})
        self.assertEqual(values["country_code"], "DE")
        self.assertTrue(values["api_key_configured"])
        self.assertNotIn(b"dummy-original-key", body)

    def test_both_fields_save_atomically_without_any_weather_request(self):
        self.login()
        with patch("wetterstation.weather.weather_service.OpenWeatherClient._request", side_effect=AssertionError("no provider HTTP")) as weather:
            status, _, body = self.request("POST", "/api/settings", {"location": "Potsdam, 14467, DE", "api_key": "dummy-new-key"})
            weather.assert_not_called()
        self.assertEqual(status, 200)
        self.assertEqual(self.store.load_location(), "Potsdam, 14467, DE")
        self.assertEqual(self.store.load_api_key(), "dummy-new-key")
        self.assertEqual(self.notifications, [True])
        self.assertNotIn(b"dummy-new-key", body)

    def test_blank_key_preserves_existing_credential(self):
        self.login()
        status, _, _ = self.request("POST", "/api/settings", {"location": "Potsdam", "api_key": ""})
        self.assertEqual(status, 200)
        self.assertEqual(self.store.load_api_key(), "dummy-original-key")
        self.assertEqual(self.notifications, [False])

    def test_international_country_save_preserves_key_and_layout_and_round_trips(self):
        self.login()
        before_layout = self.store.load_dashboard()
        for place, code in (("Wien", "AT"), ("Paris", "FR"), ("London", "GB"), ("New York", "US"), ("Tokio", "JP")):
            with patch("wetterstation.weather.weather_service.OpenWeatherClient._request", side_effect=AssertionError("no live HTTP")):
                status, _, body = self.request("POST", "/api/settings", {"location": place, "country_code": code})
            self.assertEqual(status, 200)
            _, _, body = self.request("GET", "/api/settings")
            snapshot = json.loads(body)
            self.assertEqual((snapshot["location"], snapshot["country_code"]), (place, code))
            self.assertEqual(self.store.load_api_key(), "dummy-original-key")
            self.assertEqual(self.store.load_dashboard(), before_layout)
            self.assertNotIn(b"dummy-original-key", body)
        before = self.store.path.read_bytes()
        self.assertEqual(self.request("POST", "/api/settings", {"location": "Paris", "country_code": "XX"})[0], 400)
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_cross_origin_host_and_missing_csrf_are_rejected(self):
        self.login()
        update = {"location": "Potsdam", "api_key": "dummy-unwanted-key"}
        for headers in ({"Origin": "https://example.invalid"}, {"Origin": "null"},
                        {"Host": "attacker.invalid"}, {"X-CSRF-Token": ""}):
            self.assertEqual(self.request("POST", "/api/settings", update, headers)[0], 403)
        self.assertEqual(self.store.load_api_key(), "dummy-original-key")
        self.assertEqual(self.notifications, [])

    def test_wrong_login_code_is_rate_limited(self):
        for _ in range(5):
            self.assertEqual(self.request("POST", "/api/login", {"code": "wrong-dummy"})[0], 401)
        status, headers, _ = self.request("POST", "/api/login", {"code": "DEMO-CODE-ONLY"})
        self.assertEqual(status, 429)
        self.assertEqual(headers["Retry-After"], "60")

    def test_logout_and_expired_sessions_cannot_save(self):
        self.login()
        token = SimpleCookie(self.cookie)[COOKIE_NAME].value
        with self.service._lock:
            self.service._sessions[token] = (0, self.csrf)
        self.assertEqual(self.request("POST", "/api/settings", {"location": "Potsdam"})[0], 401)
        self.login()
        self.assertEqual(self.request("POST", "/api/logout", {})[0], 200)
        self.assertEqual(self.request("GET", "/api/settings")[0], 401)

    def test_invalid_payload_does_not_overwrite_settings(self):
        self.login()
        original = self.store.path.read_bytes()
        invalid = ({"location": ""}, {"location": "x" * 81}, {"location": None},
                   {"location": "Potsdam", "api_key": 12},
                   {"location": "Potsdam", "api_key": "dummy\nkey"},
                   {"location": "Potsdam", "api_key": "x" * 257},
                   {"location": "Potsdam", "unknown": True}, [])
        for update in invalid:
            self.assertEqual(self.request("POST", "/api/settings", update)[0], 400)
            self.assertEqual(self.store.path.read_bytes(), original)

    def test_malformed_and_oversized_requests_are_rejected_without_secret_echo(self):
        self.login()
        for body in (b'{"dummy-secret":', b' ' * 4097, b'\xff'):
            status, _, response = self.request("POST", "/api/settings", raw=body)
            self.assertEqual(status, 400)
            self.assertNotIn(b"dummy-secret", response)
        self.assertEqual(self.request("POST", "/api/settings", {}, {"Content-Type": "text/plain"})[0], 400)

    def test_storage_failure_is_sanitized_and_keeps_original_file(self):
        self.login()
        original = self.store.path.read_bytes()
        with patch.object(self.store, "_write_settings", side_effect=OSError("dummy-secret")):
            status, _, body = self.request("POST", "/api/settings", {"location": "Potsdam", "api_key": "dummy-new-key"})
        self.assertEqual(status, 503)
        self.assertNotIn(b"dummy-secret", body)
        self.assertNotIn(b"dummy-new-key", body)
        self.assertEqual(self.store.path.read_bytes(), original)
        self.assertEqual(self.notifications, [])

    def test_only_bundled_assets_are_served_and_caching_is_disabled(self):
        for path, content_type in (("/", "text/html"), ("/app.js", "text/javascript"), ("/style.css", "text/css")):
            status, headers, body = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertIn(content_type, headers["Content-Type"])
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertEqual(headers["X-Frame-Options"], "DENY")
            self.assertNotIn(b"dummy-original-key", body)
        for path in ("/private/settings.json", "/../api_key_store.py", "/?api_key=dummy"):
            self.assertEqual(self.request("GET", path)[0], 404)

    def test_tls_certificate_requires_trust_and_plain_http_is_not_accepted(self):
        connection = http.client.HTTPSConnection("127.0.0.1", self.port, context=ssl.create_default_context(), timeout=3)
        try:
            with self.assertRaises(ssl.SSLCertVerificationError):
                connection.request("GET", "/")
        finally:
            connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        try:
            with self.assertRaises((OSError, http.client.HTTPException)):
                connection.request("GET", "/")
                connection.getresponse()
        finally:
            connection.close()

    def test_stopping_revokes_sessions_and_releases_port(self):
        self.login()
        token = SimpleCookie(self.cookie)[COOKIE_NAME].value
        self.service.stop()
        self.assertFalse(self.service.running)
        self.assertIsNone(self.service.session(token))
        self.assertIsNone(self.service.pairing_display())
        self.service.start("127.0.0.1", self.port)
        self.assertIsNone(self.service.session(token))

    def test_public_and_wildcard_addresses_are_never_bound(self):
        for address in ("0.0.0.0", "8.8.8.8", "::", "2001:db8::1", "169.254.1.1"):
            self.assertFalse(private_address(address))
            other = MobileSettingsServer(self.store)
            with self.assertRaises(MobileSettingsError):
                other.start(address)

    def test_pc_and_mobile_style_updates_preserve_independent_fields(self):
        barrier = threading.Barrier(2)
        errors = []
        def update(work):
            try:
                barrier.wait(timeout=2)
                work()
            except Exception as error:
                errors.append(type(error).__name__)
        pc = threading.Thread(target=update, args=(lambda: self.store.save_api_key("dummy-pc-key"),))
        phone = threading.Thread(target=update, args=(lambda: self.store.save_configuration("Potsdam", ""),))
        pc.start(); phone.start()
        pc.join(timeout=3); phone.join(timeout=3)
        self.assertEqual(errors, [])
        self.assertEqual(self.store.load_api_key(), "dummy-pc-key")
        self.assertEqual(self.store.load_location(), "Potsdam")


    def test_pairing_is_browser_bound_and_codes_never_leave_display(self):
        first=self.begin_pairing();cookie1=self.cookie
        _,_,body=self.request('GET','/api/pairing')
        self.assertEqual(json.loads(body)['state'],'active')
        _,_,again=self.request('POST','/api/pairing/start',{})
        self.assertEqual(len(self.service._pairings),1)
        self.assertNotIn(first.encode(),again)
        self.cookie='';self.request('POST','/api/pairing/start',{})
        # No pairing cookie: another browser cannot consume the visible code.
        self.assertEqual(self.request('POST','/api/login',{'code':first})[0],401)
        self.cookie=cookie1
        status,headers,_=self.request('POST','/api/login',{'code':first})
        self.assertEqual(status,200)
        self.assertEqual(self.request('POST','/api/login',{'code':first})[0],401)
        self.assertIsNotNone(self.service.pairing_display())
        self.assertNotEqual(self.service.pairing_display()['code'],first)

    def test_pairing_queue_limit_fifo_and_timeout_restore_display(self):
        cookies=[]
        for index in range(4):
            self.cookie=''
            _,headers,body=self.request('POST','/api/pairing/start',{})
            cookies.append(headers['Set-Cookie'].split(';')[0])
            self.assertEqual(json.loads(body)['position'],index)
        self.cookie=''
        self.assertEqual(self.request('POST','/api/pairing/start',{})[0],429)
        active=self.service.pairing_display()
        first=next(iter(self.service._pairings.values()))
        first['expires']=0
        self.assertNotEqual(self.service.pairing_display()['label'],active['label'])
        self.cookie=cookies[0]
        self.assertEqual(json.loads(self.request('GET','/api/pairing')[2])['state'],'expired')
        with self.service._lock:
            for pair in self.service._pairings.values():
                pair['created']=-10000;pair['expires']=0
        self.assertIsNone(self.service.pairing_display())

    def test_eight_sessions_survive_time_and_capacity_does_not_evict(self):
        tokens=[]
        for index in range(8):
            with self.service._lock:
                self.service._pair_attempts.clear();self.service._attempts.clear()
            self.cookie='';self.login()
            tokens.append(SimpleCookie(self.cookie)[COOKIE_NAME].value)
        self.cookie=''
        self.assertEqual(self.request('POST','/api/pairing/start',{})[0],409)
        with patch('wetterstation.mobile.mobile_settings.time.monotonic',return_value=10**12):
            for token in tokens:
                self.assertIsNotNone(self.service.session(token))
        self.service.stop();self.service.start('127.0.0.1',self.port)
        self.assertTrue(all(self.service.session(t) is None for t in tokens))
        self.assertIsNone(self.service.pairing_display())

    def test_pairing_start_requires_same_origin_and_preserves_settings(self):
        before=self.store.path.read_bytes()
        for headers in ({'Origin':'null'},{'Host':'bad.invalid'}):
            self.assertEqual(self.request('POST','/api/pairing/start',{},headers)[0],403)
        self.assertFalse(self.service._pairings)
        self.assertEqual(self.store.path.read_bytes(),before)

    def test_authenticated_reload_does_not_create_another_pairing(self):
        self.login()
        _,_,body=self.request('POST','/api/pairing/start',{})
        self.assertEqual(json.loads(body),{'state':'authenticated'})
        self.assertFalse(self.service._pairings)

    def test_last_free_session_releases_other_waiters_without_showing_useless_codes(self):
        self.service._sessions.update({f'dummy-{i}': (None, 'dummy-csrf') for i in range(7)})
        token1, _ = self.service.request_pairing('', '192.168.1.2')
        token2, _ = self.service.request_pairing('', '192.168.1.3')
        code = self.service.pairing_display()['code']
        token, _ = self.service.login(code, '192.168.1.2', token1)
        self.assertIsNotNone(self.service.session(token))
        self.assertEqual(self.service.pairing_status(token2), {'state': 'full'})
        self.assertIsNone(self.service.pairing_display())


if __name__ == "__main__":
    unittest.main(verbosity=2)
