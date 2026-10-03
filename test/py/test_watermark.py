"""Regression checks for the watermark (generator/watermark.py), for the coderprint.py given as the only argument.
The watermark's outline comes from a secret (CARDS_MARK_DATA), so its parsing is checked first and hardest. One line
per check; exit 1 on any failure.

  outline   mark_outline turns M, L, H, V and Z (absolute and relative, implicit lines after a move, a new
            subpath after Z) into the exact closed polygons, drops pieces of fewer than three points, and refuses
            with its own message: data over MARK_MAX_CHARS, other commands (C, Q, A, ...), stray characters,
            tabs and newlines, comma runs, data not starting with M, missing or misplaced numbers, numbers or
            relative sums past a million, infinities, and an outline that is empty, flat or too thin
  hexrgb    a #rrggbb color as its three bytes
  png       png() writes a valid PNG whose decoded pixels equal its input, at 1, 2, 4 and 8 bit palettes and in
            RGB, with correct CRCs and the bit depth the color count needs
  flat      flattened_mark draws nothing without polygons; otherwise one <image> inside MARK_LIMIT whose PNG
            is the right size, fills the mark's inside, leaves an even-odd hole and the outside as background
            (with the grid stroke on its rows and columns), and scales a tall outline down to fit the corners
  word      load_wordmark reads design/wordmark.svg, is None without design/, and stops on a wordmark that is
            missing or unreadable; wordmark() draws nothing for None, places the letters by their frame, and
            glows only in a nite
"""
import base64
import importlib.util
import os
import re
import shutil
import struct
import sys
import tempfile
import zlib

spec = importlib.util.spec_from_file_location("cp_under_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if callable(ok):
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  %s" % (detail,)), flush=True)


def outline(d):
    """mark_outline's polygons, or the message it refused with."""
    try:
        return cp.mark_outline(d)
    except RuntimeError as e:
        return str(e)


# ---------------------------------------------------------------- outline: accepted

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
CASES = [
    ("absolute L", "M0 0 L10 0 L10 10 L0 10 Z", [SQUARE]),
    ("absolute H V", "M0 0 H10 V10 H0 Z", [SQUARE]),
    ("relative l", "m0 0 l10 0 l0 10 l-10 0 z", [SQUARE]),
    ("relative h v", "M0 0 h10 v10 h-10 z", [SQUARE]),
    ("implicit lines after M", "M0 0 10 0 10 10 0 10Z", [SQUARE]),
    ("implicit lines after m are relative", "m1 1 2 0 0 2 z", [[(1.0, 1.0), (3.0, 1.0), (3.0, 3.0)]]),
    ("repeated pairs after L", "M0 0 L10 0 10 10 0 10 Z", [SQUARE]),
    ("commas and no spaces", "M0,0L10,0L10,10L0,10Z", [SQUARE]),
    ("packed numbers", "M.5.5L10.5.5L10.5-9.5Z", [[(0.5, 0.5), (10.5, 0.5), (10.5, -9.5)]]),
    ("exponents and signs", "M+1e1 0 L2E1 0 L20 1.5e+1 Z", [[(10.0, 0.0), (20.0, 0.0), (20.0, 15.0)]]),
    ("Z returns the pen to the start", "M0 0 L10 0 L10 10 Z l5 5 l5 0 l0 5",
     [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], [(0.0, 0.0), (5.0, 5.0), (10.0, 5.0), (10.0, 10.0)]]),
    ("a second M starts a second polygon", "M0 0 L10 0 L10 10 M20 20 L30 20 L30 30",
     [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], [(20.0, 20.0), (30.0, 20.0), (30.0, 30.0)]]),
    ("relative m after a shape is from the last point", "M0 0 L10 0 L10 10 m5 0 l1 0 l0 1",
     [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)], [(15.0, 10.0), (16.0, 10.0), (16.0, 11.0)]]),
    ("pieces of fewer than three points are dropped", "M0 0 L5 5 M0 0 L10 0 L10 10 Z M3 3 Z",
     [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]]),
    ("a double Z adds nothing", "M0 0 L10 0 L10 10 Z Z", [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]]),
    ("lowercase z then absolute L", "M0 0 L4 0 L4 4 z L0 4 L-4 4",
     [[(0.0, 0.0), (4.0, 0.0), (4.0, 4.0)], [(0.0, 0.0), (0.0, 4.0), (-4.0, 4.0)]]),
    ("a million exactly is allowed", "M-1000000 0 L1000000 0 L0 1000000 Z",
     [[(-1e6, 0.0), (1e6, 0.0), (0.0, 1e6)]]),
    ("leading and trailing spaces", "  M0 0 L10 0 L10 10  ", [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]]),
]
for name, d, want in CASES:
    got = outline(d)
    check("outline accepts: %s" % name, got == want, got)

