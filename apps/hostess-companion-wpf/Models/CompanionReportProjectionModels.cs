using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class CompanionReportProjection
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("projection_id")]
    public string ProjectionId { get; set; } = "";

    [JsonPropertyName("frontend")]
    public string Frontend { get; set; } = "";

    [JsonPropertyName("summary")]
    public JsonElement Summary { get; set; }

    [JsonPropertyName("source_artifacts")]
    public List<CompanionReportProjectionSource> SourceArtifacts { get; set; } = [];

    [JsonPropertyName("rows")]
    public List<CompanionReportProjectionRow> Rows { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CompanionReportProjectionIssue> Issues { get; set; } = [];

    [JsonIgnore]
    public string ReportPath { get; set; } = "";
}

public sealed class CompanionReportProjectionSource
{
    [JsonPropertyName("source_id")]
    public string SourceId { get; set; } = "";

    [JsonPropertyName("requested_role")]
    public string RequestedRole { get; set; } = "";

    [JsonPropertyName("role")]
    public string Role { get; set; } = "";

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("sha256")]
    public string Sha256 { get; set; } = "";

    [JsonPropertyName("summary")]
    public JsonElement Summary { get; set; }
}

public sealed class CompanionReportProjectionRow
{
    [JsonPropertyName("row_id")]
    public string RowId { get; set; } = "";

    [JsonPropertyName("section")]
    public string Section { get; set; } = "";

    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";

    [JsonPropertyName("label")]
    public string Label { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("authority_owner")]
    public string AuthorityOwner { get; set; } = "";

    [JsonPropertyName("evidence_tier")]
    public string EvidenceTier { get; set; } = "";

    [JsonPropertyName("source_artifact")]
    public string SourceArtifact { get; set; } = "";

    [JsonPropertyName("source_path")]
    public string SourcePath { get; set; } = "";

    [JsonPropertyName("source_schema")]
    public string SourceSchema { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("evidence")]
    public string Evidence { get; set; } = "";

    [JsonPropertyName("notes")]
    public string Notes { get; set; } = "";

    [JsonPropertyName("issue_count")]
    public int IssueCount { get; set; }

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];

    [JsonPropertyName("metrics")]
    public JsonElement Metrics { get; set; }

    [JsonPropertyName("details")]
    public JsonElement Details { get; set; }
}

public sealed class CompanionReportProjectionIssue
{
    [JsonPropertyName("issue_code")]
    public string IssueCode { get; set; } = "";

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";

    [JsonPropertyName("source_artifact")]
    public string SourceArtifact { get; set; } = "";
}
