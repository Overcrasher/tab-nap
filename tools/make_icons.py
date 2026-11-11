#!/usr/bin/env python3
"""Generates icons/icon{16,32,48,128}.png: a moon-yellow crescent resting on a lavender browser window with a raised tab on a rounded indigo tile.
Stdlib only (zlib + struct). Run from anywhere: python3 tools/make_icons.py"""
import os, struct, zlib, math

SS = 5  # supersampling per axis


def lerp(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def rrect(x, y, x0, y0, x1, y1, r):
    cx = min(max(x, x0 + r), x1 - r)
    cy = min(max(y, y0 + r), y1 - r)
    return x0 <= x <= x1 and y0 <= y <= y1 and (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def circle(x, y, cx, cy, r):
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def ellipse(x, y, cx, cy, rx, ry, ang):
    c, s = math.cos(ang), math.sin(ang)
    dx, dy = x - cx, y - cy
    u, v = dx * c + dy * s, -dx * s + dy * c
    return (u / rx) ** 2 + (v / ry) ** 2 <= 1


def seg_dist(x, y, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    t = ((x - ax) * vx + (y - ay) * vy) / (vx * vx + vy * vy)
    t = min(max(t, 0), 1)
    return math.hypot(x - ax - t * vx, y - ay - t * vy)


def stroke(x, y, pts, w):
    return any(seg_dist(x, y, *pts[i], *pts[i + 1]) <= w / 2 for i in range(len(pts) - 1))


def bez(p0, p1, p2, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
    return out


def render(size, bg_top, bg_bot, shapes):
    """shapes: ordered list of (fn(x,y,size)->bool, color or fn(y)->color). Later shapes paint over earlier ones."""
    rows = []
    n = SS * SS
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            acc = [0.0, 0.0, 0.0]
            cov = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = (px + (sx + 0.5) / SS) / size
                    y = (py + (sy + 0.5) / SS) / size
                    if not rrect(x, y, 0, 0, 1, 1, 0.22):
                        continue
                    cov += 1
                    col = lerp(bg_top, bg_bot, y)
                    for fn, c in shapes:
                        if fn(x, y, size):
                            col = c(y) if callable(c) else c
                    for i in range(3):
                        acc[i] += col[i]
            if cov == 0:
                row += bytes([0, 0, 0, 0])
            else:
                row += bytes([round(acc[i] / cov) for i in range(3)] + [round(255 * cov / n)])
        rows.append(bytes(row))
    return b"".join(rows)


def png(size, bg_top, bg_bot, shapes):
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(render(size, bg_top, bg_bot, shapes), 9)) + chunk(b"IEND", b""))


def write_all(bg_top, bg_bot, shapes):
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "icons")
    os.makedirs(out, exist_ok=True)
    for s in (16, 32, 48, 128):
        with open(os.path.join(out, "icon%d.png" % s), "wb") as f:
            f.write(png(s, bg_top, bg_bot, shapes))
        print("wrote icon%d.png" % s)

BG_TOP = (66, 62, 140)
BG_BOT = (38, 35, 104)
LAV = (190, 200, 255)
MOON = (253, 230, 138)


LAV2 = (132, 144, 226)
LAV = (226, 231, 255)
WT, WB = 0.42, 0.88   # window top / bottom


def window(x, y, s):
    return rrect(x, y, 0.12, WT, 0.88, WB, 0.07)


def tabshape(x, y, s):
    # Chrome-style tab: slanted sides, rounded top corners, joined to the toolbar band
    y0, y1 = WT + 0.04, WT + 0.17
    if y0 <= y <= y1:
        t = (y - y0) / (y1 - y0)
        if not (0.19 - 0.05 * t <= x <= 0.52 + 0.05 * t):
            return False
        return y > y0 + 0.05 or rrect(x, y, 0.185, y0, 0.525, y0 + 0.1, 0.05)
    return False


def toolbar(x, y, s):
    # toolbar band + page area, same light colour as the active tab; keeps the window's rounded bottom
    return WT + 0.16 <= y <= WB and rrect(x, y, 0.12, WT, 0.88, WB, 0.07)


def omnibox(x, y, s):
    return s >= 32 and rrect(x, y, 0.24, WT + 0.185, 0.76, WT + 0.23, 0.022)


def moon(x, y, s):
    k = 0.0 if s >= 32 else 0.03   # thicker crescent at 16 px
    return circle(x, y, 0.69, 0.27, 0.19) and not circle(x, y, 0.77 + k, 0.215 - k, 0.165 - k)


write_all(BG_TOP, BG_BOT, [(window, LAV2), (tabshape, LAV), (toolbar, LAV), (omnibox, LAV2), (moon, MOON)])
