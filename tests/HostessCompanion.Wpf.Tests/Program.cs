using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

var tests = new (string Name, Action Test)[]
{
    ("device-link projection promotes devices and transports", DeviceLinkProjectionPromotesDevicesAndTransports),
    ("session service reads device-link artifact", SessionServiceReadsDeviceLinkArtifact),
    ("connectivity suite rows expose groups and metrics", ConnectivitySuiteRowsExposeGroupsAndMetrics),
    ("firewall rows expose product verification", FirewallRowsExposeProductVerification),
    ("operator actions map WPF commands to CLI routes", OperatorActionsMapWpfCommandsToCliRoutes),
};

var failed = 0;
foreach (var (name, test) in tests)
{
    try
    {
        test();
        Console.WriteLine($"PASS {name}");
    }
    catch (Exception ex)
    {
        failed++;
        Console.Error.WriteLine($"FAIL {name}: {ex}");
    }
}

return failed == 0 ? 0 : 1;

static void DeviceLinkProjectionPromotesDevicesAndTransports()
{
    var report = ReadFixture<DeviceLinkReport>("device-link-pass.json");
    var deviceRows = DeviceLinkOperatorProjection.BuildDeviceChecks(report);
    Assert(deviceRows.Any(row => row.CheckId == "device_link.identity" && row.Status == "pass"), "missing pass identity row");
    Assert(deviceRows.Any(row => row.Group == "runtime" && row.CheckId.Contains("runtime_subscriber")), "missing runtime subscriber row");
    Assert(deviceRows.Any(row => row.Group == "runtime" && row.CheckId.Contains("command_result")), "missing command result row");

    var transports = DeviceLinkOperatorProjection.BuildTransportDescriptors(report);
    Assert(transports.Any(row => row.TransportId == "tunnel.adb_forward.manifold_broker"), "missing ADB tunnel transport");
    Assert(transports.Any(row => row.TransportId == "broker.manifold.quest_forwarded"), "missing broker endpoint transport");
    var command = transports.Single(row => row.TransportId == "capability.command.hostess_makepad_bridge");
    Assert(command.RequiredEvidenceStages.Contains("applied"), "command capability must require applied evidence");
    Assert(transports.Any(row => row.TransportId == "capability.biosignal.lsl_clocked_samples"), "missing LSL stream capability");
}

static void SessionServiceReadsDeviceLinkArtifact()
{
    var service = new HostessctlSessionService();
    var session = new CompanionSessionReport
    {
        ArtifactRefs =
        [
            new SessionArtifactRef
            {
                Role = "device_link_report",
                Schema = "rusty.quest.device_link.v1",
                Path = "tests/HostessCompanion.Wpf.Tests/Fixtures/device-link-pass.json",
            },
        ],
    };
    var report = service.TryReadDeviceLinkReport(session);
    Assert(report is not null, "expected device-link report");
    Assert(report!.Status == "pass", "expected pass report");
    Assert(report.Tunnels.Count == 1, "expected tunnel");
}

static void ConnectivitySuiteRowsExposeGroupsAndMetrics()
{
    var metrics = JsonSerializer.SerializeToElement(new
    {
        rtt_ms = 12,
        samples = 3,
    });
    var report = new ConnectivitySuiteRunReport
    {
        Status = "warn",
        SuiteId = "suite",
        SuiteRunId = "suite-run",
        Mode = "fixture",
        SuiteDescriptorPath = "target/suite.json",
        EnvironmentSnapshot = JsonSerializer.SerializeToElement(new { network = "fixture" }),
        GroupedResults =
        [
            new ConnectivitySuiteGroupResult
            {
                GroupId = "group.protocol",
                Phase = "protocol",
                Status = "pass",
                SlotCount = 1,
                PassCount = 1,
                SlotIds = ["suite.qcl080"],
            },
        ],
        SlotResults =
        [
            new ConnectivitySuiteSlotResult
            {
                SlotId = "suite.qcl080",
                ProbeId = "QCL-080",
                Phase = "protocol",
                Status = "pass",
                ReportStatus = "pass",
                ValidationStatus = "pass",
                ReportPath = "target/qcl080.json",
                Metrics = metrics,
            },
        ],
    };

    var rows = ConnectivityRows.ForSuiteReport(report);
    Assert(rows[0].Name == "quest.device_link.install_environment_suite_run", "missing suite summary row");
    Assert(rows.Any(row => row.Name == "group.protocol"), "missing protocol group row");
    Assert(rows.Any(row => row.Name == "suite.qcl080" && row.Evidence.Contains("rtt_ms=12", StringComparison.Ordinal)), "missing metric summary");
    Assert(ConnectivityRows.StatusFromRows(rows) == "warn", "suite row warning must remain visible");
}

