using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;

static partial class WpfCompanionTests
{
    public static void OperatorActionsMapWpfCommandsToCliRoutes()
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
            var advertisesHostessCtl =
                action.CliRoute.Contains("python tools\\hostessctl\\hostessctl.py", StringComparison.Ordinal)
                || (
                    action.CliRoute.Contains("$HostessCtl = 'tools\\hostessctl\\hostessctl.py'", StringComparison.Ordinal)
                    && action.CliRoute.Contains("python $HostessCtl", StringComparison.Ordinal)
                );
            Assert(advertisesHostessCtl,
                $"CLI route must advertise the Hostess CLI entrypoint for {action.ActionId}");
            Assert(!Regex.IsMatch(action.CliRoute, @"[A-Za-z0-9_)-]\|[A-Za-z0-9_(]"),
                $"CLI route must not use pipe-delimited option shorthand for {action.ActionId}");
            foreach (var routeSegment in HostessCliSegments(action.CliRoute))
            {
                Assert(Regex.IsMatch(routeSegment, @"(^|\s)--out(\s|$)"),
                    $"Hostess CLI route segment must name a primary --out artifact for {action.ActionId}: {routeSegment}");
            }
            Assert(!string.IsNullOrWhiteSpace(action.EvidenceArtifact), $"missing evidence artifact for {action.ActionId}");
            Assert(!string.IsNullOrWhiteSpace(action.TestCoverage), $"missing test coverage for {action.ActionId}");
            Assert(!action.RequiresAdbServerLifecycleLease,
                $"ordinary WPF operator actions must stay serial-scoped instead of requiring adb-server:lifecycle: {action.ActionId}");
            if (action.RequiresElevation)
            {
                Assert(action.CliRoute.Contains("windows-firewall-rule", StringComparison.Ordinal),
                    $"elevated WPF operator actions must use the Hostess firewall route: {action.ActionId}");
                Assert(action.MutatesHost,
                    $"elevated WPF operator actions must mark host mutation: {action.ActionId}");
            }
            if (action.RequiresQuestLease)
            {
                Assert(
                    action.CliRoute.Contains("$QuestSerial", StringComparison.Ordinal)
                    || action.CliRoute.Contains("<quest-serial>", StringComparison.Ordinal),
                    $"Quest-leased WPF operator actions must advertise the serial placeholder: {action.ActionId}");
            }
        }
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "RefreshCommand"
                && action.CliRoute.Contains("companion-readiness --out $ReadinessReport", StringComparison.Ordinal)
                && action.CliRoute.Contains("companion-catalog --out $CatalogReport", StringComparison.Ordinal)),
            "readiness refresh must name the readiness and catalog report artifacts");
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "RunSessionCommand"
                && action.CliRoute.Contains("companion-session run", StringComparison.Ordinal)
                && action.CliRoute.Contains("--out $SessionReport", StringComparison.Ordinal)
                && action.CliRoute.Contains("--adb $Adb --serial $QuestSerial", StringComparison.Ordinal)
                && action.CliRoute.Contains("--wait-seconds 30", StringComparison.Ordinal)
                && action.CliRoute.Contains("--fallback-wait-seconds 30", StringComparison.Ordinal)
                && action.CliRoute.Contains("--runtime-subscriber-retry-count 8", StringComparison.Ordinal)
                && action.CliRoute.Contains("--runtime-subscriber-retry-wait-seconds 2", StringComparison.Ordinal)
                && action.RequiresQuestLease
                && action.MutatesHost
                && action.MutatesDevice),
            "session run must advertise the robust headset-bound runtime receipt CLI route");
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "LoadSessionHistoryCommand"
                && action.CliRoute.Contains("companion-session history --out $SessionHistory", StringComparison.Ordinal)),
            "session history must stay backed by the companion-session history CLI route");
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "RunProbeCommand"
                && action.CliRoute.Contains("run-bridge-command-live-android --input $PrimaryInput --out $PrimaryEvidence --adb $Adb --serial $QuestSerial", StringComparison.Ordinal)
                && action.CliRoute.Contains("run-bridge-command-android --input $FallbackInput --out $FallbackEvidence --adb $Adb --serial $QuestSerial", StringComparison.Ordinal)
                && action.RequiresQuestLease
                && action.MutatesHost
                && action.MutatesDevice),
            "safe bridge probe must name input, output, ADB, and serial placeholders for both primary and fallback CLI routes");
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "VerifyConnectivityCommand"
                && action.CliRoute.Contains("$ProbeId = '<QCL-010-or-QCL-080>'", StringComparison.Ordinal)
                && action.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-080 --out $ConnectivityReport", StringComparison.Ordinal)
                && action.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-010 --out $ConnectivityReport", StringComparison.Ordinal)
                && action.CliRoute.Contains("--adb $Adb --serial $QuestSerial", StringComparison.Ordinal)
                && action.CliRoute.Contains("--udp-listener-helper $HostessCompanionWpfExe", StringComparison.Ordinal)
                && action.CliRoute.Contains("connectivity-probe stream-capability --input $ConnectivityReport --out $StreamCapability", StringComparison.Ordinal)
                && action.RequiresQuestLease
                && action.MutatesDevice),
            "connectivity verification must name probe inputs plus probe report and stream-capability descriptor artifacts");
        Assert(
            OperatorActionCatalog.All.Any(action =>
                action.UiCommandProperty == "RunConnectivitySuiteCommand"
                && action.CliRoute.Contains("connectivity-probe run-suite --mode fixture --suite-id wpf-connectivity-suite --out $ConnectivitySuite", StringComparison.Ordinal)
                && action.CliRoute.Contains("--artifact-dir $ConnectivitySuiteArtifacts", StringComparison.Ordinal)
                && action.CliRoute.Contains("--listener-program $HostessCompanionWpfExe", StringComparison.Ordinal)),
            "connectivity suite must name its suite-run artifact, artifact directory, and product listener input");
        var protocolMatrixAction = OperatorActionCatalog.All.Single(action =>
            action.UiCommandProperty == "RunProtocolMatrixCommand");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe protocol-matrix", StringComparison.Ordinal),
            "protocol matrix action must advertise the protocol-matrix CLI route");
        Assert(protocolMatrixAction.RequiresQuestLease && protocolMatrixAction.MutatesHost && protocolMatrixAction.MutatesDevice,
            "protocol matrix action must mark its live Quest and product-media side effects");
        Assert(protocolMatrixAction.CliRoute.Contains("--latest-artifact-dir", StringComparison.Ordinal),
            "protocol matrix action must advertise latest artifact directory selection");
        Assert(protocolMatrixAction.CliRoute.Contains("--latest-probe-id", StringComparison.Ordinal),
            "protocol matrix action must advertise latest probe-id selection");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-020", StringComparison.Ordinal),
            "protocol matrix action must advertise generated QCL-020 topology fixture evidence");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl-020-wifi-adb-session-pass", StringComparison.Ordinal),
            "protocol matrix action must advertise QCL-020 fixture profile");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-030", StringComparison.Ordinal),
            "protocol matrix action must advertise generated QCL-030 topology fixture evidence");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl-030-local-only-hotspot-started", StringComparison.Ordinal),
            "protocol matrix action must advertise QCL-030 fixture profile");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-040", StringComparison.Ordinal),
            "protocol matrix action must advertise generated QCL-040 topology fixture evidence");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl-040-wifi-direct-phone-peer-pass", StringComparison.Ordinal),
            "protocol matrix action must advertise QCL-040 fixture profile");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-041", StringComparison.Ordinal),
            "protocol matrix action must advertise generated QCL-041 topology fixture evidence");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl-041-wifi-direct-windows-peer-pass", StringComparison.Ordinal),
            "protocol matrix action must advertise QCL-041 fixture profile");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-040", StringComparison.Ordinal),
            "protocol matrix action must advertise live QCL-040 Wi-Fi Direct preflight");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode live --probe-id QCL-041", StringComparison.Ordinal),
            "protocol matrix action must advertise live QCL-041 Wi-Fi Direct preflight");
        Assert(protocolMatrixAction.CliRoute.Contains("--adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
            "protocol matrix action must use PowerShell variables for serial-scoped ADB placeholders");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-040 --out $Qcl040LifecyclePlan --preflight-report-out $Qcl040Preflight --adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle execution plan route");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out $Qcl041LifecyclePlan --preflight-report-out $Qcl041Preflight --adb $Adb --serial $QuestSerial", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle execution plan route");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-040 --out $Qcl040LifecycleTemplate", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle source template route");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe wifi-direct-lifecycle-template --probe-id QCL-041 --out $Qcl041LifecycleTemplate", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle source template route");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report $LifecycleReport", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-040 Wi-Fi Direct lifecycle normalization route");
        Assert(protocolMatrixAction.CliRoute.Contains("connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report $LifecycleReport", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-041 Wi-Fi Direct lifecycle normalization route");
        Assert(protocolMatrixAction.CliRoute.Contains("$TopologyFixtureInputs", StringComparison.Ordinal),
            "protocol matrix action must advertise explicit topology fixture report inputs through a PowerShell splat");
        Assert(protocolMatrixAction.CliRoute.Contains("@TopologyFixtureInputs", StringComparison.Ordinal),
            "protocol matrix action must pass explicit topology fixture report inputs through a PowerShell splat");
        Assert(protocolMatrixAction.CliRoute.Contains("@LifecycleTopologyInputs", StringComparison.Ordinal),
            "protocol matrix action must pass explicit lifecycle topology report inputs through a PowerShell splat");
        Assert(protocolMatrixAction.CliRoute.Contains("$LatestProbeArgs", StringComparison.Ordinal),
            "protocol matrix action must use repeated latest-probe-id arguments through a PowerShell splat");
        foreach (var routeSegment in protocolMatrixAction.CliRoute
            .Split(';', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Where(segment => segment.Contains("connectivity-probe run ", StringComparison.Ordinal)))
        {
            Assert(routeSegment.Contains(" --out ", StringComparison.Ordinal),
                $"connectivity-probe run segment must name an output artifact: {routeSegment}");
        }
        Assert(!protocolMatrixAction.CliRoute.Contains("QCL-000|", StringComparison.Ordinal),
            "protocol matrix action must not advertise pipe-delimited latest probe IDs");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-000", StringComparison.Ordinal),
            "protocol matrix action must include WebSocket command route evidence QCL-000");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-010", StringComparison.Ordinal),
            "protocol matrix action must include same-Wi-Fi TCP topology probe QCL-010");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-011", StringComparison.Ordinal),
            "protocol matrix action must include PC-hotspot TCP topology probe QCL-011");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-020", StringComparison.Ordinal),
            "protocol matrix action must include Wi-Fi ADB topology probe QCL-020");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-030", StringComparison.Ordinal),
            "protocol matrix action must include LocalOnlyHotspot topology probe QCL-030");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-040", StringComparison.Ordinal),
            "protocol matrix action must include phone-peer Wi-Fi Direct topology probe QCL-040");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-041", StringComparison.Ordinal),
            "protocol matrix action must include Windows-peer Wi-Fi Direct topology probe QCL-041");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-050", StringComparison.Ordinal),
            "protocol matrix action must include Bluetooth readiness probe QCL-050");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-051", StringComparison.Ordinal),
            "protocol matrix action must include Bluetooth reconnect probe QCL-051");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-080", StringComparison.Ordinal),
            "protocol matrix action must include UDP freshness probe QCL-080");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-081", StringComparison.Ordinal),
            "protocol matrix action must include LSL probe QCL-081");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-082", StringComparison.Ordinal),
            "protocol matrix action must include media-stream probe QCL-082");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-083", StringComparison.Ordinal),
            "protocol matrix action must include OSC probe QCL-083");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-084", StringComparison.Ordinal),
            "protocol matrix action must include ZeroMQ probe QCL-084");
        Assert(protocolMatrixAction.CliRoute.Contains("QCL-079", StringComparison.Ordinal),
            "protocol matrix action must include generic WebSocket probe QCL-079");
        Assert(protocolMatrixAction.CliRoute.Contains("--websocket-source", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-079 generic WebSocket probe route");
        Assert(protocolMatrixAction.CliRoute.Contains("--websocket-route-descriptor", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-079 Manifold WebSocket route descriptor input");
        Assert(protocolMatrixAction.CliRoute.Contains("--websocket-route-evidence", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-079 Manifold WebSocket route evidence input");
        Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-session-plan", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 media-stream source-contract input");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl082-product-media-plan", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 product-media direct-Wi-Fi plan route");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl082-product-media-direct-wifi-plan.json", StringComparison.Ordinal),
            "protocol matrix action must name the QCL-082 product-media plan artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("direct-wifi-product-media-plan --out $DirectWifiProductMediaPlan", StringComparison.Ordinal),
            "protocol matrix action must advertise the combined direct-Wi-Fi product-media acceptance plan route");
        Assert(protocolMatrixAction.CliRoute.Contains("--qcl040-preflight-report $Qcl040Preflight", StringComparison.Ordinal),
            "protocol matrix action must pass QCL-040 live preflight into the combined acceptance plan");
        Assert(protocolMatrixAction.CliRoute.Contains("--qcl041-preflight-report $Qcl041Preflight", StringComparison.Ordinal),
            "protocol matrix action must pass QCL-041 live preflight into the combined acceptance plan");
        Assert(protocolMatrixAction.CliRoute.Contains("direct-wifi-product-media-acceptance-plan.json", StringComparison.Ordinal),
            "protocol matrix action must name the combined direct-Wi-Fi product-media acceptance plan artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("$Qcl082ReceiverReport = 'target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json'", StringComparison.Ordinal),
            "protocol matrix action must name the QCL-082 receiver fold-in report artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("--qcl082-report $Qcl082ReceiverReport", StringComparison.Ordinal),
            "protocol matrix action must pass QCL-082 product-media evidence into the combined acceptance plan");
        Assert(protocolMatrixAction.CliRoute.Contains("emit-bridge-command-request", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 bridge-command request generator");
        Assert(protocolMatrixAction.CliRoute.Contains("--bridge-command command.media_stream.start_source", StringComparison.Ordinal),
            "protocol matrix action must generate the QCL-082 start_source request through Hostess CLI");
        Assert(protocolMatrixAction.CliRoute.Contains("run-bridge-command-live-android", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 live Android start_source command route");
        Assert(protocolMatrixAction.CliRoute.Contains("--execution-out $RuntimeStatus", StringComparison.Ordinal),
            "protocol matrix action must use the live Android execution artifact as the runtime-status source");
        Assert(protocolMatrixAction.CliRoute.Contains("qcl082-product-media-live-session", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 orchestrated live media session route");
        Assert(protocolMatrixAction.CliRoute.Contains("$PreviewFfplay = '<ffplay>'", StringComparison.Ordinal),
            "protocol matrix action must advertise the live preview ffplay placeholder");
        Assert(protocolMatrixAction.CliRoute.Contains("--preview-ffplay $PreviewFfplay", StringComparison.Ordinal),
            "protocol matrix action must pass ffplay to the QCL-082 receiver route");
        Assert(protocolMatrixAction.CliRoute.Contains("--preview-window-title $PreviewWindowTitle", StringComparison.Ordinal),
            "protocol matrix action must pass the WPF preview window title to the QCL-082 receiver route");
        Assert(protocolMatrixAction.CliRoute.Contains("--quest-lease-id $QuestLeaseId", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 product-media quest lease id");
        Assert(protocolMatrixAction.CliRoute.Contains("--quest-lease-resource $QuestLeaseResource", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 product-media quest lease resource");
        Assert(protocolMatrixAction.CliRoute.Contains("--quest-lease-reserved-before-live-steps", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 product-media reserved-before-live lease flag");
        Assert(protocolMatrixAction.CliRoute.Contains("--start-source-request-out $StartSourceRequest", StringComparison.Ordinal),
            "protocol matrix action must pass the start_source request artifact into the live media session route");
        Assert(protocolMatrixAction.CliRoute.Contains("--logcat-out $StartSourceLogcat", StringComparison.Ordinal),
            "protocol matrix action must preserve the live media session logcat sidecar path");
        Assert(protocolMatrixAction.CliRoute.Contains("--out $ReceiverResult", StringComparison.Ordinal),
            "protocol matrix action must write the QCL-082 receiver-result artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("media-stream-start-source.live-android-execution.json", StringComparison.Ordinal),
            "protocol matrix action must name the QCL-082 live Android execution sidecar");
        Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-runtime-status", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 broker runtime-status input");
        Assert(protocolMatrixAction.CliRoute.Contains("rmanvid1-receiver-capture", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 RMANVID1 receiver capture route");
        Assert(protocolMatrixAction.CliRoute.Contains("--media-stream-receiver-result $ReceiverResult", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 receiver-result fold-in input");
        Assert(protocolMatrixAction.CliRoute.Contains("media-stream-receiver-result.json", StringComparison.Ordinal),
            "protocol matrix action must name the QCL-082 receiver-result artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("--topology-report", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 receiver topology report input");
        Assert(protocolMatrixAction.CliRoute.Contains("windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal),
            "protocol matrix action must advertise the product TCP firewall verification route");
        Assert(protocolMatrixAction.CliRoute.Contains("--rule-profile qcl-082-rmanvid1-media", StringComparison.Ordinal),
            "protocol matrix action must use the QCL-082 product media listener firewall profile");
        Assert(protocolMatrixAction.CliRoute.Contains("--firewall-report", StringComparison.Ordinal),
            "protocol matrix action must advertise the QCL-082 receiver firewall report input");
        Assert(protocolMatrixAction.CliRoute.Contains("--latest-device-link-dir", StringComparison.Ordinal),
            "protocol matrix action must advertise latest device-link directory selection");
        Assert(protocolMatrixAction.CliRoute.Contains("--latest-stream-capability-dir", StringComparison.Ordinal),
            "protocol matrix action must advertise latest stream-capability directory selection");
        Assert(protocolMatrixAction.CliRoute.Contains("--latest-stream-probe-id", StringComparison.Ordinal),
            "protocol matrix action must advertise latest stream probe-id selection");
        Assert(protocolMatrixAction.CliRoute.Contains("companion-report projection", StringComparison.Ordinal),
            "protocol matrix action must render a companion-report projection");
        Assert(protocolMatrixAction.CliRoute.Contains("--include-protocol-matrix-inputs", StringComparison.Ordinal),
            "protocol matrix action must include protocol-matrix inputs in the report projection");
        Assert(protocolMatrixAction.CliRoute.Contains("--firewall-rule $FirewallVerify", StringComparison.Ordinal),
            "protocol matrix action must preserve the QCL-082 firewall report in the report projection");
        Assert(protocolMatrixAction.CliRoute.Contains("--direct-wifi-product-media-plan $DirectWifiProductMediaPlan", StringComparison.Ordinal),
            "protocol matrix action must preserve the direct-Wi-Fi product-media acceptance plan in the report projection");
        Assert(protocolMatrixAction.CliRoute.Contains("companion-report transport-gates", StringComparison.Ordinal),
            "protocol matrix action must render the transport gate status artifact");
        Assert(protocolMatrixAction.CliRoute.Contains("--fail-on-error", StringComparison.Ordinal),
            "protocol matrix action must advertise transport gate validation failure handling");
        Assert(protocolMatrixAction.CliRoute.Contains("--fail-on-pending", StringComparison.Ordinal),
            "protocol matrix action must advertise the pending transport gate automation switch");
        Assert(protocolMatrixAction.CliRoute.Contains("--fail-on-incomplete", StringComparison.Ordinal),
            "protocol matrix action must fail automation when data protocols or transport gates remain incomplete");
        Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.quest.connectivity_topology_probe.v1", StringComparison.Ordinal),
            "protocol matrix action must advertise topology probe evidence");
        Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.direct_wifi_product_media_acceptance_plan.v1", StringComparison.Ordinal),
            "protocol matrix action must advertise direct-Wi-Fi product-media acceptance plan evidence");
        Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.companion.report_projection.v1", StringComparison.Ordinal),
            "protocol matrix action must render the shared companion-report projection artifact");
        Assert(protocolMatrixAction.EvidenceArtifact.Contains("rusty.hostess.companion.transport_gate_report.v1", StringComparison.Ordinal),
            "protocol matrix action must advertise the transport gate status artifact");
        var firewallActions = OperatorActionCatalog.All
            .Where(action => action.ActionId.StartsWith("wpf.connectivity.firewall.", StringComparison.Ordinal))
            .ToArray();
        Assert(firewallActions.Length == 4,
            "firewall controls must expose plan/apply/verify/remove operator action descriptors");
        Assert(firewallActions.All(action =>
                action.CliRoute.Contains("connectivity-probe windows-firewall-rule --action ", StringComparison.Ordinal)),
            "firewall controls must stay backed by the windows-firewall-rule CLI route");
        Assert(firewallActions.All(action =>
                action.CliRoute.Contains("--rule-profile", StringComparison.Ordinal)),
            "firewall controls must advertise the CLI rule profile route");
        Assert(firewallActions.All(action =>
                Regex.IsMatch(action.CliRoute, @"(^|\s)--out\s+\$Firewall(?:Plan|Apply|Verify|Remove)(\s|$)")),
            "firewall controls must name primary firewall report artifacts");
        Assert(firewallActions.Any(action =>
                action.CliRoute.Contains("--handoff-script-out $AdminHandoffScript", StringComparison.Ordinal)
                && action.CliRoute.Contains("--handoff-verify-out $VerifyReport", StringComparison.Ordinal)),
            "firewall mutation controls must advertise PowerShell-variable handoff outputs");
        Assert(firewallActions.All(action =>
                action.EvidenceArtifact == "rusty.quest.connectivity_windows_firewall_rule.v1"),
            "firewall controls must advertise the emitted windows firewall evidence schema");
        Assert(firewallActions.Single(action => action.ActionId == "wpf.connectivity.firewall.apply").RequiresElevation,
            "firewall apply must mark elevation");
        Assert(firewallActions.Single(action => action.ActionId == "wpf.connectivity.firewall.remove").RequiresElevation,
            "firewall remove must mark elevation");
        Assert(firewallActions.Where(action =>
                action.ActionId == "wpf.connectivity.firewall.apply"
                || action.ActionId == "wpf.connectivity.firewall.remove")
            .All(action => action.MutatesHost),
            "firewall apply/remove must mark host mutation");
        Assert(firewallActions.Where(action =>
                action.ActionId == "wpf.connectivity.firewall.plan"
                || action.ActionId == "wpf.connectivity.firewall.verify")
            .All(action => !action.RequiresElevation && !action.MutatesHost),
            "firewall plan/verify must remain non-mutating non-elevated actions");
    }
    

    public static void OperatorActionCliReportMatchesWpfCatalog()
    {
        var repoRoot = LocateHostessRepoRoot();
        var outPath = Path.Combine(
            repoRoot.FullName,
            "target",
            "companion-report",
            "wpf-operator-actions-test.json");
        Directory.CreateDirectory(Path.GetDirectoryName(outPath)!);
        var startInfo = new ProcessStartInfo
        {
            FileName = "python",
            WorkingDirectory = repoRoot.FullName,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            UseShellExecute = false,
        };
        foreach (var argument in new[]
        {
            "tools\\hostessctl\\hostessctl.py",
            "companion-report",
            "operator-actions",
            "--frontend",
            "wpf",
            "--out",
            outPath,
            "--fail-on-error",
        })
        {
            startInfo.ArgumentList.Add(argument);
        }
    
        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("could not start hostessctl operator-actions report");
        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();
        if (!process.WaitForExit(30_000))
        {
            process.Kill(entireProcessTree: true);
            throw new TimeoutException("hostessctl operator-actions report timed out");
        }
        var stdout = stdoutTask.GetAwaiter().GetResult();
        var stderr = stderrTask.GetAwaiter().GetResult();
        Assert(process.ExitCode == 0,
            $"hostessctl operator-actions exited with {process.ExitCode}: {stderr}{stdout}");
        Assert(File.Exists(outPath), "operator action CLI report must be written");
    
        using var document = JsonDocument.Parse(File.ReadAllText(outPath));
        var root = document.RootElement;
        Assert(JsonString(root, "$schema") == "rusty.hostess.companion.operator_action_catalog.v1",
            "operator action CLI report must use the expected schema");
        Assert(JsonString(root, "status") == "pass", "operator action CLI report must pass validation");
        Assert(JsonString(root, "frontend") == "wpf", "operator action CLI report must be WPF-scoped");
        var authority = root.GetProperty("authority");
        Assert(authority.GetProperty("catalog_only").GetBoolean(),
            "operator action CLI report must be catalog-only");
    
        var reportActions = root.GetProperty("actions")
            .EnumerateArray()
            .ToDictionary(action => JsonString(action, "action_id"), StringComparer.Ordinal);
        Assert(reportActions.Count == OperatorActionCatalog.All.Count,
            "operator action CLI report must expose every WPF action");
        foreach (var action in OperatorActionCatalog.All)
        {
            Assert(reportActions.TryGetValue(action.ActionId, out var reportAction),
                $"operator action CLI report missing {action.ActionId}");
            Assert(JsonString(reportAction, "title") == action.Title,
                $"operator action title mismatch for {action.ActionId}");
            Assert(JsonString(reportAction, "ui_command_property") == action.UiCommandProperty,
                $"operator action command property mismatch for {action.ActionId}");
            Assert(JsonString(reportAction, "cli_route") == action.CliRoute,
                $"operator action CLI route mismatch for {action.ActionId}");
            Assert(JsonString(reportAction, "evidence_artifact") == action.EvidenceArtifact,
                $"operator action evidence artifact mismatch for {action.ActionId}");
            Assert(JsonString(reportAction, "authority_owner") == action.AuthorityOwner,
                $"operator action authority owner mismatch for {action.ActionId}");
            Assert(JsonString(reportAction, "test_coverage") == action.TestCoverage,
                $"operator action test coverage mismatch for {action.ActionId}");
            Assert(JsonBool(reportAction, "requires_elevation") == action.RequiresElevation,
                $"operator action elevation flag mismatch for {action.ActionId}");
            Assert(JsonBool(reportAction, "requires_quest_lease") == action.RequiresQuestLease,
                $"operator action Quest lease flag mismatch for {action.ActionId}");
            Assert(JsonBool(reportAction, "requires_adb_server_lifecycle_lease") == action.RequiresAdbServerLifecycleLease,
                $"operator action ADB lifecycle lease flag mismatch for {action.ActionId}");
            Assert(JsonBool(reportAction, "mutates_host") == action.MutatesHost,
                $"operator action host mutation flag mismatch for {action.ActionId}");
            Assert(JsonBool(reportAction, "mutates_device") == action.MutatesDevice,
                $"operator action device mutation flag mismatch for {action.ActionId}");
        }
    }
    

}
