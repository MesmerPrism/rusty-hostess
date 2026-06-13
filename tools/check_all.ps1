$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name,
        [Parameter(Mandatory=$true)]
        [string]$File,
        [string[]]$Arguments = @()
    )

    & $File @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Push-Location $RepoRoot
try {
    $PythonFiles = @(
        "tools\hostessctl\hostessctl.py",
        "tools\hostessctl\android_files.py",
        "tools\hostessctl\broker_transport.py",
        "tools\hostessctl\cli_parser.py",
        "tools\hostessctl\manifold_recording.py",
        "tools\hostessctl\pmb_broker_bridge.py",
        "tools\hostessctl\pmb_evidence.py",
        "tools\hostessctl\recording_evidence.py",
        "tools\hostessctl\telemetry_render.py",
        "tools\capture_window_printwindow.py",
        "tools\telemetry_snapshot.py",
        "tools\telemetry_stream.py",
        "tools\check_makepad_quest_gpu_evidence.py",
        "tools\check_makepad_quest_live_recorded_ab.py",
        "tools\summarize_makepad_quest_gpu_evidence.py",
        "tools\test_telemetry_snapshot.py",
        "tools\test_check_makepad_quest_gpu_evidence.py",
        "tools\test_check_makepad_quest_live_recorded_ab.py",
        "tools\test_hostessctl_cli_parser.py",
        "tools\test_summarize_makepad_quest_gpu_evidence.py",
        "tools\test_hostessctl_pmb_replay.py"
    ) | Where-Object { Test-Path $_ }
    if ($PythonFiles.Count -gt 0) {
        Invoke-Checked "python compile" "python" (@("-m", "py_compile") + $PythonFiles)
    }
    if (Test-Path "tools\test_telemetry_snapshot.py") {
        Invoke-Checked "python unit tests" "python" @("-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py")
    }
    $PackagesRootCandidate = Join-Path $RepoRoot "..\rusty-manifold-packages"
    $PmbPackageRootCandidate = Join-Path $PackagesRootCandidate "packages\projected-motion-breath"
    if (Test-Path $PmbPackageRootCandidate) {
        $PackagesRoot = Resolve-Path $PackagesRootCandidate
        $PmbReplayOut = Join-Path $RepoRoot "target\hostess-pmb-desktop-replay\pmb-desktop-replay.json"
        New-Item -ItemType Directory -Force -Path (Split-Path $PmbReplayOut) | Out-Null
        Invoke-Checked "PMB desktop replay execution" "python" @(
            "tools\hostessctl\hostessctl.py",
            "run-pmb-replay",
            "--target",
            "desktop",
            "--packages-root",
            $PackagesRoot.Path,
            "--out",
            $PmbReplayOut
        )
    }
    if (Test-Path "apps\hostess-t-makepad\Cargo.toml") {
        Invoke-Checked "Makepad app cargo check" "cargo" @("check", "--manifest-path", "apps\hostess-t-makepad\Cargo.toml")
    }
    $AdapterLib = "apps\hostess-t-android\native\polar-runtime-jni\src\lib.rs"
    if ((Test-Path $AdapterLib) -and (Test-Path $PackagesRootCandidate)) {
        Invoke-Checked "Android JNI adapter format" "rustfmt" @("--check", $AdapterLib)
        $PackagesRoot = Resolve-Path (Join-Path $RepoRoot "..\rusty-manifold-packages")
        $PolarCorePath = Resolve-Path (Join-Path $PackagesRoot "packages\polar-h10\crates\polar-h10-core")
        $AdapterCheckRoot = Join-Path $env:TEMP "hostess-polar-runtime-jni-check"
        New-Item -ItemType Directory -Force -Path $AdapterCheckRoot | Out-Null
        $AdapterManifest = Join-Path $AdapterCheckRoot "Cargo.toml"
        $AdapterLibPathForCargo = (Resolve-Path $AdapterLib).Path -replace "\\", "/"
        $PolarCorePathForCargo = $PolarCorePath.Path -replace "\\", "/"
        @(
            "[package]",
            'name = "hostess-polar-runtime-jni-check"',
            'version = "0.1.0"',
            'edition = "2021"',
            'publish = false',
            "",
            "[lib]",
            'name = "hostess_polar_runtime_jni_check"',
            "path = `"$AdapterLibPathForCargo`"",
            'crate-type = ["rlib"]',
            "",
            "[dependencies]",
            'jni = "0.21"',
            "polar-h10-core = { path = `"$PolarCorePathForCargo`" }",
            'serde_json = "1"'
        ) | Set-Content -Encoding ASCII -Path $AdapterManifest
        Invoke-Checked "Android JNI adapter cargo check" "cargo" @("check", "--manifest-path", $AdapterManifest)
    }
    $PmbAdapterLib = "apps\hostess-t-android\native\pmb-runtime-jni\src\lib.rs"
    if ((Test-Path $PmbAdapterLib) -and (Test-Path $PackagesRootCandidate)) {
        Invoke-Checked "Android PMB JNI adapter format" "rustfmt" @("--check", $PmbAdapterLib)
        $PackagesRoot = Resolve-Path (Join-Path $RepoRoot "..\rusty-manifold-packages")
        $PmbCorePath = Resolve-Path (Join-Path $PackagesRoot "packages\projected-motion-breath\crates\projected-motion-breath-core")
        $PmbAdapterCheckRoot = Join-Path $env:TEMP "hostess-pmb-runtime-jni-check"
        New-Item -ItemType Directory -Force -Path $PmbAdapterCheckRoot | Out-Null
        $PmbAdapterManifest = Join-Path $PmbAdapterCheckRoot "Cargo.toml"
        $PmbAdapterLibPathForCargo = (Resolve-Path $PmbAdapterLib).Path -replace "\\", "/"
        $PmbCorePathForCargo = $PmbCorePath.Path -replace "\\", "/"
        @(
            "[package]",
            'name = "hostess-pmb-runtime-jni-check"',
            'version = "0.1.0"',
            'edition = "2021"',
            'publish = false',
            "",
            "[lib]",
            'name = "hostess_pmb_runtime_jni_check"',
            "path = `"$PmbAdapterLibPathForCargo`"",
            'crate-type = ["rlib"]',
            "",
            "[dependencies]",
            'jni = "0.21"',
            "projected-motion-breath-core = { path = `"$PmbCorePathForCargo`" }",
            'serde_json = "1"'
        ) | Set-Content -Encoding ASCII -Path $PmbAdapterManifest
        Invoke-Checked "Android PMB JNI adapter cargo check" "cargo" @("check", "--manifest-path", $PmbAdapterManifest)
    }
} finally {
    Pop-Location
}
