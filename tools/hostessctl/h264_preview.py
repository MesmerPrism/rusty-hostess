"""Low-latency Windows preview for live raw H.264 byte streams."""

from __future__ import annotations

import ctypes
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


TIMING_MODE = "receiver_arrival_wallclock"
SYNC_MASTER = "external_clock"
DROP_POLICY = "ffplay_framedrop"
PREVIEW_QUEUE_CAPACITY_PACKETS = 4
PREVIEW_QUEUE_DROP_POLICY = "drop_on_overflow_resync_on_keyframe"
H264_KEY_FRAME_FLAG = 1
H264_CODEC_CONFIG_FLAG = 2


def build_low_latency_h264_ffplay_command(
    ffplay: str,
    window_title: str,
    *,
    width: int = 0,
    height: int = 0,
) -> list[str]:
    """Build a host-arrival-clocked FFplay command for timestamp-free H.264.

    Both ``adb exec-out screenrecord`` and the RMANVID1 preview adapter deliver
    Annex-B payloads to FFplay without their original container timestamps.
    Treating those bytes as a fixed 25-fps file makes high-rate Quest streams
    accumulate seconds of latency.  Wall-clock timestamps keep playback tied
    to live receiver arrival, while FFplay may discard a late frame instead of
    growing an unbounded playback queue.
    """

    command = [
        ffplay,
        "-hide_banner",
        "-loglevel",
        "warning",
        "-fflags",
        "nobuffer",
        "-flags",
        "low_delay",
        "-probesize",
        "32",
        "-analyzeduration",
        "0",
        "-use_wallclock_as_timestamps",
        "1",
        "-framedrop",
        "-sync",
        "ext",
        "-window_title",
        window_title,
    ]
    if width > 0 and height > 0:
        command.extend(["-x", str(int(width)), "-y", str(int(height))])
    command.extend(["-f", "h264", "-i", "pipe:0"])
    return command


