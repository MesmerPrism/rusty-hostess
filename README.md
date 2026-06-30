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

## Agent Instructions

Use `AGENTS.md` as the first-hop policy surface. Detailed Hostess agent
runbooks live under `docs/agent-instructions/`, including the Quest Makepad APK,
settings, particle/SDF/ADF/GPU, and live/recorded hand evidence route in
`docs/agent-instructions/quest-makepad-runbook.md`.

## Current Apps

- `apps/hostess-t-desktop/capture_polar.py`: desktop live capture and runtime
  Polar stream validation using a local Python dependency.
- `apps/hostess-t-makepad`: the intended Hostess T GUI surface. It can seed
  itself from bounded `TelemetrySnapshot` checkpoint JSON, then watch an
  append-only telemetry JSONL stream and maintain independent rolling plots per
  datastream. Snapshots are evidence/checkpoint artifacts, not the live data
  plane. Its companion frontend projection reduces shared catalog, device-link,
  protocol-matrix, and companion-report projection artifacts into compact rows
  without owning validation, artifact selection, or protocol promotion.
- `apps/hostess-t-android`: Java-only Android APK built with Android
  command-line tools. The same APK can run mobile and headset profiles, and
  owns platform lifecycle, BLE acquisition, permissions, ADB command bridging,
  app-private evidence storage, and the Hostess JNI bridge. Its native Canvas
  telemetry view is fallback/debug-only platform evidence plumbing; Makepad is
  the scalable GUI path.
- `apps/hostess-t-android/src/main/java/.../MainActivity.java`: Android
  lifecycle, action routing, BLE capture, top-level evidence file writes, and
  handler registration. Fallback render UI and PMB evidence/package helpers
  live in sibling Java files.
- `apps/hostess-t-android/src/main/java/.../PlatformDebugTelemetryView.java`:
  fallback/debug Canvas telemetry renderer and PNG validation.
- `apps/hostess-t-android/src/main/java/.../TelemetryRenderMetadata.java`:
  telemetry render sidecar JSON contract.
- `apps/hostess-t-android/src/main/java/.../HostessAssetStore.java` and
  `PmbPackageAssets.java`: Android asset reads, package fixture copy, and
  manifest SHA snapshots for packaged PMB assets.
- `apps/hostess-t-android/src/main/java/.../PmbAndroidEvidence.java`: PMB
  Android replay/controller-preflight evidence builders, scorecards, and
  failure report helpers.
- `apps/hostess-companion-wpf`: Windows companion shell. It renders Hostess
  readiness reports plus descriptor-driven Session, Devices, Transports,
  Commands, and Evidence pages through WPF while calling `hostessctl
  companion-readiness`, `hostessctl companion-catalog`,
  `hostessctl companion-session run`, `hostessctl companion-report projection`,
  and bridge-command routes as backend authority paths. Session-linked
  `rusty.quest.device_link.v1` artifacts are projected into Devices and
  Transports rows so operator UI stays reusable without becoming device-link
  authority.
- `tools/hostessctl/hostessctl.py`: compatibility facade for command dispatch,
  platform defaults, and existing imports. Route bodies live in focused helper
  modules so new command behavior does not accumulate in the CLI root.
- `tools/hostessctl/platform_defaults.py`: Hostess app package names, Android
  actions, remote artifact paths, Makepad defaults, and broker identity
  helpers.
- `tools/hostessctl/runtime.py`: shared process execution helpers and repo-root
  resolution for command route modules.
- `tools/hostessctl/live_capture_routes.py`: desktop live capture, Polar
  selected-module replay, Android live/replay launch, live evidence validation,
  and runtime artifact pulls.
- `tools/hostessctl/pmb_desktop_routes.py`: desktop
  projected-motion-breath replay, live-route self-test, and shell-handoff
  evidence routes.
- `tools/hostessctl/pmb_android_routes.py`: Android/Quest
  projected-motion-breath replay, controller preflight, and
  simulated/physical live routes.
- `tools/hostessctl/broker_telemetry_routes.py`: foreground broker telemetry
  observer route and evidence pull/validation orchestration.
- `tools/hostessctl/makepad_pmb_setup.py`: Makepad PMB provider setup,
  breath-feedback receiver properties, physical-provider properties, and broker
  runtime permission grants used by PMB routes.
- `tools/hostessctl/native_breathing_room_setup.py`: native Rusty Quest
  Breathing Room setup receipts derived from the canonical Rusty Quest native
  runtime profile, with only per-run projection/PMB overrides applied, plus
  Hostess/Manifold PMB stream subscription intent. Receipts record the source
  profile SHA-256 and the exact parameterized property list so Hostess cannot
  silently become a partial parallel settings layer.
