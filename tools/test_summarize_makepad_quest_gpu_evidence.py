import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from summarize_makepad_quest_gpu_evidence import (
    strict_log_scan,
    summarize_evidence,
)


def log_line(pid, tag, message, tid=None, level="I"):
    return (
        f"06-12 21:06:00.000 {pid:5d} {tid or pid + 1:5d} {level} "
        f"{tag}: {message}"
    )


def compact_log_line(pid, tag, message, level="I"):
    return f"06-12 21:06:00.000 {level}/{tag}({pid:5d}): {message}"


def write_evidence(root, log_lines, power_after="", mounted_after="", window_after=""):
    root.mkdir(parents=True, exist_ok=True)
    (root / "logcat.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    (root / "metadata.json").write_text(
        json.dumps(
            {
                "schema": "rusty.hostess.quest_recorded_hand_test_metadata.v1",
                "package": "io.github.mesmerprism.rustyhostess.makepad",
                "source_mode": "recorded-hand-replay",
            }
        ),
        encoding="utf-8",
    )
    if power_after:
        (root / "power-after.txt").write_text(power_after, encoding="utf-8")
    if mounted_after:
        (root / "sys-hmt-mounted-after.txt").write_text(
            mounted_after, encoding="utf-8"
        )
    if window_after:
        (root / "window-after.txt").write_text(window_after, encoding="utf-8")


