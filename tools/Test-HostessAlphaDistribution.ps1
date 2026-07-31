# Copyright (C) 2026 Rusty Hostess contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

[CmdletBinding()] param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Alpha([bool] $Condition, [string] $Message) {
    if (-not $Condition) { throw $Message }
}

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$temp = Join-Path ([IO.Path]::GetTempPath()) (
    "rusty-hostess-alpha-test-$([Guid]::NewGuid().ToString('N'))")
try {
    $wpf = Join-Path $temp 'wpf'
    & dotnet publish (Join-Path $root 'apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj') `
        --configuration Release --runtime win-x64 --self-contained true `
        -p:PublishSingleFile=true --output $wpf
    if ($LASTEXITCODE -ne 0) { throw 'real WPF test publish failed' }
    $wpfHash = (Get-FileHash (Join-Path $wpf 'HostessCompanion.Wpf.exe') `
        -Algorithm SHA256).Hash.ToLowerInvariant()
    $pythonPath = @(& where.exe python.exe | Where-Object {
        try { (& $_ --version 2>$null) -ceq 'Python 3.12.10' } catch { $false }
    })[0]
    $pythonHash = (Get-FileHash $pythonPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Assert-Alpha ((& $pythonPath --version) -ceq 'Python 3.12.10') `
        'focused alpha smoke requires the pinned Python 3.12.10 test runtime'
    $syntheticThumbprint = 'A' * 40
    $syntheticCertificateHash = 'b' * 64
    $revision = (& git -C $root rev-parse HEAD).Trim()
    $tree = (& git -C $root rev-parse 'HEAD^{tree}').Trim()
    $outputs = @()
    foreach ($suffix in @('one','two')) {
        $out = Join-Path $temp $suffix
        & (Join-Path $root 'packaging\windows-alpha\New-HostessAlphaBundle.ps1') `
            -Version 1.2.3 `
            -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision `
            -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfSignerThumbprint $syntheticThumbprint `
            -ExpectedWpfSignerCertificateSha256 $syntheticCertificateHash `
            -ExpectedWpfExecutableSha256 $wpfHash `
            -PythonExecutableSha256 $pythonHash `
            -OutputDirectory $out `
            -AllowDirtySourceForSyntheticTest `
            -AllowUnsignedForSyntheticTest | Out-Null
        $outputs += $out
    }
    $name = 'RustyHostess-Alpha-1.2.3-win-x64'
    $zipOne = Join-Path $outputs[0] "$name.zip"
    $zipTwo = Join-Path $outputs[1] "$name.zip"
    Assert-Alpha (
        (Get-FileHash $zipOne -Algorithm SHA256).Hash -ceq
        (Get-FileHash $zipTwo -Algorithm SHA256).Hash
    ) 'complete-product alpha ZIP is not deterministic'

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
        Assert-Alpha ($smokeProcess.ExitCode -eq 0) 'extracted real WPF bundle smoke failed'
    } finally { $env:LOCALAPPDATA = $oldLocalAppData }
    $smoke = Get-Content -Raw -LiteralPath (
        Join-Path $smokeState 'RustyHostessAlpha\reports\bundle-smoke.json') |
        ConvertFrom-Json
    Assert-Alpha ($smoke.readiness_loaded -and $smoke.catalog_loaded) `
        'bundle smoke did not exercise readiness and catalog through pinned Python'
    $bootstrap = Join-Path $bundle 'bootstrap\hostess-alpha.ps1'
    $describeOutput = & pwsh -NoProfile -ExecutionPolicy Bypass `
        -File $bootstrap -Action describe 2>&1
    Assert-Alpha ($LASTEXITCODE -eq 0 -and
        ($describeOutput -join "`n").Length -gt 0) `
        "extracted describe bootstrap action failed: $($describeOutput -join ' ')"
    $oldLocalAppData = $env:LOCALAPPDATA
    try {
        $env:LOCALAPPDATA = $smokeState
        & pwsh -NoProfile -ExecutionPolicy Bypass `
            -File $bootstrap -Action casting-describe | Out-Null
        Assert-Alpha ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (
            Join-Path $smokeState `
                'RustyHostessAlpha\reports\casting-descriptor.json'))) `
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
        Assert-Alpha ($null -ne $companionProcess) `
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
    Assert-Alpha (
        Test-Json `
            -Json ($manifest | ConvertTo-Json -Depth 30) `
            -SchemaFile (
                Join-Path $root 'schemas\hostess-windows-complete-product.schema.json'
            )
    ) 'complete-product manifest does not satisfy its published schema'
    $paths = @($manifest.files.path)
    Assert-Alpha (
        $manifest.channel -ceq 'alpha' -and
        $manifest.prerelease -eq $true -and
        $manifest.release_tag -ceq 'v1.2.3-alpha.4' -and
        $manifest.version -ceq '1.2.3' -and
        @($manifest.features) -ccontains 'hostess-companion-wpf' -and
        @($manifest.features) -ccontains 'hostessctl-complete-source' -and
        @($manifest.features) -ccontains 'meta-cinematic-cast-opaque-adapter' -and
        @($manifest.features) -ccontains 'desktop-capture-source' -and
        @($manifest.features) -ccontains 'projection-replay-source' -and
        $paths -ccontains 'source/tools/hostessctl/meta_quest_casting.py' -and
        $paths -ccontains 'source/tools/hostessctl/meta_quest_casting_windows.py' -and
        $paths -ccontains 'companion/HostessCompanion.Wpf.exe' -and
        @($manifest.separately_released_products) -ccontains
            'rusty-hostess-hotspot-provider'
    ) 'complete Hostess alpha feature closure is not exact'
    Assert-Alpha (
        @($manifest.authority_exclusions) -ccontains 'recording' -and
        @($manifest.authority_exclusions) -ccontains 'input-forwarding' -and
        @($manifest.authority_exclusions) -ccontains 'fov-restoration' -and
        @($manifest.authority_exclusions) -ccontains 'device-cleanup'
    ) 'opaque Meta authority exclusions are incomplete'
    foreach ($invalidManifest in @(
        [ordered]@{ name='stable'; mutate={
            param($value); $value.channel = 'stable'
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
        [ordered]@{ name='duplicate-external'; mutate={
            param($value); $value.external_requirements[1] =
                $value.external_requirements[0]
        }},
        [ordered]@{ name='missing-python-external'; mutate={
            param($value); $value.external_requirements = @(
                $value.external_requirements[0])
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
        Assert-Alpha (
            -not (Test-Json `
                -Json ($candidate | ConvertTo-Json -Depth 30) `
                -SchemaFile (
                    Join-Path $root (
                        'schemas\hostess-windows-complete-product.schema.json'
                    )
                ) `
                -ErrorAction SilentlyContinue)
        ) "schema accepted $($invalidManifest.name) damage"
    }
    $payloadNames = @(
        Get-ChildItem -LiteralPath $bundle -File -Recurse |
        ForEach-Object Name
    )
    Assert-Alpha (
        @($payloadNames | Where-Object {
            $_ -imatch '^(?:Casting|Meta Quest Developer Hub|mqdh).*\.exe$' -or
            $_ -imatch '\.(apk|pfx|pem|key)$'
        }).Count -eq 0
    ) 'bundle redistributed Meta, APK, or signing material'
    foreach ($textFile in Get-ChildItem -LiteralPath $bundle -File -Recurse |
             Where-Object Extension -In @('.json','.md','.py','.ps1','.txt')) {
        $text = Get-Content -LiteralPath $textFile.FullName -Raw
        Assert-Alpha (
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
        Assert-Alpha (
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
                    & (Join-Path $root 'packaging\windows-alpha\New-HostessAlphaBundle.ps1') `
                        -Version 1.2.3 -ReleaseTag v1.2.3 `
                        -SourceRevision $revision -SourceTree $tree `
                        -WpfPublishDirectory $wpf `
                        -ExpectedWpfSignerThumbprint $syntheticThumbprint `
                        -ExpectedWpfSignerCertificateSha256 $syntheticCertificateHash `
                        -ExpectedWpfExecutableSha256 $wpfHash `
                        -PythonExecutableSha256 $pythonHash `
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
        Assert-Alpha $rejected "$damage substitution was accepted"
    }
    $unsignedRejected = $false
    try {
        & (Join-Path $root 'packaging\windows-alpha\New-HostessAlphaBundle.ps1') `
            -Version 1.2.3 -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfSignerThumbprint $syntheticThumbprint `
            -ExpectedWpfSignerCertificateSha256 $syntheticCertificateHash `
            -ExpectedWpfExecutableSha256 $wpfHash `
            -PythonExecutableSha256 $pythonHash `
            -OutputDirectory (Join-Path $temp 'unsigned') `
            -AllowDirtySourceForSyntheticTest | Out-Null
    } catch { $unsignedRejected = $_.Exception.Message -match 'signature is absent or invalid' }
    Assert-Alpha $unsignedRejected 'missing/invalid Authenticode was accepted'
    $wrongHashRejected = $false
    try {
        & (Join-Path $root 'packaging\windows-alpha\New-HostessAlphaBundle.ps1') `
            -Version 1.2.3 -ReleaseTag v1.2.3-alpha.4 `
            -SourceRevision $revision -SourceTree $tree `
            -WpfPublishDirectory $wpf `
            -ExpectedWpfSignerThumbprint $syntheticThumbprint `
            -ExpectedWpfSignerCertificateSha256 $syntheticCertificateHash `
            -ExpectedWpfExecutableSha256 ('0' * 64) `
            -PythonExecutableSha256 $pythonHash `
            -OutputDirectory (Join-Path $temp 'wrong-hash') `
            -AllowDirtySourceForSyntheticTest `
            -AllowUnsignedForSyntheticTest | Out-Null
    } catch { $wrongHashRejected = $true }
    Assert-Alpha $wrongHashRejected 'wrong signed executable hash was accepted'
    $workflow = Get-Content `
        -LiteralPath (Join-Path $root '.github\workflows\release-windows-alpha.yml') `
        -Raw
    $remoteTagBeforeBuild = $workflow.IndexOf(
        '- name: Verify authoritative remote tag before build',
        [StringComparison]::Ordinal)
    $buildStep = $workflow.IndexOf(
        '- name: Build deterministic complete-product alpha',
        [StringComparison]::Ordinal)
    $prePromotionCheck = $workflow.IndexOf(
        '$prePromotionRef = & gh api',
        [StringComparison]::Ordinal)
    $promotion = $workflow.IndexOf(
        '& gh api --method PATCH',
        [StringComparison]::Ordinal)
    Assert-Alpha (
        $workflow -match 'environment: windows-alpha-release' -and
        $workflow -match '--prerelease' -and
        $workflow -match '--draft' -and
        $workflow -match 'signtool verify /pa /v' -and
        $workflow -match '\$thumbprint -cne \$env:EXPECTED_SIGNER_THUMBPRINT' -and
        $workflow -match '\$certificateHash -cne \$env:EXPECTED_SIGNER_CERT_SHA256' -and
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
        $workflow -match '\$remote\[0\]\.digest -cne "sha256:\$hash"'
    ) 'protected prerelease or closed remote readback contract is incomplete'
    [ordered]@{
        schema='rusty.hostess.windows_alpha_distribution_test.v1'
        result='pass'; deterministic=$true; complete_product=$true
        meta_redistributed=$false; stable_default_preserved=$true
    } | ConvertTo-Json
}
finally {
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
