using System.IO;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class SessionHistoryEntryViewModel
{
    public SessionHistoryEntryViewModel(CompanionSessionReport report)
    {
        Report = report;
        SessionId = string.IsNullOrWhiteSpace(report.SessionId)
            ? Path.GetFileNameWithoutExtension(report.ReportPath)
            : report.SessionId;
        Status = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status;
        Profile = report.Profile;
        ReportPath = report.ReportPath;
        StartedAt = report.StartedAtMs > 0
            ? DateTimeOffset.FromUnixTimeMilliseconds(report.StartedAtMs).LocalDateTime
            : report.ReportLastWriteTimeLocal;
    }

    public CompanionSessionReport Report { get; }

    public string SessionId { get; }

    public string Status { get; }

    public string Profile { get; }

    public string ReportPath { get; }

    public DateTime StartedAt { get; }

    public string StartedAtLabel => StartedAt.ToString("yyyy-MM-dd HH:mm:ss");

    public int PhaseCount => Report.Summary.PhaseCount;

    public int ArtifactCount => Report.Summary.ArtifactCount;

    public int IssueCount => Report.Summary.IssueCount;

    public string SummaryLine => $"{Status} / {PhaseCount} phases / {ArtifactCount} artifacts / {IssueCount} issues";

    public Brush StatusBrush => Status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "pass" => Brushes.DarkGreen,
        _ => Brushes.DimGray,
    };
}
