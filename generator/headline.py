# coderprint's headline, stats, stream chart and legend. coderprint.py runs this file as part of one module, after
# the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- the headline: lines of code
# Four tiles (in use, production, tests, written), and under them a ring and a bar, each filled with production
# then tests out of everything written, the ring's middle saying what share is kept. Their story, told as motion
# for a visitor who allows it, runs STORY seconds from the rest that is the drawing itself: everything written
# fills in and glows red with its figure; it falls back to what is in use, which glows yellow; to production,
# green; then tests fill back in, green; and the middle says what each is. Each move takes the seconds between
# its pair of STORY_ marks, and each glow rises, holds and settles before the next move.
STORY = 25.0
STORY_FILL, STORY_UNFILL, STORY_DOWN, STORY_UP = (3.0, 5.0), (8.2, 10.0), (13.2, 14.8), (18.0, 19.6)
STORY_RISE, STORY_HOLD, STORY_FADE, STORY_SWAP = 0.6, 1.8, 0.8, 0.5
# Where the headline goes on a panel. kicker: x, y, size. tiles: x0, x1, the figures' baseline and size, the
# labels' baseline and size, the room left of every figure but the first, the rules' top and bottom. ring: centre,
# radius, stroke, the middle's size and its word's size (0 for no word). bar: x0, x1, top, height. bars: the
# activity bars' x0, span, baseline, reach, burst labels' size, and the bottom of the room they keep clear of.
# dates: the bars' dates' baseline and size, and the key's centre and its swatch, pad and gap.
Head = namedtuple("Head", "kicker tiles ring bar bars dates")
WIDE_HEAD = Head((16, 52, 9.5), (16, 280, 82, 22, 95, 7.5, 8, 66, 99), (30, 117, 11, 4.5, 7, 0), (52, 280, 113, 8),
                 (16, 264.0, 150, 10, BURST_SIZE, 131), (171, 8, (148, 5, 9, 12)))


def story_figures():
    """The headline's figures, (written, in use, production, tests), and production's and in use's shares of
    what was written, each 0 when nothing was."""
    q = QUANTITY or {}
    written, prod, tests = q.get("written", 0), q.get("production", 0), q.get("tests", 0)
    use = prod + tests
    if written <= 0:
        return written, use, prod, tests, 0.0, 0.0
    shown = min(1.0, use / float(written))
    return written, use, prod, tests, min(shown, prod / float(written)), shown


def share_label(whole, exact):
    """A share of what was written as the ring's middle and the words write it, whole being its percentage from
    kept_shares and exact the share itself: never 0% for a share above nothing, which says <1%, as the legend's
    shares do."""
    return "<1%" if whole == 0 and exact > 0 else "%d%%" % whole


def kept_shares(P, U, counts=None):
    """What is kept, and production's and tests' shares, as whole percentages of what was written: rounded half
    up, as a reader rounds, not to even as Python does, and the two parts rounded so they add up to what is kept.
    None of them says 100% while anything is missing from it: not what is kept while any line written is gone,
    and not a part while the other holds any line.

    counts: (written, production, tests), from which the shares are taken exactly, as fractions, clamped as
    story_figures clamps them. Without whole numbers there it rounds the shares P and U themselves, in floating
    point, nudged so that an exact half stored just below it (29 of 200 is 14.499999999999998%) still rounds up;
    that nudge could also round up a share less than a billionth of a percent under a half, which takes more than
    500 million lines written."""
    if counts and all(isinstance(n, int) and n >= 0 for n in counts) and counts[0] > 0:
        written, prod, tests = counts
        U = min(Fraction(1), Fraction(prod + tests, written))
        P = min(U, Fraction(prod, written))
        kept = math.floor(100 * U + Fraction(1, 2))
    else:
        kept = int(math.floor(100 * U + 0.5 + 1e-9))
    if kept == 100 and U < 1:   # never all of it while any is gone
        kept = 99
    exact = (100 * P, 100 * (U - P))
    whole = [int(math.floor(v)) for v in exact]
    for k in sorted(range(2), key=lambda k: exact[k] - whole[k], reverse=True)[:max(0, kept - sum(whole))]:
        whole[k] += 1
    for k in range(2):   # a part is everything written only when the other part holds nothing
        if whole[k] == 100 and exact[1 - k] > 0:
            whole[k], whole[1 - k] = 99, whole[1 - k] + 1
    return kept, whole[0], whole[1]


# A headline figure's characters, in em: in the wider at each character of the two bold faces of SANS a viewer
# most likely has (Segoe UI Bold's digits and M, Arial Bold's B and point; k, as every other character, a digit's),
# and in DejaVu Sans Bold, wider than either at every character, which a viewer with neither may fall back to.
# Each was measured with the face set at 1000 units to the em, and rounded up. FIGURE_GAP: the room kept clear
# before a tile's rule.
FIGURE_EM, FIGURE_DIGIT = {"M": 0.96, "B": 0.73, ".": 0.28}, 0.58
FIGURE_EM_WIDEST, FIGURE_DIGIT_WIDEST = {"M": 1.0, "B": 0.77, ".": 0.38, "k": 0.67}, 0.7
FIGURE_GAP = 2


