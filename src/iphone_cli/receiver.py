"""Authenticated loopback receiver for responses posted by the iPhone Shortcut."""

from __future__ import annotations

import http.server
import json
import os
from pathlib import Path
import re
import time

from .config import DATA_DIR, receiver_port, receiver_token


TEXTS: dict[str, str] = {}
CLIPBOARDS: dict[str, str] = {}
ALARMS: dict[str, list[dict[str, object]]] = {}
SCREEN_TEXT_POST_PATHS = {"/text", "/screentext"}
SCREENSHOT_POST_PATHS = {"/photo", "/screenshot", "/shot"}


def id_from_header(value: str) -> str | None:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,32}", value):
        return value
    digits = re.search(r"[0-9]{4,10}", value)
    return digits.group(0) if digits else None


def compose(payload: dict[str, object], screen: str) -> str:
    def section(tag: str, value: object) -> str | None:
        if isinstance(value, str) and value.strip():
            return f"<{tag}>\n{value.strip()}\n</{tag}>"
        return None

    parts: list[str] = []
    app = payload.get("current_app")
    if isinstance(app, str) and app.strip():
        parts.append(
            f"The user's current app is **{app.strip()}**. "
            "You can read the contents of their screen below."
        )
    selected = section("selected_text", payload.get("selected_text"))
    if selected:
        parts.append("The user has selected/highlighted this text on their screen:")
        parts.append(selected)
    parts.extend(
        value
        for value in (
            section("messages", payload.get("messages")),
            section("webpage", payload.get("webpage")),
            section("urls", payload.get("urls")),
            section("screen", screen),
        )
        if value
    )
    return "\n\n".join(parts)


