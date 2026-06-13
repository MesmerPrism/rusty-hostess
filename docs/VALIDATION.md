# Validation

Run the repo-local check before committing changes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\check_all.ps1
```

The check covers the available local surface:

- Python syntax checks for Hostess control and evidence tools;
- Python unit tests under `tools\test_*.py`;
- desktop projected-motion-breath replay when the sibling package repo is
  available;
- `cargo check` for `apps\hostess-t-makepad`;
- Rust formatting and temporary cargo checks for Android JNI bridge crates when
  their inputs are present.

For fast CLI/evidence edits, run the Python path first:

```powershell
python -m py_compile tools\hostessctl\hostessctl.py tools\hostessctl\android_files.py tools\hostessctl\broker_transport.py tools\hostessctl\pmb_broker_bridge.py tools\hostessctl\pmb_evidence.py tools\hostessctl\recording_evidence.py tools\hostessctl\telemetry_render.py tools\telemetry_snapshot.py tools\telemetry_stream.py
python -m unittest discover -s tools -p "test_*.py"
```

For Makepad app-shell edits, run:

```powershell
cargo check --manifest-path apps\hostess-t-makepad\Cargo.toml
```

For projected-motion-breath desktop replay:

```powershell
python tools\hostessctl\hostessctl.py run-pmb-replay `
  --target desktop `
  --packages-root ..\rusty-manifold-packages `
  --out target\hostess-pmb-desktop-replay\pmb-desktop-replay.json
```

Quest, phone, ADB, BLE, APK, screenshot, and Perfetto checks are hardware or
platform validation. Use the documented Hostess commands and record evidence
bundles, but keep Agent Board reservations and headset leases scoped to the
actual shared-resource run.

Hostess validation should prove host packaging, launch, command bridging,
settings adoption, and evidence export. It must not redefine package semantics,
Matter CPU truth, Lattice relation truth, Manifold command authority, or
renderer backend policy.
