using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

internal static class Qcl082ProductMediaReportSelector
{
    public static FileInfo? Select(
        DirectoryInfo repoRoot,
        ConnectivityProtocolEvidenceMatrix matrix)
    {
        foreach (var candidate in ConnectivityReportSelectorSupport.CandidateReports(
            repoRoot,
            matrix,
            DefaultCandidateReports(repoRoot)))
        {
            if (IsPromotedProductMediaReport(candidate))
            {
                return candidate;
            }
        }
        return null;
    }

    private static IEnumerable<FileInfo> DefaultCandidateReports(DirectoryInfo repoRoot)
    {
        var reports = new List<FileInfo>
        {
            new(Path.Combine(
                repoRoot.FullName,
                "target",
                "connectivity-probe",
                "qcl082-rmanvid1-receiver-capture.json")),
        };

        var latestArtifactOverride = Environment.GetEnvironmentVariable(
            HostessctlConnectivityService.LatestArtifactDirEnvironmentVariable);
        if (!string.IsNullOrWhiteSpace(latestArtifactOverride))
        {
            var latestArtifactTarget = new DirectoryInfo(Path.GetFullPath(
                latestArtifactOverride.Trim(),
                repoRoot.FullName));
            if (latestArtifactTarget.Exists)
            {
                reports.AddRange(
                    latestArtifactTarget
                        .EnumerateFiles("qcl082-product-media-live-qcl082.json", SearchOption.AllDirectories)
                        .OrderByDescending(report => report.LastWriteTimeUtc));
                reports.AddRange(
                    latestArtifactTarget
                        .EnumerateFiles("qcl082-rmanvid1-receiver-capture.json", SearchOption.AllDirectories)
                        .OrderByDescending(report => report.LastWriteTimeUtc));
            }
        }

        return reports;
    }

    private static bool IsPromotedProductMediaReport(FileInfo reportPath)
    {
        return ConnectivityReportSelectorSupport.ReportMatches(
            reportPath,
            root =>
            {
                if (!ConnectivityReportSelectorSupport.JsonString(root, "probe_id")
                    .Equals("QCL-082", StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
                if (!ConnectivityReportSelectorSupport.JsonString(root, "status")
                    .Equals("pass", StringComparison.OrdinalIgnoreCase))
                {
                    return false;
                }
                if (!ConnectivityReportSelectorSupport.JsonBoolObject(root, "promotion", "allowed"))
                {
                    return false;
                }

                var measurements = ConnectivityReportSelectorSupport.ObjectProperty(root, "measurements");
                var capture = ConnectivityReportSelectorSupport.ObjectProperty(root, "media_stream_receiver_capture");
                var source = ConnectivityReportSelectorSupport.ObjectProperty(capture, "source");
                var productTopology = ConnectivityReportSelectorSupport.ObjectProperty(capture, "product_topology");
                var productFirewall = ConnectivityReportSelectorSupport.ObjectProperty(capture, "product_listener_firewall");
                var captureKind = ConnectivityReportSelectorSupport.JsonString(capture, "capture_kind");
                var liveCapture = JsonBool(capture, "live_capture")
                    || captureKind is "live_broker_stream" or "live_quest_runtime_stream";
                var topologyReady = JsonBool(measurements, "media_product_topology_ready")
                    || JsonBool(productTopology, "ready");
                var firewallReady = JsonBool(measurements, "media_product_listener_firewall_verified")
                    || JsonBool(productFirewall, "ready");

                return liveCapture
                    && JsonBool(source, "broker_or_quest_source")
                    && topologyReady
                    && firewallReady;
            });
    }

    private static bool JsonBool(JsonElement element, string propertyName) =>
        element.ValueKind == JsonValueKind.Object
        && element.TryGetProperty(propertyName, out var value)
        && value.ValueKind == JsonValueKind.True;
}
