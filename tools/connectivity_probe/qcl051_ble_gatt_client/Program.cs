using System.Diagnostics;
using System.Text;
using System.Text.Json;
using Windows.Devices.Bluetooth;
using Windows.Devices.Bluetooth.Advertisement;
using Windows.Devices.Bluetooth.GenericAttributeProfile;
using Windows.Storage.Streams;

var options = CliOptions.Parse(args);
var started = DateTimeOffset.UtcNow;
var eventsLog = new List<Dictionary<string, object?>>();
var issues = new List<Dictionary<string, object?>>();
var errors = new List<string>();
var perMessage = new List<Dictionary<string, object?>>();
var status = "fail";
ulong? selectedBluetoothAddress = null;
string selectedLocalName = "";
bool? selectedIsPaired = null;
bool? selectedCanPair = null;
var bytesWritten = 0;
var bytesRead = 0;

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
    AddEvent("host.winrt.bluetooth_api", "pass", "Windows WinRT Bluetooth API loaded");
    var serviceUuid = Guid.Parse(options.ServiceUuid);
    var controlUuid = Guid.Parse(options.ControlUuid);
    var statusUuid = Guid.Parse(options.StatusUuid);

    using var timeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(options.TimeoutSeconds));
    var discovered = new TaskCompletionSource<(ulong address, string localName)>(TaskCreationOptions.RunContinuationsAsynchronously);
    using var registration = timeoutCts.Token.Register(() => discovered.TrySetCanceled(timeoutCts.Token));
    var watcher = new BluetoothLEAdvertisementWatcher
    {
        ScanningMode = BluetoothLEScanningMode.Active,
    };
    watcher.AdvertisementFilter.Advertisement.ServiceUuids.Add(serviceUuid);
    watcher.Received += (_, eventArgs) =>
    {
        if (!eventArgs.Advertisement.ServiceUuids.Contains(serviceUuid))
        {
            return;
        }
        var localName = eventArgs.Advertisement.LocalName ?? "";
        discovered.TrySetResult((eventArgs.BluetoothAddress, localName));
    };
    watcher.Stopped += (_, eventArgs) =>
    {
        if (eventArgs.Error != BluetoothError.Success)
        {
            AddEvent("ble.scan.stopped", "warn", $"watcher stopped with {eventArgs.Error}");
        }
    };

    AddEvent("ble.scan.start", "pass", "active BLE scan for QCL-051 service UUID started");
    watcher.Start();
    var found = await discovered.Task;
    watcher.Stop();
    selectedBluetoothAddress = found.address;
    selectedLocalName = found.localName;
    AddEvent("ble.scan.found", "pass", "QCL-051 service advertisement found; address redacted");

    using var device = await BluetoothLEDevice.FromBluetoothAddressAsync(found.address);
    if (device is null)
    {
        throw new InvalidOperationException("BluetoothLEDevice.FromBluetoothAddressAsync returned null");
    }
    selectedIsPaired = device.DeviceInformation?.Pairing?.IsPaired;
    selectedCanPair = device.DeviceInformation?.Pairing?.CanPair;
    AddEvent("ble.device.open", "pass", "BLE device opened from advertisement; address redacted");
    AddEvent("ble.device.pairing_state", "pass", $"is_paired={selectedIsPaired}; can_pair={selectedCanPair}");

    using var service = await WaitForGattServiceAsync(
        device,
        serviceUuid,
        timeoutCts.Token,
        AddEvent,
        AddIssue);
    AddEvent("gatt.service.discovery", "pass", "QCL-051 GATT service discovered");

    var control = await WaitForGattCharacteristicAsync(
        service,
        controlUuid,
        "control",
        "hostess.issue.connectivity_probe.ble_gatt_control_characteristic_missing",
        timeoutCts.Token,
        AddEvent,
        AddIssue);

    var statusCharacteristic = await WaitForGattCharacteristicAsync(
        service,
        statusUuid,
        "status",
        "hostess.issue.connectivity_probe.ble_gatt_status_characteristic_missing",
        timeoutCts.Token,
        AddEvent,
        AddIssue);
    AddEvent("gatt.characteristics.discovery", "pass", "control and status characteristics discovered");

    for (var index = 1; index <= options.MessageCount; index += 1)
    {
        var payloadText = $"{options.PayloadPrefix};runId={options.RunId};sequence={index}";
        var payload = Encoding.UTF8.GetBytes(payloadText);
        var stopwatch = Stopwatch.StartNew();
        using var writer = new DataWriter();
        writer.WriteBytes(payload);
        var writeResult = await control.WriteValueWithResultAsync(writer.DetachBuffer(), GattWriteOption.WriteWithResponse);
        if (writeResult.Status != GattCommunicationStatus.Success)
        {
            AddIssue("hostess.issue.connectivity_probe.ble_gatt_control_write_failed", "error", $"GATT write failed: {writeResult.Status}");
            throw new InvalidOperationException($"GATT write failed: {writeResult.Status}");
        }
        bytesWritten += payload.Length;

        var readResult = await statusCharacteristic.ReadValueAsync(BluetoothCacheMode.Uncached);
        if (readResult.Status != GattCommunicationStatus.Success)
        {
            AddIssue("hostess.issue.connectivity_probe.ble_gatt_status_read_failed", "error", $"GATT status read failed: {readResult.Status}");
            throw new InvalidOperationException($"GATT status read failed: {readResult.Status}");
        }
        var statusBytes = BufferToBytes(readResult.Value);
        stopwatch.Stop();
        bytesRead += statusBytes.Length;
        var statusText = Encoding.UTF8.GetString(statusBytes);
        perMessage.Add(new Dictionary<string, object?>
        {
            ["sequence"] = index,
            ["payload_bytes"] = payload.Length,
            ["status_bytes"] = statusBytes.Length,
            ["round_trip_ms"] = stopwatch.Elapsed.TotalMilliseconds,
            ["status_preview"] = statusText.Length > 160 ? statusText[..160] : statusText,
        });
        AddEvent("gatt.payload_exchange", "pass", $"message {index} write/read completed");
    }

    status = "pass";
}
catch (OperationCanceledException)
{
    errors.Add("BLE advertisement scan timed out");
    AddIssue("hostess.issue.connectivity_probe.ble_gatt_advertisement_timeout", "error", "Windows helper did not observe the Quest GATT advertisement before timeout");
    AddEvent("ble.scan.timeout", "fail", "advertisement timeout");
}
catch (Exception ex)
{
    errors.Add(ex.Message);
    AddEvent("host.helper.failure", "fail", ex.Message);
}

