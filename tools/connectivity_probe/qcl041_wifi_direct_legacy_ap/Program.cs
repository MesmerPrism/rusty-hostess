using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using Windows.Devices.WiFiDirect;
using Windows.Security.Credentials;

var options = CliOptions.Parse(args);
var started = DateTimeOffset.UtcNow;
var eventsLog = new List<Dictionary<string, object?>>();
var issues = new List<Dictionary<string, object?>>();
var errors = new List<string>();
var sync = new object();
var status = "blocked";
var publisherStarted = false;
var publisherStatus = "";
var cleanupCompleted = false;
var udpPackets = 0;
var udpBytes = 0L;
var udpLastSender = "";
var udpError = "";
var tcpAccepts = 0;
var tcpBytes = 0L;
var tcpAckBytes = 0;
var tcpLastSender = "";
var tcpError = "";
var socketExchangeCompleted = false;
var holdAfterSocketStarted = false;
var holdAfterSocketCompleted = false;

void AddEvent(string phase, string eventStatus, string evidence)
{
    lock (sync)
    {
        eventsLog.Add(new Dictionary<string, object?>
        {
            ["phase"] = phase,
            ["status"] = eventStatus,
            ["evidence"] = evidence,
            ["observed_at_utc"] = DateTimeOffset.UtcNow.ToString("O"),
        });
    }
}

void AddIssue(string issueCode, string severity, string message)
{
    lock (sync)
    {
        if (issues.Any(issue => string.Equals(issue.GetValueOrDefault("issue_code") as string, issueCode, StringComparison.Ordinal)))
        {
            return;
        }
        issues.Add(new Dictionary<string, object?>
        {
            ["issue_code"] = issueCode,
            ["severity"] = severity,
            ["message"] = message,
        });
    }
}

WiFiDirectAdvertisementPublisher? publisher = null;
using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
Task? udpTask = null;
Task? tcpTask = null;

try
{
    AddEvent("host.winrt.wifi_direct_api", "pass", "Windows WinRT Wi-Fi Direct API loaded");

    publisher = new WiFiDirectAdvertisementPublisher();
    publisher.Advertisement.IsAutonomousGroupOwnerEnabled = true;
    publisher.Advertisement.LegacySettings.IsEnabled = true;
    publisher.Advertisement.LegacySettings.Ssid = options.Ssid;
    publisher.Advertisement.LegacySettings.Passphrase = new PasswordCredential
    {
        Password = options.Passphrase,
    };
    publisher.StatusChanged += (_, eventArgs) =>
    {
        publisherStatus = eventArgs.Status.ToString();
        AddEvent(
            "wifi_direct.publisher.status",
            eventArgs.Status is WiFiDirectAdvertisementPublisherStatus.Started ? "pass" : "warn",
            $"publisher status={eventArgs.Status}; error={eventArgs.Error}");
    };
    publisher.Start();
    publisherStarted = true;
    publisherStatus = publisher.Status.ToString();
    AddEvent(
        "wifi_direct.legacy_ap.publisher.start",
        "pass",
        "Windows Wi-Fi Direct publisher started with LegacySettings enabled and redacted credential");

    udpTask = Task.Run(() => RunUdpReceiverAsync(options, timeoutCts.Token), timeoutCts.Token);
    tcpTask = Task.Run(() => RunTcpReceiverAsync(options, timeoutCts.Token), timeoutCts.Token);
    AddEvent(
        "wifi_direct.legacy_ap.socket_listeners.start",
        "pass",
        $"UDP listener 0.0.0.0:{options.UdpPort}; TCP listener 0.0.0.0:{options.TcpPort}");

    await WriteReportAsync(options.ReadyOut, "ready");

    while (!timeoutCts.IsCancellationRequested)
    {
        if (udpBytes >= options.ExpectedBytes && tcpBytes >= options.ExpectedBytes && tcpAckBytes > 0)
        {
            socketExchangeCompleted = true;
            break;
        }
        await Task.Delay(250, timeoutCts.Token);
    }
    if (socketExchangeCompleted && options.HoldAfterSocketSeconds > 0)
    {
        holdAfterSocketStarted = true;
        AddEvent(
            "wifi_direct.legacy_ap.hold_after_socket",
            "pass",
            $"holding Windows legacy AP for {options.HoldAfterSocketSeconds}s after socket exchange");
        await Task.Delay(TimeSpan.FromSeconds(options.HoldAfterSocketSeconds), timeoutCts.Token);
        holdAfterSocketCompleted = true;
    }
}
catch (OperationCanceledException)
{
    AddIssue(
        "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_timeout",
        "warning",
        "Windows legacy AP helper timed out before both UDP and TCP counters reached the requested byte count");
}
catch (Exception ex)
{
    status = "fail";
    errors.Add(ex.ToString());
    AddIssue(
        "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_failed",
        "error",
        ex.ToString());
    AddEvent("host.helper.failure", "fail", ex.ToString());
}
finally
{
    try
    {
        timeoutCts.Cancel();
        if (udpTask is not null)
        {
            try { await udpTask; } catch { }
        }
        if (tcpTask is not null)
        {
            try { await tcpTask; } catch { }
        }
        publisher?.Stop();
        cleanupCompleted = true;
        AddEvent("wifi_direct.legacy_ap.cleanup", "pass", "Windows Wi-Fi Direct legacy AP publisher and listeners were stopped");
    }
    catch (Exception ex)
    {
        AddIssue(
            "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_cleanup_failed",
            "warning",
            ex.Message);
        AddEvent("wifi_direct.legacy_ap.cleanup", "warn", ex.Message);
    }
}

