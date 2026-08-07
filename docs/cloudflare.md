# Cloudflare Tunnel

The receiver needs a public HTTPS origin because an iPhone cannot reach a Mac loopback port. This project uses a named Cloudflare Tunnel and a DNS hostname you own, rather than a temporary quick tunnel.

## Automated setup

After `scripts/configure` and `brew install cloudflared`, run:

```bash
./scripts/setup-cloudflare
./scripts/install-services
```

The setup script follows Cloudflare's documented local-tunnel lifecycle:

```bash
cloudflared tunnel login
cloudflared tunnel create codex-ios-assistant
cloudflared tunnel route dns codex-ios-assistant iphone.example.com
```

It writes the tunnel UUID and credential path to the private file `~/.config/codex-ios-assistant/cloudflared.yml`. Do not copy a credential JSON into this repository.

The setup script never overwrites an unrelated existing DNS record. If the chosen hostname is already occupied on first setup, select a dedicated free hostname or deliberately replace the record in Cloudflare before retrying.

See Cloudflare's official guides for [creating a locally managed tunnel](https://developers.cloudflare.com/tunnel/advanced/local-management/create-local-tunnel/) and [running `cloudflared` as a macOS service](https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/macos/). This project installs its own per-user LaunchAgent so its three related services can be managed together.

## Why the hostname persists

Cloudflare quick tunnels generate a random `trycloudflare.com` hostname every time. A named tunnel has a durable UUID, and the DNS CNAME remains associated with that tunnel. Rebooting the Mac reconnects the same tunnel without changing the URL embedded in the Shortcut.

## Exposure

`iphone-assistant-receiver` binds only to `127.0.0.1`. The tunnel is the sole public path. `/` and `/health` return a generic status without authentication; every endpoint that accepts or returns user data requires `X-Auth`.

The last ingress rule is `http_status:404`, so unrecognized hostnames are not forwarded. Receiver logs record sizes and correlation IDs, not screen, clipboard, or alarm contents.

## Change the hostname

1. Rerun `scripts/configure --url https://new-host.example.com`.
2. Rerun `scripts/setup-cloudflare` to create the new DNS route and rewrite the private tunnel config.
3. Rerun `scripts/install-services`.
4. Rerun `scripts/copy-shortcut` and paste the newly rendered actions into a new Shortcut.
5. Point the iPhone Message automation to the new Shortcut.

Keep the old Shortcut until the public health check and a response-producing command work through the new hostname.
