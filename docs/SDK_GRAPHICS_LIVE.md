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
No automatic retry, cleanup, rollback or remote deletion is performed. Reports
use the existing `companion-report projection --sdk-graphics` route.

## Provider gaps and retirement

QFM lacks the SDK trigger, fixed remote hashes and participating app-status
routes. The selected developer fallback fills only those fixed operations,
the package-derived `files/app_assets` directory, raw display readback and exact
process/boot observations. No caller shell, component, remote path, broadcast
or argument vector is accepted. The stock SDK receiver stays unauthenticated;
twelve uploads remain non-atomic.

Host children use completion-driven observation, genuine exit/reap and both
EOFs. Direct ADB transport retirement and QFM's confirmed transfer receipt are
separate from SDK/GPU retirement. A malformed or uncertain QFM response cannot
prove its nested transfer retired, even if matching bytes later appear.
The Python API preserves original child exceptions. CLI interruption loses
in-memory handles and requires owner reconciliation, never automatic replay.
Known operation facts survive later report errors with a visible warning;
read-only observation failure preserves known dispatch state.

`tools/test_hostessctl_sdk_graphics_live.py` exercises actual backend command
paths through an executable local peer with synthetic bytes/pixels and real
host process observation. It establishes transport conformance, not hardware
acceptance. Generic preparer promotion and selected app-wrapper availability
remain explicit provider dependencies until their owning source is published.
