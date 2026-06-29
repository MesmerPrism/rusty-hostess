using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class ConnectivityProbeReport
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("probe_id")]
    public string ProbeId { get; set; } = "";

    [JsonPropertyName("run_id")]
    public string RunId { get; set; } = "";

    [JsonPropertyName("transport")]
    public ConnectivityTransport Transport { get; set; } = new();

    [JsonPropertyName("host")]
    public ConnectivityHost Host { get; set; } = new();

    [JsonPropertyName("device")]
    public ConnectivityDevice Device { get; set; } = new();

    [JsonPropertyName("checks")]
    public List<ConnectivityCheck> Checks { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    public string ReportPath { get; set; } = "";
}

public sealed class ConnectivityStreamCapabilityRun
{
    public ConnectivityProbeReport Report { get; set; } = new();

    public ConnectivityStreamCapabilityDescriptor Descriptor { get; set; } = new();

    public string DescriptorPath { get; set; } = "";

    public string ValidationPath { get; set; } = "";
}

public sealed class ConnectivitySuiteRunReport
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("suite_run_id")]
    public string SuiteRunId { get; set; } = "";

    [JsonPropertyName("suite_id")]
    public string SuiteId { get; set; } = "";

    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "";

    [JsonPropertyName("suite_descriptor_path")]
    public string SuiteDescriptorPath { get; set; } = "";

    [JsonPropertyName("environment_snapshot")]
    public JsonElement EnvironmentSnapshot { get; set; }

    [JsonPropertyName("slot_results")]
    public List<ConnectivitySuiteSlotResult> SlotResults { get; set; } = [];

    [JsonPropertyName("grouped_results")]
    public List<ConnectivitySuiteGroupResult> GroupedResults { get; set; } = [];

    [JsonPropertyName("summary")]
    public JsonElement Summary { get; set; }

    public string ReportPath { get; set; } = "";
}

public sealed class ConnectivitySuiteSlotResult
{
    [JsonPropertyName("slot_id")]
    public string SlotId { get; set; } = "";

    [JsonPropertyName("probe_id")]
    public string ProbeId { get; set; } = "";

    [JsonPropertyName("phase")]
    public string Phase { get; set; } = "";

    [JsonPropertyName("purpose")]
    public string Purpose { get; set; } = "";

    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("report_status")]
    public string ReportStatus { get; set; } = "";

    [JsonPropertyName("validation_status")]
    public string ValidationStatus { get; set; } = "";

    [JsonPropertyName("report_path")]
    public string ReportPath { get; set; } = "";

    [JsonPropertyName("validation_path")]
    public string ValidationPath { get; set; } = "";

    [JsonPropertyName("descriptor_path")]
    public string DescriptorPath { get; set; } = "";

    [JsonPropertyName("descriptor_status")]
    public string DescriptorStatus { get; set; } = "";

    [JsonPropertyName("elapsed_ms")]
    public double ElapsedMs { get; set; }

    [JsonPropertyName("metrics")]
    public JsonElement Metrics { get; set; }

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];
}

public sealed class ConnectivitySuiteGroupResult
{
    [JsonPropertyName("group_id")]
    public string GroupId { get; set; } = "";

    [JsonPropertyName("phase")]
    public string Phase { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("slot_count")]
    public int SlotCount { get; set; }

    [JsonPropertyName("pass_count")]
    public int PassCount { get; set; }

    [JsonPropertyName("warn_count")]
    public int WarnCount { get; set; }

    [JsonPropertyName("fail_count")]
    public int FailCount { get; set; }

    [JsonPropertyName("slot_ids")]
    public List<string> SlotIds { get; set; } = [];
}

public sealed class ConnectivityProtocolEvidenceMatrix
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("matrix_id")]
    public string MatrixId { get; set; } = "";

    [JsonPropertyName("summary")]
    public JsonElement Summary { get; set; }

    [JsonPropertyName("rows")]
    public List<ConnectivityProtocolEvidenceRow> Rows { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    public string ReportPath { get; set; } = "";
}

public sealed class ConnectivityProtocolEvidenceRow
{
    [JsonPropertyName("capability_id")]
    public string CapabilityId { get; set; } = "";

    [JsonPropertyName("probe_id")]
    public string ProbeId { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";

    [JsonPropertyName("semantic_family")]
    public string SemanticFamily { get; set; } = "";

    [JsonPropertyName("authority_owner")]
    public string AuthorityOwner { get; set; } = "";

    [JsonPropertyName("required_for_fold_in")]
    public bool RequiredForFoldIn { get; set; }

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("promotion_state")]
    public string PromotionState { get; set; } = "";

    [JsonPropertyName("promotion_allowed")]
    public bool PromotionAllowed { get; set; }

    [JsonPropertyName("evidence_tier")]
    public string EvidenceTier { get; set; } = "";

    [JsonPropertyName("promotion_gate")]
    public string PromotionGate { get; set; } = "";

    [JsonPropertyName("missing_gates")]
    public List<string> MissingGates { get; set; } = [];

    [JsonPropertyName("gate_results")]
    public List<ConnectivityProtocolEvidenceGate> GateResults { get; set; } = [];

    [JsonPropertyName("source")]
    public JsonElement Source { get; set; }

    [JsonPropertyName("descriptor")]
    public JsonElement Descriptor { get; set; }

    [JsonPropertyName("measurements")]
    public JsonElement Measurements { get; set; }

    [JsonPropertyName("next_cli")]
    public string NextCli { get; set; } = "";
}

