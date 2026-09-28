"""Regression checks for the data file, assets/coderprint.json (coderprint v1.2.1, area B3_data_file), for the
coderprint.py given as the only argument; README.md, api/card.js and lib/compose.js are read from beside it. main()
runs on synthetic data with every network call faked, and collect() on synthetic git repositories built in
temporary folders, with every lookup GitHub would answer faked. One line per check; a section that cannot run to its
end (an older coderprint.py lacking what it tests) is one failed check. Exit 1 on any failure.

  P1   series.days and slice_days come from the calendar dates alone, so the hour of the run changes no date, span or
       width, and with it no offset of the owner's zone can be read back (the same as C4-04, C4-10 and F3); the
       slices' own contents, which the activity bars draw, can move with the hour, and slice.limits says so
  M31  the data file holds no time of day: no generated stamp, as_of a date, nothing shaped like a time
  P2   languages.legend is the legend the wide and compact panels draw, ties settled as they settle them, and
       share_of_loc keeps every language, with as_drawn only where the legend draws that language as its own
       layer and drawn_as Other where it draws it inside Other (the same as C4-01 and F2)
  C4-02  window.from is the first day the window counts, and imports are windowed as commits are
  C4-05  left_out says which span each count covers; commits left out are counted over the window when collect
       gave their times, and over the whole history, said so, when it did not or gave one it cannot place
  C4-06  README names the plain numbers, and every other number carries its provenance on itself or a parent
  C4-09, blind-23, blind-19, blind-25, blind-24  the definitions say what the code does, checked against the code
       both ways where the code can be asked: line_of_code, commit, day, language, in_use and scope
  blind-17  series.commits_before_span and loc_before_span relate the slices to the headline
  F4   only coderprint's own cards.json is removed or read by the guard, known by the shape every release wrote
  F1   README says to update the relay before moving the Action, and the relay reads both files
"""
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