def fitted(s, size, room):
    """The font size a headline figure s is set at, and the length it is held to, or None. How wide a figure is
    drawn depends on the viewer's own font, which cannot be known here. So the size is size, or less when s at
    size would be wider than room in the faces FIGURE_EM measures; and a figure that could still run past room
    in the widest face a viewer may fall back to (FIGURE_EM_WIDEST) is also held to its width in FIGURE_EM, which
    a viewer that reads textLength fits it to exactly in whatever face it has. A viewer that ignores textLength
    falls back on the size alone, which fits in the faces FIGURE_EM measures and may not in a wider one."""
    em = sum(FIGURE_EM.get(ch, FIGURE_DIGIT) for ch in s)
    if size * em > room:
        size = num(math.floor(10.0 * room / em) / 10.0)
    widest = sum(FIGURE_EM_WIDEST.get(ch, FIGURE_DIGIT_WIDEST) for ch in s)
    return size, (math.floor(100.0 * float(size) * em) / 100.0 if float(size) * widest > room else None)


def keyframes(name, prop, stops):
    """@keyframes name, prop taking each value at each of its moments (a second, or a tuple of seconds) of STORY."""
    return "@keyframes %s{%s}" % (name, "".join(
        "%s{%s:%s}" % (",".join(num(100.0 * t / STORY, 2) + "%" for t in (at if isinstance(at, tuple) else (at,))),
                       prop, value) for at, value in stops))


