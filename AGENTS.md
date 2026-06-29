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
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_session.py tools\hostessctl\companion_session_defaults.py tools\hostessctl\connectivity_bluetooth.py tools\hostessctl\connectivity_data_protocols.py tools\hostessctl\connectivity_probe.py tools\hostessctl\connectivity_probe_common.py tools\hostessctl\connectivity_suite.py tools\hostessctl\connectivity_udp.py tools\hostessctl\device_link_report.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\check_makepad_quest_gpu_evidence.py tools\makepad_quest_gpu_evidence\__init__.py tools\makepad_quest_gpu_evidence\proof_lines.py tools\makepad_quest_gpu_evidence\force_authority.py tools\studio_staging_request.py tools\studio_staging\request_cli.py tools\studio_staging\request_cli_parser.py tools\studio_staging\request_cli_validation.py tools\studio_staging\pmb_release.py tools\studio_staging\pmb_validation_handoff.py tools\studio_staging\pmb_replay_validation.py tools\studio_staging\operator_release.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
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
  requester/inspector projection over companion catalog, Quest device-link, and
  protocol evidence matrix reports. It may produce compact rows and marker
  lines for operator panels; it must not own validation, setup, transport,
  protocol promotion, or command authority.

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
