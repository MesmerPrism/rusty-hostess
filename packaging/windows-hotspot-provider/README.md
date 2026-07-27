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
documents, source-availability URL, and Authenticode state. An
`unsigned-dev` result is explicitly `development_only`. Publication tooling
must accept only `signed-release` metadata with a verified Authenticode
identity.

Validate metadata and its artifact offline:

```powershell
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderReleaseMetadata.ps1 `
  -MetadataDirectory target\windows-hotspot-provider-release-metadata `
  -ArtifactPath target\windows-hotspot-provider\rusty-hostess-hotspot-provider.exe
```
