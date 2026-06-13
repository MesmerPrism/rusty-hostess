import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_makepad_quest_live_recorded_ab import validate_provider_ab


def recorded_summary():
    return {
        "schema": "rusty.hostess.quest_live_hand_small_profile_summary.v1",
        "recorded_hand_source": {
            "ready_line_count": 1,
            "compact_worker_ready_line_count": 1,
            "sample_lines": [
                "RUSTY_HOSTESS_MAKEPAD_RECORDED_HAND_SURFACE_WORKER_SOURCE "
                "status=ready selectedMode=recorded-hand-replay "
                "sourceId=recorded-meta-quest-hand-left-capture "
                "providerShape=bind-mesh-plus-compact-joint-frame frameIndex=10 "
                "vertexCount=1360 triangleCount=2314 issue=none "
                "recordedHandProvider=true workerSourceSelected=true "
                "compactFrameWorkerSubmit=true sourceFrameExpansionThread=matter-worker "
                "gpuOraclePayloadsRequested=false recordedInputEquivalent=true "
                "gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false"
            ],
        },
    }


def live_summary():
    return {
        "schema": "rusty.hostess.quest_live_hand_small_profile_summary.v1",
        "live_hand_source": {
            "ready_line_count": 1,
            "sample_lines": [
                "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_SOURCE "
                "status=ready sourceId=live-meta-quest-hand-left handedness=left "
                "frameIndex=214 bindVersion=3 jointCount=26 vertexCount=1360 "
                "indexCount=6942 providerShape=bind-mesh-plus-compact-joint-frame "
                "liveOpenXrHandProvider=true recordedInputEquivalent=true "
                "gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false"
            ],
        },
        "live_hand_worker_source": {
            "ready_line_count": 1,
            "compact_worker_ready_line_count": 1,
            "sample_lines": [
                "RUSTY_HOSTESS_MAKEPAD_LIVE_HAND_SURFACE_WORKER_SOURCE "
                "status=ready selectedMode=live-openxr-hand-left "
                "sourceId=live-meta-quest-hand-left "
                "providerShape=bind-mesh-plus-compact-joint-frame frameIndex=214 "
                "vertexCount=1360 triangleCount=2314 issue=none "
                "liveOpenXrHandProvider=true workerSourceSelected=true "
                "compactFrameWorkerSubmit=true sourceFrameExpansionThread=matter-worker "
                "gpuOraclePayloadsRequested=true recordedInputEquivalent=true "
                "gpuAdapterBoundaryUnchanged=true highRateJsonPayload=false"
            ],
        },
    }


class MakepadQuestLiveRecordedAbCheckTests(unittest.TestCase):
    def test_accepts_matching_live_recorded_provider_shape(self):
        result = validate_provider_ab(
            recorded_summary(),
            live_summary(),
            Path("recorded-summary.json"),
            Path("live-summary.json"),
        )

        self.assertTrue(result.ok)
        self.assertEqual("ok", result.report["status"])
        self.assertTrue(
            result.report["promotion"]["liveRecordedProviderAbReadyCandidate"]
        )
        self.assertFalse(result.report["promotion"]["runtimeSelectionPermitted"])
        self.assertFalse(result.report["promotion"]["runtimeForceAuthority"])
        self.assertFalse(result.report["promotion"]["gpuComputeReady"])

    def test_rejects_missing_live_worker_shape(self):
        live = live_summary()
        live["live_hand_worker_source"]["sample_lines"] = []

        result = validate_provider_ab(
            recorded_summary(),
            live,
            Path("recorded-summary.json"),
            Path("live-summary.json"),
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("live worker" in issue for issue in result.issues))

    def test_rejects_topology_mismatch(self):
        live = live_summary()
        live["live_hand_worker_source"]["sample_lines"] = [
            live["live_hand_worker_source"]["sample_lines"][0].replace(
                "vertexCount=1360", "vertexCount=1359"
            )
        ]

        result = validate_provider_ab(
            recorded_summary(),
            live,
            Path("recorded-summary.json"),
            Path("live-summary.json"),
        )

        self.assertFalse(result.ok)
        self.assertTrue(any("vertexCount mismatch" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
