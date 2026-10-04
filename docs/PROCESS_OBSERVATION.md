# Completion-driven host process observation

`tools/hostessctl/process_observation.py` owns the new `observe_process` API;
`tools/observe_process.py` exposes the same route. Existing `runtime.run` and
`runtime.run_captured` callers keep their behavior.

API callers may pass a distinct `admit` callback to reject dispatch. It runs
once immediately after the diagnostic `dispatch_before` event and before
Popen. Admission failure produces an incomplete receipt with no started child;
opened raw files are closed and hashed, with no pipe EOF or exit claim.
Progress errors alone remain diagnostic and do not reject dispatch. Consumers
requiring current source or argument admission must use `admit`, rather than
treating progress as an authorization hook. This separation does not imply
atomic admission versus concurrent source changes.

The observer uses one retained `Popen` object, concurrent stdout/stderr readers,
and CreateNew raw files. It waits for genuine child exit/reap and settlement of
every started reader. Child exit alone does not prove inherited pipes reached
EOF. Raw files are flushed and closed before hashing. Numeric nonzero exit is
a complete observation when both streams are complete; callers choose product
acceptance. Collector, callback and source-read errors preserve known facts in
`ObservationFailure.receipt`; unexpected interruption exposes the retained
child in `ObservationInterrupted.owned_process` without killing it.

Short flushed output is read with `read1` and flushed into raw evidence while
the child remains alive. If a raw sink write/flush fails, that reader continues
draining the pipe without retaining bytes; it never closes the pipe early as
an indirect child termination. Genuine pipe-read failure remains unknown.

There is no elapsed kill or automatic finally cleanup. A child or inherited
pipe that never completes remains pending, with progress events. The caller
must remain present or arrange continued owned observation. This is a host
process tool, not device cleanup or remote-effect authority. Interrupting the
observer may leave child and reader threads active; abandoning that object
cannot qualify cleanup.

## CLI

```powershell
python tools/observe_process.py --out <new-evidence-directory> -- <executable> <args>
```

The directory contains raw stdout/stderr, progress JSONL and the Hostess receipt.
Command arguments and raw output can contain secrets; choose private evidence
storage appropriately. No shell is used. Optional `--stdout-budget` and
`--stderr-budget` retain prefixes while still draining all bytes; excess sets
incomplete evidence, without cancelling the child. There is no default cap.

`--source <file>` compares current byte hashes while observing. Those reads are
non-atomic diagnostics and do not authenticate authority or forbid source drift.
Source-change is explicit; read errors make observation incomplete.
The CLI returns failure for source drift even when capture is complete. The
API leaves that acceptance decision to its caller.

On unexpected interruption the CLI saves partial unknown evidence and exits.
It cannot preserve an in-memory Popen object across interpreter exit, so it
does not offer retained-child recovery after host interruption. It performs no
implicit kill or PID reopen. Callers needing continued owned recovery must use
the API and retain the exception's object in the same observing process.

## Cancellation

API callbacks are explicit: `cancelled` requests cooperative cancellation;
`cooperative_cancel` notifies the exact retained child. Notification returning
does not prove child or remote cleanup. A separately authenticated second force
request must join the retained Popen object, observation session, PID, birth
descriptor, recorded cooperative notice identifier and distinct second request
identifier. It is accepted only after the
cooperative notification returned. The observer never reopens numeric PIDs or
kills trees. Windows birth is read with GetProcessTimes from Popen's retained
handle; unavailable birth makes force unsupported. POSIX uses retained object
and session identity and reports no OS birth.

The CLI's `--cancel-request <file>` requests notification. It writes a
`COOPERATIVE_CANCEL.json` marker whose path is passed through the child's
`HOSTESS_COOPERATIVE_CANCEL_PATH` environment variable. The child must implement
its own cooperative hook. A separate `--force-request <file>` carries exactly
`action`, `session_id`, `pid`, `birth_identity`, `cooperative_notice_id`, `request_id`; action must be
`force_cancel_exact_owned_host_child`. Session and birth come from current
progress. The caller owns authorization and private control-file access. No
force is inferred from elapsed time or mere cancellation. Failed notification
or force checks remain unknown. Cooperative and forced receipts do not imply
remote effects were undone.

## Focused validation

The default provider artifact smoke and WPF operator-catalog report fixture
consume this CLI and validate the inner child receipt before their existing
provider/catalog assertions. Standalone `Test-WindowsHotspotProviderArtifact.ps1`
requires Python in addition to .NET; pass `-PythonExe <interpreter>` to select it.
Both routes print the live progress path and retain observation directories.
They do not forward an implicit cancellation or kill trees. The separately
selected external capability-contract gate uses the same observer and requires
its explicit pinned contract checkout. Its descriptor freshness checks remain
in force; retained process observation does not extend descriptor validity.

```powershell
python -m unittest discover -s tools -p test_hostessctl_process_observation.py
$env:HOSTESS_OBSERVATION_LONG_TEST = '1'
python -m unittest discover -s tools -p test_hostessctl_process_observation.py
```

The long case deliberately waits 35 seconds to demonstrate completion beyond
prior host cutoffs. Its delay is a stimulus, never an observer timeout. Default
tests cover concurrent volume, prefixes, known nonzero exit, real parent exit
with descendant-held pipes, callback errors, cooperative cancellation, explicit
owned force, source drift/read errors and the real CLI. A release marker ends
the inherited-pipe fixture naturally; no broad teardown kill exists. Artifacts
remain in task-owned temporary directories, including failures, outside source.
Reader initialization failures at both positions use a genuinely exiting small
child and only inject the thread-start error. Wrong owned-force identity is
denied without killing the child. These are neutral host tests, with no
network/device qualification. Unexpected-interruption and Windows handle-error
fault injection remain separate coverage work; no successful cleanup claim is
made for those paths.

Reader initialization failure may leave an unread live child blocked on its
pipe. This is explicitly unknown pending state requiring operator attention,
with no automatic lifetime cutoff. The small-child fault tests establish
settlement after genuine exit, not guaranteed liveness for a blocked producer.
