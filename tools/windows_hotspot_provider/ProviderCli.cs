using System.Text.Json;

namespace RustyHostess.WindowsHotspot;

internal static class ProviderCli
{
    internal static int Run(
        string[] args,
        Func<TextReader> inputFactory,
        TextWriter output,
        Func<IClock> clockFactory,
        Func<IHotspotBackend> backendFactory,
        Func<IStateStore> stateStoreFactory,
        Func<IStateStore> volatileStateStoreFactory,
        Func<DateTimeOffset> discoveryClock,
        Func<string> providerVersion)
    {
        if (args.Length == 1 && args[0] == "--describe-json")
        {
            output.Write(CapabilityDiscovery.Serialize(
                discoveryClock(),
                providerVersion()));
            return 0;
        }

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

        var clock = clockFactory();
        Request request;
        try
        {
            using var input = inputFactory();
            request = Protocol.ParseRequest(
                input.ReadToEnd(),
                clock.UtcNow);
        }
        catch (RejectedException)
        {
            output.Write(JsonSerializer.Serialize(new Receipt {
                Outcome = "rejected",
                Reason = "request.rejected",
                ObservedAtUtc = clock.UtcNow.ToString("O")
            }));
            return 2;
        }
        if (artifactReadOnlyProbe && request.Action != "status")
        {
            output.Write(JsonSerializer.Serialize(new Receipt {
                RequestId = request.RequestId,
                OperationId = request.OperationId,
                Action = request.Action,
                Outcome = "rejected",
                Reason = "artifact_probe.status_only",
                ObservedAtUtc = clock.UtcNow.ToString("O")
            }));
            return 2;
        }

        using var mutex = new Mutex(
            false,
            "Global\\RustyHostess.WindowsHotspot.Provider.v1");
        var acquired = MutexGate.TryAcquire(mutex, TimeSpan.FromSeconds(2));
        if (!acquired)
        {
            output.Write(JsonSerializer.Serialize(new Receipt {
                RequestId = request.RequestId,
                OperationId = request.OperationId,
                Action = request.Action,
                Outcome = "rejected",
                Reason = "operation.concurrent",
                ObservedAtUtc = clock.UtcNow.ToString("O")
            }));
            return 2;
        }
        try
        {
            var remaining = request.ExpiresAtUtc - clock.UtcNow;
            if (remaining <= TimeSpan.Zero)
            {
                output.Write(JsonSerializer.Serialize(new Receipt {
                    RequestId = request.RequestId,
                    OperationId = request.OperationId,
                    Action = request.Action,
                    Outcome = "rejected",
                    Reason = "request.expired",
                    ObservedAtUtc = clock.UtcNow.ToString("O")
                }));
                return 2;
            }
            using var timeout = new CancellationTokenSource(
                TimeSpan.FromMilliseconds(request.TimeoutMs));
            using var expiry = new CancellationTokenSource(remaining);
            using var combined = CancellationTokenSource.CreateLinkedTokenSource(
                timeout.Token,
                expiry.Token);
            var stateStore = artifactReadOnlyProbe
                ? volatileStateStoreFactory()
                : stateStoreFactory();
            var provider = new Provider(
                backendFactory(),
                stateStore,
                clock);
            // Mutex ownership is thread-affine. Block the console entrypoint on
            // the asynchronous WinRT operation so this thread also releases it.
            var result = provider.ExecuteAsync(request, combined.Token)
                .GetAwaiter()
                .GetResult();
            output.Write(JsonSerializer.Serialize(result.Receipt));
            return (int)result.Outcome;
        }
        finally
        {
            mutex.ReleaseMutex();
        }
    }
}
