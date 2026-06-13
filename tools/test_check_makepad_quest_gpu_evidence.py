import unittest
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_makepad_quest_gpu_evidence import (
    EvidenceThresholds,
    resolve_summary_path,
    validate_summary,
)


def valid_summary():
    return {
        "schema": "rusty.hostess.quest_live_hand_small_profile_summary.v1",
        "evidence_root": r"S:\Work\tmp\quest-makepad-live-hand-small-profile-example",
        "markers": {
            "proof_schedule": 1,
            "gpu_skinning_probe": 1,
            "gpu_skinning_mesh_residency": 1,
            "gpu_mesh_sdf_probe": 2,
            "gpu_field_construction": 2,
            "gpu_field_sampling_probe": 2,
            "gpu_field_force_sampling_probe": 2,
            "gpu_field_particle_force_probe": 2,
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
            "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true denseSdfConstructedOnGpu=true fullSourceMeshConsumedByGpu=true sampleCount=8 programReused=false shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true sourceMeshBuffersResident=true sourceMeshBuffersReused=false derivedBuffersResident=true derivedBuffersReused=false",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false highRateJsonPayload=false sourceMeshBuffersResident=true sourceMeshBuffersReused=false derivedBuffersResident=true derivedBuffersReused=false measuredBy=RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE.elapsedMs",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeSamplingBoundaryReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true fieldSamplingKernel=true forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false highRateJsonPayload=false programReused=false shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeForceSamplingBoundaryReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true fieldSamplingKernel=true fieldForceSamplingKernel=true fieldParticleKernel=false runtimeParticleIntegration=false forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 componentCount=12 gpuComputeReady=false highRateJsonPayload=false programReused=false shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeParticleForceComparisonReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true particleSampleSource=matter-particle-snapshot matterParticleForceEquation=true fieldSamplingKernel=true fieldForceSamplingKernel=true fieldParticleKernel=true runtimeParticleIntegration=false forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 componentCount=12 gpuComputeReady=false highRateJsonPayload=false programReused=false shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true",
            "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true denseSdfConstructedOnGpu=true fullSourceMeshConsumedByGpu=true sampleCount=8 programReused=true shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false sourceMeshBuffersResident=true sourceMeshBuffersReused=true derivedBuffersResident=true derivedBuffersReused=true",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false highRateJsonPayload=false sourceMeshBuffersResident=true sourceMeshBuffersReused=true derivedBuffersResident=true derivedBuffersReused=true measuredBy=RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE.elapsedMs",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeSamplingBoundaryReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true fieldSamplingKernel=true forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false highRateJsonPayload=false programReused=true shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeForceSamplingBoundaryReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true fieldSamplingKernel=true fieldForceSamplingKernel=true fieldParticleKernel=false runtimeParticleIntegration=false forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 componentCount=12 gpuComputeReady=false highRateJsonPayload=false programReused=true shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false",
            "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE readbackMatched=true queueWaitIdlePerformed=false recordedInputEquivalent=true runtimeFieldBoundaryReady=true runtimeParticleForceComparisonReady=true residentFieldBufferSampled=true sourceFieldGenerationMatched=true particleSampleSource=matter-particle-snapshot matterParticleForceEquation=true fieldSamplingKernel=true fieldForceSamplingKernel=true fieldParticleKernel=true runtimeParticleIntegration=false forceAuthorityReady=false runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 componentCount=12 gpuComputeReady=false highRateJsonPayload=false programReused=true shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false",
        ],
    }


def add_valid_gpu_proof_epoch(summary):
    summary["markers"]["gpu_proof_epoch"] = 1
    summary["proof_lines"].append(
        "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH "
        "status=applied source=hotload proofCountersReset=true "
        "runtimeSettingsReloaded=false replayRuntimeRebuilt=false "
        "matterWorkerRestarted=false highRateJsonPayload=false"
    )
    return summary


def remove_force_stage_markers(summary):
    summary["markers"]["gpu_field_force_sampling_probe"] = 0
    summary["markers"]["gpu_field_particle_force_probe"] = 0
    summary["proof_lines"] = [
        line
        for line in summary["proof_lines"]
        if "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE" not in line
        and "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE" not in line
    ]
    return summary


