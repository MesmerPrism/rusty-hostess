# Windows Companion WPF

`apps/hostess-companion-wpf` is the Windows companion shell. It is an
operational frontend over Hostess reports, Rusty GUI companion descriptors, and
Hostess/Manifold evidence routes.

## Current Scope

- Readiness view.
- Session view derived from `rusty.hostess.companion.session.v1` phases.
- Devices view derived from readiness device/runtime/network checks and
  Quest device-link artifacts.
- Transports view derived from Rusty GUI transport capability descriptors and
  Quest device-link stream capability rows.
- Commands view for the Quest broker-stream bridge probe.
- Connectivity view for scoped Windows Firewall planning, QCL-010 TCP
  verification, and QCL-080 UDP stream-capability verification.
- Evidence view derived from companion module evidence bindings.
- Workspaces view derived from Rusty GUI companion workspace descriptors.
- Hostess `companion-readiness` refresh command.
- Hostess `companion-catalog` descriptor refresh command.
- Hostess `companion-session run` command for the reusable session
  orchestration path.
- Hostess `run-bridge-command-live-android` safe probe command, with
  app-private Android staging as the recovery path.
- Hostess `connectivity-probe` commands for firewall rule artifacts and
  same-Wi-Fi connectivity reports.
- Optional Quest profile and broker probe switches.
- Serial input for serial-scoped ADB checks.
- Page-specific tables with a shared selected-row detail inspector.

## Viewmodel Map

`MainWindowViewModel` is the WPF coordinator and compatibility facade for XAML
bindings. Service calls, busy state, aggregate status labels, navigation, and
operator commands stay there. Page row ownership and report-to-row projection
live in focused page viewmodels:

- `ReadinessPageViewModel`: readiness checks and refresh failure rows.
- `DevicesPageViewModel`: readiness-derived device/runtime/network rows and
  `rusty.quest.device_link.v1` device rows.
- `ConnectivityPageViewModel`: firewall, QCL, suite, and failure rows.
- `SessionPageViewModel`: session history, phases, artifact expansion, and
  session failure rows.
- `TransportsPageViewModel`: catalog transport rows and device-link transport
  capability rows.
- `CommandsPageViewModel`: command stage and command issue rows.
- `EvidencePageViewModel`: module evidence artifact rows.
- `WorkspacesPageViewModel`: workspace composition rows from catalog
  descriptors.

The legacy collection and selection properties on `MainWindowViewModel` remain
as pass-through bindings for XAML stability. New page behavior should be added
to the owning page viewmodel first, then surfaced through the window facade
only when existing bindings or command coordination require it.

## Authority Boundary

The WPF app is a requester and inspector. It does not decide that dependencies,
device state, broker routes, app-private receipts, or runtime behavior are
valid.

Every operator-visible WPF action must map to a CLI-equivalent Hostess route or
to a future local API route that calls the same implementation path. The UI may
collect parameters, show progress, and project evidence, but acceptance comes
from the route's structured report, sidecar, receipt, or validation artifact.
Automated tests should exercise the CLI/API route or its fixture output, then
verify that WPF viewmodels render the same evidence a human operator sees.
Read-only WPF report views follow the same rule: they render CLI/API reports,
descriptors, sidecars, receipts, or fixture outputs, and their projection tests
must prove the operator-facing rows map back to that evidence.
The durable action map lives in
`apps/hostess-companion-wpf/ViewModels/OperatorActionCatalog.cs`; the WPF test
suite reflects over `MainWindowViewModel` commands and fails when a command is
added without a CLI-equivalent route and evidence artifact.

All readiness state comes from:

```powershell
python tools\hostessctl\hostessctl.py companion-readiness --out target\companion-readiness\wpf-readiness.json
```

Descriptor catalog state comes from:

```powershell
python tools\hostessctl\hostessctl.py companion-catalog --out target\companion-catalog\wpf-catalog.json
```

The shell reads `rusty.hostess.companion.readiness_report.v1` and
`rusty.hostess.companion.catalog.v1`.
The WPF refresh path intentionally does not pass `--fail-on-error` for the
catalog call, so invalid descriptor evidence can still be rendered for human
inspection. CI and release validation still use `--fail-on-error`.

