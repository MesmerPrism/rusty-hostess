"""Unified headset display-stream orchestration for Hostess."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Sequence

from tools.hostessctl.connectivity_media_receiver_capture import (
    capture_rmanvid1_receiver_stream,
)
from tools.hostessctl.h264_preview import (
    LowLatencyH264PreviewSink,
    build_low_latency_h264_ffplay_command,
    windows_creation_flags,
)


REPORT_SCHEMA = "rusty.hostess.display_stream.run.v1"
STOP_REPORT_SCHEMA = "rusty.hostess.display_stream.stop.v1"
DISPLAY_STREAM_PACKAGE = "io.github.mesmerprism.rustyquest.displaystream"
DISPLAY_STREAM_ACTIVITY = f"{DISPLAY_STREAM_PACKAGE}/.DisplayStreamActivity"
DISPLAY_STREAM_CONTROL_RECEIVER = f"{DISPLAY_STREAM_PACKAGE}/.DisplayStreamControlReceiver"
DISPLAY_STREAM_STOP_ACTION = f"{DISPLAY_STREAM_PACKAGE}.action.STOP"
SHELL_MAIN_CLASS = (
    "io.github.mesmerprism.rustyquest.displaystream.ShellDisplayMirrorMain"
)
DEVICE_SHELL_JAR = "/data/local/tmp/rusty-quest-display-mirror-shell.jar"
RMANVID1_MAGIC = b"RMANVID1"
DISPLAY_STREAM_PACKET_RATE_CEILING = 120
DISPLAY_STREAM_PACKET_DRAIN_ALLOWANCE = 256


def build_media_projection_start_command(args: Any) -> list[str]:
    return adb_prefix(args) + [
        "shell",
        "am",
        "start",
        "-n",
        DISPLAY_STREAM_ACTIVITY,
        "--es",
        "host",
        "127.0.0.1",
        "--ei",
        "port",
        str(int(args.port)),
        "--ei",
        "width",
        str(int(args.width)),
        "--ei",
        "height",
        str(int(args.height)),
        "--ei",
        "fps",
        str(int(args.fps)),
        "--ei",
        "bitrate_bps",
        str(int(args.bitrate_bps)),
        "--ei",
        "duration_seconds",
        str(int(args.duration_seconds)),
    ]


def build_media_projection_stop_command(args: Any) -> list[str]:
    return adb_prefix(args) + [
        "shell",
        "am",
        "broadcast",
        "-a",
        DISPLAY_STREAM_STOP_ACTION,
        "-n",
        DISPLAY_STREAM_CONTROL_RECEIVER,
    ]


def build_shell_mirror_command(args: Any) -> list[str]:
    return adb_prefix(args) + [
        "shell",
        "env",
        f"CLASSPATH={getattr(args, '_remote_shell_jar', DEVICE_SHELL_JAR)}",
        "app_process",
        "/system/bin",
        SHELL_MAIN_CLASS,
        "--host",
        "127.0.0.1",
        "--port",
        str(int(args.port)),
        "--display-id",
        str(int(args.display_id)),
        "--width",
        str(int(args.width)),
        "--height",
        str(int(args.height)),
        "--fps",
        str(int(args.fps)),
        "--bitrate-bps",
        str(int(args.bitrate_bps)),
        "--duration-seconds",
        str(int(args.duration_seconds)),
    ]


def build_scrcpy_command(args: Any, recording_path: Path) -> list[str]:
    command = [
        str(args.scrcpy),
        "--serial",
        str(args.serial),
        f"--display-id={int(args.display_id)}",
        "--no-control",
        "--no-audio",
        "--no-clipboard-autosync",
        "--video-codec=h264",
        f"--max-size={max(int(args.width), int(args.height))}",
        f"--max-fps={int(args.fps)}",
        f"--video-bit-rate={int(args.bitrate_bps)}",
        f"--window-title={preview_window_title(args)}",
    ]
    if int(args.duration_seconds) > 0:
        command.append(f"--time-limit={int(args.duration_seconds)}")
    if str(getattr(args, "capture_mode", "full")) == "full":
        command.extend([f"--record={recording_path}", "--record-format=mkv"])
    if not bool(getattr(args, "preview", False)):
        command.append("--no-window")
    return command


def build_adb_screenrecord_command(args: Any) -> list[str]:
    command = adb_prefix(args) + [
        "exec-out",
        "screenrecord",
        "--output-format=h264",
        "--size",
        f"{int(args.width)}x{int(args.height)}",
        "--bit-rate",
        str(int(args.bitrate_bps)),
        "--time-limit",
        str(int(args.duration_seconds)),
    ]
    if int(args.display_id) > 0:
        command.extend(["--display-id", str(int(args.display_id))])
    command.append("-")
    return command


def build_raw_h264_ffplay_command(
    ffplay: str,
    window_title: str,
) -> list[str]:
    return build_low_latency_h264_ffplay_command(ffplay, window_title)


def effective_display_stream_max_packets(args: Any) -> int:
    requested = int(getattr(args, "max_packets", 0) or 0)
    if requested > 0:
        return requested
    duration_seconds = int(getattr(args, "duration_seconds", 0) or 0)
    if duration_seconds <= 0:
        return 0
    return (
        duration_seconds * DISPLAY_STREAM_PACKET_RATE_CEILING
        + DISPLAY_STREAM_PACKET_DRAIN_ALLOWANCE
    )


def run_display_stream(
    args: Any,
    *,
    run_func: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> int:
    """Run one of the four display sources behind one evidence contract."""

    runner = run_func or subprocess.run
    source = str(args.source)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    capture = Path(args.capture_out).resolve() if args.capture_out else out.with_suffix(".rmanvid1")
    sidecar = (
        Path(args.sidecar_out).resolve()
        if args.sidecar_out
        else capture.with_suffix(capture.suffix + ".sidecar.json")
    )
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": "fail",
        "source": {
            "kind": source,
            "consent_authority": (
                (
                    "android_project_media_appop_temporary"
                    if str(getattr(args, "media_projection_consent", "prompt")) == "pregrant"
                    else "android_media_projection_prompt"
                )
                if source == "media-projection"
                else (
                    "android_shell_screenrecord"
                    if source == "adb-screenrecord"
                    else ("android_shell_uid" if source == "shell-mirror" else "scrcpy_server")
                )
            ),
        },
        "device": {"serial": str(args.serial)},
        "video": {
            "codec": "h264",
            "width": int(args.width),
            "height": int(args.height),
            "fps": int(args.fps),
            "bitrate_bps": int(args.bitrate_bps),
            "duration_seconds": int(args.duration_seconds),
        },
        "transport": {
            "kind": (
                "scrcpy_internal"
                if source == "scrcpy"
                else ("adb_exec_out" if source == "adb-screenrecord" else "adb_reverse_tcp")
            ),
            "wire_protocol": (
                "scrcpy_internal"
                if source == "scrcpy"
                else ("h264_annex_b" if source == "adb-screenrecord" else "RMANVID1")
            ),
            "port": None if source in {"scrcpy", "adb-screenrecord"} else int(args.port),
        },
        "capture": {},
        "launch": {},
        "cleanup": {},
        "issue_codes": [],
    }
    media_projection_restore_mode: str | None = None
    shell_directory_owned = False
    source_started = False
    remote_dir = "/data/local/tmp/rusty-hostess-display-" + uuid.uuid4().hex
    remote_jar = remote_dir + "/producer.jar"
    stop_file = stop_file_path(args)
    report["lifecycle"] = {
        "mode": "until_stopped" if int(args.duration_seconds) <= 0 else "timed",
        "stop_file": str(stop_file) if stop_file is not None else "",
        "stop_requested": False,
        "capture_mode": str(getattr(args, "capture_mode", "full")),
    }

    if source == "shell-mirror" and (int(args.duration_seconds) <= 0 or stop_file is not None):
        report["issue_codes"].append("hostess.issue.display_stream.owned_control_adapter_required")
        return finish(report, out, args)
    try:
        device = execute(runner, adb_prefix(args) + ["get-state"], timeout=10)
        report["device"]["get_state"] = device
        if device["returncode"] != 0 or "device" not in device["stdout"].split():
            report["issue_codes"].append("hostess.issue.display_stream.device_unavailable")
            return finish(report, out, args)

        if source == "shell-mirror" and not Path(str(args.shell_jar)).is_file():
            report["issue_codes"].append("hostess.issue.display_stream.shell_jar_missing")
            return finish(report, out, args)

        if source == "scrcpy":
            return run_scrcpy_source(args, report, out, runner)
        if source == "adb-screenrecord":
            return run_adb_screenrecord_source(args, report, out, runner)

        if bool(getattr(args, "install_apk", False)):
            apk = Path(str(args.apk)).resolve()
            if not apk.is_file():
                report["issue_codes"].append("hostess.issue.display_stream.apk_missing")
                report["launch"]["apk"] = str(apk)
                return finish(report, out, args)
            report["launch"]["install"] = execute(
                runner,
                adb_prefix(args) + ["install", "-r", str(apk)],
                timeout=120,
            )
            if report["launch"]["install"]["returncode"] != 0:
                report["issue_codes"].append("hostess.issue.display_stream.apk_install_failed")
                return finish(report, out, args)
            report["launch"]["package_readback"] = execute(
                runner,
                adb_prefix(args) + ["shell", "pm", "path", DISPLAY_STREAM_PACKAGE],
                timeout=15,
            )
            if (
                report["launch"]["package_readback"]["returncode"] != 0
                or "package:" not in report["launch"]["package_readback"]["stdout"]
            ):
                report["issue_codes"].append("hostess.issue.display_stream.apk_readback_failed")
                return finish(report, out, args)

        if source == "media-projection" and str(args.media_projection_consent) == "pregrant":
            appop_before = execute(
                runner,
                adb_prefix(args) + ["shell", "cmd", "appops", "get", DISPLAY_STREAM_PACKAGE, "PROJECT_MEDIA"],
                timeout=15,
            )
            media_projection_restore_mode = appop_mode(appop_before.get("stdout", ""))
            appop_allow = execute(
                runner,
                adb_prefix(args) + ["shell", "cmd", "appops", "set", DISPLAY_STREAM_PACKAGE, "PROJECT_MEDIA", "allow"],
                timeout=15,
            )
            appop_readback = execute(
                runner,
                adb_prefix(args) + ["shell", "cmd", "appops", "get", DISPLAY_STREAM_PACKAGE, "PROJECT_MEDIA"],
                timeout=15,
            )
            report["launch"]["media_projection_appop"] = {
                "before": appop_before,
                "restore_mode": media_projection_restore_mode,
                "allow": appop_allow,
                "readback": appop_readback,
            }
            if appop_allow["returncode"] != 0 or appop_mode(appop_readback.get("stdout", "")) != "allow":
                report["issue_codes"].append("hostess.issue.display_stream.media_projection_pregrant_failed")
                return finish(report, out, args)

        if source == "media-projection" and bool(getattr(args, "focus_home_before_consent", False)):
            report["launch"]["focus_home"] = execute(
                runner,
                adb_prefix(args) + ["shell", "input", "keyevent", "HOME"],
                timeout=15,
            )

        reverse_state = create_reverse(args, runner)
        report["transport"]["reverse"] = reverse_state
        if reverse_state["apply"]["returncode"] != 0:
            report["issue_codes"].append("hostess.issue.display_stream.adb_reverse_failed")
            return finish(report, out, args)

        receiver_result: dict[str, Any] = {}
        receiver_ready = threading.Event()

        def receive() -> None:
            receiver_result.update(
                capture_rmanvid1_receiver_stream(
                    bind_host=str(args.bind_host),
                    bind_port=int(args.port),
                    capture_path=capture,
                    sidecar_path=sidecar,
                    timeout_seconds=float(args.timeout_seconds),
                    max_capture_bytes=int(args.max_bytes),
                    max_packets=effective_display_stream_max_packets(args),
                    continue_after_capture_limit=(
                        int(args.duration_seconds) <= 0
                        and str(getattr(args, "capture_mode", "full")) == "sample"
                    ),
                    capture_kind=f"display_stream_{source.replace('-', '_')}",
                    source_endpoint_source="quest-runtime",
                    source_remote_endpoint=f"127.0.0.1:{int(args.port)}",
                    command_id="command.display_stream.start",
                    session_id=str(getattr(args, "session_id", "") or ""),
                    listening_callback=lambda _endpoint: receiver_ready.set(),
                    preview_ffplay=str(args.ffplay) if bool(args.preview) else "",
                    preview_window_title=preview_window_title(args),
                )
            )

        receiver_thread = threading.Thread(target=receive, name="HostessDisplayStreamReceiver")
        receiver_thread.start()
        if not receiver_ready.wait(timeout=5):
            report["issue_codes"].append("hostess.issue.display_stream.receiver_not_armed")
            return finish(report, out, args)

        shell_process: subprocess.Popen[str] | None = None
        shell_result: dict[str, Any] | None = None
        shell_waiter: threading.Thread | None = None
        if source == "media-projection":
            source_started = True
            report["launch"]["source"] = execute(
                runner,
                build_media_projection_start_command(args),
                timeout=15,
            )
        else:
            shell_jar = Path(str(args.shell_jar)).resolve()
            if not shell_jar.is_file():
                report["issue_codes"].append("hostess.issue.display_stream.shell_jar_missing")
                report["launch"]["shell_jar"] = str(shell_jar)
                return finish(report, out, args)
            report["launch"]["mkdir"] = execute(runner, adb_prefix(args) + ["shell", "mkdir", remote_dir], timeout=15)
            if report["launch"]["mkdir"]["returncode"] != 0:
                report["issue_codes"].append("hostess.issue.display_stream.shell_directory_unavailable")
                return finish(report, out, args)
            shell_directory_owned = True
            args._remote_shell_jar = remote_jar
            report["launch"]["push"] = execute(
                runner,
                adb_prefix(args) + ["push", str(shell_jar), remote_jar],
                timeout=60,
            )
            if report["launch"]["push"]["returncode"] != 0:
                report["issue_codes"].append("hostess.issue.display_stream.shell_jar_push_failed")
                return finish(report, out, args)
            source_started = True
            if runner is subprocess.run:
                shell_process, shell_result, shell_waiter = start_text_process(
                    build_shell_mirror_command(args)
                )
                report["launch"]["source"] = shell_result
            else:
                report["launch"]["source"] = execute(
                    runner,
                    build_shell_mirror_command(args),
                    timeout=max(30, int(args.duration_seconds) + 25),
                )

        wait_deadline = (
            None
            if int(args.duration_seconds) <= 0
            else time.monotonic() + float(args.timeout_seconds) + int(args.duration_seconds) + 10
        )
        while receiver_thread.is_alive():
            if is_stop_requested(stop_file):
                report["lifecycle"]["stop_requested"] = True
                if source == "media-projection":
                    report["cleanup"]["stop_service_on_request"] = execute(
                        runner,
                        build_media_projection_stop_command(args),
                        timeout=15,
                    )
                else:
                    raise RuntimeError("Owned nonce control adapter required; no class-wide process kill")
                break
            if wait_deadline is not None and time.monotonic() >= wait_deadline:
                break
            receiver_thread.join(timeout=0.2)

        receiver_thread.join(timeout=float(args.timeout_seconds) + 5)
        if shell_waiter is not None:
            shell_waiter.join(timeout=5)
        if shell_process is not None and shell_process.poll() is None:
            terminate_process(shell_process)
            if shell_waiter is not None:
                shell_waiter.join(timeout=5)
        if receiver_thread.is_alive():
            report["issue_codes"].append("hostess.issue.display_stream.receiver_timeout")
        report["capture"] = receiver_result
        shell_completion_confirmed = (
            source == "shell-mirror"
            and (finite_shell_retired(report["launch"].get("source", {}))
                 or shell_mirror_completed(report["launch"].get("source", {})))
        )
        if shell_completion_confirmed:
            report["launch"]["source"]["completion_marker_confirmed"] = True
        if (
            report["launch"].get("source", {}).get("returncode") not in {0, None}
            and not bool(report["lifecycle"].get("stop_requested"))

        ):
            report["issue_codes"].append("hostess.issue.display_stream.source_launch_failed")
        if receiver_result.get("status") != "pass":
            report["issue_codes"].append("hostess.issue.display_stream.capture_failed")

        viewer = receiver_result.get("viewer", {})
        if bool(args.preview) and preview_failed(viewer):
            report["issue_codes"].append("hostess.issue.display_stream.preview_failed")

        if capture.is_file() and receiver_result.get("status") == "pass":
            elementary = Path(args.h264_out).resolve() if args.h264_out else capture.with_suffix(".h264")
            report["capture"]["h264_extract"] = extract_rmanvid1_h264(capture, elementary)
            if str(args.ffmpeg).strip():
                report["capture"]["decode_check"] = decode_check(
                    runner,
                    str(args.ffmpeg),
                    elementary,
                )
                if report["capture"]["decode_check"]["returncode"] != 0:
                    report["issue_codes"].append("hostess.issue.display_stream.h264_decode_failed")

        report["status"] = "pass" if not report["issue_codes"] else "fail"
        return finish(report, out, args)
    finally:
        if source != "scrcpy":
            cleanup: dict[str, Any] = report.setdefault("cleanup", {})
            if source == "media-projection" and source_started:
                cleanup["stop_service"] = execute(
                    runner,
                    build_media_projection_stop_command(args),
                    timeout=15,
                )
            if shell_directory_owned and not bool(getattr(args, "keep_staged_shell", False)):
                # Finite compatibility cleanup requires genuine completion; uncertain actors retain their bytes.
                if finite_shell_retired(report["launch"].get("source", {})):
                    cleanup["remove_shell_jar"] = execute(runner, adb_prefix(args) + ["shell", "rm", remote_jar], timeout=15)
                    cleanup["remove_shell_directory"] = execute(runner, adb_prefix(args) + ["shell", "rmdir", remote_dir], timeout=15)
                else:
                    cleanup["shell_resources_retained"] = True
            reverse = report.get("transport", {}).get("reverse", {})
            if reverse and reverse.get("created") and not bool(getattr(args, "keep_reverse", False)):
                cleanup["remove_reverse"] = execute(
                    runner,
                    adb_prefix(args) + ["reverse", "--remove", f"tcp:{int(args.port)}"],
                    timeout=15,
                )
            if media_projection_restore_mode is not None:
                cleanup["restore_media_projection_appop"] = execute(
                    runner,
                    adb_prefix(args)
                    + [
                        "shell",
                        "cmd",
                        "appops",
                        "set",
                        DISPLAY_STREAM_PACKAGE,
                        "PROJECT_MEDIA",
                        media_projection_restore_mode,
                    ],
                    timeout=15,
                )
                cleanup["media_projection_appop_readback"] = execute(
                    runner,
                    adb_prefix(args) + ["shell", "cmd", "appops", "get", DISPLAY_STREAM_PACKAGE, "PROJECT_MEDIA"],
                    timeout=15,
                )
            if out.parent.exists():
                out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_scrcpy_source(
    args: Any,
    report: dict[str, Any],
    out: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> int:
    recording = Path(args.capture_out).resolve() if args.capture_out else out.with_suffix(".mkv")
    scrcpy = str(args.scrcpy).strip()
    resolved = shutil.which(scrcpy) if scrcpy else None
    if not resolved and Path(scrcpy).is_file():
        resolved = str(Path(scrcpy).resolve())
    if not resolved:
        report["issue_codes"].append("hostess.issue.display_stream.scrcpy_missing")
        return finish(report, out, args)
    args.scrcpy = resolved
    command = build_scrcpy_command(args, recording)
    if runner is subprocess.run:
        timeout = None if int(args.duration_seconds) <= 0 else max(30, int(args.duration_seconds) + 25)
        report["launch"]["source"] = run_text_process_until_stopped(
            command,
            stop_file=stop_file_path(args),
            timeout_seconds=timeout,
        )
    else:
        report["launch"]["source"] = execute(
            runner,
            command,
            timeout=max(30, int(args.duration_seconds) + 25),
        )
    stopped = bool(report["launch"]["source"].get("stop_requested"))
    report.setdefault("lifecycle", {})["stop_requested"] = stopped
    if report["launch"]["source"]["returncode"] != 0 and not stopped:
        report["issue_codes"].append("hostess.issue.display_stream.scrcpy_failed")
    capture_mode = str(getattr(args, "capture_mode", "full"))
    if capture_mode == "full" and recording.is_file() and recording.stat().st_size > 0:
        report["capture"] = file_evidence(recording)
        if str(args.ffmpeg).strip():
            report["capture"]["decode_check"] = decode_container_check(
                runner,
                str(args.ffmpeg),
                recording,
            )
            if report["capture"]["decode_check"]["returncode"] != 0:
                report["issue_codes"].append("hostess.issue.display_stream.scrcpy_decode_failed")
    elif capture_mode == "full":
        report["issue_codes"].append("hostess.issue.display_stream.scrcpy_recording_missing")
    else:
        report["capture"] = {
            "mode": "preview_only",
            "path": "",
            "bytes": 0,
            "retention_bounded": True,
        }
    report["status"] = "pass" if not report["issue_codes"] else "fail"
    return finish(report, out, args)


def run_adb_screenrecord_source(
    args: Any,
    report: dict[str, Any],
    out: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> int:
    capture = Path(args.capture_out).resolve() if args.capture_out else out.with_suffix(".h264")
    capture.parent.mkdir(parents=True, exist_ok=True)
    before = execute(
        runner,
        adb_prefix(args) + ["shell", "pidof", "screenrecord"],
        timeout=15,
    )
    report["launch"]["screenrecord_process_before"] = before
    before_pids = process_ids(before.get("stdout", ""))
    if before_pids:
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_busy")
        return finish(report, out, args)

    preview = build_raw_h264_preview_sink(args)
    command = build_adb_screenrecord_command(args)
    capture_result = capture_binary_process(
        command,
        capture,
        max_bytes=int(args.max_bytes),
        timeout_seconds=(
            None
            if int(args.duration_seconds) <= 0
            else float(args.timeout_seconds) + int(args.duration_seconds) + 10
        ),
        preview=preview,
        stop_file=stop_file_path(args),
        continue_after_max_bytes=(
            int(args.duration_seconds) <= 0
            and str(getattr(args, "capture_mode", "full")) in {"sample", "none"}
        ),
        retain_capture=str(getattr(args, "capture_mode", "full")) != "none",
    )
    report.setdefault("lifecycle", {})["stop_requested"] = bool(
        capture_result.get("stop_requested")
    )
    report["launch"]["source"] = {
        key: value
        for key, value in capture_result.items()
        if key not in {"bytes_written", "chunk_count", "preview"}
    }
    capture_exists = capture.is_file() and capture.stat().st_size > 0
    report["capture"] = file_evidence(capture) if capture_exists else {"path": str(capture), "bytes": 0}
    report["capture"].update(
        {
            "bytes_written": int(capture_result.get("bytes_written", 0)),
            "chunk_count": int(capture_result.get("chunk_count", 0)),
            "annex_b_start_code": capture_exists and has_annex_b_start_code(capture),
            "preview": capture_result.get("preview", {}),
        }
    )

    if capture_result.get("returncode") != 0 and not bool(capture_result.get("stop_requested")):
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_failed")
    if bool(capture_result.get("timed_out")):
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_timeout")
    if bool(capture_result.get("max_bytes_reached")) and not bool(
        capture_result.get("continued_after_max_bytes")
    ):
        report["issue_codes"].append("hostess.issue.display_stream.capture_max_bytes")
    if not capture_exists and str(getattr(args, "capture_mode", "full")) != "none":
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_capture_missing")
    elif (
        str(getattr(args, "capture_mode", "full")) != "none"
        and not report["capture"]["annex_b_start_code"]
    ):
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_not_annex_b")

    if capture_exists and str(args.ffmpeg).strip():
        report["capture"]["decode_check"] = decode_full_check(
            runner,
            str(args.ffmpeg),
            capture,
        )
        if report["capture"]["decode_check"]["returncode"] != 0:
            report["issue_codes"].append("hostess.issue.display_stream.h264_decode_failed")

    preview_result = report["capture"].get("preview", {})
    if bool(args.preview) and preview_failed(preview_result):
        report["issue_codes"].append("hostess.issue.display_stream.preview_failed")

    after = execute(
        runner,
        adb_prefix(args) + ["shell", "pidof", "screenrecord"],
        timeout=15,
    )
    report["cleanup"]["screenrecord_process_after"] = after
    if process_ids(after.get("stdout", "")) - before_pids:
        # A later PID has no original-actor binding and may belong to another operator.
        report["cleanup"]["screenrecord_retirement_unknown"] = True
        report["issue_codes"].append("hostess.issue.display_stream.screenrecord_cleanup_unknown")

    report["status"] = "pass" if not report["issue_codes"] else "fail"
    return finish(report, out, args)


RawH264PreviewSink = LowLatencyH264PreviewSink


def build_raw_h264_preview_sink(args: Any) -> RawH264PreviewSink:
    return LowLatencyH264PreviewSink(
        str(getattr(args, "ffplay", "") or "")
        if bool(getattr(args, "preview", False))
        else "",
        preview_window_title(args),
    )


def preview_failed(preview_result: dict[str, Any]) -> bool:
    started = bool(
        preview_result.get("started", preview_result.get("ffplay_started", False))
    )
    payload_writes = int(
        preview_result.get(
            "payload_writes",
            preview_result.get("ffplay_payload_writes", 0),
        )
        or 0
    )
    error = str(
        preview_result.get("error", preview_result.get("ffplay_error", "")) or ""
    ).strip()
    if not started or payload_writes <= 0 or error:
        return True
    return bool(
        (
            preview_result.get("returncode") != 0
            and not bool(preview_result.get("terminated_after_eof_timeout"))
        )
        or (os.name == "nt" and not bool(preview_result.get("visible_window_seen")))
    )


def capture_binary_process(
    command: Sequence[str],
    capture: Path,
    *,
    max_bytes: int,
    timeout_seconds: float | None,
    preview: RawH264PreviewSink,
    stop_file: Path | None = None,
    continue_after_max_bytes: bool = False,
    retain_capture: bool = True,
) -> dict[str, Any]:
    started_at = time.monotonic()
    result: dict[str, Any] = {
        "command": [str(part) for part in command],
        "returncode": 127,
        "stderr": "",
        "timed_out": False,
        "max_bytes_reached": False,
        "continued_after_max_bytes": False,
        "stop_requested": False,
        "bytes_written": 0,
        "bytes_received": 0,
        "chunk_count": 0,
    }
    stderr_chunks: list[bytes] = []
    pump_errors: list[str] = []
    try:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=windows_creation_flags(),
        )
    except OSError as error:
        result["stderr"] = str(error)
        result["elapsed_seconds"] = time.monotonic() - started_at
        result["preview"] = preview.close()
        return result

    preview.start()

    def read_stderr() -> None:
        if process.stderr is None:
            return
        while True:
            chunk = process.stderr.read(4096)
            if not chunk:
                return
            stderr_chunks.append(chunk)

    def pump_stdout() -> None:
        if process.stdout is None:
            pump_errors.append("screenrecord stdout pipe was unavailable")
            return
        try:
            with capture.open("wb") as stream:
                while True:
                    chunk = process.stdout.read(64 * 1024)
                    if not chunk:
                        return
                    result["bytes_received"] = int(result["bytes_received"]) + len(chunk)
                    preview.write(chunk)
                    result["chunk_count"] = int(result["chunk_count"]) + 1
                    if not retain_capture:
                        continue
                    remaining = max_bytes - int(result["bytes_written"])
                    if max_bytes <= 0:
                        remaining = len(chunk)
                    if remaining <= 0:
                        result["max_bytes_reached"] = True
                        if continue_after_max_bytes:
                            result["continued_after_max_bytes"] = True
                            continue
                        process.terminate()
                        return
                    accepted = chunk[:remaining]
                    stream.write(accepted)
                    result["bytes_written"] = int(result["bytes_written"]) + len(accepted)
                    if len(accepted) != len(chunk):
                        result["max_bytes_reached"] = True
                        if continue_after_max_bytes:
                            result["continued_after_max_bytes"] = True
                            continue
                        process.terminate()
                        return
        except OSError as error:
            pump_errors.append(str(error))
            process.terminate()

    stderr_thread = threading.Thread(
        target=read_stderr,
        name="HostessAdbScreenrecordStderr",
        daemon=True,
    )
    stdout_thread = threading.Thread(
        target=pump_stdout,
        name="HostessAdbScreenrecordCapture",
        daemon=True,
    )
    stderr_thread.start()
    stdout_thread.start()
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    while process.poll() is None:
        if is_stop_requested(stop_file):
            result["stop_requested"] = True
            process.terminate()
            break
        if deadline is not None and time.monotonic() >= deadline:
            result["timed_out"] = True
            process.terminate()
            break
        time.sleep(0.1)
    try:
        result["returncode"] = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        result["returncode"] = process.wait(timeout=5)
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=2)
    if stdout_thread.is_alive():
        pump_errors.append("screenrecord stdout pump did not stop")
    result["stderr"] = b"".join(stderr_chunks).decode("utf-8", errors="replace")[-8192:]
    if pump_errors:
        result["pump_error"] = "; ".join(pump_errors)
    result["preview"] = preview.close()
    result["elapsed_seconds"] = time.monotonic() - started_at
    return result


def preview_window_title(args: Any) -> str:
    return str(
        getattr(args, "preview_window_title", "")
        or f"Rusty Quest display stream â€” {getattr(args, 'source', 'video')}"
    ).strip()


def stop_file_path(args: Any) -> Path | None:
    value = str(getattr(args, "stop_file", "") or "").strip()
    return Path(value).resolve() if value else None


def is_stop_requested(stop_file: Path | None) -> bool:
    return stop_file is not None and stop_file.is_file()


def request_display_stream_stop(args: Any) -> int:
    stop_file = Path(str(args.stop_file)).resolve()
    out = Path(str(args.out)).resolve()
    stop_file.parent.mkdir(parents=True, exist_ok=True)
    requested_at_unix_ns = time.time_ns()
    stop_file.write_text(
        json.dumps({"requested_at_unix_ns": requested_at_unix_ns}) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema": STOP_REPORT_SCHEMA,
        "status": "pass",
        "stop_file": str(stop_file),
        "requested_at_unix_ns": requested_at_unix_ns,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def start_text_process(
    command: Sequence[str],
) -> tuple[subprocess.Popen[str] | None, dict[str, Any], threading.Thread | None]:
    result: dict[str, Any] = {
        "command": [str(part) for part in command],
        "returncode": None,
        "stdout": "",
        "stderr": "",
    }
    try:
        process = subprocess.Popen(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=windows_creation_flags(),
        )
    except OSError as error:
        result.update({"returncode": 127, "stderr": str(error)})
        return None, result, None

    def wait_for_output() -> None:
        stdout, stderr = process.communicate()
        result.update(
            {
                "returncode": process.returncode,
                "stdout": stdout[-8192:],
                "stderr": stderr[-8192:],
            }
        )

    waiter = threading.Thread(
        target=wait_for_output,
        name="HostessDisplayStreamSourceProcess",
        daemon=True,
    )
    waiter.start()
    return process, result, waiter


def terminate_process(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_text_process_until_stopped(
    command: Sequence[str],
    *,
    stop_file: Path | None,
    timeout_seconds: float | None,
) -> dict[str, Any]:
    process, result, waiter = start_text_process(command)
    result["stop_requested"] = False
    result["timed_out"] = False
    if process is None:
        return result
    deadline = None if timeout_seconds is None else time.monotonic() + timeout_seconds
    while process.poll() is None:
        if is_stop_requested(stop_file):
            result["stop_requested"] = True
            terminate_process(process)
            break
        if deadline is not None and time.monotonic() >= deadline:
            result["timed_out"] = True
            terminate_process(process)
            break
        time.sleep(0.1)
    if waiter is not None:
        waiter.join(timeout=5)
    if result.get("returncode") is None:
        result["returncode"] = process.poll()
    return result


def create_reverse(args: Any, runner: Callable[..., subprocess.CompletedProcess[str]]) -> dict[str, Any]:
    before = execute(runner, adb_prefix(args) + ["reverse", "--list"], timeout=15)
    port = f"tcp:{int(args.port)}"
    existing = any(port in line for line in before["stdout"].splitlines())
    apply = execute(runner, adb_prefix(args) + ["reverse", "--no-rebind", port, port], timeout=15)
    return {"before": before, "apply": apply, "created": not existing and apply["returncode"] == 0}


def extract_rmanvid1_h264(capture: Path, output: Path) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    packet_count = 0
    payload_bytes = 0
    with capture.open("rb") as source, output.open("wb") as target:
        header = source.read(32)
        if len(header) != 32 or header[:8] != RMANVID1_MAGIC:
            raise ValueError("not an RMANVID1 capture")
        metadata_bytes = struct.unpack(">I", header[28:32])[0]
        if len(source.read(metadata_bytes)) != metadata_bytes:
            raise ValueError("truncated RMANVID1 metadata")
        while True:
            packet_header = source.read(32)
            if not packet_header:
                break
            if len(packet_header) != 32:
                raise ValueError("truncated RMANVID1 packet header")
            payload_length = struct.unpack(">I", packet_header[12:16])[0]
            payload = source.read(payload_length)
            if len(payload) != payload_length:
                raise ValueError("truncated RMANVID1 payload")
            target.write(payload)
            packet_count += 1
            payload_bytes += payload_length
    evidence = file_evidence(output)
    evidence.update({"packet_count": packet_count, "payload_bytes": payload_bytes})
    return evidence


def decode_check(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    ffmpeg: str,
    elementary: Path,
) -> dict[str, Any]:
    return execute(
        runner,
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "h264",
            "-i",
            str(elementary),
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        timeout=30,
    )


def decode_container_check(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    ffmpeg: str,
    recording: Path,
) -> dict[str, Any]:
    return execute(
        runner,
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(recording),
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        timeout=30,
    )


def decode_full_check(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    ffmpeg: str,
    elementary: Path,
) -> dict[str, Any]:
    return execute(
        runner,
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "h264",
            "-i",
            str(elementary),
            "-f",
            "null",
            "-",
        ],
        timeout=60,
    )


def appop_mode(output: str) -> str:
    for line in output.splitlines():
        if "PROJECT_MEDIA" not in line:
            continue
        value = line.split(":", 1)[-1].strip().split(";", 1)[0].strip()
        if value in {"allow", "deny", "ignore", "default", "foreground", "ask"}:
            return value
    return "default"


def execute(
    runner: Callable[..., subprocess.CompletedProcess[str]],
    command: Sequence[str],
    *,
    timeout: float,
) -> dict[str, Any]:
    try:
        result = runner(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=windows_creation_flags(),
        )
        return {
            "command": [str(part) for part in command],
            "returncode": int(result.returncode),
            "stdout": str(result.stdout or ""),
            "stderr": str(result.stderr or ""),
        }
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "command": [str(part) for part in command],
            "returncode": 124 if isinstance(error, subprocess.TimeoutExpired) else 127,
            "stdout": "",
            "stderr": str(error),
        }


def adb_prefix(args: Any) -> list[str]:
    return [str(args.adb), "-s", str(args.serial)]


def process_ids(output: str) -> set[int]:
    return {int(token) for token in output.split() if token.isdigit()}


def finite_shell_retired(result: dict[str, Any]) -> bool:
    """Join current finite producer hello/terminal with its genuine host child exit."""
    if result.get("returncode") != 0:
        return False
    try:
        records = [json.loads(line) for line in str(result.get("stdout", "")).splitlines() if line.strip()]
        if len(records) != 2:
            return False
        hello, terminal = records
        identity = {"invocation_id", "generation", "stop_nonce", "pid", "uid", "start_ticks"}
        return (hello.get("schema") == "rusty.quest.display_stream.hello.v1"
                and terminal.get("schema") == "rusty.quest.display_stream.terminal.v1"
                and set(hello) == identity | {"schema"}
                and all(hello.get(k) == terminal.get(k) for k in identity)
                and type(hello["pid"]) is int and hello["pid"] > 0
                and hello["uid"] == 2000 and type(hello["start_ticks"]) is int and hello["start_ticks"] > 0
                and terminal.get("worker_retired") is True and terminal.get("resources_retired") is True
                and terminal.get("state") == "retired" and terminal.get("failure_code") == "NONE"
                and terminal.get("failures") == [])
    except (ValueError, TypeError, AttributeError, KeyError):
        return False


def shell_mirror_completed(result: dict[str, Any]) -> bool:
    """Observe a legacy marker alongside genuine zero exit; never override failure."""
    if result.get("returncode") != 0:
        return False

    for line in str(result.get("stdout", "") or "").splitlines():
        prefix = "RUSTY_QUEST_DISPLAY_STREAM "
        if not line.startswith(prefix):
            continue
        try:
            marker = json.loads(line[len(prefix) :])
        except json.JSONDecodeError:
            continue
        if (
            marker.get("schema") == "rusty.quest.display_stream.shell_marker.v1"
            and marker.get("status") == "complete"
            and not str(marker.get("error") or "")
        ):
            return True
    return False


def has_annex_b_start_code(path: Path) -> bool:
    with path.open("rb") as stream:
        prefix = stream.read(4)
    return prefix.startswith(b"\x00\x00\x01") or prefix.startswith(b"\x00\x00\x00\x01")


def file_evidence(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def finish(report: dict[str, Any], out: Path, args: Any) -> int:
    if report.get("status") != "pass" and not report.get("issue_codes"):
        report.setdefault("issue_codes", []).append("hostess.issue.display_stream.incomplete")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report.get("status") == "pass" or not bool(args.fail_on_error) else 2


__all__ = [
    "REPORT_SCHEMA",
    "STOP_REPORT_SCHEMA",
    "build_adb_screenrecord_command",
    "build_raw_h264_ffplay_command",
    "build_raw_h264_preview_sink",
    "effective_display_stream_max_packets",
    "build_media_projection_start_command",
    "build_shell_mirror_command",
    "build_scrcpy_command",
    "extract_rmanvid1_h264",
    "has_annex_b_start_code",
    "preview_failed",
    "request_display_stream_stop",
    "run_display_stream",
    "shell_mirror_completed",
]
