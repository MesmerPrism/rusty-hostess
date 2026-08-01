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
$policyPath = Join-Path $repoRoot `
    "packaging\windows-hotspot-provider\release-policy.json"
$policySchemaPath = Join-Path $repoRoot `
    "schemas\hostess-windows-hotspot-release-policy.schema.json"
$policyText = Get-Content -Raw -LiteralPath $policyPath
if (-not (Test-Json -Json $policyText -SchemaFile $policySchemaPath)) {
    throw "Windows hotspot provider release policy failed its owner schema."
}
$policy = $policyText | ConvertFrom-Json -Depth 10
if ($policy.signer.subject -cne "CN=MesmerPrism" -or
    $policy.signer.issuer -cne "CN=MesmerPrism" -or
    $policy.signer.thumbprint_sha1 -cne
        "08A5878AD6E652A94517D2C79144EB2655B0088C" -or
    $policy.signer.certificate_sha256 -cne
        "baead63c37e32085c3af19b4c739a6a308d700529f107d40e14fec2c94fe7ddf" -or
    $policy.signer.self_issued -ne $true -or
    $policy.signer.public_trust_claim -ne $false -or
    $policy.signer.timestamp_required -ne $true -or
    $policy.signer.code_signing_eku_oid -cne "1.3.6.1.5.5.7.3.3" -or
    @($policy.accepted_validation_boundaries).Count -ne 2 -or
    @($policy.distribution.allowed_channels).Count -ne 1 -or
    $policy.distribution.allowed_channels[0] -cne "labs" -or
    $policy.distribution.stable_eligible -ne $false) {
    throw "Windows hotspot provider release policy does not equal the reviewed public pins."
}

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
        Pattern = 'WindowsAuthenticodePolicy\.psm1'
        Message = "Release workflow must use the provider-owned Authenticode assessor."
    },
    @{
        Pattern = 'release-policy\.json'
        Message = "Release workflow must use the reviewed provider release policy."
    },
    @{
        Pattern = 'hostess-windows-hotspot-release-policy\.schema\.json'
        Message = "Release workflow must validate the provider release policy schema."
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
        Pattern = "assessment\.authenticode_status -cne 'unknown_error'"
        Message = "Hosted publication must observe the self-issued UnknownError boundary."
    },
    @{
        Pattern = "assessment\.chain_status_flags\[0\] -cne 'UntrustedRoot'"
        Message = "Hosted publication must observe only UntrustedRoot."
    },
    @{
        Pattern = 'no public Windows trust claim'
        Message = "Provider release notes must state the self-issued trust limitation."
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
        Pattern = '-RequireSignedRelease'
        Message = "Release workflow must fail closed through signed-release validation."
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
        Pattern = "provenance\.distribution\.eligibility -cne 'labs_signed_release'"
        Message = "Release workflow must require Labs-only signed eligibility."
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

$securitySurfacePaths = @(
    $workflowPath,
    (Join-Path $repoRoot "packaging\windows-hotspot-provider\WindowsAuthenticodePolicy.psm1"),
    (Join-Path $repoRoot "tools\New-WindowsHotspotProviderReleaseMetadata.ps1"),
    (Join-Path $repoRoot "tools\Test-WindowsHotspotProviderReleaseMetadata.ps1")
)
$securitySurface = ($securitySurfacePaths | ForEach-Object {
    Get-Content -Raw -LiteralPath $_
}) -join "`n"
foreach ($forbidden in @(
    '\$_\.ObjectId\.Value',
    '(?i)Cert:\\[^\r\n]*\\(?:Root|TrustedPublisher)',
    '(?i)\bImport-Certificate\b',
    '(?i)\bImport-PfxCertificate\b',
    '(?i)\bcertutil(?:\.exe)?\b[^\r\n]*\baddstore\b',
    '(?i)\bNew-SelfSignedCertificate\b',
    '(?i)-CertStoreLocation\b',
    '(?i)\bgh\s+release\s+upload\b',
    '(?i)\bgh\s+release\s+edit\b',
    '(?i)--clobber\b',
    '(?im)^\s*git\s+tag\b',
    '(?im)^\s*git\s+push\b',
    '(?i)provider_capability_discovery[^''"]*\.(?:json|schema)'
)) {
    if ($securitySurface -match $forbidden) {
        throw "Provider release surface contains a trust-store, overwrite, or discovery-publication route."
    }
}

$expectedAssetMentions = [ordered]@{
    "rusty-hostess-hotspot-provider.exe" = 4
    "rusty-hostess-hotspot-provider.provenance.json" = 4
    "rusty-hostess-hotspot-provider.release-policy.json" = 4
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