- `tools/hostessctl/telemetry_routes.py`: Android-class app-rendered PNG export
  for phone and headset telemetry evidence, desktop PNG rendering dispatch,
  Makepad render pulls, shell-contract launch, and snapshot command dispatch.
  Desktop rendering, PNG validation, and render-sidecar helpers live in
  `tools/hostessctl/telemetry_render.py`. Renders must pass dimension and
  nonblank checks and write a JSON sidecar beside the PNG.
- `tools/hostessctl/questionnaire_bridge.py`: low-rate Quest questionnaire
  operator bridge routes. It exposes status/open/dismiss CLI commands and a
  local HTTP bridge for Windows operator smoke tests while preserving the
  caller-owned Android panel result URI contract.
- `tools/hostessctl/android_artifacts.py`: route-level Android cleanup,
  app-private `run-as` facade functions, evidence waits, and Makepad
  render-sidecar polling.
- `tools/hostessctl/android_files.py`: Android shell-file and app-private
  `run-as` file helpers used by Hostess CLI routes. Low-level waiting,
  pulling, pushing, and quoting live in this helper.
- `tools/hostessctl/cli_parser.py`: `hostessctl` argument-surface
  construction. It receives platform defaults from the CLI root and imports
  only argument-surface constants, keeping parser churn separate from command
  behavior and route implementation modules.
- `tools/hostessctl/broker_transport.py`: Manifold broker WebSocket protocol
  primitives, command envelope helpers, ACK normalization, retry connection,
  and stream-event aliasing used by recording routes. The CLI root re-exports
  these helpers as a compatibility facade for tests and existing callers.
- `tools/hostessctl/bridge_command_android_routes.py`: headset-backed
  bridge-command proof over the Hostess Makepad app-private command inbox. It
  stages low-rate command JSON with serial-scoped ADB, collects the app-written
  runtime receipt, and emits bridge-route evidence. With `--broker-authority`,
  it first requires Manifold broker command acceptance before staging the
  app-private runtime delivery request. With `--adb-forward-broker`, it prepares
  the host-to-device broker port forward before requesting authority.
- `tools/hostessctl/bridge_command_live_android_routes.py`: connected-Quest
  orchestration for the broker-stream bridge command path. It starts/checks
  the Manifold broker, prepares the ADB TCP forward, starts Hostess Makepad,
  waits for socket/process readiness, then delegates command execution to
  `bridge_command_routes.py` and records setup actions in a Hostess sidecar.
- `tools/hostessctl/bridge_command_routes.py`: frontend-neutral bridge command
  request generation and execution over the Manifold broker WebSocket route.
  It emits/consumes command request JSON, sends a Manifold command envelope,
  waits for authority/runtime receipts, and emits bridge-route evidence for
  WPF, Makepad, and future UI shells.
- `tools/hostessctl/bridge_route_evidence.py`: UI-neutral bridge-route
  evidence normalization and validation. WPF, Makepad, and future frontends can
  feed Hostess stage observations into the same Manifold bridge-route evidence
  shape without becoming command or runtime authority.
- `tools/hostessctl/companion_readiness.py`: Windows companion readiness report
  route. It emits `rusty.hostess.companion.readiness_report.v1` for host,
  toolchain, device, runtime, broker package/process, ADB forward mapping,
  forwarded broker socket, direct broker socket, network, and Rusty GUI
  descriptor checks so WPF, Makepad, CLI, and future frontends can render the
  same precondition state.
- `tools/hostessctl/companion_catalog.py`: Windows companion descriptor catalog
  route. It loads Rusty GUI companion module, workspace, and transport
  descriptors, validates frontend authority boundaries, and emits
  `rusty.hostess.companion.catalog.v1` for WPF, Makepad, CLI, and future
  frontends.
- `tools/hostessctl/companion_session.py`: Windows companion session
  orchestrator. It composes readiness, descriptor catalog, live broker-stream
  command probing, and app-private fallback evidence into ordered phases in
  `rusty.hostess.companion.session.v1` and indexes saved reports through
  `rusty.hostess.companion.session_history.v1` so WPF, Makepad, CLI, and
  future frontends can render the same session state without owning
  orchestration or history enumeration logic.
- `tools/hostessctl/companion_session_defaults.py`: companion-session
  argument defaults shared by the parser and session orchestrator. It keeps
  WPF/CLI receipt wait parity visible without making `cli_parser.py` import
  route implementation code.
- `tools/hostessctl/companion_report_projection.py`: frontend-neutral
  read-only report projection. It emits
  `rusty.hostess.companion.report_projection.v1` from explicit device-link,
  connectivity-probe, firewall-rule, protocol-matrix, and suite-run artifacts
  so WPF, Makepad, CLI automation, and future frontends can compare the same
  operator rows without owning artifact selection, validation, command
  authority, firewall semantics, topology readiness, or protocol promotion.
