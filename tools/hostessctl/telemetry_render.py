"""Telemetry rendering and PNG validation helpers for hostessctl."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


MIN_RENDER_WIDTH = 320
MIN_RENDER_HEIGHT = 240
MIN_RENDER_CONTENT_PIXELS = 64


def render_desktop_telemetry(args: argparse.Namespace) -> int:
    if not args.input:
        raise SystemExit("--input is required for desktop telemetry rendering")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise SystemExit("desktop telemetry rendering requires Pillow") from exc

    evidence_path = Path(args.input)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    capture = evidence.get("capture", {})
    runtime_name = capture.get("runtime_input")
    graph_name = capture.get("graph_execution_report")
    runtime_path = evidence_path.with_name(runtime_name) if runtime_name else None
    graph_path = evidence_path.with_name(graph_name) if graph_name else None
    runtime_input = json.loads(runtime_path.read_text(encoding="utf-8")) if runtime_path and runtime_path.exists() else {}
    graph_report = json.loads(graph_path.read_text(encoding="utf-8")) if graph_path and graph_path.exists() else {}

    image = Image.new("RGB", (1080, 760), (248, 248, 246))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw_header(draw, font, evidence, graph_report, args.page)
    if args.page == "raw":
        draw_desktop_raw_page(draw, font, runtime_input, evidence)
    else:
        draw_desktop_module_page(draw, font, graph_report)
    image.save(out)
    sidecar = render_sidecar_path(out)
    write_render_sidecar(
        out,
        sidecar,
        page=args.page,
        target="desktop",
        source_evidence_path=str(evidence_path),
    )
    validate_render_output(
        out,
        sidecar,
        expected_page=args.page,
        source_evidence_path=str(evidence_path),
        target="desktop",
    )
    return 0


def render_sidecar_path(image_path: Path) -> Path:
    return Path(f"{image_path}.json")


def write_render_sidecar(
    image_path: Path,
    sidecar_path: Path,
    *,
    page: str,
    target: str,
    source_evidence_path: str,
) -> None:
    metrics = measure_render_image(image_path)
    sidecar = {
        "$schema": "rusty.hostess.telemetry.render_evidence.v1",
        "status": "pass",
        "rendered_at_utc": datetime.now(UTC).isoformat(),
        "target": target,
        "render_page": page,
        "image_path": str(image_path),
        "source_evidence_path": source_evidence_path,
        "width": metrics["width"],
        "height": metrics["height"],
        "content_pixel_count": metrics["content_pixel_count"],
        "validation": {
            "min_width": MIN_RENDER_WIDTH,
            "min_height": MIN_RENDER_HEIGHT,
            "min_content_pixels": MIN_RENDER_CONTENT_PIXELS,
        },
    }
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True), encoding="utf-8")


def validate_render_output(
    image_path: Path,
    sidecar_path: Path,
    *,
    expected_page: str,
    source_evidence_path: str,
    target: str,
) -> None:
    if not image_path.exists():
        raise SystemExit(f"render output missing: {image_path}")
    if not sidecar_path.exists():
        raise SystemExit(f"render sidecar missing: {sidecar_path}")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    metrics = measure_render_image(image_path)
    errors: list[str] = []
    if sidecar.get("status") != "pass":
        errors.append(f"render sidecar status is {sidecar.get('status')}")
    if sidecar.get("target") != target:
        errors.append(f"render sidecar target is {sidecar.get('target')}, expected {target}")
    if sidecar.get("render_page") != expected_page:
        errors.append(f"render sidecar page is {sidecar.get('render_page')}, expected {expected_page}")
    sidecar_source = str(sidecar.get("source_evidence_path", ""))
    if (
        source_evidence_path
        and sidecar_source not in {source_evidence_path, str(source_evidence_path)}
        and not str(source_evidence_path).endswith(sidecar_source)
    ):
        errors.append("render sidecar source evidence path does not match request")
    for key in ["width", "height", "content_pixel_count"]:
        if int(sidecar.get(key, -1)) != int(metrics[key]):
            errors.append(f"render sidecar {key} does not match PNG")
    if metrics["width"] < MIN_RENDER_WIDTH or metrics["height"] < MIN_RENDER_HEIGHT:
        errors.append(
            f"render is too small: {metrics['width']}x{metrics['height']} "
            f"(minimum {MIN_RENDER_WIDTH}x{MIN_RENDER_HEIGHT})"
        )
    if metrics["content_pixel_count"] < MIN_RENDER_CONTENT_PIXELS:
        errors.append(f"render appears blank: {metrics['content_pixel_count']} content pixels")
    if errors:
        raise SystemExit("; ".join(errors))


def measure_render_image(image_path: Path) -> dict[str, int]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("telemetry render validation requires Pillow") from exc
    import warnings

    with Image.open(image_path) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            pixels = list(rgb.getdata())
    if not pixels:
        return {"width": width, "height": height, "content_pixel_count": 0}
    background = pixels[0]
    content_pixels = sum(1 for pixel in pixels if pixel != background)
    return {"width": width, "height": height, "content_pixel_count": content_pixels}


def draw_header(draw: Any, font: Any, evidence: dict[str, Any], graph_report: dict[str, Any], page: str) -> None:
    draw_panel(draw, 24, 18, 1032, 92)
    selected = evidence.get("capture", {}).get("selected_module_ids", [])
    status = evidence.get("status", "unknown")
    graph_status = graph_report.get("status", "waiting")
    draw.text((42, 36), "Rusty Hostess T", fill=(29, 29, 27), font=font)
    draw.text((42, 58), f"{status} / {evidence.get('host_profile', 'desktop')}", fill=(92, 88, 82), font=font)
    draw.text(
        (42, 80),
        f"{page} / {len(selected)} modules / graph {graph_status} / streams {len(evidence.get('streams', []))}",
        fill=(92, 88, 82),
        font=font,
    )


def draw_desktop_raw_page(draw: Any, font: Any, runtime_input: dict[str, Any], evidence: dict[str, Any]) -> None:
    rr_values = [float(value) for value in runtime_input.get("hr_rr", {}).get("rr_intervals_ms", []) if value is not None]
    acc_values: list[float] = []
    for frame in runtime_input.get("raw_acc", {}).get("frames", []):
        for sample in frame.get("samples_mg", frame.get("samples", [])):
            if isinstance(sample, dict):
                acc_values.append(float(sample.get("z_mg", 0.0)))
    draw_plot(draw, font, "RR", f"{len(rr_values)} intervals", rr_values, (15, 118, 110), 24, 132, 1032, 260)
    acc_rate = runtime_input.get("raw_acc", {}).get("sample_rate_hz", "n/a")
    draw_plot(draw, font, "ACC Z", f"{len(acc_values)} samples / {acc_rate} Hz", acc_values, (79, 76, 71), 24, 418, 1032, 260)
    draw.text((42, 706), f"evidence streams: {', '.join(stream.get('stream_id', '') for stream in evidence.get('streams', [])[:4])}", fill=(92, 88, 82), font=font)


def draw_desktop_module_page(draw: Any, font: Any, graph_report: dict[str, Any]) -> None:
    metrics = [
        ("HRV lnRMSSD", "stream.polar_h10.hrv_window", "ln_rmssd", 5.0, (37, 99, 235)),
        ("RMSSD gain", "stream.polar_h10.rmssd_gain", "ln_rmssd_gain", 2.0, (126, 34, 206)),
        ("Coherence", "stream.polar_h10.coherence", "normalized_score", 1.0, (15, 118, 110)),
        ("Breath vol", "stream.polar_h10.breath_volume", "breath_volume_01", 1.0, (185, 60, 20)),
        ("Breath rate", "stream.polar_h10.breath_dynamics", "breathing_rate_bpm", 30.0, (79, 76, 71)),
        ("HRVB amp", "stream.polar_h10.hrvb_resonance_amplitude", "amplitude_bpm", 10.0, (159, 18, 57)),
    ]
    for index, (label, stream_id, field, scale, color) in enumerate(metrics):
        col = index % 2
        row = index // 2
        left = 24 + col * 522
        top = 132 + row * 170
        stream = find_stream(graph_report, stream_id)
        value = float_value(stream.get(field)) if stream else 0.0
        status = stream.get("status", "missing") if stream else "missing"
        draw_metric_panel(draw, font, label, f"{value:.3f} / {status}", value / scale if scale else 0.0, color, left, top, 510, 142)


def draw_panel(draw: Any, left: int, top: int, width: int, height: int) -> None:
    draw.rounded_rectangle(
        (left, top, left + width, top + height),
        radius=8,
        fill=(255, 255, 255),
        outline=(214, 211, 205),
        width=1,
    )


def draw_plot(
    draw: Any,
    font: Any,
    label: str,
    count: str,
    values: list[float],
    color: tuple[int, int, int],
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    draw_panel(draw, left, top, width, height)
    draw.text((left + 16, top + 16), label, fill=(29, 29, 27), font=font)
    draw.text((left + 16, top + 38), count, fill=(92, 88, 82), font=font)
    plot_left = left + 110
    plot_top = top + 24
    plot_width = width - 140
    plot_height = height - 54
    draw.line((plot_left, plot_top + plot_height // 2, plot_left + plot_width, plot_top + plot_height // 2), fill=(231, 229, 224), width=1)
    if not values:
        draw.text((plot_left + 8, plot_top + plot_height // 2), "waiting", fill=(92, 88, 82), font=font)
        return
    sampled = downsample(values, 800)
    low = min(sampled)
    high = max(sampled)
    if abs(high - low) < 0.0001:
        high += 1.0
        low -= 1.0
    points = []
    for index, value in enumerate(sampled):
        x = plot_left + (index * plot_width / max(len(sampled) - 1, 1))
        y = plot_top + plot_height - ((value - low) / (high - low) * plot_height)
        points.append((x, y))
    if len(points) == 1:
        x, y = points[0]
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=color)
    else:
        draw.line(points, fill=color, width=2)


def draw_metric_panel(
    draw: Any,
    font: Any,
    label: str,
    value: str,
    fraction: float,
    color: tuple[int, int, int],
    left: int,
    top: int,
    width: int,
    height: int,
) -> None:
    draw_panel(draw, left, top, width, height)
    draw.text((left + 16, top + 18), label, fill=(29, 29, 27), font=font)
    draw.text((left + 16, top + 42), value, fill=(92, 88, 82), font=font)
    bar_left = left + 16
    bar_top = top + 88
    bar_width = width - 32
    draw.rounded_rectangle((bar_left, bar_top, bar_left + bar_width, bar_top + 18), radius=4, fill=(231, 229, 224))
    filled = max(0.0, min(1.0, fraction)) * bar_width
    draw.rounded_rectangle((bar_left, bar_top, bar_left + filled, bar_top + 18), radius=4, fill=color)


def downsample(values: list[float], max_points: int) -> list[float]:
    if len(values) <= max_points:
        return values
    step = len(values) / max_points
    return [values[int(index * step)] for index in range(max_points)]


def find_stream(graph_report: dict[str, Any], stream_id: str) -> dict[str, Any] | None:
    for stream in graph_report.get("streams", []):
        if stream.get("stream_id") == stream_id:
            return stream
    return None


def float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def sanitize_remote_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "_" for character in value)
