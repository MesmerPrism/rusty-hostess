# Evidence Bundle

Hostess T run evidence uses JSON files with schema
`rusty.manifold.live_capture_evidence.v1` for the current slice.

Required fields:

- `host_profile`: `desktop`, `mobile`, or `headset`
- `software.origin`: `rusty-hostess`
- `software.host_app`: the Hostess T app id that produced the evidence
- `package.package_id`: `package.polar_h10`
- `package.package_manifest_sha256`: hash of the consumed package manifest
- `package.stream_manifest_sha256`: hashes for embedded stream manifests when
  the host can report them
- `status`: top-level pass/fail result; failed evidence is never accepted even
  if one stream row says `pass`
- `errors`: must be empty for a trusted pass
- `streams`: stream results with counters, rates, malformed-frame counts, and
  pass/fail status

The current validator is:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json> --packages-root <packages-root>
```

The validator compares the package manifest hash to the supplied packages root,
rejects missing, fake, or `unavailable` hashes, rejects non-empty evidence
errors, rejects malformed frames, and can write a validation report with
`--report-out`.

When `hostessctl run-live` succeeds it also writes a companion
`rusty.manifold.hostess.run_evidence.v1` contract artifact beside the raw
capture JSON.

Raw run artifacts should stay outside this repository.
