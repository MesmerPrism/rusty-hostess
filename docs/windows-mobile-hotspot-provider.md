# Windows Mobile Hotspot Provider

`rusty-hostess-hotspot-provider.exe` is the Hostess-owned Windows effect
adapter for Rusty Fleet. It is separate from the QCL-011 read-only probe and
from the QCL-041 Wi-Fi Direct `LegacySettings` helper. Fleet owns scheduling,
policy, retries, and desired state; this executable owns only bounded Windows
Mobile Hotspot effects and receipts.

## Invocation and execution protocol

The only accepted execution command line is case-sensitive:

```text
rusty-hostess-hotspot-provider.exe integration windows-hotspot --json
```

The process reads exactly one JSON object from stdin and writes exactly one
compact JSON receipt to stdout. Handled outcomes leave stderr empty.

Request schema: `rusty.hostess.windows_hotspot.provider_request.v1`

Required fields are `schema`, `request_id`, `operation_id`, `action`,
`expires_at_utc`, and `timeout_ms`. `action` is exactly one of `status`,
`start`, `ensure`, or `stop`. `ownership_generation` is required for `stop`,
optional for `ensure`, and forbidden for `status` and `start`. Unknown,
duplicate, incorrectly cased, or malformed fields are rejected. Expiry must be
in the future and no more than ten minutes away; timeouts are 100–120000 ms.
Request and operation IDs are replay-protected by the private state store.

Receipt schema: `rusty.hostess.windows_hotspot.provider_receipt.v1`

Receipts distinguish capability, operational state, client count and maximum,
configured band, and source connectivity. They never contain SSID,
passphrase, connection-profile identity, paths, IP addresses, or credentials.
Exit codes are `0` verified from fresh readback, `1` failed, `2` rejected, and
`3` unavailable.

## Inert capability discovery

The executable also accepts exactly:

```text
rusty-hostess-hotspot-provider.exe --describe-json
```

This route runs before stdin is read and before the effect-runtime system
clock, mutex, Windows backend, private state store, or effect provider is
initialized. It emits one compact
`rusty.quest.workflow.provider_capability_discovery.v1` document and exits.
Mixed, extra, alternate, or case-varied arguments fail closed with no output.

The descriptor is derived from `Protocol.Actions`; closed metadata must have
an exact key for every action or description fails. `status` is `observe`.
`start`, `ensure`, and `stop` are `effect`. Every action lists
`process-access-control` and `caller-authority-external` as minimum
authentication requirements. Effect actions also list
`effect-owner-profile`, and `stop` lists its mandatory
`ownership-generation`. Ensure's generation remains conditional and optional
under the existing execution request, so it is not presented as an
unconditional authentication requirement. These labels are descriptive
minimums, not execution grants.

The capability advertises only the existing
`rusty.hostess.windows_hotspot.provider_request.v1` contract, Hostess effect
owner, and existing `rusty.hostess.windows_hotspot.provider_receipt.v1`
receipt. Provider version comes from the executable's assembly/release
metadata and must use the shared contract's lowercase-prerelease SemVer
vocabulary. Core and numeric prerelease identifiers cannot have leading
zeroes, and dot-separated prerelease/build identifiers cannot be empty.
Valid assembly build metadata is checked and removed because the discovery
schema carries no build metadata; invalid informational metadata fails
discovery instead of advertising a different version. Availability lasts
exactly 300 seconds and means only that the provider described its registry.
It does not prove Windows support, authorization, configured-profile
readiness, hotspot activation, effective state, Fleet admission, or release
eligibility.

The shared schema and semantic validator remain owned by
`meta-quest-agent-workflow`; Hostess does not copy them. The Hostess validation
script requires the accepted exact shared commit and tree before applying that
validator. The descriptor carries no invocation, path, endpoint, network
name, credential, configured profile data, private owner state, target,
coordination record, approval, or generic execution surface.

## Effect and ownership rules

The Windows backend uses
`Windows.Networking.NetworkOperators.NetworkOperatorTetheringManager` against
the current Internet connection profile. It uses the already configured
Mobile Hotspot profile without reading or changing its SSID or passphrase.
Start/stop API results are not success evidence: a second fresh manager
readback must show `On`/`Off`.

The provider never adopts a hotspot that is already on. A successful start
creates a random ownership generation in a current-user LocalAppData record.
Ensure and stop preserve or require that exact generation. Wrong-generation,
takeover, damaged-state, inconsistent-state, and host-restart cases fail
closed. If an owned hotspot is freshly read back as Off, `ensure` with the
exact current generation may restart it only after fresh On readback and
retains the same generation on success or failure.

