using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

var tests = new (string Name, Action Test)[]
{
    ("device-link projection promotes devices and transports", DeviceLinkProjectionPromotesDevicesAndTransports),
    ("session service reads device-link artifact", SessionServiceReadsDeviceLinkArtifact),
    ("connectivity suite rows expose groups and metrics", ConnectivitySuiteRowsExposeGroupsAndMetrics),
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
