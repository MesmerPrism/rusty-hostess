using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Windows.Devices.Bluetooth.Rfcomm;
using Windows.Devices.Enumeration;
using Windows.Networking.Sockets;
using Windows.Storage.Streams;

var options = CliOptions.Parse(args);
var started = DateTimeOffset.UtcNow;
var eventsLog = new List<Dictionary<string, object?>>();
var issues = new List<Dictionary<string, object?>>();
var errors = new List<string>();
var perMessage = new List<Dictionary<string, object?>>();
var status = "fail";
var blocked = false;
var bytesWritten = 0;
var bytesRead = 0;
Dictionary<string, object?> selectedDevice = new()
{
    ["id_redacted"] = false,
    ["name"] = "",
    ["is_paired"] = null,
    ["can_pair"] = null,
};

void AddEvent(string phase, string eventStatus, string evidence)
{
    eventsLog.Add(new Dictionary<string, object?>
    {
        ["phase"] = phase,
        ["status"] = eventStatus,
        ["evidence"] = evidence,
        ["observed_at_utc"] = DateTimeOffset.UtcNow.ToString("O"),
    });
}

void AddIssue(string issueCode, string severity, string message)
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

try
{
    AddEvent("host.winrt.rfcomm_api", "pass", "Windows WinRT RFCOMM API loaded");
    var serviceUuid = Guid.Parse(options.ServiceUuid);
    var serviceId = RfcommServiceId.FromUuid(serviceUuid);
    using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
    var selector = RfcommDeviceService.GetDeviceSelector(serviceId);

    AddEvent("rfcomm.service.discovery", "pass", "RFCOMM service discovery started");
    var services = await DeviceInformation.FindAllAsync(selector).AsTask(timeoutCts.Token);
    if (services.Count == 0)
    {
        blocked = true;
        status = "blocked";
        AddIssue(
            "hostess.issue.connectivity_probe.rfcomm_service_not_found_or_unpaired",
            "error",
            "Windows did not find a paired/discoverable RFCOMM service for the QCL-050 UUID");
        AddEvent("rfcomm.service.discovery", "blocked", "no RFCOMM service instance found");
    }
    else
    {
        var deviceInfo = services[0];
        selectedDevice = new Dictionary<string, object?>
        {
            ["id_redacted"] = true,
            ["name"] = deviceInfo.Name ?? "",
            ["is_paired"] = deviceInfo.Pairing?.IsPaired,
            ["can_pair"] = deviceInfo.Pairing?.CanPair,
        };
        AddEvent("rfcomm.service.discovery", "pass", $"found {services.Count} RFCOMM service instance(s)");
        AddEvent(
            "rfcomm.device.pairing_state",
            "pass",
            $"is_paired={deviceInfo.Pairing?.IsPaired}; can_pair={deviceInfo.Pairing?.CanPair}");

        using var service = await RfcommDeviceService.FromIdAsync(deviceInfo.Id).AsTask(timeoutCts.Token);
        if (service is null)
        {
            blocked = true;
            status = "blocked";
            AddIssue(
                "hostess.issue.connectivity_probe.rfcomm_service_access_denied",
                "error",
                "Windows found the RFCOMM service but could not open it");
            AddEvent("rfcomm.service.open", "blocked", "RfcommDeviceService.FromIdAsync returned null");
        }
        else
        {
            using var socket = new StreamSocket();
            await socket.ConnectAsync(
                service.ConnectionHostName,
                service.ConnectionServiceName,
                SocketProtectionLevel.BluetoothEncryptionAllowNullAuthentication).AsTask(timeoutCts.Token);
            AddEvent("rfcomm.socket.connect", "pass", "RFCOMM socket connected");

            using var writer = new DataWriter(socket.OutputStream);
            using var reader = new DataReader(socket.InputStream)
            {
                InputStreamOptions = InputStreamOptions.Partial,
            };
            for (var index = 1; index <= options.MessageCount; index += 1)
            {
                var payloadText = $"{options.PayloadPrefix};runId={options.RunId};sequence={index}\n";
                var payload = Encoding.UTF8.GetBytes(payloadText);
                var stopwatch = Stopwatch.StartNew();
                writer.WriteBytes(payload);
                await writer.StoreAsync().AsTask(timeoutCts.Token);
                await writer.FlushAsync().AsTask(timeoutCts.Token);
                bytesWritten += payload.Length;

                var response = await ReadLineAsync(reader, timeoutCts.Token);
                stopwatch.Stop();
                var responseBytes = Encoding.UTF8.GetByteCount(response);
                bytesRead += responseBytes;
                perMessage.Add(new Dictionary<string, object?>
                {
                    ["sequence"] = index,
                    ["payload_bytes"] = payload.Length,
                    ["status_bytes"] = responseBytes,
                    ["round_trip_ms"] = stopwatch.Elapsed.TotalMilliseconds,
                    ["status_preview"] = response.Length > 160 ? response[..160] : response,
                });
                AddEvent("rfcomm.payload_exchange", "pass", $"message {index} write/read completed");
            }
            status = "pass";
        }
    }
}
catch (OperationCanceledException)
{
    status = blocked ? "blocked" : "fail";
    errors.Add("RFCOMM operation timed out");
    AddIssue("hostess.issue.connectivity_probe.rfcomm_timeout", "error", "Windows helper timed out during RFCOMM discovery or payload exchange");
    AddEvent("rfcomm.timeout", status, "RFCOMM timeout");
}
catch (Exception ex)
{
    errors.Add(ex.Message);
    AddEvent("host.helper.failure", "fail", ex.Message);
}

