using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlReadinessService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<ReadinessReport> RefreshAsync(
        string serial,
        bool useQuestProfile,
        bool checkBroker,
        CancellationToken cancellationToken)
    {
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-readiness",
            "wpf-readiness.json"));
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
        startInfo.ArgumentList.Add("companion-readiness");
        startInfo.ArgumentList.Add("--out");
        startInfo.ArgumentList.Add(reportPath.FullName);
        startInfo.ArgumentList.Add("--descriptor");
        startInfo.ArgumentList.Add(descriptorPath.FullName);
        if (useQuestProfile)
        {
            startInfo.ArgumentList.Add("--profile");
            startInfo.ArgumentList.Add("hostess-makepad-quest");
        }
        if (!string.IsNullOrWhiteSpace(serial))
        {
            startInfo.ArgumentList.Add("--serial");
            startInfo.ArgumentList.Add(serial.Trim());
        }
        if (checkBroker)
        {
            startInfo.ArgumentList.Add("--check-broker");
        }

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start hostessctl readiness process.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"hostessctl companion-readiness exited with {process.ExitCode}: {stderr}{stdout}");
        }

        await using var stream = File.OpenRead(reportPath.FullName);
        return await JsonSerializer.DeserializeAsync<ReadinessReport>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Readiness report was empty.");
    }

}
