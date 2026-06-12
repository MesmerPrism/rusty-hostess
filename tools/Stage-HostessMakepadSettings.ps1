param(
    [Parameter(Mandatory=$true)]
    [string]$BundleDir,
    [string]$Package = "io.github.mesmerprism.rustyhostess.makepad",
    [string]$Adb = $env:RUSTY_XR_ADB,
    [string]$RemoteTmp = "/data/local/tmp/rusty-hostess-makepad-settings-staging",
    [string]$InternalSettingsDir = "files/hostess-t/settings",
    [string]$ReportOut = "",
    [switch]$DryRun,
    [switch]$KeepRemoteTmp
)

$ErrorActionPreference = "Stop"

function Resolve-ToolPath {
    param(
        [string]$PathValue,
        [string]$DefaultPath
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        $PathValue = $DefaultPath
    }
    return (Resolve-Path $PathValue).Path
}

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

function Assert-SafeRemoteTmp {
    param([string]$Path)

    if (-not $Path.StartsWith("/data/local/tmp/")) {
        throw "RemoteTmp must stay under /data/local/tmp/: $Path"
    }
    if ($Path.Length -le "/data/local/tmp/".Length) {
        throw "RemoteTmp must name a child directory under /data/local/tmp"
    }
    if ($Path.Contains("..")) {
        throw "RemoteTmp must not contain '..': $Path"
    }
}

function Assert-SafeInternalSettingsDir {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "InternalSettingsDir must not be empty"
    }
    if ($Path.StartsWith("/") -or $Path.Contains("..")) {
        throw "InternalSettingsDir must be a run-as relative app files path: $Path"
    }
}

function Add-Payload {
    param(
        [System.Collections.ArrayList]$Payloads,
        [string]$Source,
        [string]$RelativePath,
        [string]$Role
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Missing $Role payload: $Source"
    }
    [void]$Payloads.Add([ordered]@{
        source = (Resolve-Path $Source).Path
        relative_path = $RelativePath
        role = $Role
        size_bytes = (Get-Item -LiteralPath $Source).Length
    })
}

function Get-Sha256HexForText {
    param([string]$Text)

    $Sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return (($Sha.ComputeHash($Bytes) | ForEach-Object { $_.ToString("x2") }) -join "")
    } finally {
        $Sha.Dispose()
    }
}

function Select-ScopeSettingIds {
    param(
        [object[]]$Settings,
        [string[]]$ExactIds,
        [string[]]$Prefixes
    )

    $Rows = foreach ($Setting in $Settings) {
        $SettingId = [string]$Setting.setting_id
        $ExactMatch = $ExactIds -contains $SettingId
        $PrefixMatch = $false
        foreach ($Prefix in $Prefixes) {
            if ($SettingId.StartsWith($Prefix)) {
                $PrefixMatch = $true
                break
            }
        }
        if ($ExactMatch -or $PrefixMatch) {
            [ordered]@{
                setting_id = $SettingId
                value = $Setting.value
                hotload_policy = $Setting.hotload_policy
                writer_policy = $Setting.writer_policy
            }
        }
    }
    return @($Rows | Sort-Object { $_["setting_id"] })
}

function New-SettingsScopeRevision {
    param(
        [string]$Scope,
        [object[]]$Settings,
        [string[]]$ExactIds = @(),
        [string[]]$Prefixes = @()
    )

    $Rows = Select-ScopeSettingIds -Settings $Settings -ExactIds $ExactIds -Prefixes $Prefixes
    $ScopePayload = [ordered]@{
        scope = $Scope
        settings = @($Rows)
    }
    $ScopeJson = $ScopePayload | ConvertTo-Json -Depth 10 -Compress
    [ordered]@{
        revision_hash_sha256 = Get-Sha256HexForText $ScopeJson
        setting_count = @($Rows).Count
        setting_ids = @($Rows | ForEach-Object { $_["setting_id"] })
    }
}

