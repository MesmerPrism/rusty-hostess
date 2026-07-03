param(
    [string]$Out = "",
    [int]$SampleCount = 16,
    [int]$TimeoutSeconds = 8,
    [int]$CrateTestTimeoutSeconds = 420,
    [string]$RlslVersion = "0.0.5",
    [switch]$SkipCrateTests
)

$ErrorActionPreference = "Stop"

function Invoke-CapturedProcess {
    param(
        [Parameter(Mandatory=$true)]
        [string]$File,
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments,
        [int]$TimeoutMilliseconds = 30000,
        [string]$WorkingDirectory = (Get-Location).Path
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $File
    foreach ($arg in $Arguments) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true

    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $timedOut = -not $process.WaitForExit($TimeoutMilliseconds)
    if ($timedOut) {
        $process.Kill($true)
        [void]$process.WaitForExit(5000)
    } else {
        $process.WaitForExit()
    }

    [ordered]@{
        exit_code = if ($timedOut) { $null } else { $process.ExitCode }
        timed_out = $timedOut
        stdout = $stdoutTask.GetAwaiter().GetResult()
        stderr = $stderrTask.GetAwaiter().GetResult()
    }
}

function Start-CapturedProcess {
    param(
        [Parameter(Mandatory=$true)]
        [string]$File,
        [Parameter(Mandatory=$true)]
        [string[]]$Arguments,
        [string]$WorkingDirectory = (Get-Location).Path
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $File
    foreach ($arg in $Arguments) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()

    [pscustomobject]@{
        process = $process
        stdout_task = $stdoutTask
        stderr_task = $stderrTask
    }
}

function Stop-CapturedProcess {
    param([Parameter(Mandatory=$true)]$Process)

    $target = if ($Process.PSObject.Properties["process"]) { $Process.process } else { $Process }
    if (-not $target.HasExited) {
        $target.Kill($true)
        [void]$target.WaitForExit(5000)
    } else {
        $target.WaitForExit()
    }

    [ordered]@{
        exit_code = if ($target.HasExited) { $target.ExitCode } else { $null }
        stdout = if ($Process.PSObject.Properties["stdout_task"]) { $Process.stdout_task.GetAwaiter().GetResult() } else { $target.StandardOutput.ReadToEnd() }
        stderr = if ($Process.PSObject.Properties["stderr_task"]) { $Process.stderr_task.GetAwaiter().GetResult() } else { $target.StandardError.ReadToEnd() }
    }
}

function Find-RlslCrate {
    param([Parameter(Mandatory=$true)][string]$Version)

    $registry = Join-Path $env:USERPROFILE ".cargo\registry\src"
    if (-not (Test-Path $registry)) {
        return $null
    }
    Get-ChildItem -LiteralPath $registry -Recurse -Directory -Filter "rlsl-$Version" |
        Select-Object -First 1
}

function Limit-Text {
    param([string]$Text, [int]$Max = 1600)
    if ($null -eq $Text) {
        return ""
    }
    if ($Text.Length -le $Max) {
        return $Text
    }
    return $Text.Substring(0, $Max)
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
if (-not $Out) {
    $Out = Join-Path $repoRoot "target\connectivity-probe\qcl081-pure-rust-rlsl-smoke.json"
}
New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null

$observedAt = (Get-Date).ToUniversalTime().ToString("o")
$rlslCrate = Find-RlslCrate -Version $RlslVersion
if ($null -eq $rlslCrate) {
    [void](Invoke-CapturedProcess -File "cargo" -Arguments @("info", "rlsl") -TimeoutMilliseconds 120000 -WorkingDirectory $repoRoot)
    $rlslCrate = Find-RlslCrate -Version $RlslVersion
}
if ($null -eq $rlslCrate) {
    throw "Could not locate rlsl-$RlslVersion in the Cargo registry after cargo info."
}

$manifest = Join-Path $rlslCrate.FullName "Cargo.toml"
$checks = New-Object System.Collections.ArrayList

$pylslCheck = Invoke-CapturedProcess -File "python" -Arguments @(
    "-c",
    "import json, pylsl; print(json.dumps({'pylsl_version': getattr(pylsl, '__version__', 'unknown'), 'liblsl_version': pylsl.library_version()}))"
) -TimeoutMilliseconds 30000 -WorkingDirectory $repoRoot
$pylslInfo = $null
if ($pylslCheck.exit_code -eq 0) {
    $pylslInfo = $pylslCheck.stdout | ConvertFrom-Json
}
[void]$checks.Add([ordered]@{
    name = "dependency.pylsl_import"
    status = if ($pylslCheck.exit_code -eq 0) { "pass" } else { "blocked" }
    evidence = if ($pylslInfo) { "pylsl=$($pylslInfo.pylsl_version), liblsl=$($pylslInfo.liblsl_version)" } else { Limit-Text $pylslCheck.stderr }
})

if (-not $SkipCrateTests) {
    $crateTests = Invoke-CapturedProcess -File "cargo" -Arguments @(
        "test",
        "--manifest-path",
        $manifest
    ) -TimeoutMilliseconds ($CrateTestTimeoutSeconds * 1000) -WorkingDirectory $repoRoot
    [void]$checks.Add([ordered]@{
        name = "dependency.rlsl_crate_tests"
        status = if ($crateTests.exit_code -eq 0) { "pass" } elseif ($crateTests.timed_out) { "blocked" } else { "fail" }
        evidence = if ($crateTests.exit_code -eq 0) { "cargo test rlsl passed" } else { Limit-Text ($crateTests.stderr + "`n" + $crateTests.stdout) }
    })
} else {
    [void]$checks.Add([ordered]@{
        name = "dependency.rlsl_crate_tests"
        status = "skipped"
        evidence = "Skipped by -SkipCrateTests"
    })
}

$rlslOutletProcess = Start-CapturedProcess -File "cargo" -Arguments @(
    "run",
    "--manifest-path",
    $manifest,
    "--example",
    "send_data",
    "--quiet"
) -WorkingDirectory $repoRoot
$rlslOutletStopped = $null
$rlslToPylsl = $null
try {
    Start-Sleep -Seconds 5
    $receiverCode = @"
import json, time
from pylsl import StreamInlet, resolve_byprop, local_clock
start = time.perf_counter()
streams = resolve_byprop('name', 'RustSender', minimum=1, timeout=float($TimeoutSeconds))
result = {'streams_found': len(streams), 'samples': [], 'status': 'blocked'}
if streams:
    info = streams[0]
    result.update({
        'name': info.name(),
        'type': info.type(),
        'source_id': info.source_id(),
        'channel_count': info.channel_count(),
        'nominal_srate': info.nominal_srate(),
    })
    inlet = StreamInlet(info, max_buflen=8)
    for _ in range(int($SampleCount)):
        sample, ts = inlet.pull_sample(timeout=2.0)
        if sample is not None:
            result['samples'].append({'sample': sample, 'timestamp': ts, 'host_clock': local_clock()})
    result['status'] = 'pass' if len(result['samples']) == int($SampleCount) else 'warn'
result['elapsed_ms'] = int((time.perf_counter() - start) * 1000)
print(json.dumps(result))
"@
    $receiver = Invoke-CapturedProcess -File "python" -Arguments @("-c", $receiverCode) -TimeoutMilliseconds (($TimeoutSeconds + 10) * 1000) -WorkingDirectory $repoRoot
    if ($receiver.exit_code -eq 0 -and $receiver.stdout.Trim()) {
        $rlslToPylsl = $receiver.stdout | ConvertFrom-Json
    } else {
        $rlslToPylsl = [ordered]@{
            status = "blocked"
            stdout = Limit-Text $receiver.stdout
            stderr = Limit-Text $receiver.stderr
        }
    }
} finally {
    $rlslOutletStopped = Stop-CapturedProcess -Process $rlslOutletProcess
}

[void]$checks.Add([ordered]@{
    name = "interop.rlsl_outlet_to_pylsl_inlet"
    status = if ($rlslToPylsl.status -eq "pass") { "pass" } else { "blocked" }
    evidence = if ($rlslToPylsl.status -eq "pass") { "$($rlslToPylsl.samples.Count)/$SampleCount samples via pylsl from rlsl outlet" } else { "pylsl did not receive the requested rlsl samples" }
})

$producerCode = @"
import time
from pylsl import StreamInfo, StreamOutlet
info = StreamInfo('PyLslToRlsl', 'EEG', 8, 250.0, 'float32', 'pylsl-to-rlsl')
outlet = StreamOutlet(info)
i = 0
while True:
    outlet.push_sample([float(i)] * 8)
    i += 1
    time.sleep(0.004)
"@
$pylslOutletProcess = Start-CapturedProcess -File "python" -Arguments @("-c", $producerCode) -WorkingDirectory $repoRoot
$rlslInletProcess = $null
$pylslOutletStopped = $null
$rlslInletStopped = $null
try {
    Start-Sleep -Seconds 2
    $rlslInletProcess = Start-CapturedProcess -File "cargo" -Arguments @(
        "run",
        "--manifest-path",
        $manifest,
        "--example",
        "receive_data",
        "--quiet"
    ) -WorkingDirectory $repoRoot
    Start-Sleep -Seconds $TimeoutSeconds
} finally {
    if ($rlslInletProcess) {
        $rlslInletStopped = Stop-CapturedProcess -Process $rlslInletProcess
    }
    $pylslOutletStopped = Stop-CapturedProcess -Process $pylslOutletProcess
}

$rlslInletLines = @()
if ($rlslInletStopped) {
    $rlslInletLines = @($rlslInletStopped.stdout -split "\r?\n")
}
$rlslFound = ($rlslInletLines | Where-Object { $_ -like "Found: name=PyLslToRlsl*" } | Select-Object -First 1)
$rlslSamples = @($rlslInletLines | Where-Object { $_ -like "t=*" })
$pylslToRlsl = [ordered]@{
    status = if ($rlslFound -and $rlslSamples.Count -ge $SampleCount) { "pass" } else { "blocked" }
    stream_found = [bool]$rlslFound
    found_line = if ($rlslFound) { $rlslFound } else { "" }
    samples_received = $rlslSamples.Count
    stdout_excerpt = Limit-Text (($rlslInletLines | Select-Object -First 24) -join "`n")
    stderr_excerpt = if ($rlslInletStopped) { Limit-Text $rlslInletStopped.stderr } else { "" }
}
[void]$checks.Add([ordered]@{
    name = "interop.pylsl_outlet_to_rlsl_inlet"
    status = $pylslToRlsl.status
    evidence = if ($pylslToRlsl.status -eq "pass") { "$($pylslToRlsl.samples_received) samples via rlsl from pylsl outlet" } else { "rlsl did not receive the requested pylsl samples" }
})

$rlslOutletToRlslProcess = Start-CapturedProcess -File "cargo" -Arguments @(
    "run",
    "--manifest-path",
    $manifest,
    "--example",
    "send_data",
    "--quiet"
) -WorkingDirectory $repoRoot
$rlslInletForRlslProcess = $null
$rlslOutletToRlslStopped = $null
$rlslInletForRlslStopped = $null
try {
    Start-Sleep -Seconds 2
    $rlslInletForRlslProcess = Start-CapturedProcess -File "cargo" -Arguments @(
        "run",
        "--manifest-path",
        $manifest,
        "--example",
        "receive_data",
        "--quiet"
    ) -WorkingDirectory $repoRoot
    Start-Sleep -Seconds $TimeoutSeconds
} finally {
    if ($rlslInletForRlslProcess) {
        $rlslInletForRlslStopped = Stop-CapturedProcess -Process $rlslInletForRlslProcess
    }
    $rlslOutletToRlslStopped = Stop-CapturedProcess -Process $rlslOutletToRlslProcess
}

$rlslToRlslInletLines = @()
if ($rlslInletForRlslStopped) {
    $rlslToRlslInletLines = @($rlslInletForRlslStopped.stdout -split "\r?\n")
}
$rlslToRlslFound = ($rlslToRlslInletLines | Where-Object { $_ -like "Found: name=RustSender*" } | Select-Object -First 1)
$rlslToRlslSamples = @($rlslToRlslInletLines | Where-Object { $_ -like "t=*" })
$rlslToRlsl = [ordered]@{
    status = if ($rlslToRlslFound -and $rlslToRlslSamples.Count -ge $SampleCount) { "pass" } else { "blocked" }
    stream_found = [bool]$rlslToRlslFound
    found_line = if ($rlslToRlslFound) { $rlslToRlslFound } else { "" }
    samples_received = $rlslToRlslSamples.Count
    stdout_excerpt = Limit-Text (($rlslToRlslInletLines | Select-Object -First 24) -join "`n")
    stderr_excerpt = if ($rlslInletForRlslStopped) { Limit-Text $rlslInletForRlslStopped.stderr } else { "" }
}
[void]$checks.Add([ordered]@{
    name = "interop.rlsl_outlet_to_rlsl_inlet"
    status = $rlslToRlsl.status
    evidence = if ($rlslToRlsl.status -eq "pass") { "$($rlslToRlsl.samples_received) samples via rlsl from rlsl outlet" } else { "rlsl did not receive the requested rlsl samples" }
})

$failed = @($checks | Where-Object { $_.status -notin @("pass", "skipped") })
$report = [ordered]@{
    schema = "rusty.hostess.qcl081_pure_rust_rlsl_probe.v1"
    observed_at_utc = $observedAt
    status = if ($failed.Count -eq 0) { "pass" } else { "blocked" }
    promotion_allowed = $false
    promotion_reason = "Pure-Rust rlsl is candidate-only until licensing, maintenance, and Quest/direct-Wi-Fi behavior are accepted."
    crate = [ordered]@{
        name = "rlsl"
        version = $RlslVersion
        license = "GPL-3.0-only"
        repository = "https://github.com/eugenehp/rlsl"
        manifest = $manifest
        crate_test_timeout_seconds = $CrateTestTimeoutSeconds
    }
    official_lsl = [ordered]@{
        pylsl_version = if ($pylslInfo) { $pylslInfo.pylsl_version } else { $null }
        liblsl_version = if ($pylslInfo) { $pylslInfo.liblsl_version } else { $null }
    }
    checks = $checks
    rlsl_outlet_to_pylsl_inlet = $rlslToPylsl
    pylsl_outlet_to_rlsl_inlet = $pylslToRlsl
    rlsl_outlet_to_rlsl_inlet = $rlslToRlsl
    process_output = [ordered]@{
        rlsl_outlet_stdout = Limit-Text $rlslOutletStopped.stdout
        rlsl_outlet_stderr = Limit-Text $rlslOutletStopped.stderr
        pylsl_outlet_stdout = Limit-Text $pylslOutletStopped.stdout
        pylsl_outlet_stderr = Limit-Text $pylslOutletStopped.stderr
        rlsl_to_rlsl_outlet_stdout = Limit-Text $rlslOutletToRlslStopped.stdout
        rlsl_to_rlsl_outlet_stderr = Limit-Text $rlslOutletToRlslStopped.stderr
        rlsl_to_rlsl_inlet_stdout = Limit-Text $rlslInletForRlslStopped.stdout
        rlsl_to_rlsl_inlet_stderr = Limit-Text $rlslInletForRlslStopped.stderr
    }
}

$report | ConvertTo-Json -Depth 24 | Set-Content -Encoding UTF8 -LiteralPath $Out
Write-Host $Out
if ($report.status -ne "pass") {
    exit 1
}
