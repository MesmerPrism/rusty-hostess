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
    private const string DefaultTcpRuleNamePrefix = "Rusty Hostess WPF QCL-010 TCP Echo";
    private const string DefaultUdpRuleNamePrefix = "Rusty Hostess WPF QCL-080 UDP Freshness";

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

        var arguments = FirewallRuleArguments(
            "plan",
            reportPath,
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            selectedProtocol,
            port,
            profile,
            remoteAddress,
            ruleName);

        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivityFirewallRuleReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
    }

    public async Task<ConnectivityFirewallRuleReport> ApplyFirewallRuleAsync(
        ConnectivityFirewallRuleReport report,
        CancellationToken cancellationToken)
    {
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = FirewallActionReportPath(repoRoot, "apply");
        var arguments = FirewallRuleArguments(
            "apply",
            reportPath,
            report.Rule.Program,
            report.Rule.Protocol,
            report.Rule.LocalPort,
            string.Join(",", report.Rule.Profiles),
            report.Rule.RemoteAddress,
            report.Rule.Name);
        return await RunElevatedHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
    }

    public async Task<ConnectivityFirewallRuleReport> VerifyFirewallRuleAsync(
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
        var reportPath = FirewallActionReportPath(repoRoot, "verify");
        var arguments = FirewallRuleArguments(
            "verify",
            reportPath,
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            selectedProtocol,
            port,
            profile,
            remoteAddress,
            ruleName);
        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivityFirewallRuleReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
    }

    public async Task<ConnectivityFirewallRuleReport> RemoveFirewallRuleAsync(
        string program,
        string ruleName,
        string protocol,
        string portText,
        string profile,
        string remoteAddress,
        CancellationToken cancellationToken)
    {
        var selectedProtocol = NormalizeProtocol(protocol);
        var port = ParsePort(portText, DefaultPortForProtocol(selectedProtocol));
        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var reportPath = FirewallActionReportPath(repoRoot, "remove");
        var arguments = FirewallRuleArguments(
            "remove",
            reportPath,
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            selectedProtocol,
            port,
            profile,
            remoteAddress,
            ruleName);
        return await RunElevatedHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
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
        arguments.Add("--listener-rule-name");
        arguments.Add(DefaultRuleName(port, selectedProtocol));
        arguments.Add("--listener-remote-address");
        arguments.Add("LocalSubnet");
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

    public async Task<ConnectivityProtocolEvidenceMatrix> RunProtocolEvidenceMatrixAsync(
        string serial,
        string program,
        string protocol,
        string portText,
        CancellationToken cancellationToken) =>
        (await RunProtocolMatrixProjectionAsync(
                serial,
                program,
                protocol,
                portText,
                cancellationToken)
            .ConfigureAwait(false)).Matrix;

    public async Task<ConnectivityProtocolMatrixProjectionRun> RunProtocolMatrixProjectionAsync(
        string serial,
        string program,
        string protocol,
        string portText,
        CancellationToken cancellationToken)
    {
        var suite = await RunFixtureSuiteAsync(
                serial,
                program,
                protocol,
                portText,
                cancellationToken)
            .ConfigureAwait(false);

        var repoRoot = HostessctlServicePaths.LocateRepoRoot();
        var qcl082SourceContractReport = await RunQcl082MediaStreamSessionPlanIfAvailableAsync(
                repoRoot,
                suite.SuiteRunId,
                cancellationToken)
            .ConfigureAwait(false);

        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{suite.SuiteRunId}.protocol-matrix.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        var matrixArguments = new List<string>
        {
            "connectivity-probe",
            "protocol-matrix",
            "--suite-run",
            suite.ReportPath,
        };
        if (qcl082SourceContractReport is not null)
        {
            matrixArguments.Add("--input");
            matrixArguments.Add(qcl082SourceContractReport.FullName);
        }
        matrixArguments.AddRange(
        [
            "--latest-artifact-dir",
            Path.Combine(repoRoot.FullName, "target", "connectivity-probe"),
            "--latest-probe-id",
            "QCL-050",
            "--latest-probe-id",
            "QCL-051",
            "--latest-probe-id",
            "QCL-080",
            "--latest-probe-id",
            "QCL-081",
            "--latest-probe-id",
            "QCL-082",
            "--latest-probe-id",
            "QCL-083",
            "--latest-probe-id",
            "QCL-084",
            "--latest-device-link-dir",
            Path.Combine(repoRoot.FullName, "target", "companion-session"),
            "--latest-stream-capability-dir",
            Path.Combine(repoRoot.FullName, "target", "connectivity-probe"),
            "--latest-stream-probe-id",
            "QCL-080",
            "--out",
            reportPath.FullName,
            "--fail-on-error",
        ]);

        await RunHostessctlAsync(
                repoRoot,
                matrixArguments,
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);

        var matrix = await ReadReportAsync<ConnectivityProtocolEvidenceMatrix>(
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);
        matrix.ReportPath = reportPath.FullName;
        var projection = await RunCompanionReportProjectionAsync(
                repoRoot,
                suite,
                matrix,
                cancellationToken)
            .ConfigureAwait(false);
        return new ConnectivityProtocolMatrixProjectionRun
        {
            Suite = suite,
            Matrix = matrix,
            Projection = projection,
        };
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

    private static async Task<ConnectivityFirewallRuleReport> RunElevatedHostessctlAsync(
        DirectoryInfo repoRoot,
        IReadOnlyList<string> arguments,
        FileInfo expectedReport,
        CancellationToken cancellationToken)
    {
        var script = string.Join(
            " ",
            [
                "$ErrorActionPreference = 'Stop';",
                $"Set-Location -LiteralPath {PowerShellString(repoRoot.FullName)};",
                "& python tools/hostessctl/hostessctl.py " + string.Join(" ", arguments.Select(PowerShellString)) + ";",
                "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }",
            ]);
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = "powershell.exe",
            Arguments = "-NoProfile -ExecutionPolicy Bypass -EncodedCommand " + EncodePowerShell(script),
            UseShellExecute = true,
            Verb = "runas",
            WindowStyle = ProcessWindowStyle.Normal,
        }) ?? throw new InvalidOperationException("Failed to start elevated Hostess firewall action.");

        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);
        if (process.ExitCode != 0)
        {
            throw new InvalidOperationException($"elevated Hostess firewall action exited with {process.ExitCode}");
        }
        if (!expectedReport.Exists)
        {
            throw new InvalidOperationException(
                $"Hostess firewall action did not write report: {expectedReport.FullName}");
        }
        var report = await ReadReportAsync<ConnectivityFirewallRuleReport>(
                expectedReport,
                cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = expectedReport.FullName;
        return report;
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

    private static async Task<CompanionReportProjection> RunCompanionReportProjectionAsync(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix,
        CancellationToken cancellationToken)
    {
        var projectionPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-report",
            $"{SafeFileToken(matrix.MatrixId, suite.SuiteRunId)}.projection.json"));
        Directory.CreateDirectory(projectionPath.Directory!.FullName);

        var arguments = new List<string>
        {
            "companion-report",
            "projection",
            "--frontend",
            "wpf",
            "--projection-id",
            $"{matrix.MatrixId}.wpf",
            "--protocol-matrix",
            matrix.ReportPath,
            "--include-protocol-matrix-inputs",
            "--suite-run",
            suite.ReportPath,
            "--out",
            projectionPath.FullName,
            "--fail-on-error",
        };

        await RunHostessctlAsync(repoRoot, arguments, projectionPath, cancellationToken)
            .ConfigureAwait(false);

        var report = await ReadReportAsync<CompanionReportProjection>(
                projectionPath,
                cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = projectionPath.FullName;
        return report;
    }

    private static async Task<FileInfo?> RunQcl082MediaStreamSessionPlanIfAvailableAsync(
        DirectoryInfo repoRoot,
        string suiteRunId,
        CancellationToken cancellationToken)
    {
        var planPath = DefaultQcl082MediaStreamSessionPlanPath(repoRoot);
        if (!planPath.Exists)
        {
            return null;
        }

        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{suiteRunId}.qcl082-media-stream-session-plan.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        await RunHostessctlAsync(
                repoRoot,
                [
                    "connectivity-probe",
                    "run",
                    "--mode",
                    "fixture",
                    "--probe-id",
                    "QCL-082",
                    "--media-stream-session-plan",
                    planPath.FullName,
                    "--out",
                    reportPath.FullName,
                    "--fail-on-error",
                ],
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);
        return reportPath;
    }

    private static FileInfo DefaultQcl082MediaStreamSessionPlanPath(DirectoryInfo repoRoot) =>
        new(Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-quest",
            "fixtures",
            "media-stream-sessions",
            "display-composite-mediaprojection-h264.plan.json")));

    private static FileInfo FirewallActionReportPath(DirectoryInfo repoRoot, string action) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"wpf-firewall-rule-{action}.json"));

    private static List<string> FirewallRuleArguments(
        string action,
        FileInfo reportPath,
        string program,
        string protocol,
        int port,
        string profile,
        string remoteAddress,
        string ruleName)
    {
        Directory.CreateDirectory(reportPath.Directory!.FullName);
        return
        [
            "connectivity-probe",
            "windows-firewall-rule",
            "--action",
            action,
            "--out",
            reportPath.FullName,
            "--program",
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            "--port",
            port.ToString(CultureInfo.InvariantCulture),
            "--protocol",
            NormalizeProtocol(protocol),
            "--profile",
            string.IsNullOrWhiteSpace(profile) ? "Public" : profile.Trim(),
            "--remote-address",
            string.IsNullOrWhiteSpace(remoteAddress) ? "LocalSubnet" : remoteAddress.Trim(),
            "--rule-name",
            string.IsNullOrWhiteSpace(ruleName) ? DefaultRuleName(port, protocol) : ruleName.Trim(),
        ];
    }

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

    private static string SafeFileToken(string preferred, string fallback)
    {
        var value = string.IsNullOrWhiteSpace(preferred) ? fallback : preferred;
        var chars = value
            .Select(ch => char.IsLetterOrDigit(ch) || ch is '.' or '_' or '-' ? ch : '-')
            .ToArray();
        var token = new string(chars).Trim('.', '_', '-');
        return string.IsNullOrWhiteSpace(token) ? "companion-report" : token;
    }

    private static string EncodePowerShell(string script) =>
        Convert.ToBase64String(Encoding.Unicode.GetBytes(script));

    private static string PowerShellString(string value) => "'" + value.Replace("'", "''") + "'";
}
