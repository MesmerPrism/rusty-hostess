# Trusted Local Control Conformance Agent Notes

This directory is an independent, offline Hostess conformance harness for
`trusted_local_http_v1`. It is not a product server and it does not own
admission, controller leases, replay, expiry, revocation, or command
acceptance. Those decisions remain Manifold authority. The deterministic
Manifold fixture port exists only to supply scripted test receipts.

Keep all changes for this app inside this directory.

## Guardrails

- Bind tests only to `127.0.0.1` with port `0`. Reject every other bind host or
  fixed port.
- Keep the listener disabled unless a test or operator explicitly opts in.
- Do not advertise mDNS, mutate LAN/firewall state, use ADB, contact a device,
  or install packages.
- Treat WebSocket delivery and `command_accepted` as transport/authority facts,
  not application effect. Only a fake-player callback may produce
  `command_applied` and a new effective player-state revision.
- Keep the command registry closed and build-time: `describe`, `get_state`,
  `list_videos`, `select_video`, `play`, and `pause`.
- Do not add generic command execution, shell/ADB/intents/components, arbitrary
  paths or URLs, uploads, plugins, executable discovery, or runtime UI code.
- Keep browser assets same-origin and packaged. Reject permissive CORS and
  external scripts.
- Test data must be synthetic and must not contain credentials, private
  evidence, device identities, or machine-local endpoints.

## Validation

Run from this directory:

```powershell
python -m unittest discover -s tests -v
python run_conformance.py
python run_browser_smoke.py --quest-root path\to\rusty-quest
```

The browser smoke exits with code `77` when `playwright-cli` is unavailable;
that optional result does not block the standard-library unit suite.