if (status != "fail")
{
    status = publisherStarted && udpBytes >= options.ExpectedBytes && tcpBytes >= options.ExpectedBytes && tcpAckBytes > 0
        ? "pass"
        : "blocked";
    if (status == "pass")
    {
        AddEvent(
            "wifi_direct.legacy_ap.socket_exchange",
            "pass",
            $"received UDP bytes={udpBytes}; TCP bytes={tcpBytes}; TCP ack bytes={tcpAckBytes}");
    }
    else
    {
        AddIssue(
            "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_socket_exchange_incomplete",
            "warning",
            $"Expected UDP/TCP bytes>={options.ExpectedBytes}; observed udp={udpBytes}, tcp={tcpBytes}, tcp_ack={tcpAckBytes}");
        AddEvent(
            "wifi_direct.legacy_ap.socket_exchange",
            "blocked",
            $"expected_bytes={options.ExpectedBytes}; udp={udpBytes}; tcp={tcpBytes}; tcp_ack={tcpAckBytes}");
    }
}

await WriteReportAsync(options.Out, status);
return status == "pass" ? 0 : status == "blocked" ? 3 : 2;

async Task WriteReportAsync(string path, string reportStatus)
{
    if (string.IsNullOrWhiteSpace(path))
    {
        return;
    }
    var ended = DateTimeOffset.UtcNow;
    var report = new Dictionary<string, object?>
    {
        ["schema"] = "rusty.hostess.windows.qcl041_wifi_direct_legacy_ap.v1",
        ["schema_version"] = 1,
        ["run_id"] = options.RunId,
        ["status"] = reportStatus,
        ["started_at_utc"] = started.ToString("O"),
        ["observed_at_utc"] = ended.ToString("O"),
        ["role"] = "windows_wifi_direct_legacy_ap_owner",
        ["windows_wifidirect_mode"] = "autonomous_legacy_ap",
        ["legacy_settings_enabled"] = true,
        ["autonomous_group_owner"] = true,
        ["ssid"] = options.Ssid,
        ["credential_sensitive_redacted"] = true,
        ["udp_port"] = options.UdpPort,
        ["tcp_port"] = options.TcpPort,
        ["timeout_seconds"] = options.TimeoutSeconds,
        ["hold_after_socket_seconds"] = options.HoldAfterSocketSeconds,
        ["expected_bytes"] = options.ExpectedBytes,
        ["selected_owner_host"] = SelectOwnerHost(options.OwnerHost),
        ["network_addresses"] = NetworkAddressReport(),
        ["measurements"] = new Dictionary<string, object?>
        {
            ["advertisement_started"] = publisherStarted,
            ["publisher_status"] = publisherStatus,
            ["udp_packets"] = udpPackets,
            ["udp_bytes"] = udpBytes,
            ["udp_last_sender"] = udpLastSender,
            ["udp_error"] = udpError,
            ["tcp_accepts"] = tcpAccepts,
            ["tcp_bytes"] = tcpBytes,
            ["tcp_ack_bytes"] = tcpAckBytes,
            ["tcp_last_sender"] = tcpLastSender,
            ["tcp_error"] = tcpError,
            ["socket_exchange_completed"] = socketExchangeCompleted,
            ["hold_after_socket_started"] = holdAfterSocketStarted,
            ["hold_after_socket_completed"] = holdAfterSocketCompleted,
            ["cleanup_completed"] = cleanupCompleted,
        },
        ["events"] = eventsLog,
        ["issues"] = issues,
        ["errors"] = errors,
    };
    var outPath = Path.GetFullPath(path);
    Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
    await File.WriteAllTextAsync(
        outPath,
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine,
        new UTF8Encoding(false));
}

