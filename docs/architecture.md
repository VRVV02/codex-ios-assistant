# Architecture and protocol

The system separates command delivery from response delivery. Commands are small private iMessages; sensitive responses use HTTPS and never travel back through Messages.

## Components

1. The `iphone` CLI validates intent, builds Apple URLs or Shortcut protocol commands, and presents stable text/JSON results.
2. The Codex skill teaches an agent when and how to invoke that CLI safely.
3. The sender LaunchAgent accepts a narrowly validated local command over a mode-`0600` Unix socket and automates Messages in the user's GUI session.
4. An iPhone Message personal automation invokes the 95-action Shortcut for `hola …` messages.
5. The Shortcut performs native iOS actions. Response-producing branches POST to `/text`, `/photo`, `/clipboard`, or `/get-alarm`.
6. A named Cloudflare Tunnel forwards the stable public HTTPS hostname to the receiver bound on `127.0.0.1:8787`.
7. The receiver correlates responses by a random five-digit request ID. The CLI polls the loopback receiver until the matching result arrives or times out.

## Command protocol

Every outbound command is one line beginning with `hola `. The current Shortcut recognizes these forms:

```text
hola openurl <url>
hola homescreen
hola screenshot <id>
hola screentext <id>
hola getclipboard <id>
hola copytoclipboard <text>
hola alarm get <id>
hola alarm set <HH:MM> <label>
hola alarm off <HH:MM>
hola timer start <seconds>
hola timer pause
hola timer resume
hola timer cancel
hola flashlight on|off
hola lowpower on|off
hola controlcenter open|close
hola call <phone>
```

The CLI is the supported interface. These protocol strings are documented for maintainers, not as an invitation to bypass input validation.

## Response protocol

All data endpoints require the configured token in `X-Auth`. Correlation IDs use the `X-Screenshot-Id` header for historical compatibility.

| Shortcut request | HTTP response | CLI behavior |
| --- | --- | --- |
| `hola screentext <id>` | JSON to `POST /text` | Polls `GET /text/<id>` every 0.5 seconds, default 30 seconds |
| `hola screenshot <id>` | Image to `POST /photo` | Watches the private inbox, default 45 seconds |
| `hola getclipboard <id>` | Text/JSON to `POST /clipboard` | Polls `GET /clipboard/<id>`, default 30 seconds |
| `hola alarm get <id>` | Enabled alarm data to `POST /get-alarm` | Polls `GET /get-alarm/<id>`, default 30 seconds |

The receiver keeps at most 200 in-memory values of each text response type. Screenshots are persisted under `~/.local/share/codex-ios-assistant/inbox`. Restarting the receiver clears in-memory response values, which is fine because IDs are short-lived.

## Result semantics

- `dry-run`: nothing was sent; the CLI reports the exact underlying command or URL.
- `requested`: Messages accepted the request, but the branch has no correlated phone-side receipt.
- `completed`: a correlated response arrived or a local read-only helper completed.
- `failed`: the doctor found a missing required layer, or the command exited with an error.

`requested` is not proof that iOS performed an action. A future protocol could add acknowledgements for one-way actions, but the current design avoids a second HTTP request for every simple command.

## Why not send directly from sandboxed Codex?

AppleScript calls made inside an application sandbox can fail before permission is considered, with errors such as `Unable to find application named 'Messages'` or `LSCopyApplicationURLsForBundleIdentifier() failed`. The sender LaunchAgent is launched by `launchd` in the user's GUI domain. Codex contacts it through a local Unix socket; the agent, not the sandboxed process, resolves and automates Messages.

The boundary remains narrow:

- only the current macOS user can open the `0600` socket;
- only a small JSON object containing one `hola …` line is accepted;
- newlines and messages over 4 KiB are rejected;
- the server invokes a fixed `/usr/bin/osascript` program rather than a caller-provided command.
