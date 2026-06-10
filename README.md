# Rusty Hostess

Rusty Hostess T is the default install and test shell for proving Manifold
packages on desktop, mobile, and headset profiles without relying on older host
applications.

The repo is intentionally separate from:

- `rusty-manifold`: contracts, fixtures, schemas, and neutral helpers.
- `rusty-manifold-packages`: package manifests, package fixtures, and package
  validators.

Hostess T consumes package manifests as build or run inputs and emits evidence
JSON that includes package manifest hashes.

## Current Apps

- `apps/hostess-t-desktop/capture_polar.py`: desktop live capture and runtime
  Polar stream validation using a local Python dependency.
- `apps/hostess-t-makepad`: the intended Hostess T GUI surface. It can seed
  itself from bounded `TelemetrySnapshot` checkpoint JSON, then watch an
  append-only telemetry JSONL stream and maintain independent rolling plots per
  datastream. Snapshots are evidence/checkpoint artifacts, not the live data
  plane.
- `apps/hostess-t-android`: Java-only Android APK built with Android
  command-line tools. The same APK can run mobile and headset profiles, and
  owns platform lifecycle, BLE acquisition, permissions, ADB command bridging,
  app-private evidence storage, and the Hostess JNI bridge. Its native Canvas
  telemetry view is fallback/debug-only platform evidence plumbing; Makepad is
  the scalable GUI path.
- `tools/hostessctl/hostessctl.py render-telemetry`: Android-class app-rendered
  PNG export for phone and headset telemetry evidence, plus desktop PNG
  rendering from completed evidence artifacts. Renders must pass dimension and
  nonblank checks and write a JSON sidecar beside the PNG.
- `tools/hostessctl/hostessctl.py run-replay`: deterministic selected-module
  replay that calls the package Rust processor core and validates the resulting
  graph-resolved evidence.
- `tools/hostessctl/hostessctl.py run-pmb-replay`: projected-motion breath
  replay execution. Desktop runs `projected-motion-breath-core` against the
  package golden fixtures directly. Phone and Quest launch the Hostess Android
  app, execute the same PMB core through JNI over packaged synthetic assets,
  pull app-private evidence, and emit Hostess validation plus host-run evidence.
- `tools/hostessctl/hostessctl.py run-pmb-controller-preflight`: non-human
  Android/Quest controller-path preflight for projected-motion breath. It
  launches the Hostess Android app, runs a packaged headset-controller-shaped
  `stream.motion.object_pose` provider fixture through the same PMB core, pulls
  app-private evidence, and emits Hostess validation plus host-run evidence
  with physical controller input explicitly marked unused.
- `tools/hostessctl/hostessctl.py record-values`: general Manifold value
  recording entrypoint. It accepts repeated `--value <stream-id-or-alias>` and
  `--duration-seconds`, builds provider plans, runs an existing single-value
  live capture route when one is available, or records Quest broker WebSocket
  streams for provider sets that share that transport. The recorder remains
  general-purpose and records explicit missing-stream evidence instead of
  becoming Polar- or controller-specific.
- `tools/hostessctl/hostessctl.py snapshot-telemetry`: converts bounded
  replay/live evidence into `rusty.hostess.telemetry.snapshot.v1` checkpoints
  for Makepad and future Rusty GUI surfaces.
- `tools/telemetry_stream.py`: emits replay-derived
  `rusty.hostess.telemetry.stream_event.v1` JSONL batches for Makepad watcher
  validation. Real live adapters should append the same event shape as data
  arrives.

