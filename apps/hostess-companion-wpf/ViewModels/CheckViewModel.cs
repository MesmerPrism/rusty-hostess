using System.Text.Json;
using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class CheckViewModel : IOperatorDetailRow
{
    private static readonly JsonSerializerOptions DetailJsonOptions = new() { WriteIndented = true };

    public CheckViewModel(ReadinessCheck check)
    {
        CheckId = check.CheckId;
        Group = check.Group;
        Title = check.Title;
        Status = check.Status;
        Required = check.Required;
        Severity = check.Severity;
        Evidence = check.Evidence;
        IssueCodes = check.IssueCodes.Count == 0 ? "" : string.Join(", ", check.IssueCodes);
        Observed = check.Observed.ValueKind == JsonValueKind.Undefined
            ? ""
            : JsonSerializer.Serialize(check.Observed, DetailJsonOptions);
    }

    public string CheckId { get; }

    public string Group { get; }

    public string Title { get; }

    public string Status { get; }

    public bool Required { get; }

    public string Severity { get; }

    public string Evidence { get; }

    public string IssueCodes { get; }

    public string Observed { get; }

    public string StatusLine => $"{Status} / {Severity}";

    public string DetailText =>
        $"Id: {CheckId}{Environment.NewLine}" +
        $"Group: {Group}{Environment.NewLine}" +
        $"Required: {Required}{Environment.NewLine}" +
        $"Evidence: {Evidence}{Environment.NewLine}" +
        $"Issues: {(string.IsNullOrWhiteSpace(IssueCodes) ? "none" : IssueCodes)}{Environment.NewLine}" +
        $"Observed:{Environment.NewLine}{Observed}";

    public Brush StatusBrush => Status switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "skipped" => Brushes.DimGray,
        _ => Brushes.DarkGreen,
    };
}
