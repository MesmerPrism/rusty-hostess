# Evidence Bundle

Hostess T run evidence uses JSON files with schema
`rusty.manifold.live_capture_evidence.v1` for the current slice.

Projected-motion breath desktop replay uses
`rusty.hostess.projected_motion_breath.desktop_replay_execution_evidence.v1`.
`hostessctl run-pmb-replay --target desktop` emits it after running
`projected-motion-breath-core validate-goldens` against the package fixtures.
The evidence records the core validation report, stdout/stderr artifacts,
fixture counts, runtime execution flags, and explicit false flags for Android,
Quest, APK, OpenXR, ADB, and live sensors. A passing run also writes a
companion `rusty.manifold.host_run.run_evidence.v1` artifact.

Projected-motion breath Android and Quest replay uses
`rusty.hostess.projected_motion_breath.android_replay_execution_evidence.v1`.
`hostessctl run-pmb-replay --target phone|quest` launches the Hostess Android
action `io.github.mesmerprism.rustyhostess.t.RUN_PMB_REPLAY`, executes
`projected-motion-breath-core` through the Hostess PMB JNI library over packaged
synthetic PMB assets, pulls `latest.json` and
`latest.core-validation-report.json` from app-private evidence storage, writes a
Hostess validation report, and writes a companion
`rusty.manifold.host_run.run_evidence.v1` artifact on pass. The evidence must
record Android execution, Quest execution when `--target quest` is selected,
processor-core execution, synthetic replay, and explicit false flags for
OpenXR, live sensors, and controller input.

Projected-motion breath Android and Quest controller preflight uses
`rusty.hostess.projected_motion_breath.android_controller_preflight_evidence.v1`.
`hostessctl run-pmb-controller-preflight --target phone|quest` launches the
Hostess Android action
`io.github.mesmerprism.rustyhostess.t.RUN_PMB_CONTROLLER_PREFLIGHT`, executes
`projected-motion-breath-core controller-preflight` through the Hostess PMB JNI
library over a packaged headset-controller-shaped `stream.motion.object_pose`
fixture, pulls `latest.json` and `latest.controller-preflight-report.json` from
app-private evidence storage, writes a Hostess validation report, and writes a
companion `rusty.manifold.host_run.run_evidence.v1` artifact on pass. The
evidence must record `pmb_controller_path_preflight_passed=true`,
`quest_execution_performed=true` for Quest targets, `processor_core_executed=true`,
`controller_provider_route_ready=true`, `physical_controller_input_used=false`,
`controller_input_used=false`, `human_controller_trial_performed=false`, and
`manual_controller_trial_required=true`.

Projected-motion breath Quest simulated live routing uses
`rusty.hostess.projected_motion_breath.android_simulated_live_execution_evidence.v1`.
`hostessctl run-pmb-quest-simulated-live --target quest` launches the Quest
broker, starts the clean Makepad XR app with breath feedback receipt handling,
then launches the Hostess Android action
`io.github.mesmerprism.rustyhostess.t.RUN_PMB_SIMULATED_LIVE`. Hostess copies
the PMB package assets into app-private storage, executes the PMB live-route
self-test through the Hostess PMB JNI library on Quest, publishes selected
breath volume and breath feedback samples to the Quest broker, and requires
Makepad feedback receipts before the host accepts the run. The evidence must
record `pmd_computed_on_quest=true`, `pmd_computed_on_pc=false`,
`processor_authority=quest_hostess_android_app`,
`simulated_polar_provider_used=true`,
`simulated_controller_provider_used=true`, `physical_polar_ble_used=false`,
`physical_controller_input_used=false`, broker publish counts, and Makepad
feedback receipt counts. This autonomous route is not a physical Polar BLE or
human controller trial; it proves the Quest-owned processor, broker, and Makepad
feedback path with packaged simulated providers.

