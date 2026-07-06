param(
    [string]$Serial = $env:RUSTY_QUEST_SERIAL,
    [string]$Adb = $(if ($env:RUSTY_XR_ADB) { $env:RUSTY_XR_ADB } elseif ($env:ADB) { $env:ADB } else { "adb" }),
    [string]$Python = "python",
    [string]$QuestToolingScript = "S:\Work\tools\Quest\Use-QuestTooling.ps1",
    [string]$ManifoldRoot = "S:\Work\repos\active\rusty-manifold",
    [string]$ManifoldPackagesRoot = "S:\Work\repos\active\rusty-manifold-packages",
    [string]$RustyQuestRoot = "S:\Work\repos\active\rusty-quest",
    [string]$MakepadForkRoot = "S:\Work\repos\active\makepad-morphospace",
    [string]$MakepadPackage = "io.github.mesmerprism.rustyhostess.makepad",
    [string]$MakepadActivity = "io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
    [string]$HostessAndroidPackage = "io.github.mesmerprism.rustyhostess.t",
    [string]$BrokerPackage = "io.github.mesmerprism.rustymanifold.broker",
    [string]$BrokerActivity = "io.github.mesmerprism.rustymanifold.broker/.BrokerStartActivity",
    [string]$StreamingAppLabel = "Rusty Morphospace Streaming",
    [string]$FirewallProgram = "",
    [string]$FirewallProfile = "Any",
    [string]$FirewallRemoteAddress = "LocalSubnet",
    [int]$TcpEchoPort = 18766,
    [int]$UdpFreshnessPort = 18767,
    [int]$Qcl082MediaPort = 9079,
    [ValidateSet("true", "false")]
    [string]$QuestCameraPermissions = "false",
    [string]$OutDir = "",
    [switch]$SkipBuild,
    [switch]$SkipWpfBuild,
    [switch]$SkipInstall,
    [switch]$SkipMakepadBuild,
    [switch]$SkipManifoldBrokerBuild,
    [switch]$SkipCargoMakepadInstall,
    [switch]$SkipHostessAndroidBuild,
    [switch]$SkipHostessAndroidInstall,
    [switch]$SkipManifoldBrokerInstall,
    [switch]$SkipEnvironmentScan,
    [switch]$EnvironmentScanOnly,
    [switch]$ApplyFirewallRules,
    [switch]$LaunchElevatedFirewallHandoff,
    [switch]$SkipBluetoothPayloadRows,
    [switch]$SkipPcHotspotRow,
    [switch]$RunPcHotspotRow,
    [switch]$RunQcl050Rfcomm,
    [switch]$SkipQcl030Preflight,
    [switch]$SkipQcl041Preflight,
    [switch]$SkipQcl082Plan,
    [switch]$SkipProtocolMatrix,
    [switch]$RunQcl041WindowsLifecycle,
    [switch]$FailFast
)

$ErrorActionPreference = "Stop"

function Get-UtcStamp {
    return (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
}

function Get-SafeToken {
    param([Parameter(Mandatory=$true)][string]$Value)
    $token = [regex]::Replace($Value, "[^A-Za-z0-9._-]+", "-").Trim("._-")
    if ([string]::IsNullOrWhiteSpace($token)) {
        return "step"
    }
    return $token
}

function ConvertTo-JsonFile {
    param(
        [Parameter(Mandatory=$true)][object]$Value,
        [Parameter(Mandatory=$true)][string]$Path
    )
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
    $Value | ConvertTo-Json -Depth 80 | Set-Content -Encoding UTF8 -Path $Path
}

function Get-JsonObject {
    param([Parameter(Mandatory=$true)][string]$Path)
    if (-not (Test-Path $Path)) {
        return $null
    }
    try {
        return Get-Content -Raw -Path $Path | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Get-FirstExistingPath {
    param([string[]]$Candidates)
    foreach ($candidate in $Candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path $candidate)) {
            return (Resolve-Path $candidate).Path
        }
    }
    return ""
}

function Resolve-MakepadApkPath {
    param([Parameter(Mandatory=$true)][string]$RepoRoot)
    return Get-FirstExistingPath @(
        (Join-Path $RepoRoot "apps\hostess-t-makepad\target\android\makepad-android-apk\hostess_t_makepad\apk\rustymorphospacestreaming.apk"),
        (Join-Path $RepoRoot "apps\hostess-t-makepad\target\android\makepad-android-apk\hostess_t_makepad\apk\rustyhostessmakepad.apk")
    )
}

function Write-RunPhase {
    param([Parameter(Mandatory=$true)][string]$Name)
    Write-Host ("[rusty-morphospace-qcl] PHASE {0}" -f $Name)
}

function Resolve-OneAdbDevice {
    param([Parameter(Mandatory=$true)][string]$AdbPath)
    $devices = & $AdbPath devices 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "adb devices failed: $devices"
    }
    $connected = @()
    foreach ($line in $devices) {
        if ($line -match "^([^\s]+)\s+device(\s|$)") {
            $connected += $Matches[1]
        }
    }
    if ($connected.Count -eq 1) {
        return $connected[0]
    }
    if ($connected.Count -eq 0) {
        throw "No authorized Quest device is visible to adb."
    }
    throw "Multiple adb devices are connected; pass -Serial explicitly."
}

function Invoke-ProcessStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$File,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = "",
        [string]$StdoutPath = "",
        [string]$StderrPath = "",
        [int]$TimeoutSeconds = 0,
        [switch]$AllowFailure
    )

    $slug = Get-SafeToken $Name
    if ([string]::IsNullOrWhiteSpace($StdoutPath)) {
        $StdoutPath = Join-Path $script:LogDir "$slug.stdout.txt"
    }
    if ([string]::IsNullOrWhiteSpace($StderrPath)) {
        $StderrPath = Join-Path $script:LogDir "$slug.stderr.txt"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $StdoutPath), (Split-Path -Parent $StderrPath) | Out-Null

    $started = (Get-Date).ToUniversalTime().ToString("o")
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host ("[rusty-morphospace-qcl] START {0}" -f $Name)
    if (Test-Path $StdoutPath) {
        Remove-Item -LiteralPath $StdoutPath -Force
    }
    if (Test-Path $StderrPath) {
        Remove-Item -LiteralPath $StderrPath -Force
    }
    $argumentLine = ($Arguments | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " "
    $startArgs = @{
        FilePath = $File
        ArgumentList = $argumentLine
        PassThru = $true
        RedirectStandardOutput = $StdoutPath
        RedirectStandardError = $StderrPath
        WindowStyle = "Hidden"
    }
    if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) {
        $startArgs.WorkingDirectory = $WorkingDirectory
    }
    $process = Start-Process @startArgs
    $timedOut = $false
    if ($TimeoutSeconds -gt 0) {
        $finished = $process.WaitForExit($TimeoutSeconds * 1000)
        if (-not $finished) {
            $timedOut = $true
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            try {
                $process.WaitForExit(5000) | Out-Null
            } catch {
            }
        }
    } else {
        $process.WaitForExit()
    }
    $timer.Stop()

    if (-not $timedOut) {
        try {
            $process.Refresh()
        } catch {
        }
    }
    $exitCode = if ($timedOut) { 124 } else { [int]$process.ExitCode }
    $timeoutLabel = if ($timedOut) { " timedOut=true" } else { "" }
    Write-Host ("[rusty-morphospace-qcl] DONE {0} exit={1} elapsedMs={2}{3}" -f $Name, $exitCode, [math]::Round($timer.Elapsed.TotalMilliseconds, 0), $timeoutLabel)
    $step = [ordered]@{
        name = $Name
        status = $(if ($exitCode -eq 0) { "pass" } else { "fail" })
        exit_code = $exitCode
        timed_out = $timedOut
        timeout_seconds = $TimeoutSeconds
        started_at_utc = $started
        elapsed_ms = [math]::Round($timer.Elapsed.TotalMilliseconds, 3)
        file = $File
        arguments = @($Arguments)
        working_directory = $WorkingDirectory
        stdout_path = $StdoutPath
        stderr_path = $StderrPath
    }
    $script:Steps += $step
    if ($exitCode -ne 0 -and -not $AllowFailure -and $FailFast) {
        throw "Step failed: $Name. See $StdoutPath and $StderrPath."
    }
    return $step
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) {
        return '""'
    }
    if ($Value -notmatch '[\s"]') {
        return $Value
    }
    $escaped = $Value -replace '\\(?=\\*")', '\\' -replace '"', '\"'
    return '"' + $escaped + '"'
}

