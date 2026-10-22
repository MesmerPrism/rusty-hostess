from __future__ import annotations

import argparse
import json
import socket
import struct
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from tools.hostessctl.display_stream import (
    STOP_REPORT_SCHEMA,
    appop_mode,
    build_adb_screenrecord_command,
    build_media_projection_start_command,
    build_media_projection_stop_command,
    build_raw_h264_ffplay_command,
    build_scrcpy_command,
    build_shell_mirror_command,
    effective_display_stream_max_packets,
    extract_rmanvid1_h264,
    has_annex_b_start_code,
    request_display_stream_stop,
    shell_mirror_completed,
)
from tools.hostessctl.connectivity_media_receiver_capture import (
    capture_rmanvid1_socket_bytes,
)
from tools.hostessctl.h264_preview import (
    LowLatencyH264PreviewSink,
)


class RunningPreviewProcess:
    def poll(self) -> None:
        return None


class DisplayStreamTests(unittest.TestCase):
    def args(self) -> argparse.Namespace:
        return argparse.Namespace(
            adb="adb",
            serial="quest-serial",
            port=9079,
            display_id=0,
            width=1920,
            height=1080,
            fps=30,
            bitrate_bps=8_000_000,
            duration_seconds=5,
            scrcpy="scrcpy",
            preview=False,
            preview_window_title="Rusty Hostess Test Viewer",
            capture_mode="full",
        )

    def test_media_projection_and_shell_share_stream_settings(self) -> None:
        args = self.args()
        media = build_media_projection_start_command(args)
        shell = build_shell_mirror_command(args)
        for token in ["9079", "1920", "1080", "30", "8000000", "5"]:
            self.assertIn(token, media)
            self.assertIn(token, shell)
        self.assertIn(".DisplayStreamActivity", " ".join(media))
        self.assertIn("ShellDisplayMirrorMain", " ".join(shell))
        self.assertNotIn("MediaProjection", " ".join(shell))

    def test_media_projection_stop_uses_app_owned_control_receiver(self) -> None:
        command = build_media_projection_stop_command(self.args())
        self.assertIn("broadcast", command)
        self.assertIn("io.github.mesmerprism.rustyquest.displaystream.action.STOP", command)
        self.assertIn(
            "io.github.mesmerprism.rustyquest.displaystream/.DisplayStreamControlReceiver",
            command,
        )

    def test_scrcpy_is_a_compatibility_protocol_adapter(self) -> None:
        command = build_scrcpy_command(self.args(), Path("capture.mp4"))
        self.assertIn("--video-codec=h264", command)
        self.assertIn("--no-control", command)
        self.assertIn("--no-clipboard-autosync", command)
        self.assertIn("--display-id=0", command)
        self.assertIn("--record-format=mkv", command)
        self.assertIn("--no-window", command)
        self.assertNotIn("RMANVID1", " ".join(command))
        self.assertIn("--window-title=Rusty Hostess Test Viewer", command)

    def test_unlimited_scrcpy_omits_timer_and_recording_for_preview_only_mode(self) -> None:
        args = self.args()
        args.duration_seconds = 0
        args.capture_mode = "none"
        args.preview = True
        command = build_scrcpy_command(args, Path("capture.mkv"))
        self.assertFalse(any(part.startswith("--time-limit=") for part in command))
        self.assertFalse(any(part.startswith("--record=") for part in command))
        self.assertNotIn("--no-window", command)

    def test_adb_screenrecord_streams_raw_h264_without_device_file(self) -> None:
        command = build_adb_screenrecord_command(self.args())
        joined = " ".join(command)
        for token in [
            "exec-out",
            "screenrecord",
            "--output-format=h264",
            "1920x1080",
            "8000000",
            "5",
        ]:
            self.assertIn(token, command)
        self.assertEqual("-", command[-1])
        self.assertNotIn("--display-id", command)
        self.assertNotIn("/sdcard", joined)
        self.assertNotIn("MediaProjection", joined)
        self.assertNotIn("RMANVID1", joined)

    def test_adb_screenrecord_preserves_large_physical_display_id(self) -> None:
        args = self.args()
        args.display_id = 12_345_678_901
        command = build_adb_screenrecord_command(args)
        display_index = command.index("--display-id")
        self.assertEqual("12345678901", command[display_index + 1])

    def test_raw_h264_preview_uses_receiver_wallclock_for_live_playback(self) -> None:
        command = build_raw_h264_ffplay_command("ffplay", "Quest preview")
        self.assertEqual("nobuffer", command[command.index("-fflags") + 1])
        self.assertEqual("1", command[command.index("-use_wallclock_as_timestamps") + 1])
        self.assertEqual("ext", command[command.index("-sync") + 1])
        self.assertIn("-framedrop", command)
        self.assertNotIn("-framerate", command)
        self.assertNotIn("-autoexit", command)
        self.assertNotIn("-vf", command)
        self.assertEqual("Quest preview", command[command.index("-window_title") + 1])

    def test_preview_queue_drops_backlog_and_recovers_on_keyframe(self) -> None:
        sink = LowLatencyH264PreviewSink(
            "ffplay",
            "Quest preview",
            queue_capacity_packets=2,
        )
        sink.process = RunningPreviewProcess()  # type: ignore[assignment]
        sink.started = True
        sink.accepting_payloads = True
        sink.write(b"config", flags=2)
        sink.write(b"delta-1")
        sink.write(b"delta-overflow")
        sink.write(b"keyframe", flags=1)

        self.assertEqual([b"config", b"keyframe"], list(sink.payload_queue.queue))
        self.assertEqual(3, sink.queue_dropped_packets)
        self.assertEqual(1, sink.queue_resync_events)
        self.assertEqual(2, sink.queue_max_depth)

    def test_rmanvid1_auto_packet_bound_covers_high_rate_quest_displays(self) -> None:
        args = self.args()
        args.duration_seconds = 30
        args.max_packets = 0
        self.assertEqual(3856, effective_display_stream_max_packets(args))
        args.max_packets = 777
        self.assertEqual(777, effective_display_stream_max_packets(args))
        args.max_packets = 0
        args.duration_seconds = 0
        self.assertEqual(0, effective_display_stream_max_packets(args))

    def test_stop_route_writes_control_file_and_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stop_file = Path(directory) / "active.stop"
            out = Path(directory) / "stop.json"
            result = request_display_stream_stop(
                argparse.Namespace(stop_file=str(stop_file), out=str(out))
            )
            self.assertEqual(0, result)
            self.assertTrue(stop_file.is_file())
            receipt = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(STOP_REPORT_SCHEMA, receipt["schema"])
            self.assertEqual("pass", receipt["status"])

    def test_appop_mode_preserves_prior_project_media_authority(self) -> None:
        self.assertEqual("ignore", appop_mode("PROJECT_MEDIA: ignore; rejectTime=+2m"))
        self.assertEqual("allow", appop_mode("PROJECT_MEDIA: allow; time=+4s"))
        self.assertEqual("default", appop_mode("No operations."))

    def test_extracts_h264_payloads_from_rmanvid1(self) -> None:
        metadata = json.dumps({"source_kind": "shell_display_mirror"}).encode("utf-8")
        payloads = [b"\x00\x00\x00\x01\x67", b"\x00\x00\x00\x01\x65\x88"]
        with tempfile.TemporaryDirectory() as directory:
            capture = Path(directory) / "capture.rmanvid1"
            output = Path(directory) / "capture.h264"
            with capture.open("wb") as stream:
                stream.write(b"RMANVID1")
                stream.write(struct.pack(">IIIIII", 1, 1, 1920, 1080, 0, len(metadata)))
                stream.write(metadata)
                for index, payload in enumerate(payloads):
                    stream.write(struct.pack(">QIIQQ", index, 0, len(payload), index, index))
                    stream.write(payload)
            evidence = extract_rmanvid1_h264(capture, output)
            self.assertEqual(2, evidence["packet_count"])
            self.assertEqual(b"".join(payloads), output.read_bytes())

    def test_unlimited_receiver_keeps_streaming_after_sample_is_full(self) -> None:
        sender, receiver = socket.socketpair()
        try:
            header = b"RMANVID1" + struct.pack(">IIIIII", 1, 1, 1920, 1080, 0, 0)
            payloads = [b"\x00\x00\x00\x01\x67", b"\x00\x00\x00\x01\x65"]
            stream = bytearray(header)
            for index, payload in enumerate(payloads):
                stream.extend(struct.pack(">QIIQQ", index, 0, len(payload), index, index))
                stream.extend(payload)
            sender.sendall(stream)
            sender.shutdown(socket.SHUT_WR)
            output = BytesIO()
            close_reason, bytes_written, packet_count, retention_full = (
                capture_rmanvid1_socket_bytes(
                    receiver,
                    output,
                    [],
                    max_capture_bytes=len(header) + 32 + len(payloads[0]),
                    max_packets=0,
                    max_packet_bytes=1024,
                    max_metadata_bytes=1024,
                    continue_after_capture_limit=True,
                )
            )
            self.assertEqual("peer_closed", close_reason)
            self.assertEqual(2, packet_count)
            self.assertTrue(retention_full)
            self.assertEqual(len(header) + 32 + len(payloads[0]), bytes_written)
        finally:
            sender.close()
            receiver.close()

    def test_detects_annex_b_start_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            valid = Path(directory) / "valid.h264"
            invalid = Path(directory) / "invalid.h264"
            valid.write_bytes(b"\x00\x00\x00\x01\x67")
            invalid.write_bytes(b"not-h264")
            self.assertTrue(has_annex_b_start_code(valid))
            self.assertFalse(has_annex_b_start_code(invalid))

    def test_shell_mirror_marker_never_overrides_nonzero_exit(self) -> None:
        marker = {
            "schema": "rusty.quest.display_stream.shell_marker.v1",
            "status": "complete",
            "error": "",
        }
        result = {
            "returncode": 1,
            "stdout": "RUSTY_QUEST_DISPLAY_STREAM " + json.dumps(marker),
        }

        self.assertFalse(shell_mirror_completed(result))
        result["returncode"] = 0
        self.assertTrue(shell_mirror_completed(result))
        marker["error"] = "encoder failed"
        result["stdout"] = "RUSTY_QUEST_DISPLAY_STREAM " + json.dumps(marker)
        self.assertFalse(shell_mirror_completed(result))


if __name__ == "__main__":
    unittest.main()
