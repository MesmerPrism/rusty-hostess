using System.IO;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

internal static class PromotedDirectWifiTopologySelector
{
    public static FileInfo? Select(
        DirectoryInfo repoRoot,
        ConnectivityProtocolEvidenceMatrix matrix,
        IReadOnlyList<FileInfo> topologyReports)
    {
        foreach (var candidate in ConnectivityReportSelectorSupport.CandidateReports(
            repoRoot,
            matrix,
            topologyReports))
        {
            if (IsPromotedDirectWifiTopologyReport(candidate))
            {
                return candidate;
            }
        }
        return null;
    }

    private static bool IsPromotedDirectWifiTopologyReport(FileInfo reportPath)
    {
        return ConnectivityReportSelectorSupport.ReportMatches(
            reportPath,
            root =>
            {
                var probeId = ConnectivityReportSelectorSupport.JsonString(root, "probe_id").ToUpperInvariant();
                if (probeId is not ("QCL-040" or "QCL-041"))
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

                return ConnectivityReportSelectorSupport.JsonObjectContainsToken(root, "topology", "wifi_direct")
                    || ConnectivityReportSelectorSupport.JsonObjectContainsToken(root, "transport", "wifi_direct");
            });
    }
}
