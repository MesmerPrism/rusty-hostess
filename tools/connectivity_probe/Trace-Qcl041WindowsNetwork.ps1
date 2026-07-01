param(
    [Parameter(Mandatory=$true)]
    [string]$RunId,
    [Parameter(Mandatory=$true)]
    [string]$OutDir,
    [int]$ListenPort = 18768,
    [int]$DurationSeconds = 120,
    [int]$SampleIntervalMilliseconds = 1000,
    [switch]$CaptureAllPackets
)

$ErrorActionPreference = "Stop"

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Write-JsonFile {
    param(
        [Parameter(Mandatory=$true)]
        [object]$Value,
        [Parameter(Mandatory=$true)]
        [string]$Path
    )
    $Value | ConvertTo-Json -Depth 64 | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Invoke-CaptureCommand {
    param(
        [Parameter(Mandatory=$true)]
        [string]$Name,
        [Parameter(Mandatory=$true)]
        [scriptblock]$Command,
        [Parameter(Mandatory=$true)]
        [string]$Path
    )
    try {
        & $Command 2>&1 | Out-String -Width 240 | Set-Content -LiteralPath $Path -Encoding UTF8
        return [pscustomobject]@{ name = $Name; status = "pass"; path = $Path; error = $null }
    } catch {
        $_ | Out-String | Set-Content -LiteralPath $Path -Encoding UTF8
        return [pscustomobject]@{ name = $Name; status = "blocked"; path = $Path; error = $_.Exception.Message }
    }
}

function Select-ObjectProperties {
    param(
        [object[]]$InputObject,
        [string[]]$Properties
    )
    $rows = @()
    foreach ($item in @($InputObject)) {
        if ($null -eq $item) {
            continue
        }
        $row = [ordered]@{}
        foreach ($property in $Properties) {
            $row[$property] = $item.$property
        }
        $rows += [pscustomobject]$row
    }
    return $rows
}

function Get-Snapshot {
    param([int]$Index)
    $tcpConnections = @(Get-NetTCPConnection -ErrorAction SilentlyContinue |
        Where-Object {
            $_.LocalPort -eq $ListenPort -or
            $_.RemotePort -eq $ListenPort -or
            $_.LocalAddress -like "192.168.137.*" -or
            $_.RemoteAddress -like "192.168.137.*"
        })
    return [pscustomobject]@{
        schema = "rusty.hostess.windows.qcl041_network_trace_sample.v1"
        run_id = $RunId
        sample_index = $Index
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        adapters = Select-ObjectProperties -InputObject @(Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue) -Properties @(
            "Name", "InterfaceDescription", "ifIndex", "Status", "MacAddress", "LinkSpeed", "MediaConnectionState"
        )
        ip_addresses = Select-ObjectProperties -InputObject @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue) -Properties @(
            "InterfaceAlias", "InterfaceIndex", "IPAddress", "PrefixLength", "AddressState", "Type"
        )
        routes = Select-ObjectProperties -InputObject @(Get-NetRoute -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.DestinationPrefix -eq "0.0.0.0/0" -or $_.DestinationPrefix -like "192.168.137.*" }) -Properties @(
            "DestinationPrefix", "InterfaceAlias", "InterfaceIndex", "NextHop", "RouteMetric", "Protocol", "State"
        )
        tcp = Select-ObjectProperties -InputObject $tcpConnections -Properties @(
            "LocalAddress", "LocalPort", "RemoteAddress", "RemotePort", "State", "OwningProcess", "AppliedSetting"
        )
        neighbors = Select-ObjectProperties -InputObject @(Get-NetNeighbor -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -like "192.168.137.*" }) -Properties @(
            "InterfaceAlias", "InterfaceIndex", "IPAddress", "LinkLayerAddress", "State"
        )
        connection_profiles = Select-ObjectProperties -InputObject @(Get-NetConnectionProfile -ErrorAction SilentlyContinue) -Properties @(
            "Name", "InterfaceAlias", "InterfaceIndex", "NetworkCategory", "IPv4Connectivity", "IPv6Connectivity"
        )
        firewall_profiles = Select-ObjectProperties -InputObject @(Get-NetFirewallProfile -ErrorAction SilentlyContinue) -Properties @(
            "Name", "Enabled", "DefaultInboundAction", "DefaultOutboundAction", "LogAllowed", "LogBlocked", "LogFileName"
        )
    }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path -LiteralPath $OutDir).Path