async Task RunUdpReceiverAsync(CliOptions receiverOptions, CancellationToken cancellationToken)
{
    try
    {
        using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        socket.Bind(new IPEndPoint(IPAddress.Any, receiverOptions.UdpPort));
        socket.ReceiveTimeout = 1000;
        var buffer = new byte[2048];
        while (!cancellationToken.IsCancellationRequested && udpBytes < receiverOptions.ExpectedBytes)
        {
            try
            {
                var result = await socket.ReceiveFromAsync(buffer, SocketFlags.None, new IPEndPoint(IPAddress.Any, 0), cancellationToken);
                udpPackets += 1;
                udpBytes += result.ReceivedBytes;
                udpLastSender = result.RemoteEndPoint.ToString() ?? "";
            }
            catch (OperationCanceledException)
            {
                break;
            }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.TimedOut)
            {
            }
        }
    }
    catch (Exception ex)
    {
        udpError = ex.ToString();
        AddIssue(
            "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_udp_listener_failed",
            "warning",
            ex.ToString());
    }
}

async Task RunTcpReceiverAsync(CliOptions receiverOptions, CancellationToken cancellationToken)
{
    TcpListener? listener = null;
    try
    {
        listener = new TcpListener(IPAddress.Any, receiverOptions.TcpPort);
        listener.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        listener.Start();
        using var registration = cancellationToken.Register(() =>
        {
            try { listener.Stop(); } catch { }
        });
        while (!cancellationToken.IsCancellationRequested && tcpBytes < receiverOptions.ExpectedBytes)
        {
            using var client = await listener.AcceptTcpClientAsync(cancellationToken);
            tcpAccepts += 1;
            tcpLastSender = client.Client.RemoteEndPoint?.ToString() ?? "";
            client.ReceiveTimeout = Math.Max(1000, receiverOptions.TimeoutSeconds * 1000);
            await using var stream = client.GetStream();
            var buffer = new byte[4096];
            while (tcpBytes < receiverOptions.ExpectedBytes)
            {
                var read = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), cancellationToken);
                if (read <= 0)
                {
                    break;
                }
                tcpBytes += read;
            }
            var ack = Encoding.UTF8.GetBytes($"QCL041-WINDOWS-LEGACY-AP-ACK;bytes={tcpBytes};run_id={receiverOptions.RunId}");
            await stream.WriteAsync(ack, cancellationToken);
            await stream.FlushAsync(cancellationToken);
            tcpAckBytes += ack.Length;
        }
    }
    catch (OperationCanceledException)
    {
    }
    catch (ObjectDisposedException) when (cancellationToken.IsCancellationRequested)
    {
    }
    catch (SocketException ex) when (cancellationToken.IsCancellationRequested)
    {
        tcpError = $"listener stopped during cancellation: {ex.SocketErrorCode}";
    }
    catch (Exception ex)
    {
        tcpError = ex.ToString();
        AddIssue(
            "hostess.issue.connectivity_probe.qcl041_windows_legacy_ap_tcp_listener_failed",
            "warning",
            ex.ToString());
    }
    finally
    {
        try { listener?.Stop(); } catch { }
    }
}

string SelectOwnerHost(string explicitOwnerHost)
{
    if (!string.IsNullOrWhiteSpace(explicitOwnerHost))
    {
        return explicitOwnerHost;
    }
    var candidates = NetworkAddressReport();
    var wifiDirect = candidates.FirstOrDefault(candidate =>
        Convert.ToBoolean(candidate.GetValueOrDefault("wifi_direct_name_hint")) &&
        IsLikelyPrivateIpv4(candidate.GetValueOrDefault("ipv4") as string ?? ""));
    if (wifiDirect is not null)
    {
        return wifiDirect["ipv4"] as string ?? "";
    }
    var privateCandidate = candidates.FirstOrDefault(candidate =>
        IsLikelyPrivateIpv4(candidate.GetValueOrDefault("ipv4") as string ?? ""));
    return privateCandidate?["ipv4"] as string ?? "";
}

