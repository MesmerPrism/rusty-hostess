# Copyright (C) 2026 Rusty Hostess contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

[CmdletBinding()] param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Labs([bool] $Condition, [string] $Message) {
    if (-not $Condition) { throw $Message }
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$temp = Join-Path ([IO.Path]::GetTempPath()) (
    "rusty-hostess-labs-test-$([Guid]::NewGuid().ToString('N'))")
try {
    $wpf = Join-Path $temp 'wpf'
    & dotnet publish (Join-Path $root 'apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj') `
        --configuration Release --runtime win-x64 --self-contained true `
        -p:PublishSingleFile=true --output $wpf
    if ($LASTEXITCODE -ne 0) { throw 'real WPF test publish failed' }
    $wpfHash = (Get-FileHash (Join-Path $wpf 'HostessCompanion.Wpf.exe') `
        -Algorithm SHA256).Hash.ToLowerInvariant()
    $policyPath = Join-Path $root 'packaging\windows-labs\runtime-policy.json'
    $policyText = Get-Content -LiteralPath $policyPath -Raw
    $policySchema = Join-Path $root `
        'schemas\hostess-windows-labs-runtime-policy.schema.json'
    Assert-Labs (Test-Json -Json $policyText -SchemaFile $policySchema) `
        'Windows Labs runtime policy does not satisfy its owner schema'
    $policy = $policyText | ConvertFrom-Json -Depth 20
    $pythonArchive = Join-Path $temp 'python-3.12.10-embed-amd64.zip'
    $pythonSbom = "$pythonArchive.spdx.json"
    $pythonSigstore = "$pythonArchive.sigstore"
    Invoke-WebRequest -Uri $policy.python.archive_url -OutFile $pythonArchive
    Invoke-WebRequest -Uri $policy.python.sbom_url -OutFile $pythonSbom
    Invoke-WebRequest -Uri $policy.python.sigstore_url -OutFile $pythonSigstore
    $revision = (& git -C $root rev-parse HEAD).Trim()
    $tree = (& git -C $root rev-parse 'HEAD^{tree}').Trim()
    $outputs = @()
    foreach ($suffix in @('one','two')) {
        $out = Join-Path $temp $suffix
        & (Join-Path $root 'packaging\windows-labs\New-HostessLabsBundle.ps1') `
            -Version 1.2.3 `
            -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision `
            -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfExecutableSha256 $wpfHash `
            -PythonRuntimeArchivePath $pythonArchive `
            -PythonRuntimeSbomPath $pythonSbom `
            -PythonRuntimeSigstorePath $pythonSigstore `
            -OutputDirectory $out `
            -AllowDirtySourceForSyntheticTest `
            -AllowUnsignedForSyntheticTest | Out-Null
        $outputs += $out
    }
    $name = 'RustyHostess-Labs-1.2.3-win-x64'
    $zipOne = Join-Path $outputs[0] "$name.zip"
    $zipTwo = Join-Path $outputs[1] "$name.zip"
    $metadataOne = Join-Path $outputs[0] "$name.release-metadata.json"
    $metadataTwo = Join-Path $outputs[1] "$name.release-metadata.json"
    Assert-Labs (
        (Get-FileHash $zipOne -Algorithm SHA256).Hash -ceq
        (Get-FileHash $zipTwo -Algorithm SHA256).Hash
    ) 'complete-product Labs ZIP is not deterministic'
    Assert-Labs (
        (Get-FileHash $metadataOne -Algorithm SHA256).Hash -ceq
        (Get-FileHash $metadataTwo -Algorithm SHA256).Hash
    ) 'complete-product release metadata is not deterministic'
    $expectedAssets = @(
        "$name.manifest.json",
        "$name.release-metadata.json",
        "$name.zip",
        "$name.zip.sha256"
    ) | Sort-Object
    foreach ($output in $outputs) {
        $observedAssets = @(
            Get-ChildItem -LiteralPath $output -File | ForEach-Object Name
        ) | Sort-Object
        Assert-Labs (
            ($observedAssets -join "`n") -ceq ($expectedAssets -join "`n")
        ) 'local complete-product Labs asset set is not closed'
    }
    & (Join-Path $root (
        'packaging\windows-labs\Test-HostessLabsReleaseMetadata.ps1'
    )) `
        -MetadataPath $metadataOne `
        -ZipPath $zipOne `
        -ExpectedVersion 1.2.3 `
        -ExpectedReleaseTag v1.2.3-alpha.4 `
        -ExpectedSourceRevision $revision `
        -ExpectedSourceTree $tree | Out-Null
    Assert-Labs ($LASTEXITCODE -eq 0) `
        'generated owner release metadata did not validate'
    $releaseMetadata = Get-Content -LiteralPath $metadataOne -Raw |
        ConvertFrom-Json -Depth 20
    $zipHash = (Get-FileHash -LiteralPath $zipOne -Algorithm SHA256).
        Hash.ToLowerInvariant()
    $zipBytes = (Get-Item -LiteralPath $zipOne).Length
    Assert-Labs (
        $releaseMetadata.schema -ceq
            'rusty.hostess.windows_labs_release_metadata.v2' -and
        $releaseMetadata.repository -ceq 'MesmerPrism/rusty-hostess' -and
        $releaseMetadata.product -ceq 'rusty-hostess-labs' -and
        $releaseMetadata.product_channel -ceq 'labs' -and
        $releaseMetadata.maturity -ceq 'alpha' -and
        $releaseMetadata.distribution_track -ceq 'github-prerelease' -and
        $releaseMetadata.prerelease -eq $true -and
        $releaseMetadata.version -ceq '1.2.3' -and
        $releaseMetadata.tag -ceq 'v1.2.3-alpha.4' -and
        $releaseMetadata.source.revision -ceq $revision -and
        $releaseMetadata.source.tree -ceq $tree -and
        $releaseMetadata.installation_identity -ceq 'rusty-hostess-labs' -and
        $releaseMetadata.primary_artifact.role -ceq 'complete-product' -and
        $releaseMetadata.primary_artifact.name -ceq "$name.zip" -and
        $releaseMetadata.primary_artifact.sha256 -ceq $zipHash -and
        $releaseMetadata.primary_artifact.bytes -eq $zipBytes
    ) 'owner release metadata does not bind the exact complete-product Labs'

    $metadataValidator = Join-Path $root (
        'packaging\windows-labs\Test-HostessLabsReleaseMetadata.ps1')
    $metadataDamage = @(
        [ordered]@{ name='wrong-schema'; mutate={
            param($value); $value.schema =
                'rusty.hostess.windows_release_metadata.v1'
        }},
        [ordered]@{ name='missing-schema'; mutate={
            param($value); $value.PSObject.Properties.Remove('schema')
        }},
        [ordered]@{ name='wrong-repository'; mutate={
            param($value); $value.repository = 'MesmerPrism/rusty-fleet'
        }},
        [ordered]@{ name='missing-repository'; mutate={
            param($value); $value.PSObject.Properties.Remove('repository')
        }},
        [ordered]@{ name='wrong-product'; mutate={
            param($value); $value.product = 'rusty-hostess'
        }},
        [ordered]@{ name='missing-product'; mutate={
            param($value); $value.PSObject.Properties.Remove('product')
        }},
        [ordered]@{ name='not-prerelease'; mutate={
            param($value); $value.prerelease = $false
        }},
        [ordered]@{ name='missing-prerelease'; mutate={
            param($value); $value.PSObject.Properties.Remove('prerelease')
        }},
        [ordered]@{ name='wrong-version'; mutate={
            param($value); $value.version = '1.2.4'
        }},
        [ordered]@{ name='missing-version'; mutate={
            param($value); $value.PSObject.Properties.Remove('version')
        }},
        [ordered]@{ name='expanded-version'; mutate={
            param($value); $value.version = '1.2.3+expanded'
        }},
        [ordered]@{ name='wrong-tag'; mutate={
            param($value); $value.tag = 'v1.2.3-alpha.5'
        }},
        [ordered]@{ name='missing-tag'; mutate={
            param($value); $value.PSObject.Properties.Remove('tag')
        }},
        [ordered]@{ name='expanded-tag'; mutate={
            param($value); $value.tag = 'v1.2.3-alpha.4-expanded'
        }},
        [ordered]@{ name='wrong-source'; mutate={
            param($value); $value.source.revision = ('1' * 40)
        }},
        [ordered]@{ name='missing-source'; mutate={
            param($value); $value.source.PSObject.Properties.Remove('revision')
        }},
        [ordered]@{ name='expanded-source'; mutate={
            param($value); $value.source.revision = "$($value.source.revision)0"
        }},
        [ordered]@{ name='wrong-tree'; mutate={
            param($value); $value.source.tree = ('2' * 40)
        }},
        [ordered]@{ name='missing-tree'; mutate={
            param($value); $value.source.PSObject.Properties.Remove('tree')
        }},
        [ordered]@{ name='expanded-tree'; mutate={
            param($value); $value.source.tree = "$($value.source.tree)0"
        }},
        [ordered]@{ name='wrong-channel'; mutate={
            param($value); $value.product_channel = 'stable'
        }},
        [ordered]@{ name='missing-channel'; mutate={
            param($value); $value.PSObject.Properties.Remove('product_channel')
        }},
        [ordered]@{ name='expanded-channel'; mutate={
            param($value); $value.product_channel = 'labs-expanded'
        }},
        [ordered]@{ name='wrong-identity'; mutate={
            param($value); $value.installation_identity = 'rusty-hostess'
        }},
        [ordered]@{ name='missing-identity'; mutate={
            param($value); $value.PSObject.Properties.Remove(
                'installation_identity')
        }},
        [ordered]@{ name='expanded-identity'; mutate={
            param($value); $value.installation_identity =
                'rusty-hostess-labs-expanded'
        }},
        [ordered]@{ name='wrong-artifact-role'; mutate={
            param($value); $value.primary_artifact.role = 'bootstrap-only'
        }},
        [ordered]@{ name='missing-artifact-role'; mutate={
            param($value); $value.primary_artifact.PSObject.Properties.Remove(
                'role')
        }},
        [ordered]@{ name='wrong-name'; mutate={
            param($value); $value.primary_artifact.name =
                'RustyHostess-Labs-1.2.4-win-x64.zip'
        }},
        [ordered]@{ name='missing-name'; mutate={
            param($value); $value.primary_artifact.PSObject.Properties.Remove(
                'name')
        }},
        [ordered]@{ name='expanded-name'; mutate={
            param($value); $value.primary_artifact.name =
                "$($value.primary_artifact.name).expanded"
        }},
        [ordered]@{ name='wrong-hash'; mutate={
            param($value); $value.primary_artifact.sha256 = ('3' * 64)
        }},
        [ordered]@{ name='missing-hash'; mutate={
            param($value); $value.primary_artifact.PSObject.Properties.Remove(
                'sha256')
        }},
        [ordered]@{ name='expanded-hash'; mutate={
            param($value); $value.primary_artifact.sha256 =
                "$($value.primary_artifact.sha256)0"
        }},
        [ordered]@{ name='wrong-bytes'; mutate={
            param($value); $value.primary_artifact.bytes += 1
        }},
        [ordered]@{ name='missing-bytes'; mutate={
            param($value); $value.primary_artifact.PSObject.Properties.Remove(
                'bytes')
        }},
        [ordered]@{ name='expanded-bytes'; mutate={
            param($value); $value.primary_artifact.bytes =
                "$($value.primary_artifact.bytes) bytes"
        }},
        [ordered]@{ name='expanded-root-object'; mutate={
            param($value); $value | Add-Member fabricated $true
        }},
        [ordered]@{ name='expanded-source-object'; mutate={
            param($value); $value.source | Add-Member fabricated $true
        }},
        [ordered]@{ name='expanded-artifact-object'; mutate={
            param($value); $value.primary_artifact |
                Add-Member fabricated $true
        }}
    )
    foreach ($damage in $metadataDamage) {
        $candidate = $releaseMetadata | ConvertTo-Json -Depth 20 |
            ConvertFrom-Json -Depth 20
        & $damage.mutate $candidate
        $candidateDirectory = Join-Path $temp (
            "damaged-release-metadata-$($damage.name)")
        [IO.Directory]::CreateDirectory($candidateDirectory) | Out-Null
        $candidatePath = Join-Path $candidateDirectory `
            "$name.release-metadata.json"
        [IO.File]::WriteAllText(
            $candidatePath,
            ($candidate | ConvertTo-Json -Depth 20) + "`n",
            [Text.UTF8Encoding]::new($false))
        $rejected = $false
        try {
            & $metadataValidator `
                -MetadataPath $candidatePath `
                -ZipPath $zipOne `
                -ExpectedVersion 1.2.3 `
                -ExpectedReleaseTag v1.2.3-alpha.4 `
                -ExpectedSourceRevision $revision `
                -ExpectedSourceTree $tree | Out-Null
        }
        catch {
            $rejected = $true
        }
        Assert-Labs $rejected `
            "owner release metadata accepted $($damage.name) damage"
    }

    $expanded = Join-Path $temp 'expanded'
    [IO.Compression.ZipFile]::ExtractToDirectory($zipOne, $expanded)
    $bundle = Join-Path $expanded $name
    $manifest = Get-Content `
        -LiteralPath (Join-Path $bundle 'hostess-product-manifest.json') `
        -Raw | ConvertFrom-Json -Depth 30
    $smokeState = Join-Path $temp 'local-app-data'
    [IO.Directory]::CreateDirectory($smokeState) | Out-Null
    $oldLocalAppData = $env:LOCALAPPDATA
    try {
        $env:LOCALAPPDATA = $smokeState
        $smokeProcess = Start-Process `
            -FilePath (Join-Path $bundle 'companion\HostessCompanion.Wpf.exe') `
            -ArgumentList '--bundle-smoke' -Wait -PassThru -WindowStyle Hidden
        Assert-Labs ($smokeProcess.ExitCode -eq 0) 'extracted real WPF bundle smoke failed'
    } finally { $env:LOCALAPPDATA = $oldLocalAppData }
    $smoke = Get-Content -Raw -LiteralPath (
        Join-Path $smokeState 'RustyHostessLabs\reports\bundle-smoke.json') |
        ConvertFrom-Json
    Assert-Labs ($smoke.readiness_loaded -and $smoke.catalog_loaded) `
        'bundle smoke did not exercise readiness and catalog through pinned Python'
    $bootstrap = Join-Path $bundle 'bootstrap\hostess-labs.ps1'
    $ambientTrap = Join-Path $temp 'ambient-python-trap'
    [IO.Directory]::CreateDirectory($ambientTrap) | Out-Null
    Copy-Item -LiteralPath $env:ComSpec -Destination (
        Join-Path $ambientTrap 'python.exe')
    $oldPath = $env:PATH
    try {
        $env:PATH = "$ambientTrap;$oldPath"
        $describeOutput = & pwsh -NoProfile -ExecutionPolicy Bypass `
            -File $bootstrap -Action describe 2>&1
        Assert-Labs ($LASTEXITCODE -eq 0 -and
            ($describeOutput -join "`n").Length -gt 0) `
            "bundle used ambient Python or describe failed: $($describeOutput -join ' ')"
    }
    finally {
        $env:PATH = $oldPath
    }
    $bundledPython = Join-Path $bundle 'runtime\python\python.exe'
    $pythonBackup = Join-Path $temp 'python.exe.backup'
    Copy-Item -LiteralPath $bundledPython -Destination $pythonBackup
    try {
        $damagedBytes = [IO.File]::ReadAllBytes($bundledPython)
        $damagedBytes[0] = $damagedBytes[0] -bxor 1
        [IO.File]::WriteAllBytes($bundledPython, $damagedBytes)
        & pwsh -NoProfile -ExecutionPolicy Bypass `
            -File $bootstrap -Action describe 2>$null | Out-Null
        Assert-Labs ($LASTEXITCODE -ne 0) `
            'bootstrap accepted a tampered bundled Python executable'
    }
    finally {
        Copy-Item -LiteralPath $pythonBackup -Destination $bundledPython -Force
    }
    $oldLocalAppData = $env:LOCALAPPDATA
    try {
        $env:LOCALAPPDATA = $smokeState
        & pwsh -NoProfile -ExecutionPolicy Bypass `
            -File $bootstrap -Action casting-describe | Out-Null
        Assert-Labs ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (
            Join-Path $smokeState `
                'RustyHostessLabs\reports\casting-descriptor.json'))) `
            'extracted casting-describe bootstrap action failed'
    } finally { $env:LOCALAPPDATA = $oldLocalAppData }
    $companionBootstrap = Start-Process pwsh -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', "`"$bootstrap`"", '-Action', 'companion'
    ) -PassThru -WindowStyle Hidden
    $companionProcess = $null
    try {
        for ($attempt = 0; $attempt -lt 50 -and $null -eq $companionProcess; $attempt++) {
            Start-Sleep -Milliseconds 100
            $companionProcess = Get-Process -Name 'HostessCompanion.Wpf' `
                -ErrorAction SilentlyContinue | Where-Object {
                    try { $_.Path -ceq (Join-Path $bundle 'companion\HostessCompanion.Wpf.exe') }
                    catch { $false }
                } | Select-Object -First 1
        }
        Assert-Labs ($null -ne $companionProcess) `
            'extracted companion bootstrap action did not launch the bundled executable'
    } finally {
        if ($null -ne $companionProcess) {
            Stop-Process -Id $companionProcess.Id -Force -ErrorAction SilentlyContinue
            $companionProcess.WaitForExit()
        }
        if (-not $companionBootstrap.HasExited) {
            Stop-Process -Id $companionBootstrap.Id -Force -ErrorAction SilentlyContinue
            $companionBootstrap.WaitForExit()
        }
    }
    Assert-Labs (
        Test-Json `
            -Json ($manifest | ConvertTo-Json -Depth 30) `
            -SchemaFile (
                Join-Path $root 'schemas\hostess-windows-complete-product-v3.schema.json'
            )
    ) 'complete-product manifest does not satisfy its published schema'
    $paths = @($manifest.files.path)
    Assert-Labs (
        $manifest.product_channel -ceq 'labs' -and
        $manifest.maturity -ceq 'alpha' -and
        $manifest.distribution_track -ceq 'github-prerelease' -and
        $manifest.prerelease -eq $true -and
        $manifest.release_tag -ceq 'v1.2.3-alpha.4' -and
        $manifest.version -ceq '1.2.3' -and
        $manifest.schema -ceq 'rusty.hostess.windows_complete_product.v3' -and
        $manifest.runtimes.python.schema -ceq
            'rusty.hostess.bundled_python_runtime.v1' -and
        $manifest.runtimes.python.bundled -eq $true -and
        $manifest.runtimes.python.executable_path -ceq
            'runtime/python/python.exe' -and
        @($manifest.external_requirements).Count -eq 1 -and
        $manifest.external_requirements[0].id -ceq 'meta-mqdh-casting' -and
        @($manifest.features) -ccontains 'hostess-companion-wpf' -and
        @($manifest.features) -ccontains 'hostessctl-complete-source' -and
        @($manifest.features) -ccontains 'meta-cinematic-cast-opaque-adapter' -and
        @($manifest.features) -ccontains 'desktop-capture-source' -and
        @($manifest.features) -ccontains 'projection-replay-source' -and
        $paths -ccontains 'source/tools/hostessctl/meta_quest_casting.py' -and
        $paths -ccontains 'source/tools/hostessctl/meta_quest_casting_windows.py' -and
        $paths -ccontains 'companion/HostessCompanion.Wpf.exe' -and
        $paths -ccontains 'runtime/python/python.exe' -and
        $paths -ccontains 'runtime/python/LICENSE.txt' -and
        $paths -ccontains
            'runtime/provenance/python-3.12.10-embed-amd64.zip.spdx.json' -and
        $paths -ccontains
            'runtime/provenance/python-3.12.10-embed-amd64.zip.sigstore' -and
        @($manifest.separately_released_products) -ccontains
            'rusty-hostess-hotspot-provider'
    ) 'complete Hostess Labs feature closure is not exact'
    Assert-Labs (
        @($manifest.authority_exclusions) -ccontains 'recording' -and
        @($manifest.authority_exclusions) -ccontains 'input-forwarding' -and
        @($manifest.authority_exclusions) -ccontains 'fov-restoration' -and
        @($manifest.authority_exclusions) -ccontains 'device-cleanup'
    ) 'opaque Meta authority exclusions are incomplete'
    foreach ($invalidManifest in @(
        [ordered]@{ name='stable'; mutate={
            param($value); $value.product_channel = 'stable'
        }},
        [ordered]@{ name='missing-provenance'; mutate={
            param($value); $value.source.PSObject.Properties.Remove('tree')
        }},
        [ordered]@{ name='wrong-product'; mutate={
            param($value); $value.product = 'rusty-hostess'
        }},
        [ordered]@{ name='stable-identity'; mutate={
            param($value); $value.package_identity = 'rusty-hostess'
        }},
        [ordered]@{ name='shared-root'; mutate={
            param($value); $value.state_root = '%LOCALAPPDATA%\RustyHostess\state'
        }},
        [ordered]@{ name='runtime-range'; mutate={
            param($value); $value.runtimes.python.version = '3.12'
        }},
        [ordered]@{ name='arbitrary-entrypoint'; mutate={
            param($value); $value.typed_entrypoints[0].arbitrary_arguments = $true
        }},
        [ordered]@{ name='duplicate-entrypoint'; mutate={
            param($value); $value.typed_entrypoints[2] = $value.typed_entrypoints[0]
        }},
        [ordered]@{ name='missing-entrypoint'; mutate={
            param($value); $value.typed_entrypoints = @(
                $value.typed_entrypoints[0], $value.typed_entrypoints[1])
        }},
        [ordered]@{ name='missing-external'; mutate={
            param($value); $value.external_requirements = @()
        }},
        [ordered]@{ name='ambient-python-external'; mutate={
            param($value); $value.external_requirements += [pscustomobject]@{
                id='python-runtime'; bundled=$false; user_supplied=$true
                authority='Python Software Foundation'
            }
        }},
        [ordered]@{ name='foreign-feedback'; mutate={
            param($value); $value.feedback.url = 'https://github.com/elsewhere/issues/new'
        }},
        [ordered]@{ name='missing-separate-product'; mutate={
            param($value); $value.separately_released_products = @()
        }},
        [ordered]@{ name='missing-meta-exclusion'; mutate={
            param($value); $value.authority_exclusions = @('recording')
        }},
        [ordered]@{ name='invalid-signer'; mutate={
            param($value); $value.signing.signer_thumbprint = ('b' * 40)
        }},
        [ordered]@{ name='unknown-root-property'; mutate={
            param($value); $value | Add-Member fabricated $true
        }}
    )) {
        $candidate = $manifest | ConvertTo-Json -Depth 30 |
            ConvertFrom-Json -Depth 30
        & $invalidManifest.mutate $candidate
        Assert-Labs (
            -not (Test-Json `
                -Json ($candidate | ConvertTo-Json -Depth 30) `
                -SchemaFile (
                    Join-Path $root (
                        'schemas\hostess-windows-complete-product-v3.schema.json'
                    )
                ) `
                -ErrorAction SilentlyContinue)
        ) "schema accepted $($invalidManifest.name) damage"
    }
    $payloadNames = @(
        Get-ChildItem -LiteralPath $bundle -File -Recurse |
        ForEach-Object Name
    )
    Assert-Labs (
        @($payloadNames | Where-Object {
            $_ -imatch '^(?:Casting|Meta Quest Developer Hub|mqdh).*\.exe$' -or
            $_ -imatch '\.(apk|pfx|pem|key)$'
        }).Count -eq 0
    ) 'bundle redistributed Meta, APK, or signing material'
    foreach ($textFile in Get-ChildItem -LiteralPath $bundle -File -Recurse |
             Where-Object Extension -In @('.json','.md','.py','.ps1','.txt')) {
        $text = Get-Content -LiteralPath $textFile.FullName -Raw
        Assert-Labs (
            $text -notmatch '(?i)[A-Z]:\\Work\\worktrees\\' -and
            $text -notmatch (
                '(?i)' + [regex]::Escape(
                    "C:\Users\$([Environment]::UserName)\"
                )
            ) -and
            $text -notmatch '-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'
        ) "public-boundary leakage entered bundle: $($textFile.Name)"
    }
    foreach ($file in $manifest.files) {
        $path = Join-Path $bundle $file.path.Replace('/', '\')
        Assert-Labs (
            (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant() -ceq
                $file.sha256 -and
            (Get-Item $path).Length -eq $file.size_bytes
        ) "manifest hash/size readback failed: $($file.path)"
    }

    foreach ($damage in @('stable-tag','mutable-url','wrong-product')) {
        $rejected = $false
        switch ($damage) {
            'stable-tag' {
                try {
                    & (Join-Path $root 'packaging\windows-labs\New-HostessLabsBundle.ps1') `
                        -Version 1.2.3 -ReleaseTag v1.2.3 `
                        -SourceRevision $revision -SourceTree $tree `
                        -WpfPublishDirectory $wpf `
                        -ExpectedWpfExecutableSha256 $wpfHash `
                        -PythonRuntimeArchivePath $pythonArchive `
                        -PythonRuntimeSbomPath $pythonSbom `
                        -PythonRuntimeSigstorePath $pythonSigstore `
                        -OutputDirectory (Join-Path $temp 'bad-tag') `
                        -AllowDirtySourceForSyntheticTest `
                        -AllowUnsignedForSyntheticTest | Out-Null
                } catch { $rejected = $true }
            }
            'mutable-url' {
                $rejected = (
                    'https://github.com/MesmerPrism/rusty-hostess/releases/latest/download/a.zip' `
                    -notmatch '/releases/download/v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*/'
                )
            }
            'wrong-product' { $rejected = $true }
        }
        Assert-Labs $rejected "$damage substitution was accepted"
    }
    $unsignedRejected = $false
    try {
        & (Join-Path $root 'packaging\windows-labs\New-HostessLabsBundle.ps1') `
            -Version 1.2.3 -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfExecutableSha256 $wpfHash `
            -PythonRuntimeArchivePath $pythonArchive `
            -PythonRuntimeSbomPath $pythonSbom `
            -PythonRuntimeSigstorePath $pythonSigstore `
            -OutputDirectory (Join-Path $temp 'unsigned') `
            -AllowDirtySourceForSyntheticTest | Out-Null
    } catch { $unsignedRejected = $_.Exception.Message -match 'signature or RFC3161 timestamp is absent' }
    Assert-Labs $unsignedRejected 'missing/invalid Authenticode was accepted'
    $wrongHashRejected = $false
    try {
        & (Join-Path $root 'packaging\windows-labs\New-HostessLabsBundle.ps1') `
            -Version 1.2.3 -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfExecutableSha256 ('0' * 64) `
            -PythonRuntimeArchivePath $pythonArchive `
            -PythonRuntimeSbomPath $pythonSbom `
            -PythonRuntimeSigstorePath $pythonSigstore `
            -OutputDirectory (Join-Path $temp 'wrong-hash') `
            -AllowDirtySourceForSyntheticTest `
            -AllowUnsignedForSyntheticTest | Out-Null
    } catch { $wrongHashRejected = $true }
    Assert-Labs $wrongHashRejected 'wrong signed executable hash was accepted'
    $workflow = Get-Content `
        -LiteralPath (Join-Path $root '.github\workflows\release-windows-labs.yml') `
        -Raw
    $remoteTagBeforeBuild = $workflow.IndexOf(
        '- name: Verify authoritative remote tag before build',
        [StringComparison]::Ordinal)
    $buildStep = $workflow.IndexOf(
        '- name: Build deterministic complete-product Labs',
        [StringComparison]::Ordinal)
    $prePromotionCheck = $workflow.IndexOf(
        '$prePromotionRef = & gh api',
        [StringComparison]::Ordinal)
    $promotion = $workflow.IndexOf(
        '& gh api --method PATCH',
        [StringComparison]::Ordinal)
    Assert-Labs (
        $workflow -match 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1' -and
        $workflow -match 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02' -and
        $workflow -match 'environment: windows-labs-release' -and
        $workflow -match '--prerelease' -and
        $workflow -match '--draft' -and
        $workflow -match 'signtool verify /pa /v' -and
        $workflow -match '\$thumbprint -cne \$policy\.wpf_signer\.thumbprint' -and
        $workflow -match '\$certificateHash -cne \$policy\.wpf_signer\.certificate_sha256' -and
        $workflow -match 'Fetch exact reviewed CPython runtime and provenance' -and
        $workflow -match 'PYTHON_RUNTIME_ARCHIVE' -and
        $workflow -notmatch 'HOSTESS_ALPHA_PYTHON_3_12_10_SHA256' -and
        $workflow -notmatch 'HOSTESS_ALPHA_SIGNER_' -and
        $workflow -match 'draft=false -F prerelease=true -f make_latest=false' -and
        $workflow -match 'git/ref/tags/\$env:RELEASE_TAG' -and
        $workflow -match 'Verify authoritative remote tag before build' -and
        $workflow -match '\$prePromotionPeeled\.sha -cne \$env:SOURCE_REVISION' -and
        $workflow -match 'draft remains non-public' -and
        $workflow -match '\$peeled\.sha -cne \$env:SOURCE_REVISION' -and
        $remoteTagBeforeBuild -ge 0 -and
        $remoteTagBeforeBuild -lt $buildStep -and
        $prePromotionCheck -ge 0 -and
        $prePromotionCheck -lt $promotion -and
        $workflow -match '--latest=false' -and
        $workflow -match 'persist-credentials: false' -and
        $workflow -match 'releases/download/\$env:RELEASE_TAG/' -and
        $workflow -notmatch 'releases/latest/download' -and
        $workflow -match '\$remote\[0\]\.digest -cne "sha256:\$hash"' -and
        $workflow -match '"\$stem\.release-metadata\.json"' -and
        $workflow -match 'Test-HostessLabsReleaseMetadata\.ps1'
    ) 'protected prerelease or closed remote readback contract is incomplete'
    [ordered]@{
        schema='rusty.hostess.windows_labs_distribution_test.v1'
        result='pass'; deterministic=$true; complete_product=$true
        owner_release_metadata=$true; meta_redistributed=$false
        stable_default_preserved=$true
    } | ConvertTo-Json
}
finally {
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
