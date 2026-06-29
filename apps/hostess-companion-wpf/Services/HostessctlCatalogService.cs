using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlCatalogService
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<CompanionCatalog> RefreshAsync(CancellationToken cancellationToken)
    {
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-catalog",
            "wpf-catalog.json"));
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
        startInfo.ArgumentList.Add("companion-catalog");
        startInfo.ArgumentList.Add("--out");
        startInfo.ArgumentList.Add(reportPath.FullName);
        startInfo.ArgumentList.Add("--frontend");
        startInfo.ArgumentList.Add("wpf");

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start hostessctl catalog process.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"hostessctl companion-catalog exited with {process.ExitCode}: {stderr}{stdout}");
        }

        await using var stream = File.OpenRead(reportPath.FullName);
        return await JsonSerializer.DeserializeAsync<CompanionCatalog>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Companion catalog was empty.");
    }
}
