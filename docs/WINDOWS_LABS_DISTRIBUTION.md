# Windows Labs Distribution

Rusty Hostess Labs is an opt-in complete Windows Hostess product, distinct
from the independently released Mobile Hotspot provider. Stable and existing
source workflows are unchanged.

The immutable `RustyHostess-Labs-X.Y.Z-win-x64.zip` combines the current
self-contained WPF companion with the complete source-owned `hostessctl`
Python surface, its schemas and fixtures, licensing/architecture documentation,
and a fixed-action bootstrap. The bundle manifest binds every included file,
the exact clean source revision/tree, numeric artifact version, canonical
`vX.Y.Z-alpha.N` tag, runtime requirements, feedback route, features, and
authority exclusions. The Labs product channel owns `rusty-hostess-labs`,
`%LOCALAPPDATA%\RustyHostessLabs`, and its state/report descendants.
The fixed bootstrap sets `RUSTY_HOSTESS_PRODUCT_CHANNEL=labs` for every child
process so the included casting adapter cannot reuse Stable private state;
repository/source execution defaults to the Stable state root.
The product bundle carries the official CPython `3.12.10` Windows x64
embeddable distribution as a private application-local runtime. The reviewed
policy in `packaging/windows-labs/runtime-policy.json` pins its python.org URL,
archive SHA-256, executable SHA-256, PSF Authenticode identity, SPDX document,
Sigstore bundle, and license path. The enabled CLI routes use only the standard
library; the manifest locks the third-party dependency set to empty. The WPF
companion and bootstrap invoke only `runtime/python/python.exe` by its
bundle-relative path, verify its exact hash and version, use isolated mode, and
never search `PATH` or accept an arbitrary runtime path. The embedded
distribution keeps `site` disabled, so ambient user packages remain inert.

The Cinematic Cast adapter is included as Hostess-owned source and remains
experimental. MQDH, `Casting.exe`, Meta libraries/APKs/icons, recordings, and
private logs are never packaged. Users must separately install and license
MQDH. Hostess claims only closed compatibility checks, process identity,
bounded window-close requests, and Hostess receipts—not presentation,
recording, input, extended-FOV, Meta device-session, or device-cleanup effects.
The distribution does not make the adapter suitable for unattended operation.

Each release also carries the deterministic
`RustyHostess-Labs-X.Y.Z-win-x64.release-metadata.json` owner asset. Its
closed contract binds the canonical tag, numeric version, Labs product channel,
alpha maturity, GitHub-prerelease distribution track,
exact source revision/tree, isolated `rusty-hostess-labs` installation
identity, and the outer complete-product ZIP name, SHA-256, and byte length.
It is release provenance for that ZIP only. It does not redistribute Meta
software or attest MQDH presentation, recording, input, extended-FOV,
device-session, or cleanup effects.

The protected `windows-labs-release` workflow requires only the owner signing
PFX and password as secrets. Public owner-signer and CPython trust pins live in
the reviewed versioned runtime policy. The workflow validates the PFX before
use, signs with an RFC3161 timestamp, performs `signtool /pa` chain readback,
and independently matches the signed executable to the exact signer
thumbprint and certificate SHA-256. The current organizational signer is
self-issued, so Labs claims exact pinned owner identity but explicitly makes
no public Windows trust-chain or SmartScreen-reputation claim. It records the
signed executable hash and rejects every other signature or trust failure.
After exact clean tag/revision/tree admission it creates a draft, uploads and
verifies the four-file closed asset set, then publishes only a prerelease with
`latest=false` and performs final readback. It rejects an existing release,
mutable URLs, stable/Labs substitution, extra assets, or a Labs prerelease as
the stable latest pointer. Draft verification resolves the draft's numeric
release ID before reading its closed asset set because GitHub's tag endpoint
does not expose drafts. A failure leaves an explicit immutable incident for
manual review; the workflow never deletes the release or pretends the same tag
can be rerun.

Synthetic validation:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-HostessLabsDistribution.ps1
```

The synthetic test downloads the same hash-pinned official CPython inputs,
builds the product twice, proves deterministic output, runs WPF and CLI bundle
smokes, rejects a tampered bundled interpreter, and proves an ambient fake
`python.exe` cannot become runtime authority.

Reference intake: the [official Python 3.12.10 release](https://www.python.org/downloads/release/python-31210/)
and [Windows embeddable-package documentation](https://docs.python.org/3.12/using/windows.html#the-embeddable-package)
provide the private-runtime model, PSF provenance, and redistribution license.
Hostess borrows only the application-local isolated runtime; it does not add
pip, user packages, Python update authority, or general-purpose interpreter
selection.
