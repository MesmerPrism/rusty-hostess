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
        "tools\hostessctl\android_artifacts.py",
        "tools\hostessctl\android_files.py",
        "tools\hostessctl\bridge_command_android_routes.py",
        "tools\hostessctl\bridge_command_live_android_routes.py",
        "tools\hostessctl\bridge_command_routes.py",
        "tools\hostessctl\bridge_route_evidence.py",
        "tools\hostessctl\broker_telemetry_routes.py",
        "tools\hostessctl\broker_transport.py",
        "tools\hostessctl\cli_parser.py",
        "tools\hostessctl\companion_catalog.py",
        "tools\hostessctl\companion_readiness.py",
        "tools\hostessctl\companion_session.py",
        "tools\hostessctl\connectivity_probe.py",
        "tools\hostessctl\live_capture_routes.py",
        "tools\hostessctl\makepad_pmb_setup.py",
        "tools\hostessctl\manifold_recording.py",
        "tools\hostessctl\native_breathing_room_setup.py",
        "tools\hostessctl\platform_defaults.py",
        "tools\hostessctl\pmb_android_routes.py",
        "tools\hostessctl\pmb_broker_bridge.py",
        "tools\hostessctl\pmb_desktop_routes.py",
        "tools\hostessctl\pmb_evidence.py",
        "tools\hostessctl\pmb_host_run_evidence.py",
        "tools\hostessctl\pmb_native_receipts.py",
        "tools\hostessctl\pmb_support.py",
        "tools\hostessctl\questionnaire_bridge.py",
        "tools\hostessctl\recording_evidence.py",
        "tools\hostessctl\runtime.py",
        "tools\hostessctl\telemetry_render.py",
        "tools\hostessctl\telemetry_routes.py",
        "tools\capture_window_printwindow.py",
        "tools\telemetry_snapshot.py",
        "tools\telemetry_stream.py",
        "tools\check_makepad_quest_gpu_evidence.py",
        "tools\makepad_quest_gpu_evidence\__init__.py",
        "tools\makepad_quest_gpu_evidence\proof_lines.py",
        "tools\makepad_quest_gpu_evidence\force_authority.py",
        "tools\check_makepad_quest_live_recorded_ab.py",
        "tools\summarize_makepad_quest_gpu_evidence.py",
        "tools\studio_staging_request.py",
        "tools\studio_staging\request_cli.py",
        "tools\studio_staging\request_cli_parser.py",
        "tools\studio_staging\request_cli_validation.py",
        "tools\studio_staging\pmb_release.py",
        "tools\studio_staging\pmb_validation_handoff.py",
        "tools\studio_staging\pmb_replay_validation.py",
        "tools\studio_staging\operator_release.py",
        "tools\test_telemetry_snapshot.py",
        "tools\test_check_makepad_quest_gpu_evidence.py",
        "tools\test_check_makepad_quest_live_recorded_ab.py",
        "tools\test_hostessctl_cli_parser.py",
        "tools\test_hostessctl_bridge_command_android.py",
        "tools\test_hostessctl_bridge_command_live_android.py",
        "tools\test_hostessctl_bridge_command.py",
        "tools\test_hostessctl_bridge_route_evidence.py",
        "tools\test_hostessctl_companion_catalog.py",
        "tools\test_hostessctl_companion_readiness.py",
        "tools\test_hostessctl_companion_session.py",
        "tools\test_hostessctl_connectivity_probe.py",
        "tools\test_hostessctl_questionnaire_bridge.py",
        "tools\test_summarize_makepad_quest_gpu_evidence.py",
        "tools\test_hostessctl_pmb_replay.py"
    ) | Where-Object { Test-Path $_ }
    if ($PythonFiles.Count -gt 0) {
        Invoke-Checked "python compile" "python" (@("-m", "py_compile") + $PythonFiles)
    }
    if (Test-Path "tools\test_telemetry_snapshot.py") {
        Invoke-Checked "python unit tests" "python" @("-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py")
    }
    $GuiDescriptorRootCandidate = Join-Path $RepoRoot "..\rusty-gui\fixtures\descriptors"
    if (Test-Path $GuiDescriptorRootCandidate) {
        $CatalogOut = Join-Path $RepoRoot "target\companion-catalog\check-all-catalog.json"
        New-Item -ItemType Directory -Force -Path (Split-Path $CatalogOut) | Out-Null
        Invoke-Checked "companion catalog descriptor smoke" "python" @(
            "tools\hostessctl\hostessctl.py",
            "companion-catalog",
            "--out",
            $CatalogOut,
            "--frontend",
            "wpf",
            "--fail-on-error"
        )
    }
    if (Test-Path "apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj") {
        Invoke-Checked "WPF companion build" "dotnet" @("build", "apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj")
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
    $AndroidJavaRoot = "apps\hostess-t-android\src\main\java"
    if (Test-Path $AndroidJavaRoot) {
        $AndroidHome = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } else { "S:\Work\tools\Android\windows-sdk" }
        $JavaHome = if ($env:JAVA_HOME) { $env:JAVA_HOME } else { "S:\Work\tools\Java\temurin-17" }
        $PlatformJar = Join-Path $AndroidHome "platforms\android-34\android.jar"
        $Javac = Join-Path $JavaHome "bin\javac.exe"
        if ((Test-Path $PlatformJar) -and (Test-Path $Javac)) {
            $JavaCheckRoot = Join-Path $env:TEMP "hostess-android-java-check"
            Remove-Item -Recurse -Force $JavaCheckRoot -ErrorAction SilentlyContinue
            New-Item -ItemType Directory -Force -Path $JavaCheckRoot | Out-Null
            $SourceList = Join-Path $JavaCheckRoot "sources.rsp"
            Get-ChildItem -Path $AndroidJavaRoot -Recurse -Filter *.java |
                ForEach-Object { $_.FullName } |
                Set-Content -Encoding ASCII -Path $SourceList
            Invoke-Checked "Android Java source compile" $Javac @(
                "-source",
                "17",
                "-target",
                "17",
                "-classpath",
                $PlatformJar,
                "-d",
                $JavaCheckRoot,
                "@$SourceList"
            )
        } else {
            Write-Host "[SKIP] Android Java source compile: missing $PlatformJar or $Javac"
        }
    }
    if (Test-Path "apps\hostess-t-makepad\Cargo.toml") {
        Invoke-Checked "Makepad app cargo check" "cargo" @("check", "--manifest-path", "apps\hostess-t-makepad\Cargo.toml")
        Invoke-Checked "Makepad app Hostess contract serde tests" "cargo" @("test", "--manifest-path", "apps\hostess-t-makepad\Cargo.toml", "--features", "serde", "hostess_contracts")
        Invoke-Checked "Makepad app shell regression tests" "cargo" @("test", "--manifest-path", "apps\hostess-t-makepad\Cargo.toml", "--features", "serde", "main_tests")
    }
    $AdapterLib = "apps\hostess-t-android\native\polar-runtime-jni\src\lib.rs"
    if ((Test-Path $AdapterLib) -and (Test-Path $PackagesRootCandidate)) {
        Invoke-Checked "Android JNI adapter format" "rustfmt" @("--check", $AdapterLib)
        $PackagesRoot = Resolve-Path (Join-Path $RepoRoot "..\rusty-manifold-packages")
        $PolarCorePath = Resolve-Path (Join-Path $PackagesRoot "packages\polar-h10\crates\polar-h10-core")
        $AdapterCheckRoot = Join-Path $env:TEMP "hostess-polar-runtime-jni-check"
        Remove-Item -Recurse -Force $AdapterCheckRoot -ErrorAction SilentlyContinue
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
        Remove-Item -Recurse -Force $PmbAdapterCheckRoot -ErrorAction SilentlyContinue
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
