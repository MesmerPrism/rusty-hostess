using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class ProjectRunnerRowViewModel : IOperatorDetailRow
{
    public ProjectRunnerRowViewModel(ProjectRunnerProjection projection, ProjectRunnerProjectionRow row)
    {
        RowId = row.RowId;
        Kind = row.Kind;
        Title = row.Title;
        Status = row.Status;
        Owner = row.Owner;
        Detail = row.Detail;
        RunId = projection.RunId;
        GenerationId = projection.GenerationId;
        CompletionMarker = projection.CompletionMarker;
    }

    public string RowId { get; }

    public string Kind { get; }

    public string Title { get; }

    public string Status { get; }

    public string Owner { get; }

    public string Detail { get; }

    public string RunId { get; }

    public string GenerationId { get; }

    public string CompletionMarker { get; }

    public string StatusLine => $"{Status} / {Kind} / {Owner}";

    public string DetailText =>
        $"Row: {RowId}{Environment.NewLine}" +
        $"Run: {RunId}{Environment.NewLine}" +
        $"Generation: {GenerationId}{Environment.NewLine}" +
        $"Owner: {Owner}{Environment.NewLine}" +
        $"Completion marker: {CompletionMarker}{Environment.NewLine}{Environment.NewLine}" +
        Detail;

    public Brush StatusBrush => Status switch
    {
        "pass" or "bound" => Brushes.DarkGreen,
        "required" => Brushes.DarkGoldenrod,
        _ => Brushes.DimGray,
    };
}
