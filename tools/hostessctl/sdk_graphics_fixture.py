"""Neutral file consumer for the shader adapter, never GPU/device evidence.

Reload runs a real short-lived host child through the shared process observer.
The child reads the complete staged byte set and emits a tiny PPM witness. Its
delayed/unknown adoption controls exercise the same handler used by API callers.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from tools.hostessctl.process_observation import observe_process
from tools.hostessctl.sdk_graphics_batch import NAMES, digest


class FileConsumer:
    evidence_scope = "neutral-file-consumer-no-gpu"

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=False)
        self.remote = self.root / "overrides"
        self.remote.mkdir()
        self.actor = {"consumer": "neutral-file", "birth": "one-owned-instance",
                      "scene": "one-fixture-scene", "settings": "fixed"}
        self.frame = 0
        self.reloads = 0
        self.fail_upload = None
        self.unknown_reload = False
        self.delay_adoption = False
        self.stalled = False
        self.operations = {}
        self.hold_retirement = False

    def status(self):
        if not self.stalled:
            self.frame += 1
        return {"actor": dict(self.actor), "frame": self.frame, "eligible": True}

    def upload(self, request_id, name, data):
        if name not in NAMES:
            raise ValueError("fixed_names_only")
        (self.remote / name).write_bytes(data)
        self.operations[request_id] = not self.hold_retirement
        if self.fail_upload == name:
            raise OSError("unknown_after_original_write")

    def hashes(self, names):
        return {name: digest((self.remote / name).read_bytes())
                for name in names if (self.remote / name).is_file()}

    def reload(self, request_id, batch_digest):
        self.reloads += 1
        self.operations[request_id] = False
        lane = self.root / request_id
        lane.mkdir(exist_ok=False)
        selected = {"batch_digest": batch_digest, "request_id": request_id,
                    "effect_frame": self.frame + 1,
                    "hashes": self.hashes(NAMES), "actor": self.actor}
        (lane / "selection.json").write_text(json.dumps(selected))
        script = Path(__file__).resolve().parents[1] / "sdk_graphics_fixture_consumer.py"
        process = observe_process(
            [sys.executable, str(script), str(self.remote), str(lane / "selection.json"),
             str(lane / "output.json")], lane / "stdout.txt", lane / "stderr.txt")
        (lane / "process.json").write_text(json.dumps(process, indent=2) + "\n")
        if not process["observation_complete"] or process["exit_code"] != 0:
            raise RuntimeError("consumer_unknown")
        self.operations[request_id] = not self.hold_retirement
        if not self.delay_adoption:
            (self.root / "current.json").write_bytes((lane / "output.json").read_bytes())
            (self.root / "current.ppm").write_bytes((lane / "output.ppm").read_bytes())
        if self.unknown_reload:
            raise OSError("unknown_after_original_reload")

    def observe(self):
        path = self.root / "current.json"
        output = json.loads(path.read_text()) if path.exists() else {}
        if output and digest((self.root / "current.ppm").read_bytes()) != output["witness_sha256"]:
            raise ValueError("fixture_witness_changed")
        return {"actor": dict(self.actor), "frame": self.frame,
                "batch_digest": output.get("batch_digest"),
                "request_id": output.get("request_id"), "effect_frame": output.get("effect_frame"),
                "witness_sha256": output.get("witness_sha256"),
                "scope": self.evidence_scope}

    def retirement(self, request_id):
        return {"request_id": request_id, "retired": self.operations.get(request_id) is True}
