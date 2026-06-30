# Architecture

Rusty Hostess T is an install and test shell for Manifold package development.
It is not a new authority layer. It consumes Manifold and package contracts,
executes named validation slots on target hosts, and exports evidence bundles.

## Authority

Manifold owns command descriptors, leases, package/runtime state, stream
registries, audit records, and scorecards.

Hostess T owns platform packaging, permission probes, launch/install routes,
small app UI surfaces, command bridging, and evidence export.

## Current Slice

The first implementation supports one live package slot:

- `live-smoke`: bounded direct-stream capture for the Polar H10 package and
  opt-in processor-module validation for selected package modules.

The Android app embeds selected package manifests as assets, opens the platform
sensor route itself, and writes evidence that includes the package manifest
hash. The desktop script follows the same evidence shape. Both desktop and
Android captures are accepted only after the shared evidence validator compares
the reported manifest hash against the supplied package root.

The intended GUI surface is Makepad. `apps/hostess-t-makepad` seeds from
bounded `TelemetrySnapshot` checkpoint JSON when useful, then watches
append-only `TelemetryStreamEvent` JSONL and maintains rolling buffers per
datastream. It is the first scalable Rusty GUI example for Hostess T. It
observes run state and can request commands only through the same
Hostess/Manifold command routes as `hostessctl`.
`apps/hostess-t-makepad/src/companion_frontend.rs` owns the source/fixture-only
Makepad projection of Hostess companion catalog, Quest device-link, protocol
evidence matrix, and companion-report projection reports. It reduces
`rusty.hostess.companion.catalog.v1`, `rusty.quest.device_link.v1`,
`rusty.quest.device_link.protocol_evidence_matrix.v1`, and
`rusty.hostess.companion.report_projection.v1` evidence into compact rows and
marker lines for a future Makepad panel; it does not own validation, setup,
transport, artifact selection, protocol promotion, or command authority.

The Windows companion shell lives in `apps/hostess-companion-wpf`. It is a WPF
operational shell over Hostess readiness reports, Rusty GUI companion
descriptors, and Hostess/Manifold bridge-command evidence. It calls
`hostessctl companion-readiness` and `hostessctl companion-catalog`, displays
Readiness, Session, Devices, Transports, Commands, and Evidence tables plus
selected-row details, and does not implement dependency, device, broker,
descriptor, command authority, session orchestration, or runtime acceptance
logic inside WPF handlers.
WPF projection helpers under `apps/hostess-companion-wpf/ViewModels` translate
Hostess connectivity reports and Quest `rusty.quest.device_link.v1` artifacts
into operator rows for Devices, Transports, and Connectivity. Those helpers
keep UI composition reusable while preserving the authority boundary: Hostess
and Quest reports own readiness, stream capabilities, subscriber delivery, and
command-stage truth; WPF only renders and drills into the evidence.
The equivalent source-owned read-only projection route is
`hostessctl companion-report projection`. It emits
`rusty.hostess.companion.report_projection.v1` from explicit device-link,
connectivity-probe, firewall-rule, protocol-matrix, and suite-run source
artifacts. The route is a row-normalizing view contract for WPF, Makepad, CLI
automation, and future frontends; it does not select latest artifacts, validate
QCL source evidence, run probes, change firewall/device state, declare topology
readiness, or re-evaluate protocol promotion gates.
The WPF Protocol Matrix action first requests the fixture suite, generates
QCL-020/QCL-030/QCL-040/QCL-041 topology limitation fixture reports, optionally
refreshes the QCL-082 source-contract report from the sibling Rusty Quest
media-stream session plan when that branch is present, accepts broker/runtime
status artifacts through the same Hostess CLI route, runs a read-only
`qcl-082-rmanvid1-media` Windows Firewall verify report for the Hostess/WPF
executable, then requests the Hostess
protocol-matrix route with those topology reports as explicit inputs. After
the matrix is written, WPF requests the read-only
`connectivity-probe direct-wifi-product-media-plan` artifact with the same
topology, firewall, matrix, projection, and transport-gate output paths. That
preserves the CLI route's latest-artifact selection and promotion policy before
WPF passes the suite and matrix artifacts into
`companion-report projection --include-protocol-matrix-inputs --firewall-rule
--direct-wifi-product-media-plan`.
The CLI
projection route derives selected device-link and connectivity-probe inputs
from the matrix, so WPF does not parse matrix sources or own artifact
selection. The projected direct-Wi-Fi product-media plan is a checklist source:
it renders readiness, dependency, and next-step rows, but it does not run ADB,
mutate firewall state, parse media payloads, or promote topology/media gates.
QCL-000 fixture WebSocket evidence is visible as candidate evidence;
promotion still requires live device-link command evidence. Topology report
views can still pass explicit connectivity-probe artifacts through that same
projection route. WPF renders the resulting projection rows through
`ConnectivityRows.ForCompanionReportProjection` so the human page and CLI
automation inspect the same normalized report artifact.
The same Protocol Matrix action then requests
`companion-report transport-gates --projection <projection>` and renders the
resulting `rusty.hostess.companion.transport_gate_report.v1` rows in the
Connectivity page. WPF deserializes `operator_next_actions` and each pending
gate's `next_actions` only as operator-visible guidance; Hostess CLI remains
the owner of the PowerShell command text, elevation flags, Quest lease
requirements, mutation flags, and acceptance artifacts.
`tools.test_hostessctl_companion_transport_gate_actions` validates that the
source-owned next-action catalog keeps direct-Wi-Fi and QCL-082 product-media
commands PowerShell-shaped, output-artifact-backed, serial-scoped, and honest
about elevation, Quest lease, host mutation, device mutation, and dependency
requirements before WPF row-projection tests render those fields.
Page-owned viewmodels keep the row projection families separated:
`ReadinessPageViewModel`, `DevicesPageViewModel`,
`ConnectivityPageViewModel`, `SessionPageViewModel`,
`TransportsPageViewModel`, `CommandsPageViewModel`, and
`EvidencePageViewModel` own their rows and selected-detail state.
`WorkspacesPageViewModel` renders catalog workspace descriptors so operators can
see which modules a workspace composes without letting WPF redefine module or
transport semantics. `MainWindowViewModel` remains the XAML-compatible
coordinator and service requester.
`OperatorActionCatalog` maps each visible WPF command to its Hostess
CLI-equivalent route, evidence artifact, authority owner, and test coverage.
Hostess keeps the machine-readable row source split as
`tools/hostessctl/companion_operator_action_rows.py`, while
`tools/hostessctl/companion_operator_actions.py` owns report assembly and
validation. The row source also carries structured requirement flags for
elevation, Quest lease use, host mutation, device mutation, and
`adb-server:lifecycle`; WPF renders/requesters use those flags as metadata and
do not turn them into a second execution policy.
The equivalent machine-readable catalog is
`hostessctl companion-report operator-actions --frontend wpf`, which emits
`rusty.hostess.companion.operator_action_catalog.v1` without executing the
advertised routes. `HostessCompanion.Wpf.Tests` compares every WPF catalog row
with that CLI report so human-visible buttons, automation recipes, evidence
artifacts, authority labels, and lease/elevation/mutation posture stay locked
together.
Session browsing follows the same rule through `companion-session history`,
which emits `rusty.hostess.companion.session_history.v1`; WPF loads selected
session artifacts after that route has supplied the report index.

