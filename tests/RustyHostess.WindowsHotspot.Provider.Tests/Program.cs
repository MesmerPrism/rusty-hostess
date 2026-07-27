using System.Text.Json;
using RustyHostess.WindowsHotspot;

var tests = new (string, Func<Task>)[]
{
    ("strict JSON and private fields", StrictJson),
    ("expiry and replay", ExpiryReplay),
    ("external already-on", ExternalOn),
    ("start and readback", StartReadback),
    ("ensure and wrong-generation stop", EnsureStop),
    ("owned ensure restarts from off", EnsureRestart),
    ("operation failures and timeout", FailuresTimeout),
    ("concurrent ownership", ConcurrentOwnership),
    ("prior-boot recovery and damaged state", RestartDamaged),
    ("receipt redaction", Redaction),
    ("exit mapping and unavailable", ExitMapping),
    ("abandoned mutex is acquired", AbandonedMutex),
    ("durable transition reconciliation", DurableTransitions),
    ("private state migration and validation", StateMigration),
    ("boot identity ignores clock correction", ClockCorrection),
    ("provider capability descriptor parity", CapabilityDescriptorParity),
    ("provider discovery version parity", DiscoveryVersionParity),
    ("description route is inert and exact", DescriptionRoute),
};
var failed = 0;
foreach (var (name, test) in tests)
{
    try { await test(); Console.WriteLine($"PASS {name}"); }
    catch (Exception ex) { failed++; Console.Error.WriteLine($"FAIL {name}: {ex.Message}"); }
}
return failed == 0 ? 0 : 1;

static Request Request(FakeClock clock, string action, string? generation = null, string? requestId = null, string? operationId = null) =>
    new(requestId ?? Guid.NewGuid().ToString("N"), operationId ?? Guid.NewGuid().ToString("N"), action, clock.UtcNow.AddMinutes(1), 1000, generation);
static Snapshot Off() => new(true, "Enabled", "Off", 0, 8, "FiveGigahertz", "InternetAccess");
static Snapshot On() => Off() with { OperationalState = "On", ClientCount = 1 };
static StateRecord Active(FakeClock clock, string generation) =>
    new() { BootId = clock.BootId, OwnershipPhase = "active", OwnershipGeneration = generation };
static void Equal<T>(T expected, T actual) { if (!EqualityComparer<T>.Default.Equals(expected, actual)) throw new Exception($"expected {expected}, got {actual}"); }
static void True(bool value, string message = "assertion failed") { if (!value) throw new Exception(message); }

static Task StrictJson()
{
    var clock = new FakeClock();
    var valid = $$"""{"schema":"{{Protocol.RequestSchema}}","request_id":"r","operation_id":"o","action":"status","expires_at_utc":"{{clock.UtcNow.AddMinutes(1):O}}","timeout_ms":1000}""";
    Equal("status", Protocol.ParseRequest(valid, clock.UtcNow).Action);
    foreach (var bad in new[] { valid[..^1] + ",\"ssid\":\"secret\"}", valid[..^1] + ",\"private\":true}", "[]", valid.Replace("\"status\"", "\"Status\"") })
    {
        try { Protocol.ParseRequest(bad, clock.UtcNow); throw new Exception("accepted invalid JSON"); } catch (RejectedException) { }
    }
    return Task.CompletedTask;
}

static async Task ExpiryReplay()
{
    var clock = new FakeClock();
    var expired = $$"""{"schema":"{{Protocol.RequestSchema}}","request_id":"r","operation_id":"o","action":"status","expires_at_utc":"{{clock.UtcNow.AddSeconds(-1):O}}","timeout_ms":1000}""";
    try { Protocol.ParseRequest(expired, clock.UtcNow); throw new Exception("accepted expired"); } catch (RejectedException) { }
    var store = new MemoryStore(); var provider = new Provider(new FakeBackend(Off()), store, clock);
    var request = Request(clock, "status", requestId: "same", operationId: "same-op");
    Equal(Outcome.Verified, (await provider.ExecuteAsync(request, default)).Outcome);
    Equal(Outcome.Rejected, (await provider.ExecuteAsync(request, default)).Outcome);
}

