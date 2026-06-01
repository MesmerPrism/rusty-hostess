# Architecture

Rusty Hostess T is an install and test shell for Manifold package development.
It is not a new authority layer. It consumes Manifold and package contracts,
executes named validation slots on target hosts, and exports evidence bundles.

## Authority

Manifold owns command descriptors, leases, package/runtime state, stream
registries, audit records, and scorecards.

Hostess T owns platform packaging, permission probes, launch/install routes,
small app UI surfaces, command bridging, and evidence export.

## Current Slice

The first implementation supports one live package slot:

- `live-smoke`: bounded direct-stream capture for the Polar H10 package and
  opt-in processor-module validation for selected package modules.

The Android app embeds selected package manifests as assets, opens the platform
sensor route itself, and writes evidence that includes the package manifest
hash. The desktop script follows the same evidence shape. Both desktop and
Android captures are accepted only after the shared evidence validator compares
the reported manifest hash against the supplied package root.

The intended GUI surface is Makepad. `apps/hostess-t-makepad` seeds from
bounded `TelemetrySnapshot` checkpoint JSON when useful, then watches
append-only `TelemetryStreamEvent` JSONL and maintains rolling buffers per
datastream. It is the first scalable Rusty GUI example for Hostess T. It
observes run state and can request commands only through the same
Hostess/Manifold command routes as `hostessctl`.

The Android-class app shell includes a compact native Canvas telemetry view for
phone and headset profiles, but that view is fallback/debug-only platform
evidence plumbing. Android Java owns Activity lifecycle, BLE acquisition,
permission UX, ADB intent/file command bridging, app-private evidence storage,
and JNI calls into the Rust runtime. It does not own reusable panel layout,
processor formulas, package state, graph execution, or module authority.

The desktop CLI can render equivalent evidence pages from completed run
artifacts. Rendered PNGs must include dimensions, nonblank content evidence,
and a JSON sidecar before they are accepted as visual evidence.

Processor modules are selected by module id. For deterministic replay, Hostess
delegates formula execution and dependency resolution to the package Rust
processor core, then validates the graph-resolved evidence. Desktop live module
capture now keeps acquisition in Hostess, writes captured HR/RR and ACC buffers
into the package runtime input shape, and delegates selected module outputs to
the same Rust graph runner.

The current selected modules cover HRV window, RMSSD gain, coherence, breath
volume from ACC, breath dynamics, and HRVB resonance amplitude. Coherence is
computed at runtime from a live HR/RR capture by resampling a 64-second RR
window to 128 uniform samples and producing the package-defined spectral ratio
plus normalized score fields.

The phone/headset path uses a JNI bridge from the app shell to the same package
runtime ABI. The bridge is recorded in `docs/ON_DEVICE_RUNTIME_BRIDGE.md`.
Java/Kotlin owns acquisition and display only; selected processor outputs come
from the Rust graph report.

The telemetry panel boundary is recorded in `docs/TELEMETRY_GUI.md`.

After a raw capture validates, `hostessctl` writes a
`rusty.manifold.host_run.run_evidence.v1` wrapper with a scorecard so the live
run is tied back to the Manifold Hostess contract spine.

## Non-Scope

This repo does not define package semantics, dynamic loading, product UI, or a
long-lived runtime daemon.
