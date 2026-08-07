# Codex iOS Assistant

Codex iOS Assistant lets Codex on a Mac control an iPhone. The `iphone` CLI sends private commands through iMessage. An iOS Shortcut runs the requested action and returns screen text, screenshots, clipboard contents, or alarm data over an authenticated Cloudflare Tunnel.

This is alpha software. Apple permission prompts and the iPhone Message automation require manual setup.

## Supported commands

- Read visible text or save a screenshot from the iPhone.
- Read and replace the clipboard.
- List enabled alarms, create an alarm, or disable alarms at a given time.
- Open Camera, Weather, Calendar, Calculator, Messages, Find My, Spotify, Photos, Wallet, Notes, Books, App Store, Uber, and DoorDash.
- Open the Home Screen or Control Center; control timers, the flashlight, and Low Power Mode; place calls.
- Search Mac Contacts and read the Mac's Messages database.

Message composition opens a draft for review. The CLI does not send ordinary messages, buy anything, install apps, order food, or request rides.

## How it works

```mermaid
flowchart LR
    A["ChatGPT app on iPhone"] -->|Remote session| B["Codex on Mac"]
    B --> C["iphone CLI + skill"]
    C -->|Unix socket| D["Messages sender LaunchAgent"]
    D -->|private hola command| E["iPhone automation + Shortcut"]
    E --> F["Native iOS action"]
    E -->|authenticated HTTPS response| G["Cloudflare Tunnel"]
    G --> H["receiver on Mac loopback"]
    H --> C
```

The Messages sender runs as a per-user LaunchAgent. This keeps Messages automation outside the Codex sandbox, where LaunchServices may be unable to resolve `com.apple.MobileSMS`.

See [Architecture and protocol](docs/architecture.md) for request formats and trust boundaries.

## Requirements

- A Mac running macOS 14 or newer, with Python 3.11+, Messages, and Xcode Command Line Tools.
- An iPhone that receives messages sent to the configured iMessage address.
- A domain managed in Cloudflare.
- iCloud sync for Shortcuts.

The ChatGPT desktop and mobile apps are required only for the Remote workflow.

## Install

```bash
git clone https://github.com/samin100/codex-ios-assistant.git
cd codex-ios-assistant
brew install cloudflared steipete/tap/imsg
./scripts/install
./scripts/setup-cloudflare
./scripts/install-services
./scripts/copy-shortcut
```

Configuration has three values: the iMessage address that reaches your iPhone, a stable HTTPS hostname such as `https://iphone.example.com`, and a generated receiver token. The installer stores them in `~/.config/codex-ios-assistant/`, outside the repository.

`scripts/copy-shortcut` puts 95 native Shortcuts actions on the Mac clipboard. Paste them once into a blank shortcut and name it `iOS Assistant`. After iCloud syncs it to your iPhone, create the automation that listens for commands:

1. Open Shortcuts > Automation, tap the plus sign at the bottom, then choose New Automation > Message.
2. Under `When I receive a message where`, set `Sender is` to your own iMessage contact.
3. Tap `Add Filter` and set `Message contains` to `hola`.
4. Tap `Run Shortcut` and select `iOS Assistant`.

You must create this automation by hand in the Shortcuts app on your iPhone. Follow the [installation guide](docs/installation.md) for the remaining Apple permissions.

## Test the setup

```bash
iphone doctor
curl http://127.0.0.1:8787/health
iphone home
iphone screen read --timeout 30
iphone alarm list --timeout 30
```

`iphone home` returns `requested` after Messages accepts the command. Commands that wait for data from the phone, including `screen read` and `alarm list`, return `completed` after the matching response reaches the Mac.

## Files

| Path | Contents |
| --- | --- |
| `src/iphone_cli/` | CLI, Messages bridge, receiver, and URL builders |
| `shortcut/actions.template.plist` | Sanitized 95-action Shortcut template |
| `scripts/` | Install, configuration, tunnel, LaunchAgent, and clipboard tools |
| `skills/iphone-control/` | Codex skill installed under `~/.agents/skills` |
| `contacts/` | Swift Contacts search helper |
| `tests/` | Python tests and Shortcut validation |

## Docs

- [Installation](docs/installation.md)
- [Commands](docs/commands.md)
- [Architecture and protocol](docs/architecture.md)
- [Shortcut maintenance](docs/shortcut.md)
- [Cloudflare Tunnel](docs/cloudflare.md)
- [Security](docs/security.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Development](docs/development.md)

Released under the [MIT License](LICENSE).
