using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class WorkspacesPageViewModel : OperatorPageViewModel<WorkspaceViewModel>
{
    public WorkspacesPageViewModel()
        : base("No workspace selected")
    {
    }

    public void ApplyCatalog(CompanionCatalog catalog)
    {
        var modulesById = catalog.Modules
            .GroupBy(module => module.ModuleId, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(group => group.Key, group => group.First(), StringComparer.OrdinalIgnoreCase);
        ReplaceRows(catalog.Workspaces.Select(workspace => new WorkspaceViewModel(workspace, modulesById)));
    }
}
