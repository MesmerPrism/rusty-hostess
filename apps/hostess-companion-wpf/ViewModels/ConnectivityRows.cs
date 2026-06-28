using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public static class ConnectivityRows
{
    public static IReadOnlyList<ConnectivityCheck> ForFirewallPlan(
        ConnectivityFirewallRuleReport report)
    {
        var rows = new List<ConnectivityCheck> { FirewallPlanCheck(report) };
        if (!string.IsNullOrWhiteSpace(report.Verification.Status))
        {
            rows.Add(FirewallVerificationCheck(report));
        }
        if (report.ActionResult.Attempted)
        {
            rows.Add(FirewallActionResultCheck(report));
        }
        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> ForProbeReport(
        ConnectivityProbeReport report) =>
        report.Checks;

    public static IReadOnlyList<ConnectivityCheck> ForCapabilityRun(
        ConnectivityStreamCapabilityRun run)
    {
        var rows = new List<ConnectivityCheck>(run.Report.Checks);
        var descriptor = run.Descriptor;
        var warningCodes = descriptor.Warnings
            .Select(warning => warning.IssueCode)
            .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
            .ToList();
        rows.Add(new ConnectivityCheck
        {
            Name = "quest.device_link.stream_capability",
            Status = string.IsNullOrWhiteSpace(descriptor.Status) ? "unknown" : descriptor.Status,
            Evidence =
                $"{descriptor.StreamId}: {descriptor.TransportKind} / {descriptor.Direction}. " +
                $"Descriptor: {run.DescriptorPath}",
            Notes = descriptor.CapabilityId,
            IssueCodes = warningCodes,
                Observed = ToObservedElement(descriptor),
        });
        foreach (var requirement in descriptor.Requirements)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = requirement.RequirementId,
                Status = StatusForRequirement(requirement.Status),
                Evidence = string.IsNullOrWhiteSpace(requirement.Evidence)
                    ? requirement.Status
                    : requirement.Evidence,
                Notes = requirement.Notes,
                IssueCodes = [],
                Observed = ToObservedElement(requirement),
            });
        }
        foreach (var warning in descriptor.Warnings)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = warning.IssueCode,
                Status = "warn",
                Evidence = warning.Message,
                Notes = warning.Severity,
                IssueCodes = string.IsNullOrWhiteSpace(warning.IssueCode) ? [] : [warning.IssueCode],
                Observed = ToObservedElement(warning),
            });
        }

        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> ForSuiteReport(
        ConnectivitySuiteRunReport report)
    {
        var rows = new List<ConnectivityCheck>
        {
            new()
            {
                Name = "quest.device_link.install_environment_suite_run",
                Status = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status,
                Evidence =
                    $"{report.SuiteId} / {report.Mode}: {report.SlotResults.Count} slots. " +
                    $"Descriptor: {report.SuiteDescriptorPath}",
                Notes = report.ReportPath,
                IssueCodes = [],
                Observed = ToObservedElement(report),
            },
            new()
            {
                Name = "suite.environment_snapshot",
                Status = "pass",
                Evidence = "host tools, network adapters, firewall profiles, hotspot, and Bluetooth snapshot captured",
                Notes = "environment state is evidence; protocol validity remains in QCL slot reports",
                IssueCodes = [],
                Observed = ExistingJsonElementOrFallback(
                    report.EnvironmentSnapshot,
                    "suite.environment_snapshot"),
            },
        };

        foreach (var group in report.GroupedResults)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = group.GroupId,
                Status = group.Status,
                Evidence =
                    $"{group.Phase}: {group.PassCount} pass, {group.WarnCount} warn, " +
                    $"{group.FailCount} fail across {group.SlotCount} slots",
                Notes = string.Join(", ", group.SlotIds),
                IssueCodes = [],
                Observed = ToObservedElement(group),
            });
        }

        foreach (var slot in report.SlotResults)
        {
            var issues = slot.Issues
                .Select(issue => issue.IssueCode)
                .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
                .ToList();
            rows.Add(new ConnectivityCheck
            {
                Name = slot.SlotId,
                Status = slot.Status,
                Evidence =
                    $"{slot.ProbeId} {slot.Phase}: report={slot.ReportStatus}, " +
                    $"validation={slot.ValidationStatus}, metrics={MetricsSummary(slot.Metrics)}",
                Notes = string.IsNullOrWhiteSpace(slot.DescriptorPath)
                    ? slot.ReportPath
                    : $"{slot.ReportPath}; descriptor={slot.DescriptorPath} ({slot.DescriptorStatus})",
                IssueCodes = issues,
                Observed = ToObservedElement(slot),
            });
        }

        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> Failure(string checkName, Exception ex) =>
        [
            new ConnectivityCheck
            {
                Name = checkName,
                Status = "fail",
                Evidence = ex.Message,
                Notes = "",
                IssueCodes = ["hostess.issue.wpf.connectivity_failed"],
                Observed = ToObservedElement(new
                {
                    Error = ex.Message,
                    Type = ex.GetType().Name,
                }),
            },
        ];

    public static ConnectivityCheck FirewallPlanCheck(ConnectivityFirewallRuleReport report) =>
        new()
        {
            Name = $"host.windows_firewall_rule_{(string.IsNullOrWhiteSpace(report.Action) ? "plan" : report.Action)}",
            Status = report.Status,
            Evidence =
                $"{report.Rule.Name}: {report.Rule.Program}, {report.Rule.Protocol} {report.Rule.LocalPort}, " +
                $"{string.Join(",", report.Rule.Profiles)} / {report.Rule.RemoteAddress}",
            Notes = report.Rule.ScopeNote,
            IssueCodes = report.Issues.Select(issue => issue.IssueCode)
                .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
                .ToList(),
            Observed = ToObservedElement(report),
        };

    public static ConnectivityCheck FirewallVerificationCheck(ConnectivityFirewallRuleReport report) =>
        new()
        {
            Name = "host.windows_firewall_rule_verify",
            Status = report.Verification.ProductRuleVerified ? "pass" : report.Verification.AllowedOnActiveProfile ? "warn" : "fail",
            Evidence =
                $"product_rule_verified={report.Verification.ProductRuleVerified}; " +
                $"allowed_on_active_profile={report.Verification.AllowedOnActiveProfile}",
            Notes = report.Rule.ScopeNote,
            IssueCodes = report.Verification.IssueCodes,
            Observed = ExistingJsonElementOrFallback(
                report.Verification.ListenerFirewall,
                "host.windows_firewall_rule_verify"),
        };

    public static ConnectivityCheck FirewallActionResultCheck(ConnectivityFirewallRuleReport report) =>
        new()
        {
            Name = $"host.windows_firewall_rule_{report.Action}_process",
            Status = report.ActionResult.ReturnCode == 0 ? "pass" : "fail",
            Evidence = $"exit={report.ActionResult.ReturnCode}",
            Notes = report.ActionResult.Stderr,
            IssueCodes = report.ActionResult.ReturnCode == 0
                ? []
                : ["hostess.issue.connectivity_probe.elevated_firewall_rule_failed"],
            Observed = ToObservedElement(report.ActionResult),
        };

    public static string StatusFromRows(IReadOnlyList<ConnectivityCheck> rows)
    {
        if (rows.Any(row => row.Status is "fail" or "blocked" or "rejected"))
        {
            return "fail";
        }
        if (rows.Any(row => row.Status is "warn" or "usable_with_warnings" or "missing" or "unknown"))
        {
            return "warn";
        }
        if (rows.Any(row => row.Status is "planned" or "candidate"))
        {
            return "planned";
        }
        return rows.Count == 0 ? "unknown" : "pass";
    }

    private static string MetricsSummary(JsonElement metrics)
    {
        if (metrics.ValueKind != JsonValueKind.Object)
        {
            return "none";
        }
        var parts = new List<string>();
        foreach (var property in metrics.EnumerateObject())
        {
            if (parts.Count >= 4)
            {
                break;
            }
            parts.Add($"{property.Name}={property.Value}");
        }
        return parts.Count == 0 ? "none" : string.Join(", ", parts);
    }

    private static string StatusForRequirement(string status) => status switch
    {
        "satisfied" => "pass",
        "present_unverified" => "warn",
        "missing" => "warn",
        "unknown" => "warn",
        "blocked" => "blocked",
        _ => string.IsNullOrWhiteSpace(status) ? "unknown" : status,
    };

    private static JsonElement ToObservedElement<T>(T value)
    {
        try
        {
            return JsonSerializer.SerializeToElement(value);
        }
        catch (InvalidOperationException ex)
        {
            return JsonSerializer.SerializeToElement(new
            {
                observed_serialization = "unavailable",
                type = typeof(T).Name,
                error = ex.Message,
            });
        }
    }

    private static JsonElement ExistingJsonElementOrFallback(JsonElement value, string source) =>
        value.ValueKind == JsonValueKind.Undefined
            ? JsonSerializer.SerializeToElement(new
            {
                observed_serialization = "unavailable",
                source,
                error = "JsonElement was not present in the report.",
            })
            : value.Clone();
}