SRC = os.path.abspath(sys.argv[1])
REPO = os.path.dirname(SRC)
ROOT = tempfile.mkdtemp(prefix="b3-data-")
DAY = 86400
TODAY = float(int(time.time()) // DAY * DAY)
NOW = TODAY + 20 * 3600   # 20:00 UTC today
fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  %s" % (detail,)), flush=True)


def section(name):
    """Runs the function it decorates at once; one that stops early is a failed check, not a crash."""
    def run_it(fn):
        try:
            fn()
        except Exception as e:
            check("%s: the checks ran to their end" % name, False, "%s: %s" % (type(e).__name__, str(e)[:300]))
        return fn
    return run_it


def load():
    spec = importlib.util.spec_from_file_location("cp_%d" % time.perf_counter_ns(), SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


CP = load()


def run_main(events, now=NOW, commits=None, extra=None, env=None, offset=None, repos=None, owner="someone",
             folder=None, data=None):
    """main() on the given file versions (time, language, lines) and commit times, or on data as collect gave it,
    in a fresh folder unless one is given. Returns main's code, the data file (None if none was written) and the
    folder."""
    cp = load()
    folder = folder or tempfile.mkdtemp(dir=ROOT)
    cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    cp.owner_login = lambda: owner
    cp.profile_offset = lambda o: (offset, now) if offset is not None else None
    cp.profile_location = lambda o: ""
    cp.list_repositories = lambda o: repos or [{"name": "a", "isPrivate": True}]
    if data is None:
        data = {"events": events, "commits": commits if commits is not None else [e[0] for e in events],
                "imports": [], "import_lines": [], "mismatched": 0, "unread": 0, "left_out": {}, "copies": set(),
                "now": now, "code": {"production": 0, "tests": 0, "unread": 0}}
        data.update(extra or {})
    cp.collect = lambda o, r, work, since=None: data
    old = dict(os.environ)
    for name in ("GITHUB_REPOSITORY", "CARDS_WINDOW", "CARDS_RELAY", "CARDS_SPOTIFY_UID", "CARDS_APPLE_MUSIC_UID"):
        os.environ.pop(name, None)
    os.environ.update({"CLONE_CACHE": os.path.join(folder, "cache"), "FORCE": "1", **(env or {})})
    try:
        code = cp.main()
    except RuntimeError as e:
        code = "failed: %s" % e
    finally:
        os.environ.clear()
        os.environ.update(old)
    path = os.path.join(folder, "assets", "coderprint.json")
    card = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return code, card, folder


def panel(folder, name="panel-dark.svg"):
    return open(os.path.join(folder, "assets", name), encoding="utf-8").read()


WIDE = re.compile(r'<text x="454\.0" y="([\d.]+)"[^>]*>([^<]+)</text><text x="560\.0" y="\1"[^>]*>([^<]+)</text>')
COMPACT = re.compile(r'<text x="(?:29|205)\.0" y="([\d.]+)"[^>]*font-size="11\.5"[^>]*>([^<]+)</text>'
                     r'<text x="(?:170|346)\.0" y="\1"[^>]*>([^<]+)</text>')


def legend(folder, compact=False):
    """What a panel's legend draws: {name as the legend writes it: share as it writes it}."""
    found = (COMPACT if compact else WIDE).findall(panel(folder, "panel-compact-dark.svg" if compact
                                                        else "panel-dark.svg"))
    return {n: s.replace("&lt;", "<") for _, n, s in found}


def plain(card):
    """The data file with the slices' own contents set aside, which the activity bars draw as they fall."""
    c = json.loads(json.dumps(card))
    for key in ("loc_written", "commits"):
        c["activity"]["series"].pop(key)
    c["languages"]["by_slice"].pop("loc")
    return c


def dates_only(series):
    """Whether series.days and slice_days are what its two dates alone give."""
    days = (dt.date.fromisoformat(series["to"]) - dt.date.fromisoformat(series["from"])).days + 1
    return series["days"] == days and series["slice_days"] == round(days / 52.0, 2)


# ------------------------------------------------------------------ P1, C4-04, C4-10, F3 and M31: no time of day
@section("P1")
def _():
    base = sorted((TODAY - d * DAY + 9 * 3600, "Python", 100 + d) for d in range(1, 60))
    cards = {}
    for hour in (1, 8, 11.5, 12.5, 20, 23):
        code, cards[hour], _ = run_main(base, now=TODAY + hour * 3600)
    series = {h: {k: c["activity"]["series"][k] for k in ("from", "to", "days", "slice_days")}
              for h, c in cards.items()}
    check("P1 series from, to, days and slice_days are the same at 01:00, 08:00, 11:30, 12:30, 20:00 and 23:00 UTC",
          len({json.dumps(s, sort_keys=True) for s in series.values()}) == 1, series)
    check("P1 series.days is the calendar days from series.from to series.to, both counted, and slice_days is days/52",
          all(dates_only(c["activity"]["series"]) for c in cards.values()), series)
    plains = {json.dumps(plain(c), sort_keys=True) for c in cards.values()}
    check("P1 nothing else in coderprint.json changes with the hour of the run but the slices' contents",
          len(plains) == 1, len(plains))
    moved = len({json.dumps(c["activity"]["series"]["loc_written"]) for c in cards.values()}) > 1
    limits = cards[1]["definitions"]["slice"].get("limits", "")
    check("P1 the slices' contents can move with the hour, as the bars draw them, and slice.limits says so",
          moved and "hour of the run" in limits, (moved, limits))
    # a fixed offset, the refresh at 15:10 UTC as a public commit would show: every value is the dates' own
    for off in (-420, 330, 60, -210):
        code, card, _ = run_main(base, now=TODAY + (15 + 10 / 60.0) * 3600, offset=off)
        s = card["activity"]["series"]
        text = json.dumps(card)
        check("P1 at a fixed offset of %+d minutes the span is the dates' own, and no zone is written" % off,
              dates_only(s) and "UTC%s" % ("+" if off >= 0 else "-") not in text
              and "%+03d:%02d" % (off / 60, abs(off) % 60) not in text, s)


@section("M31")
def _():
    base = sorted((TODAY - d * DAY + 9 * 3600, "Rust", 50) for d in range(1, 30))
    code, card, folder = run_main(base, now=TODAY + 7 * 3600 + 13 * 60)
    text = open(os.path.join(folder, "assets", "coderprint.json"), encoding="utf-8").read()
    check("M31 no generated stamp, and no cards.json written", "generated" not in card
          and not os.path.exists(os.path.join(folder, "assets", "cards.json")), sorted(card))
    check("M31 as_of, window and series dates are dates only", all(
        re.fullmatch(r"\d{4}-\d\d-\d\d", v or "") for v in (card["as_of"], card["window"]["to"],
                                                         card["activity"]["series"]["from"],
                                                         card["activity"]["series"]["to"])))
    check("M31 nothing in the file is shaped like a time of day", not re.search(r"\d\d:\d\d|T\d\d", text),
          re.findall(r".{20}\d\d:\d\d.{5}", text)[:3])
    check("M31 privacy says no times of day, and the day definition that none is written",
          "times of day" in card["privacy"]["never_contains"]
          and "no time of day" in card["definitions"]["day"]["means"])


# ------------------------------------------------------------------ P2, C4-01, F2: the legend as drawn
TEN = ["Python", "Rust", "Go", "C", "Java", "Ruby", "Lua", "Swift", "Kotlin", "Dart"]


def legend_checks(tag, card, folder):
    cp = CP
    wide, compact = legend(folder), legend(folder, compact=True)
    lg = {cp.legend_name(l): v for l, v in card["languages"]["legend"]["as_drawn"].items()}
    check("P2 %s: languages.legend is what the wide legend draws" % tag, lg == wide, (lg, wide))
    check("P2 %s: and what the compact legend draws" % tag, lg == compact, (lg, compact))
    rows = card["languages"]["share_of_loc"]
    bad = [(r["language"], r["as_drawn"], wide.get(cp.legend_name(r["language"]))) for r in rows
           if r["as_drawn"] is not None and wide.get(cp.legend_name(r["language"])) != r["as_drawn"]]
    check("P2 %s: every share_of_loc as_drawn is the share the legend draws beside that name" % tag, not bad, bad)
    return wide, rows


@section("P2")
def _():
    ev = sorted((TODAY - k * DAY + 9 * 3600, l, 100 + 10 * i) for k in range(1, 20) for i, l in enumerate(TEN))
    code, card, folder = run_main(ev)
    wide, rows = legend_checks("ten languages at 1% or more", card, folder)
    folded = {r["language"] for r in rows if r.get("drawn_as") == "Other"}
    check("P2 ten languages: the two the legend folds keep their rows, with no share as drawn, marked drawn_as Other",
          folded == {"Rust", "Python"} and all(r["as_drawn"] is None for r in rows if r["language"] in folded)
          and len(rows) == 10, [(r["language"], r["as_drawn"], r.get("drawn_as")) for r in rows])
    check("P2 ten languages: every language keeps its lines, adding up to written",
          sum(r["loc"] for r in rows) == card["quantity"]["written_loc"]["value"]
          and card["languages"]["counted"]["value"] == 10)
    drawn = card["languages"]["legend"]["as_drawn"]
    check("P2 ten languages: the Other the legend draws is in languages.legend",
          "Other" in drawn and wide.get("other") == drawn["Other"], drawn)
    check("P2 the legend carries its provenance and definition", card["languages"]["legend"].get("provenance")
          == "display" and card["languages"]["legend"].get("definition") == "#/definitions/language")

    three = sorted((TODAY - k * DAY + 9 * 3600, l, 100) for k in range(1, 20) for l in ("Python", "Rust", "Go"))
    code, card, folder = run_main(three)
    wide, rows = legend_checks("three equal languages", card, folder)
    check("P2 three equal languages: the tie goes where the legend puts it",
          {r["language"]: r["as_drawn"] for r in rows} == {"Rust": wide["rust"], "Python": wide["python"],
                                                           "Go": wide["go"]}, (rows, wide))

    few = sorted([(TODAY - k * DAY + 9 * 3600, "Python", 700) for k in range(1, 20)]
                 + [(TODAY - k * DAY + 9 * 3600, "Rust", 290) for k in range(1, 20)]
                 + [(TODAY - 3 * DAY + 9 * 3600, "Go", 30)])
    code, card, folder = run_main(few)
    wide, rows = legend_checks("two languages and a sliver", card, folder)
    other = [r for r in rows if r["language"] == "Other"]
    check("P2 two languages and a sliver: the Other row is the legend's Other, with its share as drawn",
          other and other[0]["as_drawn"] == wide.get("other") == "<1%", (other, wide))

    nine = sorted([(TODAY - k * DAY + 9 * 3600, l, 100 + 10 * i) for k in range(1, 20) for i, l in enumerate(TEN[:9])]
                  + [(TODAY - 3 * DAY + 9 * 3600, "Haskell", 20)])
    code, card, folder = run_main(nine)
    wide, rows = legend_checks("nine languages and a sliver", card, folder)
    other = [r for r in rows if r["language"] == "Other"]
    check("P2 nine languages and a sliver: the Other row holds only the sliver, so it has no share as drawn, while "
          "the legend's Other, holding the ninth language too, is in languages.legend",
          other and other[0]["as_drawn"] is None and card["languages"]["legend"]["as_drawn"].get("Other")
          == wide.get("other"), (other, wide))
    means = card["definitions"]["language"]["means"]
    check("P2 the language definition says the chart names at most eight and marks the rest drawn_as Other",
          "at most eight" in means and "drawn_as" in means, means)


# ------------------------------------------------------------------ C4-02: the window's first day
@section("C4-02")
def _():
    hist = sorted((NOW - k * DAY, "Python", 100) for k in range(1, 12 * 365, 30))
    for w in ("10y", "5y", "3y", "2y", "12m"):
        code, card, _ = run_main(hist, env={"CARDS_WINDOW": w})
        win = card["window"]
        span = (dt.date.fromisoformat(win["to"]) - dt.date.fromisoformat(win["from"])).days + 1
        check("C4-02 %s: window.from to window.to holds window.days calendar days" % w, span == win["days"],
              (win["from"], win["to"], win["days"], span))
    for w, n in (("12m", 365), ("2y", 730)):
        start = NOW - n * DAY
        edge = TODAY - n * DAY + 21 * 3600         # the day holding the window's first moment, after that moment
        first = TODAY - (n - 1) * DAY + 1 * 3600   # the next day, the first the window counts
        code, card, _ = run_main(sorted([(NOW - 10 * DAY, "Python", 10), (edge, "Python", 1000),
                                         (first, "Python", 100)]), env={"CARDS_WINDOW": w},
                                 extra={"imports": [edge, first], "import_lines": [(edge, 555), (first, 7)]})
        day = lambda t: dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat()
        check("C4-02 %s: window.from is the first day counted: work on it counts, work the day before does not" % w,
              card["window"]["from"] == day(first) and card["quantity"]["written_loc"]["value"] == 110
              and CP.iso_day(CP.first_day(start, dt.timezone.utc), dt.timezone.utc) == day(first),
              (card["window"]["from"], day(first), card["quantity"]["written_loc"]["value"]))
        check("C4-02 %s: an import is counted on the days commits are, and not on the day before window.from" % w,
              card["left_out"]["imports"]["commits"] == 1 and card["left_out"]["imports"]["loc_skipped"] == 7,
              card["left_out"]["imports"])
    utc, midnight = dt.timezone.utc, TODAY - 5 * DAY
    iso = lambda t: dt.datetime.fromtimestamp(t, utc).date().isoformat()
    check("C4-02 first_day: a window starting at a day's first moment counts that day, one a second later the next",
          CP.iso_day(CP.first_day(midnight, utc), utc) == iso(midnight)
          and CP.iso_day(CP.first_day(midnight + 1, utc), utc) == iso(midnight + DAY),
          (CP.first_day(midnight, utc), CP.first_day(midnight + 1, utc)))


# ------------------------------------------------------------------ C4-05: which span each left-out count covers
@section("C4-05")
def _():
    hist = sorted((NOW - k * DAY, "Python", 100) for k in range(1, 3 * 365, 30))
    code, card, _ = run_main(hist, env={"CARDS_WINDOW": "12m"}, extra={"left_out": {"automation": 40, "others": 9}})
    over = card["left_out"].get("over", {})
    check("C4-05 without each commit's time the counts are the whole history's, and over says so",
          over.get("commits") == "whole history" and card["left_out"]["commits"]["automation"] == 40
          and over.get("imports") == "window" and over.get("future_dated_file_versions") == "whole history"
          and over.get("unparsed_commits") == "whole history", card["left_out"])
    old = [(NOW - 400 * DAY, "automation")] * 40 + [(NOW - 500 * DAY, "others")] * 9
    new = [(NOW - 20 * DAY, "automation")] * 3 + [(NOW - 2 * DAY, "copied"), (NOW + 5 * DAY, "others")]
    extra = {"left_out": {"automation": 43, "others": 10, "copied": 1}, "left_out_times": old + new}
    code, card, _ = run_main(hist, env={"CARDS_WINDOW": "12m"}, extra=extra)
    c = card["left_out"]["commits"]
    check("C4-05 with their times, a 12 month card counts the commits left out in its window only",
          card["left_out"]["over"]["commits"] == "window" and (c["automation"], c["by_other_accounts"],
                                                               c["template_or_relay_copy"]) == (3, 0, 1), c)
    code, card, _ = run_main(hist, extra=extra)
    c = card["left_out"]["commits"]
    check("C4-05 and all time counts every one but those dated more than a day ahead, as commits are counted",
          (c["automation"], c["by_other_accounts"], c["template_or_relay_copy"]) == (43, 9, 1), c)
    extra = {"left_out": {"automation": 43}, "left_out_times": [(None, "automation")]}
    code, card, _ = run_main(hist, env={"CARDS_WINDOW": "12m"}, extra=extra)
    check("C4-05 a time that cannot be placed falls back to the whole history, said so, and the run goes on",
          code == 0 and card["left_out"]["over"]["commits"] == "whole history"
          and card["left_out"]["commits"]["automation"] == 43, (code, card and card["left_out"]))


# ------------------------------------------------------------------ C4-06: units and provenance, or README says not
@section("C4-06")
def _():
    hist = sorted((NOW - k * DAY, l, 100) for k in range(1, 400, 7) for l in ("Python", "Rust"))
    code, card, _ = run_main(hist)
    bare = []

    def walk(node, path, inherited):
        if path.startswith(("/definitions", "/presentation", "/privacy")):
            return
        meta = isinstance(node, dict) and "provenance" in node
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + "/" + k, inherited or meta)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s/%d" % (path, i), inherited)
        elif isinstance(node, (int, float)) and not isinstance(node, bool) and not inherited:
            bare.append(path)

    walk(card, "", False)
    plain_ok = all(p.startswith(("/scope/", "/left_out/"))
                   or re.fullmatch(r"/languages/share_of_loc/\d+/(loc|share)", p) for p in bare)
    check("C4-06 the only numbers with no provenance of their own or a parent's are the plain counts README names",
          plain_ok, bare)
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    check("C4-06 README no longer says every figure carries a unit, and names the plain numbers",
          "Every figure carries" not in readme and "plain numbers named for what they count" in readme
          and "Every headline and stats figure carries" in readme)
    q, a = card["quantity"], card["activity"]
    check("C4-06 every headline and stats figure has a value, a unit, a provenance and a definition",
          all({"value", "unit", "provenance", "definition"} <= set(v) for v in list(q.values()) + list(a.values())
              if isinstance(v, dict) and "value" in v))


# ------------------------------------------------------------------ blind-17: the slices against the headline
@section("blind-17")
def _():
    stray = sorted([(TODAY - 900 * DAY + 9 * 3600, "Python", 5)]
                   + [(TODAY - k * DAY + 9 * 3600, "Python", 200) for k in range(1, 60)])
    code, card, _ = run_main(stray)
    s, q, a = card["activity"]["series"], card["quantity"], card["activity"]
    check("blind-17 a stray day before the span: the slices and what falls before them add up to the headline",
          (s.get("loc_before_span"), s.get("commits_before_span")) == (5, 1)
          and sum(s["loc_written"]) + s["loc_before_span"] == q["written_loc"]["value"]
          and sum(s["commits"]) + s["commits_before_span"] == a["commits"]["value"],
          (s.get("loc_before_span"), s.get("commits_before_span")))
    commits = [NOW - d * DAY for d in range(0, 400, 3)]
    code, card, _ = run_main([], commits=commits, env={"CARDS_WINDOW": "12m"})
    s, a = card["activity"]["series"], card["activity"]
    check("blind-17 commits and no lines in a 12 month window: they add up too, with nothing before the span",
          sum(s["commits"]) + s["commits_before_span"] == a["commits"]["value"] and s["loc_before_span"] == 0
          and s["commits_before_span"] == 0, (sum(s["commits"]), s["commits_before_span"], a["commits"]["value"]))
    method = card["definitions"]["slice"].get("method", "")
    check("blind-17 slice.method says what real work is and names the counts before the span",
          "10 lines of code" in method and "commits_before_span" in method and "loc_before_span" in method, method)


# ------------------------------------------------------------------ C4-09, blind-23: line_of_code, checked both ways
@section("C4-09")
def _():
    cp = CP
    d = cp.DEFINITIONS["line_of_code"]
    leaves, limits = d["leaves_out"], d.get("limits", "")
    shared = [p for p in ("util.h", "view.m", "script.pl", "top.v")
              if not cp.counts_as_code(p, cp.language_of(p))]
    check("C4-09 leaves_out names the shared extensions exactly when they count as no code",
          bool(shared) == ("several languages share" in leaves)
          and all(os.path.splitext(p)[1] in leaves for p in shared), (shared, leaves))
    data = [p for p in ("a.json", "b.csv", "c.xml", "d.svg", "e.ipynb") if cp.language_of(p) is None]
    check("C4-09 leaves_out names data files, which never count", len(data) == 5 and "data files" in leaves, data)
    def kinds(lang, lines):
        reader = cp.LineKinds(lang)
        return [reader.kind(line) for line in lines]

    check("C4-09 limits describes the fallback when a language has no known comment syntax",
          "every line that is not blank is code" in limits
          and kinds("Unknown syntax", ["{{!-- a comment --}}", "   "]) == ["code", "blank"])
    closed = kinds("C", ["/* why */ int x = 1;"]) == ["comment"]
    closing = kinds("C", ["/* a", "b */ int y = 2;"])[1] == "comment"
    check("C4-09 limits says a line starting with, or closing, a block comment is a comment with code after it, "
          "exactly when the code reads it so", (closed or closing) == ("even with code after the comment" in limits),
          (closed, closing, limits))
    after = kinds("C", ["int x = 1; /* a", "still inside"])[1] == "code"
    check("C4-09 limits says a block comment opened after code is not followed, exactly when it is not",
          after == ("opened after code on its line is not followed" in limits), after)
    doc = kinds("Python", ['"""A docstring', "x = 1", '"""']) == ["comment", "comment", "comment"]
    check("C4-09 limits says a Python line starting with three quotes is a comment to the closing three, exactly "
          "when it is", doc == ("starts with three quotes counts as a comment" in limits), doc)
    hunk = kinds("C", ["still inside a comment opened above"]) == ["code"]
    check("C4-09 limits says a diff hunk starting inside a block comment is read as code, exactly when a fresh "
          "reader reads it so", hunk == ("a hunk that starts inside a block comment" in limits), hunk)
    lang = cp.DEFINITIONS["language"]["means"]
    folds = [cp.language_of(p) for p in ("a.scss", "b.less", "c.rst", "d.pgsql")]
    check("C4-09 the language definition names coderprint's folds, which the code makes",
          folds == ["CSS", "CSS", "Markdown", "SQL"] and "CSS preprocessors count as CSS" in lang
          and "prose markups as Markdown" in lang and "SQL dialects as SQL" in lang, folds)


# ------------------------------------------------------------------ blind-19: what a commit is, on real history
def git(repo, *args, when=None, author=("Owner One", "123+owner1@users.noreply.github.com"), committer=None):
    env = dict(os.environ)
    committer = committer or author
    env.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=committer[0],
               GIT_COMMITTER_EMAIL=committer[1], GIT_AUTHOR_DATE="%d +0000" % when,
               GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false"] + list(args),
                       env=env, capture_output=True, timeout=120)
    if p.returncode:
        raise RuntimeError("git %s failed: %s" % (args[0], p.stderr.decode()[:200]))
    return p.stdout.decode()