function Write-EffectiveSettingsRevisionManifest {
    param(
        [string]$Source,
        [string]$Out
    )

    $SourceItem = Get-Item -LiteralPath $Source
    $Text = Get-Content -LiteralPath $Source -Raw
    $Report = $Text | ConvertFrom-Json
    $Settings = @($Report.settings)
    $Manifest = [ordered]@{
        schema = "rusty.gui.makepad.effective_settings_revision.v1"
        generated_at = (Get-Date).ToUniversalTime().ToString("o")
        source_file = "makepad-effective-settings.json"
        source_size_bytes = $SourceItem.Length
        source_sha256 = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
        app_id = $Report.app_id
        surface_schema = $Report.surface_schema
        surface_version = $Report.surface_version
        source_revision = $Report.revision
        invalidation_policy = [ordered]@{
            global_gate = "source_sha256_or_source_revision"
            scope_gate = "revision_hash_sha256"
            detail_read = "only_after_relevant_scope_changed"
            watcher_events_are_hints = $true
            high_rate_payload_in_settings_json = $false
        }
        scopes = [ordered]@{
            mesh_replay = New-SettingsScopeRevision `
                -Scope "mesh_replay" `
                -Settings $Settings `
                -Prefixes @("makepad.mesh_replay.")
            camera_projection = New-SettingsScopeRevision `
                -Scope "camera_projection" `
                -Settings $Settings `
                -ExactIds @("makepad.render.scale", "makepad.camera.streaming.enabled") `
                -Prefixes @("makepad.projection.")
            matter_surface = New-SettingsScopeRevision `
                -Scope "matter_surface" `
                -Settings $Settings `
                -ExactIds @("makepad.collision.enabled", "makepad.sdf_adf.overlay_mode") `
                -Prefixes @("makepad.matter.surface_runtime.", "makepad.sdf.slice.", "makepad.adf.debug.", "makepad.sdf_adf.debug.")
            particles = New-SettingsScopeRevision `
                -Scope "particles" `
                -Settings $Settings `
                -Prefixes @("makepad.particles.")
        }
    }
    $Manifest | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Out -Encoding UTF8
}

function Remote-Parent {
    param([string]$RemoteFile)

    $index = $RemoteFile.LastIndexOf("/")
    if ($index -lt 0) {
        return "."
    }
    return $RemoteFile.Substring(0, $index)
}

$DefaultAdb = "S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe"
$ResolvedAdb = Resolve-ToolPath -PathValue $Adb -DefaultPath $DefaultAdb
$ResolvedBundleDir = (Resolve-Path $BundleDir).Path
Assert-SafeRemoteTmp $RemoteTmp
Assert-SafeInternalSettingsDir $InternalSettingsDir

$Payloads = New-Object System.Collections.ArrayList
$GeneratedPayloadDir = Join-Path ([System.IO.Path]::GetTempPath()) "rusty-hostess-makepad-settings-staging"
New-Item -ItemType Directory -Force -Path $GeneratedPayloadDir | Out-Null
$EffectiveSettingsSource = Join-Path $ResolvedBundleDir "effective-settings.json"
$EffectiveSettingsRevisionManifest = Join-Path $GeneratedPayloadDir "makepad-effective-settings.revision.json"
Write-EffectiveSettingsRevisionManifest -Source $EffectiveSettingsSource -Out $EffectiveSettingsRevisionManifest
Add-Payload -Payloads $Payloads `
    -Source $EffectiveSettingsSource `
    -RelativePath "makepad-effective-settings.json" `
    -Role "effective-settings"
Add-Payload -Payloads $Payloads `
    -Source $EffectiveSettingsRevisionManifest `
    -RelativePath "makepad-effective-settings.revision.json" `
    -Role "effective-settings-revision"

