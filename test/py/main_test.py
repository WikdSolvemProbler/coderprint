"""The audit's panel-level fixes, checked by running main() of the coderprint.py given as argv[1] on fake data
in temp folders: the date at the bars' right end, the caption, the languages count, whole days only, commits
without lines, unread repositories, numbers and plurals, and the README handling that main() still owns.

A copy of the workflow's main_test.py, changed where v1.2.1 changes the card on purpose (area B1_panel):
  - the languages row is named LANGUAGES_ROW ("languages · 1%+") and read out as LANGUAGES_WORDS ("N languages
    at 1% or more of the lines of code"), so M10, S14 and "DATA the stats written are the stats drawn" look for
    those words, taken from the module, instead of "languages written";
  - SAME compares against the release given this version's languages row name and words (its source is changed
    at exactly those three strings, and the check fails if any is missing), and sets aside the two sentences
    the description gains (the day the bars end on, and the share kept), which the README's alt text shares
    in the second; everything else must still be byte for byte the same."""
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import time

SRC = sys.argv[1]
NOW = float(int(time.time()) // 86400 * 86400 + 20 * 3600)   # 20:00 UTC today, so hours can move within the day
fails, passes = [], 0


def load():
    spec = importlib.util.spec_from_file_location("cp_%d" % time.perf_counter_ns(), SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s %s" % ("ok" if ok else "FAIL", name, detail if not ok else ""))


def run_main(cp, folder, events, commits=None, extra=None, env=None, repos=None):
    cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    cp.owner_login = lambda: "someone"
    cp.profile_offset = lambda owner: None
    cp.profile_location = lambda owner: ""
    cp.list_repositories = lambda owner: repos or [{"name": "a", "isPrivate": True}]
    data = {"events": events, "commits": commits if commits is not None else [e[0] for e in events], "imports": [],
            "import_lines": [], "mismatched": 0, "unread": 0, "left_out": {}, "copies": set(), "now": NOW,
            "code": {"production": 0, "tests": 0, "unread": 0}}
    data.update(extra or {})
    cp.collect = lambda owner, repos, work, since=None: data
    old = dict(os.environ)
    os.environ.update({"CLONE_CACHE": os.path.join(folder, "cache"), "FORCE": "1", **(env or {})})
    try:
        return cp.main()
    except RuntimeError as e:
        return "failed: %s" % e
    finally:
        os.environ.clear()
        os.environ.update(old)


def ev(days_ago, lang, n, hour=None):
    t = NOW - days_ago * 86400
    if hour is not None:
        t = t // 86400 * 86400 + hour * 3600
    return (t, lang, n)


def panel(folder, name="panel-dark.svg"):
    return open(os.path.join(folder, "assets", name), encoding="utf-8").read()


def meta(folder):
    return json.load(open(os.path.join(folder, "assets", "coderprint.json"), encoding="utf-8"))


# the languages row's name and its words, as this version draws and says them
_cp = load()
ROW = getattr(_cp, "LANGUAGES_ROW", "languages written")
MANY, ONE = getattr(_cp, "LANGUAGES_WORDS", ("{v} languages written", "1 language written"))

# 1. M7: moving work between hours of the same day changes nothing published
base = [ev(d, "Python", 100 + d, hour=9) for d in range(1, 60)]
early = sorted(base + [ev(0, "Rust", 400, hour=1), ev(0, "Python", 50, hour=2)])
late = sorted(base + [ev(0, "Rust", 400, hour=19), ev(0, "Python", 50, hour=19.5)])
a, b = tempfile.mkdtemp(prefix="m7a-"), tempfile.mkdtemp(prefix="m7b-")
run_main(load(), a, early)
run_main(load(), b, late)
same = all(panel(a, f) == panel(b, f) for f in ("panel-dark.svg", "panel-light.svg", "panel-compact-dark.svg"))
ma, mb = meta(a), meta(b)
check("M7 hours within a day change no panel", same)
check("M7 hours within a day change nothing in coderprint.json", ma == mb, (ma, mb))
check("M7 the span is whole days", isinstance(meta(a)["activity"]["series"]["days"], int), meta(a)["activity"]["series"])
check("P2 private_repositories not written", "private_repositories" not in json.dumps(meta(a)))
check("M31 as_of is a date, no time of day", re.fullmatch(r"\d{4}-\d\d-\d\d", meta(a)["as_of"]) is not None,
      meta(a)["as_of"])

# 2. M16: the bars end at the run's date, not "today"
day = dt.datetime.fromtimestamp(NOW, dt.timezone.utc)
stamp = "%02d%s%d" % (day.day, ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"][
    day.month - 1], day.year)
check("M16 wide bars end at the run's date", ">%s<" % stamp in panel(a) and ">TODAY<" not in panel(a))
check("M16 compact bars end at the run's date", ">%s<" % stamp in panel(a, "panel-compact-dark.svg"))

# 3. M15 and M4: the caption says what is counted and still fits beside the wordmark
cp = load()
wide = " · ".join(cp.caption_parts(True)).upper()
check("M15 caption words", "EACH FILE VERSION COUNTED ONCE" in panel(a) and "OWN REPOS, NO FORKS" in panel(a))
end = 16 + cp.char_width(7.5) * len(wide)
check("caption clear of the wordmark (wide)", end <= cp.WORDMARK_RIGHT - cp.WORDMARK_WIDTH - 8, end)
ends = [14 + cp.char_width(cp.COMPACT_SMALL) * len(p) for p in cp.caption_parts(True)]
check("caption clear of the wordmark (compact)", max(ends) <= 346 - 100 - 8, ends)

# 4. M10: a language under 1% is not counted; one past the legend's eight is (in this version's words)
c = tempfile.mkdtemp(prefix="m10-")
run_main(load(), c, sorted([ev(d, "Python", 1000, 9) for d in range(1, 30)] + [ev(3, "Go", 5, 9)]))
check("M10 a 0.02% language is not counted", re.search(r"\b" + re.escape(ONE), meta_desc := panel(c)) is not None,
      re.findall(r"languages? [^.<,]*", meta_desc))
langs = ["Python", "Rust", "Go", "C", "Java", "Ruby", "Lua", "Swift", "Kotlin", "Dart"]
many = sorted(ev(d, l, 100, 9) for d in range(1, 20) for l in langs)
run_main(load(), c, many)
check("M10 languages past the legend's eight still count", re.search(re.escape(MANY.format(v=10)), panel(c)) is not None)

# 5. M9: commits but no counted lines: the bars span the commits, and the chart says why it is empty
e = tempfile.mkdtemp(prefix="m9-")
commits = [NOW - d * 86400 for d in range(720)]
run_main(load(), e, [], commits=commits)
p = panel(e)
check("M9 empty chart says no counted code", "no counted code in own repos" in p)
check("M9 bars span the commits (starts ~720 days back)", meta(e)["activity"]["series"]["days"] >= 700,
      meta(e)["activity"]["series"]["days"])

# 6. M17: too many unread repositories keeps the old panels; one is drawn without
f = tempfile.mkdtemp(prefix="m17-")
three = [{"name": n, "isPrivate": False} for n in "abc"]
code = run_main(load(), f, base, extra={"unread": 2}, repos=three)
check("M17 2 of 3 unread keeps the old panels", code == 1 and not os.path.exists(os.path.join(f, "assets")), code)
code = run_main(load(), f, base, extra={"unread": 1}, repos=three)
check("M17 1 of 3 unread is drawn, and counted", code == 0 and meta(f)["scope"]["repositories"]["unread"] == 1, code)

# 7. S14: numbers and plurals
cp = load()
check("S14 billions", cp.fmt(999_960_000) == "1.0B" and cp.fmt(12_345_678_901) == "12.3B",
      (cp.fmt(999_960_000), cp.fmt(12_345_678_901)))
check("S14 millions unchanged", cp.fmt(1_234_567) == "1.2M" and cp.fmt(999_940_000) == "999.9M",
      (cp.fmt(1_234_567), cp.fmt(999_940_000)))
check("S14 plural keeps separators", cp.plural(1234, "day") == "1,234 days" and cp.plural(1, "day") == "1 day")
title, desc = cp.words("all", 5, [0] * 52, [("commits · all branches", "1"), ("active days", "1"), (ROW, "1")], [])
check("S14 singulars in words", "1 commit across" in desc and "1 active day," in desc and ONE in desc, desc)

# 8. cards.json records what was left out, and the notice names both licenses
g = tempfile.mkdtemp(prefix="meta-")
run_main(load(), g, base, extra={"left_out": {"others": 3}, "import_lines": [(NOW - 86400, 777)]})
m = meta(g)
check("coderprint.json left out: 3 others' commits and 777 lines of import",
      m["left_out"]["commits"]["by_other_accounts"] == 3 and m["left_out"]["imports"]["loc_skipped"] == 777,
      m["left_out"])
check("notice in the panel names the licenses, not PolyForm Strict", "LICENSE.md, design/LICENSE.md" in panel(g)
      and "Strict" not in panel(g))

# 9. README handling main() owns, from the older checks: other bytes kept, reruns identical
for name, raw in {"cp1252": "# Hi, I'm Ren\xe9e\n".encode("cp1252"), "bom": b"\xef\xbb\xbf# About\n",
                  "crlf": b"# About\r\n\r\nWords.\r\n"}.items():
    d = tempfile.mkdtemp(prefix="rd-")
    open(os.path.join(d, "README.md"), "wb").write(raw)
    c1 = run_main(load(), d, base)
    after = open(os.path.join(d, "README.md"), "rb").read()
    c2 = run_main(load(), d, base)
    again = open(os.path.join(d, "README.md"), "rb").read()
    kept = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    check("README %s kept and rerun identical" % name, c1 == 0 and c2 == 0 and after.endswith(kept) and after == again,
          (c1, c2))
    shutil.rmtree(d, ignore_errors=True)

# 10. The lines of code headline: in use over written, split production and tests, and the story
h = tempfile.mkdtemp(prefix="loc-")
written = sum(x[2] for x in base)
run_main(load(), h, base, extra={"code": {"production": written // 2, "tests": written // 5, "unread": 0}})
wide, phone = panel(h), panel(h, "panel-compact-dark.svg")
m = {k: v["value"] for k, v in meta(h)["quantity"].items() if isinstance(v, dict) and "value" in v}
check("LOC coderprint.json figures", m["written_loc"] == written and m["production_loc"] == written // 2
      and m["test_loc"] == written // 5 and m["in_use_loc"] == written // 2 + written // 5, m)
check("LOC kicker says lines of code", "LINES OF CODE" in wide and "LINES OF CODE" in phone)
check("LOC no leftover CODE WRITTEN kicker", "CODE WRITTEN" not in wide.upper().replace("LINES OF CODE", ""))
cp = load()
use = cp.fmt(written // 2 + written // 5)
check("LOC in use and written both drawn", ">%s<" % use in wide and ">%s<" % cp.fmt(written) in wide, (use, cp.fmt(written)))
check("LOC story only inside reduced motion guard", "@media (prefers-reduced-motion: no-preference)" in wide
      and re.search(r"@keyframes cp-q", wide) is not None)
bad = re.findall(r'<(?:path|circle|rect|line)[^>]*class="cp-q[^"]*"[^>]*filter=', wide)
check("LOC no animated shape inside a filter", not bad, bad[:2])
dims = re.search(r'<svg[^>]*viewBox="0 0 (\d+) (\d+)"', phone)
check("LOC phone panel 360x806", dims and dims.groups() == ("360", "806"), dims and dims.groups())
dims = re.search(r'<svg[^>]*viewBox="0 0 (\d+) (\d+)"', wide)
check("LOC wide panel size unchanged", dims and dims.groups() == ("576", "445"), dims and dims.groups())
check("LOC title and desc", "lines of code in use" in wide, re.findall(r"<title>[^<]*", wide))
shutil.rmtree(h, ignore_errors=True)

# 11. The card as data: coderprint.json says what the panels draw, what each figure means, and nothing private
PANELS = ("panel-dark.svg", "panel-light.svg", "panel-compact-dark.svg", "panel-compact-light.svg")
k = tempfile.mkdtemp(prefix="data-")
secret = [{"name": "zeta-secret-payroll", "isPrivate": True}, {"name": "omega-client-acme", "isPrivate": True}]
mixed = sorted([ev(d, "Python", 300, 9) for d in range(1, 40)] + [ev(d, "Rust", 120, 9) for d in range(1, 20)]
               + [ev(3, "Go", 5, 9)])
extra = {"code": {"production": 9000, "tests": 3000, "unread": 0}, "left_out": {"others": 7, "automation": 2},
         "copies": {"omega-client-acme"}}
run_main(load(), k, mixed, extra=extra, repos=secret)
d = meta(k)
out = os.path.join(k, "assets")
everything = "".join(open(os.path.join(out, x), encoding="utf-8").read() for x in os.listdir(out)) + open(
    os.path.join(k, "README.md"), encoding="utf-8").read()
check("DATA no repository name anywhere in what is written", not re.search(r"zeta|omega|acme|payroll", everything))
check("DATA schema and generator", d["schema"] == "coderprint/1" and d["generator"]["name"] == "coderprint", d["schema"])
refs = set(re.findall(r'"#/definitions/([a-z_]+)"', json.dumps(d)))
check("DATA every definition referred to exists", refs and refs <= set(d["definitions"]), refs - set(d["definitions"]))
q = d["quantity"]
check("DATA in use = production + tests", q["in_use_loc"]["value"] == q["production_loc"]["value"] + q["test_loc"]["value"])
check("DATA retained = in use / written", q["retained_fraction"]["value"]
      == round(q["in_use_loc"]["value"] / float(q["written_loc"]["value"]), 4), q["retained_fraction"])
check("DATA provenance is measured, derived or display", {v["provenance"] for v in q.values()}
      <= {"measured", "derived", "display"})
series, bys = d["activity"]["series"], d["languages"]["by_slice"]["loc"]
check("DATA 52 slices, each slice's languages adding up to its lines", len(series["loc_written"]) == 52
      and len(series["commits"]) == 52 and all(sum(v[i] for v in bys.values()) == series["loc_written"][i]
                                               for i in range(52)))
check("DATA the series never holds more than written", sum(series["loc_written"]) <= q["written_loc"]["value"])
shares = d["languages"]["share_of_loc"]
check("DATA shares add up to written", abs(sum(s["share"] for s in shares) - 1) < 0.001
      and sum(s["loc"] for s in shares) == q["written_loc"]["value"], shares)
wide = panel(k)
check("DATA the headline written is the headline drawn",
      all(">%s<" % q["as_drawn"][x] in wide for x in ("in_use", "production", "tests", "written")), q["as_drawn"])
check("DATA the stats written are the stats drawn",
      MANY.format(v=d["languages"]["counted"]["value"]) in wide
      and "{:,} commits".format(d["activity"]["commits"]["value"]) in wide)
check("DATA scope and left out", d["scope"]["visibility"] == "public and private"
      and d["scope"]["repositories"]["visible"] == 2 and d["left_out"]["commits"]["by_other_accounts"] == 7
      and d["left_out"]["commits"]["automation"] == 2, (d["scope"], d["left_out"]))
check("DATA well under the relay's 256 KiB", os.path.getsize(os.path.join(out, "coderprint.json")) < 64 * 1024)
check("DATA no time of day anywhere", not re.search(r"T\d\d:\d\d|\d\d:\d\d", json.dumps(d)))
check("DATA presentation holds what the relay reads", set(d["presentation"]["palette"]) == {"light", "dark"})
readme = open(os.path.join(k, "README.md"), encoding="utf-8").read()
block = readme[readme.index("<!-- coderprint:start -->"):readme.index("<!-- coderprint:end -->")]
pointer = re.search(r"<!-- (Machine-readable[^>]*?) -->", block)
check("DISCOVER the README block names the data file in a comment", pointer is not None
      and "assets/coderprint.json" in pointer.group(1) and "coderprint/1" in pointer.group(1), block[:300])
check("DISCOVER the comment cannot end early", pointer is not None and "--" not in pointer.group(1))
url = "https://raw.githubusercontent.com/someone/someone/HEAD/assets/coderprint.json"
check("DISCOVER every panel's metadata names the data file",
      all(url in re.search(r"<metadata>(.*?)</metadata>", panel(k, x), re.S).group(1) for x in PANELS))

# the visible card is unchanged: against the release before, byte for byte outside <metadata>, and the README's
# picture line the same; the release is given this version's languages row, and the description's two new
# sentences are set aside (see the docstring)
if len(sys.argv) > 2:
    source = open(sys.argv[2], encoding="utf-8").read()
    swaps = [('("languages written", ', '(%r, ' % ROW),
             ('"languages written": "{v} languages written"', '%r: %r' % (ROW, MANY)),
             ('"languages written": "1 language written"', '%r: %r' % (ROW, ONE))]
    missing = [old for old, _ in swaps if old not in source]
    for old_text, new_text in swaps:
        source = source.replace(old_text, new_text)
    old = type(sys)("old_%d" % time.perf_counter_ns())
    old.__file__ = os.path.abspath(sys.argv[2])
    exec(compile(source, old.__file__, "exec"), old.__dict__)
    o = tempfile.mkdtemp(prefix="old-")
    run_main(old, o, mixed, extra=extra, repos=secret)
    bare = lambda s: re.sub(r"<metadata>.*?</metadata>", "", s, flags=re.S)
    # the share kept ends the description as a sentence, and the alt text, which drops the last full stop, as a
    # clause before its closing quote
    kept = r" Of what was written, (?:under 1%|\d+%) is kept\.|\. Of what was written, (?:under 1%|\d+%) is kept(?=\")"
    new_only = lambda s: re.sub(r" The bars end on \d\d[A-Z]{3}\d{4}, the day this panel was drawn\.", "",
                                re.sub(kept, "", s))
    check("SAME the release's languages row found and renamed", not missing, missing)
    check("SAME every panel byte-identical to the last release outside <metadata>, but for the new words",
          all(new_only(bare(panel(k, x))) == bare(panel(o, x)) for x in PANELS))
    check("SAME the description's new sentences are there to set aside",
          all(new_only(panel(k, x)) != panel(k, x) for x in PANELS))
    old_readme = open(os.path.join(o, "README.md"), encoding="utf-8").read()
    pictures = lambda r: [l for l in r.splitlines() if l.startswith("<a ") or l.startswith("<p ")]
    check("SAME the README's pictures unchanged but for the share kept in the alt text",
          [new_only(l) for l in pictures(readme)] == pictures(old_readme) and pictures(readme))
    shutil.rmtree(o, ignore_errors=True)

# the move from cards.json: this script's own is removed, anyone else's file of that name is left alone, and the
# guard against a shrinking account reads either
for name, body, gone in (("own", {"palette": {}, "repositories": 1}, True), ("foreign", {"hello": 1}, False)):
    m = tempfile.mkdtemp(prefix="legacy-")
    os.makedirs(os.path.join(m, "assets"))
    json.dump(body, open(os.path.join(m, "assets", "cards.json"), "w"))
    run_main(load(), m, base)
    check("MIGRATE %s cards.json %s" % (name, "removed" if gone else "kept"),
          os.path.exists(os.path.join(m, "assets", "cards.json")) != gone
          and os.path.exists(os.path.join(m, "assets", "coderprint.json")))
    shutil.rmtree(m, ignore_errors=True)
three = [{"name": n, "isPrivate": False} for n in "abc"]
s = tempfile.mkdtemp(prefix="shrink-")
run_main(load(), s, base, repos=three)
check("GUARD fewer repositories than coderprint.json saw keeps the panels",
      run_main(load(), s, base, repos=three[:2], env={"FORCE": ""}) == 1)
shutil.rmtree(s, ignore_errors=True)
s = tempfile.mkdtemp(prefix="shrink-")
os.makedirs(os.path.join(s, "assets"))
json.dump({"palette": {}, "repositories": 3}, open(os.path.join(s, "assets", "cards.json"), "w"))
check("GUARD and fewer than a cards.json saw",
      run_main(load(), s, base, repos=three[:2], env={"FORCE": ""}) == 1)
shutil.rmtree(s, ignore_errors=True)
shutil.rmtree(k, ignore_errors=True)

for folder in (a, b, c, e, f, g):
    shutil.rmtree(folder, ignore_errors=True)
print("PASS %d FAIL %d %s" % (passes, len(fails), fails))
sys.exit(1 if fails else 0)
