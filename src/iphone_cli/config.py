"""Small, dependency-free configuration loader for codex-ios-assistant."""

from __future__ import annotations

import os
import re
import shlex
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from .errors import IPhoneError


APP_NAME = "codex-ios-assistant"
CONFIG_DIR = Path(
    os.environ.get("IOS_ASSISTANT_CONFIG_DIR", Path.home() / ".config" / APP_NAME)
).expanduser()
CONFIG_FILE = Path(
    os.environ.get("IOS_ASSISTANT_CONFIG_FILE", CONFIG_DIR / "config.env")
).expanduser()
DATA_DIR = Path(
    os.environ.get("IOS_ASSISTANT_DATA_DIR", Path.home() / ".local" / "share" / APP_NAME)
).expanduser()
LOG_DIR = Path(
    os.environ.get("IOS_ASSISTANT_LOG_DIR", Path.home() / "Library" / "Logs" / APP_NAME)
).expanduser()


@lru_cache(maxsize=1)
def file_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not CONFIG_FILE.is_file():
        return values
    for line_number, raw_line in enumerate(CONFIG_FILE.read_text().splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise IPhoneError(f"Invalid configuration at {CONFIG_FILE}:{line_number}.")
        name, raw_value = line.split("=", 1)
        name = name.strip()
        try:
            parsed = shlex.split(raw_value.strip(), posix=True)
        except ValueError as error:
            raise IPhoneError(
                f"Invalid quoted value at {CONFIG_FILE}:{line_number}: {error}"
            ) from error
        if len(parsed) > 1:
            raise IPhoneError(
                f"Configuration values containing spaces must be quoted at "
                f"{CONFIG_FILE}:{line_number}."
            )
        values[name] = parsed[0] if parsed else ""
    return values


def value(name: str, *, required: bool = False) -> str:
    result = os.environ.get(name, file_values().get(name, "")).strip()
    if required and not result:
        raise IPhoneError(
            f"{name} is not configured. Run scripts/configure or edit {CONFIG_FILE}."
        )
    return result


def message_target() -> str:
    return value("IPHONE_MSG_TARGET", required=True)


def receiver_token() -> str:
    token = value("IPHONE_RECEIVER_TOKEN", required=True)
    if len(token) < 32:
        raise IPhoneError("IPHONE_RECEIVER_TOKEN must contain at least 32 characters.")
    return token


def receiver_admin_token() -> str:
    token = value("IPHONE_RECEIVER_ADMIN_TOKEN", required=True)
    if len(token) < 32:
        raise IPhoneError(
            "IPHONE_RECEIVER_ADMIN_TOKEN must contain at least 32 characters."
        )
    return token


def command_prefix() -> str:
    prefix = value("IPHONE_COMMAND_PREFIX") or "ios_command"
    if not re.fullmatch(r"[A-Za-z0-9_-]{4,64}", prefix):
        raise IPhoneError(
            "IPHONE_COMMAND_PREFIX must be 4-64 letters, numbers, hyphens, or underscores."
        )
    return prefix


def shortcut_receiver_url() -> str:
    """Return the tailnet-only HTTPS origin embedded in the iPhone Shortcut.

    ``IPHONE_PUBLIC_URL`` remains a read-only compatibility fallback so existing
    configs fail with a useful host validation error instead of disappearing.
    """
    url = (value("IPHONE_RECEIVER_URL") or value("IPHONE_PUBLIC_URL", required=True)).rstrip("/")
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise IPhoneError("IPHONE_RECEIVER_URL contains an invalid port.") from error
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise IPhoneError(
            "IPHONE_RECEIVER_URL must be an HTTPS origin without a path."
        )
    hostname = parsed.hostname.lower().rstrip(".")
    if not hostname.endswith(".ts.net"):
        raise IPhoneError(
            "IPHONE_RECEIVER_URL must be a private Tailscale HTTPS origin ending in .ts.net."
        )
    return url


def receiver_port() -> int:
    raw = value("IPHONE_RECEIVER_PORT") or "8787"
    try:
        port = int(raw)
    except ValueError as error:
        raise IPhoneError("IPHONE_RECEIVER_PORT must be an integer.") from error
    if not 1 <= port <= 65535:
        raise IPhoneError("IPHONE_RECEIVER_PORT must be between 1 and 65535.")
    return port


def receiver_url() -> str:
    return f"http://127.0.0.1:{receiver_port()}"


def sender_socket() -> Path:
    configured = value("IPHONE_SENDER_SOCKET")
    if configured:
        return Path(configured).expanduser()
    return Path("/tmp") / f"codex-ios-assistant-{os.getuid()}.sock"
