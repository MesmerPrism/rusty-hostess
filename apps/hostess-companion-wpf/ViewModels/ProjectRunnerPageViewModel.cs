using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class ProjectRunnerPageViewModel : OperatorPageViewModel<ProjectRunnerRowViewModel>
{
    public ProjectRunnerPageViewModel()
        : base("No project-runner row selected")
    {
    }

    public void ApplyProjection(ProjectRunnerProjection projection)
    {
        ReplaceRows(projection.Rows.Select(row => new ProjectRunnerRowViewModel(projection, row)));
    }
}
