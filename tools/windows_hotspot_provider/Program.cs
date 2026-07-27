using System.Text.Json;
using RustyHostess.WindowsHotspot;

var standardInvocation =
    args.Length == 3 &&
    args[0] == "integration" &&
    args[1] == "windows-hotspot" &&
    args[2] == "--json";
var artifactReadOnlyProbe =
    args.Length == 4 &&
    args[0] == "integration" &&
    args[1] == "windows-hotspot" &&
    args[2] == "--json" &&
    args[3] == "--artifact-readonly-probe";
if (!standardInvocation && !artifactReadOnlyProbe)
    return 2;

var clock = new SystemClock();
Request request;
try
{
    using var reader = new StreamReader(Console.OpenStandardInput());
    request = Protocol.ParseRequest(reader.ReadToEnd(), clock.UtcNow);
}
catch (RejectedException)
{
    Console.Out.Write(JsonSerializer.Serialize(new Receipt {
        Outcome = "rejected", Reason = "request.rejected", ObservedAtUtc = clock.UtcNow.ToString("O")
    }));
    return 2;
}
if (artifactReadOnlyProbe && request.Action != "status")
{
    Console.Out.Write(JsonSerializer.Serialize(new Receipt {
        RequestId = request.RequestId, OperationId = request.OperationId, Action = request.Action,
        Outcome = "rejected", Reason = "artifact_probe.status_only", ObservedAtUtc = clock.UtcNow.ToString("O")
    }));
    return 2;
}

using var mutex = new Mutex(false, "Global\\RustyHostess.WindowsHotspot.Provider.v1");
var acquired = MutexGate.TryAcquire(mutex, TimeSpan.FromSeconds(2));
if (!acquired)
{
    Console.Out.Write(JsonSerializer.Serialize(new Receipt {
        RequestId = request.RequestId, OperationId = request.OperationId, Action = request.Action,
        Outcome = "rejected", Reason = "operation.concurrent", ObservedAtUtc = clock.UtcNow.ToString("O")
    }));
    return 2;
}
try
{
    var remaining = request.ExpiresAtUtc - clock.UtcNow;
    if (remaining <= TimeSpan.Zero)
    {
        Console.Out.Write(JsonSerializer.Serialize(new Receipt {
            RequestId = request.RequestId, OperationId = request.OperationId, Action = request.Action,
            Outcome = "rejected", Reason = "request.expired", ObservedAtUtc = clock.UtcNow.ToString("O")
        }));
        return 2;
    }
    using var timeout = new CancellationTokenSource(TimeSpan.FromMilliseconds(request.TimeoutMs));
    using var expiry = new CancellationTokenSource(remaining);
    using var combined = CancellationTokenSource.CreateLinkedTokenSource(timeout.Token, expiry.Token);
    IStateStore stateStore = artifactReadOnlyProbe ? new VolatileStateStore() : new FileStateStore();
    var provider = new Provider(new WindowsHotspotBackend(), stateStore, clock);
    // Mutex ownership is thread-affine. Block the console entrypoint on the
    // asynchronous WinRT operation so this thread also performs ReleaseMutex.
    var result = provider.ExecuteAsync(request, combined.Token).GetAwaiter().GetResult();
    Console.Out.Write(JsonSerializer.Serialize(result.Receipt));
    return (int)result.Outcome;
}
finally { mutex.ReleaseMutex(); }
