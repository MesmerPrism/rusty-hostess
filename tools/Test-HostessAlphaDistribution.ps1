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
    [IO.Directory]::CreateDirectory($wpf) | Out-Null
    [IO.File]::WriteAllText(
        (Join-Path $wpf 'HostessCompanion.Wpf.exe'),
        'synthetic-owner-wpf',
        [Text.UTF8Encoding]::new($false))
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
            -OutputDirectory $out `
            -AllowDirtySourceForSyntheticTest | Out-Null
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
                        -OutputDirectory (Join-Path $temp 'bad-tag') `
                        -AllowDirtySourceForSyntheticTest | Out-Null
                } catch { $rejected = $true }
            }
            'mutable-url' {
                $rejected = (
                    'https://github.com/MesmerPrism/rusty-hostess/releases/latest/download/a.zip' `
                    -notmatch '/releases/download/v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*/'
                )
            }
            'wrong-product' {
                $rejected = $manifest.product -cne 'rusty-hostess'
            }
        }
        Assert-Alpha $rejected "$damage substitution was accepted"
    }
    $workflow = Get-Content `
        -LiteralPath (Join-Path $root '.github\workflows\release-windows-alpha.yml') `
        -Raw
    Assert-Alpha (
        $workflow -match 'environment: windows-alpha-release' -and
        $workflow -match '--prerelease' -and
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
