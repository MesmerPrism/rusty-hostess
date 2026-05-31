# Evidence Bundle

Hostess T run evidence uses JSON files with schema
`rusty.manifold.live_capture_evidence.v1` for the current slice.

Required fields:

- `host_profile`: `desktop`, `mobile`, or `headset`
- `software.origin`: `rusty-hostess`
- `software.host_app`: the Hostess T app id that produced the evidence
- `package.package_id`: `package.polar_h10`
- `package.package_manifest_sha256`: hash of the consumed package manifest
- `streams`: stream results with counters, rates, malformed-frame counts, and
  pass/fail status

The current validator is:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json>
```

Raw run artifacts should stay outside this repository.