The Workspaces page renders the `workspaces` section of
`rusty.hostess.companion.catalog.v1`. It shows workspace ids, module counts,
required/prominent composition, supported frontends, sensitivity, and source
paths. It also renders catalog-emitted workspace validation issues such as
unknown module references. Workspace descriptors compose existing modules; WPF
does not fork module implementation, redefine transport semantics, or treat
unresolved module ids as accepted capability.
The same catalog route is also the Makepad parity gate:

```powershell
python tools\hostessctl\hostessctl.py companion-catalog `
  --frontend makepad `
  --out target\companion-catalog\makepad-catalog.json `
  --fail-on-error
```

Makepad-facing panels should consume that report or the same underlying
descriptors. They should not copy WPF setup logic or introduce Makepad-only
command/readiness semantics.

The Session page calls:

```powershell
& 'C:\Users\tillh\Agent Bureau\scripts\agent-board.ps1' reserve quest:REPLACE_WITH_QUEST_SERIAL --duration 45m --task "WPF companion headset session"
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py companion-session run `
  --out target\companion-session\wpf-session.json `
  --frontend wpf `
  --profile hostess-makepad-quest `
  --adb $Adb `
  --serial $QuestSerial `
  --wait-seconds 30 `
  --fallback-wait-seconds 30 `
  --authority-wait-seconds 30 `
  --broker-process-wait-seconds 20 `
  --makepad-process-wait-seconds 20 `
  --socket-wait-seconds 20 `
  --launch-settle-seconds 8 `
  --runtime-subscriber-retry-count 8 `
  --runtime-subscriber-retry-wait-seconds 2
& 'C:\Users\tillh\Agent Bureau\scripts\agent-board.ps1' release 'LEASE_ID_FROM_RESERVE_OUTPUT' --result done
```

It renders the returned ordered phases, actions, issues, and artifact
references from `rusty.hostess.companion.session.v1`. Session orchestration,
fallback recovery, and evidence validation remain in `hostessctl`; WPF only
requests the run and displays the result. The session artifact list also
includes the Quest-owned `rusty.quest.device_link.v1` report, which is the
operator-facing summary for device identity, ADB forward state, broker
readiness, runtime subscriber health, command results, and stream capability
costs.
For QCL-000 promotion, the broker-stream evidence must include
`runtime_accepted` and `applied`; app-private fallback recovery is displayed
for diagnosis but does not satisfy the device-link command authority gate.

When a session report references a `rusty.quest.device_link.v1` artifact, WPF
loads it through `HostessctlSessionService` and projects it into the operator
tables:

- Devices: device identity, host tools, ADB tunnels, broker endpoints, runtime
  subscriber delivery, command-stage evidence, and issues.
- Transports: tunnel routes, broker endpoints, stream capabilities, measured
  costs, preconditions, limitations, and required command evidence stages.

These rows are view projections only. The Quest/Hostess report remains the
source of truth for whether ADB forwarding, `/manifold/v1/events`, runtime
subscriber delivery, or `sent -> transport_ok -> authority_accepted ->
runtime_accepted -> applied` command stages actually passed.

The Commands page safe probe calls:

```powershell
& 'C:\Users\tillh\Agent Bureau\scripts\agent-board.ps1' reserve quest:REPLACE_WITH_QUEST_SERIAL --duration 30m --task "WPF command probe"
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py run-bridge-command-live-android `
  --input fixtures\bridge-command\hostess-broker-stream-command-request.json `
  --out target\companion-command\wpf-broker-stream-probe-evidence.json `
  --adb $Adb `
  --serial $QuestSerial
& 'C:\Users\tillh\Agent Bureau\scripts\agent-board.ps1' release 'LEASE_ID_FROM_RESERVE_OUTPUT' --result done
```

It displays the Hostess execution sidecar stages instead of deciding command
success in WPF. The route starts the Quest broker, prepares the host ADB
forward, starts Hostess Makepad, waits for the forwarded broker socket, and then
uses the reusable broker-stream path. That path dispatches through
`stream.hostess.makepad.bridge_command` and listens for
`stream.hostess.makepad.bridge_command.receipt`.

If the broker-stream execution does not produce a passing sidecar, the button
falls back to:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py run-bridge-command-android `
  --input fixtures\bridge-command\hostess-android-hotload-command-request.json `
  --out target\companion-command\wpf-app-private-probe-evidence.json `
  --adb $Adb `
  --serial $QuestSerial
```

