using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class SessionArtifactViewModel : IOperatorDetailRow
{
    public SessionArtifactViewModel(SessionArtifactRef artifact, string previewText)
    {
        ArtifactId = artifact.ArtifactId;
        Role = artifact.Role;
        Path = artifact.Path;
        Schema = artifact.Schema;
        ValidationStatus = string.IsNullOrWhiteSpace(artifact.ValidationStatus)
            ? "unknown"
            : artifact.ValidationStatus;
        PreviewText = previewText;
    }

    public string ArtifactId { get; }

    public string Role { get; }

    public string Path { get; }

    public string Schema { get; }

    public string ValidationStatus { get; }

    public string PreviewText { get; }

    public string Title => string.IsNullOrWhiteSpace(Role) ? ArtifactId : Role;

    public string StatusLine => $"{ValidationStatus} / {Schema}";

    public string DetailText =>
        $"Artifact: {ArtifactId}{Environment.NewLine}" +
        $"Role: {Role}{Environment.NewLine}" +
        $"Schema: {Schema}{Environment.NewLine}" +
        $"Validation: {ValidationStatus}{Environment.NewLine}" +
        $"Path: {Path}{Environment.NewLine}{Environment.NewLine}" +
        PreviewText;

    public Brush StatusBrush => ValidationStatus switch
    {
        "fail" => Brushes.Firebrick,
        "warn" => Brushes.DarkGoldenrod,
        "pass" or "generated" => Brushes.DarkGreen,
        _ => Brushes.DimGray,
    };
}
