using System.Diagnostics;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Windows.Devices.WiFiDirect;
using Windows.Security.Credentials;

// Diagnostic WinRT autonomous GO only. No Internet-sharing API is invoked.
if (args.SequenceEqual(["--self-test"])) return await SelfTest();
if (args.SequenceEqual(["--host-preflight"])) return await Run(true);
if (args.Length == 3 && args[0] is "--status" or "--stop")
    return await FileControl(args[0][2..].ToUpperInvariant(), args[1], args[2]);
if (args.Length != 0) return 2;
return await Run(false);

static async Task<int> Run(bool preflight)
{
    WiFiDirectAdvertisementPublisher? publisher = null;
    TcpListener? listener = null;
    using var cancel = new CancellationTokenSource();
    var stopped = Signal(); var aborted = Signal(); var stop = Signal();
    Dictionary<string, object?> receipt = [];
    string? receiptPath = null; RuntimeState? state = null;
    Task? controlTask = null; Task? echoTask = null;
    bool success = false, stopObserved = false;
    string stopReason = "startup_failure";
    try
    {
        Request request = ParseRequest(await Console.In.ReadToEndAsync(), preflight);
        string root = CheckedRoot(request.OutputRoot);
        string readyPath = CheckedOutput(root, request.ReadyName);
        receiptPath = CheckedOutput(root, request.ReceiptName);
        if (readyPath.Equals(receiptPath, StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("distinct_outputs_required");
        receipt = BaseReceipt(request.OperationId, preflight);

        List<Link> before = Addresses();
        publisher = new WiFiDirectAdvertisementPublisher();
        publisher.Advertisement.IsAutonomousGroupOwnerEnabled = true;
        publisher.Advertisement.LegacySettings.IsEnabled = true;
        publisher.Advertisement.LegacySettings.Ssid = request.Ssid;
        publisher.Advertisement.LegacySettings.Passphrase = new PasswordCredential { Password = request.Passphrase };
        var started = Signal();
        publisher.StatusChanged += (_, e) =>
        {
            if (e.Status == WiFiDirectAdvertisementPublisherStatus.Started) started.TrySetResult(true);
            if (e.Status == WiFiDirectAdvertisementPublisherStatus.Stopped) stopped.TrySetResult(true);
            if (e.Status == WiFiDirectAdvertisementPublisherStatus.Aborted)
            { aborted.TrySetResult(true); started.TrySetResult(false); }
        };
        publisher.Start();
        if (await Task.WhenAny(started.Task, Task.Delay(10_000)) != started.Task || !await started.Task)
            throw new InvalidOperationException("publisher_not_started");

        Link? link = null;
        for (int i = 0; i < 40 && !aborted.Task.IsCompleted; i++)
        {
            Link[] candidates = Addresses().Where(x => !before.Any(b => b.Index == x.Index && b.Address == x.Address)).ToArray();
            if (candidates.Length == 1) { link = candidates[0]; break; }
            if (candidates.Length > 1) throw new InvalidOperationException("go_interface_ambiguous");
            await Task.Delay(250);
        }
        if (link is null) throw new InvalidOperationException("go_ipv4_before_client_unavailable");
        if (aborted.Task.IsCompleted || !await NoUpstream(link))
            throw new InvalidOperationException("local_only_interface_unproven");

        listener = new TcpListener(IPAddress.Parse(link.Address), request.HealthPort);
        listener.Server.ExclusiveAddressUse = true; listener.Start(4);
        var endpoint = (IPEndPoint)listener.LocalEndpoint;
        if (endpoint.Address.ToString() != link.Address || endpoint.Port != request.HealthPort)
            throw new InvalidOperationException("listener_bind_failed");
        long now = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        string statusPath = ControlPath(root, request.OperationId, "status.json");
        string stopPath = ControlPath(root, request.OperationId, "stop.json");
        if (File.Exists(statusPath) || File.Exists(stopPath))
            throw new InvalidOperationException("control_path_exists");
        state = new(request.OperationId, link, request.HealthPort, now, now + request.DurationMs,
            statusPath, stopPath);
        echoTask = EchoLoop(listener, state, cancel.Token);
        controlTask = FileControlLoop(state, stop, cancel.Token);
        receipt = StartedReceipt(request, preflight, state);
        await WriteNew(readyPath, receipt);

        var elapsed = Stopwatch.StartNew();
        while (elapsed.ElapsedMilliseconds < request.DurationMs && !stop.Task.IsCompleted && !aborted.Task.IsCompleted)
        {
            if (controlTask.IsCompleted)
            {
                await controlTask;
                if (!stop.Task.IsCompleted) throw new InvalidOperationException("control_loop_stopped");
            }
            if (publisher.Status != WiFiDirectAdvertisementPublisherStatus.Started ||
                !Addresses().Any(x => x == link) || !await NoUpstream(link))
                throw new InvalidOperationException("runtime_local_only_proof_lost");
            await Task.WhenAny(Task.Delay(2_000), stop.Task, aborted.Task, controlTask);
        }
        if (controlTask.IsCompleted && !stop.Task.IsCompleted)
        {
            await controlTask;
            throw new InvalidOperationException("control_loop_stopped");
        }
        if (aborted.Task.IsCompleted) throw new InvalidOperationException("publisher_aborted");
        stopReason = stop.Task.IsCompleted ? "explicit_stop" : "ttl_expired";
        success = true;
    }
    catch (Exception e)
    {
        receipt["error_class"] = e.GetType().Name;
        string[] codes = ["publisher_not_started", "go_interface_ambiguous", "go_ipv4_before_client_unavailable",
            "local_only_interface_unproven", "listener_bind_failed", "runtime_local_only_proof_lost", "publisher_aborted",
            "control_io_unavailable", "control_loop_stopped"];
        if ((e is InvalidOperationException or IOException) && codes.Contains(e.Message)) receipt["error_code"] = e.Message;
    }
    finally
    {
        cancel.Cancel(); listener?.Stop();
        if (publisher is not null)
        {
            try
            {
                stopped = Signal(); publisher.Stop();
                stopObserved = await Task.WhenAny(stopped.Task, Task.Delay(10_000)) == stopped.Task &&
                    publisher.Status == WiFiDirectAdvertisementPublisherStatus.Stopped && !aborted.Task.IsCompleted;
            }
            catch { stopObserved = false; }
        }
        await ObserveShutdown(echoTask); await ObserveShutdown(controlTask);
        success &= stopObserved;
        receipt["state"] = success ? "stopped" : "failed";
        receipt["stop_reason"] = stopReason; receipt["stop_observed"] = stopObserved;
        receipt["echo_success_count"] = state?.EchoSuccessCount ?? 0;
        receipt["echo_rejection_count"] = state?.EchoRejectionCount ?? 0;
        if (receiptPath is not null)
            try { await WriteNew(receiptPath, receipt); } catch { success = false; }
        if (state is not null)
        {
            TryDelete(state.StopPath);
            TryDelete(state.StatusPath);
        }
    }
    return success ? 0 : 1;
}

static Request ParseRequest(string input, bool preflight)
{
    if (input.Length > 8192) throw new InvalidOperationException("request_oversize");
    using var doc = JsonDocument.Parse(input); JsonElement r = doc.RootElement;
    string[] allowed = ["schema", "operation_id", "ssid", "passphrase", "duration_ms", "output_root", "ready_name", "receipt_name", "health_port"];
    if (r.ValueKind != JsonValueKind.Object || r.EnumerateObject().Count() != allowed.Length ||
        r.EnumerateObject().Any(p => !allowed.Contains(p.Name))) throw new InvalidOperationException("request_fields");
    if (r.GetProperty("schema").GetString() != "rusty.hostess.wifi_direct_legacy_go.request.v2")
        throw new InvalidOperationException("request_schema");
    var request = new Request(r.GetProperty("operation_id").GetString() ?? "", r.GetProperty("ssid").GetString() ?? "",
        r.GetProperty("passphrase").GetString() ?? "", r.GetProperty("duration_ms").GetInt32(),
        r.GetProperty("output_root").GetString() ?? "", r.GetProperty("ready_name").GetString() ?? "",
        r.GetProperty("receipt_name").GetString() ?? "", r.GetProperty("health_port").GetInt32());
    bool validDuration = preflight ? request.DurationMs is >= 15_000 and <= 60_000 : request.DurationMs is >= 120_000 and <= 900_000;
    if (!ValidOperation(request.OperationId) || !Regex.IsMatch(request.Ssid, "^B11-[0-9a-f]{12}$") ||
        !Regex.IsMatch(request.Passphrase, "^[A-Za-z0-9_-]{8,63}$") || !validDuration ||
        request.HealthPort is < 40_000 or > 59_999) throw new InvalidOperationException("request_bounds");
    return request;
}

static async Task EchoLoop(TcpListener listener, RuntimeState state, CancellationToken token)
{
    while (!token.IsCancellationRequested)
    {
        TcpClient client;
        try { client = await listener.AcceptTcpClientAsync(token); }
        catch (OperationCanceledException) { break; }
        catch (SocketException) when (token.IsCancellationRequested) { break; }
        _ = HandleEcho(client, state, token);
    }
}

static async Task HandleEcho(TcpClient client, RuntimeState state, CancellationToken token)
{
    using (client)
    using (var timeout = CancellationTokenSource.CreateLinkedTokenSource(token))
    {
        timeout.CancelAfter(5_000);
        try
        {
            client.NoDelay = true; using NetworkStream stream = client.GetStream();
            string? line = await ReadLine(stream, 160, timeout.Token);
            Match match = Regex.Match(line ?? "", "^B11ECHO1 ([a-z0-9-]+) ([0-9a-f]{32})$");
            if (!match.Success || match.Groups[1].Value != state.OperationId)
            { Interlocked.Increment(ref state.EchoRejectionCount); return; }
            byte[] response = Encoding.ASCII.GetBytes($"B11ECHO1 OK {state.OperationId} {match.Groups[2].Value}\n");
            await stream.WriteAsync(response, timeout.Token); await stream.FlushAsync(timeout.Token);
            Interlocked.Increment(ref state.EchoSuccessCount);
        }
        catch { Interlocked.Increment(ref state.EchoRejectionCount); }
    }
}

static async Task<string?> ReadLine(Stream stream, int maximumBytes, CancellationToken token)
{
    var bytes = new List<byte>(maximumBytes); var one = new byte[1];
    while (bytes.Count < maximumBytes)
    {
        if (await stream.ReadAsync(one, token) == 0) return null;
        if (one[0] == (byte)'\n') return Encoding.ASCII.GetString(bytes.ToArray()).TrimEnd('\r');
        if (one[0] is < 0x20 or > 0x7e) return null;
        bytes.Add(one[0]);
    }
    return null;
}

static async Task FileControlLoop(RuntimeState state, TaskCompletionSource<bool> stop, CancellationToken token)
{
    long lastStatus = 0;
    long firstIoFailure = 0;
    while (!token.IsCancellationRequested)
    {
        try
        {
            if (File.Exists(state.StopPath))
            {
                try
                {
                    using JsonDocument request = await ReadJsonShared(state.StopPath, token);
                    JsonElement root = request.RootElement;
                    if (root.ValueKind != JsonValueKind.Object || root.EnumerateObject().Count() != 3 ||
                        root.GetProperty("schema").GetString() != "rusty.hostess.wifi_direct_legacy_go.stop.v1" ||
                        root.GetProperty("operation_id").GetString() != state.OperationId ||
                        root.GetProperty("action").GetString() != "stop")
                    {
                        File.Delete(state.StopPath);
                        continue;
                    }
                    File.Delete(state.StopPath);
                    stop.TrySetResult(true);
                    return;
                }
                catch (JsonException)
                {
                    File.Delete(state.StopPath);
                    continue;
                }
            }
            long now = Environment.TickCount64;
            if (now - lastStatus >= 500)
            {
                await WriteReplace(state.StatusPath, StatusReceipt(state, "running"));
                lastStatus = now;
            }
            firstIoFailure = 0;
            await Task.Delay(100, token);
        }
        catch (OperationCanceledException) { break; }
        catch (IOException) when (token.IsCancellationRequested) { break; }
        catch (Exception e) when (e is IOException or UnauthorizedAccessException)
        {
            long now = Environment.TickCount64;
            if (firstIoFailure == 0) firstIoFailure = now;
            if (now - firstIoFailure >= 2_000) throw new IOException("control_io_unavailable", e);
            await Task.Delay(50, token);
        }
    }
}

static async Task<int> FileControl(string command, string operationId, string outputRoot)
{
    if (!ValidOperation(operationId)) return 2;
    try
    {
        string root = CheckedRoot(outputRoot);
        string statusPath = ControlPath(root, operationId, "status.json");
        using JsonDocument status = await ReadJsonShared(statusPath, CancellationToken.None);
        if (status.RootElement.GetProperty("schema").GetString() != "rusty.hostess.wifi_direct_legacy_go.control.v1" ||
            status.RootElement.GetProperty("operation_id").GetString() != operationId ||
            status.RootElement.GetProperty("state").GetString() != "running") return 1;
        if (command == "STATUS")
        {
            Console.WriteLine(status.RootElement.GetRawText());
            return 0;
        }
        string stopPath = ControlPath(root, operationId, "stop.json");
        await WriteNew(stopPath, new()
        {
            ["schema"] = "rusty.hostess.wifi_direct_legacy_go.stop.v1",
            ["operation_id"] = operationId,
            ["action"] = "stop"
        });
        var timeout = Stopwatch.StartNew();
        while (timeout.ElapsedMilliseconds < 5_000 && File.Exists(stopPath)) await Task.Delay(50);
        var result = new Dictionary<string, object?>
        {
            ["schema"] = "rusty.hostess.wifi_direct_legacy_go.stop_request.v1",
            ["operation_id"] = operationId,
            ["state"] = File.Exists(stopPath) ? "stop_unobserved" : "stop_observed"
        };
        Console.WriteLine(JsonSerializer.Serialize(result));
        return File.Exists(stopPath) ? 1 : 0;
    }
    catch (Exception e)
    {
        Console.Error.WriteLine(JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            ["schema"] = "rusty.hostess.wifi_direct_legacy_go.control_error.v1",
            ["operation_id"] = operationId,
            ["error_class"] = e.GetType().Name
        }));
        return 1;
    }
}

