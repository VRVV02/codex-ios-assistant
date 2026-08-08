# Public tunnels are disabled

The upstream project used a Cloudflare Tunnel to publish the loopback receiver.
This hardened fork intentionally disables `scripts/setup-cloudflare`: a bearer
token on a public endpoint is a wider trust boundary than this project needs.

Use [Tailscale Serve](tailscale.md). Serve is private to the tailnet; do not use
Tailscale Funnel, which would make the service public again.