def quantity_head(g, window):
    """The headline where g puts it (WIDE_HEAD or COMPACT_HEAD), drawn at rest, and the story's CSS for the panel's
    style sheet. Every part the story lights has a copy over it, in its color, that fades in and out as a group
    around its glow: fading a shape inside a filter itself makes Chrome and Edge paint a black tile at the
    panel's corner."""
    written, use, prod, tests, P, U = story_figures()
    kept, prod_pct, tests_pct = kept_shares(P, U, (written, prod, tests))
    story = written > 0 and U > 0
    yellow = YELLOW if THEME["dark"] else YELLOW_LITE
    lit = lambda cls, content: ('<g class="cp-q %s" opacity="0">%s</g>' % (cls, glow("glowG", content))
                                if story else "")
    x, y, size = g.kicker
    out = label(x, y, "lines of code · " + WINDOWS[window][1], size=size)

    x0, x1, figure_y, figure_size, word_y, word_size, pad, rule_top, rule_bottom = g.tiles
    width = (x1 - x0) / 4.0
    cells = [(use, "in use", TEXT, "cp-qu", yellow), (prod, "prod", TEXT, "cp-qp", GREEN),
             (tests, "tests", TEXT, "cp-qt", GREEN), (written, "written", MUTED, "cp-qw", RED)]
    for i, (n, word, fill, cls, color) in enumerate(cells):
        tx = x0 + i * width + (pad if i else 0)
        # a figure too wide for its tile is set smaller and held to its width (see fitted), so it runs into no
        # rule and not past the last tile
        s = fmt(n)
        size, length = fitted(s, figure_size, x0 + (i + 1) * width - tx - (FIGURE_GAP if i < 3 else 0))
        out += glow("glowW" if i == 0 else "glowS", text(tx, figure_y, s, size, fill, SANS, 700, length=length))
        out += label(tx, word_y, word, size=word_size) + lit(cls, text(tx, figure_y, s, size, color, SANS, 700,
                                                                       length=length))
        if i:
            out += '<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s"/>' % (
                num(x0 + i * width), num(rule_top), num(x0 + i * width), num(rule_bottom), LINE)

    # the bar: lines with round ends, so a length is a dash; each fill runs from the bar's left end
    bx0, bx1, by, bh = g.bar
    W, yc = bx1 - bx0, by + bh / 2.0
    D = W - bh
    # the dash that shows fraction f of the bar, a dot at least (its round ends are the dot); and its offset under a
    # dash of the whole length, which for a share of 0 puts the whole dash before the line's start, so none shows
    dash = lambda f: max(0.01, f * W - bh)
    off = lambda f: D - dash(f) if f > 0 else D + 1
    whole = "%s %s" % (num(D, 2), num(2 * W, 2))

    def line(color, pattern, offset, cls=""):
        return ('<line%s x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                'stroke-dasharray="%s" stroke-dashoffset="%s"/>'
                % (' class="cp-q %s"' % cls if cls else "", num(bx0 + bh / 2), num(yc), num(bx1 - bh / 2), num(yc),
                   color, num(bh), pattern, num(offset, 2)))
    out += '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s"/>' % (num(bx0), num(by), num(W), num(bh),
                                                                                num(bh / 2), LINE)
    if U > 0:
        out += line(DIM, whole, off(U), "cp-qbs" if story else "")                 # everything written, filled
        out += glow("glowS", line(MUTED, whole, off(U), "cp-qbt" if story else ""))  # tests
        if P > 0:
            out += glow("glowS", line(TEXT, whole, off(P)))                        # production
    out += lit("cp-qw", line(RED, whole, 0)) + lit("cp-qu", line(yellow, "%s %s" % (num(dash(U), 2), num(2 * W, 2)), 0))
    if P > 0:
        out += lit("cp-qp", line(GREEN, "%s %s" % (num(dash(P), 2), num(2 * W, 2)), 0))
    if U > P:   # from production's end; or, when production all but fills the bar, a dot at the line's end
        tail = max(0.01, (U - P) * W - bh)
        out += lit("cp-qt", line(GREEN, "%s %s" % (num(tail, 2), num(2 * W, 2)), -min(P * W, D - tail)))

    # the ring: the same layers around a circle turned to start at the top. As on the bar, a share above 0 shows
    # a dot at least and a share of 0 shows none; C(1 - f) alone would leave a share narrower than the stroke a
    # dash shorter than nothing, which draws nothing at all.
    cx, cy, r, sw, middle_size, middle_word = g.ring
    C = 2 * math.pi * r
    roff = lambda f: C * (1 - f) if f * C - sw >= 0.01 else (C - sw - 0.01 if f > 0 else C)

    def ring(color, pattern, offset, cls=""):
        return ('<circle%s cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" '
                'stroke-dasharray="%s" stroke-dashoffset="%s" transform="rotate(-90 %s %s)"/>'
                % (' class="cp-q %s"' % cls if cls else "", num(cx), num(cy), num(r), color, num(sw), pattern,
                   num(offset, 2), num(cx), num(cy)))
    full = "%s %s" % (num(C - sw, 2), num(2 * C, 2))
    out += '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>' % (num(cx), num(cy), num(r),
                                                                                            LINE, num(sw))
    if U > 0:
        out += ring(DIM, full, roff(U), "cp-qrs" if story else "")
        out += glow("glowS", ring(MUTED, full, roff(U), "cp-qrt" if story else ""))
        if P > 0:
            out += glow("glowS", ring(TEXT, full, roff(P)))
    out += lit("cp-qw", '<circle cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="%s"/>'
               % (num(cx), num(cy), num(r), RED, num(sw)))
    out += lit("cp-qu", ring(yellow, "%s %s" % (num(max(0.01, U * C - sw), 2), num(2 * C, 2)), 0))
    if P > 0:
        out += lit("cp-qp", ring(GREEN, "%s %s" % (num(max(0.01, P * C - sw), 2), num(2 * C, 2)), 0))
    if U > P:
        out += lit("cp-qt", ring(GREEN, "%s %s" % (num(max(0.01, (U - P) * C - sw), 2), num(2 * C, 2)), -P * C))

    # the ring's middle: what is kept at rest, and in the story, 100%, then kept, then production, then tests, each
    # as share_label writes it
    def middle(cls, share, word, shown):
        if not story and not shown:
            return ""
        fy = cy + middle_size * (0.2 if middle_word else 0.36)
        s = glow("glowS", text(cx, fy, share, middle_size, TEXT, SANS, 700, "middle"))
        if middle_word and word:
            s += label(cx, fy + middle_word + 6, word, "middle", size=middle_word)
        if not story:
            return s
        return '<g class="cp-q %s"%s>%s</g>' % (cls, "" if shown else ' opacity="0"', s)
    out += middle("cp-qmk", share_label(kept, U), "kept", True) + middle("cp-qmw", "100%", None, False)
    out += (middle("cp-qmp", share_label(prod_pct, P), "prod", False)
            + middle("cp-qmt", share_label(tests_pct, U - P), "tests", False))
    if not story:
        return out, ""

    # the story: each move between its marks, each glow rising, holding and settling after its move
    bar_at = lambda f: num(off(f), 2)
    ring_at = lambda f: num(roff(f), 2)
    fill = lambda at: [((0, STORY_FILL[0]), at(U)), ((STORY_FILL[1], STORY_UNFILL[0]), at(1.0)),
                       ((STORY_UNFILL[1], STORY_DOWN[0]), at(U)), ((STORY_DOWN[1], STORY_UP[0]), at(P)),
                       ((STORY_UP[1], STORY), at(U))]
    parts = lambda at: [((0, STORY_DOWN[0]), at(U)), ((STORY_DOWN[1], STORY_UP[0]), at(P)), ((STORY_UP[1], STORY), at(U))]
    pulse = lambda t: [((0, t), 0), ((t + STORY_RISE, t + STORY_RISE + STORY_HOLD), 1),
                       ((t + STORY_RISE + STORY_HOLD + STORY_FADE, STORY), 0)]
    swap = STORY_SWAP
    tests_end = STORY_UP[1] + STORY_RISE + STORY_HOLD + STORY_FADE
    rules = [
        ("cp-qbs", "stroke-dashoffset", fill(bar_at)), ("cp-qbt", "stroke-dashoffset", parts(bar_at)),
        ("cp-qrs", "stroke-dashoffset", fill(ring_at)), ("cp-qrt", "stroke-dashoffset", parts(ring_at)),
        ("cp-qw", "opacity", pulse(STORY_FILL[1])), ("cp-qu", "opacity", pulse(STORY_UNFILL[1])),
        ("cp-qp", "opacity", pulse(STORY_DOWN[1])), ("cp-qt", "opacity", pulse(STORY_UP[1])),
        ("cp-qmk", "opacity", [((0, STORY_FILL[0]), 1), ((STORY_FILL[0] + swap, STORY_UNFILL[1] - swap), 0),
                               ((STORY_UNFILL[1], STORY_DOWN[0]), 1), ((STORY_DOWN[0] + swap, tests_end), 0),
                               ((tests_end + swap, STORY), 1)]),
        ("cp-qmw", "opacity", [((0, STORY_FILL[1] - swap), 0), ((STORY_FILL[1], STORY_UNFILL[0]), 1),
                               ((STORY_UNFILL[0] + swap, STORY), 0)]),
        ("cp-qmp", "opacity", [((0, STORY_DOWN[1] - swap), 0), ((STORY_DOWN[1], STORY_UP[0]), 1),
                               ((STORY_UP[0] + swap, STORY), 0)]),
        ("cp-qmt", "opacity", [((0, STORY_UP[1] - swap), 0), ((STORY_UP[1], tests_end), 1), ((tests_end + swap, STORY), 0)]),
    ]
    css = "".join(keyframes(name, prop, stops) + ".%s{animation:%s %ss ease-in-out infinite}" % (name, name, num(STORY))
                  for name, prop, stops in rules)
    return out, css


