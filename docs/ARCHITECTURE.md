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
`apps/hostess-t-makepad/src/companion_frontend.rs` owns the source/fixture-only
Makepad projection of Hostess companion catalog and Quest device-link reports.
It reduces `rusty.hostess.companion.catalog.v1` and
`rusty.quest.device_link.v1` evidence into compact rows and marker lines for a
future Makepad panel; it does not own validation, setup, transport, or command
authority.

The Windows companion shell lives in `apps/hostess-companion-wpf`. It is a WPF
operational shell over Hostess readiness reports, Rusty GUI companion
descriptors, and Hostess/Manifold bridge-command evidence. It calls
`hostessctl companion-readiness` and `hostessctl companion-catalog`, displays
Readiness, Session, Devices, Transports, Commands, and Evidence tables plus
selected-row details, and does not implement dependency, device, broker,
descriptor, command authority, session orchestration, or runtime acceptance
logic inside WPF handlers.
WPF projection helpers under `apps/hostess-companion-wpf/ViewModels` translate
Hostess connectivity reports and Quest `rusty.quest.device_link.v1` artifacts
into operator rows for Devices, Transports, and Connectivity. Those helpers
keep UI composition reusable while preserving the authority boundary: Hostess
and Quest reports own readiness, stream capabilities, subscriber delivery, and
command-stage truth; WPF only renders and drills into the evidence.
Page-owned viewmodels keep the row projection families separated:
`ReadinessPageViewModel`, `DevicesPageViewModel`,
`ConnectivityPageViewModel`, `SessionPageViewModel`,
`TransportsPageViewModel`, `CommandsPageViewModel`, and
`EvidencePageViewModel` own their rows and selected-detail state.
`WorkspacesPageViewModel` renders catalog workspace descriptors so operators can
see which modules a workspace composes without letting WPF redefine module or
transport semantics. `MainWindowViewModel` remains the XAML-compatible
coordinator and service requester.
`OperatorActionCatalog` maps each visible WPF command to its Hostess
CLI-equivalent route, evidence artifact, authority owner, and test coverage.
Session browsing follows the same rule through `companion-session history`,
which emits `rusty.hostess.companion.session_history.v1`; WPF loads selected
session artifacts after that route has supplied the report index.

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
Quest questionnaire operator bridging lives in
`tools/hostessctl/questionnaire_bridge.py`. It is a low-rate command/status
route for foreground panel requests, not a data-plane path; answer data stays
with the caller-owned `content://` result URI described by the panel contract.
Android shell-file and app-private `run-as` file transport lives in
`tools/hostessctl/android_files.py`, with route-level cleanup and compatibility
facades in `tools/hostessctl/android_artifacts.py`.
Manifold broker WebSocket transport lives in
`tools/hostessctl/broker_transport.py`: handshake/framing, Manifold command
envelopes, ACK normalization, retry connection, and stream-event timestamp
aliasing are isolated from route orchestration. Projected Motion Breath broker
publication and receipt listening live in
`tools/hostessctl/pmb_broker_bridge.py`.
Bridge command execution lives in
`tools/hostessctl/bridge_command_routes.py`. It consumes a UI-neutral
`rusty.hostess.bridge_command.request.v1` command request, sends the Manifold
command envelope through `broker_transport.py`, subscribes to the selected
runtime receipt stream, waits for authority ACK and runtime/applied receipts,
and emits bridge-route evidence. It is the shared backend route that WPF,
Makepad, and future UI shells should call instead of adding UI-local command
acceptance logic.
The Hostess Makepad broker-stream runtime consumer lives in
`apps/hostess-t-makepad/src/manifold_bridge_command_subscriber.rs`. It
subscribes to `stream.hostess.makepad.bridge_command`, reuses
`bridge_command_inbox` to apply the benign safe-probe request, and publishes
`rusty.hostess.makepad.bridge_command_runtime_receipt.v1` on
`stream.hostess.makepad.bridge_command.receipt`.
Connected-Quest broker-stream command orchestration lives in
`tools/hostessctl/bridge_command_live_android_routes.py`. It owns the Hostess
setup evidence around the shared command path: launch/check the Quest broker,
prepare the serial-scoped ADB forward, wait for the forwarded broker socket,
launch/check Hostess Makepad, then delegate the actual command to
`bridge_command_routes.py`. WPF, Makepad, and future frontends can request this
route, but they still render the sidecar instead of deciding broker authority
or runtime acceptance themselves.
Quest/Android app-private bridge command proof lives in
`tools/hostessctl/bridge_command_android_routes.py` plus the Hostess Makepad
`bridge_command_inbox` module. It stages the same request shape into the
app-private settings directory with serial-scoped ADB and accepts only the
benign `hostess.makepad.bridge_probe.set_marker` command. This route proves
that the Quest runtime emitted `runtime_accepted` and `applied` receipts, but
it intentionally does not claim Manifold `authority_accepted`; broker-stream
dispatch remains the separate command-authority path.
The broker-authorized Android command route is an explicit bring-up bridge over
that gap: `run-bridge-command-android --broker-authority` first sends the
command envelope to the Manifold broker and requires an accepted ACK, then
stages the app-private runtime delivery request with
`broker_authority_accepted=true`. It records
`sent -> transport_ok -> authority_accepted -> runtime_accepted -> applied`,
but the runtime delivery leg is still app-private JSON. When the selected
authority is the Quest broker APK, `--adb-forward-broker` prepares the host TCP
forward before the WebSocket authority request; the forward is transport setup
evidence, not runtime acceptance.
Bridge-route evidence normalization lives in
`tools/hostessctl/bridge_route_evidence.py`. It converts Hostess route-stage
observations into `rusty.manifold.bridge.route_evidence.v1` and validates the
route-required stages from a Manifold descriptor, explicit CLI requirements, a
Hostess input receipt, or the known bridge-route fixtures. It does not open
sockets, run ADB, launch apps, or decide whether a command is authoritative;
WPF, Makepad, and future frontends can call the same low-rate evidence adapter
and render the resulting validation rows without becoming runtime authority.
Windows companion readiness lives in
`tools/hostessctl/companion_readiness.py`. It emits
`rusty.hostess.companion.readiness_report.v1` for host, toolchain, device,
runtime, broker package/process, ADB forward mapping, forwarded broker socket,
direct broker socket, network, and Rusty GUI descriptor checks. Readiness is
Hostess-owned execution/evidence, not GUI authority: WPF, Makepad, CLI, and
future frontends render the report and may request refreshes, but they do not
decide that ADB, broker routes, app-private receipts, package install state, or
runtime acceptance are valid.
Windows companion descriptor discovery lives in
`tools/hostessctl/companion_catalog.py`. It emits
`rusty.hostess.companion.catalog.v1` from Rusty GUI companion module,
workspace, and transport descriptors, validates that GUI/WPF do not claim
command or route authority, and gives WPF, Makepad, CLI, and future frontends a
shared catalog for module lists, transport costs, and evidence artifact panels.
The same report carries descriptor semantic issues, including workspace
references to unknown modules, so operator frontends can render invalid catalog
evidence without becoming the validator.
The repo-wide check runs the catalog smoke for both `wpf` and `makepad`
frontends. This keeps the Hostess Makepad validation workspace honest: if a
workspace claims Makepad support, its selected modules and required transport
descriptors must survive the same Hostess catalog filtering and validation as
WPF.
Windows companion session orchestration lives in
`tools/hostessctl/companion_session.py`. It emits
`rusty.hostess.companion.session.v1` by composing readiness, descriptor
catalog, connected-Quest broker-stream command probing, app-private fallback
recovery, validation sidecars, and artifact references into ordered phases.
This route is the frontend-neutral session backend for WPF, Makepad, CLI, and
future companion shells; frontends render phases/actions/issues and may request
the run, but they do not decide broker authority, runtime acceptance, fallback
recovery, or evidence validity.
Quest device-link report adaptation lives in
`tools/hostessctl/device_link_report.py`. It summarizes Hostess readiness and
bridge execution sidecars into the Quest-owned `rusty.quest.device_link.v1`
shape so WPF, Makepad tooling, CLI, and later frontends can inspect device
identity, ADB forward/tunnel state, broker readiness, runtime subscriber
health, command-result stages, and stream capabilities without becoming the
device-link authority. The same module also derives measured
`rusty.quest.device_link.stream_capability.v1` descriptors from connectivity
probe artifacts; QCL-080 app-owned UDP evidence becomes a reusable capability
row only when the runtime marker, UDP freshness counters, product-scoped WPF
listener firewall verification, and promotion decision are all preserved.
QCL-081 LSL artifacts emit their own descriptor instead of falling through to
UDP: host-loopback evidence stays candidate, blocked Quest-runtime preflight
keeps the missing `pylsl/liblsl` producer gate visible, and usable LSL requires
Quest-runtime, study-adapter, or broker-owned sample-continuity evidence.
The same device-link adapter owns the planned downloadable
`rusty.quest.device_link.install_environment_test_suite.v1` descriptor. That
suite is the frontend-neutral map for host install checks, network adapter and
firewall checks, Quest device checks, protocol capability checks, and RTT/clock
alignment strategy. Hostess still owns execution through QCL reports; WPF,
Makepad, CLI, and future installers should render and request the suite rather
than embedding protocol-specific dependency logic.
Suite execution lives in `tools/hostessctl/connectivity_suite.py`. It consumes
the descriptor, runs selected QCL slots through the existing probe adapters,
records a host snapshot for tools, network profiles, firewall listener state,
hotspot state, and Bluetooth readiness, then emits
`rusty.quest.device_link.install_environment_suite_run.v1`. Aggregate status is
allowed to warn on host posture, such as Public firewall profile or missing
listener allow rule, even when all fixture protocol slots pass. That makes the
future installer and WPF page honest about the install environment without
turning either frontend into a validator.
Windows firewall listener lifecycle also stays in Hostess:
`connectivity-probe windows-firewall-rule --action plan|apply|verify|remove`
emits the rule report and verification evidence. WPF requests these actions and
renders the report; it does not invent firewall scope rules or treat broad
diagnostic Python listener allowances as product readiness.
Quest connectivity lab probing lives in `tools/hostessctl/connectivity_probe.py`.
It emits the experimental `rusty.quest.connectivity_topology_probe.v1` report
shape for QCL fixture and live same-Wi-Fi probes. Hostess owns execution and
evidence packaging; Rusty Quest/Manifold remain the future contract and
command/stream authority. The live QCL-010 route uses serial-scoped ADB to
observe headset Wi-Fi identity, then tests LAN reachability separately so ADB
is not mistaken for the data path.
The same lab module owns Bluetooth QCL-050/QCL-051 readiness and payload
evidence. QCL-051 uses the Hostess T Android app as an app-owned BLE/GATT
server plus `tools/connectivity_probe/qcl051_ble_gatt_client` as the Windows
WinRT BLE/GATT client. QCL-050 uses the same app-owned pattern with an Android
RFCOMM server and `tools/connectivity_probe/qcl050_rfcomm_client` as the
Windows WinRT RFCOMM helper. Hostess joins both reports and records launch
preconditions such as the Quest VR lockscreen separately from protocol
failures. QCL-051 is promotable in the tested Windows-central/Quest-GATT-server
direction after reconnect evidence; QCL-050 remains blocked until Classic
Bluetooth pairing/service visibility is proven. This borrows Polar/PMD failure
vocabulary for permissions, service discovery, control writes, handoff timeout,
and cleanup, but PMD physical sensor ownership remains with Manifold/PMB
routes rather than QCL-051.
The same lab module owns protocol-fit reports for LSL, OSC, and ZeroMQ.
QCL-081 treats Manifold-owned LSL broker evidence the same way QCL-084 treats
the Manifold ZeroMQ broker path: Hostess shells to the Manifold JSON report
tool, requires `evidence_tier=broker_owned`,
`authority.owner=rusty.manifold.transport`, passing bridge-route evidence,
complete sample continuity, and monotonic received sequences, then wraps that
report as Hostess connectivity evidence for WPF and protocol-matrix rendering.
Quest-runtime LSL promotion remains separate and blocked until the Quest side
can emit its own `pylsl/liblsl` sample-continuity evidence.
QCL-084 treats ZeroMQ as a generic data-protocol capability: manifests,
endpoint/open-mode config, bounded receiver queues, message/drop/decode
counters, and optional runtime feature gates belong to a reusable ZeroMQ
adapter/module. Goofi Pipe is only an example source profile through a sidecar
that converts Goofi PAIR/send_pyobj payloads into bounded JSON for the generic
ZeroMQ route. The generic proof now lives in the Manifold-owned
`rusty-manifold-zmq` adapter, while Hostess can still ingest the public
Rusty-XR compatibility proof and the Goofi sidecar witness log. Neither WPF
nor Hostess should make Goofi the protocol authority. The promotable
`native-rust-broker` QCL-084 path is still CLI-owned: Hostess shells to the
Manifold adapter's JSON report mode, requires `evidence_tier=broker_owned`,
`authority.owner=rusty.manifold.transport`, passing bridge-route evidence,
zero drops, and zero decode errors, then wraps that report as Hostess
connectivity evidence for WPF and protocol-matrix rendering.
`hostessctl connectivity-probe protocol-matrix` is the roll-up contract for
operator protocol promotion views. It consumes existing suite, probe,
device-link, and stream-capability artifacts and classifies each protocol by
evidence tier, promotion state, and missing gate. WPF renders this matrix as a
requester/inspector; promotion rules stay in the CLI/report module so fixture
and host-loopback LSL/OSC/ZeroMQ evidence cannot accidentally become UI-only
acceptance proof.
Projected-motion-breath evidence construction and validation live in
`tools/hostessctl/pmb_evidence.py`. PMB route modules own desktop, Android,
and Quest route orchestration, while PMB contract constants, replay/self-test
evidence builders, and PMB validation reports remain separate from host-run
evidence writing. Host-run evidence writers live in
`tools/hostessctl/pmb_host_run_evidence.py`. Native Rusty Quest renderer PMB
receipt policy parsing lives in `tools/hostessctl/pmb_native_receipts.py`; it
accepts native projection-target effective markers as app-side consumption
evidence for the canonical `stream.breath.state` and
`stream.breath.state.value` contract instead of requiring the Makepad-only
`stream.breath.feedback_receipt` stream. Shared PMB stream IDs, contract
authority constants, package snapshot, scorecard, host-app, timestamp, and path
helpers live in `tools/hostessctl/pmb_support.py`.
Manifold value recording planning and broker capture orchestration live in
`tools/hostessctl/manifold_recording.py`: the provider registry,
`record-values` route planner, Quest broker WebSocket capture, Makepad
controller-pose provider setup, and PMB live processor bridge execution are
kept out of the CLI root. `hostessctl.py` preserves thin wrappers for existing
tests and scripts.
Native Rusty Quest Breathing Room setup lives in
`tools/hostessctl/native_breathing_room_setup.py`. It consumes the canonical
Rusty Quest native runtime profile as the startup settings authority, records
the profile SHA-256 in the Hostess setup receipt, and allows only the named
projection-target, PMB bridge, and Manifold broker endpoint properties to vary
per run. The setup receipt also records the PMB stream contract authority and
rejects custom state/value stream IDs until the broker publisher and native
receipt policy can be parameterized together.
Broker telemetry and Manifold value-recording evidence construction lives in
`tools/hostessctl/recording_evidence.py`. Recording evidence schemas,
validators, scorecards, and host-run wrappers are isolated from command
orchestration.
Quest Makepad GPU summary validation keeps
`tools/check_makepad_quest_gpu_evidence.py` as the stable checker command and
CLI/import facade. Shared proof-marker parsing lives in
`tools/makepad_quest_gpu_evidence/proof_lines.py`, while GPU force
candidate/gate/freshness/residency/runtime-authority validation lives in
`tools/makepad_quest_gpu_evidence/force_authority.py`. The facade keeps schema
loading, cadence/stale checks, mesh-SDF checks, and compact summary assembly;
new independent evidence families should move into sibling modules when they
start adding pressure.
Studio platform-smoke staging helpers are split by workflow phase:
`tools/studio_staging/platform_smoke.py` remains the import facade, while
`platform_smoke_plan.py`, `platform_smoke_execution.py`,
`platform_smoke_operator_start.py`, `platform_smoke_execution_report.py`, and
`platform_smoke_evidence.py` own plan/approval, execution, operator-start,
report, and evidence review behavior. These helpers are staging contract and
review evidence builders; they must not start Studio, Hostess, Quest, Makepad,
or Manifold runtimes.
Projected-motion-breath release staging helpers follow that same facade
pattern: `tools/studio_staging/pmb_release.py` remains the import surface,
while `pmb_validation_handoff.py`, `pmb_replay_validation.py`, and
`operator_release.py` own validation handoff, replay validation, and
operator-release readiness behavior.
Hostess staging handoff helpers follow the same facade pattern:
`tools/studio_staging/staging_handoff.py` remains the import surface, while
`staging_handoff_acceptance.py`, `staging_handoff_file_plan.py`,
`staging_handoff_file_copy.py`, `staging_handoff_payload_manifest.py`, and
`staging_handoff_downstream_shell.py` own acceptance, file planning, file copy,
payload manifest, and downstream shell selection behavior. The file-copy helper
may copy files under validated staging roots, but these modules must not launch
Studio, Hostess, Quest, Makepad, or Manifold runtimes.
The Studio staging request command follows that same facade pattern:
`tools/studio_staging_request.py` remains the stable import/CLI surface,
`tools/studio_staging/request_cli.py` owns command orchestration across the
already split staging families, `request_cli_parser.py` owns the argument
surface, and `request_cli_validation.py` owns terminal validation-output
generation. The CLI modules may coordinate artifacts and validation outputs,
but new schema or workflow authority belongs in the focused helper modules.
The Studio staging request tests follow the same facade pattern:
`tools/test_studio_staging_request.py` remains the stable unittest entry point,
while `tools/studio_staging/request_tests/` groups the coverage by
intake/smoke workflow, platform-smoke control, platform-smoke evidence,
PMB/release, Hostess staging handoff, and CLI fixture-writing families.

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
`ExternalH264VideoSource` construction.

