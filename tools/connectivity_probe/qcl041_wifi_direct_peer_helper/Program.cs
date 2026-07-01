using System.Text;
using System.Text.Json;
using System.Net;
using System.Net.Sockets;
using Windows.Devices.Enumeration;
using Windows.Devices.WiFiDirect;

var options = CliOptions.Parse(args);
var started = DateTimeOffset.UtcNow;
var eventsLog = new List<Dictionary<string, object?>>();
var issues = new List<Dictionary<string, object?>>();
var errors = new List<string>();
var messages = new List<Dictionary<string, object?>>();
var sync = new object();
var status = "blocked";
var publisherStarted = false;
var listenerReady = false;
var peerRequested = false;
var groupFormed = false;
var socketExchangeCompleted = false;
var cleanupCompleted = false;
var endpointPairCount = 0;
var messagesSent = 0;
var messagesReceived = 0;
string publisherStatus = "";
string selectedPeerName = "";
bool? selectedPeerPaired = null;
bool? selectedPeerCanPair = null;
string selectedPeerPairingStatus = "";
string localEndpointHostName = "";
string remoteEndpointHostName = "";

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
WiFiDirectConnectionRequest? connectionRequestHandle = null;
WiFiDirectDevice? wifiDirectDevice = null;
TcpListener? tcpListener = null;
Task<TcpProbeResult>? tcpProbeTask = null;
CancellationTokenSource? tcpTimeoutCts = null;
var tcpProbeConsumed = false;

async Task ConsumeTcpProbeAsync()
{
    if (tcpProbeTask is null || tcpProbeConsumed)
    {
        return;
    }
    tcpProbeConsumed = true;
    var tcpResult = await tcpProbeTask;
    if (tcpResult.Success)
    {
        messagesReceived += tcpResult.MessagesReceived;
        messagesSent += tcpResult.MessagesSent;
        socketExchangeCompleted = true;
        groupFormed = true;
        if (endpointPairCount == 0)
        {
            AddEvent("wifi_direct.group_formation", "pass", "bounded TCP peer connected across the Wi-Fi Direct subnet");
        }
        messages.Add(new Dictionary<string, object?>
        {
            ["sequence"] = 1,
            ["request_preview"] = tcpResult.RequestPreview,
            ["response_bytes"] = tcpResult.ResponseBytes,
            ["remote_endpoint"] = tcpResult.RemoteEndpoint,
        });
        status = "pass";
        AddEvent("wifi_direct.socket_exchange", "pass", $"bounded TCP request/ack exchange completed; remote={tcpResult.RemoteEndpoint}");
    }
    else
    {
        AddIssue(
            "hostess.issue.connectivity_probe.wifi_direct_windows_socket_peer_not_connected",
            "warning",
            tcpResult.Error);
        AddEvent("wifi_direct.socket_exchange", "blocked", tcpResult.Error);
    }
}