- `tools/hostessctl/companion_report_transport_coverage.py`: transport
  coverage row helper for companion-report projection. It derives the
  `transport_coverage.summary` row from already-projected source rows so TCP,
  WebSocket, Wi-Fi Direct, other Wi-Fi topologies, and QCL probe IDs stay
  visible without moving topology or protocol-promotion authority into WPF.
  The row also emits `term_gates` and `remaining_live_gates` so operators can
  distinguish Manifold-command WebSocket visibility, QCL-079 generic
  WebSocket evidence, TCP echo/media evidence, and Wi-Fi Direct topology
  visibility from unfinished live product gates.
- `tools/hostessctl/companion_transport_gates.py`: read-only transport gate
  report helper. It consumes the shared companion-report projection and emits
  `rusty.hostess.companion.transport_gate_report.v1` so automation can fail on
  the same `remaining_live_gates` that WPF renders and, when requested, on an
  incomplete protocol-matrix data-protocol summary without moving probe,
  firewall, media, topology, or promotion authority into UI code.
- `tools/hostessctl/companion_transport_gate_actions.py`: static operator
  action catalog for transport gates. It names Hostess CLI routes,
  PowerShell-compatible commands, acceptance artifacts, elevation flags, and
  Quest lease requirements for pending gate guidance; it does not execute
  those actions or clear gates.
- `tools/hostessctl/connectivity_probe.py`: Quest connectivity lab probe
  facade. It emits `rusty.quest.connectivity_topology_probe.v1` reports,
  dispatches QCL routes, and preserves the CLI/report shape for WPF, Makepad,
  and automation. Protocol mechanics live in focused helpers.
- `tools/hostessctl/connectivity_firewall.py`: Windows Firewall listener rule
  planning, apply/verify/remove report shaping, product-rule verification,
  elevation preflight for mutating actions, and Windows network/firewall
  profile summaries used by QCL-010/QCL-080 and WPF operator rows.
- `tools/hostessctl/connectivity_lan.py`: live LAN/device transport helpers
  for serial-scoped Quest ADB identity, host IPv4 selection, same-subnet checks,
  ICMP probes, Windows Mobile Hotspot state collection, TCP echo probes, and
  QCL-010/QCL-011 live report assembly.
- `tools/hostessctl/connectivity_probe_common.py`: shared connectivity report
  helpers for the QCL report skeleton, check rows, issue rows,
  JSON/ADB/PowerShell cleanup, Android readback, and small measurement
  utilities.
- `tools/hostessctl/connectivity_probe_fixtures.py`: QCL fixture report
  construction, damaged fixture variants, and fixture ingestion for media
  session/runtime/receiver artifacts.
- `tools/hostessctl/connectivity_probe_live_reports.py`: pure live report
  shaping for QCL live status derivation, listener rows, protocol topology
  summaries, and measurements. It has no ADB, socket, broker, or protocol
  execution authority.
- `tools/hostessctl/connectivity_probe_validation.py`: shared QCL connectivity
  report schema/status validation used by the probe facade, tests, WPF, Makepad,
  and CLI automation before rendered operator rows are accepted.
- `tools/hostessctl/connectivity_udp.py`: QCL-080 UDP freshness sender/listener
  live report assembly, sender/listener mechanics, Makepad runtime UDP sender
  setup, WPF listener-helper ingestion, and app-owned UDP runtime-marker
  parsing.
- `tools/hostessctl/connectivity_media.py`: QCL-082 binary media-plane fixture
  report helpers, Rusty Quest media-stream session plan ingestion, and
  broker/runtime status artifact ingestion for H.264/TCP framing, command
  acceptance, timestamp, queue/drop/backpressure, source classification,
  shell-display lab gating, and high-rate JSON rejection evidence.
- `tools/hostessctl/connectivity_media_receiver.py`: QCL-082 Hostess
  receiver-counter helpers for bounded `RMANVID1` stream-header and packet
  parsing, bounded TCP receiver capture, receiver sidecar counters,
  runtime-status pairing, optional direct-Wi-Fi topology report pairing, the
  orchestrated product-media live session that arms the receiver before the
  Quest/Manifold source command, and no-decode binary media evidence.
- `tools/hostessctl/connectivity_media_product_plan.py`: read-only QCL-082
  product-media direct-Wi-Fi plan artifacts. It binds the existing
  start_source, runtime-status, product firewall, RMANVID1 capture, QCL-082
  fold-in, protocol-matrix, lease, and acceptance-artifact routes for WPF/CLI
  parity without running the live steps or clearing gates.
- `tools/hostessctl/connectivity_topology.py`: QCL-020/QCL-030/QCL-040/QCL-041
  topology fixture report helpers for Wi-Fi ADB stability, Quest
  LocalOnlyHotspot, and Wi-Fi Direct phone/Windows peer limits. These fixtures
  keep experimental topology rows CLI-visible before any WPF affordance is
  accepted.
