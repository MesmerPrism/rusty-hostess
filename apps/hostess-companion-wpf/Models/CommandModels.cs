using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class BridgeCommandExecution
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("route_id")]
    public string RouteId { get; set; } = "";

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = "";

    [JsonPropertyName("command")]
    public string Command { get; set; } = "";

    [JsonPropertyName("broker_authority")]
    public BrokerAuthoritySummary BrokerAuthority { get; set; } = new();

    [JsonPropertyName("stage_observations")]
    public List<CommandStageObservation> StageObservations { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<CommandIssue> Issues { get; set; } = [];

    [JsonPropertyName("runtime_receipt")]
    public JsonElement RuntimeReceipt { get; set; }
}

public sealed class BrokerAuthoritySummary
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; }

    [JsonPropertyName("host")]
    public string Host { get; set; } = "";

    [JsonPropertyName("port")]
    public int Port { get; set; }

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("client_id")]
    public string ClientId { get; set; } = "";
}

public sealed class CommandStageObservation
{
    [JsonPropertyName("stage")]
    public string Stage { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("observed_at_ms")]
    public long ObservedAtMs { get; set; }

    [JsonPropertyName("evidence_refs")]
    public List<string> EvidenceRefs { get; set; } = [];

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];
}

public sealed class CommandIssue
{
    [JsonPropertyName("issue_code")]
    public string IssueCode { get; set; } = "";

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}
