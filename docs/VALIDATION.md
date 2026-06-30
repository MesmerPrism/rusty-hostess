# Validation

Run the repo-local check before committing changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\check_all.ps1
```

The check covers the available local surface:

- Python syntax checks for Hostess control and evidence tools;
- Python unit tests under `tools\test_*.py`;
- desktop projected-motion-breath replay when the sibling package repo is
  available;
- `cargo check` for `apps\hostess-t-makepad`;
- serde-gated Hostess contract tests for current schema defaults and frozen
  legacy schema compatibility;
- app-root Makepad shell regression tests in `main_tests`;
- Rust formatting and temporary cargo checks for Android JNI bridge crates when
  their inputs are present.
- Companion catalog descriptor smoke when the sibling Rusty GUI descriptor
  folder is present.
- WPF companion build and projection tests when the WPF projects exist.

For fast CLI/evidence edits, run the Python path first:

```powershell
python -m py_compile tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_catalog.py tools\hostessctl\companion_operator_action_rows.py tools\hostessctl\companion_operator_actions.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_report_projection.py tools\hostessctl\companion_report_transport_coverage.py tools\hostessctl\companion_transport_gate_actions.py tools\hostessctl\companion_transport_gates.py tools\hostessctl\companion_session.py tools\hostessctl\companion_session_defaults.py tools\hostessctl\connectivity_bluetooth.py tools\hostessctl\connectivity_data_protocols.py tools\hostessctl\connectivity_firewall.py tools\hostessctl\connectivity_lan.py tools\hostessctl\connectivity_media.py tools\hostessctl\connectivity_media_product_plan.py tools\hostessctl\connectivity_media_receiver.py tools\hostessctl\connectivity_probe.py tools\hostessctl\connectivity_probe_common.py tools\hostessctl\connectivity_probe_fixtures.py tools\hostessctl\connectivity_probe_live_reports.py tools\hostessctl\connectivity_probe_validation.py tools\hostessctl\connectivity_suite.py tools\hostessctl\connectivity_topology.py tools\hostessctl\connectivity_topology_lifecycle.py tools\hostessctl\connectivity_topology_live.py tools\hostessctl\connectivity_udp.py tools\hostessctl\device_link_report.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py
python -m unittest discover -s tools -p "test_*.py"
```

Bridge command and bridge-route evidence fixture validation is covered by:

```powershell
python -m unittest tools.test_hostessctl_bridge_command_android
python -m unittest tools.test_hostessctl_bridge_command_live_android
python -m unittest tools.test_hostessctl_bridge_command
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde bridge_command
python tools\hostessctl\hostessctl.py emit-bridge-route-evidence --input fixtures\bridge-route\hostess-command-websocket-applied-input.json --out target\bridge-route\hostess-command-websocket-applied-evidence.json
python -m unittest tools.test_hostessctl_bridge_route_evidence
```

The Hostess bridge-command tests cover broker receipt stream parsing from
`stream_event.payload`, the Makepad broker-stream subscriber, raw app-private
runtime receipt proof, and the broker-authorized Android route that blocks
app-private staging unless the broker emits `authority_accepted`. The live
Android command tests cover the Hostess-owned setup sidecar around broker
launch, ADB forwarding, forwarded socket readiness, Makepad launch, and the
delegated broker-stream command execution.

Windows companion catalog, readiness, and session report validation is covered by:

```powershell
python -m unittest tools.test_hostessctl_companion_catalog tools.test_hostessctl_companion_operator_actions tools.test_hostessctl_companion_transport_gate_actions tools.test_hostessctl_companion_readiness tools.test_hostessctl_companion_report_projection tools.test_hostessctl_companion_session
python tools\hostessctl\hostessctl.py companion-catalog --out target\companion-catalog\catalog.json --fail-on-error
python tools\hostessctl\hostessctl.py companion-readiness --out target\companion-readiness\readiness.json
python tools\hostessctl\hostessctl.py companion-session run --out target\companion-session\session.json --profile basic --skip-probe
dotnet run --project tests\HostessCompanion.Wpf.Tests\HostessCompanion.Wpf.Tests.csproj
```

`companion-catalog --fail-on-error` is the automation gate for descriptor
integrity. The catalog report also carries semantic issue rows for workspace
composition failures, such as unknown module references, so WPF can render the
same invalid-descriptor evidence for operators without owning validation logic.
The repo-local `check_all.ps1` runs that descriptor smoke for both `wpf` and
`makepad` frontends when the sibling Rusty GUI descriptor folder is present, so
Makepad-facing workspaces cannot claim frontend parity while selecting
WPF-only modules or transports.

The WPF projection tests cover `rusty.quest.device_link.v1` artifact loading
from a session report, Devices/Transports projection rows, command-stage
evidence promotion, connectivity suite row grouping, companion-report
projection rows, and catalog-backed workspace composition and validation-issue
rows. Makepad companion frontend tests cover the same shared catalog and
device-link reports, the
`rusty.quest.device_link.protocol_evidence_matrix.v1` report fixture, and the
shared `rusty.hostess.companion.report_projection.v1` fixture so the
headset-local frontend can render the same normalized operator evidence without
owning artifact selection or promotion gates.
The WPF Session action also carries the live receipt wait envelope that CLI
automation should use for headset smoke:
`--wait-seconds 30 --fallback-wait-seconds 30 --authority-wait-seconds 30
--broker-process-wait-seconds 20 --makepad-process-wait-seconds 20
--socket-wait-seconds 20 --launch-settle-seconds 8
--runtime-subscriber-retry-count 8
--runtime-subscriber-retry-wait-seconds 2`. QCL-000 promotion requires the
broker-stream `runtime_accepted` and `applied` stages; app-private fallback
evidence remains a recovery diagnostic, not command authority.

Every new WPF operator action needs UI-equivalent CLI coverage before it is
accepted as an operator capability. The minimum validation shape is: a
Hostess CLI or local API route that emits the structured report/sidecar the UI
renders, fixture or fake-mode coverage for that route, and a WPF projection
test proving the viewmodel surface maps the same evidence into human-facing
rows. WPF button handlers must not be the only executable path for setup,
commands, probes, firewall changes, or evidence export.
The WPF operator action catalog test also checks that each advertised command
names the Hostess CLI entrypoint (`python tools\hostessctl\hostessctl.py`) and
does not use pipe-delimited option shorthand. Use PowerShell variables, quoted
placeholders, or splatted argument arrays for routes that need repeated flags
such as `--input` or `--latest-probe-id`. Every advertised Hostess CLI segment
in a WPF operator action must name a primary `--out` report artifact. Any
advertised `connectivity-probe run` segment must also name its output artifact
with `--out`, so the human-visible recipe is the same report-producing route
that automation can validate. The same catalog now exposes typed
`requires_elevation`, `requires_quest_lease`,
`requires_adb_server_lifecycle_lease`, `mutates_host`, and `mutates_device`
flags. Tests keep ordinary headset-bound actions serial-scoped and reject
hidden `adb-server:lifecycle` requirements unless a future route explicitly
owns disruptive ADB daemon recovery.
Every new WPF report view needs the same evidence-backed shape even when it is
read-only: a CLI/API report, descriptor, sidecar, receipt, or fixture output
must exist first, and projection tests must prove the page rows are derived from
that artifact.
The WPF test suite also reflects over `MainWindowViewModel` command properties
and compares them with `OperatorActionCatalog`, so a new command fails tests
until its CLI-equivalent route, evidence artifact, and test coverage are named.
It also runs:

```powershell
python tools\hostessctl\hostessctl.py companion-report operator-actions `
  --frontend wpf `
  --out target\companion-report\wpf-operator-actions-test.json `
  --fail-on-error
```

