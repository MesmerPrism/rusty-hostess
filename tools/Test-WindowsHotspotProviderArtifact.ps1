#requires -Version 7.0
param([string]$OutDir = "target\windows-hotspot-provider")
$ErrorActionPreference = "Stop"
if ($PSVersionTable.PSVersion.Major -lt 7) { throw "PowerShell 7 or newer is required." }
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$Project = Join-Path $RepoRoot "tools\windows_hotspot_provider\RustyHostess.WindowsHotspot.Provider.csproj"
$Publish = Join-Path $RepoRoot $OutDir
dotnet publish $Project -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -o $Publish
if ($LASTEXITCODE -ne 0) { throw "Provider publish failed." }
$Exe = Join-Path $Publish "rusty-hostess-hotspot-provider.exe"
if (-not (Test-Path $Exe)) { throw "Expected single-file provider executable was not published." }
$Unexpected = @(Get-ChildItem $Publish -File | Where-Object Name -NotIn @("rusty-hostess-hotspot-provider.exe", "rusty-hostess-hotspot-provider.pdb"))
if ($Unexpected.Count -ne 0) { throw "Unexpected publish artifacts: $($Unexpected.Name -join ', ')" }
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
$StatusRequest | & $Exe integration windows-hotspot --json 1> $StatusOut 2> $StatusErr
$StatusExit = $LASTEXITCODE
if ($StatusExit -notin @(0, 1, 3)) { throw "Read-only status smoke returned unexpected exit $StatusExit." }
if ((Get-Item $StatusErr).Length -ne 0) { throw "Read-only status smoke wrote stderr." }
$StatusReceipt = Get-Content -Raw $StatusOut | ConvertFrom-Json
if ($StatusReceipt.schema -ne "rusty.hostess.windows_hotspot.provider_receipt.v1" -or
    $StatusReceipt.action -ne "status" -or
    $StatusReceipt.outcome -notin @("verified", "failed", "unavailable")) {
    throw "Invalid read-only status smoke receipt."
}
Remove-Item -LiteralPath $StatusOut, $StatusErr
$BadOut = Join-Path $Publish "bad-args.stdout.txt"
$BadErr = Join-Path $Publish "bad-args.stderr.txt"
& $Exe integration Windows-Hotspot --json 1> $BadOut 2> $BadErr
if ($LASTEXITCODE -ne 2) { throw "Incorrectly-cased args expected exit 2, got $LASTEXITCODE." }
if ((Get-Item $BadOut).Length -ne 0 -or (Get-Item $BadErr).Length -ne 0) { throw "Argument rejection wrote output." }
Remove-Item -LiteralPath $BadOut, $BadErr
Write-Host "Windows hotspot provider artifact gate passed: $Exe"