static void FirewallRowsExposeProductVerification()
{
    var listener = JsonSerializer.SerializeToElement(new
    {
        product_rule_verified = true,
        expected_rule_name = "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
        expected_remote_address = "LocalSubnet",
    });
    var report = new ConnectivityFirewallRuleReport
    {
        Status = "pass",
        Action = "verify",
        Rule = new ConnectivityFirewallRule
        {
            Name = "Rusty Hostess WPF QCL-080 UDP Freshness 18767",
            Program = "C:\\Program Files\\Rusty Hostess\\HostessCompanion.Wpf.exe",
            Protocol = "UDP",
            LocalPort = 18767,
            Profiles = ["Public"],
            RemoteAddress = "LocalSubnet",
            ScopeNote = "product scoped listener",
        },
        Verification = new ConnectivityFirewallVerification
        {
            Status = "pass",
            ProductRuleVerified = true,
            AllowedOnActiveProfile = true,
            ListenerFirewall = listener,
        },
    };

    var rows = ConnectivityRows.ForFirewallPlan(report);

    Assert(rows.Any(row => row.Name == "host.windows_firewall_rule_verify" && row.Status == "pass"),
        "missing verify action row");
    Assert(rows.Any(row => row.Evidence.Contains("product_rule_verified=True", StringComparison.Ordinal)),
        "missing product verification evidence");
    Assert(ConnectivityRows.StatusFromRows(rows) == "pass", "verified product rule should pass");
}

static void OperatorActionsMapWpfCommandsToCliRoutes()
{
    var commandProperties = typeof(MainWindowViewModel)
        .GetProperties()
        .Where(property => property.PropertyType == typeof(AsyncRelayCommand))
        .Select(property => property.Name)
        .Order(StringComparer.Ordinal)
        .ToArray();
    var mappedProperties = OperatorActionCatalog.All
        .Select(action => action.UiCommandProperty)
        .Order(StringComparer.Ordinal)
        .ToArray();

    Assert(
        commandProperties.SequenceEqual(mappedProperties),
        "every WPF command property must have an operator action descriptor");
    foreach (var action in OperatorActionCatalog.All)
    {
        Assert(action.ActionId.StartsWith("wpf.", StringComparison.Ordinal), "action id must be WPF scoped");
        Assert(!string.IsNullOrWhiteSpace(action.CliRoute), $"missing CLI route for {action.ActionId}");
        Assert(!action.CliRoute.Contains("button", StringComparison.OrdinalIgnoreCase),
            $"CLI route must not be UI-only for {action.ActionId}");
        Assert(!string.IsNullOrWhiteSpace(action.EvidenceArtifact), $"missing evidence artifact for {action.ActionId}");
        Assert(!string.IsNullOrWhiteSpace(action.TestCoverage), $"missing test coverage for {action.ActionId}");
    }
    Assert(
        OperatorActionCatalog.All.Any(action =>
            action.UiCommandProperty == "LoadSessionHistoryCommand"
            && action.CliRoute.Contains("companion-session history", StringComparison.Ordinal)),
        "session history must stay backed by the companion-session history CLI route");
}

static T ReadFixture<T>(string name)
{
    var path = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "Fixtures", name);
    using var stream = File.OpenRead(Path.GetFullPath(path));
    return JsonSerializer.Deserialize<T>(
            stream,
            new JsonSerializerOptions { PropertyNameCaseInsensitive = true })
        ?? throw new InvalidOperationException($"fixture {name} was empty");
}

static void Assert(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
