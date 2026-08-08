# Private Tailscale transport

Install Tailscale on the Mac and iPhone, sign both into the same tailnet, and
enable the VPN on the phone. Then run:

```bash
./scripts/setup-tailscale
```

The script checks that Tailscale is connected, discovers the Mac's MagicDNS
name, runs `tailscale serve --bg http://127.0.0.1:8787`, and configures the
Shortcut origin as `https://<mac>.<tailnet>.ts.net`.

Tailscale Serve applies tailnet access controls. Keep membership minimal, enable
MFA, and remove old devices. Do not run `tailscale funnel` for port 8787.

Inspect the route with:

```bash
tailscale serve status
```

Disable it with:

```bash
tailscale serve reset
```
