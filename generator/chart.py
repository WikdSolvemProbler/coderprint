# coderprint's numbers, days and the language mix along the chart's log axis. coderprint.py runs this file as part of
# one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- numbers


def fmt(n):
    """1,234 as 1.2k, 56,789 as 57k, 1,234,567 as 1.2M, 12,345,678,901 as 12.3B; rounded first, so nothing
    prints as 1000k or 1000.0M."""
    if n < 1000:
        return str(int(round(n)))
    k = n / 1e3
    if round(k, 1) < 10:
        return "%.1fk" % k
    if round(k) < 1000:
        return "%.0fk" % k
    if round(n / 1e6, 1) < 1000:
        return "%.1fM" % (n / 1e6)
    return "%.1fB" % (n / 1e9)


def plural(n, word):
    return "{:,} {}{}".format(n, word, "" if n == 1 else "s")


def span_words(S):
    """How long ago a span of S days began, rounded up: whole days, or whole hours when under a day."""
    if S < 1:
        return plural(max(1, math.ceil(S * 24 - 1e-9)), "hour") + " ago"
    return plural(math.ceil(S - 1e-9), "day") + " ago"


MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def moment(t, zone):
    """The moment t, in seconds from the epoch, as a time in zone: what datetime.fromtimestamp gives, but also
    before the epoch on Windows, whose clock functions refuse more than 12 hours before it, and where the start
    of a commit's day falls when the commit is dated on the first day of 1970 anywhere west of UTC."""
    return (EPOCH + dt.timedelta(seconds=t)).astimezone(zone)


def day_start(t, zone):
    """The start of the calendar day in zone that the moment t falls on."""
    return moment(t, zone).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def first_day(t, zone):
    """The start of the first calendar day in zone that begins at or after the moment t: where a window reaching back
    to t starts, so a day is inside the window or outside it, never cut at the hour the run happens to start, and a
    commit's day is inside exactly when the commit is: day_start(x) >= first_day(t) exactly when x >= first_day(t)."""
    d = day_start(t, zone)
    return d if d >= t else day_start(d + 36 * 3600, zone)   # 36 hours on is the next day, however long a day is


def day_label(t, zone):
    """A moment's calendar day in zone, written the house way: 06MAR2026."""
    d = moment(t, zone).date()
    return "%02d%s%d" % (d.day, MONTHS[d.month - 1], d.year)


def activity(times, now, zone=dt.timezone.utc):
    """Active days, the longest streak and the current streak, over the days with a commit, as calendar
    days in zone (see local_zone). The current streak may end yesterday, since today is not over. A commit
    dated up to FUTURE_SLACK ahead counts as today, so a fast clock cannot open a gap in the streak."""
    today = moment(now, zone).date()
    days = sorted({min(moment(t, zone).date(), today) for t in times})
    if not days:
        return 0, 0, 0
    longest = run_len = 0
    prev = None
    for d in days:
        run_len = run_len + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run_len)
        prev = d
    have, d, current = set(days), days[-1], 0
    if (today - d).days <= 1:
        while d in have:
            current += 1
            d -= dt.timedelta(days=1)
    return len(days), longest, current


def percents(shares):
    """Whole percentages for the legend by largest remainder, so the column's labels add up; anything
    under 1% says so instead."""
    big = {k: 100.0 * v for k, v in shares.items() if v >= 0.01}
    out = {k: int(math.floor(v)) for k, v in big.items()}
    short = int(round(sum(big.values()))) - sum(out.values())
    for k in sorted(big, key=lambda k: big[k] - out[k], reverse=True)[:max(0, short)]:
        out[k] += 1
    return {k: ("%d%%" % out[k] if k in out else "<1%") for k in shares}


