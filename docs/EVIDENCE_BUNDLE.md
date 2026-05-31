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
- `package.module_manifest_sha256`: hashes for embedded module manifests when
  selected module outputs are emitted
- `status`: top-level pass/fail result; failed evidence is never accepted even
  if one stream row says `pass`
- `errors`: must be empty for a trusted pass
- `streams`: stream results with counters, rates, malformed-frame counts, and
  pass/fail status
- selected processor-module streams include `module_id`, input stream id,
  method id, module-specific metrics, quality label, and empty issue code on
  pass
- coherence stream metrics include a 64-second window, 2 Hz sample rate, 128
  uniform RR samples, peak frequency, peak-band power, total-band power,
  remaining power, ratio variants, normalized score, quality label, and empty
  issue code on pass

The current validator is:

```powershell
python tools\check_live_capture_evidence.py --input <capture.json> --packages-root <packages-root>
```

The validator compares the package manifest hash to the supplied packages root,
rejects missing, fake, or `unavailable` hashes, rejects non-empty evidence
errors, rejects malformed frames, validates selected module outputs for
declared module ids, requires runtime coherence metrics for
`stream.polar_h10.coherence`, and can write a validation report with
`--report-out`.

When `hostessctl run-live` succeeds it also writes a companion
`rusty.manifold.hostess.run_evidence.v1` contract artifact beside the raw
capture JSON.

Raw run artifacts should stay outside this repository.
