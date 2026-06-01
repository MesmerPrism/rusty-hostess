# Studio Staging Request Adapter

This is the Hostess-owned schema-only intake boundary for Studio staging
execution requests.

Studio emits `rusty.studio.shell_hostess_staging_execution_request.v1` after it
has selected and compared accepted handoff/acceptance artifacts. Hostess reads
that request, validates the authority and route contract, and can emit accepted
ack or rejected reject fixtures. Hostess can also emit a schema-only smoke
handoff checklist that names the request, ack, and expected evidence receipt
items for the first small Hostess-owned build smoke test, then a dry-run
request/receipt pair over that checklist. This tool does not copy files, stage
files, install apps, launch apps, open command sessions, collect evidence, talk
to ADB, run Quest builds, or execute Hostess runtime behavior.

Authority:

- Studio remains authoring, export-planning, and review.
- Hostess owns copy/stage/install/launch/evidence handoff and the ack/reject
  response.
- Manifold remains command/session authority.

Local validation:

```powershell
python -m py_compile tools\studio_staging_request.py tools\test_studio_staging_request.py
python -m unittest tools.test_studio_staging_request
```

Example intake:

```powershell
python tools\studio_staging_request.py `
  --request <studio-execution-request.json> `
  --report-out <hostess-intake-report.json> `
  --ack-out <hostess-ack-fixture.json> `
  --reject-out <hostess-reject-fixture.json> `
  --smoke-handoff-out <hostess-smoke-handoff.json> `
  --smoke-dry-run-request-out <hostess-smoke-dry-run-request.json> `
  --smoke-dry-run-receipt-out <hostess-smoke-dry-run-receipt.json> `
  --smoke-preflight-out <hostess-smoke-preflight.json> `
  --smoke-host-shell-execution-out <hostess-smoke-host-shell-execution.json> `
  --smoke-review-bundle-out <hostess-smoke-review-bundle.json> `
  --platform-smoke-plan-out <hostess-platform-smoke-plan.json> `
  --platform-smoke-approval-out <hostess-platform-smoke-approval.json> `
  --platform-smoke-rejection-out <hostess-platform-smoke-rejection.json> `
  --platform-smoke-execution-request-out <hostess-platform-smoke-execution-request.json> `
  --platform-smoke-execution-receipt-out <hostess-platform-smoke-execution-receipt.json> `
  --platform-smoke-operator-start-gate-out <hostess-platform-smoke-operator-start-gate.json> `
  --platform-smoke-operator-start-preflight-out <hostess-platform-smoke-operator-start-preflight.json> `
  --platform-smoke-operator-start-preflight-rejection-out <hostess-platform-smoke-operator-start-preflight-rejection.json> `
  --platform-smoke-execution-report-out <hostess-platform-smoke-execution-report.json> `
  --platform-smoke-execution-report-rejection-out <hostess-platform-smoke-execution-report-rejection.json> `
  --platform-smoke-evidence-attachment-out <hostess-platform-smoke-evidence-attachment.json> `
  --platform-smoke-evidence-attachment-rejection-out <hostess-platform-smoke-evidence-attachment-rejection.json> `
  --platform-smoke-evidence-review-out <hostess-platform-smoke-evidence-review.json> `
  --platform-smoke-evidence-review-rejection-out <hostess-platform-smoke-evidence-review-rejection.json>
```

The intake report uses
`rusty.hostess.studio_staging_execution_request_intake.v1` and always records
`execution_performed = false`, `copy_stage_install_launch_evidence_started =
false`, and `command_session_started = false`.

The smoke handoff checklist uses
`rusty.hostess.studio_staging_smoke_handoff.v1`. It records
`build_started = false`, `copy_started = false`, `stage_started = false`,
`install_started = false`, `launch_started = false`,
`evidence_collection_started = false`, and `command_session_started = false`.
It is a checklist for Hostess T or a dedicated host shell to consume later, not
a build or device execution command.