`apps/hostess-t-makepad/src/source_metadata.rs` remains the Makepad
source/import marker facade for runtime target-footprint, source-sampling, and
hardware-buffer import marker helpers. Its `source_metadata/` child modules own
focused metadata families; `broker_projection.rs` owns broker-H264 stream-header
projection metadata parsing, content-geometry marker records, and broker
projection plan decisions.

`apps/hostess-t-makepad/src/projection_geometry.rs` remains the projection-plan
and OpenXR geometry facade. Its `projection_geometry/` child modules own focused
projection support families; `markers.rs` owns Makepad stereo projection
marker/report field formatting and marker-shape tests.

`apps/hostess-t-makepad/src/camera_projection_flow.rs` owns the paired camera
import/projection runtime flow: broker stream-header metadata handling, video
texture update bookkeeping, pending stereo-frame adoption, cadence sample
markers, paired import timers, broker-H264 texture import requests, native
video widget startup, YUV content probes, projection panel texture binding,
projection-complete markers, stereo comparison parity markers, and direct
Camera2 plan probing. The app root keeps top-level event ordering and calls
this module through split `App` methods.

`apps/hostess-t-makepad/src/hostess_camera_model.rs` remains the public
compatibility facade for app-neutral camera helpers. Its
`hostess_camera_model/` child modules own source selection, projection
footprint/layout and border geometry, camera basis/projection math, homography
and temporal smoothing, and timestamp matching.
`apps/hostess-t-makepad/src/hostess_contracts/camera.rs` remains the
camera-contract facade for shared primitives, diagnostics, frame metadata,
and calibration/source diagnostics. Its `hostess_contracts/camera/` child
modules own focused camera contract families; `source_sampling.rs` owns
source-sampling DTOs, texture transform helpers, and source-sampling schema
acceptance, `temporal_projection.rs` owns frame timing, projection state,
visual projection state, temporal policy, and metrics, while `texture_lane.rs`
owns camera texture-lane DTOs, validation, and current-or-legacy schema
acceptance.