List<Dictionary<string, object?>> NetworkAddressReport()
{
    var addresses = new List<Dictionary<string, object?>>();
    foreach (var nic in NetworkInterface.GetAllNetworkInterfaces())
    {
        var props = nic.GetIPProperties();
        foreach (var unicast in props.UnicastAddresses)
        {
            if (unicast.Address.AddressFamily != AddressFamily.InterNetwork || IPAddress.IsLoopback(unicast.Address))
            {
                continue;
            }
            addresses.Add(new Dictionary<string, object?>
            {
                ["name"] = nic.Name,
                ["description"] = nic.Description,
                ["status"] = nic.OperationalStatus.ToString(),
                ["ipv4"] = unicast.Address.ToString(),
                ["wifi_direct_name_hint"] =
                    nic.Name.Contains("Wi-Fi Direct", StringComparison.OrdinalIgnoreCase) ||
                    nic.Description.Contains("Wi-Fi Direct", StringComparison.OrdinalIgnoreCase),
            });
        }
    }
    return addresses;
}

static bool IsLikelyPrivateIpv4(string value)
{
    return value.StartsWith("192.168.", StringComparison.Ordinal) ||
        value.StartsWith("10.", StringComparison.Ordinal) ||
        value.StartsWith("172.16.", StringComparison.Ordinal) ||
        value.StartsWith("172.17.", StringComparison.Ordinal) ||
        value.StartsWith("172.18.", StringComparison.Ordinal) ||
        value.StartsWith("172.19.", StringComparison.Ordinal) ||
        value.StartsWith("172.2", StringComparison.Ordinal) ||
        value.StartsWith("172.30.", StringComparison.Ordinal) ||
        value.StartsWith("172.31.", StringComparison.Ordinal);
}

internal sealed class CliOptions
{
    public string RunId { get; init; } = "qcl041-windows-legacy-ap";
    public string Out { get; init; } = "";
    public string ReadyOut { get; init; } = "";
    public string Ssid { get; init; } = "DIRECT-rq-QCL041WIN";
    public string Passphrase { get; init; } = "RustyQcl041WinPass";
    public string OwnerHost { get; init; } = "";
    public int UdpPort { get; init; } = 19068;
    public int TcpPort { get; init; } = 19069;
    public int TimeoutSeconds { get; init; } = 90;
    public int HoldAfterSocketSeconds { get; init; } = 0;
    public int ExpectedBytes { get; init; } = 65536;

    public static CliOptions Parse(string[] args)
    {
        var values = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < args.Length; index += 1)
        {
            var arg = args[index];
            if (!arg.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }
            var name = arg[2..];
            var value = index + 1 < args.Length ? args[index + 1] : "";
            if (value.StartsWith("--", StringComparison.Ordinal))
            {
                value = "true";
            }
            else
            {
                index += 1;
            }
            values[name] = value;
        }
        var udpPort = ParseBoundedInt(values.GetValueOrDefault("udp-port"), 19068, 1, 65534);
        return new CliOptions
        {
            RunId = values.GetValueOrDefault("run-id", "qcl041-windows-legacy-ap"),
            Out = values.GetValueOrDefault("out", ""),
            ReadyOut = values.GetValueOrDefault("ready-out", ""),
            Ssid = values.GetValueOrDefault("ssid", "DIRECT-rq-QCL041WIN"),
            Passphrase = values.GetValueOrDefault("passphrase", "RustyQcl041WinPass"),
            OwnerHost = values.GetValueOrDefault("owner-host", ""),
            UdpPort = udpPort,
            TcpPort = ParseBoundedInt(values.GetValueOrDefault("tcp-port"), udpPort + 1, 1, 65535),
            TimeoutSeconds = ParseBoundedInt(values.GetValueOrDefault("timeout-seconds"), 90, 3, 600),
            HoldAfterSocketSeconds = ParseBoundedInt(values.GetValueOrDefault("hold-after-socket-seconds"), 0, 0, 600),
            ExpectedBytes = ParseBoundedInt(values.GetValueOrDefault("expected-bytes"), 65536, 1, 128 * 1024 * 1024),
        };
    }

    private static int ParseBoundedInt(string? value, int fallback, int min, int max)
    {
        if (int.TryParse(value, out var parsed))
        {
            return Math.Clamp(parsed, min, max);
        }
        return fallback;
    }
}
