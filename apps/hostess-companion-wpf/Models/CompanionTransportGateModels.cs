using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class CompanionTransportGateReport
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("report_id")]
    public string ReportId { get; set; } = "";

    [JsonPropertyName("authority")]
    public CompanionTransportGateAuthority Authority { get; set; } = new();

    [JsonPropertyName("source_projection")]
    public CompanionTransportGateSourceProjection SourceProjection { get; set; } = new();

    [JsonPropertyName("summary")]
    public CompanionTransportGateSummary Summary { get; set; } = new();

    [JsonPropertyName("data_protocols")]
    public CompanionTransportGateDataProtocols DataProtocols { get; set; } = new();

    [JsonPropertyName("operator_next_actions")]
    public CompanionTransportGateOperatorActions OperatorNextActions { get; set; } = new();

    [JsonPropertyName("term_gates")]
    public Dictionary<string, JsonElement> TermGates { get; set; } = [];

    [JsonPropertyName("remaining_live_gates")]
    public List<CompanionTransportGate> RemainingLiveGates { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    [JsonIgnore]
    public string ReportPath { get; set; } = "";
}

public sealed class CompanionTransportGateAuthority
{
    [JsonPropertyName("ui_role")]
    public string UiRole { get; set; } = "";

    [JsonPropertyName("projection_only")]
    public bool ProjectionOnly { get; set; }

    [JsonPropertyName("source_artifact")]
    public string SourceArtifact { get; set; } = "";

    [JsonPropertyName("acceptance_owner")]
    public string AcceptanceOwner { get; set; } = "";

    [JsonPropertyName("policy")]
    public string Policy { get; set; } = "";
}

public sealed class CompanionTransportGateSourceProjection
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("projection_id")]
    public string ProjectionId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("sha256")]
    public string Sha256 { get; set; } = "";
}

public sealed class CompanionTransportGateSummary
{
    [JsonPropertyName("all_transport_gates_clear")]
    public bool AllTransportGatesClear { get; set; }

    [JsonPropertyName("all_required_data_protocols_promoted")]
    public bool AllRequiredDataProtocolsPromoted { get; set; }

    [JsonPropertyName("all_wpf_transport_and_protocol_gates_clear")]
    public bool AllWpfTransportAndProtocolGatesClear { get; set; }

    [JsonPropertyName("completion_blockers")]
    public List<string> CompletionBlockers { get; set; } = [];

    [JsonPropertyName("remaining_gate_count")]
    public int RemainingGateCount { get; set; }

    [JsonPropertyName("remaining_gate_ids")]
    public List<string> RemainingGateIds { get; set; } = [];

    [JsonPropertyName("term_gate_count")]
    public int TermGateCount { get; set; }

    [JsonPropertyName("term_gate_ids")]
    public List<string> TermGateIds { get; set; } = [];
}

public sealed class CompanionTransportGateDataProtocols
{
    [JsonPropertyName("protocol_matrix_present")]
    public bool ProtocolMatrixPresent { get; set; }

    [JsonPropertyName("row_id")]
    public string RowId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("source_artifact")]
    public string SourceArtifact { get; set; } = "";

    [JsonPropertyName("source_path")]
    public string SourcePath { get; set; } = "";

    [JsonPropertyName("all_required_data_protocols_promoted")]
    public bool AllRequiredDataProtocolsPromoted { get; set; }

    [JsonPropertyName("required_promoted_count")]
    public int RequiredPromotedCount { get; set; }

    [JsonPropertyName("promoted_count")]
    public int PromotedCount { get; set; }

    [JsonPropertyName("required_count")]
    public int RequiredCount { get; set; }

    [JsonPropertyName("candidate_count")]
    public int CandidateCount { get; set; }

    [JsonPropertyName("missing_gate_count")]
    public int MissingGateCount { get; set; }

    [JsonPropertyName("issue_count")]
    public int IssueCount { get; set; }

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];
}

