using System.Diagnostics;
using System.Globalization;
using System.Reflection;
using System.Text.RegularExpressions;
using System.Text.Json;
using HostessCompanion.Wpf.Models;
using HostessCompanion.Wpf.Services;
using HostessCompanion.Wpf.ViewModels;
using static WpfCompanionTests;

var tests = new (string Name, Action Test)[]
{
    ("device-link projection promotes devices and transports", DeviceLinkProjectionPromotesDevicesAndTransports),
    ("session service reads device-link artifact", SessionServiceReadsDeviceLinkArtifact),
    ("session service exposes robust receipt wait arguments", SessionServiceExposesRobustReceiptWaitArguments),
    ("connectivity suite rows expose groups and metrics", ConnectivitySuiteRowsExposeGroupsAndMetrics),
    ("protocol matrix rows expose promotion gates", ProtocolMatrixRowsExposePromotionGates),
    ("protocol matrix rows expose latest promoted evidence", ProtocolMatrixRowsExposeLatestPromotedEvidence),
    ("companion report projection rows expose shared artifact", CompanionReportProjectionRowsExposeSharedArtifact),
    ("companion report projection projects topology probe rows", CompanionReportProjectionProjectsTopologyProbeRows),
    ("companion report projection rows expose transport coverage", CompanionReportProjectionRowsExposeTransportCoverage),
    ("transport gate rows expose next actions", TransportGateRowsExposeNextActions),
    ("connectivity service builds companion report projection artifact", ConnectivityServiceBuildsCompanionReportProjectionArtifact),
    ("connectivity service forwards promoted direct wifi topology input", ConnectivityServiceForwardsPromotedDirectWifiTopologyInput),
    ("connectivity service forwards QCL-082 product media input", ConnectivityServiceForwardsQcl082ProductMediaInput),
    ("connectivity service finds sibling QCL-082 product media artifact", ConnectivityServiceFindsSiblingQcl082ProductMediaArtifact),
    ("firewall rows expose product verification", FirewallRowsExposeProductVerification),
    ("firewall rows expose elevation preflight", FirewallRowsExposeElevationPreflight),
    ("firewall service uses CLI admin handoff", FirewallServiceUsesCliAdminHandoff),
    ("firewall default names stay product scoped", FirewallDefaultNamesStayProductScoped),
    ("firewall QCL-082 profile plan uses CLI profile", FirewallQcl082ProfilePlanUsesCliProfile),
    ("operator action CLI report matches WPF catalog", OperatorActionCliReportMatchesWpfCatalog),
    ("operator actions map WPF commands to CLI routes", OperatorActionsMapWpfCommandsToCliRoutes),
    ("page viewmodels own WPF rows and selections", PageViewModelsOwnWpfRowsAndSelections),
    ("page viewmodels project backend reports", PageViewModelsProjectBackendReports),
    ("project runner projection is read-only and completion bound", ProjectRunnerProjectionIsReadOnlyAndCompletionBound),
    ("project runner projection rejects executed artifacts", ProjectRunnerProjectionRejectsExecutedOrIncompleteArtifacts),
    ("project runner operator action matches CLI route", ProjectRunnerOperatorActionMatchesReadOnlyCliRoute),
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
