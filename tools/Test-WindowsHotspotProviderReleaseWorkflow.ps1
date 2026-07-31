#requires -Version 7.0
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$workflowPath = Join-Path $repoRoot `
    ".github\workflows\windows-hotspot-provider-release.yml"
if (-not (Test-Path -LiteralPath $workflowPath -PathType Leaf)) {
    throw "Windows hotspot provider release workflow is missing."
}
$workflow = Get-Content -Raw -LiteralPath $workflowPath

function Assert-WorkflowContains {
    param(
        [Parameter(Mandatory)][string] $Pattern,
        [Parameter(Mandatory)][string] $Message
    )
    if ($workflow -cnotmatch $Pattern) {
        throw $Message
    }
}

foreach ($requirement in @(
    @{
        Pattern = 'actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1'
        Message = "Release workflow must pin checkout to the reviewed immutable revision."
    },
    @{
        Pattern = 'actions/setup-dotnet@26b0ec14cb23fa6904739307f278c14f94c95bf1'
        Message = "Release workflow must pin setup-dotnet to the reviewed immutable revision."
    },
    @{
        Pattern = 'actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a'
        Message = "Release workflow must pin upload-artifact to the reviewed immutable revision."
    },
    @{
        Pattern = '(?m)^\s+- "windows-hotspot-provider-v\*"\s*$'
        Message = "Release workflow must be restricted to provider-owned version tags."
    },
    @{
        Pattern = '(?m)^\s+environment: windows-hotspot-provider-release\s*$'
        Message = "Release workflow must use the protected provider release environment."
    },
    @{
        Pattern = 'secrets\.RUSTY_HOSTESS_AUTHENTICODE_PFX_BASE64'
        Message = "Release workflow must require protected Authenticode PFX input."
    },
    @{
        Pattern = 'secrets\.RUSTY_HOSTESS_AUTHENTICODE_PFX_PASSWORD'
        Message = "Release workflow must require the protected PFX password."
    },
    @{
        Pattern = 'vars\.RUSTY_HOSTESS_AUTHENTICODE_SIGNER_THUMBPRINT'
        Message = "Release workflow must independently supply the authorized signer thumbprint."
    },
    @{
        Pattern = 'secrets\.RUSTY_HOSTESS_RELEASE_POLICY_TOKEN'
        Message = "Release workflow must require protected immutable-release policy readback."
    },
    @{
        Pattern = '(?m)^\s+persist-credentials: false\s*$'
        Message = "Release checkout must not retain write credentials."
    },
    @{
        Pattern = '(?m)^\s+cancel-in-progress: false\s*$'
        Message = "A release attempt must not be cancelled by a concurrent retry."
    },
    @{
        Pattern = '\$tagRevision -cne \$headRevision'
        Message = "Release workflow must bind the existing tag to the checked-out commit."
    },
    @{
        Pattern = 'Set-AuthenticodeSignature'
        Message = "Release workflow must Authenticode-sign the owner executable."
    },
    @{
        Pattern = '-BuildKind signed-release'
        Message = "Release workflow must issue signed-release provenance."
    },
    @{
        Pattern = '-VerifyPublicSource'
        Message = "Release workflow must verify exact source availability."
    },
    @{
        Pattern = '-AllowedSignerThumbprint \$env:SIGNER_THUMBPRINT'
        Message = "Provenance generation must use the independent signer thumbprint."
    },
    @{
        Pattern = '-RequireSignedRelease'
        Message = "Release workflow must fail closed through signed-release validation."
    },
    @{
        Pattern = '-ExpectedSignerThumbprint \$env:SIGNER_THUMBPRINT'
        Message = "Release validation must use the independent signer thumbprint."
    },
    @{
        Pattern = 'repos/\$env:GITHUB_REPOSITORY/immutable-releases'
        Message = "Release workflow must verify GitHub immutable-release enforcement."
    },
    @{
        Pattern = "provenance\.source\.revision -cne [`$]env:SOURCE_REVISION"
        Message = "Release workflow must read back the exact source revision."
    },
    @{
        Pattern = "provenance\.source\.tree -cne [`$]env:SOURCE_TREE"
        Message = "Release workflow must read back the exact source tree."
    },
    @{
        Pattern = "provenance\.source\.availability_state -cne 'verified_public'"
        Message = "Release workflow must require verified public source."
    },
    @{
        Pattern = "provenance\.distribution\.eligibility -cne 'signed_release'"
        Message = "Release workflow must require signed release eligibility."
    },
    @{
        Pattern = "releaseErrorText -notmatch 'HTTP 404'"
        Message = "Release workflow must distinguish absence from API failure."
    },
    @{
        Pattern = "'--verify-tag'"
        Message = "Release creation must require a pre-existing exact tag."
    },
    @{
        Pattern = "Published release readback does not match the immutable asset set"
        Message = "Release workflow must read back the published asset set."
    },
    @{
        Pattern = "-not \[bool\] [`$]release\.immutable"
        Message = "Published release readback must require platform-enforced immutability."
    },
    @{
        Pattern = "asset\.digest -cne [`$]localDigest"
        Message = "Published release readback must verify every asset digest."
    }
)) {
    Assert-WorkflowContains `
        -Pattern $requirement.Pattern `
        -Message $requirement.Message
}

foreach ($forbidden in @(
    '(?i)\bgh\s+release\s+upload\b',
    '(?i)\bgh\s+release\s+edit\b',
    '(?i)--clobber\b',
    '(?im)^\s*git\s+tag\b',
    '(?im)^\s*git\s+push\b',
    '(?i)provider_capability_discovery[^''"]*\.(?:json|schema)'
)) {
    if ($workflow -match $forbidden) {
        throw "Release workflow contains an overwrite or discovery-publication route."
    }
}

$expectedAssetMentions = [ordered]@{
    "rusty-hostess-hotspot-provider.exe" = 4
    "rusty-hostess-hotspot-provider.provenance.json" = 4
    "LICENSE" = 4
    "THIRD-PARTY-NOTICES.txt" = 4
}
foreach ($entry in $expectedAssetMentions.GetEnumerator()) {
    $observed = [regex]::Matches(
        $workflow,
        [regex]::Escape($entry.Key),
        [Text.RegularExpressions.RegexOptions]::CultureInvariant
    ).Count
    if ($observed -lt $entry.Value) {
        throw "Release workflow does not consistently bind asset $($entry.Key)."
    }
}

Write-Host "Windows hotspot provider release workflow gate passed."