try
{
    AddEvent("host.winrt.wifi_direct_api", "pass", "Windows WinRT Wi-Fi Direct API loaded");

    var connectionRequest = new TaskCompletionSource<WiFiDirectConnectionRequest>(TaskCreationOptions.RunContinuationsAsynchronously);
    using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
    using var timeoutRegistration = timeoutCts.Token.Register(() => connectionRequest.TrySetCanceled(timeoutCts.Token));

    var listener = new WiFiDirectConnectionListener();
    listenerReady = true;
    AddEvent("wifi_direct.connection_listener.ready", "pass", "Windows Wi-Fi Direct connection listener created");
    listener.ConnectionRequested += (_, eventArgs) =>
    {
        try
        {
            var request = eventArgs.GetConnectionRequest();
            connectionRequestHandle = request;
            peerRequested = true;
            AddEvent("wifi_direct.connection_requested", "pass", "Wi-Fi Direct peer connection request received");
            connectionRequest.TrySetResult(request);
        }
        catch (Exception ex)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_connection_request_failed",
                "error",
                ex.Message);
            connectionRequest.TrySetException(ex);
        }
    };

    publisher = new WiFiDirectAdvertisementPublisher();
    publisher.Advertisement.IsAutonomousGroupOwnerEnabled = options.AutonomousGroupOwner;
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
    AddEvent("wifi_direct.publisher.start", "pass", "Windows Wi-Fi Direct advertisement publisher started");

    tcpTimeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds + options.SocketTimeoutSeconds + 5.0));
    tcpListener = new TcpListener(IPAddress.Any, options.ListenPort);
    tcpListener.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
    tcpListener.Start();
    tcpProbeTask = AcceptTcpProbeAsync(tcpListener, options.RunId, tcpTimeoutCts.Token);
    AddEvent("wifi_direct.tcp_listener.start", "pass", $"bounded TCP listener started on 0.0.0.0:{options.ListenPort}");

    WiFiDirectConnectionRequest? request;
    try
    {
        request = await connectionRequest.Task;
    }
    catch (OperationCanceledException)
    {
        AddIssue(
            "hostess.issue.connectivity_probe.wifi_direct_windows_peer_not_connected",
            "warning",
            "No Quest Wi-Fi Direct peer connected to the Windows helper before timeout");
        AddEvent("wifi_direct.peer.wait_timeout", "blocked", "no peer connected before timeout");
        request = null;
    }

    if (request is not null)
    {
        var peer = request.DeviceInformation;
        selectedPeerName = peer.Name ?? "";
        selectedPeerPaired = peer.Pairing?.IsPaired;
        selectedPeerCanPair = peer.Pairing?.CanPair;
        AddEvent("wifi_direct.peer.selected", "pass", "Wi-Fi Direct peer selected from connection request");

        if (options.PairBeforeOpen && peer.Pairing is { IsPaired: false, CanPair: true })
        {
            var pairResult = await peer.Pairing.PairAsync().AsTask(timeoutCts.Token);
            selectedPeerPairingStatus = pairResult.Status.ToString();
            AddEvent("wifi_direct.peer.pairing", pairResult.Status == DevicePairingResultStatus.Paired ? "pass" : "warn", $"pairing status={pairResult.Status}");
        }

        try
        {
            var connectionParameters = new WiFiDirectConnectionParameters
            {
                GroupOwnerIntent = options.GroupOwnerIntent,
            };
            wifiDirectDevice = await RunStaAsync(
                () => WiFiDirectDevice.FromIdAsync(peer.Id, connectionParameters).AsTask(timeoutCts.Token));
        }
        catch (Exception ex)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_device_open_failed",
                "warning",
                ex.ToString());
            AddEvent("wifi_direct.device.open", "warn", ex.ToString());
        }
        if (wifiDirectDevice is null)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_device_open_failed",
                "error",
                "WiFiDirectDevice.FromIdAsync returned null");
            AddEvent("wifi_direct.device.open", "blocked", "WiFiDirectDevice.FromIdAsync returned null");
        }
        else
        {
            var endpointPairs = wifiDirectDevice.GetConnectionEndpointPairs();
            endpointPairCount = endpointPairs.Count;
            groupFormed = endpointPairCount > 0;
            if (groupFormed)
            {
                localEndpointHostName = endpointPairs[0].LocalHostName?.RawName ?? "";
                remoteEndpointHostName = endpointPairs[0].RemoteHostName?.RawName ?? "";
            }
            AddEvent(
                "wifi_direct.group_formation",
                groupFormed ? "pass" : "blocked",
                $"endpoint_pair_count={endpointPairCount}; local={localEndpointHostName}; remote={remoteEndpointHostName}");

            if (groupFormed)
            {
                AddEvent("wifi_direct.tcp_listener.group_ready", "pass", $"bounded TCP listener awaiting peer on {localEndpointHostName}:{options.ListenPort}");
            }
        }
        await ConsumeTcpProbeAsync();
    }
}
catch (Exception ex)
{
    status = "fail";
    errors.Add(ex.ToString());
    AddIssue(
        "hostess.issue.connectivity_probe.wifi_direct_windows_peer_helper_failed",
        "error",
        ex.ToString());
    AddEvent("host.helper.failure", "fail", ex.ToString());
}
finally
{
    try
    {
        wifiDirectDevice?.Dispose();
        connectionRequestHandle?.Dispose();
        tcpTimeoutCts?.Cancel();
        tcpListener?.Stop();
        tcpTimeoutCts?.Dispose();
        publisher?.Stop();
        cleanupCompleted = true;
        AddEvent("wifi_direct.cleanup", "pass", "Windows Wi-Fi Direct helper resources were disposed");
    }
    catch (Exception ex)
    {
        AddIssue(
            "hostess.issue.connectivity_probe.wifi_direct_windows_cleanup_failed",
            "warning",
            ex.Message);
        AddEvent("wifi_direct.cleanup", "warn", ex.Message);
    }
}

