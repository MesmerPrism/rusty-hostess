using System.Text.Json;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class ConnectivityCheckViewModel : IOperatorDetailRow
{
    private static readonly JsonSerializerOptions DetailJsonOptions = new() { WriteIndented = true };

    public ConnectivityCheckViewModel(ConnectivityCheck check)
    {
        Name = check.Name;
        Status = check.Status;
        Evidence = check.Evidence;
        Notes = check.Notes;
        IssueCodes = check.IssueCodes.Count == 0 ? "" : string.Join(", ", check.IssueCodes);
        Observed = check.Observed.ValueKind == JsonValueKind.Undefined
            ? ""
            : JsonSerializer.Serialize(check.Observed, DetailJsonOptions);
    }

    public string Name { get; }

    public string Title => Name;

    public string Status { get; }

    public string Evidence { get; }

    public string Notes { get; }

    public string IssueCodes { get; }

    public string Observed { get; }

    public string StatusLine => string.IsNullOrWhiteSpace(IssueCodes)
        ? Status
        : $"{Status} / {IssueCodes}";

    public string DetailText =>
        $"Check: {Name}{Environment.NewLine}" +
        $"Status: {Status}{Environment.NewLine}" +
        $"Evidence: {Evidence}{Environment.NewLine}" +
        $"Notes: {Notes}{Environment.NewLine}" +
        $"Issues: {(string.IsNullOrWhiteSpace(IssueCodes) ? "none" : IssueCodes)}{Environment.NewLine}" +
        $"Observed:{Environment.NewLine}{Observed}";

    public Brush StatusBrush => Status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "blocked" => Brushes.Firebrick,
        "rejected" => Brushes.Firebrick,
        "usable_with_warnings" => Brushes.DarkGoldenrod,
        "missing" => Brushes.DarkGoldenrod,
        "skipped" => Brushes.DimGray,
        "planned" => Brushes.DimGray,
        "candidate" => Brushes.DimGray,
        "usable" => Brushes.DarkGreen,
        "satisfied" => Brushes.DarkGreen,
        "pass" => Brushes.DarkGreen,
        _ => Brushes.DarkGreen,
    };
}
