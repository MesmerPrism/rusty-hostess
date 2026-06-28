using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public sealed class TransportsPageViewModel : OperatorPageViewModel<TransportViewModel>
{
    public TransportsPageViewModel()
        : base("No transport selected")
    {
    }

    public void ApplyCatalog(CompanionCatalog catalog) =>
        ReplaceRows(catalog.Transports.Select(transport => new TransportViewModel(transport)));

    public void ApplyDeviceLink(DeviceLinkReport report) =>
        ReplaceRows(
            DeviceLinkOperatorProjection.BuildTransportDescriptors(report)
                .Select(transport => new TransportViewModel(transport)));
}
