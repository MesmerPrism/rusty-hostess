# Rusty Hostess Agent Notes

This repo contains Rusty Hostess T, the first-party install and test shell for
Manifold packages. It is allowed to contain platform APIs and installable test
apps. Keep `rusty-manifold` contract-first and keep `rusty-manifold-packages`
manifest/fixture-first.

Rusty Morphospace is the top-level project/platform umbrella. Hostess remains
an install/test shell product lane inside that umbrella; it can collect
evidence for Matter, Lattice, Manifold, Optics, Studio, and Quest flows without
becoming their schema or runtime authority.

Project-owned source in this repo is licensed `AGPL-3.0-or-later`. Keep
third-party dependencies, Makepad toolkit code, generated APKs, installer
bundles, signing material, captured evidence, device logs, platform SDKs,
binary releases, and external tools under their own provenance and notice
requirements; see `docs/LICENSING.md`.

## Scope

- Minimal host apps and scripts that consume Manifold package manifests.
- Live package validation slots for desktop, mobile, and headset profiles.
- Evidence JSON, validators, and build scripts for clean host tests.
- Lattice evidence collection for tracked view sets, poses, spatial input
  roles, frame-state binding, calibration, validity, confidence, and runtime
  capabilities when a host run needs situated relation proof.
- Makepad dependencies only inside Hostess Makepad shell crates.

## Non-Scope

- Legacy app integration.
- Product UI.
- Dynamic package loading.
- Long-lived background services.
- Local-only planning paths, device serials, personal package ids, or old project
  names in committed files.
- Lattice contract authority. Hostess can collect evidence and run adapters,
  but generic relation schemas belong in Rusty Lattice and command/session
  authority remains Manifold.
- Makepad dependencies in Hostess core, CLI, validators, manifests, or
  descriptor logic.

## Sustainable Design Guardrails

- Treat monolithic file pressure as an ownership problem, not a line-count
  problem. Split only by durable authority, schema, route, validation, adapter,
  or test-family boundaries; preserve facades, schema IDs, serde fields,
  fixture outputs, CLI behavior, validation outcomes, and dependency boundaries.
- After a split, update the nearest distributed file map: this `AGENTS.md`,
  `README.md`, `docs/ARCHITECTURE.md`, fixture docs, validation docs, or the
  planning `agent-state\iteration-events.jsonl`.
- Keep `AGENTS.md`, README, and skill files as concise routing indexes. Move
  lane-specific recipes, device/build detail, compatibility ledgers, and long
  validation flows into named docs or runbooks.
- Keep legacy Rusty-XR names as explicit compatibility surfaces only. New
  schemas, routes, and types use the owning lane (`rusty.manifold.*`,
  `rusty.lattice.*`, `rusty.matter.*`, `rusty.optics.*`, `rusty.quest.*`, or
  repo-local names); do not introduce `rusty.morphospace.*` schemas or
  `Morphospace*` core types by default.
- Every WPF, Makepad, or future operator UI action must have a CLI-equivalent
  or local API route that automation can exercise with the same inputs,
  authority checks, and evidence artifacts. UI handlers collect parameters,
  invoke the route, and project structured evidence; they do not own hidden
  business logic or acceptance rules.
- Every operator report view must render a CLI/API report, descriptor, sidecar,
  receipt, or fixture output that automated tests can exercise before the UI
  feature is accepted for human operators.

## Validation