That fallback is app-private runtime staging. It is useful for recovery and
runtime receipt debugging, but it is not Manifold command authority.

The Connectivity page calls the same Hostess-owned probe routes. For TCP, it
keeps QCL-010 available:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
$TcpEchoPort = 18766
$RunId = 'wpf-qcl010-live'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-010 `
  --adb $Adb `
  --serial $QuestSerial `
  --tcp-echo-port $TcpEchoPort `
  --out "target\connectivity-probe\$RunId.json"
```

Firewall rule lifecycle is Hostess-owned. WPF plans, applies, verifies, and
removes scoped product listener rules by requesting
`connectivity-probe windows-firewall-rule`; it does not run ad hoc firewall
logic in button handlers. The product UDP rule uses the WPF executable, fixed
UDP port `18767`, the selected Windows profile, and `LocalSubnet`:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe windows-firewall-rule `
  --action verify `
  --program apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --protocol UDP `
  --port 18767 `
  --profile Public `
  --remote-address LocalSubnet `
  --rule-name "Rusty Hostess WPF QCL-080 UDP Freshness 18767" `
  --out target\connectivity-probe\wpf-qcl080-udp-firewall-verify.json
```

Use `--action apply` or `--action remove` for elevated lifecycle changes. The
CLI report includes an `elevation` preflight; when the current process is not
elevated, Hostess blocks before mutation with
`hostess.issue.connectivity_probe.firewall_rule_requires_elevation` and WPF
renders that row instead of pretending the rule was applied. Verification
records `product_rule_verified` separately from generic
`allowed_on_active_profile`, so broad port-only rules and diagnostic Python
rules do not satisfy product readiness.
For mutating apply/remove requests, WPF asks the same route to write a `.ps1`
admin handoff and matching verify report with `--handoff-script-out` and
`--handoff-verify-out`. In a normal shell this returns a blocked preflight
report plus the generated script; if WPF itself is already elevated, the same
Hostess CLI route may perform the mutation. WPF does not own a private `runas`
launcher or embed separate firewall business logic.
The plan report also carries the matching QCL-080 probe arguments, including
the WPF listener executable as `--udp-listener-helper`, so a human operator and
CLI automation follow the same product-owned listener route.
The WPF rule-profile selector is the UI projection of the same CLI contract:
`custom`, `qcl-010-tcp-echo`, `qcl-080-udp-freshness`, and
`qcl-082-rmanvid1-media`. Selecting the QCL-082 profile projects TCP port
`9079`, rule `Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079`, and the
CLI-owned `--rule-profile qcl-082-rmanvid1-media` plan/verify/remove route.
WPF still only collects parameters, requests Hostess CLI, and renders the
returned `rusty.quest.connectivity_windows_firewall_rule.v1` artifact.

For UDP, the page uses QCL-080 with the WPF executable itself in listener
helper mode:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
$RunId = 'wpf-qcl080-live'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-080 `
  --run-id $RunId `
  --adb $Adb `
  --serial $QuestSerial `
  --udp-port 18767 `
  --udp-sender-source makepad-runtime `
  --udp-listener-helper apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --out "target\connectivity-probe\$RunId.json"
```

It then derives the reusable stream descriptor:

```powershell
$RunId = 'wpf-qcl080-live'
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability `
  --input "target\connectivity-probe\$RunId.json" `
  --out "target\connectivity-probe\$RunId.stream-capability.json" `
  --fail-on-error
```

The WPF app renders the report checks plus the
`rusty.quest.device_link.stream_capability.v1` descriptor requirements and
warnings. WPF does not decide that UDP is product-ready; it displays Hostess
firewall evidence, Makepad runtime sender evidence, packet counters, promotion
state, and remaining warnings. The route materializes a default run id before
Makepad runtime sender setup, but automation should still pass `--run-id`
explicitly so the app-owned runtime marker can be matched to the report.

The page can also request the installer-style suite runner:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run-suite `
  --mode fixture `
  --suite-id wpf-connectivity-suite `
  --out target\connectivity-probe\wpf-connectivity-suite.json
