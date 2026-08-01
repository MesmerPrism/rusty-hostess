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
- `rusty-hostess-hotspot-provider.release-policy.json`;
- the Rusty Hostess `LICENSE`;
- generated `THIRD-PARTY-NOTICES.txt`.

The provenance binds the artifact digest and size to the exact source commit
and tree, dependency report, embedded native-library inputs, companion
documents, source-availability URL, and Authenticode state. The executable
also embeds its exact source revision. Unsigned output must byte-match a fresh
clean rebuild before metadata is emitted. An `unsigned-dev` result is
explicitly `development_only`.

The archived policy is hash-bound by provenance so an offline consumer can
evaluate the exact historical signer and channel policy.

Publication tooling must accept only `signed-release` metadata with a
signature revalidated against the artifact and public-source verification.
The signed-release generator therefore also requires
`-VerifyPublicSource`; it checks the exact commit and tree through GitHub
before declaring the source publicly available. It verifies the exact owner
certificate from the checked-in protected release policy and
compares the signed PE payload (excluding only the standard Authenticode
checksum/certificate locations) with the clean unsigned rebuild. Offline
signed-release validation revalidates the executable against the archived,
hash-bound copy of that exact policy.

The current certificate is self-issued. It is accepted only as exact-pinned
Labs evidence: either Windows and X509 report `Valid` with a one-element chain
and no status flags, or PowerShell reports `UnknownError` with an untrusted
one-element chain carrying only `UntrustedRoot`. Both cases require the exact
subject, issuer, SHA-1 thumbprint, certificate SHA-256, code-signing EKU, and
timestamp evidence. Neither case claims public Windows trust or Stable
eligibility. The workflow and tools never install a certificate into Root or
TrustedPublisher; a Windows reputation/trust warning is therefore expected.

Provenance records the release runner's admitted chain observation. Offline
validation independently admits the current host's observation against the
same two branches, then compares only host-invariant signing identity and
timestamp facts. A runner-recorded `UnknownError`/`UntrustedRoot` boundary may
therefore validate on a host that already observes the exact certificate as
`Valid` with a clean chain, and vice versa. Local trust never rewrites owner
provenance, creates a public trust claim, or enables Stable distribution.

Validate metadata and its artifact offline:

```powershell
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderReleaseMetadata.ps1 `
  -MetadataDirectory target\windows-hotspot-provider-release-metadata `
  -ArtifactPath target\windows-hotspot-provider\rusty-hostess-hotspot-provider.exe
```

## Immutable public release

The owner release workflow is
`.github/workflows/windows-hotspot-provider-release.yml`. It runs only for a
pre-existing tag named
`windows-hotspot-provider-v<provider-version>`, for example
`windows-hotspot-provider-v0.1.0`. The tag must resolve to the exact clean
checkout. The workflow never creates, moves, or overwrites a tag and refuses
to continue when a GitHub Release already exists for it.

Configure the protected GitHub environment
`windows-hotspot-provider-release` with required reviewers. Before creating
any provider tag, enable GitHub release immutability for the Rusty Hostess
repository. The workflow verifies that setting and fails before building when
it is disabled. Configure these environment inputs:

- secret `RUSTY_HOSTESS_AUTHENTICODE_PFX_BASE64`: base64 of the owner
  Authenticode PFX;
- secret `RUSTY_HOSTESS_AUTHENTICODE_PFX_PASSWORD`: its password;
- secret `RUSTY_HOSTESS_RELEASE_POLICY_TOKEN`: a fine-grained token limited to
  Rusty Hostess with repository Administration read permission, used only to
  verify that GitHub release immutability is enabled;
The public pins live only in the versioned
`packaging/windows-hotspot-provider/release-policy.json`; only the PFX and its
password are secrets. The workflow validates that the PFX contains exactly
one private-key code-signing identity matching that policy, signs the exact
self-contained provider, verifies the resulting
Authenticode signature, generates owner provenance with public commit/tree
verification, and revalidates the complete bundle. It then creates one
immutable GitHub Release containing exactly:

- `rusty-hostess-hotspot-provider.exe`;
- `rusty-hostess-hotspot-provider.provenance.json`;
- `rusty-hostess-hotspot-provider.release-policy.json`;
- `LICENSE`;
- `THIRD-PARTY-NOTICES.txt`.

GitHub Releases is the binary authority. Provider discovery remains a
time-varying, non-authorizing description surface and is never a release
asset. After publication, the workflow reads back GitHub's immutable flag and
the SHA-256 digest and size of every asset. It has no asset-update,
release-edit, tag-creation, tag-move, or clobber path. A failed or existing
release requires a new version and tag, not replacement.

`windows-hotspot-provider-v0.1.1` and the immutable public v0.1.2 release are
fixed at their original commits and must not be moved, deleted, reused, or
replaced. This cross-host validator correction does not alter the v0.1.2
assets or provenance. Any successor provider release must use a fresh version
and tag, at least `windows-hotspot-provider-v0.1.3`.

These releases are provider-neutral Labs inputs only. A consumer may project
`allowed_channels: ["labs"]`, but must keep `stable_eligible: false`. Moving
to Stable requires a separately reviewed publicly trusted managed signing
policy and a new release; it cannot be inferred from a locally trusted chain.

Validate this policy locally without signing or publishing:

```powershell
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderReleaseWorkflow.ps1
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderAuthenticodePolicy.ps1
```
