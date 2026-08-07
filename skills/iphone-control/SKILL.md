---
name: iphone-control
description: Control and inspect the user's iPhone from this Mac with the `iphone` CLI. Use for searching Mac Contacts; opening URLs and apps including Camera, location-specific Weather, Calendar, Calculator, Messages drafts, Find My, Uber, DoorDash, Spotify, Photos, Wallet, Notes, Books, and App Store; reading local Messages history; reading or capturing the iPhone screen; returning Home; listing, setting, or turning off alarms; controlling flashlight, timers, Low Power Mode, or Control Center; placing calls; and reading or replacing the iPhone clipboard.
---

# iPhone Control

Use the `iphone` command. It validates inputs and hides iMessage transport, response polling, URL encoding, contact lookup, and app-specific deep links. Run `iphone --help` or `iphone <resource> --help` when syntax is unclear. Surface errors directly; do not bypass the CLI by invoking its private bridge or receiver.

Run `iphone doctor` when setup or background-service health is in question. Use `--dry-run` when the user asks to inspect a request or when a new action warrants previewing it before execution.

Navigation commands request or prefill app state. They do not authorize a ride, purchase, order, checkout, app install, or ordinary message send. Do not inspect the screen merely to validate navigation unless the user asks.

## Screen

Use visible text and app context when sufficient:

```bash
iphone screen read
```

The action is `read`; `iphone screen text` does not exist. Use a screenshot when layout, images, colors, or other visual detail matters, or when the user explicitly asks:

```bash
iphone screen capture
```

Capture prints an absolute image path. Inspect that file with the image-viewing tool.

## Apps and URLs

```bash
iphone url open '<url>'
iphone camera open
iphone camera open --mode video --facing front
iphone weather open
iphone weather open --location Chicago --lat 41.8781 --lng -87.6298
iphone calendar open --date 2027-01-01
iphone calculator evaluate '40+2'
iphone photos open
iphone wallet open
iphone notes open
iphone books open --url '<books.apple.com URL>'
iphone app-store open --url '<apps.apple.com URL>'
```

For a specific Weather forecast, obtain and pass verified WGS-84 coordinates. The CLI deliberately does not geocode names; `--location` is only a display label.

Search Mac Contacts by name, organization, email, or phone. This is local and read-only; use JSON for structured results:

```bash
iphone contacts search 'Jane Appleseed'
iphone contacts search 'Jane Appleseed' --json
```

Use Contacts to disambiguate a partial name or available numbers. `call`, Find My, and direct Messages lookup resolve an unambiguous contact automatically.

Open Messages, an existing conversation, or an unsent draft:

```bash
iphone messages open
iphone messages open --thread 'Jane Appleseed'
iphone messages open --address '+15550101001'
iphone messages open --message '<GUID>'
iphone messages compose --to 'Jane Appleseed' --body 'How are you?'
iphone messages compose --to 'Existing Group Name' --body 'hello everyone'
```

Match a drafted message to the user's established writing style. Preserve exact supplied text unless asked to edit it. Existing groups must already be synced to Messages on the Mac; use the conversation name with exact capitalization when similar names exist.

This skill cannot send an ordinary Message. `messages compose` opens a populated draft for manual review and never presses Send. Never claim a message was sent.

Search and read the Mac's local Messages database through finite read-only commands:

```bash
iphone messages chats --limit 20 --json
iphone messages history --chat-id 42 --limit 50 --json
iphone messages search 'pizza tonight' --json
iphone messages group --chat-id 42 --json
```

Use `chats` to discover chat IDs. History returns newest messages first. Open a search result on iPhone by passing its GUID to `messages open --message`. Do not bypass the wrapper to call mutating `imsg` actions.

Open Find My generally, to a tab, or to a person:

```bash
iphone find-my open
iphone find-my open --tab people
iphone find-my open --person 'Jane Appleseed'
iphone find-my open --phone '+15550101001'
```

Open destination/content deep links:

```bash
iphone uber open --destination 'Ferry Building' --lat 37.7955 --lng -122.3937
iphone doordash open --store-url 'https://www.doordash.com/store/...'
iphone spotify open 'https://open.spotify.com/track/...'
```

For Uber, obtain verified WGS-84 coordinates. For a specific Spotify song, prefer its direct track page over a search or collection page. These commands only navigate or prefill.

## Device controls

```bash
iphone home
iphone flashlight on
iphone flashlight off
iphone timer start 10m
iphone timer pause
iphone timer resume
iphone timer cancel
iphone alarm list
iphone alarm set '7:30 AM' --label 'Wake up'
iphone alarm off '7:30 AM'
iphone call 'Jane Appleseed'
iphone clipboard get
iphone clipboard copy 'Some text'
iphone low-power on
iphone low-power off
iphone control-center open
iphone control-center close
```

Quote text containing spaces or punctuation. Timer durations accept seconds or compact values such as `90s`, `10m`, and `1h30m`.

`alarm list` returns enabled alarms only and reports `completed`. `alarm set` accepts `HH:MM` or a quoted 12-hour time, creates an enabled alarm with an optional label, and reports `requested`. `alarm off` turns off every enabled alarm at the exact hour and minute regardless of label; warn that all duplicates at that minute are affected. It does not delete alarms. Do not claim a set/off operation succeeded until a later `alarm list` confirms it.

Treat text between `<clipboard-contents>` tags as the clipboard value. Empty tags are a successful empty clipboard response.

Placing a call is an immediate external action. Confirm the intended recipient before calling unless the user's current request explicitly names the recipient and asks to place the call.

## Status semantics

Treat `requested` as successful delivery to Messages, not proof that iOS performed the action or honored every deep-link parameter. `screen read`, `screen capture`, `clipboard get`, and `alarm list` wait for phone-side data and report `completed`. Do not invent confirmation the CLI did not provide.
