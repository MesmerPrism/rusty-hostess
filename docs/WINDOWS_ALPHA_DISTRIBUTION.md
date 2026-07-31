# Windows Alpha Distribution

Rusty Hostess alpha is an opt-in complete Windows Hostess product, distinct
from the independently released Mobile Hotspot provider. Stable and existing
source workflows are unchanged.

The immutable `RustyHostess-Alpha-X.Y.Z-win-x64.zip` combines the current
self-contained WPF companion with the complete source-owned `hostessctl`
Python surface, its schemas and fixtures, licensing/architecture documentation,
and a fixed-action bootstrap. The bundle manifest binds every included file,
the exact clean source revision/tree, numeric artifact version, canonical
`vX.Y.Z-alpha.N` tag, runtime requirements, feedback route, features, and
authority exclusions. Alpha owns `rusty-hostess-alpha`,
`%LOCALAPPDATA%\RustyHostessAlpha`, and its state/report descendants.
The product bundle is not wholly self-contained: Python is external and
fail-closed at CPython `3.12.10` plus an independently reviewed executable
SHA-256. The enabled CLI routes use only the standard library; the manifest
locks the third-party dependency set to empty. The WPF companion and bootstrap
both enforce this fixed runtime contract and accept no arbitrary runtime path.

The Cinematic Cast adapter is included as Hostess-owned source and remains
experimental. MQDH, `Casting.exe`, Meta libraries/APKs/icons, recordings, and
private logs are never packaged. Users must separately install and license
MQDH. Hostess claims only closed compatibility checks, process identity,
bounded window-close requests, and Hostess receipts—not presentation,
recording, input, extended-FOV, Meta device-session, or device-cleanup effects.
The distribution does not make the adapter suitable for unattended operation.

Each release also carries the deterministic
`RustyHostess-Alpha-X.Y.Z-win-x64.release-metadata.json` owner asset. Its
closed contract binds the canonical tag, numeric version, alpha channel,
exact source revision/tree, isolated `rusty-hostess-alpha` installation
identity, and the outer complete-product ZIP name, SHA-256, and byte length.
It is release provenance for that ZIP only. It does not redistribute Meta
software or attest MQDH presentation, recording, input, extended-FOV,
device-session, or cleanup effects.

The protected `windows-alpha-release` workflow requires owner signing
credentials at execution, verifies Authenticode with `signtool /pa`, and
matches the signer thumbprint and certificate SHA-256 to independently
protected pins. It records those values and the signed executable hash.
After exact clean tag/revision/tree admission it creates a draft, uploads and
verifies the four-file closed asset set, then publishes only a prerelease with
`latest=false` and performs final readback. It rejects an existing release,
mutable URLs, stable/alpha substitution, extra assets, or an alpha latest
pointer. A failure leaves an explicit immutable incident for manual review;
the workflow never deletes the release or pretends the same tag can be rerun.

Synthetic validation:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-HostessAlphaDistribution.ps1
```
