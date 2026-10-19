using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlShellRecenterService
{
    public static IReadOnlyList<string> Modes { get; } = ["readiness", "recenter", "reconcile"];

    public static IReadOnlyList<string> BuildArguments(string profile, string mode, string output)
    {
        if (string.IsNullOrWhiteSpace(profile) || !Modes.Contains(mode))
            throw new InvalidOperationException("A pinned private shell profile and lifecycle mode are required.");
        return ["companion-session", "shell-recenter", "--profile", profile, "--mode", mode, "--out", output];
    }

    public async Task<CompanionReportProjection> RunAsync(string profile, string mode)
    {
        var repo = HostessctlServicePaths.LocateRepoRoot();
        var observation = Guid.NewGuid().ToString("N");
        var output = Path.Combine(repo.FullName, "target", "companion-command", $"wpf-shell-recenter-{observation}.json");
        var projection = Path.Combine(repo.FullName, "target", "companion-command", $"wpf-shell-recenter-{observation}.projection.json");
        Directory.CreateDirectory(Path.GetDirectoryName(output)!);
        // A failed new invocation must never display a previous request's success.
        var exit = await RunCliAsync(repo, BuildArguments(profile, mode, output));
        if (!File.Exists(output))
            throw new InvalidOperationException($"Shell recenter CLI exited {exit} without evidence.");
        var projectionExit = await RunCliAsync(repo,
            ["companion-report", "projection", "--frontend", "wpf", "--shell-recenter", output, "--out", projection, "--fail-on-error"]);
        if (projectionExit != 0)
            throw new InvalidOperationException("Shell recenter evidence projection failed validation.");
        await using var stream = File.OpenRead(projection);
        return await JsonSerializer.DeserializeAsync<CompanionReportProjection>(stream)
            ?? throw new InvalidOperationException("Shell recenter projection was empty.");
    }

    private static async Task<int> RunCliAsync(DirectoryInfo repo, IReadOnlyList<string> arguments)
    {
        var start = new ProcessStartInfo
        {
            FileName = HostessctlServicePaths.ResolvePythonExecutable(repo), WorkingDirectory = repo.FullName,
            UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true, CreateNoWindow = true,
        };
        start.ArgumentList.Add("-I");
        start.ArgumentList.Add("tools/hostessctl/hostessctl.py");
        foreach (var argument in arguments) start.ArgumentList.Add(argument);
        using var child = Process.Start(start) ?? throw new InvalidOperationException("Could not start shell recenter CLI.");
        // No UI observer cancellation or destructive timeout can abandon an
        // original. Both readers and the same child are retained through EOF/reap.
        var stdout = child.StandardOutput.ReadToEndAsync();
        var stderr = child.StandardError.ReadToEndAsync();
        await child.WaitForExitAsync();
        await Task.WhenAll(stdout, stderr);
        if (child.ExitCode != 0 && !string.IsNullOrWhiteSpace(stderr.Result))
            throw new InvalidOperationException($"Shell recenter CLI exited {child.ExitCode}: {stderr.Result}");
        return child.ExitCode;
    }
}
