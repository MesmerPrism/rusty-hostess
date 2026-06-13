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
  rendering from completed evidence artifacts. Desktop rendering, PNG
  validation, and render-sidecar helpers live in
  `tools/hostessctl/telemetry_render.py`; the CLI root stays the parser and
  platform dispatch facade. Renders must pass dimension and nonblank checks
  and write a JSON sidecar beside the PNG.
- `tools/hostessctl/android_files.py`: Android shell-file and app-private
  `run-as` file helpers used by Hostess CLI routes. Route-specific constants
  and command dispatch remain in `hostessctl.py`; low-level waiting, pulling,
  pushing, quoting, and Makepad render-sidecar polling live in this helper.
- `tools/hostessctl/broker_transport.py`: Manifold broker WebSocket protocol
  primitives, command envelope helpers, ACK normalization, retry connection,
  and stream-event aliasing used by recording routes. The CLI root re-exports
  these helpers as a compatibility facade for tests and existing callers.
- `tools/hostessctl/pmb_broker_bridge.py`: Projected Motion Breath feedback
  publication, breath-source selection, and PMB receipt listening over the
  broker transport. Recording orchestration remains in `hostessctl.py`.
- `tools/hostessctl/pmb_evidence.py`: projected-motion-breath contract
  constants, replay/self-test evidence builders, PMB validators, and host-run
  evidence writers used by `hostessctl.py` command routes.
- `tools/hostessctl/recording_evidence.py`: broker telemetry and Manifold
  value-recording evidence builders, validators, scorecards, and host-run
  evidence writers used by general recording routes.
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
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\hostessctl\android_files.py tools\hostessctl\broker_transport.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_evidence.py tools\hostessctl\recording_evidence.py tools\hostessctl\telemetry_render.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
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
For Quest APK validation, stage the report and any sibling data-plane assets
with `tools\Stage-HostessMakepadSettings.ps1`. The helper pushes the generated
bundle to `/data/local/tmp`, then copies it into the app-owned
`files/hostess-t/settings` directory with `run-as
io.github.mesmerprism.rustyhostess.makepad`. Do not use
`/sdcard/Android/data/...` as the handoff path for these files; on current
Quest builds ADB may write that tree while the app cannot read it reliably.
The helper also stages `makepad-effective-settings.revision.json`, a compact
control-plane sidecar with global and scoped hashes for settings invalidation.
Hostess runtime hotload prefers that sidecar as its revision key and falls back
to path/mtime only for older staged bundles. Treat filesystem/watch events and
mtime changes as hints: compare relevant scope hashes before parsing the full
effective-settings JSON. The policy is wakeup hint, global revision/hash,
scoped revision/hash, then detailed adoption with applied/rejected evidence.
High-rate hand, mesh, field, particle, and GPU-buffer payloads must stay in
sibling data-plane files or adapter buffers, never in settings/control JSON.
The same staging helper also copies a sibling `stimulus/` directory for
browser-created Optics stimulus profiles. Effective settings carry only the
stimulus enable flag, app-private profile/tuning paths, expected SHA-256
digests, schema, and `StereoEyeField` presentation mode; the profile body
remains an app-private JSON payload for the Quest Makepad renderer adapter.
When that profile declares `rusty.optics.stimulus.volume.v1`, Hostess emits
`RUSTY_QUEST_MAKEPAD_STIMULUS_VOLUME_ADOPTION` from the staged profile summary
with grid, step, bounded readback, and stereo-output fields. This marker is
profile adoption evidence only: `gpuComputeReady=false`,
`computeKernel=false`, and `highRateJsonPayload=false` remain explicit until a
Makepad/Vulkan command-buffer readback proof exists.
Collision, SDF, ADF, and particle controls are also sourced from the same
effective-settings report. Hostess now consumes the camera-shell adapter's
native Matter-surface runtime boundary and records receipt evidence for the
derived Matter config. Only the `sdf` mode activates the SDF feature uniform;
`adf` activates the Quest-Makepad Matter/Optics ADF debug adapter path and is
proved through compact runtime markers such as `adfDebugEnabled`,
`adfStatus`, `adfCells`, `adfBuildMs`, and `adfVisualMs`. `combined` remains
a gated future mode until simultaneous SDF plus ADF output is intentionally
supported. Hostess records and renders adapter outputs; it does not own ADF
truth or parse high-rate ADF leaf cells through settings JSON.
The Makepad world-object ADF debug smoke renderer lives in
`apps/hostess-t-makepad/src/matter_world_adf_debug.rs`. It consumes
`QuestMakepadWorldAdfDebugBatch` rows and emits
`RUSTY_QUEST_MAKEPAD_WORLD_ADF_DEBUG_DRAW` evidence with
`renderer=hostess-makepad-adf-debug-cell-boxes`; it must remain a renderer-only
consumer of the Quest-Makepad adapter output.
Hostess also emits `RUSTY_QUEST_MAKEPAD_GPU_RESIDENCY` when bounded
world-particle or ADF debug batches are submitted to Makepad instanced draw
buffers. This is the first render-plane GPU residency proof for the
particle/SDF/ADF path: Matter remains the CPU oracle, Hostess does not own GPU
compute, and high-rate rows or future buffers stay out of settings/control
JSON. Pair this marker with cadence evidence such as
`xrRepaintGeometryUploadBytes`, `xrRepaintInstances`, and `xrRepaintGpuMs`.
For the next compute-resource checkpoint, Hostess emits
`RUSTY_QUEST_MAKEPAD_GPU_COMPUTE_PREFLIGHT` when the Quest-Makepad adapter sees
a ready Matter `sdf-field` or `adf-field` CPU oracle. The marker is a bounded
eligibility/readback contract for a future Makepad command encoder, not a GPU
compute proof; it keeps `gpuComputeReady=false`, `computeKernel=false`, and
`highRateJsonPayload=false`.