def real_work(events):
    """The age in days of the oldest and of the newest real work. A real day is a 24-hour slice, counted
    back from now, holding at least max(10, 5% of the median active day) lines. The oldest real work
    skips any oldest group cut off from the rest by more than a year and holding under 1% of all lines,
    so a stray commit cannot stretch the axis. The newest is judged against the newest 30 active days
    instead, so a quieter present still counts as recent work after a prolific past.
    events: (age in days, language, lines)."""
    per_day = Counter()
    for a, _, n in events:
        per_day[int(a)] += n
    active = sorted(per_day.values())
    floor = max(10, 0.05 * active[len(active) // 2])
    real = sorted((d for d, n in per_day.items() if n >= floor), reverse=True) or sorted(per_day, reverse=True)
    total = float(sum(per_day.values()))
    older_lines, acc = {}, 0
    for d in sorted(per_day, reverse=True):
        acc += per_day[d]
        older_lines[d] = acc   # lines written on this day or earlier
    start = real[0]
    for k, (older, newer) in enumerate(zip(real, real[1:])):
        # a stray group is small in every sense: cut off, a sliver of the total, and a few days at most
        if older - newer > 365 and older_lines[older] < 0.01 * total and k + 1 <= 3:
            start = newer
    # "recent" is the active days within 90 days of the newest one, so a quieter present is judged on its own
    recent = [d for d in per_day if d <= min(per_day) + 90]
    rv = sorted(per_day[d] for d in recent)
    recent_day = rv[len(rv) // 2]
    kfloor = max(10, 0.05 * recent_day)
    knee_day = min((d for d, n in per_day.items() if n >= kfloor), default=min(per_day))
    oldest = max(a for a, _, _ in events if int(a) == start)
    newest = min(a for a, _, _ in events if int(a) == knee_day)
    return oldest, newest, float(recent_day)


def knee(newest, S):
    """The log axis's knee c. One day while the work is recent. Otherwise large enough that the silence
    since the newest real work takes at most half the width, and a straight axis when even that cannot
    hold (the silence is then over half of the whole span, and is drawn at its true share)."""
    if newest <= 1:
        return 1.0
    if S > 2 * newest:
        return max(1.0, newest, newest * newest / (S - 2 * newest))
    return 1e9


# ---------------------------------------------------------------- the mix along the log axis


def x_of_age(d, S, c):
    """Where d days ago sits: x1 is now, x0 is S days ago, log(1 + d/c) in between."""
    return X1 - PLOT_W * math.log1p(d / c) / math.log1p(S / c)


def assign_colors(layers):
    """Each layer's color. A language keeps its own (COLORS) whatever else is drawn, unless it would come
    within MIN_APART of a language ranked above it. Then it takes the SPARE color nearest its own among
    those clear of every color already given and of the own colors of the layers still to come, so one move
    does not set off another; failing that, the nearest clear of those given; failing that, the one farthest
    from them. Markdown and Other take the theme's prose and other colors, and those count as given from
    the start, since a pale lite's prose or Other can sit within MIN_APART of a language color (Oxblood's
    lite prose is 2.8 from #ad959a). So a language's color turns on the day's theme only where it would
    otherwise be drawn beside a near twin."""
    LAYER_COLORS.clear()
    taken = ([THEME["prose"]] if any(l in PROSE for l in layers) else []) + ([OTHER_COLOR] if OTHER in layers else [])
    for k, lang in enumerate(layers):
        if lang == OTHER:
            color = OTHER_COLOR
        elif lang in PROSE:
            color = THEME["prose"]
        else:
            own = color = COLORS.get(lang)
            if own is None or any(delta_e(own, c) < MIN_APART for c in taken):
                later = [COLORS[l] for l in layers[k + 1:] if l in COLORS]
                clear = lambda c, others: all(delta_e(c, t) >= MIN_APART for t in others)
                pool = [c for c in SPARE if clear(c, taken + later)] or [c for c in SPARE if clear(c, taken)]
                if pool:
                    color = min(pool, key=lambda c: delta_e(c, own)) if own else pool[0]
                else:
                    color = max(SPARE, key=lambda c: min(delta_e(c, t) for t in taken))
            taken.append(color)
        LAYER_COLORS[lang] = color


def wmedian(pairs):
    pairs = sorted(pairs)
    half = sum(w for _, w in pairs) / 2.0
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= half:
            return v
    return pairs[-1][0]


def mix_along(events, S, c, layers, top, recent_day=None):
    """events: (age in days, language, lines), all within S days. Returns one x per panel unit across
    the plot, each layer's share at every x, the confidence at every x, and the quiet stretches.

    The share at x is a Gaussian-kernel mix of the lines written near x on the log axis, pulled toward a
    bridge: straight lines between anchor mixes, held flat past the first and last. Evidence is lines
    per day: the kernel spans weeks of the distant past but hours of today, so its mass is divided by
    the time it covers (never less than a day) before it is compared with alpha, and steady work reads
    as steady everywhere. Anchors are the slices with enough evidence. They go in strongest first, and
    an anchor's own mix counts in full from confidence 0.7 up and fades to nothing at 0.5, where its
    value is exactly what the stronger anchors already give there, so a slice crossing the bar changes
    nothing abruptly. Where much was written the kernel dominates; where little or nothing was, the
    bridge does, so a quiet stretch eases from one period of work to the next and a single tiny commit
    cannot pin it. Each share is a convex combination of real mixes, so every x sums to exactly 100%."""
    L = len(layers)
    idx = {l: i for i, l in enumerate(layers)}
    li = lambda lang: idx[lang] if lang in top else idx[OTHER]
    U = math.log1p(S / c)
    bins = {}
    for a, lang, n in events:
        k = min(NBINS - 1, int(math.log1p(a / c) / U * NBINS))
        b = bins.get(k)
        if b is None:
            b = bins[k] = {"u": (k + 0.5) * U / NBINS, "vec": [0.0] * L, "tot": 0.0, "amin": a, "amax": a}
        b["vec"][li(lang)] += n
        b["tot"] += n
        b["amin"], b["amax"] = min(b["amin"], a), max(b["amax"], a)
    blist = sorted(bins.values(), key=lambda b: b["u"])
    us = [b["u"] for b in blist]
    h = U * H_X / PLOT_W
    x_of_u = lambda u: X1 - PLOT_W * u / U
    span = lambda u: max(1.0, h * c * math.exp(u))   # the kernel's width in days there, h * (c + d)

    def mass(u, hh=h):
        m, t = [0.0] * L, 0.0
        # six widths either side: a slice entering the window weighs exp(-18), so no visible step
        for b in blist[bisect.bisect_left(us, u - 6 * hh):bisect.bisect_right(us, u + 6 * hh)]:
            w = math.exp(-0.5 * ((u - b["u"]) / hh) ** 2)
            t += w * b["tot"]
            for j, v in enumerate(b["vec"]):
                if v:
                    m[j] += w * v
        return m, t

    def density(u, t_narrow):
        """Lines per day around u, over a kernel at least a day wide: near now the drawing kernel spans
        only hours, and the hours between two commits must not read as a lack of evidence."""
        wide = 1.0 / (c * math.exp(u))
        if wide > h:
            window = blist[bisect.bisect_left(us, u - 6 * wide):bisect.bisect_right(us, u + 6 * wide)]
            t_narrow = sum(math.exp(-0.5 * ((u - b["u"]) / wide) ** 2) * b["tot"] for b in window)
        return t_narrow / span(u)

    masses = [mass(b["u"]) for b in blist]
    dens = [density(b["u"], t) for (_, t), b in zip(masses, blist)]
    # significance is judged against the typical day, or against the recent typical day if that is lower,
    # so a quieter present after a prolific past still anchors its own mix
    typical = wmedian([(q, b["tot"]) for q, b in zip(dens, blist)])
    alpha = max(ALPHA_FRAC * (min(typical, recent_day) if recent_day else typical), 1e-9)
    confs = [q / (q + alpha) for q in dens]
    anc_x, anc_v = [], []

    def bridge(x):
        if x <= anc_x[0]:
            return anc_v[0]
        if x >= anc_x[-1]:
            return anc_v[-1]
        k = bisect.bisect_right(anc_x, x) - 1
        s = (x - anc_x[k]) / (anc_x[k + 1] - anc_x[k])
        return [(1 - s) * p + s * q for p, q in zip(anc_v[k], anc_v[k + 1])]

    order = sorted((i for i, cf in enumerate(confs) if cf >= 0.5), key=lambda i: (-confs[i], blist[i]["u"]))
    if not order:
        order = [max(range(len(blist)), key=lambda i: masses[i][1])]
    for i in order:
        m, t = masses[i]
        q = [v / t for v in m]
        lam = min(1.0, max(0.0, (confs[i] - 0.5) / 0.2))
        lam = lam * lam * (3 - 2 * lam)
        xb = x_of_u(blist[i]["u"])
        v = q if not anc_x else [lam * p + (1 - lam) * r for p, r in zip(q, bridge(xb))]
        k = bisect.bisect_left(anc_x, xb)
        anc_x.insert(k, xb)
        anc_v.insert(k, v)

    xs = [X0 + i for i in range(PLOT_W + 1)]
    shares, conf = [[0.0] * len(xs) for _ in range(L)], [0.0] * len(xs)
    for i, x in enumerate(xs):
        u = U * (X1 - x) / PLOT_W
        m, t = mass(u)
        a = alpha * span(u)
        p = bridge(x)
        for j in range(L):
            shares[j][i] = (m[j] + a * p[j]) / (t + a)
        q = density(u, t)
        conf[i] = q / (q + alpha)

    stretches = []
    sig = sorted((b for b, cf in zip(blist, confs) if cf >= 0.5), key=lambda b: -b["u"])   # oldest first
    for older, newer in zip(sig, sig[1:]):
        xo, xn = x_of_age(older["amin"], S, c), x_of_age(newer["amax"], S, c)
        if xn - xo >= G_QUIET and older["amin"] - newer["amax"] >= QUIET_DAYS:
            stretches.append({"x_old": xo, "x_new": xn, "width": xn - xo, "stop": older["amin"],
                              "resume": newer["amax"], "trailing": False})
    if sig and sig[-1]["amin"] >= QUIET_DAYS and X1 - x_of_age(sig[-1]["amin"], S, c) >= G_QUIET:
        xo = x_of_age(sig[-1]["amin"], S, c)
        stretches.append({"x_old": xo, "x_new": float(X1), "width": X1 - xo, "last": sig[-1]["amin"],
                          "trailing": True})
    return xs, shares, conf, stretches


def tick_label(v, S):
    """Whole days before now, "now" at the 0 line, and the start in words, rounded up: a span of 1.5 days
    starts 2 DAYS AGO, and one under a day starts so many hours ago."""
    if v == 0:
        return "now"
    return span_words(S) if v == S else "%d" % v


def tick_box(v, S, c):
    """The tick label's horizontal extent: the start label runs right from x0, the rest are centred."""
    w = TICK_CHAR * len(tick_label(v, S))
    if v == S:
        return (float(X0), X0 + w)
    x = x_of_age(v, S, c)
    return (x - w / 2, x + w / 2)


def pick_ticks(S, c, stretches):
    """0 and the start always; then, while there is room and fewer than MAX_TICKS, the moments the data
    marks (the end of activity if it has gone quiet, the return from the longest quiet stretch), the
    round spans, the other returns, and where the longest quiet stretch began. A tick is kept only if
    its label clears every kept label by G_MIN, so no two can ever crowd, and none can land inside a
    quiet stretch it would mislabel. A data tick is a whole number of days, so it is used only if one
    of the two whole days around the moment lands within SNAP units of it."""
    def snap(age):
        best = None
        for v in (math.floor(age), math.ceil(age)):
            if 1 <= v < S:
                off = abs(x_of_age(v, S, c) - x_of_age(age, S, c))
                if off <= SNAP and (best is None or off < best[0]):
                    best = (off, v)
        return best[1] if best else None

    trailing = [s for s in stretches if s["trailing"]]
    inner = sorted((s for s in stretches if not s["trailing"]), key=lambda s: -s["width"])
    candidates = [snap(trailing[0]["last"])] if trailing else []
    if inner:
        candidates.append(snap(inner[0]["resume"]))
    candidates += [v for v in LADDER if 1 <= v < S
                   and not any(s["x_old"] < x_of_age(v, S, c) < s["x_new"] for s in stretches)]
    candidates += [snap(s["resume"]) for s in inner[1:]]
    if inner:
        candidates.append(snap(inner[0]["stop"]))

    kept = [0, S]
    for v in candidates:
        if len(kept) >= MAX_TICKS:
            break
        if v is None or v in kept or not 1 <= v < S:
            continue
        box = tick_box(v, S, c)
        if all(max(box[0] - o[1], o[0] - box[1]) >= G_MIN for o in (tick_box(k, S, c) for k in kept)):
            kept.append(v)
    return sorted(kept, reverse=True)
