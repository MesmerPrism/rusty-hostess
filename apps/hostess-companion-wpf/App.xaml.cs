using System.Windows;
using System.Text.Json;
using System.IO;
using HostessCompanion.Wpf.Services;

namespace HostessCompanion.Wpf;

public partial class App : Application
{
    protected override void OnStartup(StartupEventArgs e)
    {
        if (e.Args is ["--bundle-smoke"])
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            try
            {
                var readiness = new HostessctlReadinessService()
                    .RefreshAsync("", false, false, CancellationToken.None)
                    .GetAwaiter().GetResult();
                var catalog = new HostessctlCatalogService()
                    .RefreshAsync(CancellationToken.None).GetAwaiter().GetResult();
                var localAppData = Environment.GetEnvironmentVariable("LOCALAPPDATA");
                if (string.IsNullOrWhiteSpace(localAppData) ||
                    !Path.IsPathFullyQualified(localAppData))
                {
                    throw new InvalidOperationException("LOCALAPPDATA is unavailable.");
                }
                var reportRoot = Path.Combine(
                    localAppData, "RustyHostessAlpha", "reports");
                Directory.CreateDirectory(reportRoot);
                File.WriteAllText(
                    Path.Combine(reportRoot, "bundle-smoke.json"),
                    JsonSerializer.Serialize(new
                    {
                        schema = "rusty.hostess.bundle_smoke.v1",
                        readiness_loaded = readiness is not null,
                        catalog_loaded = catalog is not null,
                    }));
                Shutdown(0);
            }
            catch (Exception exception)
            {
                Console.Error.WriteLine(exception);
                Shutdown(1);
            }
            return;
        }
        if (Qcl080UdpListenerMode.IsListenerMode(e.Args))
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            var exitCode = Qcl080UdpListenerMode.Run(e.Args);
            Shutdown(exitCode);
            return;
        }
        if (Qcl010TcpEchoListenerMode.IsListenerMode(e.Args))
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            var exitCode = Qcl010TcpEchoListenerMode.Run(e.Args);
            Shutdown(exitCode);
            return;
        }
        if (Qcl082Rmanvid1TcpReceiverMode.IsReceiverMode(e.Args))
        {
            ShutdownMode = ShutdownMode.OnExplicitShutdown;
            var exitCode = Qcl082Rmanvid1TcpReceiverMode.Run(e.Args);
            Shutdown(exitCode);
            return;
        }

        base.OnStartup(e);
        MainWindow = new MainWindow();
        MainWindow.Show();
    }
}