class LowLatencyH264PreviewSink:
    """Own one FFplay preview without exposing a helper console window."""

    def __init__(
        self,
        ffplay: str,
        window_title: str,
        *,
        width: int = 0,
        height: int = 0,
        queue_capacity_packets: int = PREVIEW_QUEUE_CAPACITY_PACKETS,
    ) -> None:
        self.ffplay = str(ffplay or "").strip()
        self.window_title = str(window_title or "").strip()
        self.width = max(0, int(width))
        self.height = max(0, int(height))
        self.queue_capacity_packets = max(2, int(queue_capacity_packets))
        self.process: subprocess.Popen[bytes] | None = None
        self.stderr_chunks: list[bytes] = []
        self.stderr_thread: threading.Thread | None = None
        self.writer_thread: threading.Thread | None = None
        self.payload_queue: queue.Queue[bytes | None] = queue.Queue(
            maxsize=self.queue_capacity_packets
        )
        self.started = False
        self.accepting_payloads = False
        self.payload_writes = 0
        self.bytes_written = 0
        self.payload_enqueues = 0
        self.bytes_enqueued = 0
        self.queue_max_depth = 0
        self.queue_dropped_packets = 0
        self.queue_dropped_bytes = 0
        self.queue_resync_events = 0
        self.codec_config_payload = b""
        self.error = ""
        self.visible_window_seen = False
        self.visible_window_title = ""
        self.started_monotonic: float | None = None
        self.first_payload_monotonic: float | None = None
        self.first_window_monotonic: float | None = None
        self.result: dict[str, Any] | None = None

    def start(self) -> None:
        if not self.ffplay or self.started:
            return
        resolved = shutil.which(self.ffplay)
        if not resolved and Path(self.ffplay).is_file():
            resolved = str(Path(self.ffplay).resolve())
        if not resolved:
            self.error = f"ffplay was not found: {self.ffplay}"
            return
        try:
            self.process = subprocess.Popen(
                build_low_latency_h264_ffplay_command(
                    resolved,
                    self.window_title,
                    width=self.width,
                    height=self.height,
                ),
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
                creationflags=windows_creation_flags(),
            )
            self.started = self.process.stdin is not None
            self.accepting_payloads = self.started
            self.started_monotonic = time.monotonic()
            self.stderr_thread = threading.Thread(
                target=self._read_stderr,
                name="HostessLowLatencyH264PreviewStderr",
                daemon=True,
            )
            self.stderr_thread.start()
            if self.started:
                self.writer_thread = threading.Thread(
                    target=self._write_payloads,
                    name="HostessLowLatencyH264PreviewWriter",
                    daemon=True,
                )
                self.writer_thread.start()
        except OSError as error:
            self.error = str(error)

    def _read_stderr(self) -> None:
        if self.process is None or self.process.stderr is None:
            return
        while True:
            chunk = self.process.stderr.read(4096)
            if not chunk:
                return
            self.stderr_chunks.append(chunk)

    def write(self, payload: bytes, *, flags: int = 0) -> None:
        """Queue payload without allowing preview backpressure onto the receiver."""

        if not payload or not self.accepting_payloads or self.process is None:
            return
        returncode = self.process.poll()
        if returncode is not None:
            if not self.error:
                self.error = f"ffplay exited before preview completed (returncode={returncode})"
            return
        if flags & H264_CODEC_CONFIG_FLAG:
            self.codec_config_payload = payload
        if self._enqueue(payload):
            return

        if not flags & H264_KEY_FRAME_FLAG:
            self.queue_dropped_packets += 1
            self.queue_dropped_bytes += len(payload)
            return

        self._discard_queued_payloads()
        self.queue_resync_events += 1
        if self.codec_config_payload and self.codec_config_payload != payload:
            self._enqueue(self.codec_config_payload)
        self._enqueue(payload)

    def _enqueue(self, payload: bytes) -> bool:
        try:
            self.payload_queue.put_nowait(payload)
        except queue.Full:
            return False
        self.payload_enqueues += 1
        self.bytes_enqueued += len(payload)
        self.queue_max_depth = max(self.queue_max_depth, self.payload_queue.qsize())
        return True

    def _discard_queued_payloads(self) -> None:
        while True:
            try:
                discarded = self.payload_queue.get_nowait()
            except queue.Empty:
                return
            if discarded is not None:
                self.queue_dropped_packets += 1
                self.queue_dropped_bytes += len(discarded)

    def _write_payloads(self) -> None:
        if self.process is None or self.process.stdin is None:
            return
        while True:
            payload = self.payload_queue.get()
            if payload is None:
                return
            try:
                remaining = memoryview(payload)
                while remaining:
                    written = self.process.stdin.write(remaining)
                    if written is None or written <= 0:
                        raise BrokenPipeError("ffplay preview pipe stopped accepting video")
                    remaining = remaining[written:]
                now = time.monotonic()
                if self.first_payload_monotonic is None:
                    self.first_payload_monotonic = now
                self.payload_writes += 1
                self.bytes_written += len(payload)
                self._observe_visible_window(now)
            except (BrokenPipeError, OSError) as error:
                if not self.error:
                    self.error = str(error)
                self.accepting_payloads = False
                return

    def close(self) -> dict[str, Any]:
        if self.result is not None:
            return dict(self.result)
        returncode: int | None = None
        terminated_after_eof_timeout = False
        killed_after_eof_timeout = False
        self.accepting_payloads = False
        self._discard_queued_payloads()
        try:
            self.payload_queue.put_nowait(None)
        except queue.Full:
            pass
        if self.writer_thread is not None:
            self.writer_thread.join(timeout=2)
        self._observe_visible_window()
        if self.process is not None:
            if self.process.stdin is not None:
                try:
                    self.process.stdin.close()
                except OSError:
                    pass
            try:
                returncode = self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                terminated_after_eof_timeout = True
                self.process.terminate()
                try:
                    returncode = self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    killed_after_eof_timeout = True
                    self.process.kill()
                    returncode = self.process.wait(timeout=5)
            if self.stderr_thread is not None:
                self.stderr_thread.join(timeout=2)
        self._observe_visible_window()
        stderr = b"".join(self.stderr_chunks).decode("utf-8", errors="replace")
        self.result = {
            "enabled": bool(self.ffplay),
            "ffplay": self.ffplay,
            "window_title": self.window_title,
            "started": self.started,
            "payload_writes": self.payload_writes,
            "bytes_written": self.bytes_written,
            "payload_enqueues": self.payload_enqueues,
            "bytes_enqueued": self.bytes_enqueued,
            "queue_capacity_packets": self.queue_capacity_packets,
            "queue_max_depth": self.queue_max_depth,
            "queue_dropped_packets": self.queue_dropped_packets,
            "queue_dropped_bytes": self.queue_dropped_bytes,
            "queue_resync_events": self.queue_resync_events,
            "writer_thread_stopped": self.writer_thread is None or not self.writer_thread.is_alive(),
            "returncode": returncode,
            "terminated_after_eof_timeout": terminated_after_eof_timeout,
            "killed_after_eof_timeout": killed_after_eof_timeout,
            "error": self.error,
            "visible_window_seen": self.visible_window_seen,
            "visible_window_title": self.visible_window_title,
            "first_payload_delay_ms": elapsed_ms(
                self.started_monotonic,
                self.first_payload_monotonic,
            ),
            "first_visible_window_delay_ms": elapsed_ms(
                self.started_monotonic,
                self.first_window_monotonic,
            ),
            "timing_mode": TIMING_MODE,
            "sync_master": SYNC_MASTER,
            "drop_policy": DROP_POLICY,
            "preview_queue_drop_policy": PREVIEW_QUEUE_DROP_POLICY,
            "stderr": stderr[-8192:],
        }
        return dict(self.result)

    def _observe_visible_window(self, now: float | None = None) -> None:
        if self.visible_window_seen or self.process is None or os.name != "nt":
            return
        for title in visible_window_titles_for_process(self.process.pid):
            if title == self.window_title:
                self.visible_window_seen = True
                self.visible_window_title = title
                self.first_window_monotonic = now if now is not None else time.monotonic()
                return


def elapsed_ms(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return round(max(0.0, (end - start) * 1000.0), 3)


def windows_creation_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def visible_window_titles_for_process(process_id: int) -> list[str]:
    if os.name != "nt":
        return []
    user32 = ctypes.windll.user32
    titles: list[str] = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(window_handle: int, _: int) -> bool:
        owner_process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(window_handle, ctypes.byref(owner_process_id))
        if owner_process_id.value != int(process_id) or not user32.IsWindowVisible(window_handle):
            return True
        title_length = int(user32.GetWindowTextLengthW(window_handle))
        if title_length <= 0:
            return True
        buffer = ctypes.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(window_handle, buffer, title_length + 1)
        if buffer.value:
            titles.append(buffer.value)
        return True

    user32.EnumWindows(visit, 0)
    return titles


__all__ = [
    "DROP_POLICY",
    "PREVIEW_QUEUE_CAPACITY_PACKETS",
    "PREVIEW_QUEUE_DROP_POLICY",
    "LowLatencyH264PreviewSink",
    "SYNC_MASTER",
    "TIMING_MODE",
    "build_low_latency_h264_ffplay_command",
    "visible_window_titles_for_process",
    "windows_creation_flags",
]
