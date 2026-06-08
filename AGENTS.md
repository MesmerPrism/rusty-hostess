# Rusty Hostess Agent Notes

This repo contains Rusty Hostess T, the first-party install and test shell for
Manifold packages. It is allowed to contain platform APIs and installable test
apps. Keep `rusty-manifold` contract-first and keep `rusty-manifold-packages`
manifest/fixture-first.

Rusty Morphospace is the top-level project/platform umbrella. Hostess remains
an install/test shell product lane inside that umbrella; it can collect
evidence for Matter, Lattice, Manifold, Optics, Studio, and Quest flows without
becoming their schema or runtime authority.

Project-owned source in this repo is licensed `AGPL-3.0-or-later`. Keep
third-party dependencies, Makepad toolkit code, generated APKs, installer
bundles, signing material, captured evidence, device logs, platform SDKs,
binary releases, and external tools under their own provenance and notice
requirements; see `docs/LICENSING.md`.

## Scope

- Minimal host apps and scripts that consume Manifold package manifests.
- Live package validation slots for desktop, mobile, and headset profiles.
- Evidence JSON, validators, and build scripts for clean host tests.
- Lattice evidence collection for tracked view sets, poses, spatial input
  roles, frame-state binding, calibration, validity, confidence, and runtime
  capabilities when a host run needs situated relation proof.
- Makepad dependencies only inside Hostess Makepad shell crates.

## Non-Scope

- Legacy app integration.
- Product UI.
- Dynamic package loading.
- Long-lived background services.
- Private planning paths, device serials, personal package ids, or old project
  names in committed files.
- Lattice contract authority. Hostess can collect evidence and run adapters,
  but generic relation schemas belong in Rusty Lattice and command/session
  authority remains Manifold.
- Makepad dependencies in Hostess core, CLI, validators, manifests, or
  descriptor logic.

## Validation

Run the narrow checks before committing:

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence tools.test_polar_runtime_bridge tools.test_telemetry_snapshot
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
```

For live captures, write raw run artifacts outside the repo and commit only
generic code or sanitized sample fixtures.