and compares every emitted action row with `OperatorActionCatalog`, so the
machine-readable report and the human-visible WPF command catalog cannot drift.
The advertised protocol-matrix workflow must render transport gates with
`--fail-on-error --fail-on-pending --fail-on-incomplete`, matching the WPF
service path's validation-first report request before human operators see the
rows.
The Hostess-side report imports static rows from
`tools\hostessctl\companion_operator_action_rows.py` and keeps schema,
validation, and failure status in `companion_operator_actions.py`, so row
ownership and report checks stay separable while still testing the same
lease/elevation/mutation posture WPF shows to operators.
Firewall controls are covered the same way: the WPF rule-profile selector must
map to the CLI `--rule-profile` contract, and
`HostessCompanion.Wpf.Tests` plans the QCL-082 profile through Hostess CLI to
prove the UI-visible TCP/9079 media listener route emits the same structured
firewall report automation will consume.

The shared read-only report projection route is covered by:

```powershell
python -m unittest tools.test_hostessctl_companion_report_projection
python tools\hostessctl\hostessctl.py companion-report projection `
  --frontend wpf `
  --device-link fixtures\companion\device-link-pass.json `
  --connectivity-probe fixtures\connectivity-probe\qcl-030-local-only-hotspot-started.json `
  --protocol-matrix fixtures\companion\protocol-matrix-promoted.json `
  --out target\companion-report\projection-smoke.json `
  --fail-on-error
```

That route emits `rusty.hostess.companion.report_projection.v1` and only copies
source artifact rows into a frontend-neutral operator view. Individual
connectivity-probe rows can show topology and promotion gates, but use
`connectivity-probe protocol-matrix` first when the view needs latest-artifact
selection or protocol-promotion state. After a QCL-082 firewall verify report
exists, add `--firewall-rule target\connectivity-probe\qcl082-product-firewall-verify.json`
to project the standalone product listener firewall gate evidence through the
same report route.
The transport coverage summary row is shaped in
`tools\hostessctl\companion_report_transport_coverage.py`; it is still covered
through `tools.test_hostessctl_companion_report_projection` because the row is
part of the shared projection artifact consumed by WPF and Makepad. The row
must expose `details.term_gates` and `details.remaining_live_gates` so TCP,
WebSocket, and Wi-Fi Direct visibility cannot be mistaken for live product
TCP/direct-Wi-Fi or generic WebSocket promotion. The product TCP/direct-Wi-Fi
gate is cleared only by a QCL-082 receiver report that carries
`protocol.media_product_topology_gate` with
`product_gate=product_tcp_media_over_direct_wifi` and
`product_gate_proven=true`.
The product TCP listener firewall gate is separate: it clears only from a
QCL-082 receiver report with `protocol.media_product_listener_firewall_gate` or
a standalone `--firewall-rule` report that verifies the
`qcl-082-rmanvid1-media` Hostess/WPF executable rule. That standalone firewall
proof must not clear live direct-Wi-Fi topology or product media over direct
Wi-Fi.
When QCL-079 is present, the WebSocket term gate changes from command-only
coverage to command receipts plus generic WebSocket protocol-fit coverage, but
the generic gate remains pending until broker-owned or Quest-runtime endpoint
evidence exists.
For automation that needs a standalone gate artifact, derive it from the
projection:

```powershell
python tools\hostessctl\hostessctl.py companion-report transport-gates `
  --projection target\companion-report\projection-smoke.json `
  --out target\companion-report\projection-smoke.transport-gates.json `
  --fail-on-error