Run the narrow checks before committing:

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_operator_action_rows.py tools\hostessctl\companion_operator_actions.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_report_projection.py tools\hostessctl\companion_report_transport_coverage.py tools\hostessctl\companion_transport_gate_actions.py tools\hostessctl\companion_transport_gates.py tools\hostessctl\companion_session.py tools\hostessctl\companion_session_defaults.py tools\hostessctl\connectivity_bluetooth.py tools\hostessctl\connectivity_data_protocols.py tools\hostessctl\connectivity_firewall.py tools\hostessctl\connectivity_lan.py tools\hostessctl\connectivity_media.py tools\hostessctl\connectivity_media_product_plan.py tools\hostessctl\connectivity_media_receiver.py tools\hostessctl\connectivity_probe.py tools\hostessctl\connectivity_probe_common.py tools\hostessctl\connectivity_probe_fixtures.py tools\hostessctl\connectivity_probe_live_reports.py tools\hostessctl\connectivity_probe_validation.py tools\hostessctl\connectivity_suite.py tools\hostessctl\connectivity_topology.py tools\hostessctl\connectivity_topology_lifecycle.py tools\hostessctl\connectivity_topology_live.py tools\hostessctl\connectivity_udp.py tools\hostessctl\device_link_report.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\check_makepad_quest_gpu_evidence.py tools\makepad_quest_gpu_evidence\__init__.py tools\makepad_quest_gpu_evidence\proof_lines.py tools\makepad_quest_gpu_evidence\force_authority.py tools\studio_staging_request.py tools\studio_staging\request_cli.py tools\studio_staging\request_cli_parser.py tools\studio_staging\request_cli_validation.py tools\studio_staging\pmb_release.py tools\studio_staging\pmb_validation_handoff.py tools\studio_staging\pmb_replay_validation.py tools\studio_staging\operator_release.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence tools.test_polar_runtime_bridge tools.test_telemetry_snapshot tools.test_hostessctl_bridge_command_android tools.test_hostessctl_bridge_command_live_android tools.test_hostessctl_bridge_command tools.test_hostessctl_bridge_route_evidence tools.test_hostessctl_companion_readiness tools.test_hostessctl_companion_session tools.test_makepad_morphospace_boundaries
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde hostess_contracts
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde main_tests
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
dotnet run --project tests\HostessCompanion.Wpf.Tests\HostessCompanion.Wpf.Tests.csproj
```

For live captures, write raw run artifacts outside the repo and commit only
generic code or sanitized sample fixtures.

## File Organization

- Keep `apps\hostess-t-makepad\src\hostess_contracts\camera.rs` as the
  camera-contract facade plus shared primitives, diagnostics, frame metadata,
  and calibration/source diagnostics. The `hostess_contracts\camera\` child
  modules own focused contract families; `source_sampling.rs` owns
  source-sampling DTOs, texture transform helpers, and source-sampling schema
  acceptance, `temporal_projection.rs` owns frame timing, projection state,
  visual projection state, temporal policy, and metrics, while
  `texture_lane.rs` owns camera texture-lane DTOs, validation, and
  current-or-legacy schema acceptance.
- Keep `apps\hostess-t-makepad\src\source_metadata.rs` as the Makepad
  source/import marker facade for runtime target-footprint, source-sampling,
  and hardware-buffer import marker helpers. The `source_metadata\` child
  modules own focused metadata families; `broker_projection.rs` owns broker-H264
  stream-header projection metadata parsing, content-geometry marker records,
  and broker projection plan decisions.
- Keep `apps\hostess-t-makepad\src\projection_geometry.rs` as the
  projection-plan and OpenXR geometry facade. The `projection_geometry\` child
  modules own focused projection support families; `markers.rs` owns Makepad
  stereo projection marker/report field formatting and marker-shape tests.
- Keep `apps\hostess-t-makepad\src\makepad_effective_settings.rs` as the
  effective-settings receipt/runtime-selection facade. The
  `makepad_effective_settings\` child modules own focused settings families;
  `revision.rs` owns revision sidecar identity and scoped invalidation keys,
  while `tests.rs` owns the effective-settings regression fixtures.
- Keep `apps\hostess-t-makepad\src\companion_frontend.rs` as the Makepad-side
  requester/inspector projection over companion catalog, Quest device-link,
  protocol evidence matrix, and companion-report projection reports. It may
  produce compact rows and marker lines for operator panels; it must not own
  validation, setup, transport, protocol promotion, artifact selection, or
  command authority.
- Keep `tools\hostessctl\companion_report_transport_coverage.py` as the
  companion-report transport coverage row owner. It may summarize TCP,
  WebSocket, Wi-Fi Direct, other Wi-Fi topology, family, and QCL probe ID
  presence plus term-gate scope from already-projected source rows, including
  the product TCP media listener firewall remaining gate; it must not select
  artifacts, run probes, validate protocols, or promote topology/protocol
  evidence.
- Keep `tools\hostessctl\companion_transport_gates.py` as the read-only
  transport gate report owner. It may summarize `term_gates` and
  `remaining_live_gates` from an existing companion-report projection and
  optionally fail automation on pending gates. It may attach structured
  operator `next_actions` that name CLI-equivalent PowerShell commands,
  acceptance artifacts, elevation flags, mutation flags, and Agent Board
  `quest:<serial>` lease reserve/release metadata; it must not run probes,
  select artifacts, change
  firewall/device state, parse media, or promote evidence. Its validation
  sidecar must reject drift between top-level `operator_next_actions` summaries
  and each pending gate's source-owned `next_actions`, and must reject
  malformed next-action metadata before WPF renders operator guidance.
- Keep `tools\hostessctl\companion_transport_gate_actions.py` as the static
  transport gate operator-action catalog. It may name existing Hostess CLI
  routes, PowerShell command strings, acceptance artifacts, and lease/elevation
  metadata for pending gates; it must keep authority owner, elevation, lease,
  mutation, dependency, gate-clearing, and acceptance-artifact fields
  structured so report validation can enforce them. It must not execute those
  commands or decide that a gate is cleared.
- Keep `tools\test_hostessctl_companion_transport_gate_actions.py` as the
  source-owned test family for that static transport-gate next-action catalog.
  It checks QCL-079 generic WebSocket, direct-Wi-Fi, and QCL-082 product-media
  PowerShell command shape, output artifacts, elevation boundaries, Quest lease
  metadata, serial-scoped ADB posture, dependencies, candidate-vs-promoting
  boundaries, and non-mutating verify routes before WPF projection tests render
  the rows.
- Keep `tests\HostessCompanion.Wpf.Tests\TransportGateReportFixtures.cs` as the
  WPF transport-gate report fixture owner. It may construct the large
  pending-gate report shape used by `Program.cs` row-projection assertions, but
  it must not replace Hostess source-owned validation in
  `companion_transport_gates.py` or the CLI next-action catalog tests.
- Keep `apps\hostess-companion-wpf\Models\CompanionTransportGateModels.cs`,
  `Services\HostessctlConnectivityService.cs`, and
  `ViewModels\ConnectivityRows.cs` projection-only for transport-gate sidecar
  content. They may load and render the Hostess-written
  `rusty.hostess.companion.transport_gate_report.validation.v1` status, counts,
  warnings, and source path, but they must not recalculate transport-gate
  validation or change promotion policy.
- Keep `tools\hostessctl\companion_operator_action_rows.py` as the static WPF
  operator-action row owner, and keep
  `tools\hostessctl\companion_operator_actions.py` as the read-only
  report/validation facade. The facade may emit
  `rusty.hostess.companion.operator_action_catalog.v1` so automation can
  inspect the same visible action ids, command properties, PowerShell-shaped
  Hostess CLI routes, evidence artifacts, authority owners, test coverage, and
  structured elevation/Quest lease/host-mutation/device-mutation metadata that
  WPF advertises; it must not execute commands, select latest artifacts,
  reserve leases, change firewall/device state, run probes, or promote
  protocols. Ordinary headset-bound rows stay serial-scoped and must not
  require `adb-server:lifecycle` unless the route explicitly owns disruptive
  ADB daemon recovery.
- Keep `tools\hostessctl\connectivity_media_receiver.py` as the QCL-082
  Hostess receiver-counter owner. It may arm bounded TCP `RMANVID1` captures,
  write raw capture/sidecar/result artifacts, parse packet counters, and run
  the orchestrated product-media live session that starts the receiver before
  requesting the Quest/Manifold media source command. It may join product TCP
  listener firewall verification reports, but it must not own Windows firewall
  rule lifecycle, Android camera/display source setup, or QCL promotion
  policy.
- Keep `tools\hostessctl\connectivity_media_product_plan.py` as the read-only
  QCL-082 product-media direct-Wi-Fi plan artifact owner. It may bind the
  existing Hostess CLI routes, dependencies, lease policy, and acceptance
  artifacts into one WPF/CLI-equivalent plan, but it must not run headset
  commands, mutate firewall/device state, parse media, or clear promotion
  gates.
- Keep `tools\hostessctl\connectivity_firewall.py` as the Windows Firewall
  listener lifecycle owner. It owns rule planning, product-rule verification,
  network/firewall profile summaries, and elevation preflight for mutating
  apply/remove actions; WPF renders its reports and uses explicit elevated
  action requests instead of hidden firewall logic.
- Keep `tools\hostessctl\connectivity_probe_fixtures.py` as the QCL fixture
  construction owner. `connectivity_probe.py` may preserve facade imports and
  route fixture mode to it, but fixture bodies, damaged fixture variants, and
  media/status fixture ingestion belong in the fixture helper.
- Keep `tools\hostessctl\connectivity_probe_validation.py` as the shared
  QCL report validator. `connectivity_probe.py` may dispatch routes and
  preserve facade imports, but validation requirements and schema/report
  checks belong in the validator helper.
- Keep `tools\hostessctl\connectivity_probe_live_reports.py` as the pure live
  report-shaping owner for QCL status derivation, listener report rows,
  topology summaries, and measurement projection. It must not own live ADB,
  socket, broker, or protocol execution.
- Keep `tools\hostessctl\connectivity_topology_live.py` as the read-only live
  topology preflight owner for experimental QCL-040/QCL-041 Wi-Fi Direct
  reports. It may collect serial-scoped ADB feature state and Windows
  Wi-Fi Direct adapter state, but it must not promote direct-Wi-Fi topology
  without peer discovery, group formation, socket exchange, and cleanup
  evidence.
- Keep `tools\hostessctl\connectivity_topology_lifecycle.py` as the
  QCL-040/QCL-041 Wi-Fi Direct lifecycle evidence ingestion owner. It may
  validate a structured live lifecycle artifact and emit a promoted topology
  report only when peer discovery, group formation, bounded TCP socket
  exchange, and cleanup all pass; it must not run headset lifecycle mechanics,
  mutate Wi-Fi Direct state, or claim QCL-082 product media readiness.
- Keep `tools\hostessctl\connectivity_topology_lifecycle_plan.py` as the
  read-only QCL-040/QCL-041 Wi-Fi Direct lifecycle plan owner. It may bind
  Agent Board lease metadata, preflight, source-template, external live-source,
  and normalization CLI routes into a WPF/CLI-equivalent artifact, but it must
  not run headset commands, mutate Wi-Fi Direct state, or clear topology gates.
- Keep `tools\hostessctl\connectivity_bluetooth.py` as the QCL-050/QCL-051
  Bluetooth readiness, payload, reconnect, transport, and live report assembly
  owner. `connectivity_probe.py` may preserve facade imports and route
  dispatch, but Bluetooth evidence logic belongs in the helper.
- Keep `tools\hostessctl\connectivity_data_protocols.py` as the QCL-081,
  QCL-083, and QCL-084 data-protocol mechanics owner. It may own host
  loopbacks, Manifold broker wrappers, Quest-runtime OSC/ZeroMQ probe helpers,
  live report assembly, protocol evidence rows, and source-specific report
  promotion gates; it must not own protocol-matrix promotion or WPF projection.
- Keep `tools\hostessctl\connectivity_websocket.py` as the QCL-079 generic
  WebSocket mechanics owner. It may own bounded HTTP upgrade/echo loopbacks,
  Manifold stream route/evidence ingestion, fixture report bodies, WebSocket
  message measurements, and the command-authority/high-rate-media guard
  checks; it must not own Manifold command acceptance, protocol-matrix
  promotion, or WPF projection.
- Keep `tools\hostessctl\connectivity_lan.py` as the live LAN/device transport
  helper owner for Quest ADB identity, host IPv4 selection, same-subnet checks,
  ICMP checks, Windows Mobile Hotspot state collection, and TCP echo transport
  probes, including QCL-010/QCL-011 live report assembly. `connectivity_probe.py`
  may preserve facade imports and route dispatch, but LAN probing mechanics
  belong in the helper.
- Keep `tools\hostessctl\connectivity_udp.py` as the QCL-080 UDP freshness
  owner. It owns the live QCL-080 report assembly, UDP sender/listener
  mechanics, Makepad runtime UDP sender setup, WPF listener-helper ingestion,
  and app-owned UDP runtime-marker parsing. `connectivity_probe.py` may
  preserve facade imports and dispatch, but QCL-080 evidence logic belongs in
  the UDP helper.
- Keep `tools\test_hostessctl_connectivity_probe.py` as the stable unittest
  facade for QCL connectivity-probe coverage. The
  `tools\connectivity_probe_tests\` package owns split test families for
  fixture reports, QCL-082 media receiver gates, QCL-079/WebSocket and data
  protocols, live LAN/UDP/Bluetooth paths, parser coverage, and firewall rule
  profiles. Add new tests to the family module that owns the behavior instead
  of growing the facade.

## Quest Makepad APK Route

Open `docs\agent-instructions\quest-makepad-runbook.md` before Quest Makepad
APK builds, headset evidence collection, settings staging, GPU proof, ADF,
particle, or live/recorded hand validation work.

Keep these first-hop rules visible here:

- Build Hostess T Makepad Quest validation from `apps\hostess-t-makepad` with
  the Morphospace Makepad Quest variant and the active `makepad-morphospace`
  `cargo-makepad`.
- Do not add an app-local `resources\android\AndroidManifest.xml.template` just
  to remove camera permissions; use the packager camera-permission opt-out so
  `.MakepadAppXr` and OpenXR metadata stay intact.
- Stage effective settings and sibling data-plane artifacts with
  `tools\Stage-HostessMakepadSettings.ps1`; do not use
  `/sdcard/Android/data/...` as the app/ADB handoff path for these payloads.
- Treat settings writes as revision/scoped hashes transactions; the runbook
  keeps the full layered invalidation details.
- Hostess helper scripts must map Makepad, Quest, and PMB knobs through their
  owning master layer: effective-settings receipts for Makepad behavior, Quest
  runtime profiles for property transport, and Manifold/PMB commands for breath
  source selection and calibration. Do not treat direct property readback or
  launch arguments as accepted behavior without the app-side marker/receipt.
- Use `tools\check_makepad_quest_gpu_evidence.py` for Quest Makepad GPU proof
  evidence review when GPU/page-fault or compute-readiness claims are touched.
- Keep high-rate hands, meshes, SDF/ADF fields, particles, and GPU buffers out
  of settings/control JSON.
- Hostess remains the install/test/evidence shell. Matter, Optics,
  Quest-Makepad, Makepad, Lattice, and Manifold keep their runtime/schema
  authority according to their lane ownership.