The dry-run request uses
`rusty.hostess.studio_staging_smoke_dry_run_request.v1`. It turns the smoke
handoff checklist into Hostess/Manifold-owned request steps and expected
receipt kinds, but still records all runtime-start flags as false. The dry-run
receipt uses `rusty.hostess.studio_staging_smoke_dry_run_receipt.v1` and
acknowledges those request steps without performing them.

The smoke execution preflight uses
`rusty.hostess.studio_staging_smoke_execution_preflight.v1`. It consumes the
dry-run request and receipt, verifies the Hostess/Manifold capability routes and
receipt kinds, and records `device_required = false` and
`platform_execution_allowed = false`. It is the last schema-only readiness
fixture before Hostess T or a dedicated host shell starts real platform smoke
execution.

The no-device host-shell execution uses
`rusty.hostess.studio_staging_smoke_host_shell_execution.v1`. It consumes the
preflight, performs Hostess-owned schema checks, and emits evidence records for
each Hostess/Manifold capability. It records
`host_shell_harness_performed = true` and `schema_checks_performed = true`,
while `execution_performed`, `runtime_execution_performed`,
`platform_execution_performed`, `build_started`, `copy_started`,
`stage_started`, `install_started`, `launch_started`,
`evidence_collection_started`, and `command_session_started` remain false. It
is not a Quest/APK build, app install, app launch, or evidence-capture run.

The reviewed Hostess bundle uses
`rusty.hostess.studio_staging_smoke_review_bundle.v1`. It consumes the
no-device host-shell execution artifact, checks its validation status, and
bundles the source evidence records into Hostess-reviewed handoff records. It
records `review_bundle_written = true` and
`operator_review_required_before_platform_smoke = true`, while device,
platform, Studio, build, copy, stage, install, launch, evidence collection, and
command-session execution remain disabled.

The operator-controlled platform smoke plan uses
`rusty.hostess.studio_staging_platform_smoke_plan.v1`. It consumes the reviewed
bundle and names future Hostess/Manifold copy, stage, install, launch,
evidence, and command-session review actions plus required operator approvals.
The plan records `operator_approved = false`, `schema_path_execution_allowed =
false`, `platform_execution_allowed = false`, and
`studio_execution_allowed = false`; it is a plan and approval surface, not an
execution command.

The platform smoke approval receipt uses
`rusty.hostess.studio_staging_platform_smoke_approval_receipt.v1`. It consumes
the platform smoke plan and records either an approved or rejected operator
decision over each planned action. An approved receipt may set
`future_execution_authorized = true` so a later Hostess-owned shell can start
work, but the receipt itself still records `execution_performed = false`,
`runtime_execution_performed = false`, `platform_execution_performed = false`,
`build_started = false`, `copy_started = false`, `stage_started = false`,
`install_started = false`, `launch_started = false`,
`evidence_collection_started = false`, and `command_session_started = false`.
It is an approval/rejection contract only; it does not copy, stage, install,
launch, collect evidence, open a command session, or run Quest/APK work.

The platform smoke execution request uses
`rusty.hostess.studio_staging_platform_smoke_execution_request.v1`. It consumes
an approved platform smoke approval receipt and converts each approved planned
action into a pending Hostess-owned execution request for a future Hostess T or
dedicated host-shell run. The request records
`operator_controlled_execution_required = true` and
`hostess_shell_execution_required = true`, but it still records
`device_required = false`, `schema_path_execution_allowed = false`,
`platform_execution_allowed = false`, `studio_execution_allowed = false`,
`execution_performed = false`, `runtime_execution_performed = false`, and
`platform_execution_performed = false`.

The platform smoke execution receipt uses
`rusty.hostess.studio_staging_platform_smoke_execution_receipt.v1`. It
acknowledges or rejects the execution request shape and leaves all copy, stage,
install, launch, evidence collection, command-session, ADB, Quest, OpenXR, APK,
and runtime execution flags false. A pending receipt is not proof that platform
work ran; it is the reviewed handoff shape that a Hostess-owned shell may
consume after an operator starts that shell outside Studio.

