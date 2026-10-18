"""Host adapter for the existing Quest SDK0.14 graphics preparer.

Quest owns compilation/reflection. Hostess binds that exact owner invocation
and validates its immutable outputs; a manifest alone is no device admission.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

from tools.hostessctl.process_observation import ObservationFailure, ObservationInterrupted, observe_process

CATALOG = "rusty.quest.sdk_hotload.catalog.v1"
BATCH = "rusty.quest.sdk_hotload.fresh_batch.v1"
NAMES = tuple("workload.vert" + s + ".spv" for s in
              ("", ".mv", ".2uv", ".2uv.mv", ".tangent", ".tangent.mv", ".skin", ".skin.mv")) + tuple(
    "workload.frag" + s + ".spv" for s in ("", ".mv", ".tangent", ".tangent.mv"))
PROFILE = {"schema": "rusty.quest.sdk014.compile_profile.v1",
           "optimization": "performance", "optimizationFlag": "-O",
           "targetEnvironment": "default-vulkan1.0", "hsrFlags": ["GRAPHICS_HSR"]}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file(path: Path, maximum: int = 4 * 1024 * 1024) -> bytes:
    path = Path(path).absolute()
    if any(p.is_symlink() or p.is_junction() for p in (path, *path.parents)):
        raise ValueError("reparse_path_refused")
    if not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError("bounded_regular_file_required")
    data = path.read_bytes()
    if len(data) > maximum:
        raise ValueError("file_grew_beyond_bound")
    return data


def read_json(path: Path) -> dict:
    return decode_json(read_file(path))


def decode_json(data: bytes) -> dict:
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("duplicate_json_key")
            result[k] = v
        return result
    value = json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique)
    if type(value) is not dict:
        raise ValueError("json_object_required")
    return value


def file_rows(rows: list, root: Path, name_key: str, *, read=read_file) -> dict:
    if type(rows) is not list or len(rows) != len(NAMES):
        raise ValueError("complete_twelve_file_batch_required")
    result = {}
    for row in rows:
        name = row[name_key]
        if name not in NAMES or name in result:
            raise ValueError("unique_fixed_shader_names_required")
        data = read(root / name, 1048576)
        if (type(row["bytes"]) is not int or row["bytes"] != len(data)
                or len(data) < 20 or digest(data) != row["sha256"]
                or not isinstance(row["abiSha256"], str)
                or len(row["abiSha256"]) != 64
                or any(c not in "0123456789abcdef" for c in row["abiSha256"])):
            raise ValueError("shader_bytes_or_abi_identity_changed")
        result[name] = {"bytes": data, "sha256": row["sha256"], "abi": row["abiSha256"]}
    return result


def load_baseline(catalog_path: Path, *, read=read_file, document=read_json) -> tuple[dict, dict]:
    catalog = document(catalog_path)
    if (catalog.get("schema") != CATALOG or catalog.get("sdkVersion") != "0.14.0"
            or catalog.get("compileProfile") != PROFILE
            or type(catalog.get("materialUniformBytes")) is not int
            or catalog["materialUniformBytes"] != 160):
        raise ValueError("optimized_sdk014_160_byte_catalog_required")
    matches = [b for b in catalog["batches"] if b["name"] == "baseline"]
    if len(matches) != 1:
        raise ValueError("one_baseline_required")
    base = matches[0]
    if base["vertexPaths"] + base["fragmentPaths"] != list(NAMES):
        raise ValueError("baseline_variant_order_changed")
    return catalog, file_rows(base["files"], catalog_path.parent / "baseline", "path", read=read)


def load_batch(batch_path: Path, catalog_path: Path, *, read=read_file, document=read_json) -> dict:
    catalog, baseline = load_baseline(catalog_path, read=read, document=document)
    manifest = document(batch_path / "MANIFEST.json")
    pin = manifest.get("baselineCatalog", {})
    if (manifest.get("schema") != BATCH or manifest.get("sdkVersion") != "0.14.0"
            or manifest.get("status") != "host-validated-not-uploaded"
            or manifest.get("mode") not in ("fresh-source", "exact-baseline-revert")
            or pin.get("sha256") != digest(read(catalog_path))
            or pin.get("bytes") != len(read(catalog_path))):
        raise ValueError("batch_baseline_binding_invalid")
    for key in ("compileProfile", "tools", "headers"):
        if manifest.get(key) != catalog.get(key):
            raise ValueError("batch_compiler_profile_changed")
    files = file_rows(manifest["files"], batch_path, "relative", read=read)
    for name in NAMES:
        if files[name]["abi"] != baseline[name]["abi"]:
            raise ValueError("batch_abi_changed")
    changed = [name for name in NAMES if files[name]["sha256"] != baseline[name]["sha256"]]
    if (manifest.get("changed") != changed or
            (manifest["mode"] == "exact-baseline-revert" and changed) or
            (manifest["mode"] == "fresh-source" and not changed)):
        raise ValueError("batch_mode_or_changed_inventory_invalid")
    return {"digest": digest(read(batch_path / "MANIFEST.json")),
            "files": files, "mode": manifest["mode"], "catalog": pin["sha256"]}


def prepare(args) -> dict:
    """Invoke two explicitly pinned owner scripts through the shared observer."""
    root = Path(args.owner_app)
    scripts = [(root / "Prepare-FreshSdkHotload.py", args.preparer_sha256),
               (root / "Prepare-SdkHotloadCatalog.py", args.reflector_sha256)]

    def admit():
        for path, sha in scripts:
            if digest(read_file(path)) != sha:
                raise ValueError("owner_source_pin_changed")
        load_baseline(Path(args.baseline_catalog))

    admit()
    evidence = Path(args.process_evidence)
    evidence.mkdir(parents=True, exist_ok=False)
    argv = [sys.executable, str(scripts[0][0].absolute())]
    for name in ("baseline_catalog", "output", "glslc", "spirv_val", "spirv_dis", "headers", "shader_config"):
        value = args.batch_output if name == "output" else getattr(args, name)
        argv += ["--" + name.replace("_", "-"), str(Path(value).absolute())]
    argv += ["--require-sdk-primary"]
    argv += (["--baseline-revert"] if args.baseline_revert else
             ["--source-directory", str(Path(args.source_directory).absolute())])
    # ObservationFailure/Interrupted retain their exact receipt/child; no replay,
    # timeout kill, or claim of cleanup by this adapter.
    try:
        process = observe_process(argv, evidence / "stdout.txt", evidence / "stderr.txt",
                                  admit=admit, source_paths=tuple(p for p, _ in scripts))
    except (ObservationFailure, ObservationInterrupted) as error:
        (evidence / "process.json").write_text(json.dumps(error.receipt, indent=2) + "\n")
        raise  # API caller retains the exact owned child on the exception.
    (evidence / "process.json").write_text(json.dumps(process, indent=2) + "\n")
    if (not process["observation_complete"] or process["exit_code"] != 0
            or process["source_changed"]):
        raise ValueError("owner_preparation_failed_or_unknown")
    admit()
    batch = load_batch(Path(args.batch_output), Path(args.baseline_catalog))
    return {"schema": "rusty.hostess.sdk_graphics.preparation.v1", "status": "host-prepared",
            "owner_scripts": [{"path": str(p), "sha256": h} for p, h in scripts],
            "batch_manifest_sha256": batch["digest"], "process_evidence": str(evidence),
            "device_admission": False, "gpu_completion": False, "pixels_proven": False}