Hostess may emit one `RUSTY_QUEST_MAKEPAD_GPU_STORAGE_PROBE` marker when the
Makepad XR backend returns a bounded storage-buffer readback result for an
eligible compute preflight. This is the first real command-buffer/readback
resource proof: Hostess records the result, but Quest-Makepad owns the marker
contract, Makepad owns the generic Vulkan probe API, and Matter remains the
CPU oracle. The marker must keep `gpuComputeReady=false`,
`computeKernel=false`, and `highRateJsonPayload=false` until a real
field/particle GPU kernel is validated against Matter.

Hostess may also emit one `RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE` marker when
a completed Matter surface frame carries recorded-hand skinning probe input.
Hostess only converts the four bounded adapter samples into the generic
Makepad XR/Vulkan f32 skinning probe and records the readback marker from
Quest-Makepad; Matter remains the CPU skinning oracle and Quest-Makepad owns
the marker contract. The marker must report `jointMatrixSkinningKernel=true`,
but still keep `meshToSdfKernel=false`, `gpuComputeReady=false`, and
`highRateJsonPayload=false` until full-mesh resident skinning and GPU
mesh-to-SDF slices are validated.
Implementation lives outside the app root: `matter_surface_runtime.rs` owns
worker submission, bounded GPU-probe evidence, and world particle/ADF draw
evidence; `matter_surface_gpu.rs` owns the bounded Makepad XR/Vulkan sample
conversion; `recorded_hand_surface.rs` owns loading staged bind-rig plus
compact joint-frame recordings. Keep `main.rs` as app-shell wiring.

For live-hand GPU proof performance evidence, validate the compact Quest run
summary before accepting the run as a cadence baseline:

```powershell
python tools\summarize_makepad_quest_gpu_evidence.py --input <evidence-root> --require-mesh-sdf-program-reuse --require-source-buffer-reuse --require-derived-buffer-reuse --require-mesh-sdf-min-sample-count 8
python tools\check_makepad_quest_gpu_evidence.py --input <evidence-root-or-summary-json> --require-mesh-sdf-program-reuse --require-mesh-sdf-source-buffer-reuse --require-mesh-sdf-derived-buffer-reuse --require-mesh-sdf-min-sample-count 8
```

The checker requires the source-aware proof schedule, the GPU skinning,
full-mesh residency, mesh-to-dense-SDF proof, and GPU field-construction
receipt markers, asynchronous readback without `queueWaitIdle`, zero
Hostess-process `Stale>=90`, no `Stale>=30`, and near-90 Hz app/XR cadence.
The live proof schedule disables the older blocking storage/oracle/force
diagnostics, emits `blockingGpuDiagnostics=false`, and expects two mesh-SDF
proof lines: first-use setup and a reused-program line with `programReused=true`;
current scaled dense-SDF evidence should also report at least `sampleCount=8`.
The paired `RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION` receipt must report
`runtimeFieldBoundaryReady=true`, while keeping `forceAuthorityReady=false`,
`runtimeForceAuthority=false`, `gpuComputeReady=false`, and
`highRateJsonPayload=false`. Stale-heavy debug APK runs remain functional marker
evidence only. The summarizer is the Hostess-owned raw evidence adapter: it
parses `logcat.txt`, filters VrApi stale counts to the Hostess process, ignores
GPU-marker `kgslFaultsBeforeMarker` telemetry as non-fault evidence, writes the
compact summary/check sidecars, and classifies off-face/asleep launches as XR
readiness failures instead of GPU failures when startup markers appeared but
proof markers did not.

The first camera-free Quest ADF proof is recorded at
`S:\Work\tmp\quest-makepad-adf-evidence-20260611-040006` with APK SHA256
`AD4C2416096D7FABDE9A751B04DA7ECF94EE6FAA520641BC2E294D0DA0A59BD3`.
That run used generated/local effective settings selecting
`makepad.sdf_adf.overlay_mode=adf`, staged recorded mesh replay files as
app-private data-plane assets, and logged ADF-ready Matter runtime markers
without camera permissions or camera discovery.

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
