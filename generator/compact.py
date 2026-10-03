# coderprint's the compact panel for phones. coderprint.py runs this file as part of one module, after the parts
# before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- the compact panel
# The same panel for phones, 360 units wide: on a phone the README is the screen's width less about 81 CSS
# px (279 px at 360, 309 at 390, 349 at 430), so this one is drawn at 0.78 to 0.97 of its size and nothing
# that must be read is under 10 units. It is drawn by the wide panel's own functions, with the geometry in
# COMPACT swapped in for the wide panel's while it is drawn and put back whatever happens. Its height is
# the same for every history: a row that a history does not fill is left empty.
COMPACT_W, COMPACT_H = 360, 686   # COMPACT_H: the panel under its headline, before COMPACT_HEAD_SHIFT
COMPACT_HEAD_SHIFT = 120          # how far the headline moves the rest down: whole grid cells, 5 of 24
COMPACT_TYPE = 10.5    # the chrome: the theme strip, the headline's label, the stats' names, the selector
COMPACT_SMALL = 10     # the ticks, the gutter, the bursts, the bars' dates and key, and the caption
# The headline across the phone's width (see WIDE_HEAD for what each number is): the tiles, then the ring
# beside the bar, then the activity bars, their dates and key under them.
COMPACT_HEAD = Head((14, 56, COMPACT_TYPE), (14, 346, 100, 28, 120, 9, 10, 78, 126), (44, 160, 26, 7, 12, 7),
                    (84, 346, 154, 12), (14, 332.0, 218, 16, COMPACT_SMALL, 193), (252, COMPACT_SMALL, (180, 7, 11, 14)))
# The watermark moves from the wide panel's spot by whole grid cells, so the grid drawn into it lines up
# with the panel's and it is the wide panel's raster, moved; its limits move with it and keep clear of
# this panel's corners.
COMPACT_SHIFT = (-9 * 24, 10 * 24)
# Every wide global the compact panel changes, each on purpose, and what reads it while the compact panel
# is drawn: PANEL_W and PANEL_H the theme strip, the mix's mask, the glow and the document; X0 to PLOT_W
# the mix, its veil, its Pareto line and its axis, and T0 and T1 where an empty chart's words go; TICK_CHAR
# and G_MIN the spacing of the ticks along that axis (tick_box and pick_ticks), whose labels are drawn at
# COMPACT_SMALL here; MARK_CENTRE and MARK_LIMIT the watermark; WORDMARK_WIDTH, _RIGHT and _BOTTOM the
# wordmark; ROWS the stats rows and the dots' timetable; SQUARE_FOOT the outline of the background, the
# grid and the vignette (document). The bars and their key read none of these: the compact headline passes
# its bars' baseline and reach, and its key's size, as arguments.
COMPACT = dict(
    PANEL_W=COMPACT_W, PANEL_H=COMPACT_H + COMPACT_HEAD_SHIFT, SQUARE_FOOT=True,
    X0=40, X1=304, XC=328, XW=346, T0=334, T1=494, AXIS_Y=508, TICK_Y=523, PLOT_W=304 - 40,
    TICK_CHAR=char_width(COMPACT_SMALL), G_MIN=2 * char_width(COMPACT_SMALL),
    MARK_CENTRE=(MARK_CENTRE[0] + COMPACT_SHIFT[0], MARK_CENTRE[1] + COMPACT_SHIFT[1]),
    MARK_LIMIT=(max(8, MARK_LIMIT[0] + COMPACT_SHIFT[0]), max(8, MARK_LIMIT[1] + COMPACT_SHIFT[1]),
                min(COMPACT_W - 10, MARK_LIMIT[2] + COMPACT_SHIFT[0]),
                min(COMPACT_H - 10, MARK_LIMIT[3] + COMPACT_SHIFT[1])),
    WORDMARK_WIDTH=100.0, WORDMARK_RIGHT=346.0, WORDMARK_BOTTOM=672.0,
    ROWS=Rows(14, 346, 182, 24, COMPACT_TYPE, 15, 8.8, 4, 2.0),
)