function Invoke-PowerShellScriptStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$ScriptPath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = "",
        [int]$TimeoutSeconds = 0,
        [switch]$AllowFailure
    )
    $powershell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if ([string]::IsNullOrWhiteSpace($powershell)) {
        $powershell = (Get-Command powershell -ErrorAction Stop).Source
    }
    $allArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) + $Arguments
    return Invoke-ProcessStep -Name $Name -File $powershell -Arguments $allArgs -WorkingDirectory $WorkingDirectory -TimeoutSeconds $TimeoutSeconds -AllowFailure:$AllowFailure
}

function Invoke-ElevatedPowerShellScriptStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$ScriptPath,
        [int]$TimeoutSeconds = 300,
        [switch]$AllowFailure
    )

    $powershell = (Get-Command powershell -ErrorAction Stop).Source
    $started = (Get-Date).ToUniversalTime().ToString("o")
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Write-Host ("[rusty-morphospace-qcl] START {0}" -f $Name)
    $exitCode = 1
    $timedOut = $false
    $errorText = ""
    try {
        $argumentLine = (@("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath) | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " "
        $process = Start-Process -FilePath $powershell -ArgumentList $argumentLine -Verb RunAs -PassThru
        if ($TimeoutSeconds -gt 0) {
            $finished = $process.WaitForExit($TimeoutSeconds * 1000)
            if (-not $finished) {
                $timedOut = $true
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
                try {
                    $process.WaitForExit(5000) | Out-Null
                } catch {
                }
                $exitCode = 124
            } else {
                try {
                    $process.Refresh()
                } catch {
                }
                $exitCode = [int]$process.ExitCode
            }
        } else {
            $process.WaitForExit()
            try {
                $process.Refresh()
            } catch {
            }
            $exitCode = [int]$process.ExitCode
        }
    } catch {
        $errorText = $_.Exception.Message
    }
    $timer.Stop()
    $timeoutLabel = if ($timedOut) { " timedOut=true" } else { "" }
    Write-Host ("[rusty-morphospace-qcl] DONE {0} exit={1} elapsedMs={2}{3}" -f $Name, $exitCode, [math]::Round($timer.Elapsed.TotalMilliseconds, 0), $timeoutLabel)
    $step = [ordered]@{
        name = $Name
        status = $(if ($exitCode -eq 0) { "pass" } else { "fail" })
        exit_code = $exitCode
        timed_out = $timedOut
        timeout_seconds = $TimeoutSeconds
        started_at_utc = $started
        elapsed_ms = [math]::Round($timer.Elapsed.TotalMilliseconds, 3)
        file = $powershell
        arguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ScriptPath)
        working_directory = ""
        stdout_path = ""
        stderr_path = ""
        error = $errorText
    }
    $script:Steps += $step
    if ($exitCode -ne 0 -and -not $AllowFailure -and $FailFast) {
        throw "Elevated step failed: $Name. $errorText"
    }
    return $step
}

function Invoke-HostessCtlStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [string[]]$Arguments = @(),
        [switch]$AllowFailure
    )
    $allArgs = @($script:HostessCtl) + $Arguments
    return Invoke-ProcessStep -Name $Name -File $Python -Arguments $allArgs -WorkingDirectory $script:RepoRoot -AllowFailure:$AllowFailure
}

function Invoke-FirewallRuleReport {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$RuleProfile,
        [Parameter(Mandatory=$true)][string]$ProbeId,
        [Parameter(Mandatory=$true)][string]$Action,
        [Parameter(Mandatory=$true)][string]$OutFileName,
        [int]$Port = 0,
        [string]$HandoffScriptOut = "",
        [string]$HandoffVerifyOut = ""
    )

    $outPath = Join-Path $OutDir $OutFileName
    $args = @(
        "connectivity-probe",
        "windows-firewall-rule",
        "--action", $Action,
        "--rule-profile", $RuleProfile,
        "--program", $FirewallProgram,
        "--profile", $FirewallProfile,
        "--remote-address", $FirewallRemoteAddress,
        "--out", $outPath
    )
    if ($Port -gt 0) {
        $args += @("--port", [string]$Port)
    }
    if (-not [string]::IsNullOrWhiteSpace($HandoffScriptOut)) {
        $args += @("--handoff-script-out", $HandoffScriptOut)
    }
    if (-not [string]::IsNullOrWhiteSpace($HandoffVerifyOut)) {
        $args += @("--handoff-verify-out", $HandoffVerifyOut)
    }
    Invoke-HostessCtlStep -Name $Name -Arguments $args -AllowFailure | Out-Null
    Add-Artifact -Role "firewall_rule_report" -ProbeId $ProbeId -Path $outPath
    return $outPath
}

function Add-Artifact {
    param(
        [Parameter(Mandatory=$true)][string]$Role,
        [Parameter(Mandatory=$true)][string]$Path,
        [string]$ProbeId = "",
        [string]$Schema = ""
    )
    $script:Artifacts += [ordered]@{
        role = $Role
        probe_id = $ProbeId
        schema = $Schema
        path = $Path
        exists = (Test-Path $Path)
    }
}

function Add-ProtocolMatrixInput {
    param([Parameter(Mandatory=$true)][string]$Path)
    $script:ProtocolMatrixInputs += $Path
}

function Add-QclReportArtifact {
    param(
        [Parameter(Mandatory=$true)][string]$Role,
        [Parameter(Mandatory=$true)][string]$ProbeId,
        [Parameter(Mandatory=$true)][string]$Path,
        [switch]$ProtocolMatrixInput
    )
    Add-Artifact -Role $Role -ProbeId $ProbeId -Path $Path
    if ($ProtocolMatrixInput) {
        Add-ProtocolMatrixInput -Path $Path
    }
}

function Add-Skip {
    param(
        [Parameter(Mandatory=$true)][string]$Id,
        [Parameter(Mandatory=$true)][string]$Reason
    )
    $script:Skipped += [ordered]@{
        id = $Id
        reason = $Reason
    }
}

function Invoke-QclReportStep {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$ProbeId,
        [Parameter(Mandatory=$true)][string]$OutFileName,
        [Parameter(Mandatory=$true)][string[]]$RunArguments,
        [string]$Role = "connectivity_probe_report",
        [switch]$ProtocolMatrixInput
    )
    $outPath = Join-Path $OutDir $OutFileName
    Invoke-HostessCtlStep -Name $Name -Arguments (@("connectivity-probe", "run") + $RunArguments + @("--out", $outPath)) -AllowFailure | Out-Null
    Add-QclReportArtifact -Role $Role -ProbeId $ProbeId -Path $outPath -ProtocolMatrixInput:$ProtocolMatrixInput
    return $outPath
}

