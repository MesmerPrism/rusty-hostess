#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $MetadataDirectory,

    [Parameter(Mandatory)]
    [string] $ArtifactPath,

    [switch] $RequireSignedRelease
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Import-Module (
    Join-Path $repoRoot `
        "packaging\windows-hotspot-provider\WindowsAuthenticodePolicy.psm1"
) -Force
$releasePolicySchema = Join-Path $repoRoot `
    "schemas\hostess-windows-hotspot-release-policy.schema.json"
$sourceReleasePolicyPath = Join-Path $repoRoot `
    "packaging\windows-hotspot-provider\release-policy.json"

function Get-Sha256 {
    param([Parameter(Mandatory)][string] $LiteralPath)
    (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
}

function Test-ProviderDiscoverySemVer {
    param([Parameter(Mandatory)][string] $Value)

    if ($Value -cnotmatch (
        "^(?:0|[1-9][0-9]*)\." +
        "(?:0|[1-9][0-9]*)\." +
        "(?:0|[1-9][0-9]*)" +
        "(?:-(?<prerelease>[0-9a-z-]+(?:\.[0-9a-z-]+)*))?$"
    )) {
        return $false
    }
    $Prerelease = $Matches["prerelease"]
    if ([string]::IsNullOrEmpty($Prerelease)) {
        return $true
    }
    foreach ($Identifier in $Prerelease.Split(".")) {
        if ($Identifier -cmatch "^[0-9]+$" -and
            $Identifier.Length -gt 1 -and
            $Identifier.StartsWith("0", [StringComparison]::Ordinal)) {
            return $false
        }
    }
    return $true
}

function Assert-ExactProperties {
    param(
        [Parameter(Mandatory)] $Object,
        [Parameter(Mandatory)][string[]] $Expected,
        [Parameter(Mandatory)][string] $Context
    )
    $actual = @($Object.PSObject.Properties.Name | Sort-Object)
    if (Compare-Object ($Expected | Sort-Object) $actual) {
        throw "$Context has missing or unknown fields."
    }
}

foreach ($ValidVersion in @(
    "0.0.0",
    "1.2.3",
    "1.0.0-0",
    "1.0.0-alpha.1",
    "10.20.30-alpha-beta.9"
)) {
    if (-not (Test-ProviderDiscoverySemVer -Value $ValidVersion)) {
        throw "Release metadata SemVer gate rejected '$ValidVersion'."
    }
}
foreach ($InvalidVersion in @(
    "01.0.0",
    "1.01.0",
    "1.0.01",
    "1.0.0-01",
    "1.0.0-alpha..1",
    "1.0.0--.",
    "1.0.0-RC1",
    "1.0.0+build"
)) {
    if (Test-ProviderDiscoverySemVer -Value $InvalidVersion) {
        throw "Release metadata SemVer gate accepted '$InvalidVersion'."
    }
}

$Generator = Join-Path $PSScriptRoot `
    "New-WindowsHotspotProviderReleaseMetadata.ps1"
$MissingArtifact = Join-Path (
    [IO.Path]::GetTempPath()
) "rusty-hostess-generator-input-$([guid]::NewGuid().ToString('N')).missing"
foreach ($InvalidGeneratorVersion in @(
    "01.0.0",
    "1.0.0-01",
    "1.0.0-RC1",
    "1.0.0-alpha..1"
)) {
    $RejectedAtBinding = $false
    try {
        & $Generator `
            -ArtifactPath $MissingArtifact `
            -ProviderVersion $InvalidGeneratorVersion `
            -BuildKind unsigned-dev |
            Out-Null
    }
    catch {
        if ($_.FullyQualifiedErrorId -notmatch
            "^ParameterArgumentValidationError") {
            throw (
                "Generator version '$InvalidGeneratorVersion' reached its " +
                "body instead of failing parameter validation: " +
                $_.FullyQualifiedErrorId)
        }
        $RejectedAtBinding = $true
    }
    if (-not $RejectedAtBinding) {
        throw (
            "Generator accepted malformed provider version " +
            "'$InvalidGeneratorVersion'.")
    }
}

function Get-PeCanonicalPayload {
    param(
        [Parameter(Mandatory)][string] $LiteralPath,
        [Parameter(Mandatory)][long] $ExpectedPayloadSize
    )
    [byte[]] $bytes = [System.IO.File]::ReadAllBytes($LiteralPath)
    if ($bytes.Length -lt 512) { throw "PE artifact is unexpectedly small." }
    $peOffset = [int] [BitConverter]::ToUInt32($bytes, 0x3c)
    if ($peOffset -lt 64 -or $peOffset + 256 -gt $bytes.Length -or
        $bytes[$peOffset] -ne 0x50 -or
        $bytes[$peOffset + 1] -ne 0x45 -or
        $bytes[$peOffset + 2] -ne 0 -or
        $bytes[$peOffset + 3] -ne 0) {
        throw "Artifact does not have a valid PE header."
    }
    $optionalHeader = $peOffset + 24
    $magic = [BitConverter]::ToUInt16($bytes, $optionalHeader)
    $dataDirectories = switch ($magic) {
        0x10b { $optionalHeader + 96 }
        0x20b { $optionalHeader + 112 }
        default { throw "Artifact has an unsupported PE optional header." }
    }
    $checksumOffset = $optionalHeader + 64
    $certificateDirectory = $dataDirectories + (4 * 8)
    if ($certificateDirectory + 8 -gt $bytes.Length) {
        throw "Artifact PE certificate directory is truncated."
    }
    $certificateOffset = [long] [BitConverter]::ToUInt32(
        $bytes,
        $certificateDirectory
    )
    $certificateSize = [long] [BitConverter]::ToUInt32(
        $bytes,
        $certificateDirectory + 4
    )
    if (($certificateOffset -eq 0) -xor ($certificateSize -eq 0)) {
        throw "Artifact PE certificate directory is inconsistent."
    }
    $physicalPayloadSize = [long] $bytes.Length
    if ($certificateOffset -ne 0) {
        if ($certificateOffset % 8 -ne 0 -or
            $certificateSize -lt 8 -or
            $certificateOffset + $certificateSize -ne $bytes.Length) {
            throw "Artifact Authenticode certificate table is malformed or has an overlay."
        }
        $physicalPayloadSize = $certificateOffset
    }
    if ($ExpectedPayloadSize -le $certificateDirectory + 8 -or
        $ExpectedPayloadSize -gt $physicalPayloadSize) {
        throw "Artifact canonical payload size is invalid."
    }
    for ($index = $ExpectedPayloadSize; $index -lt $physicalPayloadSize; $index++) {
        if ($bytes[$index] -ne 0) {
            throw "Artifact has nonzero data between its payload and certificate table."
        }
    }
    [byte[]] $payload = [byte[]]::new($ExpectedPayloadSize)
    [Array]::Copy($bytes, 0, $payload, 0, $ExpectedPayloadSize)
    [Array]::Clear($payload, $checksumOffset, 4)
    [Array]::Clear($payload, $certificateDirectory, 8)
    [ordered]@{
        sha256 = [Convert]::ToHexString(
            [System.Security.Cryptography.SHA256]::HashData($payload)
        ).ToLowerInvariant()
        size_bytes = $ExpectedPayloadSize
    }
}

$metadataRoot = (Resolve-Path -LiteralPath $MetadataDirectory).Path
$artifact = Get-Item -LiteralPath (Resolve-Path -LiteralPath $ArtifactPath).Path
$allowedFiles = @(
    "LICENSE",
    "THIRD-PARTY-NOTICES.txt",
    "rusty-hostess-hotspot-provider.release-policy.json",
    "rusty-hostess-hotspot-provider.provenance.json"
)
$observedFiles = @(
    Get-ChildItem -LiteralPath $metadataRoot -File |
        Select-Object -ExpandProperty Name |
        Sort-Object
)
if (Compare-Object ($allowedFiles | Sort-Object) $observedFiles) {
    throw "Release metadata must contain exactly the four owner-issued documents."
}

$archivedPolicyPath = Join-Path $metadataRoot `
    "rusty-hostess-hotspot-provider.release-policy.json"
$releasePolicy = Read-RustyHostessProviderReleasePolicy `
    -PolicyPath $archivedPolicyPath `
    -SchemaPath $releasePolicySchema
$releasePolicySha256 = Get-Sha256 -LiteralPath $archivedPolicyPath
if ($releasePolicySha256 -cne (Get-Sha256 -LiteralPath $sourceReleasePolicyPath)) {
    throw "Archived release policy does not equal the exact source policy."
}

$provenancePath = Join-Path $metadataRoot "rusty-hostess-hotspot-provider.provenance.json"
$provenanceText = Get-Content -Raw -LiteralPath $provenancePath
$provenanceSchemaPath = Join-Path $repoRoot `
    "schemas\hostess-windows-hotspot-release-provenance-v2.schema.json"
if (-not (Test-Json -Json $provenanceText -SchemaFile $provenanceSchemaPath)) {
    throw "Provider release provenance failed its owner v2 schema."
}
$provenance = $provenanceText | ConvertFrom-Json
Assert-ExactProperties $provenance @(
    "schema",
    "product_id",
    "provider_version",
    "artifact",
    "source",
    "build",
    "dependencies",
    "bundled_native_libraries",
    "signing",
    "release_policy",
    "companion_documents",
    "distribution"
) "provenance"
Assert-ExactProperties $provenance.artifact @(
    "name", "sha256", "size_bytes", "product_version"
) "artifact"
Assert-ExactProperties $provenance.source @(
    "repository",
    "revision",
    "tree",
    "availability_url",
    "availability_state",
    "verified_at_utc",
    "tree_clean"
) "source"
Assert-ExactProperties $provenance.build @(
    "kind",
    "framework",
    "runtime_identifier",
    "source_date_epoch",
    "unsigned_artifact_sha256",
    "unsigned_artifact_size_bytes",
    "canonical_payload_sha256",
    "canonical_payload_size_bytes"
) "build"
Assert-ExactProperties $provenance.signing @(
    "state",
    "authenticode_status",
    "subject",
    "issuer",
    "thumbprint_sha1",
    "certificate_sha256",
    "code_signing_eku_present",
    "self_issued",
    "timestamp_present",
    "chain_trusted",
    "chain_element_count",
    "chain_status_flags",
    "public_trust_claim",
    "trust_boundary"
) "signing"
Assert-ExactProperties $provenance.release_policy @(
    "asset_name", "schema", "sha256", "size_bytes"
) "release policy evidence"
Assert-ExactProperties $provenance.distribution @(
    "eligibility", "binary_authority", "allowed_channels", "stable_eligible"
) "distribution"
if ($provenance.schema -cne "rusty.hostess.windows_hotspot.release_provenance.v2" -or
    $provenance.product_id -cne "rusty-hostess-windows-hotspot-provider") {
    throw "Unexpected Hostess provider provenance identity."
}
if ($provenance.provider_version -isnot [string] -or
    -not (Test-ProviderDiscoverySemVer `
        -Value $provenance.provider_version)) {
    throw "Provider version is incompatible with capability discovery."
}
if ($provenance.artifact.name -cne "rusty-hostess-hotspot-provider.exe" -or
    $artifact.Name -cne $provenance.artifact.name -or
    $artifact.Length -ne $provenance.artifact.size_bytes -or
    (Get-Sha256 -LiteralPath $artifact.FullName) -cne $provenance.artifact.sha256) {
    throw "Provider artifact does not match owner provenance."
}
$observedProductVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo(
    $artifact.FullName
).ProductVersion
$expectedProductVersion =
    "$($provenance.provider_version)+$($provenance.source.revision)"
if ($provenance.artifact.product_version -cne $expectedProductVersion -or
    $observedProductVersion -cne $expectedProductVersion) {
    throw "Provider artifact does not embed the exact source revision."
}
if ($provenance.source.repository -cne "https://github.com/MesmerPrism/rusty-hostess" -or
    $provenance.source.revision -cnotmatch "^[0-9a-f]{40}$" -or
    $provenance.source.tree -cnotmatch "^[0-9a-f]{40}$" -or
    -not [bool] $provenance.source.tree_clean) {
    throw "Provider source evidence is incomplete."
}
if ($provenance.build.kind -cnotin @("unsigned-dev", "signed-release")) {
    throw "Provider build kind is not closed."
}
$sourceUri = [Uri] $provenance.source.availability_url
if ($sourceUri.Scheme -cne "https" -or
    $sourceUri.Host -cne "github.com" -or
    $sourceUri.AbsolutePath.TrimEnd("/") -cne
        "/MesmerPrism/rusty-hostess/tree/$($provenance.source.revision)") {
    throw "Provider source availability URL does not bind the exact revision."
}
if (@($provenance.dependencies).Count -eq 0 -or
    @($provenance.bundled_native_libraries).Count -eq 0) {
    throw "Dependency or bundled native-library inventory is empty."
}
if ($provenance.build.unsigned_artifact_sha256 -cnotmatch "^[0-9a-f]{64}$" -or
    [long] $provenance.build.unsigned_artifact_size_bytes -le 0 -or
    $provenance.build.canonical_payload_sha256 -cnotmatch "^[0-9a-f]{64}$" -or
    [long] $provenance.build.canonical_payload_size_bytes -le 0) {
    throw "Reproducible unsigned artifact evidence is invalid."
}
$canonicalPayload = Get-PeCanonicalPayload `
    -LiteralPath $artifact.FullName `
    -ExpectedPayloadSize $provenance.build.canonical_payload_size_bytes
if ($canonicalPayload.sha256 -cne
        $provenance.build.canonical_payload_sha256 -or
    $canonicalPayload.size_bytes -ne
        $provenance.build.canonical_payload_size_bytes) {
    throw "Artifact PE payload does not match owner provenance."
}
foreach ($dependency in @($provenance.dependencies)) {
    Assert-ExactProperties $dependency @(
        "name", "version", "license", "license_url", "project_url"
    ) "dependency"
    if ([string]::IsNullOrWhiteSpace($dependency.name) -or
        [string]::IsNullOrWhiteSpace($dependency.version) -or
        [string]::IsNullOrWhiteSpace($dependency.license)) {
        throw "Dependency evidence is incomplete."
    }
}
foreach ($library in @($provenance.bundled_native_libraries)) {
    Assert-ExactProperties $library @(
        "name", "sha256", "size_bytes"
    ) "bundled native library"
    if ($library.name -cnotmatch "^[A-Za-z0-9_.-]+\.dll$" -or
        $library.sha256 -cnotmatch "^[0-9a-f]{64}$" -or
        [long] $library.size_bytes -le 0) {
        throw "Bundled native-library evidence is invalid."
    }
}
if (@($provenance.bundled_native_libraries.name | Sort-Object -Unique).Count -ne
    @($provenance.bundled_native_libraries).Count) {
    throw "Bundled native-library names are not unique."
}
$companionNameDifference = Compare-Object `
    @("LICENSE", "THIRD-PARTY-NOTICES.txt") `
    @($provenance.companion_documents.name | Sort-Object)
if (@($provenance.companion_documents).Count -ne 2 -or
    $null -ne $companionNameDifference) {
    throw "Companion document inventory is incomplete."
}
foreach ($document in @($provenance.companion_documents)) {
    Assert-ExactProperties $document @(
        "name", "sha256", "size_bytes"
    ) "companion document"
    if ($document.name -cnotin @("LICENSE", "THIRD-PARTY-NOTICES.txt")) {
        throw "Unexpected companion document."
    }
    $documentPath = Join-Path $metadataRoot $document.name
    if (-not (Test-Path -LiteralPath $documentPath -PathType Leaf) -or
        (Get-Item -LiteralPath $documentPath).Length -ne $document.size_bytes -or
        (Get-Sha256 -LiteralPath $documentPath) -cne $document.sha256) {
        throw "Companion document does not match owner provenance."
    }
}
if ($provenance.release_policy.asset_name -cne
        "rusty-hostess-hotspot-provider.release-policy.json" -or
    $provenance.release_policy.schema -cne $releasePolicy.schema -or
    $provenance.release_policy.sha256 -cne $releasePolicySha256 -or
    [long] $provenance.release_policy.size_bytes -ne
        (Get-Item -LiteralPath $archivedPolicyPath).Length) {
    throw "Archived release policy does not match owner provenance."
}
if ($provenanceText -match "(?i)[a-z]:\\\\|\\\\\\\\") {
    throw "Provenance contains a machine-private path."
}
if ($provenanceText -match
    "(?i)provider_capability_discovery|descriptor-available|describe-json") {
    throw (
        "Time-varying capability discovery must not be signed, hashed, or " +
        "treated as release provenance.")
}
if ($RequireSignedRelease) {
    $observedAssessment = Get-RustyHostessProviderAuthenticodeAssessment `
        -LiteralPath $artifact.FullName `
        -Policy $releasePolicy
    $verifiedAt = [DateTimeOffset]::MinValue
    $verifiedAtValid = [DateTimeOffset]::TryParse(
        [string] $provenance.source.verified_at_utc,
        [ref] $verifiedAt
    )
    if ($provenance.build.kind -cne "signed-release" -or
        $provenance.distribution.eligibility -cne "labs_signed_release" -or
        @($provenance.distribution.allowed_channels).Count -ne 1 -or
        $provenance.distribution.allowed_channels[0] -cne "labs" -or
        $provenance.distribution.stable_eligible -ne $false -or
        $provenance.signing.state -cne "accepted_exact_owner_signature" -or
        $provenance.signing.authenticode_status -cnotin @(
            "valid", "unknown_error") -or
        [string]::IsNullOrWhiteSpace($provenance.signing.subject) -or
        $provenance.signing.subject -cne $releasePolicy.signer.subject -or
        $provenance.signing.issuer -cne $releasePolicy.signer.issuer -or
        $provenance.signing.thumbprint_sha1 -cnotmatch "^[0-9a-f]{40}$" -or
        $provenance.signing.certificate_sha256 -cnotmatch "^[0-9a-f]{64}$" -or
        $provenance.signing.thumbprint_sha1 -cne
            $releasePolicy.signer.thumbprint_sha1.ToLowerInvariant() -or
        $provenance.signing.certificate_sha256 -cne
            $releasePolicy.signer.certificate_sha256 -or
        $provenance.signing.code_signing_eku_present -ne $true -or
        $provenance.signing.self_issued -ne $true -or
        $provenance.signing.timestamp_present -ne $true -or
        $provenance.signing.public_trust_claim -ne $false -or
        $provenance.signing.chain_element_count -ne 1 -or
        $observedAssessment.state -cne $provenance.signing.state -or
        $observedAssessment.authenticode_status -cne
            $provenance.signing.authenticode_status -or
        $observedAssessment.subject -cne
            $provenance.signing.subject -or
        $observedAssessment.issuer -cne $provenance.signing.issuer -or
        $observedAssessment.thumbprint_sha1.ToLowerInvariant() -cne
            $provenance.signing.thumbprint_sha1 -or
        $observedAssessment.certificate_sha256 -cne
            $provenance.signing.certificate_sha256 -or
        $observedAssessment.code_signing_eku_present -ne
            $provenance.signing.code_signing_eku_present -or
        $observedAssessment.self_issued -ne $provenance.signing.self_issued -or
        $observedAssessment.timestamp_present -ne
            $provenance.signing.timestamp_present -or
        $observedAssessment.chain_trusted -ne
            $provenance.signing.chain_trusted -or
        $observedAssessment.chain_element_count -ne
            $provenance.signing.chain_element_count -or
        (@($observedAssessment.chain_status_flags) -join "|") -cne
            (@($provenance.signing.chain_status_flags) -join "|") -or
        $observedAssessment.public_trust_claim -ne
            $provenance.signing.public_trust_claim -or
        $observedAssessment.trust_boundary -cne
            $provenance.signing.trust_boundary -or
        $provenance.source.availability_state -cne "verified_public" -or
        -not $verifiedAtValid) {
        throw "Metadata is not eligible for signed publication."
    }
    $recordedTrustedBoundary =
        $provenance.signing.authenticode_status -ceq "valid" -and
        $provenance.signing.chain_trusted -eq $true -and
        $provenance.signing.chain_element_count -eq 1 -and
        @($provenance.signing.chain_status_flags).Count -eq 0 -and
        $provenance.signing.trust_boundary -ceq
            "host-chain-valid-no-public-trust-claim"
    $recordedUntrustedBoundary =
        $provenance.signing.authenticode_status -ceq "unknown_error" -and
        $provenance.signing.chain_trusted -eq $false -and
        $provenance.signing.chain_element_count -eq 1 -and
        @($provenance.signing.chain_status_flags).Count -eq 1 -and
        $provenance.signing.chain_status_flags[0] -ceq "UntrustedRoot" -and
        $provenance.signing.trust_boundary -ceq
            "exact-pinned-self-issued-untrusted-root-only"
    if (-not $recordedTrustedBoundary -and -not $recordedUntrustedBoundary) {
        throw "Signed provenance does not report one admitted chain boundary."
    }
}
elseif ($provenance.build.kind -eq "signed-release") {
    throw "Signed metadata requires explicit RequireSignedRelease validation."
}
elseif ($provenance.build.kind -eq "unsigned-dev" -and
    ($provenance.distribution.eligibility -cne "development_only" -or
     @($provenance.distribution.allowed_channels).Count -ne 0 -or
     $provenance.distribution.stable_eligible -ne $false -or
     $provenance.source.availability_state -cne "unverified_development" -or
     $null -ne $provenance.source.verified_at_utc -or
     $provenance.signing.state -cne "unsigned" -or
     $provenance.signing.authenticode_status -cne "not_signed" -or
     $null -ne $provenance.signing.subject -or
     $null -ne $provenance.signing.issuer -or
     $null -ne $provenance.signing.thumbprint_sha1 -or
     $null -ne $provenance.signing.certificate_sha256 -or
     $provenance.signing.code_signing_eku_present -ne $false -or
     $null -ne $provenance.signing.self_issued -or
     $provenance.signing.timestamp_present -ne $false -or
     $provenance.signing.chain_trusted -ne $false -or
     $provenance.signing.chain_element_count -ne 0 -or
     @($provenance.signing.chain_status_flags).Count -ne 0 -or
     $provenance.signing.public_trust_claim -ne $false -or
     $provenance.signing.trust_boundary -cne "unsigned-development" -or
     $provenance.build.unsigned_artifact_sha256 -cne
        $provenance.artifact.sha256 -or
     $provenance.build.unsigned_artifact_size_bytes -ne
        $provenance.artifact.size_bytes)) {
    throw "Unsigned development metadata is not causally bound and development-only."
}

[ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_metadata_validation.v2"
    result = "pass"
    artifact_sha256 = $provenance.artifact.sha256
    source_revision = $provenance.source.revision
    distribution_eligibility = $provenance.distribution.eligibility
} | ConvertTo-Json -Depth 5
