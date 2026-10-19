using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class CommandsPageViewModel : OperatorPageViewModel<CommandStageViewModel>
{
    public CommandsPageViewModel()
        : base("No command stage selected")
    {
    }

    public void ApplyExecution(BridgeCommandExecution execution)
    {
        var rows = execution.StageObservations
            .Select(stage => new CommandStageViewModel(stage))
            .ToList();
        rows.AddRange(execution.Issues.Select(issue => new CommandStageViewModel(new CommandStageObservation
        {
            Stage = issue.IssueCode,
            Status = "fail",
            ObservedAtMs = 0,
            EvidenceRefs = [issue.Message],
            IssueCodes = [issue.IssueCode],
        })));
        ReplaceRows(rows);
    }

    public void ApplyShellRecenterProjection(CompanionReportProjection projection)
    {
        ReplaceRows(projection.Rows.Where(row => row.Kind == "shell_recenter").Select(row =>
            new CommandStageViewModel(new CommandStageObservation
            {
                Stage = row.Label,
                Status = row.Status,
                EvidenceRefs = [row.Evidence, row.Notes, row.Details.GetRawText()],
                IssueCodes = row.IssueCodes,
            })));
    }

    public void ApplyFailure(Exception ex)
    {
        ReplaceRows(
        [
            new CommandStageViewModel(new CommandStageObservation
            {
                Stage = "wpf_command",
                Status = "fail",
                ObservedAtMs = 0,
                EvidenceRefs = [ex.Message],
                IssueCodes = ["hostess.issue.wpf.command_failed"],
            }),
        ]);
    }
}
