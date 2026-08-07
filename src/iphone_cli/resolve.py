"""Resolve friendly contacts and Messages threads from local Mac data."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
from dataclasses import dataclass
from urllib.parse import quote
from uuid import UUID

from .errors import IPhoneError
from .urls import looks_like_phone, normalize_phone


@dataclass(frozen=True)
class Contact:
    name: str
    phones: tuple[str, ...]
    emails: tuple[str, ...]


@dataclass(frozen=True)
class Chat:
    row_id: int
    label: str
    identifier: str
    participants: tuple[str, ...]
    is_group: bool
    service: str
    last_message_at: str


@dataclass(frozen=True)
class MessageComposeTarget:
    label: str
    address: str | None = None
    group_id: str | None = None

    @property
    def is_group(self) -> bool:
        return self.group_id is not None


def _command_from_environment(name: str, default: str) -> list[str]:
    return shlex.split(os.environ.get(name, default))


def _run(command: list[str], *, timeout: float = 20) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as error:
        raise IPhoneError(f"Required helper is not installed: {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise IPhoneError(f"Timed out while running {command[0]}.") from error

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise IPhoneError(f"{command[0]} failed: {detail}")
    return completed.stdout


def parse_contacts_output(output: str) -> list[Contact]:
    contacts: list[Contact] = []
    name: str | None = None
    values: list[str] = []

    def flush() -> None:
        nonlocal name, values
        if name:
            phones = tuple(value for value in values if looks_like_phone(value))
            emails = tuple(value for value in values if "@" in value)
            contacts.append(Contact(name=name, phones=phones, emails=emails))
        name = None
        values = []

    for line in output.splitlines() + [""]:
        if not line.strip():
            flush()
        elif line.startswith("  "):
            values.append(line.strip())
        elif line != "No contacts found." and not line.startswith("Showing "):
            flush()
            name = line.strip()
    return contacts


def search_contacts(query: str) -> list[Contact]:
    command = _command_from_environment("IPHONE_CONTACTS_COMMAND", "contacts")
    output = _run([*command, "search", query])
    return parse_contacts_output(output)


def _contact_error(query: str, contacts: list[Contact]) -> IPhoneError:
    if not contacts:
        return IPhoneError(f"No contact matched {query!r}. Pass a phone number instead.")
    candidates = "; ".join(
        f"{contact.name} ({', '.join(contact.phones) or 'no phone'})" for contact in contacts[:8]
    )
    return IPhoneError(
        f"Contact {query!r} is ambiguous: {candidates}. "
        "Use the full contact name or pass the phone number directly."
    )


def resolve_contact_phone(query: str) -> str:
    query = query.strip()
    if looks_like_phone(query):
        return normalize_phone(query)

    contacts = search_contacts(query)
    exact = [contact for contact in contacts if contact.name.casefold() == query.casefold()]
    candidates = exact or contacts
    if len(candidates) != 1:
        raise _contact_error(query, candidates)

    phones = tuple(dict.fromkeys(normalize_phone(phone) for phone in candidates[0].phones))
    if len(phones) != 1:
        if not phones:
            raise IPhoneError(f"Contact {candidates[0].name!r} has no phone number.")
        joined = ", ".join(phones)
        raise IPhoneError(
            f"Contact {candidates[0].name!r} has multiple phone numbers: {joined}. "
            "Pass the desired number directly."
        )
    return phones[0]


def _load_chats(limit: int = 5000) -> list[Chat]:
    command = _command_from_environment(
        "IPHONE_HISTORY_IMSG_COMMAND",
        "imsg",
    )
    output = _run([*command, "chats", "--limit", str(limit), "--json"], timeout=30)
    chats: list[Chat] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        labels = [
            value.get("contact_name", ""),
            value.get("display_name", ""),
            value.get("name", ""),
        ]
        label = next((item for item in labels if item), value.get("identifier", ""))
        chats.append(
            Chat(
                row_id=int(value.get("id") or 0),
                label=label,
                identifier=value.get("identifier", ""),
                participants=tuple(value.get("participants") or ()),
                is_group=bool(value.get("is_group")),
                service=value.get("service", ""),
                last_message_at=value.get("last_message_at", ""),
            )
        )
    return chats


def _match_score(value: str, query: str) -> int | None:
    if value == query:
        return 0
    folded_value = value.casefold()
    folded_query = query.casefold()
    if folded_value == folded_query:
        return 1
    if value.startswith(query):
        return 2
    if folded_value.startswith(folded_query):
        return 3
    if query in value:
        return 4
    if folded_query in folded_value:
        return 5
    return None


def _resolve_named_message_chat(query: str) -> Chat | None:
    matches: list[tuple[int, Chat]] = []
    for chat in _load_chats():
        values = [chat.label, chat.identifier, *chat.participants]
        scores = [
            score
            for value in values
            if (score := _match_score(value, query)) is not None
        ]
        if scores:
            matches.append((min(scores), chat))

    if not matches:
        return None

    best_score = min(score for score, _ in matches)
    best = [chat for score, chat in matches if score == best_score]

    # A single person can have parallel iMessage/SMS/RCS chats. Collapse those
    # by participant while retaining the most recent entry returned by imsg.
    unique: dict[tuple[bool, str], Chat] = {}
    for chat in best:
        identity = (
            chat.identifier
            if chat.is_group
            else (chat.participants[0] if chat.participants else chat.identifier)
        )
        unique.setdefault((chat.is_group, identity), chat)
    best = list(unique.values())

    if len(best) != 1:
        choices = "; ".join(
            f"{chat.label} ({chat.identifier or ', '.join(chat.participants)})" for chat in best[:8]
        )
        raise IPhoneError(
            f"Messages thread {query!r} is ambiguous: {choices}. "
            "Use the exact capitalization, a full contact name, phone number, or email address."
        )

    return best[0]


def _messages_database_path() -> Path:
    configured = os.environ.get("IPHONE_MESSAGES_DB", "~/Library/Messages/chat.db")
    return Path(configured).expanduser()


def _load_group_id(chat: Chat) -> str:
    if chat.row_id <= 0:
        raise IPhoneError(f"Messages thread {chat.label!r} has no usable local chat ID.")

    database = _messages_database_path()
    database_uri = f"file:{quote(str(database), safe='/')}?mode=ro"
    try:
        with sqlite3.connect(database_uri, uri=True) as connection:
            row = connection.execute(
                "SELECT group_id FROM chat WHERE ROWID = ?",
                (chat.row_id,),
            ).fetchone()
    except sqlite3.Error as error:
        raise IPhoneError(f"Could not read the Messages database at {database}: {error}") from error

    group_id = str(row[0]).strip() if row and row[0] else ""
    try:
        normalized = str(UUID(group_id)).upper()
    except ValueError as error:
        raise IPhoneError(
            f"Messages group {chat.label!r} has no synced group identifier."
        ) from error
    return normalized


def resolve_message_recipient(query: str) -> str:
    """Resolve a phone/email or a named recent 1:1 Messages thread."""
    query = query.strip()
    if looks_like_phone(query):
        return normalize_phone(query)
    if "@" in query and " " not in query:
        return query

    chat = _resolve_named_message_chat(query)
    if chat is None:
        return resolve_contact_phone(query)

    if chat.is_group:
        raise IPhoneError(
            f"{chat.label!r} is a group chat. Use 'iphone messages compose --to "
            f'"{chat.label}" --body "..."' " to open an unsent group draft, or open "
            "a specific message by GUID."
        )
    if not chat.participants:
        raise IPhoneError(f"Messages thread {chat.label!r} has no usable participant address.")
    return chat.participants[0]


def resolve_message_compose_target(query: str) -> MessageComposeTarget:
    """Resolve an address or an existing named group for an unsent draft."""
    query = query.strip()
    if looks_like_phone(query):
        address = normalize_phone(query)
        return MessageComposeTarget(label=query, address=address)
    if "@" in query and " " not in query:
        return MessageComposeTarget(label=query, address=query)

    chat = _resolve_named_message_chat(query)
    if chat is None:
        address = resolve_contact_phone(query)
        return MessageComposeTarget(label=query, address=address)
    if chat.is_group:
        return MessageComposeTarget(label=chat.label, group_id=_load_group_id(chat))
    if not chat.participants:
        raise IPhoneError(f"Messages thread {chat.label!r} has no usable participant address.")
    return MessageComposeTarget(label=chat.label, address=chat.participants[0])
