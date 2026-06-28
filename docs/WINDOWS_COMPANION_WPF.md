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
- Evidence view derived from companion module evidence bindings.
- Hostess `companion-readiness` refresh command.
- Hostess `companion-catalog` descriptor refresh command.
- Hostess `companion-session run` command for the reusable session
  orchestration path.
- Hostess `run-bridge-command-live-android` safe probe command, with
  app-private Android staging as the recovery path.
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

## Build

```powershell
dotnet build apps\hostess-companion-wpf\HostessCompanion.Wpf.csproj
```

The repo-local `tools\check_all.ps1` runs this build when the project exists.
