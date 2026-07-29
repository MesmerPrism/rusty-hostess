# Trusted Local Control Conformance

This is the independent Hostess test surface for
`trusted_local_http_v1`: a Quest-hosted, same-origin HTTP/WebSocket control
surface for low-rate player commands. It deliberately uses a deterministic
fake player and scripted, synthetic Manifold fixture receipts, so Windows host
tests can run before any Android build or headset work.

It is a neutral conformance consumer, not a second authority implementation:

- Manifold owns listener admission, pairing, the single controller lease,
  request replay, rate decisions, expiry, revocation, and command acceptance.
- Quest owns the effective player state. The harness fake player stands in for
  Media3/ExoPlayer and emits effect callbacks.
- Hostess owns only the offline fixture projection, protocol checks, and
  loopback test shell.

The fixture port models the receipts a real Manifold adapter must supply. Its
in-memory rules are an executable oracle for tests, not reusable product logic.
The loopback server cannot bind to a LAN: construction rejects anything except
`127.0.0.1` and port `0`.

## Covered contract

- disabled by default; explicit wearer opt-in and bounded listener window;
- manual IP plus one-use pairing code (QR and mDNS remain optional and absent);
- exact `Host` and `Origin`, same-origin packaged assets, no CORS;
- one controller, wearer-visible controller state, on-headset revoke;
- bounded idle/session expiry and strict rate limit;
- closed commands: `describe`, `get_state`, `list_videos`, `select_video`,
  `play`, and `pause`; the offline cross-repo check binds the exact Quest
  registry path
  `apps/spatial-video-control-example-android/contracts/trusted_local_http_v1.commands.registry.json`;
- bounded canonical JSON, one-use request IDs, expected state revision, and
  request causality;
- separate select/play operations;
- `command_accepted` before fake-player callback-derived `command_applied`;
- rejection of replay, stale revision, unknown fields/commands/videos,
  arbitrary URLs/paths, and generic execution surfaces.

`trusted_local_http_v1` authenticates a controller on a trusted LAN or private
hotspot but does not provide confidentiality. Do not send passwords, private
evidence, device-management credentials, or other secrets through it.

## Offline validation

```powershell
cd apps\trusted-local-control-conformance
python -m unittest discover -s tests -v
python run_conformance.py
```

The suite uses only the Python standard library. Every socket test uses an
ephemeral loopback listener and closes it in the test.

To validate another implementation without adding a product dependency, export
its discovery descriptor and packaged web directory, then run:

```powershell
python run_conformance.py --descriptor path\to\descriptor.json --web-root path\to\web --quest-root path\to\rusty-quest
```

This is static/offline discovery validation. It does not dial a headset,
perform mDNS discovery, or infer an endpoint.

## Optional Windows browser smoke

If `playwright-cli` is already installed and its browser is already available:

```powershell
python run_browser_smoke.py --quest-root path\to\rusty-quest
```

The entrypoint starts the same port-`0` loopback fixture, opens its packaged UI,
checks the visible disabled/no-confidentiality posture, and closes the browser.
It never installs Playwright or downloads a browser. Missing prerequisites
produce exit code `77` with a skip message.

Use `--fixture-assets` only for an explicitly labeled Hostess fixture smoke; it
does not support a Quest product-asset claim.

## Non-scope

No LAN listener, hotspot or Wi-Fi mutation, mDNS advertisement, APK
build/install, Quest/ADB access, Agent Board action, collaborator testing,
signing, publication, relay, Fleet operation, media streaming, or production
authority implementation is included.
