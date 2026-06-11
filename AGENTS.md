# Rusty Hostess Agent Notes

This repo contains Rusty Hostess T, the first-party install and test shell for
Manifold packages. It is allowed to contain platform APIs and installable test
apps. Keep `rusty-manifold` contract-first and keep `rusty-manifold-packages`
manifest/fixture-first.

Rusty Morphospace is the top-level project/platform umbrella. Hostess remains
an install/test shell product lane inside that umbrella; it can collect
evidence for Matter, Lattice, Manifold, Optics, Studio, and Quest flows without
becoming their schema or runtime authority.

Project-owned source in this repo is licensed `AGPL-3.0-or-later`. Keep
third-party dependencies, Makepad toolkit code, generated APKs, installer
bundles, signing material, captured evidence, device logs, platform SDKs,
binary releases, and external tools under their own provenance and notice
requirements; see `docs/LICENSING.md`.

## Scope

- Minimal host apps and scripts that consume Manifold package manifests.
- Live package validation slots for desktop, mobile, and headset profiles.
- Evidence JSON, validators, and build scripts for clean host tests.
- Lattice evidence collection for tracked view sets, poses, spatial input
  roles, frame-state binding, calibration, validity, confidence, and runtime
  capabilities when a host run needs situated relation proof.
- Makepad dependencies only inside Hostess Makepad shell crates.

## Non-Scope

- Legacy app integration.
- Product UI.
- Dynamic package loading.
- Long-lived background services.
- Local-only planning paths, device serials, personal package ids, or old project
  names in committed files.
- Lattice contract authority. Hostess can collect evidence and run adapters,
  but generic relation schemas belong in Rusty Lattice and command/session
  authority remains Manifold.
- Makepad dependencies in Hostess core, CLI, validators, manifests, or
  descriptor logic.

## Validation

Run the narrow checks before committing:

```powershell
python -m py_compile tools\polar_protocol.py tools\check_live_capture_evidence.py tools\hostessctl\hostessctl.py tools\telemetry_snapshot.py tools\telemetry_stream.py tools\polar_runtime_bridge.py apps\hostess-t-desktop\capture_polar.py
python -m unittest tools.polar_protocol tools.test_check_live_capture_evidence tools.test_polar_runtime_bridge tools.test_telemetry_snapshot tools.test_makepad_morphospace_boundaries
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
```

For live captures, write raw run artifacts outside the repo and commit only
generic code or sanitized sample fixtures.

## Quest Makepad APK Route

For Hostess T Makepad Quest validation, build from
`apps\hostess-t-makepad` with the Morphospace Makepad Quest variant. Do not
add an app-local `resources\android\AndroidManifest.xml.template` just to
remove permissions; an incomplete custom manifest can remove required
`MakepadAppXr`/OpenXR Quest metadata and leave the headset stuck on the loading
screen.

Use the Work SSD Quest toolchain and the installed `cargo-makepad` from the
active Makepad fork:

```powershell
& 'S:\Work\tools\Quest\Use-QuestTooling.ps1'
cargo install --path S:\Work\repos\active\makepad-morphospace\tools\cargo_makepad --force
cd S:\Work\repos\active\rusty-hostess\apps\hostess-t-makepad
cargo makepad android --variant=quest --abi=aarch64 --sdk-path="$env:ANDROID_HOME" --package-name=io.github.mesmerprism.rustyhostess.makepad --app-label="Rusty Hostess Makepad" --quest-camera-permissions=false build -p hostess-t-makepad
```

The expected APK is
`apps\hostess-t-makepad\target\android\makepad-android-apk\hostess_t_makepad\apk\rustyhostessmakepad.apk`.
The `--variant=quest` flag is required for `.MakepadAppXr` and OpenXR broker
queries. The explicit package id keeps app-private settings staging aligned
with Hostess runtime reads. `--quest-camera-permissions=false` is the clean
camera-free path for particle-only tests; it preserves the generated Quest
manifest while omitting Android/headset/spatial camera permissions.

Stage effective settings into the app-private path before judging runtime
behavior:

```powershell
$adb = $env:RUSTY_XR_ADB
$package = 'io.github.mesmerprism.rustyhostess.makepad'
& $adb push S:\Work\repos\active\rusty-quest-makepad\fixtures\effective-settings\mesh-replay.effective-settings.json /data/local/tmp/makepad-effective-settings.json
& $adb shell "run-as $package sh -c 'mkdir -p files/hostess-t/settings && cp /data/local/tmp/makepad-effective-settings.json files/hostess-t/settings/makepad-effective-settings.json'"
& $adb shell am start -W -n "$package/.MakepadAppXr"
```

