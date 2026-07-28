using System.Text.Json;
using System.Text.Json.Serialization;
using System.Runtime.InteropServices;
using Windows.Networking.Connectivity;
using Windows.Networking.NetworkOperators;

namespace RustyHostess.WindowsHotspot;

internal sealed class WindowsHotspotBackend : IHotspotBackend
{
    private static NetworkOperatorTetheringManager Manager()
    {
        var profile = NetworkInformation.GetInternetConnectionProfile()
            ?? throw new PlatformNotSupportedException("No current Internet connection profile");
        return NetworkOperatorTetheringManager.CreateFromConnectionProfile(profile);
    }
    public async Task<Snapshot> ReadAsync(CancellationToken cancellationToken)
    {
        var profile = NetworkInformation.GetInternetConnectionProfile()
            ?? throw new PlatformNotSupportedException("No current Internet connection profile");
        var capability = NetworkOperatorTetheringManager.GetTetheringCapabilityFromConnectionProfile(profile);
        var manager = NetworkOperatorTetheringManager.CreateFromConnectionProfile(profile);
        var config = manager.GetCurrentAccessPointConfiguration();
        await Task.Yield();
        cancellationToken.ThrowIfCancellationRequested();
        return new(capability == TetheringCapability.Enabled, capability.ToString(),
            manager.TetheringOperationalState.ToString(), manager.ClientCount, manager.MaxClientCount,
            config.Band.ToString(), profile.GetNetworkConnectivityLevel().ToString());
    }
    public async Task<BackendResult> StartAsync(CancellationToken cancellationToken)
    {
        var result = await Manager().StartTetheringAsync().AsTask(cancellationToken);
        return new(result.Status == TetheringOperationStatus.Success, result.Status.ToString());
    }
    public async Task<BackendResult> StopAsync(CancellationToken cancellationToken)
    {
        var result = await Manager().StopTetheringAsync().AsTask(cancellationToken);
        return new(result.Status == TetheringOperationStatus.Success, result.Status.ToString());
    }
}

internal sealed class FileStateStore : IStateStore
{
    private readonly string path;
    internal FileStateStore(string? overridePath = null)
    {
        path = overridePath ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "RustyHostess", "WindowsHotspotProvider", "private-state.json");
    }
    public StateRecord Load()
    {
        if (!File.Exists(path)) return new();
        var json = File.ReadAllText(path);
        using var document = JsonDocument.Parse(json);
        if (document.RootElement.ValueKind != JsonValueKind.Object) throw new InvalidDataException();
        var schema = document.RootElement.GetProperty("schema").GetString();
        var allowed = schema == "rusty.hostess.windows_hotspot.private_state.v1"
            ? new HashSet<string>(["schema", "boot_id", "ownership_generation", "request_ids", "operation_ids"], StringComparer.Ordinal)
            : new HashSet<string>(["schema", "boot_id", "ownership_phase", "ownership_generation", "transition_origin", "request_ids", "operation_ids"], StringComparer.Ordinal);
        var seen = new HashSet<string>(StringComparer.Ordinal);
        if (document.RootElement.EnumerateObject().Any(property => !allowed.Contains(property.Name) || !seen.Add(property.Name)))
            throw new InvalidDataException("unknown or duplicate private state field");
        StateRecord state;
        if (schema == "rusty.hostess.windows_hotspot.private_state.v1")
        {
            var legacy = JsonSerializer.Deserialize<LegacyStateRecord>(json) ?? throw new InvalidDataException();
            state = new StateRecord {
                BootId = legacy.BootId,
                OwnershipPhase = legacy.OwnershipGeneration is null ? "none" : "active",
                OwnershipGeneration = legacy.OwnershipGeneration,
                RequestIds = legacy.RequestIds,
                OperationIds = legacy.OperationIds
            };
        }
        else
        {
            state = JsonSerializer.Deserialize<StateRecord>(json) ?? throw new InvalidDataException();
        }
        state.Validate();
        return state;
    }
    public void Save(StateRecord state)
    {
        state.Validate();
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(state));
        File.Move(temp, path, true);
    }

    private sealed record LegacyStateRecord
    {
        [JsonPropertyName("boot_id")] public string BootId { get; init; } = "";
        [JsonPropertyName("ownership_generation")] public string? OwnershipGeneration { get; init; }
        [JsonPropertyName("request_ids")] public List<string> RequestIds { get; init; } = [];
        [JsonPropertyName("operation_ids")] public List<string> OperationIds { get; init; } = [];
    }
}

// Artifact validation must exercise the real process and WinRT read boundary
// without reading, reconciling, or writing the installed provider's ownership
// journal.
internal sealed class VolatileStateStore : IStateStore
{
    private StateRecord state = new();

    public StateRecord Load() => state;

    public void Save(StateRecord next) => state = next;
}

internal sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
    public string BootId => WindowsBootIdentifier.Read();
}

internal static class WindowsBootIdentifier
{
    private const int SystemBootEnvironmentInformation = 90;

    [StructLayout(LayoutKind.Sequential)]
    private struct BootEnvironmentInformation
    {
        internal Guid BootIdentifier;
        internal int FirmwareType;
        internal ulong BootFlags;
    }

    [DllImport("ntdll.dll")]
    private static extern int NtQuerySystemInformation(
        int systemInformationClass,
        out BootEnvironmentInformation systemInformation,
        int systemInformationLength,
        out int returnLength);

    internal static string Read()
    {
        if (!OperatingSystem.IsWindows()) throw new PlatformNotSupportedException();
        var status = NtQuerySystemInformation(
            SystemBootEnvironmentInformation,
            out var information,
            Marshal.SizeOf<BootEnvironmentInformation>(),
            out var returned);
        if (status != 0 || returned < Marshal.SizeOf<Guid>() || information.BootIdentifier == Guid.Empty)
            throw new InvalidOperationException($"Boot identifier unavailable (NTSTATUS=0x{status:X8}).");
        return information.BootIdentifier.ToString("D");
    }
}
