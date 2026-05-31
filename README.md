# Rusty Hostess

Rusty Hostess T is the default install and test shell for proving Manifold
packages on desktop, mobile, and headset profiles without relying on older host
applications.

The repo is intentionally separate from:

- `rusty-manifold`: contracts, fixtures, schemas, and neutral helpers.
- `rusty-manifold-packages`: package manifests, package fixtures, and package
  validators.

Hostess T consumes package manifests as build or run inputs and emits evidence
JSON that includes package manifest hashes.

## Current Apps

- `apps/hostess-t-desktop/capture_polar.py`: desktop live capture and runtime
  Polar stream validation using a local Python dependency.
- `apps/hostess-t-android`: Java-only Android APK built with Android
  command-line tools. The same APK can run mobile and headset profiles.
- `tools/hostessctl/hostessctl.py run-replay`: deterministic selected-module
  replay that calls the package Rust processor core and validates the resulting
  graph-resolved evidence.

## Validation

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence
python tools\hostessctl\hostessctl.py run-replay --target desktop --module rmssd_gain --module coherence --packages-root <packages-root> --out <capture.json>
```

Live evidence, including runtime processor-module metrics, is validated with:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json> --packages-root <packages-root>
```

`hostessctl run-live` and `hostessctl run-replay` validate evidence through the
same validator and write a companion `rusty.manifold.hostess.run_evidence.v1`
contract artifact beside the raw capture JSON. Runtime artifacts should be
written outside this repository.

Direct stream slots use `--stream hr_rr|ecg|acc|coherence`. Processor modules
are opt-in with repeated `--module` selections, for example:

```powershell
python tools\hostessctl\hostessctl.py run-live --target desktop --module hrv_window --module rmssd_gain --module coherence --packages-root <packages-root> --out <capture.json>
```
