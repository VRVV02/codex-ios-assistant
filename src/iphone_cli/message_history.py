"""Read-only adapter for the local openclaw/imsg Messages database CLI."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from typing import Any

from .errors import IPhoneError
from .transport import Result, command_from_environment


READ_ONLY_ACTIONS = frozenset({"chats", "history", "search", "group"})


def _imsg_command(action: str, arguments: list[str], *, json_output: bool) -> list[str]:
    if action not in READ_ONLY_ACTIONS:
        raise IPhoneError(f"Unsupported read-only Messages action: {action}")
    helper = command_from_environment(
        "IPHONE_HISTORY_IMSG_COMMAND",
        "imsg",
    )
    command = [*helper, action, *arguments]
    if json_output:
        command.append("--json")
    return command


def parse_ndjson(output: str) -> list[Any]:
    """Parse imsg's one-object-per-line JSON into one stable result list."""
    records: list[Any] = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise IPhoneError(f"imsg returned invalid JSON on line {line_number}.") from error
        if isinstance(value, list):
            records.extend(value)
        else:
            records.append(value)
    return records


def run_message_read(
    action: str,
    arguments: list[str],
    *,
    dry_run: bool,
    json_output: bool,
    timeout: float,
) -> Result:
    """Run one hard-coded finite read command; arbitrary imsg passthrough is forbidden."""
    command = _imsg_command(action, arguments, json_output=json_output)

    common: dict[str, Any] = {"command": command, "read_only": True}
    if dry_run:
        return Result(
            resource="messages",
            action=action,
            status="dry-run",
            summary=shlex.join(command),
            data=common,
        )

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
    except FileNotFoundError as error:
        raise IPhoneError(f"Required Messages history helper is not installed: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise IPhoneError(f"Timed out after {timeout:g}s while reading Messages history.") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise IPhoneError(f"{command[0]} failed: {detail}")

    if json_output:
        records = parse_ndjson(completed.stdout)
        return Result(
            resource="messages",
            action=action,
            status="completed",
            summary=f"{len(records)} record(s) read.",
            data={**common, "records": records},
        )

    output = completed.stdout.rstrip()
    return Result(
        resource="messages",
        action=action,
        status="completed",
        summary=output or "No results found.",
        data=common,
    )
