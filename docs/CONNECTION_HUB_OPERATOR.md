# Rusty Connection Hub operator and conformance client

`tools/connection_hub_cli.py` is the external Hostess controller, automation
client, and deterministic conformance harness for the Rusty Connection Hub.
It is not a Hub service and it does not own admission, trust, logical sessions,
surface registration, command acceptance, replay, expiry, or revocation.
Those decisions stay with the Hub's Manifold authority. Hostess only transports
requests, checks the closed protocol, and projects secret-redacted evidence.

## Security and transport posture

Every endpoint must have an explicit transport classification. There is no
unlabelled or ambient endpoint mode:

- `loopback_fixture` is only for the deterministic `127.0.0.1` fixture;
- `adb_forward` is a separately labelled loopback transport and is not LAN
  confidentiality evidence;
- `trusted_lan_experimental` is paired plaintext HTTP/WebSocket on a private or
  link-local network. It requires `--allow-insecure-trusted-lan`, reports
  `confidentiality=none`, and always sets `production_ineligible=true`;
- `tls` requires HTTPS/WSS plus the platform certificate verifier.

The current Quest Hub adapter advertises
`transport_classification=trusted_lan_experimental`,
`confidentiality=none`, and `production_eligible=false`. Pairing authenticates
a controller but does not encrypt traffic. Never transmit passwords, private
evidence, device-management credentials, or high-rate payloads over that
route.

Pairing/session secrets are never printed in Hostess receipts. `pair` writes
the opaque session to an explicit local session file opened with exclusive
create and restrictive file mode, then prints only its SHA-256 fingerprint.
The file is controller state, not publishable evidence. Delete it after the
session is revoked. On Windows, production credential persistence requires a
future OS credential-vault adapter; this file route is an operator/test bridge.

## Protocol lock

HTTP routes:

- `GET /v1/status`
- `POST /v1/pair`
- `POST /v1/revoke`

The socket is `WS /v1/socket?session=<opaque>`. The first event on every
physical socket must be `surface_snapshot`. Subsequent server event types are
closed to `surface_available`, `surface_removed`, `surface_state`, and
`command_receipt`. Each event binds one `transport_epoch` and monotonic
`surface_revision`.

Surface descriptors are version 1 and contain only a bounded surface ID,
display label, description, server-derived provider package/signer identity,
closed command descriptors, flat low-rate state, and state revision. Client
commands use the exact envelope:

```json
{
  "$schema": "rusty.quest.connection_hub.surface_command.v1",
  "type": "surface.command",
  "request_id": "hostess-command-...",
  "surface_id": "media.control",
  "command": "play",
  "args": {}
}
```

Arguments are objects with at most 16 ASCII-token keys. Values are only null,
boolean, integer, or a string no longer than 256 characters. Arrays and nested
objects reject. Commands are also checked against the selected surface's
advertised registry before dispatch. The Hub remains responsible for the
authoritative replay, surface, and command decisions.

High-rate media, LSL samples, BLE samples, camera/depth data, and other stream
payloads do not use this socket. The Hub socket carries low-rate discovery,
state, commands, and receipts; negotiated data planes remain independently
owned.

## Operator commands

The examples use PowerShell. Replace values with the exact Hub origin,
one-use pairing code, public controller identity digest, and a private local
session-file path.

```powershell
$Cli = 'tools\connection_hub_cli.py'
$Origin = 'http://192.168.50.20:43210'
$SessionFile = "$env:TEMP\rusty-connection-hub-session.json"

python $Cli status --origin $Origin `
  --transport-classification trusted_lan_experimental `
  --allow-insecure-trusted-lan

python $Cli pair --origin $Origin `
  --transport-classification trusted_lan_experimental `
  --allow-insecure-trusted-lan `
  --pairing-code 123456 `
  --controller-identity-sha256 <64-lowercase-hex> `
  --session-file $SessionFile

python $Cli connect-watch --session-file $SessionFile --seconds 30
python $Cli list-surfaces --session-file $SessionFile
python $Cli invoke-surface-command --session-file $SessionFile `
  --surface-id media.control --command play --args-json '{}'
python $Cli revoke --session-file $SessionFile
```

`connect-watch` is bounded to 300 seconds because Hostess is not a long-lived
background-service owner. Re-running `list-surfaces`, `connect-watch`, or
`invoke-surface-command` may replace the physical transport while preserving
the server-side logical session. Receipts report whether the observed
`transport_epoch` changed.

## Deterministic offline E2E

The conformance fixture binds only to `127.0.0.1` on port `0` and never uses
ADB, a headset, discovery, LAN/firewall mutation, or an external service:

```powershell
python -m unittest tools.test_connection_hub_cli -v
python tools\connection_hub_cli.py simulate-e2e
```

The E2E receipt proves:

1. safe status and secret-redacted pairing;
2. an empty socket snapshot followed by a media surface appearing;
3. a media command dispatches only to its selected provider;
4. replay, unknown surface, and unknown command reject without dispatch;
5. a second synthetic diagnostics provider appears and receives only its own
   command;
6. the media provider disappears without ending the logical session;
7. reconnect advances the transport epoch while the remaining surface and
   logical session persist;
8. explicit revoke closes the socket and blocks reconnect;
9. no high-rate data-plane payload entered the Hub socket.

The fixture is an executable Hostess oracle, not reusable production authority
and not evidence that a Quest or network transport passed.

## Current assumptions and follow-up

- Pairing includes the public `controller_identity_sha256` alongside the
  one-use code. The server derives provider package/signer identity; clients do
  not supply it.
- A transport epoch is opaque. Hostess compares equality only and never parses
  ordering from it.
- A successful `command_receipt` proves authority acceptance and routing, not
  application effect. The deterministic fixture sets
  `proves_application_effect=false`.
- Logical-session continuity is demonstrated by using one unchanged opaque
  session across transport epochs without a second pair. The session secret is
  represented in receipts only by its SHA-256 fingerprint.
- TLS, durable credential-vault storage, discovery, and live Quest evidence
  remain separate implementation/validation slices.
