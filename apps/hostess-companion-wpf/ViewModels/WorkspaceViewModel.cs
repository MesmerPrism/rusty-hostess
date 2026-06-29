using System.Windows.Media;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class WorkspaceViewModel : IOperatorDetailRow
{
    public WorkspaceViewModel(
        CompanionWorkspaceDescriptor workspace,
        IReadOnlyDictionary<string, CompanionModuleDescriptor> modulesById)
    {
        WorkspaceId = workspace.WorkspaceId;
        Title = workspace.Title;
        SupportedFrontends = Join(workspace.SupportedFrontends);
        RequiredCount = workspace.Modules.Count(module => module.Required);
        OptionalCount = workspace.Modules.Count(module => !module.Required);
        ProminentCount = workspace.Modules.Count(module => module.Prominent);
        HiddenCount = workspace.Modules.Count(module => !module.Prominent);
        ModuleCount = workspace.Modules.Count;
        Sensitivity = Join(workspace.Sensitivity);
        SourcePath = workspace.SourcePath;
        ModuleSummary = workspace.Modules.Count == 0
            ? "none"
            : string.Join(
                Environment.NewLine,
                workspace.Modules.Select(module => ModuleLine(module, modulesById)));
    }

    public string WorkspaceId { get; }

    public string Title { get; }

    public string SupportedFrontends { get; }

    public int RequiredCount { get; }

    public int OptionalCount { get; }

    public int ProminentCount { get; }

    public int HiddenCount { get; }

    public int ModuleCount { get; }

    public string Sensitivity { get; }

    public string SourcePath { get; }

    public string ModuleSummary { get; }

    public string StatusLine =>
        $"{RequiredCount} required / {OptionalCount} optional / {ProminentCount} prominent";

    public string DetailText =>
        $"Workspace: {WorkspaceId}{Environment.NewLine}" +
        $"Supported frontends: {SupportedFrontends}{Environment.NewLine}" +
        $"Sensitivity: {(string.IsNullOrWhiteSpace(Sensitivity) ? "none" : Sensitivity)}{Environment.NewLine}" +
        $"Source: {SourcePath}{Environment.NewLine}{Environment.NewLine}" +
        $"Modules:{Environment.NewLine}{ModuleSummary}";

    public Brush StatusBrush => Brushes.DarkSlateGray;

    private static string ModuleLine(
        WorkspaceModuleSelection module,
        IReadOnlyDictionary<string, CompanionModuleDescriptor> modulesById)
    {
        var title = modulesById.TryGetValue(module.ModuleId, out var descriptor)
            ? descriptor.Title
            : "unresolved descriptor";
        var required = module.Required ? "required" : "optional";
        var prominence = module.Prominent ? "prominent" : "background";
        return $"{module.ModuleId} ({title}) - {required}, {prominence}";
    }

    private static string Join(IEnumerable<string> values) => string.Join(", ", values);
}
