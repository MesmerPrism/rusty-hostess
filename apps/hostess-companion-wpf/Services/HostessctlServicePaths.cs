using System.IO;
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

namespace HostessCompanion.Wpf.Services;

internal static class HostessctlServicePaths
{
    public static DirectoryInfo LocateRepoRoot()
    {
        var bundleSource = Path.GetFullPath(Path.Combine(
            AppContext.BaseDirectory,
            "..",
            "source"));
        if (File.Exists(Path.Combine(
                bundleSource,
                "tools",
                "hostessctl",
                "hostessctl.py")))
        {
            return new DirectoryInfo(bundleSource);
        }
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

    public static string ResolvePythonExecutable(DirectoryInfo sourceRoot)
    {
        var contractPath = Path.GetFullPath(Path.Combine(
            sourceRoot.FullName,
            "..",
            "runtime",
            "python-runtime.json"));
        if (!File.Exists(contractPath))
        {
            return "python";
        }
        using var document = JsonDocument.Parse(File.ReadAllBytes(contractPath));
        var root = document.RootElement;
        if (root.GetProperty("schema").GetString() is not
                "rusty.hostess.bundled_python_runtime.v1" ||
            root.GetProperty("bundled").GetBoolean() is not true ||
            root.GetProperty("version").GetString() is not { } version ||
            root.GetProperty("executable_path").GetString() is not { } executablePath ||
            root.GetProperty("executable_sha256").GetString() is not { } expectedHash ||
            version is not "3.12.10" ||
            expectedHash.Length != 64)
        {
            throw new InvalidDataException("Bundled Python runtime contract is invalid.");
        }
        var productRoot = sourceRoot.Parent
            ?? throw new InvalidDataException("Bundled product root is absent.");
        var runtimeRoot = Path.GetFullPath(Path.Combine(productRoot.FullName, "runtime"));
        var runtimePrefix = runtimeRoot + Path.DirectorySeparatorChar;
        var python = Path.GetFullPath(Path.Combine(
            productRoot.FullName,
            executablePath.Replace('/', Path.DirectorySeparatorChar)));
        if (!python.StartsWith(runtimePrefix, StringComparison.OrdinalIgnoreCase) ||
            !File.Exists(python))
        {
            throw new InvalidDataException(
                "Bundled Python runtime is absent or escapes the product runtime root.");
        }
        var expectedHashBytes = Convert.FromHexString(expectedHash);
        if (!CryptographicOperations.FixedTimeEquals(
                SHA256.HashData(File.ReadAllBytes(python)),
                expectedHashBytes))
        {
            throw new InvalidDataException("Bundled Python runtime hash is not authorized.");
        }

        var probeInfo = new ProcessStartInfo
        {
            FileName = python,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true,
        };
        probeInfo.ArgumentList.Add("-I");
        probeInfo.ArgumentList.Add("-c");
        probeInfo.ArgumentList.Add("import sys;print('.'.join(map(str,sys.version_info[:3])))");
        using var probe = Process.Start(probeInfo)
            ?? throw new InvalidOperationException("Could not probe bundled Python.");
        var observedVersion = probe.StandardOutput.ReadToEnd().Trim();
        var probeError = probe.StandardError.ReadToEnd().Trim();
        probe.WaitForExit();
        if (probe.ExitCode != 0 || observedVersion != version)
        {
            throw new InvalidDataException(
                $"Bundled Python interpreter version is not authorized: {probeError}");
        }
        return python;
    }
}