static Dictionary<string, object?> BaseReceipt(string operationId, bool preflight) => new()
{ ["schema"] = "rusty.hostess.wifi_direct_legacy_go.receipt.v2", ["operation_id"] = operationId, ["host_only_preflight"] = preflight };

static Dictionary<string, object?> StartedReceipt(Request request, bool preflight, RuntimeState state) => new()
{
    ["schema"] = "rusty.hostess.wifi_direct_legacy_go.receipt.v2", ["operation_id"] = request.OperationId,
    ["state"] = "started", ["process_id"] = Environment.ProcessId, ["control"] = "private-run-directory-files",
    ["autonomous_group_owner"] = true, ["legacy_settings_enabled"] = true,
    ["credential_sensitive_redacted"] = true, ["internet_sharing_api_invoked"] = false,
    ["go_interface_sharing_enabled"] = false, ["go_interface_ipv4_forwarding_enabled"] = false,
    ["go_interface_ipv6_forwarding_enabled"] = false, ["go_interface_ipv6_default_route_advertised"] = false,
    ["no_upstream_verified"] = true,
    ["ssid_sha256"] = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(request.Ssid))),
    ["host_ipv4"] = state.Link.Address, ["interface_index"] = state.Link.Index, ["subnet"] = state.Link.Subnet,
    ["listener_bound_ipv4"] = state.Link.Address, ["host_health_port"] = state.HealthPort,
    ["health_protocol"] = "B11ECHO1", ["host_only_preflight"] = preflight,
    ["started_epoch_ms"] = state.StartedEpochMs, ["expires_epoch_ms"] = state.ExpiresEpochMs,
    ["duration_ms"] = request.DurationMs, ["private_interface_evidence"] = true, ["stop_observed"] = false
};