```

Add `--fail-on-pending` only when the run must stop until every WPF-visible
transport gate is cleared. Add `--fail-on-incomplete` when the run must also
stop unless the projected protocol matrix reports
`all_required_data_protocols_promoted=true`. This route emits
`rusty.hostess.companion.transport_gate_report.v1` with both
`remaining_live_gates` and `data_protocols`; it does not run probes, change
firewall/device state, select latest artifacts, parse media, or promote
topology/protocol evidence. Pending gates include `next_actions` that
automation and WPF can render as the CLI-equivalent path to the clearing
evidence. Each action names a PowerShell-compatible command when one exists,
the expected acceptance artifacts, whether elevation is required, and whether a
Quest lease is required. Headset-bound actions also carry structured Agent
Board lease metadata with the `quest:<quest-serial>` resource, reserve command,
release command, duration, and the `adb-server:lifecycle` policy.
Headset-bound commands use serial-scoped ADB; reserve `adb-server:lifecycle`
only for disruptive daemon lifecycle recovery.
The validation sidecar also rejects report drift when the top-level
`operator_next_actions.gates` summary no longer matches the per-gate
`remaining_live_gates[*].next_actions` action IDs that WPF renders. It also
rejects malformed action metadata, including missing authority owners,
non-boolean elevation/lease/mutation/gate-clearing flags, empty acceptance
artifacts, and malformed dependency gate IDs, so WPF never treats an
underspecified operator recipe as accepted guidance.
`tools.test_hostessctl_companion_transport_gate_actions` validates that the
source-owned next-action catalog keeps those PowerShell command strings,
output artifacts, elevation boundaries, Quest lease metadata, QCL-079 generic
WebSocket candidate-vs-promoting boundaries, direct-Wi-Fi and QCL-082
dependency gates, and non-mutating firewall verify posture intact before WPF
row-projection tests render them for operators.
`HostessCompanion.Wpf.Tests` also checks that the WPF transport-gate model and
row projection preserve `data_protocols`,
`all_required_data_protocols_promoted`,
`all_wpf_transport_and_protocol_gates_clear`, and `completion_blockers`, so the
human Connectivity page shows the same strict protocol-plus-transport
completion state that `--fail-on-incomplete` enforces for automation.
The WPF Protocol Matrix action follows that sequence: it runs the fixture
suite, generates QCL-020/QCL-030/QCL-040/QCL-041 topology limitation fixtures,
refreshes the QCL-082 Rusty Quest media-stream source-contract report through
`connectivity-probe run --media-stream-session-plan` when the sibling plan
exists, accepts QCL-082 broker/runtime status artifacts through
`connectivity-probe run --media-stream-runtime-status`, asks
`connectivity-probe protocol-matrix` for source selection and promotion state
with those topology reports as explicit `--input` files, writes the read-only
`connectivity-probe direct-wifi-product-media-plan` artifact for the same
topology, firewall, matrix, projection, and gate outputs, then asks
`companion-report projection --include-protocol-matrix-inputs
--direct-wifi-product-media-plan` for the normalized operator rows that the
Connectivity page renders. That plan is projected as checklist evidence only:
live direct-Wi-Fi topology, product listener firewall, and QCL-082 RMANVID1
media reports still own promotion. It then asks
`companion-report transport-gates --projection <projection>` for the
projection-derived gate report and renders `operator_next_actions` plus
per-gate `next_actions` as read-only operator rows. The flag keeps device-link
and connectivity-probe source selection inside the CLI route rather than WPF
row projection, and the transport-gates route keeps next-action command text,
elevation, Quest lease, and acceptance-artifact metadata in Hostess-owned CLI
artifacts.

With `--check-broker`, readiness also inspects the Manifold broker APK package,
activity, process, ADB forward mapping, forwarded local socket, and direct host
socket. These checks are warnings by default and become blocking only with
`--require-broker`.

Quest connectivity lab fixture validation is covered by:

```powershell
python -m unittest tools.test_hostessctl_connectivity_probe
python -m unittest tools.test_hostessctl_device_link_report
python -m unittest tools.test_hostessctl_connectivity_suite
python tools\hostessctl\hostessctl.py connectivity-probe test-suite --out target\connectivity-probe\device-link-test-suite.json --suite-id downloadable-install-suite --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run-suite --mode fixture --suite-id downloadable-install-suite --out target\connectivity-probe\device-link-suite-run.json --artifact-dir target\connectivity-probe\device-link-suite-run-artifacts --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-000 --mode fixture --fixture-profile qcl-000-usb-adb-pass --out target\connectivity-probe\qcl-000.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-010 --mode fixture --fixture-profile qcl-010-router-pass --out target\connectivity-probe\qcl-010-router-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-011 --mode fixture --fixture-profile qcl-011-pc-hotspot-pass --out target\connectivity-probe\qcl-011-pc-hotspot-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-020 --mode fixture --fixture-profile qcl-020-wifi-adb-session-pass --out target\connectivity-probe\qcl-020-wifi-adb-session-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-030 --mode fixture --fixture-profile qcl-030-local-only-hotspot-started --out target\connectivity-probe\qcl-030-local-only-hotspot-started.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-040 --mode fixture --fixture-profile qcl-040-wifi-direct-phone-peer-pass --out target\connectivity-probe\qcl-040-wifi-direct-phone-peer-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-041 --mode fixture --fixture-profile qcl-041-wifi-direct-windows-peer-pass --out target\connectivity-probe\qcl-041-wifi-direct-windows-peer-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-050 --mode fixture --fixture-profile qcl-050-rfcomm-control-pass --out target\connectivity-probe\qcl-050-rfcomm-control-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-051 --mode fixture --fixture-profile qcl-051-ble-gatt-status-pass --out target\connectivity-probe\qcl-051-ble-gatt-status-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-080 --mode fixture --fixture-profile qcl-080-app-owned-udp-freshness-pass --out target\connectivity-probe\qcl-080-app-owned-udp-freshness-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-081 --mode fixture --fixture-profile qcl-081-lsl-loopback-pass --out target\connectivity-probe\qcl-081-lsl-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-082 --mode fixture --fixture-profile qcl-082-media-binary-plane-pass --out target\connectivity-probe\qcl-082-media-binary-plane-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-082 --mode fixture --fixture-profile qcl-082-media-high-rate-json-misuse --out target\connectivity-probe\qcl-082-media-high-rate-json-misuse.json
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-083 --mode fixture --fixture-profile qcl-083-osc-loopback-pass --out target\connectivity-probe\qcl-083-osc-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-084 --mode fixture --fixture-profile qcl-084-zeromq-loopback-pass --out target\connectivity-probe\qcl-084-zeromq-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-079 --mode fixture --fixture-profile qcl-079-websocket-loopback-pass --out target\connectivity-probe\qcl-079-websocket-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability --input fixtures\connectivity-probe\qcl-080-app-owned-udp-freshness-pass.json --out target\connectivity-probe\qcl-080-app-owned.stream-capability.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability --input fixtures\connectivity-probe\qcl-081-lsl-loopback-pass.json --out target\connectivity-probe\qcl-081-lsl-loopback.stream-capability.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix --suite-run target\connectivity-probe\device-link-suite-run.json --out target\connectivity-probe\device-link-protocol-matrix.json --fail-on-error
```

`tools.test_hostessctl_connectivity_probe` is intentionally the stable unittest
entrypoint. The implementation tests live under
`tools\connectivity_probe_tests\` by family: fixture reports, QCL-082 media
receiver/product gates, QCL-079/WebSocket and data-protocol evidence, live
transport paths, parser coverage, and firewall rule profiles. Add new tests to
the focused family module while keeping this command stable for WPF/CLI parity
automation.

The test-suite descriptor is the installer-facing index. It must cover host,
toolchain, network adapter, firewall, device, protocol, and timing categories;
QCL-000/QCL-010/QCL-011/QCL-050/QCL-051/QCL-080/QCL-081/QCL-082/QCL-083/QCL-084/QCL-079 slots;
and reusable capability rows for Manifold command WebSocket, generic
WebSocket, UDP, LSL, OSC, ZeroMQ, RFCOMM, BLE/GATT, and binary media/TCP.
QCL-020/QCL-030/QCL-040/QCL-041 are explicit topology limitation probes and
remain opt-in; do not add them as required downloadable-install suite slots
without a separate promotion decision. QCL-040/QCL-041 live mode currently
emits a read-only Wi-Fi Direct preflight report and intentionally stays
blocked/non-promoting until peer discovery, group formation, bounded socket
exchange, and cleanup evidence exists.

Once a leased Quest-side or peer harness has produced a structured
`rusty.quest.connectivity_wifi_direct_lifecycle.v1` artifact, normalize it
through the same CLI route instead of treating the WPF UI as the promotion
owner:

```powershell
$ProbeId = 'QCL-041'
$LifecyclePlan = 'target\connectivity-probe\qcl041-wifi-direct-lifecycle-plan.json'
$LifecycleTemplate = 'target\connectivity-probe\qcl041-wifi-direct-lifecycle-template.json'
$LifecycleReport = 'target\connectivity-probe\qcl041-wifi-direct-lifecycle-source.json'
$TopologyReport = 'target\connectivity-probe\qcl041-live-wifi-direct-lifecycle.json'
python tools\hostessctl\hostessctl.py connectivity-probe wifi-direct-lifecycle-plan `
  --probe-id $ProbeId `
  --out $LifecyclePlan `
  --adb $Adb `
  --serial $QuestSerial