check("outline: data exactly MARK_MAX_CHARS long is read",
      lambda: cp.mark_outline("M0 0 L10 0 L10 10 Z".ljust(cp.MARK_MAX_CHARS)) == [[(0.0, 0.0), (10.0, 0.0),
                                                                                     (10.0, 10.0)]])

# ---------------------------------------------------------------- outline: refused

SYNTAX = "the mark must be SVG path data with straight segments only (M, L, H, V, Z)"
START = "the mark's path data must start with M"
MALFORMED = "the mark's path data is malformed"
RANGE = "the mark's numbers must lie within plus or minus a million"
NONE = "the mark has no usable outline"
LONG = "the mark is longer than 48 KB, more than a secret can hold"
REFUSED = [
    ("a diagonal line", "M0 0 L10 10 L20 20 Z", NONE),
    ("only flat diagonal pieces", "M0 0 L1 1 L2 2 Z M5 5 L6 6 L7 7 Z", NONE),
    ("one char over MARK_MAX_CHARS", "M0 0 L10 0 L10 10 Z".ljust(cp.MARK_MAX_CHARS + 1), LONG),
    ("length is checked before anything else", "C" * (cp.MARK_MAX_CHARS + 1), LONG),
    ("empty", "", SYNTAX),
    ("cubic C", "M0 0 C1 1 2 2 3 3 Z", SYNTAX),
    ("smooth S", "M0 0 S1 1 2 2 Z", SYNTAX),
    ("quadratic Q", "M0 0 Q1 1 2 2 Z", SYNTAX),
    ("T", "M0 0 T1 1 Z", SYNTAX),
    ("arc A", "M0 0 A1 1 0 0 1 2 2 Z", SYNTAX),
    ("a tag", '<path d="M0 0"/>', SYNTAX),
    ("a newline", "M0 0\nL10 0 L10 10 Z", SYNTAX),
    ("a tab", "M0 0\tL10 0 L10 10 Z", SYNTAX),
    ("non-ASCII digit", "M١ 0 L10 0 L10 10 Z", SYNTAX),
    ("a stray e", "M0 0 e L10 0 L10 10", SYNTAX),
    ("a dangling exponent", "M0 0 L1e L10 10", SYNTAX),
    ("a double sign", "M0 0 L--1 0 L10 10", SYNTAX),
    ("a lone dot", "M0 0 L . 0 L10 10", SYNTAX),
    ("a lone sign", "M0 0 L10 0 L10 10 +", SYNTAX),
    ("leading comma", ",M0 0 L10 0 L10 10", SYNTAX),
    ("leading comma after space", " ,M0 0 L10 0 L10 10", SYNTAX),
    ("two commas", "M0,,0 L10 0 L10 10", SYNTAX),
    ("two commas with a space", "M0, ,0 L10 0 L10 10", SYNTAX),
    ("comma after a command", "M,0 0 L10 0 L10 10", SYNTAX),
    ("comma after Z", "M0 0 L10 0 L10 10 Z,M1 1", SYNTAX),
    ("spaces only", "   ", START),
    ("commas only past the checks", "0", START),
    ("starts with L", "L0 0 L10 0 L10 10", START),
    ("starts with Z", "Z M0 0 L10 0 L10 10", START),
    ("starts with a number", "0 0 L10 0 L10 10", START),
    ("M with one number", "M0", MALFORMED),
    ("M with no numbers", "M L10 0", MALFORMED),
    ("L missing y", "M0 0 L10 0 L10", MALFORMED),
    ("H with no number", "M0 0 L10 0 L10 10 H", MALFORMED),
    ("V with no number then Z", "M0 0 L10 0 L10 10 V Z", MALFORMED),
    ("a number after Z", "M0 0 L10 0 L10 10 Z 5 5", MALFORMED),
    ("a number after z", "M0 0 L10 0 L10 10 z 5 5", MALFORMED),
    ("absolute number past a million", "M0 0 L1000000.5 0 L10 10", RANGE),
    ("negative number past a million", "M0 0 L10 0 V-1000001", RANGE),
    ("exponent past a million", "M0 0 L1e7 0 L10 10", RANGE),
    ("an infinity", "M0 0 L1e999 0 L10 10", RANGE),
    ("relative l sum past a million", "M999999 0 l2 0 l0 5", RANGE),
    ("relative l sum past a million in y", "M0 999999 l5 0 l0 2", RANGE),
    ("relative h sum past a million", "M0 0 L5 5 h999999 h2", RANGE),
    ("relative v sum past a million", "M0 0 L5 5 v-999999 v-10", RANGE),
    ("relative m sum past a million", "M999999 0 L999999 5 L999990 5 m20 0", RANGE),
    ("implicit relative lines past a million", "m999999 0 0 5 5 0", RANGE),
    ("only a move", "M0 0", NONE),
    ("only two points", "M0 0 L10 10 Z", NONE),
    ("a flat line", "M0 0 L10 0 L20 0 Z", NONE),
    ("a vertical line", "M0 0 V10 V20 Z", NONE),
    ("all one point", "M3 3 L3 3 L3 3 Z", NONE),
    ("too thin for its size", "M0 0 L1000000 0 L1000000 0.5 Z", NONE),
    ("too thin for its distance from the origin", "M999000 999000 L999000.5 999000 L999000.5 999100 Z", NONE),
    ("tiny near the origin", "M0 0 L0.0000005 0 L0.0000005 0.0000005 Z", NONE),
]
for name, d, want in REFUSED:
    got = outline(d)
    check("outline refuses: %s" % name, got == want, got)

