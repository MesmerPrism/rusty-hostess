using System.Windows;
using HostessCompanion.Wpf.Services;

namespace HostessCompanion.Wpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (Qcl080UdpListenerMode.IsListenerMode(e.Args))
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            var exitCode = Qcl080UdpListenerMode.Run(e.Args);
            Shutdown(exitCode);
            return;
        }

        base.OnStartup(e);
        MainWindow = new MainWindow();
        MainWindow.Show();
    }
}