python tools\hostessctl\hostessctl.py connectivity-probe wifi-direct-lifecycle-template `
  --probe-id $ProbeId `
  --out $LifecycleTemplate

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id $ProbeId `
  --wifi-direct-lifecycle-report $LifecycleReport `
  --out $TopologyReport `
  --fail-on-error
```

The plan route is read-only and non-promoting: it records the PowerShell
command chain, Agent Board `quest:<quest-serial>` lease policy, expected
artifacts, and external live-source dependency that WPF renders. The template
route is a local contract aid only: it writes the expected source artifact
shape with `live_evidence=false` and blocked phases, so the normalizer keeps
`transport.direct_wifi_live_topology` pending until a leased live harness
replaces it with real evidence.

Use `QCL-040` plus `qcl040-*` artifact names for Android-phone peer lifecycle
evidence, or `QCL-041` plus `qcl041-*` artifact names for Windows-peer
lifecycle evidence. That output clears only
`transport.direct_wifi_live_topology` when feature, peer/API, permission,
discovery, group formation, bounded TCP socket exchange, and cleanup checks all
pass. Product TCP media over that topology still needs the separate QCL-082
RMANVID1 receiver/listener report.

The lifecycle normalizer requires concrete live details before promotion. The
source artifact must include a positive `peer_discovery.peer_count`, recorded
`group_formation.local_role` and `group_formation.peer_role`,
`socket_exchange.protocol=tcp`, bounded
`socket_exchange.payload_class=bounded_tcp_probe`, positive
`socket_exchange.messages_sent` and `socket_exchange.messages_received`
counters, and `cleanup.completed=true`. It must also include a `lease` or
`agent_board_lease` object proving an Agent Board `quest:<serial>` lease was
reserved before live Wi-Fi Direct steps and released after cleanup, with a
real lease id rather than a placeholder. A phase with only `status=pass`, or a
complete-looking artifact without the lease receipt, is not enough to clear
the topology gate.

LSL, OSC, ZeroMQ, and generic WebSocket protocol-fit smokes are covered by
host-loopback live reports. These are dependency/protocol checks, not Quest
topology promotion:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source host-loopback --out target\connectivity-probe\qcl081-live-host-loopback.json
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source host-loopback --out target\connectivity-probe\qcl083-live-host-loopback.json
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source manifold-zmq-loopback --zeromq-pattern pub-sub --zeromq-manifold-root S:\Work\repos\active\rusty-manifold --out target\connectivity-probe\qcl084-live-manifold-zmq-loopback.json
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source host-loopback --out target\connectivity-probe\qcl079-live-host-loopback.json
```

Live Wi-Fi Direct topology preflight uses serial-scoped ADB and read-only
Windows adapter inspection. It does not mutate Wi-Fi Direct state and it does
not clear `transport.direct_wifi_live_topology` by itself:

```powershell
$QuestSerial = '<quest-serial>'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-041 `
  --adb S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe `
  --serial $QuestSerial `
  --out target\connectivity-probe\qcl041-live-wifi-direct-preflight.json
```

QCL-079 can promote only when the endpoint source is broker-owned or
Quest-runtime-owned. The broker-owned Manifold route uses the stream
bridge-route descriptor/evidence pair, not the QCL-000 command WebSocket route:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-079 --websocket-source broker-owned-websocket --websocket-route-descriptor S:\Work\repos\active\rusty-manifold\fixtures\bridge-route\stream-websocket-ordered-route.json --websocket-route-evidence S:\Work\repos\active\rusty-manifold\fixtures\bridge-route\stream-websocket-ordered-evidence.json --out target\connectivity-probe\qcl079-live-manifold-websocket-broker.json --fail-on-error
```

The protocol evidence matrix is the WPF-equivalent CLI report for promotion
state. It rolls up suite/probe/device-link artifacts and marks each protocol as
`usable`, `usable_with_warnings`, `candidate`, `blocked`, `missing`, or
`rejected` with explicit missing gates. Fixture and host-loopback LSL/OSC/ZeroMQ
rows must remain candidates until Quest-runtime or broker-owned live QCL
evidence exists. QCL-000 fixture WebSocket evidence also remains candidate-only;
QCL-000 promotion requires a live `rusty.quest.device_link.v1` report with
runtime subscriber and applied command receipt evidence. QCL-079 generic
WebSocket host-loopback evidence is also candidate-only and never substitutes
for QCL-000 command authority or QCL-082 high-rate media transport; the
broker-owned QCL-079 path must reject command/control WebSocket descriptors.

Operator views that need the current promoted data-protocol rows should use the
same CLI artifact resolver as WPF:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix `
  --suite-run target\connectivity-probe\device-link-suite-run.json `
  --input target\connectivity-probe\qcl-020-wifi-adb-session-pass.json `
  --input target\connectivity-probe\qcl-030-local-only-hotspot-started.json `
  --input target\connectivity-probe\qcl-040-wifi-direct-phone-peer-pass.json `
  --input target\connectivity-probe\qcl-041-wifi-direct-windows-peer-pass.json `
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
  --latest-device-link-dir target\companion-session `
  --latest-stream-capability-dir target\connectivity-probe `
  --latest-stream-probe-id QCL-080 `
  --out target\connectivity-probe\device-link-protocol-matrix.json `
  --fail-on-error
```

