# Architecture

Rusty Hostess T is an install and test shell for Manifold package development.
It is not a new authority layer. It consumes Manifold and package contracts,
executes named validation slots on target hosts, and exports evidence bundles.

## Authority

Manifold owns command descriptors, leases, package/runtime state, stream
registries, audit records, and scorecards.

Hostess T owns platform packaging, permission probes, launch/install routes,
small app UI surfaces, command bridging, and evidence export.

## Current Slice

The first implementation supports one live package slot:

- `live-smoke`: bounded direct-stream capture for the Polar H10 package and
  opt-in processor-module validation for selected package modules.

The Android app embeds selected package manifests as assets, opens the platform
sensor route itself, and writes evidence that includes the package manifest
hash. The desktop script follows the same evidence shape. Both desktop and
Android captures are accepted only after the shared evidence validator compares
the reported manifest hash against the supplied package root.

The intended GUI surface is Makepad. `apps/hostess-t-makepad` seeds from
bounded `TelemetrySnapshot` checkpoint JSON when useful, then watches
append-only `TelemetryStreamEvent` JSONL and maintains rolling buffers per
datastream. It is the first scalable Rusty GUI example for Hostess T. It
observes run state and can request commands only through the same
Hostess/Manifold command routes as `hostessctl`.

The Android-class app shell includes a compact native Canvas telemetry view for
phone and headset profiles, but that view is fallback/debug-only platform
evidence plumbing. Android Java owns Activity lifecycle, direct diagnostic BLE
capture routes, permission UX, ADB intent/file command bridging, app-private
evidence storage, and JNI calls into the Rust runtime. For Quest PMB and
foreground telemetry, physical Polar PMD is broker-owned and Hostess observes
broker streams or computes bounded on-Quest processor evidence; Hostess must
not open a second BLE session for that path. It does not own reusable panel
layout, processor formulas, package state, graph execution, broker provider
authority, or module authority.

The desktop CLI can render equivalent evidence pages from completed run
artifacts. Rendered PNGs must include dimensions, nonblank content evidence,
and a JSON sidecar before they are accepted as visual evidence.
Argument parser construction lives in `tools/hostessctl/cli_parser.py`; it
receives platform defaults from `tools/hostessctl/hostessctl.py` and does not
import command implementations. The CLI root stays the platform default,
dispatch, and compatibility-wrapper facade.
Shared process helpers live in `tools/hostessctl/runtime.py`, and package
names, Android actions, remote artifact paths, Makepad defaults, and broker
identity helpers live in `tools/hostessctl/platform_defaults.py`.
Live capture, Polar selected-module replay, Android live/replay launch, live
evidence validation, and runtime artifact pulls live in
`tools/hostessctl/live_capture_routes.py`.
Desktop PMB replay, PMB live-route self-test, and PMB shell-handoff validation
live in `tools/hostessctl/pmb_desktop_routes.py`; Android/Quest PMB replay,
controller preflight, and simulated/physical live routes live in
`tools/hostessctl/pmb_android_routes.py`.
Makepad PMB provider setup lives in `tools/hostessctl/makepad_pmb_setup.py`,
and foreground broker telemetry observation lives in
`tools/hostessctl/broker_telemetry_routes.py`.
Telemetry command dispatch, Makepad render pulls, shell-contract launch, and
snapshot command dispatch live in `tools/hostessctl/telemetry_routes.py`.
Desktop PNG rendering, sidecar writing, and render-output validation live in
`tools/hostessctl/telemetry_render.py` so render evidence remains a focused
helper family instead of growing the CLI root.
Android shell-file and app-private `run-as` file transport lives in
`tools/hostessctl/android_files.py`, with route-level cleanup and compatibility
facades in `tools/hostessctl/android_artifacts.py`.
Manifold broker WebSocket transport lives in
`tools/hostessctl/broker_transport.py`: handshake/framing, Manifold command
envelopes, ACK normalization, retry connection, and stream-event timestamp
aliasing are isolated from route orchestration. Projected Motion Breath broker
publication and receipt listening live in
`tools/hostessctl/pmb_broker_bridge.py`.
Projected-motion-breath evidence construction and validation live in
`tools/hostessctl/pmb_evidence.py`. PMB route modules own desktop, Android,
and Quest route orchestration, while PMB contract constants, replay/self-test
evidence builders, and PMB validation reports remain separate from host-run
evidence writing. Host-run evidence writers live in
`tools/hostessctl/pmb_host_run_evidence.py`, and shared PMB package snapshot,
scorecard, host-app, timestamp, and path helpers live in
`tools/hostessctl/pmb_support.py`.
Manifold value recording planning and broker capture orchestration live in
`tools/hostessctl/manifold_recording.py`: the provider registry,
`record-values` route planner, Quest broker WebSocket capture, Makepad
controller-pose provider setup, and PMB live processor bridge execution are
kept out of the CLI root. `hostessctl.py` preserves thin wrappers for existing
tests and scripts.
Broker telemetry and Manifold value-recording evidence construction lives in
`tools/hostessctl/recording_evidence.py`. Recording evidence schemas,
validators, scorecards, and host-run wrappers are isolated from command
orchestration.

Processor modules are selected by module id. For deterministic replay, Hostess
delegates formula execution and dependency resolution to the package Rust
processor core, then validates the graph-resolved evidence. Desktop live module
capture now keeps acquisition in Hostess, writes captured HR/RR and ACC buffers
into the package runtime input shape, and delegates selected module outputs to
the same Rust graph runner.

