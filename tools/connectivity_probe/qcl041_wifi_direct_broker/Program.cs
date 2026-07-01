using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.IO;
using System.Windows;
using Windows.Devices.Enumeration;
using Windows.Devices.WiFiDirect;

namespace RustyHostess.ConnectivityProbe.Qcl041WifiDirectBroker;

internal static class Program
{
    [STAThread]
    public static int Main(string[] args)
    {
        var options = CliOptions.Parse(args);
        var application = new Application
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown,
        };
        var exitCode = 2;
        application.Startup += async (_, _) =>
        {
            try
            {
                exitCode = await new Broker(options).RunAsync();
            }
            finally
            {
                application.Shutdown(exitCode);
            }
        };
        return application.Run();
    }
}

internal sealed class Broker(CliOptions options)
{
    private readonly List<Dictionary<string, object?>> _eventsLog = [];
    private readonly List<Dictionary<string, object?>> _issues = [];
    private readonly List<Dictionary<string, object?>> _messages = [];
    private readonly List<string> _errors = [];
    private readonly object _sync = new();
    private readonly DateTimeOffset _started = DateTimeOffset.UtcNow;
    private string _status = "blocked";
    private bool _publisherStarted;
    private bool _listenerReady;
    private bool _peerRequested;
    private bool _groupFormed;
    private bool _socketExchangeCompleted;
    private bool _cleanupCompleted;
    private int _endpointPairCount;
    private int _messagesSent;
    private int _messagesReceived;
    private string _publisherStatus = "";
    private string _selectedPeerName = "";
    private bool? _selectedPeerPaired;
    private bool? _selectedPeerCanPair;
    private string _selectedPeerPairingStatus = "";
    private string _localEndpointHostName = "";
    private string _remoteEndpointHostName = "";
    private string _tcpListenerBindAddress = "";
    private WiFiDirectAdvertisementPublisher? _publisher;
    private WiFiDirectConnectionRequest? _connectionRequest;
    private WiFiDirectDevice? _wifiDirectDevice;
    private TcpListener? _tcpListener;
    private CancellationTokenSource? _tcpTimeoutCts;

    public async Task<int> RunAsync()
    {
        AddEvent(
            "host.winrt.ui_thread",
            Thread.CurrentThread.GetApartmentState() == ApartmentState.STA ? "pass" : "warn",
            $"WPF dispatcher broker running on apartment={Thread.CurrentThread.GetApartmentState()}");

        try
        {
            AddEvent("host.winrt.wifi_direct_api", "pass", "Windows WinRT Wi-Fi Direct API loaded");
            using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
            var connectionRequest = new TaskCompletionSource<WiFiDirectConnectionRequest>(TaskCreationOptions.RunContinuationsAsynchronously);
            using var timeoutRegistration = timeoutCts.Token.Register(() => connectionRequest.TrySetCanceled(timeoutCts.Token));

            var listener = new WiFiDirectConnectionListener();
            _listenerReady = true;
            AddEvent("wifi_direct.connection_listener.ready", "pass", "Windows Wi-Fi Direct connection listener created on WPF STA dispatcher");
            listener.ConnectionRequested += (_, eventArgs) =>
            {
                try
                {
                    var request = eventArgs.GetConnectionRequest();
                    _connectionRequest = request;
                    _peerRequested = true;
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

            _publisher = new WiFiDirectAdvertisementPublisher();
            _publisher.Advertisement.IsAutonomousGroupOwnerEnabled = options.AutonomousGroupOwner;
            _publisher.StatusChanged += (_, eventArgs) =>
            {
                _publisherStatus = eventArgs.Status.ToString();
                AddEvent(
                    "wifi_direct.publisher.status",
                    eventArgs.Status is WiFiDirectAdvertisementPublisherStatus.Started ? "pass" : "warn",
                    $"publisher status={eventArgs.Status}; error={eventArgs.Error}");
            };
            _publisher.Start();
            _publisherStarted = true;
            _publisherStatus = _publisher.Status.ToString();
            AddEvent("wifi_direct.publisher.start", "pass", "Windows Wi-Fi Direct advertisement publisher started from WPF STA dispatcher");

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
                    "No Quest Wi-Fi Direct peer connected to the Windows UI-thread broker before timeout");
                AddEvent("wifi_direct.peer.wait_timeout", "blocked", "no peer connected before timeout");
                request = null;
            }

            if (request is not null)
            {
                await OpenPeerAndServeTcpAsync(request, timeoutCts.Token);
            }
        }
        catch (Exception ex)
        {
            _status = "fail";
            _errors.Add(ex.ToString());
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_peer_helper_failed",
                "error",
                ex.ToString());
            AddEvent("host.helper.failure", "fail", ex.ToString());
        }
        finally
        {
            await CleanupAsync();
        }

