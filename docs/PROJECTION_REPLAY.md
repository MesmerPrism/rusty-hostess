# Offline Projection Replay

`apps/hostess-projection-replay` is the Hostess-owned desktop validation host
for Vulkan projection effects. It is intended for fast work on guide passes,
blur, distortion, projection regions, RGB-selective seams, and premultiplied
alpha before a smaller final validation pass on the target headset.

## Ownership

Hostess owns:

- capsule validation and fail-closed ABI sizes;
- native Vulkan device selection and direct SPIR-V loading;
- generic stereo color, video, and two-layer depth inputs;
- deterministic synthetic inputs;
- guide and output image readback;
- shader/input/output hashing and the replay report.

The provider owns:

- shader source and compiled shader artifacts;
- product-specific uniform values and semantic labels;
- real camera/depth recordings and their consent/retention policy;
- effect-specific comparisons and acceptance thresholds.

Provider shaders, presets, captures, and rendered evidence are local artifacts.
They must not be copied into this repository.

## Capsule Contracts

The original capsule schema is
`rusty.hostess.projection_replay_capsule.v1`. It remains the only executable
capsule contract in this slice and binds:

- an even-width packed-stereo output extent;
- one fullscreen vertex shader, six guide fragment shaders, one final
  projection fragment shader, and an optional displacement vertex shader;
- independent left/right color sources, one packed video source, and a
  two-layer depth source;
- exact 112-byte guide pushes, 128-byte projection pushes, 96-byte RGB
  transport, 64-byte displacement transport, and 368-byte zone transport;
- independent projection scissors and named output-layer override values.

The packed video input may be a bounded `png-sequence` of one through 120
frames. `play-capture` accepts either one repeated frame or exactly one video
frame per recorded camera frame, and records the effective video frame beside
each output. This is a generic offline texture-replay facility: the
provider-owned capsule remains responsible for declaring that the texture is a
readable flat-video layer. Direct 180-degree and 360-degree media surfaces are
not sampled or flattened by Hostess.

The runner uses Vulkan combined image samplers at sets 0, 1, 2, and 4 and
uniform buffers at sets 3 and 5. It loads the referenced SPIR-V directly
through Vulkan; it does not translate the provider shader to another language.

The additive `rusty.hostess.projection_replay_capsule.v2` contract is an
effect-neutral declarative graph. It declares bounded resources, graphics
passes, dependencies, descriptor bindings, push ranges, render targets,
exports, and optional opaque provider labels. The supported vocabulary is
deliberately closed to operations already present in the Hostess renderer:
`rgba8-unorm` and `r32-sfloat` images, aligned bounded buffers,
combined-image-sampler and uniform-buffer descriptors, vertex and fragment
shader stages, descriptor sets 0 through 5, bindings 0 through 8, and color
render targets. Each v2 pass currently represents the implemented fullscreen
graphics operation and therefore requires exactly one vertex module and one
fragment module.

Hostess validates v2 before producing
`rusty.hostess.projection_replay_execution_plan.v1`. Validation rejects unknown
fields or enum values, duplicate identifiers or bindings, missing resources or
dependencies, dependency cycles, unordered conflicting writes,
internal reads without an explicit transitive producer dependency, multiple
writes even when dependency-ordered, resources without producers, excessive
counts or descriptor indices, descriptor byte-size or stage-visibility
mismatches, invalid push ranges, non-finite push or override values, and
absolute or traversing shader paths. Shader artifact validation checks aligned
minimum length, a 16 MiB size ceiling, and only the five-word little-endian
SPIR-V header: magic, versions 1.0 through 1.6, nonzero ID bound, and zero
reserved word. It does not claim full SPIR-V semantic or module-stage
validation. Simultaneously ready passes are ordered by portable pass identifier
and exports by portable export name, so normalization is deterministic and
does not depend on JSON declaration order. Top-level, pass, and export
provider-label values are limited to 256 bytes. V1 requested output names may
not shadow the five fixed guide export names.

Normalize either contract without executing it:

```powershell
apps\hostess-projection-replay\target\release\hostess-projection-replay.exe `
  normalize-plan `
  --capsule <v1-or-v2-provider-capsule.json> `
  --out <normalized-plan.json>
