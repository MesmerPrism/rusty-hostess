# Bounded browser transport relay

`tools/connection_hub_browser_relay.py` is a foreground, opt-in Hostess transport adapter for the existing Connection Hub controller. It reuses `connection_hub_cli.HubConnection`: actual downstream authentication, advertised surface validation, epoch/listener/revision checks, command preflight, sequence/replay and joined receipts remain unchanged. It does not own sessions, peer formation, Wi-Fi settings, enrollment, camera readiness or command acceptance.

The Mesmer Prism HTTPS page cannot connect directly to the current plaintext Hub listener. This helper terminates a **locally trusted** TLS connection on `127.0.0.1`, for a browser running on the same computer. It connects only to one explicitly configured existing Hub. It accepts the exact `https://mesmerprism.com` Origin and `/v1/socket` route; the browser cannot choose a new downstream destination. There is no network listener by default, no background installation, no discovery and no ADB. A browser on a phone cannot reach the computer's loopback endpoint.

Use an existing sanctioned local TLS certificate/key, separately protected and trusted by the browser, with exact SHA-256 pins. No certificate generation or trust-store mutation is implicit. The current owner tooling has a platform-verified TLS **client** route but no certificate bootstrap/server relay. If no appropriate local certificate is available, the helper fails closed; the original Hub-local UI remains supported.

First inspect the non-binding plan:

```text
python tools/connection_hub_browser_relay.py --origin http://<explicit-private-address>:<hub-port> --classification trusted_lan_experimental --allow-insecure-trusted-lan
```

The explicit foreground invocation adds `--serve --port <loopback-port> --seconds <1..900> --certificate <private-local-cert-file> --certificate-sha256 <exact-hash> --private-key <private-local-key-file> --private-key-sha256 <exact-hash>`. Run one helper per target/port when using two headset slots. The page uses `wss://localhost:<loopback-port>/v1/socket` and the existing short-lived controller session, held in tab memory. Do not put credentials in URLs, arguments, logs or receipts. A browser device chooser still requires a gesture for Bluetooth; this relay does not fake that approval.

One browser session is admitted per invocation, with a maximum 900-second foreground lifetime and a 30-second accept bound. Frames are final masked canonical text: authentication first, then only exact v2 surface commands or keepalives, bounded to 4096 bytes. Hub events stay below 65536 bytes. Unsupported frames, bad origins, malformed keys, unknown fields, noncurrent sequences and unadvertised commands close the route without automatic retries. The existing strict client retains authority-derived receipts; local output reports counts and `authority_accepted=not_claimed`, never a bearer or inferred provider success. Closing the relay is transport disconnect, not session revocation.

TLS protects the browser-to-host leg. The existing trusted-LAN downstream still reports `confidentiality=none`, `production_eligible=false`; a relay must not relabel it end-to-end TLS or promote it to production. The Hub-local page remains the owner pairing/revocation UI. The relay cannot convert BLE v1 hints into observed v2 group readiness or expose commands the provider has not registered.

Focused validation: `python -m unittest tools.test_connection_hub_browser_relay -v`. The actual owner loopback fixture test runs the production relay/controller chain and verifies joined provider receipts, canonical frames and exactly one dispatch. It is target-free conformance evidence, not device qualification or TLS trust evidence.
