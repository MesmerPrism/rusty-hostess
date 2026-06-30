using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.Services;

public sealed class HostessctlConnectivityService
{
    private const int DefaultTcpPort = 18766;
    private const int DefaultUdpPort = 18767;
    private const int DefaultQcl082Rmanvid1MediaPort = 9079;
    public const string FirewallRuleProfileCustom = "custom";
    public const string FirewallRuleProfileQcl010TcpEcho = "qcl-010-tcp-echo";
    public const string FirewallRuleProfileQcl080UdpFreshness = "qcl-080-udp-freshness";
    public const string FirewallRuleProfileQcl082Rmanvid1Media = "qcl-082-rmanvid1-media";
    private const string DefaultTcpRuleNamePrefix = "Rusty Hostess WPF QCL-010 TCP Echo";
    private const string DefaultUdpRuleNamePrefix = "Rusty Hostess WPF QCL-080 UDP Freshness";
    private const string DefaultQcl082RuleNamePrefix = "Rusty Hostess WPF QCL-082 TCP RMANVID1 Media";

    public static readonly IReadOnlyList<string> FirewallRuleProfiles =
    [
        FirewallRuleProfileCustom,
        FirewallRuleProfileQcl010TcpEcho,
        FirewallRuleProfileQcl080UdpFreshness,
        FirewallRuleProfileQcl082Rmanvid1Media,
    ];

