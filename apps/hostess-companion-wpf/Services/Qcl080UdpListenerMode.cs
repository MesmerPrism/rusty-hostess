using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Services;

internal static class Qcl080UdpListenerMode
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    public static bool IsListenerMode(string[] args) =>
        args.Any(arg => string.Equals(arg, "--qcl080-udp-listener", StringComparison.OrdinalIgnoreCase));

    public static int Run(string[] args)
    {
        var options = ParseOptions(args);
        var outPath = Required(options, "out");
        try
        {
            var bindHost = ValueOrDefault(options, "bind-host", "0.0.0.0");
            var requestedPort = IntOption(options, "port", 18767);
            var marker = ValueOrDefault(options, "marker", "rusty-qcl-udp");
            var packetCount = Math.Max(1, IntOption(options, "packet-count", 12));
            var timeoutSeconds = Math.Max(0.5, DoubleOption(options, "timeout-seconds", 5.0));
            var result = Listen(
                bindHost,
                requestedPort,
                marker,
                packetCount,
                timeoutSeconds,
                readyOut: ValueOrDefault(options, "ready-out", ""));
            WriteJson(outPath, result);
            return result.Status == "pass" ? 0 : 1;
        }
        catch (Exception ex)
        {
            WriteJson(
                outPath,
                new Qcl080UdpListenerResult
                {
                    Schema = "rusty.hostess.wpf.qcl080_udp_listener.v1",
                    Status = "fail",
                    Program = Environment.ProcessPath ?? "",
                    Error = ex.Message,
                });
            return 2;
        }
    }

    private static Qcl080UdpListenerResult Listen(
        string bindHost,
        int requestedPort,
        string marker,
        int packetCount,
        double timeoutSeconds,
        string readyOut)
    {
        using var socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, ProtocolType.Udp);
        socket.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        socket.ReceiveTimeout = 200;
        socket.Bind(new IPEndPoint(ParseAddress(bindHost), requestedPort));
        var local = (IPEndPoint)socket.LocalEndPoint!;
        var program = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "";
        var result = new Qcl080UdpListenerResult
        {
            Schema = "rusty.hostess.wpf.qcl080_udp_listener.v1",
            Status = "fail",
            Program = program,
            BindHost = bindHost,
            Port = local.Port,
            Marker = marker,
            PacketsRequested = packetCount,
        };
        if (!string.IsNullOrWhiteSpace(readyOut))
        {
            WriteJson(
                readyOut,
                new
                {
                    schema = "rusty.hostess.wpf.qcl080_udp_listener.ready.v1",
                    status = "ready",
                    program,
                    bind_host = bindHost,
                    port = local.Port,
                    marker,
                    packets_requested = packetCount,
                });
        }

        var buffer = new byte[2048];
        var stopwatch = Stopwatch.StartNew();
        while (stopwatch.Elapsed.TotalSeconds < timeoutSeconds + packetCount * 1.2)
        {
            EndPoint remote = new IPEndPoint(IPAddress.Any, 0);
            try
            {
                var received = socket.ReceiveFrom(buffer, ref remote);
                var peer = remote is IPEndPoint endpoint
                    ? $"{endpoint.Address}:{endpoint.Port}"
                    : remote.ToString() ?? "";
                result.Packets.Add(new Qcl080UdpPacket
                {
                    Payload = Encoding.UTF8.GetString(buffer, 0, received).Trim(),
                    Peer = peer,
                    ArrivalElapsedMs = (long)Math.Round(stopwatch.Elapsed.TotalMilliseconds),
                });
                if (result.Packets.Count >= packetCount)
                {
                    break;
                }
            }
            catch (SocketException ex) when (ex.SocketErrorCode == SocketError.TimedOut)
            {
            }
        }

        stopwatch.Stop();
        result.ElapsedMs = (long)Math.Round(stopwatch.Elapsed.TotalMilliseconds);
        result.PacketsReceived = result.Packets
            .Select(packet => SequenceFor(packet.Payload, marker))
            .Where(sequence => sequence.HasValue)
            .Select(sequence => sequence!.Value)
            .Distinct()
            .Count();
        result.DatagramsReceived = result.Packets.Count;
        result.Status = result.PacketsReceived > 0 ? "pass" : "fail";
        if (result.PacketsReceived == 0)
        {
            result.Error = "no matching UDP datagrams received";
        }
        return result;
    }

    private static IPAddress ParseAddress(string bindHost)
    {
        if (string.IsNullOrWhiteSpace(bindHost) || bindHost == "0.0.0.0")
        {
            return IPAddress.Any;
        }
        return IPAddress.Parse(bindHost);
    }

    private static int? SequenceFor(string payload, string marker)
    {
        var prefix = marker + "|";
        if (!payload.StartsWith(prefix, StringComparison.Ordinal))
        {
            return null;
        }

        var text = payload[prefix.Length..].Split('|', 2)[0].Trim();
        return int.TryParse(text, NumberStyles.Integer, CultureInfo.InvariantCulture, out var sequence)
            ? sequence
            : null;
    }

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
            if (string.Equals(key, "qcl080-udp-listener", StringComparison.OrdinalIgnoreCase))
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

    private static void WriteJson(string path, object value)
    {
        var file = new FileInfo(path);
        file.Directory?.Create();
        File.WriteAllText(file.FullName, JsonSerializer.Serialize(value, JsonOptions) + Environment.NewLine);
    }

    private sealed class Qcl080UdpListenerResult
    {
        [JsonPropertyName("schema")]
        public string Schema { get; set; } = "";

        [JsonPropertyName("status")]
        public string Status { get; set; } = "";

        [JsonPropertyName("program")]
        public string Program { get; set; } = "";

        [JsonPropertyName("bind_host")]
        public string BindHost { get; set; } = "";

        [JsonPropertyName("port")]
        public int Port { get; set; }

        [JsonPropertyName("marker")]
        public string Marker { get; set; } = "";

        [JsonPropertyName("packets_requested")]
        public int PacketsRequested { get; set; }

        [JsonPropertyName("packets_received")]
        public int PacketsReceived { get; set; }

        [JsonPropertyName("datagrams_received")]
        public int DatagramsReceived { get; set; }

        [JsonPropertyName("elapsed_ms")]
        public long ElapsedMs { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; } = "";

        [JsonPropertyName("packets")]
        public List<Qcl080UdpPacket> Packets { get; } = [];
    }

    private sealed class Qcl080UdpPacket
    {
        [JsonPropertyName("payload")]
        public string Payload { get; set; } = "";

        [JsonPropertyName("peer")]
        public string Peer { get; set; } = "";

        [JsonPropertyName("arrival_elapsed_ms")]
        public long ArrivalElapsedMs { get; set; }
    }
}
