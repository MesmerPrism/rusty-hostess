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