def headline_block(g, window, S, spark, since, commits, right, divider):
    """The headline (quantity_head), and under it the activity bars with their bursts, their dates and their key.
    right: where the bars' right date ends; divider: the wide panel's rule between the headline and the rows,
    or "". Returns the drawing and the story's CSS."""
    out, story = quantity_head(g, window)
    x0, span, base, reach, burst_size, keep_clear = g.bars
    bars, tops = activity_bars(spark, commits, x0, span, base, reach)
    out += glow("glowG", bars) + burst_labels(spark, tops, [(0, 0, right + 12, keep_clear)], x0, span, burst_size)
    y, size, (key_x, box, pad, gap) = g.dates
    out += label(x0, y, since or span_words(S), size=size) + label(right, y, AS_OF or "today", "end", size=size)
    if commits and any(commits):   # the key, between the start and today
        out += bars_key(key_x, y, size, box, pad, gap)
    return out + divider, story


def stats_block(window, S, new_lines, spark, rows, since=None, commits=None):
    """The headline and its bars (headline_block), the column rule and the stats rows. since: the day the bars
    start, written out; without it, how long ago. commits: commits per bar. Lines of code rise in green above
    the bars' baseline and commits hang in red below it, each scaled to its own peak. Returns the drawing and
    the story's CSS."""
    out, story = headline_block(WIDE_HEAD, window, S, spark, since, commits, 280,
                                '<line x1="292" y1="42" x2="292" y2="156" stroke="%s"/>' % LINE)
    return out + stats_rows(rows), story


def stats_rows(rows):
    """The stats rows where ROWS puts them: each name, its leader, the dot that hops along it and the value,
    which lights as the dot arrives."""
    g, out = ROWS, ""
    trip, starts = hop_plan(rows)
    for i, (name, value) in enumerate(rows):
        y = g.top + i * g.pitch
        start, n = leader(name, value)
        out += label(g.x, y, name, size=g.name)
        if n:
            # The leader is one line whose dashes are squares. The dot is a second, green line on it with
            # one dash, which hops a square at a time and then off the end, where it waits out the loop;
            # at rest it sits one square before the start, so a frozen clock shows the plain row.
            seg = ('x1="%s" y1="%d" x2="%s" y2="%d" stroke-width="%s" stroke-linecap="square"'
                   % (num(start + 0.8, 2), y - g.rise, num(start + 0.81 + (n - 1) * BIT_PITCH, 2), y - g.rise,
                      num(g.dot, 2)))
            out += '<line %s stroke="%s" stroke-dasharray=".01 %s"/>' % (seg, DIM, num(BIT_PITCH - 0.01, 2))
            out += glow("glowG", '<line class="cp-hop" %s stroke="%s" stroke-dasharray=".01 %s" '
                        'stroke-dashoffset="%s" style="animation-delay:%ss"/>'
                        % (seg, GREEN, num(trip * BIT_PITCH - 0.01, 2), num(BIT_PITCH), num(starts[i], 2)))
        out += glow("glowS", text(g.right, y, value, g.value, TEXT, SANS, 600, "end"))
        if n:   # the value lights as the dot leaves the last square
            out += ('<g class="cp-ping" opacity="0" style="animation-delay:%ss">%s</g>'
                    % (num(starts[i] + (n + 1) * HOP, 2),
                       glow("glowG", text(g.right, y, value, g.value, GREEN, SANS, 600, "end"))))
    return out


