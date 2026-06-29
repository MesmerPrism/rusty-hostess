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
python tools\hostessctl\hostessctl.py companion-readiness --out <report.json>
```

Descriptor catalog state comes from:

```powershell
python tools\hostessctl\hostessctl.py companion-catalog --out <catalog.json>
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

Use `--action apply` or `--action remove` for elevated lifecycle changes.
Verification records `product_rule_verified` separately from generic
`allowed_on_active_profile`, so broad port-only rules and diagnostic Python
rules do not satisfy product readiness.

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
dotnet run --project tests\HostessCompanion.Wpf.Tests\HostessCompanion.Wpf.Tests.csproj
```

The repo-local `tools\check_all.ps1` runs the WPF build and projection tests
when the projects exist.
