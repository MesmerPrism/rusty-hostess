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

The Cinematic Cast adapter is included as Hostess-owned source and remains
experimental. MQDH, `Casting.exe`, Meta libraries/APKs/icons, recordings, and
private logs are never packaged. Users must separately install and license
MQDH. Hostess claims only closed compatibility checks, process identity,
bounded window-close requests, and Hostess receipts—not presentation,
recording, input, extended-FOV, Meta device-session, or device-cleanup effects.
The distribution does not make the adapter suitable for unattended operation.

The protected `windows-alpha-release` workflow requires owner signing
credentials at execution, verifies an exact clean tag/revision/tree, creates
only a GitHub prerelease with `--latest=false`, uploads a three-file closed
asset set, and reads back exact tag, visibility, sizes, SHA-256 digests, and
immutable exact-tag URLs. It rejects an existing release, mutable URLs,
stable/alpha substitution, extra assets, or an alpha latest pointer.

Synthetic validation:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\tools\Test-HostessAlphaDistribution.ps1
```