- `tools/hostessctl/connectivity_topology_live.py`: read-only live QCL-040/
  QCL-041 Wi-Fi Direct topology preflight. It records Quest feature state and
  Windows adapter state without promoting direct-Wi-Fi topology until peer
  discovery, group formation, socket exchange, and cleanup evidence exists.
- `tools/hostessctl/connectivity_topology_lifecycle.py`: QCL-040/QCL-041
  Wi-Fi Direct lifecycle evidence ingestion. It validates a structured live
  lifecycle artifact and emits the promoted topology report only when feature,
  peer/API, permission, discovery, group formation, bounded TCP socket
  exchange, and cleanup checks pass.
- `tools/hostessctl/connectivity_topology_lifecycle_plan.py`: read-only
  QCL-040/QCL-041 Wi-Fi Direct lifecycle plan artifacts. It binds the Agent
  Board lease, live preflight, source-template, external live-source, and
  normalization routes into one WPF/CLI-equivalent report without running the
  live steps or clearing gates.
- `tools/hostessctl/connectivity_bluetooth.py`: QCL-050/QCL-051 Bluetooth
  RFCOMM and BLE/GATT readiness, Android payload probes, Windows helper
  command construction, live report assembly, reconnect measurements, and
  Bluetooth transport rows.
- `tools/hostessctl/connectivity_data_protocols.py`: QCL-081/QCL-083/QCL-084
  LSL, OSC, and ZeroMQ adapter mechanics, Quest-runtime OSC/ZeroMQ execution
  helpers, live report assembly, source-specific report promotion gates, and
  their protocol-specific evidence-row derivation.
- `tools/hostessctl/connectivity_websocket.py`: QCL-079 generic WebSocket
  protocol-fit helper. It owns the bounded host-loopback HTTP upgrade/echo
  probe, Manifold stream route/evidence ingestion, fixture body,
  authority-boundary checks, command-route rejection, and the rule that
  host-loopback WebSocket evidence is candidate-only until broker-owned or
  Quest-runtime endpoint evidence exists.
- `tools/hostessctl/connectivity_suite.py`: install/environment/protocol suite
  runner. It executes selected QCL slots, records host network/firewall/tool
  snapshots, aggregates grouped results, and emits
  `rusty.quest.device_link.install_environment_suite_run.v1` for WPF, CLI,
  installers, and future frontends.
- `tools/test_hostessctl_connectivity_probe.py`: compatibility facade for the
  QCL connectivity-probe unittest suite. Test-family implementations live in
  `tools/connectivity_probe_tests/` so fixture reports, QCL-082 media receiver
  gates, QCL-079/WebSocket/data-protocol evidence, live transport paths,
  parser coverage, and firewall rule-profile checks can evolve without making
  one multi-authority test file the review surface.
- `tools/hostessctl/pmb_broker_bridge.py`: Projected Motion Breath feedback
  publication, breath-source selection, and PMB receipt listening over the
  broker transport.
- `tools/hostessctl/manifold_recording.py`: Manifold value provider registry,
  `record-values` route planning, broker WebSocket stream capture, Makepad
  controller-pose provider setup, and PMB live processor bridge execution.
  `hostessctl.py` re-exports thin wrappers so existing scripts and tests can
  continue importing from the CLI root.
- `tools/hostessctl/pmb_evidence.py`: projected-motion-breath contract
  constants, replay/self-test evidence builders, PMB validators, and facade
  re-exports for existing callers.
- `tools/hostessctl/pmb_support.py`: shared projected-motion-breath stream IDs
  and contract authority constants plus PMB package snapshots, scorecard
  helpers, host-app mapping, and timestamp/segment helpers shared by builders,
  validators, and host-run writers.
- `tools/hostessctl/pmb_native_receipts.py`: native Rusty Quest renderer PMB
  receipt policy helpers. It parses compact native projection-target markers
  and validates canonical state/value stream consumption without turning
  `stream.breath.feedback_receipt` into a second native-app contract.
- `tools/hostessctl/pmb_host_run_evidence.py`: host-run evidence writers for
  PMB and live-capture validation routes.
- `tools/hostessctl/recording_evidence.py`: broker telemetry and Manifold
  value-recording evidence builders, validators, scorecards, and host-run
  evidence writers used by general recording routes.
- `tools/check_makepad_quest_gpu_evidence.py`: Quest Makepad GPU proof checker
  CLI and compatibility facade. Schema loading, cadence/stale checks,
  mesh-SDF checks, and compact summary assembly stay here.
- `tools/makepad_quest_gpu_evidence/`: focused implementation package for
  Quest Makepad GPU proof validation. `proof_lines.py` owns proof-marker
  parsing helpers, and `force_authority.py` owns the GPU force
  candidate/gate/freshness/residency/runtime-authority evidence family.