The Android-class app shell includes a compact native Canvas telemetry view for
phone and headset profiles, but that view is fallback/debug-only platform
evidence plumbing. Android Java owns Activity lifecycle, direct diagnostic BLE
capture routes, permission UX, ADB intent/file command bridging, app-private
evidence storage, and JNI calls into the Rust runtime. For Quest PMB and
foreground telemetry, physical Polar PMD is broker-owned and Hostess observes
broker streams or computes bounded on-Quest processor evidence; Hostess must
not open a second BLE session for that path. It does not own reusable panel
layout, processor formulas, package state, graph execution, broker provider
authority, or module authority.

The desktop CLI can render equivalent evidence pages from completed run
artifacts. Rendered PNGs must include dimensions, nonblank content evidence,
and a JSON sidecar before they are accepted as visual evidence.
Argument parser construction lives in `tools/hostessctl/cli_parser.py`; it
receives platform defaults from `tools/hostessctl/hostessctl.py` and imports
only argument-surface constants such as
`tools/hostessctl/companion_session_defaults.py`, not command
implementations. The CLI root stays the platform default, dispatch, and
compatibility-wrapper facade.
Shared process helpers live in `tools/hostessctl/runtime.py`, and package
names, Android actions, remote artifact paths, Makepad defaults, and broker
identity helpers live in `tools/hostessctl/platform_defaults.py`.
Live capture, Polar selected-module replay, Android live/replay launch, live
evidence validation, and runtime artifact pulls live in
`tools/hostessctl/live_capture_routes.py`.
Desktop PMB replay, PMB live-route self-test, and PMB shell-handoff validation
live in `tools/hostessctl/pmb_desktop_routes.py`; Android/Quest PMB replay,
controller preflight, and simulated/physical live routes live in
`tools/hostessctl/pmb_android_routes.py`.
Makepad PMB provider setup lives in `tools/hostessctl/makepad_pmb_setup.py`,
and foreground broker telemetry observation lives in
`tools/hostessctl/broker_telemetry_routes.py`.
Telemetry command dispatch, Makepad render pulls, shell-contract launch, and
snapshot command dispatch live in `tools/hostessctl/telemetry_routes.py`.
Desktop PNG rendering, sidecar writing, and render-output validation live in
`tools/hostessctl/telemetry_render.py` so render evidence remains a focused
helper family instead of growing the CLI root.
Quest questionnaire operator bridging lives in
`tools/hostessctl/questionnaire_bridge.py`. It is a low-rate command/status
route for foreground panel requests, not a data-plane path; answer data stays
with the caller-owned `content://` result URI described by the panel contract.
Android shell-file and app-private `run-as` file transport lives in
`tools/hostessctl/android_files.py`, with route-level cleanup and compatibility
facades in `tools/hostessctl/android_artifacts.py`.
Manifold broker WebSocket transport lives in
`tools/hostessctl/broker_transport.py`: handshake/framing, Manifold command
envelopes, ACK normalization, retry connection, and stream-event timestamp
aliasing are isolated from route orchestration. Projected Motion Breath broker
publication and receipt listening live in
`tools/hostessctl/pmb_broker_bridge.py`.
Bridge command execution lives in
`tools/hostessctl/bridge_command_routes.py`. It emits and consumes UI-neutral
`rusty.hostess.bridge_command.request.v1` command request artifacts, sends the
Manifold command envelope through `broker_transport.py`, subscribes to the
selected runtime receipt stream, waits for authority ACK and runtime/applied
receipts, and emits bridge-route evidence. It is the shared backend route that
WPF, Makepad, and future UI shells should call instead of adding UI-local
command request shaping or acceptance logic.
The Hostess Makepad broker-stream runtime consumer lives in
`apps/hostess-t-makepad/src/manifold_bridge_command_subscriber.rs`. It
subscribes to `stream.hostess.makepad.bridge_command`, reuses
`bridge_command_inbox` to apply the benign safe-probe request, and publishes
`rusty.hostess.makepad.bridge_command_runtime_receipt.v1` on
`stream.hostess.makepad.bridge_command.receipt`.
Connected-Quest broker-stream command orchestration lives in
`tools/hostessctl/bridge_command_live_android_routes.py`. It owns the Hostess
setup evidence around the shared command path: launch/check the Quest broker,
prepare the serial-scoped ADB forward, wait for the forwarded broker socket,
launch/check Hostess Makepad, then delegate the actual command to
`bridge_command_routes.py`. WPF, Makepad, and future frontends can request this
route, but they still render the sidecar instead of deciding broker authority
or runtime acceptance themselves.
Quest/Android app-private bridge command proof lives in
`tools/hostessctl/bridge_command_android_routes.py` plus the Hostess Makepad
`bridge_command_inbox` module. It stages the same request shape into the
app-private settings directory with serial-scoped ADB and accepts only the
benign `hostess.makepad.bridge_probe.set_marker` command. This route proves
that the Quest runtime emitted `runtime_accepted` and `applied` receipts, but
it intentionally does not claim Manifold `authority_accepted`; broker-stream
dispatch remains the separate command-authority path.
The broker-authorized Android command route is an explicit bring-up bridge over
that gap: `run-bridge-command-android --broker-authority` first sends the
command envelope to the Manifold broker and requires an accepted ACK, then
stages the app-private runtime delivery request with
`broker_authority_accepted=true`. It records
`sent -> transport_ok -> authority_accepted -> runtime_accepted -> applied`,
but the runtime delivery leg is still app-private JSON. When the selected
authority is the Quest broker APK, `--adb-forward-broker` prepares the host TCP
forward before the WebSocket authority request; the forward is transport setup
evidence, not runtime acceptance.
Bridge-route evidence normalization lives in
`tools/hostessctl/bridge_route_evidence.py`. It converts Hostess route-stage
observations into `rusty.manifold.bridge.route_evidence.v1` and validates the
route-required stages from a Manifold descriptor, explicit CLI requirements, a
Hostess input receipt, or the known bridge-route fixtures. It does not open
sockets, run ADB, launch apps, or decide whether a command is authoritative;
WPF, Makepad, and future frontends can call the same low-rate evidence adapter
and render the resulting validation rows without becoming runtime authority.
Windows companion readiness lives in
`tools/hostessctl/companion_readiness.py`. It emits
`rusty.hostess.companion.readiness_report.v1` for host, toolchain, device,
runtime, broker package/process, ADB forward mapping, forwarded broker socket,
direct broker socket, network, and Rusty GUI descriptor checks. Readiness is
Hostess-owned execution/evidence, not GUI authority: WPF, Makepad, CLI, and
future frontends render the report and may request refreshes, but they do not
decide that ADB, broker routes, app-private receipts, package install state, or
runtime acceptance are valid.
Windows companion descriptor discovery lives in
`tools/hostessctl/companion_catalog.py`. It emits
`rusty.hostess.companion.catalog.v1` from Rusty GUI companion module,
workspace, and transport descriptors, validates that GUI/WPF do not claim
command or route authority, and gives WPF, Makepad, CLI, and future frontends a
shared catalog for module lists, transport costs, and evidence artifact panels.
The same report carries descriptor semantic issues, including workspace
references to unknown modules, so operator frontends can render invalid catalog
evidence without becoming the validator.
The repo-wide check runs the catalog smoke for both `wpf` and `makepad`
frontends. This keeps the Hostess Makepad validation workspace honest: if a
workspace claims Makepad support, its selected modules and required transport
descriptors must survive the same Hostess catalog filtering and validation as
WPF.
Windows companion session orchestration lives in
`tools/hostessctl/companion_session.py`. It emits
`rusty.hostess.companion.session.v1` by composing readiness, descriptor
catalog, connected-Quest broker-stream command probing, app-private fallback
recovery, validation sidecars, and artifact references into ordered phases.
This route is the frontend-neutral session backend for WPF, Makepad, CLI, and
future companion shells; frontends render phases/actions/issues and may request
the run, but they do not decide broker authority, runtime acceptance, fallback
recovery, or evidence validity.
Its receipt/process wait defaults live in
`tools/hostessctl/companion_session_defaults.py` so the parser, CLI docs, and
WPF invocation can share the same argument surface without coupling the parser
to the session orchestration module.
Read-only report projection lives in
`tools/hostessctl/companion_report_projection.py`. It consumes only explicit
artifact paths and copies source status, topology metadata, evidence tier,
promotion state, missing gates, issue codes, and detailed payloads into
frontend-neutral rows.
Transport coverage summarization lives in
`tools/hostessctl/companion_report_transport_coverage.py`. It derives the
`transport_coverage.summary` row from already-projected rows so WebSocket, TCP,
Wi-Fi Direct, other Wi-Fi topologies, and QCL probe IDs stay visible without
moving artifact selection, topology probing, or protocol promotion into the
projection facade or WPF. The same row emits structured `term_gates`: WebSocket
is scoped to Manifold command/session receipts until QCL-079 generic WebSocket
evidence is present, TCP is scoped to QCL-010/QCL-011 echo plus QCL-082 binary
media, and Wi-Fi Direct is scoped to QCL-040/QCL-041 topology evidence.
Broker-owned QCL-079 evidence clears the generic WebSocket gate;
`remaining_live_gates` keeps live direct-Wi-Fi topology and product TCP media
over direct Wi-Fi explicit without turning them into promotion decisions. The
product TCP media
gate clears only when a projected QCL-082 receiver report contains
`protocol.media_product_topology_gate` with
`product_gate=product_tcp_media_over_direct_wifi` and `product_gate_proven=true`.
The product listener firewall gate is distinct: QCL-082 emits
`protocol.media_product_listener_firewall_gate` from a supplied
`connectivity-probe windows-firewall-rule --action verify --rule-profile
qcl-082-rmanvid1-media`
report, or the projection route can consume the same standalone firewall report
through `--firewall-rule`. `transport.product_tcp_media_listener_firewall`
clears only when that report verifies a product-scoped Hostess/WPF executable
rule for the RMANVID1 TCP listener port. The current product rule name is
`Rusty Hostess WPF QCL-082 TCP RMANVID1 Media 9079`. Diagnostic Python
listener allowances stay diagnostic evidence and do not satisfy product
readiness.
Transport gate status automation lives in
`tools/hostessctl/companion_transport_gates.py`. It consumes an existing
`rusty.hostess.companion.report_projection.v1` artifact and emits
`rusty.hostess.companion.transport_gate_report.v1`, including the same
`term_gates` and `remaining_live_gates` WPF renders, plus the
`data_protocols` summary copied from `protocol_matrix.summary`. Pending gates
also carry `next_actions` with PowerShell-compatible Hostess CLI routes,
acceptance artifacts, elevation flags, host/device mutation flags, and
structured Agent Board `quest:<quest-serial>` lease reserve/release metadata
supplied by
`companion_transport_gate_actions.py`. WPF renders the same authority owner,
dependency gates, acceptance artifacts, `data_protocols`,
`completion_blockers`, and strict
`all_wpf_transport_and_protocol_gates_clear` state from the report, including
the QCL-082 product-media dependency on promoted direct-Wi-Fi topology plus the
product listener firewall gate. Those rows are operator guidance and
automation inputs; the route still does not run
probes, choose latest artifacts, mutate firewall/device state, parse media, or
promote topology/protocol evidence. Its optional `--fail-on-pending` behavior
stops automation on remaining live transport gates; `--fail-on-incomplete`
also stops automation when the protocol matrix has not promoted all required
data protocols. WPF renders the same report rows while normal UI refreshes keep
pending gates visible instead of turning the view update into a failed command.
For direct-Wi-Fi topology promotion, the QCL-040/QCL-041 lifecycle source
artifact itself must also prove lease discipline. The
`tools/hostessctl/connectivity_topology_lifecycle.py` normalizer blocks
promotion unless the source carries an Agent Board `quest:<serial>` lease
receipt with a real lease id, reserve-before-live metadata, and
release-after-cleanup metadata. WPF may render the lease requirement and the
Hostess checks, but it must not infer topology readiness from an action label,
preflight row, or status-only lifecycle artifact.
Source artifacts remain authoritative: `device_link_report.py` owns device and
command-route evidence, `connectivity_probe.py` owns QCL probe reports and
topology classification, `connectivity_suite.py` owns suite execution, and
`protocol_evidence_matrix.py` owns promotion policy and latest-artifact selection.
Quest device-link report adaptation lives in
`tools/hostessctl/device_link_report.py`. It summarizes Hostess readiness and
bridge execution sidecars into the Quest-owned `rusty.quest.device_link.v1`
shape so WPF, Makepad tooling, CLI, and later frontends can inspect device
identity, ADB forward/tunnel state, broker readiness, runtime subscriber
health, command-result stages, and stream capabilities without becoming the
device-link authority. The same module also derives measured
`rusty.quest.device_link.stream_capability.v1` descriptors from connectivity
probe artifacts; QCL-080 app-owned UDP evidence becomes a reusable capability
row only when the runtime marker, UDP freshness counters, product-scoped WPF
listener firewall verification, and promotion decision are all preserved.
QCL-081 LSL artifacts emit their own descriptor instead of falling through to
UDP: host-loopback evidence stays candidate, blocked Quest-runtime preflight
keeps the missing `pylsl/liblsl` producer gate visible, and usable LSL requires
Quest-runtime, study-adapter, or broker-owned sample-continuity evidence.
The same device-link adapter owns the planned downloadable
`rusty.quest.device_link.install_environment_test_suite.v1` descriptor. That
suite is the frontend-neutral map for host install checks, network adapter and
firewall checks, Quest device checks, protocol capability checks, and RTT/clock
alignment strategy. Hostess still owns execution through QCL reports; WPF,
Makepad, CLI, and future installers should render and request the suite rather
than embedding protocol-specific dependency logic.
Suite execution lives in `tools/hostessctl/connectivity_suite.py`. It consumes
the descriptor, runs selected QCL slots through the existing probe adapters,
records a host snapshot for tools, network profiles, firewall listener state,
hotspot state, and Bluetooth readiness, then emits
`rusty.quest.device_link.install_environment_suite_run.v1`. Aggregate status is
allowed to warn on host posture, such as Public firewall profile or missing
listener allow rule, even when all fixture protocol slots pass. That makes the
future installer and WPF page honest about the install environment without
turning either frontend into a validator.
Windows firewall listener lifecycle also stays in Hostess:
`connectivity-probe windows-firewall-rule --action plan|apply|verify|remove`
emits the rule report and verification evidence. WPF requests these actions and
renders the report through explicit rule profiles (`custom`,
`qcl-010-tcp-echo`, `qcl-080-udp-freshness`, and
`qcl-082-rmanvid1-media`); it does not invent firewall scope rules or treat
broad diagnostic Python listener allowances as product readiness.
Mutating `apply` and `remove` reports include an `elevation` preflight. A
non-elevated shell emits
`hostess.issue.connectivity_probe.firewall_rule_requires_elevation`, blocks
before `New-NetFirewallRule` or removal, and still permits read-only
verification when the rule shape is valid. WPF renders that row and can request
the same CLI route with an operator-owned PowerShell handoff using
`--handoff-script-out` and `--handoff-verify-out`. That script reruns the
Hostess CLI from an elevated shell and then reruns the matching `verify`
report, so firewall lifecycle remains Hostess-owned instead of moving rule
creation into WPF, a hidden `runas` launcher, or a handwritten admin snippet.
Quest connectivity lab probing lives in `tools/hostessctl/connectivity_probe.py`.
It emits the experimental `rusty.quest.connectivity_topology_probe.v1` report
shape for QCL fixture and live same-Wi-Fi probes. Hostess owns execution and
evidence packaging; Rusty Quest/Manifold remain the future contract and
command/stream authority. The live QCL-010 route uses serial-scoped ADB to
observe headset Wi-Fi identity, then tests LAN reachability separately so ADB
is not mistaken for the data path.
The probe module is now a facade over focused helpers:
`connectivity_probe_common.py` owns shared check rows, issue rows, JSON/ADB/
PowerShell cleanup, Android readback, the shared QCL report skeleton, and the
empty measurement shape;
`connectivity_probe_fixtures.py` owns QCL fixture report construction, damaged
fixture variants, and fixture ingestion of media session/runtime/receiver
artifacts while preserving the facade import surface;
`connectivity_probe_live_reports.py` owns pure live report shaping for QCL
status derivation, listener rows, topology summaries, and measurement
projection while route execution remains in the facade and protocol helpers;
`connectivity_topology_live.py` owns read-only live QCL-040/QCL-041 Wi-Fi
Direct topology preflight reports. It may collect Quest feature state and
Windows adapter state, but it keeps promotion blocked until peer discovery,
group formation, bounded socket exchange, and cleanup evidence are present;
`connectivity_topology_lifecycle.py` owns structured QCL-040/QCL-041
Wi-Fi Direct lifecycle artifact ingestion. It validates live evidence source,
peer class, feature/API or peer, permission, discovery, group formation,
bounded TCP socket exchange, and cleanup before emitting a promoted topology
report. Promotion requires a positive peer count, recorded group roles,
positive bounded TCP message counters, and explicit cleanup completion; a
phase marked `status=pass` without those details remains blocked. The
normalizer does not run the peer harness, mutate Wi-Fi Direct state, or claim
QCL-082 product TCP media readiness;
`connectivity_topology_lifecycle_plan.py` owns the read-only QCL-040/QCL-041
Wi-Fi Direct lifecycle plan artifact. It binds Agent Board lease metadata,
live preflight, source-template, external live-source, and normalization
PowerShell routes into one WPF/CLI-equivalent report before a human or agent
runs the live steps; it does not run headset commands, mutate Wi-Fi Direct
state, or declare topology promotion;
`connectivity_probe_validation.py` owns the shared QCL report schema/status
validator so route dispatch, fixture construction, live probing, WPF rows, and
Makepad rows all depend on the same report acceptance surface;
`connectivity_firewall.py` owns Windows Firewall listener rule planning,
apply/verify/remove reports, elevation preflight, product-rule verification,
and network/firewall profile summaries used by QCL-010/QCL-080 and WPF
operator rows;
`connectivity_lan.py` owns serial-scoped Quest ADB identity collection, host
IPv4 selection, same-subnet checks, ICMP probes, Windows Mobile Hotspot state
collection, TCP echo transport probes, and QCL-010/QCL-011 live report
assembly used by live QCL LAN routes;
`connectivity_udp.py` owns QCL-080 UDP freshness live report assembly,
sender/listener mechanics, Makepad runtime UDP sender evidence, WPF
listener-helper ingestion, and app-owned runtime-marker parsing;
`connectivity_bluetooth.py` owns QCL-050
RFCOMM and QCL-051 BLE/GATT readiness, payload, reconnect, transport helpers,
and live report assembly; `connectivity_media.py` owns QCL-082 binary media-plane fixture
reports, Rusty Quest `rusty.quest.media_stream_session.v1` source-contract
ingestion, and `rusty.quest.media_stream.android_runtime_status.v1`
broker/runtime artifact ingestion for H.264/TCP framing, accepted
`command.media_stream.*` commands, timestamp, queue/drop/backpressure,
source-classification, shell-display lab gating, and high-rate JSON rejection;
`connectivity_media_receiver.py` owns QCL-082 Hostess receiver-counter
evidence by arming bounded TCP `RMANVID1` captures, parsing stream headers and
packet records, writing receiver sidecar queue/drop/close counters, pairing
that evidence with broker runtime status when available, and optionally joining
a topology report through the explicit product TCP media over direct-Wi-Fi
gate. It also owns the orchestrated
`connectivity-probe qcl082-product-media-live-session` route, which binds the
same receiver and bridge-command helpers so the TCP listener is already armed
before the Quest/Manifold `start_source` command is sent. That route writes the
request, bridge evidence, live execution, validation, logcat, capture, sidecar,
and receiver-result artifacts only after its live preflight passes. The
preflight blocks before writing the request, arming the receiver, or running
serial-scoped ADB unless the operator supplies an Agent Board `quest:<serial>`
lease id/resource, a promoted direct-Wi-Fi topology report, and a verified
product Hostess/WPF listener firewall report. It still does not apply firewall
rules, collect Wi-Fi Direct lifecycle evidence, choose Android camera/display
sources, or promote QCL-082 by itself;
`connectivity_media_product_plan.py` owns the read-only QCL-082 product-media
direct-Wi-Fi plan artifact. It binds the existing Hostess CLI routes,
dependency gates, Quest lease policy, PowerShell command strings, and
acceptance artifacts into one WPF/CLI-equivalent report before a human or agent
runs the live steps; it does not run headset commands, mutate firewall/device
state, parse media, or declare promotion;
`connectivity_direct_wifi_product_media_plan.py` owns the read-only acceptance
plan that composes the QCL-040/QCL-041 lifecycle plans, promoted direct-Wi-Fi
topology candidates, product Hostess/WPF TCP listener firewall evidence, and
QCL-082 RMANVID1 product-media report into one WPF/CLI-equivalent checklist.
It is not a new topology, firewall, media, or promotion authority and does not
run ADB, mutate Wi-Fi Direct, mutate firewall state, or parse media payloads;
`companion_report_projection.py` classifies that acceptance plan as a distinct
source artifact and projects summary, dependency, and check rows without
turning the plan into a promotion authority;
`connectivity_topology.py` owns topology metadata helpers, Windows Mobile
Hotspot status formatting, and fixture-only QCL-020/QCL-030/QCL-040/QCL-041
topology report bodies for Wi-Fi ADB, LocalOnlyHotspot, and Wi-Fi Direct
limitations. Live QCL-040/QCL-041 routes are intentionally separate and
non-promoting until a real topology harness records the full Wi-Fi Direct peer
lifecycle and the lifecycle ingestion route normalizes that evidence; and
`connectivity_data_protocols.py` owns QCL-081 LSL, QCL-083 OSC, and QCL-084
ZeroMQ adapter mechanics, Quest-runtime OSC/ZeroMQ execution helpers, and
protocol-specific live report assembly, source-specific report promotion
gates, and evidence rows; `connectivity_websocket.py` owns QCL-079 generic
WebSocket host-loopback fixture/live mechanics, bounded message measurements,
and the explicit separation from Manifold command authority and high-rate media
routes.
The Bluetooth helper owns QCL-050/QCL-051 readiness and payload
evidence. QCL-051 uses the Hostess T Android app as an app-owned BLE/GATT
server plus `tools/connectivity_probe/qcl051_ble_gatt_client` as the Windows
WinRT BLE/GATT client. QCL-050 uses the same app-owned pattern with an Android
RFCOMM server and `tools/connectivity_probe/qcl050_rfcomm_client` as the
Windows WinRT RFCOMM helper. Hostess joins both reports and records launch
preconditions such as the Quest VR lockscreen separately from protocol
failures. QCL-051 is promotable in the tested Windows-central/Quest-GATT-server
direction after reconnect evidence; QCL-050 remains blocked until Classic
Bluetooth pairing/service visibility is proven. This borrows Polar/PMD failure
vocabulary for permissions, service discovery, control writes, handoff timeout,
and cleanup, but PMD physical sensor ownership remains with Manifold/PMB
routes rather than QCL-051.
The same lab module owns protocol-fit reports for LSL, OSC, and ZeroMQ.
QCL-081 treats Manifold-owned LSL broker evidence the same way QCL-084 treats
the Manifold ZeroMQ broker path: Hostess shells to the Manifold JSON report
tool, requires `evidence_tier=broker_owned`,
`authority.owner=rusty.manifold.transport`, passing bridge-route evidence,
complete sample continuity, and monotonic received sequences, then wraps that
report as Hostess connectivity evidence for WPF and protocol-matrix rendering.
Quest-runtime LSL promotion remains separate and blocked until the Quest side
can emit its own `pylsl/liblsl` sample-continuity evidence.
QCL-082 is the media/binary data-plane slot. Its fixture route declares the
source-neutral `tcp_binary` contract shape, `RMANVID1` packet marker,
frame-timestamp policy, bounded receiver queue, drop/close backpressure rules,
and the rule that high-rate media payloads must not ride JSON command/report
streams. Its media-stream plan route consumes Rusty Quest
`rusty.quest.media_stream_session.v1` plans from the camera/display streaming
work and projects them into the same QCL-082 report schema. Its broker/runtime
status route consumes `rusty.quest.media_stream.android_runtime_status.v1` or a
Manifold command ACK carrying `media_stream_runtime`; it also accepts the
Hostess `rusty.hostess.bridge_command.live_android_execution_evidence.v1`
sidecar when that sidecar contains the broker command ACK from
`run-bridge-command-live-android`. That proves command acceptance, selected
source/runtime state, consent or lab-only gating, and binary-plane policy from
the broker side. Its receiver-counter route can first
arm a bounded TCP listener that writes a raw `RMANVID1` capture and sidecar,
then parse that byte stream without decoding H.264, validate packet boundaries
and timestamps, and require queue capacity, drops, backpressure, and close
reason. This lets WPF and CLI automation see MediaProjection display-stream
contracts, shell-hidden display lab gates, and receiver packet evidence without
making Hostess the source authority for Android capture. Session plans remain
source-contract evidence; broker/runtime status is broker-owned candidate
evidence; receiver counters become promotable only when paired with live
broker-owned or Quest-runtime status. The preferred QCL-082 fold-in input is
the Hostess receiver-result artifact; `connectivity-probe run --probe-id
QCL-082 --media-stream-receiver-result <result.json>` resolves the capture,
sidecar, runtime-status, topology, and firewall report paths from that
artifact. The older explicit path flags remain lower-level compatibility
inputs. Product TCP media over direct Wi-Fi is a separate gate: the receiver
report must also be paired with a promoted QCL-040/QCL-041 direct-Wi-Fi
topology report before the WPF transport summary can mark that product path
proven.
QCL-084 treats ZeroMQ as a generic data-protocol capability: manifests,
endpoint/open-mode config, bounded receiver queues, message/drop/decode
counters, and optional runtime feature gates belong to a reusable ZeroMQ
adapter/module. Goofi Pipe is only an example source profile through a sidecar
that converts Goofi PAIR/send_pyobj payloads into bounded JSON for the generic
ZeroMQ route. The generic proof now lives in the Manifold-owned
`rusty-manifold-zmq` adapter, while Hostess can still ingest the public
Rusty-XR compatibility proof and the Goofi sidecar witness log. Neither WPF
nor Hostess should make Goofi the protocol authority. The promotable
`native-rust-broker` QCL-084 path is still CLI-owned: Hostess shells to the
Manifold adapter's JSON report mode, requires `evidence_tier=broker_owned`,
`authority.owner=rusty.manifold.transport`, passing bridge-route evidence,
zero drops, and zero decode errors, then wraps that report as Hostess
connectivity evidence for WPF and protocol-matrix rendering.
QCL-079 treats generic WebSocket as a separate optional protocol-fit slot. It
does not promote or weaken QCL-000 Manifold command/session WebSocket
authority. The host-loopback route validates a bounded HTTP upgrade, echo
payload exchange, message limits, command-authority separation, and high-rate
media guard; it remains candidate-only until a broker-owned or Quest-runtime
endpoint produces live evidence. The broker-owned path accepts the Manifold
`stream_bridge` WebSocket descriptor/evidence pair and rejects command/control
WebSocket descriptors so QCL-000 receipt authority cannot be reused as generic
data-plane proof.
`hostessctl connectivity-probe protocol-matrix` is the roll-up contract for
operator protocol promotion views. It consumes existing suite, probe,
device-link, and stream-capability artifacts and classifies each protocol by
evidence tier, promotion state, and missing gate. WPF renders this matrix as a
requester/inspector; promotion rules stay in the CLI/report module so fixture
and host-loopback LSL/media/OSC/ZeroMQ evidence cannot accidentally become
UI-only acceptance proof. The same route owns latest-artifact selection for
promoted QCL-000, QCL-080, QCL-081, QCL-082, QCL-083, and QCL-084 rows:
device-link reports
provide command/session authority, stream-capability descriptors preserve
QCL-080 product UDP evidence, and connectivity probe reports provide the
protocol rows. WPF and automated CLI smoke tests therefore share one
artifact-selection policy. Makepad companion projection can either consume the
finished protocol matrix as a lower-level report artifact or consume the
`rusty.hostess.companion.report_projection.v1` artifact emitted by
`hostessctl companion-report projection`; in both cases it only emits compact
panel rows/markers and does not re-evaluate gates or promotion state.
Projected-motion-breath evidence construction and validation live in
`tools/hostessctl/pmb_evidence.py`. PMB route modules own desktop, Android,
and Quest route orchestration, while PMB contract constants, replay/self-test
evidence builders, and PMB validation reports remain separate from host-run
evidence writing. Host-run evidence writers live in
`tools/hostessctl/pmb_host_run_evidence.py`. Native Rusty Quest renderer PMB
receipt policy parsing lives in `tools/hostessctl/pmb_native_receipts.py`; it
accepts native projection-target effective markers as app-side consumption
evidence for the canonical `stream.breath.state` and
`stream.breath.state.value` contract instead of requiring the Makepad-only
`stream.breath.feedback_receipt` stream. Shared PMB stream IDs, contract
authority constants, package snapshot, scorecard, host-app, timestamp, and path
helpers live in `tools/hostessctl/pmb_support.py`.
Manifold value recording planning and broker capture orchestration live in
`tools/hostessctl/manifold_recording.py`: the provider registry,
`record-values` route planner, Quest broker WebSocket capture, Makepad
controller-pose provider setup, and PMB live processor bridge execution are
kept out of the CLI root. `hostessctl.py` preserves thin wrappers for existing
tests and scripts.
Native Rusty Quest Breathing Room setup lives in
`tools/hostessctl/native_breathing_room_setup.py`. It consumes the canonical
Rusty Quest native runtime profile as the startup settings authority, records
the profile SHA-256 in the Hostess setup receipt, and allows only the named
projection-target, PMB bridge, and Manifold broker endpoint properties to vary
per run. The setup receipt also records the PMB stream contract authority and
rejects custom state/value stream IDs until the broker publisher and native
receipt policy can be parameterized together.
Broker telemetry and Manifold value-recording evidence construction lives in
`tools/hostessctl/recording_evidence.py`. Recording evidence schemas,
validators, scorecards, and host-run wrappers are isolated from command
orchestration.
Quest Makepad GPU summary validation keeps
`tools/check_makepad_quest_gpu_evidence.py` as the stable checker command and
CLI/import facade. Shared proof-marker parsing lives in
`tools/makepad_quest_gpu_evidence/proof_lines.py`, while GPU force
candidate/gate/freshness/residency/runtime-authority validation lives in
`tools/makepad_quest_gpu_evidence/force_authority.py`. The facade keeps schema
loading, cadence/stale checks, mesh-SDF checks, and compact summary assembly;
new independent evidence families should move into sibling modules when they
start adding pressure.
Studio platform-smoke staging helpers are split by workflow phase:
`tools/studio_staging/platform_smoke.py` remains the import facade, while
`platform_smoke_plan.py`, `platform_smoke_execution.py`,
`platform_smoke_operator_start.py`, `platform_smoke_execution_report.py`, and
`platform_smoke_evidence.py` own plan/approval, execution, operator-start,
report, and evidence review behavior. These helpers are staging contract and
review evidence builders; they must not start Studio, Hostess, Quest, Makepad,
or Manifold runtimes.
Projected-motion-breath release staging helpers follow that same facade
pattern: `tools/studio_staging/pmb_release.py` remains the import surface,
while `pmb_validation_handoff.py`, `pmb_replay_validation.py`, and
`operator_release.py` own validation handoff, replay validation, and
operator-release readiness behavior.
Hostess staging handoff helpers follow the same facade pattern:
`tools/studio_staging/staging_handoff.py` remains the import surface, while
`staging_handoff_acceptance.py`, `staging_handoff_file_plan.py`,
`staging_handoff_file_copy.py`, `staging_handoff_payload_manifest.py`, and
`staging_handoff_downstream_shell.py` own acceptance, file planning, file copy,
payload manifest, and downstream shell selection behavior. The file-copy helper
may copy files under validated staging roots, but these modules must not launch
Studio, Hostess, Quest, Makepad, or Manifold runtimes.
The Studio staging request command follows that same facade pattern:
`tools/studio_staging_request.py` remains the stable import/CLI surface,
`tools/studio_staging/request_cli.py` owns command orchestration across the
already split staging families, `request_cli_parser.py` owns the argument
surface, and `request_cli_validation.py` owns terminal validation-output
generation. The CLI modules may coordinate artifacts and validation outputs,
but new schema or workflow authority belongs in the focused helper modules.
The Studio staging request tests follow the same facade pattern:
`tools/test_studio_staging_request.py` remains the stable unittest entry point,
while `tools/studio_staging/request_tests/` groups the coverage by
intake/smoke workflow, platform-smoke control, platform-smoke evidence,
PMB/release, Hostess staging handoff, and CLI fixture-writing families.
The QCL connectivity-probe tests follow the same facade pattern:
`tools/test_hostessctl_connectivity_probe.py` remains the stable unittest entry
point, while `tools/connectivity_probe_tests/` groups coverage by fixture
reports, QCL-082 media receiver/product gates, QCL-079 generic WebSocket and
data-protocol evidence, live LAN/UDP/Bluetooth paths, parser coverage, and
firewall rule profiles. The split keeps the automation gate stable while
preventing the test suite from becoming the next mixed-authority source file.

