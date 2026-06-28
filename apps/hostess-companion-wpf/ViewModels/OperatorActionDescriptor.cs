namespace HostessCompanion.Wpf.ViewModels;

public sealed record OperatorActionDescriptor(
    string ActionId,
    string Title,
    string UiCommandProperty,
    string CliRoute,
    string EvidenceArtifact,
    string AuthorityOwner,
    string TestCoverage);