def write(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        f.write(text)


def commit(repo, msg, when, **who):
    git(repo, "add", "-A", when=when, **who)
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, when=when, **who)
    return git(repo, "rev-parse", "HEAD", when=when).strip()


@section("blind-19")
def _():
    cp = load()
    real_now = time.time()
    src = os.path.join(ROOT, "src", "hist")
    os.makedirs(src)
    subprocess.run(["git", "init", "-q", "-b", "main", src], check=True, timeout=60)
    bot = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")
    day = lambda k: int(real_now - k * DAY)
    write(src, "a.py", "a = 1\n")
    commit(src, "by a workflow", day(400), committer=bot)
    write(src, "b.py", "b = 1\n")
    commit(src, "by someone else", day(399), author=("Stranger", "stranger@else.where"))
    write(src, "c.py", "c = 1\n")
    commit(src, "by a workflow again", day(10), committer=bot)
    for i in range(12):
        write(src, "m%d.py" % i, "".join("m%d_%d = %d\n" % (i, k, k) for k in range(20)))
    commit(src, "write", day(9))
    for i in range(12):
        write(src, "m%d.py" % i, "".join("    m%d_%d = %d\n" % (i, k, k) for k in range(20)))
    commit(src, "reformat", day(8))
    for i in range(501):
        write(src, "vendorless/f%d.py" % i, "f%d = %d\n" % (i, i))
    commit(src, "import", day(7))
    write(src, "d.py", "".join("d_%d = %d\n" % (k, k) for k in range(10)))
    marked = commit(src, "marked", day(6))
    write(src, ".git-blame-ignore-revs", marked + "\n")
    commit(src, "ignore it", day(5))
    write(src, "relay.js", "export const relay = 1;\n")
    blob = git(src, "hash-object", "relay.js", when=day(4)).strip()
    commit(src, "copy of coderprint", day(4))

    def fake_clone(owner, name, dest):
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        result = subprocess.run(["git", "clone", "-q", "--bare", src, dest], capture_output=True, timeout=120)
        if result.returncode:
            raise RuntimeError("git clone fixture failed (%s): %s" %
                               (name, result.stderr.decode("utf-8", "replace")[:240]))

    cp.clone = fake_clone
    cp.resolve_authors = lambda owner, samples: {e: ("someoneelse" if "stranger" in e else None) for e in samples}
    cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
    cp.templates = lambda owner: {}
    cp.seed_blobs = lambda full_name, dest: {blob} if full_name == cp.UPSTREAM else set()
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    old = dict(os.environ)
    os.environ["CLONE_CACHE"] = work
    try:
        data = cp.collect("owner1", [{"name": "hist", "isPrivate": True}], work)
    finally:
        os.environ.clear()
        os.environ.update(old)
    whys = sorted(w for _, w in data.get("left_out_times", []))
    check("blind-19 collect gives each left-out commit's time and why", whys == ["automation", "automation",
                                                                                "copied", "others"], whys)
    check("blind-19 the import, the sweep and the commit in .git-blame-ignore-revs count as commits, the copy "
          "does not", len(data["commits"]) == 5 and len(data["imports"]) == 1 and day(4) not in data["commits"]
          and all(day(k) in data["commits"] for k in (9, 8, 7, 6, 5)), sorted(data["commits"]))
    check("blind-19 and they add no lines written: 240 lines from the first write only",
          sum(n for _, _, n in data["events"]) == 240, sum(n for _, _, n in data["events"]))
    c = cp.DEFINITIONS["commit"]
    check("blind-19 the commit definition says so",
          all(w in c["means"] for w in ("import", ".git-blame-ignore-revs", "sweep"))
          and all(w in c["leaves_out"] for w in ("template or from a relay copy", "could not be read",
                                                 "more than a day in the future")), c)
    code, card, _ = run_main(None, now=data["now"], data=data, env={"CARDS_WINDOW": "12m"}, owner="owner1")
    got = card["left_out"]["commits"]
    check("blind-19 with collect's times, a 12 month card leaves out the workflow's recent commit and the copy only",
          card["left_out"]["over"]["commits"] == "window" and (got["automation"], got["by_other_accounts"],
                                                               got["template_or_relay_copy"]) == (1, 0, 1), got)
    code, card, _ = run_main(None, now=data["now"], data=data, owner="owner1")
    got = card["left_out"]["commits"]
    check("blind-19 and an all time card all four", (got["automation"], got["by_other_accounts"],
                                                     got["template_or_relay_copy"]) == (2, 1, 1), got)