def compact_headline(window, S, new_lines, spark, since=None, commits=None):
    """The headline and its bars (headline_block) across the full width, for phones. Returns the drawing and the
    story's CSS."""
    return headline_block(COMPACT_HEAD, window, S, spark, since, commits, 346, "")


def compact_legend(order, shown, top=550, pitch=17):
    """The legend under the chart, in two columns with swatches, biggest first and Other last: on a phone
    it reads as a list, and there is no room for it beside the column."""
    langs = [lang for lang, _, _ in sorted(order, key=lambda m: (m[0] == OTHER, -m[2]))]
    per, out = int(math.ceil(len(langs) / 2.0)), ""
    for k, lang in enumerate(langs):
        x, y = (14 if k < per else 190), top + (k % per) * pitch
        out += ('<rect x="%d" y="%s" width="9" height="9" rx="2" fill="%s"/>' % (x, num(y - 8.5), LAYER_COLORS[lang])
                + text(x + 15, y, legend_name(lang), 11.5, TEXT, MONO, 500)
                + text(x + 156, y, shown[lang], 11.5, MUTED, MONO, 400, "end"))
    return out


def compact_panel_svg(theme, window, S, c, new_lines, spark, rows, stream, column, has_history, mark_polys, turn,
                      private, word, recent_day=None, since=None, commits=None):
    """One version of a theme's compact panel, COMPACT_W x COMPACT_H, from exactly what panel_svg is given:
    the theme strip, the headline with its bars and their key beside and under it, the stats full width, the
    mix with its selector and the legend under it, the caption, and the wordmark over the watermark in the
    bottom right corner. Every motion is the wide panel's, under the same rules."""
    saved = {k: globals()[k] for k in COMPACT}
    globals().update(COMPACT)
    try:
        use_theme(theme)
        head, story = compact_headline(window, S, new_lines, spark, since, commits)
        # everything under the headline is laid out as it was before the headline grew, and moved down by whole
        # grid cells, so the watermark's own copy of the grid still lines up with the panel's
        body = (flattened_mark(mark_polys, turn)
                + '<line x1="14" y1="158" x2="346" y2="158" stroke="%s"/>' % LINE
                + stats_rows(rows)
                + '<line x1="14" y1="294" x2="346" y2="294" stroke="%s"/>' % LINE
                + label(14, 318, "language mix", size=COMPACT_TYPE)
                + window_selector(window, 346, 318, COMPACT_TYPE))
        grow = ""
        if stream:
            chart, grow, order, shown = mix_chart(stream, column, S, c, recent_day, COMPACT_SMALL, COMPACT_SMALL)
            body += chart + compact_legend(order, shown)
        else:
            body += text(COMPACT_W / 2, (T0 + T1) / 2, empty_words(window, has_history), 12, MUTED, MONO, 400, "middle")
        for i, part in enumerate(caption_parts(private)):
            body += label(14, 646 + 13 * i, part, size=COMPACT_SMALL)
        body += wordmark(word)
        body = (theme_strip(theme, 28, COMPACT_TYPE) + head
                + '<g transform="translate(0,%d)">%s</g>' % (COMPACT_HEAD_SHIFT, body))
        return document(body, rows, grow + story, words(window, new_lines, spark, rows, column, since))
    finally:
        globals().update(saved)


def todays_themes(pin=None, today=None):
    """Today's theme as its lite and its nite, keys of THEMES: one theme a day for everyone, Paper, Sepia,
    Sage, Oxblood and Ink in turn by the UTC date, or the one pinned."""
    day = (today or dt.datetime.now(dt.timezone.utc).date()).toordinal()
    return VARIANTS[pin or THEME_ORDER[day % len(THEME_ORDER)]]
