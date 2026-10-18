"""Create explicitly synthetic inputs for the neutral SDK adapter demonstration.

These header-sized byte strings are not validated executable SPIR-V and must
never be sent to a GPU. Production preparation uses the actual Quest owner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.hostessctl.sdk_graphics_batch import BATCH, CATALOG, NAMES, PROFILE, digest


def create_inputs(root: Path):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    baseline = root / "catalog" / "baseline"
    baseline.mkdir(parents=True)
    files = []
    for index, name in enumerate(NAMES):
        data = b"NEUTRAL-NOT-SPIRV" + index.to_bytes(4, "little")
        (baseline / name).write_bytes(data)
        files.append({"path": name, "bytes": len(data), "sha256": digest(data),
                      "abiSha256": digest(b"synthetic-160-byte-abi")})
    catalog = {"schema": CATALOG, "sdkVersion": "0.14.0", "materialUniformBytes": 160,
               "compileProfile": PROFILE, "tools": {"fixture": digest(b"no-tool")},
               "headers": {"fixture.glsl": digest(b"synthetic")},
               "batches": [{"name": "baseline", "vertexPaths": list(NAMES[:8]),
                            "fragmentPaths": list(NAMES[8:]), "files": files}]}
    catalog_path = root / "catalog" / "catalog.json"
    catalog_path.write_text(json.dumps(catalog) + "\n")
    for mode, folder in (("exact-baseline-revert", "baseline-batch"), ("fresh-source", "candidate-batch")):
        batch = root / folder
        batch.mkdir()
        rows, changed = [], []
        for item in files:
            name = item["path"]
            data = (baseline / name).read_bytes()
            if mode == "fresh-source" and name == NAMES[0]:
                data += b"changed-neutral-color"
                changed.append(name)
            (batch / name).write_bytes(data)
            rows.append({"relative": name, "bytes": len(data), "sha256": digest(data),
                         "abiSha256": item["abiSha256"]})
        manifest = {"schema": BATCH, "sdkVersion": "0.14.0", "status": "host-validated-not-uploaded",
                    "baselineCatalog": {"bytes": catalog_path.stat().st_size,
                                        "sha256": digest(catalog_path.read_bytes())},
                    "mode": mode, "compileProfile": PROFILE, "tools": catalog["tools"],
                    "headers": catalog["headers"], "files": rows, "changed": changed}
        (batch / "MANIFEST.json").write_text(json.dumps(manifest) + "\n")
    return root


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    print(create_inputs(parser.parse_args().out))