function Get-ArtifactOutcome {
    param([Parameter(Mandatory=$true)][object]$Artifact)
    if (-not $Artifact.exists -or -not (Test-Path $Artifact.path)) {
        return $null
    }
    $json = Get-JsonObject -Path $Artifact.path
    if ($null -eq $json) {
        return $null
    }
    $outcome = ""
    if ($json.PSObject.Properties.Name -contains "report_status" -and -not [string]::IsNullOrWhiteSpace($json.report_status)) {
        $outcome = [string]$json.report_status
    } elseif ($json.PSObject.Properties.Name -contains "status" -and -not [string]::IsNullOrWhiteSpace($json.status)) {
        $outcome = [string]$json.status
    }
    if ([string]::IsNullOrWhiteSpace($outcome)) {
        return $null
    }
    return [ordered]@{
        role = $Artifact.role
        probe_id = $Artifact.probe_id
        path = $Artifact.path
        status = $outcome
    }
}

function Get-StatusArtifactOutcomes {
    param([object[]]$ArtifactOutcomes)

    $afterKeys = @{}
    foreach ($outcome in $ArtifactOutcomes) {
        $path = [string]$outcome.path
        if ($path -match "\.verify\.after\.json$") {
            $key = ([string]$outcome.role) + "|" + ([string]$outcome.probe_id)
            $afterKeys[$key] = $true
        }
    }
    $statusOutcomes = @()
    foreach ($outcome in $ArtifactOutcomes) {
        $path = [string]$outcome.path
        $key = ([string]$outcome.role) + "|" + ([string]$outcome.probe_id)
        if ($path -match "\.verify\.before\.json$" -and $afterKeys.ContainsKey($key)) {
            continue
        }
        $statusOutcomes += $outcome
    }
    return $statusOutcomes
}

$script:RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$script:HostessCtl = Join-Path $script:RepoRoot "tools\hostessctl\hostessctl.py"
if (-not (Test-Path $script:HostessCtl)) {
    throw "hostessctl not found: $script:HostessCtl"
}
if ([string]::IsNullOrWhiteSpace($FirewallProgram)) {
    $FirewallProgram = Join-Path $script:RepoRoot "apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe"
}

if (Test-Path $QuestToolingScript) {
    & $QuestToolingScript | Out-Host
    if (($Adb -eq "adb" -or [string]::IsNullOrWhiteSpace($Adb)) -and $env:RUSTY_XR_ADB) {
        $Adb = $env:RUSTY_XR_ADB
    }
}
if ([string]::IsNullOrWhiteSpace($Serial)) {
    $Serial = Resolve-OneAdbDevice -AdbPath $Adb
}

$runStamp = Get-UtcStamp
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $script:RepoRoot "target\connectivity-probe\rusty-morphospace-streaming-qcl-$runStamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$script:LogDir = Join-Path $OutDir "logs"
New-Item -ItemType Directory -Force -Path $script:LogDir | Out-Null
$script:Steps = @()
$script:Artifacts = @()
$script:Skipped = @()
$script:ProtocolMatrixInputs = @()

Write-RunPhase "output directory: $OutDir"

$makepadApk = Resolve-MakepadApkPath -RepoRoot $script:RepoRoot
$hostessAndroidApk = Join-Path $script:RepoRoot "apps\hostess-t-android\build\rusty-hostess-t.apk"
$manifoldBrokerApk = Join-Path $RustyQuestRoot "target\manifold-broker-android\rusty-manifold-broker.apk"