# ------------------------------------------------------------------ blind-24 and blind-25: in use, day and scope
@section("blind-24")
def _():
    cp = CP
    means = cp.DEFINITIONS["in_use"]["means"]
    trimmed = cp.line_hash("    x  =  1  ") == cp.line_hash("x = 1")
    spaced = cp.line_hash("b=2") != cp.line_hash("b = 2")
    check("blind-24 in_use says how text is compared, as line_hash compares it",
          trimmed and spaced and "b=2 does not match b = 2" in means and "spacing aside" not in means, means)


@section("blind-25")
def _():
    cp = load()
    means = cp.DEFINITIONS["day"]["means"]
    now = time.time()
    fixed = cp.local_zone(-420, "", now)
    check("blind-25 a shown time with no location that settles a zone is a fixed offset, and day says so",
          isinstance(fixed, dt.timezone) and fixed.utcoffset(None) == dt.timedelta(minutes=-420)
          and "fixed for every day" in means and "daylight saving is ignored" in means, fixed)
    check("blind-25 neither a time nor a location is UTC, and day says so", cp.local_zone(None, "", now)
          is dt.timezone.utc and "Otherwise UTC" in means)
    cp.rules_id = lambda zone: None   # as on a machine with no time zone database
    blind = cp.local_zone(330, "Paris, France", now), cp.local_zone(None, "Paris, France", now)
    check("blind-25 with no time zone database the location sets no zone: the shown offset, fixed, or UTC",
          blind[0].utcoffset(None) == dt.timedelta(minutes=330) and blind[1] is dt.timezone.utc
          and "no time zone database" in means, blind)
    if CP.zone_database():
        placed = CP.local_zone(None, "Paris, France", now)
        check("blind-25 a location alone that names a zone clearly sets it, and day says so",
              "Paris" in str(placed) and "zone its location names clearly" in means, placed)
    else:
        print("note blind-25: this Python has no time zone database, so a location's own zone is checked above only "
              "as the fallback", flush=True)
    code, card, _ = run_main(sorted((NOW - k * DAY, "Go", 50) for k in range(1, 20)))
    check("blind-25 a person's profile repository is excluded, as list_repositories leaves it out",
          card["scope"].get("profile_repository") == "excluded")
    code, card, folder = run_main(sorted((NOW - k * DAY, "Go", 50) for k in range(1, 20)), owner="someorg",
                                  env={"GITHUB_REPOSITORY": "someorg/.github"})
    check("blind-25 an organization's profile repository, .github, is counted", code == 0
          and card["scope"].get("profile_repository") == "counted", (code, card and card["scope"]))
    lister = load()
    lister.gql = lambda query, **kw: {"repositoryOwner": {"repositories": {
        "nodes": [{"name": n, "isPrivate": False, "isDisabled": False, "isLocked": False}
                  for n in ("someorg", ".github", "tool")], "pageInfo": {"hasNextPage": False}}}}
    names = [r["name"] for r in lister.list_repositories("someorg")]
    check("blind-25 list_repositories leaves out only the repository named after the account", names == [".github",
                                                                                                        "tool"], names)


