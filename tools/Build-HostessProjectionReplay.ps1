param(
    [string]$Glslc = $env:GLSLC,
    [switch]$Debug
)
$ErrorActionPreference = 'Stop'

function Find-Glslc {
    param([string]$ExplicitPath)

    if (-not [string]::IsNullOrWhiteSpace($ExplicitPath) -and
        (Test-Path -LiteralPath $ExplicitPath)) {
        return (Resolve-Path -LiteralPath $ExplicitPath).Path
    }
    $command = Get-Command glslc -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }
    foreach ($environmentName in @('ANDROID_NDK_HOME', 'ANDROID_NDK_ROOT')) {
        $root = [Environment]::GetEnvironmentVariable($environmentName)
        if (-not [string]::IsNullOrWhiteSpace($root)) {
            $candidate = Join-Path $root 'shader-tools\windows-x86_64\glslc.exe'
            if (Test-Path -LiteralPath $candidate) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($env:ANDROID_HOME)) {
        $ndkRoot = Join-Path $env:ANDROID_HOME 'ndk'
        if (Test-Path -LiteralPath $ndkRoot) {
            $candidate = Get-ChildItem -LiteralPath $ndkRoot -Directory |
                Sort-Object Name -Descending |
                ForEach-Object {
                    Join-Path $_.FullName 'shader-tools\windows-x86_64\glslc.exe'
                } |
                Where-Object { Test-Path -LiteralPath $_ } |
                Select-Object -First 1
            if ($null -ne $candidate) {
                return (Resolve-Path -LiteralPath $candidate).Path
            }
        }
    }
    throw 'glslc was not found. Set GLSLC or install an Android NDK shader toolchain.'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $repoRoot 'apps\hostess-projection-replay'
$shaderOut = Join-Path $repoRoot 'target\hostess-projection-replay\shaders'
New-Item -ItemType Directory -Force -Path $shaderOut | Out-Null
$glslcPath = Find-Glslc -ExplicitPath $Glslc
$source = Join-Path $appRoot 'shaders\fullscreen_triangle.vert.glsl'
$output = Join-Path $shaderOut 'fullscreen_triangle.vert.spv'
& $glslcPath '--target-env=vulkan1.1' '-fshader-stage=vertex' $source '-o' $output
if ($LASTEXITCODE -ne 0) {
    throw "glslc failed with exit code $LASTEXITCODE"
}

$cargoArguments = @('build', '--manifest-path', (Join-Path $appRoot 'Cargo.toml'))
if (-not $Debug) {
    $cargoArguments += '--release'
}
& cargo @cargoArguments
if ($LASTEXITCODE -ne 0) {
    throw "cargo build failed with exit code $LASTEXITCODE"
}

[ordered]@{
    schema = 'rusty.hostess.projection_replay_build.v1'
    glslc = $glslcPath
    fullscreen_vertex_spirv = (Resolve-Path -LiteralPath $output).Path
    fullscreen_vertex_sha256 = (
        Get-FileHash -Algorithm SHA256 -LiteralPath $output
    ).Hash.ToLowerInvariant()
    cargo_profile = if ($Debug) { 'debug' } else { 'release' }
    executable = if ($Debug) {
        Join-Path $appRoot 'target\debug\hostess-projection-replay.exe'
    } else {
        Join-Path $appRoot 'target\release\hostess-projection-replay.exe'
    }
} | ConvertTo-Json -Depth 4
