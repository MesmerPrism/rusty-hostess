# Bridge Route Evidence

Hostess can emit Manifold bridge-route evidence for Windows-to-Quest,
Quest-to-PC, Makepad, WPF, and future UI shells without making any one frontend
the authority.

The emitted contract is:

```text
rusty.manifold.bridge.route_evidence.v1
```

The Hostess input receipt is:

```text
rusty.hostess.bridge_route_evidence_input.v1
```

## Boundary

Manifold owns the bridge-route contract and required evidence stages.

Hostess owns platform execution and evidence collection. The
`emit-bridge-route-evidence` command only normalizes and validates stage
observations already collected by a Hostess adapter or UI shell.

WPF, Makepad, and future frontends should treat the command as a shared
evidence adapter. They may collect or display stage observations, command ids,
transport receipts, runtime markers, and validation rows, but should not invent
parallel command acceptance rules.

## Command

```powershell
python tools\hostessctl\hostessctl.py emit-bridge-route-evidence `
  --input fixtures\bridge-route\hostess-command-websocket-applied-input.json `
  --out target\bridge-route\hostess-command-websocket-applied-evidence.json
```

The command writes:

- `rusty.manifold.bridge.route_evidence.v1` at `--out`;
- `rusty.hostess.bridge_route_evidence.validation.v1` beside it as
  `<stem>.validation-report.json`, unless `--validation-out` is set.

Use `--route-descriptor <descriptor.json>` when a Manifold route descriptor is
available. Use repeated `--required-stage <stage>` only for narrow tests or
temporary adapter work where the descriptor is not available yet. The input
receipt can also carry `required_evidence_stages`.

## Command Execution

Use `run-bridge-command` when Hostess should actually send a command envelope
through the Manifold broker WebSocket route:

```powershell
python tools\hostessctl\hostessctl.py run-bridge-command `
  --input fixtures\bridge-command\hostess-websocket-command-request.json `
  --out target\bridge-command\hostess-websocket-command-evidence.json `
  --broker-host 127.0.0.1 `
  --broker-port 8765
```

The command consumes `rusty.hostess.bridge_command.request.v1`, writes
`rusty.manifold.bridge.route_evidence.v1` to `--out`, and writes a
`rusty.hostess.bridge_command.execution_evidence.v1` sidecar beside it. The
execution sidecar records the command envelope and broker messages for
debugging; the bridge-route evidence remains the frontend-neutral result.

By default `run-bridge-command` subscribes to
`stream.hostess.makepad.bridge_command.receipt` before sending the command.
The Quest Manifold broker dispatches the safe Hostess Makepad probe command
onto `stream.hostess.makepad.bridge_command`, and the Hostess Makepad app's
broker subscriber publishes
`rusty.hostess.makepad.bridge_command_runtime_receipt.v1` back on the receipt
stream. Use `--runtime-receipt-stream <stream>` to select another receipt
stream, or `--no-runtime-receipt-subscribe` only for narrow transport tests.

## Live Android Broker-Stream Probe

Use `run-bridge-command-live-android` when Hostess should prepare the connected
Quest broker/runtime pair and then run the reusable broker-stream command
route:

```powershell
python tools\hostessctl\hostessctl.py run-bridge-command-live-android `
  --input fixtures\bridge-command\hostess-broker-stream-command-request.json `
  --out target\bridge-command\hostess-broker-stream-command-evidence.json `
  --adb S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe `
  --serial <quest-serial>
```

The Hostess sidecar is
`rusty.hostess.bridge_command.live_android_execution_evidence.v1`. It records
broker launch, broker process wait, ADB forward setup, forwarded socket
readiness, Makepad launch/process wait, and then embeds the normal
`run-bridge-command` execution. The bridge-route evidence still means only the
command route stages:

```text
sent -> transport_ok -> authority_accepted -> runtime_accepted -> applied
```

This is the preferred WPF safe-probe backend when USB ADB is available. The
older app-private Android route remains the recovery path when broker-stream
setup or runtime receipt collection fails.

## Headset Runtime Receipt Proof

Use `run-bridge-command-android` when the immediate goal is to prove that the
Hostess Makepad Quest runtime can consume a low-rate command request and emit
`runtime_accepted` plus `applied` evidence over USB ADB:

```powershell
python tools\hostessctl\hostessctl.py run-bridge-command-android `
  --input fixtures\bridge-command\hostess-android-hotload-command-request.json `
  --out target\bridge-command\hostess-android-hotload-command-evidence.json `
  --adb S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe `
  --serial <quest-serial>
```

This stages the request into
`files/hostess-t/settings/bridge-command-request.json`, launches the generated
Makepad XR activity by default, and pulls
`files/hostess-t/settings/bridge-command-receipt.json`. The route requires:

```text
sent -> transport_ok -> runtime_accepted -> applied
```

It does not require or emit `authority_accepted`, because app-private ADB
staging is not Manifold command authority. Use it as the headset-backed runtime
receipt fallback and launch/staging slice.

## Broker-Authorized Android Runtime Probe

Use `--broker-authority` when the Windows companion or another frontend needs a
single safe probe that proves both Manifold command acceptance and Quest
runtime adoption:

```powershell
python tools\hostessctl\hostessctl.py run-bridge-command-android `
  --input fixtures\bridge-command\hostess-android-authorized-command-request.json `
  --out target\bridge-command\hostess-android-authorized-command-evidence.json `
  --broker-authority `
  --adb-forward-broker `
  --adb S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe `
  --serial <quest-serial>
```

This route requires:

```text
sent -> transport_ok -> authority_accepted -> runtime_accepted -> applied
```

Hostess sends the command envelope to the Manifold broker first. Only after an
accepted ACK does it stage the app-private Makepad runtime request with
`broker_authority_accepted=true`. This is intentional bring-up plumbing: it is
not the broker-stream runtime consumer used by `run-bridge-command`, but it
prevents WPF or another frontend from treating raw ADB staging as command
authority while the UI still needs launch/staging help.

`--adb-forward-broker` prepares a host TCP port forward to the connected
Quest broker before the WebSocket authority request. The forward proves only
transport setup; the route still requires broker `authority_accepted` and
runtime `applied` evidence before it can pass.

## Stage Policy

Applied command routes require the full chain:

```text
sent -> transport_ok -> authority_accepted -> runtime_accepted -> applied
```

This is the case for `bridge_route.command.websocket.applied`. A WebSocket ACK
or ADB exit code alone is not enough to claim the command took effect.

Transport-only device-management routes require only their transport stages.
For example, `bridge_route.device.adb.transport_only` requires:

```text
sent -> transport_ok
```

Use transport-only evidence for install, push, pull, log, and shell operations
when the claim is only that the host/device transport completed. Use applied
command evidence when the runtime must report the requested setting, command,
or visual state as accepted and applied.

## Validation

```powershell
python -m unittest tools.test_hostessctl_bridge_command_android
python -m unittest tools.test_hostessctl_bridge_command
python -m unittest tools.test_hostessctl_bridge_route_evidence
```

The fixtures cover:

- applied WebSocket command evidence with runtime/applied receipts;
- broker stream command receipt parsing from `stream_event.payload`;
- applied Android app-private command evidence with headset runtime/applied
  receipts and no Manifold authority claim;
- ADB transport-only evidence that does not require runtime adoption;
- damaged command evidence that has transport and authority ACKs but no
  `runtime_accepted` or `applied` stages.