# ------------------------------------------------------------------ F4: only coderprint's own cards.json
@section("F4")
def _():
    pal = {"light": {"bg": "#ffffff", "text": "#000000", "muted": "#555555", "line": "#dddddd"}}
    base = sorted((NOW - k * DAY, "Python", 100) for k in range(1, 30))
    cases = (("v1.2.0's own", {"generated": "2026-09-26T07:38Z", "span_days": 203, "repositories": 1,
                               "palette": pal, "theme": "sage"}, True),
             ("v1's own", {"span_days": 12.34, "repositories": 1, "private_repositories": 1, "palette": pal}, True),
             ("a design tool's swatches", {"name": "brand", "palette": ["#112233", "#445566"]}, False),
             ("a card game's deck", {"deck": "tarot", "palette": {"major": "gold"}, "cards": 78}, False),
             ("a count that is true", {"palette": {}, "repositories": True}, False),
             ("no palette", {"hello": 1}, False))
    for name, body, gone in cases:
        folder = tempfile.mkdtemp(dir=ROOT)
        os.makedirs(os.path.join(folder, "assets"))
        json.dump(body, open(os.path.join(folder, "assets", "cards.json"), "w"))
        code, card, _ = run_main(base, folder=folder)
        check("F4 %s cards.json %s" % (name, "removed" if gone else "kept"),
              code == 0 and os.path.exists(os.path.join(folder, "assets", "cards.json")) != gone, code)
    three = [{"name": n, "isPrivate": False} for n in "abc"]
    folder = tempfile.mkdtemp(dir=ROOT)
    os.makedirs(os.path.join(folder, "assets"))
    json.dump({"deck": "tarot", "palette": [], "repositories": 99}, open(os.path.join(folder, "assets",
                                                                                      "cards.json"), "w"))
    code, card, _ = run_main(base, folder=folder, repos=three, env={"FORCE": ""})
    check("F4 someone else's cards.json does not hold the panels back", code == 0, code)
    folder = tempfile.mkdtemp(dir=ROOT)
    os.makedirs(os.path.join(folder, "assets"))
    json.dump({"palette": {}, "repositories": 3}, open(os.path.join(folder, "assets", "cards.json"), "w"))
    code, card, _ = run_main(base, folder=folder, repos=three[:2], env={"FORCE": ""})
    check("F4 coderprint's own cards.json still guards against a shrinking account", code == 1, code)