static Dictionary<string, object?> StatusReceipt(RuntimeState state, string outcome) => new()
{
    ["schema"] = "rusty.hostess.wifi_direct_legacy_go.control.v1", ["operation_id"] = state.OperationId,
    ["state"] = outcome, ["process_id"] = Environment.ProcessId, ["host_ipv4"] = state.Link.Address,
    ["interface_index"] = state.Link.Index, ["subnet"] = state.Link.Subnet, ["host_health_port"] = state.HealthPort,
    ["started_epoch_ms"] = state.StartedEpochMs, ["expires_epoch_ms"] = state.ExpiresEpochMs,
    ["echo_success_count"] = state.EchoSuccessCount, ["echo_rejection_count"] = state.EchoRejectionCount
};

static string CheckedRoot(string value)
{
    if (!Path.IsPathFullyQualified(value) || !Directory.Exists(value)) throw new InvalidOperationException("existing_absolute_output_root_required");
    string root = Path.GetFullPath(value);
    for (DirectoryInfo? directory = new(root); directory is not null; directory = directory.Parent)
        if ((directory.Attributes & FileAttributes.ReparsePoint) != 0) throw new InvalidOperationException("reparse_output_root");
    return root;
}

static string CheckedOutput(string root, string name)
{
    CheckedRoot(root);
    if (!Regex.IsMatch(name, "^[a-zA-Z0-9][a-zA-Z0-9._-]{0,80}\\.json$") || name.Contains(".."))
        throw new InvalidOperationException("output_name_invalid");
    string path = Path.Combine(root, name);
    if (File.Exists(path) || Directory.Exists(path)) throw new InvalidOperationException("output_exists");
    return path;
}

