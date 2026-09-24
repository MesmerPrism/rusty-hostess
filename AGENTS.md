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

Complete-product Windows Labs packaging is owned by
`packaging/windows-labs` and documented in
`docs/WINDOWS_LABS_DISTRIBUTION.md`. It packages Hostess-owned WPF and source
surfaces only; never fold MQDH/Casting or the separately released hotspot
provider into that product identity. Its versioned `runtime-policy.json` owns
the public signer and official CPython embeddable-runtime pins; GitHub secrets
contain only the private PFX and password. Bundled execution must use the exact
bundle-relative interpreter and never fall back to ambient `PATH` Python.

## Scope

- Minimal host apps and scripts that consume Manifold package manifests.
- Live package validation slots for desktop, mobile, and headset profiles.
- Evidence JSON, validators, and build scripts for clean host tests.
- Offline Vulkan projection replay from explicit provider-owned capsules and
  shader assets. Hostess may own generic descriptor recreation, image
  generation, readback, hashing, and evidence reports; it must not own or copy
  private shaders, product presets, camera captures, or effect formulas.
- Lattice evidence collection for tracked view sets, poses, spatial input
  roles, frame-state binding, calibration, validity, confidence, and runtime
  capabilities when a host run needs situated relation proof.
- Makepad dependencies only inside Hostess Makepad shell crates, and only for
  explicit legacy compatibility, migration, or regression work.

## Runtime Surface Default

For new operator and validation work, prefer WPF plus CLI/API-equivalent
Hostess routes. For Quest runtime work, prefer native OpenXR/Vulkan and Meta
Spatial SDK apps in `rusty-quest`; Hostess should install, launch, report, and
project evidence without becoming runtime authority.

Do not start new Makepad APK routes, Makepad profile work, or Makepad parity
work unless the user explicitly requests Makepad support. Existing Makepad
shells and evidence tools are legacy/migration surfaces.

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

## Sustainable Design Guardrails

- Treat monolithic file pressure as an ownership problem, not a line-count
  problem. Split only by durable authority, schema, route, validation, adapter,
  or test-family boundaries; preserve facades, schema IDs, serde fields,
  fixture outputs, CLI behavior, validation outcomes, and dependency boundaries.
- After a split, update the nearest distributed file map: this `AGENTS.md`,
  `README.md`, `docs/ARCHITECTURE.md`, fixture docs, validation docs, or the
  planning `agent-state\iteration-events.jsonl`.
- Keep `AGENTS.md`, README, and skill files as concise routing indexes. Move
  lane-specific recipes, device/build detail, compatibility ledgers, and long
  validation flows into named docs or runbooks.
- Keep legacy Rusty-XR names as explicit compatibility surfaces only. New
  schemas, routes, and types use the owning lane (`rusty.manifold.*`,
  `rusty.lattice.*`, `rusty.matter.*`, `rusty.optics.*`, `rusty.quest.*`, or
  repo-local names); do not introduce `rusty.morphospace.*` schemas or
  `Morphospace*` core types by default.
- Every WPF, native Quest panel, Spatial SDK tool surface, or explicitly
  requested legacy Makepad action must have a CLI-equivalent or local API route
  that automation can exercise with the same inputs, authority checks, and
  evidence artifacts. UI handlers collect parameters, invoke the route, and
  project structured evidence; they do not own hidden business logic or
  acceptance rules.
- Every operator report view must render a CLI/API report, descriptor, sidecar,
  receipt, or fixture output that automated tests can exercise before the UI
  feature is accepted for human operators.

## Validation

Use [docs/VALIDATION.md](docs/VALIDATION.md) to select checks for the touched
owner: focused Python, Rust, WPF, or packaging tests while iterating, then the
repo-local aggregate gate for a coherent Hostess handoff. Run
`tools/check_all.ps1` for the default WPF/CLI/Hostess gate; pass
`-IncludeMakepadLegacy` only for explicit Makepad compatibility or migration.
Follow the document's additional cross-repository and live-device prerequisites
when those surfaces are in scope. For live captures, write raw run artifacts
outside the repo and commit only generic code or sanitized sample fixtures.

## File Organization

For changes to an existing file family, read the matching ownership entry in
[the file organization map](docs/agent-instructions/file-organization.md). Preserve its
facades, authority boundaries, schema identities, and source-owned test families.

## Legacy Quest Makepad APK Route

Use this route only for explicit Makepad compatibility, migration, regression
repair, or historical evidence replay. Open
`docs\agent-instructions\quest-makepad-runbook.md` before Quest Makepad APK
builds, headset evidence collection, settings staging, GPU proof, ADF,
particle, or live/recorded hand validation work.

Keep these first-hop rules visible here:

- Build Hostess T Makepad Quest validation from `apps\hostess-t-makepad` with
  the Morphospace Makepad Quest variant and the active `makepad-morphospace`
  `cargo-makepad`.
- Do not add an app-local `resources\android\AndroidManifest.xml.template` just
  to remove camera permissions; use the packager camera-permission opt-out so
  `.MakepadAppXr` and OpenXR metadata stay intact.
- Stage effective settings and sibling data-plane artifacts with
  `tools\Stage-HostessMakepadSettings.ps1`; do not use
  `/sdcard/Android/data/...` as the app/ADB handoff path for these payloads.
- Treat settings writes as revision/scoped hashes transactions; the runbook
  keeps the full layered invalidation details.
- Hostess helper scripts must map Makepad, Quest, and PMB knobs through their
  owning master layer: effective-settings receipts for Makepad behavior, Quest
  runtime profiles for property transport, and Manifold/PMB commands for breath
  source selection and calibration. Do not treat direct property readback or
  launch arguments as accepted behavior without the app-side marker/receipt.
- Use `tools\check_makepad_quest_gpu_evidence.py` for Quest Makepad GPU proof
  evidence review when GPU/page-fault or compute-readiness claims are touched.
- Keep high-rate hands, meshes, SDF/ADF fields, particles, and GPU buffers out
  of settings/control JSON.
- Hostess remains the install/test/evidence shell. Matter, Optics,
  Quest-Makepad, Makepad, Lattice, and Manifold keep their runtime/schema
  authority according to their lane ownership.
