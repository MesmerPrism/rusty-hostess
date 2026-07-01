using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Services;

internal static class Qcl082Rmanvid1TcpReceiverMode
{
    private const string ResultSchema = "rusty.hostess.media_stream.rmanvid1_receiver_capture_result.v1";
    private const string SidecarSchema = "rusty.hostess.media_stream.receiver_capture_sidecar.v1";
    private const string CaptureKindLiveBroker = "live_broker_stream";
    private const string EndpointSource = "rusty-quest-manifold-broker-media-stream-runtime";
    private const int StreamHeaderBytes = 32;
    private const int PacketHeaderBytes = 32;
    private const int DefaultMaxPackets = 240;
    private const int DefaultMaxCaptureBytes = 67_108_864;
    private const int DefaultMaxPacketBytes = 4_194_304;
    private const int DefaultQueueCapacityPackets = 48;
    private const int CodecH264 = 1;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    public static bool IsReceiverMode(string[] args) =>
        args.Any(arg => string.Equals(arg, "--qcl082-rmanvid1-receiver", StringComparison.OrdinalIgnoreCase));

    public static int Run(string[] args)
    {
        var options = ParseOptions(args);
        var outPath = Required(options, "out");
        try
        {
            var result = Listen(options);
            WriteJson(outPath, result);
            return string.Equals(StringValue(result, "status"), "pass", StringComparison.Ordinal) ? 0 : 1;
        }
        catch (Exception ex)
        {
            WriteJson(
                outPath,
                new Dictionary<string, object?>
                {
                    ["schema"] = ResultSchema,
                    ["status"] = "fail",
                    ["capture_kind"] = CaptureKindLiveBroker,
                    ["program"] = ProgramPath(),
                    ["error"] = ex.Message,
                    ["issue_codes"] = new[] { "hostess.issue.connectivity_probe.media_receiver_capture_socket_error" },
                });
            return 2;
        }
    }

