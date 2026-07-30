# Meta Quest Casting Adapter

## Purpose

`hostessctl meta-quest-casting` is a Windows-only, experimental Hostess
adapter for the separately installed Meta Quest Developer Hub `Casting.exe`.
It exists to launch and supervise Meta's Cast window without requiring the
main MQDH window to remain open.

The adapter is not a media-source implementation. Meta owns the Quest
companion service, casting protocol, encoding, transport, Cast presentation,
and recording behavior. Hostess owns only closed compatibility checks,
exact-target preflight, process ownership, lifecycle receipts, and bounded
cleanup requests.

It must not be registered as a generic Manifold or Rusty Quest stream source.
The Meta transport remains opaque: Hostess receives no frames, codec stream,
socket endpoint, or `RMANVID1` payload from this route.

## CLI surface

```powershell
python tools\hostessctl\hostessctl.py meta-quest-casting describe `
  --out <descriptor.json>

python tools\hostessctl\hostessctl.py meta-quest-casting doctor `
  --serial <exact-serial> `
  --out <doctor.json>

python tools\hostessctl\hostessctl.py meta-quest-casting start `
  --serial <exact-serial> `
  --transport usb `
  --coordination-mode user-supervised `
  --out <start.json>

python tools\hostessctl\hostessctl.py meta-quest-casting status `
  --out <status.json>

python tools\hostessctl\hostessctl.py meta-quest-casting stop `
  --out <stop.json>