The platform smoke operator-start gate uses
`rusty.hostess.studio_staging_platform_smoke_operator_start_gate.v1`. It
consumes a pending platform smoke execution receipt and emits request, ack,
reject, and expected evidence receipt templates for a future Hostess T or
dedicated Quest host-shell operator start. The gate records
`operator_start_required = true`, but it also records `operator_started =
false`, `host_shell_started = false`, `device_required = false`,
`schema_path_execution_allowed = false`, `platform_execution_allowed = false`,
`studio_execution_allowed = false`, `execution_performed = false`,
`runtime_execution_performed = false`, and `platform_execution_performed =
false`. It is a schema handoff gate only; the actual first build smoke test
must be Hostess-owned, operator-started outside Studio, and separately
evidenced.

The platform smoke operator-start preflight receipt uses
`rusty.hostess.studio_staging_platform_smoke_operator_start_preflight_receipt.v1`.
It consumes the operator-start gate and records an approved or rejected
operator decision over the gate, required Hostess shell/toolchain/device
readiness inputs, the Manifold command-session review input, evidence
destination readiness, rollback readiness, and per-action decision receipts.
An approved preflight may authorize a future Hostess-owned host shell to start,
but this receipt still records `operator_started = false`,
`host_shell_started = false`, `device_required = false`,
`schema_path_execution_allowed = false`, `platform_execution_allowed = false`,
`studio_execution_allowed = false`, `execution_performed = false`,
`runtime_execution_performed = false`, and `platform_execution_performed =
false`. It is a preflight approval/rejection contract only; the actual first
build smoke test remains Hostess-owned, operator-started outside Studio, and
separately evidenced.

The platform smoke execution report uses
`rusty.hostess.studio_staging_platform_smoke_execution_report.v1`. It consumes
an approved operator-start preflight and records an operator-started external
Hostess shell report, per-action completed/rejected report rows, readiness
results, and pending evidence placeholders. It does not attach collected
evidence and still records `device_required = false`,
`schema_path_execution_allowed = false`, `platform_execution_allowed = false`,
`studio_execution_allowed = false`, `execution_performed = false`,
`runtime_execution_performed = false`, `platform_execution_performed = false`,
and `real_platform_execution_evidence_attached = false`. The report is the
next Hostess-owned handoff shape toward build readiness; real Quest/APK copy,
stage, install, launch, and evidence collection remain outside Studio and must
be evidenced by a later Hostess-owned shell or Quest host.

The platform smoke evidence attachment receipt uses
`rusty.hostess.studio_staging_platform_smoke_evidence_attachment_receipt.v1`.
It consumes the platform smoke execution report and binds externally supplied
Hostess evidence descriptors to the report's pending evidence placeholders and
readiness results. It is descriptor-only: it can validate that each placeholder
has a matching Hostess-owned external evidence descriptor, but it does not copy
payloads, collect files, start ADB, install, launch, or run Quest/APK work. It
records `device_required = false`, `evidence_payloads_copied = false`,
`schema_path_execution_allowed = false`, `platform_execution_allowed = false`,
`studio_execution_allowed = false`, `execution_performed = false`,
`runtime_execution_performed = false`, `platform_execution_performed = false`,
`evidence_collection_started = false`, and
`real_platform_execution_evidence_attached = false`. Actual evidence
collection and artifact storage remain Hostess-owned work outside Studio.

The platform smoke evidence review uses
`rusty.hostess.studio_staging_platform_smoke_evidence_review.v1`. It consumes
the evidence attachment receipt and emits a Hostess-owned scorecard over the
validated, missing, or rejected evidence descriptors. It records
`operator_review_ready = true` only when the attachment receipt and all
descriptor rows are validated. It is still scorecard-only and records
`device_required = false`, `evidence_payloads_copied = false`,
`schema_path_execution_allowed = false`, `platform_execution_allowed = false`,
`studio_execution_allowed = false`, `execution_performed = false`,
`runtime_execution_performed = false`, `platform_execution_performed = false`,
`evidence_collection_started = false`, and
`real_platform_execution_evidence_attached = false`. It does not collect
evidence, copy payloads, start a host shell, install, launch, run ADB, or run a
Quest/APK build.

Projected-motion breath validation handoff:

