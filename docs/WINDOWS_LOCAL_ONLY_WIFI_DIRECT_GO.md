# Windows local-only Wi-Fi Direct group owner

`tools/connectivity_probe/b11_wifi_direct_legacy_go` is a bounded Windows
diagnostic that creates a Wi-Fi Direct autonomous group owner through WinRT
`WiFiDirectAdvertisementPublisher` and `LegacySettings`. It does not enable
Mobile Hotspot, ICS, NAT, or connection sharing, or change the host Wi-Fi
association. Its isolation checks read the relevant sharing and routing state.
It is a lab topology provider, not a general-purpose access point or background
service.

The provider reads one private JSON request from stdin:

```json
{
  "schema": "rusty.hostess.wifi_direct_legacy_go.request.v2",
  "operation_id": "b11-go-0123456789ab",
  "ssid": "B11-012345abcdef",
  "passphrase": "replace_with_private_value",
  "duration_ms": 600000,
  "output_root": "<absolute-private-existing-run-directory>",
  "ready_name": "go-ready.json",
  "receipt_name": "go-terminal.json",
  "health_port": 47831
}
```

`operation_id` is a bounded lowercase token, the SSID is `B11-` plus 12
lowercase hexadecimal characters, the passphrase is 8–63 characters from the
accepted ASCII set, ordinary runtime is 120–900 seconds, and the health port is
40000–59999. The supplied elevation wrapper is intentionally fixed to port
47831, matching its scoped firewall rule; use another accepted port only when
launching the provider through an equivalently reviewed firewall boundary. The
output directory must already exist, be absolute, and have no
reparse-point ancestor. Output files are create-new. Credentials remain in the
private request and never enter receipts or command-line arguments.

Readiness requires an exact new Wi-Fi Direct IPv4 `/24` interface, the listener
bound to that interface and requested port, no IPv4 or IPv6 default route on
the interface, IPv4 and IPv6 forwarding disabled, no advertised IPv6 default
route, no matching Windows NAT prefix, no ICS on the GO interface, and the
global IPv4 router setting disabled. These checks apply to the GO path and do
not remove or alter unrelated host NAT or the host's existing infrastructure
Wi-Fi association.

The health listener accepts only the bounded ASCII nonce exchange:

```text
B11ECHO1 <operation_id> <32-lowerhex-nonce>\n
B11ECHO1 OK <operation_id> <same-nonce>\n
```

No command execution, filesystem access, forwarding, or generic RPC is
exposed. Malformed echo requests are rejected and counted.

## Elevated launch and standard-user control

`Invoke-Elevated.ps1` is the single elevation boundary. It verifies the
apphost executable and effective DLL SHA-256 values, reads the request from a
private file, creates one temporary inbound firewall rule scoped to the exact
executable, TCP port 47831, and `LocalSubnet`, runs the provider, and
removes that exact rule in `finally`. Supply the request path and stdout/stderr
paths to the wrapper; do not place the SSID or passphrase on the command line.

The provider writes `<operation_id>.status.json` in the private output
directory. A standard-user process uses the same binary for typed control:

```powershell
& $exe --status $operationId $privateRunDirectory
& $exe --stop $operationId $privateRunDirectory
```

STOP first validates the current status identity and state. It writes the
three-field request through a closed same-directory temporary file and an
atomic no-overwrite move. The elevated loop uses share-safe reads, retries
transient control-file I/O for at most two seconds, validates the exact schema,
operation ID, and action, and deletes the request before acknowledging it. A
control-loop failure is observed by main and enters the same bounded GO cleanup
path instead of leaving the provider alive until TTL.

The terminal receipt is authoritative. `stop_observed` from the standard-user
client proves request consumption only. Acceptance requires the terminal
receipt to report `state=stopped`, `stop_observed=true`, and the matching
`stop_reason` (`explicit_stop` or `ttl_expired`), followed by provider and
wrapper exit and independent absence checks for the firewall rule, listener,
process, and connected virtual adapter.

The atomic publication is required by an observed Windows race in the earlier
implementation. That implementation exposed the final STOP path while holding
it with `FileShare.None`; the production reader could receive sharing violation
`0x80070020`, fault silently, and leave the request unconsumed. The regression
test now runs the production file-control loop under status-reader contention
and performs a real typed STOP through that loop.

## Validation boundary

Build and run the host-only regression with:

```powershell
dotnet build tools\connectivity_probe\b11_wifi_direct_legacy_go\b11-wifi-direct-legacy-go.csproj -c Release
dotnet run --no-build -c Release --project tools\connectivity_probe\b11_wifi_direct_legacy_go\b11-wifi-direct-legacy-go.csproj -- --self-test
```

The self-test uses temporary files and IPv4 loopback. It does not create a
publisher, change firewall state, or mutate networking. The Windows 11 live
qualification separately observed group creation, local nonce echo from a
Quest, blocked IPv4 and IPv6 external paths with positive controls on the
original network, TCP ADB UID 2000 over the local GO, TTL Stop-to-Stopped
cleanup, and a later host-only explicit STOP after repeated standard-user
STATUS calls. The explicit-STOP retest did not reconnect the Quest. These
results qualify that tested host/device combination and do not establish
post-reboot ADB bootstrap or a general product service.
