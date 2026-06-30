using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

internal static class ConnectivityReportSelectorSupport
{
    public static IEnumerable<FileInfo> CandidateReports(
        DirectoryInfo repoRoot,
        ConnectivityProtocolEvidenceMatrix matrix,
        IEnumerable<FileInfo> extraReports)
    {
        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var input in matrix.Inputs)
        {
            if (string.IsNullOrWhiteSpace(input.Path))
            {
                continue;
            }
            var report = ResolveReportPath(repoRoot, input.Path);
            if (seen.Add(report.FullName))
            {
                yield return report;
            }
        }

        foreach (var report in extraReports)
        {
            if (seen.Add(report.FullName))
            {
                yield return report;
            }
        }
    }

    public static bool ReportMatches(FileInfo reportPath, Func<JsonElement, bool> predicate)
    {
        if (!reportPath.Exists)
        {
            return false;
        }

        try
        {
            using var document = JsonDocument.Parse(File.ReadAllText(reportPath.FullName));
            return predicate(document.RootElement);
        }
        catch (JsonException)
        {
            return false;
        }
        catch (IOException)
        {
            return false;
        }
        catch (UnauthorizedAccessException)
        {
            return false;
        }
    }

    public static string JsonString(JsonElement element, string propertyName) =>
        element.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : string.Empty;

    public static bool JsonBoolObject(JsonElement root, string objectName, string propertyName) =>
        root.TryGetProperty(objectName, out var container)
        && container.ValueKind == JsonValueKind.Object
        && container.TryGetProperty(propertyName, out var value)
        && value.ValueKind == JsonValueKind.True;

    public static bool JsonObjectContainsToken(JsonElement root, string propertyName, string token)
    {
        if (!root.TryGetProperty(propertyName, out var container)
            || container.ValueKind != JsonValueKind.Object)
        {
            return false;
        }

        foreach (var property in container.EnumerateObject())
        {
            if (property.Value.ValueKind == JsonValueKind.String
                && JsonStringContainsToken(property.Value.GetString(), token))
            {
                return true;
            }
        }
        return false;
    }

    public static bool JsonStringContainsToken(string? value, string token) =>
        value?.Replace("-", "_", StringComparison.Ordinal)
            .Contains(token, StringComparison.OrdinalIgnoreCase) is true;

    public static JsonElement ObjectProperty(JsonElement root, string propertyName) =>
        root.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.Object
            ? value
            : default;

    private static FileInfo ResolveReportPath(DirectoryInfo repoRoot, string path)
    {
        var trimmed = path.Trim();
        if (Path.IsPathFullyQualified(trimmed))
        {
            return new FileInfo(trimmed);
        }
        return new FileInfo(Path.GetFullPath(Path.Combine(repoRoot.FullName, trimmed)));
    }
}
