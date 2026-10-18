# SDK graphics development adapter

`hostessctl sdk-graphics` adds host preparation and a closed, injectable shader
iteration handler. Quest owns shader compilation/reflection and APK integration;
the effect executor owns transfer, runtime adoption and retirement. Hostess owns
the host invocation, request lifecycle and evidence projection. No new registry,
watcher, device server or project-runner execution mode is introduced.

This first adapter deliberately selects the audited **SDK0.14 optimized,
ten-vec4/160-byte material** consumer contract. Eight vertex variants and four
fragment aliases must exactly match that owner contract. Earlier 80/96-byte
consumers are unavailable here; those sizes are not invalid SDK interfaces.
Adding a consumer requires its actual owner preparer, ABI and variant closure.
The generic Quest provider lives under `tools/sdk_graphics` in its owning
source. Select a reviewed published revision and pin actual scripts; until
that adoption lands, donor preparation remains an explicit dependency. This
adapter never resolves a floating owner checkout.

## Available operations

`describe` is inert and target-free: it initializes no consumer/process/device
backend. `prepare` invokes the existing Quest `Prepare-FreshSdkHotload.py` with
`--require-sdk-primary`; the caller pins both that script and its adjacent
`Prepare-SdkHotloadCatalog.py`. It uses the existing completion-driven process
observer, requires actual exit and both EOFs, preserves raw output/process
receipts, and rechecks script identity. No arbitrary child argument vector is
accepted. The owner retains the compiler/header/config/source/reflection checks.

```powershell
python tools/hostessctl/hostessctl.py sdk-graphics describe --out <new-report.json>
python tools/hostessctl/hostessctl.py sdk-graphics prepare `
  --owner-app <selected-quest-app-directory> `
  --preparer-sha256 <reviewed-script-digest> --reflector-sha256 <reviewed-script-digest> `
  --baseline-catalog <catalog.json> --source-directory <reviewed-shader-directory> `
  --glslc <glslc> --spirv-val <spirv-val> --spirv-dis <spirv-dis> `
  --headers <selected-headers> --shader-config <shader_config.json> `
  --batch-output <new-batch-directory> --process-evidence <new-observer-directory> `
  --out <new-preparation-report.json>
```

Use `--baseline-revert` instead of `--source-directory` to copy the exact
baseline through the same owner. A manifest's claim alone is not compilation
evidence: retain the actual pinned owner invocation and its artifacts. Source
pinning is explicit local trusted-code selection, not authentication of an
arbitrary supplied script. Source observations are non-atomic diagnostics;
no source lock or runtime grant is fabricated. Incomplete observation retains
the original exception's child in the Python API; CLI exit cannot preserve that
in-memory child, so host interruption requires operator reconciliation, with no
automatic kill, timeout replay or remote-cleanup claim.

## Finite lifecycle and executor seam

`ShaderIteration.handle` is the single API for `prepare`, `transfer`, `reload`,
`observe` and `revert`; the CLI fixture uses it unchanged. Preparation checks
all twelve names, byte counts/digests, exact compiler profile, baseline binding
and per-variant ABI identities before transfer. Snapshot identity includes the
executor's actor/scene/settings identity and strict advancing frame counters.
Input shader bytes are retained as an immutable in-memory batch.

An executor implements only status, fixed-name byte upload, complete hash
readback, scoped reload, output observation and original-request retirement.
It must observe its own current handles/effects. It is not a caller-supplied
completion JSON file or general shell command surface. Mutations have a
write-ahead request checkpoint; unknown results retain the original request
and prohibit all further mutations. Read-only reconciliation requires complete
matching bytes **and original executor operation retirement**. A reload also
requires a fresh post-trigger output witness tied to the exact original request,
batch and actor; cached same-batch output is insufficient. Matching files while
an original operation is still alive cannot permit another mutation.

Revert is a preparation of the exact baseline followed by ordinary transfer,
one trigger and actual observation. Relabeling baseline bytes is not baseline
adoption. No automatic rollback, broad cleanup or replacement session hides an
uncertain effect. The executor retains its cleanup responsibility.
Intent persistence failure prevents dispatch. Once executor retirement is known,
a later journal failure is reported separately and preserves the known operation
state; it never permits replay of that operation. Successful observation and
reconciliation persist the terminal state with the pending request cleared.

The [finite SDK debug backend](SDK_GRAPHICS_LIVE.md) supplies actual QFM and
fixed developer-fallback operations for one selected app-status family, with
original settings and actual output witnesses. Hardware qualification remains
pending. Neither fixture success nor preparation grants device execution or
proves GPU work.

## Executable neutral consumer

The file consumer performs a real process-observed reload in a short-lived
child, reads all twelve uploaded byte strings and emits a deterministic PPM
witness. Baseline/candidate/baseline must change and then restore that witness.
Synthetic inputs are explicitly **not executable SPIR-V** and must never be
uploaded to a GPU. No ports, device processes, SDK compiler or APK build is used.

```powershell
python tools/sdk_graphics_fixture_inputs.py --out <new-input-directory>
python tools/hostessctl/hostessctl.py sdk-graphics fixture `
  --catalog <new-input-directory/catalog/catalog.json> `
  --baseline-batch <new-input-directory/baseline-batch> `
  --candidate-batch <new-input-directory/candidate-batch> `
  --consumer-root <new-consumer-directory> --out <new-iteration-report.json>
python tools/hostessctl/hostessctl.py companion-catalog --frontend cli `
  --hostess-descriptor fixtures/sdk-graphics/module-descriptor.json `
  --gui-descriptors-root fixtures/sdk-graphics --out <new-catalog.json> --fail-on-error
python tools/hostessctl/hostessctl.py companion-report projection `
  --sdk-graphics <new-iteration-report.json> --out <new-projection.json> --fail-on-error
```

The existing descriptor catalog consumes the CLI-only module/neutral transport;
the existing report projector renders its lifecycle, pending request, scope and
cleanup limits. There is no WPF action/button acceptance or new UI registry.
All adapter reports keep live-device acceptance and GPU completion false.
Validation: `python -m unittest tools.test_hostessctl_sdk_graphics`. The source
family includes byte/ABI/profile negatives, exact revert, real child/CLI/catalog/
projection consumers, unknown and active originals, stale witnesses, actor/frame
drift, and inert discovery. Live stereo output and performance remain separate.