`--latest-artifact-dir` recursively selects the newest valid
`rusty.quest.connectivity_topology_probe.v1` report per requested probe id from
the directory tree. Broad scans prefer independently produced run reports over
generated `*-artifacts` suite copies, and ignore protocol-matrix, validation,
and stream-capability sidecars.
`--latest-device-link-dir` selects the newest
`rusty.quest.device_link.v1` report, and `--latest-stream-capability-dir`
selects the newest stream descriptor per requested probe id plus that
descriptor's source probe report. The WPF Protocol Matrix action runs the
fixture suite for baseline coverage, refreshes the QCL-082 source-contract
probe report through the same CLI route when the Rusty Quest media-stream plan
exists, and then calls this route so CLI automation and human operators inspect
the same promotion rows.
Latest probe selection ranks evidence quality before file recency: a promoted
Quest-runtime or broker-owned QCL report stays the selected protocol row even
when a newer source-contract-only candidate exists. The WPF route still passes
the refreshed QCL-082 media-stream source-contract report as an explicit
matrix input so operators can inspect the dirty-camera fold-in contract without
letting it demote stronger live evidence.
When a recent WPF session and QCL-080 stream-capability run exist, this route
can reproduce the consolidated operator matrix: QCL-000 from live device-link,
QCL-050/QCL-051 from Bluetooth probe evidence, QCL-080 from live product UDP
evidence, and QCL-081/QCL-082/QCL-083/QCL-084 from their latest promoted
protocol artifacts.

The firewall plan artifact is also part of that CLI-equivalent path: for the
WPF QCL-080 UDP rule it records the exact follow-on
`connectivity-probe run --probe-id QCL-080 --udp-listener-helper
apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe
--udp-sender-source makepad-runtime` arguments, so
operators and automation use the same product listener rule rather than a
diagnostic Python allowance.

The QCL-081 stream-capability route is still useful before promotion: blocked
Quest-runtime preflight artifacts validate as descriptors with explicit LSL
discovery, sample-continuity, producer-owner, and promotion gates, so WPF can
show the same missing Quest-side `pylsl/liblsl` evidence that CLI automation
sees.

QCL-082 is the binary media-plane slot. The built-in fixture pass report
declares the TCP binary/H.264 packet shape, `RMANVID1` marker, timestamp
policy, bounded queue, drop/close backpressure behavior, and frame/byte/drop/
queue counters. Hostess can also ingest the Rusty Quest
`rusty.quest.media_stream_session.v1` source contract from the media/display
streaming branch and translate it into the same QCL-082 connectivity report.
That route accepts MediaProjection display-stream source contracts, rejects
high-rate JSON media payloads, and rejects shell-hidden display plans that are
not lab-only. Hostess can also ingest broker/runtime status artifacts with
`rusty.quest.media_stream.android_runtime_status.v1` or Manifold command ACKs
carrying `media_stream_runtime`. That broker-owned route proves accepted
`command.media_stream.*` commands, selected source/runtime state, consent or
lab-only gating, and binary-plane policy. Hostess can also arm a bounded TCP
`RMANVID1` receiver with `connectivity-probe rmanvid1-receiver-capture`; the
capture command writes the raw byte stream plus receiver sidecar/result
artifacts. The preferred QCL report fold-in route ingests that result through
`--media-stream-receiver-result`, resolves the capture, sidecar,
runtime-status, topology, and firewall paths from the result, parses stream
headers and packet records without decoding H.264, and joins receiver
queue/drop/backpressure/close evidence. The older explicit
`--media-stream-rmanvid1-capture` and sidecar/status/topology/firewall flags
remain lower-level compatibility inputs. Source contracts, runtime status
artifacts, and fixture receiver captures are CLI/WPF-visible candidate checks
only; promotion still needs live broker-owned or Quest-runtime receiver frame,
byte, drop, close-reason, and queue evidence. Product TCP media over direct
Wi-Fi additionally needs the receiver result paired with a promoted
QCL-040/QCL-041 direct-Wi-Fi topology report through the receiver capture
`--topology-report` field. Product listener readiness is a separate CLI-owned
artifact: verify the Hostess/WPF TCP listener firewall rule first, then attach
that report through the receiver capture `--firewall-report` field:

For live acceptance, prefer the orchestrated
`connectivity-probe qcl082-product-media-live-session` route over separate
`run-bridge-command-live-android` plus `rmanvid1-receiver-capture` fragments.
It writes the inspectable start-source request, starts the bounded RMANVID1 TCP
receiver, and only then sends the Quest/Manifold source command after its live
preflight passes. The route uses serial-scoped ADB, requires a `quest:<serial>`
lease for live headset work, and does not require an `adb-server:lifecycle`
lease unless the run also performs disruptive ADB daemon recovery or Wi-Fi ADB
setup. It does not mutate firewall state and does not clear product gates until
the follow-on QCL-082 fold-in and protocol-matrix/projection routes consume the
generated artifacts. A valid `quest:<serial>` lease is necessary but not
sufficient: the route also requires `--topology-report` to resolve to a
promoted direct-Wi-Fi topology report and `--firewall-report` to resolve to a
verified product Hostess/WPF listener firewall report. If either dependency is
missing or unready, Hostess writes a blocked receiver result with
`close_reason=blocked_missing_product_media_dependencies`, does not write the
start-source request, does not arm the receiver, and does not start the live
Android command.

If verification reports `product_rule_verified=false`, run the same command
with `--action apply` from an elevated PowerShell session, then rerun
`--action verify`. A non-elevated apply must emit a blocked report with
`hostess.issue.connectivity_probe.firewall_rule_requires_elevation`,
`elevation.blocked_before_mutation=true`, and `action_result.attempted=false`;
that report is useful operator evidence but does not clear the firewall gate.
The scoped rule name is part of the QCL-082 product contract and must stay
distinct from the default QCL-010 TCP echo rule.
For an auditable admin handoff, generate the elevated script from a normal
shell first; this writes the blocked report plus a PowerShell script that calls
the same Hostess CLI apply route and then the matching verify route:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe windows-firewall-rule `
  --action apply `
  --rule-profile qcl-082-rmanvid1-media `
  --program apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --out target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-apply.json `
  --handoff-script-out target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-apply.ps1 `
  --handoff-verify-out target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-verify.json
```

Validate generated handoff snippets with the bureau checker before documenting
or reusing them:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File S:\Work\agent-bureau\scripts\Test-AgentPowerShell.ps1 `
  -Path target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-apply.ps1 `
  -AsJson