$MeshReplayDir = Join-Path $ResolvedBundleDir "mesh-replay"
if (Test-Path -LiteralPath $MeshReplayDir -PathType Container) {
    $MeshReplayRoot = (Resolve-Path $MeshReplayDir).Path
    foreach ($File in Get-ChildItem -LiteralPath $MeshReplayRoot -Recurse -File) {
        $Relative = $File.FullName.Substring($MeshReplayRoot.Length).TrimStart("\", "/")
        $Relative = "mesh-replay/" + ($Relative -replace "\\", "/")
        Add-Payload -Payloads $Payloads -Source $File.FullName -RelativePath $Relative -Role "mesh-replay"
    }
}

foreach ($CaptureFile in @(
    "left.rig.json",
    "left.clip.jsonl",
    "right.rig.json",
    "right.clip.jsonl"
)) {
    $CapturePath = Join-Path $ResolvedBundleDir $CaptureFile
    if (Test-Path -LiteralPath $CapturePath -PathType Leaf) {
        Add-Payload -Payloads $Payloads -Source $CapturePath -RelativePath $CaptureFile -Role "recorded-hand-capture"
    }
}

if ([string]::IsNullOrWhiteSpace($ReportOut)) {
    $ReportOut = Join-Path $ResolvedBundleDir "hostess-makepad-settings-stage-report.json"
}

$Report = [ordered]@{
    schema = "rusty.hostess.makepad_settings_stage_report.v1"
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    dry_run = [bool]$DryRun
    package = $Package
    adb = $ResolvedAdb
    bundle_dir = $ResolvedBundleDir
    remote_tmp = $RemoteTmp
    internal_settings_dir = $InternalSettingsDir
    keep_remote_tmp = [bool]$KeepRemoteTmp
    payload_count = $Payloads.Count
    payloads = @($Payloads)
    boundary = [ordered]@{
        app_visible_runtime_root = $InternalSettingsDir
        adb_handoff_tmp_root = "/data/local/tmp"
        external_android_data_used = $false
        settings_json_payload = "source selection and low-rate profile values only"
        settings_revision_manifest = "makepad-effective-settings.revision.json"
        settings_invalidation_policy = "global revision/hash gate, scoped revision/hash gate, then detailed JSON read"
        high_rate_payload_in_settings_json = $false
    }
}

if (-not $DryRun) {
    Invoke-Checked "clear remote staging directory" $ResolvedAdb @("shell", "rm", "-rf", $RemoteTmp)
    Invoke-Checked "create remote staging directory" $ResolvedAdb @("shell", "mkdir", "-p", $RemoteTmp)

    foreach ($Payload in @($Payloads)) {
        $RemoteFile = "$RemoteTmp/$($Payload.relative_path)"
        $RemoteParent = Remote-Parent $RemoteFile
        Invoke-Checked "create remote payload parent $RemoteParent" $ResolvedAdb @(
            "shell", "mkdir", "-p", $RemoteParent
        )
        Invoke-Checked "push $($Payload.relative_path)" $ResolvedAdb @(
            "push", [string]$Payload.source, $RemoteFile
        )
    }

    Invoke-Checked "make remote staging readable by run-as app copy" $ResolvedAdb @(
        "shell", "chmod", "-R", "755", $RemoteTmp
    )

    Invoke-Checked "clear internal staged payload" $ResolvedAdb @(
        "shell", "run-as", $Package, "rm", "-rf", $InternalSettingsDir
    )
    Invoke-Checked "create internal settings directory" $ResolvedAdb @(
        "shell", "run-as", $Package, "mkdir", "-p", $InternalSettingsDir
    )
    Invoke-Checked "copy staged payload into app-private files" $ResolvedAdb @(
        "shell", "run-as", $Package, "cp", "-R", "$RemoteTmp/.", "$InternalSettingsDir/"
    )

    $ListOutput = & $ResolvedAdb @(
        "shell", "run-as", $Package, "ls", "-lR", $InternalSettingsDir
    )
    if ($LASTEXITCODE -ne 0) {
        throw "list internal staged payload failed with exit code $LASTEXITCODE"
    }
    $Report["internal_listing"] = @($ListOutput)

    if (-not $KeepRemoteTmp) {
        Invoke-Checked "remove remote staging directory" $ResolvedAdb @("shell", "rm", "-rf", $RemoteTmp)
    }
}

$Report | ConvertTo-Json -Depth 8 | Set-Content -Path $ReportOut -Encoding UTF8
Write-Output "Hostess Makepad settings staging report: $ReportOut"
if ($DryRun) {
    Write-Output "Dry run only; no ADB writes performed."
} else {
    Write-Output "Hostess Makepad settings staged for $Package at $InternalSettingsDir"
}
