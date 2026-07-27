using System.Text.Json.Serialization;

namespace RustyHostess.WindowsHotspot;

internal enum Outcome { Verified = 0, Failed = 1, Rejected = 2, Unavailable = 3 }
internal sealed record Snapshot(bool CapabilityAvailable, string Capability, string OperationalState,
    uint ClientCount, uint MaxClientCount, string Band, string SourceConnectivity);
internal sealed record BackendResult(bool Success, string Status);

internal interface IHotspotBackend
{
    Task<Snapshot> ReadAsync(CancellationToken cancellationToken);
    Task<BackendResult> StartAsync(CancellationToken cancellationToken);
    Task<BackendResult> StopAsync(CancellationToken cancellationToken);
}
internal interface IStateStore
{
    StateRecord Load();
    void Save(StateRecord state);
}
internal interface IClock { DateTimeOffset UtcNow { get; } string BootId { get; } }

internal static class MutexGate
{
    internal static bool TryAcquire(Mutex mutex, TimeSpan timeout)
    {
        try { return mutex.WaitOne(timeout); }
        catch (AbandonedMutexException) { return true; }
    }
}

internal sealed record StateRecord
{
    [JsonPropertyName("schema")] public string Schema { get; init; } = "rusty.hostess.windows_hotspot.private_state.v1";
    [JsonPropertyName("boot_id")] public string BootId { get; init; } = "";
    [JsonPropertyName("ownership_generation")] public string? OwnershipGeneration { get; init; }
    [JsonPropertyName("request_ids")] public List<string> RequestIds { get; init; } = [];
    [JsonPropertyName("operation_ids")] public List<string> OperationIds { get; init; } = [];
}

internal sealed record Receipt
{
    [JsonPropertyName("schema")] public string Schema { get; init; } = Protocol.ReceiptSchema;
    [JsonPropertyName("request_id")] public string RequestId { get; init; } = "";
    [JsonPropertyName("operation_id")] public string OperationId { get; init; } = "";
    [JsonPropertyName("action")] public string Action { get; init; } = "";
    [JsonPropertyName("outcome")] public string Outcome { get; init; } = "";
    [JsonPropertyName("reason")] public string Reason { get; init; } = "";
    [JsonPropertyName("observed_at_utc")] public string ObservedAtUtc { get; init; } = "";
    [JsonPropertyName("capability_available")] public bool CapabilityAvailable { get; init; }
    [JsonPropertyName("capability")] public string Capability { get; init; } = "Unknown";
    [JsonPropertyName("operational_state")] public string OperationalState { get; init; } = "Unknown";
    [JsonPropertyName("client_count")] public uint ClientCount { get; init; }
    [JsonPropertyName("max_client_count")] public uint MaxClientCount { get; init; }
    [JsonPropertyName("band")] public string Band { get; init; } = "Unknown";
    [JsonPropertyName("source_connectivity")] public string SourceConnectivity { get; init; } = "Unknown";
    [JsonPropertyName("ownership_generation")] public string? OwnershipGeneration { get; init; }
}

