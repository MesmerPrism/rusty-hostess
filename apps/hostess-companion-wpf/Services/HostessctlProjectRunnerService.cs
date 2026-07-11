using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlProjectRunnerService
{
    public const string ProjectionSchema = "rusty.hostess.project_runner.projection.v1";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public static string DefaultCompletionMarkerPath()
    {
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        return Path.Combine(
            repoRoot.FullName,
            "target",
            "project-runner",
            "latest.complete.json");
    }

    public async Task<ProjectRunnerProjection> LoadProjectionAsync(
        string completionMarkerPath,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(completionMarkerPath))
        {
            throw new InvalidOperationException("A project-runner completion marker path is required.");
        }

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var marker = Path.IsPathFullyQualified(completionMarkerPath)
            ? completionMarkerPath
            : Path.Combine(repoRoot.FullName, completionMarkerPath);
        var projectionPath = Path.Combine(
            repoRoot.FullName,
            "target",
            "project-runner",
            "wpf-project-runner-projection.json");
        Directory.CreateDirectory(Path.GetDirectoryName(projectionPath)!);

        var startInfo = new ProcessStartInfo
        {
            FileName = "python",
            WorkingDirectory = repoRoot.FullName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("tools/hostessctl/hostessctl.py");
        startInfo.ArgumentList.Add("project-runner");
        startInfo.ArgumentList.Add("inspect");
        startInfo.ArgumentList.Add("--completion");
        startInfo.ArgumentList.Add(marker);
        startInfo.ArgumentList.Add("--out");
        startInfo.ArgumentList.Add(projectionPath);

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start project-runner inspector.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"project-runner inspect exited with {process.ExitCode}: {stderr}{stdout}");
        }

        return await LoadValidatedProjectionAsync(projectionPath, cancellationToken)
            .ConfigureAwait(false);
    }

    public static async Task<ProjectRunnerProjection> LoadValidatedProjectionAsync(
        string projectionPath,
        CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(projectionPath);
        var projection = await JsonSerializer.DeserializeAsync<ProjectRunnerProjection>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Project-runner projection was empty.");
        if (projection.Schema != ProjectionSchema
            || projection.Status != "complete"
            || !projection.DryRun
            || projection.Executed)
        {
            throw new InvalidOperationException(
                "Project-runner projection is not a complete read-only generation.");
        }
        return projection;
    }
}