$summaryPath = Join-Path $OutDir "qcl041-windows-network-trace-summary.json"
$samplesPath = Join-Path $OutDir "qcl041-windows-network-trace-samples.jsonl"
$pktmonEtlPath = Join-Path $OutDir "qcl041-pktmon.etl"
$pktmonTextPath = Join-Path $OutDir "qcl041-pktmon.txt"
$pktmonPcapPath = Join-Path $OutDir "qcl041-pktmon.pcapng"
$pktmonCountersPath = Join-Path $OutDir "qcl041-pktmon-counters.json"
$netshTracePath = Join-Path $OutDir "qcl041-netsh-trace.etl"
$readyPath = Join-Path $OutDir "qcl041-windows-network-trace-ready.json"

$events = @()
$captures = @()
$startedPktmon = $false
$startedNetsh = $false
$isAdmin = Test-Admin

try {
    $ready = [pscustomobject]@{
        schema = "rusty.hostess.windows.qcl041_network_trace_ready.v1"
        run_id = $RunId
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        elevated = $isAdmin
        out_dir = $OutDir
        listen_port = $ListenPort
        duration_seconds = $DurationSeconds
        capture_all_packets = [bool]$CaptureAllPackets
    }
    Write-JsonFile -Value $ready -Path $readyPath

    if (-not $isAdmin) {
        throw "Trace-Qcl041WindowsNetwork.ps1 must run elevated."
    }

    $captures += Invoke-CaptureCommand "whoami_groups" { whoami /groups } (Join-Path $OutDir "whoami-groups.txt")
    $captures += Invoke-CaptureCommand "ipconfig_all" { ipconfig /all } (Join-Path $OutDir "ipconfig-all.txt")
    $captures += Invoke-CaptureCommand "route_print_ipv4" { route print -4 } (Join-Path $OutDir "route-print-ipv4.txt")
    $captures += Invoke-CaptureCommand "netsh_wlan_interfaces" { netsh wlan show interfaces } (Join-Path $OutDir "netsh-wlan-interfaces.txt")
    $captures += Invoke-CaptureCommand "netsh_wlan_drivers" { netsh wlan show drivers } (Join-Path $OutDir "netsh-wlan-drivers.txt")
    $captures += Invoke-CaptureCommand "netsh_advfirewall_profiles" { netsh advfirewall show allprofiles } (Join-Path $OutDir "netsh-advfirewall-profiles.txt")
    $captures += Invoke-CaptureCommand "netstat_before" { netstat -ano -p tcp } (Join-Path $OutDir "netstat-before.txt")
    $captures += Invoke-CaptureCommand "firewall_rules_qcl041" {
        Get-NetFirewallRule -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like "*qcl041*" -or $_.DisplayName -like "*Wi-Fi Direct*" -or $_.DisplayName -like "*Wifi Direct*" } |
            Get-NetFirewallPortFilter -ErrorAction SilentlyContinue
    } (Join-Path $OutDir "firewall-rules-qcl041.txt")

    try {
        pktmon stop | Out-Null
    } catch {}
    try {
        pktmon filter remove | Out-Null
        if ($CaptureAllPackets) {
            $events += [pscustomobject]@{ name = "pktmon_filter"; status = "pass"; path = $null; error = "no filter; capture all packet events" }
        } else {
            pktmon filter add -p $ListenPort | Out-Null
            $events += [pscustomobject]@{ name = "pktmon_filter"; status = "pass"; path = $null; error = "port=$ListenPort" }
        }
        pktmon start --capture --comp all --type all --pkt-size 0 --file-name $pktmonEtlPath | Out-Null
        $startedPktmon = $true
        $events += [pscustomobject]@{ name = "pktmon_start"; status = "pass"; path = $pktmonEtlPath; error = $null }
    } catch {
        $events += [pscustomobject]@{ name = "pktmon_start"; status = "blocked"; path = $pktmonEtlPath; error = $_.Exception.Message }
    }

    try {
        netsh trace start scenario=NetConnection capture=yes report=yes persistent=no maxSize=512 tracefile="$netshTracePath" | Out-Null
        $startedNetsh = $true
        $events += [pscustomobject]@{ name = "netsh_trace_start"; status = "pass"; path = $netshTracePath; error = $null }
    } catch {
        $events += [pscustomobject]@{ name = "netsh_trace_start"; status = "blocked"; path = $netshTracePath; error = $_.Exception.Message }
    }

    $deadline = (Get-Date).AddSeconds($DurationSeconds)
    $index = 0
    while ((Get-Date) -lt $deadline) {
        try {
            $snapshot = Get-Snapshot -Index $index
            $snapshot | ConvertTo-Json -Depth 64 -Compress | Add-Content -LiteralPath $samplesPath -Encoding UTF8
        } catch {
            ([pscustomobject]@{
                schema = "rusty.hostess.windows.qcl041_network_trace_sample_error.v1"
                run_id = $RunId
                sample_index = $index
                timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
                error = $_.Exception.Message
            } | ConvertTo-Json -Depth 16 -Compress) | Add-Content -LiteralPath $samplesPath -Encoding UTF8
        }
        Start-Sleep -Milliseconds $SampleIntervalMilliseconds
        $index += 1
    }

    $captures += Invoke-CaptureCommand "netstat_after" { netstat -ano -p tcp } (Join-Path $OutDir "netstat-after.txt")
    $captures += Invoke-CaptureCommand "arp_after" { arp -a } (Join-Path $OutDir "arp-after.txt")
} finally {
    if ($startedPktmon) {
        try {
            pktmon counters --json | Set-Content -LiteralPath $pktmonCountersPath -Encoding UTF8
            $events += [pscustomobject]@{ name = "pktmon_counters"; status = "pass"; path = $pktmonCountersPath; error = $null }
        } catch {
            $events += [pscustomobject]@{ name = "pktmon_counters"; status = "blocked"; path = $pktmonCountersPath; error = $_.Exception.Message }
        }
        try {
            pktmon stop | Out-Null
            $events += [pscustomobject]@{ name = "pktmon_stop"; status = "pass"; path = $pktmonEtlPath; error = $null }
        } catch {
            $events += [pscustomobject]@{ name = "pktmon_stop"; status = "blocked"; path = $pktmonEtlPath; error = $_.Exception.Message }
        }
        try {
            pktmon etl2txt $pktmonEtlPath --out $pktmonTextPath | Out-Null
            $events += [pscustomobject]@{ name = "pktmon_etl2txt"; status = "pass"; path = $pktmonTextPath; error = $null }
        } catch {
            $events += [pscustomobject]@{ name = "pktmon_etl2txt"; status = "blocked"; path = $pktmonTextPath; error = $_.Exception.Message }
        }
        try {
            pktmon etl2pcap $pktmonEtlPath --out $pktmonPcapPath | Out-Null
            $events += [pscustomobject]@{ name = "pktmon_etl2pcap"; status = "pass"; path = $pktmonPcapPath; error = $null }
        } catch {
            $events += [pscustomobject]@{ name = "pktmon_etl2pcap"; status = "blocked"; path = $pktmonPcapPath; error = $_.Exception.Message }
        }
    }
    if ($startedNetsh) {
        try {
            netsh trace stop | Out-Null
            $events += [pscustomobject]@{ name = "netsh_trace_stop"; status = "pass"; path = $netshTracePath; error = $null }
        } catch {
            $events += [pscustomobject]@{ name = "netsh_trace_stop"; status = "blocked"; path = $netshTracePath; error = $_.Exception.Message }
        }
    }
}

