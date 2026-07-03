using System.Net;
using System.Net.Sockets;
using System.Diagnostics;
using System.Runtime.InteropServices;
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
    private readonly List<Dictionary<string, object?>> _lslCommandTimingSamples = [];
    private readonly Queue<Dictionary<string, object?>> _lslCommandTimingTail = new();
    private readonly List<double> _lslCommandPublishIntervalMs = [];
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
    private int _lslCommandSamplesPublished;
    private int _lslCommandFirstSequence = -1;
    private int _lslCommandLastSequence = -1;
    private int _lslCommandLastPushResult;
    private double? _lslCommandFirstClockSeconds;
    private double? _lslCommandLastClockSeconds;
    private double? _lslCommandPublishElapsedMs;
    private DateTimeOffset? _lslCommandPublishStartedAtUtc;
    private DateTimeOffset? _lslCommandPublishEndedAtUtc;
    private string _publisherStatus = "";
    private string _lslCommandStatus = "disabled";
    private string _lslCommandIssue = "";
    private string _lslCommandLastError = "";
    private string _lslCommandStreamXml = "";
    private string _lslCommandHostname = "";
    private string _lslCommandUid = "";
    private string _lslCommandSessionId = "";
    private string _lslCommandV4Address = "";
    private string _lslCommandV4DataPort = "";
    private string _lslCommandV4ServicePort = "";
    private string _lslCommandV6Address = "";
    private string _lslCommandV6DataPort = "";
    private string _lslCommandV6ServicePort = "";
    private double? _lslCommandCreatedAtSeconds;
    private string _lslCommandApiConfigPath = "";
    private string _lslCommandApiConfigContent = "";
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
            if (options.LslCommandOutletEnabled)
            {
                await RunLslCommandOutletAsync(openCancellationToken);
            }
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

    private async Task RunLslCommandOutletAsync(CancellationToken cancellationToken)
    {
        _lslCommandStatus = "blocked";
        IntPtr streamInfo = IntPtr.Zero;
        IntPtr outlet = IntPtr.Zero;
        LslNative? lsl = null;
        var previousLslApiCfg = Environment.GetEnvironmentVariable("LSLAPICFG");
        try
        {
            PrepareLslCommandApiConfig();
            lsl = LslNative.Load(options.LslDllPath);
            if (!string.IsNullOrWhiteSpace(_lslCommandApiConfigContent))
            {
                var configContentApplied = lsl.TrySetConfigContent(_lslCommandApiConfigContent);
                AddEvent(
                    "qcl081_lsl_command.api_config_content",
                    configContentApplied ? "pass" : "warn",
                    configContentApplied
                        ? "applied per-run LSL config content before command outlet creation"
                        : "liblsl does not export lsl_set_config_content; using LSLAPICFG file path only");
            }
            AddEvent(
                "qcl081_lsl_command.library",
                "pass",
                $"loaded liblsl for broker command outlet: {lsl.LibraryInfo}");
            streamInfo = lsl.CreateStreamInfo(
                options.LslCommandStreamName,
                options.LslCommandStreamType,
                2,
                0.0,
                2,
                options.LslCommandSourceId);
            if (streamInfo == IntPtr.Zero)
            {
                throw new InvalidOperationException($"lsl_create_streaminfo returned null; last_error={lsl.LastError}");
            }
            outlet = lsl.CreateOutlet(streamInfo, 1, 60);
            if (outlet == IntPtr.Zero)
            {
                throw new InvalidOperationException($"lsl_create_outlet returned null; last_error={lsl.LastError}");
            }
            _lslCommandStreamXml = lsl.GetXml(streamInfo);
            _lslCommandHostname = lsl.GetHostname(streamInfo);
            _lslCommandUid = lsl.GetUid(streamInfo);
            _lslCommandSessionId = lsl.GetSessionId(streamInfo);
            _lslCommandCreatedAtSeconds = lsl.GetCreatedAt(streamInfo);
            _lslCommandV4Address = XmlTagValue(_lslCommandStreamXml, "v4address");
            _lslCommandV4DataPort = XmlTagValue(_lslCommandStreamXml, "v4data_port");
            _lslCommandV4ServicePort = XmlTagValue(_lslCommandStreamXml, "v4service_port");
            _lslCommandV6Address = XmlTagValue(_lslCommandStreamXml, "v6address");
            _lslCommandV6DataPort = XmlTagValue(_lslCommandStreamXml, "v6data_port");
            _lslCommandV6ServicePort = XmlTagValue(_lslCommandStreamXml, "v6service_port");
            AddEvent(
                "qcl081_lsl_command.outlet",
                "pass",
                $"broker LSL command outlet source_id={options.LslCommandSourceId}");
            if (options.LslCommandStartDelayMs > 0)
            {
                await Task.Delay(options.LslCommandStartDelayMs, cancellationToken);
            }
            _lslCommandPublishStartedAtUtc = DateTimeOffset.UtcNow;
            var publishWatch = Stopwatch.StartNew();
            double? previousPublishElapsedMs = null;
            for (var sequence = 0; sequence < options.LslCommandSampleCount; sequence += 1)
            {
                cancellationToken.ThrowIfCancellationRequested();
                var elapsedBeforePushMs = publishWatch.Elapsed.TotalMilliseconds;
                var timestamp = lsl.LocalClock();
                var sample = new[] { (double)sequence, timestamp };
                var result = lsl.PushSampleDtp(outlet, sample, timestamp, 1);
                _lslCommandLastPushResult = result;
                _lslCommandLastError = lsl.LastError;
                if (result != 0)
                {
                    _lslCommandIssue = $"lsl_push_sample_dtp returned {result}; last_error={lsl.LastError}";
                    break;
                }
                if (_lslCommandSamplesPublished == 0)
                {
                    _lslCommandFirstSequence = sequence;
                    _lslCommandFirstClockSeconds = timestamp;
                }
                if (previousPublishElapsedMs.HasValue)
                {
                    _lslCommandPublishIntervalMs.Add(elapsedBeforePushMs - previousPublishElapsedMs.Value);
                }
                previousPublishElapsedMs = elapsedBeforePushMs;
                _lslCommandLastSequence = sequence;
                _lslCommandLastClockSeconds = timestamp;
                var timingSample = new Dictionary<string, object?>
                {
                    ["sequence"] = sequence,
                    ["host_send_lsl_clock_seconds"] = timestamp,
                    ["publish_elapsed_ms"] = Math.Round(elapsedBeforePushMs, 3),
                };
                if (_lslCommandTimingSamples.Count < 25)
                {
                    _lslCommandTimingSamples.Add(timingSample);
                }
                _lslCommandTimingTail.Enqueue(timingSample);
                while (_lslCommandTimingTail.Count > 10)
                {
                    _lslCommandTimingTail.Dequeue();
                }
                _lslCommandSamplesPublished += 1;
                await Task.Delay(options.LslCommandIntervalMs, cancellationToken);
            }
            _lslCommandPublishEndedAtUtc = DateTimeOffset.UtcNow;
            publishWatch.Stop();
            _lslCommandPublishElapsedMs = publishWatch.Elapsed.TotalMilliseconds;
            _lslCommandStatus = _lslCommandSamplesPublished == options.LslCommandSampleCount
                ? "pass"
                : (_lslCommandSamplesPublished > 0 ? "warn" : "fail");
            AddEvent(
                "qcl081_lsl_command.publish",
                _lslCommandStatus,
                $"broker published {_lslCommandSamplesPublished}/{options.LslCommandSampleCount} command samples");
            if (options.LslCommandHoldAfterMs > 0)
            {
                await Task.Delay(options.LslCommandHoldAfterMs, cancellationToken);
                AddEvent(
                    "qcl081_lsl_command.hold_after_publish",
                    "pass",
                    $"held Wi-Fi Direct group and LSL outlet for {options.LslCommandHoldAfterMs} ms after command publish");
            }
        }
        catch (Exception ex)
        {
            _lslCommandStatus = _lslCommandSamplesPublished > 0 ? "warn" : "fail";
            _lslCommandIssue = ex.Message;
            AddIssue(
                "hostess.issue.connectivity_probe.qcl081_lsl_broker_command_outlet_failed",
                "error",
                ex.ToString());
            AddEvent("qcl081_lsl_command.publish", _lslCommandStatus, ex.ToString());
        }
        finally
        {
            if (outlet != IntPtr.Zero)
            {
                try
                {
                    lsl?.DestroyOutlet(outlet);
                }
                catch
                {
                    // Native cleanup should not hide the command outlet evidence.
                }
            }
            if (streamInfo != IntPtr.Zero)
            {
                try
                {
                    lsl?.DestroyStreamInfo(streamInfo);
                }
                catch
                {
                    // Native cleanup should not hide the command outlet evidence.
                }
            }
            lsl?.Dispose();
            Environment.SetEnvironmentVariable("LSLAPICFG", previousLslApiCfg, EnvironmentVariableTarget.Process);
        }
    }

    private void PrepareLslCommandApiConfig()
    {
        if (string.IsNullOrWhiteSpace(options.Out))
        {
            return;
        }
        var localAddress = _localEndpointHostName.Trim();
        if (!IPAddress.TryParse(localAddress, out var parsedLocal) ||
            parsedLocal.AddressFamily != AddressFamily.InterNetwork)
        {
            AddIssue(
                "hostess.issue.connectivity_probe.qcl081_lsl_command_listen_address_unavailable",
                "warning",
                $"Cannot force LSL ListenAddress because local Wi-Fi Direct endpoint is '{_localEndpointHostName}'.");
            return;
        }
        var peers = new List<string> { localAddress };
        var remoteAddress = _remoteEndpointHostName.Trim();
        if (IPAddress.TryParse(remoteAddress, out var parsedRemote) &&
            parsedRemote.AddressFamily == AddressFamily.InterNetwork &&
            !peers.Contains(remoteAddress, StringComparer.OrdinalIgnoreCase))
        {
            peers.Add(remoteAddress);
        }
        var sessionId = "default";
        var outPath = Path.GetFullPath(options.Out);
        var outDir = Path.GetDirectoryName(outPath);
        if (string.IsNullOrWhiteSpace(outDir))
        {
            return;
        }
        Directory.CreateDirectory(outDir);
        _lslCommandApiConfigPath = Path.Combine(outDir, "qcl081-lsl-command-lsl_api.cfg");
        _lslCommandApiConfigContent = string.Join(
            Environment.NewLine,
            [
                "[ports]",
                "IPv6 = disable",
                "",
                "[multicast]",
                "ResolveScope = link",
                $"ListenAddress = {localAddress}",
                "",
                "[lab]",
                $"KnownPeers = {{{string.Join(", ", peers)}}}",
                $"SessionID = {sessionId}",
                "",
                "[log]",
                "level = 0",
                "",
            ]);
        File.WriteAllText(_lslCommandApiConfigPath, _lslCommandApiConfigContent, new UTF8Encoding(false));
        Environment.SetEnvironmentVariable("LSLAPICFG", _lslCommandApiConfigPath, EnvironmentVariableTarget.Process);
        AddEvent(
            "qcl081_lsl_command.api_config",
            "pass",
            $"wrote per-run LSLAPICFG with ListenAddress={localAddress}, KnownPeers={string.Join(",", peers)}");
    }

    private static string SanitizeLslSessionId(string value)
    {
        var text = string.IsNullOrWhiteSpace(value) ? "qcl081-direct-wifi" : value.Trim();
        var builder = new StringBuilder(text.Length);
        foreach (var ch in text)
        {
            builder.Append(char.IsLetterOrDigit(ch) || ch is '-' or '_' or '.' ? ch : '-');
        }
        return builder.Length == 0 ? "qcl081-direct-wifi" : builder.ToString();
    }

    private static string XmlTagValue(string xml, string tag)
    {
        if (string.IsNullOrEmpty(xml) || string.IsNullOrEmpty(tag))
        {
            return "";
        }
        var openTag = $"<{tag}>";
        var closeTag = $"</{tag}>";
        var start = xml.IndexOf(openTag, StringComparison.Ordinal);
        if (start < 0)
        {
            return "";
        }
        var valueStart = start + openTag.Length;
        var end = xml.IndexOf(closeTag, valueStart, StringComparison.Ordinal);
        if (end < valueStart)
        {
            return "";
        }
        return xml[valueStart..end];
    }

    private static Dictionary<string, object?>? BuildMsSummary(IReadOnlyList<double> values)
    {
        if (values.Count == 0)
        {
            return null;
        }
        var ordered = values.OrderBy(value => value).ToArray();
        return new Dictionary<string, object?>
        {
            ["count"] = ordered.Length,
            ["min"] = Math.Round(ordered[0], 3),
            ["median"] = Math.Round(Percentile(ordered, 50.0), 3),
            ["p95"] = Math.Round(Percentile(ordered, 95.0), 3),
            ["max"] = Math.Round(ordered[^1], 3),
        };
    }

    private static double Percentile(IReadOnlyList<double> ordered, double percentile)
    {
        if (ordered.Count == 0)
        {
            return double.NaN;
        }
        if (ordered.Count == 1)
        {
            return ordered[0];
        }
        var position = Math.Clamp(percentile, 0.0, 100.0) / 100.0 * (ordered.Count - 1);
        var lower = (int)Math.Floor(position);
        var upper = (int)Math.Ceiling(position);
        if (lower == upper)
        {
            return ordered[lower];
        }
        var fraction = position - lower;
        return ordered[lower] + ((ordered[upper] - ordered[lower]) * fraction);
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
                ["lsl_command_outlet_enabled"] = options.LslCommandOutletEnabled,
                ["lsl_command_status"] = _lslCommandStatus,
                ["lsl_command_samples_requested"] = options.LslCommandSampleCount,
                ["lsl_command_samples_published"] = _lslCommandSamplesPublished,
                ["lsl_command_source_id"] = options.LslCommandSourceId,
                ["lsl_command_api_config_path"] = _lslCommandApiConfigPath,
                ["lsl_command_api_config_content"] = _lslCommandApiConfigContent,
                ["lsl_command_stream_info"] = new Dictionary<string, object?>
                {
                    ["hostname"] = _lslCommandHostname,
                    ["uid"] = _lslCommandUid,
                    ["session_id"] = _lslCommandSessionId,
                    ["created_at_seconds"] = _lslCommandCreatedAtSeconds,
                    ["v4address"] = _lslCommandV4Address,
                    ["v4data_port"] = _lslCommandV4DataPort,
                    ["v4service_port"] = _lslCommandV4ServicePort,
                    ["v6address"] = _lslCommandV6Address,
                    ["v6data_port"] = _lslCommandV6DataPort,
                    ["v6service_port"] = _lslCommandV6ServicePort,
                    ["xml"] = _lslCommandStreamXml,
                },
                ["lsl_command_first_sequence"] = _lslCommandFirstSequence >= 0 ? _lslCommandFirstSequence : null,
                ["lsl_command_last_sequence"] = _lslCommandLastSequence >= 0 ? _lslCommandLastSequence : null,
                ["lsl_command_first_clock_seconds"] = _lslCommandFirstClockSeconds,
                ["lsl_command_last_clock_seconds"] = _lslCommandLastClockSeconds,
                ["lsl_command_publish_started_at_utc"] = _lslCommandPublishStartedAtUtc?.ToString("O"),
                ["lsl_command_publish_ended_at_utc"] = _lslCommandPublishEndedAtUtc?.ToString("O"),
                ["lsl_command_publish_elapsed_ms"] = _lslCommandPublishElapsedMs.HasValue
                    ? Math.Round(_lslCommandPublishElapsedMs.Value, 3)
                    : null,
                ["lsl_command_publish_interval_ms_summary"] = BuildMsSummary(_lslCommandPublishIntervalMs),
                ["lsl_command_last_push_result"] = _lslCommandLastPushResult,
                ["lsl_command_last_error"] = _lslCommandLastError,
                ["lsl_command_timing_samples"] = _lslCommandTimingSamples,
                ["lsl_command_timing_samples_tail"] = _lslCommandTimingTail.ToArray(),
                ["lsl_command_hold_after_ms"] = options.LslCommandHoldAfterMs,
                ["lsl_command_issue"] = _lslCommandIssue,
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

internal sealed class LslNative : IDisposable
{
    private readonly IntPtr _library;
    private readonly CreateStreamInfoDelegate _createStreamInfo;
    private readonly DestroyStreamInfoDelegate _destroyStreamInfo;
    private readonly CreateOutletDelegate _createOutlet;
    private readonly DestroyOutletDelegate _destroyOutlet;
    private readonly PushSampleDtpDelegate _pushSampleDtp;
    private readonly LocalClockDelegate _localClock;
    private readonly SetConfigContentDelegate? _setConfigContent;
    private readonly StringDelegate _libraryInfo;
    private readonly StringDelegate _lastError;
    private readonly StreamInfoStringDelegate _getXml;
    private readonly StreamInfoStringDelegate _getHostname;
    private readonly StreamInfoStringDelegate _getUid;
    private readonly StreamInfoStringDelegate _getSessionId;
    private readonly StreamInfoDoubleDelegate _getCreatedAt;

    private LslNative(IntPtr library)
    {
        _library = library;
        _createStreamInfo = GetDelegate<CreateStreamInfoDelegate>("lsl_create_streaminfo");
        _destroyStreamInfo = GetDelegate<DestroyStreamInfoDelegate>("lsl_destroy_streaminfo");
        _createOutlet = GetDelegate<CreateOutletDelegate>("lsl_create_outlet");
        _destroyOutlet = GetDelegate<DestroyOutletDelegate>("lsl_destroy_outlet");
        _pushSampleDtp = GetDelegate<PushSampleDtpDelegate>("lsl_push_sample_dtp");
        _localClock = GetDelegate<LocalClockDelegate>("lsl_local_clock");
        _setConfigContent = TryGetDelegate<SetConfigContentDelegate>("lsl_set_config_content");
        _libraryInfo = GetDelegate<StringDelegate>("lsl_library_info");
        _lastError = GetDelegate<StringDelegate>("lsl_last_error");
        _getXml = GetDelegate<StreamInfoStringDelegate>("lsl_get_xml");
        _getHostname = GetDelegate<StreamInfoStringDelegate>("lsl_get_hostname");
        _getUid = GetDelegate<StreamInfoStringDelegate>("lsl_get_uid");
        _getSessionId = GetDelegate<StreamInfoStringDelegate>("lsl_get_session_id");
        _getCreatedAt = GetDelegate<StreamInfoDoubleDelegate>("lsl_get_created_at");
    }

    public string LibraryInfo => PtrToString(_libraryInfo());

    public string LastError => PtrToString(_lastError());

    public static LslNative Load(string path)
    {
        var libraryPath = string.IsNullOrWhiteSpace(path)
            ? throw new ArgumentException("liblsl path is required", nameof(path))
            : Path.GetFullPath(path);
        if (!File.Exists(libraryPath))
        {
            throw new FileNotFoundException("liblsl DLL not found", libraryPath);
        }
        return new LslNative(NativeLibrary.Load(libraryPath));
    }

    public IntPtr CreateStreamInfo(
        string name,
        string type,
        int channelCount,
        double nominalSrate,
        int channelFormat,
        string sourceId) =>
        _createStreamInfo(name, type, channelCount, nominalSrate, channelFormat, sourceId);

    public IntPtr CreateOutlet(IntPtr streamInfo, int chunkSize, int maxBuffered) =>
        _createOutlet(streamInfo, chunkSize, maxBuffered);

    public int PushSampleDtp(IntPtr outlet, double[] sample, double timestamp, int pushthrough) =>
        _pushSampleDtp(outlet, sample, timestamp, pushthrough);

    public double LocalClock() => _localClock();

    public bool TrySetConfigContent(string content)
    {
        if (_setConfigContent is null)
        {
            return false;
        }
        _setConfigContent(content);
        return true;
    }

    public string GetXml(IntPtr info) => PtrToString(_getXml(info));

    public string GetHostname(IntPtr info) => PtrToString(_getHostname(info));

    public string GetUid(IntPtr info) => PtrToString(_getUid(info));

    public string GetSessionId(IntPtr info) => PtrToString(_getSessionId(info));

    public double GetCreatedAt(IntPtr info) => _getCreatedAt(info);

    public void DestroyOutlet(IntPtr outlet)
    {
        _destroyOutlet(outlet);
    }

    public void DestroyStreamInfo(IntPtr streamInfo)
    {
        _destroyStreamInfo(streamInfo);
    }

    public void Dispose()
    {
        NativeLibrary.Free(_library);
    }

    private T GetDelegate<T>(string name) where T : Delegate =>
        Marshal.GetDelegateForFunctionPointer<T>(NativeLibrary.GetExport(_library, name));

    private T? TryGetDelegate<T>(string name) where T : Delegate =>
        NativeLibrary.TryGetExport(_library, name, out var address)
            ? Marshal.GetDelegateForFunctionPointer<T>(address)
            : null;

    private static string PtrToString(IntPtr value) =>
        value == IntPtr.Zero ? "" : (Marshal.PtrToStringUTF8(value) ?? "");

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate IntPtr CreateStreamInfoDelegate(
        [MarshalAs(UnmanagedType.LPUTF8Str)] string name,
        [MarshalAs(UnmanagedType.LPUTF8Str)] string type,
        int channelCount,
        double nominalSrate,
        int channelFormat,
        [MarshalAs(UnmanagedType.LPUTF8Str)] string sourceId);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void DestroyStreamInfoDelegate(IntPtr streamInfo);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate IntPtr CreateOutletDelegate(IntPtr streamInfo, int chunkSize, int maxBuffered);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void DestroyOutletDelegate(IntPtr outlet);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate int PushSampleDtpDelegate(IntPtr outlet, [In] double[] sample, double timestamp, int pushthrough);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate double LocalClockDelegate();

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate void SetConfigContentDelegate([MarshalAs(UnmanagedType.LPUTF8Str)] string content);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate IntPtr StringDelegate();

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate IntPtr StreamInfoStringDelegate(IntPtr info);

    [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
    private delegate double StreamInfoDoubleDelegate(IntPtr info);
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
    public bool LslCommandOutletEnabled { get; init; }
    public string LslDllPath { get; init; } = "";
    public string LslCommandStreamName { get; init; } = "RustyQCL081WifiDirectCommand";
    public string LslCommandStreamType { get; init; } = "rusty.quest.qcl081.wifi_direct.command";
    public string LslCommandSourceId { get; init; } = "";
    public int LslCommandSampleCount { get; init; } = 300;
    public int LslCommandIntervalMs { get; init; } = 100;
    public int LslCommandStartDelayMs { get; init; } = 250;
    public int LslCommandHoldAfterMs { get; init; } = 10000;

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
            LslCommandOutletEnabled = values.TryGetValue("lsl-command-outlet", out var lslCommandOutlet)
                && string.Equals(lslCommandOutlet, "true", StringComparison.OrdinalIgnoreCase),
            LslDllPath = values.GetValueOrDefault("lsl-dll", ""),
            LslCommandStreamName = values.GetValueOrDefault("lsl-command-stream-name", "RustyQCL081WifiDirectCommand"),
            LslCommandStreamType = values.GetValueOrDefault("lsl-command-stream-type", "rusty.quest.qcl081.wifi_direct.command"),
            LslCommandSourceId = values.GetValueOrDefault("lsl-command-source-id", ""),
            LslCommandSampleCount = int.TryParse(values.GetValueOrDefault("lsl-command-sample-count"), out var lslCommandSampleCount)
                ? Math.Max(1, lslCommandSampleCount)
                : 300,
            LslCommandIntervalMs = int.TryParse(values.GetValueOrDefault("lsl-command-interval-ms"), out var lslCommandIntervalMs)
                ? Math.Max(1, lslCommandIntervalMs)
                : 100,
            LslCommandStartDelayMs = int.TryParse(values.GetValueOrDefault("lsl-command-start-delay-ms"), out var lslCommandStartDelayMs)
                ? Math.Max(0, lslCommandStartDelayMs)
                : 250,
            LslCommandHoldAfterMs = int.TryParse(values.GetValueOrDefault("lsl-command-hold-after-ms"), out var lslCommandHoldAfterMs)
                ? Math.Max(0, lslCommandHoldAfterMs)
                : 10000,
        };
    }
}
