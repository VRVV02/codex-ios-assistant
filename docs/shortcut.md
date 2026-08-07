# Shortcut source and maintenance

`shortcut/actions.template.plist` is a sanitized list of 95 native Shortcuts actions. It contains placeholders instead of a user's hostname and receiver token:

```text
__IOS_ASSISTANT_PUBLIC_URL__
__IOS_ASSISTANT_RECEIVER_TOKEN__
```

`scripts/render-shortcut.py` substitutes values from the private config and writes the ignored, mode-`0600` artifact under `build/`.

## The Command-V installation technique

Shortcuts on macOS uses the pasteboard type `com.apple.shortcuts.action`. Each copied action is a separate pasteboard item containing a binary property list. `scripts/copy-shortcut-actions.swift` recreates that representation from the committed action array and verifies every item before reporting success.

This is why the workflow can be installed without signing or importing a `.shortcut` package:

1. `scripts/copy-shortcut` renders the private action list.
2. The Swift helper serializes each action as one native pasteboard item.
3. The user creates a blank Shortcut and presses Command-V once.
4. Shortcuts reconstructs the complete action graph, including UUID references and grouped control flow.

The technique depends on an implementation detail of the macOS Shortcuts app. If Apple changes the pasteboard representation, the committed plist remains readable but the copy helper may need an update.

## Current branches

The action graph dispatches the incoming text by prefix and handles:

- timer start/pause/resume/cancel;
- flashlight, Low Power Mode, and Control Center;
- call, clipboard read/write, and generic URL opening;
- screen text, screenshot, and Home Screen;
- enabled-alarm listing, alarm creation, and time-based alarm disabling.

Screen text and screenshots are intentionally different commands and endpoints. `hola screentext <id>` extracts native on-screen content and posts JSON to `/text`. `hola screenshot <id>` takes an image and posts it to `/photo`.

The alarm list branch uses `Find Alarms` with an enabled filter before formatting results. This avoids iterating through hundreds of disabled alarms. The off branch filters enabled alarms by hour and minute, then disables all exact-time matches, including unlabeled alarms.

## Inspect copied actions while developing

`scripts/inspect-shortcuts-clipboard.swift` prints the property lists currently present under the Shortcuts action pasteboard type.

To study a new native action:

1. Build the smallest possible scratch Shortcut in the Shortcuts app.
2. Select only the action or tightly coupled block you need.
3. Press Command-C.
4. Run `swift scripts/inspect-shortcuts-clipboard.swift` and save the terminal output outside the repo while studying it.
5. Identify action identifiers, parameters, output UUIDs, and control-flow grouping identifiers.
6. Recreate the change in a working copy of the action plist.
7. Run `make test`, especially the structural validator.
8. Copy the full result into a new blank Shortcut and exercise both the changed and neighboring branches on a real iPhone.

Dynamic values usually contain an `ActionOutput` attachment with an `OutputUUID`. That UUID must refer to an earlier action. Conditional and repeat blocks share a `GroupingIdentifier`; their start/end modes must remain balanced. Alarm predicates also contain archived native objects, so treat those blocks as opaque unless you have reproduced and inspected the exact change in Shortcuts.

## Source-of-truth policy

The sanitized plist is the public source of truth. Never commit:

- a rendered plist from `build/`;
- an exported Shortcut containing a real token or hostname;
- screenshots of the user's messages, screen contents, contacts, or alarms;
- Cloudflare credential JSON files.

After a functional Shortcut edit, update the branch documentation and add or strengthen validation. `scripts/validate-shortcut.py` checks the action count, placeholder count, forbidden personal strings, backward output references, and balanced control-flow groups.
