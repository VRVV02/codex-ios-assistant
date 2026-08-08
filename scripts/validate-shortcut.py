#!/usr/bin/env python3
"""Check the public Shortcut template's structure and secret-free placeholders."""

from __future__ import annotations

import plistlib
from pathlib import Path
import sys


RECEIVER_URL_PLACEHOLDER = "__IOS_ASSISTANT_RECEIVER_URL__"
TOKEN_PLACEHOLDER = "__IOS_ASSISTANT_RECEIVER_TOKEN__"
COMMAND_PREFIX_PLACEHOLDER = "__IOS_ASSISTANT_COMMAND_PREFIX__"
FORBIDDEN = ("@gmail.com", "/Users/", "trycloudflare.com", "hola")


def walk(value: object):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("shortcut/actions.template.plist")
    with path.open("rb") as source:
        actions = plistlib.load(source)
    if not isinstance(actions, list) or len(actions) != 95:
        raise SystemExit(f"expected 95 Shortcut actions, found {len(actions) if isinstance(actions, list) else 'non-list'}")

    strings = [value for value in walk(actions) if isinstance(value, str)]
    receiver_url_count = sum(value.count(RECEIVER_URL_PLACEHOLDER) for value in strings)
    token_count = sum(value.count(TOKEN_PLACEHOLDER) for value in strings)
    prefix_count = sum(value.count(COMMAND_PREFIX_PLACEHOLDER) for value in strings)
    if receiver_url_count != 4 or token_count != 4 or prefix_count != 28:
        raise SystemExit(
            "expected four URL/token placeholders and 28 command-prefix placeholders"
        )
    folded = "\n".join(strings).casefold()
    for forbidden in FORBIDDEN:
        if forbidden.casefold() in folded:
            raise SystemExit(f"private-looking value remains in template: {forbidden}")
    if "is.workflow.actions.speaktext" in folded:
        raise SystemExit("unsupported legacy speech branch remains in the Shortcut template")
    literal_web_origins = [
        value
        for value in strings
        if value.startswith("https://") and RECEIVER_URL_PLACEHOLDER not in value
    ]
    if literal_web_origins:
        raise SystemExit("literal HTTPS origin remains in the Shortcut template")

    seen: set[str] = set()
    groups: list[str] = []
    for index, action in enumerate(actions):
        parameters = action.get("WFWorkflowActionParameters", {})
        for value in walk(parameters):
            if isinstance(value, dict) and value.get("Type") == "ActionOutput":
                output_uuid = value.get("OutputUUID")
                if output_uuid not in seen:
                    raise SystemExit(f"action {index} has unresolved output reference {output_uuid}")
        mode = parameters.get("WFControlFlowMode")
        group = parameters.get("GroupingIdentifier")
        if mode == 0:
            groups.append(group)
        elif mode == 2:
            if not groups or groups.pop() != group:
                raise SystemExit(f"unbalanced control-flow group at action {index}")
        action_uuid = parameters.get("UUID")
        if action_uuid:
            seen.add(action_uuid)
    if groups:
        raise SystemExit("unclosed Shortcut control-flow groups")
    print(f"validated {len(actions)} sanitized Shortcut actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