public sealed class ConnectivityProtocolEvidenceGate
{
    [JsonPropertyName("gate_id")]
    public string GateId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonExtensionData]
    public Dictionary<string, JsonElement> ExtensionData { get; set; } = [];
}

public sealed class ConnectivityStreamCapabilityDescriptor
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("capability_id")]
    public string CapabilityId { get; set; } = "";

    [JsonPropertyName("stream_id")]
    public string StreamId { get; set; } = "";

    [JsonPropertyName("semantic_family")]
    public string SemanticFamily { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "";

    [JsonPropertyName("runtime_evidence")]
    public JsonElement RuntimeEvidence { get; set; }

    [JsonPropertyName("host_listener")]
    public JsonElement HostListener { get; set; }

    [JsonPropertyName("measurements")]
    public JsonElement Measurements { get; set; }

    [JsonPropertyName("source_probe")]
    public JsonElement SourceProbe { get; set; }

    [JsonPropertyName("requirements")]
    public List<ConnectivityStreamRequirement> Requirements { get; set; } = [];

    [JsonPropertyName("warnings")]
    public List<ConnectivityStreamWarning> Warnings { get; set; } = [];

    public string DescriptorPath { get; set; } = "";
}

public sealed class ConnectivityStreamRequirement
{
    [JsonPropertyName("requirement_id")]
    public string RequirementId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonPropertyName("notes")]
    public string Notes { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonExtensionData]
    public Dictionary<string, JsonElement> ExtensionData { get; set; } = [];
}

public sealed class ConnectivityStreamWarning
{
    [JsonPropertyName("issue_code")]
    public string IssueCode { get; set; } = "";

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";

    [JsonExtensionData]
    public Dictionary<string, JsonElement> ExtensionData { get; set; } = [];
}

public sealed class ConnectivityTransport
{
    [JsonPropertyName("local_endpoint")]
    public string LocalEndpoint { get; set; } = "";

    [JsonPropertyName("remote_endpoint")]
    public string RemoteEndpoint { get; set; } = "";
}

public sealed class ConnectivityHost
{
    [JsonPropertyName("selected_ipv4")]
    public string SelectedIpv4 { get; set; } = "";

    [JsonPropertyName("firewall_profile")]
    public string FirewallProfile { get; set; } = "";

    [JsonPropertyName("firewall_listener")]
    public ConnectivityFirewallListener FirewallListener { get; set; } = new();
}

public sealed class ConnectivityDevice
{
    [JsonPropertyName("model")]
    public string Model { get; set; } = "";

    [JsonPropertyName("wifi_ipv4")]
    public string WifiIpv4 { get; set; } = "";
}

public sealed class ConnectivityFirewallListener
{
    [JsonPropertyName("program")]
    public string Program { get; set; } = "";

    [JsonPropertyName("protocol")]
    public string Protocol { get; set; } = "";

    [JsonPropertyName("port")]
    public int Port { get; set; }

    [JsonPropertyName("active_profiles")]
    public List<string> ActiveProfiles { get; set; } = [];

    [JsonPropertyName("matching_rule_count")]
    public int MatchingRuleCount { get; set; }

    [JsonPropertyName("allowed_on_active_profile")]
    public bool AllowedOnActiveProfile { get; set; }
}

public sealed class ConnectivityCheck
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonPropertyName("notes")]
    public string Notes { get; set; } = "";

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];

    [JsonPropertyName("observed")]
    public JsonElement Observed { get; set; }
}

public sealed class ConnectivityFirewallRuleReport
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("action")]
    public string Action { get; set; } = "";

    [JsonPropertyName("rule")]
    public ConnectivityFirewallRule Rule { get; set; } = new();

    [JsonPropertyName("powershell")]
    public ConnectivityFirewallPowerShell PowerShell { get; set; } = new();

    [JsonPropertyName("verification")]
    public ConnectivityFirewallVerification Verification { get; set; } = new();

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    [JsonPropertyName("action_result")]
    public ConnectivityProcessResult ActionResult { get; set; } = new();

    [JsonPropertyName("apply_result")]
    public ConnectivityProcessResult ApplyResult { get; set; } = new();

    public string ReportPath { get; set; } = "";
}

public sealed class ConnectivityFirewallRule
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("program")]
    public string Program { get; set; } = "";

    [JsonPropertyName("protocol")]
    public string Protocol { get; set; } = "";

    [JsonPropertyName("local_port")]
    public int LocalPort { get; set; }

    [JsonPropertyName("profiles")]
    public List<string> Profiles { get; set; } = [];

    [JsonPropertyName("remote_address")]
    public string RemoteAddress { get; set; } = "";

    [JsonPropertyName("scope_note")]
    public string ScopeNote { get; set; } = "";
}

public sealed class ConnectivityFirewallPowerShell
{
    [JsonPropertyName("requires_admin")]
    public bool RequiresAdmin { get; set; }

    [JsonPropertyName("script")]
    public string Script { get; set; } = "";
}

public sealed class ConnectivityFirewallVerification
{
    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("product_rule_verified")]
    public bool ProductRuleVerified { get; set; }

    [JsonPropertyName("allowed_on_active_profile")]
    public bool AllowedOnActiveProfile { get; set; }

    [JsonPropertyName("listener_firewall")]
    public JsonElement ListenerFirewall { get; set; }

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];
}

public sealed class ConnectivityProcessResult
{
    [JsonPropertyName("attempted")]
    public bool Attempted { get; set; }

    [JsonPropertyName("returncode")]
    public int? ReturnCode { get; set; }

    [JsonPropertyName("stdout")]
    public string Stdout { get; set; } = "";

    [JsonPropertyName("stderr")]
    public string Stderr { get; set; } = "";
}
