# Independent Quest display receivers

This experimental AGPL-3.0-or-later source exposes the existing four-source
Hostess CLI/API receiver. It does not add a WPF display page. The separately
maintained [Meta casting guide](meta-quest-casting-adapter.md) controls opaque
MQDH presentation; those bytes are not this independent receiver protocol.

| `--source` | Producer and bytes | Required tools/authority |
| --- | --- | --- |
| `adb-screenrecord` | Android shell `screenrecord`, raw AVC | Explicit selected ADB target; supported screenrecord dimensions/time limit |
| `shell-mirror` | Independently authored Quest hidden display mirror, RMANVID1 | Genuine shell UID; built shell jar; positive finite duration |
| `scrcpy` | External scrcpy process records MKV/AVC | Separately installed compatible scrcpy; its server/protocol remains external |
| `media-projection` | Quest consent Activity/service, RMANVID1 | Built/installed Quest display-stream APK; attended Android MediaProjection consent |

Python 3.11+ is sufficient for source/import/host tests. The four-source route
uses `tools/hostessctl/hostessctl.py display-stream run` and the same public
`display_stream.run_display_stream(args)` handler. The operator selects ADB and
a target explicitly. No device operation runs on import or help. Before actual
headset operations, arrange exclusive device ownership under your local
coordination policy. These commands are recipes, not evidence of a current run.

The independently authored producer source is published in
[Quest PR 130](https://github.com/MesmerPrism/rusty-quest/pull/130), pending main acceptance.
Build the independent generic producer in
[Quest](https://github.com/MesmerPrism/rusty-quest/blob/031f7c360dad17aac1aac064d80fa0a8dcff2207/apps/display-stream-android/README.md):
`pwsh -NoProfile -File tools/Build-DisplayStreamAndroid.ps1 -AndroidHome <sdk> -JavaHome <jdk17>`.
The output folder `target/display-stream-android/` contains
`rusty-quest-display-stream.apk`, `rusty-quest-display-mirror-shell.jar` and a
build receipt. API 34 compilation does not qualify hidden display APIs on every
Quest firmware. Native systemdriver square capture is a separate producer;
see the Quest native browser capture source and QMS browser documentation.

From Hostess, use explicit private output paths and replace sample selectors:

```powershell
python tools/hostessctl/hostessctl.py display-stream run --source shell-mirror --adb <adb-executable> --serial <selected-target> --shell-jar <built-shell-jar> --duration-seconds 5 --out <private-output>/run.json --fail-on-error
python tools/hostessctl/hostessctl.py display-stream run --source media-projection --adb <adb-executable> --serial <selected-target> --duration-seconds 5 --out <private-output>/projection.json --fail-on-error
python tools/hostessctl/hostessctl.py display-stream run --source adb-screenrecord --adb <adb-executable> --serial <selected-target> --duration-seconds 5 --out <private-output>/screenrecord.json --fail-on-error
python tools/hostessctl/hostessctl.py display-stream run --source scrcpy --adb <adb-executable> --serial <selected-target> --scrcpy <scrcpy-executable> --duration-seconds 5 --out <private-output>/scrcpy.json --fail-on-error
```

MediaProjection defaults to the normal consent prompt. `--install-apk --apk`
is explicit installation; `--media-projection-consent pregrant` is an optional
lab permission mutation that records/restores the previous app-op. Failed or
unrecognized prior-state readback blocks this mutation. It is not
consent bypass qualification. Optional `--preview --ffplay <executable>` uses
an external low-latency player; `--ffmpeg <executable>` adds a decode check.
No third-party binary, SDK, capture or personal device configuration is bundled.
Use `run --help` for capture retention and output controls. Runtime artifacts
can contain personal images/identities and belong outside source commits.

The finite shell route creates exclusive per-run staging and a new-only reverse;
it never uses a class-wide Stop. Its current hello/terminal join plus genuine
zero child exit permits finite staging cleanup. Legacy completion markers remain
diagnostic only. Unconfirmed shell outcomes fail and retain staging and the original reverse.
Reverse removal requires a fresh exact mapping match; foreign replacements are
retained and reported unknown. A screenrecord PID
discovered after capture is unbound and is never signaled by this route; the
report records retirement as unknown. This finite diagnostic
is not the controlled adapter's stronger original-actor retirement proof.
For shell streams that run until explicit Stop, use the
[owned child adapter](OWNED_DISPLAY_ADAPTER.md), not a finite route stop-file.
`display-stream stop` writes only the local stop-file request; it is not proof
of producer retirement. Viewer disconnection and producer lifetime are separate.

RMANVID1v1 has a 32-byte stream header, bounded UTF-8 JSON metadata and 32-byte
packet headers: original AVC PTS, codec-config/key flags, payload length and two
emission-clock fields. Configuration is handled before video PTS ordering.
Emission clocks describe packet emission, not capture-to-display latency;
zero means unavailable for sources without those clocks. Decode progress is
not a rendered frame, GPU duration or headset acceptance. Historical retained
runs do not qualify changed binaries or current firmware.

The MIT QMS browser consumes this AGPL implementation out of process through
its documented binary/control protocol. Quest retains platform capture and
producer lifecycle ownership; Hostess retains operator/receiver ownership.
Do not copy platform implementation into the MIT bridge.

Host-only checks (no ADB/device effects):

```powershell
python -m unittest tools.test_hostessctl_display_stream tools.test_hostessctl_display_stream_qms tools.test_hostessctl_display_stream_routes
pwsh -NoProfile -ExecutionPolicy Bypass -File tools/check_all.ps1
```

Tests exercise actual RMANVID1 parsing/socketpair capture, bounded preview queue
recovery, the executable child rejection boundary, shared CLI dispatch, pinned
bindings and modeled exact Stop/retirement/failure transports. Physical streaming,
Android consent UI and actual remote stdin/EOF still need their own qualification.
