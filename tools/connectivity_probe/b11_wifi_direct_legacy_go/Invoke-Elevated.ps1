[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Executable,
    [Parameter(Mandatory)][string]$ExpectedSha256,
    [Parameter(Mandatory)][string]$ExpectedDllSha256,
    [Parameter(Mandatory)][string]$RequestPath,
    [Parameter(Mandatory)][string]$StdoutPath,
    [Parameter(Mandatory)][string]$StderrPath
)

$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new(
    [Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Administrator token required for the scoped firewall rule and ICS readback.'
}

$exe = (Resolve-Path -LiteralPath $Executable -ErrorAction Stop).Path
$requestFile = (Resolve-Path -LiteralPath $RequestPath -ErrorAction Stop).Path
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant() -ne
    $ExpectedSha256.ToLowerInvariant()) {
    throw 'Executable SHA-256 mismatch.'
}
$dll = [IO.Path]::ChangeExtension($exe, '.dll')
if (-not (Test-Path -LiteralPath $dll -PathType Leaf) -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $dll).Hash.ToLowerInvariant() -ne
    $ExpectedDllSha256.ToLowerInvariant()) {
    throw 'Provider DLL SHA-256 mismatch.'
}
if (Test-Path -LiteralPath $StdoutPath -PathType Any) { throw 'Stdout path exists.' }
if (Test-Path -LiteralPath $StderrPath -PathType Any) { throw 'Stderr path exists.' }

$requestText = [IO.File]::ReadAllText($requestFile)
$request = $requestText | ConvertFrom-Json -AsHashtable
if ($request.schema -ne 'rusty.hostess.wifi_direct_legacy_go.request.v2') {
    throw 'Unexpected request schema.'
}
if ([int]$request.health_port -ne 47831) { throw 'Expected health port 47831.' }
if ([string]$request.operation_id -notmatch '^[a-z0-9][a-z0-9-]{7,47}$') {
    throw 'Invalid operation id.'
}
$ruleName = 'RustyHostess-B11-GO-' + [string]$request.operation_id
if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
    throw 'Run-owned firewall rule already exists.'
}

try {
    New-NetFirewallRule -Name $ruleName -DisplayName $ruleName `
        -Direction Inbound -Action Allow -Enabled True -Profile Any `
        -Program $exe -Protocol TCP -LocalPort 47831 -RemoteAddress LocalSubnet |
        Out-Null
    $requestText | & $exe 1> $StdoutPath 2> $StderrPath
    if ($LASTEXITCODE -ne 0) { throw "GO provider exited $LASTEXITCODE." }
}
finally {
    Remove-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
    if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
        throw 'Run-owned firewall rule cleanup failed.'
    }
}
