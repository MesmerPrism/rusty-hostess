"""Narrow raw Android display pixel predicate; no stereo or GPU attribution."""
import struct
from tools.hostessctl.sdk_graphics_png import decode_png_roi


def validate_predicate(predicate):
    if type(predicate) is not dict or set(predicate) != {"rect", "rgb", "tolerance", "minimum_matches"}:
        raise ValueError("closed_pixel_predicate_required")
    rect, rgb = predicate["rect"], predicate["rgb"]
    if (type(rect) is not list or len(rect) != 4 or type(rgb) is not list or len(rgb) != 3 or
            any(type(x) is not int for x in rect+rgb) or min(rect) < 0 or min(rect[2:]) < 1 or
            any(not 0 <= x <= 255 for x in rgb) or type(predicate["tolerance"]) is not int or
            not 0 <= predicate["tolerance"] <= 16 or type(predicate["minimum_matches"]) is not int or
            not 64 <= predicate["minimum_matches"] <= rect[2]*rect[3]):
        raise ValueError("bounded_pixel_predicate_required")
    if rect[0]+rect[2] > 8192 or rect[1]+rect[3] > 8192 or rect[2]*rect[3] > 4194304:
        raise ValueError("bounded_pixel_rect_required")
    return rect, rgb


def check_pixels(raw, predicate):
    if not 12 <= len(raw) <= 33554432:
        raise ValueError("bounded_android_raw_capture_required")
    width, height, pixel_format = struct.unpack_from("<III", raw)
    if not 0 < width <= 8192 or not 0 < height <= 8192 or pixel_format not in (1, 3):
        raise ValueError("unsupported_android_capture_format")
    channels = 4 if pixel_format == 1 else 3
    header = len(raw)-width*height*channels
    if header not in (12, 16):
        raise ValueError("android_capture_layout_mismatch")
    return check_rgb(memoryview(raw)[header:], width, height, channels, predicate)


def check_png_pixels(encoded, predicate, expected_size):
    rect, _ = validate_predicate(predicate)
    width, height, channels, pixels = decode_png_roi(encoded, expected_size, rect)
    result = check_rgb(pixels, rect[2], rect[3], channels,
                       {**predicate, "rect": [0, 0, rect[2], rect[3]]})
    result.update(width=width, height=height)
    result["source_encoding"] = "android-png"
    return result


def check_rgb(pixels, width, height, channels, predicate):
    rect, rgb = validate_predicate(predicate)
    x, y, rw, rh = rect
    if x+rw > width or y+rh > height:
        raise ValueError("pixel_rect_outside_capture")
    matches = 0
    for row in range(y, y+rh):
        for column in range(x, x+rw):
            offset = (row*width+column)*channels
            matches += all(abs(pixels[offset+i]-rgb[i]) <= predicate["tolerance"] for i in range(3))
    return {"matches": matches, "matched": matches >= predicate["minimum_matches"],
            "width": width, "height": height, "scope": "android-display-readback-no-eye-attribution"}
