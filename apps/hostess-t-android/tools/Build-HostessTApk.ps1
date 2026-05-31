param(
    [Parameter(Mandatory=$true)]
    [string]$PackagesRoot,

    [string]$AndroidHome = $env:ANDROID_HOME,
    [string]$NdkRoot = $(if ($env:ANDROID_NDK_ROOT) { $env:ANDROID_NDK_ROOT } else { $env:ANDROID_NDK_HOME }),
    [string]$JavaHome = $env:JAVA_HOME,
    [string]$OutDir = "",
    [string]$Keystore = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($AndroidHome)) {
    throw "ANDROID_HOME or -AndroidHome is required."
}
if ([string]::IsNullOrWhiteSpace($JavaHome)) {
    throw "JAVA_HOME or -JavaHome is required."
}
if ([string]::IsNullOrWhiteSpace($NdkRoot)) {
    throw "ANDROID_NDK_ROOT, ANDROID_NDK_HOME, or -NdkRoot is required."
}

$projectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$repoRoot = Split-Path -Parent (Split-Path -Parent $projectRoot)
if ([string]::IsNullOrWhiteSpace($OutDir)) {
    $OutDir = Join-Path $projectRoot "build"
}

$buildTools = Join-Path $AndroidHome "build-tools\36.0.0"
$platformJar = Join-Path $AndroidHome "platforms\android-34\android.jar"
$aapt2 = Join-Path $buildTools "aapt2.exe"
$d8 = Join-Path $buildTools "d8.bat"
$zipalign = Join-Path $buildTools "zipalign.exe"
$apksigner = Join-Path $buildTools "apksigner.bat"
$javac = Join-Path $JavaHome "bin\javac.exe"
$jar = Join-Path $JavaHome "bin\jar.exe"
$keytool = Join-Path $JavaHome "bin\keytool.exe"

foreach ($tool in @($platformJar, $aapt2, $d8, $zipalign, $apksigner, $javac, $jar, $keytool)) {
    if (-not (Test-Path $tool)) {
        throw "Required tool not found: $tool"
    }
}

$classesDir = Join-Path $OutDir "classes"
$dexDir = Join-Path $OutDir "dex"
$assetsDir = Join-Path $OutDir "assets"
$nativeTargetDir = Join-Path $OutDir "native-target"
$nativeLibRoot = Join-Path $OutDir "native-libs"
$classesJar = Join-Path $OutDir "classes.jar"
$apkUnsigned = Join-Path $OutDir "hostess-t-unsigned.apk"
$apkUnaligned = Join-Path $OutDir "hostess-t-unaligned.apk"
$apkAligned = Join-Path $OutDir "hostess-t-aligned.apk"
$apkSigned = Join-Path $OutDir "rusty-hostess-t.apk"
if ([string]::IsNullOrWhiteSpace($Keystore)) {
    $Keystore = Join-Path $env:USERPROFILE ".rusty-hostess\hostess-t-debug.keystore"
}

Remove-Item -Recurse -Force $OutDir -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $classesDir, $dexDir, $assetsDir | Out-Null

$packageSource = Join-Path $PackagesRoot "packages\polar-h10"
if (-not (Test-Path $packageSource) -and (Split-Path -Leaf $PackagesRoot) -eq "polar-h10") {
    $packageSource = $PackagesRoot
}
if (-not (Test-Path (Join-Path $packageSource "manifests\package.manifold.json"))) {
    throw "Could not find polar-h10 package manifests under $PackagesRoot"
}

$assetPackageRoot = Join-Path $assetsDir "manifold\packages\polar-h10"
New-Item -ItemType Directory -Force -Path $assetPackageRoot | Out-Null
Copy-Item -Recurse -Force (Join-Path $packageSource "manifests") $assetPackageRoot
$assetFixtureRoot = Join-Path $assetPackageRoot "fixtures\valid"
New-Item -ItemType Directory -Force -Path $assetFixtureRoot | Out-Null
Copy-Item -Force (Join-Path $packageSource "fixtures\valid\graph.json") $assetFixtureRoot
Copy-Item -Force (Join-Path $packageSource "fixtures\valid\processor-runtime-input-synthetic.json") $assetFixtureRoot