# The Pareto line draws itself: it grows from its left end at a pace set by how fast lines were being
# written at each point, racing through a burst and crawling across quiet time, then holds, fades and grows
# again. The loop starts partway through the hold, so the first frame, and a frozen clock, show it whole.
GROW, GROW_HOLD, GROW_FADE, GROW_LEAD = 5.0, 6.0, 0.8, 1.5   # seconds: growing, whole, fading; whole at first
GROW_FLOOR = 0.25    # the slowest pace, as a share of the fastest, so quiet time still moves
GROW_WINDOW = 8      # the writing rate at a point is judged over this many samples either side of it
GROW_EPS = 1.0       # panel units the drawn length may stray between two keyframes


def pareto(stream, S, c):
    """The running share of every line in the chart, from 0% at its left edge to 100% at the 0 line, laid
    over the stream: thin and bright, no glow and no label, stepped, since lines arrive in commits.
    Returns the line and the keyframes it grows by."""
    ev = sorted(((a, n) for a, _, n in stream if n > 0), key=lambda e: e[0])   # youngest first
    total = float(sum(n for _, n in ev))
    if total <= 0:
        return "", ""
    ages, upto, run_sum = [a for a, _ in ev], [], 0
    for _, n in ev:
        run_sum += n
        upto.append(run_sum)

    def written_before(d):
        k = bisect.bisect_right(ages, d)
        return (total - (upto[k - 1] if k else 0)) / total

    N = 480
    days = [c * ((1 + S / c) ** (1 - i / float(N)) - 1) for i in range(N + 1)]
    share = [written_before(d) for d in days[:-1]] + [1.0]
    pts = [(X0 if i == 0 else x_of_age(d, S, c), T1 - (T1 - T0) * v) for i, (d, v) in enumerate(zip(days, share))]
    # a point in the middle of a flat run adds nothing, so only the corners are kept
    keep = [p for k, p in enumerate(pts) if k in (0, N) or p[1] != pts[k - 1][1] or p[1] != pts[k + 1][1]]
    line = ('<polyline class="cp-grow" points="%s" fill="none" stroke="%s" stroke-width="1.3" '
            'stroke-linejoin="round"/>' % (" ".join("%s,%s" % (num(x), num(y)) for x, y in keep), RED))

    # The pace along each stretch: lines per day written around it, judged over at least a whole day so the
    # hours just past cannot outrun everything, square-rooted so one burst does not leave the rest standing.
    rates = []
    for i in range(N):
        hi, lo = days[max(0, i - GROW_WINDOW)], days[min(N, i + GROW_WINDOW + 1)]
        if hi - lo < 1.0:
            mid = (hi + lo) / 2
            lo, hi = max(0.0, mid - 0.5), min(S, max(0.0, mid - 0.5) + 1.0)
        rates.append((written_before(lo) - written_before(hi)) * total / max(hi - lo, 1e-9))
    fastest = max(rates) or 1.0
    marks, t, s = [(0.0, 0.0)], 0.0, 0.0
    for i in range(N):
        seg = math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
        t += seg / (GROW_FLOOR + (1 - GROW_FLOOR) * math.sqrt(max(0.0, rates[i]) / fastest))
        s += seg
        marks.append((t, s))
    length = s + 2   # the dash is a little longer than the line, so whole means whole
    marks = simplify([(GROW * tt / (t or 1.0), ss) for tt, ss in marks], GROW_EPS)
    cycle = GROW + GROW_HOLD + GROW_FADE
    pct = lambda sec: num(100.0 * sec / cycle, 3)
    css = ("@keyframes cp-grow{0%%{stroke-dashoffset:%s;opacity:1}%s%s%%{stroke-dashoffset:0}%s%%{opacity:1}"
           "100%%{stroke-dashoffset:0;opacity:0}}.cp-grow{stroke-dasharray:%s %s;"
           "animation:cp-grow %ss linear -%ss infinite}"
           % (num(length), "".join("%s%%{stroke-dashoffset:%s}" % (pct(tt), num(length - ss)) for tt, ss in marks[1:-1]),
              pct(GROW), pct(GROW + GROW_HOLD), num(length), num(length), num(cycle, 2),
              num(GROW + GROW_HOLD - GROW_LEAD, 2)))
    return line, css