## Validation

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence tools.test_polar_runtime_bridge tools.test_telemetry_snapshot
python tools\hostessctl\hostessctl.py run-replay --target desktop --module rmssd_gain --module coherence --packages-root <packages-root> --out <capture.json>
python tools\hostessctl\hostessctl.py run-pmb-replay --target desktop --packages-root <packages-root> --out <pmb-replay-evidence.json>
python tools\hostessctl\hostessctl.py run-pmb-replay --target quest --adb <adb> --serial <serial> --packages-root <packages-root> --out <pmb-quest-replay-evidence.json>
python tools\hostessctl\hostessctl.py run-pmb-controller-preflight --target quest --adb <adb> --serial <serial> --packages-root <packages-root> --out <pmb-quest-controller-preflight-evidence.json>
python tools\hostessctl\hostessctl.py record-values --target quest --value stream.polar_h10.acc --value stream.motion.object_pose --duration-seconds 120 --packages-root <packages-root> --out <recording.json> --adb <adb> --serial <quest-serial> --device-address <polar-address> --makepad-pose-controller right --makepad-pose-kind grip --makepad-pose-sample-hz 20
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <capture.json> --out <snapshot.json>
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
```

For Makepad running-telemetry validation from a replay checkpoint:

```powershell
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <capture.json> --out <snapshot.json>
python tools\telemetry_stream.py --snapshot <snapshot.json> --out <telemetry.jsonl>
cargo run --manifest-path apps\hostess-t-makepad\Cargo.toml -- --snapshot <snapshot.json> --stream-jsonl <telemetry.jsonl>
```

## Makepad Runtime Settings

Hostess Makepad runtime settings use Morphospace Makepad names only. Use
`RUSTY_MAKEPAD_*` environment variables, `debug.rusty.*` Android properties,
canonical snake_case runtime keys, or current `makepad.*` launch aliases.
Legacy `RUSTY_XR_*`, `debug.rustyxr.*`, and `rustyxr.*` spellings are not
accepted by the active Hostess Makepad settings stack.

The projection runtime trace marker is
`RUSTY_MAKEPAD_PROJECTION_RUNTIME_MANIFEST` with schema
`rusty.gui.makepad.projection_runtime_manifest.v1`. App-level profile and
hotload behavior should be modeled through the canonical `rusty.gui.makepad.*`
settings surface in the Rusty Makepad repo, then consumed as effective settings
instead of adding another local resolver.

`apps/hostess-t-makepad` can consume a generated effective-settings report with
`--makepad-effective-settings <path>`, `HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS`, or
`RUSTY_MAKEPAD_EFFECTIVE_SETTINGS`. The app emits
`RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS` receipt evidence and can write the
receipt with `--makepad-effective-settings-receipt-out <path>`. Mesh replay
settings are interpreted through the active `rusty-quest-makepad-camera-shell`
adapter instead of a Hostess-local parser. Hostess constructs the adapter's
mesh replay runtime from that same effective-settings report, emits
`RUSTY_QUEST_MAKEPAD_MESH_REPLAY` evidence, hotload-checks the selected report
by file identity, and binds the runtime's four segment uniforms into the XR
panel shader overlay. The `makepad.render.scale` value is applied as the
Hostess `xr_render_scale` runtime override when the report is configured.
Collision, SDF, ADF, and particle controls are also sourced from the same
effective-settings report. Hostess now consumes the camera-shell adapter's
native Matter-surface runtime boundary and records receipt evidence for the
derived Matter config. Only the `sdf` mode activates the SDF feature uniform;
`adf` and `combined` are logged as unsupported future placeholders until Matter
owns a real ADF contract. The remaining render-integration slice is to replace
the procedural shader collision/SDF/particle scaffolds with the adapter's
Matter-backed upload rows.

Live evidence, including runtime processor-module metrics, is validated with:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json> --packages-root <packages-root>
```

`hostessctl run-live`, `hostessctl run-replay`, `hostessctl run-pmb-replay`,
`hostessctl run-pmb-controller-preflight`, and `hostessctl record-values`
validate evidence and write
companion `rusty.manifold.host_run.run_evidence.v1` contract artifacts beside
the raw capture JSON. Runtime artifacts should be written outside this
repository.

Direct stream slots use `--stream hr_rr|ecg|acc|coherence`. Processor modules
are opt-in with repeated `--module` selections, for example:

```powershell
python tools\hostessctl\hostessctl.py run-live --target desktop --module hrv_window --module rmssd_gain --module coherence --packages-root <packages-root> --out <capture.json>
```

General value recording uses Manifold stream IDs or aliases. Current supported
single-value live routes are Polar H10 streams (`stream.polar_h10.hr_rr`,
`stream.polar_h10.ecg`, `stream.polar_h10.acc`, and
`stream.polar_h10.coherence`). Quest broker WebSocket recording supports
combined provider sets whose providers publish through the broker, including
`stream.polar_h10.acc` via Polar PMD and `stream.motion.object_pose` via the
Makepad XR controller-pose provider. The combined route launches or reuses the
broker, configures the Makepad provider, starts Polar PMD when requested,
records for the requested duration, and reports a failed run if any selected
stream is missing.

Broker-backed routes default to the Morphospace Manifold Android broker
identity `io.github.mesmerprism.rustymanifold.broker/.BrokerStartActivity`.
The old public Rusty-XR broker package is not the active default; use
`--broker-package com.example.rustyxr.broker` only as an explicit
legacy-reference override. Hostess writes `rusty.hostess.manifold_broker_identity.v1`
metadata into broker-backed evidence so a run can be traced to the selected
package and whether a legacy-reference package was selected or used.

For Quest foreground telemetry while the broker owns physical Polar PMD, use
`observe-broker-telemetry`. It foregrounds the Hostess telemetry UI as a broker
stream observer and must not open a direct BLE session. The older `run-live`
direct BLE path remains a standalone diagnostic capture route, not the PMB or
foreground telemetry authority path.

```powershell
python tools\hostessctl\hostessctl.py record-values --target desktop --value stream.polar_h10.acc --duration-seconds 120 --packages-root <packages-root> --out <recording.json>
python tools\hostessctl\hostessctl.py record-values --target quest --value stream.polar_h10.acc --value stream.motion.object_pose --duration-seconds 120 --packages-root <packages-root> --out <recording.json> --adb <adb> --serial <quest-serial> --device-address <polar-address> --makepad-pose-controller right --makepad-pose-kind grip --makepad-pose-sample-hz 20
python tools\hostessctl\hostessctl.py observe-broker-telemetry --target quest --out <observer.json> --adb <adb> --serial <quest-serial> --device-address <polar-address> --render-out <telemetry.png>
```

For visual telemetry evidence on Android-class targets, prefer the app-rendered
path over compositor screenshots:

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target quest --adb <adb> --serial <serial> --out <telemetry.png>
```

For desktop evidence rendering:

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target desktop --page modules --input <capture.json> --out <telemetry.png>
```
