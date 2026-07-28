# Windows hotspot provider release metadata

The provider executable is an owner artifact of Rusty Hostess. It is not a
distributable release by itself.

Generate its owner-issued metadata only from a clean source tree:

```powershell
pwsh -NoProfile -File tools\New-WindowsHotspotProviderReleaseMetadata.ps1 `
  -ArtifactPath target\windows-hotspot-provider\rusty-hostess-hotspot-provider.exe `
  -ProviderVersion 0.1.0 `
  -BuildKind unsigned-dev
```

The output contains:

- `rusty-hostess-hotspot-provider.provenance.json`;
- the Rusty Hostess `LICENSE`;
- generated `THIRD-PARTY-NOTICES.txt`.

The provenance binds the artifact digest and size to the exact source commit
and tree, dependency report, embedded native-library inputs, companion
documents, source-availability URL, and Authenticode state. The executable
also embeds its exact source revision. Unsigned output must byte-match a fresh
clean rebuild before metadata is emitted. An `unsigned-dev` result is
explicitly `development_only`.

Publication tooling must accept only `signed-release` metadata with a
signature revalidated against the artifact and public-source verification.
The signed-release generator therefore also requires
`-VerifyPublicSource`; it checks the exact commit and tree through GitHub
before declaring the source publicly available. It also requires
`-AllowedSignerThumbprint`, verifies that exact owner certificate, and
compares the signed PE payload (excluding only the standard Authenticode
checksum/certificate locations) with the clean unsigned rebuild. Offline
signed-release validation requires the same thumbprint through
`-ExpectedSignerThumbprint`.

Validate metadata and its artifact offline:

```powershell
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderReleaseMetadata.ps1 `
  -MetadataDirectory target\windows-hotspot-provider-release-metadata `
  -ArtifactPath target\windows-hotspot-provider\rusty-hostess-hotspot-provider.exe
```