Projected-motion breath Quest physical live routing uses
`rusty.hostess.projected_motion_breath.android_physical_live_execution_evidence.v1`.
`hostessctl run-pmb-quest-physical-live --target quest` launches the Quest
broker, configures the selected app receipt consumer, then starts the Hostess
foreground service action
`io.github.mesmerprism.rustyhostess.t.RUN_PMB_PHYSICAL_LIVE_BACKGROUND`.
The background-service route is the default so Hostess can run the physical PMB
processor without foregrounding the Hostess activity or stealing focus from the
Makepad XR app; `--foreground-hostess` remains available when an operator wants
the Hostess telemetry/debug UI and starts the activity action
`io.github.mesmerprism.rustyhostess.t.RUN_PMB_PHYSICAL_LIVE`.
The Hostess Android app connects to the Quest broker from the Quest, starts
Polar PMD ACC through broker command `polar_pmd.start`, records `bio:polar_acc`
and usable active/tracked/connected `stream.motion.object_pose` broker events
into app-private JSONL, executes `projected-motion-breath-core
live-route-from-events` through the Hostess PMB JNI library on Quest, and
publishes breath volume, state, state-value, and feedback samples to the Quest
broker. The default `--app-receipt-policy makepad-feedback-receipt` still
requires Makepad `stream.breath.feedback_receipt` acknowledgements. The
`--app-receipt-policy native-renderer-projection-target` route skips Makepad
setup, captures filtered native renderer logcat, and requires
`RUSTY_QUEST_NATIVE_RENDERER channel=projection-target status=effective`
markers showing `projectionTargetRuntimeAuthority=native-renderer`,
`projectionTargetScaleDriver=pmb`, `projectionTargetPmbAvailable=true`, and
matching `breathReceivedSamples` / `breathLastSequenceId` for the published
`stream.breath.state` and `stream.breath.state.value` samples. The evidence
must record `pmd_computed_on_quest=true`,
`pmd_computed_on_pc=false`,
`processor_authority=quest_hostess_android_app`,
the selected physical input requirements, for example
`physical_polar_ble_used=true` plus `physical_controller_input_used=true` for
Polar/controller runs or `polar_required=false` plus
`physical_controller_input_used=true` for controller-only native Breathing Room,
`simulated_polar_provider_used=false`, `simulated_controller_provider_used=false`,
`synthetic_live_route=false`, `plan_only_fixture=false`, physical input counts,
broker publish counts, and the selected app receipt policy evidence. This
route is the real physical PMB gate; the older host-side
`record-values --pmb-live-processor` bridge is not acceptable for this gate
because it computes PMB on the PC.

`hostessctl observe-broker-telemetry --target quest` starts the Hostess
foreground telemetry UI as a broker-stream observer, optionally requests the
broker Polar PMD provider, subscribes to `bio:polar_acc`, renders the existing
live telemetry plot, and writes
`rusty.hostess.broker_telemetry_observer.evidence.v1`. This route is the
foreground telemetry visualization proof while preserving broker BLE authority:
the evidence must record `hostess_role=foreground_telemetry_ui_observer`,
`broker_transport_used=true`, `broker_connected=true`, `direct_ble_used=false`,
`telemetry_ui_visualized=true`, and nonzero `bio:polar_acc` frame/sample counts.

General Manifold value recording uses
`rusty.hostess.manifold_value_recording.evidence.v1`.
`hostessctl record-values --target desktop|phone|quest --value <stream-id>`
accepts repeated values and a duration, normalizes known aliases, builds
provider plans, and writes a companion validation report plus
`rusty.manifold.host_run.run_evidence.v1`. When exactly one requested value has
an existing live route, the recorder delegates to that route and records the
source capture artifact. On Quest, provider sets that share the broker
WebSocket transport can be recorded together. The broker route writes
`rusty.hostess.broker_stream_recording.evidence.v1`, captures matching broker
`stream_event` JSONL, and fails explicitly if any selected stream is missing.
The evidence must record `general_recorder=true`, `polar_specific=false`,
`controller_specific=false`, and must only claim physical controller input when
`stream.motion.object_pose` events were actually captured.

Manifold bridge-route evidence uses
`rusty.manifold.bridge.route_evidence.v1`.
`hostessctl emit-bridge-route-evidence --input <input.json> --out <evidence.json>`
normalizes a Hostess-owned input receipt with stage observations into the
Manifold bridge-route shape and writes a neighboring
`rusty.hostess.bridge_route_evidence.validation.v1` report. Applied command
routes must prove `sent`, `transport_ok`, `authority_accepted`,
`runtime_accepted`, and `applied`; transport-only device routes such as ADB
must prove only the route-required transport stages. This is an evidence
adapter for WPF, Makepad, and future UI shells. It does not run the transport
or make Hostess the command authority.

Bridge command execution uses
`rusty.hostess.bridge_command.execution_evidence.v1` as its Hostess sidecar and
`rusty.manifold.bridge.route_evidence.v1` as the frontend-neutral result.
`hostessctl run-bridge-command --input <request.json> --out <evidence.json>`
consumes `rusty.hostess.bridge_command.request.v1`, sends a Manifold command
envelope through the broker WebSocket route, subscribes to the runtime receipt
stream, waits for `transport_ok`, `authority_accepted`, `runtime_accepted`,
and `applied` evidence, then writes a validation report. The default runtime
receipt stream is `stream.hostess.makepad.bridge_command.receipt`; the Makepad
subscriber receives command requests on `stream.hostess.makepad.bridge_command`
and publishes `rusty.hostess.makepad.bridge_command_runtime_receipt.v1`.
Transport and authority ACKs without runtime/applied receipts must fail
validation for applied command routes.