The current selected modules cover HRV window, RMSSD gain, coherence, breath
volume from ACC, breath dynamics, and HRVB resonance amplitude. Coherence is
computed at runtime from a live HR/RR capture by resampling a 64-second RR
window to 128 uniform samples and producing the package-defined spectral ratio
plus normalized score fields.

The phone/headset path uses a JNI bridge from the app shell to the same package
runtime ABI. The bridge is recorded in `docs/ON_DEVICE_RUNTIME_BRIDGE.md`.
Java/Kotlin owns acquisition and display only; selected processor outputs come
from the Rust graph report.

The telemetry panel boundary is recorded in `docs/TELEMETRY_GUI.md`.

For the Quest Makepad Matter surface path, Hostess remains the app-shell and
evidence boundary. `apps/hostess-t-makepad/src/recorded_hand_surface.rs` loads
staged recorded bind rigs and compact joint clips from app-private files for
recorded replay evidence, then submits the cached recorded-hand builder plus
the current compact joint frame to the Quest-Makepad Matter worker so source
frame construction happens off the app/render thread. It requests full GPU
oracle payloads only for bounded proof cadence; ordinary recorded replay uses
the Matter-only source-frame option. Source selection now keeps the fallback
`recorded-or-positions-replay`, the explicit `recorded-hand-replay` proof mode,
and the `positions-only-surface` smoke mode distinct. The explicit recorded
mode is the live-input-equivalent replay provider for GPU proof evidence: it
does not silently fall back to baked positions, requests two mesh-SDF proof
markers so renderer-lifetime program reuse is observable, expects the scaled
proof path to report at least `sampleCount=8`, and still keeps all hand frames,
meshes, dense SDF cells, and GPU buffers off settings/control JSON.
`apps/hostess-t-makepad/src/live_hand_surface.rs`
observes live Makepad `XrHandMeshBindData` plus `XrHand` updates and converts
them into the same bind-mesh-plus-compact-joint-frame shape. When an explicit
`live-openxr-hand-*` source mode is selected, Hostess submits the cached live
source-frame builder plus compact joint frame to the same Matter worker path as
recorded replay. Source-frame expansion and optional GPU oracle payload
packaging happen on the worker thread, with full GPU oracle payloads requested
only at bounded proof cadence. The live path does not own Matter CPU
skinning/SDF truth and does not route hand meshes, joint frames, fields,
particles, or GPU buffers through settings/control JSON.

`apps/hostess-t-makepad/src/makepad_diagnostics.rs` owns app-level diagnostic
marker emission, marker token formatting, bounded cadence helpers, raw camera
event markers, YUV texture handles, and runtime target-footprint marker
augmentation so the Makepad app root remains app-shell wiring.

`apps/hostess-t-makepad/src/broker_h264_runtime.rs` owns broker-H264 and
remote-camera runtime key parsing, texture-path selection, source-sampling
selection, stream-port defaults, target-screen fallback rectangles, and
`ExternalH264VideoSource` construction. The app root keeps the paired import
event orchestration and delegates source planning through thin wrappers.

`apps/hostess-t-makepad/src/makepad_stereo_camera_panel.rs` owns the Rust
`DrawMakepadStereoCameraPanel` and `MakepadStereoCameraPanel` types, shader
uniform application, texture slot binding, target-footprint push state, and
horizontal alignment tuning application. It also owns the panel live-design
`script_mod!` block, including draw shader defaults and widget defaults. The
app root registers the panel module before the Hostess app layout script and
keeps the app UI `startup()` block as app-shell wiring.

Hostess settings hotload follows the repo-family settings invalidation policy:
settings writes are active control-plane transactions that publish a compact
revision sidecar; runtime consumers compare global then scoped hashes before
parsing detailed settings; adoption evidence must distinguish seen, applied,
and rejected revisions. Hostess may stage and observe settings, but it must not
turn settings JSON into a frame, field, particle, or GPU-buffer transport.
The current app emits
`RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS_ADOPTION` after a runtime settings
detail read, recording the scoped revision key, subscribed scopes, selected
gate, and applied/rejected status.

`apps/hostess-t-makepad/src/makepad_runtime_config.rs` owns canonical
renderer-neutral projection runtime keys, typed parsing, layered resolution,
and manifest marker formatting. Accepted external spellings for launch extras,
Android properties, and environment variables live in
`apps/hostess-t-makepad/src/makepad_runtime_config/aliases.rs` and are
re-exported through the parent module only for facade compatibility. Keep
legacy or retired names out of the canonical registry unless a compatibility
bridge is explicitly approved and covered by the alias tests.
Retired projection spellings that should be rejected by active parsing but may
need property or environment cleanup live in
`apps/hostess-t-makepad/src/makepad_runtime_config/retired_aliases.rs`. This
ledger is documentation and hygiene input, not a resolver table.

`apps/hostess-t-makepad/src/hostess_contracts/legacy_rusty_xr_schemas.rs`
is the frozen compatibility ledger for old `rusty.xr.*` schema IDs still
serialized by Hostess-local contract DTOs. Contract modules re-export those
constants to preserve the existing facade, but new default-lane schema work
belongs in the owning Morphospace lane rather than adding more old Rusty-XR
defaults.

After a raw capture validates, `hostessctl` writes a
`rusty.manifold.host_run.run_evidence.v1` wrapper with a scorecard so the live
run is tied back to the Manifold Hostess contract spine.

## Non-Scope

This repo does not define package semantics, dynamic loading, product UI, or a
long-lived runtime daemon.
