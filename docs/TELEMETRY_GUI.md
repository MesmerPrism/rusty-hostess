# Telemetry GUI

Hostess T includes a lightweight on-device telemetry panel for phone and
headset profiles. It is an operator-visible monitor for package validation
runs, not a processor authority.

## Boundary

The GUI displays acquisition buffers and capture state from the same Android
activity path that `hostessctl run-live` starts. It does not select formulas,
own module state, write package manifests, or replace the package Rust runtime.

Canonical selected-module evidence still comes from the Rust package runtime
path where that bridge is available. Until the on-device JNI runtime bridge is
implemented, Java/Kotlin processor rows are smoke evidence only.

## Current Panel

The panel renders four rolling time-series lanes:

- HR: heart-rate notification values
- RR: RR intervals from heart-rate notifications
- ACC: magnitude from decoded ACC samples
- ECG: decoded ECG microvolt samples

The header shows run status, mode, selected-module count, and malformed-frame
count. Raw evidence and validation reports are still written as JSON artifacts
and pulled by `hostessctl`.

## Command Route

The GUI has no independent state-changing controls in this slice. Captures are
started through the existing command route:

```powershell
python tools\hostessctl\hostessctl.py run-live --target phone --stream hr_rr --packages-root <packages-root> --out <evidence.json> --adb <adb> --serial <serial>
```

The same route is used for headset profile runs by setting `--target quest`.

## Next Bridge

The next implementation step is to add the JNI runtime bridge described in
`docs/ON_DEVICE_RUNTIME_BRIDGE.md`, then have the telemetry panel display direct
acquisition streams plus graph-resolved selected-module outputs from the Rust
runtime report.
