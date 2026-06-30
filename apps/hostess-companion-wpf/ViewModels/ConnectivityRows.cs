using System.Text.Json;
using HostessCompanion.Wpf.Models;

namespace HostessCompanion.Wpf.ViewModels;

public static class ConnectivityRows
{
    public static IReadOnlyList<ConnectivityCheck> ForFirewallPlan(
        ConnectivityFirewallRuleReport report)
    {
        var rows = new List<ConnectivityCheck> { FirewallPlanCheck(report) };
        if (report.Elevation.RequiresAdmin || report.Elevation.BlockedBeforeMutation)
        {
            rows.Add(FirewallElevationCheck(report));
        }
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

    public static IReadOnlyList<ConnectivityCheck> ForProtocolEvidenceMatrix(
        ConnectivityProtocolEvidenceMatrix matrix)
    {
        var rows = new List<ConnectivityCheck>
        {
            new()
            {
                Name = "quest.device_link.protocol_evidence_matrix",
                Status = string.IsNullOrWhiteSpace(matrix.Status) ? "unknown" : matrix.Status,
                Evidence = $"{matrix.MatrixId}: {matrix.Rows.Count} protocol capability rows",
                Notes = matrix.ReportPath,
                IssueCodes = matrix.Issues.Select(issue => issue.IssueCode)
                    .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
                    .ToList(),
                Observed = ExistingJsonElementOrFallback(
                    matrix.Summary,
                    "quest.device_link.protocol_evidence_matrix"),
            },
        };

        foreach (var protocol in matrix.Rows)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = $"{protocol.ProbeId}.{protocol.TransportKind}",
                Status = string.IsNullOrWhiteSpace(protocol.Status) ? "unknown" : protocol.Status,
                Evidence =
                    $"{protocol.CapabilityId}: tier={protocol.EvidenceTier}, " +
                    $"promotion={protocol.PromotionState}, allowed={protocol.PromotionAllowed}",
                Notes = protocol.MissingGates.Count == 0
                    ? protocol.PromotionGate
                    : $"{protocol.PromotionGate} Missing: {string.Join(", ", protocol.MissingGates)}",
                IssueCodes = ProtocolIssueCodes(protocol),
                Observed = ToObservedElement(protocol),
            });

