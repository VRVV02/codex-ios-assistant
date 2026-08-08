# Architecture and protocol

## Command path

1. Codex invokes the typed `iphone` CLI.
2. The CLI validates arguments and builds either a dedicated deep link or a
   native Shortcut operation.
3. A mode-`0600` Unix socket hands one bounded command to the per-user sender.
4. Messages sends the command to the user's own iMessage address.
5. The iPhone automation matches both the configured sender and a random
   per-install prefix, then runs the 95-action Shortcut.

The wire grammar uses the generated prefix shown by `scripts/show-trigger`:

```text
<prefix> openurl <validated URL>
<prefix> homescreen
<prefix> screenshot <128-bit-id>
<prefix> screentext <128-bit-id>
<prefix> getclipboard <128-bit-id>
<prefix> copytoclipboard <text>
<prefix> alarm get <128-bit-id>
<prefix> alarm set <HH:MM> <label>
<prefix> alarm off <HH:MM>
<prefix> timer start <seconds>
<prefix> timer pause|resume|cancel
<prefix> flashlight on|off
<prefix> lowpower on|off
<prefix> controlcenter open|close
<prefix> call <phone>
```

The sender accepts one line up to 4 KiB and never accepts a caller-selected
program or AppleScript.

## Private response path

1. Before a read command is sent, the Mac registers the expected response kind
   and a random 128-bit ID on the local receiver with `X-Admin-Auth`.
2. The Shortcut performs the native read and POSTs it with the matching ID and
   `X-Auth` write token.
3. Tailscale Serve carries the HTTPS callback inside the tailnet to the receiver
   bound on `127.0.0.1:8787`.
4. The receiver rejects unknown, expired, mismatched, or already-used IDs.
5. The Mac consumes text responses once with the admin token. Screenshots are
   written mode `0600` into the private inbox and expire through retention cleanup.

| Request | iPhone response | Mac behavior |
| --- | --- | --- |
| `screentext` | JSON to `POST /text` | one-time `GET /text/<id>` |
| `screenshot` | image to `POST /photo` | watch private inbox |
| `getclipboard` | text/JSON to `POST /clipboard` | one-time `GET /clipboard/<id>` |
| `alarm get` | alarm data to `POST /get-alarm` | one-time `GET /get-alarm/<id>` |

The Shortcut knows only the phone-write token. It cannot register requests or
read stored responses. The admin token remains on the Mac.

## URL boundary

Generic URL opening accepts only HTTP(S). Supported app deep links are built by
dedicated validators in `src/iphone_cli/urls.py`; arbitrary native schemes such
as `shortcuts://` are rejected. Message composition creates an unsent draft.

See [Security](security.md) for residual risks and operational guidance.
