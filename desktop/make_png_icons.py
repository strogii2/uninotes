"""
Generează iconițele PNG pentru instalarea pe telefon (iOS / Android).
Refolosește desenul din make_icon.py. Doar stdlib — encoder PNG scris de mână.
"""

import struct
import zlib
from pathlib import Path

import make_icon as art

OUT = Path(__file__).resolve().parent.parent / "icons"


def write_png(path: Path, size: int, rows) -> None:
    raw = b"".join(b"\x00" + bytes(row) for row in rows)      # filtru 0 pe fiecare rând

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))  # 8 biți, RGBA
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def render(size: int, rounded: bool):
    """
    rounded=True  → colțuri rotunjite, fundal transparent (iconiță obișnuită)
    rounded=False → pătrat plin până în margini (apple-touch-icon și „maskable”:
                    iOS și Android taie ele forma, deci nu trebuie s-o desenăm noi)
    """
    rows = []
    step = 1.0 / (size * art.SS)
    for y in range(size):
        row = bytearray()
        for x in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(art.SS):
                for sx in range(art.SS):
                    u = (x * art.SS + sx + 0.5) * step
                    v = (y * art.SS + sy + 0.5) * step
                    b, g, r, a = art.sample(u, v)
                    if not rounded and a == 0:          # umplem colțurile tăiate
                        t = max(0.0, min(1.0, u * 0.45 + v * 0.55))
                        r = round(art.C1[0] + (art.C2[0] - art.C1[0]) * t)
                        g = round(art.C1[1] + (art.C2[1] - art.C1[1]) * t)
                        b = round(art.C1[2] + (art.C2[2] - art.C1[2]) * t)
                        a = 255
                    acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += a
            n = art.SS * art.SS
            row += bytes((acc[0] // n, acc[1] // n, acc[2] // n, acc[3] // n))
        rows.append(row)
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plan = [
        ("icon-192.png", 192, True),
        ("icon-512.png", 512, True),
        ("icon-maskable-512.png", 512, False),
        ("apple-touch-icon.png", 180, False),     # iPhone: pătrat plin, iOS rotunjește singur
    ]
    for name, size, rounded in plan:
        path = OUT / name
        write_png(path, size, render(size, rounded))
        print(f"  {name}  {size}x{size}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