    private static readonly (string ProbeId, string FixtureProfile, string FileSuffix)[] TopologyFixtureProfiles =
    {
        ("QCL-020", "qcl-020-wifi-adb-session-pass", "qcl020-wifi-adb-session-pass"),
        ("QCL-030", "qcl-030-local-only-hotspot-started", "qcl030-local-only-hotspot-started"),
        ("QCL-040", "qcl-040-wifi-direct-phone-peer-pass", "qcl040-wifi-direct-phone-peer-pass"),
        ("QCL-041", "qcl-041-wifi-direct-windows-peer-pass", "qcl041-wifi-direct-windows-peer-pass"),
    };

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
        string ruleProfile,
        CancellationToken cancellationToken)
    {
        var selectedRuleProfile = NormalizeFirewallRuleProfile(ruleProfile);
        var selectedProtocol = NormalizeProtocol(
            string.IsNullOrWhiteSpace(protocol)
                ? DefaultProtocolForRuleProfile(selectedRuleProfile)
                : protocol);
        var port = ParsePort(portText, DefaultPortForRuleProfile(selectedRuleProfile, selectedProtocol));
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
            ruleName,
            selectedRuleProfile);

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
            report.Rule.Name,
            report.RuleProfile);
        AddFirewallHandoffArguments(
            arguments,
            FirewallActionHandoffScriptPath(repoRoot, "apply"),
            FirewallActionHandoffVerifyReportPath(repoRoot, "apply"));
        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var applied = await ReadReportAsync<ConnectivityFirewallRuleReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        applied.ReportPath = reportPath.FullName;
        return applied;
    }

    public async Task<ConnectivityFirewallRuleReport> VerifyFirewallRuleAsync(
        string program,
        string protocol,
        string portText,
        string profile,
        string remoteAddress,
        string ruleName,
        string ruleProfile,
        CancellationToken cancellationToken)
    {
        var selectedRuleProfile = NormalizeFirewallRuleProfile(ruleProfile);
        var selectedProtocol = NormalizeProtocol(
            string.IsNullOrWhiteSpace(protocol)
                ? DefaultProtocolForRuleProfile(selectedRuleProfile)
                : protocol);
        var port = ParsePort(portText, DefaultPortForRuleProfile(selectedRuleProfile, selectedProtocol));
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
            ruleName,
            selectedRuleProfile);
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
        string ruleProfile,
        CancellationToken cancellationToken)
    {
        var selectedRuleProfile = NormalizeFirewallRuleProfile(ruleProfile);
        var selectedProtocol = NormalizeProtocol(
            string.IsNullOrWhiteSpace(protocol)
                ? DefaultProtocolForRuleProfile(selectedRuleProfile)
                : protocol);
        var port = ParsePort(portText, DefaultPortForRuleProfile(selectedRuleProfile, selectedProtocol));
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
            ruleName,
            selectedRuleProfile);
        AddFirewallHandoffArguments(
            arguments,
            FirewallActionHandoffScriptPath(repoRoot, "remove"),
            FirewallActionHandoffVerifyReportPath(repoRoot, "remove"));
        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        var report = await ReadReportAsync<ConnectivityFirewallRuleReport>(reportPath, cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        return report;
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
        var productProgram = string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim();
        var qcl082SourceContractReport = await RunQcl082MediaStreamSessionPlanIfAvailableAsync(
                repoRoot,
                suite.SuiteRunId,
                cancellationToken)
            .ConfigureAwait(false);
        var qcl082FirewallVerifyReport = await RunQcl082ProductFirewallVerifyAsync(
                repoRoot,
                suite.SuiteRunId,
                productProgram,
                cancellationToken)
            .ConfigureAwait(false);
        var qcl079WebSocketReport = await RunQcl079ManifoldWebSocketIfAvailableAsync(
                repoRoot,
                suite.SuiteRunId,
                cancellationToken)
            .ConfigureAwait(false);
        var topologyReports = await RunTopologyFixtureReportsAsync(
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
        if (qcl079WebSocketReport is not null)
        {
            matrixArguments.Add("--input");
            matrixArguments.Add(qcl079WebSocketReport.FullName);
        }
        foreach (var topologyReport in topologyReports)
        {
            matrixArguments.Add("--input");
            matrixArguments.Add(topologyReport.FullName);
        }
        matrixArguments.AddRange(
        [
            "--latest-artifact-dir",
            Path.Combine(repoRoot.FullName, "target", "connectivity-probe"),
            "--latest-probe-id",
            "QCL-000",
            "--latest-probe-id",
            "QCL-010",
            "--latest-probe-id",
            "QCL-011",
            "--latest-probe-id",
            "QCL-020",
            "--latest-probe-id",
            "QCL-030",
            "--latest-probe-id",
            "QCL-040",
            "--latest-probe-id",
            "QCL-041",
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
            "--latest-probe-id",
            "QCL-079",
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
        var projectionPath = CompanionProjectionReportPath(repoRoot, suite, matrix);
        var transportGatesPath = CompanionTransportGatesReportPath(repoRoot, suite, matrix);
        var directWifiProductMediaPlan = await RunDirectWifiProductMediaPlanAsync(
                repoRoot,
                suite,
                matrix,
                topologyReports,
                qcl082FirewallVerifyReport,
                projectionPath,
                transportGatesPath,
                productProgram,
                cancellationToken)
            .ConfigureAwait(false);
        var projection = await RunCompanionReportProjectionAsync(
                repoRoot,
                suite,
                matrix,
                qcl082FirewallVerifyReport,
                directWifiProductMediaPlan,
                projectionPath,
                cancellationToken)
            .ConfigureAwait(false);
        var transportGates = await RunCompanionTransportGateReportAsync(
                repoRoot,
                suite,
                matrix,
                projection,
                transportGatesPath,
                cancellationToken)
            .ConfigureAwait(false);
        return new ConnectivityProtocolMatrixProjectionRun
        {
            Suite = suite,
            Matrix = matrix,
            Projection = projection,
            TransportGates = transportGates,
            DirectWifiProductMediaPlanPath = directWifiProductMediaPlan.FullName,
        };
    }

    public string DefaultRuleNameForPort(string portText, string protocol) =>
        DefaultRuleNameForPortAndProfile(portText, protocol, FirewallRuleProfileCustom);

    public string DefaultRuleNameForPortAndProfile(string portText, string protocol, string ruleProfile)
    {
        var selectedRuleProfile = NormalizeFirewallRuleProfile(ruleProfile);
        var selectedProtocol = NormalizeProtocol(
            string.IsNullOrWhiteSpace(protocol)
                ? DefaultProtocolForRuleProfile(selectedRuleProfile)
                : protocol);
        return DefaultRuleName(
            ParsePort(portText, DefaultPortForRuleProfile(selectedRuleProfile, selectedProtocol)),
            selectedProtocol,
            selectedRuleProfile);
    }

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

    private static async Task<CompanionReportProjection> RunCompanionReportProjectionAsync(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix,
        FileInfo? qcl082FirewallVerifyReport,
        FileInfo? directWifiProductMediaPlan,
        FileInfo projectionPath,
        CancellationToken cancellationToken)
    {
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
        if (qcl082FirewallVerifyReport is not null)
        {
            arguments.Add("--firewall-rule");
            arguments.Add(qcl082FirewallVerifyReport.FullName);
        }
        if (directWifiProductMediaPlan is not null)
        {
            arguments.Add("--direct-wifi-product-media-plan");
            arguments.Add(directWifiProductMediaPlan.FullName);
        }

        await RunHostessctlAsync(repoRoot, arguments, projectionPath, cancellationToken)
            .ConfigureAwait(false);

        var report = await ReadReportAsync<CompanionReportProjection>(
                projectionPath,
                cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = projectionPath.FullName;
        return report;
    }

    private static async Task<CompanionTransportGateReport> RunCompanionTransportGateReportAsync(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix,
        CompanionReportProjection projection,
        FileInfo reportPath,
        CancellationToken cancellationToken)
    {
        Directory.CreateDirectory(reportPath.Directory!.FullName);
        var validationPath = new FileInfo(Path.Combine(
            reportPath.Directory.FullName,
            $"{Path.GetFileNameWithoutExtension(reportPath.Name)}.validation-report.json"));

        await RunHostessctlAsync(
                repoRoot,
                [
                    "companion-report",
                    "transport-gates",
                    "--projection",
                    projection.ReportPath,
                    "--out",
                    reportPath.FullName,
                    "--validation-out",
                    validationPath.FullName,
                    "--report-id",
                    $"{matrix.MatrixId}.wpf.transport-gates",
                    "--fail-on-error",
                ],
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);

        var report = await ReadReportAsync<CompanionTransportGateReport>(
                reportPath,
                cancellationToken)
            .ConfigureAwait(false);
        report.ReportPath = reportPath.FullName;
        report.ValidationReportPath = validationPath.FullName;
        if (validationPath.Exists)
        {
            report.ValidationReport = await ReadReportAsync<CompanionTransportGateValidationReport>(
                    validationPath,
                    cancellationToken)
                .ConfigureAwait(false);
        }
        return report;
    }

    private static async Task<IReadOnlyList<FileInfo>> RunTopologyFixtureReportsAsync(
        DirectoryInfo repoRoot,
        string suiteRunId,
        CancellationToken cancellationToken)
    {
        var reports = new List<FileInfo>();
        foreach (var fixture in TopologyFixtureProfiles)
        {
            var reportPath = new FileInfo(Path.Combine(
                repoRoot.FullName,
                "target",
                "connectivity-probe",
                $"{suiteRunId}.{fixture.FileSuffix}.json"));
            Directory.CreateDirectory(reportPath.Directory!.FullName);

            await RunHostessctlAsync(
                    repoRoot,
                    [
                        "connectivity-probe",
                        "run",
                        "--mode",
                        "fixture",
                        "--probe-id",
                        fixture.ProbeId,
                        "--fixture-profile",
                        fixture.FixtureProfile,
                        "--run-id",
                        $"{suiteRunId}-{fixture.FileSuffix}",
                        "--out",
                        reportPath.FullName,
                        "--fail-on-error",
                    ],
                    reportPath,
                    cancellationToken)
                .ConfigureAwait(false);
            reports.Add(reportPath);
        }
        return reports;
    }

    private static async Task<FileInfo> RunDirectWifiProductMediaPlanAsync(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix,
        IReadOnlyList<FileInfo> topologyReports,
        FileInfo? qcl082FirewallVerifyReport,
        FileInfo projectionPath,
        FileInfo transportGatesPath,
        string program,
        CancellationToken cancellationToken)
    {
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{suite.SuiteRunId}.direct-wifi-product-media-acceptance-plan.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        var arguments = new List<string>
        {
            "connectivity-probe",
            "direct-wifi-product-media-plan",
            "--out",
            reportPath.FullName,
            "--program",
            program,
            "--qcl082-report",
            DefaultQcl082ProductMediaReportPath(repoRoot).FullName,
            "--protocol-matrix-out",
            matrix.ReportPath,
            "--projection-out",
            projectionPath.FullName,
            "--transport-gates-out",
            transportGatesPath.FullName,
            "--fail-on-error",
        };

        var qcl040TopologyReport = topologyReports.FirstOrDefault(report =>
            report.Name.Contains(".qcl040-", StringComparison.OrdinalIgnoreCase));
        if (qcl040TopologyReport is not null)
        {
            arguments.Add("--qcl040-topology-report");
            arguments.Add(qcl040TopologyReport.FullName);
        }

        var qcl041TopologyReport = topologyReports.FirstOrDefault(report =>
            report.Name.Contains(".qcl041-", StringComparison.OrdinalIgnoreCase));
        if (qcl041TopologyReport is not null)
        {
            arguments.Add("--qcl041-topology-report");
            arguments.Add(qcl041TopologyReport.FullName);
        }

        var promotedTopologyReport = PromotedDirectWifiTopologySelector.Select(
            repoRoot,
            matrix,
            topologyReports);
        if (promotedTopologyReport is not null)
        {
            arguments.Add("--promoted-topology-report");
            arguments.Add(promotedTopologyReport.FullName);
        }

        if (qcl082FirewallVerifyReport is not null)
        {
            arguments.Add("--firewall-report");
            arguments.Add(qcl082FirewallVerifyReport.FullName);
        }

        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        return reportPath;
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

    private static async Task<FileInfo> RunQcl082ProductFirewallVerifyAsync(
        DirectoryInfo repoRoot,
        string suiteRunId,
        string program,
        CancellationToken cancellationToken)
    {
        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{suiteRunId}.qcl082-product-firewall-verify.json"));
        var arguments = FirewallRuleArguments(
            "verify",
            reportPath,
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            "TCP",
            DefaultQcl082Rmanvid1MediaPort,
            "Public",
            "LocalSubnet",
            "",
            FirewallRuleProfileQcl082Rmanvid1Media);
        await RunHostessctlAsync(repoRoot, arguments, reportPath, cancellationToken)
            .ConfigureAwait(false);
        return reportPath;
    }

    private static async Task<FileInfo?> RunQcl079ManifoldWebSocketIfAvailableAsync(
        DirectoryInfo repoRoot,
        string suiteRunId,
        CancellationToken cancellationToken)
    {
        var routeDescriptor = DefaultQcl079ManifoldWebSocketRouteDescriptorPath(repoRoot);
        var routeEvidence = DefaultQcl079ManifoldWebSocketRouteEvidencePath(repoRoot);
        if (!routeDescriptor.Exists || !routeEvidence.Exists)
        {
            return null;
        }

        var reportPath = new FileInfo(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"{suiteRunId}.qcl079-manifold-websocket-stream.json"));
        Directory.CreateDirectory(reportPath.Directory!.FullName);

        await RunHostessctlAsync(
                repoRoot,
                [
                    "connectivity-probe",
                    "run",
                    "--mode",
                    "live",
                    "--probe-id",
                    "QCL-079",
                    "--websocket-source",
                    "broker-owned-websocket",
                    "--websocket-route-descriptor",
                    routeDescriptor.FullName,
                    "--websocket-route-evidence",
                    routeEvidence.FullName,
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

    private static FileInfo DefaultQcl079ManifoldWebSocketRouteDescriptorPath(DirectoryInfo repoRoot) =>
        new(Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-manifold",
            "fixtures",
            "bridge-route",
            "stream-websocket-ordered-route.json")));

    private static FileInfo DefaultQcl079ManifoldWebSocketRouteEvidencePath(DirectoryInfo repoRoot) =>
        new(Path.GetFullPath(Path.Combine(
            repoRoot.FullName,
            "..",
            "rusty-manifold",
            "fixtures",
            "bridge-route",
            "stream-websocket-ordered-evidence.json")));

    private static FileInfo DefaultQcl082ProductMediaReportPath(DirectoryInfo repoRoot) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            "qcl082-rmanvid1-receiver-capture.json"));

    private static FileInfo CompanionProjectionReportPath(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-report",
            $"{SafeFileToken(matrix.MatrixId, suite.SuiteRunId)}.projection.json"));

    private static FileInfo CompanionTransportGatesReportPath(
        DirectoryInfo repoRoot,
        ConnectivitySuiteRunReport suite,
        ConnectivityProtocolEvidenceMatrix matrix) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-report",
            $"{SafeFileToken(matrix.MatrixId, suite.SuiteRunId)}.transport-gates.json"));

    private static FileInfo FirewallActionReportPath(DirectoryInfo repoRoot, string action) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"wpf-firewall-rule-{action}.json"));

    private static FileInfo FirewallActionHandoffScriptPath(DirectoryInfo repoRoot, string action) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"wpf-firewall-rule-{action}.admin-handoff.ps1"));

    private static FileInfo FirewallActionHandoffVerifyReportPath(DirectoryInfo repoRoot, string action) =>
        new(Path.Combine(
            repoRoot.FullName,
            "target",
            "connectivity-probe",
            $"wpf-firewall-rule-{action}.verify.json"));

    private static void AddFirewallHandoffArguments(
        List<string> arguments,
        FileInfo scriptPath,
        FileInfo verifyReportPath)
    {
        Directory.CreateDirectory(scriptPath.Directory!.FullName);
        Directory.CreateDirectory(verifyReportPath.Directory!.FullName);
        arguments.Add("--handoff-script-out");
        arguments.Add(scriptPath.FullName);
        arguments.Add("--handoff-verify-out");
        arguments.Add(verifyReportPath.FullName);
    }

    private static List<string> FirewallRuleArguments(
        string action,
        FileInfo reportPath,
        string program,
        string protocol,
        int port,
        string profile,
        string remoteAddress,
        string ruleName,
        string ruleProfile)
    {
        var selectedRuleProfile = NormalizeFirewallRuleProfile(ruleProfile);
        var selectedProtocol = NormalizeProtocol(protocol);
        var selectedRuleName = string.IsNullOrWhiteSpace(ruleName)
            ? DefaultRuleName(port, selectedProtocol, selectedRuleProfile)
            : ruleName.Trim();
        Directory.CreateDirectory(reportPath.Directory!.FullName);
        var arguments = new List<string>
        {
            "connectivity-probe",
            "windows-firewall-rule",
            "--action",
            action,
            "--out",
            reportPath.FullName,
            "--program",
            string.IsNullOrWhiteSpace(program) ? DefaultProductProgramPath() : program.Trim(),
            "--profile",
            string.IsNullOrWhiteSpace(profile) ? "Public" : profile.Trim(),
            "--remote-address",
            string.IsNullOrWhiteSpace(remoteAddress) ? "LocalSubnet" : remoteAddress.Trim(),
        };
        if (selectedRuleProfile == FirewallRuleProfileCustom)
        {
            arguments.Add("--port");
            arguments.Add(port.ToString(CultureInfo.InvariantCulture));
            arguments.Add("--protocol");
            arguments.Add(selectedProtocol);
            arguments.Add("--rule-name");
            arguments.Add(selectedRuleName);
        }
        else
        {
            arguments.Add("--rule-profile");
            arguments.Add(selectedRuleProfile);
            if (port != DefaultPortForRuleProfile(selectedRuleProfile, selectedProtocol))
            {
                arguments.Add("--port");
                arguments.Add(port.ToString(CultureInfo.InvariantCulture));
            }
        }
        return arguments;
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

    private static string DefaultRuleName(
        int port,
        string protocol,
        string ruleProfile = FirewallRuleProfileCustom) =>
        NormalizeFirewallRuleProfile(ruleProfile) switch
        {
            FirewallRuleProfileQcl010TcpEcho => $"{DefaultTcpRuleNamePrefix} {port}",
            FirewallRuleProfileQcl080UdpFreshness => $"{DefaultUdpRuleNamePrefix} {port}",
            FirewallRuleProfileQcl082Rmanvid1Media => $"{DefaultQcl082RuleNamePrefix} {port}",
            _ => $"{(NormalizeProtocol(protocol) == "UDP" ? DefaultUdpRuleNamePrefix : DefaultTcpRuleNamePrefix)} {port}",
        };

    private static int DefaultPortForProtocol(string protocol) =>
        NormalizeProtocol(protocol) == "UDP" ? DefaultUdpPort : DefaultTcpPort;

    public static int DefaultPortForRuleProfile(string ruleProfile, string protocol = "") =>
        NormalizeFirewallRuleProfile(ruleProfile) switch
        {
            FirewallRuleProfileQcl080UdpFreshness => DefaultUdpPort,
            FirewallRuleProfileQcl082Rmanvid1Media => DefaultQcl082Rmanvid1MediaPort,
            FirewallRuleProfileQcl010TcpEcho => DefaultTcpPort,
            _ => DefaultPortForProtocol(protocol),
        };

    public static string DefaultProtocolForRuleProfile(string ruleProfile) =>
        NormalizeFirewallRuleProfile(ruleProfile) == FirewallRuleProfileQcl080UdpFreshness ? "UDP" : "TCP";

    public static string NormalizeFirewallRuleProfile(string ruleProfile)
    {
        var normalized = string.IsNullOrWhiteSpace(ruleProfile)
            ? FirewallRuleProfileCustom
            : ruleProfile.Trim().ToLowerInvariant();
        return FirewallRuleProfiles.Contains(normalized)
            ? normalized
            : FirewallRuleProfileCustom;
    }

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

}