            foreach (var gate in protocol.GateResults)
            {
                rows.Add(new ConnectivityCheck
                {
                    Name = gate.GateId,
                    Status = StatusForProtocolGate(gate.Status),
                    Evidence = gate.Evidence,
                    Notes = protocol.CapabilityId,
                    IssueCodes = gate.Status == "satisfied" ? [] : [gate.GateId],
                    Observed = ToObservedElement(gate),
                });
            }
        }

        foreach (var issue in matrix.Issues)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = issue.IssueCode,
                Status = issue.Severity == "error" ? "fail" : "warn",
                Evidence = issue.Message,
                Notes = issue.Severity,
                IssueCodes = string.IsNullOrWhiteSpace(issue.IssueCode) ? [] : [issue.IssueCode],
                Observed = ToObservedElement(issue),
            });
        }

        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> ForCompanionReportProjection(
        CompanionReportProjection report)
    {
        var rows = new List<ConnectivityCheck>
        {
            new()
            {
                Name = "hostess.companion_report_projection",
                Status = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status,
                Evidence =
                    $"{report.ProjectionId}: {report.Rows.Count} rows from " +
                    $"{report.SourceArtifacts.Count} source artifacts",
                Notes = report.ReportPath,
                IssueCodes = report.Issues
                    .Select(issue => issue.IssueCode)
                    .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
                    .ToList(),
                Observed = ExistingJsonElementOrFallback(
                    report.Summary,
                    "hostess.companion_report_projection"),
            },
        };

        foreach (var source in report.SourceArtifacts)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = $"projection.source.{source.Role}.{source.SourceId}",
                Status = string.IsNullOrWhiteSpace(source.Status) ? "unknown" : source.Status,
                Evidence = $"{source.Schema}: {source.Path}",
                Notes = string.IsNullOrWhiteSpace(source.Sha256)
                    ? source.RequestedRole
                    : $"sha256={source.Sha256}; requested={source.RequestedRole}",
                IssueCodes = [],
                Observed = ToObservedElement(source),
            });
        }

        foreach (var projectionRow in report.Rows)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = string.IsNullOrWhiteSpace(projectionRow.RowId)
                    ? projectionRow.Label
                    : projectionRow.RowId,
                Status = string.IsNullOrWhiteSpace(projectionRow.Status)
                    ? "unknown"
                    : projectionRow.Status,
                Evidence = ProjectionEvidence(projectionRow),
                Notes = ProjectionNotes(projectionRow),
                IssueCodes = projectionRow.IssueCodes,
                Observed = ProjectionObservedElement(projectionRow),
            });
        }

        foreach (var issue in report.Issues)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = issue.IssueCode,
                Status = issue.Severity == "error" ? "fail" : "warn",
                Evidence = issue.Message,
                Notes = issue.SourceArtifact,
                IssueCodes = string.IsNullOrWhiteSpace(issue.IssueCode) ? [] : [issue.IssueCode],
                Observed = ToObservedElement(issue),
            });
        }

        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> ForTransportGateReport(
        CompanionTransportGateReport report)
    {
        var rows = new List<ConnectivityCheck>
        {
            new()
            {
                Name = "hostess.companion_transport_gates",
                Status = string.IsNullOrWhiteSpace(report.Status) ? "unknown" : report.Status,
                Evidence =
                    $"{report.ReportId}: {report.Summary.RemainingGateCount} remaining gates; " +
                    $"data_protocols_promoted={report.Summary.AllRequiredDataProtocolsPromoted}; " +
                    $"complete={report.Summary.AllWpfTransportAndProtocolGatesClear}; " +
                    $"source={report.SourceProjection.ProjectionId}",
                Notes = TransportGateSummaryNotes(report),
                IssueCodes = report.Issues
                    .Select(issue => issue.IssueCode)
                    .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
                    .ToList(),
                Observed = ToObservedElement(report),
            },
            new()
            {
                Name = "transport_gates.data_protocols",
                Status = TransportGateDataProtocolStatus(report.DataProtocols),
                Evidence = TransportGateDataProtocolEvidence(report.DataProtocols),
                Notes = TransportGateDataProtocolNotes(report),
                IssueCodes = TransportGateDataProtocolIssueCodes(report.DataProtocols),
                Observed = ToObservedElement(report.DataProtocols),
            },
            new()
            {
                Name = "transport_gates.operator_next_actions",
                Status = report.OperatorNextActions.GateCount == 0 ? "pass" : "planned",
                Evidence =
                    $"shell={report.OperatorNextActions.Shell}; cwd={report.OperatorNextActions.Cwd}; " +
                    $"gates={report.OperatorNextActions.GateCount}",
                Notes = report.OperatorNextActions.Policy,
                IssueCodes = [],
                Observed = ToObservedElement(report.OperatorNextActions),
            },
        };

        foreach (var termGate in report.TermGates)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = $"transport_gates.term.{termGate.Key}",
                Status = "pass",
                Evidence = termGate.Key,
                Notes = "term gate copied from companion-report projection",
                IssueCodes = [],
                Observed = ExistingJsonElementOrFallback(termGate.Value, termGate.Key),
            });
        }

        foreach (var gate in report.RemainingLiveGates)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = gate.GateId,
                Status = StatusForTransportGate(gate.Status),
                Evidence = gate.Evidence,
                Notes = gate.NextActions.Count == 0
                    ? "no next actions"
                    : $"next_actions={string.Join(", ", gate.NextActions.Select(action => action.ActionId))}",
                IssueCodes = string.IsNullOrWhiteSpace(gate.GateId) ? [] : [gate.GateId],
                Observed = ToObservedElement(gate),
            });

            foreach (var action in gate.NextActions)
            {
                rows.Add(new ConnectivityCheck
                {
                    Name = $"{gate.GateId}.{action.ActionId}",
                    Status = "planned",
                    Evidence = string.IsNullOrWhiteSpace(action.Command.Command)
                        ? string.Join("; ", action.AcceptanceArtifacts)
                        : action.Command.Command,
                    Notes = TransportGateActionNotes(action),
                    IssueCodes = [],
                    Observed = ToObservedElement(action),
                });
            }
        }

        foreach (var issue in report.Issues)
        {
            rows.Add(new ConnectivityCheck
            {
                Name = issue.IssueCode,
                Status = issue.Severity == "error" ? "fail" : "warn",
                Evidence = issue.Message,
                Notes = issue.Severity,
                IssueCodes = string.IsNullOrWhiteSpace(issue.IssueCode) ? [] : [issue.IssueCode],
                Observed = ToObservedElement(issue),
            });
        }

        return rows;
    }

    public static IReadOnlyList<ConnectivityCheck> ForProtocolMatrixProjectionRun(
        ConnectivityProtocolMatrixProjectionRun run)
    {
        var rows = new List<ConnectivityCheck>();
        rows.AddRange(ForCompanionReportProjection(run.Projection));
        rows.AddRange(ForTransportGateReport(run.TransportGates));
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

    public static ConnectivityCheck FirewallElevationCheck(ConnectivityFirewallRuleReport report) =>
        new()
        {
            Name = "host.windows_firewall_rule_elevation",
            Status = !report.Elevation.RequiresAdmin
                ? "pass"
                : report.Elevation.MutationPermitted
                    ? "pass"
                    : "blocked",
            Evidence =
                $"requires_admin={report.Elevation.RequiresAdmin}; " +
                $"current_process_is_elevated={report.Elevation.CurrentProcessIsElevated}; " +
                $"mutation_permitted={report.Elevation.MutationPermitted}" +
                FirewallHandoffEvidenceSuffix(report),
            Notes = FirewallHandoffNotes(report),
            IssueCodes = report.Elevation.BlockedBeforeMutation
                ? ["hostess.issue.connectivity_probe.firewall_rule_requires_elevation"]
                : [],
            Observed = ToObservedElement(report.Elevation),
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

    private static string FirewallHandoffEvidenceSuffix(ConnectivityFirewallRuleReport report)
    {
        var scriptOut = FirstNonEmpty(report.AdminHandoff.ScriptOut, report.Elevation.Handoff.ScriptOut);
        var verifyOut = FirstNonEmpty(report.AdminHandoff.VerifyReportOut, report.Elevation.Handoff.VerifyReportOut);
        var scriptSha = FirstNonEmpty(report.AdminHandoff.ScriptSha256, report.Elevation.Handoff.ScriptSha256);
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(scriptOut))
        {
            parts.Add($"handoff_script={scriptOut}");
        }
        if (!string.IsNullOrWhiteSpace(verifyOut))
        {
            parts.Add($"verify_report={verifyOut}");
        }
        if (!string.IsNullOrWhiteSpace(scriptSha))
        {
            parts.Add($"handoff_sha256={scriptSha}");
        }
        return parts.Count == 0 ? "" : "; " + string.Join("; ", parts);
    }

    private static string FirewallHandoffNotes(ConnectivityFirewallRuleReport report)
    {
        var note = FirstNonEmpty(
            report.AdminHandoff.OperatorNote,
            report.Elevation.Handoff.OperatorAction,
            report.Elevation.Handoff.PowerShellCommand);
        var actionCommand = FirstNonEmpty(
            report.AdminHandoff.HostessActionCommand,
            report.Elevation.Handoff.HostessActionCommand);
        var verifyCommand = FirstNonEmpty(
            report.AdminHandoff.HostessVerifyCommand,
            report.Elevation.Handoff.HostessVerifyCommand);
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(note))
        {
            parts.Add(note);
        }
        if (!string.IsNullOrWhiteSpace(actionCommand))
        {
            parts.Add($"hostess_action={actionCommand}");
        }
        if (!string.IsNullOrWhiteSpace(verifyCommand))
        {
            parts.Add($"hostess_verify={verifyCommand}");
        }
        return string.Join("; ", parts);
    }

    private static string FirstNonEmpty(params string[] values) =>
        values.FirstOrDefault(value => !string.IsNullOrWhiteSpace(value)) ?? "";

    private static string TransportGateActionNotes(CompanionTransportGateNextAction action)
    {
        var parts = new List<string>
        {
            $"authority_owner={action.AuthorityOwner}",
            $"available_now={action.AvailableNow}",
            $"requires_quest_lease={action.RequiresQuestLease}",
            $"requires_elevation={action.RequiresElevation}",
            $"requires_adb_server_lifecycle_lease={action.RequiresAdbServerLifecycleLease}",
            $"mutates_host={action.MutatesHost}",
            $"mutates_device={action.MutatesDevice}",
            $"clears_gate={action.ClearsGateWhenAccepted}",
        };
        if (action.DependsOn.Count > 0)
        {
            parts.Add($"depends_on={string.Join(",", action.DependsOn)}");
        }
        if (action.AcceptanceArtifacts.Count > 0)
        {
            parts.Add($"acceptance_artifacts={string.Join(",", action.AcceptanceArtifacts)}");
        }
        if (!string.IsNullOrWhiteSpace(action.Command.Label))
        {
            parts.Add($"command_label={action.Command.Label}");
        }
        if (!string.IsNullOrWhiteSpace(action.Lease.Resource))
        {
            parts.Add($"lease_resource={action.Lease.Resource}");
        }
        if (!string.IsNullOrWhiteSpace(action.Lease.Duration))
        {
            parts.Add($"lease_duration={action.Lease.Duration}");
        }
        if (!string.IsNullOrWhiteSpace(action.Lease.ReleaseCommand))
        {
            parts.Add($"lease_release={action.Lease.ReleaseCommand}");
        }
        return string.Join("; ", parts);
    }

    private static string TransportGateSummaryNotes(CompanionTransportGateReport report)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(report.ReportPath))
        {
            parts.Add(report.ReportPath);
        }
        if (report.Summary.CompletionBlockers.Count > 0)
        {
            parts.Add($"completion_blockers={string.Join(",", report.Summary.CompletionBlockers)}");
        }
        return string.Join("; ", parts);
    }

    private static string TransportGateDataProtocolStatus(
        CompanionTransportGateDataProtocols dataProtocols)
    {
        if (!dataProtocols.ProtocolMatrixPresent)
        {
            return "warn";
        }
        return dataProtocols.AllRequiredDataProtocolsPromoted ? "pass" : "warn";
    }

    private static string TransportGateDataProtocolEvidence(
        CompanionTransportGateDataProtocols dataProtocols) =>
        "protocol_matrix_present=" + dataProtocols.ProtocolMatrixPresent +
        $"; all_required_data_protocols_promoted={dataProtocols.AllRequiredDataProtocolsPromoted}" +
        $"; required={dataProtocols.RequiredPromotedCount}/{dataProtocols.RequiredCount}" +
        $"; promoted={dataProtocols.PromotedCount}" +
        $"; candidates={dataProtocols.CandidateCount}" +
        $"; missing_gates={dataProtocols.MissingGateCount}";

    private static string TransportGateDataProtocolNotes(
        CompanionTransportGateReport report)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(report.DataProtocols.SourcePath))
        {
            parts.Add($"source={report.DataProtocols.SourcePath}");
        }
        if (!string.IsNullOrWhiteSpace(report.DataProtocols.SourceArtifact))
        {
            parts.Add($"source_artifact={report.DataProtocols.SourceArtifact}");
        }
        if (report.Summary.CompletionBlockers.Count > 0)
        {
            parts.Add($"completion_blockers={string.Join(",", report.Summary.CompletionBlockers)}");
        }
        return string.Join("; ", parts);
    }

    private static List<string> TransportGateDataProtocolIssueCodes(
        CompanionTransportGateDataProtocols dataProtocols)
    {
        var issueCodes = dataProtocols.IssueCodes
            .Where(issueCode => !string.IsNullOrWhiteSpace(issueCode))
            .ToList();
        if (!dataProtocols.ProtocolMatrixPresent)
        {
            issueCodes.Add("hostess.issue.transport_gates.protocol_matrix_missing");
        }
        else if (!dataProtocols.AllRequiredDataProtocolsPromoted)
        {
            issueCodes.Add("hostess.issue.transport_gates.required_data_protocols_not_promoted");
        }
        return issueCodes;
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

    private static string StatusForProtocolGate(string status) => status switch
    {
        "satisfied" => "pass",
        "missing" => "warn",
        "blocked" => "blocked",
        _ => string.IsNullOrWhiteSpace(status) ? "unknown" : status,
    };

    private static string StatusForTransportGate(string status) => status switch
    {
        "satisfied" => "pass",
        "clear" => "pass",
        "cleared" => "pass",
        "pending_live_evidence" => "planned",
        "not_in_current_scope" => "planned",
        "blocked" => "blocked",
        _ => string.IsNullOrWhiteSpace(status) ? "unknown" : status,
    };

    private static List<string> ProtocolIssueCodes(ConnectivityProtocolEvidenceRow row)
    {
        if (row.MissingGates.Count == 0)
        {
            return [];
        }
        var codes = new List<string>(row.MissingGates);
        if (row.RequiredForFoldIn)
        {
            codes.Add("hostess.issue.protocol_evidence_matrix.required_protocol_not_promoted");
        }
        return codes;
    }

    private static string ProjectionEvidence(CompanionReportProjectionRow row)
    {
        var tier = string.IsNullOrWhiteSpace(row.EvidenceTier)
            ? ""
            : $"; tier={row.EvidenceTier}";
        return $"{row.Label}: {row.Evidence}{tier}; authority={row.AuthorityOwner}";
    }

    private static string ProjectionNotes(CompanionReportProjectionRow row)
    {
        var parts = new List<string>();
        if (!string.IsNullOrWhiteSpace(row.Notes))
        {
            parts.Add(row.Notes);
        }
        if (!string.IsNullOrWhiteSpace(row.SourcePath))
        {
            parts.Add($"source={row.SourcePath}");
        }
        if (!string.IsNullOrWhiteSpace(row.SourceSchema))
        {
            parts.Add($"schema={row.SourceSchema}");
        }
        if (row.Required)
        {
            parts.Add("required");
        }
        if (row.IssueCount > 0)
        {
            parts.Add($"issues={row.IssueCount}");
        }
        return string.Join("; ", parts);
    }

    private static JsonElement ProjectionObservedElement(CompanionReportProjectionRow row)
    {
        var details = row.Details.ValueKind == JsonValueKind.Undefined
            ? JsonSerializer.SerializeToElement(new { row.RowId, row.Section, row.Kind })
            : row.Details.Clone();
        var metrics = row.Metrics.ValueKind == JsonValueKind.Undefined
            ? JsonSerializer.SerializeToElement(new { })
            : row.Metrics.Clone();
        return JsonSerializer.SerializeToElement(new
        {
            row.RowId,
            row.Section,
            row.Kind,
            row.Label,
            row.Status,
            row.AuthorityOwner,
            row.EvidenceTier,
            row.SourceArtifact,
            row.SourcePath,
            row.SourceSchema,
            row.Required,
            row.Evidence,
            row.Notes,
            row.IssueCount,
            row.IssueCodes,
            Metrics = metrics,
            Details = details,
        });
    }

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
