using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class ConnectivityPageViewModel : OperatorPageViewModel<ConnectivityCheckViewModel>
{
    public ConnectivityPageViewModel()
        : base("No connectivity check selected")
    {
    }

    public void ApplyRows(IReadOnlyList<ConnectivityCheck> rows) =>
        ReplaceRows(rows.Select(row => new ConnectivityCheckViewModel(row)));

    public void ApplyFailure(string checkName, Exception ex) =>
        ApplyRows(ConnectivityRows.Failure(checkName, ex));
}
