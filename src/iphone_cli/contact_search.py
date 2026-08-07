"""Read-only adapter for the local macOS Contacts search helper."""

from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

from .errors import IPhoneError
from .resolve import Contact, parse_contacts_output
from .transport import Result, command_from_environment


def _contacts_command(query: str) -> list[str]:
    query = query.strip()
    if not query:
        raise IPhoneError("Contact search query cannot be empty.")
    helper = command_from_environment("IPHONE_CONTACTS_COMMAND", "contacts")
    return [*helper, "search", query]


def _contact_record(contact: Contact) -> dict[str, Any]:
    return {
        "name": contact.name,
        "emails": list(contact.emails),
        "phones": list(contact.phones),
    }


def run_contact_search(
    query: str,
    *,
    dry_run: bool,
    json_output: bool,
    timeout: float,
) -> Result:
    """Search Contacts without exposing arbitrary helper commands."""
    command = _contacts_command(query)
    common: dict[str, Any] = {
        "command": command,
        "query": query.strip(),
        "read_only": True,
    }
    if dry_run:
        return Result(
            resource="contacts",
            action="search",
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
        raise IPhoneError(f"Required Contacts helper is not installed: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise IPhoneError(f"Timed out after {timeout:g}s while searching Contacts.") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise IPhoneError(f"{command[0]} failed: {detail}")

    output = completed.stdout.rstrip()
    if json_output:
        contacts = parse_contacts_output(completed.stdout)
        records = [_contact_record(contact) for contact in contacts]
        return Result(
            resource="contacts",
            action="search",
            status="completed",
            summary=f"{len(records)} contact(s) found.",
            data={**common, "contacts": records},
        )

    return Result(
        resource="contacts",
        action="search",
        status="completed",
        summary=output or "No contacts found.",
        data=common,
    )
