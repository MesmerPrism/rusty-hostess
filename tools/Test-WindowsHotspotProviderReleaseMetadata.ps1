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

function Get-Sha256 {
    param([Parameter(Mandatory)][string] $LiteralPath)
    (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
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

$metadataRoot = (Resolve-Path -LiteralPath $MetadataDirectory).Path
$artifact = Get-Item -LiteralPath (Resolve-Path -LiteralPath $ArtifactPath).Path
$allowedFiles = @(
    "LICENSE",
    "THIRD-PARTY-NOTICES.txt",
    "rusty-hostess-hotspot-provider.provenance.json"
)
$observedFiles = @(
    Get-ChildItem -LiteralPath $metadataRoot -File |
        Select-Object -ExpandProperty Name |
        Sort-Object
)
if (Compare-Object ($allowedFiles | Sort-Object) $observedFiles) {
    throw "Release metadata must contain exactly the three owner-issued documents."
}

$provenancePath = Join-Path $metadataRoot "rusty-hostess-hotspot-provider.provenance.json"
$provenanceText = Get-Content -Raw -LiteralPath $provenancePath
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
    "companion_documents",
    "distribution"
) "provenance"
Assert-ExactProperties $provenance.artifact @(
    "name", "sha256", "size_bytes"
) "artifact"
Assert-ExactProperties $provenance.source @(
    "repository", "revision", "tree", "availability_url", "tree_clean"
) "source"
Assert-ExactProperties $provenance.build @(
    "kind", "framework", "runtime_identifier", "source_date_epoch"
) "build"
Assert-ExactProperties $provenance.signing @(
    "state", "status", "subject", "thumbprint"
) "signing"
Assert-ExactProperties $provenance.distribution @(
    "eligibility", "binary_authority"
) "distribution"
if ($provenance.schema -cne "rusty.hostess.windows_hotspot.release_provenance.v1" -or
    $provenance.product_id -cne "rusty-hostess-windows-hotspot-provider") {
    throw "Unexpected Hostess provider provenance identity."
}
if ($provenance.artifact.name -cne "rusty-hostess-hotspot-provider.exe" -or
    $artifact.Name -cne $provenance.artifact.name -or
    $artifact.Length -ne $provenance.artifact.size_bytes -or
    (Get-Sha256 -LiteralPath $artifact.FullName) -cne $provenance.artifact.sha256) {
    throw "Provider artifact does not match owner provenance."
}
if ($provenance.source.repository -cne "https://github.com/MesmerPrism/rusty-hostess" -or
    $provenance.source.revision -cnotmatch "^[0-9a-f]{40}$" -or
    $provenance.source.tree -cnotmatch "^[0-9a-f]{40}$" -or
    -not [bool] $provenance.source.tree_clean) {
    throw "Provider source evidence is incomplete."
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
if ($provenanceText -match "(?i)[a-z]:\\\\|\\\\\\\\") {
    throw "Provenance contains a machine-private path."
}
if ($RequireSignedRelease) {
    if ($provenance.build.kind -cne "signed-release" -or
        $provenance.distribution.eligibility -cne "signed_release" -or
        $provenance.signing.state -cne "verified" -or
        [string]::IsNullOrWhiteSpace($provenance.signing.subject) -or
        $provenance.signing.thumbprint -cnotmatch "^[0-9a-f]+$") {
        throw "Metadata is not eligible for signed publication."
    }
}
elseif ($provenance.build.kind -eq "unsigned-dev" -and
    $provenance.distribution.eligibility -cne "development_only") {
    throw "Unsigned development metadata must remain development-only."
}

[ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_metadata_validation.v1"
    result = "pass"
    artifact_sha256 = $provenance.artifact.sha256
    source_revision = $provenance.source.revision
    distribution_eligibility = $provenance.distribution.eligibility
} | ConvertTo-Json -Depth 5