public sealed class CompanionTransportGateOperatorActions
{
    [JsonPropertyName("policy")]
    public string Policy { get; set; } = "";

    [JsonPropertyName("shell")]
    public string Shell { get; set; } = "";

    [JsonPropertyName("cwd")]
    public string Cwd { get; set; } = "";

    [JsonPropertyName("gate_count")]
    public int GateCount { get; set; }

    [JsonPropertyName("gates")]
    public List<CompanionTransportGateActionSummary> Gates { get; set; } = [];
}

public sealed class CompanionTransportGateActionSummary
{
    [JsonPropertyName("gate_id")]
    public string GateId { get; set; } = "";

    [JsonPropertyName("next_action_ids")]
    public List<string> NextActionIds { get; set; } = [];
}

public sealed class CompanionTransportGate
{
    [JsonPropertyName("gate_id")]
    public string GateId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonPropertyName("next_actions")]
    public List<CompanionTransportGateNextAction> NextActions { get; set; } = [];

    [JsonExtensionData]
    public Dictionary<string, JsonElement> ExtensionData { get; set; } = [];
}

public sealed class CompanionTransportGateNextAction
{
    [JsonPropertyName("action_id")]
    public string ActionId { get; set; } = "";

    [JsonPropertyName("label")]
    public string Label { get; set; } = "";

    [JsonPropertyName("authority_owner")]
    public string AuthorityOwner { get; set; } = "";

    [JsonPropertyName("available_now")]
    public bool AvailableNow { get; set; } = true;

    [JsonPropertyName("requires_elevation")]
    public bool RequiresElevation { get; set; }

    [JsonPropertyName("requires_quest_lease")]
    public bool RequiresQuestLease { get; set; }

    [JsonPropertyName("requires_adb_server_lifecycle_lease")]
    public bool RequiresAdbServerLifecycleLease { get; set; }

    [JsonPropertyName("mutates_host")]
    public bool MutatesHost { get; set; }

    [JsonPropertyName("mutates_device")]
    public bool MutatesDevice { get; set; }

    [JsonPropertyName("clears_gate_when_accepted")]
    public bool ClearsGateWhenAccepted { get; set; }

    [JsonPropertyName("acceptance_artifacts")]
    public List<string> AcceptanceArtifacts { get; set; } = [];

    [JsonPropertyName("depends_on")]
    public List<string> DependsOn { get; set; } = [];

    [JsonPropertyName("note")]
    public string Note { get; set; } = "";

    [JsonPropertyName("command")]
    public CompanionTransportGateNextActionCommand Command { get; set; } = new();

    [JsonPropertyName("lease")]
    public CompanionTransportGateNextActionLease Lease { get; set; } = new();

    [JsonExtensionData]
    public Dictionary<string, JsonElement> ExtensionData { get; set; } = [];
}

public sealed class CompanionTransportGateNextActionCommand
{
    [JsonPropertyName("label")]
    public string Label { get; set; } = "";

    [JsonPropertyName("shell")]
    public string Shell { get; set; } = "";

    [JsonPropertyName("cwd")]
    public string Cwd { get; set; } = "";

    [JsonPropertyName("command")]
    public string Command { get; set; } = "";
}

public sealed class CompanionTransportGateNextActionLease
{
    [JsonPropertyName("manager")]
    public string Manager { get; set; } = "";

    [JsonPropertyName("resource")]
    public string Resource { get; set; } = "";

    [JsonPropertyName("duration")]
    public string Duration { get; set; } = "";

    [JsonPropertyName("task")]
    public string Task { get; set; } = "";

    [JsonPropertyName("lease_id_placeholder")]
    public string LeaseIdPlaceholder { get; set; } = "";

    [JsonPropertyName("reserve_command")]
    public string ReserveCommand { get; set; } = "";

    [JsonPropertyName("release_command")]
    public string ReleaseCommand { get; set; } = "";

    [JsonPropertyName("adb_server_lifecycle_policy")]
    public string AdbServerLifecyclePolicy { get; set; } = "";
}