static async Task ExternalOn()
{
    var clock = new FakeClock(); var result = await new Provider(new FakeBackend(On()), new MemoryStore(), clock).ExecuteAsync(Request(clock, "start"), default);
    Equal(Outcome.Rejected, result.Outcome); Equal("ownership.external_hotspot_on", result.Receipt.Reason);
}

static async Task StartReadback()
{
    var clock = new FakeClock(); var backend = new FakeBackend(Off()) { AfterStart = On() };
    var result = await new Provider(backend, new MemoryStore(), clock).ExecuteAsync(Request(clock, "start"), default);
    Equal(Outcome.Verified, result.Outcome); True(result.Receipt.OwnershipGeneration is not null); Equal("On", result.Receipt.OperationalState);
    var failed = await new Provider(new FakeBackend(Off()) { AfterStart = Off() }, new MemoryStore(), clock).ExecuteAsync(Request(clock, "start"), default);
    Equal(Outcome.Failed, failed.Outcome);
}

static async Task EnsureStop()
{
    var clock = new FakeClock(); var store = new MemoryStore(); var backend = new FakeBackend(Off()) { AfterStart = On(), AfterStop = Off() };
    var provider = new Provider(backend, store, clock);
    var started = await provider.ExecuteAsync(Request(clock, "start"), default);
    var generation = started.Receipt.OwnershipGeneration!;
    Equal(Outcome.Verified, (await provider.ExecuteAsync(Request(clock, "ensure", generation), default)).Outcome);
    var wrong = await provider.ExecuteAsync(Request(clock, "stop", "wrong"), default);
    Equal(Outcome.Rejected, wrong.Outcome); Equal<string?>(null, wrong.Receipt.OwnershipGeneration);
    Equal(Outcome.Verified, (await provider.ExecuteAsync(Request(clock, "stop", generation), default)).Outcome);
}

static async Task EnsureRestart()
{
    var clock = new FakeClock();
    var store = new MemoryStore { State = Active(clock, "owned") };
    var backend = new FakeBackend(Off()) { AfterStart = On() };
    var restarted = await new Provider(backend, store, clock).ExecuteAsync(Request(clock, "ensure", "owned"), default);
    Equal(Outcome.Verified, restarted.Outcome);
    Equal("ensure.restart_readback_verified", restarted.Receipt.Reason);
    Equal("owned", restarted.Receipt.OwnershipGeneration);
    Equal("owned", store.State.OwnershipGeneration);

    var failedStore = new MemoryStore { State = Active(clock, "owned") };
    var apiFailure = await new Provider(new FakeBackend(Off()) { StartSuccess = false }, failedStore, clock)
        .ExecuteAsync(Request(clock, "ensure", "owned"), default);
    Equal(Outcome.Failed, apiFailure.Outcome);
    Equal("owned", failedStore.State.OwnershipGeneration);

    var readbackStore = new MemoryStore { State = Active(clock, "owned") };
    var readbackFailure = await new Provider(new FakeBackend(Off()) { AfterStart = Off() }, readbackStore, clock)
        .ExecuteAsync(Request(clock, "ensure", "owned"), default);
    Equal(Outcome.Failed, readbackFailure.Outcome);
    Equal("owned", readbackStore.State.OwnershipGeneration);
}

static async Task FailuresTimeout()
{
    var clock = new FakeClock();
    Equal(Outcome.Failed, (await new Provider(new FakeBackend(Off()) { StartSuccess = false }, new MemoryStore(), clock).ExecuteAsync(Request(clock, "start"), default)).Outcome);
    var owned = new MemoryStore { State = Active(clock, "g") };
    Equal(Outcome.Failed, (await new Provider(new FakeBackend(On()) { StopSuccess = false }, owned, clock).ExecuteAsync(Request(clock, "stop", "g"), default)).Outcome);
    using var cancelled = new CancellationTokenSource(); cancelled.Cancel();
    Equal(Outcome.Failed, (await new Provider(new FakeBackend(Off()) { Delay = true }, new MemoryStore(), clock).ExecuteAsync(Request(clock, "status"), cancelled.Token)).Outcome);
}

static async Task ConcurrentOwnership()
{
    var clock = new FakeClock(); var store = new MemoryStore { State = Active(clock, "owner-a") };
    var result = await new Provider(new FakeBackend(On()), store, clock).ExecuteAsync(Request(clock, "ensure", "owner-b"), default);
    Equal(Outcome.Rejected, result.Outcome); Equal("owner-a", store.State.OwnershipGeneration);
}