```

WPF renders the resulting
`rusty.quest.device_link.install_environment_suite_run.v1` summary, grouped
phase rows, per-QCL slot rows, metrics, and artifact paths. Fixture suite
success proves the diagnostic harness is coherent; live protocol promotion
still comes from the individual QCL reports and stream capability descriptors.
The suite includes QCL-079 as a generic WebSocket protocol-fit slot; it is
separate from QCL-000 Manifold command/session WebSocket authority.

The Protocol Matrix action keeps that split explicit. WPF first requests the
fixture suite, generates QCL-020/QCL-030/QCL-040/QCL-041 topology limitation
fixture reports, refreshes the QCL-082 Rusty Quest media-stream source-contract
report when the sibling plan exists, accepts QCL-082 broker/runtime status
artifacts when present, and generates a read-only QCL-082 product firewall
verify report for the Hostess/WPF executable. It then shells to the CLI roll-up
with explicit topology inputs and the shared latest-artifact resolver. QCL-000
fixture WebSocket
evidence remains candidate-only; QCL-000 promotion comes from a live
`rusty.quest.device_link.v1` companion-session artifact. QCL-079 generic
WebSocket host-loopback evidence is also candidate-only; it answers protocol
fit without promoting command authority or media transport:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-079 `
  --websocket-source host-loopback `
  --out target\connectivity-probe\qcl079-live-host-loopback.json
```

When the sibling Manifold repo has the generic stream route descriptor and
evidence fixture, WPF and CLI automation can promote QCL-079 as broker-owned
without treating the Manifold command WebSocket as generic data:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-079 `
  --websocket-source broker-owned-websocket `
  --websocket-route-descriptor S:\Work\repos\active\rusty-manifold\fixtures\bridge-route\stream-websocket-ordered-route.json `
  --websocket-route-evidence S:\Work\repos\active\rusty-manifold\fixtures\bridge-route\stream-websocket-ordered-evidence.json `
  --out target\connectivity-probe\qcl079-live-manifold-websocket-broker.json `
  --fail-on-error
```

When the Rusty Quest media/display streaming branch is present, WPF and CLI
automation use the same source-contract refresh route to translate the
source-neutral media-stream session plan:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-session-plan S:\Work\repos\active\rusty-quest\fixtures\media-stream-sessions\display-composite-mediaprojection-h264.plan.json `
  --out target\connectivity-probe\qcl082-media-stream-session-plan.json `
  --fail-on-error
```

Broker/runtime status artifacts from the same branch use a second
CLI-equivalent route. This is broker-owned candidate evidence for command
acceptance, source/runtime state, consent or lab-only gating, and binary-plane
policy; it still does not promote QCL-082 without measured receiver counters.
When using the connected-Quest route, first write the inspectable
`rusty.hostess.bridge_command.request.v1` command artifact and run the
Manifold bridge command. The resulting live Android execution sidecar carries
the accepted command ACK and can be supplied directly to
`--media-stream-runtime-status`:

```powershell
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
python tools\hostessctl\hostessctl.py emit-bridge-command-request `
  --bridge-command command.media_stream.start_source `
  --request-id request.hostess.qcl082.media_stream.start_source `
  --evidence-id evidence.hostess.qcl082.media_stream.start_source `
  --route-id bridge_route.command.websocket.applied `
  --required-stage sent `
  --required-stage transport_ok `
  --required-stage authority_accepted `
  --out target\connectivity-probe\media-stream-start-source.request.json

python tools\hostessctl\hostessctl.py run-bridge-command-live-android `
  --input target\connectivity-probe\media-stream-start-source.request.json `
  --out target\connectivity-probe\media-stream-start-source.bridge-evidence.json `
  --execution-out target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --validation-out target\connectivity-probe\media-stream-start-source.validation-report.json `
  --adb $Adb `
  --serial $QuestSerial

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-runtime-status target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --out target\connectivity-probe\qcl082-media-stream-runtime-status.json `
  --fail-on-error
```

Receiver-counter evidence uses a third CLI-equivalent route. Hostess first
arms a bounded TCP `RMANVID1` receiver, writes the raw capture and receiver
sidecar/result artifacts, then parses the bounded stream header and packet
records into the QCL report. WPF should only render the generated report
through protocol-matrix/projection; it must not parse binary media itself. To
prove product TCP media over direct Wi-Fi, pair the receiver with a QCL-040 or
QCL-041 topology report. To prove product listener readiness, also pass a
verified Hostess/WPF TCP listener firewall report. Unpromoted topology or
missing/product-mismatched firewall evidence keeps the product gates visible
instead of letting WPF infer readiness from separate TCP, firewall, and Wi-Fi
Direct rows:

Direct-Wi-Fi topology has a read-only plan artifact before any live headset or
peer-harness work. WPF renders the same plan route and must not infer topology
readiness from TCP, Wi-Fi, or preflight rows:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py connectivity-probe wifi-direct-lifecycle-plan `
  --probe-id QCL-041 `
  --out target\connectivity-probe\qcl041-wifi-direct-lifecycle-plan.json `
  --adb $Adb `
  --serial $QuestSerial
```