`apps/hostess-t-makepad/src/frame_orientation.rs` owns Hostess-local
direct-camera and broker-H264 source-raster orientation decisions plus shared
broker pair pose-source combination. `source_sampling.rs` consumes the
orientation decision when building source-sampling contracts and markers, and
`camera_pair.rs` consumes the same pose-source helper for broker projection
plans.

`apps/hostess-t-makepad/src/makepad_stereo_camera_panel.rs` owns the Rust
`DrawMakepadStereoCameraPanel` and `MakepadStereoCameraPanel` types, shader
uniform application, texture slot binding, target-footprint push state, and
panel-side horizontal alignment uniform application. It also owns the panel
live-design `script_mod!` block, including draw shader defaults and widget
defaults. The app root registers the panel module before the Hostess app layout
script.

`apps/hostess-t-makepad/src/matter_world_particle_billboard.rs` and
`apps/hostess-t-makepad/src/matter_world_adf_debug.rs` own the
Hostess-local world-particle and ADF debug renderer widgets plus their
Makepad widget-default `script_mod!` blocks. Matter, Optics, and
Quest-Makepad remain the runtime truth and renderer-neutral row authorities;
these modules only draw bounded Makepad evidence rows.

`apps/hostess-t-makepad/src/makepad_app_live_design.rs` owns the Hostess app
layout `script_mod!` block and `startup()` UI tree. The app root calls this
module after all widget/default modules are registered, then keeps runtime
state, event handling, and data-plane adoption wiring in Rust.
`apps/hostess-t-makepad/src/app_mesh_replay_runtime.rs` owns selected
effective-settings adoption, mesh replay stepping, Matter/particle/stimulus
runtime resets, and panel/world cadence binding.
`apps/hostess-t-makepad/src/makepad_effective_settings.rs` remains the
effective-settings receipt/runtime-selection facade.
`apps/hostess-t-makepad/src/makepad_effective_settings/revision.rs` owns the
revision sidecar identity, scoped invalidation keys, and path/mtime fallback
comparison helper used by runtime and GPU-proof adoption gates.
`apps/hostess-t-makepad/src/makepad_effective_settings/tests.rs` owns the
effective-settings regression fixtures so the facade does not also act as the
test suite container.
`apps/hostess-t-makepad/src/app_stimulus_runtime.rs` owns stimulus field panel
binding, runtime XR projection rows, bounded volume preview probe polling, and
image-preview texture adoption.
`apps/hostess-t-makepad/src/app_projection_target.rs` owns the app-shell
projection-target control loop: controller offset/scale updates, breath-source
target-scale adoption, and related runtime markers. Pure projection-target
math/settings helpers remain in `projection_target_controls.rs`.
`apps/hostess-t-makepad/src/app_horizontal_alignment.rs` owns the app-shell
horizontal-alignment tuning surface: runtime-resolution fallback, legacy
hotload values, change detection, hotload markers, and panel binding.
`apps/hostess-t-makepad/src/main_tests.rs` owns app-root regression tests that
need private access to this shell wiring.

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

