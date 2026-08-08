import http.server
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from iphone_cli.receiver import ALARMS, CLIPBOARDS, PENDING, TEXTS, Handler


class ReceiverTests(unittest.TestCase):
    phone_token = "phone-write-token-that-is-longer-than-thirty-two-characters"
    admin_token = "mac-admin-token-that-is-longer-than-thirty-two-characters"

    def setUp(self):
        TEXTS.clear()
        CLIPBOARDS.clear()
        ALARMS.clear()
        PENDING.clear()
        self.temporary = tempfile.TemporaryDirectory()
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.receiver_token = self.phone_token
        self.server.receiver_admin_token = self.admin_token
        self.server.inbox = Path(self.temporary.name)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.origin = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        auth: str | None = "phone",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        request_headers = dict(headers or {})
        if auth == "phone":
            request_headers["X-Auth"] = self.phone_token
        elif auth == "admin":
            request_headers["X-Admin-Auth"] = self.admin_token
        request = Request(
            self.origin + path,
            method=method,
            data=body,
            headers=request_headers,
        )
        try:
            with urlopen(request, timeout=2) as response:
                return response.status, response.read()
        except HTTPError as error:
            try:
                return error.code, error.read()
            finally:
                error.close()

    def register(self, kind: str, request_id: str) -> None:
        status, _ = self.request("POST", f"/pending/{kind}/{request_id}", auth="admin")
        self.assertEqual(status, 201)

    def test_health_is_public_but_mac_data_paths_require_admin_authentication(self):
        request_id = "1" * 32
        status, body = self.request("GET", "/health", auth=None)
        self.assertEqual(status, 200)
        self.assertIn(b"receiver up", body)

        status, _ = self.request("GET", f"/text/{request_id}", auth=None)
        self.assertEqual(status, 403)
        status, _ = self.request("GET", f"/text/{request_id}", auth="phone")
        self.assertEqual(status, 403)

    def test_screen_text_requires_pending_id_and_is_read_once(self):
        request_id = "2" * 32
        self.register("text", request_id)
        payload = json.dumps(
            {
                "screen": "Wi-Fi\nConnected",
                "current_app": "Settings",
                "selected_text": "Home Network",
            }
        ).encode()
        status, _ = self.request(
            "POST",
            "/text",
            body=payload,
            headers={"Content-Type": "application/json", "X-Screenshot-Id": request_id},
        )
        self.assertEqual(status, 200)

        status, body = self.request("GET", f"/text/{request_id}", auth="admin")
        self.assertEqual(status, 200)
        self.assertIn("UNTRUSTED IPHONE CONTENT", body.decode())
        self.assertIn("current app is **Settings**", body.decode())
        self.assertIn("<screen>\nWi-Fi\nConnected", body.decode())
        status, _ = self.request("GET", f"/text/{request_id}", auth="admin")
        self.assertEqual(status, 404)
        status, _ = self.request(
            "POST",
            "/text",
            body=payload,
            headers={"Content-Type": "application/json", "X-Screenshot-Id": request_id},
        )
        self.assertEqual(status, 409)

    def test_unsolicited_and_expired_response_ids_are_rejected(self):
        unsolicited_id = "3" * 32
        status, _ = self.request(
            "POST",
            "/clipboard",
            body=b"surprise",
            headers={"X-Screenshot-Id": unsolicited_id},
        )
        self.assertEqual(status, 409)

        expired_id = "4" * 32
        self.register("clipboard", expired_id)
        PENDING[expired_id] = ("clipboard", time.monotonic() - 1)
        status, _ = self.request(
            "POST",
            "/clipboard",
            body=b"late",
            headers={"X-Screenshot-Id": expired_id},
        )
        self.assertEqual(status, 409)

    def test_screenshot_is_saved_only_for_correlated_id(self):
        request_id = "5" * 32
        self.register("photo", request_id)
        image = b"\x89PNG\r\n\x1a\n" + b"test-image"
        status, _ = self.request(
            "POST",
            "/photo",
            body=image,
            headers={"Content-Type": "image/png", "X-Screenshot-Id": request_id},
        )
        self.assertEqual(status, 200)
        self.assertEqual((Path(self.temporary.name) / f"shot-{request_id}.png").read_bytes(), image)

    def test_empty_clipboard_round_trip(self):
        request_id = "6" * 32
        self.register("clipboard", request_id)
        status, _ = self.request(
            "POST", "/clipboard", body=b"", headers={"X-Screenshot-Id": request_id}
        )
        self.assertEqual(status, 200)
        status, body = self.request("GET", f"/clipboard/{request_id}", auth="admin")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")

    def test_alarm_text_becomes_structured_enabled_records(self):
        request_id = "7" * 32
        self.register("get-alarm", request_id)
        payload = json.dumps(
            {"alarms": "7:30 AM\tWake up\tWeekdays\ttrue\n8:15 AM\t\tNever\tfalse"}
        ).encode()
        status, _ = self.request(
            "POST",
            "/get-alarm",
            body=payload,
            headers={"Content-Type": "application/json", "X-Screenshot-Id": request_id},
        )
        self.assertEqual(status, 200)
        status, body = self.request("GET", f"/get-alarm/{request_id}", auth="admin")
        self.assertEqual(status, 200)
        alarms = json.loads(body)["alarms"]
        self.assertEqual(len(alarms), 2)
        self.assertEqual(alarms[1]["label"], "")
        self.assertFalse(alarms[1]["allows_snooze"])
        self.assertTrue(all(alarm["enabled"] for alarm in alarms))


if __name__ == "__main__":
    unittest.main()
