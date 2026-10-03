# coderprint's drawing: colors, text, the window selector and the activity bars. coderprint.py runs this file as part
# of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- compact numbers and paths
# A panel is fetched on every profile view, so it is written tight: shortest numbers, relative path data,
# and every chart boundary written once.


def num(v, d=1):
    """The shortest SVG number at d decimals: 0.5 as .5, -0.50 as -.5, 3.0 as 3."""
    s = "%.*f" % (d, v)
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    if s in ("-0", ""):
        s = "0"
    if s.startswith("0."):
        s = s[1:]
    elif s.startswith("-0."):
        s = "-" + s[2:]
    return s


def joined(nums):
    """Numbers run together as path data allows: a space between two, unless a minus sign separates them."""
    out = ""
    for s in nums:
        out += s if not out or s.startswith("-") else " " + s
    return out


def simplify(points, eps):
    """Douglas-Peucker on y(x): a point is kept unless the chord between its kept neighbours passes within
    eps of it."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        a, b = stack.pop()
        (xa, ya), (xb, yb) = points[a], points[b]
        worst, at = -1.0, None
        for i in range(a + 1, b):
            x, y = points[i]
            dev = abs(y - (ya + (yb - ya) * (x - xa) / (xb - xa) if xb != xa else y - ya))
            if dev > worst:
                worst, at = dev, i
        if at is not None and worst > eps:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(points, keep) if k]


def rel_run(points):
    """A line through points on whole-unit x, after its first point, as relative lineto data with y to a
    tenth. Each step is taken between rounded absolute values, so no rounding error builds up."""
    t = [(x, int(round(y * 10))) for x, y in points]
    nums = []
    for (xa, ya), (xb, yb) in zip(t, t[1:]):
        nums += [num(xb - xa, 0), num((yb - ya) / 10.0)]
    return "l" + joined(nums) if nums else ""


PATH_TOKEN = re.compile(r"[MmLlHhVvCcSsQqTtZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
PATH_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "Z": 0}


def relative_path(d, decimals=1):
    """Path data (M L H V C S Q T Z, absolute or relative) rewritten as relative commands. Every absolute
    coordinate is rounded first and each step taken between rounded values, so no error builds up."""
    toks = PATH_TOKEN.findall(d)
    i, cmd, out, last = 0, None, [], None
    cx = cy = sx = sy = 0.0
    q = 10 ** decimals
    r = lambda v: round(v * q) / q
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                out.append("z")
                cx, cy, last = sx, sy, "z"
                continue
        up, rel = cmd.upper(), cmd.islower()
        vals = [float(v) for v in toks[i:i + PATH_ARITY[up]]]
        i += PATH_ARITY[up]
        if up == "H":
            x = r(cx + vals[0] if rel else vals[0])
            letter, deltas, cx = "h", [x - cx], x
        elif up == "V":
            y = r(cy + vals[0] if rel else vals[0])
            letter, deltas, cy = "v", [y - cy], y
        else:
            deltas = []
            px, py = cx, cy
            for k in range(0, len(vals), 2):
                x = r(cx + vals[k] if rel else vals[k])
                y = r(cy + vals[k + 1] if rel else vals[k + 1])
                deltas += [x - px, y - py]
                if up in "LMT":
                    px, py = x, y
            cx, cy = x, y
            if up == "M":
                sx, sy = cx, cy
                cmd = "l" if rel else "L"   # coordinates repeated after a moveto are linetos
            letter = up.lower()
        body = joined([num(v, decimals) for v in deltas])
        implicit = (letter == last and letter != "m") or (last == "m" and letter == "l")
        out.append((body if body.startswith("-") else " " + body) if implicit else letter + body)
        last = letter
    return "".join(out)


def luminance(color):
    def channel(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = hexrgb(color)
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a, b):
    """The contrast ratio of two colors, as the Web Content Accessibility Guidelines define it."""
    la, lb = luminance(a), luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def lab(color):
    """A color in CIELAB, from sRGB under the D65 white."""
    def linear(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(v) for v in hexrgb(color))
    xyz = ((0.4124564 * r + 0.3575761 * g + 0.1804375 * b) / 0.95047,
           0.2126729 * r + 0.7151522 * g + 0.0721750 * b,
           (0.0193339 * r + 0.1191920 * g + 0.9503041 * b) / 1.08883)
    fx, fy, fz = (t ** (1 / 3.0) if t > 216 / 24389.0 else (24389 / 27.0 * t + 16) / 116.0 for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a, b):
    """How different two colors look: CIEDE2000, as Sharma, Wu and Dalal (2005) set it out. About 1 is
    the least an eye can see side by side; 12 reads plainly as two colors."""
    (l1, a1, b1), (l2, a2, b2) = lab(a), lab(b)
    cbar = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cbar ** 7 / (cbar ** 7 + 25.0 ** 7)))
    a1, a2 = (1 + g) * a1, (1 + g) * a2
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1 = math.degrees(math.atan2(b1, a1)) % 360 if c1 else 0.0
    h2 = math.degrees(math.atan2(b2, a2)) % 360 if c2 else 0.0
    dh = 0.0 if not c1 * c2 else h2 - h1
    dh = dh - 360 if dh > 180 else dh + 360 if dh < -180 else dh
    dl, dc, dhh = l2 - l1, c2 - c1, 2 * math.sqrt(c1 * c2) * math.sin(math.radians(dh / 2))
    lb, cb = (l1 + l2) / 2, (c1 + c2) / 2
    if not c1 * c2:
        hb = h1 + h2
    elif abs(h1 - h2) <= 180:
        hb = (h1 + h2) / 2
    else:
        hb = (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    t = (1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb))
         + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63)))
    sl = 1 + 0.015 * (lb - 50) ** 2 / math.sqrt(20 + (lb - 50) ** 2)
    sc, sh = 1 + 0.045 * cb, 1 + 0.015 * cb * t
    rt = (-math.sin(math.radians(60 * math.exp(-((hb - 275) / 25.0) ** 2)))
          * 2 * math.sqrt(cb ** 7 / (cb ** 7 + 25.0 ** 7)))
    return math.sqrt((dl / sl) ** 2 + (dc / sc) ** 2 + (dhh / sh) ** 2 + rt * (dc / sc) * (dhh / sh))


def over(top, alpha, under):
    """top laid over under at alpha, as one color."""
    return "#%02x%02x%02x" % tuple(int(round(alpha * t + (1 - alpha) * u)) for t, u in zip(hexrgb(top), hexrgb(under)))


# ---------------------------------------------------------------- drawing


def use_theme(name):
    global BG, LINE, TEXT, MUTED, DIM, OTHER_COLOR, THEME
    THEME = THEMES[name]
    BG, LINE, TEXT, MUTED, DIM, OTHER_COLOR = (THEME[k] for k in ("bg", "line", "text", "muted", "dim", "other"))


# The nites glow: the greens bloom, the headline and the values carry a soft halo, the lit names and
# the 0 line shine, and the corners fall away. All still filters, so a frozen animation clock changes
# nothing. They work in the panel's own units, so a bar 1.5 units wide still gets its whole halo, and
# their region is the whole panel being drawn, wide or compact.
def glow_defs():
    full = ('filterUnits="userSpaceOnUse" x="0" y="0" width="%d" height="%d" color-interpolation-filters="sRGB"'
            % (PANEL_W, PANEL_H))
    return (
        '<filter id="glowG" %s><feGaussianBlur in="SourceGraphic" stdDeviation="3" result="b"/>'
        '<feComponentTransfer in="b" result="c"><feFuncA type="linear" slope=".55"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="glowW" %s><feGaussianBlur in="SourceGraphic" stdDeviation="3.5" result="b"/>'
        '<feComponentTransfer in="b" result="c"><feFuncA type="linear" slope=".3"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<filter id="glowS" %s><feGaussianBlur in="SourceGraphic" stdDeviation="2" result="b"/>'
        '<feComponentTransfer in="b" result="c"><feFuncA type="linear" slope=".22"/></feComponentTransfer>'
        '<feMerge><feMergeNode in="c"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        '<radialGradient id="vignette" cx="50%%" cy="48%%" r="75%%"><stop offset=".62" stop-color="#000" '
        'stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></radialGradient>' % (full, full, full))


def glow(name, content):
    """content inside one of the glow filters in a nite, and unchanged in a lite."""
    return '<g filter="url(#%s)">%s</g>' % (name, content) if THEME["dark"] else content


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text(x, y, s, size, fill, family, weight=400, anchor="start", spacing=0, length=None):
    """A line of text; length, when given, is the width a viewer fits it to, glyphs and all, in any face."""
    return ('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" font-weight="%d" fill="%s"%s%s%s>%s</text>'
            % (x, y, family, size, weight, fill, ' text-anchor="%s"' % anchor if anchor != "start" else "",
               ' letter-spacing="%s"' % spacing if spacing else "",
               ' textLength="%s" lengthAdjust="spacingAndGlyphs"' % num(length, 2) if length else "", esc(s)))


def label(x, y, s, anchor="start", fill=None, size=9.5):
    """The house chrome: small uppercase mono, tracked out."""
    return text(x, y, s.upper(), size, fill or MUTED, MONO, 500, anchor, 1.3)


def char_width(size):
    """The rendered width of one character of the house chrome (label) at size."""
    return size * 0.6 + 1.3


def switch(names, lit, x, y, size=9.5):
    """A row of names that looks like a switch, one lit and underlined in green, thin rules between. Each
    name is fitted to its budgeted width, so the underline and the rules line up in any monospace font."""
    gap, out = 26.0 if len(names) == len(THEME_ORDER) else 14.0, ""
    for i, name in enumerate(names):
        w = char_width(size) * len(name)
        on = i == lit
        name_text = ('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" font-weight="%d" fill="%s" '
                     'textLength="%.1f" lengthAdjust="spacing">%s</text>'
                     % (x, y, MONO, size, 600 if on else 500, TEXT if on else DIM, w - 1.3, esc(name.upper())))
        out += glow("glowS", name_text) if on else name_text
        if on:
            out += glow("glowG", '<rect x="%.1f" y="%.1f" width="%.1f" height="1.5" rx=".75" fill="%s"/>'
                        % (x, y + 4, w - 1.3, GREEN))
        if i < len(names) - 1:
            sep = x + w + gap / 2 - 0.65
            out += ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>'
                    % (sep, y - (size - 1.5), sep, y + 2, LINE))
        x += w + gap
    return out


def switch_width(names, size=9.5):
    gap = 26.0 if len(names) == len(THEME_ORDER) else 14.0
    return char_width(size) * sum(len(n) for n in names) - 1.3 + gap * (len(names) - 1)


def theme_of(variant):
    """The house theme a key of THEMES is a version of."""
    return next(name for name, pair in VARIANTS.items() if variant in pair)


def theme_strip(active, y=30, size=9.5):
    """paper | sepia | sage | oxblood | ink, centred at the top, with the theme of the version drawn (active,
    a key of THEMES) lit. On the wide panel its baseline sits where it shares a centre line with the music
    card's header across the seam."""
    return switch(THEME_ORDER, THEME_ORDER.index(theme_of(active)), (PANEL_W - switch_width(THEME_ORDER, size)) / 2,
                  y, size)