FOLD = 0.01            # a language under this share of the window's lines is drawn as Other
EDGE_EPS = 0.03        # panel units a layer's written boundary may stray from the exact one
VEIL_EPS = 0.004       # the veil's opacity may stray this much where a stop is left out
MIN_CONTRAST = 1.35    # the now line gets a dark casing across any band it would nearly vanish into


def empty_words(window, has_history):
    """What the chart says when the window holds no lines: that older work exists, or that the account's own
    repositories hold none that counts (its commits may still be there, in notebooks or data, or its code in
    repositories it does not own)."""
    return ("nothing in the last " + WINDOWS[window][1] if has_history else
            "no counted code in selected repos" if organization_settings()[0] else "no counted code in own repos")


def stream_block(window, stream, column, S, c, has_history, recent_day=None):
    """The language mix on the log axis, flowing into a column for the whole window that is also the
    legend. stream: (age in days, language, lines) within the chart's span; column: every line in the
    window, strays included. Returns the drawing and the Pareto line's keyframes."""
    out = label(16, 192, "language mix · share of lines of code") + window_selector(window)
    if not stream:
        return out + text(222, 300, empty_words(window, has_history), 12, MUTED, MONO, 400, "middle"), ""
    chart, grow, order, shown = mix_chart(stream, column, S, c, recent_day)
    return out + chart + side_legend(order, shown), grow


def mix_chart(stream, column, S, c, recent_day=None, tick_size=8, grid_size=8):
    """The chart itself, wherever X0, X1, XC, XW, T0, T1, AXIS_Y and TICK_Y put it: the mix and its column,
    the veil, the Pareto line, the 0 line and the axis with its ticks. Returns the drawing, the Pareto
    line's keyframes, each layer as (language, the middle of its band in the column, its share) from the
    top down, and each language's share as the legend writes it."""
    totals, small = folded(column)
    if small:   # slivers are drawn as Other, so the legend lists only what can be seen
        stream = [(a, OTHER if l in small else l, n) for a, l, n in stream]
    top, layers, amount = legend_layers(totals)
    assign_colors(layers)
    grand = float(sum(amount.values()))
    xs, shares, conf, stretches = mix_along(stream, S, c, layers, top, recent_day)
    y_of = lambda v: T1 - (T1 - T0) * v

    # Each layer is drawn as the shape under its upper boundary, run on past the plot's left and bottom and
    # through its ribbon into the column. Filled from the top layer down, each covers the layers above it
    # below its own boundary, so every boundary is written once; the same shapes stroked in the background
    # color draw the seams, and one mask trims everything to the plot. (A mask, not a clip: at a phone's
    # fractional scale a clip would stack every layer's anti-aliased edge on the plot's bottom row.)
    base, col_base, shapes, mids = [0.0] * len(xs), 0.0, "", []
    for j, lang in enumerate(layers):
        upper = [b + shares[j][i] for i, b in enumerate(base)]
        col_top = col_base + amount[lang] / grand
        edge = simplify([(x, y_of(u)) for x, u in zip(xs, upper)], EDGE_EPS)
        ue, ct = y_of(upper[-1]), y_of(col_top)
        shapes += ('<path id="cp-L%d" d="M%d,%sH%d%sC%s,%s %s,%s %d,%sH%dV%dH%dZ"/>'
                   % (j, X0 - 6, num(edge[0][1]), X0, rel_run(edge), X1 + 12, num(ue), XC - 12, num(ct), XC,
                      num(ct), XW + 6, T1 + 6, X0 - 6))
        mids.append((lang, (ct + y_of(col_base)) / 2, amount[lang] / grand))
        base, col_base = upper, col_top
    down = range(len(layers) - 1, -1, -1)
    mix = ('<defs><mask id="cp-plot" maskUnits="userSpaceOnUse" x="0" y="0" width="%d" height="%d"><rect x="%d" '
           'y="%d" width="%d" height="%d" fill="#fff"/></mask>%s</defs><g mask="url(#cp-plot)">%s<g fill="none" '
           'stroke="%s">%s</g></g>'
           % (PANEL_W, PANEL_H, X0, T0 - 1, XW - X0, T1 - T0 + 1, shapes,
              "".join('<use href="#cp-L%d" fill="%s"/>' % (j, LAYER_COLORS[layers[j]]) for j in down), BG,
              "".join('<use href="#cp-L%d"/>' % j for j in down)))

    # the veil: the background laid over the stream, as opaque as the mix is inferred rather than seen. Its
    # gradient runs over 1000 units, so a stop at any whole x is exact at three decimals.
    stops = simplify([(x - X0, VEIL * (1 - cf)) for x, cf in zip(xs, conf)], VEIL_EPS)
    veil = ('<defs><linearGradient id="veil" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">%s'
            '</linearGradient></defs><rect x="%d" y="%d" width="%d" height="%d" fill="url(#veil)"/>'
            % (X0, X0 + 1000, "".join('<stop offset="%s" stop-color="%s" stop-opacity="%s"/>'
                                      % (num(x / 1000.0, 3), BG, num(o, 3)) for x, o in stops),
               X0, T0, PLOT_W, T1 - T0))

    order = sorted(mids, key=lambda m: m[1])
    shown = percents({lang: share for lang, _, share in order})

    # 100%, 50% and 0% in the gutter; no rule across the plot, since the stream always covers it
    grid = "".join('<text x="%d" y="%.1f" text-anchor="end" font-family="%s" font-size="%s" fill="%s">%s</text>'
                   % (X0 - 6, y_of(v) + 3, MONO, grid_size, MUTED, s)
                   for v, s in ((1, "100%"), (0.5, "50%"), (0, "0%")))
    # the 0 line: where the dated stream ends and the ribbon into the column begins. Across a band too close
    # to its own color it gets a casing, outside the glow so the casing does not bloom.
    alpha = ".95" if THEME["dark"] else ".6"
    casing, b = "", 0.0
    for j, lang in enumerate(layers):
        v = shares[j][-1]
        if v > 0.002 and contrast(over(TEXT, float(alpha), LAYER_COLORS[lang]), LAYER_COLORS[lang]) < MIN_CONTRAST:
            casing += ('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="%s" stroke-opacity=".5" stroke-width="2.6"/>'
                       % (X1, num(y_of(b + v)), X1, num(y_of(b)), BG))
        b += v
    zero = casing + glow("glowW", '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity="%s"/>'
                         % (X1, T0 - 2, X1, AXIS_Y, TEXT, alpha))
    axis = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (X0, AXIS_Y, X1, AXIS_Y, LINE)
    for v in pick_ticks(S, c, stretches):
        x = X0 if v == S else x_of_age(v, S, c)
        ink = TEXT if v == 0 else MUTED   # now in the text color, the foot of the 0 line
        axis += ('<circle cx="%.1f" cy="%d" r="2.4" fill="%s"/>' % (x, AXIS_Y, ink)
                 + label(x, TICK_Y, tick_label(v, S), "start" if v == S else "middle", ink, tick_size))
    line, grow = pareto(stream, S, c)
    return grid + mix + veil + line + zero + axis, grow, order, shown


