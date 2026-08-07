# Security

This project deliberately bridges a remote agent, private messages, native iOS actions, and a public hostname. Read this before making the repository public or broadening the Shortcut protocol.

## Protected data

- The iMessage target identifies the user's account or phone number.
- The receiver token authorizes uploads and reads of transient phone data.
- Screen text, screenshots, clipboard contents, alarms, contacts, and Messages history can all be sensitive.
- Cloudflare tunnel credential JSON files authorize a tunnel in the user's account.

None of those values belongs in Git. Private config lives under `~/.config/codex-ios-assistant`, incoming images under `~/.local/share/codex-ios-assistant`, and logs under `~/Library/Logs/codex-ios-assistant`.

## Existing controls

- The local receiver binds only to loopback.
- All data endpoints require an exact `X-Auth` token of at least 32 characters.
- Public health checks reveal only that the receiver is up.
- Logs redact response contents and record only sizes/counts and short correlation IDs.
- The Messages sender socket is mode `0600`, verifies the peer UID where macOS exposes it, and accepts only one bounded `hola …` line.
- AppleScript source and executable paths are fixed; callers cannot supply a shell command.
- The Shortcut template contains placeholders. The renderer writes its private output mode `0600` to an ignored directory.
- Message drafts are opened for review rather than sent automatically. Commerce and rideshare URLs navigate but do not complete transactions.

## Limitations

The receiver token is a bearer secret embedded in the installed Shortcut. Anyone who obtains it and knows the public hostname can post fabricated results or retrieve a response if they also guess a short-lived request ID. Cloudflare encrypts transport, but the project does not currently provide per-request signatures or replay prevention.

The receiver stores transient text responses in memory and screenshots on disk. It does not automatically expire screenshots. Users should delete sensitive images from the inbox when no longer needed.

The Message personal automation is part of the trust boundary. Restrict it to the expected sender/self identity and messages containing `hola`. Do not make the Shortcut execute arbitrary shell commands or arbitrary Shortcuts actions derived directly from message text.

## Before publishing a change

Run:

```bash
make test
./scripts/secret-scan
git status --short
git diff --cached
```

Inspect the entire staged diff. At minimum, search for personal domains, email addresses, phone numbers, `/Users/...` paths, quick-tunnel hostnames, receiver tokens, Cloudflare tunnel UUIDs, and private key material. Avoid relying on `.gitignore` after a sensitive file has already been staged.

If a token or Cloudflare credential is ever committed, remove it from history before publishing and rotate it. Treat deletion from the current tree as insufficient because Git preserves prior commits.
