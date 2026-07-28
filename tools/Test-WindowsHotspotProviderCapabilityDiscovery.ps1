#requires -Version 7.0
[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ContractRoot
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

    $StartInfo = [Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = "dotnet"
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    $StartInfo.RedirectStandardInput = $true
    $StartInfo.RedirectStandardOutput = $true
    $StartInfo.RedirectStandardError = $true
    $StartInfo.ArgumentList.Add($ProviderAssembly)
    $StartInfo.ArgumentList.Add("--describe-json")
    $Process = [Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    if (-not $Process.Start()) {
        throw "Windows hotspot provider discovery process did not start."
    }
    $Process.StandardInput.Close()
    $StdoutTask = $Process.StandardOutput.ReadToEndAsync()
    $StderrTask = $Process.StandardError.ReadToEndAsync()
    if (-not $Process.WaitForExit(5000)) {
        $Process.Kill($true)
        throw "Windows hotspot provider discovery did not exit promptly."
    }
    $DescriptorText = $StdoutTask.GetAwaiter().GetResult()
    $StderrText = $StderrTask.GetAwaiter().GetResult()
    if ($Process.ExitCode -ne 0) {
        throw (
            "Windows hotspot provider discovery exited " +
            "$($Process.ExitCode).")
    }
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
    if (Test-Path -LiteralPath $TemporaryRoot) {
        Remove-Item -LiteralPath $TemporaryRoot -Recurse -Force
    }
}