def legend_layers(totals):
    """The chart's layers, from a window's lines per language as folded gives them: the TOP_N biggest languages
    by name, then Other when any language is left over. Returns the languages named, the layers, biggest first,
    and the lines each layer draws, Other's holding every language not named. card_data takes the data file's
    legend from the same, so it says what the chart and its legends draw."""
    top = [lang for lang, _ in totals.most_common() if lang != OTHER][:TOP_N]
    layers = top + ([OTHER] if any(l not in top for l in totals) else [])
    amount = {lang: (sum(v for l, v in totals.items() if l not in top) if lang == OTHER else totals[lang])
              for lang in layers}
    return top, layers, amount


def legend_name(lang):
    """How the legends write a language: in lowercase, and by its LEGEND_NAMES name where it has one."""
    return LEGEND_NAMES.get(lang, lang).lower()


def side_legend(order, shown):
    """The wide panel's legend beside the column: labels keep their band's height where they can, spread
    apart so none collide, stay inside the plot, and an elbow leader ties each one to its band."""
    top_y, bottom_y = T0 + 4, T1 + 2
    gap = min(13.0, (bottom_y - top_y) / float(max(1, len(order) - 1)))
    ys = []
    for _, y, _ in order:
        ys.append(max(y, top_y, (ys[-1] + gap) if ys else top_y))
    for i in range(len(ys) - 1, -1, -1):
        ys[i] = min(ys[i], bottom_y if i == len(ys) - 1 else ys[i + 1] - gap)
    legend = ""
    for (lang, y, share), ly in zip(order, ys):
        legend += ('<path d="M%d,%.1f H%d V%.1f H%d" stroke="%s" fill="none"/>%s%s'
                   % (XW + 2, y, XW + 5, ly - 3.5, XW + 9, DIM,
                      text(454, ly, legend_name(lang), 10.5, TEXT, MONO, 500),
                      text(560, ly, shown[lang], 10.5, MUTED, MONO, 400, "end")))
    return legend


# Every mark is drawn in its final state. A browser freezes the animation clock of an SVG image in a
# background tab, and some viewers never start it, so an intro that fades or grows things in shows a
# blank panel there. Motion only adds to a finished panel: today's bar breathes like the widget's
# equalizer, starting at full opacity; in the stats rows one dot at a time hops along a leader's squares
# and its value lights green as the dot arrives; the Pareto line grows (see GROW). The dots and the lit
# values rest invisible, and the Pareto line's loop starts with it whole.
BIT_PITCH = 4.5                            # the leader's squares, apart
HOP, HOP_REST, HOP_END = 0.12, 0.6, 3.0    # seconds: on each square, after a value lights, before the rows go again
PING = (0.12, 1.0, 1.5)                    # seconds: a value is fully lit by, lit until, and out by