Processor modules are selected by module id. For deterministic replay, Hostess
delegates formula execution and dependency resolution to the package Rust
processor core, then validates the graph-resolved evidence. Desktop live module
capture now keeps acquisition in Hostess, writes captured HR/RR and ACC buffers
into the package runtime input shape, and delegates selected module outputs to
the same Rust graph runner.

The current selected modules cover HRV window, RMSSD gain, coherence, breath
volume from ACC, breath dynamics, and HRVB resonance amplitude. Coherence is
computed at runtime from a live HR/RR capture by resampling a 64-second RR
window to 128 uniform samples and producing the package-defined spectral ratio
plus normalized score fields.

The phone/headset path uses a JNI bridge from the app shell to the same package
runtime ABI. The bridge is recorded in `docs/ON_DEVICE_RUNTIME_BRIDGE.md`.
Java/Kotlin owns acquisition and display only; selected processor outputs come
from the Rust graph report.

The telemetry panel boundary is recorded in `docs/TELEMETRY_GUI.md`.

For the Quest Makepad Matter surface path, Hostess remains the app-shell and
evidence boundary. `apps/hostess-t-makepad/src/recorded_hand_surface.rs` loads
staged recorded bind rigs and compact joint clips from app-private files for
recorded replay evidence, then submits the cached recorded-hand builder plus
the current compact joint frame to the Quest-Makepad Matter worker so source
frame construction happens off the app/render thread. It requests full GPU
oracle payloads only for bounded proof cadence; ordinary recorded replay uses
the Matter-only source-frame option. Source selection now keeps the fallback
`recorded-or-positions-replay`, the explicit `recorded-hand-replay` proof mode,
and the `positions-only-surface` smoke mode distinct. The explicit recorded
mode is the live-input-equivalent replay provider for GPU proof evidence: it
does not silently fall back to baked positions, requests two mesh-SDF proof
markers so renderer-lifetime program reuse is observable, expects the scaled
proof path to report at least `sampleCount=8`, and still keeps all hand frames,
meshes, dense SDF cells, and GPU buffers off settings/control JSON.
`apps/hostess-t-makepad/src/live_hand_surface.rs`
observes live Makepad `XrHandMeshBindData` plus `XrHand` updates and converts
them into the same bind-mesh-plus-compact-joint-frame shape. When an explicit
`live-openxr-hand-*` source mode is selected, Hostess submits the cached live
source-frame builder plus compact joint frame to the same Matter worker path as
recorded replay. Source-frame expansion and optional GPU oracle payload
packaging happen on the worker thread, with full GPU oracle payloads requested
only at bounded proof cadence. The live path does not own Matter CPU
skinning/SDF truth and does not route hand meshes, joint frames, fields,
particles, or GPU buffers through settings/control JSON.

