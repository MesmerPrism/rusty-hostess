using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class EvidencePageViewModel : OperatorPageViewModel<EvidenceArtifactViewModel>
{
    public EvidencePageViewModel()
        : base("No evidence artifact selected")
    {
    }

    public void ApplyCatalog(CompanionCatalog catalog) =>
        ReplaceRows(
            catalog.Modules.SelectMany(module =>
                module.EvidenceArtifacts.Select(artifact => new EvidenceArtifactViewModel(module, artifact))));
}