static async Task WriteNew(string path, Dictionary<string, object?> value)
{
    CheckedRoot(Path.GetDirectoryName(path)!);
    string temporary = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
    try
    {
        using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None))
        {
            await stream.WriteAsync(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value) + "\n"));
            stream.Flush(true);
        }
        File.Move(temporary, path, false);
    }
    finally { TryDelete(temporary); }
}

static async Task WriteReplace(string path, Dictionary<string, object?> value)
{
    CheckedRoot(Path.GetDirectoryName(path)!);
    string temporary = path + ".tmp";
    byte[] bytes = Encoding.UTF8.GetBytes(JsonSerializer.Serialize(value) + "\n");
    await File.WriteAllBytesAsync(temporary, bytes);
    File.Move(temporary, path, true);
}

static async Task<JsonDocument> ReadJsonShared(string path, CancellationToken token)
{
    using var stream = new FileStream(path, FileMode.Open, FileAccess.Read,
        FileShare.ReadWrite | FileShare.Delete, 4096, FileOptions.Asynchronous);
    return await JsonDocument.ParseAsync(stream, cancellationToken: token);
}

static string ControlPath(string root, string operationId, string suffix) =>
    Path.Combine(root, $"{operationId}.{suffix}");

static void TryDelete(string path)
{
    try { if (File.Exists(path)) File.Delete(path); } catch { }
}

