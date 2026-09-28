"""Regression checks for the panel and its words (coderprint v1.2.1, area B1_panel), run through main() of the
coderprint.py given as the only argument, with every network lookup and the history itself stubbed, in temporary
folders. One line per check; exit 1 on any failure.

  F2     the ring and the bar draw the same shares down to the smallest: a share above 0 shows at least a dot on
         both, at rest and in the story, a share of 0 shows nothing on either, and the tests' lit segment is on
         the bar whatever production's share; shares at or above the stroke keep their offsets
  F3     one line of code in use is "1 line", in the title, the description and the README's alt text
  F4     every headline figure fits its tile, in the measured faces, and one that could overrun in a wider face
         is held to its width with textLength, every copy of it alike; ordinary figures are drawn as before
  U1     the ring's middle rounds half up, never says 0% for a share above nothing or 100% while anything is
         missing, the parts add up to what is kept, exactly from whole numbers and in floating point without
         them, and the description and the data file say what the middle draws
  U2     the description names the day the bars end on, and the README is unchanged a day later
  LABEL  the languages row is named by one constant, "languages · 1%+" by default, fits on both panels, and the
         words say "N languages at 1% or more of the lines of code"
"""
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from fractions import Fraction

SRC = os.path.abspath(sys.argv[1])
NOW = float(int(time.time()) // 86400 * 86400 + 20 * 3600)   # 20:00 UTC today
SVG = "{http://www.w3.org/2000/svg}"
ROOT = tempfile.mkdtemp(prefix="b1-panel-")
fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  %s" % (detail,)))


def load():
    spec = importlib.util.spec_from_file_location("cp_%d" % time.perf_counter_ns(), SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ev(days_ago, lang, n, hour=9):
    t = NOW - days_ago * 86400
    return (t // 86400 * 86400 + hour * 3600, lang, n)


def events_for(total, lang="Python"):
    days = list(range(1, 41))
    per, rest = divmod(total, len(days))
    return sorted(ev(d, lang, per + (1 if i < rest else 0)) for i, d in enumerate(days) if per or i < rest)


def run_main(cp, events, production=0, tests=0, now=NOW, env=None):
    folder = tempfile.mkdtemp(prefix="run-", dir=ROOT)
    cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    cp.owner_login = lambda: "someone"
    cp.profile_offset = lambda owner: None
    cp.profile_location = lambda owner: ""
    cp.list_repositories = lambda owner: [{"name": "a", "isPrivate": True}]
    data = {"events": events, "commits": [e[0] for e in events], "imports": [], "import_lines": [], "mismatched": 0,
            "unread": 0, "left_out": {}, "copies": set(), "now": now,
            "code": {"production": production, "tests": tests, "unread": 0}}
    cp.collect = lambda owner, repos, work, since=None: data
    cp.say = lambda *args, **kwargs: None   # the run's own log would come between the checks' lines
    old = dict(os.environ)
    os.environ.update({"CLONE_CACHE": os.path.join(folder, "cache"), "FORCE": "1", "CARDS_THEME": "ink", **(env or {})})
    try:
        code = cp.main()
    finally:
        os.environ.clear()
        os.environ.update(old)
    if code != 0:
        raise SystemExit("main() returned %r" % (code,))
    return folder


def panel(folder, name="panel-dark.svg"):
    return open(os.path.join(folder, "assets", name), encoding="utf-8").read()


def meta(folder):
    return json.load(open(os.path.join(folder, "assets", "coderprint.json"), encoding="utf-8"))


def alt(folder):
    readme = open(os.path.join(folder, "README.md"), encoding="utf-8").read()
    return re.search(r'alt="([^"]*)"', readme).group(1)


def elements(svg):
    """Every element of svg as (element, hidden under an opacity 0 group, classes of it and its ancestors)."""
    out = []

    def walk(node, hidden, classes):
        hidden = hidden or node.get("opacity") == "0"
        classes = classes + (node.get("class") or "").split()
        out.append((node, hidden, classes))
        for child in node:
            walk(child, hidden, classes)
    walk(ET.fromstring(svg), False, [])
    return out


def texts(svg):
    return [(e, hidden, classes) for e, hidden, classes in elements(svg) if e.tag == SVG + "text"]


def title_desc(svg):
    root = ET.fromstring(svg)
    return root.find(SVG + "title").text, root.find(SVG + "desc").text


def keyframe(svg, name, k):
    m = re.search(r"@keyframes %s\{(.*?)\}\}" % name, svg)
    values = re.findall(r"stroke-dashoffset:(-?[\d.]+)", m.group(1)) if m else []
    return float(values[k]) if len(values) > k else None


def fonts(*paths):
    """Pillow faces at 1000 units to the em, for those of paths that exist, or [] without Pillow."""
    try:
        from PIL import ImageFont
    except ImportError:
        return []
    return [ImageFont.truetype(p, 1000) for p in paths if os.path.exists(p)]


def run_case(name, fn):
    """Runs one group of checks; an exception in it is a failed check, not the end of the run."""
    try:
        fn()
    except SystemExit as e:
        check("%s ran" % name, False, e)
    except Exception as e:   # a broken case still lets every other case report
        check("%s ran" % name, False, "%s: %s" % (type(e).__name__, e))


# ---------------------------------------------------------------- F2: the ring and the bar, down to the smallest
def f2():
    cases = [("tiny3", 1000, 30, 0), ("tiny", 100000, 1, 0), ("prod0", 1000, 0, 400), ("p97", 1000, 975, 10),
             ("tests_small", 1000, 500, 20), ("prod_small", 1000, 20, 500), ("all_kept", 1000, 700, 300)]
    for name, written, prod, tests in cases:
        cp = load()
        folder = run_main(cp, events_for(written), prod, tests)
        U, P = (prod + tests) / float(written), prod / float(written)
        for fname, g in (("panel-dark.svg", cp.WIDE_HEAD), ("panel-compact-light.svg", cp.COMPACT_HEAD)):
            svg = panel(folder, fname)
            bx0, bx1, _, bh = g.bar
            W, D = bx1 - bx0, bx1 - bx0 - bh
            r, sw = g.ring[2], g.ring[3]
            C = 2 * math.pi * r
            shapes = [(e, hidden, classes) for e, hidden, classes in elements(svg)
                      if e.tag in (SVG + "line", SVG + "circle") and e.get("stroke-dasharray")
                      and e.get("stroke-linecap") == "round"]
            rest = [e for e, hidden, _ in shapes if not hidden]
            dash = lambda e: float(e.get("stroke-dasharray").split()[0])
            offset = lambda e: float(e.get("stroke-dashoffset"))
            ring_rest = [dash(e) - offset(e) for e in rest if e.tag == SVG + "circle" and abs(dash(e) - (C - sw)) < .02]
            bar_rest = [dash(e) - offset(e) for e in rest if e.tag == SVG + "line" and abs(dash(e) - D) < .02]
            want = 1 + sum(1 for f in (U, P) if f > 0)
            problems = []
            if not (len(ring_rest) == want and all(v > 0 for v in ring_rest)):
                problems.append("ring at rest %s" % ["%.2f" % v for v in ring_rest])
            if not (len(bar_rest) == want and all(v > 0 for v in bar_rest)):
                problems.append("bar at rest %s" % ["%.2f" % v for v in bar_rest])
            vb, vr = keyframe(svg, "cp-qbt", 1), keyframe(svg, "cp-qrt", 1)
            if vb is None or vr is None:
                problems.append("no story")
            elif (P == 0) != (D - vb < 0) or (P == 0) != ((C - sw) - vr < 0):
                problems.append("production step shows bar %.2f ring %.2f" % (D - vb, (C - sw) - vr))
            for e, hidden, classes in shapes:
                if e.tag == SVG + "line" and hidden and "cp-qt" in classes:
                    start = -offset(e)
                    if not (start < D and start + dash(e) <= D + 0.011):
                        problems.append("tests' lit segment %.2f..%.2f off the line (%.2f)" % (start, start + dash(e), D))
            # a share at or above the stroke keeps the offset C(1 - f) it had before
            if U * C - sw >= 0.01 and ("%s" % cp.num(C * (1 - U), 2)) not in [e.get("stroke-dashoffset") for e in rest]:
                problems.append("in use's ring offset is not C(1 - U) = %s" % cp.num(C * (1 - U), 2))
            check("F2 %s %s: ring and bar agree at rest and in the story" % (name, fname), not problems, problems)


# ---------------------------------------------------------------- F3: one line of code
def f3():
    cp = load()
    folder = run_main(cp, [ev(3, "Python", 1)], 1, 0)
    title, desc = title_desc(panel(folder))
    words = [title, desc, alt(folder)]
    check("F3 one line in use is '1 line of code in use' in the title, the description and the alt text",
          all("1 line of code in use" in w for w in words) and not any(re.search(r"\b1 lines\b", w) for w in words),
          words)
    folder = run_main(load(), sorted([ev(3, "Python", 5), ev(4, "Python", 5)]), 2, 0)
    title, desc = title_desc(panel(folder))
    check("F3 two lines stay '2 lines of code in use'", "2 lines of code in use" in title
          and desc.startswith("2 lines of code in use"), (title, desc[:60]))


# ---------------------------------------------------------------- F4: every figure fits its tile
# A figure's characters in em, measured here as in coderprint.py and rounded up: the wider at each character of
# Segoe UI Bold and Arial Bold, and DejaVu Sans Bold, the widest face a viewer may fall back to; each as a table
# and the width of every character it leaves out. GAP: the room kept clear before a tile's rule.
MEASURED = ({"M": 0.96, "B": 0.73, ".": 0.28}, 0.58)
WIDEST = ({"M": 1.0, "B": 0.77, ".": 0.38, "k": 0.67}, 0.7)
GAP = 2


def f4():
    measured = fonts(r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf")
    cases = [("1.0k", 1000, 700, 300), ("9.9k", 9900, 9000, 900), ("999k", 999499, 999499, 0),
             ("wide12M", 12345678, 9876543, 1234567), ("m99", 99_000_000, 88_000_000, 11_000_000),
             ("m999", 999900000, 999900000, 0), ("b200", 1234567890, 1000000000, 200000000),
             ("b123", 123_456_789_012, 100_000_000_000, 23_000_000_000)]
    for name, written, prod, tests in cases:
        cp = load()
        folder = run_main(cp, events_for(written), prod, tests)
        em = lambda s, table: sum(table[0].get(ch, table[1]) for ch in s)
        for fname, g in (("panel-dark.svg", cp.WIDE_HEAD), ("panel-compact-dark.svg", cp.COMPACT_HEAD)):
            x0, x1, fy, nominal = g.tiles[:4]
            width = (x1 - x0) / 4.0
            figures = {}
            for e, hidden, classes in texts(panel(folder, fname)):
                if abs(float(e.get("y")) - fy) < .01 and e.get("font-weight") == "700":
                    figures.setdefault(int((float(e.get("x")) - x0) // width), []).append(e)
            problems = []
            for i, copies in sorted(figures.items()):
                e = copies[0]
                s, x, size, length = "".join(e.itertext()), float(e.get("x")), float(e.get("font-size")), e.get("textLength")
                limit = x0 + (i + 1) * width - (GAP if i < 3 else 0)
                if len({(c.get("font-size"), c.get("textLength"), c.get("lengthAdjust")) for c in copies}) != 1:
                    problems.append("tile %d: its copies differ" % i)
                if x + size * em(s, MEASURED) > limit + 0.01:
                    problems.append("tile %d %r at %s overruns in the measured faces" % (i, s, size))
                for face in measured:
                    if x + face.getlength(s) / 1000.0 * size > limit + 0.01:
                        problems.append("tile %d %r at %s overruns in a real face (%.1f past %.1f)"
                                        % (i, s, size, x + face.getlength(s) / 1000.0 * size, limit))
                at_risk = x + size * em(s, WIDEST) > limit
                if at_risk and not (length and e.get("lengthAdjust") == "spacingAndGlyphs"
                                    and x + float(length) <= limit + 0.005):
                    problems.append("tile %d %r could overrun in a wider face and is not held (%s)" % (i, s, length))
                if not at_risk and length:
                    problems.append("tile %d %r is held though it cannot overrun" % (i, s))
                if written < 100000 and (size != nominal or length):
                    problems.append("tile %d %r is not drawn as before (%s, %s)" % (i, s, size, length))
            check("F4 %s %s: %d figures fit their tiles" % (name, fname, len(figures)), len(figures) == 4 and not problems,
                  problems)
    cp = load()
    tables = [(getattr(cp, "FIGURE_EM", {}), getattr(cp, "FIGURE_DIGIT", 0)), MEASURED,
              (getattr(cp, "FIGURE_EM_WIDEST", {}), getattr(cp, "FIGURE_DIGIT_WIDEST", 0)), WIDEST]
    narrower = [ch for ch in "0123456789.kMB" for k in (0, 2)
                if tables[k][0].get(ch, tables[k][1]) < tables[k + 1][0].get(ch, tables[k + 1][1])]
    check("F4 coderprint.py's tables are as wide as the faces measured here", not narrower, narrower)
    for path, table, face in ((r"C:\Windows\Fonts\segoeuib.ttf", MEASURED, "Segoe UI Bold"),
                              (r"C:\Windows\Fonts\arialbd.ttf", MEASURED, "Arial Bold"),
                              (os.path.join(os.path.dirname(os.__file__), "site-packages", "matplotlib", "mpl-data",
                                            "fonts", "ttf", "DejaVuSans-Bold.ttf"), WIDEST, "DejaVu Sans Bold")):
        found = fonts(path)
        if found:
            wider = [ch for ch in "0123456789.kMB" if found[0].getlength(ch) / 1000.0 > table[0].get(ch, table[1])]
            check("F4 the table holds %s at every character" % face, not wider, wider)
        else:
            print("skip F4 %s is not installed here (or Pillow is not), so it is not remeasured" % face)


# ---------------------------------------------------------------- U1: the ring's middle
def u1():
    for name, written, prod, tests, want in (("almost_all", 200, 198, 1, "99%"), ("almost_none", 100000, 1, 0, "<1%"),
                                             ("half", 1000, 125, 0, "13%"), ("all", 1000, 700, 300, "100%"),
                                             ("none", 1000, 0, 0, "0%")):
        folder = run_main(load(), events_for(written), prod, tests)
        for fname in ("panel-dark.svg", "panel-compact-dark.svg"):
            mid = ["".join(e.itertext()) for e, hidden, _ in texts(panel(folder, fname))
                   if e.get("text-anchor") == "middle" and e.get("font-weight") == "700" and not hidden]
            check("U1 %s %s: the middle at rest says %s" % (name, fname, want), mid == [want], mid)
        _, desc = title_desc(panel(folder))
        said = want.replace("<1%", "under 1%")
        drawn = meta(folder)["quantity"]["as_drawn"]
        check("U1 %s: the description and the data file say what the middle draws" % name,
              ("Of what was written, %s is kept." % said in desc) == (written > 0)
              and drawn.get("kept_label") == want, (desc[-50:], drawn))
    cp = load()
    wrong = []
    for written in range(1, 301):
        for prod in range(0, written + 1):
            for tests in ({0, 1, written - prod} if written - prod > 1 else {0, written - prod}):
                cp.QUANTITY = {"written": written, "production": prod, "tests": tests}
                _, use, _, _, P, U = cp.story_figures()
                kept, pp, tp = cp.kept_shares(P, U, (written, prod, tests))
                shown = [cp.share_label(kept, U), cp.share_label(pp, P), cp.share_label(tp, U - P)]
                if pp + tp != kept or (shown[0] == "100%") != (use == written) or (shown[0] == "0%") != (use == 0) \
                        or (shown[1] == "0%") != (prod == 0) or (shown[2] == "0%") != (tests == 0) \
                        or (shown[1] == "100%") != (prod == written) or (shown[2] == "100%") != (tests == written):
                    wrong.append((written, prod, tests, shown))
    check("U1 every split up to 300 lines is drawn right: 0% only for none, 100% only for all, parts add up",
          not wrong, wrong[:3])
    exact_wrong, float_wrong = [], []
    for written in range(1, 601):
        for use in range(0, written + 1):
            for prod in {use, use // 2, 0}:
                cp.QUANTITY = {"written": written, "production": prod, "tests": use - prod}
                P, U = cp.story_figures()[4:]
                want = int(Fraction(100 * use, written) + Fraction(1, 2))
                want = 99 if want == 100 and use < written else want
                if cp.kept_shares(P, U, (written, prod, use - prod))[0] != want:
                    exact_wrong.append((use, written))
                if cp.kept_shares(P, U)[0] != want:
                    float_wrong.append((use, written))
    check("U1 half up, exactly from whole numbers, every split up to 600 lines", not exact_wrong, exact_wrong[:4])
    check("U1 half up in floating point without them (the fallback), every split up to 600 lines", not float_wrong,
          float_wrong[:4])
    # 2,000,000,000 of 16,000,000,001 is 12.49999999922%, a hair under a half that the floating point nudge takes
    # for one; the exact count does not
    written, use = 16000000001, 2000000000
    cp.QUANTITY = {"written": written, "production": use, "tests": 0}
    P, U = cp.story_figures()[4:]
    check("U1 whole numbers are rounded exactly where floating point would not be",
          cp.kept_shares(P, U, (written, use, 0))[0] == 12 and cp.kept_shares(P, U)[0] == 13,
          (cp.kept_shares(P, U, (written, use, 0)), cp.kept_shares(P, U)))
    check("U1 counts that are not whole numbers fall back to the shares instead of failing",
          cp.kept_shares(0.5, 0.75, (4.0, 2, 1)) == (75, 50, 25) and cp.kept_shares(0.5, 0.75, None) == (75, 50, 25),
          (cp.kept_shares(0.5, 0.75, (4.0, 2, 1)), cp.kept_shares(0.5, 0.75, None)))
    cp.QUANTITY = {"written": 1000, "production": 996, "tests": 4}
    P, U = cp.story_figures()[4:]
    check("U1 production is not 100% while tests hold any line: 100, 99, 1",
          cp.kept_shares(P, U, (1000, 996, 4)) == (100, 99, 1), cp.kept_shares(P, U, (1000, 996, 4)))


# ---------------------------------------------------------------- U2: the day the bars end on
def u2():
    evs = sorted([ev(d, "Python", 50) for d in (1, 2, 3, 30, 31)] + [ev(d, "Rust", 20) for d in (60, 61)])
    readmes = []
    for shift in (0, 1):
        cp = load()
        folder = run_main(cp, [(t + shift * 86400, l, n) for t, l, n in evs], 120, 40, now=NOW + shift * 86400)
        for fname in ("panel-dark.svg", "panel-compact-dark.svg"):
            svg = panel(folder, fname)
            drawn = ["".join(e.itertext()) for e, _, _ in texts(svg) if e.get("text-anchor") == "end"
                     and re.fullmatch(r"\d\d[A-Z]{3}\d{4}", "".join(e.itertext()))]
            _, desc = title_desc(svg)
            check("U2 day %d %s: the description names the drawn end date %s" % (shift, fname, drawn),
                  len(drawn) == 1 and "The bars end on %s, the day this panel was drawn." % drawn[0] in desc, desc)
        readmes.append(open(os.path.join(folder, "README.md"), encoding="utf-8").read())
        check("U2 day %d: the alt text says no date" % shift, not re.search(r"\d\d[A-Z]{3}\d{4}", alt(folder)),
              alt(folder))
    check("U2 the README is byte-identical a day later", readmes[0] == readmes[1])


# ---------------------------------------------------------------- LABEL: the languages row
def label():
    cp = load()
    name = getattr(cp, "LANGUAGES_ROW", None)
    check("LABEL the row's name is one constant, 'languages · 1%+' by default", name == "languages · 1%+", name)
    source = open(SRC, encoding="utf-8").read()
    check("LABEL the name is written once in the source, and 'languages written' nowhere",
          source.count('"languages · 1%+"') == 1 and "languages written" not in source,
          (source.count('"languages · 1%+"'), source.count("languages written")))
    many = sorted(ev(d, l, 100) for d in range(1, 20) for l in ("Python", "Rust", "Go"))
    folder = run_main(cp, many + [ev(3, "Lua", 1)], 3000, 1000)
    counted = meta(folder)["languages"]["counted"]["value"]
    consolas = fonts(r"C:\Windows\Fonts\consola.ttf")
    for fname, rows in (("panel-dark.svg", cp.ROWS), ("panel-compact-dark.svg", cp.COMPACT["ROWS"])):
        svg = panel(folder, fname)
        items = elements(svg)
        names = [e for e, _, _ in items if e.tag == SVG + "text" and "".join(e.itertext()) == name.upper()]
        check("LABEL %s draws the row %r, and no 'LANGUAGES WRITTEN'" % (fname, name.upper()),
              len(names) == 1 and "LANGUAGES WRITTEN" not in svg, len(names))
        if len(names) != 1:
            continue
        e = names[0]
        x, y, size = float(e.get("x")), float(e.get("y")), float(e.get("font-size"))
        leaders = [l for l, _, _ in items if l.tag == SVG + "line" and l.get("stroke-linecap") == "square"
                   and "cp-hop" not in (l.get("class") or "") and abs(float(l.get("y1")) - (y - rows.rise)) < .01]
        values = [v for v, _, _ in items if v.tag == SVG + "text" and v.get("text-anchor") == "end"
                  and abs(float(v.get("y")) - y) < .01 and "".join(v.itertext()) == str(counted)]
        name_end = x + cp.char_width(size) * len(name)
        real_end = x + (consolas[0].getlength(name.upper()) / 1000.0 * size + 1.3 * len(name) if consolas else 0)
        value_start = rows.right - rows.vchar * len(str(counted))
        fit = (len(leaders) == 1 and values and name_end < float(leaders[0].get("x1"))
               and real_end < float(leaders[0].get("x1")) and float(leaders[0].get("x2")) < value_start
               and value_start > name_end)
        check("LABEL %s: the row fits, name then leader then its value %d, all before x %s" % (fname, counted, rows.right),
              fit, (name_end, real_end, [(l.get("x1"), l.get("x2")) for l in leaders], value_start))
    title, desc = title_desc(panel(folder))
    phrase = "%d languages at 1%% or more of the lines of code" % counted
    check("LABEL the description and the alt text say '%s'" % phrase, phrase in desc and phrase in alt(folder),
          (desc, alt(folder)))
    folder = run_main(load(), sorted([ev(d, "Python", 1000) for d in range(1, 30)] + [ev(3, "Go", 5)]), 100, 0)
    one = "1 language at 1% or more of the lines of code"
    _, desc = title_desc(panel(folder))
    check("LABEL one language is '%s', and a 0.02%% language is not counted" % one,
          one in desc and one in alt(folder) and meta(folder)["languages"]["counted"]["value"] == 1, desc)
    title, desc = cp.words("all", 5, [0] * 52, [("commits · all branches", "1"), ("active days", "1"),
                                                (cp.LANGUAGES_ROW, "1")], [])
    check("LABEL singulars in words for every row that has one",
          "1 commit across" in desc and "1 active day," in desc and one in desc, desc)


for case in (f2, f3, f4, u1, u2, label):
    run_case(case.__name__.upper(), case)
shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d %s" % (passes, len(fails), fails))
sys.exit(1 if fails else 0)
