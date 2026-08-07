# Development

## Local checks

The project has no runtime Python dependencies. Run the checkout directly or install it editable:

```bash
./iphone --help
python3 -m venv .venv
.venv/bin/pip install -e .
make test
./scripts/secret-scan
```

`make test` runs unit tests, compiles Python sources, and validates the Shortcut action graph. On macOS, also build the Contacts helper:

```bash
swift build --package-path contacts --configuration release
```

## Design rules

- Keep required user configuration to the three values documented in `.env.example`.
- Keep the receiver on loopback and require authentication for every data path.
- Never log screen, clipboard, alarm, contact, or Messages content.
- Preserve the `requested` versus `completed` distinction.
- Validate new CLI inputs before constructing a `hola` command or URL.
- Do not add automatic sending, purchases, ride requests, app installation, or destructive alarm deletion.
- Keep Apple UI setup explicit; do not claim that device-local personal automations sync through iCloud.
- Add tests for every parser, URL form, or response format change.

## Shortcut changes

Read [Shortcut source and maintenance](shortcut.md) before editing the plist. The control-flow and dynamic-output UUID graph is easy to corrupt with a mechanical edit. Reproduce unfamiliar native actions in a scratch Shortcut, inspect their pasteboard property list, and test the full rebuilt Shortcut on a physical device.

## Release checklist

1. Run `make test` and build Contacts.
2. Render/copy the Shortcut with throwaway or local private config and install it as a new copy.
3. Exercise one-way commands, all four response endpoints, alarm no-label behavior, and exact-time multi-alarm disabling.
4. Run `scripts/secret-scan` and inspect `git diff --cached`.
5. Update the version in `pyproject.toml` and `src/iphone_cli/__init__.py` together.
6. Tag only after the new Shortcut and sandboxed Remote workflow have passed on real devices.