def window_names():
    return [WINDOWS[k][0] for k in WINDOW_ORDER]


def window_selector(window, right=560, y=192, size=9.5):
    """ALL | 10Y | 5Y | 3Y | 2Y | 12M at the chart's top right, the panel's window lit."""
    names = window_names()
    return switch(names, WINDOW_ORDER.index(window), right - switch_width(names, size), y, size)


# The activity bars' bursts: runs of bars not broken by BURST_GAP or more empty bars (about 12 days at 52
# bars). Each is labelled with its lines, so the bars show where the headline came from.
BURST_GAP, BURSTS_SHOWN, BURST_SIZE = 3, 4, 8.5


def bursts(spark):
    """[first bar, last bar, lines] for each run of bars not broken by BURST_GAP or more empty bars."""
    out, cur, empty = [], None, 0
    for i, v in enumerate(spark):
        if v:
            if cur is None or empty >= BURST_GAP:
                if cur:
                    out.append(cur)
                cur = [i, i, 0]
            cur[1] = i
            cur[2] += v
            empty = 0
        else:
            empty += 1
    if cur:
        out.append(cur)
    return out


def burst_labels(spark, tops, avoid, x0=16, span=264.0, size=BURST_SIZE):
    """Each burst's lines over its tallest bar, the biggest bursts first, none against a box in avoid (the
    headline) or another label. Nothing when the bars are one burst, since the headline already says it.
    The bars are those activity_bars draws with the same x0 and span; tops is what it returned."""
    groups = bursts(spark)
    if len(groups) < 2:
        return ""
    step = span / len(spark)
    width = max(1.5, step * 0.6)
    cap = 0.72 * size   # digits, k and M have no descenders
    hits = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    kept, out = [], ""
    for first, last, total in sorted(groups, key=lambda g: -g[2])[:BURSTS_SHOWN]:
        s = fmt(total)
        w = len(s) * size * 0.6
        cx = min(max(x0 + (first + last) * step / 2 + width / 2, x0 + w / 2), x0 + span - w / 2)
        top = min(tops[first:last + 1])
        box = (cx - w / 2 - 4, top - 5 - cap, cx + w / 2 + 4, top - 5)
        if any(hits(box, a) for a in avoid):   # tucked just over the burst's tallest bar instead
            box = (box[0], top - 1.2 - cap, box[2], top - 1.2)
            if any(hits(box, a) for a in avoid):
                continue
        if any(box[0] < b[2] and b[0] < box[2] for b in kept):
            continue
        kept.append(box)
        out += text(cx, box[3], s, size, MUTED, MONO, 500, "middle")
    return out


