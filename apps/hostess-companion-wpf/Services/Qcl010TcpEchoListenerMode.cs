using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Services;

internal static class Qcl010TcpEchoListenerMode
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        WriteIndented = true,
    };

    public static bool IsListenerMode(string[] args) =>
        args.Any(arg => string.Equals(arg, "--qcl010-tcp-echo-listener", StringComparison.OrdinalIgnoreCase));

    public static int Run(string[] args)
    {
        var options = ParseOptions(args);
        var outPath = Required(options, "out");
        try
        {
            var result = Listen(
                bindHost: ValueOrDefault(options, "bind-host", "0.0.0.0"),
                requestedPort: IntOption(options, "port", 18766),
                marker: ValueOrDefault(options, "marker", "rusty-qcl-tcp-echo"),
                timeoutSeconds: Math.Max(0.5, DoubleOption(options, "timeout-seconds", 4.0)),
                readyOut: ValueOrDefault(options, "ready-out", ""));
            WriteJson(outPath, result);
            return result.Status == "pass" ? 0 : 1;
        }
        catch (Exception ex)
        {
            WriteJson(
                outPath,
                new Qcl010TcpEchoResult
                {
                    Schema = "rusty.hostess.wpf.qcl010_tcp_echo_listener.v1",
                    Status = "fail",
                    Program = Environment.ProcessPath ?? "",
                    Error = ex.Message,
                });
            return 2;
        }
    }

    private static Qcl010TcpEchoResult Listen(
        string bindHost,
        int requestedPort,
        string marker,
        double timeoutSeconds,
        string readyOut)
    {
        using var server = new Socket(AddressFamily.InterNetwork, SocketType.Stream, ProtocolType.Tcp);
        server.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
        server.Bind(new IPEndPoint(ParseAddress(bindHost), requestedPort));
        server.Listen(1);
        var local = (IPEndPoint)server.LocalEndPoint!;
        var program = Environment.ProcessPath ?? Process.GetCurrentProcess().MainModule?.FileName ?? "";
        var result = new Qcl010TcpEchoResult
        {
            Schema = "rusty.hostess.wpf.qcl010_tcp_echo_listener.v1",
            Status = "fail",
            Program = program,
            BindHost = bindHost,
            Port = local.Port,
            Marker = marker,
        };
        if (!string.IsNullOrWhiteSpace(readyOut))
        {
            WriteJson(
                readyOut,
                new
                {
                    schema = "rusty.hostess.wpf.qcl010_tcp_echo_listener.ready.v1",
                    status = "ready",
                    program,
                    bind_host = bindHost,
                    port = local.Port,
                    marker,
                });
        }

        var stopwatch = Stopwatch.StartNew();
        using var connection = Accept(server, timeoutSeconds);
        if (connection is null)
        {
            stopwatch.Stop();
            result.ElapsedMs = (long)Math.Round(stopwatch.Elapsed.TotalMilliseconds);
            result.Error = "no TCP connection accepted";
            return result;
        }

        var remote = connection.RemoteEndPoint?.ToString() ?? "";
        connection.ReceiveTimeout = (int)Math.Ceiling(timeoutSeconds * 1000);
        var buffer = new byte[512];
        var received = connection.Receive(buffer);
        stopwatch.Stop();
        result.ElapsedMs = (long)Math.Round(stopwatch.Elapsed.TotalMilliseconds);
        result.Peer = remote;
        result.Payload = Encoding.UTF8.GetString(buffer, 0, received).Trim();
        result.BytesReceived = received;
        result.Status = result.Payload.Contains(marker, StringComparison.Ordinal) ? "pass" : "fail";
        if (result.Status != "pass")
        {
            result.Error = "matching TCP echo marker was not received";
        }
        return result;
    }

    private static Socket? Accept(Socket server, double timeoutSeconds)
    {
        var accepted = server.AcceptAsync();
        return accepted.Wait(TimeSpan.FromSeconds(timeoutSeconds)) ? accepted.Result : null;
    }

    private static IPAddress ParseAddress(string bindHost)
    {
        if (string.IsNullOrWhiteSpace(bindHost) || bindHost == "0.0.0.0")
        {
            return IPAddress.Any;
        }
        return IPAddress.Parse(bindHost);
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
            if (string.Equals(key, "qcl010-tcp-echo-listener", StringComparison.OrdinalIgnoreCase))
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
        int.TryParse(ValueOrDefault(options, key, ""), out var value) ? value : fallback;

    private static double DoubleOption(Dictionary<string, string> options, string key, double fallback) =>
        double.TryParse(ValueOrDefault(options, key, ""), out var value) ? value : fallback;

    private static void WriteJson(string path, object value)
    {
        var file = new FileInfo(path);
        file.Directory?.Create();
        File.WriteAllText(file.FullName, JsonSerializer.Serialize(value, JsonOptions) + Environment.NewLine);
    }

    private sealed class Qcl010TcpEchoResult
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

        [JsonPropertyName("bytes_received")]
        public int BytesReceived { get; set; }

        [JsonPropertyName("payload")]
        public string Payload { get; set; } = "";

        [JsonPropertyName("peer")]
        public string Peer { get; set; } = "";

        [JsonPropertyName("elapsed_ms")]
        public long ElapsedMs { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; } = "";
    }
}
