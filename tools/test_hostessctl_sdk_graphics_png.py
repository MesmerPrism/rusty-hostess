"""Independent neutral PNG encoder plus strict full/ROI/raw equivalence tests."""
import binascii
import struct
import unittest
from unittest.mock import patch
import zlib

from tools.hostessctl.sdk_graphics_png import decode_png, decode_png_roi, SIGNATURE
from tools.hostessctl.sdk_graphics_pixels import check_pixels, check_png_pixels


def chunk(kind, payload):
    return struct.pack(">I", len(payload))+kind+payload+struct.pack(">I", binascii.crc32(kind+payload) & 0xffffffff)


def encode(pixels, width, height, channels, method, *, split=False, scan_override=None):
    stride = width*channels
    scan, previous = bytearray(), bytes(stride)
    for y in range(height):
        row = pixels[y*stride:(y+1)*stride]
        scan.append(method)
        for i, value in enumerate(row):
            a, b, c = row[i-channels] if i >= channels else 0, previous[i], previous[i-channels] if i >= channels else 0
            p = a+b-c
            distances = [abs(p-a), abs(p-b), abs(p-c)]
            prediction = [0, a, b, (a+b)//2, (a, b, c)[distances.index(min(distances))]][method]
            scan.append((value-prediction) & 255)
        previous = row
    compressed = zlib.compress(bytes(scan if scan_override is None else scan_override))
    pieces = [compressed[:3], compressed[3:]] if split else [compressed]
    header = struct.pack(">IIBBBBB", width, height, 8, 2 if channels == 3 else 6, 0, 0, 0)
    return SIGNATURE+chunk(b"IHDR", header)+b"".join(chunk(b"IDAT", p) for p in pieces)+chunk(b"IEND", b"")


class PngTests(unittest.TestCase):
    def test_filters_rgb_rgba_split_idat_and_every_edge_roi_exactly_match_neutral_bytes(self):
        width, height = 17, 11
        for channels in (3, 4):
            pixels = bytes((i*39+i//13) % 256 for i in range(width*height*channels))
            for method in range(5):
                for split in (False, True):
                    with self.subTest(channels=channels, method=method, split=split):
                        encoded = encode(pixels, width, height, channels, method, split=split)
                        self.assertEqual(decode_png(encoded, [width, height])[3], pixels)
                        for rect in ([0, 0, 1, 1], [16, 10, 1, 1], [0, 3, 17, 4], [4, 0, 5, 11], [0, 0, 17, 11]):
                            x, y, rw, rh = rect
                            expected = b"".join(pixels[(r*width+x)*channels:(r*width+x+rw)*channels] for r in range(y, y+rh))
                            self.assertEqual(decode_png_roi(encoded, [width, height], rect)[3], expected)

    def test_neutral_png_and_android_raw_predicate_equivalence(self):
        predicate = {"rect": [3, 2, 8, 8], "rgb": [19, 87, 203], "tolerance": 0, "minimum_matches": 64}
        for channels in (3, 4):
            pixels = bytes([19, 87, 203]+([129] if channels == 4 else []))*12*12
            raw = struct.pack("<III", 12, 12, 1 if channels == 4 else 3)+pixels
            for method in range(5):
                png_result = check_png_pixels(encode(pixels, 12, 12, channels, method), predicate, [12, 12])
                self.assertEqual({k:v for k,v in png_result.items() if k != "source_encoding"}, check_pixels(raw, predicate))

    def test_corruption_truncation_order_multiple_images_and_layout_rejected(self):
        good = encode(bytes([1, 2, 3])*4, 2, 2, 3, 0)
        ihdr, idat, end = good[8:33], good[33:-12], good[-12:]
        invalid = [good[:-1], good+b"extra", good+good, good[:40]+bytes([good[40]^1])+good[41:],
                   SIGNATURE+idat+ihdr+end, SIGNATURE+ihdr+ihdr+idat+end,
                   SIGNATURE+ihdr+idat+chunk(b"tEXt", b"a\0b")+idat+end]
        for kind in (b"acTL", b"fcTL", b"fdAT", b"iCCP", b"zTXt", b"iTXt", b"ABCD"):
            invalid.append(SIGNATURE+ihdr+chunk(kind, b"bad")+idat+end)
        for field, value in ((2, 16), (3, 3), (4, 1), (5, 1), (6, 1)):
            header = list(struct.unpack(">IIBBBBB", good[16:29]))
            header[field] = value
            invalid.append(SIGNATURE+chunk(b"IHDR", struct.pack(">IIBBBBB", *header))+idat+end)
        for data in invalid:
            with self.subTest(data=data[:40]), self.assertRaises(ValueError):
                decode_png(data, [2, 2])
        with self.assertRaises(ValueError):
            decode_png(good, [1, 2])

    def test_complete_deflate_and_all_filter_bytes_validated_after_roi(self):
        header = chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 2, 0, 0, 0))
        scan = bytes(14)
        streams = [zlib.compress(scan[:-1]), zlib.compress(scan+b"x"), zlib.compress(scan)[:-1],
                   zlib.compress(scan)+b"extra", zlib.compress(scan)+zlib.compress(scan),
                   zlib.compress(scan[:7]+b"\5"+scan[8:])]
        for compressed in streams:
            with self.subTest(compressed=compressed), self.assertRaises(ValueError):
                decode_png_roi(SIGNATURE+header+chunk(b"IDAT", compressed)+chunk(b"IEND", b""), [2, 2], [0, 0, 1, 1])

    def test_encoded_and_decoded_budgets_enforced_before_inflate(self):
        good = encode(bytes(12), 2, 2, 3, 0)
        with patch("tools.hostessctl.sdk_graphics_png.MAX_ENCODED", len(good)-1), self.assertRaises(ValueError):
            decode_png(good, [2, 2])
        with patch("tools.hostessctl.sdk_graphics_png.MAX_DECODED", 13), self.assertRaises(ValueError):
            decode_png(good, [2, 2])


if __name__ == "__main__":
    unittest.main()
