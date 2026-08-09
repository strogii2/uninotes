"""
Generează desktop/icon.ico — pătrat albastru rotunjit cu trei linii albe,
la fel ca iconița din fila browserului. Doar stdlib, fără Pillow.
"""

import struct
from pathlib import Path

OUT = Path(__file__).resolve().parent / "icon.ico"
SIZES = [16, 32, 48, 64, 128, 256]
SS = 4                                   # supraeșantionare, pentru margini netede

C1 = (0x25, 0x63, 0xEB)                  # albastru principal
C2 = (0x3B, 0x82, 0xF6)                  # albastru secundar (colțul opus)


def rounded_rect_sdf(px, py, cx, cy, hw, hh, r):
    """Distanță cu semn față de un dreptunghi rotunjit; negativ = în interior."""
    dx = abs(px - cx) - (hw - r)
    dy = abs(py - cy) - (hh - r)
    ox, oy = max(dx, 0.0), max(dy, 0.0)
    return (ox * ox + oy * oy) ** 0.5 + min(max(dx, dy), 0.0) - r


BARS = [                                 # (y_centru, x_stânga, x_dreapta) în 0..1
    (0.315, 0.235, 0.765),
    (0.500, 0.235, 0.765),
    (0.685, 0.235, 0.575),
]
BAR_H = 0.088


def sample(u, v):
    """Culoare (B, G, R, A) pentru un punct din pătratul unitate."""
    if rounded_rect_sdf(u, v, 0.5, 0.5, 0.5, 0.5, 0.215) > 0:
        return (0, 0, 0, 0)

    t = max(0.0, min(1.0, (u * 0.45 + v * 0.55)))
    r = round(C1[0] + (C2[0] - C1[0]) * t)
    g = round(C1[1] + (C2[1] - C1[1]) * t)
    b = round(C1[2] + (C2[2] - C1[2]) * t)

    for cy, x0, x1 in BARS:
        hw = (x1 - x0) / 2
        if rounded_rect_sdf(u, v, x0 + hw, cy, hw, BAR_H / 2, BAR_H / 2) <= 0:
            return (255, 255, 255, 255)
    return (b, g, r, 255)


def render(size):
    """Pixeli BGRA, rând cu rând de sus în jos."""
    rows = []
    step = 1.0 / (size * SS)
    for y in range(size):
        row = []
        for x in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SS):
                for sx in range(SS):
                    u = (x * SS + sx + 0.5) * step
                    v = (y * SS + sy + 0.5) * step
                    px = sample(u, v)
                    for i in range(4):
                        acc[i] += px[i]
            n = SS * SS
            row.append(tuple(a // n for a in acc))
        rows.append(row)
    return rows


def ico_image(rows, size):
    """BITMAPINFOHEADER + pixeli XOR (jos-sus) + mască AND."""
    header = struct.pack("<IiiHHIIiiII", 40, size, size * 2, 1, 32, 0, size * size * 4, 0, 0, 0, 0)
    xor = bytearray()
    for y in range(size - 1, -1, -1):
        for b, g, r, a in rows[y]:
            xor += bytes((b, g, r, a))
    mask_row = ((size + 31) // 32) * 4          # rânduri aliniate la 4 octeți
    and_mask = bytes(mask_row * size)           # totul opac; transparența vine din alfa
    return header + bytes(xor) + and_mask


def main():
    images = [(s, ico_image(render(s), s)) for s in SIZES]
    out = bytearray(struct.pack("<HHH", 0, 1, len(images)))
    offset = 6 + 16 * len(images)
    for size, data in images:
        dim = 0 if size >= 256 else size
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in images:
        out += data
    OUT.write_bytes(out)
    print(f"scris {OUT} ({len(out)} octeti, {len(images)} rezolutii)")


if __name__ == "__main__":
    main()
