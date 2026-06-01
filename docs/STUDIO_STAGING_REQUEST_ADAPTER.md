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
  --platform-smoke-rejection-out <hostess-platform-smoke-rejection.json>
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
