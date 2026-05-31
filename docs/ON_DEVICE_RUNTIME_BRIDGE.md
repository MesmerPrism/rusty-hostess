# On-Device Runtime Bridge

This document defines the Hostess T bridge from Android-class app shells to the
package Rust runtime. The first bridge is implemented as a JSON JNI ABI for the
Polar package runtime, with desktop parity, synthetic on-device replay, and live
phone/headset evidence.

## Authority Boundary

Hostess owns installation, launch, permissions, BLE acquisition, evidence file
storage, and command routing.

The package Rust core owns processor formulas, graph dependency resolution,
runtime input parsing, graph execution reports, and module stream outputs.

Manifold remains platform-neutral. The on-device bridge must not add Android or
headset dependencies to Manifold core contracts.

## JNI Shape

The native library exposes a small static ABI around JSON documents:

- `polar_h10_run_graph(graph_json, input_json, selected_modules_json) -> json`

The Java layer wraps this ABI as:

- `PolarRuntime.runGraph(input: JSONObject, selectedModules: List<String>): JSONObject`

Decoded HR/RR and ACC buffers are passed into Rust using the same runtime input
shape that desktop live capture writes. Protocol decode remains in the app shell
for this slice. Moving decode into Rust is a later optimization only if parity
tests justify it.

## On-Device Modules

The app shell should keep four narrow modules:

- acquisition: BLE permissions, scan/connect, notifications, PMD control
- buffer bridge: converts decoded HR/RR and ACC frames into runtime input JSON
- runtime bridge: calls the native Rust graph runner through `PolarRuntime`
- evidence writer: merges direct acquisition streams, graph report streams, and
  validation metadata into Hostess evidence

Processor modules are not Java/Kotlin modules. They are selected package modules
executed by the Rust graph runner.

## Evidence Rules

On-device evidence should match the desktop live shape:

- direct HR/RR, ECG, and ACC rows remain acquisition evidence
- selected processor rows are copied from the Rust graph report
- `capture.runtime_path` is `rust.polar_h10_core.v1`
- `capture.runtime_input` names the runtime-input artifact
- `capture.graph_execution_report` names the graph report artifact
- `commands` includes a `run_graph_live_capture` acknowledgement or rejection
- `errors` includes graph issues only when the graph status is not `pass`

## Validation Ladder

1. Rust unit tests and package goldens pass on desktop.
2. Desktop live capture writes runtime input and passes graph-resolved evidence
   validation.
3. Replaying captured runtime input through `hostessctl run-replay` produces
   graph-resolved selected module streams.
4. The Android-class native library builds for the app ABI and is packaged in
   the install APK.
5. A synthetic on-device replay intent runs the Rust graph with packaged fixture
   input and writes validated evidence.
6. Phone live capture uses the same bridge.
7. Headset live capture uses the same bridge.

Steps 1-7 have passing evidence for the first Polar selected-module set. Direct
ECG capture remains acquisition evidence rather than graph evidence because no
current processor module consumes ECG.
