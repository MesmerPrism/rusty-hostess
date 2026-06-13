"""Makepad PMB provider setup helpers for Hostess control routes."""

from __future__ import annotations

import argparse
import time
from typing import Any, Callable

from tools.hostessctl.makepad_visual_profile import makepad_visual_profile_runtime_properties
from tools.hostessctl.pmb_evidence import (
    PMB_BREATH_SCALE_SMOOTHING_ALPHA,
    PMB_BREATH_SCALE_VOLUME0,
    PMB_BREATH_SCALE_VOLUME1,
    PMB_BREATH_VOLUME_SELECTED_STREAM,
)


RunFunc = Callable[..., Any]


def configure_makepad_breath_feedback_receiver(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    setprops = {
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "false",
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.manifold.breath.feedback.enabled": "true",
        "debug.rusty.manifold.breath.feedback.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rustyquest.makepad.projection.target.breath.controls": "scale",
        "debug.rustyquest.makepad.projection.target.breath.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rustyquest.makepad.projection.target.breath.min.scale": PMB_BREATH_SCALE_VOLUME0,
        "debug.rustyquest.makepad.projection.target.breath.max.scale": PMB_BREATH_SCALE_VOLUME1,
        "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha": PMB_BREATH_SCALE_SMOOTHING_ALPHA,
        "debug.rustyquest.makepad.projection.target.breath.invert": "false",
        "debug.rustyquest.makepad.projection.target.breath.min.quality": "0.0",
        "debug.rustyquest.makepad.projection.target.joystick.controls": "offset-scale",
    }
    for key, value in setprops.items():
        run_func([args.adb, "-s", args.serial, "shell", "setprop", key, value])
    for permission in [
        "android.permission.CAMERA",
        "horizonos.permission.HEADSET_CAMERA",
    ]:
        run_func(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", args.makepad_package, permission],
            allow_failure=True,
        )
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", args.makepad_package], allow_failure=True)
    run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.makepad_activity])
    time.sleep(max(0.0, float(args.makepad_settle_seconds)))


def configure_makepad_physical_pmb_provider(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
) -> None:
    setprops = {
        **makepad_visual_profile_runtime_properties(),
        "debug.rusty.manifold.pose.publish.enabled": "true",
        "debug.rusty.manifold.pose.stream": "stream.motion.object_pose",
        "debug.rusty.manifold.pose.source": "provider.makepad.controller_pose",
        "debug.rusty.manifold.pose.controller": args.makepad_pose_controller,
        "debug.rusty.manifold.pose.kind": args.makepad_pose_kind,
        "debug.rusty.manifold.pose.sample.hz": str(args.makepad_pose_sample_hz),
        "debug.rusty.manifold.broker.host": "127.0.0.1",
        "debug.rusty.manifold.broker.port": str(args.broker_port),
        "debug.rusty.manifold.breath.feedback.enabled": "true",
        "debug.rusty.manifold.breath.feedback.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rusty.manifold.breath.feedback.receiver": "app.makepad_camera_shell.breath_feedback",
        "debug.rusty.manifold.breath.feedback.connect.timeout.ms": "5000",
        "debug.rustyquest.makepad.projection.target.breath.controls": "scale",
        "debug.rustyquest.makepad.projection.target.breath.stream": PMB_BREATH_VOLUME_SELECTED_STREAM,
        "debug.rustyquest.makepad.projection.target.breath.min.scale": PMB_BREATH_SCALE_VOLUME0,
        "debug.rustyquest.makepad.projection.target.breath.max.scale": PMB_BREATH_SCALE_VOLUME1,
        "debug.rustyquest.makepad.projection.target.breath.smoothing.alpha": PMB_BREATH_SCALE_SMOOTHING_ALPHA,
        "debug.rustyquest.makepad.projection.target.breath.invert": "false",
        "debug.rustyquest.makepad.projection.target.breath.min.quality": "0.0",
        "debug.rustyquest.makepad.projection.target.joystick.controls": "offset-scale",
    }
    for key, value in setprops.items():
        run_func([args.adb, "-s", args.serial, "shell", "setprop", key, value])
    for permission in [
        "android.permission.CAMERA",
        "horizonos.permission.HEADSET_CAMERA",
    ]:
        run_func(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", args.makepad_package, permission],
            allow_failure=True,
        )
    run_func([args.adb, "-s", args.serial, "shell", "am", "force-stop", args.makepad_package], allow_failure=True)
    run_func([args.adb, "-s", args.serial, "shell", "am", "start", "-n", args.makepad_activity])
    time.sleep(max(0.0, float(args.makepad_settle_seconds)))


def grant_broker_runtime_permissions(
    args: argparse.Namespace,
    *,
    run_func: RunFunc,
    selected_broker_package_func: Callable[[argparse.Namespace], str],
) -> None:
    for permission in [
        "android.permission.BLUETOOTH_SCAN",
        "android.permission.BLUETOOTH_CONNECT",
    ]:
        run_func(
            [args.adb, "-s", args.serial, "shell", "pm", "grant", selected_broker_package_func(args), permission],
            allow_failure=True,
        )
