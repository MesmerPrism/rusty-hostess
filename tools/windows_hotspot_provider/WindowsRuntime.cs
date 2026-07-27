using System.Text.Json;
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
        var state = JsonSerializer.Deserialize<StateRecord>(json) ?? throw new InvalidDataException();
        if (state.Schema != "rusty.hostess.windows_hotspot.private_state.v1" ||
            state.RequestIds is null || state.OperationIds is null) throw new InvalidDataException();
        return state;
    }
    public void Save(StateRecord state)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(state));
        File.Move(temp, path, true);
    }
}

internal sealed class SystemClock : IClock
{
    public DateTimeOffset UtcNow => DateTimeOffset.UtcNow;
    public string BootId
    {
        get
        {
            var boot = DateTimeOffset.UtcNow - TimeSpan.FromMilliseconds(Environment.TickCount64);
            return (boot.ToUnixTimeSeconds() / 60).ToString(System.Globalization.CultureInfo.InvariantCulture);
        }
    }
}
