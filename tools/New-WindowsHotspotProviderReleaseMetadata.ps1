#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ArtifactPath,

    [Parameter(Mandatory)]
    [ValidatePattern("^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$")]
    [string] $ProviderVersion,

    [ValidateSet("unsigned-dev", "signed-release")]
    [string] $BuildKind = "unsigned-dev",

    [string] $OutputDirectory = "target\windows-hotspot-provider-release-metadata",

    [string] $SourceAvailabilityUrl
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

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
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

$signature = Get-AuthenticodeSignature -LiteralPath $artifact.FullName
$signatureVerified =
    $signature.Status -eq [System.Management.Automation.SignatureStatus]::Valid
if ($BuildKind -eq "signed-release" -and -not $signatureVerified) {
    throw "A signed release requires a valid Authenticode signature."
}
$signing = [ordered]@{
    state = if ($signatureVerified) { "verified" } else { "unsigned" }
    status = [string] $signature.Status
    subject = if ($signatureVerified) { $signature.SignerCertificate.Subject } else { $null }
    thumbprint = if ($signatureVerified) {
        $signature.SignerCertificate.Thumbprint.ToLowerInvariant()
    } else {
        $null
    }
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

$outputPath = if ([System.IO.Path]::IsPathRooted($OutputDirectory)) {
    [System.IO.Path]::GetFullPath($OutputDirectory)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $OutputDirectory))
}
[System.IO.Directory]::CreateDirectory($outputPath) | Out-Null
$licenseOutput = Join-Path $outputPath "LICENSE"
$noticesOutput = Join-Path $outputPath "THIRD-PARTY-NOTICES.txt"
Copy-Item -LiteralPath (Join-Path $repoRoot "LICENSE") -Destination $licenseOutput -Force
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
$provenance = [ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_provenance.v1"
    product_id = "rusty-hostess-windows-hotspot-provider"
    provider_version = $ProviderVersion
    artifact = [ordered]@{
        name = $artifact.Name
        sha256 = Get-Sha256 -LiteralPath $artifact.FullName
        size_bytes = $artifact.Length
    }
    source = [ordered]@{
        repository = $sourceRepository
        revision = $revision
        tree = $tree
        availability_url = $SourceAvailabilityUrl
        tree_clean = $true
    }
    build = [ordered]@{
        kind = $BuildKind
        framework = "net9.0-windows10.0.19041.0"
        runtime_identifier = "win-x64"
        source_date_epoch = $sourceDateEpoch
    }
    dependencies = @($dependencies)
    bundled_native_libraries = $nativeLibraries
    signing = $signing
    companion_documents = $companionDocuments
    distribution = [ordered]@{
        eligibility = if ($BuildKind -eq "signed-release") {
            "signed_release"
        } else {
            "development_only"
        }
        binary_authority = "rusty-hostess-github-releases"
    }
}
$provenancePath = Join-Path $outputPath "rusty-hostess-hotspot-provider.provenance.json"
Write-Utf8 `
    -LiteralPath $provenancePath `
    -Content (($provenance | ConvertTo-Json -Depth 12) + "`n")

[ordered]@{
    schema = "rusty.hostess.windows_hotspot.release_metadata_result.v1"
    result = "pass"
    metadata_directory = $outputPath
    provenance = $provenancePath
    artifact_sha256 = $provenance.artifact.sha256
    source_revision = $revision
    distribution_eligibility = $provenance.distribution.eligibility
} | ConvertTo-Json -Depth 5
