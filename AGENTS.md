# Rusty Hostess Agent Notes

This repo contains Rusty Hostess T, the first-party install and test shell for
Manifold packages. It is allowed to contain platform APIs and installable test
apps. Keep `rusty-manifold` contract-first and keep `rusty-manifold-packages`
manifest/fixture-first.

## Scope

- Minimal host apps and scripts that consume Manifold package manifests.
- Live package validation slots for desktop, mobile, and headset profiles.
- Evidence JSON, validators, and build scripts for clean host tests.

## Non-Scope

- Legacy app integration.
- Product UI.
- Dynamic package loading.
- Long-lived background services.
- Private planning paths, device serials, personal package ids, or old project
  names in committed files.

## Validation

Run the narrow checks before committing:

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol
```

For live captures, write raw run artifacts outside the repo and commit only
generic code or sanitized sample fixtures.