$packetText = ""
if (Test-Path -LiteralPath $pktmonTextPath) {
    $packetText = Get-Content -LiteralPath $pktmonTextPath -Raw
}
$samples = @()
if (Test-Path -LiteralPath $samplesPath) {
    foreach ($line in Get-Content -LiteralPath $samplesPath) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $samples += ($line | ConvertFrom-Json)
        }
    }
}
$p2pAddresses = @($samples.ip_addresses | Where-Object { $_.IPAddress -like "192.168.137.*" } | Select-Object -ExpandProperty IPAddress -Unique)
$listenerStates = @($samples.tcp | Where-Object { $_.LocalPort -eq $ListenPort } | Select-Object -Property LocalAddress, LocalPort, State, OwningProcess -Unique)
$remotePortHits = @($samples.tcp | Where-Object { $_.RemotePort -eq $ListenPort } | Select-Object -Property LocalAddress, LocalPort, RemoteAddress, RemotePort, State, OwningProcess -Unique)
$summary = [pscustomobject]@{
    schema = "rusty.hostess.windows.qcl041_network_trace_summary.v1"
    run_id = $RunId
    timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
    elevated = $isAdmin
    listen_port = $ListenPort
    duration_seconds = $DurationSeconds
    capture_all_packets = [bool]$CaptureAllPackets
    sample_count = $samples.Count
    p2p_ipv4_addresses_observed = $p2pAddresses
    listener_states_observed = $listenerStates
    remote_port_states_observed = $remotePortHits
    packet_text_mentions_listen_port = $packetText.Contains($ListenPort.ToString())
    packet_text_mentions_p2p_subnet = $packetText.Contains("192.168.137.")
    captures = $captures
    events = $events
    artifacts = [pscustomobject]@{
        ready = $readyPath
        samples = $samplesPath
        pktmon_etl = $pktmonEtlPath
        pktmon_text = $pktmonTextPath
        pktmon_pcapng = $pktmonPcapPath
        pktmon_counters = $pktmonCountersPath
        netsh_trace_etl = $netshTracePath
    }
}
Write-JsonFile -Value $summary -Path $summaryPath
Write-Output $summaryPath