```

The explicit v1 compatibility adapter projects the existing six guide passes
onto the exact five-target reuse schedule
`0,1,2,3,1,4`, retains the existing descriptor sets and bindings, 112-byte
guide pushes, 128-byte projection pushes, 96/64/368-byte uniform buffers, five
guide exports, and each named final export's output override. It does not
replace or mutate the v1 capsule.

`render`, `play-capture`, `control-capture`, provider controls, and portable
profile authoring intentionally remain on the explicit v1 path. The
deterministic `render` command is not yet dispatched from
`ReplayExecutionPlan`: the exact remaining wiring point is
`vulkan::render_capsule`, whose resource allocation, descriptor creation, and
pipeline construction are still fixed to v1. Adding generic plan execution
requires a bounded backend adapter rather than silently interpreting v2 as v1.

## Build And Run

Compile the Hostess fullscreen vertex shader and build the runner:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File tools\Build-HostessProjectionReplay.ps1
```

Then render a provider-owned capsule:

```powershell
apps\hostess-projection-replay\target\release\hostess-projection-replay.exe `
  render `
  --capsule <provider-capsule.json> `
  --out <local-output-directory> `
  --adapter <optional-gpu-name-substring>
```

The output directory receives all five guide targets, each requested final
layer, and `replay-report.json`. The report records the adapter, exact shader
hashes, capsule hash, output hashes, alpha extrema, and accepted ABI sizes.

Compare two runs, including runs from different Vulkan drivers:

```powershell
apps\hostess-projection-replay\target\release\hostess-projection-replay.exe `
  compare `
  --baseline <baseline-replay-report.json> `
  --candidate <candidate-replay-report.json> `
  --out <comparison-report.json>
```

The default cross-driver gate allows at most eight levels of error in any
8-bit channel, a mean absolute error of `0.05`, and at most one percent of
pixels above a two-level channel error. All thresholds are explicit CLI
arguments and are written into
`rusty.hostess.projection_replay_comparison.v1`; exact hashes remain visible
but are not mistaken for the only valid visual comparison.

Synthetic source-isolation mode intentionally replaces effect-layer colors
with three independent generated region feeds. In that mode, compare the final
seam result and the separately exported guide targets; final diagnostic-layer
overrides are expected to share the synthetic region result. Disable the
synthetic compositor mode when validating raw/blur/strength/depth layers.

## Recorded Quest Camera Loop

`play-capture` consumes a complete
`rusty.quest.camera_replay_capture.v1` manifest plus its packed left-right
RGBA8 frames, splits each frame into provider inputs, renders every pair
through the selected capsule layer, writes a hash-bound
`rusty.hostess.projection_replay_sequence.v1` report, and loops the rendered
PNGs in a resizable desktop window:

```powershell
apps\hostess-projection-replay\target\release\hostess-projection-replay.exe `
  play-capture `
  --capture <capture.manifest.json> `
  --capsule <provider-capsule.json> `
  --out <local-output-directory> `
  --layer final `
  --loops 0 `
  --camera-only
```

Zero loops means play until the window closes; Escape closes it.
`--camera-only` is an explicit isolation mode: it selects the provider
shader's legacy camera path, disables stale synthetic zone diagnostics,
disables the video input, and disables projection-surface displacement. Omit
the switch when the capture should exercise the capsule's declared video,
zone, and displacement configuration. Add `--headless --loops 1` for a
noninteractive preparation and validation sweep.

For live effect work, open the same replay through the interactive control
surface:

```powershell
apps\hostess-projection-replay\target\release\hostess-projection-replay.exe `
  control-capture `
  --capture <capture.manifest.json> `
  --capsule <provider-capsule.json> `
  --control-transport <provider-control-transport.json> `
  --out <local-output-directory> `
  --layer final