Write-RunPhase "host dependency check"
if (-not (Test-Path $FirewallProgram) -and -not $SkipBuild -and -not $SkipWpfBuild) {
    Invoke-ProcessStep `
        -Name "build-hostess-companion-wpf-firewall-listener" `
        -File "dotnet" `
        -Arguments @("build", (Join-Path $script:RepoRoot "apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj"), "-c", "Debug") `
        -WorkingDirectory $script:RepoRoot `
        -AllowFailure | Out-Null
} elseif (Test-Path $FirewallProgram) {
    Add-Skip -Id "build-hostess-companion-wpf-firewall-listener" -Reason "Existing WPF companion listener found: $FirewallProgram"
} else {
    Add-Skip -Id "build-hostess-companion-wpf-firewall-listener" -Reason "Skipped by build flags and WPF companion listener is missing: $FirewallProgram"
}

Write-RunPhase "environment scan"
if (-not $SkipEnvironmentScan) {
    $networkProfiles = @()
    $firewallProfiles = @()
    $environmentWarnings = @()
    try {
        $networkProfiles = @(Get-NetConnectionProfile | ForEach-Object {
            [ordered]@{
                name = $_.Name
                interface_alias = $_.InterfaceAlias
                network_category = $_.NetworkCategory.ToString()
                ipv4_connectivity = $_.IPv4Connectivity.ToString()
                ipv6_connectivity = $_.IPv6Connectivity.ToString()
            }
        })
    } catch {
        $environmentWarnings += "Get-NetConnectionProfile failed: $($_.Exception.Message)"
    }
    if (@($networkProfiles | Where-Object { $_.network_category -eq "Public" }).Count -gt 0) {
        $environmentWarnings += "Active Windows network profile is Public; product-scoped listener rules must cover Public, or switch a trusted lab network to Private."
    }
    try {
        $firewallProfiles = @(Get-NetFirewallProfile | ForEach-Object {
            [ordered]@{
                name = $_.Name
                enabled = [bool]$_.Enabled
                default_inbound_action = $_.DefaultInboundAction.ToString()
                default_outbound_action = $_.DefaultOutboundAction.ToString()
                allow_inbound_rules = $_.AllowInboundRules.ToString()
            }
        })
    } catch {
        $environmentWarnings += "Get-NetFirewallProfile failed: $($_.Exception.Message)"
    }
    $headsetSettings = [ordered]@{
        location_mode = "not_checked"
        location_enabled = $false
        qcl041_wifi_direct_ready = $false
    }
    try {
        $locationModeLines = @(& $Adb -s $Serial shell settings get secure location_mode 2>&1)
        $locationMode = (($locationModeLines | Select-Object -First 1) -join "").Trim()
        if ([string]::IsNullOrWhiteSpace($locationMode)) {
            $locationMode = "unknown"
        }
        $locationEnabled = $locationMode -notin @("0", "null", "unknown")
        $headsetSettings.location_mode = $locationMode
        $headsetSettings.location_enabled = [bool]$locationEnabled
        $headsetSettings.qcl041_wifi_direct_ready = [bool]$locationEnabled
        if (-not $locationEnabled) {
            $environmentWarnings += "Quest Location Mode is disabled or unreadable; QCL-041 Wi-Fi Direct peer discovery requires Location Mode before a lifecycle promotion attempt."
        }
    } catch {
        $environmentWarnings += "Quest Location Mode check failed: $($_.Exception.Message)"
    }
    $environmentScan = [ordered]@{
        schema = "rusty.hostess.rusty_morphospace_streaming_environment_scan.v1"
        schema_version = 1
        observed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        adb = $Adb
        serial_redacted = $true
        android_home = $env:ANDROID_HOME
        java_home = $env:JAVA_HOME
        firewall = [ordered]@{
            program = $FirewallProgram
            program_exists = (Test-Path $FirewallProgram)
            profile = $FirewallProfile
            remote_address = $FirewallRemoteAddress
            qcl010_tcp_echo_port = $TcpEchoPort
            qcl080_udp_freshness_port = $UdpFreshnessPort
            qcl082_media_port = $Qcl082MediaPort
            apply_requested = [bool]$ApplyFirewallRules
            elevated_handoff_requested = [bool]$LaunchElevatedFirewallHandoff
        }
        network_profiles = $networkProfiles
        firewall_profiles = $firewallProfiles
        headset_settings = $headsetSettings
        warnings = $environmentWarnings
    }
    $environmentScanPath = Join-Path $OutDir "environment-scan.summary.json"
    ConvertTo-JsonFile -Value $environmentScan -Path $environmentScanPath
    Add-Artifact -Role "environment_scan" -Path $environmentScanPath

    Invoke-ProcessStep -Name "scan-adb-devices" -File $Adb -Arguments @("devices", "-l") -StdoutPath (Join-Path $OutDir "environment-adb-devices.txt") -AllowFailure | Out-Null
    Add-Artifact -Role "environment_scan_raw" -Path (Join-Path $OutDir "environment-adb-devices.txt")
    Invoke-ProcessStep -Name "scan-headset-model" -File $Adb -Arguments @("-s", $Serial, "shell", "getprop", "ro.product.model") -StdoutPath (Join-Path $OutDir "environment-headset-model.txt") -TimeoutSeconds 10 -AllowFailure | Out-Null
    Add-Artifact -Role "environment_scan_raw" -Path (Join-Path $OutDir "environment-headset-model.txt")
    Invoke-ProcessStep -Name "scan-headset-power" -File $Adb -Arguments @("-s", $Serial, "shell", "dumpsys", "power") -StdoutPath (Join-Path $OutDir "environment-headset-power.txt") -TimeoutSeconds 15 -AllowFailure | Out-Null
    Add-Artifact -Role "environment_scan_raw" -Path (Join-Path $OutDir "environment-headset-power.txt")
    Invoke-ProcessStep -Name "scan-headset-foreground" -File $Adb -Arguments @("-s", $Serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|FocusPlaceholder|rustyhostess'") -StdoutPath (Join-Path $OutDir "environment-headset-foreground.txt") -TimeoutSeconds 15 -AllowFailure | Out-Null
    Add-Artifact -Role "environment_scan_raw" -Path (Join-Path $OutDir "environment-headset-foreground.txt")
    Invoke-ProcessStep -Name "scan-headset-location-mode" -File $Adb -Arguments @("-s", $Serial, "shell", "settings", "get", "secure", "location_mode") -StdoutPath (Join-Path $OutDir "environment-headset-location-mode.txt") -TimeoutSeconds 10 -AllowFailure | Out-Null
    Add-Artifact -Role "environment_scan_raw" -Path (Join-Path $OutDir "environment-headset-location-mode.txt")

    Invoke-FirewallRuleReport -Name "firewall-verify-qcl010-tcp-echo-before" -RuleProfile "qcl-010-tcp-echo" -ProbeId "QCL-010" -Action "verify" -OutFileName "firewall-qcl010-tcp-echo.verify.before.json" -Port $TcpEchoPort | Out-Null
    Invoke-FirewallRuleReport -Name "firewall-verify-qcl080-udp-freshness-before" -RuleProfile "qcl-080-udp-freshness" -ProbeId "QCL-080" -Action "verify" -OutFileName "firewall-qcl080-udp-freshness.verify.before.json" -Port $UdpFreshnessPort | Out-Null
    Invoke-FirewallRuleReport -Name "firewall-verify-qcl082-rmanvid1-media-before" -RuleProfile "qcl-082-rmanvid1-media" -ProbeId "QCL-082" -Action "verify" -OutFileName "firewall-qcl082-rmanvid1-media.verify.before.json" -Port $Qcl082MediaPort | Out-Null

    if ($ApplyFirewallRules) {
        $handoffRoot = Join-Path $OutDir "firewall-handoff"
        New-Item -ItemType Directory -Force -Path $handoffRoot | Out-Null
        $qcl010Handoff = Join-Path $handoffRoot "apply-qcl010-tcp-echo.ps1"
        $qcl010HandoffVerify = Join-Path $OutDir "firewall-qcl010-tcp-echo.verify.handoff.json"
        $qcl080Handoff = Join-Path $handoffRoot "apply-qcl080-udp-freshness.ps1"
        $qcl080HandoffVerify = Join-Path $OutDir "firewall-qcl080-udp-freshness.verify.handoff.json"
        $qcl082Handoff = Join-Path $handoffRoot "apply-qcl082-rmanvid1-media.ps1"
        $qcl082HandoffVerify = Join-Path $OutDir "firewall-qcl082-rmanvid1-media.verify.handoff.json"

        Invoke-FirewallRuleReport -Name "firewall-apply-qcl010-tcp-echo" -RuleProfile "qcl-010-tcp-echo" -ProbeId "QCL-010" -Action "apply" -OutFileName "firewall-qcl010-tcp-echo.apply.json" -Port $TcpEchoPort -HandoffScriptOut $qcl010Handoff -HandoffVerifyOut $qcl010HandoffVerify | Out-Null
        Invoke-FirewallRuleReport -Name "firewall-apply-qcl080-udp-freshness" -RuleProfile "qcl-080-udp-freshness" -ProbeId "QCL-080" -Action "apply" -OutFileName "firewall-qcl080-udp-freshness.apply.json" -Port $UdpFreshnessPort -HandoffScriptOut $qcl080Handoff -HandoffVerifyOut $qcl080HandoffVerify | Out-Null
        Invoke-FirewallRuleReport -Name "firewall-apply-qcl082-rmanvid1-media" -RuleProfile "qcl-082-rmanvid1-media" -ProbeId "QCL-082" -Action "apply" -OutFileName "firewall-qcl082-rmanvid1-media.apply.json" -Port $Qcl082MediaPort -HandoffScriptOut $qcl082Handoff -HandoffVerifyOut $qcl082HandoffVerify | Out-Null

        if ($LaunchElevatedFirewallHandoff) {
            $combinedHandoff = Join-Path $handoffRoot "apply-required-firewall-rules.ps1"
            $combinedLines = @(
                "#Requires -RunAsAdministrator",
                "`$ErrorActionPreference = 'Stop'"
            )
            foreach ($handoff in @($qcl010Handoff, $qcl080Handoff, $qcl082Handoff)) {
                if (Test-Path $handoff) {
                    $quoted = "'" + ($handoff -replace "'", "''") + "'"
                    $combinedLines += "& $quoted"
                    $combinedLines += "if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }"
                }
            }
            $combinedLines += "exit 0"
            $combinedLines -join "`n" | Set-Content -Encoding UTF8 -Path $combinedHandoff
            Add-Artifact -Role "firewall_handoff_script" -Path $combinedHandoff
            Invoke-ElevatedPowerShellScriptStep -Name "elevated-apply-required-firewall-rules" -ScriptPath $combinedHandoff -AllowFailure | Out-Null
        } else {
            Add-Skip -Id "elevated-firewall-handoff" -Reason "Firewall apply reports include admin handoff scripts; pass -LaunchElevatedFirewallHandoff to run UAC prompts from the runner."
        }

        Invoke-FirewallRuleReport -Name "firewall-verify-qcl010-tcp-echo-after" -RuleProfile "qcl-010-tcp-echo" -ProbeId "QCL-010" -Action "verify" -OutFileName "firewall-qcl010-tcp-echo.verify.after.json" -Port $TcpEchoPort | Out-Null
        Invoke-FirewallRuleReport -Name "firewall-verify-qcl080-udp-freshness-after" -RuleProfile "qcl-080-udp-freshness" -ProbeId "QCL-080" -Action "verify" -OutFileName "firewall-qcl080-udp-freshness.verify.after.json" -Port $UdpFreshnessPort | Out-Null
        Invoke-FirewallRuleReport -Name "firewall-verify-qcl082-rmanvid1-media-after" -RuleProfile "qcl-082-rmanvid1-media" -ProbeId "QCL-082" -Action "verify" -OutFileName "firewall-qcl082-rmanvid1-media.verify.after.json" -Port $Qcl082MediaPort | Out-Null
    }
} else {
    Add-Skip -Id "environment-scan" -Reason "Skipped by -SkipEnvironmentScan."
}