- `tools/studio_staging/platform_smoke.py`: compatibility facade for Studio
  platform-smoke planning, operator approval, execution, evidence attachment,
  and evidence review helpers. Phase implementations live in
  `platform_smoke_plan.py`, `platform_smoke_execution.py`,
  `platform_smoke_operator_start.py`, `platform_smoke_execution_report.py`, and
  `platform_smoke_evidence.py` so staging workflow growth stays reviewable.
- `tools/studio_staging/pmb_release.py`: compatibility facade for
  projected-motion-breath release staging receipts. Validation handoff,
  replay validation, and operator-release readiness behavior live in
  `pmb_validation_handoff.py`, `pmb_replay_validation.py`, and
  `operator_release.py`.
- `tools/studio_staging/staging_handoff.py`: compatibility facade for Hostess
  staging handoff acceptance, file planning, file copy, staged payload
  manifest, and downstream shell selection helpers. Phase implementations live
  in `staging_handoff_acceptance.py`, `staging_handoff_file_plan.py`,
  `staging_handoff_file_copy.py`, `staging_handoff_payload_manifest.py`, and
  `staging_handoff_downstream_shell.py`.
- `tools/studio_staging_request.py`: stable Studio staging request CLI/import
  facade. Domain builders remain re-exported here for existing callers.
- `tools/studio_staging/request_cli.py`: Studio staging request command
  orchestration. It wires intake, smoke, PMB, handoff, and downstream shell
  outputs without owning the schema helpers.
- `tools/studio_staging/request_cli_parser.py`: Studio staging request
  argument surface, kept separate from command orchestration so option churn
  does not expand the facade.
- `tools/studio_staging/request_cli_validation.py`: terminal validation-output
  pipeline for the staging request CLI. It rebuilds prerequisite receipts when
  needed, writes validation reports, and leaves schema authority in the
  focused helper modules.
- `tools/test_studio_staging_request.py`: compatibility facade for the Studio
  staging request test suite. Test-family implementations live in
  `tools/studio_staging/request_tests/` so intake/smoke, platform-smoke,
  PMB/release, handoff, and CLI coverage stays reviewable.
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
  `--duration-seconds`, then delegates provider planning and capture execution
  to `tools/hostessctl/manifold_recording.py`. The recorder remains
  general-purpose and records explicit missing-stream evidence instead of
  becoming Polar- or controller-specific.
- `tools/hostessctl/hostessctl.py emit-bridge-route-evidence`: converts a
  Hostess bridge-route input receipt into
  `rusty.manifold.bridge.route_evidence.v1` plus a Hostess validation report.
  It is a low-rate evidence adapter, not a transport runner.
- `tools/hostessctl/hostessctl.py run-bridge-command`: sends a generic
  Hostess bridge command request through the Manifold WebSocket command route
  and writes `rusty.manifold.bridge.route_evidence.v1` plus Hostess execution
  and validation sidecars. It is the shared backend path intended for WPF,
  Makepad, and future UI frontends.
- `tools/hostessctl/hostessctl.py run-bridge-command-live-android`: prepares a
  connected Quest broker/runtime pair with serial-scoped ADB, then runs the
  shared broker-stream command route. It is the preferred WPF safe-probe
  backend because lifecycle, forwarding, socket readiness, Manifold authority,
  runtime receipt, and applied evidence are captured in one sidecar.
- `tools/hostessctl/hostessctl.py run-bridge-command-android`: stages the
  same request shape into the Hostess Makepad app-private inbox on a connected
  Android/Quest target, launches the XR activity, pulls the runtime receipt,
  and writes bridge-route evidence. The raw app-private route proves `sent`,
  `transport_ok`, `runtime_accepted`, and `applied`; the
  `--broker-authority` route adds Manifold `authority_accepted` before runtime
  delivery. Use `--adb-forward-broker` when the broker authority is the
  connected Quest broker rather than a broker already listening on the host;
  readiness reports both the ADB forward mapping and the local forwarded socket
  separately.
- `tools/hostessctl/hostessctl.py companion-readiness`: emits a frontend-neutral
  readiness report plus validation sidecar. The command is safe for UI refresh:
  blocked checks are recorded in the report, and the process only returns a
  failing status when `--fail-on-blocking` is selected.
- `tools/hostessctl/hostessctl.py companion-catalog`: emits a frontend-neutral
  module/workspace/transport descriptor catalog plus validation sidecar. The WPF
  shell uses it to render Devices, Transports, and Evidence pages without
  hardcoding module authority in XAML or handlers.
- `tools/hostessctl/hostessctl.py companion-session run`: emits a
  frontend-neutral companion session report plus validation sidecar. The route
  runs readiness/catalog collection, attempts the connected-Quest
  broker-stream command probe, records app-private fallback recovery when
  needed, and exposes ordered phases for WPF, Makepad, CLI, and future UI
  frontends.