`apps/hostess-t-makepad/src/makepad_diagnostics.rs` owns app-level diagnostic
marker emission, marker token formatting, bounded cadence helpers, raw camera
event markers, YUV texture handles, and runtime target-footprint marker
augmentation so the Makepad app root remains app-shell wiring.

`apps/hostess-t-makepad/src/broker_h264_runtime.rs` owns broker-H264 and
remote-camera runtime key parsing, texture-path selection, source-sampling
selection, stream-port defaults, target-screen fallback rectangles, and
`ExternalH264VideoSource` construction.

`apps/hostess-t-makepad/src/source_metadata.rs` remains the Makepad
source/import marker facade for runtime target-footprint, source-sampling, and
hardware-buffer import marker helpers. Its `source_metadata/` child modules own
focused metadata families; `broker_projection.rs` owns broker-H264 stream-header
projection metadata parsing, content-geometry marker records, and broker
projection plan decisions.

`apps/hostess-t-makepad/src/projection_geometry.rs` remains the projection-plan
and OpenXR geometry facade. Its `projection_geometry/` child modules own focused
projection support families; `markers.rs` owns Makepad stereo projection
marker/report field formatting and marker-shape tests.

`apps/hostess-t-makepad/src/camera_projection_flow.rs` owns the paired camera
import/projection runtime flow: broker stream-header metadata handling, video
texture update bookkeeping, pending stereo-frame adoption, cadence sample
markers, paired import timers, broker-H264 texture import requests, native
video widget startup, YUV content probes, projection panel texture binding,
projection-complete markers, stereo comparison parity markers, and direct
Camera2 plan probing. The app root keeps top-level event ordering and calls
this module through split `App` methods.

