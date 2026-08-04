#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ArtifactPath,

    [Parameter(Mandatory)]
    [ValidateScript({
        $Match = [regex]::Match(
            $_,
            "^(?:0|[1-9][0-9]*)\." +
            "(?:0|[1-9][0-9]*)\." +
            "(?:0|[1-9][0-9]*)" +
            "(?:-(?<prerelease>[0-9a-z-]+(?:\.[0-9a-z-]+)*))?$",
            [Text.RegularExpressions.RegexOptions]::CultureInvariant)
        if (-not $Match.Success) {
            return $false
        }
        foreach ($Identifier in $Match.Groups["prerelease"].Value.Split(".")) {
            if ($Identifier -cmatch "^[0-9]+$" -and
                $Identifier.Length -gt 1 -and
                $Identifier.StartsWith(
                    "0",
                    [StringComparison]::Ordinal)) {
                return $false
            }
        }
        return $true
    })]
    [string] $ProviderVersion,

    [ValidateSet("unsigned-dev", "signed-release")]
    [string] $BuildKind = "unsigned-dev",

    [string] $OutputDirectory = "target\windows-hotspot-provider-release-metadata",

    [string] $SourceAvailabilityUrl,

    [switch] $VerifyPublicSource
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Get-Sha256 {
    param([Parameter(Mandatory)][string] $LiteralPath)
    (Get-FileHash -Algorithm SHA256 -LiteralPath $LiteralPath).Hash.ToLowerInvariant()
}

