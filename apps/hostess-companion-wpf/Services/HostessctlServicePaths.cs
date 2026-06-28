using System.IO;

namespace HostessCompanion.Wpf.Services;

internal static class HostessctlServicePaths
{
    public static DirectoryInfo LocateRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "tools", "hostessctl", "hostessctl.py")))
            {
                return current;
            }
            current = current.Parent;
        }
        throw new InvalidOperationException("Could not locate rusty-hostess repository root.");
    }
}
