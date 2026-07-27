#requires -Version 7.0
param(
    [string] $OutDir = "target\windows-hotspot-provider",
    [ValidatePattern("^[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?$")]
    [string] $ProviderVersion = "0.1.0"
)
$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 7) { throw "PowerShell 7 or newer is required." }
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Project = Join-Path $RepoRoot "tools\windows_hotspot_provider\RustyHostess.WindowsHotspot.Provider.csproj"
$Publish = Join-Path $RepoRoot $OutDir
$SourceRevision = (& git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $SourceRevision -cnotmatch "^[0-9a-f]{40}$") {
    throw "Could not resolve the provider source revision."
}
$SourceDirt = @(& git -C $RepoRoot status --porcelain=v1 --untracked-files=all)
$SourceClaim = if ($SourceDirt.Count -eq 0) {
    $SourceRevision
} else {
    "dirty.$SourceRevision"
}
dotnet publish $Project `
    -c Release `
    -r win-x64 `
    --self-contained true `
    -p:PublishSingleFile=true `
    -p:Version=$ProviderVersion `
    -p:InformationalVersion="$ProviderVersion+$SourceClaim" `
    -p:IncludeSourceRevisionInInformationalVersion=false `
    -p:RepositoryCommit=$SourceRevision `
    -p:SourceRevisionId=$SourceRevision `
    -o $Publish
