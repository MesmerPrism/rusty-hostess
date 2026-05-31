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

    def test_rejects_old_coherence_squared_formula(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            stream = valid_coherence_stream()
            stream["coherence_ratio_squared"] = 12500.0
            evidence["streams"] = [stream]

            self.assertIn(
                "coherence squared ratio does not match coherence_ratio * coherence_ratio",
                validate(evidence, snapshot),
            )

    def test_rejects_underfilled_coherence_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            stream = valid_coherence_stream()
            stream["uniform_sample_count"] = 96
            evidence["streams"] = [stream]

            self.assertIn("coherence has fewer than 128 uniform samples", validate(evidence, snapshot))

    def test_accepts_selected_module_stream_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["capture"] = {"selected_module_ids": ["module.polar_h10.hrv_window"]}
            evidence["streams"] = [valid_hrv_window_stream()]

            self.assertEqual(validate(evidence, snapshot), [])

    def test_accepts_explicit_rmssd_gain_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            evidence["capture"] = {"selected_module_ids": ["module.polar_h10.rmssd_gain"]}
            evidence["streams"] = [valid_rmssd_gain_stream()]

            self.assertEqual(validate(evidence, snapshot), [])

    def test_rejects_same_run_rmssd_gain_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            snapshot = make_package(Path(temp))
            evidence = valid_evidence(snapshot)
            stream = valid_rmssd_gain_stream()
            stream["baseline_source"] = "same_run_initial_segment"
            evidence["streams"] = [stream]

            self.assertIn(
                "RMSSD gain baseline source must be an explicit package/runtime baseline",
                validate(evidence, snapshot),
            )


def make_package(root: Path) -> dict[str, object]:
    package = root / "packages" / "polar-h10" / "manifests"
    streams = package / "streams"
    streams.mkdir(parents=True)
    (package / "package.manifold.json").write_text('{"package_id":"package.polar_h10"}', encoding="utf-8")
    (streams / "hr-rr.json").write_text('{"stream_id":"stream.polar_h10.hr_rr"}', encoding="utf-8")
    (streams / "ecg.json").write_text('{"stream_id":"stream.polar_h10.ecg"}', encoding="utf-8")
    (streams / "acc.json").write_text('{"stream_id":"stream.polar_h10.acc"}', encoding="utf-8")
    (streams / "coherence.json").write_text('{"stream_id":"stream.polar_h10.coherence"}', encoding="utf-8")
    (streams / "hrv-window.json").write_text('{"stream_id":"stream.polar_h10.hrv_window"}', encoding="utf-8")
    (streams / "rmssd-gain.json").write_text('{"stream_id":"stream.polar_h10.rmssd_gain"}', encoding="utf-8")
    (streams / "breath-volume.json").write_text('{"stream_id":"stream.polar_h10.breath_volume"}', encoding="utf-8")
    (streams / "breath-dynamics.json").write_text('{"stream_id":"stream.polar_h10.breath_dynamics"}', encoding="utf-8")
    (streams / "hrvb-resonance-amplitude.json").write_text(
        '{"stream_id":"stream.polar_h10.hrvb_resonance_amplitude"}', encoding="utf-8"
    )
    modules = package / "modules"
    modules.mkdir()
    (modules / "provider.json").write_text('{"module_id":"module.polar_h10.provider"}', encoding="utf-8")
    (modules / "coherence.json").write_text('{"module_id":"module.polar_h10.coherence"}', encoding="utf-8")
    (modules / "hrv-window.json").write_text('{"module_id":"module.polar_h10.hrv_window"}', encoding="utf-8")
    (modules / "rmssd-gain.json").write_text('{"module_id":"module.polar_h10.rmssd_gain"}', encoding="utf-8")
    (modules / "breath-volume-from-acc.json").write_text(
        '{"module_id":"module.polar_h10.breath_volume_from_acc"}', encoding="utf-8"
    )
    (modules / "breath-dynamics.json").write_text('{"module_id":"module.polar_h10.breath_dynamics"}', encoding="utf-8")
    (modules / "hrvb-resonance-amplitude.json").write_text(
        '{"module_id":"module.polar_h10.hrvb_resonance_amplitude"}', encoding="utf-8"
    )
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
            "module_manifest_sha256": copy.deepcopy(snapshot["module_manifest_sha256"]),
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
        "remaining_power": 31.25,
        "coherence_ratio": 20.0,
        "coherence_ratio_squared": 400.0,
        "normalized_peak_power": 0.952381,
        "paper_ratio": 20.0,
        "normalized_score": 0.952381,
        "quality": "stable",
        "issue_code": None,
        "malformed_frame_count": 0,
    }


def valid_hrv_window_stream() -> dict[str, object]:
    return {
        "stream_id": "stream.polar_h10.hrv_window",
        "module_id": "module.polar_h10.hrv_window",
        "status": "pass",
        "input_stream_id": "stream.polar_h10.hr_rr",
        "method": "rr_window_v1",
        "heart_rate_event_count": 12,
        "input_rr_interval_count": 12,
        "accepted_count": 12,
        "rejected_count": 0,
        "successive_difference_count": 11,
        "mean_nn_ms": 1000.0,
        "mean_hr_bpm": 60.0,
        "sdnn_ms": 7.0,
        "rmssd_ms": 13.0,
        "ln_rmssd": 2.56,
        "pnn50": 0.0,
        "sd1_ms": 9.2,
        "quality": "stable",
        "issue_code": None,
        "malformed_frame_count": 0,
    }


def valid_rmssd_gain_stream() -> dict[str, object]:
    return {
        "stream_id": "stream.polar_h10.rmssd_gain",
        "module_id": "module.polar_h10.rmssd_gain",
        "status": "pass",
        "input_stream_id": "stream.polar_h10.hrv_window",
        "method": "log_rmssd_gain_v1",
        "baseline_source": "explicit_baseline",
        "baseline_window_count": 6,
        "current_window_count": 6,
        "baseline_rmssd_ms": 10.0,
        "current_rmssd_ms": 13.0,
        "rmssd_ratio": 1.3,
        "ln_rmssd_gain": 0.262364,
        "quality": "stable",
        "issue_code": None,
        "malformed_frame_count": 0,
    }


if __name__ == "__main__":
    unittest.main()
