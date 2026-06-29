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
python -m py_compile tools\hostessctl\hostessctl.py tools\hostessctl\android_artifacts.py tools\hostessctl\android_files.py tools\hostessctl\bridge_command_android_routes.py tools\hostessctl\bridge_command_live_android_routes.py tools\hostessctl\bridge_command_routes.py tools\hostessctl\bridge_route_evidence.py tools\hostessctl\broker_telemetry_routes.py tools\hostessctl\broker_transport.py tools\hostessctl\cli_parser.py tools\hostessctl\companion_catalog.py tools\hostessctl\companion_readiness.py tools\hostessctl\companion_session.py tools\hostessctl\connectivity_probe.py tools\hostessctl\connectivity_suite.py tools\hostessctl\device_link_report.py tools\hostessctl\live_capture_routes.py tools\hostessctl\makepad_pmb_setup.py tools\hostessctl\manifold_recording.py tools\hostessctl\platform_defaults.py tools\hostessctl\pmb_android_routes.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_desktop_routes.py tools\hostessctl\pmb_evidence.py tools\hostessctl\pmb_host_run_evidence.py tools\hostessctl\pmb_native_receipts.py tools\hostessctl\pmb_support.py tools\hostessctl\recording_evidence.py tools\hostessctl\runtime.py tools\hostessctl\telemetry_render.py tools\hostessctl\telemetry_routes.py tools\telemetry_snapshot.py tools\telemetry_stream.py
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
python -m unittest tools.test_hostessctl_companion_catalog tools.test_hostessctl_companion_readiness tools.test_hostessctl_companion_session
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
evidence promotion, connectivity suite row grouping, and catalog-backed
workspace composition and validation-issue rows.

Every new WPF operator action needs UI-equivalent CLI coverage before it is
accepted as an operator capability. The minimum validation shape is: a
Hostess CLI or local API route that emits the structured report/sidecar the UI
renders, fixture or fake-mode coverage for that route, and a WPF projection
test proving the viewmodel surface maps the same evidence into human-facing
rows. WPF button handlers must not be the only executable path for setup,
commands, probes, firewall changes, or evidence export.
Every new WPF report view needs the same evidence-backed shape even when it is
read-only: a CLI/API report, descriptor, sidecar, receipt, or fixture output
must exist first, and projection tests must prove the page rows are derived from
that artifact.
The WPF test suite also reflects over `MainWindowViewModel` command properties
and compares them with `OperatorActionCatalog`, so a new command fails tests
until its CLI-equivalent route, evidence artifact, and test coverage are named.

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
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-050 --mode fixture --fixture-profile qcl-050-rfcomm-control-pass --out target\connectivity-probe\qcl-050-rfcomm-control-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-051 --mode fixture --fixture-profile qcl-051-ble-gatt-status-pass --out target\connectivity-probe\qcl-051-ble-gatt-status-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-080 --mode fixture --fixture-profile qcl-080-app-owned-udp-freshness-pass --out target\connectivity-probe\qcl-080-app-owned-udp-freshness-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-081 --mode fixture --fixture-profile qcl-081-lsl-loopback-pass --out target\connectivity-probe\qcl-081-lsl-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-083 --mode fixture --fixture-profile qcl-083-osc-loopback-pass --out target\connectivity-probe\qcl-083-osc-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe run --probe-id QCL-084 --mode fixture --fixture-profile qcl-084-zeromq-loopback-pass --out target\connectivity-probe\qcl-084-zeromq-loopback-pass.json --fail-on-error
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability --input fixtures\connectivity-probe\qcl-080-app-owned-udp-freshness-pass.json --out target\connectivity-probe\qcl-080-app-owned.stream-capability.json --fail-on-error
```

The test-suite descriptor is the installer-facing index. It must cover host,
toolchain, network adapter, firewall, device, protocol, and timing categories;
QCL-000/QCL-010/QCL-011/QCL-050/QCL-051/QCL-080/QCL-081/QCL-083/QCL-084 slots;
and reusable capability rows for Manifold WebSocket, UDP, LSL, OSC, ZeroMQ,
RFCOMM, BLE/GATT, and binary media/TCP.

LSL, OSC, and ZeroMQ protocol-fit smokes are covered by host-loopback live
reports. These are dependency/protocol checks, not Quest topology promotion:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-081 --lsl-source host-loopback --out target\connectivity-probe\qcl081-live-host-loopback.json
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-083 --osc-source host-loopback --out target\connectivity-probe\qcl083-live-host-loopback.json
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source manifold-zmq-loopback --zeromq-pattern pub-sub --zeromq-manifold-root S:\Work\repos\active\rusty-manifold --out target\connectivity-probe\qcl084-live-manifold-zmq-loopback.json
```

