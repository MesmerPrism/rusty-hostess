from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools.check_live_capture_evidence import package_snapshot, validate


class LiveCaptureEvidenceValidatorTests(unittest.TestCase):
    def test_accepts_matching_pass_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)

            self.assertEqual(validate(evidence, snapshot), [])

    def test_rejects_top_level_failure_even_when_stream_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["status"] = "fail"

            self.assertIn("top-level status must be pass, got fail", validate(evidence, snapshot))

    def test_rejects_non_empty_evidence_errors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["errors"] = ["device not found"]

            errors = validate(evidence, snapshot)

            self.assertTrue(any(error.startswith("evidence errors must be empty") for error in errors))

    def test_rejects_unavailable_package_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["package"]["package_manifest_sha256"] = "unavailable"

            self.assertIn("package manifest hash must be a SHA-256 hex digest", validate(evidence, snapshot))

    def test_rejects_mismatched_package_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["package"]["package_manifest_sha256"] = "0" * 64

            self.assertIn("package manifest hash does not match packages root", validate(evidence, snapshot))

    def test_accepts_coherence_stream_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["streams"] = [valid_coherence_stream()]

            self.assertEqual(validate(evidence, snapshot), [])

    def test_rejects_underfilled_coherence_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            stream = valid_coherence_stream()
            stream["uniform_sample_count"] = 96
            evidence["streams"] = [stream]

            self.assertIn("coherence has fewer than 128 uniform samples", validate(evidence, snapshot))


def make_package(root: Path) -> dict[str, object]:
    package = root / "packages" / "polar-h10" / "manifests"
    streams = package / "streams"
    streams.mkdir(parents=True)
    (package / "package.manifold.json").write_text('{"package_id":"package.polar_h10"}', encoding="utf-8")
    (streams / "hr-rr.json").write_text('{"stream_id":"stream.polar_h10.hr_rr"}', encoding="utf-8")
    (streams / "ecg.json").write_text('{"stream_id":"stream.polar_h10.ecg"}', encoding="utf-8")
    (streams / "acc.json").write_text('{"stream_id":"stream.polar_h10.acc"}', encoding="utf-8")
    (streams / "coherence.json").write_text('{"stream_id":"stream.polar_h10.coherence"}', encoding="utf-8")
    return package_snapshot(root)


def valid_evidence(snapshot: dict[str, object]) -> dict[str, object]:
    return {
        "$schema": "rusty.manifold.live_capture_evidence.v1",
        "status": "pass",
        "host_profile": "desktop",
        "software": {"origin": "rusty-hostess"},
        "package": {
            "package_id": "package.polar_h10",
            "package_manifest_sha256": snapshot["package_manifest_sha256"],
            "stream_manifest_sha256": copy.deepcopy(snapshot["stream_manifest_sha256"]),
        },
        "streams": [
            {
                "stream_id": "stream.polar_h10.hr_rr",
                "status": "pass",
                "heart_rate_event_count": 1,
                "rr_interval_count": 1,
                "malformed_frame_count": 0,
            }
        ],
        "errors": [],
    }


def valid_coherence_stream() -> dict[str, object]:
    return {
        "stream_id": "stream.polar_h10.coherence",
        "status": "pass",
        "input_stream_id": "stream.polar_h10.hr_rr",
        "method": "spectral_ratio_v1",
        "heart_rate_event_count": 72,
        "input_rr_interval_count": 72,
        "uniform_sample_count": 128,
        "window_seconds": 64.0,
        "sample_rate_hz": 2.0,
        "peak_frequency_hz": 0.09375,
        "peak_band_power": 625.0,
        "total_band_power": 656.25,
        "paper_ratio": 20.0,
        "normalized_score": 0.952381,
        "quality": "stable",
        "issue_code": None,
        "malformed_frame_count": 0,
    }


if __name__ == "__main__":
    unittest.main()