`apps/hostess-t-makepad/src/hostess_camera_model.rs` remains the public
compatibility facade for app-neutral camera helpers. Its
`hostess_camera_model/` child modules own source selection, projection
footprint/layout and border geometry, camera basis/projection math, homography
and temporal smoothing, and timestamp matching.
`apps/hostess-t-makepad/src/hostess_contracts/camera.rs` remains the
camera-contract facade for shared primitives, diagnostics, frame metadata,
and calibration/source diagnostics. Its `hostess_contracts/camera/` child
modules own focused camera contract families; `source_sampling.rs` owns
source-sampling DTOs, texture transform helpers, and source-sampling schema
acceptance, `temporal_projection.rs` owns frame timing, projection state,
visual projection state, temporal policy, and metrics, while `texture_lane.rs`
owns camera texture-lane DTOs, validation, and current-or-legacy schema
acceptance.

`apps/hostess-t-makepad/src/frame_orientation.rs` owns Hostess-local
direct-camera and broker-H264 source-raster orientation decisions plus shared
broker pair pose-source combination. `source_sampling.rs` consumes the
orientation decision when building source-sampling contracts and markers, and
`camera_pair.rs` consumes the same pose-source helper for broker projection
plans.

`apps/hostess-t-makepad/src/makepad_stereo_camera_panel.rs` owns the Rust
`DrawMakepadStereoCameraPanel` and `MakepadStereoCameraPanel` types, shader
uniform application, texture slot binding, target-footprint push state, and
panel-side horizontal alignment uniform application. It also owns the panel
live-design `script_mod!` block, including draw shader defaults and widget
defaults. The app root registers the panel module before the Hostess app layout
script.

