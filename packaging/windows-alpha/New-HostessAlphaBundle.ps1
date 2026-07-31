# Copyright (C) 2026 Rusty Hostess contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string] $Version,
    [Parameter(Mandatory)]
    [ValidatePattern('^v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*$')]
    [string] $ReleaseTag,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')]
    [string] $SourceRevision,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')]
    [string] $SourceTree,
    [Parameter(Mandatory)][string] $WpfPublishDirectory,
    [Parameter(Mandatory)][string] $OutputDirectory,
    [Parameter(Mandatory)][ValidatePattern('^[0-9A-F]{40}$')]
    [string] $ExpectedWpfSignerThumbprint,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')]
    [string] $ExpectedWpfSignerCertificateSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')]
    [string] $ExpectedWpfExecutableSha256,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')]
    [string] $PythonExecutableSha256,
    [string] $RepositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path,
    [switch] $AllowDirtySourceForSyntheticTest,
    [switch] $AllowUnsignedForSyntheticTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Utf8([string] $Path, [string] $Value) {
    [IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

function Get-Sha256([string] $Path) {
    (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

$tagVersion = $ReleaseTag -replace '^v([0-9]+\.[0-9]+\.[0-9]+)-alpha\.[1-9][0-9]*$', '$1'
if ($tagVersion -cne $Version) {
    throw 'release tag and numeric artifact version differ'
}
$head = (& git -C $RepositoryRoot rev-parse HEAD).Trim()
$tree = (& git -C $RepositoryRoot rev-parse 'HEAD^{tree}').Trim()
$status = @(& git -C $RepositoryRoot status --porcelain=v1 --untracked-files=no)
if ($LASTEXITCODE -ne 0 -or $head -cne $SourceRevision -or
    $tree -cne $SourceTree -or
    ($status.Count -ne 0 -and -not $AllowDirtySourceForSyntheticTest)) {
    throw 'bundle source is not the exact clean revision and tree'
}

$wpf = (Resolve-Path -LiteralPath $WpfPublishDirectory).Path
if (-not (Test-Path -LiteralPath (Join-Path $wpf 'HostessCompanion.Wpf.exe'))) {
    throw 'complete-product bundle requires the published WPF companion'
}
$wpfExe = Join-Path $wpf 'HostessCompanion.Wpf.exe'
if ((Get-Sha256 $wpfExe) -cne $ExpectedWpfExecutableSha256) {
    throw 'published WPF executable hash does not match reviewed signed artifact'
}
$signature = Get-AuthenticodeSignature -LiteralPath $wpfExe
if (-not $AllowUnsignedForSyntheticTest) {
    if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -or
        $null -eq $signature.SignerCertificate) {
        throw 'WPF Authenticode signature is absent or invalid'
    }
    $observedThumbprint = $signature.SignerCertificate.Thumbprint.ToUpperInvariant()
    $observedCertificateHash = [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData(
            $signature.SignerCertificate.RawData)).ToLowerInvariant()
    if ($observedThumbprint -cne $ExpectedWpfSignerThumbprint -or
        $observedCertificateHash -cne $ExpectedWpfSignerCertificateSha256) {
        throw 'WPF Authenticode signer is not the independently reviewed owner'
    }
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) {
    throw 'output directory already exists'
}
[IO.Directory]::CreateDirectory($output) | Out-Null
$name = "RustyHostess-Alpha-$Version-win-x64"
$stage = Join-Path $output $name
[IO.Directory]::CreateDirectory($stage) | Out-Null

try {
    Copy-Item -LiteralPath $wpf -Destination (Join-Path $stage 'companion') -Recurse
    $tracked = @(& git -C $RepositoryRoot ls-files -- `
        'tools/*.py' 'schemas/*.json' 'fixtures/**' `
        'apps/hostess-t-desktop/*.py' 'apps/hostess-projection-replay/**' `
        'README.md' 'AGENTS.md' 'LICENSE' 'docs/LICENSING.md' `
        'docs/ARCHITECTURE.md' 'docs/meta-quest-casting-adapter.md')
    if ($LASTEXITCODE -ne 0 -or $tracked.Count -lt 10) {
        throw 'closed source inventory could not be resolved'
    }
    foreach ($relative in $tracked | Sort-Object -Unique) {
        if ($relative -match '(^|/)(bin|obj|target)/' -or
            $relative -match '\.(exe|dll|apk|msi|msix|pfx|pem|key)$') {
            throw "prohibited tracked payload entered Hostess alpha: $relative"
        }
        $source = Join-Path $RepositoryRoot $relative
        $destination = Join-Path $stage ('source\' + $relative.Replace('/', '\'))
        [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }

    $launcher = @'
param([Parameter(Mandatory)][ValidateSet('companion','describe','casting-describe')][string] $Action)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$runtime = Get-Content -LiteralPath (Join-Path $root 'runtime\python-runtime.json') -Raw | ConvertFrom-Json
$pythonCandidates = @(& where.exe python.exe)
if ($LASTEXITCODE -ne 0) {
  throw 'Supported Python interpreter is absent.'
}
$authorized = @(foreach ($candidate in $pythonCandidates) {
  try {
    if ((Get-FileHash -LiteralPath $candidate -Algorithm SHA256 -ErrorAction Stop).
        Hash.ToLowerInvariant() -ceq $runtime.executable_sha256) {
      $candidate
    }
  } catch { continue }
})
$authorized = @($authorized | Select-Object -Unique)
if ($authorized.Count -ne 1) { throw 'Exactly one hash-authorized Python interpreter is required.' }
$python = $authorized[0]
$hash = (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()
$observed = (& $python -c "import sys;print('.'.join(map(str,sys.version_info[:3])))").Trim()
if ($LASTEXITCODE -ne 0 -or $runtime.version -cne '3.12.10' -or
    $observed -cne $runtime.version -or $hash -cne $runtime.executable_sha256) {
  throw 'Python runtime version/hash is not authorized.'
}
switch ($Action) {
  'companion' { & (Join-Path $root 'companion\HostessCompanion.Wpf.exe'); exit $LASTEXITCODE }
  'describe' { & $python (Join-Path $root 'source\tools\hostessctl\hostessctl.py') --help; exit $LASTEXITCODE }
  'casting-describe' {
    & $python (Join-Path $root 'source\tools\hostessctl\hostessctl.py') meta-quest-casting describe --out (Join-Path $env:LOCALAPPDATA 'RustyHostessAlpha\reports\casting-descriptor.json')
    exit $LASTEXITCODE
  }
}
'@
    Write-Utf8 (Join-Path $stage 'bootstrap\hostess-alpha.ps1') $launcher
    $runtime = [ordered]@{
        schema = 'rusty.hostess.external_python_runtime.v1'
        external = $true
        version = '3.12.10'
        executable_sha256 = $PythonExecutableSha256
        third_party_packages = @()
    }
    Write-Utf8 (Join-Path $stage 'runtime\python-runtime.json') (
        ($runtime | ConvertTo-Json -Depth 10) + "`n")

    $files = @(Get-ChildItem -LiteralPath $stage -File -Recurse | ForEach-Object {
        [ordered]@{
            path = [IO.Path]::GetRelativePath($stage, $_.FullName).Replace('\','/')
            sha256 = Get-Sha256 $_.FullName
            size_bytes = $_.Length
        }
    } | Sort-Object path)
    $manifest = [ordered]@{
        schema = 'rusty.hostess.windows_complete_product.v1'
        product = 'rusty-hostess-alpha'
        display_name = 'Rusty Hostess Alpha'
        channel = 'alpha'
        prerelease = $true
        version = $Version
        release_tag = $ReleaseTag
        package_identity = 'rusty-hostess-alpha'
        install_root = '%LOCALAPPDATA%\RustyHostessAlpha'
        state_root = '%LOCALAPPDATA%\RustyHostessAlpha\state'
        source = [ordered]@{
            repository = 'https://github.com/MesmerPrism/rusty-hostess'
            revision = $SourceRevision
            tree = $SourceTree
            license = 'AGPL-3.0-or-later'
        }
        runtimes = [ordered]@{
            windows = '10-or-later-x64'
            companion = 'self-contained-owner-signed-wpf'
            python = $runtime
        }
        typed_entrypoints = @(
            [ordered]@{ id='companion'; command='bootstrap/hostess-alpha.ps1 companion'; arbitrary_arguments=$false },
            [ordered]@{ id='describe'; command='bootstrap/hostess-alpha.ps1 describe'; arbitrary_arguments=$false },
            [ordered]@{ id='casting-describe'; command='bootstrap/hostess-alpha.ps1 casting-describe'; arbitrary_arguments=$false }
        )
        features = @(
            'hostess-companion-wpf',
            'hostessctl-complete-source',
            'meta-cinematic-cast-opaque-adapter',
            'desktop-capture-source',
            'projection-replay-source',
            'schemas-fixtures-and-owner-docs'
        )
        external_requirements = @(
            [ordered]@{
                id = 'meta-mqdh-casting'
                bundled = $false
                user_supplied = $true
                authority = 'Meta'
            },
            [ordered]@{
                id = 'python-runtime'
                bundled = $false
                user_supplied = $true
                authority = 'Python Software Foundation'
            }
        )
        authority_exclusions = @(
            'meta-software-redistribution',
            'cast-presentation-effectiveness',
            'recording',
            'input-forwarding',
            'fov-restoration',
            'device-cleanup'
        )
        separately_released_products = @('rusty-hostess-hotspot-provider')
        feedback = [ordered]@{
            url = 'https://github.com/MesmerPrism/rusty-hostess/issues/new'
            required = @('channel','version','source_revision','artifact_sha256','windows_version','device_class')
            prohibit = @('credentials','personal-data','device-serials','private-logs')
        }
        signing = [ordered]@{
            authenticode_policy = 'signtool-verify-pa'
            signer_thumbprint = $ExpectedWpfSignerThumbprint
            signer_certificate_sha256 = $ExpectedWpfSignerCertificateSha256
            companion_executable_sha256 = $ExpectedWpfExecutableSha256
        }
        files = $files
    }
    $manifestPath = Join-Path $stage 'hostess-product-manifest.json'
    Write-Utf8 $manifestPath (($manifest | ConvertTo-Json -Depth 20) + "`n")

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zipPath = Join-Path $output "$name.zip"
    $stream = [IO.File]::Open($zipPath, [IO.FileMode]::CreateNew)
    try {
        $zip = [IO.Compression.ZipArchive]::new(
            $stream, [IO.Compression.ZipArchiveMode]::Create, $false)
        try {
            foreach ($file in Get-ChildItem -LiteralPath $stage -File -Recurse |
                     Sort-Object FullName) {
                $relative = "$name/" + [IO.Path]::GetRelativePath(
                    $stage, $file.FullName).Replace('\','/')
                $entry = $zip.CreateEntry($relative, [IO.Compression.CompressionLevel]::Optimal)
                $entry.LastWriteTime = [DateTimeOffset]::new(
                    1980, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
                $input = [IO.File]::OpenRead($file.FullName)
                $target = $entry.Open()
                try { $input.CopyTo($target) } finally { $target.Dispose(); $input.Dispose() }
            }
        } finally { $zip.Dispose() }
    } finally { $stream.Dispose() }
    $zipHash = Get-Sha256 $zipPath
    $zipBytes = (Get-Item -LiteralPath $zipPath).Length
    Write-Utf8 (Join-Path $output "$name.zip.sha256") "$zipHash  $name.zip`n"
    Copy-Item -LiteralPath $manifestPath -Destination (
        Join-Path $output "$name.manifest.json")
    $releaseMetadataPath = Join-Path $output "$name.release-metadata.json"
    $releaseMetadata = [ordered]@{
        schema = 'rusty.hostess.windows_alpha_release_metadata.v1'
        repository = 'MesmerPrism/rusty-hostess'
        product = 'rusty-hostess-alpha'
        channel = 'alpha'
        prerelease = $true
        version = $Version
        tag = $ReleaseTag
        source = [ordered]@{
            revision = $SourceRevision
            tree = $SourceTree
        }
        installation_identity = 'rusty-hostess-alpha'
        primary_artifact = [ordered]@{
            role = 'complete-product'
            name = "$name.zip"
            sha256 = $zipHash
            bytes = $zipBytes
        }
    }
    Write-Utf8 $releaseMetadataPath (
        ($releaseMetadata | ConvertTo-Json -Depth 10) + "`n")
    & (Join-Path $PSScriptRoot 'Test-HostessAlphaReleaseMetadata.ps1') `
        -MetadataPath $releaseMetadataPath `
        -ZipPath $zipPath `
        -ExpectedVersion $Version `
        -ExpectedReleaseTag $ReleaseTag `
        -ExpectedSourceRevision $SourceRevision `
        -ExpectedSourceTree $SourceTree | Out-Null
    [ordered]@{
        schema='rusty.hostess.windows_alpha_bundle_receipt.v1'
        result='pass'; version=$Version; tag=$ReleaseTag
        source_revision=$SourceRevision; source_tree=$SourceTree
        zip="$name.zip"; zip_sha256=$zipHash; zip_bytes=$zipBytes
        release_metadata="$name.release-metadata.json"
        release_metadata_sha256=(Get-Sha256 $releaseMetadataPath)
        release_metadata_bytes=(Get-Item -LiteralPath $releaseMetadataPath).Length
        file_count=$files.Count + 1
    } | ConvertTo-Json -Depth 10
}
finally {
    if (Test-Path -LiteralPath $stage) {
        Remove-Item -LiteralPath $stage -Recurse -Force
    }
}
