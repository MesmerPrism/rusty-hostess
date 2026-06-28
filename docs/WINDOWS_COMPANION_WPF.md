# Windows Companion WPF

`apps/hostess-companion-wpf` is the Windows companion shell. It is an
operational frontend over Hostess reports, Rusty GUI companion descriptors, and
Hostess/Manifold evidence routes.

## Current Scope

- Readiness view.
- Session view derived from `rusty.hostess.companion.session.v1` phases.
- Devices view derived from readiness device/runtime/network checks.
- Transports view derived from Rusty GUI transport capability descriptors.
- Commands view for the Quest broker-stream bridge probe.
- Connectivity view for scoped Windows Firewall planning, QCL-010 TCP
  verification, and QCL-080 UDP stream-capability verification.
- Evidence view derived from companion module evidence bindings.
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

## Authority Boundary

The WPF app is a requester and inspector. It does not decide that dependencies,
device state, broker routes, app-private receipts, or runtime behavior are
valid.

All readiness state comes from:

```powershell
python tools\hostessctl\hostessctl.py companion-readiness --out <report.json>
```

Descriptor catalog state comes from:

```powershell
python tools\hostessctl\hostessctl.py companion-catalog --out <catalog.json>
```

The shell reads `rusty.hostess.companion.readiness_report.v1` and
`rusty.hostess.companion.catalog.v1`.

The Session page calls:

```powershell
python tools\hostessctl\hostessctl.py companion-session run `
  --out target\companion-session\wpf-session.json `
  --frontend wpf `
  --profile hostess-makepad-quest `
  --adb <adb.exe> `
  --serial <quest-serial>
```

It renders the returned ordered phases, actions, issues, and artifact
references from `rusty.hostess.companion.session.v1`. Session orchestration,
fallback recovery, and evidence validation remain in `hostessctl`; WPF only
requests the run and displays the result. The session artifact list also
includes the Quest-owned `rusty.quest.device_link.v1` report, which is the
operator-facing summary for device identity, ADB forward state, broker
readiness, runtime subscriber health, command results, and stream capability
costs.

The Commands page safe probe calls:

```powershell
python tools\hostessctl\hostessctl.py run-bridge-command-live-android `
  --input fixtures\bridge-command\hostess-broker-stream-command-request.json `
  --out target\companion-command\wpf-broker-stream-probe-evidence.json `
  --adb <adb.exe> `
  --serial <quest-serial>
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
python tools\hostessctl\hostessctl.py run-bridge-command-android `
  --input fixtures\bridge-command\hostess-android-hotload-command-request.json `
  --out target\companion-command\wpf-app-private-probe-evidence.json `
  --adb <adb.exe> `
  --serial <quest-serial>
```

That fallback is app-private runtime staging. It is useful for recovery and
runtime receipt debugging, but it is not Manifold command authority.

The Connectivity page calls the same Hostess-owned probe routes. For TCP, it
keeps QCL-010 available:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-010 `
  --adb <adb.exe> `
  --serial <quest-serial> `
  --tcp-echo-port <port> `
  --out target\connectivity-probe\<run-id>.json
```

For UDP, the page uses QCL-080 with the WPF executable itself in listener
helper mode:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe run `
  --mode live `
  --probe-id QCL-080 `
  --adb <adb.exe> `
  --serial <quest-serial> `
  --udp-port 18767 `
  --udp-sender-source makepad-runtime `
  --udp-listener-helper apps\hostess-companion-wpf\bin\Debug\net9.0-windows\HostessCompanion.Wpf.exe `
  --out target\connectivity-probe\<run-id>.json
```

It then derives the reusable stream descriptor:

```powershell
python tools\hostessctl\hostessctl.py connectivity-probe stream-capability `
  --input target\connectivity-probe\<run-id>.json `
  --out target\connectivity-probe\<run-id>.stream-capability.json `
  --fail-on-error
```

The WPF app renders the report checks plus the
`rusty.quest.device_link.stream_capability.v1` descriptor requirements and
warnings. WPF does not decide that UDP is product-ready; it displays Hostess
firewall evidence, Makepad runtime sender evidence, packet counters, promotion
state, and remaining warnings.

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

## Build

```powershell
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
```

The repo-local `tools\check_all.ps1` runs this build when the project exists.