if ($EnvironmentScanOnly) {
    $failedSteps = @($script:Steps | Where-Object { $_.status -eq "fail" })
    $missingArtifacts = @($script:Artifacts | Where-Object { -not $_.exists })
    $artifactOutcomes = @($script:Artifacts | ForEach-Object { Get-ArtifactOutcome -Artifact $_ } | Where-Object { $null -ne $_ })
    $statusArtifactOutcomes = @(Get-StatusArtifactOutcomes -ArtifactOutcomes $artifactOutcomes)
    $failedArtifacts = @($statusArtifactOutcomes | Where-Object { $_.status -eq "fail" })
    $blockedOrWarnArtifacts = @($statusArtifactOutcomes | Where-Object { $_.status -eq "blocked" -or $_.status -eq "warn" })
    $status = if ($failedSteps.Count -gt 0 -or $failedArtifacts.Count -gt 0) { "fail" } elseif ($missingArtifacts.Count -gt 0 -or $blockedOrWarnArtifacts.Count -gt 0) { "warn" } else { "pass" }
    $report = [ordered]@{
        '$schema' = "rusty.hostess.rusty_morphospace_streaming_qcl_matrix_run.v1"
        schema_version = 1
        status = $status
        run_id = "rusty-morphospace-streaming-environment-scan-$runStamp"
        observed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        out_dir = $OutDir
        environment_scan_only = $true
        serial_redacted = $true
        headset_to_headset_skipped = $true
        artifacts = $script:Artifacts
        artifact_outcomes = $artifactOutcomes
        status_artifact_outcomes = $statusArtifactOutcomes
        steps = $script:Steps
        skipped = $script:Skipped
        summary = [ordered]@{
            step_count = $script:Steps.Count
            failed_step_count = $failedSteps.Count
            artifact_count = $script:Artifacts.Count
            missing_artifact_count = $missingArtifacts.Count
            failed_artifact_count = $failedArtifacts.Count
            blocked_or_warn_artifact_count = $blockedOrWarnArtifacts.Count
            fail_fast = [bool]$FailFast
        }
    }
    $reportPath = Join-Path $OutDir "rusty-morphospace-streaming-environment-scan-run.json"
    ConvertTo-JsonFile -Value $report -Path $reportPath
    Write-Output $reportPath
    if ($status -eq "fail") {
        exit 2
    }
    if ($status -eq "warn") {
        exit 1
    }
    exit 0
}

Write-RunPhase "build and package APKs"
if (-not $SkipBuild -and -not $SkipHostessAndroidBuild) {
    $buildHostessAndroid = Invoke-PowerShellScriptStep `
        -Name "build-hostess-android-helper" `
        -ScriptPath (Join-Path $script:RepoRoot "apps\hostess-t-android\tools\Build-HostessTApk.ps1") `
        -Arguments @("-PackagesRoot", $ManifoldPackagesRoot) `
        -WorkingDirectory $script:RepoRoot `
        -AllowFailure
    $stdout = if (Test-Path $buildHostessAndroid.stdout_path) { Get-Content -Path $buildHostessAndroid.stdout_path } else { @() }
    $candidateApk = $stdout | Where-Object { $_ -match "\.apk$" } | Select-Object -Last 1
    if (-not [string]::IsNullOrWhiteSpace($candidateApk) -and (Test-Path $candidateApk)) {
        $hostessAndroidApk = (Resolve-Path $candidateApk).Path
    }
} elseif ($SkipBuild -or $SkipHostessAndroidBuild) {
    Add-Skip -Id "build-hostess-android-helper" -Reason "Skipped by flag; existing APK will be used if present."
}

if (-not $SkipBuild -and -not $SkipManifoldBrokerBuild) {
    $brokerBuildScript = Join-Path $RustyQuestRoot "tools\Build-ManifoldBrokerAndroid.ps1"
    if (Test-Path $brokerBuildScript) {
        $buildBroker = Invoke-PowerShellScriptStep `
            -Name "build-manifold-broker-android-apk" `
            -ScriptPath $brokerBuildScript `
            -Arguments @("-AndroidHome", $env:ANDROID_HOME, "-JavaHome", $env:JAVA_HOME) `
            -WorkingDirectory $RustyQuestRoot `
            -AllowFailure
        $stdout = if (Test-Path $buildBroker.stdout_path) { Get-Content -Path $buildBroker.stdout_path } else { @() }
        $candidateApk = $stdout | Where-Object { $_ -match "\.apk$" } | Select-Object -Last 1
        if (-not [string]::IsNullOrWhiteSpace($candidateApk) -and (Test-Path $candidateApk)) {
            $manifoldBrokerApk = (Resolve-Path $candidateApk).Path
        }
    } else {
        Add-Skip -Id "build-manifold-broker-android-apk" -Reason "Rusty Quest broker build script not found: $brokerBuildScript"
    }
} elseif ($SkipBuild -or $SkipManifoldBrokerBuild) {
    Add-Skip -Id "build-manifold-broker-android-apk" -Reason "Skipped by flag; existing APK will be used if present."
}

