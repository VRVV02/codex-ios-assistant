# Troubleshooting

## `Unable to find application named 'Messages'`

Or:

```text
LSCopyApplicationURLsForBundleIdentifier() failed ... com.apple.MobileSMS
```

This usually means AppleScript was launched inside an application sandbox that cannot resolve Messages. Do not point the CLI back at a direct AppleScript helper. Install and start this project's GUI-domain sender:

```bash
./scripts/install
./scripts/install-services
iphone doctor
```

The doctor should show the Messages sender socket as available. Inspect `~/Library/Logs/codex-ios-assistant/sender.log` if it does not.

## Messages automation is denied

Open System Settings → Privacy & Security → Automation and allow the Python process used by `io.github.codex-ios-assistant.sender` to control Messages. Also confirm Messages is openable and signed into an enabled iMessage account.

Restart the sender after changing permission:

```bash
launchctl kickstart -k "gui/$(id -u)/io.github.codex-ios-assistant.sender"
```

## The command appears in Messages, but nothing happens on iPhone

- Confirm the message reached the same iPhone.
- Open Shortcuts → Automation and confirm the Message automation is enabled and runs immediately.
- Confirm its content filter matches `hola` and it runs the intended `iOS Assistant` Shortcut.
- Run the Shortcut manually once so iOS can show pending permission prompts.
- Open the specific automation's run history if your iOS version exposes it.

For diagnosis, start with `iphone home`, because it does not depend on the tunnel.

## `The network connection was lost` in Shortcuts

Check both ends:

```bash
curl http://127.0.0.1:8787/health
curl https://iphone.example.com/health
launchctl print "gui/$(id -u)/io.github.codex-ios-assistant.receiver"
launchctl print "gui/$(id -u)/io.github.codex-ios-assistant.tunnel"
tail -n 100 ~/Library/Logs/codex-ios-assistant/receiver.log
tail -n 100 ~/Library/Logs/codex-ios-assistant/tunnel.log
```

Replace the example hostname with the configured one. If local health works but public health does not, rerun `scripts/setup-cloudflare` and `scripts/install-services`. If both work, verify that the Shortcut was rendered after the latest hostname/token change and allow its network permission prompt.

## A response command times out

The default response timeout is 30 seconds (45 for screenshots), and polling occurs every 0.5 seconds. Separate the pipeline:

1. Did the command appear in Messages quickly? If not, inspect the sender.
2. Did the automation start? If not, inspect the iPhone trigger.
3. Did the Shortcut branch finish? Run it manually to expose permissions/errors.
4. Did the receiver log a correlated POST? If not, inspect the tunnel and Shortcut URL/header.
5. Did the ID in the command match the logged ID? A stale or modified Shortcut may omit it.

Temporarily increase the wait without changing defaults:

```bash
iphone screen read --timeout 60
```

## `imsg chats` crashes looking for a PhoneNumberKit bundle

An old standalone binary may have been copied without its Swift resource bundle. Remove that obsolete wrapper from earlier in `PATH` and install the packaged release:

```bash
which -a imsg
brew install steipete/tap/imsg
hash -r
imsg --version
```

The current project's command lookup uses `imsg` from `PATH`; it does not bundle or shadow the external tool.

## `imsg` cannot read Messages history

Grant Full Disk Access to the parent application running the command (Terminal, ChatGPT, or another Codex host), then restart that application. Confirm `~/Library/Messages/chat.db` exists and Messages is syncing.

## Contacts do not resolve

Run the helper directly to trigger or diagnose macOS permission:

```bash
contacts search 'Jane'
```

If the executable is missing, install Xcode Command Line Tools and rerun `scripts/install`.

## The pasted Shortcut is incomplete or invalid

- Create a new blank Shortcut; do not paste over a partially built copy.
- Click the action canvas and press Command-V only once.
- Rerun `scripts/copy-shortcut` immediately before pasting.
- Confirm the helper reports `Copied and verified 95 Shortcuts actions`.
- Run `make test` to validate the committed template.

Keep the prior working Shortcut and automation target until the replacement is tested.
