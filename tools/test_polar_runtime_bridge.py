from __future__ import annotations

import unittest

from tools import polar_protocol as polar
from tools import polar_runtime_bridge as bridge


class PolarRuntimeBridgeTests(unittest.TestCase):
    def test_builds_runtime_input_from_live_buffers(self) -> None:
        hr_events = [
            (
                10,
                polar.HeartRateReading(
                    bpm=61,
                    rr_intervals_ms=[1000.0, 990.0],
                    energy_expended=None,
                ),
            )
        ]
        acc_frames = [
            (
                20,
                polar.AccFrame(
                    sensor_timestamp_ns=123,
                    samples_mg=[
                        polar.AccSample(x_mg=1, y_mg=2, z_mg=3),
                        polar.AccSample(x_mg=4, y_mg=5, z_mg=6),
                    ],
                ),
            )
        ]

        doc = bridge.runtime_input_from_capture(
            input_id="input.test",
            hr_events=hr_events,
            acc_frames=acc_frames,
            acc_rate_hz=200,
            rmssd_gain_baseline={
                "baseline_ln_rmssd": 2.0,
                "baseline_mean_ln_rmssd": 2.1,
                "baseline_sd_ln_rmssd": 0.2,
                "baseline_window_count": 6,
                "baseline_source": "explicit_baseline",
            },
        )

        self.assertEqual(doc["input_id"], "input.test")
        self.assertEqual(doc["hr_rr"]["heart_rate_event_count"], 1)
        self.assertEqual(doc["hr_rr"]["rr_intervals_ms"], [1000.0, 990.0])
        self.assertEqual(doc["raw_acc"]["sample_rate_hz"], 200.0)
        self.assertEqual(len(doc["raw_acc"]["frames"]), 1)
        self.assertEqual(doc["raw_acc"]["frames"][0]["samples_mg"][1]["z_mg"], 6)
        self.assertEqual(doc["rmssd_gain_baseline"]["baseline_source"], "explicit_baseline")

    def test_graph_report_streams_drop_live_input_stream_duplicates(self) -> None:
        streams = bridge.graph_report_streams(
            {
                "streams": [
                    {"stream_id": polar.STREAM_HR_RR, "status": "pass"},
                    {"stream_id": polar.STREAM_ACC, "status": "pass"},
                    {"stream_id": polar.STREAM_COHERENCE, "status": "pass"},
                ]
            }
        )

        self.assertEqual([stream["stream_id"] for stream in streams], [polar.STREAM_COHERENCE])
        self.assertEqual(streams[0]["malformed_frame_count"], 0)


if __name__ == "__main__":
    unittest.main()
