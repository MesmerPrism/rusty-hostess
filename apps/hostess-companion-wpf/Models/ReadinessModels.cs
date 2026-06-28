using System.Text.Json;
using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class ReadinessReport
{
    [JsonPropertyName("$schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("profile")]
    public string Profile { get; set; } = "";

    [JsonPropertyName("scope")]
    public ReadinessScope Scope { get; set; } = new();

    [JsonPropertyName("summary")]
    public ReadinessSummary Summary { get; set; } = new();

    [JsonPropertyName("checks")]
    public List<ReadinessCheck> Checks { get; set; } = [];
}

public sealed class ReadinessScope
{
    [JsonPropertyName("adb")]
    public string Adb { get; set; } = "";

    [JsonPropertyName("serial")]
    public string Serial { get; set; } = "";

    [JsonPropertyName("broker_host")]
    public string BrokerHost { get; set; } = "";

    [JsonPropertyName("broker_port")]
    public int BrokerPort { get; set; }

    [JsonPropertyName("makepad_package")]
    public string MakepadPackage { get; set; } = "";

    [JsonPropertyName("makepad_activity")]
    public string MakepadActivity { get; set; } = "";
}

public sealed class ReadinessSummary
{
    [JsonPropertyName("pass")]
    public int Pass { get; set; }

    [JsonPropertyName("warn")]
    public int Warn { get; set; }

    [JsonPropertyName("fail")]
    public int Fail { get; set; }

    [JsonPropertyName("skipped")]
    public int Skipped { get; set; }

    [JsonPropertyName("blocking")]
    public int Blocking { get; set; }
}

public sealed class ReadinessCheck
{
    [JsonPropertyName("check_id")]
    public string CheckId { get; set; } = "";

    [JsonPropertyName("group")]
    public string Group { get; set; } = "";

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

    [JsonPropertyName("issue_codes")]
    public List<string> IssueCodes { get; set; } = [];

    [JsonPropertyName("observed")]
    public JsonElement Observed { get; set; }
}
