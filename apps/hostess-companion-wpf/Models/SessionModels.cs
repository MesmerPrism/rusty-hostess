using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class CompanionSessionReport
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("session_id")]
    public string SessionId { get; set; } = "";

    [JsonPropertyName("started_at_ms")]
    public long StartedAtMs { get; set; }

    [JsonPropertyName("ended_at_ms")]
    public long EndedAtMs { get; set; }

    [JsonPropertyName("frontend")]
    public string Frontend { get; set; } = "";

    [JsonPropertyName("profile")]
    public string Profile { get; set; } = "";

    [JsonPropertyName("summary")]
    public SessionSummary Summary { get; set; } = new();

    [JsonPropertyName("phases")]
    public List<SessionPhase> Phases { get; set; } = [];

    [JsonPropertyName("artifact_refs")]
    public List<SessionArtifactRef> ArtifactRefs { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    [JsonIgnore]
    public string ReportPath { get; set; } = "";

    [JsonIgnore]
    public DateTime ReportLastWriteTimeLocal { get; set; }
}

public sealed class CompanionSessionHistoryReport
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("session_dir")]
    public string SessionDir { get; set; } = "";

    [JsonPropertyName("count")]
    public int Count { get; set; }

    [JsonPropertyName("sessions")]
    public List<CompanionSessionHistoryEntry> Sessions { get; set; } = [];
}

public sealed class CompanionSessionHistoryEntry
{
    [JsonPropertyName("session_id")]
    public string SessionId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("frontend")]
    public string Frontend { get; set; } = "";

    [JsonPropertyName("profile")]
    public string Profile { get; set; } = "";

    [JsonPropertyName("started_at_ms")]
    public long StartedAtMs { get; set; }

    [JsonPropertyName("ended_at_ms")]
    public long EndedAtMs { get; set; }

    [JsonPropertyName("phase_count")]
    public int PhaseCount { get; set; }

    [JsonPropertyName("artifact_count")]
    public int ArtifactCount { get; set; }

    [JsonPropertyName("issue_count")]
    public int IssueCount { get; set; }

    [JsonPropertyName("report_path")]
    public string ReportPath { get; set; } = "";

    [JsonPropertyName("last_write_time_ms")]
    public long LastWriteTimeMs { get; set; }
}

public sealed class SessionSummary
{
    [JsonPropertyName("phase_count")]
    public int PhaseCount { get; set; }

    [JsonPropertyName("pass")]
    public int Pass { get; set; }

    [JsonPropertyName("warn")]
    public int Warn { get; set; }

    [JsonPropertyName("fail")]
    public int Fail { get; set; }

    [JsonPropertyName("skipped")]
    public int Skipped { get; set; }

    [JsonPropertyName("artifact_count")]
    public int ArtifactCount { get; set; }

    [JsonPropertyName("issue_count")]
    public int IssueCount { get; set; }

    [JsonPropertyName("action_count")]
    public int ActionCount { get; set; }
}

public sealed class SessionPhase
{
    [JsonPropertyName("phase_id")]
    public string PhaseId { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("summary")]
    public SessionSummary Summary { get; set; } = new();

    [JsonPropertyName("actions")]
    public List<SessionAction> Actions { get; set; } = [];

    [JsonPropertyName("artifact_refs")]
    public List<string> ArtifactRefs { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];
}

public sealed class SessionAction
{
    [JsonPropertyName("action_id")]
    public string ActionId { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonPropertyName("observed")]
    public JsonElement Observed { get; set; }

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];
}

public sealed class SessionArtifactRef
{
    [JsonPropertyName("artifact_id")]
    public string ArtifactId { get; set; } = "";

    [JsonPropertyName("role")]
    public string Role { get; set; } = "";

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("validation_status")]
    public string ValidationStatus { get; set; } = "";
}
