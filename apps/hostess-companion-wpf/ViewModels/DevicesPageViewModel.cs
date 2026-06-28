using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class DevicesPageViewModel : OperatorPageViewModel<CheckViewModel>
{
    private static readonly HashSet<string> DeviceCheckGroups = ["device", "runtime", "network"];

    public DevicesPageViewModel()
        : base("No device check selected")
    {
    }

    public void ApplyReadiness(ReadinessReport report) =>
        ReplaceRows(
            report.Checks
                .Select(check => new CheckViewModel(check))
                .Where(row => DeviceCheckGroups.Contains(row.Group)));

    public void ApplyDeviceLink(DeviceLinkReport report) =>
        ReplaceRows(DeviceLinkOperatorProjection.BuildDeviceChecks(report).Select(check => new CheckViewModel(check)));
}