```

`--coordination-mode agent-board --quest-lease-id <id>` records an externally
reserved Quest lease when Agent Board is the selected coordination provider.
Agent Board is not a permanent runtime dependency: the command records the
authorization/coordination selected by the caller and does not infer Fleet,
Manifold, or device authority from process launch.

The command family accepts no arbitrary executable arguments, raw broadcasts,
wireless transport, ADB daemon lifecycle operations, forced process kill, or
Meta package installation.

## Discovery and compatibility

`describe` is target-free and inert. Its descriptor:

- sets `authorizes_execution=false`;
- lists typed actions and receipt schemas;
- lists only reviewed MQDH version, Meta signer/Casting identity, Google
  signer plus `adb.exe`/adjacent ADB DLL hashes, companion version identity,
  and feature-profile identity;
- exposes no executable path, device serial, endpoint, credential, caller
  arguments, configured state, or health/readiness claim.

`doctor` is target-specific and observational. It requires an exact serial,
fails when the shared ADB daemon is not already running, refuses network-shaped
device identities in the first profile, and confirms the Meta companion
package. It does not start, stop, restart, reconnect, or repair ADB.

The current profile accepts only the standard protected MQDH installation
root, regular (non-reparse) runtime files, and exact reviewed hashes and valid
signatures for `Casting.exe`, `adb.exe`, `AdbWinApi.dll`, and
`AdbWinUsbApi.dll`. The exact companion `versionName` and `versionCode` are
also pinned. Host compatibility failure returns before any bundled executable
is invoked, and the executable identity is re-read immediately before launch.
Unknown versions, hashes, signer identities, companion versions, paths, or
invalid signatures fail closed.

The central Hostess CLI remains importable on non-Windows hosts. Target-free
`describe` is portable; effectful and target-specific actions return a
structured `host_platform_unsupported` receipt outside Windows.

## Receipt semantics

All runtime receipts use
`rusty.hostess.meta_quest_casting.receipt.v1`. Keep these observations
separate:

- `session`: Hostess-owned process identity and lifecycle phase;
- `presentation.window_observed`: an OS window exists;
- `presentation.presentation_ready`: live presentation was independently
  observed, otherwise `unconfirmed`;
- `presentation.cinematic_mode`: Cinematic mode was independently observed,
  otherwise `unconfirmed`;
- `recording.requested`, `active`, and `finalized`: distinct recording stages;
- `recording.artifact`: populated only after one isolated recording is
  finalized and its artifact metadata is observed;
- `cleanup.host_process_exited`: only the owned host process exited;
- `cleanup.device_session_stopped`, `fov_restored`, and `cleanup_complete`:
  remain `unconfirmed`/false until device-side evidence proves them.

Process existence, a main-window handle, or process exit never proves casting
effectiveness, recording finalization, extended FOV, or device cleanup.
Receipts also receive cross-field semantic validation: for example,
`cleanup_complete=true` cannot coexist with unconfirmed device/FOV cleanup,
and a finalized recording cannot omit its request or artifact.

Private lifecycle state is per-user, write-ahead, and cross-process locked. A
starting state whose post-launch PID write was interrupted can recover only
one process with the exact reviewed executable path and launch-session UUID.
Status and stop additionally bind PID, creation time, executable path, and
session UUID; stop sends no window input after an identity mismatch.

## Live validation

Live validation requires one exact Quest and appropriate external
coordination. Store device serials, logs, screenshots, recordings, state files,
and raw receipts outside the repository.

For each reviewed Meta build:

1. Run `doctor` and retain the exact MQDH/Casting/companion versions.
2. Establish the official MQDH Cast control.
3. Start the Hostess route and confirm the main MQDH process is not required.
   The default startup observation spans 25 seconds so a delayed Meta-process
   crash cannot be reported as a stable Hostess process session.
4. Observe the Cast presentation independently from the process/window check.
5. Select Cinematic in the current Cast UI and compare a known angular-grid or
   edge-marker scene against the official control.
6. Isolate one recording. Do not start a second recording until the first is
   finalized; wait for stable size/metadata before retrieval and hashing.
7. Stop through Hostess, then prove the Meta device session stopped, the
   immersive app recovered, and original FOV was restored.
8. Confirm no owned `Casting.exe` remains. A resident Meta service process is
   not by itself proof of an active or stopped casting session.

Recording selector values from other Meta capture surfaces or older builds are
historical evidence only and must not be copied into this contract without
current Cast-window validation.

The reviewed MQDH 6.4.1 matrix proved stable Hostess launch, live visual
presentation, and a Cast overlay that explicitly reported Cinematic 16:9. It
also proved exact graceful host-process shutdown without forced termination.
The Cast recorder control did not expose an observable active transition and
produced no new host or Quest artifact in the isolated attempt, so recording
remains operator-assisted/unproven. The Meta device service remained resident
after the host window closed, and no owner-issued FOV restoration evidence was
available; device-session stop and FOV cleanup therefore remain unconfirmed.

`Casting.exe` emits private per-session stdout/stderr logs under the user's
local application-data directory. The current experimental adapter captures
them because discarding those handles caused the reviewed Meta process to exit,
but it does not yet provide active log rotation. Keep sessions bounded, stop
them explicitly, and treat log retention as a wider-distribution gate.

## Distribution

Distribute only Hostess-owned AGPL source/binaries, schemas, generic fixtures,
and documentation. Never package, rename, patch, download, or redistribute
MQDH, `Casting.exe`, its libraries, Meta APKs, icons, or recordings.

The current result is suitable only for manually supervised local developer
use from source on the reviewed machine. It is not yet suitable for
distribution to other users, a general binary or store package, recording,
unattended operation, or MCP projection. A later Hostess release must remain
an explicitly experimental feature that:

- requires the user to install and license MQDH separately;
- performs local compatibility discovery at runtime;
- fails closed on unreviewed Meta updates;
- keeps live evidence outside the installation;
- bounds or rotates private Cast logs during active sessions;
- holds replacement-denying Windows file handles across final validation and
  execution so path-based hash checks cannot race a file substitution;
- leaves recording operator-assisted until requested/active/finalized/artifact
  evidence is reliable;
- leaves cleanup incomplete until Meta-owned device-session and FOV effects
  are directly observable;
- publishes registry-generated CLI/capability documentation from the inert
  descriptor after the contract stabilizes;
- adds a minimal Hostess agent manifest before considering an MCP projection.

Any future MCP surface should begin with `describe`, `doctor`, plan/status, and
`stop` projections over the CLI/local API contract. It must not expose raw
launch arguments or treat discovery as execution authorization.