static List<Link> Addresses()
{
    var result = new List<Link>();
    foreach (NetworkInterface nic in NetworkInterface.GetAllNetworkInterfaces())
    {
        if (nic.OperationalStatus != OperationalStatus.Up || !nic.Description.Contains("Wi-Fi Direct", StringComparison.OrdinalIgnoreCase)) continue;
        IPInterfaceProperties props = nic.GetIPProperties();
        foreach (UnicastIPAddressInformation address in props.UnicastAddresses)
        {
            if (address.Address.AddressFamily != AddressFamily.InterNetwork || address.PrefixLength != 24) continue;
            byte[] b = address.Address.GetAddressBytes();
            if (!(b[0] == 10 || b[0] == 172 && b[1] is >= 16 and <= 31 || b[0] == 192 && b[1] == 168) || b[3] is 0 or 255) continue;
            if (props.GatewayAddresses.Any(g => g.Address.AddressFamily == AddressFamily.InterNetwork && !g.Address.Equals(IPAddress.Any))) continue;
            result.Add(new(props.GetIPv4Properties().Index, address.Address.ToString(), $"{b[0]}.{b[1]}.{b[2]}.0/24"));
        }
    }
    return result;
}

static async Task<bool> NoUpstream(Link link)
{
    string script = "$ErrorActionPreference='Stop';try{" + $"$idx={link.Index};$prefix='{link.Subnet}';" +
        "$ip=@(Get-NetIPInterface -AddressFamily IPv4 -InterfaceIndex $idx);if($ip.Count-ne 1-or$ip[0].Forwarding-ne'Disabled'){exit 1};" +
        "$default=@(Get-NetRoute -AddressFamily IPv4 -InterfaceIndex $idx -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue);if($default.Count-ne 0){exit 1};" +
        "$ip6=@(Get-NetIPInterface -AddressFamily IPv6 -InterfaceIndex $idx);if(@($ip6|?{$_.Forwarding-ne'Disabled'-or$_.AdvertiseDefaultRoute-ne'Disabled'}).Count-ne 0){exit 1};" +
        "$default6=@(Get-NetRoute -AddressFamily IPv6 -InterfaceIndex $idx -DestinationPrefix '::/0' -ErrorAction SilentlyContinue);if($default6.Count-ne 0){exit 1};" +
        "$nat=@(Get-NetNat -ErrorAction SilentlyContinue|? InternalIPInterfaceAddressPrefix -eq $prefix);if($nat.Count-ne 0){exit 1};" +
        "$global=Get-ItemProperty 'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters';if($global.IPEnableRouter-eq 1){exit 1};" +
        "$adapter=Get-NetAdapter -InterfaceIndex $idx;$guid=([string]$adapter.InterfaceGuid).Trim('{}');$m=New-Object -ComObject HNetCfg.HNetShare;" +
        "foreach($c in $m.EnumEveryConnection()){$p=$m.NetConnectionProps($c);$cfg=$m.INetSharingConfigurationForINetConnection($c);if($cfg.SharingEnabled-and([string]$p.Guid).Trim('{}')-ieq$guid){exit 1}};exit 0}catch{exit 2}";
    using var process = new Process { StartInfo = new("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true } };
    foreach (string argument in new[] { "-NoProfile", "-NonInteractive", "-Command", script }) process.StartInfo.ArgumentList.Add(argument);
    process.Start(); using var timeout = new CancellationTokenSource(8_000);
    try { await process.WaitForExitAsync(timeout.Token); return process.ExitCode == 0; }
    catch { try { process.Kill(); } catch { } return false; }
}

static async Task<int> SelfTest()
{
    string root = Path.Combine(Path.GetTempPath(), "b11-go-selftest-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(root);
    int checks = 0; void Reject(Action action) { try { action(); } catch { checks++; return; } throw new Exception("expected_rejection"); }
    try
    {
        Reject(() => CheckedRoot("relative")); Reject(() => CheckedRoot(Path.Combine(root, "missing")));
        foreach (string name in new[] { "../outside.json", "a/other.json", "a\\other.json", "..json", "C:outside.json", "result.txt" }) Reject(() => CheckedOutput(root, name));
        string path = CheckedOutput(root, "ready.json"); await WriteNew(path, new() { ["state"] = "synthetic" });
        byte[] original = await File.ReadAllBytesAsync(path); Reject(() => CheckedOutput(root, "ready.json"));
        try { await WriteNew(path, new() { ["state"] = "overwrite" }); throw new Exception("overwrite_allowed"); } catch (IOException) { checks++; }
        if (!(await File.ReadAllBytesAsync(path)).SequenceEqual(original)) throw new Exception("original_changed"); checks++;
        string valid = JsonSerializer.Serialize(new { schema = "rusty.hostess.wifi_direct_legacy_go.request.v2", operation_id = "selftest-1234",
            ssid = "B11-012345abcdef", passphrase = "Secret_123", duration_ms = 15_000, output_root = root,
            ready_name = "new-ready.json", receipt_name = "new-result.json", health_port = 47_831 });
        _ = ParseRequest(valid, true); checks++; Reject(() => ParseRequest(valid.Replace("47831", "0"), true));
        var listener = new TcpListener(IPAddress.Loopback, 0); listener.Start(); int port = ((IPEndPoint)listener.LocalEndpoint).Port;
        var state = new RuntimeState("selftest-1234", new(1, "127.0.0.1", "127.0.0.0/24"), port, 1, 2);
        using var cancel = new CancellationTokenSource(); Task server = EchoLoop(listener, state, cancel.Token);
        string nonce = "0123456789abcdef0123456789abcdef";
        using (var client = new TcpClient()) { await client.ConnectAsync(IPAddress.Loopback, port); using NetworkStream stream = client.GetStream();
            await stream.WriteAsync(Encoding.ASCII.GetBytes($"B11ECHO1 selftest-1234 {nonce}\n"));
            if (await ReadLine(stream, 160, CancellationToken.None) != $"B11ECHO1 OK selftest-1234 {nonce}") throw new Exception("echo_mismatch"); }
        cancel.Cancel(); listener.Stop(); await ObserveShutdown(server);
        if (state.EchoSuccessCount != 1) throw new Exception("echo_not_counted"); checks++;

        string statusPath = ControlPath(root, state.OperationId, "status.json");
        string stopPath = ControlPath(root, state.OperationId, "stop.json");
        var controlState = new RuntimeState(state.OperationId, state.Link, state.HealthPort, 1, 2, statusPath, stopPath);
        using var controlCancel = new CancellationTokenSource();
        var stopSignal = Signal();
        Task control = FileControlLoop(controlState, stopSignal, controlCancel.Token);
        for (int i = 0; i < 100 && !File.Exists(statusPath); i++) await Task.Delay(10);
        if (await FileControl("STATUS", state.OperationId, root) != 0) throw new Exception("file_status_failed");
        checks++;

        using (var heldStatus = new FileStream(statusPath, FileMode.Open, FileAccess.Read, FileShare.Read))
        {
            await Task.Delay(650);
            if (control.IsCompleted) await control;
        }
        if (await FileControl("STOP", state.OperationId, root) != 0) throw new Exception("file_stop_failed");
        await control.WaitAsync(TimeSpan.FromSeconds(2));
        if (!stopSignal.Task.IsCompleted || File.Exists(stopPath)) throw new Exception("production_stop_not_consumed");
        checks += 2; TryDelete(statusPath); TryDelete(statusPath + ".tmp");
        Console.WriteLine($"PASS {checks} boundary checks; no live GO APIs invoked"); return 0;
    }
    finally { try { Directory.Delete(root, true); } catch { } }
}

static async Task ObserveShutdown(Task? task) { if (task is null) return; try { await task.WaitAsync(TimeSpan.FromSeconds(2)); } catch { } }
static bool ValidOperation(string value) => Regex.IsMatch(value, "^[a-z0-9][a-z0-9-]{7,47}$");
static TaskCompletionSource<bool> Signal() => new(TaskCreationOptions.RunContinuationsAsynchronously);

sealed record Request(string OperationId, string Ssid, string Passphrase, int DurationMs, string OutputRoot, string ReadyName, string ReceiptName, int HealthPort);
sealed record Link(int Index, string Address, string Subnet);
sealed class RuntimeState(string operationId, Link link, int healthPort, long startedEpochMs, long expiresEpochMs,
    string statusPath = "", string stopPath = "")
{
    internal string OperationId { get; } = operationId; internal Link Link { get; } = link; internal int HealthPort { get; } = healthPort;
    internal long StartedEpochMs { get; } = startedEpochMs; internal long ExpiresEpochMs { get; } = expiresEpochMs;
    internal string StatusPath { get; } = statusPath; internal string StopPath { get; } = stopPath;
    internal int EchoSuccessCount; internal int EchoRejectionCount;
}