# The stats rows: names start at x in the chrome at size name, values end at right at size value, each
# value character vchar wide; the first row's baseline is top, the rest pitch apart; the leader runs rise
# above the baseline in squares dot wide.
Rows = namedtuple("Rows", "x right top pitch name value vchar rise dot")
ROWS = Rows(306, 560, 56, 24, 9.5, 13, 7.6, 3, 1.6)
# The stats row that counts languages: every language at FOLD (1%) or more of the window's lines of code, named on
# the chart or not. Its name says what it counts, the threshold included, so it never reads as every language
# written; and the words for screen readers and the README's alt text say the same, for many and for one.
LANGUAGES_ROW = "languages · 1%+"
LANGUAGES_WORDS = ("{v} languages at 1% or more of the lines of code", "1 language at 1% or more of the lines of code")


def leader(name, value):
    """Where a stats row's leader starts, and how many squares it holds between the name and the value."""
    start = ROWS.x + char_width(ROWS.name) * len(name) + 6
    stop = ROWS.right - ROWS.vchar * len(value) - 8
    return start, (int((stop - start) // BIT_PITCH) + 1 if stop > start else 0)


def hop_plan(rows):
    """The dots' timetable. The rows take turns, so one dot is on the panel at a time: a row's dot rests
    HOP on each square, its value lights, and after HOP_REST the next row's dot sets off. Returns the hops
    in one loop, whose length every row shares, and when each row's dot sets off, in seconds."""
    starts, t = [], 0.0
    for name, value in rows:
        starts.append(t)
        n = leader(name, value)[1]
        if n:
            t += (n + 1) * HOP + HOP_REST
    return max(1, int(math.ceil((t + HOP_END) / HOP))), starts


BAR_BASE, BAR_REACH = 124, 20   # the activity bars' baseline, and how far a bar reaches from it at its peak


def bar_height(v, peak, reach=BAR_REACH):
    """An activity bar's length: square-rooted, so a quiet slice still shows beside a burst."""
    return 2 + (reach - 2) * math.sqrt(v / peak) if v else 0.0


def activity_bars(spark, commits=None, x0=16, span=264.0, base=BAR_BASE, reach=BAR_REACH):
    """The activity bars across span from x0, today's last: each slice's lines rise in green above base and
    its commits hang in red below it, each reaching up to reach at its own peak. Returns the bars and each
    slice's highest drawn point, which the burst labels sit over."""
    peak = float(max(spark) or 1)
    cpeak = float(max(commits) if commits else 0) or 1.0
    step = span / len(spark)
    width = max(1.5, step * 0.6)
    bars, tops = "", []
    for i, v in enumerate(spark):
        x = x0 + i * step
        now = ' class="cp-now"' if i == len(spark) - 1 else ""
        up, down = bar_height(v, peak, reach), bar_height(commits[i] if commits else 0, cpeak, reach)
        if up:
            bars += ('<rect%s x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="%s"/>'
                     % (now, x, base - 1 - up, width, up, width / 2, GREEN))
        if down:
            bars += ('<rect%s x="%.2f" y="%s" width="%.2f" height="%.2f" rx="%.2f" fill="%s"/>'
                     % (now, x, num(base + 1, 2), width, down, width / 2, RED))
        if not up and not down:
            bars += '<rect%s x="%.2f" y="%.1f" width="%.2f" height="1" fill="%s"/>' % (now, x, base - 0.5, width, LINE)
        tops.append(base - 1 - up)
    return bars, tops


def bars_key(cx, y, size, box=5, pad=9, gap=12):
    """The bars' key, centred on cx with its words on baseline y: for lines, then for commits, a square
    swatch box units wide and the word starting pad after the swatch's left edge, gap units between the
    two. Its widths come from size, not from TICK_CHAR, so the compact panel's swap cannot move the wide
    panel's key."""
    cw = char_width(size)
    x = cx - (2 * pad + gap + cw * 12 - 2.6) / 2   # two swatches, two words, gap between the pairs
    out = ""
    for word, color in (("lines", GREEN), ("commits", RED)):
        out += ('<rect x="%s" y="%s" width="%d" height="%d" rx="1" fill="%s"/>'
                % (num(x, 2), num(y - box - 0.5), box, box, color) + label(x + pad, y, word, size=size))
        x += pad + cw * len(word) - 1.3 + gap
    return out