        await WriteReportAsync();
        return _status == "pass" ? 0 : _status == "blocked" ? 3 : 2;
    }

    private async Task OpenPeerAndServeTcpAsync(WiFiDirectConnectionRequest connectionRequest, CancellationToken openCancellationToken)
    {
        var peer = connectionRequest.DeviceInformation;
        _selectedPeerName = peer.Name ?? "";
        _selectedPeerPaired = peer.Pairing?.IsPaired;
        _selectedPeerCanPair = peer.Pairing?.CanPair;
        AddEvent("wifi_direct.peer.selected", "pass", "Wi-Fi Direct peer selected from connection request");

        if (options.PairBeforeOpen && peer.Pairing is { IsPaired: false, CanPair: true })
        {
            var pairResult = await peer.Pairing.PairAsync().AsTask(openCancellationToken);
            _selectedPeerPairingStatus = pairResult.Status.ToString();
            AddEvent("wifi_direct.peer.pairing", pairResult.Status == DevicePairingResultStatus.Paired ? "pass" : "warn", $"pairing status={pairResult.Status}");
        }

        try
        {
            var connectionParameters = new WiFiDirectConnectionParameters
            {
                GroupOwnerIntent = options.GroupOwnerIntent,
            };
            _wifiDirectDevice = await WiFiDirectDevice.FromIdAsync(peer.Id, connectionParameters).AsTask(openCancellationToken);
            AddEvent("wifi_direct.device.open", _wifiDirectDevice is null ? "blocked" : "pass", "WiFiDirectDevice.FromIdAsync completed on WPF STA dispatcher");
        }
        catch (Exception ex)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_device_open_failed",
                "warning",
                ex.ToString());
            AddEvent("wifi_direct.device.open", "warn", ex.ToString());
        }

        if (_wifiDirectDevice is null)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_device_open_failed",
                "error",
                "WiFiDirectDevice.FromIdAsync returned null");
            AddEvent("wifi_direct.device.open", "blocked", "WiFiDirectDevice.FromIdAsync returned null");
            return;
        }

        var endpointPairs = _wifiDirectDevice.GetConnectionEndpointPairs();
        _endpointPairCount = endpointPairs.Count;
        _groupFormed = _endpointPairCount > 0;
        if (_groupFormed)
        {
            _localEndpointHostName = endpointPairs[0].LocalHostName?.RawName ?? "";
            _remoteEndpointHostName = endpointPairs[0].RemoteHostName?.RawName ?? "";
        }
        AddEvent(
            "wifi_direct.group_formation",
            _groupFormed ? "pass" : "blocked",
            $"endpoint_pair_count={_endpointPairCount}; local={_localEndpointHostName}; remote={_remoteEndpointHostName}");

        if (!_groupFormed)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_endpoint_pair_missing",
                "warning",
                "WiFiDirectDevice opened but GetConnectionEndpointPairs returned no endpoints");
            return;
        }

        var bindAddress = ResolveLocalBindAddress(_localEndpointHostName);
        _tcpListenerBindAddress = bindAddress.ToString();
        _tcpTimeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.SocketTimeoutSeconds));
        _tcpListener = new TcpListener(bindAddress, options.ListenPort);
        _tcpListener.Server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        _tcpListener.Start();
        AddEvent("wifi_direct.tcp_listener.start", "pass", $"bounded TCP listener bound to Wi-Fi Direct endpoint {_tcpListenerBindAddress}:{options.ListenPort}");

        var tcpResult = await AcceptTcpProbeAsync(_tcpListener, options.RunId, _tcpTimeoutCts.Token);
        if (tcpResult.Success)
        {
            _messagesReceived += tcpResult.MessagesReceived;
            _messagesSent += tcpResult.MessagesSent;
            _socketExchangeCompleted = true;
            _status = "pass";
            _messages.Add(new Dictionary<string, object?>
            {
                ["sequence"] = 1,
                ["request_preview"] = tcpResult.RequestPreview,
                ["response_bytes"] = tcpResult.ResponseBytes,
                ["remote_endpoint"] = tcpResult.RemoteEndpoint,
            });
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

    private IPAddress ResolveLocalBindAddress(string localHostName)
    {
        if (IPAddress.TryParse(localHostName, out var parsed))
        {
            return parsed;
        }
        try
        {
            var addresses = Dns.GetHostAddresses(localHostName);
            var address = addresses.FirstOrDefault(candidate => candidate.AddressFamily == AddressFamily.InterNetwork)
                ?? addresses.FirstOrDefault(candidate => candidate.AddressFamily == AddressFamily.InterNetworkV6);
            if (address is not null)
            {
                AddEvent("wifi_direct.tcp_listener.bind_resolution", "pass", $"resolved {localHostName} to {address}");
                return address;
            }
        }
        catch (Exception ex)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_bind_resolution_failed",
                "warning",
                ex.Message);
        }
        AddIssue(
            "hostess.issue.connectivity_probe.wifi_direct_windows_bind_fallback_any",
            "warning",
            $"Could not resolve Wi-Fi Direct local endpoint '{localHostName}', falling back to IPAddress.Any");
        return IPAddress.Any;
    }

    private async Task CleanupAsync()
    {
        try
        {
            _tcpTimeoutCts?.Cancel();
            _tcpListener?.Stop();
            _tcpTimeoutCts?.Dispose();
            _wifiDirectDevice?.Dispose();
            _connectionRequest?.Dispose();
            _publisher?.Stop();
            _cleanupCompleted = true;
            AddEvent("wifi_direct.cleanup", "pass", "Windows Wi-Fi Direct broker resources were disposed");
        }
        catch (Exception ex)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.wifi_direct_windows_cleanup_failed",
                "warning",
                ex.Message);
            AddEvent("wifi_direct.cleanup", "warn", ex.Message);
        }
        await Task.CompletedTask;
    }

    private async Task WriteReportAsync()
    {
        var ended = DateTimeOffset.UtcNow;
        var report = new Dictionary<string, object?>
        {
            ["schema"] = "rusty.hostess.windows.qcl041_wifi_direct_peer_helper.v1",
            ["schema_version"] = 1,
            ["run_id"] = options.RunId,
            ["status"] = _status,
            ["started_at_utc"] = _started.ToString("O"),
            ["ended_at_utc"] = ended.ToString("O"),
            ["role"] = "windows_wifi_direct_ui_thread_broker",
            ["broker_kind"] = "wpf_sta_dispatcher",
            ["listen_port"] = options.ListenPort,
            ["autonomous_group_owner"] = options.AutonomousGroupOwner,
            ["group_owner_intent"] = options.GroupOwnerIntent,
            ["pair_before_open"] = options.PairBeforeOpen,
            ["selected_peer"] = new Dictionary<string, object?>
            {
                ["name"] = _selectedPeerName,
                ["id_redacted"] = _peerRequested,
                ["is_paired"] = _selectedPeerPaired,
                ["can_pair"] = _selectedPeerCanPair,
                ["pairing_status"] = _selectedPeerPairingStatus,
            },
            ["measurements"] = new Dictionary<string, object?>
            {
                ["advertisement_started"] = _publisherStarted,
                ["publisher_status"] = _publisherStatus,
                ["connection_listener_ready"] = _listenerReady,
                ["peer_connection_requested"] = _peerRequested,
                ["group_formed"] = _groupFormed,
                ["endpoint_pair_count"] = _endpointPairCount,
                ["local_endpoint_host_name"] = _localEndpointHostName,
                ["remote_endpoint_host_name"] = _remoteEndpointHostName,
                ["tcp_listener_bind_address"] = _tcpListenerBindAddress,
                ["socket_exchange_completed"] = _socketExchangeCompleted,
                ["messages_sent"] = _messagesSent,
                ["messages_received"] = _messagesReceived,
                ["cleanup_completed"] = _cleanupCompleted,
            },
            ["messages"] = _messages,
            ["events"] = _eventsLog,
            ["issues"] = _issues,
            ["errors"] = _errors,
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
    }

    private void AddEvent(string phase, string eventStatus, string evidence)
    {
        lock (_sync)
        {
            _eventsLog.Add(new Dictionary<string, object?>
            {
                ["phase"] = phase,
                ["status"] = eventStatus,
                ["evidence"] = evidence,
                ["observed_at_utc"] = DateTimeOffset.UtcNow.ToString("O"),
            });
        }
    }

    private void AddIssue(string issueCode, string severity, string message)
    {
        lock (_sync)
        {
            if (_issues.Any(issue => string.Equals(issue.GetValueOrDefault("issue_code") as string, issueCode, StringComparison.Ordinal)))
            {
                return;
            }
            _issues.Add(new Dictionary<string, object?>
            {
                ["issue_code"] = issueCode,
                ["severity"] = severity,
                ["message"] = message,
            });
        }
    }

    private static async Task<TcpProbeResult> AcceptTcpProbeAsync(TcpListener listener, string runId, CancellationToken cancellationToken)
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
    public string RunId { get; init; } = "qcl041-windows-wifi-direct-broker";
    public string Out { get; init; } = "";
    public double TimeoutSeconds { get; init; } = 30.0;
    public double SocketTimeoutSeconds { get; init; } = 20.0;
    public int ListenPort { get; init; } = 18768;
    public bool AutonomousGroupOwner { get; init; } = true;
    public short GroupOwnerIntent { get; init; } = 15;
    public bool PairBeforeOpen { get; init; }

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
            RunId = values.GetValueOrDefault("run-id", "qcl041-windows-wifi-direct-broker"),
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