Launch the generated Quest/XR activity as `$package/.MakepadAppXr` for headset
evidence. `$package/.MakepadApp` is the Android launcher activity and can be
useful for fallback checks, but it is not the canonical Quest evidence launch.
Do not use the old `dev.makepad.android.MakepadApp` component for this
generated Morphospace package; it does not exist in the Hostess APK.

For camera-free particle runs, evidence should include no packaged
`android.permission.CAMERA`, no `horizonos.permission.HEADSET_CAMERA`, no
`horizonos.permission.SPATIAL_CAMERA`, `RUSTY_MAKEPAD_CAMERA2_ACQUISITION`
with `status=skipped reason=camera-streaming-disabled`,
`RUSTY_HOSTESS_MAKEPAD_CAMERA_DISCOVERY` with
`videoInputDiscoveryEnabled=false`, no app-UID headset/spatial camera
permission failures from passive Makepad media discovery, Matter runtime
markers, `RUSTY_QUEST_MAKEPAD_MATTER_SURFACE_WORKER` with `mode=latest-wins
workerThread=true renderThreadBlocking=false`, and
`RUSTY_QUEST_MAKEPAD_WORLD_PARTICLE_DRAW`.

For particle-density sweeps, keep animation and size explicit in evidence:
`makepad.particles.render.animation_mode=static-ring` and
`makepad.particles.render.size_scale=0.2` reduce visual animation/render cost
while measuring Matter compute. Log evidence should include
`particleRenderAnimationMode`, `particleRenderSizeScale`,
`particleCount`, `particleDrawLimit`, ready
`RUSTY_QUEST_MAKEPAD_WORLD_PARTICLE_DRAW` markers, `xrRepaintGpuMs`,
`xrRepaintTextureUploadBytes`, and Matter worker timing fields. The 2026-06-10
1024/2048/4096 run showed render/upload stayed light; serial Matter particle
stepping and backlog were the limiting path. To run the measured parallel
experiment, build this APK with `--features matter-particles-parallel` and set
`makepad.particles.execution.backend=rayon` plus a positive
`makepad.particles.execution.max_threads` only in generated/local effective
settings. The 2026-06-10 Rayon/4 run improved high-density Matter stepping but
still left backlog, so the next performance implementation should bound
simulation cadence before GPU compute.

Bounded density runs should patch only generated/local effective settings with
`makepad.particles.simulation.max_frame_delta_seconds` set to a positive cap
such as `0.022`; committed profiles keep `0` for unbounded behavior. Hostess
evidence should echo the cap in
`RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS` as
`matterSurfaceParticleMaxFrameDeltaSeconds`, and Matter runtime markers should
show `particleInputDeltaSeconds`, `particleSimulatedDeltaSeconds`, and
`particleDroppedDeltaSeconds`. The 2026-06-10 bounded Rayon/4 sweep showed
that static small billboards stayed render-light through the current
`8192`-instance draw cap: `xrEffectiveFrameRateHz=90.0`,
`xrRepaintTextureUploadBytes=0`, and GPU repaint about `0.40`-`1.19 ms`.
Matter worker time remained the bottleneck; a `16384` source-particle run
emitted `16384` Matter rows but drew `8192` instances with `droppedRows=8192`.
For compute-focused density runs, patch generated/local effective settings with
`makepad.particles.distance_refresh_policy=disabled` as well. Hostess should
echo this as `matterSurfaceParticleDistanceRefreshPolicy=disabled`; Matter
runtime markers should show `particleDistanceSamples=0`,
`particleRefreshSamples=0`, and `particleClosestSamples` equal to the source
particle count. Newer Quest-Makepad runtime markers also include
`particleSurfaceNodeTests`, `particleSurfaceLeafTests`, and
`particleSurfaceTriangleTests`; use those totals to judge Matter
surface-distance query shape before changing ADF, GPU, or mesh-resolution
strategy. The 2026-06-10 disabled-refresh Rayon/4 sweep at `1024` through
`32768` particles kept camera/collision/SDF off, `animation_mode=static-ring`,
and `size_scale=0.2`. App-owned cadence stayed
`90.0` Hz, texture upload bytes stayed `0`, and GPU repaint stayed about
`0.4`-`1.2 ms`; the remaining scaling pressure was Matter particle stepping
plus CPU payload/visual packing, not GPU rendering. Current Quest-Makepad
adapters apply `makepad.particles.render.draw_limit` before Optics visual-frame
resolution and Makepad row packing. Interpret `particleCount` and
`particleSourceRows` as full Matter source counts, `particleRows` as capped
visual rows, and `particleVisualRowLimit` as the effective cap. Hostess world
draw evidence should still report full `sourceRows`, drawn instances, and
`droppedRows`.