var ended = DateTimeOffset.UtcNow;
var report = new Dictionary<string, object?>
{
    ["schema"] = "rusty.hostess.windows.qcl050_rfcomm_client.v1",
    ["schema_version"] = 1,
    ["run_id"] = options.RunId,
    ["status"] = status,
    ["started_at_utc"] = started.ToString("O"),
    ["ended_at_utc"] = ended.ToString("O"),
    ["role"] = "windows_rfcomm_client",
    ["service_uuid"] = options.ServiceUuid,
    ["messages_requested"] = options.MessageCount,
    ["messages_completed"] = perMessage.Count,
    ["bytes_written"] = bytesWritten,
    ["bytes_read"] = bytesRead,
    ["selected_device"] = selectedDevice,
    ["measurements"] = new Dictionary<string, object?>
    {
        ["round_trip_ms_p95"] = Percentile(perMessage.Select(row => Convert.ToDouble(row["round_trip_ms"])).ToList(), 0.95),
        ["round_trip_ms_max"] = perMessage.Count == 0 ? null : perMessage.Max(row => Convert.ToDouble(row["round_trip_ms"])),
    },
    ["messages"] = perMessage,
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

static async Task<string> ReadLineAsync(DataReader reader, CancellationToken cancellationToken)
{
    var bytes = new List<byte>();
    while (!cancellationToken.IsCancellationRequested)
    {
        var loaded = await reader.LoadAsync(1).AsTask(cancellationToken);
        if (loaded == 0)
        {
            throw new IOException("RFCOMM stream closed before a response line was received");
        }
        var value = reader.ReadByte();
        if (value == (byte)'\n')
        {
            return Encoding.UTF8.GetString(bytes.ToArray());
        }
        if (value != (byte)'\r')
        {
            bytes.Add(value);
        }
    }
    throw new OperationCanceledException(cancellationToken);
}

static double? Percentile(IReadOnlyList<double> values, double percentile)
{
    if (values.Count == 0)
    {
        return null;
    }
    var sorted = values.OrderBy(value => value).ToArray();
    var index = Math.Clamp((int)Math.Ceiling(percentile * sorted.Length) - 1, 0, sorted.Length - 1);
    return sorted[index];
}

internal sealed class CliOptions
{
    public string RunId { get; init; } = "qcl050-windows-rfcomm";
    public string ServiceUuid { get; init; } = Defaults.ServiceUuid;
    public string PayloadPrefix { get; init; } = "rusty-qcl050-rfcomm";
    public int MessageCount { get; init; } = 3;
    public double TimeoutSeconds { get; init; } = 20.0;
    public string Out { get; init; } = "";

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
            RunId = values.GetValueOrDefault("run-id", "qcl050-windows-rfcomm"),
            ServiceUuid = values.GetValueOrDefault("service-uuid", Defaults.ServiceUuid),
            PayloadPrefix = values.GetValueOrDefault("payload-prefix", "rusty-qcl050-rfcomm"),
            MessageCount = int.TryParse(values.GetValueOrDefault("message-count"), out var messageCount)
                ? Math.Max(1, messageCount)
                : 3,
            TimeoutSeconds = double.TryParse(values.GetValueOrDefault("timeout-seconds"), out var timeoutSeconds)
                ? Math.Max(3.0, timeoutSeconds)
                : 20.0,
            Out = values.GetValueOrDefault("out", ""),
        };
    }
}

internal static class Defaults
{
    public const string ServiceUuid = "7b2a0050-7c4d-4f4c-9b16-515100515100";
}