def style_sheet(rows, grow):
    """The panel's one style sheet, all inside prefers-reduced-motion: no-preference. Every name carries
    the cp- prefix, since the relay puts the panel and the music card in one document."""
    trip = hop_plan(rows)[0]
    loop = trip * HOP
    pct = lambda sec: num(100.0 * sec / loop, 3)
    return ("@media (prefers-reduced-motion: no-preference){"
            "@keyframes cp-breathe{50%{opacity:.45}}.cp-now{animation:cp-breathe 1.8s ease-in-out infinite}"
            + "@keyframes cp-hop{from{stroke-dashoffset:%s}to{stroke-dashoffset:%s}}" % (
                num(BIT_PITCH), num(BIT_PITCH * (1 - trip), 2))
            + ".cp-hop{animation:cp-hop %ss steps(%d) infinite}" % (num(loop, 2), trip)
            + "@keyframes cp-ping{0%%{opacity:0}%s%%,%s%%{opacity:.9}%s%%,100%%{opacity:0}}" % (
                pct(PING[0]), pct(PING[1]), pct(PING[2]))
            + ".cp-ping{animation:cp-ping %ss linear infinite}" % num(loop, 2)
            + grow + "}")


def folded(column):
    """Lines per language over the window, with every language under FOLD of them counted as Other, and
    the set of languages folded."""
    totals = Counter()
    for _, lang, n in column:
        totals[lang] += n
    small = {l for l, v in totals.items() if l != OTHER and v < FOLD * sum(totals.values())}
    for l in small:
        totals[OTHER] += totals.pop(l)
    return totals, small


def words(window, new_lines, spark, rows, column, since=None):
    """The panel's title and description for screen readers, in sentences, every number and date it draws."""
    span = "all time" if window == "all" else "the last " + WINDOWS[window][1]
    written, use, prod, tests, P, U = story_figures() if QUANTITY else (new_lines, 0, 0, 0, 0.0, 0.0)
    lines = "line" if use == 1 else "lines"
    title = "coderprint: %s %s of code in use, of %s written, %s" % (fmt(use), lines, fmt(written), span)
    phrases = {"commits · all branches": "{v} commits across all branches", "active days": "{v} active days",
               "longest streak": "a longest streak of {v}", "current streak": "a current streak of {v}",
               LANGUAGES_ROW: LANGUAGES_WORDS[0]}
    one = {"commits · all branches": "1 commit across all branches", "active days": "1 active day",
           LANGUAGES_ROW: LANGUAGES_WORDS[1]}
    stats = [one[name] if value == "1" and name in one else phrases.get(name, name + " {v}").format(v=value)
             for name, value in rows]
    desc = "%s %s of code in use (%s in production, %s in tests), of %s written (%s%s)" % (
        "{:,}".format(use), lines, "{:,}".format(prod), "{:,}".format(tests), "{:,}".format(written), span,
        ", charted since %s" % since if since else "")
    desc += (": " + ", ".join(stats[:-1]) + (", and " if len(stats) > 1 else "") + stats[-1] + ".") if stats else "."
    groups = bursts(spark)
    if len(groups) > 1:
        sizes = [fmt(g[2]) for g in groups]
        desc += " They came in %d bursts of %s and %s lines of code." % (len(groups), ", ".join(sizes[:-1]), sizes[-1])
    # the day the bars end on, as drawn at their right end; the README's alt text is given no bars, so it names
    # no date, and a day passing changes nothing in the README by itself
    if AS_OF and spark:
        desc += " The bars end on %s, the day this panel was drawn." % AS_OF
    totals, _ = folded(column)
    if totals:
        top = [l for l, _ in totals.most_common() if l != OTHER][:TOP_N]
        amount = {l: totals[l] for l in top}
        rest = sum(v for l, v in totals.items() if l not in top)
        if rest:
            amount[OTHER] = rest
        grand = float(sum(amount.values()))
        shown = percents({l: v / grand for l, v in amount.items()})
        desc += " Share of lines of code by language: %s." % ", ".join(
            "%s %s" % ("other languages" if l == OTHER else l, shown[l].replace("<1%", "under 1%"))
            for l in sorted(amount, key=lambda l: (l == OTHER, -amount[l])))
    if QUANTITY and written > 0:   # the ring's middle, in words too
        kept = kept_shares(P, U, (written, prod, tests))[0]
        desc += " Of what was written, %s is kept." % share_label(kept, U).replace("<1%", "under 1%")
    return title, desc


def alt_text(window, new_lines, rows):
    """The README image's alternative text: the headline and the stats in words."""
    title, desc = words(window, new_lines, [], rows, [])
    return "%s; %s" % (title, desc[desc.index(": ") + 2:].rstrip(".")) if ": " in desc else title
