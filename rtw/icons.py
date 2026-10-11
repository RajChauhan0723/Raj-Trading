"""Creates web/icon-192.png and web/icon-512.png with the standard library only (no Pillow needed)."""
import os
import struct
import zlib

BG, BAR, UP = (11, 16, 32), (60, 70, 100), (46, 204, 113)


def _png(size: int) -> bytes:
    rows = []
    bars = [(0.20, 0.55), (0.40, 0.42), (0.60, 0.30), (0.78, 0.16)]      # (x center, top y) rising chart
    w = size * 0.11
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            px = BG
            fx, fy = x / size, y / size
            for i, (cx, top) in enumerate(bars):
                if abs(fx - cx) * size <= w and top <= fy <= 0.80:
                    px = UP if i == len(bars) - 1 else BAR
            row += bytes(px)
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def ensure_icons(web_dir: str) -> list:
    made = []
    for size in (192, 512):
        p = os.path.join(web_dir, f"icon-{size}.png")
        if not os.path.exists(p):
            os.makedirs(web_dir, exist_ok=True)
            open(p, "wb").write(_png(size))
            made.append(p)
    return made
