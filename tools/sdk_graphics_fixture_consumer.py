"""Short-lived deterministic byte consumer; deliberately not a SPIR-V renderer."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


def main():
    root, selection_path, output_path = map(Path, sys.argv[1:])
    selection = json.loads(selection_path.read_text())
    hashes = {}
    pixels = b""
    for name, expected in selection["hashes"].items():
        if Path(name).name != name or not name.endswith(".spv"):
            raise ValueError("flat_fixture_name_required")
        value = hashlib.sha256((root / name).read_bytes()).digest()
        hashes[name] = value.hex()
        if hashes[name] != expected:
            raise ValueError("uploaded_bytes_changed")
        pixels += value[:3]
    if len(hashes) != 12:
        raise ValueError("complete_fixed_batch_required")
    witness = b"P6\n12 1\n255\n" + pixels
    output_path.with_suffix(".ppm").write_bytes(witness)
    output_path.write_text(json.dumps({"batch_digest": selection["batch_digest"],
                                      "request_id": selection["request_id"],
                                      "effect_frame": selection["effect_frame"],
                                      "witness_sha256": hashlib.sha256(witness).hexdigest(),
                                      "scope": "neutral-file-consumer-no-gpu"}) + "\n")


if __name__ == "__main__":
    main()
