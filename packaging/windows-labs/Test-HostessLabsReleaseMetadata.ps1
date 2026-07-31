# Copyright (C) 2026 Rusty Hostess contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $MetadataPath,
    [Parameter(Mandatory)][string] $ZipPath,
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+$')]
    [string] $ExpectedVersion,
    [Parameter(Mandatory)]
    [ValidatePattern('^v[0-9]+\.[0-9]+\.[0-9]+-alpha\.[1-9][0-9]*$')]
    [string] $ExpectedReleaseTag,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')]
    [string] $ExpectedSourceRevision,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')]
    [string] $ExpectedSourceTree
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition([bool] $Condition, [string] $Message) {
    if (-not $Condition) {
        throw $Message
    }
}

function Assert-ExactObject(
    [Text.Json.JsonElement] $Element,
    [string[]] $ExpectedNames,
    [string] $Scope
) {
    Assert-Condition ($Element.ValueKind -eq [Text.Json.JsonValueKind]::Object) `
        "$Scope must be a JSON object"
    $observed = @($Element.EnumerateObject() | ForEach-Object Name)
    $observedKey = (@($observed | Sort-Object -CaseSensitive) -join "`u{001f}")
    $expectedKey = (@($ExpectedNames | Sort-Object -CaseSensitive) -join "`u{001f}")
    Assert-Condition (
        $observed.Count -eq $ExpectedNames.Count -and
        $observedKey -ceq $expectedKey
    ) "$Scope property set is not exact"
}

function Get-ExactString(
    [Text.Json.JsonElement] $Element,
    [string] $Name,
    [string] $Expected,
    [string] $Scope
) {
    $property = $Element.GetProperty($Name)
    Assert-Condition ($property.ValueKind -eq [Text.Json.JsonValueKind]::String) `
        "$Scope.$Name must be a string"
    $value = $property.GetString()
    Assert-Condition ($value -ceq $Expected) "$Scope.$Name does not match"
}

$metadata = (Resolve-Path -LiteralPath $MetadataPath).Path
$zip = (Resolve-Path -LiteralPath $ZipPath).Path
$tagVersion = $ExpectedReleaseTag -replace `
    '^v([0-9]+\.[0-9]+\.[0-9]+)-alpha\.[1-9][0-9]*$', '$1'
Assert-Condition ($tagVersion -ceq $ExpectedVersion) `
    'expected release tag and version differ'

$name = "RustyHostess-Labs-$ExpectedVersion-win-x64"
Assert-Condition (
    (Split-Path -Leaf $metadata) -ceq "$name.release-metadata.json"
) 'release metadata asset name does not match the expected version'
Assert-Condition (
    (Split-Path -Leaf $zip) -ceq "$name.zip"
) 'complete-product ZIP name does not match the expected version'

$document = $null
try {
    $document = [Text.Json.JsonDocument]::Parse(
        [IO.File]::ReadAllText($metadata),
        [Text.Json.JsonDocumentOptions]::new())
    $root = $document.RootElement
    Assert-ExactObject $root @(
        'schema',
        'repository',
        'product',
        'product_channel',
        'maturity',
        'distribution_track',
        'prerelease',
        'version',
        'tag',
        'source',
        'installation_identity',
        'primary_artifact'
    ) '$'
    Get-ExactString $root 'schema' `
        'rusty.hostess.windows_labs_release_metadata.v2' '$'
    Get-ExactString $root 'repository' 'MesmerPrism/rusty-hostess' '$'
    Get-ExactString $root 'product' 'rusty-hostess-labs' '$'
    Get-ExactString $root 'product_channel' 'labs' '$'
    Get-ExactString $root 'maturity' 'alpha' '$'
    Get-ExactString $root 'distribution_track' 'github-prerelease' '$'
    $prerelease = $root.GetProperty('prerelease')
    Assert-Condition (
        $prerelease.ValueKind -eq [Text.Json.JsonValueKind]::True
    ) '$.prerelease must be true'
    Get-ExactString $root 'version' $ExpectedVersion '$'
    Get-ExactString $root 'tag' $ExpectedReleaseTag '$'
    Get-ExactString $root 'installation_identity' 'rusty-hostess-labs' '$'

    $source = $root.GetProperty('source')
    Assert-ExactObject $source @('revision', 'tree') '$.source'
    Get-ExactString $source 'revision' $ExpectedSourceRevision '$.source'
    Get-ExactString $source 'tree' $ExpectedSourceTree '$.source'

    $artifact = $root.GetProperty('primary_artifact')
    Assert-ExactObject $artifact @('role', 'name', 'sha256', 'bytes') `
        '$.primary_artifact'
    Get-ExactString $artifact 'role' 'complete-product' `
        '$.primary_artifact'
    Get-ExactString $artifact 'name' "$name.zip" '$.primary_artifact'
    $zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).
        Hash.ToLowerInvariant()
    Get-ExactString $artifact 'sha256' $zipHash '$.primary_artifact'
    $bytesProperty = $artifact.GetProperty('bytes')
    Assert-Condition (
        $bytesProperty.ValueKind -eq [Text.Json.JsonValueKind]::Number
    ) '$.primary_artifact.bytes must be an integer'
    $bytes = $bytesProperty.GetInt64()
    Assert-Condition ($bytes -gt 0 -and $bytes -eq (Get-Item $zip).Length) `
        '$.primary_artifact.bytes does not match the complete-product ZIP'

    [ordered]@{
        schema = 'rusty.hostess.windows_labs_release_metadata_validation.v1'
        result = 'pass'
        metadata_sha256 = (
            Get-FileHash -LiteralPath $metadata -Algorithm SHA256
        ).Hash.ToLowerInvariant()
        primary_artifact_sha256 = $zipHash
        primary_artifact_bytes = $bytes
    } | ConvertTo-Json
}
finally {
    if ($null -ne $document) {
        $document.Dispose()
    }
}
