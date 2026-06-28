using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class CompanionCatalog
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("scope")]
    public CatalogScope Scope { get; set; } = new();

    [JsonPropertyName("summary")]
    public CatalogSummary Summary { get; set; } = new();

    [JsonPropertyName("modules")]
    public List<CompanionModuleDescriptor> Modules { get; set; } = [];

    [JsonPropertyName("workspaces")]
    public List<CompanionWorkspaceDescriptor> Workspaces { get; set; } = [];

    [JsonPropertyName("transports")]
    public List<TransportCapabilityDescriptor> Transports { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CatalogIssue> Issues { get; set; } = [];
}

public sealed class CatalogScope
{
    [JsonPropertyName("frontend")]
    public string Frontend { get; set; } = "";

    [JsonPropertyName("hostess_descriptor")]
    public string HostessDescriptor { get; set; } = "";

    [JsonPropertyName("gui_descriptors_root")]
    public string GuiDescriptorsRoot { get; set; } = "";
}

public sealed class CatalogSummary
{
    [JsonPropertyName("modules")]
    public int Modules { get; set; }

    [JsonPropertyName("workspaces")]
    public int Workspaces { get; set; }

    [JsonPropertyName("transports")]
    public int Transports { get; set; }

    [JsonPropertyName("issues")]
    public int Issues { get; set; }

    [JsonPropertyName("warnings")]
    public int Warnings { get; set; }

    [JsonPropertyName("errors")]
    public int Errors { get; set; }
}

public sealed class CatalogIssue
{
    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("code")]
    public string Code { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}

public sealed class CompanionModuleDescriptor
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("module_id")]
    public string ModuleId { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("family")]
    public string Family { get; set; } = "";

    [JsonPropertyName("owner_lane")]
    public string OwnerLane { get; set; } = "";

    [JsonPropertyName("authority_role")]
    public string AuthorityRole { get; set; } = "";

    [JsonPropertyName("supported_frontends")]
    public List<string> SupportedFrontends { get; set; } = [];

    [JsonPropertyName("required_tools")]
    public List<ToolRequirement> RequiredTools { get; set; } = [];

    [JsonPropertyName("required_device_states")]
    public List<DeviceStateRequirement> RequiredDeviceStates { get; set; } = [];

    [JsonPropertyName("required_transports")]
    public List<TransportRequirement> RequiredTransports { get; set; } = [];

    [JsonPropertyName("readable_reports")]
    public List<ExternalReportBinding> ReadableReports { get; set; } = [];

    [JsonPropertyName("command_requests")]
    public List<CommandRequestBinding> CommandRequests { get; set; } = [];

    [JsonPropertyName("evidence_artifacts")]
    public List<EvidenceArtifactBinding> EvidenceArtifacts { get; set; } = [];

    [JsonPropertyName("remediation_actions")]
    public List<RemediationAction> RemediationActions { get; set; } = [];

    [JsonPropertyName("action_policy")]
    public ActionPolicy ActionPolicy { get; set; } = new();

    [JsonPropertyName("sensitivity")]
    public List<string> Sensitivity { get; set; } = [];

    [JsonPropertyName("source_path")]
    public string SourcePath { get; set; } = "";

    [JsonPropertyName("source_paths")]
    public List<string> SourcePaths { get; set; } = [];
}

public sealed class CompanionWorkspaceDescriptor
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("workspace_id")]
    public string WorkspaceId { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("supported_frontends")]
    public List<string> SupportedFrontends { get; set; } = [];

    [JsonPropertyName("modules")]
    public List<WorkspaceModuleSelection> Modules { get; set; } = [];

    [JsonPropertyName("sensitivity")]
    public List<string> Sensitivity { get; set; } = [];

    [JsonPropertyName("source_path")]
    public string SourcePath { get; set; } = "";
}

public sealed class WorkspaceModuleSelection
{
    [JsonPropertyName("module_id")]
    public string ModuleId { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("prominent")]
    public bool Prominent { get; set; }
}

public sealed class TransportCapabilityDescriptor
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("transport_id")]
    public string TransportId { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("family")]
    public string Family { get; set; } = "";

    [JsonPropertyName("plane")]
    public string Plane { get; set; } = "";

    [JsonPropertyName("delivery")]
    public string Delivery { get; set; } = "";

    [JsonPropertyName("payload_rate")]
    public string PayloadRate { get; set; } = "";

    [JsonPropertyName("authority_role")]
    public string AuthorityRole { get; set; } = "";

    [JsonPropertyName("route_ids")]
    public List<string> RouteIds { get; set; } = [];

    [JsonPropertyName("required_evidence_stages")]
    public List<string> RequiredEvidenceStages { get; set; } = [];

    [JsonPropertyName("supported_frontends")]
    public List<string> SupportedFrontends { get; set; } = [];

    [JsonPropertyName("strengths")]
    public List<string> Strengths { get; set; } = [];

    [JsonPropertyName("costs")]
    public List<string> Costs { get; set; } = [];

    [JsonPropertyName("suitable_for")]
    public List<string> SuitableFor { get; set; } = [];

    [JsonPropertyName("not_suitable_for")]
    public List<string> NotSuitableFor { get; set; } = [];

    [JsonPropertyName("sensitivity")]
    public List<string> Sensitivity { get; set; } = [];

    [JsonPropertyName("source_path")]
    public string SourcePath { get; set; } = "";
}

public sealed class ToolRequirement
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("readiness_check_id")]
    public string ReadinessCheckId { get; set; } = "";
}

public sealed class DeviceStateRequirement
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("label")]
    public string Label { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }
}

public sealed class TransportRequirement
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("family")]
    public string Family { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }
}

public sealed class ExternalReportBinding
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("owner_lane")]
    public string OwnerLane { get; set; } = "";
}

public sealed class CommandRequestBinding
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("command_id")]
    public string CommandId { get; set; } = "";

    [JsonPropertyName("route_id")]
    public string RouteId { get; set; } = "";

    [JsonPropertyName("authority_lane")]
    public string AuthorityLane { get; set; } = "";

    [JsonPropertyName("safe_to_auto_run")]
    public bool SafeToAutoRun { get; set; }
}

public sealed class EvidenceArtifactBinding
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("owner_lane")]
    public string OwnerLane { get; set; } = "";

    [JsonPropertyName("redaction_required")]
    public bool RedactionRequired { get; set; }
}

public sealed class RemediationAction
{
    [JsonPropertyName("id")]
    public string Id { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("command_id")]
    public string? CommandId { get; set; }

    [JsonPropertyName("manual_confirmation_required")]
    public bool ManualConfirmationRequired { get; set; }
}

public sealed class ActionPolicy
{
    [JsonPropertyName("auto_run_checks")]
    public bool AutoRunChecks { get; set; }

    [JsonPropertyName("state_changes_require_confirmation")]
    public bool StateChangesRequireConfirmation { get; set; }

    [JsonPropertyName("destructive_actions_allowed")]
    public bool DestructiveActionsAllowed { get; set; }
}
