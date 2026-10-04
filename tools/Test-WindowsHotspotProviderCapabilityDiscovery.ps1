#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ContractRoot,
    # Standalone discovery also requires Python for shared process observation.
    [string] $PythonExe = "python"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$ExpectedContractRevision =
    "fc476166f9c05f941dff7e9183f5c893426c05ca"
$ExpectedContractTree =
    "dbb7d894e60626f48ba51f88bdecff7429c9997e"
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$ResolvedContractRoot = (Resolve-Path -LiteralPath $ContractRoot).Path
$Project = Join-Path $RepoRoot `
    "tools\windows_hotspot_provider\RustyHostess.WindowsHotspot.Provider.csproj"
$Validator = Join-Path $ResolvedContractRoot `
    "scripts\Test-AgentExecutionContracts.ps1"
$SharedSchema = Join-Path $ResolvedContractRoot `
    "schemas\rusty.quest.workflow.provider_capability_discovery.v1.schema.json"

if (-not (Test-Path -LiteralPath $Validator -PathType Leaf) -or
    -not (Test-Path -LiteralPath $SharedSchema -PathType Leaf)) {
    throw "The pinned provider-discovery contract surface is incomplete."
}

$ContractRevision = (
    & git -C $ResolvedContractRoot rev-parse HEAD
).Trim()
if ($LASTEXITCODE -ne 0 -or
    $ContractRevision -cne $ExpectedContractRevision) {
    throw "Provider-discovery contract revision drifted."
}
$ContractTree = (
    & git -C $ResolvedContractRoot rev-parse "HEAD^{tree}"
).Trim()
if ($LASTEXITCODE -ne 0 -or
    $ContractTree -cne $ExpectedContractTree) {
    throw "Provider-discovery contract tree drifted."
}
$ContractDirt = @(
    & git -C $ResolvedContractRoot status `
        --porcelain=v1 `
        --untracked-files=all
)
if ($LASTEXITCODE -ne 0 -or $ContractDirt.Count -ne 0) {
    throw "Provider-discovery contract worktree is not exact and clean."
}

$TemporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$TemporaryRoot = [IO.Path]::GetFullPath((
    Join-Path $TemporaryBase `
        "rusty-hostess-hotspot-discovery-$([guid]::NewGuid().ToString('N'))"
))
if (-not $TemporaryRoot.StartsWith(
    $TemporaryBase,
    [StringComparison]::OrdinalIgnoreCase)) {
    throw "Temporary discovery validation root escaped the temp directory."
}
[IO.Directory]::CreateDirectory($TemporaryRoot) | Out-Null
$ObservationRoot = Join-Path $TemporaryBase `
    "rusty-hostess-hotspot-discovery-observation-$([guid]::NewGuid().ToString('N'))"
$ValidationSucceeded = $false
try {
    & dotnet build $Project `
        -c Release `
        -o $TemporaryRoot `
        --nologo
    if ($LASTEXITCODE -ne 0) {
        throw "Windows hotspot provider build failed."
    }

    $ProviderAssembly = Join-Path $TemporaryRoot `
        "rusty-hostess-hotspot-provider.dll"
    if (-not (Test-Path -LiteralPath $ProviderAssembly -PathType Leaf)) {
        throw "Windows hotspot provider assembly was not produced."
    }

    Write-Host "Provider discovery progress: $(Join-Path $ObservationRoot 'progress.jsonl')"
    # Keep observer stdout separate from this route's existing output contract.
    # The shared CLI owns the child, concurrent drains and empty stdin EOF.
    $ObserverProjection = & $PythonExe (Join-Path $RepoRoot 'tools\observe_process.py') `
        --out $ObservationRoot --cwd $RepoRoot -- dotnet $ProviderAssembly --describe-json
    $ObserverExit = $LASTEXITCODE
    if ($ObserverExit -ne 0) {
        throw "Provider discovery observation failed ($ObserverExit); retained $ObservationRoot and $TemporaryRoot."
    }
    $Observation = Get-Content -Raw -LiteralPath (Join-Path $ObservationRoot 'receipt.json') |
        ConvertFrom-Json
    if ($Observation.schema -cne 'rusty.hostess.process_observation.v1' -or
        $Observation.child_started -isnot [bool] -or -not $Observation.child_started -or
        $Observation.exit_known -isnot [bool] -or -not $Observation.exit_known -or
        $Observation.process_reaped -isnot [bool] -or -not $Observation.process_reaped -or
        $Observation.observation_complete -isnot [bool] -or -not $Observation.observation_complete -or
        $Observation.cancel_requested -isnot [bool] -or $Observation.cancel_requested -or
        $Observation.source_changed -isnot [bool] -or $Observation.source_changed -or
        @($Observation.argv).Count -ne 3 -or $Observation.argv[0] -cne 'dotnet' -or
        $Observation.argv[1] -cne $ProviderAssembly -or $Observation.argv[2] -cne '--describe-json' -or
        -not ($Observation.exit_code -is [long] -or $Observation.exit_code -is [int]) -or
        $Observation.exit_code -ne 0 -or @($Observation.observer_errors).Count -ne 0) {
        throw "Provider discovery lacks complete successful child proof; retained $ObservationRoot and $TemporaryRoot."
    }
    foreach ($StreamName in @('stdout', 'stderr')) {
        $Raw = $Observation.streams.$StreamName
        $RawPath = Join-Path $ObservationRoot "$StreamName.raw"
        $File = Get-Item -LiteralPath $RawPath
        if ($Raw.eof -isnot [bool] -or -not $Raw.eof -or
            $Raw.raw_file_closed -isnot [bool] -or -not $Raw.raw_file_closed -or
            $Raw.budget_exceeded -isnot [bool] -or $Raw.budget_exceeded -or
            $null -ne $Raw.error -or $Raw.initialization -cne 'started' -or
            $File.PSIsContainer -or $null -ne $File.LinkType -or
            -not ($Raw.descriptor.bytes -is [long] -or $Raw.descriptor.bytes -is [int]) -or
            -not ($Raw.observed_bytes -is [long] -or $Raw.observed_bytes -is [int]) -or
            -not ($Raw.retained_bytes -is [long] -or $Raw.retained_bytes -is [int]) -or
            $Raw.descriptor.bytes -lt 0 -or $Raw.descriptor.bytes -ne $File.Length -or
            $Raw.observed_bytes -ne $File.Length -or $Raw.retained_bytes -ne $File.Length -or
            -not [string]::Equals([IO.Path]::GetFullPath($Raw.descriptor.path),
                [IO.Path]::GetFullPath($RawPath), [StringComparison]::OrdinalIgnoreCase) -or
            $Raw.descriptor.sha256 -cnotmatch '^[0-9a-f]{64}$' -or
            $Raw.descriptor.sha256 -cne (Get-FileHash -LiteralPath $RawPath -Algorithm SHA256).Hash.ToLowerInvariant()) {
            throw "Provider discovery $StreamName raw proof is incomplete; retained $ObservationRoot and $TemporaryRoot."
        }
    }
    $DescriptorText = Get-Content -Raw -LiteralPath (Join-Path $ObservationRoot 'stdout.raw')
    $StderrText = Get-Content -Raw -LiteralPath (Join-Path $ObservationRoot 'stderr.raw')
    if (-not [string]::IsNullOrEmpty($StderrText)) {
        throw "Windows hotspot provider discovery wrote stderr."
    }

    $Descriptor = $DescriptorText |
        ConvertFrom-Json -Depth 100 -DateKind String
    if ($Descriptor.schema -cne
            "rusty.quest.workflow.provider_capability_discovery.v1" -or
        $Descriptor.provider.id -cne
            "rusty.hostess.windows-hotspot-provider" -or
        $Descriptor.authorizes_execution -ne $false -or
        $Descriptor.target_specific -ne $false) {
        throw "Windows hotspot provider emitted an unexpected descriptor."
    }

    $DescriptorPath = Join-Path $TemporaryRoot "descriptor.json"
    [IO.File]::WriteAllText(
        $DescriptorPath,
        $DescriptorText,
        [Text.UTF8Encoding]::new($false))

    & pwsh `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $Validator `
        -Root $ResolvedContractRoot `
        -ProviderDiscoveryPath $DescriptorPath
    if ($LASTEXITCODE -ne 0) {
        throw "Pinned provider-discovery validator rejected the descriptor."
    }

    $ValidationSucceeded = $true
    [ordered]@{
        schema =
            "rusty.hostess.windows_hotspot.provider_discovery_validation.v1"
        result = "pass"
        provider_id = $Descriptor.provider.id
        provider_version = $Descriptor.provider.version
        contract_revision = $ContractRevision
        contract_tree = $ContractTree
    } | ConvertTo-Json -Compress
}
finally {
    # Failed/unknown validation retains its build and observation evidence.
    # Successful validation may remove only its original owned build scratch;
    # observation raw/progress stays outside that scratch in a sibling directory.
    if ($ValidationSucceeded -and (Test-Path -LiteralPath $TemporaryRoot)) {
        Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
    }
}
