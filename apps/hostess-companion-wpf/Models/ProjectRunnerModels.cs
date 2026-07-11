using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class ProjectRunnerProjection
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("generation_id")]
    public string GenerationId { get; set; } = "";

    [JsonPropertyName("run_id")]
    public string RunId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("completion_marker")]
    public string CompletionMarker { get; set; } = "";

    [JsonPropertyName("risk_tier")]
    public string RiskTier { get; set; } = "";

    [JsonPropertyName("project_id")]
    public string ProjectId { get; set; } = "";

    [JsonPropertyName("product_lock_id")]
    public string ProductLockId { get; set; } = "";

    [JsonPropertyName("product_lock_revision")]
    public int ProductLockRevision { get; set; }

    [JsonPropertyName("product_lock_fingerprint")]
    public string ProductLockFingerprint { get; set; } = "";

    [JsonPropertyName("dry_run")]
    public bool DryRun { get; set; }

    [JsonPropertyName("executed")]
    public bool Executed { get; set; }

    [JsonPropertyName("rows")]
    public List<ProjectRunnerProjectionRow> Rows { get; set; } = [];
}

public sealed class ProjectRunnerProjectionRow
{
    [JsonPropertyName("row_id")]
    public string RowId { get; set; } = "";

    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";

    [JsonPropertyName("title")]
    public string Title { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("owner")]
    public string Owner { get; set; } = "";

    [JsonPropertyName("detail")]
    public string Detail { get; set; } = "";
}