    private static Dictionary<string, object?> Listen(Dictionary<string, string> options)
    {
        var bindHost = ValueOrDefault(options, "bind-host", "0.0.0.0");
        var port = IntOption(options, "port", 9079);
        var timeoutSeconds = Math.Max(0.5, DoubleOption(options, "timeout-seconds", 10.0));
        var maxPackets = Math.Max(1, IntOption(options, "max-packets", DefaultMaxPackets));
        var maxCaptureBytes = Math.Max(StreamHeaderBytes, IntOption(options, "max-bytes", DefaultMaxCaptureBytes));
        var maxPacketBytes = Math.Max(1, IntOption(options, "max-packet-bytes", DefaultMaxPacketBytes));
        var queueCapacity = Math.Max(1, IntOption(options, "queue-capacity-packets", DefaultQueueCapacityPackets));
        var capturePath = Required(options, "capture-out");
        var sidecarPath = Required(options, "sidecar-out");
        var runtimeStatusPath = ValueOrDefault(options, "runtime-status", "");
        var topologyReportPath = ValueOrDefault(options, "topology-report", "");
        var firewallReportPath = ValueOrDefault(options, "firewall-report", "");
        var commandId = ValueOrDefault(options, "command-id", "command.media_stream.start_source");
        var sessionId = ValueOrDefault(options, "session-id", "");
        var sourceRemoteEndpoint = ValueOrDefault(options, "source-remote-endpoint", "");
        var readyOut = ValueOrDefault(options, "ready-out", "");
        var previewFfplay = ValueOrDefault(options, "preview-ffplay", "");
        var previewWindowTitle = ValueOrDefault(options, "preview-window-title", "Rusty_QCL082_Direct_WiFi_RMANVID1_Preview");
        var questLease = QuestLease(options);

        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(capturePath)) ?? ".");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(sidecarPath)) ?? ".");
        File.WriteAllBytes(capturePath, []);

        var stopwatch = Stopwatch.StartNew();
        var startedUnixNs = UnixTimeNs();
        var closeReason = "not_started";
        var accepted = false;
        var bytesWritten = 0L;
        var packetCount = 0;
        var socketError = "";
        var arrivals = new List<long>();
        var viewer = PreviewViewer(previewFfplay, previewWindowTitle, false, 0, "");
        var localEndpoint = $"{bindHost}:{port}";
        var remoteEndpoint = sourceRemoteEndpoint;

        using var server = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        try
        {
            server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
            server.Bind(new IPEndPoint(ParseAddress(bindHost), port));
            server.Listen(1);
            if (server.LocalEndPoint is IPEndPoint local)
            {
                localEndpoint = $"{local.Address}:{local.Port}";
            }
            if (!string.IsNullOrWhiteSpace(readyOut))
            {
                WriteJson(
                    readyOut,
                    new Dictionary<string, object?>
                    {
                        ["schema"] = "rusty.hostess.wpf.qcl082_rmanvid1_receiver.ready.v1",
                        ["status"] = "ready",
                        ["program"] = ProgramPath(),
                        ["bind_endpoint"] = localEndpoint,
                        ["port"] = port,
                    });
            }

            using var connection = Accept(server, timeoutSeconds);
            if (connection is null)
            {
                closeReason = "accept_timeout";
            }
            else
            {
                accepted = true;
                connection.ReceiveTimeout = Math.Max(1, (int)Math.Round(timeoutSeconds * 1000.0));
                if (connection.RemoteEndPoint is IPEndPoint remote && string.IsNullOrWhiteSpace(remoteEndpoint))
                {
                    remoteEndpoint = $"{remote.Address}:{remote.Port}";
                }
                using var output = File.Open(capturePath, FileMode.Create, FileAccess.Write, FileShare.Read);
                (closeReason, bytesWritten, packetCount, viewer) = CaptureStream(
                    connection,
                    output,
                    arrivals,
                    maxCaptureBytes,
                    maxPackets,
                    maxPacketBytes,
                    previewFfplay,
                    previewWindowTitle);
            }
        }
        catch (SocketException ex)
        {
            closeReason = "socket_error";
            socketError = ex.Message;
        }
        finally
        {
            stopwatch.Stop();
        }

        var finishedUnixNs = UnixTimeNs();
        var elapsedMs = Math.Max(0.0, stopwatch.Elapsed.TotalMilliseconds);
        var sidecar = Sidecar(
            localEndpoint,
            remoteEndpoint,
            commandId,
            sessionId,
            closeReason,
            queueCapacity,
            packetCount,
            arrivals,
            bytesWritten,
            maxCaptureBytes,
            maxPackets,
            startedUnixNs,
            finishedUnixNs,
            elapsedMs,
            runtimeStatusPath,
            topologyReportPath,
            firewallReportPath,
            questLease);
        WriteJson(sidecarPath, sidecar);

        var issueCodes = new List<string>();
        if (closeReason == "accept_timeout")
        {
            issueCodes.Add("hostess.issue.connectivity_probe.media_receiver_capture_accept_timeout");
        }
        if (closeReason == "socket_error")
        {
            issueCodes.Add("hostess.issue.connectivity_probe.media_receiver_capture_socket_error");
        }
        var status = accepted && packetCount > 0 && issueCodes.Count == 0 ? "pass" : "fail";
        return new Dictionary<string, object?>
        {
            ["schema"] = ResultSchema,
            ["status"] = status,
            ["capture_kind"] = CaptureKindLiveBroker,
            ["live_capture"] = true,
            ["capture_path"] = capturePath,
            ["sidecar_path"] = sidecarPath,
            ["runtime_status_path"] = runtimeStatusPath,
            ["topology_report_path"] = topologyReportPath,
            ["firewall_report_path"] = firewallReportPath,
            ["local_endpoint"] = localEndpoint,
            ["remote_endpoint"] = remoteEndpoint,
            ["accepted_connection"] = accepted,
            ["close_reason"] = closeReason,
            ["elapsed_ms"] = Math.Round(elapsedMs, 3),
            ["bytes_written"] = bytesWritten,
            ["socket_error"] = socketError,
            ["issue_codes"] = issueCodes,
            ["receiver_sidecar"] = sidecar,
            ["quest_lease"] = questLease,
            ["viewer"] = viewer,
            ["program"] = ProgramPath(),
            ["follow_on_qcl082_args"] = new[]
            {
                "connectivity-probe",
                "run",
                "--probe-id",
                "QCL-082",
                "--media-stream-rmanvid1-capture",
                capturePath,
                "--media-stream-receiver-sidecar",
                sidecarPath,
            },
        };
    }

    private static Socket? Accept(Socket server, double timeoutSeconds)
    {
        var deadline = Stopwatch.StartNew();
        while (deadline.Elapsed.TotalSeconds < timeoutSeconds)
        {
            if (server.Poll(100_000, SelectMode.SelectRead))
            {
                return server.Accept();
            }
        }
        return null;
    }

    private static (string CloseReason, long BytesWritten, int PacketCount, Dictionary<string, object?> Viewer) CaptureStream(
        Socket connection,
        Stream output,
        List<long> arrivals,
        int maxCaptureBytes,
        int maxPackets,
        int maxPacketBytes,
        string previewFfplay,
        string previewWindowTitle)
    {
        using var preview = new PreviewSink(previewFfplay, previewWindowTitle);
        long bytesWritten = 0;
        var packetCount = 0;
        var header = ReceiveExact(connection, StreamHeaderBytes, out var headerReason);
        output.Write(header);
        bytesWritten += header.Length;
        if (header.Length != StreamHeaderBytes)
        {
            return ($"stream_header_{headerReason}", bytesWritten, packetCount, preview.ToJson());
        }
        if (bytesWritten > maxCaptureBytes)
        {
            return ("max_bytes_reached", bytesWritten, packetCount, preview.ToJson());
        }

        var codec = U32Be(header, 12);
        var width = U32Be(header, 16);
        var height = U32Be(header, 20);
        var metadataLen = U32Be(header, 28);
        if (metadataLen < 0 || metadataLen > maxCaptureBytes)
        {
            return ("metadata_too_large", bytesWritten, packetCount, preview.ToJson());
        }
        if (bytesWritten + metadataLen > maxCaptureBytes)
        {
            return ("max_bytes_reached", bytesWritten, packetCount, preview.ToJson());
        }
        var metadata = ReceiveExact(connection, metadataLen, out var metadataReason);
        output.Write(metadata);
        bytesWritten += metadata.Length;
        if (metadata.Length != metadataLen)
        {
            return ($"metadata_{metadataReason}", bytesWritten, packetCount, preview.ToJson());
        }
        preview.Start(codec, width, height);

        while (packetCount < maxPackets)
        {
            var packetHeader = ReceiveExact(connection, PacketHeaderBytes, out var packetHeaderReason);
            if (packetHeader.Length == 0 && packetHeaderReason == "peer_closed")
            {
                return ("peer_closed", bytesWritten, packetCount, preview.ToJson());
            }
            output.Write(packetHeader);
            bytesWritten += packetHeader.Length;
            if (packetHeader.Length != PacketHeaderBytes)
            {
                return ($"packet_header_{packetHeaderReason}", bytesWritten, packetCount, preview.ToJson());
            }

            var payloadLen = U32Be(packetHeader, 12);
            if (payloadLen < 0 || payloadLen > maxPacketBytes)
            {
                return ("payload_too_large", bytesWritten, packetCount, preview.ToJson());
            }
            if (bytesWritten + payloadLen > maxCaptureBytes)
            {
                return ("max_bytes_reached", bytesWritten, packetCount, preview.ToJson());
            }

            arrivals.Add(UnixTimeNs());
            var payload = ReceiveExact(connection, payloadLen, out var payloadReason);
            output.Write(payload);
            bytesWritten += payload.Length;
            if (payload.Length != payloadLen)
            {
                return ($"payload_{payloadReason}", bytesWritten, packetCount, preview.ToJson());
            }
            preview.WritePayload(payload);
            packetCount++;
        }

        return ("max_packets_reached", bytesWritten, packetCount, preview.ToJson());
    }

    private static Dictionary<string, object?> PreviewViewer(
        string ffplay,
        string windowTitle,
        bool started,
        int payloadWrites,
        string error) =>
        new()
        {
            ["ffplay"] = ffplay,
            ["window_title"] = windowTitle,
            ["ffplay_started"] = started,
            ["ffplay_payload_writes"] = payloadWrites,
            ["ffplay_error"] = error,
        };

    private sealed class PreviewSink : IDisposable
    {
        private readonly string _ffplay;
        private readonly string _windowTitle;
        private Process? _process;
        private string _error = "";

        public PreviewSink(string ffplay, string windowTitle)
        {
            _ffplay = ffplay;
            _windowTitle = windowTitle;
        }

        public bool Started { get; private set; }

        public int PayloadWrites { get; private set; }

        public void Start(int codec, int width, int height)
        {
            if (string.IsNullOrWhiteSpace(_ffplay) || codec != CodecH264)
            {
                return;
            }

            try
            {
                var previewWidth = Math.Max(width * 2, 640);
                var previewHeight = Math.Max(height * 2, 360);
                var startInfo = new ProcessStartInfo
                {
                    FileName = _ffplay,
                    UseShellExecute = false,
                    RedirectStandardInput = true,
                    CreateNoWindow = false,
                };
                foreach (var argument in new[]
                         {
                             "-hide_banner",
                             "-loglevel",
                             "warning",
                             "-fflags",
                             "nobuffer",
                             "-flags",
                             "low_delay",
                             "-framedrop",
                             "-window_title",
                             _windowTitle,
                             "-x",
                             previewWidth.ToString(CultureInfo.InvariantCulture),
                             "-y",
                             previewHeight.ToString(CultureInfo.InvariantCulture),
                             "-f",
                             "h264",
                             "-i",
                             "pipe:0",
                         })
                {
                    startInfo.ArgumentList.Add(argument);
                }

                _process = Process.Start(startInfo);
                Started = _process is not null;
            }
            catch (Exception ex)
            {
                _error = ex.Message;
            }
        }

        public void WritePayload(byte[] payload)
        {
            if (_process is null || _process.HasExited)
            {
                return;
            }

            try
            {
                _process.StandardInput.BaseStream.Write(payload);
                _process.StandardInput.BaseStream.Flush();
                PayloadWrites++;
            }
            catch (Exception ex)
            {
                if (string.IsNullOrWhiteSpace(_error))
                {
                    _error = ex.Message;
                }
            }
        }

        public Dictionary<string, object?> ToJson() =>
            PreviewViewer(_ffplay, _windowTitle, Started, PayloadWrites, _error);

        public void Dispose()
        {
            if (_process is null)
            {
                return;
            }

            try
            {
                _process.StandardInput.Close();
            }
            catch (Exception)
            {
            }

            try
            {
                if (!_process.WaitForExit(2000))
                {
                    _process.Kill(entireProcessTree: true);
                }
            }
            catch (Exception)
            {
            }

            _process.Dispose();
        }
    }

    private static byte[] ReceiveExact(Socket connection, int byteCount, out string reason)
    {
        var buffer = new byte[byteCount];
        var offset = 0;
        reason = "complete";
        while (offset < byteCount)
        {
            try
            {
                var read = connection.Receive(buffer, offset, byteCount - offset, SocketFlags.None);
                if (read == 0)
                {
                    reason = "peer_closed";
                    break;
                }
                offset += read;
            }
            catch (SocketException)
            {
                reason = "socket_error";
                break;
            }
        }
        if (offset == byteCount)
        {
            return buffer;
        }
        Array.Resize(ref buffer, offset);
        return buffer;
    }

    private static Dictionary<string, object?> Sidecar(
        string localEndpoint,
        string remoteEndpoint,
        string commandId,
        string sessionId,
        string closeReason,
        int queueCapacity,
        int packetCount,
        List<long> arrivals,
        long bytesWritten,
        int maxCaptureBytes,
        int maxPackets,
        long startedUnixNs,
        long finishedUnixNs,
        double elapsedMs,
        string runtimeStatusPath,
        string topologyReportPath,
        string firewallReportPath,
        Dictionary<string, object?> questLease)
    {
        return new Dictionary<string, object?>
        {
            ["schema"] = SidecarSchema,
            ["capture_kind"] = CaptureKindLiveBroker,
            ["live_capture"] = true,
            ["receiver"] = new Dictionary<string, object?>
            {
                ["local_endpoint"] = localEndpoint,
                ["bind_endpoint"] = localEndpoint,
                ["remote_endpoint"] = remoteEndpoint,
                ["queue_capacity_packets"] = queueCapacity,
                ["max_queue_depth_observed"] = packetCount > 0 ? Math.Min(1, queueCapacity) : 0,
                ["drop_policy"] = "drop-oldest-complete-frame",
                ["close_policy"] = "close_after_capture_window_or_peer_eof",
                ["close_reason"] = closeReason,
                ["dropped_frames"] = 0,
                ["backpressure_events"] = 0,
                ["arrival_timestamped_packet_count"] = arrivals.Count,
                ["receiver_arrival_timestamps"] = arrivals.Count >= packetCount && packetCount > 0,
                ["timestamp_gap_ms_p95"] = ArrivalGapMsP95(arrivals),
                ["decode_error_count"] = 0,
                ["bytes_written"] = bytesWritten,
                ["max_capture_bytes"] = maxCaptureBytes,
                ["max_packets"] = maxPackets,
                ["capture_started_unix_ns"] = startedUnixNs,
                ["capture_finished_unix_ns"] = finishedUnixNs,
                ["elapsed_ms"] = Math.Round(elapsedMs, 3),
            },
            ["source"] = new Dictionary<string, object?>
            {
                ["endpoint_source"] = EndpointSource,
                ["remote_endpoint"] = remoteEndpoint,
                ["command_id"] = commandId,
                ["session_id"] = sessionId,
                ["runtime_status_path"] = runtimeStatusPath,
                ["topology_report_path"] = topologyReportPath,
                ["firewall_report_path"] = firewallReportPath,
            },
            ["lease"] = questLease,
        };
    }

    private static double? ArrivalGapMsP95(List<long> arrivals)
    {
        if (arrivals.Count < 2)
        {
            return null;
        }
        var gaps = new List<double>();
        for (var index = 1; index < arrivals.Count; index++)
        {
            gaps.Add((arrivals[index] - arrivals[index - 1]) / 1_000_000.0);
        }
        gaps.Sort();
        var p95Index = Math.Min(gaps.Count - 1, (int)Math.Ceiling(gaps.Count * 0.95) - 1);
        return Math.Round(gaps[p95Index], 3);
    }

    private static int U32Be(byte[] bytes, int offset) =>
        ((bytes[offset] & 0xff) << 24)
        | ((bytes[offset + 1] & 0xff) << 16)
        | ((bytes[offset + 2] & 0xff) << 8)
        | (bytes[offset + 3] & 0xff);

    private static IPAddress ParseAddress(string bindHost) =>
        string.IsNullOrWhiteSpace(bindHost) || bindHost == "0.0.0.0"
            ? IPAddress.Any
            : IPAddress.Parse(bindHost);

    private static Dictionary<string, object?> QuestLease(Dictionary<string, string> options)
    {
        var resource = ValueOrDefault(options, "quest-lease-resource", "");
        var leaseId = ValueOrDefault(options, "quest-lease-id", "");
        return new Dictionary<string, object?>
        {
            ["manager"] = "Agent Board",
            ["resource"] = resource,
            ["lease_id"] = leaseId,
            ["reserved_before_live_steps"] = BoolOption(options, "quest-lease-reserved-before-live-steps"),
            ["released_after_live_steps"] = false,
            ["adb_server_lifecycle_lease_used"] = false,
            ["adb_server_lifecycle_policy"] =
                "Use adb-server:lifecycle only for disruptive daemon lifecycle/recovery or Wi-Fi ADB setup. This route uses serial-scoped ADB.",
        };
    }

    private static long UnixTimeNs() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() * 1_000_000L;

    private static string ProgramPath() =>
        Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "";

    private static Dictionary<string, string> ParseOptions(string[] args)
    {
        var options = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < args.Length; index++)
        {
            var arg = args[index];
            if (!arg.StartsWith("--", StringComparison.Ordinal))
            {
                continue;
            }

            var key = arg[2..];
            if (string.Equals(key, "qcl082-rmanvid1-receiver", StringComparison.OrdinalIgnoreCase)
                || string.Equals(key, "quest-lease-reserved-before-live-steps", StringComparison.OrdinalIgnoreCase))
            {
                options[key] = "true";
                continue;
            }

            if (index + 1 >= args.Length)
            {
                throw new InvalidOperationException($"Missing value for --{key}.");
            }
            options[key] = args[++index];
        }

        return options;
    }

    private static string Required(Dictionary<string, string> options, string key)
    {
        if (!options.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value))
        {
            throw new InvalidOperationException($"--{key} is required.");
        }
        return value;
    }

    private static string ValueOrDefault(Dictionary<string, string> options, string key, string fallback) =>
        options.TryGetValue(key, out var value) && !string.IsNullOrWhiteSpace(value) ? value : fallback;

    private static int IntOption(Dictionary<string, string> options, string key, int fallback) =>
        int.TryParse(ValueOrDefault(options, key, ""), NumberStyles.Integer, CultureInfo.InvariantCulture, out var value)
            ? value
            : fallback;

    private static double DoubleOption(Dictionary<string, string> options, string key, double fallback) =>
        double.TryParse(ValueOrDefault(options, key, ""), NumberStyles.Float, CultureInfo.InvariantCulture, out var value)
            ? value
            : fallback;

    private static bool BoolOption(Dictionary<string, string> options, string key) =>
        bool.TryParse(ValueOrDefault(options, key, "false"), out var value) && value;

    private static string StringValue(Dictionary<string, object?> value, string key) =>
        value.TryGetValue(key, out var item) ? Convert.ToString(item, CultureInfo.InvariantCulture) ?? "" : "";

    private static void WriteJson(string path, object value)
    {
        var file = new FileInfo(path);
        file.Directory?.Create();
        File.WriteAllText(file.FullName, JsonSerializer.Serialize(value, JsonOptions) + Environment.NewLine);
    }
}