- `tools/hostessctl/hostessctl.py companion-session history`: emits a compact
  `rusty.hostess.companion.session_history.v1` index of saved session reports.
  The WPF History action consumes this route before loading selected report
  artifacts, preserving UI-equivalent CLI coverage for session browsing.
- `tools/hostessctl/hostessctl.py companion-report projection`: emits a
  frontend-neutral `rusty.hostess.companion.report_projection.v1` row artifact
  from explicit source reports. This is the CLI-equivalent path for read-only
  operator report views; source artifacts still own validity, latest-artifact
  selection, and protocol promotion. With
  `--include-protocol-matrix-inputs`, the route derives matrix-selected
  device-link and connectivity-probe artifacts itself; WPF feeds suite-run,
  protocol-matrix, and read-only QCL-082 product firewall verify reports into
  the route instead of parsing matrix sources or firewall evidence in UI code.
  The WPF protocol-matrix flow also passes QCL-020/QCL-030/QCL-040/QCL-041
  topology fixtures as explicit matrix inputs so TCP/WebSocket/direct Wi-Fi
  coverage is visible without promoting topology fixtures as data protocols.
  The resulting `transport_coverage.summary.details.term_gates`
  scopes WebSocket to Manifold command/session receipts, or to command receipts
  plus QCL-079 generic WebSocket when that row is present; TCP is scoped to
  QCL-010/QCL-011 echo plus QCL-082 binary media, and Wi-Fi Direct is scoped
  to QCL-040/QCL-041 topology. With broker-owned QCL-079 evidence present,
  generic WebSocket is cleared; `remaining_live_gates` keeps live
  direct-Wi-Fi topology and product TCP media over direct Wi-Fi from being
  implied by visibility alone. Product TCP media over direct Wi-Fi only
  clears when a QCL-082
  receiver report carries the explicit `protocol.media_product_topology_gate`
  proof from a paired topology report. Product TCP media listener readiness is
  separate again: `transport.product_tcp_media_listener_firewall` clears only
  when a QCL-082 receiver report carries
  `protocol.media_product_listener_firewall_gate` or the projection route
  consumes a standalone `--firewall-rule` artifact from a verified
  `connectivity-probe windows-firewall-rule --action verify --rule-profile
  qcl-082-rmanvid1-media` report for the Hostess/WPF executable using the scoped
  `Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079` rule. Topology report
  views can still pass explicit connectivity-probe reports through the same
  route instead of re-normalizing evidence in the UI. Non-elevated apply/remove
  attempts block before mutation and can emit an auditable elevated Hostess CLI
  handoff script with `--handoff-script-out`; that script still calls
  `connectivity-probe windows-firewall-rule` for apply and verify instead of
  embedding a separate firewall implementation.
- `tools/hostessctl/hostessctl.py companion-report transport-gates`: emits a
  read-only `rusty.hostess.companion.transport_gate_report.v1` from a
  companion-report projection. Use `--fail-on-pending` in automation when a run
  must stop until WPF-visible gates such as product TCP media over direct Wi-Fi
  or the product TCP media listener firewall are proven.
- `tools/hostessctl/hostessctl.py connectivity-probe run`: emits a
  `rusty.quest.connectivity_topology_probe.v1` report for the Quest
  connectivity lab. Fixture mode covers QCL-000 USB ADB command-feedback and
  QCL-010 same-Wi-Fi topology cases; QCL-000 fixtures remain candidate
  WebSocket visibility evidence until a live device-link report proves runtime
  subscriber and applied-command receipt gates. Live QCL-010 mode uses
  serial-scoped ADB only to observe Quest Wi-Fi state and then probes the
  actual data path with host/Quest LAN reachability checks.
- `tools/hostessctl/hostessctl.py connectivity-probe test-suite`: emits the
  planned downloadable install/environment/protocol test set as
  `rusty.quest.device_link.install_environment_test_suite.v1`. It groups host,
  toolchain, network adapter, firewall, device, protocol, and RTT/clock
  alignment checks, and links each QCL slot to the fixture/live commands and
  reusable stream capability descriptors that WPF, Makepad, CLI, and future
  frontends can render.
- `tools/hostessctl/hostessctl.py connectivity-probe run-suite`: executes
  selected QCL slots from the test-suite descriptor and emits
  `rusty.quest.device_link.install_environment_suite_run.v1` with host
  environment snapshots, grouped results, per-slot artifacts, and metrics.
- `tools/hostessctl/hostessctl.py snapshot-telemetry`: converts bounded
  replay/live evidence into `rusty.hostess.telemetry.snapshot.v1` checkpoints
  for Makepad and future Rusty GUI surfaces.
- `tools/telemetry_stream.py`: emits replay-derived
  `rusty.hostess.telemetry.stream_event.v1` JSONL batches for Makepad watcher
  validation. Real live adapters should append the same event shape as data
  arrives.