if (-not $SkipBuild -and -not $SkipMakepadBuild) {
    $cargoMakepadPath = Join-Path $MakepadForkRoot "tools\cargo_makepad"
    $cargoMakepadCommand = Get-Command cargo-makepad -ErrorAction SilentlyContinue
    if ($SkipCargoMakepadInstall) {
        Add-Skip -Id "install-cargo-makepad" -Reason "Skipped by -SkipCargoMakepadInstall."
    } elseif ($null -ne $cargoMakepadCommand) {
        Add-Skip -Id "install-cargo-makepad" -Reason "cargo-makepad is already available at $($cargoMakepadCommand.Source)."
    } elseif (Test-Path $cargoMakepadPath) {
        Invoke-ProcessStep `
            -Name "install-cargo-makepad" `
            -File "cargo" `
            -Arguments @("install", "--path", $cargoMakepadPath, "--force") `
            -WorkingDirectory $script:RepoRoot `
            -AllowFailure | Out-Null
    } else {
        Add-Skip -Id "install-cargo-makepad" -Reason "Makepad cargo tool path was not found: $cargoMakepadPath"
    }
    Invoke-ProcessStep `
        -Name "build-rusty-morphospace-streaming-makepad-apk" `
        -File "cargo" `
        -Arguments @(
            "makepad",
            "android",
            "--variant=quest",
            "--abi=aarch64",
            "--sdk-path=$env:ANDROID_HOME",
            "--package-name=$MakepadPackage",
            "--app-label=$StreamingAppLabel",
            "--quest-camera-permissions=$QuestCameraPermissions",
            "build",
            "-p",
            "hostess-t-makepad"
        ) `
        -WorkingDirectory (Join-Path $script:RepoRoot "apps\hostess-t-makepad") `
        -AllowFailure | Out-Null
} elseif ($SkipBuild -or $SkipMakepadBuild) {
    Add-Skip -Id "build-rusty-morphospace-streaming-makepad-apk" -Reason "Skipped by flag; existing APK will be used if present."
}
$makepadApk = Resolve-MakepadApkPath -RepoRoot $script:RepoRoot
$manifoldBrokerApk = Get-FirstExistingPath @(
    $manifoldBrokerApk,
    (Join-Path $RustyQuestRoot "target\manifold-broker-android\rusty-manifold-broker.apk")
)

Write-RunPhase "install APKs and grant permissions"
if (-not $SkipInstall) {
    if (-not $SkipHostessAndroidInstall) {
        if (Test-Path $hostessAndroidApk) {
            Invoke-ProcessStep -Name "install-hostess-android-helper-apk" -File $Adb -Arguments @("-s", $Serial, "install", "-r", $hostessAndroidApk) -AllowFailure | Out-Null
        } else {
            Add-Skip -Id "install-hostess-android-helper-apk" -Reason "Hostess Android helper APK not found: $hostessAndroidApk"
        }
    } else {
        Add-Skip -Id "install-hostess-android-helper-apk" -Reason "Skipped by -SkipHostessAndroidInstall."
    }
    if (Test-Path $makepadApk) {
        Invoke-ProcessStep -Name "install-rusty-morphospace-streaming-apk" -File $Adb -Arguments @("-s", $Serial, "install", "-r", $makepadApk) -AllowFailure | Out-Null
    } else {
        Add-Skip -Id "install-rusty-morphospace-streaming-apk" -Reason "Makepad streaming APK not found: $makepadApk"
    }
    if (-not $SkipManifoldBrokerInstall) {
        if (Test-Path $manifoldBrokerApk) {
            Invoke-ProcessStep -Name "install-manifold-broker-apk" -File $Adb -Arguments @("-s", $Serial, "install", "-r", $manifoldBrokerApk) -AllowFailure | Out-Null
        } else {
            Add-Skip -Id "install-manifold-broker-apk" -Reason "Manifold broker APK not found: $manifoldBrokerApk"
        }
    } else {
        Add-Skip -Id "install-manifold-broker-apk" -Reason "Skipped by -SkipManifoldBrokerInstall."
    }
} else {
    Add-Skip -Id "apk-install" -Reason "Skipped by -SkipInstall."
}

foreach ($grant in @(
    @($HostessAndroidPackage, "android.permission.BLUETOOTH_CONNECT"),
    @($HostessAndroidPackage, "android.permission.BLUETOOTH_SCAN"),
    @($HostessAndroidPackage, "android.permission.BLUETOOTH_ADVERTISE"),
    @($HostessAndroidPackage, "android.permission.ACCESS_FINE_LOCATION"),
    @($HostessAndroidPackage, "android.permission.POST_NOTIFICATIONS"),
    @($MakepadPackage, "android.permission.POST_NOTIFICATIONS"),
    @($BrokerPackage, "android.permission.POST_NOTIFICATIONS"),
    @($BrokerPackage, "android.permission.CAMERA"),
    @($BrokerPackage, "horizonos.permission.HEADSET_CAMERA")
)) {
    Invoke-ProcessStep `
        -Name ("grant-" + (Get-SafeToken ($grant[0] + "-" + $grant[1]))) `
        -File $Adb `
        -Arguments @("-s", $Serial, "shell", "pm", "grant", $grant[0], $grant[1]) `
        -AllowFailure | Out-Null
}

Write-RunPhase "readiness and foreground launch"
$readiness = Join-Path $OutDir "companion-readiness.json"
Invoke-HostessCtlStep -Name "companion-readiness" -Arguments @(
    "companion-readiness",
    "--profile", "hostess-makepad-quest",
    "--require-device",
    "--require-makepad-package",
    "--adb", $Adb,
    "--serial", $Serial,
    "--android-sdk", $env:ANDROID_HOME,
    "--jdk-home", $env:JAVA_HOME,
    "--broker-package", $BrokerPackage,
    "--broker-activity", $BrokerActivity,
    "--makepad-package", $MakepadPackage,
    "--makepad-activity", $MakepadActivity,
    "--out", $readiness
) -AllowFailure | Out-Null
Add-Artifact -Role "companion_readiness" -Path $readiness

Invoke-ProcessStep -Name "wake-headset-before-foreground-launch" -File $Adb -Arguments @(
    "-s", $Serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP"
) -TimeoutSeconds 10 -AllowFailure | Out-Null

Invoke-ProcessStep -Name "launch-rusty-morphospace-streaming-foreground" -File $Adb -Arguments @(
    "-s", $Serial, "shell", "am", "start", "-n", $MakepadActivity
) -TimeoutSeconds 10 -AllowFailure | Out-Null

Invoke-ProcessStep -Name "check-rusty-morphospace-streaming-foreground" -File $Adb -Arguments @(
    "-s", $Serial, "shell", "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp|FocusPlaceholder|rustyhostess'"
) -StdoutPath (Join-Path $OutDir "foreground-after-launch.txt") -TimeoutSeconds 15 -AllowFailure | Out-Null
Add-Artifact -Role "foreground_launch_check" -Path (Join-Path $OutDir "foreground-after-launch.txt")

Write-RunPhase "command authority live session"
$qcl000CompanionSession = Join-Path $OutDir "qcl000-companion-session-live.json"
Invoke-HostessCtlStep -Name "qcl000-live-companion-session-manifold-command" -Arguments @(
    "companion-session",
    "run",
    "--out", $qcl000CompanionSession,
    "--frontend", "makepad",
    "--profile", "hostess-makepad-quest",
    "--adb", $Adb,
    "--serial", $Serial,
    "--android-sdk", $env:ANDROID_HOME,
    "--jdk-home", $env:JAVA_HOME,
    "--broker-package", $BrokerPackage,
    "--broker-activity", $BrokerActivity,
    "--makepad-package", $MakepadPackage,
    "--makepad-activity", $MakepadActivity,
    "--wait-seconds", "8",
    "--authority-wait-seconds", "8",
    "--makepad-process-wait-seconds", "8",
    "--socket-wait-seconds", "8",
    "--launch-settle-seconds", "1"
) -AllowFailure | Out-Null
Add-Artifact -Role "companion_session" -ProbeId "QCL-000" -Path $qcl000CompanionSession
Add-Artifact -Role "device_link_report" -ProbeId "QCL-000" -Path ($qcl000CompanionSession -replace "\.json$", ".device-link.json")

Write-RunPhase "topology preflights"
if (-not $SkipQcl041Preflight) {
    $qcl041Preflight = Join-Path $OutDir "qcl041-live-wifi-direct-preflight.json"
    Invoke-HostessCtlStep -Name "qcl041-live-wifi-direct-preflight" -Arguments @(
        "connectivity-probe",
        "run",
        "--mode", "live",
        "--probe-id", "QCL-041",
        "--adb", $Adb,
        "--serial", $Serial,
        "--out", $qcl041Preflight
    ) -AllowFailure | Out-Null
    Add-Artifact -Role "topology_preflight" -ProbeId "QCL-041" -Path $qcl041Preflight

    $qcl041Plan = Join-Path $OutDir "qcl041-wifi-direct-lifecycle-plan.json"
    $qcl041PlanPreflight = Join-Path $OutDir "qcl041-wifi-direct-lifecycle-plan.preflight.json"
    Invoke-HostessCtlStep -Name "qcl041-wifi-direct-lifecycle-plan" -Arguments @(
        "connectivity-probe",
        "wifi-direct-lifecycle-plan",
        "--probe-id", "QCL-041",
        "--adb", $Adb,
        "--serial", $Serial,
        "--out", $qcl041Plan,
        "--preflight-report-out", $qcl041PlanPreflight
    ) -AllowFailure | Out-Null
    Add-Artifact -Role "topology_lifecycle_plan" -ProbeId "QCL-041" -Path $qcl041Plan
    Add-Skip -Id "qcl041-wifi-direct-lifecycle-plan-preflight-sidecar" -Reason "The lifecycle-plan route records this path as an operator command target; it does not write the preflight sidecar itself."
} else {
    Add-Skip -Id "qcl041-live-wifi-direct-preflight" -Reason "Skipped by -SkipQcl041Preflight."
}

if (-not $SkipQcl030Preflight) {
    $qcl030Script = Join-Path $RustyQuestRoot "tools\Invoke-Qcl030QuestLocalOnlyHotspotProbe.ps1"
    if (Test-Path $qcl030Script) {
        Invoke-PowerShellScriptStep -Name "qcl030-local-only-hotspot-preflight" -ScriptPath $qcl030Script -Arguments @(
            "-Serial", $Serial,
            "-Adb", $Adb,
            "-PreflightOnly",
            "-OutDir", (Join-Path $OutDir "qcl030-local-only-hotspot-preflight")
        ) -AllowFailure | Out-Null
        Add-Artifact -Role "topology_preflight" -ProbeId "QCL-030" -Path (Join-Path $OutDir "qcl030-local-only-hotspot-preflight\summary.json")
    } else {
        Add-Skip -Id "qcl030-local-only-hotspot-preflight" -Reason "Rusty Quest QCL-030 script not found: $qcl030Script"
    }
} else {
    Add-Skip -Id "qcl030-local-only-hotspot-preflight" -Reason "Skipped by -SkipQcl030Preflight."
}

if ($RunQcl041WindowsLifecycle) {
    $qcl041LifecycleScript = Join-Path $RustyQuestRoot "tools\Invoke-Qcl041WifiDirectLifecycle.ps1"
    if (Test-Path $qcl041LifecycleScript) {
        Invoke-PowerShellScriptStep -Name "qcl041-windows-wifi-direct-lifecycle-agent-board-route" -ScriptPath $qcl041LifecycleScript -Arguments @(
            "-Serial", $Serial,
            "-Adb", $Adb,
            "-OutDir", (Join-Path $OutDir "qcl041-windows-wifi-direct-lifecycle"),
            "-WindowsHelperProject", (Join-Path $script:RepoRoot "tools\connectivity_probe\qcl041_wifi_direct_broker\qcl041-wifi-direct-broker.csproj")
        ) -TimeoutSeconds 1200 -AllowFailure | Out-Null
        Add-Artifact -Role "topology_lifecycle_live" -ProbeId "QCL-041" -Path (Join-Path $OutDir "qcl041-windows-wifi-direct-lifecycle\wifi-direct-lifecycle-qcl041-windows.live.json")
    } else {
        Add-Skip -Id "qcl041-windows-wifi-direct-lifecycle" -Reason "Rusty Quest QCL-041 lifecycle script not found: $qcl041LifecycleScript"
    }
} else {
    Add-Skip -Id "qcl041-windows-wifi-direct-lifecycle" -Reason "Skipped by default because that route takes an Agent Board lease; pass -RunQcl041WindowsLifecycle after explicit lease coordination."
}

Write-RunPhase "core QCL rows"
Invoke-QclReportStep -Name "qcl000-usb-adb-command-feedback-fixture" -ProbeId "QCL-000" -OutFileName "qcl000-usb-adb-command-feedback.fixture.json" -RunArguments @(
    "--mode", "fixture",
    "--probe-id", "QCL-000",
    "--fixture-profile", "qcl-000-usb-adb-pass"
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl010-live-router-tcp" -ProbeId "QCL-010" -OutFileName "qcl010-live-router-tcp.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-010",
    "--tcp-echo-port", [string]$TcpEchoPort,
    "--tcp-listener-helper", $FirewallProgram,
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

if ($RunPcHotspotRow -and -not $SkipPcHotspotRow) {
    Invoke-QclReportStep -Name "qcl011-live-pc-hotspot-tcp" -ProbeId "QCL-011" -OutFileName "qcl011-live-pc-hotspot-tcp.json" -RunArguments @(
        "--mode", "live",
        "--probe-id", "QCL-011",
        "--tcp-echo-port", [string]$TcpEchoPort,
        "--tcp-listener-helper", $FirewallProgram,
        "--adb", $Adb,
        "--serial", $Serial
    ) -ProtocolMatrixInput | Out-Null
} elseif ($SkipPcHotspotRow) {
    Add-Skip -Id "qcl011-live-pc-hotspot-tcp" -Reason "Skipped by -SkipPcHotspotRow."
} else {
    Add-Skip -Id "qcl011-live-pc-hotspot-tcp" -Reason "Optional PC-hotspot topology row skipped by default; pass -RunPcHotspotRow after Windows Mobile Hotspot is enabled and the Quest is connected to that hotspot."
}

Invoke-QclReportStep -Name "qcl079-live-websocket-host-loopback" -ProbeId "QCL-079" -OutFileName "qcl079-live-websocket-host-loopback.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-079",
    "--websocket-source", "host-loopback",
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl080-live-makepad-udp" -ProbeId "QCL-080" -OutFileName "qcl080-live-makepad-udp.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-080",
    "--udp-sender-source", "makepad-runtime",
    "--udp-port", [string]$UdpFreshnessPort,
    "--udp-listener-helper", $FirewallProgram,
    "--makepad-package", $MakepadPackage,
    "--makepad-activity", $MakepadActivity,
    "--makepad-launch-timeout-seconds", "30",
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl081-live-lsl-manifold-broker" -ProbeId "QCL-081" -OutFileName "qcl081-live-lsl-manifold-broker.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-081",
    "--lsl-source", "manifold-lsl-broker",
    "--lsl-manifold-root", $ManifoldRoot,
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl082-media-binary-plane-fixture" -ProbeId "QCL-082" -OutFileName "qcl082-media-binary-plane.fixture.json" -RunArguments @(
    "--mode", "fixture",
    "--probe-id", "QCL-082",
    "--fixture-profile", "qcl-082-media-binary-plane-pass"
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl083-live-osc-quest-runtime" -ProbeId "QCL-083" -OutFileName "qcl083-live-osc-quest-runtime.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-083",
    "--osc-source", "quest-runtime",
    "--hostess-android-package", $HostessAndroidPackage,
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

Invoke-QclReportStep -Name "qcl084-live-zeromq-native-rust-broker" -ProbeId "QCL-084" -OutFileName "qcl084-live-native-rust-broker.json" -RunArguments @(
    "--mode", "live",
    "--probe-id", "QCL-084",
    "--zeromq-source", "native-rust-broker",
    "--zeromq-pattern", "pub-sub",
    "--zeromq-manifold-root", $ManifoldRoot,
    "--adb", $Adb,
    "--serial", $Serial
) -ProtocolMatrixInput | Out-Null

Write-RunPhase "bluetooth payload rows"
if (-not $SkipBluetoothPayloadRows) {
    if ($RunQcl050Rfcomm) {
        $qcl050 = Join-Path $OutDir "qcl050-live-rfcomm.json"
        Invoke-HostessCtlStep -Name "qcl050-live-rfcomm" -Arguments @(
            "connectivity-probe",
            "run",
            "--mode", "live",
            "--probe-id", "QCL-050",
            "--bluetooth-payload-source", "android-rfcomm",
            "--hostess-android-package", $HostessAndroidPackage,
            "--adb", $Adb,
            "--serial", $Serial,
            "--out", $qcl050
        ) -AllowFailure | Out-Null
        Add-QclReportArtifact -Role "connectivity_probe_report" -ProbeId "QCL-050" -Path $qcl050 -ProtocolMatrixInput
    } else {
        Add-Skip -Id "qcl050-live-rfcomm" -Reason "Optional Classic Bluetooth RFCOMM row skipped by default; pass -RunQcl050Rfcomm after Windows can discover the Quest RFCOMM service. QCL-051 BLE/GATT remains the standard Bluetooth payload row."
    }

    $qcl051 = Join-Path $OutDir "qcl051-live-ble-gatt.json"
    Invoke-HostessCtlStep -Name "qcl051-live-ble-gatt" -Arguments @(
        "connectivity-probe",
        "run",
        "--mode", "live",
        "--probe-id", "QCL-051",
        "--bluetooth-payload-source", "android-ble-gatt",
        "--bluetooth-reconnect-count", "1",
        "--hostess-android-package", $HostessAndroidPackage,
        "--adb", $Adb,
        "--serial", $Serial,
        "--out", $qcl051
    ) -AllowFailure | Out-Null
    Add-QclReportArtifact -Role "connectivity_probe_report" -ProbeId "QCL-051" -Path $qcl051 -ProtocolMatrixInput
} else {
    Add-Skip -Id "qcl050-qcl051-bluetooth-payload-rows" -Reason "Skipped by -SkipBluetoothPayloadRows."
}

Write-RunPhase "media product plan"
if (-not $SkipQcl082Plan) {
    $qcl082Plan = Join-Path $OutDir "qcl082-product-media-plan.json"
    Invoke-HostessCtlStep -Name "qcl082-product-media-plan" -Arguments @(
        "connectivity-probe",
        "qcl082-product-media-plan",
        "--adb", $Adb,
        "--serial", $Serial,
        "--program", (Join-Path $script:RepoRoot "apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe"),
        "--promoted-topology-report", (Join-Path $OutDir "qcl041-live-wifi-direct-preflight.json"),
        "--out", $qcl082Plan
    ) -AllowFailure | Out-Null
    Add-Artifact -Role "media_product_plan" -ProbeId "QCL-082" -Path $qcl082Plan
} else {
    Add-Skip -Id "qcl082-product-media-plan" -Reason "Skipped by -SkipQcl082Plan."
}

Write-RunPhase "protocol evidence matrix"
if (-not $SkipProtocolMatrix) {
    $matrix = Join-Path $OutDir "protocol-evidence-matrix.json"
    $matrixArgs = @(
        "connectivity-probe",
        "protocol-matrix",
        "--latest-artifact-dir", $OutDir,
        "--latest-device-link-dir", $OutDir,
        "--latest-stream-capability-dir", $OutDir,
        "--latest-stream-probe-id", "QCL-080",
        "--out", $matrix
    )
    foreach ($inputPath in $script:ProtocolMatrixInputs) {
        $matrixArgs += @("--input", $inputPath)
    }
    Invoke-HostessCtlStep -Name "protocol-evidence-matrix" -Arguments $matrixArgs -AllowFailure | Out-Null
    Add-Artifact -Role "protocol_evidence_matrix" -Path $matrix
} else {
    Add-Skip -Id "protocol-evidence-matrix" -Reason "Skipped by -SkipProtocolMatrix."
}

Add-Skip -Id "headset-to-headset-qcl094-qcl095-qcl096-qcl097-qcl100" -Reason "Skipped as requested: no headset-to-headset tests in this run."

$failedSteps = @($script:Steps | Where-Object { $_.status -eq "fail" })
$missingArtifacts = @($script:Artifacts | Where-Object { -not $_.exists })
$artifactOutcomes = @($script:Artifacts | ForEach-Object { Get-ArtifactOutcome -Artifact $_ } | Where-Object { $null -ne $_ })
$statusArtifactOutcomes = @(Get-StatusArtifactOutcomes -ArtifactOutcomes $artifactOutcomes)
$failedArtifacts = @($statusArtifactOutcomes | Where-Object { $_.status -eq "fail" })
$blockedOrWarnArtifacts = @($statusArtifactOutcomes | Where-Object { $_.status -eq "blocked" -or $_.status -eq "warn" })
$status = if ($failedSteps.Count -gt 0 -or $failedArtifacts.Count -gt 0) { "fail" } elseif ($missingArtifacts.Count -gt 0 -or $blockedOrWarnArtifacts.Count -gt 0) { "warn" } else { "pass" }
$temporarySidecarRows = @("QCL-051", "QCL-083")
if ($RunQcl050Rfcomm -and -not $SkipBluetoothPayloadRows) {
    $temporarySidecarRows = @("QCL-050") + $temporarySidecarRows
}

$report = [ordered]@{
    '$schema' = "rusty.hostess.rusty_morphospace_streaming_qcl_matrix_run.v1"
    schema_version = 1
    status = $status
    run_id = "rusty-morphospace-streaming-qcl-$runStamp"
    observed_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    out_dir = $OutDir
    adb_serial_provided = -not [string]::IsNullOrWhiteSpace($Serial)
    serial_redacted = $true
    headset_to_headset_skipped = $true
    matrix_options = [ordered]@{
        run_pc_hotspot_row = [bool]$RunPcHotspotRow
        run_qcl050_rfcomm = [bool]$RunQcl050Rfcomm
        run_qcl041_windows_lifecycle = [bool]$RunQcl041WindowsLifecycle
        skip_bluetooth_payload_rows = [bool]$SkipBluetoothPayloadRows
        skip_protocol_matrix = [bool]$SkipProtocolMatrix
        optional_topology_rows = @("QCL-011", "QCL-050")
    }
    app_contract = [ordered]@{
        foreground_streaming_app = [ordered]@{
            label = $StreamingAppLabel
            package = $MakepadPackage
            activity = $MakepadActivity
            source = "apps/hostess-t-makepad"
            role = "Quest foreground streaming/projection activity for app-owned UDP, Manifold command/runtime receipts, and Makepad stream rendering."
        }
        infrastructure = [ordered]@{
            hostessctl = $script:HostessCtl
            manifold_root = $ManifoldRoot
            command_authority = "rusty.manifold.command"
            execution_owner = "rusty.hostess.connectivity_probe"
            manifold_broker = [ordered]@{
                package = $BrokerPackage
                activity = $BrokerActivity
                apk = $manifoldBrokerApk
                role = "Quest-side Manifold command broker required for QCL-000 WebSocket command-route promotion and broker-owned transport proofs."
            }
        }
        host_firewall = [ordered]@{
            program = $FirewallProgram
            profile = $FirewallProfile
            remote_address = $FirewallRemoteAddress
            qcl010_tcp_echo_port = $TcpEchoPort
            qcl080_udp_freshness_port = $UdpFreshnessPort
            qcl082_media_port = $Qcl082MediaPort
            apply_requested = [bool]$ApplyFirewallRules
            elevated_handoff_requested = [bool]$LaunchElevatedFirewallHandoff
        }
        temporary_sidecar_helpers = @(
            [ordered]@{
                package = $HostessAndroidPackage
                activity = "$HostessAndroidPackage/.MainActivity"
                source = "apps/hostess-t-android"
                rows = $temporarySidecarRows
                optional_rows = @("QCL-050")
                fold_in_note = "Java Android API probes still run as a helper sidecar until their Android Bluetooth/OSC endpoints are folded into the streaming app package; QCL-050 RFCOMM is opt-in because BLE/GATT is the standard Bluetooth payload row."
            }
        )
    }
    artifacts = $script:Artifacts
    protocol_matrix_inputs = $script:ProtocolMatrixInputs
    artifact_outcomes = $artifactOutcomes
    status_artifact_outcomes = $statusArtifactOutcomes
    steps = $script:Steps
    skipped = $script:Skipped
    summary = [ordered]@{
        step_count = $script:Steps.Count
        failed_step_count = $failedSteps.Count
        artifact_count = $script:Artifacts.Count
        missing_artifact_count = $missingArtifacts.Count
        failed_artifact_count = $failedArtifacts.Count
        blocked_or_warn_artifact_count = $blockedOrWarnArtifacts.Count
        fail_fast = [bool]$FailFast
    }
}

$reportPath = Join-Path $OutDir "rusty-morphospace-streaming-qcl-matrix-run.json"
ConvertTo-JsonFile -Value $report -Path $reportPath
Write-Output $reportPath
if ($status -eq "fail") {
    exit 2
}
if ($status -eq "warn") {
    exit 1
}
exit 0