internal sealed class Provider(IHotspotBackend backend, IStateStore store, IClock clock)
{
    internal async Task<(Outcome Outcome, Receipt Receipt)> ExecuteAsync(Request request, CancellationToken cancellationToken)
    {
        StateRecord state;
        try { state = store.Load(); }
        catch { return Result(Outcome.Failed, request, "state.damaged", null, null); }
        var priorBoot = state.BootId.Length > 0 && state.BootId != clock.BootId;
        if (priorBoot)
        {
            try
            {
                var snapshot = await backend.ReadAsync(cancellationToken);
                if (request.Action == "status")
                    return Result(Outcome.Failed, request, "state.restart_detected", snapshot, null);
                if (request.Action != "start")
                    return Result(Outcome.Rejected, request, "ownership.prior_boot_generation", snapshot, null);
                if (!snapshot.CapabilityAvailable)
                    return Result(Outcome.Unavailable, request, "capability.unavailable", snapshot, null);
                if (snapshot.OperationalState != "Off")
                    return Result(Outcome.Rejected, request, "ownership.external_hotspot_on", snapshot, null);

                var start = await backend.StartAsync(cancellationToken);
                if (!start.Success)
                    return Result(Outcome.Failed, request, "start.result_failed", await backend.ReadAsync(cancellationToken), null);
                var after = await backend.ReadAsync(cancellationToken);
                if (after.OperationalState != "On")
                    return Result(Outcome.Failed, request, "start.readback_not_on", after, null);
                var recoveredGeneration = Guid.NewGuid().ToString("N");
                var recoveredState = new StateRecord {
                    BootId = clock.BootId,
                    OwnershipGeneration = recoveredGeneration,
                    RequestIds = [request.RequestId],
                    OperationIds = [request.OperationId]
                };
                store.Save(recoveredState);
                return Result(Outcome.Verified, request, "start.restart_recovery_verified", after, recoveredGeneration);
            }
            catch (OperationCanceledException) { return Result(Outcome.Failed, request, "operation.timeout_or_cancelled", null, null); }
            catch (PlatformNotSupportedException) { return Result(Outcome.Unavailable, request, "platform.unavailable", null, null); }
            catch { return Result(Outcome.Failed, request, "operation.failed", null, null); }
        }
        if (state.RequestIds.Contains(request.RequestId, StringComparer.Ordinal) ||
            state.OperationIds.Contains(request.OperationId, StringComparer.Ordinal))
            return Result(Outcome.Rejected, request, "request.replay", null, null);

        state = state with {
            BootId = clock.BootId,
            RequestIds = AppendBounded(state.RequestIds, request.RequestId),
            OperationIds = AppendBounded(state.OperationIds, request.OperationId)
        };
        try { store.Save(state); } catch { return Result(Outcome.Failed, request, "state.write_failed", null, null); }

        try
        {
            var before = await backend.ReadAsync(cancellationToken);
            if (!before.CapabilityAvailable) return Result(Outcome.Unavailable, request, "capability.unavailable", before, null);
            if (request.Action == "status") return Result(Outcome.Verified, request, "status.read", before, null);
            if (request.Action is "start" or "ensure")
            {
                if (before.OperationalState == "On")
                {
                    if (state.OwnershipGeneration is null)
                        return Result(Outcome.Rejected, request, "ownership.external_hotspot_on", before, null);
                    if (request.Action == "ensure" && request.OwnershipGeneration != state.OwnershipGeneration)
                        return Result(Outcome.Rejected, request, "ownership.generation_mismatch", before, null);
                    return Result(Outcome.Verified, request, "hotspot.already_owned_on", before, state.OwnershipGeneration);
                }
                if (state.OwnershipGeneration is not null)
                {
                    if (request.Action == "ensure" && request.OwnershipGeneration != state.OwnershipGeneration)
                        return Result(Outcome.Rejected, request, "ownership.generation_mismatch", before, null);
                    if (request.Action != "ensure")
                        return Result(Outcome.Failed, request, "ownership.state_inconsistent", before, null);
                    var restart = await backend.StartAsync(cancellationToken);
                    if (!restart.Success)
                        return Result(Outcome.Failed, request, "ensure.restart_result_failed", await backend.ReadAsync(cancellationToken), state.OwnershipGeneration);
                    var restarted = await backend.ReadAsync(cancellationToken);
                    if (restarted.OperationalState != "On")
                        return Result(Outcome.Failed, request, "ensure.restart_readback_not_on", restarted, state.OwnershipGeneration);
                    return Result(Outcome.Verified, request, "ensure.restart_readback_verified", restarted, state.OwnershipGeneration);
                }
                if (request.Action == "ensure" && request.OwnershipGeneration is not null)
                    return Result(Outcome.Rejected, request, "ownership.generation_unknown", before, null);
                var start = await backend.StartAsync(cancellationToken);
                if (!start.Success) return Result(Outcome.Failed, request, "start.result_failed", await backend.ReadAsync(cancellationToken), null);
                var after = await backend.ReadAsync(cancellationToken);
                if (after.OperationalState != "On") return Result(Outcome.Failed, request, "start.readback_not_on", after, null);
                var generation = Guid.NewGuid().ToString("N");
                state = state with { OwnershipGeneration = generation };
                store.Save(state);
                return Result(Outcome.Verified, request, "start.readback_verified", after, generation);
            }
            if (state.OwnershipGeneration is null)
                return Result(Outcome.Rejected, request, "ownership.not_owned", before, null);
            if (request.OwnershipGeneration != state.OwnershipGeneration)
                return Result(Outcome.Rejected, request, "ownership.generation_mismatch", before, null);
            if (before.OperationalState != "On")
                return Result(Outcome.Failed, request, "ownership.state_inconsistent", before, state.OwnershipGeneration);
            var stop = await backend.StopAsync(cancellationToken);
            if (!stop.Success) return Result(Outcome.Failed, request, "stop.result_failed", await backend.ReadAsync(cancellationToken), state.OwnershipGeneration);
            var stopped = await backend.ReadAsync(cancellationToken);
            if (stopped.OperationalState != "Off") return Result(Outcome.Failed, request, "stop.readback_not_off", stopped, state.OwnershipGeneration);
            state = state with { OwnershipGeneration = null };
            store.Save(state);
            return Result(Outcome.Verified, request, "stop.readback_verified", stopped, null);
        }
        catch (OperationCanceledException) { return Result(Outcome.Failed, request, "operation.timeout_or_cancelled", null, state.OwnershipGeneration); }
        catch (PlatformNotSupportedException) { return Result(Outcome.Unavailable, request, "platform.unavailable", null, state.OwnershipGeneration); }
        catch { return Result(Outcome.Failed, request, "operation.failed", null, state.OwnershipGeneration); }
    }

    private static List<string> AppendBounded(List<string> source, string value) => source.Append(value).TakeLast(256).ToList();
    internal (Outcome, Receipt) Rejected(Request request, string reason) => Result(Outcome.Rejected, request, reason, null, null);
    private (Outcome, Receipt) Result(Outcome outcome, Request request, string reason, Snapshot? snapshot, string? generation) =>
        (outcome, new Receipt {
            RequestId = request.RequestId, OperationId = request.OperationId, Action = request.Action,
            Outcome = outcome.ToString().ToLowerInvariant(), Reason = reason, ObservedAtUtc = clock.UtcNow.ToString("O"),
            CapabilityAvailable = snapshot?.CapabilityAvailable ?? false, Capability = snapshot?.Capability ?? "Unknown",
            OperationalState = snapshot?.OperationalState ?? "Unknown", ClientCount = snapshot?.ClientCount ?? 0,
            MaxClientCount = snapshot?.MaxClientCount ?? 0, Band = snapshot?.Band ?? "Unknown",
            SourceConnectivity = snapshot?.SourceConnectivity ?? "Unknown", OwnershipGeneration = generation
        });
}