Live Android broker-stream command orchestration uses
`rusty.hostess.bridge_command.live_android_execution_evidence.v1` as its
Hostess sidecar. `hostessctl run-bridge-command-live-android --input
<request.json> --out <evidence.json>` records broker launch/process checks,
ADB forwarding, forwarded socket readiness, Hostess Makepad launch/process
checks, and then embeds the normal broker-stream command execution. This is the
preferred Windows companion safe-probe backend because setup and command
evidence travel together while Manifold remains the command authority.

Headset app-private bridge command proof uses
`rusty.hostess.bridge_command.android_execution_evidence.v1` as its Hostess
sidecar and still emits `rusty.manifold.bridge.route_evidence.v1` as the
frontend-neutral result. `hostessctl run-bridge-command-android --input
<request.json> --out <evidence.json>` stages the request into the Hostess
Makepad app-private settings directory over serial-scoped ADB, launches the XR
activity by default, and pulls
`rusty.hostess.makepad.bridge_command_runtime_receipt.v1`. This route proves
`sent`, `transport_ok`, `runtime_accepted`, and `applied`; it deliberately does
not claim Manifold `authority_accepted`.

Windows companion session orchestration uses
`rusty.hostess.companion.session.v1`. `hostessctl companion-session run --out
<session.json>` writes ordered phases for host preflight, Quest device checks,
broker transport, runtime launch, broker-stream command probing,
app-private fallback recovery, and evidence packaging. The report references
the readiness, catalog, Quest device-link report, bridge-route evidence,
execution sidecar, validation, and optional logcat artifacts it produced. The
device-link artifact uses `rusty.quest.device_link.v1` to summarize device
identity, ADB forward/tunnel state, broker readiness, runtime subscriber
health, command-result stages, and stream capability descriptors. A
broker-stream failure recovered by a passing app-private fallback is reported
as a warning session, not as Manifold command authority for the fallback leg.

Required fields:

- `host_profile`: `desktop`, `mobile`, or `headset`
- `software.origin`: `rusty-hostess`
- `software.host_app`: the Hostess T app id that produced the evidence
- `package.package_id`: `package.polar_h10`
- `package.package_manifest_sha256`: hash of the consumed package manifest
- `package.stream_manifest_sha256`: hashes for embedded stream manifests when
  the host can report them
- `package.module_manifest_sha256`: hashes for embedded module manifests when
  selected module outputs are emitted
- `status`: top-level pass/fail result; failed evidence is never accepted even
  if one stream row says `pass`
- `errors`: must be empty for a trusted pass
- `streams`: stream results with counters, rates, malformed-frame counts, and
  pass/fail status
- selected processor-module streams include `module_id`, input stream id,
  method id, module-specific metrics, quality label, and empty issue code on
  pass
- desktop live selected-module evidence includes `capture.runtime_path`,
  `capture.runtime_input`, and `capture.graph_execution_report` when processor
  outputs came from the Rust graph runner
- coherence stream metrics include a 64-second window, 2 Hz sample rate, 128
  uniform RR samples, peak frequency, peak-band power, total-band power,
  remaining power, ratio variants, normalized score, quality label, and empty
  issue code on pass

The current validator is:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json> --packages-root <packages-root>
```

The validator compares the package manifest hash to the supplied packages root,
rejects missing, fake, or `unavailable` hashes, rejects non-empty evidence
errors, rejects malformed frames, validates selected module outputs for
declared module ids, requires runtime coherence metrics for
`stream.polar_h10.coherence`, and can write a validation report with
`--report-out`.

When `hostessctl run-live` succeeds it also writes a companion
`rusty.manifold.host_run.run_evidence.v1` contract artifact beside the raw
capture JSON.

Live/replay parity is checked by replaying the captured runtime-input artifact
through `hostessctl run-replay` and comparing selected module streams from the
live and replay evidence.

Telemetry GUI snapshots are generated from accepted evidence with:

```powershell
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <capture.json> --out <snapshot.json>
```

The snapshot schema is `rusty.hostess.telemetry.snapshot.v1`. It is bounded for
GUI use: stream previews are capped, module outputs are summarized, and high-rate
raw samples remain in runtime/evidence artifacts.

Telemetry render PNGs are accepted only with a neighboring
`rusty.hostess.telemetry.render_evidence.v1` sidecar. The sidecar records target,
page, source evidence path, dimensions, content-pixel count, status, timestamp,
and minimum validation thresholds. Missing, stale, too-small, or blank renders
must fail validation.

Raw run artifacts should stay outside this repository.
