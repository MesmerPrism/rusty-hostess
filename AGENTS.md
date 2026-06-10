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
