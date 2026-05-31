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

- `apps/hostess-t-desktop/capture_polar.py`: desktop live capture using a local
  Python dependency.
- `apps/hostess-t-android`: Java-only Android APK built with Android
  command-line tools. The same APK can run mobile and headset profiles.

## Validation

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol
```

Live evidence is validated with:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json>
```

Runtime artifacts should be written outside this repository.