```

The control surface provides frame playback and direct switching among the
capsule's declared output layers. The optional
`rusty.hostess.projection_replay_control_transport.v1` sidecar is limited to
64 KiB, binds the exact capsule v1 SHA-256, and declares an optional bounded
clock plus up to eight opaque phase controls. Labels, initial/default values,
ranges, rates, and projection-push, guide-push, or projection-zone-uniform
destinations come only from that sidecar. Without it, no provider phase UI is
shown and Hostess performs no implicit provider control writes. The UI also
exposes clock speed, RGB off/independent/linked mode,
per-channel phase/rate/strength/image-scale/coverage-scale, edge behavior, and
off/gentle/deep projection-surface displacement presets. A top-level
stereo/mono preview switch can enlarge either eye for tuning without changing
the packed-stereo render or its evidence output. Its bounded projection
controls cover coverage, projection and buffer footprint scale, an
enabled-by-default projection-effect edge guard with an explicit unguarded A/B
mode, stretch source/insets/curve, inner and outer blend-band width/curve, and
normal/region/sample-UV views.

The live path keeps its Vulkan device, shader pipelines, descriptors, guide
targets, output target, and readback buffer alive. Shader time is sampled
against wall time at an operator-selectable 30–120 Hz target (90 Hz by
default); camera/video textures are uploaded only when their replay frame
changes. This is intentionally separate from the deterministic `render`
command, which still rebuilds and exports every guide target for standalone
evidence.

PNG and capsule evidence is written asynchronously at most once per second, or
after a direct operator/frame change, so image encoding cannot set the visual
effect cadence. Live evidence reuses eight render slots rather than creating an
unbounded output history. Each write emits a hash-bound
`rusty.hostess.projection_replay_control_update.v2` receipt with target cadence,
observed preview cadence, and GPU round-trip time plus
`interactive/effective.capsule.json`; the latter can be passed directly to
`render` for command-line reproduction. Unknown output layers and unavailable
surface-displacement shaders fail closed instead of silently substituting a
different path.

## Replay Control States

The interactive window can save and load versioned
`rusty.hostess.projection_replay_control_state.v2` JSON files. Enter a state
name and choose **Save current** to capture the replay-layer selection,
projection scale, exact bounded capsule ABI control blocks, and desktop
preview state. The 24-float RGB, 16-float displacement, and 92-float zone
blocks remain effect-neutral and capsule-native; semantic interpretation is
owned by the provider or consumer adapter.
When a control transport is present, v2 stores descriptor-keyed selected
values bound to the transport identifier and capsule SHA-256. V1 remains a
read-only compatibility input: its former phase/rate pair is accepted only
when the matching sidecar declares exactly one phase control and the saved
finite rate has exactly the same `f32` bit pattern as the descriptor rate;
every other shape or rate fails closed.

Capsule admission reads at most 1 MiB once, deserializes from those bytes, and
computes the sidecar-binding SHA-256 from that same buffer. Sidecar validation
does not reopen or rehash the capsule path. Sidecar admission checks both
metadata and the actual post-read byte count against the 64 KiB limit before
JSON deserialization.

States use `.replay-control-state.json` and are written under
`<output-directory>/profiles` by default. Supply
`--profile-dir <directory>` to `control-capture` when several replay sessions
should share one local library. Existing Quest-owned `.profile.json` files
remain loadable through an explicit read-only legacy adapter. Hostess never
overwrites or emits that suffix or schema. Files are range-checked, reject
unknown fields, validate exact block lengths and finite values, are limited to
64 KiB, and never contain Android paths, hotload policy, camera frames, video,
shader payloads, or private effect formulas.

Loading performs one bounded read, rechecks the actual byte count, decodes
strict UTF-8, and parses JSON once before routing the schema from that same
immutable value. Applying a loaded state is transactional: the complete
candidate, descriptor/capsule identity, exact phase-key set, provider ranges,
and compatibility rate are validated on a clone before live controls change.

Saving a state does not contact a headset. Rusty Quest alone converts it:

```powershell
pwsh -NoProfile -File tools\Convert-HostessReplayControlState.ps1 `
  -InputPath <state.replay-control-state.json> `
  -OutPath <profile.profile.json>
```

The resulting Quest-owned profile can then be validated and installed through
Rusty Quest's existing serial-scoped helper.

Quest capture manifests and frame data are foreign, provider-owned inputs.
They and the generated PNG/report directories stay outside this repository.

## Confidence Boundary

This route provides high confidence for shader behavior, descriptor ABI,
guide scheduling, packed stereo UVs, region geometry, color-channel dynamics,
and output alpha on a desktop Vulkan driver. It does not prove Spatial SDK
composition order, physical stereo comfort, world/head anchoring, controller
input, Android external-YUV conversion, or Quest performance. Those remain
bounded target-device gates.

## Promotion

This starts as a Hostess application-local tool. Do not create a separate
repository merely to extract the renderer. Promote a neutral replay engine
only after a second independent provider consumes the public capsule contract
without private assumptions and the normal Morphospace extraction review
passes.