QCL-084 is the generic ZeroMQ data-protocol slot. Its primary proof is the
pure-Rust `rusty-manifold-zmq` PUB/SUB adapter consuming
`rusty.manifold.bridge.route_descriptor.v1` route profiles from the Manifold
lane. The public Rusty XR `rusty-xr-zmq` adapter remains compatibility
evidence, and Goofi is only an optional source-profile example through the
private sidecar adapter:

```powershell
cargo test -p rusty-manifold-zmq
cargo run -q -p rusty-manifold-zmq --example zmq_pub_sub_loopback --features runtime
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source rusty-xr-zmq-loopback --zeromq-pattern pub-sub --out target\connectivity-probe\qcl084-live-rusty-xr-zmq-loopback.json
powershell -NoProfile -ExecutionPolicy Bypass -File S:\Work\repos\active\Rusty-XR-Private-Planning\prototypes\gonzo-zmq-bridge\tools\Invoke-GoofiNodeSmoke.ps1
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-084 --zeromq-source goofi-sidecar --zeromq-pattern pub-sub --out target\connectivity-probe\qcl084-live-goofi-sidecar.json
```

Do not promote Goofi-specific PAIR/send_pyobj behavior into the generic
ZeroMQ module. The reusable module owns manifests, endpoint/open-mode config,
bounded queues, counters, and runtime feature gates; Goofi conversion stays in
an adapter/profile.

Live Bluetooth QCL-050/QCL-051 validation now has app-owned payload routes in
addition to the passive readiness probes:

```powershell
dotnet build tools\connectivity_probe\qcl050_rfcomm_client\qcl050-rfcomm-client.csproj
dotnet build tools\connectivity_probe\qcl051_ble_gatt_client\qcl051-ble-gatt-client.csproj
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-050 `
  --bluetooth-payload-source android-rfcomm `
  --bluetooth-message-count 3 `
  --bluetooth-timeout-seconds 35 `
  --adb <adb.exe> `
  --serial <quest-serial> `
  --out target\connectivity-probe\qcl050-live-android-rfcomm.json
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-051 `
  --bluetooth-payload-source android-ble-gatt `
  --bluetooth-message-count 3 `
  --bluetooth-reconnect-count 1 `
  --bluetooth-timeout-seconds 60 `
  --adb <adb.exe> `
  --serial <quest-serial> `
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
python tools\hostessctl\hostessctl.py connectivity-probe run --mode live --probe-id QCL-010 --adb <adb.exe> --serial <quest-serial> --out target\connectivity-probe\qcl-010-live-same-wifi.json
```

Live Windows PC-hotspot QCL-011 validation requires Windows Mobile Hotspot on
and the Quest joined to that hotspot. Use the hotspot interface address
(`192.168.137.1` on the current Windows default) as `--host-ip`:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-011 `
  --adb <adb.exe> `
  --serial <quest-serial> `
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
  --adb <adb.exe> `
  --serial <quest-serial> `
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

For QCL-080 over a non-router topology, pass the topology metadata explicitly
so stream-capability descriptors do not inherit the default router label:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-080 `
  --adb <adb.exe> `
  --serial <quest-serial> `
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
a serial-scoped ADB target, broker socket, and runtime receipt.

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
