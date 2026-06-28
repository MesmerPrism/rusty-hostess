using System.Text.Json.Serialization;

namespace HostessCompanion.Wpf.Models;

public sealed class DeviceLinkReport
{
    [JsonPropertyName("schema")]
    public string Schema { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("link_id")]
    public string LinkId { get; set; } = "";

    [JsonPropertyName("device_identity")]
    public DeviceLinkIdentity DeviceIdentity { get; set; } = new();

    [JsonPropertyName("host_tools")]
    public List<DeviceLinkHostTool> HostTools { get; set; } = [];

    [JsonPropertyName("tunnels")]
    public List<DeviceLinkTunnel> Tunnels { get; set; } = [];

    [JsonPropertyName("broker_endpoints")]
    public List<DeviceLinkBrokerEndpoint> BrokerEndpoints { get; set; } = [];

    [JsonPropertyName("runtime_subscribers")]
    public List<DeviceLinkRuntimeSubscriber> RuntimeSubscribers { get; set; } = [];

    [JsonPropertyName("command_results")]
    public List<DeviceLinkCommandResult> CommandResults { get; set; } = [];

    [JsonPropertyName("stream_capabilities")]
    public List<DeviceLinkStreamCapability> StreamCapabilities { get; set; } = [];

    [JsonPropertyName("issues")]
    public List<DeviceLinkIssue> Issues { get; set; } = [];
}

public sealed class DeviceLinkIdentity
{
    [JsonPropertyName("serial")]
    public string Serial { get; set; } = "";

    [JsonPropertyName("model")]
    public string Model { get; set; } = "";

    [JsonPropertyName("adb_state")]
    public string AdbState { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";
}

public sealed class DeviceLinkHostTool
{
    [JsonPropertyName("tool_id")]
    public string ToolId { get; set; } = "";

    [JsonPropertyName("kind")]
    public string Kind { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";
}

public sealed class DeviceLinkTunnel
{
    [JsonPropertyName("tunnel_id")]
    public string TunnelId { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("required")]
    public bool Required { get; set; }

    [JsonPropertyName("host")]
    public string Host { get; set; } = "";

    [JsonPropertyName("local_port")]
    public int LocalPort { get; set; }

    [JsonPropertyName("device_host")]
    public string DeviceHost { get; set; } = "";

    [JsonPropertyName("device_port")]
    public int DevicePort { get; set; }

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";
}

public sealed class DeviceLinkBrokerEndpoint
{
    [JsonPropertyName("endpoint_id")]
    public string EndpointId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("protocol")]
    public string Protocol { get; set; } = "";

    [JsonPropertyName("host")]
    public string Host { get; set; } = "";

    [JsonPropertyName("port")]
    public int Port { get; set; }

    [JsonPropertyName("path")]
    public string Path { get; set; } = "";

    [JsonPropertyName("authority")]
    public string Authority { get; set; } = "";

    [JsonPropertyName("routed_through_tunnel_id")]
    public string RoutedThroughTunnelId { get; set; } = "";
}

public sealed class DeviceLinkRuntimeSubscriber
{
    [JsonPropertyName("subscriber_id")]
    public string SubscriberId { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("runtime_app_id")]
    public string RuntimeAppId { get; set; } = "";

    [JsonPropertyName("request_stream_id")]
    public string RequestStreamId { get; set; } = "";

    [JsonPropertyName("receipt_stream_id")]
    public string ReceiptStreamId { get; set; } = "";

    [JsonPropertyName("last_dispatch_delivered_count")]
    public int LastDispatchDeliveredCount { get; set; }

    [JsonPropertyName("receipt_required")]
    public bool ReceiptRequired { get; set; }
}

public sealed class DeviceLinkCommandResult
{
    [JsonPropertyName("result_id")]
    public string ResultId { get; set; } = "";

    [JsonPropertyName("request_id")]
    public string RequestId { get; set; } = "";

    [JsonPropertyName("command")]
    public string Command { get; set; } = "";

    [JsonPropertyName("route_id")]
    public string RouteId { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "";

    [JsonPropertyName("applied")]
    public bool Applied { get; set; }

    [JsonPropertyName("runtime_dispatch_delivered_count")]
    public int RuntimeDispatchDeliveredCount { get; set; }

    [JsonPropertyName("required_stages")]
    public List<string> RequiredStages { get; set; } = [];
}

public sealed class DeviceLinkStreamCapability
{
    [JsonPropertyName("capability_id")]
    public string CapabilityId { get; set; } = "";

    [JsonPropertyName("stream_id")]
    public string StreamId { get; set; } = "";

    [JsonPropertyName("transport_kind")]
    public string TransportKind { get; set; } = "";

    [JsonPropertyName("semantic_family")]
    public string SemanticFamily { get; set; } = "";

    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "";

    [JsonPropertyName("payload_plane")]
    public string PayloadPlane { get; set; } = "";

    [JsonPropertyName("rate_class")]
    public string RateClass { get; set; } = "";

    [JsonPropertyName("reliability")]
    public string Reliability { get; set; } = "";

    [JsonPropertyName("clock_policy")]
    public string ClockPolicy { get; set; } = "";

    [JsonPropertyName("max_rate_hz")]
    public double? MaxRateHz { get; set; }

    [JsonPropertyName("recommended_for")]
    public List<string> RecommendedFor { get; set; } = [];

    [JsonPropertyName("not_for")]
    public List<string> NotFor { get; set; } = [];
}

public sealed class DeviceLinkIssue
{
    [JsonPropertyName("issue_code")]
    public string IssueCode { get; set; } = "";

    [JsonPropertyName("severity")]
    public string Severity { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";
}
