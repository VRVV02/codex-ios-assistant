# Commands and behavior

Run `iphone --help` or `iphone <resource> --help` for the complete, version-matched syntax. Global flags can appear before or after a leaf command.

## Diagnostics and output

```bash
iphone doctor
iphone --version
iphone --dry-run timer start 10m
iphone --json --dry-run weather open --location Chicago --lat 41.8781 --lng -87.6298
```

Use `--dry-run` before asking the phone to do anything unfamiliar. Use `--json` for automation and `--verbose` to include result status and URLs.

## Screen, clipboard, and alarms

```bash
iphone screen read --timeout 30
iphone screen capture --timeout 45
iphone screen capture --output ~/Desktop/iphone.png
iphone clipboard get
iphone clipboard copy 'Text copied by Codex'
iphone alarm list
iphone alarm set '7:30 AM' --label 'Wake up'
iphone alarm off '7:30 AM'
```

`alarm list` returns enabled alarms only. `alarm off` turns off every enabled alarm whose hour and minute exactly match, including alarms without labels. It does not delete alarms.

## Device controls

```bash
iphone home
iphone flashlight on
iphone flashlight off
iphone timer start 10m
iphone timer pause
iphone timer resume
iphone timer cancel
iphone low-power on
iphone control-center open
iphone call 'Jane Appleseed'
```

A call is an external side effect. Agents should confirm the intended recipient immediately before placing it unless the user's current request is already explicit.

## Apps and URLs

```bash
iphone url open https://example.com
iphone camera open --mode video --facing front
iphone weather open
iphone weather open --location Chicago --lat 41.8781 --lng -87.6298
iphone calendar open --date 2027-01-01
iphone calculator evaluate '40+2'
iphone messages open --thread 'Jane Appleseed'
iphone messages compose --to 'Jane Appleseed' --body 'On my way'
iphone find-my open --tab people
iphone find-my open --person 'Jane Appleseed'
iphone uber open --destination 'Ferry Building' --lat 37.7955 --lng -122.3937
iphone doordash open --store-url 'https://www.doordash.com/store/...'
iphone spotify open 'https://open.spotify.com/track/...'
iphone photos open
iphone wallet open
iphone notes open
```

Messages composition opens an unsent draft; the CLI does not press Send. Store, rideshare, media, and App Store commands only navigate. They do not purchase, order, request a ride, play media, or install an app.

## Mac-side read-only data

```bash
iphone contacts search 'Jane'
iphone messages chats --limit 20
iphone messages history --chat-id 42 --limit 20
```

Contacts uses the compiled helper. Message history uses the optional `imsg` executable and the local Messages database. These commands read Mac-synced data and do not contact the iPhone Shortcut.