```

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-session-plan S:\Work\repos\active\rusty-quest\fixtures\media-stream-sessions\display-composite-mediaprojection-h264.plan.json `
  --out target\connectivity-probe\qcl082-media-stream-session-plan.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-session-plan S:\Work\repos\active\rusty-quest\fixtures\damaged\media-stream-high-rate-json.plan.json `
  --out target\connectivity-probe\qcl082-media-stream-high-rate-json.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-session-plan S:\Work\repos\active\rusty-quest\fixtures\damaged\media-stream-shell-display-production.plan.json `
  --out target\connectivity-probe\qcl082-media-stream-shell-production.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-040 `
  --fixture-profile qcl-040-wifi-direct-phone-peer-pass `
  --out target\connectivity-probe\qcl040-wifi-direct-phone-peer-pass.json `
  --fail-on-error

$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
$QuestLeaseId = 'LEASE_ID_FROM_RESERVE_OUTPUT'
$QuestLeaseResource = "quest:$QuestSerial"
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
python tools\hostessctl\hostessctl.py connectivity-probe qcl082-product-media-plan `
  --out target\connectivity-probe\qcl082-product-media-direct-wifi-plan.json `
  --promoted-topology-report target\connectivity-probe\qcl040-wifi-direct-phone-peer-pass.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --adb $Adb `
  --serial $QuestSerial `
  --quest-lease-id $QuestLeaseId `
  --quest-lease-resource $QuestLeaseResource

python tools\hostessctl\hostessctl.py connectivity-probe direct-wifi-product-media-plan `
  --out target\connectivity-probe\direct-wifi-product-media-acceptance-plan.json `
  --qcl040-topology-report target\connectivity-probe\qcl040-live-wifi-direct-lifecycle.json `
  --qcl041-topology-report target\connectivity-probe\qcl041-live-wifi-direct-lifecycle.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-admin-handoff-verify.json `
  --qcl082-report target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json `
  --quest-lease-id $QuestLeaseId `
  --quest-lease-resource $QuestLeaseResource

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

python tools\hostessctl\hostessctl.py connectivity-probe qcl082-product-media-live-session `
  --bridge-command command.media_stream.start_source `
  --start-source-request-out target\connectivity-probe\media-stream-start-source.request.json `
  --bridge-evidence-out target\connectivity-probe\media-stream-start-source.bridge-evidence.json `
  --execution-out target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --validation-out target\connectivity-probe\media-stream-start-source.validation-report.json `
  --logcat-out target\connectivity-probe\media-stream-start-source.logcat.txt `
  --bind-host 0.0.0.0 `
  --port 9079 `
  --capture-out target\connectivity-probe\media-stream.rmanvid1 `
  --sidecar-out target\connectivity-probe\media-stream-receiver-sidecar.json `
  --topology-report target\connectivity-probe\qcl040-wifi-direct-phone-peer-pass.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --capture-kind live_broker_stream `
  --max-packets 240 `
  --adb $Adb `
  --serial $QuestSerial `
  --quest-lease-id $QuestLeaseId `
  --quest-lease-resource $QuestLeaseResource `
  --quest-lease-reserved-before-live-steps `
  --out target\connectivity-probe\media-stream-receiver-result.json `
  --fail-on-error

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
  --topology-report target\connectivity-probe\qcl040-wifi-direct-phone-peer-pass.json `
  --firewall-report target\connectivity-probe\qcl082-tcp-firewall-verify.json `
  --capture-kind live_broker_stream `
  --max-packets 240 `
  --quest-lease-id $QuestLeaseId `
  --quest-lease-resource $QuestLeaseResource `
  --quest-lease-reserved-before-live-steps `
  --out target\connectivity-probe\media-stream-receiver-result.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-receiver-result target\connectivity-probe\media-stream-receiver-result.json `
  --out target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json `
  --fail-on-error

python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix `
  --input target\connectivity-probe\qcl082-rmanvid1-receiver-capture.json `
  --out target\connectivity-probe\qcl082-rmanvid1-receiver-capture.protocol-matrix.json `
  --fail-on-error
```

The direct-Wi-Fi product-media acceptance plan is read-only. It composes the
existing lifecycle, topology, firewall, RMANVID1 receiver, protocol-matrix,
projection, and transport-gate routes so WPF and CLI automation inspect the
same remaining checklist; it does not run ADB, mutate Wi-Fi Direct, apply
firewall rules, parse media payloads, or clear pending gates without the
supplied evidence artifacts.

If the paired topology report is still experimental or unpromoted, the QCL-082
report remains valid for generic binary-media evidence but the
`protocol.media_product_topology_gate` check is `warn` and the WPF transport
summary keeps `transport.product_tcp_media_over_direct_wifi` pending. If the
firewall report is missing, scoped to Python, or not product-verified, the
`protocol.media_product_listener_firewall_gate` check stays skipped, blocked,
or warn and WPF keeps `transport.product_tcp_media_listener_firewall` pending.

The runtime-status-only route remains useful for broker command/source policy
checks. It accepts either the direct `rusty.manifold.command.ack.v1` artifact
or the Hostess `rusty.hostess.bridge_command.live_android_execution_evidence.v1`
sidecar emitted by `run-bridge-command-live-android`:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode fixture `
  --probe-id QCL-082 `
  --media-stream-runtime-status target\connectivity-probe\media-stream-start-source.live-android-execution.json `
  --out target\connectivity-probe\qcl082-media-stream-runtime-status.json `
  --fail-on-error
```

