using System.Text.Json;
using RustyHostess.WindowsHotspot;

if (args.Length != 3 || args[0] != "integration" || args[1] != "windows-hotspot" || args[2] != "--json")
    return 2;

var clock = new SystemClock();
Request request;
try
{
    using var reader = new StreamReader(Console.OpenStandardInput());
    request = Protocol.ParseRequest(await reader.ReadToEndAsync(), clock.UtcNow);
}
catch (RejectedException)
{
    Console.Out.Write(JsonSerializer.Serialize(new Receipt {
        Outcome = "rejected", Reason = "request.rejected", ObservedAtUtc = clock.UtcNow.ToString("O")
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
    var provider = new Provider(new WindowsHotspotBackend(), new FileStateStore(), clock);
    var result = await provider.ExecuteAsync(request, combined.Token);
    Console.Out.Write(JsonSerializer.Serialize(result.Receipt));
    return (int)result.Outcome;
}
finally { mutex.ReleaseMutex(); }