check("outline: a thin but not too thin shape near the origin is kept",
      outline("M0 0 L0.000002 0 L0.000002 0.000002 Z") == [[(0.0, 0.0), (2e-6, 0.0), (2e-6, 2e-6)]])
check("outline: refusals are RuntimeError, not another exception", lambda: all(
    isinstance(outline(d), str) for d in ("M", "M0 0 L", "MZ", "Mz5", "m-", "M0 0 H-", "M0 0 Z Z 1")))

# ---------------------------------------------------------------- hexrgb

check("hexrgb reads #rrggbb", cp.hexrgb("#0a10fF") == (10, 16, 255), cp.hexrgb("#0a10fF"))
check("hexrgb reads black and white", cp.hexrgb("#000000") == (0, 0, 0) and cp.hexrgb("#ffffff") == (255, 255, 255))

# ---------------------------------------------------------------- png


def unpng(blob):
    """A PNG's width, height, bit depth, color type and rows of RGB bytes; asserts every chunk's CRC."""
    assert blob[:8] == b"\x89PNG\r\n\x1a\n", "bad signature"
    pos, chunks = 8, []
    while pos < len(blob):
        n = struct.unpack(">I", blob[pos:pos + 4])[0]
        kind, body = blob[pos + 4:pos + 8], blob[pos + 8:pos + 8 + n]
        crc = struct.unpack(">I", blob[pos + 8 + n:pos + 12 + n])[0]
        assert crc == zlib.crc32(kind + body) & 0xffffffff, "bad CRC in %r" % kind
        chunks.append((kind, body))
        pos += 12 + n
    kinds = [k for k, _ in chunks]
    assert kinds[0] == b"IHDR" and kinds[-1] == b"IEND" and kinds.count(b"IDAT") == 1, kinds
    w, h, depth, ctype, comp, filt, inter = struct.unpack(">IIBBBBB", chunks[0][1])
    assert (comp, filt, inter) == (0, 0, 0)
    raw = zlib.decompress(dict(chunks)[b"IDAT"])
    if ctype == 3:
        plte = dict(chunks)[b"PLTE"]
        palette = [plte[k:k + 3] for k in range(0, len(plte), 3)]
        bpp, stride = 1, (w * depth + 7) // 8
    else:
        assert ctype == 2 and depth == 8 and b"PLTE" not in kinds
        bpp, stride = 3, w * 3
    assert len(raw) == h * (stride + 1), "IDAT holds %d bytes, not %d" % (len(raw), h * (stride + 1))
    prev, rows = bytes(stride), []
    for r in range(h):
        ft, line = raw[r * (stride + 1)], bytearray(raw[r * (stride + 1) + 1:(r + 1) * (stride + 1)])
        for k in range(stride):
            a = line[k - bpp] if k >= bpp else 0
            b = prev[k]
            c = prev[k - bpp] if k >= bpp else 0
            if ft == 0:
                p = 0
            elif ft == 1:
                p = a
            elif ft == 2:
                p = b
            elif ft == 3:
                p = (a + b) >> 1
            elif ft == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                p = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
            else:
                raise AssertionError("filter type %d" % ft)
            line[k] = (line[k] + p) & 0xff
        prev = bytes(line)
        if ctype == 3:
            idx = []
            for byte in line:
                for j in range(8 // depth - 1, -1, -1):
                    idx.append((byte >> (j * depth)) & ((1 << depth) - 1))
            rows.append(b"".join(palette[v] for v in idx[:w]))
        else:
            rows.append(bytes(line))
    return w, h, depth, ctype, rows


def png_roundtrip(name, w, h, rows, depth, ctype):
    def run():
        got = unpng(cp.png(w, h, rows))
        assert got[:4] == (w, h, depth, ctype), "header %r" % (got[:4],)
        assert got[4] == [bytes(r) for r in rows], "pixels differ"
        return True
    check("png: %s" % name, run)


def colors(n):
    return [bytes(((k * 37) % 256, (k * 91 + 7) % 256, (k // 3) % 256)) for k in range(n)]


one = [bytes([9, 8, 7] * 5) for _ in range(3)]
png_roundtrip("one color is a 1 bit palette", 5, 3, one, 1, 3)
two = [b"".join(colors(2)[(x + y) % 2] for x in range(9)) for y in range(4)]
png_roundtrip("two colors, a width not a multiple of 8, are a 1 bit palette", 9, 4, two, 1, 3)
four = [b"".join(colors(4)[(x * y) % 4] for x in range(7)) for y in range(5)]
png_roundtrip("four colors are a 2 bit palette", 7, 5, four, 2, 3)
ten = [b"".join(colors(10)[(x + 3 * y) % 10] for x in range(11)) for y in range(6)]
png_roundtrip("ten colors are a 4 bit palette", 11, 6, ten, 4, 3)
c256 = colors(256)
full = [b"".join(c256[(x + 16 * y) % 256] for x in range(16)) for y in range(16)]
check("png: the test palette has 256 distinct colors", len(set(c256)) == 256)
png_roundtrip("256 colors are an 8 bit palette", 16, 16, full, 8, 3)
grad = [bytes(v for x in range(20) for v in (x * 12 % 256, y * 12 % 256, (x * y) % 256)) for y in range(20)]
png_roundtrip("more than 256 colors are RGB with filters", 20, 20, grad, 8, 2)
_seed = [12345]


def _rand():
    _seed[0] = (_seed[0] * 1103515245 + 12345) % 2 ** 31
    return _seed[0] >> 16 & 0xff


noise = [bytes(_rand() for _ in range(18 * 3)) for _ in range(17)]
check("png: the noise has more than 256 colors",
      len({r[k:k + 3] for r in noise for k in range(0, len(r), 3)}) > 256)
png_roundtrip("noisy RGB", 18, 17, noise, 8, 2)
check("png: the most common color is palette entry 0", lambda: (
    re.search(b"PLTE", cp.png(3, 1, [bytes([1, 1, 1, 2, 2, 2, 2, 2, 2])])) is not None
    and cp.png(3, 1, [bytes([1, 1, 1, 2, 2, 2, 2, 2, 2])]).split(b"PLTE")[1][:6] == bytes([2, 2, 2, 1, 1, 1])))
check("png: rows may be bytearrays or lists", lambda: unpng(cp.png(2, 1, [[1, 2, 3, 4, 5, 6]]))[4] == [
    bytes([1, 2, 3, 4, 5, 6])])
check("png: a smooth RGB gradient compresses better than unfiltered",
      lambda: len(cp.png(20, 20, grad)) < len(zlib.compress(b"".join(b"\x00" + r for r in grad), 9)) + 60)

# ---------------------------------------------------------------- flattened_mark


def image(svg):
    m = re.fullmatch(r'<image x="(-?\d+)" y="(-?\d+)" width="(\d+)" height="(\d+)" preserveAspectRatio="none" '
                     r'href="data:image/png;base64,([A-Za-z0-9+/=]+)"/>', svg)
    assert m, svg[:200]
    x, y, w, h = (int(v) for v in m.groups()[:4])
    return x, y, w, h, unpng(base64.b64decode(m.group(5)))


def pixel(rows, col, row):
    return tuple(rows[row][3 * col:3 * col + 3])


def blend(under, over, a):
    return tuple(int(round(u * (1 - a) + o * a)) for u, o in zip(under, over))


check("flat: no polygons draw nothing", cp.flattened_mark([], 10) == "")

for theme in ("paper", "ink"):
    cp.use_theme(theme)
    bg, ink = cp.hexrgb(cp.BG), cp.hexrgb(cp.TEXT)
    ga, ma = float(cp.THEME["grid"]), float(cp.THEME["mark"])
    sq = cp.mark_outline("M0 0 H10 V10 H0 Z")

    def flat_square():
        x, y, w, h, (pw, ph, _, _, rows) = image(cp.flattened_mark(sq, 0))
        # 120 units square about (492, 372): 432..552 and 312..432, one unit of margin, inside MARK_LIMIT
        assert (x, y, w, h) == (431, 311, 122, 122), (x, y, w, h)
        assert (pw, ph) == (w * cp.MARK_PX, h * cp.MARK_PX), (pw, ph)
        assert pixel(rows, 10, 10) == blend(bg, ink, ma), pixel(rows, 10, 10)          # inside, off the grid
        assert pixel(rows, 1, 10) == bg, pixel(rows, 1, 10)                             # outside, off the grid
        # x=432 is 24*18: the grid stroke's column is the raster's column 2 (x0*2 + 2 = 864)
        assert pixel(rows, 0, 10) == bg and pixel(rows, 3, 10) == blend(bg, ink, ma)
        gridded = blend(bg, ink, ga)
        assert pixel(rows, 2, 10) == blend(gridded, ink, ma), pixel(rows, 2, 10)      # the edge column, grid + mark
        # y=312 is 24*13: row 2 carries the grid across the whole raster, outside the mark too
        assert pixel(rows, 0, 2) == gridded and pixel(rows, 0, 1) == bg
        # the half covered column at the edge is not drawn: the mark's left edge sits exactly on x=432
        return True
    check("flat (%s): a square fills its inside over background and grid" % theme, flat_square)

    def flat_hole():
        holed = cp.mark_outline("M0 0 H30 V30 H0 Z M10 10 H20 V20 H10 Z")
        x, y, w, h, (pw, ph, _, _, rows) = image(cp.flattened_mark(holed, 0))
        cx, cy = (492 - x) * cp.MARK_PX, (372 - y) * cp.MARK_PX
        assert pixel(rows, cx + 1, cy + 1) == bg or pixel(rows, cx + 1, cy + 1) == blend(bg, ink, ga), "hole filled"
        ring = (cx + 1, cy - 30 * cp.MARK_PX - 1)   # between the outer edge (60 up) and the hole (20 up)
        assert pixel(rows, *ring) in (blend(bg, ink, ma), blend(blend(bg, ink, ga), ink, ma)), pixel(rows, *ring)
        return True
    check("flat (%s): even-odd leaves a hole in the middle" % theme, flat_hole)

cp.use_theme("paper")
bg, ink, ma = cp.hexrgb(cp.BG), cp.hexrgb(cp.TEXT), float(cp.THEME["mark"])


def flat_edges():
    tri = cp.mark_outline("M0 0 L10 0 L5 7 Z")
    x, y, w, h, (pw, ph, _, _, rows) = image(cp.flattened_mark(tri, 33))
    vals = {pixel(rows, c, r) for r in range(ph) for c in range(pw)}
    lo, hi = blend(bg, ink, ma), bg
    partial = [v for v in vals if v not in (lo, hi) and all(min(a, b) <= p <= max(a, b) for p, a, b in zip(v, lo, hi))]
    assert len(partial) > 3, "no antialiased edge pixels"
    return True


check("flat: a turned outline has smooth, partly covered edges", flat_edges)


def flat_fit():
    tall = cp.mark_outline("M0 0 H1 V40 H0 Z")   # 120 wide would be 4800 tall: scaled down about the centre
    svg = cp.flattened_mark(tall, 0)
    x, y, w, h, (pw, ph, _, _, rows) = image(svg)
    lx0, ly0, lx1, ly1 = cp.MARK_LIMIT
    assert lx0 <= x and ly0 <= y and x + w <= lx1 and y + h <= ly1, (x, y, w, h)
    assert y + h == ly1, "the tall mark should reach the corner limit, got %r" % ((x, y, w, h),)
    # 372 - 8 = 364 up, 435 - 372 = 63 down: the fit is 63/2400, so the column is 3.15 units wide
    assert w <= 6, (x, y, w, h)
    assert pixel(rows, (492 - x) * cp.MARK_PX, ph - 3) != bg
    return True


check("flat: a tall outline is scaled down to fit clear of the corners", flat_fit)


def flat_turn():
    wide = cp.mark_outline("M0 0 H40 V1 H0 Z")
    x, y, w, h, _ = image(cp.flattened_mark(wide, 90))   # turned upright: a column 120 tall, which still fits
    x2, y2, w2, h2, _ = image(cp.flattened_mark(wide, 0))
    assert w <= 6 and (y, h) == (311, 122) and x <= 492 <= x + w, (x, y, w, h)
    assert h2 <= 6 and w2 <= 122 and x2 + w2 <= cp.MARK_LIMIT[2], (x2, y2, w2, h2)
    return True


check("flat: the turn rotates the outline about the centre", flat_turn)


def flat_turn_left():
    wide = cp.mark_outline("M0 0 H40 V1 H0 Z")
    x, y, w, h, _ = image(cp.flattened_mark(wide, 180 + 45))   # leans past the top-left: limited on x and y
    lx0, ly0, lx1, ly1 = cp.MARK_LIMIT
    assert lx0 <= x and ly0 <= y and x + w <= lx1 and y + h <= ly1, (x, y, w, h)
    return True


check("flat: a diagonal outline stays inside MARK_LIMIT", flat_turn_left)


def flat_real():
    poly = cp.mark_outline("M0 0 L50 0 L50 30 L25 45 L0 30 Z M10 10 L40 10 L40 20 L10 20 Z")
    x, y, w, h, (pw, ph, depth, ctype, rows) = image(cp.flattened_mark(poly, cp.MARK_TURN))
    assert (pw, ph) == (w * 2, h * 2) and len(rows) == ph and all(len(r) == pw * 3 for r in rows)
    return True


check("flat: the panel's own turn draws a full-size raster", flat_real)


def flat_vertex():
    # a diamond whose top vertex lands exactly on a sub-scanline: both its edges cross there, an empty span
    diamond = cp.mark_outline("M0 479.5 L480 0 L960 479.5 L480 959 Z")   # 120 wide, 119.875 tall
    x, y, w, h, (pw, ph, _, _, rows) = image(cp.flattened_mark(diamond, 0))
    assert (x, y, w, h) == (431, 311, 122, 122), (x, y, w, h)
    # the vertex is at panel y 312.0625, raster row 2: rows 0 and 1 are untouched (row 2 carries the grid)
    assert all(pixel(rows, c, r) == bg for r in (0, 1) for c in range(pw) if (x * 2 + c) % 48), "above the vertex"
    mid = (492 - x) * 2
    assert pixel(rows, mid, 2) != bg and pixel(rows, mid - 3, 2) == blend(bg, ink, float(cp.THEME["grid"]))
    assert pixel(rows, mid, ph // 2) == blend(bg, ink, ma)
    return True


check("flat: a vertex exactly on a sub-scanline adds no stray coverage", flat_vertex)

# ---------------------------------------------------------------- wordmark

saved = cp.DESIGN_DIR, cp.WORDMARK_FILE


def real_wordmark():
    if not os.path.isdir(cp.DESIGN_DIR):
        return True   # the plain look: nothing to read
    d, box = cp.load_wordmark()
    with open(cp.WORDMARK_FILE, encoding="utf-8") as f:
        src = f.read()
    vb = re.search(r'viewBox="([^"]+)"', src).group(1).split()
    assert box == tuple(float(v) for v in vb), box
    assert d.startswith("M") and d in src and len(d) > 100
    return True


check("word: design/wordmark.svg is read, path and frame", real_wordmark)

tmp = tempfile.mkdtemp(prefix="watermark-")
try:
    cp.DESIGN_DIR = os.path.join(tmp, "absent")
    cp.WORDMARK_FILE = os.path.join(cp.DESIGN_DIR, "wordmark.svg")
    check("word: no design/ means no wordmark", lambda: cp.load_wordmark() is None)

    cp.DESIGN_DIR = os.path.join(tmp, "design")
    os.makedirs(cp.DESIGN_DIR)
    cp.WORDMARK_FILE = os.path.join(cp.DESIGN_DIR, "wordmark.svg")

    def raises(msg):
        try:
            cp.load_wordmark()
        except RuntimeError as e:
            return str(e) == msg or str(e)
        return "no error"

    r = raises("the coderprint wordmark (wordmark.svg) is missing")
    check("word: design/ without wordmark.svg stops", r is True, r)

    def write(text):
        with open(cp.WORDMARK_FILE, "w", encoding="utf-8") as f:
            f.write(text)

    unreadable = "the coderprint wordmark (wordmark.svg) could not be read"
    for name, text in (("no viewBox", '<svg><path d="M0 0L1 1Z"/></svg>'),
                       ("no path", '<svg viewBox="0 0 10 10"></svg>'),
                       ("a path with other characters", '<svg viewBox="0 0 10 10"><path d="M0 0 X1"/></svg>'),
                       ("a negative frame size", '<svg viewBox="0 0 -10 10"><path d="M0 0L1 1Z"/></svg>'),
                       ("empty", "")):
        write(text)
        r = raises(unreadable)
        check("word: a wordmark with %s stops" % name, r is True, r)
    write('<svg viewBox="-5 2.5 200 40"><path d="M0 0C1 1 2 2 3 3L4 4Z"/></svg>')
    check("word: a wordmark with curves and a negative origin is read",
          lambda: cp.load_wordmark() == ("M0 0C1 1 2 2 3 3L4 4Z", (-5.0, 2.5, 200.0, 40.0)))
    os.remove(cp.WORDMARK_FILE)
    os.makedirs(cp.WORDMARK_FILE)   # there, but a folder: unreadable as a file
    r = raises("the coderprint wordmark (wordmark.svg) is missing")
    check("word: a wordmark.svg that cannot be opened stops", r is True, r)
finally:
    cp.DESIGN_DIR, cp.WORDMARK_FILE = saved
    shutil.rmtree(tmp, ignore_errors=True)

check("word: no wordmark draws nothing", cp.wordmark(None) == "")

word = ("M10 20 L30 20 L30 40 Z", (10.0, 20.0, 236.0, 50.0))
cp.use_theme("paper")
lite = cp.wordmark(word)
s = cp.WORDMARK_WIDTH / 236.0   # 0.5
want = ('<path d="%s" fill="%s" fill-rule="evenodd" transform="translate(%.2f %.2f) scale(%.5f) '
        'translate(%.2f %.2f)"/>' % (cp.relative_path(word[0]), cp.TEXT, cp.WORDMARK_RIGHT - cp.WORDMARK_WIDTH,
                                     cp.WORDMARK_BOTTOM - 50.0 * s, s, -10.0, -20.0))
check("word: a lite draws the letters plainly, scaled to WORDMARK_WIDTH and ending at the corner", lite == want, lite)
check("word: the placement is the expected numbers",
      'transform="translate(442.00 413.00) scale(0.50000) translate(-10.00 -20.00)"' in lite
      and 'fill="%s"' % cp.TEXT in lite, lite)
cp.use_theme("ink")
nite = cp.wordmark(word)
check("word: a nite wraps the letters in the glowS filter",
      nite.startswith('<g filter="url(#glowS)"><path ') and nite.endswith("/></g>") and 'fill="%s"' % cp.TEXT in nite,
      nite)

print("%d passed, %d failed" % (passes, len(fails)))
sys.exit(1 if fails else 0)
