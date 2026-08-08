# Installation

## Requirements

- macOS 14 or newer with Python 3.11+, Messages, and Xcode Command Line Tools.
- An iPhone receiving iMessages at the configured address.
- Tailscale installed and signed into the same tailnet on the Mac and iPhone.
- iCloud sync for Shortcuts.

The ChatGPT desktop and mobile apps are needed only for the Codex Remote workflow.

## 1. Install the Mac tools

```bash
git clone https://github.com/VRVV02/codex-ios-assistant.git
cd codex-ios-assistant
brew install --cask tailscale-app
./scripts/install
```

`scripts/install` creates a repository-local virtual environment, installs the
`iphone` CLI under `~/.local/bin`, and installs the bundled Codex skill. The
optional `imsg` dependency enables read-only Messages history:

```bash
brew install steipete/tap/imsg
```

## 2. Establish the private network

Open Tailscale on both devices, sign into the same tailnet, and enable the VPN on
the iPhone. On the Mac run:

```bash
./scripts/setup-tailscale
```

The script creates a private Tailscale Serve route to the receiver on
`127.0.0.1:8787` and asks for the iMessage address that reaches this iPhone. It
writes mode-`0600` configuration under
`~/.config/codex-ios-assistant/config.env`.

Do not enable Tailscale Funnel. Funnel would publish the receiver to the public
Internet and defeats this fork's principal safety boundary.

## 3. Start the Mac services

```bash
./scripts/install-services
curl http://127.0.0.1:8787/health
iphone doctor
```

The installer creates two per-user LaunchAgents:

| Service | Purpose |
| --- | --- |
| `io.github.codex-ios-assistant.sender` | Sends prefixed commands through Messages |
| `io.github.codex-ios-assistant.receiver` | Accepts one-time phone responses on loopback |

Tailscale itself owns the private HTTPS route; this project installs no public
tunnel service.

## 4. Create the Shortcut

```bash
./scripts/copy-shortcut
```

On the Mac, create a blank Shortcut, paste the copied actions, and name it
`iOS Assistant`. Let iCloud sync it to the iPhone. The rendered Shortcut contains
the private tailnet URL, phone-write token, and random command prefix; it does not
contain the Mac admin token.

## 5. Create the iPhone automation

First print the non-secret per-install trigger on the Mac:

```bash
./scripts/show-trigger
```

Then on the iPhone:

1. Open Shortcuts > Automation and create a Message automation.
2. Set `Sender is` to your own iMessage contact.
3. Add `Message contains` with the exact output of `scripts/show-trigger`.
4. Add `Run Shortcut`, select `iOS Assistant`, and choose Run Immediately.
5. Keep both the sender and content filters enabled.

Apple requires this automation to be created manually. Approve only the native
permissions required by the actions you intend to use. Do not add an action that
runs arbitrary Shortcut names or evaluates message text as a command.

## 6. Verify end to end

```bash
iphone home
iphone screen read --timeout 30
iphone alarm list --timeout 30
```

`iphone home` reports `requested` when Messages accepts the command. Read
operations report `completed` only after the receiver accepts the matching
one-time response.

If the callback fails, confirm Tailscale is connected on the phone and inspect:

```bash
tailscale serve status
./scripts/show-trigger
iphone doctor
```

## Permissions

- Messages automation permission is needed for the Mac sender.
- Shortcuts requests access to apps and device actions as each branch is first used.
- Full Disk Access is optional and is needed only for local Messages history.

Review [Security](security.md) before enabling sensitive actions.
