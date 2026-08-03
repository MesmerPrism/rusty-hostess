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

Pairing/session secrets are never printed in Hostess receipts. The pairing code
has no command-line-value option: `pair` reads it through a hidden prompt,
stdin, or an inherited file descriptor. The session bearer is protected with
Windows DPAPI `CurrentUser`; the JSON metadata contains only the protected
blob, its SHA-256 token fingerprint, and an exact binding to origin, protocol,
controller identity, and client/server security posture. The default CLI fails
closed when that OS store is unavailable. A process-memory store exists only
as an injected portable test double.

`pair` reserves the local session-metadata destination and proves a protected
store/load/delete round trip before it sends the one-use code. If the remote
pair succeeds but protected credential creation or atomic metadata persistence
then fails, Hostess immediately revokes with the still in-memory bearer,
deletes any protected reference, and removes the empty reservation. It reports
`pair_transaction_rollback_unconfirmed` instead of hiding a failed
compensation. No pairing code or clear bearer is written to a temporary file.

`revoke` first opens one authenticated socket, applies the HTTP revoke, requires
that exact socket to close within three seconds, and then attempts a new socket
with the still in-memory stale bearer. Protected credentials and session
metadata are deleted only after the new authentication is rejected. The receipt
reports `authenticated_socket_open_before_revoke`, `http_revoke_applied`,
`authenticated_socket_closed_within_deadline`, `stale_bearer_auth_rejected`,
and `credentials_deleted_after_negative_proof`; every field must be true for a
passing operation. Interrupted, rejected, or unproven revoke preserves local
state so the operator can investigate. A close during the mandatory
authentication phase counts as rejection only after the WebSocket upgrade and
first auth frame succeeded; listener connection failure or malformed protocol
does not. The metadata file is controller state, not publishable evidence.

## Protocol lock

HTTP routes:

- `GET /v1/status`
- `POST /v1/pair`
- `POST /v1/revoke`

The socket is exactly `WS /v1/socket`, with no bearer in its URL or HTTP
headers. The mandatory first client frame is
`rusty.quest.connection_hub.socket_authenticate.v1`; it carries the bearer only
inside the WebSocket frame. The server must answer with
`rusty.quest.connection_hub.socket_authentication_receipt.v1` before sending
the initial `surface_snapshot`. Subsequent event types are closed to
`surface_available`, `surface_removed`, `surface_state`, and
`command_receipt`. Each event binds the authenticated numeric
`transport_epoch`, one listener-instance ID, monotonic `surface_revision`, and
the advertised transport/confidentiality posture. A new authenticated transport
replaces and closes the older physical socket without re-pairing.

Surface descriptors are version 1 and contain only a bounded surface ID,
display label, description, server-derived provider package/signer identity,
a fixed surface-contract SHA-256, closed command descriptors with their required
controller capability, flat low-rate state, and state revision. Client commands
use the exact envelope:

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

The Hostess command receipt preserves the two-stage result. Top-level
`authority_accepted` is the Hub/Manifold decision; `provider_applied` and
`status` are copied from the strict provider receipt. `surface_id`, `command`,
and nonempty `request_id` are echoed with `request_binding_exact=true` only
after exact causality checks. Authority acceptance with
`provider_applied=false` is a valid, visible non-application result rather than
being rewritten as success.

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

$PairCode = Read-Host 'One-use pairing code'
$PairCode | python $Cli pair --origin $Origin `
  --transport-classification trusted_lan_experimental `
  --allow-insecure-trusted-lan `
  --pairing-code-stdin `
  --controller-identity-sha256 <64-lowercase-hex> `
  --session-file $SessionFile

python $Cli connect-watch --session-file $SessionFile --seconds 30
python $Cli list-surfaces --session-file $SessionFile
python $Cli invoke-surface-command --session-file $SessionFile `
  --surface-id media.control --command play --args-json '{}'
python $Cli revoke --session-file $SessionFile
```

Omit `--pairing-code-stdin` for the CLI's hidden interactive prompt. Automation
that already owns an inherited secret descriptor may use
`--pairing-code-fd <number>`. There is deliberately no `--pairing-code VALUE`
form because command arguments are observable by other host processes.

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

1. safe status, argv-safe secret input, pre-pair credential-store proof,
   transactional DPAPI/test-store binding, and secret-redacted pairing;
2. an empty socket snapshot followed by a media surface appearing;
3. a media command dispatches only to its selected provider;
4. replay, unknown surface, and unknown command reject without dispatch;
5. a second synthetic diagnostics provider appears and receives only its own
   command;
6. the media provider disappears without ending the logical session;
7. reconnect advances the transport epoch while the remaining surface and
   logical session persist;
8. explicit revoke closes a socket that was authenticated before the HTTP
   request, rejects a fresh stale-bearer authentication, and only then deletes
   the local protected credential plus session metadata;
9. no high-rate data-plane payload entered the Hub socket.

The fixture is an executable Hostess oracle, not reusable production authority
and not evidence that a Quest or network transport passed.

## Current assumptions and follow-up

- Pairing includes the public `controller_identity_sha256` alongside the
  one-use code. The server derives provider package/signer identity; clients do
  not supply it.
- A transport epoch is a JSON integer. Hostess requires the snapshot epoch to
  equal the preceding authentication receipt and rejects regression within a
  physical socket.
- A `command_receipt` separately reports authority `accepted` and provider
  `provider_applied`; neither is independent application-effect evidence. Its
  bounded `authority_receipt` remains Manifold-derived rather than a Hostess
  assertion.
- Logical-session continuity is demonstrated by using one unchanged opaque
  session across transport epochs without a second pair. The session secret is
  represented in receipts only by its SHA-256 fingerprint.
- Exact checked-in wire vectors live at
  `fixtures/connection-hub/connection-hub-protocol-v1.json`. Those bytes are
  vendored unchanged from Rusty Quest commit
  `3a1abc5072f1d44417f6ad0c4d27ca84935bac18`, tree
  `df9d1f50ae876b1a0b2415c96da5334534168a6e`, owner path
  `apps/manifold-broker-android/contracts/connection-hub-protocol-v1.json`,
  SHA-256
  `fa00d34511b2ee5576eebdd815e58ae032e37b10c209e41289cfd876c78c9c78`.
- TLS, discovery, and live Quest evidence remain separate
  implementation/validation slices.