var ended = DateTimeOffset.UtcNow;
var report = new Dictionary<string, object?>
{
    ["schema"] = "rusty.hostess.windows.qcl051_ble_gatt_client.v1",
    ["schema_version"] = 1,
    ["run_id"] = options.RunId,
    ["status"] = status,
    ["started_at_utc"] = started.ToString("O"),
    ["ended_at_utc"] = ended.ToString("O"),
    ["role"] = "windows_ble_gatt_client",
    ["service_uuid"] = options.ServiceUuid,
    ["control_characteristic_uuid"] = options.ControlUuid,
    ["status_characteristic_uuid"] = options.StatusUuid,
    ["messages_requested"] = options.MessageCount,
    ["messages_completed"] = perMessage.Count,
    ["bytes_written"] = bytesWritten,
    ["bytes_read"] = bytesRead,
    ["selected_device"] = new Dictionary<string, object?>
    {
        ["address_redacted"] = selectedBluetoothAddress is not null,
        ["local_name"] = selectedLocalName,
        ["is_paired"] = selectedIsPaired,
        ["can_pair"] = selectedCanPair,
    },
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

return status == "pass" ? 0 : 2;

static byte[] BufferToBytes(IBuffer buffer)
{
    using var reader = DataReader.FromBuffer(buffer);
    var bytes = new byte[reader.UnconsumedBufferLength];
    reader.ReadBytes(bytes);
    return bytes;
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

static async Task<GattDeviceService> WaitForGattServiceAsync(
    BluetoothLEDevice device,
    Guid serviceUuid,
    CancellationToken cancellationToken,
    Action<string, string, string> addEvent,
    Action<string, string, string> addIssue)
{
    var attempts = 0;
    GattCommunicationStatus lastStatus = GattCommunicationStatus.Unreachable;
    while (!cancellationToken.IsCancellationRequested)
    {
        attempts += 1;
        var services = await device.GetGattServicesForUuidAsync(serviceUuid, BluetoothCacheMode.Uncached);
        lastStatus = services.Status;
        if (services.Status == GattCommunicationStatus.Success && services.Services.Count > 0)
        {
            if (attempts > 1)
            {
                addEvent("gatt.service.discovery.retry", "pass", $"service visible after {attempts} attempts");
            }
            return services.Services[0];
        }
        addEvent(
            "gatt.service.discovery.retry",
            "warn",
            $"attempt={attempts}; status={services.Status}; service_count={services.Services.Count}");
        await Task.Delay(TimeSpan.FromMilliseconds(500), cancellationToken);
    }
    addIssue(
        "hostess.issue.connectivity_probe.ble_gatt_service_not_found",
        "error",
        $"GATT service discovery failed after {attempts} attempts; last_status={lastStatus}");
    throw new TimeoutException($"GATT service discovery failed after {attempts} attempts; last_status={lastStatus}");
}

static async Task<GattCharacteristic> WaitForGattCharacteristicAsync(
    GattDeviceService service,
    Guid characteristicUuid,
    string label,
    string issueCode,
    CancellationToken cancellationToken,
    Action<string, string, string> addEvent,
    Action<string, string, string> addIssue)
{
    var attempts = 0;
    GattCommunicationStatus lastStatus = GattCommunicationStatus.Unreachable;
    while (!cancellationToken.IsCancellationRequested)
    {
        attempts += 1;
        var characteristics = await service.GetCharacteristicsForUuidAsync(characteristicUuid, BluetoothCacheMode.Uncached);
        lastStatus = characteristics.Status;
        if (characteristics.Status == GattCommunicationStatus.Success && characteristics.Characteristics.Count > 0)
        {
            if (attempts > 1)
            {
                addEvent("gatt.characteristic.discovery.retry", "pass", $"{label} characteristic visible after {attempts} attempts");
            }
            return characteristics.Characteristics[0];
        }
        addEvent(
            "gatt.characteristic.discovery.retry",
            "warn",
            $"label={label}; attempt={attempts}; status={characteristics.Status}; characteristic_count={characteristics.Characteristics.Count}");
        await Task.Delay(TimeSpan.FromMilliseconds(500), cancellationToken);
    }
    addIssue(
        issueCode,
        "error",
        $"{label} characteristic lookup failed after {attempts} attempts; last_status={lastStatus}");
    throw new TimeoutException($"{label} characteristic lookup failed after {attempts} attempts; last_status={lastStatus}");
}

internal sealed class CliOptions
{
    public string RunId { get; init; } = "qcl051-windows-ble-gatt";
    public string ServiceUuid { get; init; } = Defaults.ServiceUuid;
    public string ControlUuid { get; init; } = Defaults.ControlUuid;
    public string StatusUuid { get; init; } = Defaults.StatusUuid;
    public string PayloadPrefix { get; init; } = "rusty-qcl051-ble-gatt";
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
            RunId = values.GetValueOrDefault("run-id", "qcl051-windows-ble-gatt"),
            ServiceUuid = values.GetValueOrDefault("service-uuid", Defaults.ServiceUuid),
            ControlUuid = values.GetValueOrDefault("control-uuid", Defaults.ControlUuid),
            StatusUuid = values.GetValueOrDefault("status-uuid", Defaults.StatusUuid),
            PayloadPrefix = values.GetValueOrDefault("payload-prefix", "rusty-qcl051-ble-gatt"),
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
    public const string ServiceUuid = "7b2a0001-7c4d-4f4c-9b16-515100515100";
    public const string ControlUuid = "7b2a0002-7c4d-4f4c-9b16-515100515100";
    public const string StatusUuid = "7b2a0003-7c4d-4f4c-9b16-515100515100";
}
