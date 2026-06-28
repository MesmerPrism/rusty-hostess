using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class ReadinessPageViewModel : OperatorPageViewModel<CheckViewModel>
{
    public ReadinessPageViewModel()
        : base("No readiness check selected")
    {
    }

    public void ApplyReport(ReadinessReport report) =>
        ReplaceRows(report.Checks.Select(check => new CheckViewModel(check)));

    public void ApplyFailure(Exception ex)
    {
        ReplaceRows(
        [
            new CheckViewModel(new ReadinessCheck
            {
                CheckId = "check.wpf.refresh",
                Group = "wpf",
                Title = "Companion refresh",
                Status = "fail",
                Severity = "error",
                Required = true,
                Evidence = ex.Message,
            }),
        ]);
    }
}