After a host restart, `status` returns `state.restart_detected` with a fresh
redacted snapshot, while `ensure` and `stop` reject the prior-boot generation.
An explicit new `start` can recover only from fresh Off state: successful
start/readback replaces stale ownership and replay history with a new
generation. Fresh On state is treated as external and is never adopted or
stopped. Stop and ensure failures retain ownership for later recovery. The
private record contains only boot identity, ownership generation, and bounded
replay IDs; it contains no hotspot configuration or credentials.

Private state schema v2 uses explicit `none`, `starting`, `active`, and
`stopping` phases. A generation is written in `starting` before calling the
Windows start API, and `stopping` is written before calling stop. Fresh
readback reconciles interrupted transitions: starting+On becomes active,
new-start starting+Off becomes none, ensure-restart starting+Off restores
active ownership, and stopping+Off becomes none. A stopping generation can
retry stop but can never ensure/restart. Final state-write failures therefore
produce failed receipts with truthful fresh readback while leaving a durable
phase that the next invocation can reconcile. Replay IDs are consumed before
effects and remain one-use across partial writes.

The loader strictly validates v2 phase/generation combinations and migrates
the previous v1 nullable-generation record to none/active. Unknown, duplicate,
or malformed private fields fail closed. Boot ownership uses the Windows boot
environment GUID, not a wall-clock/uptime calculation, so clock correction
does not resemble a restart. Provider processes serialize through a
cross-session `Global\RustyHostess.WindowsHotspot.Provider.v1` mutex; an
abandoned mutex is safely treated as acquired.

## Build and validation

The maintained script requires PowerShell 7:

```powershell
dotnet run --project tests\RustyHostess.WindowsHotspot.Provider.Tests\RustyHostess.WindowsHotspot.Provider.Tests.csproj
pwsh -NoProfile -File tools\Test-WindowsHotspotProviderArtifact.ps1
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\Test-WindowsHotspotProviderCapabilityDiscovery.ps1 -ContractRoot <meta-quest-agent-workflow-root>
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\check_all.ps1 -RequireProviderContract -ProviderContractRoot <meta-quest-agent-workflow-root>
```

Tests inject a fake backend, clock, and private state store. The artifact smoke
first proves that process-level discovery exits promptly with empty stderr and
does not create or change private state. It then uses an expired request plus a
valid read-only `status` request, so automated validation never mutates the
live hotspot and still exercises the real process-level synchronization and
WinRT readback boundary. The valid probe uses an internal, status-only
volatile journal and therefore cannot read, reconcile, or write the installed
provider's ownership state. The probe switch is an artifact-test surface, not
part of the Fleet provider contract. The publish gate produces the
self-contained single-file
`target\windows-hotspot-provider\rusty-hostess-hotspot-provider.exe`.

Plain `tools\check_all.ps1` intentionally remains a portable repo-local gate.
It reports shared-contract validation as skipped without a supplied root.
Cross-repository acceptance uses the dedicated validator command or the
explicit `-RequireProviderContract` combined mode, which fails closed when its
root is absent and never infers a machine or sibling path.

That executable is a build artifact, not a distributable release on its own.
Before another product packages it, generate and validate the Hostess-owned
release metadata described in
`packaging/windows-hotspot-provider/README.md`. Unsigned development metadata
is explicitly local-only; publication requires a valid Authenticode identity
revalidated against the artifact, verified public availability of the exact
source commit/tree, and `labs_signed_release` eligibility with
`allowed_channels: ["labs"]` and `stable_eligible: false`.
The time-varying discovery document is never included in provenance, hashed
as a release input, signed, or treated as a publishable artifact.
Artifact validation, release-metadata generation, and release validation use
the same descriptor-compatible provider-version predicate. The generator
rejects malformed core or prerelease identifiers during parameter binding,
before artifact inspection, dependency inventory, or clean rebuild work.
The tag-driven owner workflow documented in
`packaging/windows-hotspot-provider/README.md` is the only automated public
binary publication route. It requires protected Authenticode inputs, the
exact signer pins in the protected owner policy, exact public source
verification, and a new immutable GitHub Release. The current signer is
self-issued and exact-pinned for Labs only; no tool installs it into Root or
TrustedPublisher, no public Windows trust is claimed, and Stable remains
blocked until managed publicly trusted signing is reviewed. Provenance binds
the archived policy as one of five immutable assets. The discovery document
remains non-authorizing and is not a release asset.
