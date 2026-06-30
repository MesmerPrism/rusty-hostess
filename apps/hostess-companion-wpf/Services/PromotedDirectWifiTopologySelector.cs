using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

internal static class PromotedDirectWifiTopologySelector
{
    public static FileInfo? Select(
        DirectoryInfo repoRoot,
        ConnectivityProtocolEvidenceMatrix matrix,
        IReadOnlyList<FileInfo> topologyReports)
    {
        var candidates = new List<FileInfo>();
        foreach (var input in matrix.Inputs)
        {
            if (string.IsNullOrWhiteSpace(input.Path))
            {
                continue;
            }
            candidates.Add(ResolveReportPath(repoRoot, input.Path));
        }
        candidates.AddRange(topologyReports);

        var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var candidate in candidates)
        {
            if (!seen.Add(candidate.FullName))
            {
                continue;
            }
            if (IsPromotedDirectWifiTopologyReport(candidate))
            {
                return candidate;
            }
        }
        return null;
    }

    private static FileInfo ResolveReportPath(DirectoryInfo repoRoot, string path)
    {
        var trimmed = path.Trim();
        if (Path.IsPathFullyQualified(trimmed))
        {
            return new FileInfo(trimmed);
        }
        return new FileInfo(Path.GetFullPath(Path.Combine(repoRoot.FullName, trimmed)));
    }

    private static bool IsPromotedDirectWifiTopologyReport(FileInfo reportPath)
    {
        if (!reportPath.Exists)
        {
            return false;
        }

        try
        {
            using var document = JsonDocument.Parse(File.ReadAllText(reportPath.FullName));
            var root = document.RootElement;
            var probeId = JsonString(root, "probe_id").ToUpperInvariant();
            if (probeId is not ("QCL-040" or "QCL-041"))
            {
                return false;
            }
            if (!JsonString(root, "status").Equals("pass", StringComparison.OrdinalIgnoreCase))
            {
                return false;
            }
            if (!root.TryGetProperty("promotion", out var promotion)
                || promotion.ValueKind != JsonValueKind.Object
                || !promotion.TryGetProperty("allowed", out var allowed)
                || allowed.ValueKind != JsonValueKind.True)
            {
                return false;
            }

            return JsonObjectContainsToken(root, "topology", "wifi_direct")
                || JsonObjectContainsToken(root, "transport", "wifi_direct");
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

    private static bool JsonObjectContainsToken(JsonElement root, string propertyName, string token)
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

    private static bool JsonStringContainsToken(string? value, string token) =>
        value?.Replace("-", "_", StringComparison.Ordinal)
            .Contains(token, StringComparison.OrdinalIgnoreCase) is true;

    private static string JsonString(JsonElement element, string propertyName) =>
        element.TryGetProperty(propertyName, out var value) && value.ValueKind == JsonValueKind.String
            ? value.GetString() ?? string.Empty
            : string.Empty;
}
