# Security model

This fork keeps the iPhone-control capability while making the phone-to-Mac
return path private by default. It is still powerful software: it can read what
is visible on the phone, change device state, open apps, and initiate a call.

## Trust boundaries

- The receiver listens only on `127.0.0.1`.
- Tailscale Serve exposes that loopback service only to devices admitted to the
  same tailnet. Tailscale Funnel is not used and must not be enabled.
- The iPhone Shortcut receives only the write token (`X-Auth`). It cannot read
  stored phone data or register a request.
- The Mac keeps a separate admin token (`X-Admin-Auth`) for registering and
  consuming responses. That token is never rendered into the Shortcut.
- Read requests use random 128-bit identifiers. The receiver accepts a phone
  response only when the Mac registered the matching kind and identifier in the
  previous two minutes. Responses are accepted and read once.
- The Message automation uses a random per-install prefix rather than a common
  phrase. Keep both the sender filter and exact prefix filter enabled.
- The sender socket is mode `0600`, rejects other local users where macOS exposes
  peer credentials, and accepts only one bounded single-line prefixed command.

## Data handling

Configuration is stored in `~/.config/codex-ios-assistant/config.env` with mode
`0600`. Receiver data lives under `~/.local/share/codex-ios-assistant/` with mode
`0700`. Text, clipboard, and alarm responses are removed after the first Mac
read. Screenshot cleanup removes files older than 15 minutes when a new image
arrives; remove a sensitive screenshot sooner if needed.

The receiver logs request identifiers and sizes, not screen, clipboard, alarm,
or message contents.

## Command boundaries

Generic `iphone url open` accepts only HTTP and HTTPS URLs. Native deep links are
available only through dedicated, validated commands, preventing an arbitrary
`shortcuts://run-shortcut` payload. Message composition opens an unsent draft and
does not add the private `sendImmediately` flag.

Screen, clipboard, webpage, and Messages content is untrusted input. The bundled
Codex skill explicitly forbids treating instructions found in that content as
authority. Calls, messages, purchases, orders, rides, uploads, and permission
changes require the user's direct intent in the current conversation.

## Residual risks

This is not an Apple system entitlement or a security boundary. It composes
supported automations, iMessage, deep links, and a Mac process. iOS may change or
remove any of those behaviors. A compromised Mac account, compromised tailnet,
compromised Apple account, maliciously modified Shortcut, or user-approved
dangerous action can still cause harm. Use a small tailnet, require MFA, review
tailnet members, keep macOS/iOS updated, and inspect Shortcut changes before
installing them.