Before a live product-media attempt, write the read-only Hostess plan artifact.
It binds the same PowerShell commands, dependencies, Quest lease policy, and
acceptance artifacts WPF renders, but it does not run headset commands or clear
the pending gates:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe qcl082-product-media-plan `
  --out target\connectivity-probe\qcl082-product-media-direct-wifi-plan.json `
  --promoted-topology-report target\connectivity-probe\wpf-connectivity-suite.qcl040-wifi-direct-phone-peer-pass.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --adb $Adb `
  --serial $QuestSerial
```

If the verification report has `product_rule_verified=false`, generate the
admin handoff from the same Hostess CLI route, then run the generated script
from an elevated PowerShell session. A non-elevated apply produces a blocked
report with `elevation.blocked_before_mutation=true`, no attempted mutation,
and the handoff script/verify paths WPF projects for the operator. WPF must not
create firewall rules through hidden UI logic.

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe windows-firewall-rule `
  --action verify `
  --rule-profile qcl-082-rmanvid1-media `
  --program apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --out target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe rmanvid1-receiver-capture `
  --bind-host 0.0.0.0 `
  --port 9079 `
  --capture-out target\connectivity-probe\media-stream.rmanvid1 `
  --sidecar-out target\connectivity-probe\media-stream-receiver-sidecar.json `
  --runtime-status target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --topology-report target\connectivity-probe\wpf-connectivity-suite.qcl040-wifi-direct-phone-peer-pass.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --capture-kind live_broker_stream `
  --max-packets 240 `
  --out target\connectivity-probe\media-stream-receiver-result.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-rmanvid1-capture target\connectivity-probe\media-stream.rmanvid1 `
  --media-stream-receiver-sidecar target\connectivity-probe\media-stream-receiver-sidecar.json `
  --media-stream-runtime-status target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --media-stream-topology-report target\connectivity-probe\wpf-connectivity-suite.qcl040-wifi-direct-phone-peer-pass.json `
  --media-stream-firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --out target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json `
  --fail-on-error
```

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix `
  --suite-run target\connectivity-probe\wpf-connectivity-suite.json `
  --input target\connectivity-probe\wpf-connectivity-suite.qcl020-wifi-adb-session-pass.json `
  --input target\connectivity-probe\wpf-connectivity-suite.qcl030-local-only-hotspot-started.json `
  --input target\connectivity-probe\wpf-connectivity-suite.qcl040-wifi-direct-phone-peer-pass.json `
  --input target\connectivity-probe\wpf-connectivity-suite.qcl041-wifi-direct-windows-peer-pass.json `
  --latest-artifact-dir target\connectivity-probe `
  --latest-probe-id QCL-000 `
  --latest-probe-id QCL-010 `
  --latest-probe-id QCL-011 `
  --latest-probe-id QCL-020 `
  --latest-probe-id QCL-030 `
  --latest-probe-id QCL-040 `
  --latest-probe-id QCL-041 `
  --latest-probe-id QCL-050 `
  --latest-probe-id QCL-051 `
  --latest-probe-id QCL-080 `
  --latest-probe-id QCL-081 `
  --latest-probe-id QCL-082 `
  --latest-probe-id QCL-083 `
  --latest-probe-id QCL-084 `
  --latest-probe-id QCL-079 `
  --latest-device-link-dir target\companion-session `
  --latest-stream-capability-dir target\connectivity-probe `
  --latest-stream-probe-id QCL-080 `
  --out target\connectivity-probe\wpf-connectivity-suite.protocol-matrix.json