## Validation

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_catalog.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_report_projection.py tools\hostessctl\companion_report_transport_coverage.py tools\hostessctl\companion_transport_gate_actions.py tools\hostessctl\companion_transport_gates.py tools\hostessctl\companion_session.py tools\hostessctl\companion_session_defaults.py tools\hostessctl\connectivity_bluetooth.py tools\hostessctl\connectivity_data_protocols.py tools\hostessctl\connectivity_firewall.py tools\hostessctl\connectivity_lan.py tools\hostessctl\connectivity_media.py tools\hostessctl\connectivity_media_receiver.py tools\hostessctl\connectivity_probe.py tools\hostessctl\connectivity_probe_common.py tools\hostessctl\connectivity_probe_fixtures.py tools\hostessctl\connectivity_probe_live_reports.py tools\hostessctl\connectivity_probe_validation.py tools\hostessctl\connectivity_suite.py tools\hostessctl\connectivity_topology.py tools\hostessctl\connectivity_topology_lifecycle.py tools\hostessctl\connectivity_topology_live.py tools\hostessctl\connectivity_udp.py tools\hostessctl\connectivity_websocket.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\questionnaire_bridge.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\check_makepad_quest_gpu_evidence.py tools\makepad_quest_gpu_evidence\__init__.py tools\makepad_quest_gpu_evidence\proof_lines.py tools\makepad_quest_gpu_evidence\force_authority.py tools\studio_staging_request.py tools\studio_staging\request_cli.py tools\studio_staging\request_cli_parser.py tools\studio_staging\request_cli_validation.py tools\hostessctl\native_breathing_room_setup.py tools\studio_staging\pmb_release.py tools\studio_staging\pmb_validation_handoff.py tools\studio_staging\pmb_replay_validation.py tools\studio_staging\operator_release.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence tools.test_polar_runtime_bridge tools.test_telemetry_snapshot tools.test_hostessctl_bridge_command_android tools.test_hostessctl_bridge_command_live_android tools.test_hostessctl_bridge_command tools.test_hostessctl_bridge_route_evidence tools.test_hostessctl_companion_catalog tools.test_hostessctl_companion_readiness tools.test_hostessctl_companion_report_projection tools.test_hostessctl_companion_session tools.test_hostessctl_connectivity_probe
python tools\hostessctl\hostessctl.py run-replay --target desktop --module rmssd_gain --module coherence --packages-root <packages-root> --out <capture.json>
python tools\hostessctl\hostessctl.py run-pmb-replay --target desktop --packages-root <packages-root> --out <pmb-replay-evidence.json>
python tools\hostessctl\hostessctl.py run-pmb-replay --target quest --adb <adb> --serial <serial> --packages-root <packages-root> --out <pmb-quest-replay-evidence.json>
python tools\hostessctl\hostessctl.py run-pmb-controller-preflight --target quest --adb <adb> --serial <serial> --packages-root <packages-root> --out <pmb-quest-controller-preflight-evidence.json>
python tools\hostessctl\hostessctl.py record-values --target quest --value stream.polar_h10.acc --value stream.motion.object_pose --duration-seconds 120 --packages-root <packages-root> --out <recording.json> --adb <adb> --serial <quest-serial> --device-address <polar-address> --makepad-pose-controller right --makepad-pose-kind grip --makepad-pose-sample-hz 90
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <capture.json> --out <snapshot.json>
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde hostess_contracts
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde main_tests
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
```

For Makepad running-telemetry validation from a replay checkpoint:

```powershell
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <capture.json> --out <snapshot.json>
python tools\telemetry_stream.py --snapshot <snapshot.json> --out <telemetry.jsonl>
cargo run --manifest-path apps\hostess-t-makepad\Cargo.toml -- --snapshot <snapshot.json> --stream-jsonl <telemetry.jsonl>
```

## Hostess Contract Schemas

Hostess-local camera, home, and kiosk DTO constructors default to current
`rusty.hostess.*` schema IDs. Frozen `rusty.xr.*` IDs are accepted only for
serialized compatibility and are centralized in
`apps/hostess-t-makepad/src/hostess_contracts/legacy_rusty_xr_schemas.rs`.
Cross-backend source-sampling compatibility fixtures live under
`tools/quest-camera-profile/fixtures/` and are covered by the serde-gated
Hostess contract tests.

## Makepad Runtime Settings

Hostess Makepad runtime settings use Morphospace Makepad names only. Use
`RUSTY_MAKEPAD_*` environment variables, `debug.rusty.*` Android properties,
canonical snake_case runtime keys, or current `makepad.*` launch aliases.
Legacy `RUSTY_XR_*`, `debug.rustyxr.*`, and `rustyxr.*` spellings are not
accepted by the active Hostess Makepad settings stack.
Retired projection runtime spellings that may need cleanup from shell profiles
or Android properties are documented in
`apps/hostess-t-makepad/src/makepad_runtime_config/retired_aliases.rs`; that
ledger is intentionally not part of active runtime resolution.
Projection runtime key definitions live in
`apps/hostess-t-makepad/src/makepad_runtime_config/projection_keys.rs`.
Runtime-key alias evidence types, including deprecated/legacy status metadata
for the retired ledger, live in
`apps/hostess-t-makepad/src/makepad_runtime_config/alias_model.rs`.
Projection runtime manifest marker formatting and alias-evidence tokenization
live in `apps/hostess-t-makepad/src/makepad_runtime_config/manifest.rs` so the
core runtime-config file stays focused on typed parsing, layered resolution,
and the public facade.

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
compact joint-frame recordings; `makepad_diagnostics.rs` owns marker cadence,
token formatting, raw camera event markers, target-footprint augmentation, and
camera YUV texture handle structs; `broker_h264_runtime.rs` owns broker-H264
and remote-camera runtime key parsing plus `ExternalH264VideoSource`
construction; `source_metadata.rs` is the Makepad source/import marker facade
for runtime target-footprint, source-sampling, and hardware-buffer import
marker helpers, while `source_metadata/broker_projection.rs` owns broker-H264
stream-header projection metadata parsing, content-geometry marker records, and
broker projection plan decisions; `projection_geometry.rs` is the
projection-plan/OpenXR geometry facade, while `projection_geometry/markers.rs`
owns Makepad stereo projection marker/report formatting and marker-shape tests;
`camera_projection_flow.rs` owns paired camera import, frame-adoption, cadence,
broker-H264 import, native video widget, YUV probe, projection-panel binding,
and projection-complete marker flow;
`hostess_camera_model.rs` is the public facade for app-neutral camera helpers;
its `hostess_camera_model/` child modules own source selection, projection
footprint/layout, camera basis/projection math, homography smoothing, and
timestamp matching;
`hostess_contracts/camera.rs` is the camera-contract facade for shared
primitives, diagnostics, frame metadata, and calibration/source diagnostics;
`hostess_contracts/camera/source_sampling.rs` owns source-sampling DTOs,
texture transform helpers, and source-sampling schema acceptance;
`hostess_contracts/camera/temporal_projection.rs` owns frame timing,
projection state, visual projection state, temporal policy, and metrics;
`hostess_contracts/camera/texture_lane.rs` owns camera texture-lane DTOs,
validation, and current-or-legacy schema acceptance;
`app_mesh_replay_runtime.rs` owns selected effective-settings adoption, mesh
replay stepping, Matter/particle/stimulus runtime resets, and panel/world
cadence binding;
`makepad_effective_settings.rs` remains the effective-settings
receipt/runtime-selection facade, while `makepad_effective_settings/revision.rs`
owns revision sidecar identity and scoped invalidation keys and
`makepad_effective_settings/tests.rs` owns the effective-settings regression
fixtures;
`app_stimulus_runtime.rs` owns stimulus field panel binding, runtime XR
projection rows, bounded volume preview probe polling, and image-preview
texture adoption;
`app_projection_target.rs` owns the app-shell projection-target control loop,
including controller-driven target offset/scale updates and Manifold breath
feedback target-scale adoption;
`app_horizontal_alignment.rs` owns app-shell horizontal-alignment tuning:
runtime-resolution fallback, legacy hotload values, change detection, hotload
markers, and panel binding;
`frame_orientation.rs` owns direct-camera and broker-H264
source-raster orientation decisions plus shared broker pair pose-source
combination; `makepad_stereo_camera_panel.rs` owns the Rust widget/draw
state, panel live-design registration, draw shader defaults, shader uniform
application, camera texture binding, and the panel-side horizontal alignment
uniform application; `matter_world_particle_billboard.rs`
and `matter_world_adf_debug.rs` own the Hostess-local world renderer widgets
and their Makepad widget defaults; `makepad_app_live_design.rs` owns the
Hostess app layout registration. Keep `main.rs` as app-shell state,
top-level event ordering, and module registration. `main_tests.rs` owns
app-root regression tests that need private access to the shell wiring.

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
The checker command remains the stable entrypoint; the
`tools/makepad_quest_gpu_evidence/` package owns shared proof-line parsing and
the force-authority evidence family so new evidence families can be split
without growing the CLI facade.

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
python tools\hostessctl\hostessctl.py record-values --target quest --value stream.polar_h10.acc --value stream.motion.object_pose --duration-seconds 120 --packages-root <packages-root> --out <recording.json> --adb <adb> --serial <quest-serial> --device-address <polar-address> --makepad-pose-controller right --makepad-pose-kind grip --makepad-pose-sample-hz 90
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
