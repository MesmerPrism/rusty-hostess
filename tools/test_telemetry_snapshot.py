from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.telemetry_snapshot import build_snapshot


class TelemetrySnapshotTests(unittest.TestCase):
    def test_builds_bounded_snapshot_from_evidence_and_graph_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence_path = root / "capture.json"
            graph_path = root / "capture.graph-execution-report.json"
            runtime_path = root / "capture.runtime-input.json"
            evidence_path.write_text(json.dumps(evidence()), encoding="utf-8")
            graph_path.write_text(json.dumps(graph_report()), encoding="utf-8")
            runtime_path.write_text(json.dumps(runtime_input()), encoding="utf-8")

            snapshot = build_snapshot(evidence_path)

            self.assertEqual(snapshot["$schema"], "rusty.hostess.telemetry.snapshot.v1")
            self.assertEqual(snapshot["run"]["host_profile"], "desktop")
            self.assertEqual(snapshot["run"]["graph_status"], "pass")
            self.assertEqual(snapshot["raw_streams"][0]["stream_id"], "stream.polar_h10.hr_rr")
            self.assertEqual(snapshot["raw_streams"][0]["preview"], [1000.0, 1010.0])
            self.assertEqual(snapshot["module_outputs"][0]["metrics"]["normalized_score"], 0.95)
            self.assertEqual(snapshot["time_series"][0]["series_id"], "series.polar_h10.hr_bpm")
            self.assertEqual(snapshot["time_series"][0]["values"], [60.0, 59.4059])
            self.assertEqual(snapshot["time_series"][1]["series_id"], "series.polar_h10.rr_interval_ms")
            self.assertLessEqual(len(snapshot["raw_streams"][0]["preview"]), 24)
            self.assertLessEqual(len(snapshot["time_series"][1]["values"]), 256)


def evidence() -> dict[str, object]:
    return {
        "$schema": "rusty.manifold.live_capture_evidence.v1",
        "status": "pass",
        "host_profile": "desktop",
        "capture": {
            "mode": "module",
            "selected_module_ids": ["module.polar_h10.coherence"],
            "runtime_path": "rust.polar_h10_core.v1",
            "runtime_input": "latest.runtime-input.json",
            "graph_execution_report": "latest.graph-execution-report.json",
        },
        "streams": [
            {
                "stream_id": "stream.polar_h10.hr_rr",
                "status": "pass",
                "heart_rate_event_count": 2,
                "rr_interval_count": 2,
                "malformed_frame_count": 0,
            }
        ],
        "errors": [],
    }


def graph_report() -> dict[str, object]:
    return {
        "status": "pass",
        "graph_id": "graph.polar_h10_processing",
        "streams": [
            {
                "stream_id": "stream.polar_h10.coherence",
                "module_id": "module.polar_h10.coherence",
                "status": "pass",
                "input_stream_id": "stream.polar_h10.hr_rr",
                "normalized_score": 0.95,
                "quality": "stable",
                "issue_code": None,
            }
        ],
        "issues": [],
    }


def runtime_input() -> dict[str, object]:
    return {
        "hr_rr": {
            "heart_rate_event_count": 2,
            "rr_intervals_ms": [1000.0, 1010.0],
        }
    }


if __name__ == "__main__":
    unittest.main()
