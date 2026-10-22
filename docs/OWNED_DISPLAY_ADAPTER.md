# Owned display child adapter

`python -B tools/display_stream_qms.py display-stream-qms-v1` is an explicitly
started, one-invocation local child adapter. It is not a persistent background
service, generic shell, power manager or app-media authority. There are no device
operations on import or page load. QMS owns its child and browser fanout; Quest
owns independent display capture/encoding; the application owner owns bilateral
stream preparation, signed renewal and reconciliation.

The first stdin line is at most4096 UTF-8 bytes and has exactly schema
`questms.display.start.v1`, sourceId, invocationId, generation, stopNonce,
ownerBindingRef and outputDirectory. Write LF, not CRLF. Source/generation are
bounded ASCII opaque identifiers, invocationId/stopNonce lowercase32-hex.
ownerBindingRef is exact `{path,bytes,sha256}`. outputDirectory must be an absent
absolute backend-selected private path; the adapter creates it exclusively.
Neither a browser nor untrusted input may choose paths, executables or device IDs.

The immutable binding has exactly schema
`rusty.hostess.display_stream.owner_binding.v1`, adb, shellJar (exact three-field
pins), transport, canonical, bootId, remotePort, displayId, width, height, fps and
bitrateBps. Display settings are bounded; dimensions even. A fresh selected
canonical/boot is checked before effects. Existing QFM/platform custody and the
sole power writer remain separate prerequisites of the caller; the adapter never
changes awake/proximity/settings or restarts an ADB daemon.

The child stdout is binary RMANVID1v1 only; stderr contains only sanitized adapter
errors. Each source has its own invocation and exclusive temporary remote jar
directory, new-only reverse, exact app_process child and control/terminal proof.
The no-PTY remote child stdin carries exact nonce-bound Stop; remote stdout is
separate bounded JSON hello/terminal evidence. No ACK enters media bytes. The
adapter retains raw remote stdout/stderr through true EOF, checks exact remote
PID/start ticks/shell UID, and verifies that original actor is absent after exit.
The actual remote stdin/EOF path still needs device qualification.

An explicit local Stop line has exactly schema`questms.display.stop.v1`,
sourceId, invocationId, generation and stopNonce. A failed write, missing/mismatched
ACK, actor change, nonzero native exit or incomplete raw EOF stays unknown. The
operation is consumed; never replay it or kill a class-wide process. The source
jar and reverse are removed only after the exact retired proof, fresh boot and
unchanged owned mapping/bytes. A foreign reverse or changed jar is retained.

`TERMINAL.json` is create-new with exactly schema`questms.display.terminal.v1`,
sourceId, invocationId, generation, stopNonce, state, nativeChildExitCode,
nativeStdoutEof, nativeStderrEof, remoteAckMatched, resourcesRetired and receipt.
States are retired/failed/unknown. Retired requires the exact ACK, resources and
native0/full EOF; QMS independently requires this local child's zero exit/full
EOF. `NATIVE_OUTCOME.json` and raw child/action records retain evidence. No report
or observation deadline can force retirement, clear an uncertain owner or start
another producer. Viewer disconnection affects only that observer.

The adapter validates RMANVID1 version/codec/dimensions, metadata bounds and
invocation, config before keyframe, flags0..3, safe original PTS, strict video PTS
progress, packet/config bounds and truncation before forwarding bytes. Config
may share first-video PTS; no source timestamp/key flag is invented. Config bound
is262132 payload bytes to fit QMS's256KiB configuration envelope. Media buffers
are bounded; no disk video recording or second browser protocol is added.

The old finite display-stream compatibility route remains available, but its
class-wide shell Stop fallback is removed and unbounded/stop-file shell use is
denied in favor of this exact owner adapter. Legacy completion markers cannot
override native nonzero. This is a source-only repair until adopted and built.

Run `python -m unittest tools.test_hostessctl_display_stream_qms
 tools.test_hostessctl_display_stream` as one command. Tests use modeled ADB,
process and socket objects and actual adapter/wire code; no listener or device is
started. They cover repeated distinct runs, exclusive replay rejection, wrong
nonce/actor/release/live process, foreign reverse preservation, native1 retention,
unavailable peer before effects, config/key/PTS and truncation. A no-preview,
no-capture bilateral baseline precedes any owned display test. Visible frames and
app Peer flow remain separate acceptance dimensions; packet emission/decode
progress does not establish GPU duration or end-to-end latency.

For source/build and finite CLI recipes, see [DISPLAY_STREAMS.md](DISPLAY_STREAMS.md).
This Hostess source is AGPL-3.0-or-later. QMS consumes the binary/control
protocol out of process; it does not absorb Quest/Hostess platform code.
