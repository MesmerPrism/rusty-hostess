# Validation

Run the repo-local check before committing changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\check_all.ps1
```

The check covers the available local surface:

- Python syntax checks for Hostess control and evidence tools;
- Python unit tests under `tools\test_*.py`;
- desktop projected-motion-breath replay when the sibling package repo is
  available;
- `cargo check` for `apps\hostess-t-makepad`;
- serde-gated Hostess contract tests for current schema defaults and frozen
  legacy schema compatibility;
- app-root Makepad shell regression tests in `main_tests`;
- Rust formatting and temporary cargo checks for Android JNI bridge crates when
  their inputs are present.
- Companion catalog descriptor smoke when the sibling Rusty GUI descriptor
  folder is present.
- WPF companion build when `apps\hostess-companion-wpf` exists.

For fast CLI/evidence edits, run the Python path first:

```powershell
python -m py_compile tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_catalog.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_session.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py
python -m unittest discover -s tools -p "test_*.py"
```

Bridge command and bridge-route evidence fixture validation is covered by:

```powershell
python -m unittest tools.test_hostessctl_bridge_command_android
python -m unittest tools.test_hostessctl_bridge_command_live_android
python -m unittest tools.test_hostessctl_bridge_command
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde bridge_command
python tools\hostessctl\hostessctl.py emit-bridge-route-evidence --input fixtures\bridge-route\hostess-command-websocket-applied-input.json --out target\bridge-route\hostess-command-websocket-applied-evidence.json
python -m unittest tools.test_hostessctl_bridge_route_evidence
```

The Hostess bridge-command tests cover broker receipt stream parsing from
`stream_event.payload`, the Makepad broker-stream subscriber, raw app-private
runtime receipt proof, and the broker-authorized Android route that blocks
app-private staging unless the broker emits `authority_accepted`. The live
Android command tests cover the Hostess-owned setup sidecar around broker
launch, ADB forwarding, forwarded socket readiness, Makepad launch, and the
delegated broker-stream command execution.

Windows companion catalog, readiness, and session report validation is covered by:

```powershell
python -m unittest tools.test_hostessctl_companion_catalog tools.test_hostessctl_companion_readiness tools.test_hostessctl_companion_session
python tools\hostessctl\hostessctl.py companion-catalog --out target\companion-catalog\catalog.json --fail-on-error
python tools\hostessctl\hostessctl.py companion-readiness --out target\companion-readiness\readiness.json
python tools\hostessctl\hostessctl.py companion-session run --out target\companion-session\session.json --profile basic --skip-probe
```

With `--check-broker`, readiness also inspects the Manifold broker APK package,
activity, process, ADB forward mapping, forwarded local socket, and direct host
socket. These checks are warnings by default and become blocking only with
`--require-broker`.

For Makepad app-shell edits, run:

```powershell
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde hostess_contracts
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde main_tests
```

For Windows companion shell edits, run:

```powershell
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
```

The WPF Session page invokes `companion-session run` and renders Hostess-owned
phases/actions/issues. The WPF Commands page invokes
`run-bridge-command-live-android` for the safe probe and renders the Hostess
execution sidecar. If that broker-stream route does not pass, the backend falls
back to `run-bridge-command-android` without broker authority as an explicit
app-private recovery shim. UI validation is the WPF build plus the companion
session and bridge-command backend tests; live headset acceptance also requires
a serial-scoped ADB target, broker socket, and runtime receipt.

For projected-motion-breath desktop replay:

```powershell
python tools\hostessctl\hostessctl.py run-pmb-replay `
  --target desktop `
  --packages-root ..\rusty-manifold-packages `
  --out target\hostess-pmb-desktop-replay\pmb-desktop-replay.json
```

Native Rusty Quest Breathing Room setup is covered by
`tools.test_hostessctl_cli_parser`: when the sibling `rusty-quest` repo is
available, the canonical-profile test loads
`quest-native-renderer-breathing-room-pmb-scale.profile.json`, verifies that
Hostess emits the same property set, records the profile SHA-256, and preserves
every non-parameterized runtime-profile value exactly. The same test module
also rejects custom native PMB state/value stream IDs so the setup receipt,
broker publisher, and native renderer receipt policy stay on the same
canonical projected-motion-breath stream contract.

Quest, phone, ADB, BLE, APK, screenshot, and Perfetto checks are hardware or
platform validation. Use the documented Hostess commands and record evidence
bundles, but keep Agent Board reservations and headset leases scoped to the
actual shared-resource run.

Hostess validation should prove host packaging, launch, command bridging,
settings adoption, and evidence export. It must not redefine package semantics,
Matter CPU truth, Lattice relation truth, Manifold command authority, or
renderer backend policy.