`apps/hostess-t-makepad/src/matter_world_particle_billboard.rs` and
`apps/hostess-t-makepad/src/matter_world_adf_debug.rs` own the
Hostess-local world-particle and ADF debug renderer widgets plus their
Makepad widget-default `script_mod!` blocks. Matter, Optics, and
Quest-Makepad remain the runtime truth and renderer-neutral row authorities;
these modules only draw bounded Makepad evidence rows.

`apps/hostess-t-makepad/src/makepad_app_live_design.rs` owns the Hostess app
layout `script_mod!` block and `startup()` UI tree. The app root calls this
module after all widget/default modules are registered, then keeps runtime
state, event handling, and data-plane adoption wiring in Rust.
`apps/hostess-t-makepad/src/app_mesh_replay_runtime.rs` owns selected
effective-settings adoption, mesh replay stepping, Matter/particle/stimulus
runtime resets, and panel/world cadence binding.
`apps/hostess-t-makepad/src/makepad_effective_settings.rs` remains the
effective-settings receipt/runtime-selection facade.
`apps/hostess-t-makepad/src/makepad_effective_settings/revision.rs` owns the
revision sidecar identity, scoped invalidation keys, and path/mtime fallback
comparison helper used by runtime and GPU-proof adoption gates.
`apps/hostess-t-makepad/src/makepad_effective_settings/tests.rs` owns the
effective-settings regression fixtures so the facade does not also act as the
test suite container.
`apps/hostess-t-makepad/src/app_stimulus_runtime.rs` owns stimulus field panel
binding, runtime XR projection rows, bounded volume preview probe polling, and
image-preview texture adoption.
`apps/hostess-t-makepad/src/app_projection_target.rs` owns the app-shell
projection-target control loop: controller offset/scale updates, breath-source
target-scale adoption, and related runtime markers. Pure projection-target
math/settings helpers remain in `projection_target_controls.rs`.
`apps/hostess-t-makepad/src/app_horizontal_alignment.rs` owns the app-shell
horizontal-alignment tuning surface: runtime-resolution fallback, legacy
hotload values, change detection, hotload markers, and panel binding.
`apps/hostess-t-makepad/src/main_tests.rs` owns app-root regression tests that
need private access to this shell wiring.

