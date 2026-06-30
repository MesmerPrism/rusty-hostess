using System.Text.Json;
using HostessCompanion.Wpf.Models;

internal static class TransportGateReportFixtures
{
    public static CompanionTransportGateReport PendingWithNextActions() =>
        new()
        {
            Schema = "rusty.hostess.companion.transport_gate_report.v1",
            Status = "warn",
            ReportId = "transport-gates.test",
            ReportPath = "target/companion-report/transport-gates.json",
            ValidationReportPath = "target/companion-report/transport-gates.validation-report.json",
            ValidationReport = new CompanionTransportGateValidationReport
            {
                Schema = "rusty.hostess.companion.transport_gate_report.validation.v1",
                Status = "pass",
                ReportId = "transport-gates.test",
                SourceProjection = "target/companion-report/projection.json",
                RemainingGateCount = 4,
                AllRequiredDataProtocolsPromoted = false,
                AllWpfTransportAndProtocolGatesClear = false,
                Warnings =
                [
                    "required data protocols are not all promoted",
                    "transport gate remains pending: transport.general_websocket_capability",
                    "transport gate remains pending: transport.direct_wifi_live_topology",
                    "transport gate remains pending: transport.product_tcp_media_over_direct_wifi",
                    "transport gate remains pending: transport.product_tcp_media_listener_firewall",
                ],
                Issues =
                [
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.transport_gates.required_data_protocols_not_promoted",
                        Severity = "warning",
                        Message = "required data protocols are not all promoted",
                    },
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.transport_gates.gate_pending",
                        Severity = "warning",
                        Message = "transport gate remains pending: transport.general_websocket_capability",
                    },
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.transport_gates.gate_pending",
                        Severity = "warning",
                        Message = "transport gate remains pending: transport.direct_wifi_live_topology",
                    },
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.transport_gates.gate_pending",
                        Severity = "warning",
                        Message = "transport gate remains pending: transport.product_tcp_media_over_direct_wifi",
                    },
                    new CommandIssue
                    {
                        IssueCode = "hostess.issue.transport_gates.gate_pending",
                        Severity = "warning",
                        Message = "transport gate remains pending: transport.product_tcp_media_listener_firewall",
                    },
                ],
            },
            Authority = new CompanionTransportGateAuthority
            {
                ProjectionOnly = true,
                AcceptanceOwner = "source_projection",
            },
            SourceProjection = new CompanionTransportGateSourceProjection
            {
                ProjectionId = "projection.test",
                Schema = "rusty.hostess.companion.report_projection.v1",
                Path = "target/companion-report/projection.json",
            },
            Summary = new CompanionTransportGateSummary
            {
                AllTransportGatesClear = false,
                AllRequiredDataProtocolsPromoted = false,
                AllWpfTransportAndProtocolGatesClear = false,
                CompletionBlockers =
            [
                "protocol_matrix.required_data_protocols",
                "transport.general_websocket_capability",
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_over_direct_wifi",
                "transport.product_tcp_media_listener_firewall",
            ],
                RemainingGateCount = 4,
                RemainingGateIds =
            [
                "transport.general_websocket_capability",
                "transport.direct_wifi_live_topology",
                "transport.product_tcp_media_over_direct_wifi",
                "transport.product_tcp_media_listener_firewall",
            ],
                TermGateCount = 2,
                TermGateIds = ["websocket", "wifi_direct"],
            },
            DataProtocols = new CompanionTransportGateDataProtocols
            {
                ProtocolMatrixPresent = true,
                RowId = "protocol_matrix.summary",
                Status = "warn",
                SourceArtifact = "protocol_matrix",
                SourcePath = "target/connectivity-probe/protocol-matrix.json",
                AllRequiredDataProtocolsPromoted = false,
                RequiredPromotedCount = 4,
                RequiredCount = 5,
                PromotedCount = 7,
                CandidateCount = 1,
                MissingGateCount = 1,
                IssueCount = 1,
                IssueCodes = ["hostess.issue.protocol_evidence_matrix.required_protocol_not_promoted"],
            },
            OperatorNextActions = new CompanionTransportGateOperatorActions
            {
                Shell = "powershell",
                Cwd = "<rusty-hostess-root>",
                GateCount = 4,
                Policy = "Hostess-owned CLI routes only",
                Gates =
            [
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.general_websocket_capability",
                    NextActionIds =
                    [
                        "run_qcl079_host_loopback_websocket",
                        "run_qcl079_broker_owned_websocket",
                    ],
                },
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.direct_wifi_live_topology",
                    NextActionIds =
                    [
                        "write_direct_wifi_product_media_acceptance_plan",
                        "plan_qcl040_wifi_direct_lifecycle",
                        "plan_qcl041_wifi_direct_lifecycle",
                        "run_qcl041_live_wifi_direct_preflight",
                        "normalize_qcl040_wifi_direct_lifecycle_report",
                        "normalize_qcl041_wifi_direct_lifecycle_report",
                    ],
                },
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.product_tcp_media_over_direct_wifi",
                    NextActionIds =
                    [
                        "write_qcl082_product_media_direct_wifi_plan",
                        "write_direct_wifi_product_media_acceptance_plan",
                        "write_qcl082_media_stream_start_source_request",
                        "run_qcl082_media_stream_start_source",
                        "validate_qcl082_media_stream_runtime_status",
                        "capture_rmanvid1_over_promoted_direct_wifi",
                        "promote_qcl082_rmanvid1_capture",
                    ],
                },
                new CompanionTransportGateActionSummary
                {
                    GateId = "transport.product_tcp_media_listener_firewall",
                    NextActionIds = ["verify_qcl082_product_firewall_rule"],
                },
            ],
            },
            TermGates = new Dictionary<string, JsonElement>
            {
                ["websocket"] = JsonSerializer.SerializeToElement(new
                {
                    scope = "manifold_command_session_receipts_and_qcl079_generic_protocol_fit",
                }),
                ["wifi_direct"] = JsonSerializer.SerializeToElement(new
                {
                    scope = "qcl040_qcl041_topology_evidence",
                }),
            },
            RemainingLiveGates =
        [
            new CompanionTransportGate
            {
                GateId = "transport.general_websocket_capability",
                Status = "pending_live_evidence",
                Evidence = "needs broker-owned or Quest-runtime generic WebSocket endpoint evidence",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl079_host_loopback_websocket",
                        Label = "Run QCL-079 host loopback",
                        AuthorityOwner = "tools.hostessctl.connectivity_websocket",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl079-live-host-loopback.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Run QCL-079 host loopback",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source host-loopback --out target\\connectivity-probe\\qcl079-live-host-loopback.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl079_broker_owned_websocket",
                        Label = "Run QCL-079 broker-owned WebSocket",
                        AuthorityOwner = "tools.hostessctl.connectivity_websocket",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl079-live-broker-owned-websocket.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Run QCL-079 broker-owned WebSocket",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor '<manifold-stream-websocket-route>' --websocket-route-evidence '<manifold-stream-websocket-evidence>' --out target\\connectivity-probe\\qcl079-live-broker-owned-websocket.json --fail-on-error",
                        },
                    },
                ],
            },
            new CompanionTransportGate
            {
                GateId = "transport.direct_wifi_live_topology",
                Status = "pending_live_evidence",
                Evidence = "needs live peer lifecycle",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "plan_qcl041_wifi_direct_lifecycle",
                        Label = "Write QCL-041 lifecycle execution plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe wifi-direct-lifecycle-plan --probe-id QCL-041 --out target\\connectivity-probe\\qcl041-wifi-direct-lifecycle-plan.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_direct_wifi_product_media_acceptance_plan",
                        Label = "Write direct-Wi-Fi product-media acceptance plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe direct-wifi-product-media-plan --out target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json --qcl041-topology-report target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl041_live_wifi_direct_preflight",
                        Label = "Run QCL-041 live preflight",
                        RequiresQuestLease = true,
                        RequiresAdbServerLifecycleLease = false,
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode live --probe-id QCL-041 --adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe --serial '<quest-serial>'",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "normalize_qcl040_wifi_direct_lifecycle_report",
                        Label = "Build QCL-040 lifecycle topology report",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-040 --wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>' --out target\\connectivity-probe\\qcl040-live-wifi-direct-lifecycle.json --fail-on-error",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "normalize_qcl041_wifi_direct_lifecycle_report",
                        Label = "Build QCL-041 lifecycle topology report",
                        AuthorityOwner = "tools.hostessctl.connectivity_topology_lifecycle",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-041 --wifi-direct-lifecycle-report '<wifi-direct-lifecycle-report>' --out target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --fail-on-error",
                        },
                    },
                ],
            },
            new CompanionTransportGate
            {
                GateId = "transport.product_tcp_media_over_direct_wifi",
                Status = "pending_live_evidence",
                Evidence = "needs product TCP media over promoted direct Wi-Fi",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_qcl082_product_media_direct_wifi_plan",
                        Label = "Write QCL-082 product media plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_media_product_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write QCL-082 product media plan",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe qcl082-product-media-plan --out target\\connectivity-probe\\qcl082-product-media-direct-wifi-plan.json --promoted-topology-report '<promoted-qcl040-or-qcl041-topology-report>' --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_direct_wifi_product_media_acceptance_plan",
                        Label = "Write direct-Wi-Fi product-media acceptance plan",
                        AuthorityOwner = "tools.hostessctl.connectivity_direct_wifi_product_media_plan",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write direct-Wi-Fi product-media acceptance plan",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe direct-wifi-product-media-plan --out target\\connectivity-probe\\direct-wifi-product-media-acceptance-plan.json --qcl041-topology-report target\\connectivity-probe\\qcl041-live-wifi-direct-lifecycle.json --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --qcl082-report target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "write_qcl082_media_stream_start_source_request",
                        Label = "Write QCL-082 start_source request",
                        AuthorityOwner = "tools.hostessctl.bridge_command_routes",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream-start-source.request.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Write QCL-082 start_source request",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py emit-bridge-command-request --bridge-command command.media_stream.start_source --request-id request.hostess.qcl082.media_stream.start_source --evidence-id evidence.hostess.qcl082.media_stream.start_source --route-id bridge_route.command.websocket.applied --required-stage sent --required-stage transport_ok --required-stage authority_accepted --out target\\connectivity-probe\\media-stream-start-source.request.json",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl082_media_stream_start_source",
                        Label = "Run QCL-082 media-stream start_source",
                        AuthorityOwner = "tools.hostessctl.bridge_command_live_android_routes",
                        RequiresQuestLease = true,
                        MutatesHost = true,
                        MutatesDevice = true,
                        DependsOn =
                        [
                            "transport.direct_wifi_live_topology",
                            "transport.product_tcp_media_listener_firewall",
                        ],
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream-start-source.request.json",
                            "target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json",
                            "target\\connectivity-probe\\media-stream-start-source.live-android-execution.json",
                            "target\\connectivity-probe\\media-stream-start-source.validation-report.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Run QCL-082 media-stream start_source",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py run-bridge-command-live-android --input target\\connectivity-probe\\media-stream-start-source.request.json --out target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json --execution-out target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --validation-out target\\connectivity-probe\\media-stream-start-source.validation-report.json --adb S:\\Work\\tools\\Android\\windows-sdk\\platform-tools\\adb.exe --serial '<quest-serial>'",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "validate_qcl082_media_stream_runtime_status",
                        Label = "Validate QCL-082 media runtime status",
                        AuthorityOwner = "tools.hostessctl.connectivity_media",
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-media-stream-runtime-status.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Validate QCL-082 media runtime status",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-082 --media-stream-runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --out target\\connectivity-probe\\qcl082-media-stream-runtime-status.json --fail-on-error",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "run_qcl082_product_media_live_session",
                        Label = "Run QCL-082 product media live session",
                        AuthorityOwner = "tools.hostessctl.connectivity_media_receiver",
                        RequiresQuestLease = true,
                        MutatesDevice = true,
                        DependsOn =
                        [
                            "transport.direct_wifi_live_topology",
                            "transport.product_tcp_media_listener_firewall",
                        ],
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream-start-source.request.json",
                            "target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json",
                            "target\\connectivity-probe\\media-stream-start-source.live-android-execution.json",
                            "target\\connectivity-probe\\media-stream-start-source.validation-report.json",
                            "target\\connectivity-probe\\media-stream.rmanvid1",
                            "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                            "target\\connectivity-probe\\media-stream-receiver-result.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Run QCL-082 product media live session",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe qcl082-product-media-live-session --bridge-command command.media_stream.start_source --start-source-request-out target\\connectivity-probe\\media-stream-start-source.request.json --bridge-evidence-out target\\connectivity-probe\\media-stream-start-source.bridge-evidence.json --execution-out target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --validation-out target\\connectivity-probe\\media-stream-start-source.validation-report.json --capture-out target\\connectivity-probe\\media-stream.rmanvid1 --sidecar-out target\\connectivity-probe\\media-stream-receiver-sidecar.json --topology-report '<promoted-qcl040-or-qcl041-topology-report>' --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --adb '<adb>' --serial '<quest-serial>' --out target\\connectivity-probe\\media-stream-receiver-result.json",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "capture_rmanvid1_over_promoted_direct_wifi",
                        Label = "Capture RMANVID1 receiver counters",
                        AuthorityOwner = "tools.hostessctl.connectivity_media_receiver",
                        RequiresQuestLease = true,
                        MutatesDevice = true,
                        DependsOn =
                        [
                            "transport.direct_wifi_live_topology",
                            "transport.product_tcp_media_listener_firewall",
                        ],
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\media-stream.rmanvid1",
                            "target\\connectivity-probe\\media-stream-receiver-sidecar.json",
                            "target\\connectivity-probe\\media-stream-receiver-result.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Capture RMANVID1 receiver counters",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe rmanvid1-receiver-capture --runtime-status target\\connectivity-probe\\media-stream-start-source.live-android-execution.json --topology-report '<promoted-qcl040-or-qcl041-topology-report>' --firewall-report target\\connectivity-probe\\qcl082-tcp-firewall-admin-handoff-verify.json --out target\\connectivity-probe\\media-stream-receiver-result.json",
                        },
                        Lease = new CompanionTransportGateNextActionLease
                        {
                            Manager = "Agent Board",
                            Resource = "quest:<quest-serial>",
                            Duration = "45m",
                            ReleaseCommand = "& 'S:\\Work\\agent-bureau\\scripts\\agent-board.ps1' release '<quest-lease-id>' --result done",
                        },
                    },
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "promote_qcl082_rmanvid1_capture",
                        Label = "Build QCL-082 product media report",
                        AuthorityOwner = "tools.hostessctl.connectivity_probe",
                        ClearsGateWhenAccepted = true,
                        AcceptanceArtifacts =
                        [
                            "target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json",
                        ],
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Label = "Build QCL-082 product media report",
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe run --mode fixture --probe-id QCL-082 --media-stream-receiver-result target\\connectivity-probe\\media-stream-receiver-result.json --out target\\connectivity-probe\\qcl082-rmanvid1-receiver-capture.json --fail-on-error",
                        },
                    },
                ],
            },
            new CompanionTransportGate
            {
                GateId = "transport.product_tcp_media_listener_firewall",
                Status = "pending_live_evidence",
                Evidence = "needs product listener firewall rule",
                NextActions =
                [
                    new CompanionTransportGateNextAction
                    {
                        ActionId = "verify_qcl082_product_firewall_rule",
                        Label = "Verify product listener rule",
                        RequiresElevation = false,
                        Command = new CompanionTransportGateNextActionCommand
                        {
                            Shell = "powershell",
                            Command = "python tools\\hostessctl\\hostessctl.py connectivity-probe windows-firewall-rule --action verify --rule-profile qcl-082-rmanvid1-media",
                        },
                    },
                ],
            },
        ],
        };
}