var ended = DateTimeOffset.UtcNow;
var report = new Dictionary<string, object?>
{
    ["schema"] = "rusty.hostess.windows.qcl041_wifi_direct_peer_helper.v1",
    ["schema_version"] = 1,
    ["run_id"] = options.RunId,
    ["status"] = status,
    ["started_at_utc"] = started.ToString("O"),
    ["ended_at_utc"] = ended.ToString("O"),
    ["role"] = "windows_wifi_direct_peer_listener",
    ["listen_port"] = options.ListenPort,
    ["autonomous_group_owner"] = options.AutonomousGroupOwner,
    ["group_owner_intent"] = options.GroupOwnerIntent,
    ["pair_before_open"] = options.PairBeforeOpen,
    ["selected_peer"] = new Dictionary<string, object?>
    {
        ["name"] = selectedPeerName,
        ["id_redacted"] = peerRequested,
        ["is_paired"] = selectedPeerPaired,
        ["can_pair"] = selectedPeerCanPair,
        ["pairing_status"] = selectedPeerPairingStatus,
    },
    ["measurements"] = new Dictionary<string, object?>
    {
        ["advertisement_started"] = publisherStarted,
        ["publisher_status"] = publisherStatus,
        ["connection_listener_ready"] = listenerReady,
        ["peer_connection_requested"] = peerRequested,
        ["group_formed"] = groupFormed,
        ["endpoint_pair_count"] = endpointPairCount,
        ["local_endpoint_host_name"] = localEndpointHostName,
        ["remote_endpoint_host_name"] = remoteEndpointHostName,
        ["socket_exchange_completed"] = socketExchangeCompleted,
        ["messages_sent"] = messagesSent,
        ["messages_received"] = messagesReceived,
        ["cleanup_completed"] = cleanupCompleted,
    },
    ["messages"] = messages,
    ["events"] = eventsLog,
    ["issues"] = issues,
    ["errors"] = errors,
};

var json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
if (!string.IsNullOrWhiteSpace(options.Out))
{
    var outPath = Path.GetFullPath(options.Out);
    Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
    await File.WriteAllTextAsync(outPath, json + Environment.NewLine, new UTF8Encoding(false));
}
else
{
    Console.WriteLine(json);
}

return status == "pass" ? 0 : status == "blocked" ? 3 : 2;