```powershell
python tools\studio_staging_request.py `
  --request <studio-execution-request.json> `
  --pmb-authoring-review-in <studio-pmb-authoring-review.json> `
  --pmb-package-evidence-intake-in <studio-pmb-package-evidence-intake.json> `
  --pmb-source-adapter-selection-in <studio-pmb-source-adapter-selection.json> `
  --pmb-validation-handoff-out <hostess-pmb-validation-handoff.json> `
  --validate-pmb-validation-handoff <hostess-pmb-validation-handoff.json> `
  --pmb-replay-validation-receipt-out <hostess-pmb-replay-validation-receipt.json> `
  --validate-pmb-replay-validation-receipt <hostess-pmb-replay-validation-receipt.json>
```

The projected-motion breath validation handoff uses
`rusty.hostess.projected_motion_breath_validation_handoff.v1`. It consumes the
Studio projected-motion breath authoring review and package-evidence intake,
plus an optional Studio source-adapter selection review. It checks the expected
package, module, proposed Manifold command, required package evidence checks,
authority fields, source adapter stream binding, and non-execution flags, then
emits Hostess/Manifold validation slots for authoring-profile review,
package-evidence review, Manifold command-contract review, optional
source-adapter/platform-owner review, and replay-plan preparation. It is
review-only and does not start builds, install, launch, open command sessions,
run processors, copy fixture payloads, collect evidence, use sockets, use ADB,
or touch Quest/OpenXR runtime paths.

The projected-motion breath replay validation receipt uses
`rusty.hostess.projected_motion_breath_replay_validation_receipt.v1`. It
consumes the projected-motion breath validation handoff and optional replay
descriptor rows, then checks the pure-processor replay descriptor contract for
golden and damaged cases. The receipt is a descriptor scorecard only. It
records `device_required = false`, `schema_path_execution_allowed = false`,
`platform_execution_allowed = false`, `studio_execution_allowed = false`,
`runtime_execution_performed = false`, `platform_execution_performed = false`,
`execution_performed = false`, `replay_execution_started = false`,
`fixture_payloads_copied = false`, and `processor_runtime_started = false`.
Actual replay execution and any later platform smoke test remain Hostess-owned
work outside Studio and outside this schema path.

Operator release/readiness bundle:

```powershell
python tools\studio_staging_request.py `
  --request <studio-execution-request.json> `
  --platform-smoke-evidence-review-in <hostess-platform-smoke-evidence-review.json> `
  --pmb-replay-validation-receipt-in <hostess-pmb-replay-validation-receipt.json> `
  --operator-release-readiness-bundle-out <hostess-operator-release-readiness-bundle.json> `
  --operator-release-readiness-bundle-rejection-out <hostess-operator-release-readiness-bundle-rejection.json> `
  --validate-operator-release-readiness-bundle <hostess-operator-release-readiness-bundle.json>
```

The operator release/readiness bundle uses
`rusty.hostess.studio_staging_operator_release_readiness_bundle.v1`. It
consumes the platform smoke evidence review and projected-motion breath replay
validation receipt, then records the selected schema artifacts and Hostess T or
dedicated Quest host-shell readiness targets for later operator-owned work. It
is the next build-readiness handoff shape, not a build runner. It records
`operator_release_ready = true` only when both source artifacts are reviewed or
validated, and it keeps `operator_started = false`, `host_shell_started =
false`, `device_required = false`, `schema_path_execution_allowed = false`,
`platform_execution_allowed = false`, `studio_execution_allowed = false`,
`execution_performed = false`, `runtime_execution_performed = false`,
`platform_execution_performed = false`, `build_started = false`,
`copy_started = false`, `stage_started = false`, `install_started = false`,
`launch_started = false`, `evidence_collection_started = false`,
`command_session_started = false`, `replay_execution_started = false`,
`apk_build_started = false`, `schema_artifact_payloads_copied = false`,
`release_payloads_copied = false`, and `evidence_payloads_copied = false`.
Hostess T or a dedicated Quest host shell still owns any first real build
smoke test; Studio remains authoring, export-planning, and review.
