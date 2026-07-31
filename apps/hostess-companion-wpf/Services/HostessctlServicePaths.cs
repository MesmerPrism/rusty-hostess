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
                "rusty.hostess.external_python_runtime.v1" ||
            root.GetProperty("version").GetString() is not { } version ||
            root.GetProperty("executable_sha256").GetString() is not { } expectedHash ||
            version is not "3.12.10" ||
            expectedHash.Length != 64)
        {
            throw new InvalidDataException("Bundled Python runtime contract is invalid.");
        }
        var where = Process.Start(new ProcessStartInfo
        {
            FileName = "where.exe",
            Arguments = "python.exe",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException("Could not resolve Python.");
        var candidates = where.StandardOutput.ReadToEnd()
            .Split(Environment.NewLine, StringSplitOptions.RemoveEmptyEntries);
        where.WaitForExit();
        if (where.ExitCode != 0)
        {
            throw new InvalidOperationException("Supported Python interpreter is absent.");
        }
        var expectedHashBytes = Convert.FromHexString(expectedHash);
        var authorized = candidates.Where(candidate =>
        {
            try
            {
                return CryptographicOperations.FixedTimeEquals(
                    SHA256.HashData(File.ReadAllBytes(candidate)),
                    expectedHashBytes);
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
        }).Distinct(
                    StringComparer.OrdinalIgnoreCase).ToArray();
        if (authorized.Length != 1)
        {
            throw new InvalidDataException(
                "Exactly one hash-authorized Python interpreter is required.");
        }
        var probe = Process.Start(new ProcessStartInfo
        {
            FileName = authorized[0],
            Arguments = "-c \"import sys;print('.'.join(map(str,sys.version_info[:3])))\"",
            UseShellExecute = false,
            RedirectStandardOutput = true,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException("Could not probe Python.");
        var observedVersion = probe.StandardOutput.ReadToEnd().Trim();
        probe.WaitForExit();
        if (probe.ExitCode != 0 || observedVersion != version)
        {
            throw new InvalidDataException("Python interpreter version is not authorized.");
        }
        return authorized[0];
    }
}
