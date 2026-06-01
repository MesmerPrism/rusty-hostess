from __future__ import annotations

import argparse
import ctypes
import json
import sys
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DWMWA_EXTENDED_FRAME_BOUNDS = 9
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
BI_RGB = 0


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]


user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
user32.PrintWindow.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

dwmapi.DwmGetWindowAttribute.argtypes = [
    wintypes.HWND,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
]
dwmapi.DwmGetWindowAttribute.restype = ctypes.c_long

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.POINTER(BITMAPINFO),
    wintypes.UINT,
]
gdi32.GetDIBits.restype = ctypes.c_int


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a Windows top-level window without foregrounding it."
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--hwnd", type=lambda value: int(value, 0))
    target.add_argument("--title-contains")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sidecar")
    parser.add_argument("--target")
    parser.add_argument("--serial")
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("capture_window_printwindow requires Pillow") from exc

    hwnd = args.hwnd or find_window_by_title(args.title_contains)
    if not hwnd:
        raise SystemExit(f"window not found: {args.title_contains!r}")
    title = window_title(hwnd)
    rect = window_bounds(hwnd)
    width = rect.right - rect.left
    height = rect.bottom - rect.top
    if width <= 0 or height <= 0:
        raise SystemExit(f"window has invalid bounds: {width}x{height}")

    pixels = print_window_bgrx(hwnd, width, height)
    image = Image.frombuffer("RGB", (width, height), pixels, "raw", "BGRX", 0, 1)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)

    sidecar = Path(args.sidecar) if args.sidecar else Path(f"{out}.json")
    sidecar.write_text(
        json.dumps(
            {
                "$schema": "rusty.hostess.window_capture.v1",
                "status": "pass",
                "captured_at_utc": datetime.now(UTC).isoformat(),
                "capture_method": "win32.PrintWindow.PW_RENDERFULLCONTENT",
                "foreground_required": False,
                "screen_occlusion_required_clear": False,
                "target": args.target,
                "serial": args.serial,
                "hwnd": hwnd,
                "window_title": title,
                "image_path": str(out),
                "width": width,
                "height": height,
                "content_pixel_count": content_pixel_count(image),
                "note": args.note,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(str(out))
    return 0


def find_window_by_title(title_part: str) -> int:
    needle = title_part.lower()
    matches: list[int] = []

    @EnumWindowsProc
    def enum_proc(hwnd: int, _lparam: int) -> bool:
        if user32.IsWindowVisible(hwnd):
            title = window_title(hwnd)
            if needle in title.lower():
                matches.append(hwnd)
        return True

    if not user32.EnumWindows(enum_proc, 0):
        raise_windows_error("EnumWindows")
    return matches[0] if matches else 0


def window_title(hwnd: int) -> str:
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)
    return buffer.value


def window_bounds(hwnd: int) -> RECT:
    rect = RECT()
    hr = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(rect),
        ctypes.sizeof(rect),
    )
    if hr == 0:
        return rect
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise_windows_error("GetWindowRect")
    return rect


def print_window_bgrx(hwnd: int, width: int, height: int) -> bytes:
    window_dc = user32.GetDC(hwnd)
    if not window_dc:
        raise_windows_error("GetDC")
    memory_dc = gdi32.CreateCompatibleDC(window_dc)
    bitmap = gdi32.CreateCompatibleBitmap(window_dc, width, height)
    old_object = None
    try:
        if not memory_dc:
            raise_windows_error("CreateCompatibleDC")
        if not bitmap:
            raise_windows_error("CreateCompatibleBitmap")
        old_object = gdi32.SelectObject(memory_dc, bitmap)
        if not user32.PrintWindow(hwnd, memory_dc, PW_RENDERFULLCONTENT):
            raise_windows_error("PrintWindow")

        info = BITMAPINFO()
        info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        info.bmiHeader.biWidth = width
        info.bmiHeader.biHeight = -height
        info.bmiHeader.biPlanes = 1
        info.bmiHeader.biBitCount = 32
        info.bmiHeader.biCompression = BI_RGB
        raw = ctypes.create_string_buffer(width * height * 4)
        rows = gdi32.GetDIBits(
            memory_dc,
            bitmap,
            0,
            height,
            raw,
            ctypes.byref(info),
            DIB_RGB_COLORS,
        )
        if rows != height:
            raise_windows_error("GetDIBits")
        return raw.raw
    finally:
        if old_object:
            gdi32.SelectObject(memory_dc, old_object)
        if bitmap:
            gdi32.DeleteObject(bitmap)
        if memory_dc:
            gdi32.DeleteDC(memory_dc)
        if window_dc:
            user32.ReleaseDC(hwnd, window_dc)


def content_pixel_count(image: Any) -> int:
    rgb = image.convert("RGB")
    data = rgb.tobytes()
    if not data:
        return 0
    background = data[:3]
    return sum(
        1
        for index in range(0, len(data), 3)
        if data[index : index + 3] != background
    )


def raise_windows_error(operation: str) -> None:
    error = ctypes.get_last_error()
    raise OSError(error, f"{operation} failed", ctypes.FormatError(error))


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("capture_window_printwindow is Windows-only")
    raise SystemExit(main())