# ------------------------------------------------------------------ F1: the relay goes first, and reads both files
@section("F1")
def _():
    readme = open(os.path.join(REPO, "README.md"), encoding="utf-8").read()
    step = readme[readme.index("**4. Optional"):readme.index("## Options")]
    check("F1 README's relay step says to update the relay before moving the Action's pin",
          "before you move the Action's pin" in step and "reads only `cards.json`" in step, step[-600:])
    check("F1 README's data file section sends a relay install to that step",
          "update your relay first (step 4)" in readme)
    card_js = open(os.path.join(REPO, "api", "card.js"), encoding="utf-8").read()
    check("F1 the relay asks for coderprint.json and for cards.json",
          "rawUrl(user, 'coderprint.json')" in card_js and "rawUrl(user, 'cards.json')" in card_js)
    probe = ("import { readCards } from './lib/compose.js';"
             "const p = {light: {bg: '#101010', text: '#f0f0f0', muted: '#808080', line: '#303030'}};"
             "const a = readCards(JSON.stringify({presentation: {palette: p, spotify: {uid: 'abc'}}}), 'light');"
             "const b = readCards(JSON.stringify({palette: p, spotify: {uid: 'abc'}, repositories: 3}), 'light');"
             "console.log(JSON.stringify([a, b]));")
    out = subprocess.run(["node", "--input-type=module", "-e", probe], cwd=REPO, capture_output=True, timeout=60)
    got = json.loads(out.stdout.decode() or "null")
    check("F1 the relay reads the palette and music card from either file alike",
          got and got[0] == got[1] and got[0]["palette"]["bg"] == "#101010" and got[0]["uid"] == "abc",
          (got, out.stderr.decode()[:200]))


shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d %s" % (passes, len(fails), fails))
sys.exit(1 if fails else 0)
