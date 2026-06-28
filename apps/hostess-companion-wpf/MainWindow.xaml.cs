using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

namespace HostessCompanion.Wpf;

public partial class MainWindow
{
    public MainWindow()
    {
        InitializeComponent();
        DataContext = new MainWindowViewModel(
            new HostessctlReadinessService(),
            new HostessctlCatalogService(),
            new HostessctlCommandService(),
            new HostessctlSessionService(),
            new HostessctlConnectivityService());
    }
}
