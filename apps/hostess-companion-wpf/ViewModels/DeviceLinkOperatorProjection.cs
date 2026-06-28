using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public static class DeviceLinkOperatorProjection
{
    public static IReadOnlyList<ReadinessCheck> BuildDeviceChecks(DeviceLinkReport report)
    {
        var rows = new List<ReadinessCheck>
        {
            Check(
                "device_link.identity",
                "device",
                "Quest identity",
                StatusFromDevice(report.DeviceIdentity.AdbState, report.Status),
                $"{report.DeviceIdentity.Model} / {report.DeviceIdentity.TransportKind} / {report.DeviceIdentity.AdbState}",
                report.DeviceIdentity),
        };

        rows.AddRange(report.HostTools.Select(tool => Check(
            $"device_link.tool.{SafeId(tool.ToolId, tool.Kind)}",
            "host_tool",
            $"Host tool: {tool.Kind}",
            tool.Status,
            string.IsNullOrWhiteSpace(tool.Path) ? tool.Kind : tool.Path,
            tool,
            required: tool.Required)));

        rows.AddRange(report.Tunnels.Select(tunnel => Check(
            $"device_link.tunnel.{SafeId(tunnel.TunnelId, tunnel.TransportKind)}",
            "network",
            $"Tunnel: {tunnel.TransportKind}",
            tunnel.Status,
            $"{tunnel.Host}:{tunnel.LocalPort} -> {tunnel.DeviceHost}:{tunnel.DevicePort}{tunnel.Path}",
            tunnel,
            required: tunnel.Required)));

        rows.AddRange(report.BrokerEndpoints.Select(endpoint => Check(
            $"device_link.broker.{SafeId(endpoint.EndpointId, endpoint.Protocol)}",
            "network",
            $"Broker endpoint: {endpoint.Protocol}",
            endpoint.Status,
            $"{endpoint.Protocol}://{endpoint.Host}:{endpoint.Port}{endpoint.Path} / {endpoint.Authority}",
            endpoint)));

        rows.AddRange(report.RuntimeSubscribers.Select(subscriber => Check(
            $"device_link.runtime_subscriber.{SafeId(subscriber.SubscriberId, subscriber.RuntimeAppId)}",
            "runtime",
            "Runtime subscriber",
            subscriber.Status == "connected" ? "pass" : subscriber.Status,
            $"{subscriber.RuntimeAppId}: {subscriber.RequestStreamId} -> {subscriber.ReceiptStreamId}, delivered={subscriber.LastDispatchDeliveredCount}",
            subscriber)));

        rows.AddRange(report.CommandResults.Select(result => Check(
            $"device_link.command_result.{SafeId(result.ResultId, result.RequestId)}",
            "runtime",
            $"Command result: {result.Command}",
            result.Status,
            $"{result.RouteId} / {result.TransportKind} / applied={result.Applied} / delivered={result.RuntimeDispatchDeliveredCount}",
            result)));

        rows.AddRange(report.Issues.Select(issue => Check(
            $"device_link.issue.{SafeId(issue.IssueCode, issue.Severity)}",
            "issue",
            issue.IssueCode,
            SeverityToStatus(issue.Severity),
            issue.Message,
            issue,
            issueCodes: string.IsNullOrWhiteSpace(issue.IssueCode) ? [] : [issue.IssueCode])));

        return rows;
    }

    public static IReadOnlyList<TransportCapabilityDescriptor> BuildTransportDescriptors(
        DeviceLinkReport report)
    {
        var rows = new List<TransportCapabilityDescriptor>();
        rows.AddRange(report.Tunnels.Select(tunnel => new TransportCapabilityDescriptor
        {
            Schema = "rusty.gui.transport_capability_descriptor.v1",
            TransportId = tunnel.TunnelId,
            Title = $"Device link tunnel: {tunnel.TransportKind}",
            Family = tunnel.TransportKind,
            Plane = "control",
            Delivery = tunnel.Status,
            PayloadRate = "low",
            AuthorityRole = "adapter",
            RouteIds = string.IsNullOrWhiteSpace(tunnel.Path) ? [] : [tunnel.Path],
            RequiredEvidenceStages = ["adb_state", "forward_mapping"],
            SupportedFrontends = ["wpf"],
            SuitableFor = ["developer control", "broker forwarding"],
            NotSuitableFor = ["production high-rate data"],
            Strengths = [$"{tunnel.Host}:{tunnel.LocalPort} -> {tunnel.DeviceHost}:{tunnel.DevicePort}"],
            Costs = tunnel.Required ? ["required for current session route"] : [],
            Sensitivity = ["local_device"],
            SourcePath = report.LinkId,
        }));

        rows.AddRange(report.BrokerEndpoints.Select(endpoint => new TransportCapabilityDescriptor
        {
            Schema = "rusty.gui.transport_capability_descriptor.v1",
            TransportId = endpoint.EndpointId,
            Title = $"Broker endpoint: {endpoint.Protocol}",
            Family = endpoint.Protocol,
            Plane = "control",
            Delivery = endpoint.Status,
            PayloadRate = "low",
            AuthorityRole = endpoint.Authority,
            RouteIds = string.IsNullOrWhiteSpace(endpoint.Path) ? [] : [endpoint.Path],
            RequiredEvidenceStages = ["socket_ready", "authority_acceptance", "runtime_receipt"],
            SupportedFrontends = ["wpf"],
            SuitableFor = ["operator commands", "session authority"],
            NotSuitableFor = ["media frames", "unbounded sensor streams"],
            Strengths = [$"{endpoint.Host}:{endpoint.Port}{endpoint.Path}"],
            Costs = string.IsNullOrWhiteSpace(endpoint.RoutedThroughTunnelId) ? [] : [$"via {endpoint.RoutedThroughTunnelId}"],
            Sensitivity = ["local_device"],
            SourcePath = report.LinkId,
        }));

        rows.AddRange(report.StreamCapabilities.Select(capability => new TransportCapabilityDescriptor
        {
            Schema = "rusty.gui.transport_capability_descriptor.v1",
            TransportId = capability.CapabilityId,
            Title = capability.StreamId,
            Family = capability.TransportKind,
            Plane = capability.PayloadPlane,
            Delivery = capability.Reliability,
            PayloadRate = capability.RateClass,
            AuthorityRole = capability.SemanticFamily == "command" ? "authority_request" : "adapter",
            RouteIds = [capability.StreamId],
            RequiredEvidenceStages = RequiredStagesFor(capability),
            SupportedFrontends = ["wpf"],
            SuitableFor = capability.RecommendedFor,
            NotSuitableFor = capability.NotFor,
            Strengths = [capability.Direction, capability.ClockPolicy],
            Costs = capability.MaxRateHz is { } rate ? [$"max_rate_hz={rate}"] : [],
            Sensitivity = ["local_device"],
            SourcePath = report.LinkId,
        }));

        return rows;
    }

    private static ReadinessCheck Check(
        string checkId,
        string group,
        string title,
        string status,
        string evidence,
        object observed,
        bool required = false,
        List<string>? issueCodes = null) =>
        new()
        {
            CheckId = checkId,
            Group = group,
            Title = title,
            Status = string.IsNullOrWhiteSpace(status) ? "unknown" : status,
            Required = required,
            Severity = SeverityForStatus(status),
            Evidence = evidence,
            IssueCodes = issueCodes ?? [],
            Observed = JsonSerializer.SerializeToElement(observed),
        };

    private static List<string> RequiredStagesFor(DeviceLinkStreamCapability capability) =>
        capability.SemanticFamily == "command"
            ? ["sent", "transport_ok", "authority_accepted", "runtime_accepted", "applied"]
            : ["dependency_ready", "transport_ready", "freshness_or_timing_report"];

    private static string StatusFromDevice(string adbState, string reportStatus) =>
        adbState == "device" ? "pass" : string.IsNullOrWhiteSpace(reportStatus) ? "unknown" : reportStatus;

    private static string SeverityToStatus(string severity) => severity switch
    {
        "error" => "fail",
        "warning" => "warn",
        _ => "warn",
    };

    private static string SeverityForStatus(string status) => status switch
    {
        "fail" or "blocked" or "rejected" => "error",
        "warn" or "missing" or "unknown" => "warning",
        _ => "info",
    };

    private static string SafeId(string preferred, string fallback)
    {
        var value = string.IsNullOrWhiteSpace(preferred) ? fallback : preferred;
        return string.IsNullOrWhiteSpace(value)
            ? "unknown"
            : value.Replace(' ', '_').Replace('/', '.').Replace('\\', '.');
    }
}
