import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_makepad_quest_gpu_evidence import EvidenceThresholds, validate_summary


def valid_summary():
    return {
        "schema": "rusty.hostess.quest_live_hand_small_profile_summary.v1",
        "evidence_root": r"S:\Work\tmp\quest-makepad-live-hand-small-profile-example",
        "markers": {
            "proof_schedule": 1,
            "gpu_skinning_probe": 1,
            "gpu_skinning_mesh_residency": 1,
            "gpu_mesh_sdf_probe": 2,
            "gpu_residency": 8,
        },
        "cadence": {
            "app_frame_rate_hz": {"avg": 88.149},
            "xr_update_rate_hz": {"avg": 88.130},
            "xr_effective_frame_rate_hz": {"avg": 90.0, "min": 90.0},
            "xr_repaint_gpu_ms": {"avg": 0.330},
            "xr_update_dispatch_ms": {"avg": 0.255},
        },
        "vrapi_hostess_process": {
            "stale": {"count": 109, "max": 11.0, "avg": 2.56},
            "stale_90_plus_count": 0,
            "stale_30_plus_count": 0,
            "stale_nonzero_count": 77,
        },
        "proof_lines": [
            "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE status=ready",
            "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true",
            "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true",
            "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true denseSdfConstructedOnGpu=true fullSourceMeshConsumedByGpu=true programReused=false shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true",
            "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true denseSdfConstructedOnGpu=true fullSourceMeshConsumedByGpu=true programReused=true shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false",
        ],
    }


class MakepadQuestGpuEvidenceCheckTests(unittest.TestCase):
    def test_accepts_optimized_live_hand_gpu_evidence_shape(self):
        result = validate_summary(valid_summary())

        self.assertTrue(result.ok)
        self.assertEqual([], result.issues)
        self.assertEqual(0, result.summary["hostess_stale_90_plus_count"])
        self.assertEqual(77, result.summary["hostess_stale_nonzero_count"])
        self.assertEqual(2, result.summary["mesh_sdf_proof_line_count"])
        self.assertEqual(1, result.summary["mesh_sdf_program_setup_count"])
        self.assertEqual(1, result.summary["mesh_sdf_program_reuse_count"])

    def test_rejects_stale_heavy_debug_run(self):
        summary = valid_summary()
        summary["cadence"]["app_frame_rate_hz"]["avg"] = 5.0
        summary["cadence"]["xr_update_rate_hz"]["avg"] = 5.0
        summary["vrapi_hostess_process"]["stale"]["max"] = 91.0
        summary["vrapi_hostess_process"]["stale_90_plus_count"] = 12
        summary["vrapi_hostess_process"]["stale_30_plus_count"] = 12

        result = validate_summary(summary)

        self.assertFalse(result.ok)
        self.assertTrue(any("stale_90_plus_count" in issue for issue in result.issues))
        self.assertTrue(any("app_frame_rate_hz.avg" in issue for issue in result.issues))

    def test_rejects_sustained_low_stale_accumulation(self):
        summary = valid_summary()
        summary["vrapi_hostess_process"]["stale"]["avg"] = 3.44
        summary["vrapi_hostess_process"]["stale"]["count"] = 123
        summary["vrapi_hostess_process"]["stale_nonzero_count"] = 123

        result = validate_summary(summary)

        self.assertFalse(result.ok)
        self.assertTrue(any("stale.avg" in issue for issue in result.issues))
        self.assertTrue(any("stale_nonzero_count" in issue for issue in result.issues))
        self.assertTrue(any("stale_nonzero_ratio" in issue for issue in result.issues))

    def test_rejects_low_effective_frame_rate_samples(self):
        summary = valid_summary()
        summary["cadence"]["xr_effective_frame_rate_hz"]["avg"] = 87.25
        summary["cadence"]["xr_effective_frame_rate_hz"]["min"] = 22.5

        result = validate_summary(summary)

        self.assertFalse(result.ok)
        self.assertTrue(any("xr_effective_frame_rate_hz.avg" in issue for issue in result.issues))
        self.assertTrue(any("xr_effective_frame_rate_hz.min" in issue for issue in result.issues))

    def test_requires_async_gpu_readback_markers(self):
        summary = valid_summary()
        summary["proof_lines"][1] = (
            "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE "
            "readbackMatched=true queueWaitIdlePerformed=true recordedInputEquivalent=true"
        )

        result = validate_summary(summary, EvidenceThresholds(max_hostess_stale=30.0))

        self.assertFalse(result.ok)
        self.assertTrue(
            any("queueWaitIdlePerformed=false" in issue for issue in result.issues)
        )

    def test_can_require_mesh_sdf_program_reuse(self):
        summary = valid_summary()
        summary["proof_lines"] = [
            line
            for line in summary["proof_lines"]
            if "programReused=true" not in line
        ]

        result = validate_summary(
            summary,
            EvidenceThresholds(require_mesh_sdf_program_reuse=True),
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("programReused=true" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
