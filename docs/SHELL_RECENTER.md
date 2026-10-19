# Shell recenter operator action

`companion-session shell-recenter` is the single Hostess developer/operator
action for the Quest-owned privileged recenter adapter. The maintained provider
is `tools/shell_recenter/quest_shell_recenter.py` in `rusty-quest`. Hostess does
not implement the AppFunction call or send its own ADB commands. The operation
requires a genuine Android shell UID 2000 context; an ordinary installed APK
cannot use this action. This is not a Store/Lite capability.

The reviewed upstream source is Quest commit
[`de777c105e400828011d0f8d97256dd6cf15fc2b`](https://github.com/MesmerPrism/rusty-quest/commit/de777c105e400828011d0f8d97256dd6cf15fc2b).
[The source pin](../fixtures/shell-recenter/provider-source.json) records its
tree, provider SHA-256 and module source ID. That pin qualifies the source
contract and passive consumer test only. Each live profile still needs its
own exact build artifact and current device/firmware/operator identity; it
does not inherit an old execution authorization or an observed effect.

The Windows Commands page invokes the same CLI route and displays rows from
`companion-report projection --shell-recenter`. Catalog metadata names the
shell privilege and independent effect-observation requirement. The operator
action catalog records Quest custody, host/device mutation, and the absence of
ADB daemon lifecycle ownership. Readiness and passive reconciliation remain
available as lifecycle modes of this same named action.

## Exact private inputs

Create a private JSON profile outside tracked source:

```json
{
  "$schema": "rusty.hostess.companion.shell_recenter.profile.v1",
  "provider": {
    "path": "<absolute path to quest_shell_recenter.py>",
    "sha256": "<exact 64-character lowercase SHA-256>"
  },
  "request": {
    "schema": "rusty.quest.shell_recenter.request.v1",
    "request_id": "<fresh 32-character lowercase hex>",
    "nonce": "<fresh 32-character lowercase hex>",
    "adb": "<absolute executable path>",
    "canonical_serial": "<current canonical headset serial>",
    "selector": "<current serial-scoped transport selector>",
    "boot_id": "<current canonical boot UUID>",
    "operator_id": "<current responsible operator ID>",
    "artifact": {"path": "<absolute dex.jar path>", "sha256": "<exact hash>", "bytes": 1},
    "source": {"revision": "<40-character commit>", "tree": "<40-character tree>", "source_id": "<64-character build source ID>"},
    "firmware": {"fingerprint": "<current exact fingerprint>", "vrshell_sha256": "<exact hash>", "framework_sha256": "<exact hash>"},
    "output_dir": "<fresh absolute output directory with an existing parent>"
  }
}
```

The example is a shape guide, not executable evidence. Obtain artifact/source
pins through the Quest owner's build receipt and follow its shell recenter
runbook. Quest validates the closed request, clean source, current device,
boot, firmware, real shell context, permission and readiness. No historical
serial, transport, firmware or APK authorization is selected automatically.
Hostess holds the profile/provider and captured request under its Windows
immutable input binding throughout the provider invocation.

Before any live mode, negotiate current physical custody with the actual device
owner and reserve that exact Quest resource. Account for calibrated scenes and
reference-frame changes. A local profile, catalog row or callback cannot grant
custody. Preserve existing apps/data, watchdogs, shared ADB and other headsets.
The route does not manage Agent Board leases or the ADB daemon.

```powershell
python tools/hostessctl/hostessctl.py companion-session shell-recenter `
  --profile <private-profile.json> --mode readiness --out <readiness-report.json>
```

Use a fresh request ID, nonce and output directory for the subsequent explicit
`--mode recenter`. Readiness never becomes a dispatch. Once a request has an
intent, repeating it never launches a second recenter, even after success or an
observer failure. Quest also owns a durable per-user original-identity journal:
reusing the request ID with another nonce, output directory or mode is rejected.
Deleting output evidence leaves the original held and cannot recreate or replay
it. Inspect it with:

```powershell
python tools/hostessctl/hostessctl.py companion-session shell-recenter `
  --profile <original-private-profile.json> --mode reconcile --out <observation.json>
python tools/hostessctl/hostessctl.py companion-report projection `
  --shell-recenter <observation.json> --out <projection.json> --fail-on-error
```

Reconciliation invokes only the Quest provider's passive exact-request receipt
reader. It does not inspect or change the live device. A missing/malformed
receipt leaves the original unknown, with cleanup held; it is never a retry
instruction. Keep the original profile and adjacent Hostess intent/request
files. The intent is exclusively created and flushed before provider launch.

## Evidence and retirement

The Hostess report (`rusty.hostess.companion.shell_recenter.v1`) preserves the
Quest result and exposes availability, dispatch, original callback, effect,
original retirement and cleanup as separate fields/rows. It also records the
exact profile/request/provider/source/artifact pins, current target/operator
identity and the Hostess binary process-observation receipt. Callback success
does not verify reference-space movement, pose changes or a wearer-visible
effect; the provider's effect state remains `unverified`.

The synchronous caller retains the provider child and both stream readers
through genuine exit, EOF and reap. There is no observer deadline, forced kill,
automatic retrigger or ordinary APK fallback. Quest separately retains its
Android original through its genuine callback/error and owned-stage cleanup.
An unresolved original may keep the command pending indefinitely; this is not
permission to relaunch it. A process crash/reboot cannot be described as
graceful withdrawal or successful cleanup.

See [VALIDATION.md](VALIDATION.md) for source/consumer checks. Host neutral-child
tests and passive producer/consumer checks establish caller and contract
behavior; they do not establish live headset acceptance or an observed effect.