For force-source cadence experiments, Hostess only echoes the effective
settings parsed by Quest-Makepad. Evidence should include
`matterSurfaceParticleForceSource`,
`matterSurfaceParticleForceUpdateIntervalFrames`, and
`matterSurfaceParticleForceCompareProbeCount` in
`RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS`, plus the Quest-Makepad runtime
markers `particleForceSource`, `particleForceSourceStatus`,
`particleForceRefresh`, `particleSamplingAuthority`, `particleFieldSource`,
and `sdfAdfDebugParticleAuthority`. Normal profiles select exactly one force
authority at a time; nonzero compare-probe counts are bounded diagnostics only.
For `sdf-field` and `adf-field`, `particleForceSourceStatus=ready` proves the
Matter-owned CPU reference field was used; `particleSamplingAuthority` should
be `matter-sdf-field-sampler` or `matter-adf-field-sampler`, and
`sdfAdfDebugParticleAuthority=false` must remain true because particles are not
driven by Hostess or Quest-Makepad debug visual payloads. In field modes,
`particleForceRefresh=reused` means the cached Matter field was reused while
particles still sampled it for the current step.

The 2026-06-11 indexed ADF pre-GPU sweep at
`S:\Work\tmp\quest-makepad-indexed-adf-pre-gpu-sweep-20260611-141903` is the
current evidence baseline. At 1024 Matter particles / 1024 visual rows against
the recorded Meta Quest hand mesh, `sdf-field` averaged `5.466 ms` overall and
`2.181 ms` on reused cached-field steps; indexed `adf-field` averaged
`6.922 ms` overall and `4.141 ms` reused, improving the previous ADF reused
mean by about `12.5%` but remaining slower than SDF. XR-activity extended
captures held `xrEffectiveFrameRateHz=89.99`, `xrRepaintTextureUploadBytes=0`,
and GPU repaint around `0.42 ms`. Treat this as the stop point for default CPU
ADF micro-tuning before the GPU-backed phase unless a correctness or evidence
marker bug appears.

A focused 2026-06-11 headset run at `32768` source particles
with draw limit `8192` confirmed payload/visual/upload work now scales with the
cap (`9.823` / `10.474` / `0.280 ms` means) while `particleStepMs` still
reflects full Matter compute. Evidence:
`S:\Work\tmp\quest-makepad-visual-row-cap-density-20260611-0013`.
A follow-up Matter hot-path allocation cleanup, validated in
`S:\Work\tmp\quest-makepad-hotpath-allocation-density-20260611-0044`,
reduced the same `32768`/`8192` profile's `particleStepMs` mean from
`433.741` to `404.871` without changing particle truth or visual cap markers.

For the first ADF headset proof, patch only generated/local effective settings
with `makepad.sdf_adf.overlay_mode=adf`. Keep camera streaming off and use the
camera-free APK route with `--quest-camera-permissions=false`. Evidence should
include `RUSTY_HOSTESS_MAKEPAD_EFFECTIVE_SETTINGS` with
`sdfAdfRuntimeMode=adf`, `matterSurfaceAdfDebugEnabled=true`, and the default
ADF config fields, followed by `RUSTY_QUEST_MAKEPAD_MATTER_SURFACE_RUNTIME`
with `nativeMatterRuntime=true`, `wasmRuntimeUsed=false`,
`shaderScaffoldUsed=false`, `adfDebugEnabled=true`, `adfStatus=ready`,
`adfSchema=rusty.quest.makepad.matter_adf_debug.v1`, and
`adfVisualSchema=rusty.optics.adf.debug.visual.v1`. Hostess must consume the
Quest-Makepad adapter boundary only; do not move ADF leaf cells into
effective settings, Android properties, command JSON, or Hostess-local math.
The first proof passed on 2026-06-11 with APK SHA256
`AD4C2416096D7FABDE9A751B04DA7ECF94EE6FAA520641BC2E294D0DA0A59BD3`.
Evidence:
`S:\Work\tmp\quest-makepad-adf-evidence-20260611-040006`.
The run showed eight ADF-ready Matter runtime markers, camera acquisition
skipped because streaming was disabled, camera discovery disabled, no packaged
camera permissions, no camera-permission failures, and strict fatal/ANR count
zero.
Hostess ADF world debug drawing lives in
`apps/hostess-t-makepad/src/matter_world_adf_debug.rs`. It consumes
`QuestMakepadWorldAdfDebugBatch` and should emit
`RUSTY_QUEST_MAKEPAD_WORLD_ADF_DEBUG_DRAW` with
`renderer=hostess-makepad-adf-debug-cell-boxes`,
`renderMode=adf-debug-cell-boxes`, `cellRows`, `drawnCells`, `droppedCells`,
and `dataPlane=makepad-world-adf-debug-cells`. Keep this renderer a
Makepad/Hostess evidence consumer only; ADF construction and interpretation
remain Matter/Optics/Quest-Makepad adapter responsibilities.