`apps/hostess-t-makepad/src/makepad_runtime_config.rs` owns typed parsing,
layered resolution, and the runtime-config facade. Canonical renderer-neutral
projection runtime keys and ownership metadata live in
`apps/hostess-t-makepad/src/makepad_runtime_config/projection_keys.rs`.
Alias evidence types live in
`apps/hostess-t-makepad/src/makepad_runtime_config/alias_model.rs`, keeping
legacy/deprecated vocabulary with the alias ledger instead of the generic
runtime-config type section.
Projection manifest marker formatting and alias-evidence tokenization live in
`apps/hostess-t-makepad/src/makepad_runtime_config/manifest.rs` so the core
parser/resolver does not carry diagnostic marker formatting. Accepted external
spellings for launch extras, Android properties, and environment variables live in
`apps/hostess-t-makepad/src/makepad_runtime_config/aliases.rs` and are
re-exported through the parent module only for facade compatibility. Keep
legacy or retired names out of the canonical registry unless a compatibility
bridge is explicitly approved and covered by the alias tests.
Retired projection spellings that should be rejected by active parsing but may
need property or environment cleanup live in
`apps/hostess-t-makepad/src/makepad_runtime_config/retired_aliases.rs`. This
ledger is documentation and hygiene input, not a resolver table.

Hostess-local camera, home, and kiosk DTO constructors now default to
`rusty.hostess.*` schema IDs. `apps/hostess-t-makepad/src/hostess_contracts/legacy_rusty_xr_schemas.rs`
is the frozen compatibility ledger for old `rusty.xr.*` schema IDs accepted
from serialized compatibility inputs. Contract modules re-export both current
Hostess defaults and legacy constants to preserve the existing facade, but new
default-lane schema work belongs in the owning Morphospace lane rather than
adding more old Rusty-XR defaults. The source-sampling serde fixture at
`tools/quest-camera-profile/fixtures/source-sampling-contracts.cross-backend.jsonl`
keeps current Hostess defaults and one legacy Rusty-XR input in the same
validation path.

After a raw capture validates, `hostessctl` writes a
`rusty.manifold.host_run.run_evidence.v1` wrapper with a scorecard so the live
run is tied back to the Manifold Hostess contract spine.

## Non-Scope

This repo does not define package semantics, dynamic loading, product UI, or a
long-lived runtime daemon.