Hostess settings hotload follows the repo-family settings invalidation policy:
settings writes are active control-plane transactions that publish a compact
revision sidecar; runtime consumers compare global then scoped hashes before
parsing detailed settings; adoption evidence must distinguish seen, applied,
and rejected revisions. Hostess may stage and observe settings, but it must not
turn settings JSON into a frame, field, particle, or GPU-buffer transport.
The current app emits
`RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS_ADOPTION` after a runtime settings
detail read, recording the scoped revision key, subscribed scopes, selected
gate, and applied/rejected status.

`apps/hostess-t-makepad/src/makepad_runtime_config.rs` owns typed parsing,
layered resolution, and the runtime-config facade. Canonical renderer-neutral
projection runtime keys and ownership metadata live in
`apps/hostess-t-makepad/src/makepad_runtime_config/projection_keys.rs`.
Alias evidence types live in
`apps/hostess-t-makepad/src/makepad_runtime_config/alias_model.rs`, keeping
legacy/deprecated vocabulary with the alias ledger instead of the generic
runtime-config type section.
Projection manifest marker formatting and alias-evidence tokenization live in
`apps/hostess-t-makepad/src/makepad_runtime_config/manifest.rs` so the core
parser/resolver does not carry diagnostic marker formatting. Accepted external
spellings for launch extras, Android properties, and environment variables live in
`apps/hostess-t-makepad/src/makepad_runtime_config/aliases.rs` and are
re-exported through the parent module only for facade compatibility. Keep
legacy or retired names out of the canonical registry unless a compatibility
bridge is explicitly approved and covered by the alias tests.
Retired projection spellings that should be rejected by active parsing but may
need property or environment cleanup live in
`apps/hostess-t-makepad/src/makepad_runtime_config/retired_aliases.rs`. This
ledger is documentation and hygiene input, not a resolver table.

Hostess-local camera, home, and kiosk DTO constructors now default to
`rusty.hostess.*` schema IDs. `apps/hostess-t-makepad/src/hostess_contracts/legacy_rusty_xr_schemas.rs`
is the frozen compatibility ledger for old `rusty.xr.*` schema IDs accepted
from serialized compatibility inputs. Contract modules re-export both current
Hostess defaults and legacy constants to preserve the existing facade, but new
default-lane schema work belongs in the owning Morphospace lane rather than
adding more old Rusty-XR defaults. The source-sampling serde fixture at
`tools/quest-camera-profile/fixtures/source-sampling-contracts.cross-backend.jsonl`
keeps current Hostess defaults and one legacy Rusty-XR input in the same
validation path.

After a raw capture validates, `hostessctl` writes a
`rusty.manifold.host_run.run_evidence.v1` wrapper with a scorecard so the live
run is tied back to the Manifold Hostess contract spine.

## Non-Scope

This repo does not define package semantics, dynamic loading, product UI, or a
long-lived runtime daemon.
