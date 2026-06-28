using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlCommandService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<BridgeCommandExecution> RunAuthorizedProbeAsync(
        string serial,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(serial))
        {
            throw new InvalidOperationException("A Quest serial is required for the safe probe.");
        }

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var primaryOutPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-command",
            "wpf-broker-stream-probe-evidence.json"));
        var primaryExecutionPath = new FileInfo(Path.Combine(
            primaryOutPath.Directory!.FullName,
            "wpf-broker-stream-probe-evidence.live-android-execution.json"));
        var primaryInputPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "fixtures",
            "bridge-command",
            "hostess-broker-stream-command-request.json"));
        Directory.CreateDirectory(primaryOutPath.Directory!.FullName);

        try
        {
            var primary = await RunHostessctlAsync(
                repoRoot,
                primaryExecutionPath,
                [
                    "run-bridge-command-live-android",
                    "--input",
                    primaryInputPath.FullName,
                    "--out",
                    primaryOutPath.FullName,
                    "--adb",
                    HostessctlAdbResolver.ResolveAdb(),
                    "--serial",
                    serial.Trim(),
                    "--wait-seconds",
                    "20",
                ],
                cancellationToken)
                .ConfigureAwait(false);
            if (string.Equals(primary.Status, "pass", StringComparison.OrdinalIgnoreCase))
            {
                return primary;
            }
        }
        catch (InvalidOperationException)
        {
            // The app-private shim below is the explicit recovery path while the
            // live broker/runtime pair is being brought up.
        }

        var fallbackOutPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-command",
            "wpf-app-private-probe-evidence.json"));
        var fallbackExecutionPath = new FileInfo(Path.Combine(
            fallbackOutPath.Directory!.FullName,
            "wpf-app-private-probe-evidence.android-execution.json"));
        var fallbackInputPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "fixtures",
            "bridge-command",
            "hostess-android-hotload-command-request.json"));
        Directory.CreateDirectory(fallbackOutPath.Directory!.FullName);

        return await RunHostessctlAsync(
                repoRoot,
                fallbackExecutionPath,
                [
                    "run-bridge-command-android",
                    "--input",
                    fallbackInputPath.FullName,
                "--out",
                fallbackOutPath.FullName,
                "--adb",
                HostessctlAdbResolver.ResolveAdb(),
                "--serial",
                serial.Trim(),
                "--wait-seconds",
                    "20",
                ],
                cancellationToken)
            .ConfigureAwait(false);
    }

    private static async Task<BridgeCommandExecution> RunHostessctlAsync(
        DirectoryInfo repoRoot,
        FileInfo executionPath,
        IReadOnlyList<string> arguments,
        CancellationToken cancellationToken)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = "python",
            WorkingDirectory = repoRoot.FullName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("tools/hostessctl/hostessctl.py");
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start hostessctl command process.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (!executionPath.Exists)
        {
            throw new InvalidOperationException(
                $"hostessctl did not write command execution evidence: {stderr}{stdout}");
        }

        await using var stream = File.OpenRead(executionPath.FullName);
        return await JsonSerializer.DeserializeAsync<BridgeCommandExecution>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Command execution report was empty.");
    }
}
