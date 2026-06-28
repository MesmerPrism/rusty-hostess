using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class EvidenceArtifactViewModel : IOperatorDetailRow
{
    public EvidenceArtifactViewModel(CompanionModuleDescriptor module, EvidenceArtifactBinding artifact)
    {
        ModuleId = module.ModuleId;
        ModuleTitle = module.Title;
        ArtifactId = artifact.Id;
        Schema = artifact.Schema;
        OwnerLane = artifact.OwnerLane;
        RedactionRequired = artifact.RedactionRequired;
        SourcePath = module.SourcePath;
    }

    public string ModuleId { get; }

    public string ModuleTitle { get; }

    public string ArtifactId { get; }

    public string Title => ArtifactId;

    public string Schema { get; }

    public string OwnerLane { get; }

    public bool RedactionRequired { get; }

    public string SourcePath { get; }

    public string StatusLine => RedactionRequired ? $"{OwnerLane} / redaction required" : $"{OwnerLane} / displayable";

    public string DetailText =>
        $"Artifact: {ArtifactId}{Environment.NewLine}" +
        $"Schema: {Schema}{Environment.NewLine}" +
        $"Owner lane: {OwnerLane}{Environment.NewLine}" +
        $"Redaction required: {RedactionRequired}{Environment.NewLine}" +
        $"Module: {ModuleTitle} ({ModuleId}){Environment.NewLine}" +
        $"Source: {SourcePath}";

    public Brush StatusBrush => RedactionRequired ? Brushes.DarkGoldenrod : Brushes.DarkGreen;
}