$llvmBin = Join-Path $NdkRoot "toolchains\llvm\prebuilt\windows-x86_64\bin"
$androidLinker = Join-Path $llvmBin "aarch64-linux-android29-clang.cmd"
if (-not (Test-Path $androidLinker)) {
    throw "Android Rust linker not found: $androidLinker"
}
$oldTargetDir = $env:CARGO_TARGET_DIR
$oldLinker = $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER
try {
    $env:CARGO_TARGET_DIR = $nativeTargetDir
    $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER = $androidLinker
    & cargo build --manifest-path (Join-Path $packageSource "crates\polar-h10-core\Cargo.toml") --target aarch64-linux-android --release
    if ($LASTEXITCODE -ne 0) { throw "cargo Android native build failed with exit code $LASTEXITCODE" }
} finally {
    $env:CARGO_TARGET_DIR = $oldTargetDir
    $env:CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER = $oldLinker
}
$nativeSo = Join-Path $nativeTargetDir "aarch64-linux-android\release\libpolar_h10_core.so"
if (-not (Test-Path $nativeSo)) {
    throw "Native Rust library not found after build: $nativeSo"
}
$nativeAbiDir = Join-Path $nativeLibRoot "lib\arm64-v8a"
New-Item -ItemType Directory -Force -Path $nativeAbiDir | Out-Null
Copy-Item -Force $nativeSo (Join-Path $nativeAbiDir "libpolar_h10_core.so")

$sourceFiles = Get-ChildItem -Path (Join-Path $projectRoot "src\main\java") -Recurse -Filter *.java | ForEach-Object { $_.FullName }
$sourceList = Join-Path $OutDir "sources.rsp"
$sourceFiles | Set-Content -Encoding ASCII -Path $sourceList
& $javac -source 17 -target 17 -classpath $platformJar -d $classesDir "@$sourceList"
if ($LASTEXITCODE -ne 0) { throw "javac failed with exit code $LASTEXITCODE" }

& $jar cf $classesJar -C $classesDir .
if ($LASTEXITCODE -ne 0) { throw "jar class pack failed with exit code $LASTEXITCODE" }

& $d8 --lib $platformJar --output $dexDir $classesJar
if ($LASTEXITCODE -ne 0) { throw "d8 failed with exit code $LASTEXITCODE" }

& $aapt2 link `
    -o $apkUnsigned `
    --manifest (Join-Path $projectRoot "AndroidManifest.xml") `
    -I $platformJar `
    -A $assetsDir `
    --min-sdk-version 29 `
    --target-sdk-version 34 `
    --version-code 1 `
    --version-name 0.1.0
if ($LASTEXITCODE -ne 0) { throw "aapt2 link failed with exit code $LASTEXITCODE" }

Copy-Item $apkUnsigned $apkUnaligned
& $jar uf $apkUnaligned -C $dexDir classes.dex
if ($LASTEXITCODE -ne 0) { throw "jar update failed with exit code $LASTEXITCODE" }
& $jar uf $apkUnaligned -C $nativeLibRoot lib
if ($LASTEXITCODE -ne 0) { throw "jar native lib update failed with exit code $LASTEXITCODE" }

& $zipalign -f 4 $apkUnaligned $apkAligned
if ($LASTEXITCODE -ne 0) { throw "zipalign failed with exit code $LASTEXITCODE" }

if (-not (Test-Path $Keystore)) {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Keystore) | Out-Null
    & $keytool -genkeypair -v `
        -keystore $Keystore `
        -storepass android `
        -keypass android `
        -alias androiddebugkey `
        -keyalg RSA `
        -keysize 2048 `
        -validity 10000 `
        -dname "CN=Rusty Hostess T,O=Rusty Hostess,C=US" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "keytool failed with exit code $LASTEXITCODE" }
}

& $apksigner sign `
    --ks $Keystore `
    --ks-pass pass:android `
    --key-pass pass:android `
    --out $apkSigned `
    $apkAligned
if ($LASTEXITCODE -ne 0) { throw "apksigner failed with exit code $LASTEXITCODE" }

Write-Output $apkSigned
