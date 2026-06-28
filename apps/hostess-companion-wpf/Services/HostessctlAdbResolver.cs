using System.IO;

namespace HostessCompanion.Wpf.Services;

internal static class HostessctlAdbResolver
{
    public static string ResolveAdb()
    {
        foreach (var variable in new[] { "ANDROID_HOME", "ANDROID_SDK_ROOT" })
        {
            var root = Environment.GetEnvironmentVariable(variable);
            if (string.IsNullOrWhiteSpace(root))
            {
                continue;
            }
            var candidate = Path.Combine(root, "platform-tools", "adb.exe");
            if (File.Exists(candidate))
            {
                return candidate;
            }
        }

        const string bundledAdb = @"S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe";
        return File.Exists(bundledAdb) ? bundledAdb : "adb";
    }
}