function Write-Utf8 {
    param(
        [Parameter(Mandatory)][string] $LiteralPath,
        [Parameter(Mandatory)][string] $Content
    )
    [System.IO.File]::WriteAllText(
        $LiteralPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
}

function Get-NuspecValue {
    param(
        [Parameter(Mandatory)][xml] $Document,
        [Parameter(Mandatory)][string] $Name
    )
    $node = $Document.SelectSingleNode(
        "/*[local-name()='package']/*[local-name()='metadata']/*[local-name()='$Name']"
    )
    if ($null -eq $node) { return $null }
    $node.InnerText
}

function Get-PeCanonicalPayload {
    param(
        [Parameter(Mandatory)][string] $LiteralPath,
        [long] $ExpectedPayloadSize = 0
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
    $payloadSize = if ($ExpectedPayloadSize -gt 0) {
        $ExpectedPayloadSize
    } else {
        $physicalPayloadSize
    }
    if ($payloadSize -le $certificateDirectory + 8 -or
        $payloadSize -gt $physicalPayloadSize) {
        throw "Artifact canonical payload size is invalid."
    }
    for ($index = $payloadSize; $index -lt $physicalPayloadSize; $index++) {
        if ($bytes[$index] -ne 0) {
            throw "Artifact has nonzero data between its payload and certificate table."
        }
    }
    [byte[]] $payload = [byte[]]::new($payloadSize)
    [Array]::Copy($bytes, 0, $payload, 0, $payloadSize)
    [Array]::Clear($payload, $checksumOffset, 4)
    [Array]::Clear($payload, $certificateDirectory, 8)
    [ordered]@{
        sha256 = [Convert]::ToHexString(
            [System.Security.Cryptography.SHA256]::HashData($payload)
        ).ToLowerInvariant()
        size_bytes = $payloadSize
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$releasePolicyModule = Join-Path $repoRoot `
    "packaging\windows-hotspot-provider\WindowsAuthenticodePolicy.psm1"
$releasePolicySchema = Join-Path $repoRoot `
    "schemas\hostess-windows-hotspot-release-policy.schema.json"
$releaseProvenanceSchema = Join-Path $repoRoot `
    "schemas\hostess-windows-hotspot-release-provenance-v2.schema.json"
$releasePolicySourcePath = Join-Path $repoRoot `
    "packaging\windows-hotspot-provider\release-policy.json"
Import-Module $releasePolicyModule -Force
$releasePolicy = Read-RustyHostessProviderReleasePolicy `
    -PolicyPath $releasePolicySourcePath `
    -SchemaPath $releasePolicySchema
$releasePolicySha256 = Get-Sha256 -LiteralPath (
    (Resolve-Path -LiteralPath $releasePolicySourcePath).Path
)
$projectPath = Join-Path $repoRoot "tools\windows_hotspot_provider\RustyHostess.WindowsHotspot.Provider.csproj"
$artifact = Get-Item -LiteralPath (Resolve-Path -LiteralPath $ArtifactPath).Path
if ($artifact.Name -cne "rusty-hostess-hotspot-provider.exe") {
    throw "Artifact filename must be exactly rusty-hostess-hotspot-provider.exe."
}

$revision = (& git -C $repoRoot rev-parse HEAD).Trim()
$tree = (& git -C $repoRoot rev-parse "HEAD^{tree}").Trim()
$sourceDateEpoch = [long] ((& git -C $repoRoot show -s --format=%ct HEAD).Trim())
$sourceDirt = @(& git -C $repoRoot status --porcelain=v1 --untracked-files=all)
if ($LASTEXITCODE -ne 0 -or
    $revision -cnotmatch "^[0-9a-f]{40}$" -or
    $tree -cnotmatch "^[0-9a-f]{40}$") {
    throw "Could not resolve exact Git source evidence."
}
if ($sourceDirt.Count -ne 0) {
    throw "Release metadata requires a clean Rusty Hostess source tree."
}

$sourceRepository = "https://github.com/MesmerPrism/rusty-hostess"
if (-not $SourceAvailabilityUrl) {
    $SourceAvailabilityUrl = "$sourceRepository/tree/$revision"
}
$sourceUri = [Uri] $SourceAvailabilityUrl
if ($sourceUri.Scheme -cne "https" -or
    $sourceUri.Host -cne "github.com" -or
    $sourceUri.AbsolutePath.TrimEnd("/") -cne
        "/MesmerPrism/rusty-hostess/tree/$revision") {
    throw "SourceAvailabilityUrl must identify the exact public source revision."
}
$sourceAvailabilityState = "unverified_development"
$sourceVerifiedAtUtc = $null
if ($BuildKind -eq "signed-release" -and -not $VerifyPublicSource) {
    throw "A signed release requires VerifyPublicSource."
}
if ($BuildKind -eq "unsigned-dev" -and $VerifyPublicSource) {
    throw "Unsigned development metadata cannot assert public-source verification."
}
if ($VerifyPublicSource) {
    $headers = @{
        Accept = "application/vnd.github+json"
        "User-Agent" = "rusty-hostess-release-metadata"
    }
    if ($env:GITHUB_TOKEN) {
        $headers.Authorization = "Bearer $($env:GITHUB_TOKEN)"
    }
    $publicCommit = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/MesmerPrism/rusty-hostess/git/commits/$revision" `
        -Headers $headers `
        -Method Get
    if ($publicCommit.sha -cne $revision -or $publicCommit.tree.sha -cne $tree) {
        throw "Public source evidence does not match the local commit and tree."
    }
    $sourceAvailabilityState = "verified_public"
    $sourceVerifiedAtUtc = [DateTimeOffset]::UtcNow.ToString("O")
}

if ($BuildKind -eq "signed-release") {
    $assessment = Get-RustyHostessProviderAuthenticodeAssessment `
        -LiteralPath $artifact.FullName `
        -Policy $releasePolicy
    $signing = [ordered]@{
        state = $assessment.state
        authenticode_status = $assessment.authenticode_status
        subject = $assessment.subject
        issuer = $assessment.issuer
        thumbprint_sha1 = $assessment.thumbprint_sha1.ToLowerInvariant()
        certificate_sha256 = $assessment.certificate_sha256
        code_signing_eku_present = $true
        self_issued = [bool] $assessment.self_issued
        timestamp_present = [bool] $assessment.timestamp_present
        chain_trusted = [bool] $assessment.chain_trusted
        chain_element_count = [int] $assessment.chain_element_count
        chain_status_flags = @($assessment.chain_status_flags)
        public_trust_claim = $false
        trust_boundary = $assessment.trust_boundary
    }
}
else {
    $signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature `
        -LiteralPath $artifact.FullName
    if ($signature.Status -ne
        [Management.Automation.SignatureStatus]::NotSigned) {
        throw "Unsigned development metadata requires an unsigned artifact."
    }
    $signing = [ordered]@{
        state = "unsigned"
        authenticode_status = "not_signed"
        subject = $null
        issuer = $null
        thumbprint_sha1 = $null
        certificate_sha256 = $null
        code_signing_eku_present = $false
        self_issued = $null
        timestamp_present = $false
        chain_trusted = $false
        chain_element_count = 0
        chain_status_flags = @()
        public_trust_claim = $false
        trust_boundary = "unsigned-development"
    }
}
$expectedProductVersion = "$ProviderVersion+$revision"
$productVersion = [System.Diagnostics.FileVersionInfo]::GetVersionInfo(
    $artifact.FullName
).ProductVersion
if ($productVersion -cne $expectedProductVersion) {
    throw "Artifact product version does not bind the exact clean source revision."
}

& dotnet restore $projectPath -r win-x64 | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Provider restore failed." }
$assetsPath = Join-Path $repoRoot "tools\windows_hotspot_provider\obj\project.assets.json"
$assets = Get-Content -Raw -LiteralPath $assetsPath | ConvertFrom-Json -AsHashtable
$dependencyVersions = [ordered]@{}
$packageRoots = @($assets.packageFolders.Keys)

$inventoryRoot = Join-Path (
    Join-Path $repoRoot "target"
) (".windows-hotspot-provider-inventory-" + [Guid]::NewGuid().ToString("N"))
$nativeLibraries = @()
try {
    & dotnet publish $projectPath `
        -c Release `
        -r win-x64 `
        --self-contained true `
        -p:PublishSingleFile=false `
        -p:DebugType=None `
        -p:DebugSymbols=false `
        -o $inventoryRoot | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Expanded provider inventory publish failed." }
    $publishedDepsPath = Join-Path $inventoryRoot "rusty-hostess-hotspot-provider.deps.json"
    $publishedDeps = Get-Content -Raw -LiteralPath $publishedDepsPath |
        ConvertFrom-Json -AsHashtable
    foreach ($library in $publishedDeps.libraries.Keys) {
        $parts = $library -split "/", 2
        if ($parts.Count -ne 2 -or
            $parts[0] -eq "rusty-hostess-hotspot-provider") {
            continue
        }
        $packageName = $parts[0]
        if ($packageName.StartsWith("runtimepack.", [StringComparison]::Ordinal)) {
            $packageName = $packageName.Substring("runtimepack.".Length)
        }
        $dependencyVersions[$packageName] = $parts[1]
    }
    foreach ($file in Get-ChildItem -LiteralPath $inventoryRoot -Filter *.dll -File) {
        $managed = $true
        try {
            [void] [System.Reflection.AssemblyName]::GetAssemblyName($file.FullName)
        }
        catch {
            $managed = $false
        }
        if (-not $managed) {
            $nativeLibraries += [ordered]@{
                name = $file.Name
                sha256 = Get-Sha256 -LiteralPath $file.FullName
                size_bytes = $file.Length
            }
        }
    }
}
finally {
    $targetRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "target")) +
        [System.IO.Path]::DirectorySeparatorChar
    $resolvedInventory = [System.IO.Path]::GetFullPath($inventoryRoot)
    if (-not $resolvedInventory.StartsWith($targetRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove inventory outside the repository target directory."
    }
    if (Test-Path -LiteralPath $resolvedInventory) {
        Remove-Item -LiteralPath $resolvedInventory -Recurse -Force
    }
}
$nativeLibraries = @($nativeLibraries | Sort-Object name)
if ($nativeLibraries.Count -eq 0) {
    throw "Native-library inventory was unexpectedly empty."
}
if ($dependencyVersions.Count -eq 0) {
    throw "Published dependency report was unexpectedly empty."
}

$dependencies = @()
$noticeSections = @(
    "Rusty Hostess Windows hotspot provider third-party notices",
    "",
    "Generated from the exact published dependency graph for source revision $revision.",
    "Package license terms remain with their respective owners."
)
foreach ($name in @($dependencyVersions.Keys | Sort-Object)) {
    $version = [string] $dependencyVersions[$name]
    $packageRoot = $null
    foreach ($base in $packageRoots) {
        $candidate = Join-Path $base (Join-Path $name.ToLowerInvariant() $version)
        if (Test-Path -LiteralPath $candidate) {
            $packageRoot = $candidate
            break
        }
    }
    if (-not $packageRoot) {
        throw "Restored package metadata is unavailable for $name $version."
    }
    $nuspecPath = Get-ChildItem -LiteralPath $packageRoot -Filter *.nuspec -File |
        Select-Object -First 1 -ExpandProperty FullName
    if (-not $nuspecPath) { throw "Package $name $version has no nuspec." }
    [xml] $nuspec = Get-Content -Raw -LiteralPath $nuspecPath
    $licenseExpression = Get-NuspecValue -Document $nuspec -Name "license"
    $licenseUrl = Get-NuspecValue -Document $nuspec -Name "licenseUrl"
    $projectUrl = Get-NuspecValue -Document $nuspec -Name "projectUrl"
    $noticeFiles = @(
        Get-ChildItem -LiteralPath $packageRoot -File -Recurse |
            Where-Object {
                $_.Name -match "^(LICENSE|LICENSE\.TXT|THIRD-PARTY-NOTICES\.TXT)$"
            } |
            Sort-Object FullName
    )
    $dependencies += [ordered]@{
        name = $name
        version = $version
        license = if ($licenseExpression) { $licenseExpression } else { "see_license_url" }
        license_url = $licenseUrl
        project_url = $projectUrl
    }
    $noticeSections += ""
    $noticeSections += "===== $name $version ====="
    $noticeSections += "License: $(if ($licenseExpression) { $licenseExpression } else { 'See package license URL' })"
    if ($licenseUrl) { $noticeSections += "License URL: $licenseUrl" }
    if ($projectUrl) { $noticeSections += "Project URL: $projectUrl" }
    foreach ($noticeFile in $noticeFiles) {
        $noticeSections += ""
        $noticeSections += "--- $($noticeFile.Name) ---"
        $noticeSections += (Get-Content -Raw -LiteralPath $noticeFile.FullName).TrimEnd()
    }
}

$rebuildRoot = Join-Path (
    Join-Path $repoRoot "target"
) (".windows-hotspot-provider-rebuild-" + [Guid]::NewGuid().ToString("N"))
try {
    & dotnet publish $projectPath `
        -c Release `
        -r win-x64 `
        --self-contained true `
        -p:PublishSingleFile=true `
        -p:Version=$ProviderVersion `
        -p:InformationalVersion="$ProviderVersion+$revision" `
        -p:IncludeSourceRevisionInInformationalVersion=false `
        -p:RepositoryCommit=$revision `
        -p:SourceRevisionId=$revision `
        -o $rebuildRoot | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "Reproducible provider rebuild failed." }
    $rebuiltArtifact = Join-Path $rebuildRoot "rusty-hostess-hotspot-provider.exe"
    $unsignedArtifactSha256 = Get-Sha256 -LiteralPath $rebuiltArtifact
    $unsignedArtifactSize = (Get-Item -LiteralPath $rebuiltArtifact).Length
    $rebuiltCanonical = Get-PeCanonicalPayload -LiteralPath $rebuiltArtifact
    $artifactCanonical = Get-PeCanonicalPayload `
        -LiteralPath $artifact.FullName `
        -ExpectedPayloadSize $rebuiltCanonical.size_bytes
    if ($artifactCanonical.sha256 -cne $rebuiltCanonical.sha256 -or
        $artifactCanonical.size_bytes -ne $rebuiltCanonical.size_bytes) {
        throw "Artifact PE payload is not the reproducible output of the recorded source."
    }
    if ($BuildKind -eq "unsigned-dev" -and (
        $unsignedArtifactSha256 -cne (Get-Sha256 -LiteralPath $artifact.FullName) -or
        $unsignedArtifactSize -ne $artifact.Length
    )) {
        throw "Unsigned artifact is not the reproducible output of the recorded source."
    }
}
finally {
    $targetRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot "target")) +
        [System.IO.Path]::DirectorySeparatorChar
    $resolvedRebuild = [System.IO.Path]::GetFullPath($rebuildRoot)
    if (-not $resolvedRebuild.StartsWith($targetRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove rebuild output outside the repository target directory."
    }
    if (Test-Path -LiteralPath $resolvedRebuild) {
        Remove-Item -LiteralPath $resolvedRebuild -Recurse -Force
    }
}

$outputPath = if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
}
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$licenseOutput = Join-Path $outputPath "LICENSE"
$noticesOutput = Join-Path $outputPath "THIRD-PARTY-NOTICES.txt"
$policyOutputName = "rusty-hostess-hotspot-provider.release-policy.json"
$policyOutput = Join-Path $outputPath $policyOutputName
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $licenseOutput -Force
Copy-Item -LiteralPath $releasePolicySourcePath -Destination $policyOutput
Write-Utf8 -LiteralPath $noticesOutput -Content (($noticeSections -join "`n") + "`n")

$companionDocuments = @(
    [ordered]@{
        name = "LICENSE"
        sha256 = Get-Sha256 -LiteralPath $licenseOutput
        size_bytes = (Get-Item -LiteralPath $licenseOutput).Length
    },
    [ordered]@{
        name = "THIRD-PARTY-NOTICES.txt"
        sha256 = Get-Sha256 -LiteralPath $noticesOutput
        size_bytes = (Get-Item -LiteralPath $noticesOutput).Length
    }
)
$releasePolicyEvidence = [ordered]@{
    asset_name = $policyOutputName
    schema = $releasePolicy.schema
    sha256 = Get-Sha256 -LiteralPath $policyOutput
    size_bytes = (Get-Item -LiteralPath $policyOutput).Length
}
$allowedChannels = [Collections.Generic.List[string]]::new()
if ($BuildKind -eq "signed-release") {
    $allowedChannels.Add("labs")
}

$provenance = [ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_provenance.v2"
    product_id = "rusty-hostess-windows-hotspot-provider"
    provider_version = $ProviderVersion
    artifact = [ordered]@{
        name = $artifact.Name
        sha256 = Get-Sha256 -LiteralPath $artifact.FullName
        size_bytes = $artifact.Length
        product_version = $productVersion
    }
    source = [ordered]@{
        repository = $sourceRepository
        revision = $revision
        tree = $tree
        availability_url = $SourceAvailabilityUrl
        availability_state = $sourceAvailabilityState
        verified_at_utc = $sourceVerifiedAtUtc
        tree_clean = $true
    }
    build = [ordered]@{
        kind = $BuildKind
        framework = "net9.0-windows10.0.19041.0"
        runtime_identifier = "win-x64"
        source_date_epoch = $sourceDateEpoch
        unsigned_artifact_sha256 = $unsignedArtifactSha256
        unsigned_artifact_size_bytes = $unsignedArtifactSize
        canonical_payload_sha256 = $rebuiltCanonical.sha256
        canonical_payload_size_bytes = $rebuiltCanonical.size_bytes
    }
    dependencies = @($dependencies)
    bundled_native_libraries = $nativeLibraries
    signing = $signing
    release_policy = $releasePolicyEvidence
    companion_documents = $companionDocuments
    distribution = [ordered]@{
        eligibility = if ($BuildKind -eq "signed-release") {
            "labs_signed_release"
        } else {
            "development_only"
        }
        binary_authority = "rusty-hostess-github-releases"
        allowed_channels = $allowedChannels
        stable_eligible = $false
    }
}
$provenancePath = Join-Path $outputPath "rusty-hostess-hotspot-provider.provenance.json"
$provenanceText = ($provenance | ConvertTo-Json -Depth 12) + "`n"
if (-not (Test-Json -Json $provenanceText -SchemaFile $releaseProvenanceSchema)) {
    throw "Generated provider release provenance failed its owner v2 schema."
}
Write-Utf8 `
    -LiteralPath $provenancePath `
    -Content $provenanceText

[ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_metadata_result.v1"
    result = "pass"
    metadata_directory = $outputPath
    provenance = $provenancePath
    artifact_sha256 = $provenance.artifact.sha256
    source_revision = $revision
    distribution_eligibility = $provenance.distribution.eligibility
} | ConvertTo-Json -Depth 5