if ($LASTEXITCODE -ne 0) { throw "Provider publish failed." }
$Exe = Join-Path $Publish "rusty-hostess-hotspot-provider.exe"
if (-not (Test-Path $Exe)) { throw "Expected single-file provider executable was not published." }
$Unexpected = @(Get-ChildItem $Publish -File | Where-Object Name -NotIn @("rusty-hostess-hotspot-provider.exe", "rusty-hostess-hotspot-provider.pdb"))
if ($Unexpected.Count -ne 0) { throw "Unexpected publish artifacts: $($Unexpected.Name -join ', ')" }
$PrivateState = Join-Path (
    [Environment]::GetFolderPath(
        [Environment+SpecialFolder]::LocalApplicationData)
) "RustyHostess\WindowsHotspotProvider\private-state.json"
$StateBefore = if (Test-Path -LiteralPath $PrivateState -PathType Leaf) {
    "present:$((Get-FileHash -Algorithm SHA256 -LiteralPath $PrivateState).Hash)"
} else {
    "absent"
}
$DescribeOut = Join-Path $Publish "describe.stdout.json"
$DescribeErr = Join-Path $Publish "describe.stderr.txt"
$DescribeIn = Join-Path $Publish "describe.stdin.txt"
[IO.File]::WriteAllText($DescribeIn, "")
$DescribeProcess = Start-Process `
    -FilePath $Exe `
    -ArgumentList @("--describe-json") `
    -RedirectStandardInput $DescribeIn `
    -RedirectStandardOutput $DescribeOut `
    -RedirectStandardError $DescribeErr `
    -WindowStyle Hidden `
    -PassThru
if (-not $DescribeProcess.WaitForExit(5000)) {
    $DescribeProcess.Kill($true)
    throw "Capability discovery did not exit promptly."
}
if ($DescribeProcess.ExitCode -ne 0) {
    throw "Capability discovery exited $($DescribeProcess.ExitCode)."
}
if ((Get-Item $DescribeErr).Length -ne 0) {
    throw "Capability discovery wrote stderr."
}
$Descriptor = Get-Content -Raw $DescribeOut | ConvertFrom-Json
if ($Descriptor.schema -cne
        "rusty.quest.workflow.provider_capability_discovery.v1" -or
    $Descriptor.provider.id -cne
        "rusty.hostess.windows-hotspot-provider" -or
    $Descriptor.provider.version -cne $ProviderVersion -or
    $Descriptor.authorizes_execution -ne $false -or
    $Descriptor.target_specific -ne $false -or
    @($Descriptor.capabilities).Count -ne 1 -or
    $Descriptor.capabilities[0].receipt_schema -cne
        "rusty.hostess.windows_hotspot.provider_receipt.v1") {
    throw "Capability discovery emitted an invalid provider description."
}
$StateAfter = if (Test-Path -LiteralPath $PrivateState -PathType Leaf) {
    "present:$((Get-FileHash -Algorithm SHA256 -LiteralPath $PrivateState).Hash)"
} else {
    "absent"
}
if ($StateAfter -cne $StateBefore) {
    throw "Capability discovery read or changed provider state."
}
Remove-Item -LiteralPath $DescribeOut, $DescribeErr, $DescribeIn
$BadDescribeOut = Join-Path $Publish "bad-describe.stdout.txt"
$BadDescribeErr = Join-Path $Publish "bad-describe.stderr.txt"
foreach ($BadDescribeArguments in @(
    @("--Describe-Json"),
    @("--describe-json", "extra"),
    @("integration", "windows-hotspot", "--json", "--describe-json")
)) {
    & $Exe @BadDescribeArguments 1> $BadDescribeOut 2> $BadDescribeErr
    if ($LASTEXITCODE -ne 2) {
        throw "Non-exact capability-discovery arguments were accepted."
    }
    if ((Get-Item $BadDescribeOut).Length -ne 0 -or
        (Get-Item $BadDescribeErr).Length -ne 0) {
        throw "Capability-discovery argument rejection wrote output."
    }
}
Remove-Item -LiteralPath $BadDescribeOut, $BadDescribeErr
$Stdout = Join-Path $Publish "smoke.stdout.json"
$Stderr = Join-Path $Publish "smoke.stderr.txt"
$Request = '{"schema":"rusty.hostess.windows_hotspot.provider_request.v1","request_id":"smoke","operation_id":"smoke","action":"status","expires_at_utc":"2000-01-01T00:00:00.0000000+00:00","timeout_ms":1000}'
$Request | & $Exe integration windows-hotspot --json 1> $Stdout 2> $Stderr
if ($LASTEXITCODE -ne 2) { throw "Expired-request smoke expected exit 2, got $LASTEXITCODE." }
if ((Get-Item $Stderr).Length -ne 0) { throw "Handled outcome wrote stderr." }
$Receipt = Get-Content -Raw $Stdout | ConvertFrom-Json
if ($Receipt.schema -ne "rusty.hostess.windows_hotspot.provider_receipt.v1" -or $Receipt.outcome -ne "rejected") { throw "Invalid smoke receipt." }
Remove-Item -LiteralPath $Stdout, $Stderr
$StatusOut = Join-Path $Publish "status.stdout.json"
$StatusErr = Join-Path $Publish "status.stderr.txt"
$StatusId = [guid]::NewGuid().ToString("N")
$StatusExpiry = [DateTimeOffset]::UtcNow.AddMinutes(2).ToString("O")
$StatusRequest = [ordered]@{
    schema = "rusty.hostess.windows_hotspot.provider_request.v1"
    request_id = "artifact-status-$StatusId"
    operation_id = "artifact-status-$StatusId"
    action = "status"
    expires_at_utc = $StatusExpiry
    timeout_ms = 30000
} | ConvertTo-Json -Compress
$StatusRequest | & $Exe integration windows-hotspot --json --artifact-readonly-probe 1> $StatusOut 2> $StatusErr
$StatusExit = $LASTEXITCODE
if ($StatusExit -notin @(0, 1, 3)) { throw "Read-only status smoke returned unexpected exit $StatusExit." }
if ((Get-Item $StatusErr).Length -ne 0) { throw "Read-only status smoke wrote stderr." }
$StatusReceipt = Get-Content -Raw $StatusOut | ConvertFrom-Json
if ($StatusReceipt.schema -ne "rusty.hostess.windows_hotspot.provider_receipt.v1" -or
    $StatusReceipt.action -ne "status" -or
    $StatusReceipt.outcome -notin @("verified", "failed", "unavailable")) {
    throw "Invalid read-only status smoke receipt."
}
$ExpectedStatusExit = @{
    verified = 0
    failed = 1
    unavailable = 3
}[$StatusReceipt.outcome]
if ($StatusExit -ne $ExpectedStatusExit) {
    throw "Read-only status outcome $($StatusReceipt.outcome) did not map to exit $ExpectedStatusExit."
}
Remove-Item -LiteralPath $StatusOut, $StatusErr
$ProbeStartOut = Join-Path $Publish "probe-start.stdout.json"
$ProbeStartErr = Join-Path $Publish "probe-start.stderr.txt"
$ProbeStartId = [guid]::NewGuid().ToString("N")
$ProbeStartRequest = [ordered]@{
    schema = "rusty.hostess.windows_hotspot.provider_request.v1"
    request_id = "artifact-probe-start-$ProbeStartId"
    operation_id = "artifact-probe-start-$ProbeStartId"
    action = "start"
    expires_at_utc = [DateTimeOffset]::UtcNow.AddMinutes(2).ToString("O")
    timeout_ms = 30000
} | ConvertTo-Json -Compress
$ProbeStartRequest | & $Exe integration windows-hotspot --json --artifact-readonly-probe 1> $ProbeStartOut 2> $ProbeStartErr
if ($LASTEXITCODE -ne 2) { throw "Artifact probe accepted a mutating request." }
if ((Get-Item $ProbeStartErr).Length -ne 0) { throw "Artifact probe rejection wrote stderr." }
$ProbeStartReceipt = Get-Content -Raw $ProbeStartOut | ConvertFrom-Json
if ($ProbeStartReceipt.outcome -ne "rejected" -or
    $ProbeStartReceipt.reason -ne "artifact_probe.status_only") {
    throw "Artifact probe did not reject a mutating request with the closed reason."
}
Remove-Item -LiteralPath $ProbeStartOut, $ProbeStartErr
$BadOut = Join-Path $Publish "bad-args.stdout.txt"
$BadErr = Join-Path $Publish "bad-args.stderr.txt"
& $Exe integration Windows-Hotspot --json 1> $BadOut 2> $BadErr
if ($LASTEXITCODE -ne 2) { throw "Incorrectly-cased args expected exit 2, got $LASTEXITCODE." }
if ((Get-Item $BadOut).Length -ne 0 -or (Get-Item $BadErr).Length -ne 0) { throw "Argument rejection wrote output." }
Remove-Item -LiteralPath $BadOut, $BadErr
Write-Host "Windows hotspot provider artifact gate passed: $Exe"