```

The resolver recursively selects the newest valid QCL report for each
requested probe id under `--latest-artifact-dir`, preferring independent run
reports over generated `*-artifacts` suite copies during broad scans. It also
selects the newest device-link report from recent companion sessions and the
newest stream descriptor plus its source probe report for requested probe ids.
This
lets the Protocol Matrix action reuse a previous WPF Session run for QCL-000
command authority, previous QCL-050/QCL-051 Bluetooth probe reports, and a
previous QCL-080 stream-capability run for product UDP evidence while also
surfacing the QCL-082 media/binary fixture or Rusty Quest media-stream
source-contract/runtime-status/receiver-counter rows without moving artifact
scanning, binary parsing, or promotion rules into WPF. If those live artifacts
are missing, the fixture suite rows remain visible as candidates with missing
gates.

After the matrix route selects the evidence inputs, WPF asks Hostess for the
shared read-only operator projection:

```powershell
python tools\hostessctl\hostessctl.py companion-report projection `
  --frontend wpf `
  --protocol-matrix target\connectivity-probe\wpf-connectivity-suite.protocol-matrix.json `
  --include-protocol-matrix-inputs `
  --firewall-rule target\connectivity-probe\wpf-connectivity-suite.qcl082-product-firewall-verify.json `
  --suite-run target\connectivity-probe\wpf-connectivity-suite.json `
  --out target\companion-report\wpf-connectivity-suite.projection.json `
  --fail-on-error
```

The CLI projection route derives the device-link and connectivity-probe inputs
from the protocol-matrix source selection when WPF runs the full action. WPF can
still pass explicit `--connectivity-probe` artifacts for standalone topology
views without moving probe execution or promotion rules into UI code. The rows
shown in the Protocol Matrix page come from
`rusty.hostess.companion.report_projection.v1`, so WPF, Makepad-facing tests,
and CLI automation use the same row contract. The projection's
`transport_coverage.summary.details.term_gates` keeps WebSocket scoped to the
Manifold command/session receipt route, or to command receipts plus QCL-079
generic protocol fit when that evidence is present. TCP stays scoped to
QCL-010/QCL-011 echo plus QCL-082 binary media, and Wi-Fi Direct stays scoped
to QCL-040/QCL-041 topology. `remaining_live_gates` names the still-open
generic WebSocket, live direct-Wi-Fi topology, product TCP media over
direct-Wi-Fi, and product TCP listener firewall gates as applicable. A
standalone verified `--firewall-rule` report can clear only the product TCP
listener firewall gate; it does not clear live direct-Wi-Fi topology or product
media over direct Wi-Fi.

Live QCL-040/QCL-041 now has a CLI-equivalent Wi-Fi Direct preflight route, but
that report is intentionally non-promoting until the Quest/peer harness records
peer discovery, group formation, bounded socket exchange, and cleanup evidence.
WPF should render the blocked report and transport gate; it must not infer live
direct-Wi-Fi topology from normal LAN echo rows.

Automation can materialize the same WPF-visible gate state as a standalone
read-only artifact:

```powershell
python tools\hostessctl\hostessctl.py companion-report transport-gates `
  --projection target\companion-report\wpf-connectivity-suite.projection.json `
  --out target\companion-report\wpf-connectivity-suite.transport-gates.json `
  --fail-on-error
```

Use `--fail-on-pending` only for runs that require every transport gate to be
cleared. The command consumes the projection report; it does not run probes,
apply firewall rules, parse media, or promote evidence on behalf of WPF.
Pending gates carry `next_actions` so WPF can show the same CLI-equivalent
PowerShell route automation will use. The action metadata distinguishes
non-elevated handoff generation from elevated firewall mutation, marks
Quest-bound direct-Wi-Fi and product-media actions with `requires_quest_lease`,
projects the Hostess-owned Agent Board reserve/release command metadata, and
keeps ordinary ADB commands serial-scoped. Per-action rows also render the
Hostess authority owner, dependency gates, and acceptance artifacts, so
operators can see that QCL-082 product media depends on promoted direct-Wi-Fi
topology plus product listener firewall evidence before the CLI route can clear
the gate.
The WPF Protocol Matrix button now materializes this report immediately after
`companion-report projection` and appends its summary, term-gate, pending-gate,
and next-action rows to the Connectivity page. It does not use
`--fail-on-pending`; pending transport gates are rendered as operator work
items, while CI or smoke automation can opt into `--fail-on-pending` for a hard
gate.

## Build

```powershell
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
dotnet run --project tests\HostessCompanion.Wpf.Tests\HostessCompanion.Wpf.Tests.csproj
```

The repo-local `tools\check_all.ps1` runs the WPF build and projection tests
when the projects exist.