static async Task<TcpProbeResult> AcceptTcpProbeAsync(TcpListener listener, string runId, CancellationToken cancellationToken)
{
    try
    {
        using var registration = cancellationToken.Register(() =>
        {
            try
            {
                listener.Stop();
            }
            catch
            {
                // Listener cancellation should surface as the timeout result below.
            }
        });
        using var client = await listener.AcceptTcpClientAsync(cancellationToken);
        await using var stream = client.GetStream();
        using var reader = new StreamReader(stream, Encoding.UTF8, detectEncodingFromByteOrderMarks: false, leaveOpen: true);
        await using var writer = new StreamWriter(stream, new UTF8Encoding(false), leaveOpen: true)
        {
            AutoFlush = true,
            NewLine = "\n",
        };
        var request = await reader.ReadLineAsync(cancellationToken) ?? "";
        var response = $"ack;runId={runId};received={request}";
        await writer.WriteLineAsync(response);
        return new TcpProbeResult(
            Success: true,
            MessagesReceived: 1,
            MessagesSent: 1,
            RequestPreview: request.Length > 160 ? request[..160] : request,
            ResponseBytes: Encoding.UTF8.GetByteCount(response + "\n"),
            RemoteEndpoint: client.Client.RemoteEndPoint?.ToString() ?? "",
            Error: "");
    }
    catch (OperationCanceledException)
    {
        return TcpProbeResult.Blocked("no bounded TCP peer connected before timeout");
    }
    catch (ObjectDisposedException) when (cancellationToken.IsCancellationRequested)
    {
        return TcpProbeResult.Blocked("bounded TCP listener stopped before a peer connected");
    }
    catch (SocketException ex) when (cancellationToken.IsCancellationRequested)
    {
        return TcpProbeResult.Blocked($"bounded TCP listener stopped before a peer connected: {ex.SocketErrorCode}");
    }
    catch (Exception ex)
    {
        return TcpProbeResult.Blocked(ex.ToString());
    }
}

static Task<T> RunStaAsync<T>(Func<Task<T>> action)
{
    var completion = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
    var thread = new Thread(async () =>
    {
        try
        {
            completion.TrySetResult(await action());
        }
        catch (Exception ex)
        {
            completion.TrySetException(ex);
        }
    });
    thread.SetApartmentState(ApartmentState.STA);
    thread.Start();
    return completion.Task;
}

internal sealed record TcpProbeResult(
    bool Success,
    int MessagesReceived,
    int MessagesSent,
    string RequestPreview,
    int ResponseBytes,
    string RemoteEndpoint,
    string Error)
{
    public static TcpProbeResult Blocked(string error) => new(
        Success: false,
        MessagesReceived: 0,
        MessagesSent: 0,
        RequestPreview: "",
        ResponseBytes: 0,
        RemoteEndpoint: "",
        Error: error);
}

internal sealed class CliOptions
{
    public string RunId { get; init; } = "qcl041-windows-wifi-direct-peer";
    public string Out { get; init; } = "";
    public double TimeoutSeconds { get; init; } = 30.0;
    public double SocketTimeoutSeconds { get; init; } = 20.0;
    public int ListenPort { get; init; } = 18768;
    public bool AutonomousGroupOwner { get; init; } = true;
    public short GroupOwnerIntent { get; init; } = 15;
    public bool PairBeforeOpen { get; init; } = false;

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

        return new CliOptions
        {
            RunId = values.GetValueOrDefault("run-id", "qcl041-windows-wifi-direct-peer"),
            Out = values.GetValueOrDefault("out", ""),
            TimeoutSeconds = double.TryParse(values.GetValueOrDefault("timeout-seconds"), out var timeoutSeconds)
                ? Math.Max(3.0, timeoutSeconds)
                : 30.0,
            SocketTimeoutSeconds = double.TryParse(values.GetValueOrDefault("socket-timeout-seconds"), out var socketTimeoutSeconds)
                ? Math.Max(3.0, socketTimeoutSeconds)
                : 20.0,
            ListenPort = int.TryParse(values.GetValueOrDefault("listen-port"), out var listenPort)
                ? Math.Clamp(listenPort, 1, 65535)
                : 18768,
            AutonomousGroupOwner = !values.TryGetValue("autonomous-group-owner", out var autonomousGroupOwner)
                || !string.Equals(autonomousGroupOwner, "false", StringComparison.OrdinalIgnoreCase),
            GroupOwnerIntent = short.TryParse(values.GetValueOrDefault("group-owner-intent"), out var groupOwnerIntent)
                ? (short)Math.Clamp((int)groupOwnerIntent, 0, 15)
                : (short)15,
            PairBeforeOpen = values.TryGetValue("pair-before-open", out var pairBeforeOpen)
                && string.Equals(pairBeforeOpen, "true", StringComparison.OrdinalIgnoreCase),
        };
    }
}
