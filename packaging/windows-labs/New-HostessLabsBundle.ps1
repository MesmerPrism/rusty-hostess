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
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{64}$')]
    [string] $ExpectedWpfExecutableSha256,
    [Parameter(Mandatory)][string] $PythonRuntimeArchivePath,
    [Parameter(Mandatory)][string] $PythonRuntimeSbomPath,
    [Parameter(Mandatory)][string] $PythonRuntimeSigstorePath,
    [string] $RuntimePolicyPath = (Join-Path $PSScriptRoot 'runtime-policy.json'),
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

$resolvedPolicyPath = (Resolve-Path -LiteralPath $RuntimePolicyPath).Path
$policySchemaPath = Join-Path $RepositoryRoot `
    'schemas\hostess-windows-labs-runtime-policy.schema.json'
$policyText = Get-Content -LiteralPath $resolvedPolicyPath -Raw
if (-not (Test-Json -Json $policyText -SchemaFile $policySchemaPath)) {
    throw 'Windows Labs runtime policy does not satisfy its owner schema'
}
$policy = $policyText | ConvertFrom-Json -Depth 20
$ExpectedWpfSignerThumbprint = $policy.wpf_signer.thumbprint
$ExpectedWpfSignerCertificateSha256 = $policy.wpf_signer.certificate_sha256

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
    if ($null -eq $signature.SignerCertificate -or
        $null -eq $signature.TimeStamperCertificate) {
        throw 'WPF Authenticode signature or RFC3161 timestamp is absent'
    }
    $observedThumbprint = $signature.SignerCertificate.Thumbprint.ToUpperInvariant()
    $observedCertificateHash = [Convert]::ToHexString(
        [Security.Cryptography.SHA256]::HashData(
            $signature.SignerCertificate.RawData)).ToLowerInvariant()
    if ($observedThumbprint -cne $ExpectedWpfSignerThumbprint -or
        $observedCertificateHash -cne $ExpectedWpfSignerCertificateSha256) {
        throw 'WPF Authenticode signer is not the independently reviewed owner'
    }
    $selfIssued = $signature.SignerCertificate.Subject -ceq
        $signature.SignerCertificate.Issuer
    $chain = [Security.Cryptography.X509Certificates.X509Chain]::new()
    try {
        $chain.ChainPolicy.RevocationMode =
            [Security.Cryptography.X509Certificates.X509RevocationMode]::NoCheck
        $chainTrusted = $chain.Build($signature.SignerCertificate)
        $onlyUntrustedRoot = -not $chainTrusted -and
            $chain.ChainStatus.Count -eq 1 -and
            $chain.ChainStatus[0].Status -eq
                [Security.Cryptography.X509Certificates.X509ChainStatusFlags]::UntrustedRoot
    }
    finally {
        $chain.Dispose()
    }
    $allowedPinnedSelfIssuedTrust = $policy.wpf_signer.self_issued -and
        -not $policy.wpf_signer.public_trust_claim -and $selfIssued -and
        $signature.Status -eq [Management.Automation.SignatureStatus]::UnknownError -and
        $onlyUntrustedRoot
    if ($signature.Status -ne [Management.Automation.SignatureStatus]::Valid -and
        -not $allowedPinnedSelfIssuedTrust) {
        throw "WPF Authenticode validation failed: $($signature.Status) $($signature.StatusMessage)"
    }
}
$pythonArchive = (Resolve-Path -LiteralPath $PythonRuntimeArchivePath).Path
$pythonSbom = (Resolve-Path -LiteralPath $PythonRuntimeSbomPath).Path
$pythonSigstore = (Resolve-Path -LiteralPath $PythonRuntimeSigstorePath).Path
if ((Get-Sha256 $pythonArchive) -cne $policy.python.archive_sha256 -or
    (Get-Sha256 $pythonSbom) -cne $policy.python.sbom_sha256 -or
    (Get-Sha256 $pythonSigstore) -cne $policy.python.sigstore_sha256) {
    throw 'CPython archive or provenance hash does not match the reviewed policy'
}
$output = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $output) {
    throw 'output directory already exists'
}
[IO.Directory]::CreateDirectory($output) | Out-Null
$name = "RustyHostess-Labs-$Version-win-x64"
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
            throw "prohibited tracked payload entered Hostess Labs: $relative"
        }
        $source = Join-Path $RepositoryRoot $relative
        $destination = Join-Path $stage ('source\' + $relative.Replace('/', '\'))
        [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination
    }

    $runtimeRoot = Join-Path $stage 'runtime'
    $pythonRoot = Join-Path $runtimeRoot 'python'
    [IO.Directory]::CreateDirectory($pythonRoot) | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($pythonArchive)
    try {
        foreach ($entry in $archive.Entries) {
            if ([string]::IsNullOrWhiteSpace($entry.FullName) -or
                $entry.FullName.Contains('\') -or
                $entry.FullName.Contains('/') -or
                $entry.FullName -in '.', '..') {
                throw "CPython embeddable archive has an unsafe or nested entry: $($entry.FullName)"
            }
        }
    }
    finally {
        $archive.Dispose()
    }
    [IO.Compression.ZipFile]::ExtractToDirectory($pythonArchive, $pythonRoot)
    $pythonExe = Join-Path $pythonRoot $policy.python.executable_relative_path
    $pythonLicense = Join-Path $pythonRoot $policy.python.license_relative_path
    if (-not (Test-Path -LiteralPath $pythonExe) -or
        -not (Test-Path -LiteralPath $pythonLicense) -or
        (Get-Sha256 $pythonExe) -cne $policy.python.executable_sha256) {
        throw 'CPython embeddable executable, license, or hash is invalid'
    }
    $pythonSignature = Get-AuthenticodeSignature -LiteralPath $pythonExe
    if ($pythonSignature.Status -ne [Management.Automation.SignatureStatus]::Valid -or
        $null -eq $pythonSignature.SignerCertificate -or
        $pythonSignature.SignerCertificate.Subject -cne $policy.python.signer_subject -or
        $pythonSignature.SignerCertificate.Thumbprint.ToUpperInvariant() -cne
            $policy.python.signer_thumbprint) {
        throw 'CPython executable does not carry the reviewed PSF Authenticode identity'
    }
    $observedPythonVersion = (& $pythonExe --version).Trim()
    if ($LASTEXITCODE -ne 0 -or
        $observedPythonVersion -cne "Python $($policy.python.version)") {
        throw 'CPython executable version does not match the reviewed policy'
    }
    $pthPath = Join-Path $pythonRoot 'python312._pth'
    $pthText = Get-Content -LiteralPath $pthPath -Raw
    if ($pthText -match '(?m)^\s*import\s+site\s*$') {
        throw 'CPython embeddable runtime unexpectedly enables ambient site packages'
    }
    $provenanceRoot = Join-Path $runtimeRoot 'provenance'
    [IO.Directory]::CreateDirectory($provenanceRoot) | Out-Null
    $sbomName = 'python-3.12.10-embed-amd64.zip.spdx.json'
    $sigstoreName = 'python-3.12.10-embed-amd64.zip.sigstore'
    Copy-Item -LiteralPath $pythonSbom -Destination (Join-Path $provenanceRoot $sbomName)
    Copy-Item -LiteralPath $pythonSigstore -Destination (Join-Path $provenanceRoot $sigstoreName)
    Copy-Item -LiteralPath $resolvedPolicyPath -Destination (
        Join-Path $runtimeRoot 'runtime-policy.json')

    $launcher = @'
param([Parameter(Mandatory)][ValidateSet('companion','describe','casting-describe')][string] $Action)
$ErrorActionPreference = 'Stop'
$env:RUSTY_HOSTESS_PRODUCT_CHANNEL = 'labs'
$root = Split-Path -Parent $PSScriptRoot
$runtime = Get-Content -LiteralPath (Join-Path $root 'runtime\python-runtime.json') -Raw | ConvertFrom-Json
$python = [IO.Path]::GetFullPath((Join-Path $root $runtime.executable_path.Replace('/', '\')))
$runtimeRoot = [IO.Path]::GetFullPath((Join-Path $root 'runtime')) + [IO.Path]::DirectorySeparatorChar
if (-not $python.StartsWith($runtimeRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw 'Bundled Python runtime path is absent or escapes the product root.'
}
$hash = (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()
$observed = (& $python -c "import sys;print('.'.join(map(str,sys.version_info[:3])))").Trim()
if ($LASTEXITCODE -ne 0 -or $runtime.version -cne '3.12.10' -or
    $observed -cne $runtime.version -or $hash -cne $runtime.executable_sha256) {
  throw 'Python runtime version/hash is not authorized.'
}
switch ($Action) {
  'companion' { & (Join-Path $root 'companion\HostessCompanion.Wpf.exe'); exit $LASTEXITCODE }
  'describe' { & $python -I (Join-Path $root 'source\tools\hostessctl\hostessctl.py') --help; exit $LASTEXITCODE }
  'casting-describe' {
    & $python -I (Join-Path $root 'source\tools\hostessctl\hostessctl.py') meta-quest-casting describe --out (Join-Path $env:LOCALAPPDATA 'RustyHostessLabs\reports\casting-descriptor.json')
    exit $LASTEXITCODE
  }
}
'@
    Write-Utf8 (Join-Path $stage 'bootstrap\hostess-labs.ps1') $launcher
    $runtime = [ordered]@{
        schema = 'rusty.hostess.bundled_python_runtime.v1'
        bundled = $true
        distribution = $policy.python.distribution
        version = $policy.python.version
        archive_sha256 = $policy.python.archive_sha256
        executable_path = 'runtime/python/python.exe'
        executable_sha256 = $policy.python.executable_sha256
        signer_subject = $policy.python.signer_subject
        signer_thumbprint = $policy.python.signer_thumbprint
        license_path = 'runtime/python/LICENSE.txt'
        sbom_path = "runtime/provenance/$sbomName"
        sigstore_path = "runtime/provenance/$sigstoreName"
        policy_path = 'runtime/runtime-policy.json'
        policy_sha256 = Get-Sha256 $resolvedPolicyPath
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
        schema = 'rusty.hostess.windows_complete_product.v3'
        product = 'rusty-hostess-labs'
        display_name = 'Rusty Hostess Labs'
        product_channel = 'labs'
        maturity = 'alpha'
        distribution_track = 'github-prerelease'
        prerelease = $true
        version = $Version
        release_tag = $ReleaseTag
        package_identity = 'rusty-hostess-labs'
        install_root = '%LOCALAPPDATA%\RustyHostessLabs'
        state_root = '%LOCALAPPDATA%\RustyHostessLabs\state'
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
            [ordered]@{ id='companion'; command='bootstrap/hostess-labs.ps1 companion'; arbitrary_arguments=$false },
            [ordered]@{ id='describe'; command='bootstrap/hostess-labs.ps1 describe'; arbitrary_arguments=$false },
            [ordered]@{ id='casting-describe'; command='bootstrap/hostess-labs.ps1 casting-describe'; arbitrary_arguments=$false }
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
            required = @('product_channel','version','source_revision','artifact_sha256','windows_version','device_class')
            prohibit = @('credentials','personal-data','device-serials','private-logs')
        }
        signing = [ordered]@{
            authenticode_policy = 'exact-owner-pin-with-chain-readback'
            signer_thumbprint = $ExpectedWpfSignerThumbprint
            signer_certificate_sha256 = $ExpectedWpfSignerCertificateSha256
            companion_executable_sha256 = $ExpectedWpfExecutableSha256
            timestamp_required = $true
            public_trust_claim = $false
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
        schema = 'rusty.hostess.windows_labs_release_metadata.v2'
        repository = 'MesmerPrism/rusty-hostess'
        product = 'rusty-hostess-labs'
        product_channel = 'labs'
        maturity = 'alpha'
        distribution_track = 'github-prerelease'
        prerelease = $true
        version = $Version
        tag = $ReleaseTag
        source = [ordered]@{
            revision = $SourceRevision
            tree = $SourceTree
        }
        installation_identity = 'rusty-hostess-labs'
        primary_artifact = [ordered]@{
            role = 'complete-product'
            name = "$name.zip"
            sha256 = $zipHash
            bytes = $zipBytes
        }
    }
    Write-Utf8 $releaseMetadataPath (
        ($releaseMetadata | ConvertTo-Json -Depth 10) + "`n")
    & (Join-Path $PSScriptRoot 'Test-HostessLabsReleaseMetadata.ps1') `
        -MetadataPath $releaseMetadataPath `
        -ZipPath $zipPath `
        -ExpectedVersion $Version `
        -ExpectedReleaseTag $ReleaseTag `
        -ExpectedSourceRevision $SourceRevision `
        -ExpectedSourceTree $SourceTree | Out-Null
    [ordered]@{
        schema='rusty.hostess.windows_labs_bundle_receipt.v1'
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
