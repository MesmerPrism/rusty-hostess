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
        var issuesByWorkspace = catalog.Issues
            .Where(issue => !string.IsNullOrWhiteSpace(issue.WorkspaceId))
            .GroupBy(issue => issue.WorkspaceId, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(group => group.Key, group => group.ToList(), StringComparer.OrdinalIgnoreCase);
        ReplaceRows(
            catalog.Workspaces.Select(workspace =>
            {
                issuesByWorkspace.TryGetValue(workspace.WorkspaceId, out var issues);
                return new WorkspaceViewModel(workspace, modulesById, issues);
            }));
    }
}
