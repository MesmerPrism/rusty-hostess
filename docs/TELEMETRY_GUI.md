# Telemetry GUI

Hostess T includes lightweight telemetry pages for package validation runs. The
Android-class app renders the pages on device; the desktop CLI can render the
same evidence family into PNG artifacts. These pages are operator-visible
monitors, not processor authorities.

## Boundary

The GUI displays acquisition buffers and capture state from the same Android
activity path that `hostessctl run-live` starts. It does not select formulas,
own module state, write package manifests, or replace the package Rust runtime.

Canonical selected-module evidence comes from the Rust package runtime path.
The Android-class telemetry page displays module values from graph execution
reports produced through the JNI bridge.

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

The Android-class app can render the telemetry view directly into a PNG under
the app evidence folder. This is the preferred headset visual evidence route
because it captures the Hostess view itself and does not depend on which system
surface is currently focused.

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target quest --page modules --adb <adb> --serial <serial> --out <telemetry.png>
```

Desktop evidence can be rendered from a completed evidence file:

```powershell
python tools\hostessctl\hostessctl.py render-telemetry --target desktop --page raw --input <evidence.json> --out <telemetry.png>
```

## Command Route

The GUI has no independent state-changing controls in this slice. Captures are
started through the existing command route:

```powershell
python tools\hostessctl\hostessctl.py run-live --target phone --stream hr_rr --packages-root <packages-root> --out <evidence.json> --adb <adb> --serial <serial>
```

The same route is used for headset profile runs by setting `--target quest`.
