# Telemetry GUI

Hostess T telemetry is split into a portable GUI contract and platform
adapters. Makepad is the intended GUI surface. Native Android Canvas rendering
is fallback/debug-only evidence plumbing for the Android-class platform shell.

The telemetry pages are operator-visible monitors, not processor authorities.

## Boundary

The live GUI watches append-only telemetry events derived from the same
command/evidence paths that `hostessctl` uses. It may seed from a bounded
snapshot checkpoint, but it must not require knowing the end of incoming data.
It does not select formulas, own module state, write package manifests, or
replace the package Rust runtime.

Canonical selected-module evidence comes from the Rust package runtime path.
The Android-class fallback/debug view displays module values from graph
execution reports produced through the JNI bridge.

## Boundary Contract

`TelemetryStreamEvent` is the live UI data plane. It is append-only JSONL,
keyed by stable `series_id`, and carries bounded sample batches plus stream
label, unit, source, and sample-rate metadata. Makepad owns the rolling buffers
and staleness state per series, so one dropped stream does not stop other plots.

`TelemetrySnapshot` is a checkpoint/evidence model for Makepad and future Rusty
GUI surfaces. It contains run status, host profile, selected modules, direct
stream counters/rates, bounded preview values, graph status, module output
summaries, issue codes, evidence artifact paths, and optional bounded
`time_series` seeds. It intentionally does not carry unbounded ECG/ACC samples
and is not the live transport model.

`TelemetryCommand` describes GUI requests such as start run, replay run,
render/export evidence, switch page, or reset view. Any state-changing command
must map to an existing or new `hostessctl` route that calls the same
implementation path.

`PlatformAdapter` is Android/desktop acquisition and command bridge code. It
feeds snapshots and accepts commands; it must not render the intended GUI and
must not compute package semantics.

`MakepadTelemetryView` is the Makepad surface under `apps/hostess-t-makepad`.
It reads `rusty.hostess.telemetry.snapshot.v1` only as a seed/checkpoint, then
tails `rusty.hostess.telemetry.stream_event.v1` JSONL for running plots.
Telemetry plots are read-only monitor surfaces; touch drag must not pan or zoom
the plotted data.

## Pages

The raw page renders rolling direct-stream lanes:

- HR: heart-rate notification values
- RR: RR intervals from heart-rate notifications
- ACC: magnitude from decoded ACC samples
- ECG: decoded ECG microvolt samples

The modules page renders opt-in package module outputs:

- HRV lnRMSSD
- RMSSD gain
- coherence normalized score
- breath volume proxy
- breathing rate from breath dynamics
- HRVB resonance amplitude

The header shows run status, mode, selected-module count, and malformed-frame
count. Raw evidence and validation reports are still written as JSON artifacts
and pulled by `hostessctl`.

## Render Evidence

The Android-class app can render its fallback/debug telemetry view directly
into a PNG under the app evidence folder. This captures the Hostess view itself
and does not depend on which system surface is currently focused.

Every accepted render writes a JSON sidecar beside the PNG. Validation rejects
missing, stale, 1x1, too-small, blank, or sidecar-free renders.

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target quest --page modules --adb <adb> --serial <serial> --out <telemetry.png>
```

Desktop evidence can be rendered from a completed evidence file:

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target desktop --page raw --input <evidence.json> --out <telemetry.png>
```

Makepad can consume snapshot JSON as a checkpoint:

```powershell
python tools\hostessctl\hostessctl.py snapshot-telemetry --input <evidence.json> --out <snapshot.json>
cargo run --manifest-path apps\hostess-t-makepad\Cargo.toml -- --snapshot <snapshot.json>
```

For running telemetry, feed an append-only event stream:

```powershell
python tools\telemetry_stream.py --snapshot <snapshot.json> --out <telemetry.jsonl>
cargo run --manifest-path apps\hostess-t-makepad\Cargo.toml -- --snapshot <snapshot.json> --stream-jsonl <telemetry.jsonl>
```

The replay emitter is only a deterministic validation source. A live adapter
should append the same event shape while acquisition is running.

For Android and Quest Makepad validation, seed telemetry under the app-private
debug sandbox (`run-as io.github.mesmerprism.rustyhostess.makepad`), not only
under `/sdcard/Android/data/...`. On the tested phone and Quest builds, the
Makepad process could not read that external app-data path and correctly fell
back to the embedded fixture.

The Makepad app writes an app-owned watcher PNG and JSON sidecar under its
internal telemetry directory. The exporter refreshes periodically even when no
new stream lines arrive, because active/stale status is visible UI state. The
sidecar records `active_series_count`, `stale_series_count`, `sample_total`,
and `watcher_status_line` so screenshot or mirror witnesses can be compared to
the pulled render without relying only on pixels. The PNG and sidecar are
written through temporary files and renamed into place so validation pulls do
not read a half-written periodic export.

## Command Route

The GUI has no independent state-changing controls in this slice. Captures are
started through the existing command route:

```powershell
python tools\hostessctl\hostessctl.py run-live --target phone --stream hr_rr --packages-root <packages-root> --out <evidence.json> --adb <adb> --serial <serial>
```

The same route is used for headset profile runs by setting `--target quest`.