class MakepadQuestGpuEvidenceCheckTests(unittest.TestCase):
    def test_resolves_canonical_summary_from_evidence_root(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "live-hand-small-profile-summary.json"
            summary_path.write_text(json.dumps(valid_summary()), encoding="utf-8")
            (root / "readiness-failure-summary.json").write_text(
                json.dumps(
                    {"schema": "rusty.hostess.quest_gpu_evidence_readiness_summary.v1"}
                ),
                encoding="utf-8",
            )

            self.assertEqual(summary_path, resolve_summary_path(root))

    def test_resolves_schema_matching_noncanonical_summary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary_path = root / "derived-buffer-proof-summary.json"
            summary_path.write_text(json.dumps(valid_summary()), encoding="utf-8")
            (root / "readiness-failure-summary.json").write_text(
                json.dumps(
                    {"schema": "rusty.hostess.quest_gpu_evidence_readiness_summary.v1"}
                ),
                encoding="utf-8",
            )

            self.assertEqual(summary_path, resolve_summary_path(root))

    def test_rejects_evidence_root_with_only_readiness_summary(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "readiness-failure-summary.json").write_text(
                json.dumps(
                    {"schema": "rusty.hostess.quest_gpu_evidence_readiness_summary.v1"}
                ),
                encoding="utf-8",
            )

            with self.assertRaises(FileNotFoundError) as raised:
                resolve_summary_path(root)

            self.assertIn("GPU proof summary", str(raised.exception))

    def test_rejects_multiple_schema_matching_summaries(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("first-proof-summary.json", "second-proof-summary.json"):
                (root / name).write_text(json.dumps(valid_summary()), encoding="utf-8")

            with self.assertRaises(FileExistsError) as raised:
                resolve_summary_path(root)

            self.assertIn("multiple Hostess GPU proof summaries", str(raised.exception))

    def test_accepts_optimized_live_hand_gpu_evidence_shape(self):
        result = validate_summary(valid_summary())

        self.assertTrue(result.ok)
        self.assertEqual([], result.issues)
        self.assertEqual(0, result.summary["hostess_stale_90_plus_count"])
        self.assertEqual(77, result.summary["hostess_stale_nonzero_count"])
        self.assertEqual(2, result.summary["mesh_sdf_proof_line_count"])
        self.assertEqual(1, result.summary["mesh_sdf_program_setup_count"])
        self.assertEqual(1, result.summary["mesh_sdf_program_reuse_count"])
        self.assertEqual(2, result.summary["mesh_sdf_source_buffer_resident_count"])
        self.assertEqual(1, result.summary["mesh_sdf_source_buffer_reuse_count"])
        self.assertEqual(2, result.summary["mesh_sdf_derived_buffer_resident_count"])
        self.assertEqual(1, result.summary["mesh_sdf_derived_buffer_reuse_count"])
        self.assertEqual(8, result.summary["mesh_sdf_max_sample_count"])
        self.assertEqual(2, result.summary["field_construction_line_count"])
        self.assertEqual(2, result.summary["field_construction_ready_count"])
        self.assertEqual(
            2, result.summary["field_construction_force_authority_false_count"]
        )
        self.assertEqual(2, result.summary["field_sampling_line_count"])
        self.assertEqual(2, result.summary["field_sampling_ready_count"])
        self.assertEqual(2, result.summary["field_sampling_resident_count"])
        self.assertEqual(2, result.summary["field_force_sampling_line_count"])
        self.assertEqual(2, result.summary["field_force_sampling_ready_count"])
        self.assertEqual(2, result.summary["field_force_sampling_resident_count"])
        self.assertEqual(
            2,
            result.summary["field_force_sampling_runtime_particle_false_count"],
        )
        self.assertEqual(2, result.summary["field_particle_force_line_count"])
        self.assertEqual(2, result.summary["field_particle_force_ready_count"])
        self.assertEqual(2, result.summary["field_particle_force_resident_count"])
        self.assertEqual(2, result.summary["field_particle_force_kernel_count"])
        self.assertEqual(
            2,
            result.summary["field_particle_force_runtime_particle_false_count"],
        )
        self.assertEqual(0, result.summary["gpu_proof_epoch_line_count"])

    def test_accepts_mesh_sdf_only_stage_without_force_proofs(self):
        summary = remove_force_stage_markers(add_valid_gpu_proof_epoch(valid_summary()))

        result = validate_summary(
            summary,
            EvidenceThresholds(
                require_mesh_sdf_program_reuse=True,
                require_mesh_sdf_source_buffer_reuse=True,
                require_mesh_sdf_derived_buffer_reuse=True,
                require_mesh_sdf_min_sample_count=8,
                require_gpu_proof_epoch=True,
            ),
        )

        self.assertTrue(result.ok)
        self.assertEqual([], result.issues)
        self.assertEqual(0, result.summary["field_force_sampling_line_count"])
        self.assertEqual(0, result.summary["field_particle_force_line_count"])
        self.assertEqual(
            0,
            result.summary["stage_marker_counts"]["gpu_field_force_sampling_probe"],
        )

    def test_can_require_later_force_stage_markers(self):
        summary = remove_force_stage_markers(valid_summary())

        result = validate_summary(
            summary,
            EvidenceThresholds(
                require_gpu_field_force_sampling=True,
                require_gpu_field_particle_force=True,
            ),
        )

        self.assertFalse(result.ok)
        self.assertTrue(
            any("GPU_FIELD_FORCE_SAMPLING_PROBE" in issue for issue in result.issues)
        )
        self.assertTrue(
            any("GPU_FIELD_PARTICLE_FORCE_PROBE" in issue for issue in result.issues)
        )

    def test_can_require_gpu_proof_epoch(self):
        summary = add_valid_gpu_proof_epoch(valid_summary())

        result = validate_summary(
            summary,
            EvidenceThresholds(require_gpu_proof_epoch=True),
        )

        self.assertTrue(result.ok)
        self.assertEqual([], result.issues)
        self.assertEqual(1, result.summary["gpu_proof_epoch_line_count"])
        self.assertEqual(1, result.summary["gpu_proof_epoch_reset_count"])
        self.assertEqual(
            1,
            result.summary["gpu_proof_epoch_no_runtime_reload_count"],
        )
        self.assertEqual(
            1,
            result.summary["optional_marker_counts"]["gpu_proof_epoch"],
        )

    def test_rejects_missing_required_gpu_proof_epoch(self):
        result = validate_summary(
            valid_summary(),
            EvidenceThresholds(require_gpu_proof_epoch=True),
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("GPU_PROOF_EPOCH" in issue for issue in result.issues))

    def test_rejects_gpu_proof_epoch_runtime_rebuild(self):
        summary = add_valid_gpu_proof_epoch(valid_summary())
        summary["proof_lines"][-1] = summary["proof_lines"][-1].replace(
            "replayRuntimeRebuilt=false",
            "replayRuntimeRebuilt=true",
        )

        result = validate_summary(
            summary,
            EvidenceThresholds(require_gpu_proof_epoch=True),
        )

        self.assertFalse(result.ok)
        self.assertTrue(
            any("replayRuntimeRebuilt=false" in issue for issue in result.issues)
        )

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

    def test_can_require_mesh_sdf_source_buffer_reuse(self):
        summary = valid_summary()
        summary["proof_lines"] = [
            line.replace("sourceMeshBuffersReused=true", "sourceMeshBuffersReused=false")
            for line in summary["proof_lines"]
        ]

        result = validate_summary(
            summary,
            EvidenceThresholds(require_mesh_sdf_source_buffer_reuse=True),
        )

        self.assertFalse(result.ok)
        self.assertTrue(
            any("sourceMeshBuffersReused=true" in issue for issue in result.issues)
        )

    def test_can_require_mesh_sdf_sample_count(self):
        summary = valid_summary()
        summary["proof_lines"] = [
            line.replace("sampleCount=8", "sampleCount=4")
            for line in summary["proof_lines"]
        ]

        result = validate_summary(
            summary,
            EvidenceThresholds(require_mesh_sdf_min_sample_count=8),
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("sampleCount" in issue for issue in result.issues))

    def test_can_require_mesh_sdf_derived_buffer_reuse(self):
        summary = valid_summary()
        summary["proof_lines"] = [
            line.replace("derivedBuffersReused=true", "derivedBuffersReused=false")
            for line in summary["proof_lines"]
        ]

        result = validate_summary(
            summary,
            EvidenceThresholds(require_mesh_sdf_derived_buffer_reuse=True),
        )

        self.assertFalse(result.ok)
        self.assertTrue(
            any("derivedBuffersReused=true" in issue for issue in result.issues)
        )

    def test_rejects_field_construction_force_authority_claim(self):
        summary = valid_summary()
        summary["proof_lines"] = [
            line.replace("forceAuthorityReady=false", "forceAuthorityReady=true")
            for line in summary["proof_lines"]
        ]

        result = validate_summary(summary)

        self.assertFalse(result.ok)
        self.assertTrue(
            any("forceAuthorityReady=false" in issue for issue in result.issues)
        )


if __name__ == "__main__":
    unittest.main()
