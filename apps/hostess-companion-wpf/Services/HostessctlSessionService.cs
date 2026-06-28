using System.Diagnostics;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlSessionService
{
    private const string SessionSchema = "rusty.hostess.companion.session.v1";
    private const int ArtifactPreviewMaxChars = 20000;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<IReadOnlyList<CompanionSessionReport>> LoadHistoryAsync(
        CancellationToken cancellationToken)
    {
        var directory = SessionDirectory();
        if (!directory.Exists)
        {
            return [];
        }

        var reports = new List<CompanionSessionReport>();
        foreach (var file in directory.EnumerateFiles("*.json"))
        {
            cancellationToken.ThrowIfCancellationRequested();
            var report = await TryLoadSessionAsync(file, cancellationToken).ConfigureAwait(false);
            if (report is not null)
            {
                reports.Add(report);
            }
        }

        return reports
            .OrderByDescending(report => report.ReportLastWriteTimeLocal)
            .ThenByDescending(report => report.StartedAtMs)
            .Take(25)
            .ToList();
    }

    public async Task<CompanionSessionReport> LoadSessionAsync(
        string reportPath,
        CancellationToken cancellationToken)
    {
        var file = ResolveReportPath(reportPath);
        var report = await TryLoadSessionAsync(file, cancellationToken).ConfigureAwait(false);
        return report ?? throw new InvalidOperationException($"Not a companion session report: {file.FullName}");
    }

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
        var sessionStamp = DateTimeOffset.Now.ToString("yyyyMMdd-HHmmss");
        var sessionId = $"wpf-session-{sessionStamp}";
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-session",
            $"{sessionId}.json"));
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
        startInfo.ArgumentList.Add("--session-id");
        startInfo.ArgumentList.Add(sessionId);
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
        var report = await JsonSerializer.DeserializeAsync<CompanionSessionReport>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException("Companion session report was empty.");
        AttachReportMetadata(report, reportPath);
        return report;
    }

    public string ReadArtifactPreview(SessionArtifactRef artifact)
    {
        if (string.IsNullOrWhiteSpace(artifact.Path))
        {
            return "Artifact path is empty.";
        }

        var file = ResolveReportPath(artifact.Path);
        if (!file.Exists)
        {
            return $"Artifact file is missing: {file.FullName}";
        }

        var text = File.ReadAllText(file.FullName);
        if (text.Length <= ArtifactPreviewMaxChars)
        {
            return text;
        }

        return text[..ArtifactPreviewMaxChars] +
            $"{Environment.NewLine}{Environment.NewLine}[truncated at {ArtifactPreviewMaxChars} characters]";
    }

    public DeviceLinkReport? TryReadDeviceLinkReport(CompanionSessionReport session)
    {
        var artifact = session.ArtifactRefs.FirstOrDefault(
            row => string.Equals(row.Role, "device_link_report", StringComparison.OrdinalIgnoreCase)
                || string.Equals(row.Schema, "rusty.quest.device_link.v1", StringComparison.OrdinalIgnoreCase));
        if (artifact is null || string.IsNullOrWhiteSpace(artifact.Path))
        {
            return null;
        }

        var file = ResolveReportPath(artifact.Path);
        if (!file.Exists)
        {
            return null;
        }

        try
        {
            using var stream = File.OpenRead(file.FullName);
            return JsonSerializer.Deserialize<DeviceLinkReport>(stream, JsonOptions);
        }
        catch (JsonException)
        {
            return null;
        }
        catch (IOException)
        {
            return null;
        }
    }

    private static DirectoryInfo SessionDirectory()
    {
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        return new DirectoryInfo(Path.Combine(repoRoot.FullName, "target", "companion-session"));
    }

    private static FileInfo ResolveReportPath(string path)
    {
        if (Path.IsPathFullyQualified(path))
        {
            return new FileInfo(path);
        }

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        return new FileInfo(Path.Combine(repoRoot.FullName, path));
    }

    private static async Task<CompanionSessionReport?> TryLoadSessionAsync(
        FileInfo file,
        CancellationToken cancellationToken)
    {
        try
        {
            await using var stream = File.OpenRead(file.FullName);
            var report = await JsonSerializer.DeserializeAsync<CompanionSessionReport>(
                    stream,
                    JsonOptions,
                    cancellationToken)
                .ConfigureAwait(false);
            if (report?.Schema != SessionSchema)
            {
                return null;
            }

            AttachReportMetadata(report, file);
            return report;
        }
        catch (JsonException)
        {
            return null;
        }
        catch (IOException)
        {
            return null;
        }
    }

    private static void AttachReportMetadata(CompanionSessionReport report, FileInfo file)
    {
        report.ReportPath = file.FullName;
        report.ReportLastWriteTimeLocal = file.Exists
            ? file.LastWriteTime
            : DateTime.Now;
    }
}
