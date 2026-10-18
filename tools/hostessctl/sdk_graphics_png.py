"""Bounded lossless Android PNG readback; RGB/RGBA8, one noninterlaced image.

No color conversion, metadata inflation, image library, fallback or presentation
claim. Preserve the original encoded bytes as the request's pixel witness.
"""
import binascii
import struct
import zlib

MAX_ENCODED = 33554432
MAX_DECODED = 33554432
SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _scanlines(data, expected_size):
    if (type(data) is not bytes or not 57 <= len(data) <= MAX_ENCODED or
            data[:8] != SIGNATURE):
        raise ValueError("bounded_png_required")
    if (type(expected_size) not in (list, tuple) or len(expected_size) != 2 or
            any(type(x) is not int or not 0 < x <= 8192 for x in expected_size)):
        raise ValueError("explicit_png_dimensions_required")
    offset, count, header, ended, idat_ended = 8, 0, None, False, False
    chunks = []
    while offset < len(data):
        count += 1
        if count > 4096 or len(data)-offset < 12:
            raise ValueError("png_chunk_bounds")
        length, kind = struct.unpack_from(">I4s", data, offset)
        if (length > MAX_ENCODED or length > len(data)-offset-12 or
                any(not (65 <= x <= 90 or 97 <= x <= 122) for x in kind) or kind[2] & 32):
            raise ValueError("png_chunk_bounds_or_type")
        payload = memoryview(data)[offset+8:offset+8+length]
        crc = struct.unpack_from(">I", data, offset+8+length)[0]
        if binascii.crc32(payload, binascii.crc32(kind)) & 0xffffffff != crc:
            raise ValueError("png_crc_mismatch")
        offset += 12+length
        if kind == b"IHDR":
            if header is not None or count != 1 or length != 13:
                raise ValueError("png_ihdr_order")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if ([width, height] != list(expected_size) or depth != 8 or color not in (2, 6) or
                    compression != 0 or filtering != 0 or interlace != 0):
                raise ValueError("unsupported_png_layout")
            channels = 3 if color == 2 else 4
            stride = width*channels
            expected = height*(stride+1)
            if expected > MAX_DECODED:
                raise ValueError("png_decoded_budget")
            header = width, height, channels, stride, expected
        elif header is None:
            raise ValueError("png_ihdr_required_first")
        elif kind == b"IDAT":
            if idat_ended or length == 0:
                raise ValueError("png_idat_order")
            chunks.append(payload)
        elif kind == b"IEND":
            if length or not chunks or offset != len(data):
                raise ValueError("png_iend_or_trailing_data")
            ended = True
            break
        else:
            if chunks:
                idat_ended = True
            # Palette, animation, embedded compressed metadata and unknown
            # critical chunks are deliberately outside this narrow transport.
            if kind in (b"acTL", b"fcTL", b"fdAT", b"iCCP", b"zTXt", b"iTXt") or not kind[0] & 32:
                raise ValueError("unsupported_png_chunk")
    if not ended or header is None:
        raise ValueError("png_incomplete")
    width, height, channels, stride, expected = header
    inflater = zlib.decompressobj()
    scan = bytearray()
    try:
        for chunk in chunks:
            scan.extend(inflater.decompress(chunk, expected-len(scan)+1))
            if len(scan) > expected or inflater.unconsumed_tail or inflater.unused_data:
                raise ValueError("png_deflate_surplus")
    except zlib.error as error:
        raise ValueError("png_invalid_deflate") from error
    if len(scan) != expected or not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError("png_incomplete_or_surplus_deflate")
    if any(scan[y*(stride+1)] > 4 for y in range(height)):
        raise ValueError("png_unknown_row_filter")
    return width, height, channels, stride, scan


def _rows(scan, stride, channels, prefix_pixels, rows):
    prefix = prefix_pixels*channels
    previous = bytes(prefix)
    for y in range(rows):
        start = y*(stride+1)
        method = scan[start]
        row = scan[start+1:start+1+prefix]
        if method == 1:
            for i in range(channels, prefix):
                row[i] = (row[i]+row[i-channels]) & 255
        elif method == 2:
            row = bytes((a+b) & 255 for a, b in zip(row, previous))
        elif method in (3, 4):
            for i in range(prefix):
                a = row[i-channels] if i >= channels else 0
                b = previous[i]
                if method == 3:
                    predictor = (a+b)//2
                else:
                    c = previous[i-channels] if i >= channels else 0
                    p = a+b-c
                    pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
                    predictor = a if pa <= pb and pa <= pc else b if pb <= pc else c
                row[i] = (row[i]+predictor) & 255
        previous = row
        yield row


def decode_png(data, expected_size):
    """Full decode oracle, using the same complete container/deflate validation."""
    width, height, channels, stride, scan = _scanlines(data, expected_size)
    pixels = bytearray(height*stride)
    for y, row in enumerate(_rows(scan, stride, channels, width, height)):
        pixels[y*stride:(y+1)*stride] = row
    return width, height, channels, pixels


def decode_png_roi(data, expected_size, rect):
    """Reconstruct exactly the ROI dependency prefix, validate the ENTIRE image.

    Up/average/Paeth require previous-row/left prefixes, never later columns or
    rows. Every filter byte, compressed byte, CRC and final EOF still validates.
    """
    width, height, channels, stride, scan = _scanlines(data, expected_size)
    x, y, rw, rh = rect
    if min(x, y) < 0 or min(rw, rh) < 1 or x+rw > width or y+rh > height:
        raise ValueError("pixel_rect_outside_capture")
    pixels = bytearray(rw*rh*channels)
    for row_number, row in enumerate(_rows(scan, stride, channels, x+rw, y+rh)):
        if row_number >= y:
            offset = (row_number-y)*rw*channels
            pixels[offset:offset+rw*channels] = row[x*channels:(x+rw)*channels]
    return width, height, channels, pixels
