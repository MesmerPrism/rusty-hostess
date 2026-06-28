using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlSessionService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<CompanionSessionReport> RunSessionAsync(
        string serial,
        bool checkBroker,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(serial))
        {
            throw new InvalidOperationException("A Quest serial is required for the companion session.");
        }

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-session",
            "wpf-session.json"));
        var descriptorPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "fixtures",
            "companion-readiness",
            "readiness-module-descriptor.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        var startInfo = new ProcessStartInfo
        {
            FileName = "python",
            WorkingDirectory = repoRoot.FullName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("tools/hostessctl/hostessctl.py");
        startInfo.ArgumentList.Add("companion-session");
        startInfo.ArgumentList.Add("run");
        startInfo.ArgumentList.Add("--out");
        startInfo.ArgumentList.Add(reportPath.FullName);
        startInfo.ArgumentList.Add("--frontend");
        startInfo.ArgumentList.Add("wpf");
        startInfo.ArgumentList.Add("--profile");
        startInfo.ArgumentList.Add("hostess-makepad-quest");
        startInfo.ArgumentList.Add("--descriptor");
        startInfo.ArgumentList.Add(descriptorPath.FullName);
        startInfo.ArgumentList.Add("--adb");
        startInfo.ArgumentList.Add(HostessctlAdbResolver.ResolveAdb());
        startInfo.ArgumentList.Add("--serial");
        startInfo.ArgumentList.Add(serial.Trim());
        startInfo.ArgumentList.Add("--wait-seconds");
        startInfo.ArgumentList.Add("20");
        if (checkBroker)
        {
            startInfo.ArgumentList.Add("--check-broker");
        }

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start hostessctl session process.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (!reportPath.Exists)
        {
            throw new InvalidOperationException(
                $"hostessctl did not write companion session report: {stderr}{stdout}");
        }

        await using var stream = File.OpenRead(reportPath.FullName);
        return await JsonSerializer.DeserializeAsync<CompanionSessionReport>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Companion session report was empty.");
    }
}