QCL-081 also has a broker-owned Manifold LSL evidence path for host-side
fold-in validation. Hostess shells to the Manifold JSON report, requires
`evidence_tier=broker_owned`, `authority.owner=rusty.manifold.transport`, and
passing bridge-route evidence before promotion:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source manifold-lsl-broker --lsl-manifold-root S:\Work\repos\active\rusty-manifold --out target\connectivity-probe\qcl081-live-manifold-lsl-broker.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability --input target\connectivity-probe\qcl081-live-manifold-lsl-broker.json --out target\connectivity-probe\qcl081-live-manifold-lsl-broker.stream-capability.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix --input target\connectivity-probe\qcl081-live-manifold-lsl-broker.json --out target\connectivity-probe\qcl081-live-manifold-lsl-broker.protocol-matrix.json --fail-on-error
```

This does not replace Quest-runtime evidence. `quest-runtime` remains blocked
until a Quest-side LSL producer or product study adapter can emit runtime-owned
sample continuity.

QCL-084 is the generic ZeroMQ data-protocol slot. Its primary proof is the
pure-Rust `rusty-manifold-zmq` PUB/SUB adapter consuming
`rusty.manifold.bridge.route_descriptor.v1` route profiles from the Manifold
lane. The public Rusty XR `rusty-xr-zmq` adapter remains compatibility
evidence, and Goofi is only an optional source-profile example through the
private sidecar adapter:

```powershell
cargo test -p rusty-manifold-zmq
cargo run -q -p rusty-manifold-zmq --example zmq_pub_sub_loopback --features runtime
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source native-rust-broker --zeromq-pattern pub-sub --zeromq-manifold-root S:\Work\repos\active\rusty-manifold --out target\connectivity-probe\qcl084-live-native-rust-broker.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe protocol-matrix --input target\connectivity-probe\qcl084-live-native-rust-broker.json --out target\connectivity-probe\qcl084-native-rust-broker.protocol-matrix.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source rusty-xr-zmq-loopback --zeromq-pattern pub-sub --out target\connectivity-probe\qcl084-live-rusty-xr-zmq-loopback.json
powershell -NoProfile -ExecutionPolicy Bypass -File S:\Work\repos\active\Rusty-XR-Private-Planning\prototypes\gonzo-zmq-bridge\tools\Invoke-GoofiNodeSmoke.ps1
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source goofi-sidecar --zeromq-pattern pub-sub --out target\connectivity-probe\qcl084-live-goofi-sidecar.json
```

`native-rust-broker` is the broker-owned promotion path for ZeroMQ. Hostess
accepts it only when the Manifold JSON report declares broker-owned evidence,
the Manifold transport owner, passing bridge-route evidence, a complete message
exchange, and no drop/decode counters. `manifold-zmq-loopback`,
`rusty-xr-zmq-loopback`, Goofi sidecar, host-loopback, and fixtures remain
dependency/profile evidence and must not be promoted by WPF alone.

Do not promote Goofi-specific PAIR/send_pyobj behavior into the generic
ZeroMQ module. The reusable module owns manifests, endpoint/open-mode config,
bounded queues, counters, and runtime feature gates; Goofi conversion stays in
an adapter/profile.

Live Bluetooth QCL-050/QCL-051 validation now has app-owned payload routes in
addition to the passive readiness probes:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
dotnet build tools\connectivity_probe\qcl050_rfcomm_client\qcl050-rfcomm-client.csproj
dotnet build tools\connectivity_probe\qcl051_ble_gatt_client\qcl051-ble-gatt-client.csproj
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-050 `
  --bluetooth-payload-source android-rfcomm `
  --bluetooth-message-count 3 `
  --bluetooth-timeout-seconds 35 `
  --adb $Adb `
  --serial $QuestSerial `
  --out target\connectivity-probe\qcl050-live-android-rfcomm.json
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-051 `
  --bluetooth-payload-source android-ble-gatt `
  --bluetooth-message-count 3 `
  --bluetooth-reconnect-count 1 `
  --bluetooth-timeout-seconds 60 `
  --adb $Adb `
  --serial $QuestSerial `
  --out target\connectivity-probe\qcl051-live-android-ble-gatt-reconnect.json
```

QCL-051 starts a Hostess T Android BLE/GATT server with bounded control-write
and status-read characteristics, runs the Windows WinRT BLE/GATT client
helper, and joins the Android and Windows reports under
`bluetooth_payload_probe`. If the Quest VR lockscreen or Meta system UI blocks
launch, the report is `blocked` with `bluetooth.activity_launch_state=blocked`;
this is a precondition failure, not a protocol result.

The 2026-06-28 reconnect run
`qcl051-live-android-ble-gatt-reconnect-20260628-02.json` reported
`status=pass`, validation `pass`, and `promotion.allowed=true`. Windows
completed two BLE/GATT sessions, the second after app/server cleanup and
rediscovery. Across both sessions it exchanged `6/6` bounded payloads; Android
received `6/6` writes and served `6/6` status reads. Joined Bluetooth bytes
were `1470`, Windows helper `round_trip_ms_p95=88.4335`, and
`bluetooth.reconnect_cleanup=pass`.

QCL-050 starts a Hostess T Android RFCOMM server and runs a Windows WinRT
RFCOMM client helper. The 2026-06-28 live run
`qcl050-live-android-rfcomm-20260628-01.json` reported `status=blocked`,
validation `pass`: Android opened the RFCOMM server socket and cleaned it up,
but Windows found no paired/discoverable RFCOMM service for the QCL-050 UUID.
This keeps RFCOMM out of promotion until manual pairing/service visibility and
reconnect are proven.

Live same-Wi-Fi QCL-010 validation requires a USB-authorized Quest on the same
network as the PC. The route uses serial-scoped ADB for observation, then tests
host/Quest LAN reachability separately:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-010 `
  --adb $Adb `
  --serial $QuestSerial `
  --out target\connectivity-probe\qcl-010-live-same-wifi.json
```

Live Windows PC-hotspot QCL-011 validation requires Windows Mobile Hotspot on
and the Quest joined to that hotspot. Use the hotspot interface address
(`192.168.137.1` on the current Windows default) as `--host-ip`:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-011 `
  --adb $Adb `
  --serial $QuestSerial `
  --host-ip 192.168.137.1 `
  --tcp-echo-port 18766 `
  --out target\connectivity-probe\qcl011-live-pc-hotspot.json
```

The 2026-06-28 live QCL-011 run produced
`qcl011-live-pc-hotspot-20260628-02.json`: Windows Mobile Hotspot was on,
the Quest was `192.168.137.117/24`, same-subnet passed, and Quest-to-PC TCP
echo passed with `tcp_connect_ms=484`. The report remained `warn` because the
active Windows network profile was `Public`, Quest-to-PC ICMP was blocked, and
the listener was still the scoped Python diagnostic `TCP/18766` rule rather
than the signed Hostess/WPF product rule.

Live same-Wi-Fi QCL-080 validation for the WPF-owned UDP listener requires the
WPF companion build output and a scoped inbound Windows Firewall rule for that
program, UDP port `18767`, the active profile, and `LocalSubnet` remote
address:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
python tools\hostessctl\hostessctl.py connectivity-probe windows-firewall-rule `
  --action apply `
  --program apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --protocol UDP `
  --port 18767 `
  --profile Public `
  --remote-address LocalSubnet `
  --rule-name "Rusty Hostess WPF QCL-080 UDP Freshness 18767" `
  --out target\connectivity-probe\wpf-qcl080-udp-firewall-apply.json
