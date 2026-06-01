# Studio Staging Request Adapter

This is the Hostess-owned schema-only intake boundary for Studio staging
execution requests.

Studio emits `rusty.studio.shell_hostess_staging_execution_request.v1` after it
has selected and compared accepted handoff/acceptance artifacts. Hostess reads
that request, validates the authority and route contract, and can emit accepted
ack or rejected reject fixtures. This tool does not copy files, stage files,
install apps, launch apps, open command sessions, collect evidence, talk to
ADB, run Quest builds, or execute Hostess runtime behavior.

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
  --reject-out <hostess-reject-fixture.json>
```

The intake report uses
`rusty.hostess.studio_staging_execution_request_intake.v1` and always records
`execution_performed = false`, `copy_stage_install_launch_evidence_started =
false`, and `command_session_started = false`.