def largest_multipart_payload(body: bytes, content_type: str) -> bytes | None:
    match = re.search(r'boundary="?([^";]+)"?', content_type)
    if not match:
        return None
    best: bytes | None = None
    for part in body.split(b"--" + match.group(1).encode()):
        if b"\r\n\r\n" not in part:
            continue
        payload = part.split(b"\r\n\r\n", 1)[1].rstrip(b"\r\n-")
        if best is None or len(payload) > len(best):
            best = payload
    return best


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodexIOSAssistantReceiver/1"

    @property
    def token(self) -> str:
        return self.server.receiver_token  # type: ignore[attr-defined]

    @property
    def inbox(self) -> Path:
        return self.server.inbox  # type: ignore[attr-defined]

    def _reply(self, code: int, text: str, *, content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if self.headers.get("X-Auth") == self.token:
            return True
        self._reply(403, "bad token\n")
        return False

    def do_GET(self) -> None:
        alarm = re.fullmatch(r"/get-alarm/([A-Za-z0-9_-]{1,32})", self.path)
        if alarm:
            if not self._authorized():
                return
            records = ALARMS.get(alarm.group(1))
            if records is None:
                return self._reply(404, "no alarms for that id\n")
            return self._reply(
                200,
                json.dumps({"alarms": records}, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            )
        clipboard = re.fullmatch(r"/clipboard/([A-Za-z0-9_-]{1,32})", self.path)
        if clipboard:
            if not self._authorized():
                return
            text = CLIPBOARDS.get(clipboard.group(1))
            if text is None:
                return self._reply(404, "no clipboard for that id\n")
            return self._reply(200, text)
        screen = re.fullmatch(r"/(?:screentext|text)/([A-Za-z0-9_-]{1,32})", self.path)
        if screen:
            if not self._authorized():
                return
            text = TEXTS.get(screen.group(1))
            if text is None:
                return self._reply(404, "no text for that id\n")
            return self._reply(200, text + "\n")
        if self.path in {"/", "/health"}:
            return self._reply(200, "codex-ios-assistant receiver up\n")
        self._reply(404, "unknown endpoint\n")

    def do_DELETE(self) -> None:
        alarm = re.fullmatch(r"/get-alarm/([A-Za-z0-9_-]{1,32})", self.path)
        if alarm:
            if not self._authorized():
                return
            ALARMS.pop(alarm.group(1), None)
            return self._reply(204, "")
        clipboard = re.fullmatch(r"/clipboard/([A-Za-z0-9_-]{1,32})", self.path)
        if clipboard:
            if not self._authorized():
                return
            CLIPBOARDS.pop(clipboard.group(1), None)
            return self._reply(204, "")
        screen = re.fullmatch(r"/(?:screentext|text)/([A-Za-z0-9_-]{1,32})", self.path)
        if screen:
            if not self._authorized():
                return
            TEXTS.pop(screen.group(1), None)
            return self._reply(204, "")
        self._reply(404, "unknown endpoint\n")

    def do_POST(self) -> None:
        if not self._authorized():
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return self._reply(400, "bad length\n")
        if not 0 <= length <= 50_000_000 or (length == 0 and self.path != "/clipboard"):
            return self._reply(400, "bad length\n")
        data = self.rfile.read(length)
        if self.path in SCREEN_TEXT_POST_PATHS:
            return self.handle_text(data)
        if self.path == "/clipboard":
            return self.handle_clipboard(data)
        if self.path == "/get-alarm":
            return self.handle_alarms(data)
        if self.path in SCREENSHOT_POST_PATHS:
            return self.handle_screenshot(data)
        self._reply(404, "unknown endpoint\n")

    def handle_screenshot(self, data: bytes) -> None:
        content_type = self.headers.get("Content-Type", "")
        if content_type.startswith("multipart/form-data"):
            data = largest_multipart_payload(data, content_type) or data
        extension = ".png" if data[:4] == b"\x89PNG" else ".jpg" if data[:2] == b"\xff\xd8" else ".bin"
        request_id = id_from_header(self.headers.get("X-Screenshot-Id", ""))
        if not request_id:
            return self._reply(400, "missing or unusable X-Screenshot-Id\n")
        path = self.inbox / f"shot-{request_id}{extension}"
        temporary = path.with_suffix(path.suffix + ".part")
        temporary.write_bytes(data)
        temporary.chmod(0o600)
        os.replace(temporary, path)
        print(f"saved {path.name} ({len(data)} bytes)", flush=True)
        self._reply(200, f"saved {path.name}\n")

    def handle_text(self, data: bytes) -> None:
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            return self._reply(400, "body is not valid JSON\n")
        text = payload.get("screen") if isinstance(payload, dict) else None
        if not isinstance(text, str) or not text.strip():
            if isinstance(payload, dict):
                text = next(
                    (value for value in payload.values() if isinstance(value, str) and value.strip()),
                    None,
                )
        if not isinstance(text, str) or not text:
            return self._reply(400, "no usable text in JSON\n")
        request_id = id_from_header(self.headers.get("X-Screenshot-Id", ""))
        if not request_id:
            return self._reply(400, "missing or unusable X-Screenshot-Id\n")
        TEXTS[request_id] = compose(payload, text)
        while len(TEXTS) > 200:
            TEXTS.pop(next(iter(TEXTS)))
        print(f"stored screen text for {request_id} ({len(text)} chars; value redacted)", flush=True)
        self._reply(200, f"stored text for {request_id}\n")

    def handle_clipboard(self, data: bytes) -> None:
        try:
            payload = json.loads(data) if data else ""
        except (ValueError, UnicodeDecodeError):
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                return self._reply(400, "clipboard body is not UTF-8 text\n")
        else:
            if isinstance(payload, str):
                text = payload
            elif isinstance(payload, dict) and isinstance(payload.get("clipboard"), str):
                text = payload["clipboard"]
            else:
                return self._reply(400, "clipboard JSON must be a string or clipboard field\n")
        request_id = id_from_header(self.headers.get("X-Screenshot-Id", ""))
        if not request_id:
            return self._reply(400, "missing or unusable X-Screenshot-Id\n")
        CLIPBOARDS[request_id] = text
        while len(CLIPBOARDS) > 200:
            CLIPBOARDS.pop(next(iter(CLIPBOARDS)))
        print(f"stored clipboard for {request_id} ({len(text)} chars; value redacted)", flush=True)
        self._reply(200, f"stored clipboard for {request_id}\n")

    def handle_alarms(self, data: bytes) -> None:
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            return self._reply(400, "body is not valid JSON\n")
        value = payload.get("alarms") if isinstance(payload, dict) else None
        if isinstance(value, str):
            records: list[dict[str, object]] = []
            for line in value.splitlines():
                if not line.strip():
                    continue
                parts = line.split("\t", 3)
                parts += [""] * (4 - len(parts))
                snooze = parts[3].strip().lower()
                allows_snooze = True if snooze in {"true", "yes", "1", "on"} else False if snooze in {"false", "no", "0", "off"} else None
                records.append(
                    {
                        "time": parts[0].strip(),
                        "label": parts[1].strip(),
                        "repeat_days": parts[2].strip(),
                        "allows_snooze": allows_snooze,
                        "enabled": True,
                    }
                )
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            records = value
        else:
            return self._reply(400, "alarms must be a text value or an array of objects\n")
        request_id = id_from_header(self.headers.get("X-Screenshot-Id", ""))
        if not request_id:
            return self._reply(400, "missing or unusable X-Screenshot-Id\n")
        ALARMS[request_id] = records
        while len(ALARMS) > 200:
            ALARMS.pop(next(iter(ALARMS)))
        print(f"stored {len(records)} active alarms for {request_id} (details redacted)", flush=True)
        self._reply(200, f"stored alarms for {request_id}\n")

    def log_message(self, format_string: str, *arguments: object) -> None:
        print(f"{self.address_string()} {format_string % arguments}", flush=True)


def main() -> int:
    inbox = DATA_DIR / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    os.chmod(DATA_DIR, 0o700)
    os.chmod(inbox, 0o700)
    token = receiver_token()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", receiver_port()), Handler)
    server.receiver_token = token  # type: ignore[attr-defined]
    server.inbox = inbox  # type: ignore[attr-defined]
    print(f"receiver listening on 127.0.0.1:{receiver_port()}, saving to {inbox}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
