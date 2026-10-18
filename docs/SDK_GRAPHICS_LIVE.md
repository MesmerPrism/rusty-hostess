# Finite SDK debug backend

`hostessctl sdk-graphics live` uses the existing `ShaderIteration.handle`
lifecycle for actual typed QFM installed-APK observation and fixed-name pushes.
Quest's pinned SDK provider joins actual local APK primary/alias/packaged
baseline bytes first; the installed single APK must match that exact artifact.
The backend is implemented; **device qualification remains pending**.

The supported consumer is the selected Spatial workload debug status family,
not arbitrary APKs. It must already enable SDK0.14 graphics reload and expose
its DUMP/shell status provider and original ProductPanel status route. Hostess
compares the actual owner token, submitted parameters and revisions through
the app's explicitly supplied, pinned status-only wrapper. App defaults,
private effects and parameter decisions stay with the app. No new authenticated
runtime route is claimed. Other app status families remain unavailable.

## Closed private inputs

`sdk_graphics_live_contract.load_config` defines the closed
`rusty.hostess.sdk_graphics.live_inputs.v1` capsule. It binds one transport and
canonical serial, boot, package, PID, UID, process start ticks; path/SHA-256 pairs
for APK, ADB, QFM, owner enabling-APK evidence, app status and settings reference;
the settings wrapper and explicit PowerShell host pins; and the Quest provider
root and all three script pins. A catalog hash and batch-digest-keyed pixel
predicates close the inputs. The fallback boolean records existing operator
scope; it creates no authority or headset custody. Keep the capsule private.

Each pixel predicate has only `rect=[x,y,width,height]`, `rgb=[r,g,b]`,
`tolerance=0..16` and `minimum_matches>=64`. Rectangles are display-bounded and
at most four million pixels. Select independently reviewed candidate/baseline
predicates that distinguish their intended output. Moving content may be
unsuitable. The intended predicate must be negative immediately before its
trigger. A fresh post-trigger raw Android display readback must match, fenced
by advancing same-actor accepted/end sequences and unchanged app-owned submitted
settings. Cached metadata, matching remote hashes, arbitrary screenshot changes
or caller completion JSON cannot acknowledge adoption.

This is narrow Android-display pixel evidence: no eye attribution, compositor
presentation, wearer visibility, complete shader correctness or GPU completion.
No SDK callback is invented. A nonmatching predicate keeps the original trigger
pending and prohibits an automatic baseline mutation.

## Finite test

```powershell
python tools/hostessctl/hostessctl.py sdk-graphics plan-live `
  --config <private-inputs.json> --catalog <catalog.json> `
  --baseline-batch <exact-revert-batch> --candidate-batch <fresh-batch> --out <new-plan.json>
python tools/hostessctl/hostessctl.py sdk-graphics live `
  --config <same-inputs.json> --catalog <same-catalog.json> `
  --baseline-batch <same-revert-batch> --candidate-batch <same-fresh-batch> `
  --evidence-root <new-private-directory> --out <new-report.json> --confirm-live-sdk-debug
```

Planning validates local inputs only. Execution requires coordinated custody and
fresh references from the already running enabling APK. It does not install,
launch, force-stop, change properties, own a port or alter the ADB daemon.
Source/tool, actor or settings drift refuses progress. Outputs are CreateNew.

The sequence transfers one candidate, verifies all twelve remote hashes,
triggers once and takes at most three read-only observations. Only observed
candidate pixels permit exact baseline transfer, one trigger and the same
bounded observation. Incomplete execution exits nonzero while retaining its
actual lifecycle; the exit code does not mean an effect failed. Unknown
originals block mutation. Inspect `terminal-report.json`, checkpoints, owner
outputs and process receipts rather than starting a replacement session.
The default finite route closes its in-memory owner when it returns. Its report
explicitly says that live handles cannot be restored after process loss.
No automatic retry, cleanup, rollback or remote deletion is performed. Reports
use the existing `companion-report projection --sdk-graphics` route.

For an original trigger that may adopt later, add `--retain-original-stdin` to
the same `live` invocation. It emits the initial report as one JSON line and
keeps that exact `LiveRun` object alive. Send one closed JSON line per turn:

```json
{"action":"observe-original"}
{"action":"revert-baseline"}
```

`observe-original` performs one read-only observation/reconciliation; it never
uploads or triggers. `revert-baseline` requires the original candidate's actual
pixel adoption, then uses the existing handler for a new durable baseline
intent, transfer and one trigger. Late baseline adoption can be observed with
further `observe-original` turns. `status` only projects retained state; `close`
or stdin EOF ends observation without cleanup. Invalid commands produce an
error report while keeping the owner. The route exits after observed baseline
adoption. Its final report is written to `--out`; intermediate reports and
checkpoints stay under the original evidence root. Keep the stdin pipe open
for later turns; EOF discards the live owner. No socket/server or numeric-PID
restoration exists.

API callers construct `sdk_graphics_live_routes.LiveRun(args)`, retain that
object, call `run_initial()`, and later call `observe_original()` and explicit
`revert_baseline()`. The original `ShaderIteration` and executor remain exposed
on the handle. Exceptions retain the owner as `sdk_graphics_live_run`; original
observer exceptions and their exact `Popen` objects remain reachable there.
Pending incomplete transfers may reconcile to uploaded state, but these closed
stdin actions do not automatically dispatch a candidate trigger that was never
sent. Use the same retained API handler for a separately authorized next stage;
never restart the candidate sequence to resolve an original operation.

## Provider gaps and retirement

QFM lacks the SDK trigger, fixed remote hashes and participating app-status
routes. The selected developer fallback fills only those fixed operations,
the package-derived `files/app_assets` directory, raw display readback and exact
process/boot observations. No caller shell, component, remote path, broadcast
or argument vector is accepted. The stock SDK receiver stays unauthenticated;
twelve uploads remain non-atomic.

Host children use completion-driven observation, genuine exit/reap and both
EOFs. Actual original host transport exit/reap and both pipe EOFs retire that
transport even after a nonzero QFM exit or malformed response; they do not prove
file-effect success, nested process-tree retirement, or SDK/GPU retirement.
After that fact, unchanged app guards plus all twelve current hashes can
reconcile an uncertain transfer read-only. Matching bytes while the retained
original child is still active cannot clear pending. The same retained `Popen`
can later establish its real exit/EOF; no new transfer is sent. A reload also
requires its fresh original-request-bound pixel witness.
Process loss discards live handles and requires owner reconciliation, never
automatic replay. Known operation facts survive later report/checkpoint errors
with a visible warning, and reporting-only failure permits continued read-only
observation or explicit baseline revert on the same session. Each new effect
still requires its own successfully persisted pre-dispatch intent. Read-only
observation failure preserves known dispatch state.
The live route flushes and `os.fsync`s each pending `sent` intent before its
first effect. A required sync failure refuses dispatch. Later reporting-only
checkpoints do not add a new durability gate to an already known operation.

`tools/test_hostessctl_sdk_graphics_live.py` exercises actual backend command
paths through an executable local peer with synthetic bytes/pixels and real
host process observation. It establishes transport conformance, not hardware
acceptance. Generic preparer promotion and selected app-wrapper availability
remain explicit provider dependencies until their owning source is published.