python tools\hostessctl\hostessctl.py connectivity-probe windows-firewall-rule `
  --action verify `
  --program apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --protocol UDP `
  --port 18767 `
  --profile Public `
  --remote-address LocalSubnet `
  --rule-name "Rusty Hostess WPF QCL-080 UDP Freshness 18767" `
  --out target\connectivity-probe\wpf-qcl080-udp-firewall-verify.json
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-080 `
  --adb $Adb `
  --serial $QuestSerial `
  --udp-port 18767 `
  --udp-sender-source makepad-runtime `
  --udp-listener-helper apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --out target\connectivity-probe\qcl080-live-wpf.json
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability `
  --input target\connectivity-probe\qcl080-live-wpf.json `
  --out target\connectivity-probe\qcl080-live-wpf.stream-capability.json `
  --fail-on-error
```

The 2026-06-28 live WPF-owned QCL-080 run produced
`qcl080-live-wpf-scoped-rule-20260628-01.json` and
`qcl080-live-wpf-scoped-rule-20260628-01.stream-capability.json`: 24/24 UDP
datagrams, `0.0%` loss, Makepad runtime marker `packetsSent=24/24`,
`senderSource=makepad-runtime`, `socketOwner=app-owned`, host listener
`HostessCompanion.Wpf.exe UDP/18767`, and descriptor status
`usable_with_warnings`. The warning remains the active Windows network profile
being `Public`; the scoped product-shaped firewall rule itself was present.
Current validation should also preserve the firewall verification report and
expect `product_rule_verified=true`; a generic listener allow rule or Python
diagnostic rule is only data-path evidence, not product readiness.
The firewall plan report should name the same WPF executable in
`probe_usage.connectivity_probe_args`, which keeps the subsequent QCL-080 run
bound to the product listener.

The 2026-06-29 refresh produced
`wpf-qcl080-firewall-verify-20260629-223107.json`,
`qcl080-live-wpf-product-20260629-223133.json`,
`qcl080-live-wpf-product-20260629-223133.stream-capability.json`,
`wpf-live-protocol-matrix-20260629-223238.json`, and
`wpf-live-projection-20260629-223238.json`: the firewall verification reported
`product_rule_verified=true` for
`HostessCompanion.Wpf.exe UDP/18767` on the active Public profile, the WPF
listener captured 24/24 app-owned Makepad runtime datagrams with `0.0%` loss
and `jitter_ms_p95=96`, the runtime marker reported `senderSource=makepad-runtime`
and `socketOwner=app-owned`, the stream descriptor remained
`usable_with_warnings`, and the protocol matrix selected QCL-080 as
`quest_runtime` / `promoted_with_warnings` with no missing gates.

For QCL-080 over a non-router topology, pass the topology metadata explicitly
so stream-capability descriptors do not inherit the default router label:

```powershell
$Adb = 'S:\Work\tools\Android\windows-sdk\platform-tools\adb.exe'
$QuestSerial = 'REPLACE_WITH_QUEST_SERIAL'
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-080 `
  --adb $Adb `
  --serial $QuestSerial `
  --host-ip 192.168.137.1 `
  --topology-owner pc_hotspot `
  --network-provider windows_mobile_hotspot `
  --udp-port 18767 `
  --udp-packet-count 24 `
  --udp-interval-ms 100 `
  --out target\connectivity-probe\qcl080-live-pc-hotspot.json
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability `
  --input target\connectivity-probe\qcl080-live-pc-hotspot.json `
  --out target\connectivity-probe\qcl080-live-pc-hotspot.stream-capability.json `
  --fail-on-error
```

The 2026-06-28 PC-hotspot QCL-080 runs proved UDP datagrams can arrive over
the hotspot, but did not promote the route. The corrected-topology artifact
`qcl080-live-pc-hotspot-lowrate-topologyfix-20260628-01.json` recorded
`18/24` datagrams, `25.0%` loss, and `jitter_ms_p95=1125`; its stream
capability descriptor was `rejected` because the route was degraded and still
used diagnostic sender/listener ownership.

For Makepad app-shell edits, run:

```powershell
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml companion_frontend
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde hostess_contracts
cargo test --manifest-path apps\hostess-t-makepad\Cargo.toml --features serde main_tests
```

The Makepad companion frontend fixture path is intentionally source-only:
`fixtures\companion\protocol-matrix-promoted.json` is a backend protocol
matrix report, and `fixtures\companion\companion-report-projection-pass.json`
is the normalized CLI-owned report view. Makepad reduces either artifact to
rows/markers without re-running artifact selection or changing the matrix
promotion policy.

For Windows companion shell edits, run:

```powershell
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
```

The WPF Session page invokes `companion-session run` and renders Hostess-owned
phases/actions/issues. The WPF Commands page invokes
`run-bridge-command-live-android` for the safe probe and renders the Hostess
execution sidecar. If that broker-stream route does not pass, the backend falls
back to `run-bridge-command-android` without broker authority as an explicit
app-private recovery shim. UI validation is the WPF build plus the companion
session and bridge-command backend tests; live headset acceptance also requires
a serial-scoped ADB target, broker socket, and broker-stream runtime receipts
through `runtime_accepted` and `applied`. Use the WPF Session receipt wait
envelope documented above for live acceptance; fallback-only recovery should
remain visible as a warning and must not promote QCL-000.

For projected-motion-breath desktop replay:

```powershell
python tools\hostessctl\hostessctl.py run-pmb-replay `
  --target desktop `
  --packages-root ..\rusty-manifold-packages `
  --out target\hostess-pmb-desktop-replay\pmb-desktop-replay.json
```

Native Rusty Quest Breathing Room setup is covered by
`tools.test_hostessctl_cli_parser`: when the sibling `rusty-quest` repo is
available, the canonical-profile test loads
`quest-native-renderer-breathing-room-pmb-scale.profile.json`, verifies that
Hostess emits the same property set, records the profile SHA-256, and preserves
every non-parameterized runtime-profile value exactly. The same test module
also rejects custom native PMB state/value stream IDs so the setup receipt,
broker publisher, and native renderer receipt policy stay on the same
canonical projected-motion-breath stream contract.

Quest, phone, ADB, BLE, APK, screenshot, and Perfetto checks are hardware or
platform validation. Use the documented Hostess commands and record evidence
bundles, but keep Agent Board reservations and headset leases scoped to the
actual shared-resource run.

Hostess validation should prove host packaging, launch, command bridging,
settings adoption, and evidence export. It must not redefine package semantics,
Matter CPU truth, Lattice relation truth, Manifold command authority, or
renderer backend policy.
