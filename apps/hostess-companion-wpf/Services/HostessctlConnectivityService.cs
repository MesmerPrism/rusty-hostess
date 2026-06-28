using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlConnectivityService
{
    private const int DefaultTcpPort = 18766;
    private const int DefaultUdpPort = 18767;
    private const string DefaultTcpRuleNamePrefix = "Rusty Hostess QCL-010 TCP Echo";
    private const string DefaultUdpRuleNamePrefix = "Rusty Hostess QCL-080 UDP Freshness";

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
    };

    public async Task<ConnectivityFirewallRuleReport> PlanFirewallRuleAsync(
        string program,
        string protocol,
        string portText,
        string profile,
        string remoteAddress,
        string ruleName,
        CancellationToken cancellationToken)
    {
        var selectedProtocol = NormalizeProtocol(protocol);
        var port = ParsePort(portText, DefaultPortForProtocol(selectedProtocol));
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            "wpf-firewall-rule-plan.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        var arguments = new List<string>
        {
            "connectivity-probe",
            "windows-firewall-rule",
            "--out",
            reportPath.FullName,
            "--port",
            port.ToString(CultureInfo.InvariantCulture),
            "--protocol",
            selectedProtocol,
            "--profile",
            string.IsNullOrWhiteSpace(profile) ? "Public" : profile.Trim(),
            "--remote-address",
            string.IsNullOrWhiteSpace(remoteAddress) ? "LocalSubnet" : remoteAddress.Trim(),
            "--rule-name",
            string.IsNullOrWhiteSpace(ruleName) ? DefaultRuleName(port, selectedProtocol) : ruleName.Trim(),
        };
        if (!string.IsNullOrWhiteSpace(program))
        {
            arguments.Add("--program");
            arguments.Add(program.Trim());
        }

        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivityFirewallRuleReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
    }

    public async Task<IReadOnlyList<ConnectivityCheck>> ApplyFirewallRuleAsync(
        ConnectivityFirewallRuleReport report,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(report.PowerShell.Script))
        {
            return
            [
                SyntheticCheck(
                    "host.windows_firewall_rule_apply",
                    "blocked",
                    "firewall rule plan did not include an apply script",
                    new { report.Rule.Name, report.Rule.LocalPort },
                    ["hostess.issue.connectivity_probe.firewall_rule_script_missing"]),
            ];
        }

        return
        [
            await RunElevatedPowerShellAsync(
                    "host.windows_firewall_rule_apply",
                    report.PowerShell.Script,
                    $"applied {report.Rule.Name} on {report.Rule.Protocol} {report.Rule.LocalPort}",
                    $"apply {report.Rule.Name}",
                    new
                    {
                        report.Rule.Name,
                        report.Rule.Program,
                        report.Rule.LocalPort,
                        Profiles = report.Rule.Profiles,
                        report.Rule.RemoteAddress,
                        report.PowerShell.RequiresAdmin,
                    },
                    cancellationToken)
                .ConfigureAwait(false),
        ];
    }

    public async Task<IReadOnlyList<ConnectivityCheck>> RemoveFirewallRuleAsync(
        string ruleName,
        string protocol,
        string portText,
        CancellationToken cancellationToken)
    {
        var selectedProtocol = NormalizeProtocol(protocol);
        var selectedRuleName = string.IsNullOrWhiteSpace(ruleName)
            ? DefaultRuleName(ParsePort(portText, DefaultPortForProtocol(selectedProtocol)), selectedProtocol)
            : ruleName.Trim();
        var script = string.Join(
            " ",
            [
                "$ErrorActionPreference = 'Stop';",
                $"$ruleName = {PowerShellString(selectedRuleName)};",
                "$rules = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue;",
                "if ($rules) { $rules | Remove-NetFirewallRule; }",
            ]);
        return
        [
            await RunElevatedPowerShellAsync(
                    "host.windows_firewall_rule_remove",
                    script,
                    $"removed {selectedRuleName} when present",
                    $"remove {selectedRuleName}",
                    new { Name = selectedRuleName, RequiresAdmin = true },
                    cancellationToken)
                .ConfigureAwait(false),
        ];
    }

    public async Task<ConnectivityProbeReport> RunFixedPortProbeAsync(
        string serial,
        string portText,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(serial))
        {
            throw new InvalidOperationException("A Quest serial is required for the connectivity probe.");
        }

        var port = ParsePort(portText, DefaultTcpPort);
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var stamp = DateTimeOffset.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        var runId = $"wpf-qcl010-fixed-port-{stamp}";
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        await RunHostessctlAsync(
                repoRoot,
                [
                    "connectivity-probe",
                    "run",
                    "--mode",
                    "live",
                    "--probe-id",
                    "QCL-010",
                    "--run-id",
                    runId,
                    "--out",
                    reportPath.FullName,
                    "--adb",
                    HostessctlAdbResolver.ResolveAdb(),
                    "--serial",
                    serial.Trim(),
                    "--tcp-echo-port",
                    port.ToString(CultureInfo.InvariantCulture),
                ],
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivityProbeReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
    }

    public async Task<ConnectivityStreamCapabilityRun> RunQcl080StreamCapabilityAsync(
        string serial,
        string portText,
        CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(serial))
        {
            throw new InvalidOperationException("A Quest serial is required for the UDP stream capability probe.");
        }

        var port = ParsePort(portText, DefaultUdpPort);
        var listenerProgram = DefaultProductProgramPath();
        if (string.IsNullOrWhiteSpace(listenerProgram) || !File.Exists(listenerProgram))
        {
            throw new InvalidOperationException(
                "The WPF UDP listener executable could not be resolved. Build HostessCompanion.Wpf first.");
        }

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var stamp = DateTimeOffset.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        var runId = $"wpf-qcl080-app-owned-{stamp}";
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}.json"));
        var descriptorPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}.stream-capability.json"));
        var validationPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}.stream-capability.validation-report.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        await RunHostessctlAsync(
                repoRoot,
                [
                    "connectivity-probe",
                    "run",
                    "--mode",
                    "live",
                    "--probe-id",
                    "QCL-080",
                    "--run-id",
                    runId,
                    "--out",
                    reportPath.FullName,
                    "--adb",
                    HostessctlAdbResolver.ResolveAdb(),
                    "--serial",
                    serial.Trim(),
                    "--udp-port",
                    port.ToString(CultureInfo.InvariantCulture),
                    "--udp-packet-count",
                    "24",
                    "--udp-interval-ms",
                    "20",
                    "--udp-timeout-seconds",
                    "8",
                    "--udp-sender-source",
                    "makepad-runtime",
                    "--udp-listener-helper",
                    listenerProgram,
                ],
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);

        await RunHostessctlAsync(
                repoRoot,
                [
                    "connectivity-probe",
                    "stream-capability",
                    "--input",
                    reportPath.FullName,
                    "--out",
                    descriptorPath.FullName,
                    "--validation-out",
                    validationPath.FullName,
                    "--fail-on-error",
                ],
                descriptorPath,
                cancellationToken)
            .ConfigureAwait(false);

        var report = await ReadReportAsync<ConnectivityProbeReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        var descriptor = await ReadReportAsync<ConnectivityStreamCapabilityDescriptor>(
                descriptorPath,
                cancellationToken)
            .ConfigureAwait(false);
        descriptor.DescriptorPath = descriptorPath.FullName;
        return new ConnectivityStreamCapabilityRun
        {
            Report = report,
            Descriptor = descriptor,
            DescriptorPath = descriptorPath.FullName,
            ValidationPath = validationPath.FullName,
        };
    }

    public async Task<ConnectivitySuiteRunReport> RunFixtureSuiteAsync(
        string serial,
        string program,
        string protocol,
        string portText,
        CancellationToken cancellationToken)
    {
        var selectedProtocol = NormalizeProtocol(protocol);
        var port = ParsePort(portText, DefaultPortForProtocol(selectedProtocol));
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var stamp = DateTimeOffset.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture);
        var runId = $"wpf-connectivity-suite-{stamp}";
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}.json"));
        var artifactDir = new DirectoryInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{runId}-artifacts"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);
        Directory.CreateDirectory(artifactDir.FullName);

        var arguments = new List<string>
        {
            "connectivity-probe",
            "run-suite",
            "--mode",
            "fixture",
            "--suite-id",
            "wpf-connectivity-suite",
            "--run-id",
            runId,
            "--out",
            reportPath.FullName,
            "--artifact-dir",
            artifactDir.FullName,
            "--listener-protocol",
            selectedProtocol,
            "--listener-port",
            port.ToString(CultureInfo.InvariantCulture),
            "--fail-on-error",
        };
        var listenerProgram = string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim();
        if (!string.IsNullOrWhiteSpace(listenerProgram))
        {
            arguments.Add("--listener-program");
            arguments.Add(listenerProgram);
        }
        if (!string.IsNullOrWhiteSpace(serial))
        {
            arguments.Add("--serial");
            arguments.Add(serial.Trim());
            arguments.Add("--adb");
            arguments.Add(HostessctlAdbResolver.ResolveAdb());
        }

        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivitySuiteRunReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
    }

    public string DefaultRuleNameForPort(string portText, string protocol) =>
        DefaultRuleName(ParsePort(portText, DefaultPortForProtocol(NormalizeProtocol(protocol))), NormalizeProtocol(protocol));

    public static string DefaultProductProgramPath()
    {
        var appHost = Path.Combine(AppContext.BaseDirectory, "HostessCompanion.Wpf.exe");
        if (File.Exists(appHost))
        {
            return appHost;
        }

        return Environment.ProcessPath
            ?? Process.GetCurrentProcess().MainModule?.FileName
            ?? "";
    }

    private static async Task RunHostessctlAsync(
        DirectoryInfo repoRoot,
        IReadOnlyList<string> arguments,
        FileInfo expectedReport,
        CancellationToken cancellationToken)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = "python",
            WorkingDirectory = repoRoot.FullName,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add("tools/hostessctl/hostessctl.py");
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start hostessctl connectivity process.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        var stdout = await stdoutTask.ConfigureAwait(false);
        var stderr = await stderrTask.ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException(
                $"hostessctl connectivity command exited with {process.ExitCode}: {stderr}{stdout}");
        }
        if (!expectedReport.Exists)
        {
            throw new InvalidOperationException(
                $"hostessctl did not write connectivity report: {expectedReport.FullName}");
        }
    }

    private static async Task<T> ReadReportAsync<T>(
        FileInfo reportPath,
        CancellationToken cancellationToken)
    {
        await using var stream = File.OpenRead(reportPath.FullName);
        return await JsonSerializer.DeserializeAsync<T>(
                stream,
                JsonOptions,
                cancellationToken)
            .ConfigureAwait(false)
            ?? throw new InvalidOperationException($"Connectivity report was empty: {reportPath.FullName}");
    }

    private static async Task<ConnectivityCheck> RunElevatedPowerShellAsync(
        string name,
        string script,
        string successEvidence,
        string operation,
        object context,
        CancellationToken cancellationToken)
    {
        try
        {
            using var process = Process.Start(new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + EncodePowerShell(script),
                UseShellExecute = true,
                Verb = "runas",
                WindowStyle = ProcessWindowStyle.Normal,
            }) ?? throw new InvalidOperationException("Failed to start elevated PowerShell.");

            await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
            return SyntheticCheck(
                name,
                process.ExitCode == 0 ? "pass" : "fail",
                process.ExitCode == 0 ? successEvidence : $"{operation} exited with {process.ExitCode}",
                new { Operation = operation, ExitCode = process.ExitCode, Context = context },
                process.ExitCode == 0 ? [] : ["hostess.issue.connectivity_probe.elevated_firewall_rule_failed"]);
        }
        catch (Exception ex) when (ex is System.ComponentModel.Win32Exception or InvalidOperationException)
        {
            return SyntheticCheck(
                name,
                "fail",
                $"{operation} did not complete: {ex.Message}",
                new { Operation = operation, Context = context, Error = ex.Message },
                ["hostess.issue.connectivity_probe.elevated_firewall_rule_failed"]);
        }
    }

    private static ConnectivityCheck SyntheticCheck(
        string name,
        string status,
        string evidence,
        object observed,
        IReadOnlyList<string>? issueCodes = null) =>
        new()
        {
            Name = name,
            Status = status,
            Evidence = evidence,
            Notes = "",
            IssueCodes = issueCodes?.ToList() ?? [],
            Observed = JsonSerializer.SerializeToElement(observed, JsonOptions),
        };

    private static int ParsePort(string portText, int fallback)
    {
        if (string.IsNullOrWhiteSpace(portText))
        {
            return fallback;
        }
        if (!int.TryParse(portText.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out var port)
            || port <= 0
            || port > 65535)
        {
            throw new InvalidOperationException("Connectivity port must be between 1 and 65535.");
        }
        return port;
    }

    private static string DefaultRuleName(int port, string protocol) =>
        $"{(NormalizeProtocol(protocol) == "UDP" ? DefaultUdpRuleNamePrefix : DefaultTcpRuleNamePrefix)} {port}";

    private static int DefaultPortForProtocol(string protocol) =>
        NormalizeProtocol(protocol) == "UDP" ? DefaultUdpPort : DefaultTcpPort;

    private static string NormalizeProtocol(string protocol) =>
        string.Equals(protocol?.Trim(), "TCP", StringComparison.OrdinalIgnoreCase) ? "TCP" : "UDP";

    private static string EncodePowerShell(string script) =>
        Convert.ToBase64String(Encoding.Unicode.GetBytes(script));

    private static string PowerShellString(string value) => "'" + value.Replace("'", "''") + "'";
}