class MakepadQuestGpuEvidenceSummaryTests(unittest.TestCase):
    def test_summarizes_proof_and_filters_vrapi_to_hostess_pid(self):
        proof_lines = [
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_SCHEDULE "
                "status=ready selectedMode=recorded-hand-replay "
                "recordedHandReplaySelected=true liveEquivalentHandInputSelected=true "
                "blockingGpuDiagnostics=false highRateJsonPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH "
                "status=applied source=hotload proofCountersReset=true "
                "runtimeSettingsReloaded=false replayRuntimeRebuilt=false "
                "matterWorkerRestarted=false highRateJsonPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true kgslFaultsBeforeMarker=unavailable",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_MESH_RESIDENCY "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true denseSdfConstructedOnGpu=true "
                "fullSourceMeshConsumedByGpu=true sampleCount=8 programReused=false "
                "shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true "
                "sourceMeshBuffersResident=true sourceMeshBuffersReused=false "
                "sourceVertexBufferBytes=413440 sourceTriangleBufferBytes=37024 "
                "derivedBuffersResident=true derivedBuffersReused=false "
                "skinnedPositionBufferBytes=21760 sdfDistanceBufferBytes=6292 "
                "kgslFaultsAfterMarker=unavailable",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false "
                "highRateJsonPayload=false sourceMeshBuffersResident=true "
                "sourceMeshBuffersReused=false derivedBuffersResident=true "
                "derivedBuffersReused=false "
                "measuredBy=RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE.elapsedMs",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeSamplingBoundaryReady=true residentFieldBufferSampled=true "
                "sourceFieldGenerationMatched=true fieldSamplingKernel=true "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false "
                "highRateJsonPayload=false programReused=false "
                "shaderCompiledThisSubmit=true pipelineCreatedThisSubmit=true",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeForceSamplingBoundaryReady=true residentFieldBufferSampled=true "
                "sourceFieldGenerationMatched=true fieldSamplingKernel=true "
                "fieldForceSamplingKernel=true fieldParticleKernel=false "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 "
                "componentCount=12 gpuComputeReady=false highRateJsonPayload=false "
                "programReused=false shaderCompiledThisSubmit=true "
                "pipelineCreatedThisSubmit=true",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeParticleForceComparisonReady=true "
                "residentFieldBufferSampled=true sourceFieldGenerationMatched=true "
                "particleSampleSource=matter-particle-snapshot "
                "matterParticleForceEquation=true fieldSamplingKernel=true "
                "fieldForceSamplingKernel=true fieldParticleKernel=true "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 "
                "componentCount=12 gpuComputeReady=false highRateJsonPayload=false "
                "programReused=false shaderCompiledThisSubmit=true "
                "pipelineCreatedThisSubmit=true",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "candidateSelected=false candidatePromoted=false "
                "activeForceAuthorityChanged=false runtimeParticleIntegration=false "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "gpuComputeReady=false highRateJsonPayload=false "
                "settingsControlPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "forceAuthoritySlotCount=1 activeForceAuthorityCount=1 "
                "profileGate=explicit-profile-required profileGateSatisfied=false "
                "runtimeSelectionPermitted=false gpuForceAuthorityProfileEnabled=false "
                "candidateEligible=true candidateSelected=false candidatePromoted=false "
                "activeForceAuthorityChanged=false matterCpuFallbackReady=true "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false gpuComputeReady=false "
                "highRateJsonPayload=false settingsControlPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "forceAuthoritySlotCount=1 activeForceAuthorityCount=1 "
                "activeForceAuthorityKind=matter-cpu "
                "activeForceAuthoritySource=matter-runtime-profile "
                "activeMatterForceAuthority=mesh-distance "
                "matterCpuOracleForceAuthority=mesh-distance "
                "activeForceAuthorityPreserved=matter-cpu-runtime "
                "profileGate=explicit-profile-required profileGateSatisfied=false "
                "runtimeSelectionPermitted=false gpuForceAuthorityProfileEnabled=false "
                "candidateEligible=true candidateSelected=false candidatePromoted=false "
                "observedResidentProofs=1 requiredResidentProofs=4 boundedProofOnly=true "
                "steadyStateResidencyReady=false freshnessReady=false cadenceReady=false "
                "expandedOracleComparisonReady=false liveRecordedProviderAbReady=false "
                "fallbackForceAuthority=mesh-distance "
                "fallbackReason=profile-prefers-matter-cpu "
                "activeForceAuthorityChanged=false matterCpuFallbackReady=true "
                "sourceMeshBuffersResident=true sourceMeshBuffersReused=false "
                "derivedBuffersResident=true derivedBuffersReused=false "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false gpuComputeReady=false "
                "highRateJsonPayload=false settingsControlPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true denseSdfConstructedOnGpu=true "
                "fullSourceMeshConsumedByGpu=true sampleCount=8 programReused=true "
                "shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false "
                "sourceMeshBuffersResident=true sourceMeshBuffersReused=true "
                "sourceVertexBufferBytes=413440 sourceTriangleBufferBytes=37024 "
                "derivedBuffersResident=true derivedBuffersReused=true "
                "skinnedPositionBufferBytes=21760 sdfDistanceBufferBytes=6292",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_CONSTRUCTION "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false "
                "highRateJsonPayload=false sourceMeshBuffersResident=true "
                "sourceMeshBuffersReused=true derivedBuffersResident=true "
                "derivedBuffersReused=true "
                "measuredBy=RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE.elapsedMs",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_SAMPLING_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeSamplingBoundaryReady=true residentFieldBufferSampled=true "
                "sourceFieldGenerationMatched=true fieldSamplingKernel=true "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "fieldKind=dense-sdf sampleCount=8 gpuComputeReady=false "
                "highRateJsonPayload=false programReused=true "
                "shaderCompiledThisSubmit=false pipelineCreatedThisSubmit=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_FORCE_SAMPLING_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeForceSamplingBoundaryReady=true residentFieldBufferSampled=true "
                "sourceFieldGenerationMatched=true fieldSamplingKernel=true "
                "fieldForceSamplingKernel=true fieldParticleKernel=false "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 "
                "componentCount=12 gpuComputeReady=false highRateJsonPayload=false "
                "programReused=true shaderCompiledThisSubmit=false "
                "pipelineCreatedThisSubmit=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FIELD_PARTICLE_FORCE_PROBE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true runtimeFieldBoundaryReady=true "
                "runtimeParticleForceComparisonReady=true "
                "residentFieldBufferSampled=true sourceFieldGenerationMatched=true "
                "particleSampleSource=matter-particle-snapshot "
                "matterParticleForceEquation=true fieldSamplingKernel=true "
                "fieldForceSamplingKernel=true fieldParticleKernel=true "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false fieldKind=dense-sdf sampleCount=4 "
                "componentCount=12 gpuComputeReady=false highRateJsonPayload=false "
                "programReused=true shaderCompiledThisSubmit=false "
                "pipelineCreatedThisSubmit=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_CANDIDATE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "candidateSelected=false candidatePromoted=false "
                "activeForceAuthorityChanged=false runtimeParticleIntegration=false "
                "forceAuthorityReady=false runtimeForceAuthority=false "
                "gpuComputeReady=false highRateJsonPayload=false "
                "settingsControlPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_GATE "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "forceAuthoritySlotCount=1 activeForceAuthorityCount=1 "
                "profileGate=explicit-profile-required profileGateSatisfied=false "
                "runtimeSelectionPermitted=false gpuForceAuthorityProfileEnabled=false "
                "candidateEligible=true candidateSelected=false candidatePromoted=false "
                "activeForceAuthorityChanged=false matterCpuFallbackReady=true "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false gpuComputeReady=false "
                "highRateJsonPayload=false settingsControlPayload=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_QUEST_MAKEPAD_GPU_FORCE_AUTHORITY_RESIDENCY "
                "readbackMatched=true queueWaitIdlePerformed=false "
                "recordedInputEquivalent=true forceAuthorityCandidateReady=true "
                "gpuComputeCandidateReady=true singleActiveForceAuthorityPreserved=true "
                "forceAuthoritySlotCount=1 activeForceAuthorityCount=1 "
                "activeForceAuthorityKind=matter-cpu "
                "activeForceAuthoritySource=matter-runtime-profile "
                "activeMatterForceAuthority=mesh-distance "
                "matterCpuOracleForceAuthority=mesh-distance "
                "activeForceAuthorityPreserved=matter-cpu-runtime "
                "profileGate=explicit-profile-required profileGateSatisfied=false "
                "runtimeSelectionPermitted=false gpuForceAuthorityProfileEnabled=false "
                "candidateEligible=true candidateSelected=false candidatePromoted=false "
                "observedResidentProofs=2 requiredResidentProofs=4 boundedProofOnly=true "
                "steadyStateResidencyReady=false freshnessReady=false cadenceReady=false "
                "expandedOracleComparisonReady=false liveRecordedProviderAbReady=false "
                "fallbackForceAuthority=mesh-distance "
                "fallbackReason=profile-prefers-matter-cpu "
                "activeForceAuthorityChanged=false matterCpuFallbackReady=true "
                "sourceMeshBuffersResident=true sourceMeshBuffersReused=true "
                "derivedBuffersResident=true derivedBuffersReused=true "
                "runtimeParticleIntegration=false forceAuthorityReady=false "
                "runtimeForceAuthority=false gpuComputeReady=false "
                "highRateJsonPayload=false settingsControlPayload=false",
            ),
        ]
        log_lines = [
            log_line(
                2919,
                "VrApi   ",
                "FPS=72/90,Prd=23ms,Stale=90,Stale2/5/10/max=0/0/0/0",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_SOURCE_SELECTION "
                "status=ready mode=recorded-hand-replay",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_WORKER_SOURCE "
                "status=ready compactFrameWorkerSubmit=true "
                "gpuOraclePayloadsRequested=false",
            ),
            log_line(
                5884,
                "HostessMakepad",
                "RUSTY_MAKEPAD_CADENCE phase=sample status=ok "
                "appFrameRateHz=90.00 xrUpdateRateHz=89.50 "
                "xrEffectiveFrameRateHz=90.00 xrRepaintGpuMs=0.36 "
                "xrUpdateDispatchMs=0.25",
            ),
            log_line(
                5884,
                "VrApi   ",
                "FPS=90/90,Prd=19ms,Stale=14,Stale2/5/10/max=0/0/1/20",
            ),
            *proof_lines,
            compact_log_line(
                5884,
                "HostessMakepad",
                "RUSTY_MAKEPAD_CADENCE phase=sample status=ok "
                "appFrameRateHz=90.00 xrUpdateRateHz=90.00 "
                "xrEffectiveFrameRateHz=90.00 xrRepaintGpuMs=0.36 "
                "xrUpdateDispatchMs=0.25",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(root, log_lines)
            payloads = summarize_evidence(
                root,
                max_sample_lines=8,
                require_mesh_sdf_program_reuse=True,
                require_source_buffer_reuse=True,
                require_derived_buffer_reuse=True,
                mesh_sdf_min_sample_count=8,
            )

        summary = payloads["summary"]
        self.assertEqual(5884, summary["app_pid"])
        self.assertEqual(1, summary["markers"]["gpu_proof_epoch"])
        self.assertEqual(2, summary["markers"]["gpu_mesh_sdf_probe"])
        self.assertEqual(2, summary["markers"]["gpu_field_construction"])
        self.assertEqual(2, summary["markers"]["gpu_field_sampling_probe"])
        self.assertEqual(2, summary["markers"]["gpu_field_force_sampling_probe"])
        self.assertEqual(2, summary["markers"]["gpu_field_particle_force_probe"])
        self.assertEqual(2, summary["markers"]["gpu_force_authority_candidate"])
        self.assertEqual(2, summary["markers"]["gpu_force_authority_gate"])
        self.assertEqual(2, summary["markers"]["gpu_force_authority_residency"])
        self.assertTrue(
            any(
                "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_GPU_PROOF_EPOCH" in line
                for line in summary["proof_lines"]
            )
        )
        self.assertEqual(90.0, summary["cadence"]["app_frame_rate_hz"]["max"])
        self.assertEqual(0, summary["vrapi_hostess_process"]["stale_90_plus_count"])
        self.assertEqual(14.0, summary["vrapi_hostess_process"]["stale"]["max"])
        self.assertEqual("ok", payloads["strict_scan"]["status"])
        self.assertEqual("ok", payloads["mesh_sdf_check"]["status"])
        self.assertEqual(8, payloads["mesh_sdf_check"]["mesh_sdf_max_sample_count"])
        self.assertEqual(
            2, payloads["mesh_sdf_check"]["derived_buffers_resident_count"]
        )
        self.assertEqual(1, payloads["mesh_sdf_check"]["derived_buffers_reused_count"])
        self.assertEqual(
            ["21760"],
            payloads["mesh_sdf_check"]["skinned_position_buffer_bytes_values"],
        )
        self.assertEqual(
            ["6292"], payloads["mesh_sdf_check"]["sdf_distance_buffer_bytes_values"]
        )
        self.assertIsNone(payloads["readiness"])

    def test_classifies_asleep_off_face_launch_as_xr_not_ready(self):
        log_lines = [
            log_line(
                8875,
                "HostessMakepad",
                "RUSTY_HOSTESS_MAKEPAD_MATTER_SURFACE_SOURCE_SELECTION "
                "status=ready mode=recorded-hand-replay",
            ),
            log_line(
                8875,
                "HostessMakepad",
                "RUSTY_MAKEPAD_CADENCE phase=start status=started",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_evidence(
                root,
                log_lines,
                power_after="mWakefulness=Asleep\nmProximityPositive=false\n",
                mounted_after="0\n",
                window_after="io.github.mesmerprism.rustyhostess.makepad/.MakepadAppXr",
            )
            payloads = summarize_evidence(
                root,
                max_sample_lines=8,
                require_mesh_sdf_program_reuse=False,
                require_source_buffer_reuse=False,
                require_derived_buffer_reuse=False,
                mesh_sdf_min_sample_count=8,
            )

        readiness = payloads["readiness"]
        self.assertIsNotNone(readiness)
        self.assertEqual("xr_not_ready", readiness["status"])
        self.assertTrue(readiness["not_gpu_failure"])
        self.assertTrue(readiness["power_after"]["wakefulness_asleep"])
        self.assertFalse(readiness["power_after"]["proximity_positive"])
        self.assertEqual("0", readiness["power_after"]["mounted"])
        self.assertEqual(0, readiness["marker_counts"]["gpu_mesh_sdf_probe"])
        self.assertEqual(0, readiness["marker_counts"]["gpu_field_construction"])

    def test_strict_scan_ignores_marker_kgsl_telemetry(self):
        scan = strict_log_scan(
            [
                log_line(
                    5884,
                    "HostessMakepad",
                    "RUSTY_QUEST_MAKEPAD_GPU_MESH_SDF_PROBE "
                    "kgslFaultsBeforeMarker=unavailable "
                    "kgslFaultsAfterMarker=unavailable",
                ),
                compact_log_line(
                    5884,
                    "HostessMakepad",
                    "RUSTY_QUEST_MAKEPAD_GPU_SKINNING_PROBE "
                    "kgslFaultsBeforeMarker=unavailable",
                ),
                log_line(1234, "kgsl", "GPU fault detected", level="E"),
                log_line(
                    5884,
                    "CameraService",
                    "Camera permission denied for package",
                    level="E",
                ),
            ]
        )

        self.assertEqual("failed", scan["status"])
        self.assertEqual(1, scan["fatal_anr_gpu_fault_line_count"])
        self.assertEqual(1, scan["camera_permission_failure_line_count"])
        self.assertNotIn(
            "kgslFaultsBeforeMarker", "\n".join(scan["fatal_anr_gpu_fault_lines"])
        )


if __name__ == "__main__":
    unittest.main()