static async Task RestartDamaged()
{
    var clock = new FakeClock();
    var stale = new StateRecord {
        BootId = "previous", OwnershipPhase = "active", OwnershipGeneration = "old",
        RequestIds = ["stale-request"], OperationIds = ["stale-operation"]
    };
    var statusStore = new MemoryStore { State = stale };
    var status = await new Provider(new FakeBackend(Off()), statusStore, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal(Outcome.Failed, status.Outcome); Equal("state.restart_detected", status.Receipt.Reason);
    Equal("Off", status.Receipt.OperationalState); Equal<string?>(null, status.Receipt.OwnershipGeneration);

    foreach (var action in new[] { "ensure", "stop" })
    {
        var oldGeneration = new MemoryStore { State = stale };
        var rejected = await new Provider(new FakeBackend(Off()), oldGeneration, clock)
            .ExecuteAsync(Request(clock, action, "old"), default);
        Equal(Outcome.Rejected, rejected.Outcome);
        Equal("ownership.prior_boot_generation", rejected.Receipt.Reason);
        Equal("old", oldGeneration.State.OwnershipGeneration);
    }

    var recoveryStore = new MemoryStore { State = stale };
    var recovered = await new Provider(new FakeBackend(Off()) { AfterStart = On() }, recoveryStore, clock)
        .ExecuteAsync(Request(clock, "start", requestId: "new-request", operationId: "new-operation"), default);
    Equal(Outcome.Verified, recovered.Outcome); Equal("start.restart_recovery_verified", recovered.Receipt.Reason);
    True(recoveryStore.State.OwnershipGeneration is not null && recoveryStore.State.OwnershipGeneration != "old");
    Equal(clock.BootId, recoveryStore.State.BootId);
    True(recoveryStore.State.RequestIds.SequenceEqual(["new-request"]));
    True(recoveryStore.State.OperationIds.SequenceEqual(["new-operation"]));

    var failedRecoveryStore = new MemoryStore { State = stale };
    var failedRecoveryRequest = Request(
        clock,
        "start",
        requestId: "failed-recovery-request",
        operationId: "failed-recovery-operation");
    var failedRecovery = await new Provider(
        new FakeBackend(Off()) { StartSuccess = false },
        failedRecoveryStore,
        clock).ExecuteAsync(failedRecoveryRequest, default);
    Equal(Outcome.Failed, failedRecovery.Outcome);
    Equal(clock.BootId, failedRecoveryStore.State.BootId);
    Equal("starting", failedRecoveryStore.State.OwnershipPhase);
    True(failedRecoveryStore.State.OwnershipGeneration is not null);
    Equal(Outcome.Rejected, (await new Provider(new FakeBackend(Off()), failedRecoveryStore, clock)
        .ExecuteAsync(failedRecoveryRequest, default)).Outcome);

    var externalStore = new MemoryStore { State = stale };
    var external = await new Provider(new FakeBackend(On()), externalStore, clock)
        .ExecuteAsync(Request(clock, "start"), default);
    Equal(Outcome.Rejected, external.Outcome); Equal("ownership.external_hotspot_on", external.Receipt.Reason);
    Equal("old", externalStore.State.OwnershipGeneration);

    var damaged = new MemoryStore { ThrowOnLoad = true };
    Equal("state.damaged", (await new Provider(new FakeBackend(Off()), damaged, clock).ExecuteAsync(Request(clock, "status"), default)).Receipt.Reason);
}

static async Task Redaction()
{
    var clock = new FakeClock();
    var receipt = (await new Provider(new FakeBackend(On()), new MemoryStore(), clock).ExecuteAsync(Request(clock, "status"), default)).Receipt;
    var json = JsonSerializer.Serialize(receipt).ToLowerInvariant();
    foreach (var forbidden in new[] { "ssid", "passphrase", "credential", "profile", "\"path\"", "ip_address" }) True(!json.Contains(forbidden), forbidden);
}

static async Task ExitMapping()
{
    Equal(0, (int)Outcome.Verified); Equal(1, (int)Outcome.Failed);
    Equal(2, (int)Outcome.Rejected); Equal(3, (int)Outcome.Unavailable);
    var clock = new FakeClock();
    var unavailable = Off() with { CapabilityAvailable = false, Capability = "DisabledBySystemCapability" };
    Equal(Outcome.Unavailable,
        (await new Provider(new FakeBackend(unavailable), new MemoryStore(), clock)
            .ExecuteAsync(Request(clock, "status"), default)).Outcome);
}

static Task AbandonedMutex()
{
    var name = $"Local\\RustyHostess.WindowsHotspot.Provider.Test.{Guid.NewGuid():N}";
    using var ready = new ManualResetEventSlim();
    var thread = new Thread(() =>
    {
        using var abandoned = new Mutex(false, name);
        abandoned.WaitOne();
        ready.Set();
    });
    thread.Start();
    True(ready.Wait(TimeSpan.FromSeconds(2)), "abandoning thread did not acquire mutex");
    thread.Join();
    using var mutex = new Mutex(false, name);
    True(MutexGate.TryAcquire(mutex, TimeSpan.FromSeconds(2)), "abandoned mutex was not treated as acquired");
    mutex.ReleaseMutex();
    return Task.CompletedTask;
}

static async Task DurableTransitions()
{
    var clock = new FakeClock();
    var startStore = new MemoryStore { FailOnSaveCall = 3 };
    var startBackend = new FakeBackend(Off()) { AfterStart = On() };
    var startRequest = Request(clock, "start");
    var partialStart = await new Provider(startBackend, startStore, clock).ExecuteAsync(startRequest, default);
    Equal(Outcome.Failed, partialStart.Outcome); Equal("state.active_commit_failed", partialStart.Receipt.Reason);
    Equal("starting", startStore.State.OwnershipPhase);
    Equal(Outcome.Rejected, (await new Provider(startBackend, startStore, clock).ExecuteAsync(startRequest, default)).Outcome);
    var generation = startStore.State.OwnershipGeneration;
    var reconciledStart = await new Provider(startBackend, startStore, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal(Outcome.Verified, reconciledStart.Outcome); Equal("active", startStore.State.OwnershipPhase);
    Equal(generation, startStore.State.OwnershipGeneration);

    var stopStore = new MemoryStore { State = Active(clock, "stop-owner"), FailOnSaveCall = 3 };
    var stopBackend = new FakeBackend(On()) { AfterStop = Off() };
    var stopRequest = Request(clock, "stop", "stop-owner");
    var partialStop = await new Provider(stopBackend, stopStore, clock).ExecuteAsync(stopRequest, default);
    Equal(Outcome.Failed, partialStop.Outcome); Equal("state.none_commit_failed", partialStop.Receipt.Reason);
    Equal("stopping", stopStore.State.OwnershipPhase);
    Equal(Outcome.Rejected, (await new Provider(stopBackend, stopStore, clock).ExecuteAsync(stopRequest, default)).Outcome);
    var blockedEnsure = await new Provider(new FakeBackend(On()), stopStore, clock)
        .ExecuteAsync(Request(clock, "ensure", "stop-owner"), default);
    Equal(Outcome.Rejected, blockedEnsure.Outcome); Equal("ownership.stop_in_progress", blockedEnsure.Receipt.Reason);
    var reconciledStop = await new Provider(stopBackend, stopStore, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal(Outcome.Verified, reconciledStop.Outcome); Equal("none", stopStore.State.OwnershipPhase);
    Equal<string?>(null, stopStore.State.OwnershipGeneration);

    var crashStart = new MemoryStore {
        State = new() { BootId = clock.BootId, OwnershipPhase = "starting", OwnershipGeneration = "new", TransitionOrigin = "none" }
    };
    await new Provider(new FakeBackend(Off()), crashStart, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal("none", crashStart.State.OwnershipPhase);
    var crashEnsure = new MemoryStore {
        State = new() { BootId = clock.BootId, OwnershipPhase = "starting", OwnershipGeneration = "owned", TransitionOrigin = "active" }
    };
    await new Provider(new FakeBackend(Off()), crashEnsure, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal("active", crashEnsure.State.OwnershipPhase); Equal("owned", crashEnsure.State.OwnershipGeneration);
}

static Task StateMigration()
{
    var root = Path.Combine(Path.GetTempPath(), $"hostess-hotspot-state-{Guid.NewGuid():N}");
    Directory.CreateDirectory(root);
    try
    {
        var path = Path.Combine(root, "state.json");
        File.WriteAllText(path, """{"schema":"rusty.hostess.windows_hotspot.private_state.v1","boot_id":"boot","ownership_generation":"legacy","request_ids":["r"],"operation_ids":["o"]}""");
        var migrated = new FileStateStore(path).Load();
        Equal("active", migrated.OwnershipPhase); Equal("legacy", migrated.OwnershipGeneration);
        File.WriteAllText(path, """{"schema":"rusty.hostess.windows_hotspot.private_state.v2","boot_id":"boot","ownership_phase":"stopping","ownership_generation":null,"transition_origin":"active","request_ids":[],"operation_ids":[]}""");
        try { new FileStateStore(path).Load(); throw new Exception("accepted invalid phase state"); }
        catch (InvalidDataException) { }
    }
    finally { Directory.Delete(root, true); }
    return Task.CompletedTask;
}

static async Task ClockCorrection()
{
    var clock = new FakeClock();
    var store = new MemoryStore { State = Active(clock, "g") };
    clock.UtcNow = clock.UtcNow.AddHours(-3);
    var status = await new Provider(new FakeBackend(On()), store, clock).ExecuteAsync(Request(clock, "status"), default);
    Equal(Outcome.Verified, status.Outcome); Equal("status.read", status.Receipt.Reason);
}

static Task CapabilityDescriptorParity()
{
    var observed = new DateTimeOffset(
        2026,
        7,
        27,
        12,
        0,
        0,
        TimeSpan.Zero);
    var descriptor = CapabilityDiscovery.Create(observed, "0.1.0");
    Equal(CapabilityDiscovery.Schema, descriptor.Schema);
    Equal(CapabilityDiscovery.ProviderId, descriptor.Provider.Id);
    Equal("0.1.0", descriptor.Provider.Version);
    Equal("windows-host-process", descriptor.Placement);
    Equal("descriptor-available", descriptor.Availability.Status);
    Equal(observed.ToString("O"), descriptor.Availability.ObservedAtUtc);
    Equal(
        observed.AddSeconds(CapabilityDiscovery.MaximumAgeSeconds).ToString("O"),
        descriptor.Availability.ExpiresAtUtc);
    Equal(
        CapabilityDiscovery.MaximumAgeSeconds,
        descriptor.Availability.MaximumAgeSeconds);
    Equal("none", descriptor.DescriptionAuthentication);
    True(!descriptor.AuthorizesExecution);
    True(!descriptor.TargetSpecific);
    Equal(1, descriptor.Capabilities.Count);

    var capability = descriptor.Capabilities.Single();
    Equal(CapabilityDiscovery.CapabilityId, capability.Id);
    True(capability.ContractVersions.SequenceEqual([Protocol.RequestSchema]));
    Equal(CapabilityDiscovery.EffectOwner, capability.EffectOwner);
    Equal(Protocol.ReceiptSchema, capability.ReceiptSchema);
    True(
        capability.Actions.Select(action => action.Id).ToHashSet(
            StringComparer.Ordinal).SetEquals(Protocol.Actions),
        "discovery actions do not match Protocol.Actions");
    Equal(
        Protocol.Actions.Count,
        capability.Actions.Count);

    var expected = new Dictionary<string, (string Kind, string[] Authentication)>(
        StringComparer.Ordinal)
    {
        ["status"] = (
            "observe",
            ["process-access-control", "caller-authority-external"]),
        ["start"] = (
            "effect",
            [
                "process-access-control",
                "caller-authority-external",
                "effect-owner-profile"
            ]),
        ["ensure"] = (
            "effect",
            [
                "process-access-control",
                "caller-authority-external",
                "effect-owner-profile"
            ]),
        ["stop"] = (
            "effect",
            [
                "process-access-control",
                "caller-authority-external",
                "effect-owner-profile",
                "ownership-generation"
            ])
    };
    foreach (var action in capability.Actions)
    {
        True(expected.TryGetValue(action.Id, out var metadata));
        Equal(metadata.Kind, action.Kind);
        True(
            metadata.Authentication.SequenceEqual(
                action.AuthenticationRequirements),
            $"authentication requirements differ for {action.Id}");
    }
    True(
        !capability.Actions.Single(action => action.Id == "ensure")
            .AuthenticationRequirements.Contains(
                "ownership-generation",
                StringComparer.Ordinal),
        "ensure incorrectly advertises its optional generation as required");
    True(
        capability.Actions.Single(action => action.Id == "stop")
            .AuthenticationRequirements.Contains(
                "ownership-generation",
                StringComparer.Ordinal),
        "stop did not advertise its required ownership generation");
    return Task.CompletedTask;
}

static Task DescriptionRoute()
{
    var observed = new DateTimeOffset(
        2026,
        7,
        27,
        12,
        0,
        0,
        TimeSpan.Zero);
    using var output = new StringWriter();
    var result = ProviderCli.Run(
        ["--describe-json"],
        ThrowFactory<TextReader>,
        output,
        ThrowFactory<IClock>,
        ThrowFactory<IHotspotBackend>,
        ThrowFactory<IStateStore>,
        ThrowFactory<IStateStore>,
        () => observed,
        () => "0.1.0");
    Equal(0, result);
    using var document = JsonDocument.Parse(output.ToString());
    Equal(
        CapabilityDiscovery.Schema,
        document.RootElement.GetProperty("schema").GetString());

    var rejectedArguments = new[]
    {
        Array.Empty<string>(),
        new[] { "--Describe-Json" },
        new[] { "describe-json" },
        new[] { "--describe-json", "extra" },
        new[]
        {
            "integration",
            "windows-hotspot",
            "--json",
            "--describe-json"
        }
    };
    foreach (var rejected in rejectedArguments)
    {
        using var rejectedOutput = new StringWriter();
        Equal(
            2,
            ProviderCli.Run(
                rejected,
                ThrowFactory<TextReader>,
                rejectedOutput,
                ThrowFactory<IClock>,
                ThrowFactory<IHotspotBackend>,
                ThrowFactory<IStateStore>,
                ThrowFactory<IStateStore>,
                () => throw new Exception(
                    "invalid arguments consulted the discovery clock"),
                () => throw new Exception(
                    "invalid arguments consulted the provider version")));
        Equal("", rejectedOutput.ToString());
    }
    return Task.CompletedTask;
}

static Task DiscoveryVersionParity()
{
    Equal(
        "0.1.0-rc.1",
        ProviderAssemblyVersion.ParseInformationalVersion(
            "0.1.0-rc.1+source.0123456789abcdef"));
    try
    {
        ProviderAssemblyVersion.ParseInformationalVersion("0.1.0-RC1+source");
        throw new Exception("accepted uppercase prerelease metadata");
    }
    catch (InvalidOperationException)
    {
    }
    return Task.CompletedTask;
}

static T ThrowFactory<T>() =>
    throw new Exception($"inert route instantiated {typeof(T).Name}");

sealed class FakeClock : IClock
{
    public DateTimeOffset UtcNow { get; set; } = new(2026, 7, 27, 12, 0, 0, TimeSpan.Zero);
    public string BootId { get; set; } = "boot-test";
}
sealed class MemoryStore : IStateStore
{
    public StateRecord State { get; set; } = new();
    public bool ThrowOnLoad { get; set; }
    public int? FailOnSaveCall { get; set; }
    private int saveCalls;
    public StateRecord Load() => ThrowOnLoad ? throw new InvalidDataException() : State;
    public void Save(StateRecord state)
    {
        saveCalls++;
        if (saveCalls == FailOnSaveCall) throw new IOException("injected save failure");
        State = state;
    }
}
sealed class FakeBackend(Snapshot snapshot) : IHotspotBackend
{
    private Snapshot current = snapshot;
    public Snapshot? AfterStart { get; set; }
    public Snapshot? AfterStop { get; set; }
    public bool StartSuccess { get; set; } = true;
    public bool StopSuccess { get; set; } = true;
    public bool Delay { get; set; }
    public async Task<Snapshot> ReadAsync(CancellationToken token) { if (Delay) await Task.Delay(Timeout.Infinite, token); return current; }
    public Task<BackendResult> StartAsync(CancellationToken token) { if (StartSuccess && AfterStart is not null) current = AfterStart; return Task.FromResult(new BackendResult(StartSuccess, StartSuccess ? "Success" : "Failure")); }
    public Task<BackendResult> StopAsync(CancellationToken token) { if (StopSuccess && AfterStop is not null) current = AfterStop; return Task.FromResult(new BackendResult(StopSuccess, StopSuccess ? "Success" : "Failure")); }
}
