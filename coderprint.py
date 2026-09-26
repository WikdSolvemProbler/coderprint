#!/usr/bin/env python3
"""coderprint: new lines written, commit activity and the language mix over time, built from every
repository an account owns, public and private, and drawn for its GitHub profile README.

Copyright 2026 Peter Shiller. Licensed under the PolyForm Strict License 1.0.0 (LICENSE.md), with the
additional permission and the reservations in NOTICE.md.

It runs as a GitHub Action in the profile repository (see action.yml), or locally from that
repository's folder while signed in with gh. It reads with GH_TOKEN, ideally a read-only token from the
account's own GitHub App, and writes assets/panel-light.svg, assets/panel-dark.svg, assets/cards.json
and a marked block in README.md, leaving the rest of the README alone. It needs only the Python
standard library, gh and git, and no outside service ever sees the code.

Privacy: Actions logs on a public repository are public, so this script never prints or writes a
repository name, a file path or commit text, and names none of the private repositories itself. The
panels and assets/cards.json hold aggregates only.

What counts as new code: a file version counts once, the first time its exact content appears in
any repository or branch. Copies, moves, merges, branch landings and cross-repository imports all
reuse content that already exists, so they add nothing. A commit that adds more than IMPORT_FILES
brand-new files is treated as bringing in an existing codebase, not writing one, so it is skipped,
as are commits by bots. Vendored folders, generated output, lockfiles and data files never count.
Known limits: a merge's own conflict resolution is not counted, and a change landed twice under
different content (a rebase that also edits) counts twice.

Window: CARDS_WINDOW picks the span the panel covers: all time, or the last 10, 5, 3 or 2 years, or 12
months. The headline, the stats and the language column cover the whole window; a selector at the
chart's top right shows which. The chart and the activity bars start at the oldest real work inside
the window, so they never show empty time before anything existed, and a stray commit long before
everything else cannot stretch them.

The chart: days before now run along a log scale, so the last week gets room and the distant past is
compressed. The mix at each moment is a kernel-weighted share of the lines written near it, eased
toward a bridge between the well-supported moments either side, so a quiet stretch shows the mix
moving from one period of work to the next, and a veil darkens it by how little evidence it rests on.
Evidence is judged per day, so steady work reads as steady at every scale. Every moment sums to
exactly 100%. At most six tick marks, 0 always among them, chosen by the data and never crowding.

The watermark: CARDS_MARK_DATA holds its outline as SVG path data (straight segments, filled
even-odd), passed from a secret so the path data is never written to the repository. It is drawn into
the panel as pixels, merged with the background and grid into one image; what is drawn can be seen,
and traced, like any picture. The coderprint wordmark sits over it in the bottom right corner.

Layout: the panel is 576x445. With a relay (CARDS_RELAY), the README shows the panel and the Spotify
card merged into one image, so neither arrives before the other. Without one, the panel sits at 64.1%
beside the Spotify widget at 35.6% (320x445, so the heights match on any screen). Nothing here repeats
what the GitHub profile already shows (name, status, links, location, contribution count).

Themes: the five house themes. GitHub tells a README image whether the visitor uses light or dark
mode (a <picture> with prefers-color-scheme), so the script draws one panel for each; the light one
rotates daily through Paper, Sepia and Sage, the dark one through Oxblood and Ink, and a strip at the
top names all five with today's lit. The strip and the window selector look like switches on
purpose: an image cannot switch anything, so a click goes to where the widget is installed.
"""
import base64
import bisect
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import zlib
from collections import Counter

WORK = os.getcwd()   # the profile repository being drawn for
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(WORK, "assets")
README = os.path.join(WORK, "README.md")
IMPORT_FILES = 500
TIMEOUT = 900
NOTICE = ("coderprint. Copyright 2026 Peter Shiller. All rights reserved except as licensed under the PolyForm "
          "Strict License 1.0.0: https://github.com/WikdSolvemProbler/coderprint")

# The span the whole panel covers, chosen once by whoever installs it (CARDS_WINDOW): its selector
# label, its name in prose, and its length in days (None for all time).
WINDOWS = {
    "all": ("ALL", "all time", None), "10y": ("10Y", "10 years", 3652), "5y": ("5Y", "5 years", 1826),
    "3y": ("3Y", "3 years", 1096), "2y": ("2Y", "2 years", 730), "12m": ("12M", "12 months", 365),
}
WINDOW_ORDER = ["all", "10y", "5y", "3y", "2y", "12m"]
LINK = os.environ.get("CARDS_LINK") or "https://github.com/WikdSolvemProbler/coderprint"   # where a click goes

EXCLUDED_DIRS = {
    "node_modules", "vendor", "vendors", "third_party", "thirdparty", "dist", "build", "out", "target",
    "coverage", ".next", "__pycache__", ".venv", "venv", "site-packages", ".goldens", ".fixtures",
}
EXCLUDED_EXTS = {
    ".json", ".jsonl", ".lock", ".golden", ".csv", ".tsv", ".log", ".txt", ".aux", ".toc", ".out", ".bbl",
    ".blg", ".synctex", ".gz", ".map", ".snap", ".db", ".sqlite", ".svg", ".ipynb", ".pdf", ".xml",
}
EXCLUDED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock", "poetry.lock", "uv.lock",
    ".gitignore", ".gitattributes", ".gitkeep", "license",
}
LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".rs": "Rust", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".mts": "TypeScript", ".cts": "TypeScript", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".jsx": "JavaScript", ".tex": "TeX", ".sty": "TeX", ".cls": "TeX", ".bib": "TeX",
    ".md": "Markdown", ".mdx": "Markdown", ".rst": "Markdown", ".lean": "Lean", ".ps1": "PowerShell",
    ".psm1": "PowerShell", ".sh": "Shell", ".bash": "Shell", ".css": "CSS", ".scss": "CSS",
    ".html": "HTML", ".htm": "HTML", ".yml": "YAML", ".yaml": "YAML", ".toml": "TOML", ".sql": "SQL",
    ".vbs": "VBScript", ".go": "Go", ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++", ".cc": "C++",
    ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".rb": "Ruby", ".lua": "Lua", ".jl": "Julia",
    ".wl": "Wolfram", ".nb": "Wolfram", ".hs": "Haskell", ".ml": "OCaml", ".bat": "Batchfile",
    ".cmd": "Batchfile",
}
OTHER = "Other"
PROSE = {"Markdown"}  # not a programming language, so it is left out of the languages-written count

# The five house themes. The dark two are moved halfway toward the Spotify widget's own dark style, so
# panel and widget read as one piece; the light three keep their own tokens. "spotify" is the widget's
# background when it is shown on its own, which only comes with white text, so it takes the theme's
# ink; the relay instead recolors the widget to the theme itself.
THEMES = {
    "paper": dict(dark=False, bg="#fbf8f5", line="#d8cfc1", text="#2a1f1a", muted="#6b5e52", dim="#a89c8c",
                  prose="#b8ad9c", other="#cfc6b8", spotify="1e1916", grid=".05", mark=".08"),
    "sepia": dict(dark=False, bg="#f0e6d2", line="#d4c4a8", text="#3e2b1a", muted="#6b5848", dim="#b8a888",
                  prose="#b8a888", other="#cbbd9f", spotify="281e16", grid=".06", mark=".08"),
    "sage": dict(dark=False, bg="#e5e8dd", line="#c4ccbc", text="#1f2a24", muted="#566058", dim="#98a098",
                 prose="#a8b0a0", other="#bcc4b4", spotify="181e1b", grid=".05", mark=".08"),
    "oxblood": dict(dark=True, bg="#1e1315", line="#50343c", text="#f8f3e9", muted="#b6aea7", dim="#6f625c",
                    prose="#e8dfd0", other="#5c4f4a", spotify="1e1315", grid=".035", mark=".09"),
    "ink": dict(dark=True, bg="#100f0e", line="#35322f", text="#f4efe8", muted="#a7a29b", dim="#625e59",
                prose="#e8dfd0", other="#4a4540", spotify="100f0e", grid=".035", mark=".09"),
}
THEME_ORDER = ["paper", "sepia", "sage", "oxblood", "ink"]
LIGHT_THEMES, DARK_THEMES = ["paper", "sepia", "sage"], ["oxblood", "ink"]
GREEN = "#53b14f"   # the Spotify widget's green, for the bars that echo its equalizer
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"   # the widget's stack
MONO = ("'IBM Plex Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', "
        "monospace")
# The house chart palette (terracotta, atlas blue, muted violet, amber, sage), then earthen extras, each
# a distinct hue. It is the same in every theme; only prose and Other follow the theme.
COLORS = {
    "Rust": "#d4835c", "Python": "#7cbac4", "TypeScript": "#8a7090", "JavaScript": "#d4a530",
    "TeX": "#9db886", "HTML": "#c45545", "CSS": "#b0768f", "PowerShell": "#5d8aa8", "Shell": "#a3a86a",
    "YAML": "#c9a27a", "TOML": "#8f8578", "SQL": "#6aa58f", "Lean": "#e0b36a", "VBScript": "#8fb3b8",
}
SPARE = ["#4f8f86", "#b5895f", "#7d6aa8", "#9c6b52", "#6b8f5a", "#a8636f", "#5f7fa0", "#c0a068"]
PANEL_W, PANEL_H = 576, 445

# The chart's geometry: the stream runs x0..x1 (x1 is now), a ribbon eases each layer into the column
# xc..xw, the legend sits right of it; the plot runs t0 (100%) to t1 (0%), ticks on the axis line.
X0, X1, XC, XW, T0, T1, AXIS_Y, TICK_Y = 40, 404, 428, 442, 202, 392, 406, 421
PLOT_W = X1 - X0
TOP_N = 8
H_X = 5.0             # kernel width, in panel units, so it scales with the axis whatever the span
ALPHA_FRAC = 0.05     # the bridge's pull: 5% of the typical lines per day within a kernel
NBINS = 4000          # events are pooled into this many slices of the log axis before the kernel runs
G_QUIET = 24.0        # a quiet stretch has to be at least this wide on the axis to count as one
QUIET_DAYS = 7.0      # and at least this long in time
VEIL = 0.55           # the veil's opacity where the mix rests on no evidence at all
TICK_CHAR = 8 * 0.6 + 1.3   # rendered width of one tick-label character
G_MIN = 2 * TICK_CHAR       # clear space kept between neighbouring tick labels
SNAP = 4.0                  # a data tick may sit at most this far from the moment it marks
MAX_TICKS = 6
LADDER = [1, 7, 30, 365, 90, 180] + [365 * k for k in range(2, 61)]   # round spans, in the order tried
FUTURE_SLACK = 86400        # a commit dated further ahead than this is a broken clock, and is left out

# The current theme's colors; use_theme() sets them before each panel is drawn.
BG = LINE = TEXT = MUTED = DIM = OTHER_COLOR = ""
THEME = {}
LAYER_COLORS = {}

# The watermark sits behind the chart's column, 120 panel units across (scaled down further if a tall
# or turned outline would not fit), centred here, turned CARDS_MARK_TURN degrees.
MARK_WIDTH = 120
MARK_CENTRE = (492, 372)
MARK_PX = 2          # raster pixels per panel unit; 2 lines them up exactly with the half-unit grid stroke
MARK_LIMIT = (8, 8, 566, 435)   # the raster stays clear of the panel's rounded corners
MARK_MAX_CHARS = 49152          # what a GitHub secret can hold
MARK_MAX_COORD = 1e6

# The coderprint wordmark: its letters, read from wordmark.svg beside this script, whose viewBox frames
# them, drawn in the headline's color in the bottom right corner, over the watermark.
WORDMARK_FILE = os.path.join(HERE, "wordmark.svg")
WORDMARK_WIDTH, WORDMARK_RIGHT, WORDMARK_BOTTOM = 118.0, 560.0, 438.0   # ends where the values end

SPOTIFY_URL = ("https://spotify-github-profile.kittinanx.com/api/view?uid={uid}"
               "&cover_image=true&theme=default&show_offline=false&background_color={bg}&interchange=false"
               "&profanity=false&hide_remaster=false")
ALT = "New lines written, commit activity and language mix across public and private repositories"
README_START, README_END = "<!-- coderprint:start -->", "<!-- coderprint:end -->"
# With a relay (CARDS_RELAY), the panel and the Spotify card arrive as one merged image, so neither can
# show up before the other.
README_MERGED = (
    '<a href="{link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{relay}?user={owner}&mode=dark">'
    '<source media="(prefers-color-scheme: light)" srcset="{relay}?user={owner}&mode=light">'
    '<img width="100%" alt="{alt}, and now playing on Spotify" src="{relay}?user={owner}&mode=dark">'
    '</picture></a>')
# Without one, two images side by side. One line with no whitespace between the tags: GitHub pads any
# image with align="right" by 20px, so a float would push the panel below the widget, and a space
# between two inline images could wrap them. Inline and gapless, 64.1% + 35.6% always fits, and
# 64.1/35.6 = 576/320, so the heights match.
README_PAIR = (
    '<p align="right">'
    '<a href="{link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="assets/panel-dark.svg">'
    '<source media="(prefers-color-scheme: light)" srcset="assets/panel-light.svg">'
    '<img width="64.1%" alt="{alt}" src="assets/panel-dark.svg">'
    '</picture></a>'
    '<a href="https://github.com/kittinan/spotify-github-profile"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{spotify_dark}">'
    '<source media="(prefers-color-scheme: light)" srcset="{spotify_light}">'
    '<img width="35.6%" alt="Now playing on Spotify" src="{spotify_dark}">'
    '</picture></a>'
    '</p>')
README_PANEL = (
    '<a href="{link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="assets/panel-dark.svg">'
    '<source media="(prefers-color-scheme: light)" srcset="assets/panel-light.svg">'
    '<img width="64.1%" alt="{alt}" src="assets/panel-dark.svg">'
    '</picture></a>')


def say(msg):
    print(msg, flush=True)


def truthy(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def run(args, cwd=None, env=None):
    """Run a command. Failures carry only the program's name: argv can hold a clone URL, which would
    name a private repository in a public log, so no exception that carries argv leaves here."""
    what = os.path.basename(args[0])
    try:
        p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise RuntimeError("%s timed out after %d seconds" % (what, TIMEOUT)) from None
    except OSError:
        raise RuntimeError("%s could not be started" % what) from None
    if p.returncode != 0:
        raise RuntimeError("%s exited %d" % (what, p.returncode))
    return p.stdout


def gql(query, **variables):
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for k, v in variables.items():
        args += ["-f", "%s=%s" % (k, v)]
    data = json.loads(run(args).decode("utf-8"))
    if "data" not in data:
        raise RuntimeError("the GitHub API returned no data")
    return data["data"]


# ---------------------------------------------------------------- collect


def owner_login():
    """The account to report on: CARDS_OWNER in Actions, where the token belongs to an App, else gh's user."""
    return os.environ.get("CARDS_OWNER") or gql("query { viewer { login } }")["viewer"]["login"]


def list_repositories(owner):
    """Every non-fork repository the account owns, a page of 100 at a time, bar the profile repository."""
    nodes, cursor = [], None
    while True:
        page_args = {"owner": owner}
        if cursor:
            page_args["cursor"] = cursor
        data = gql("""
          query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
            repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                         orderBy: {field: CREATED_AT, direction: ASC}) {
              nodes { name isPrivate } pageInfo { hasNextPage endCursor } } } }""", **page_args)
        if not data.get("repositoryOwner"):
            raise RuntimeError("GitHub has no account named by CARDS_OWNER")
        page = data["repositoryOwner"]["repositories"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return [r for r in nodes if r["name"].lower() != owner.lower()]


def git_auth():
    """How git authenticates. With GH_TOKEN set (Actions), the token rides in an environment-only
    header, never on a command line. Otherwise gh's own credential helper answers."""
    token = os.environ.get("GH_TOKEN")
    if not token:
        return ["-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"], None
    env = dict(os.environ)
    basic = base64.b64encode(("x-access-token:" + token).encode()).decode()
    env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic " + basic, "GIT_TERMINAL_PROMPT": "0"})
    return [], env


def clone(owner, name, dest):
    """Bare clone of every branch. Output is swallowed, because it would name the repository. A cached
    clone is pointed at this repository's address before fetching, so a slot can never read another."""
    flags, env = git_auth()
    url = "https://github.com/%s/%s.git" % (owner, name)
    if os.path.isdir(dest):
        run(["git", "-C", dest, "remote", "set-url", "origin", url])
        run(["git", "-C", dest] + flags + ["fetch", "--quiet", "--prune", "origin", "+refs/heads/*:refs/heads/*"],
            env=env)
        return
    run(["git"] + flags + ["clone", "--bare", "--quiet", url, dest], env=env)


def language_of(path):
    """The language a path counts toward, or None when it is excluded."""
    parts = path.replace("\\", "/").split("/")
    for seg in parts[:-1]:
        s = seg.lower()
        if s in EXCLUDED_DIRS or "vendor" in s or s.endswith("_target"):
            return None
    name = parts[-1].lower()
    if name in EXCLUDED_NAMES or name.endswith(".min.js") or name.endswith(".min.css"):
        return None
    ext = os.path.splitext(name)[1]
    if ext in EXCLUDED_EXTS:
        return None
    return LANGUAGES.get(ext, OTHER)


def read_commits(repo_dir, index):
    """Every non-merge commit on every branch, with its author and each file's new blob and lines added.
    Records are split on NUL, which no git author name or unquoted path can contain."""
    if not run(["git", "-C", repo_dir, "for-each-ref", "--count=1", "refs/heads"]).strip():
        return [], 0  # an empty repository has nothing to read
    out = run(["git", "-C", repo_dir, "-c", "core.quotepath=off", "log", "--all", "--no-merges", "-M",
               "--no-abbrev", "--raw", "--numstat", "--format=%x00%H%x1f%at%x1f%an"]).decode("utf-8", "replace")
    commits, mismatched = [], 0
    for block in out.split("\x00")[1:]:
        head, _, body = block.partition("\n")
        parts = head.split("\x1f", 2)
        if len(parts) != 3 or not re.fullmatch(r"[0-9a-f]{40}", parts[0]) or not parts[1].isdigit():
            mismatched += 1
            continue
        sha, ts, author = parts
        raw, num = [], []
        for line in body.splitlines():
            if line.startswith(":"):
                meta, _, paths = line.partition("\t")
                fields = meta.split()
                raw.append((fields[3], fields[4][0], paths.split("\t")[-1]))
            elif line.count("\t") >= 2:
                a, d, _ = line.split("\t", 2)
                num.append(None if a == "-" else int(a))
        if len(raw) != len(num):
            mismatched += 1
            continue
        files = [(blob, status, path, added) for (blob, status, path), added in zip(raw, num)]
        commits.append((int(ts), index, sha, author.strip().lower().endswith("[bot]"), files))
    return commits, mismatched


def slot(work, owner, name):
    """A cache folder named by a hash of the repository, so it is stable and writes no name to disk."""
    return os.path.join(work, hashlib.sha256((owner + "/" + name).lower().encode()).hexdigest()[:16] + ".git")


def collect(owner, repos, work):
    """Every counted file version as (time, language, new lines), oldest first, plus the times of human
    commits and of skipped imports, over the whole history; the window is applied afterwards. A commit
    held by more than one repository, as in a fork, a mirror or the relay's private copy, counts once."""
    all_commits, mismatched = [], 0
    for i, r in enumerate(repos):
        try:
            dest = slot(work, owner, r["name"])
            clone(owner, r["name"], dest)
            commits, bad = read_commits(dest, i)
        except RuntimeError as e:
            raise RuntimeError("repository %d of %d could not be read: %s" % (i + 1, len(repos), e)) from None
        all_commits += commits
        mismatched += bad

    seen, shas, events, commit_times, import_times = set(), set(), [], [], []
    for ts, idx, sha, bot, files in sorted(all_commits, key=lambda c: (c[0], c[1], c[2])):
        if sha in shas:
            continue
        shas.add(sha)
        fresh = [f for f in files if f[1] != "D" and f[0] not in seen and not f[0].startswith("0000000")]
        if bot:  # a bot's content still counts as seen, so no later commit is credited with it
            seen.update(f[0] for f in fresh)
            continue
        commit_times.append(ts)
        if sum(1 for f in fresh if f[1] == "A") > IMPORT_FILES:
            import_times.append(ts)
            seen.update(f[0] for f in fresh)
            continue
        for blob, status, path, added in fresh:
            if blob in seen:
                continue
            seen.add(blob)
            lang = language_of(path)
            if lang and added:
                events.append((ts, lang, added))
    return {"events": events, "commits": commit_times, "imports": import_times, "mismatched": mismatched,
            "now": dt.datetime.now(dt.timezone.utc).timestamp()}


def remove_tree(path):
    """Delete a folder, clearing the read-only flag git puts on pack files (Windows refuses otherwise).
    Says so, without the path, if anything is left behind."""
    def retry(func, p, _):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except OSError:
            pass
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=retry)
    else:
        shutil.rmtree(path, onerror=retry)
    if os.path.exists(path):
        say("note: some temporary clones could not be removed")


# ---------------------------------------------------------------- numbers


def fmt(n):
    """1,234 as 1.2k, 56,789 as 57k, 1,234,567 as 1.2M; rounded first, so nothing prints as 1000k."""
    if n < 1000:
        return str(int(round(n)))
    k = n / 1e3
    if round(k, 1) < 10:
        return "%.1fk" % k
    if round(k) < 1000:
        return "%.0fk" % k
    return "%.1fM" % (n / 1e6)


def plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def activity(times, now):
    """Active days, the longest streak and the current streak, over the days (UTC) with a commit. The
    current streak may end yesterday, since today is not over."""
    days = sorted({dt.datetime.fromtimestamp(t, dt.timezone.utc).date() for t in times})
    if not days:
        return 0, 0, 0
    longest = run_len = 0
    prev = None
    for d in days:
        run_len = run_len + 1 if prev is not None and (d - prev).days == 1 else 1
        longest = max(longest, run_len)
        prev = d
    today = dt.datetime.fromtimestamp(now, dt.timezone.utc).date()
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
    """A distinct color for every layer: its palette color when free, otherwise the next unused spare."""
    LAYER_COLORS.clear()
    used = set()
    spares = [c for c in SPARE if c not in COLORS.values()]
    for lang in layers:
        if lang == OTHER:
            color = OTHER_COLOR
        elif lang in PROSE:
            color = THEME["prose"]
        else:
            color = COLORS.get(lang)
            if not color or color in used:
                color = next((c for c in spares if c not in used), "#8a8a8a")
        LAYER_COLORS[lang] = color
        used.add(color)


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
    """Negative whole days; the start label rounds up, so a span of 1.5 days reads -2."""
    if v == 0:
        return "0"
    return "-%d" % (math.ceil(S - 1e-9) if v == S else v)


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


# ---------------------------------------------------------------- the flattened watermark


MARK_TOKEN = r"[MmLlHhVvZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def mark_outline(data):
    """The watermark's outline as closed polygons, from SVG path data holding straight segments only
    (M, L, H, V, Z, absolute or relative), filled even-odd. Anything else is refused: other commands,
    stray characters, numbers out of range, data longer than a secret can hold, or an outline too thin."""
    if len(data) > MARK_MAX_CHARS:
        raise RuntimeError("the mark is longer than 48 KB, more than a secret can hold")
    if (not re.fullmatch(r"[MmLlHhVvZz0-9eE.,+\- ]+", data) or re.sub(MARK_TOKEN, " ", data).strip(" ,")
            or re.search(r"^\s*,|,\s*,|[MmLlHhVvZz]\s*,", data)):   # comma runs a browser would refuse
        raise RuntimeError("the mark must be SVG path data with straight segments only (M, L, H, V, Z)")
    tokens = re.findall(MARK_TOKEN, data)
    if not tokens or tokens[0] not in ("M", "m"):
        raise RuntimeError("the mark's path data must start with M")
    polys, cur, x, y, cmd, i = [], [], 0.0, 0.0, None, 0

    def num():
        nonlocal i
        if i >= len(tokens) or tokens[i].isalpha():
            raise RuntimeError("the mark's path data is malformed")
        v = float(tokens[i])
        i += 1
        if not math.isfinite(v) or abs(v) > MARK_MAX_COORD:
            raise RuntimeError("the mark's numbers must lie within plus or minus a million")
        return v

    def point(nx, ny):
        if abs(nx) > MARK_MAX_COORD or abs(ny) > MARK_MAX_COORD:
            raise RuntimeError("the mark's numbers must lie within plus or minus a million")
        return nx, ny

    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":   # close the shape; the pen goes back to where it started
                begin = cur[0] if cur else (x, y)
                if len(cur) > 2:
                    polys.append(cur)
                x, y = begin
                cur = [begin]
                continue
        rel = cmd.islower()
        if cmd in "Mm":
            nx, ny = num(), num()
            x, y = point(x + nx, y + ny) if rel else (nx, ny)
            if len(cur) > 2:
                polys.append(cur)
            cur = [(x, y)]
            cmd = "l" if rel else "L"   # further pairs after a move are lines
        elif cmd in "Ll":
            nx, ny = num(), num()
            x, y = point(x + nx, y + ny) if rel else (nx, ny)
            cur.append((x, y))
        elif cmd in "Hh":
            nx = num()
            x = point(x + nx, y)[0] if rel else nx
            cur.append((x, y))
        elif cmd in "Vv":
            ny = num()
            y = point(x, y + ny)[1] if rel else ny
            cur.append((x, y))
        else:
            raise RuntimeError("the mark's path data is malformed")
    if len(cur) > 2:
        polys.append(cur)
    pts = [p for poly in polys for p in poly]
    if not pts:
        raise RuntimeError("the mark has no usable outline")
    bw = max(p[0] for p in pts) - min(p[0] for p in pts)
    bh = max(p[1] for p in pts) - min(p[1] for p in pts)
    big = max(max(abs(p[0]), abs(p[1])) for p in pts)
    if bw <= 0 or bh <= 0 or min(bw, bh) < 1e-6 * max(big, 1.0):
        raise RuntimeError("the mark has no usable outline")
    return polys


def hexrgb(color):
    return tuple(int(color[k:k + 2], 16) for k in (1, 3, 5))


def png(width, height, rows):
    """An RGB PNG from rows of bytes, with the standard library only."""
    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def flattened_mark(polys, turn):
    """The watermark drawn into one opaque raster together with the background and the grid beneath it,
    as an <image>. Even-odd fill, four sub-scanlines per pixel row and exact horizontal coverage for
    smooth edges. An outline that would not fit clear of the corners is scaled down about its centre."""
    if not polys:
        return ""
    pts = [p for poly in polys for p in poly]
    bx, by = min(p[0] for p in pts), min(p[1] for p in pts)
    bw, bh = max(p[0] for p in pts) - bx, max(p[1] for p in pts) - by
    scale, a = MARK_WIDTH / bw, math.radians(turn)
    cos, sin = math.cos(a), math.sin(a)
    cx, cy = MARK_CENTRE

    def place(p):
        dx, dy = (p[0] - bx - bw / 2) * scale, (p[1] - by - bh / 2) * scale
        return cx + dx * cos - dy * sin, cy + dx * sin + dy * cos

    placed = [[place(p) for p in poly] for poly in polys]
    fit = 1.0
    for px, py in (p for poly in placed for p in poly):
        if px > cx:
            fit = min(fit, (MARK_LIMIT[2] - cx) / (px - cx))
        if px < cx:
            fit = min(fit, (cx - MARK_LIMIT[0]) / (cx - px))
        if py > cy:
            fit = min(fit, (MARK_LIMIT[3] - cy) / (py - cy))
        if py < cy:
            fit = min(fit, (cy - MARK_LIMIT[1]) / (cy - py))
    if fit < 1.0:
        placed = [[(cx + (x - cx) * fit, cy + (y - cy) * fit) for x, y in poly] for poly in placed]
    flat = [p for poly in placed for p in poly]
    x0 = max(MARK_LIMIT[0], math.floor(min(p[0] for p in flat)) - 1)
    y0 = max(MARK_LIMIT[1], math.floor(min(p[1] for p in flat)) - 1)
    x1 = min(MARK_LIMIT[2], math.ceil(max(p[0] for p in flat)) + 1)
    y1 = min(MARK_LIMIT[3], math.ceil(max(p[1] for p in flat)) + 1)
    W, H = (x1 - x0) * MARK_PX, (y1 - y0) * MARK_PX
    SUB = 4
    rows_edges = [[] for _ in range(H)]   # each edge filed under the pixel rows it crosses
    for poly in placed:
        for (ax, ay), (qx, qy) in zip(poly, poly[1:] + poly[:1]):
            if ay != qy:
                e = ((ax - x0) * MARK_PX, (ay - y0) * MARK_PX, (qx - x0) * MARK_PX, (qy - y0) * MARK_PX)
                lo, hi = max(0, int(min(e[1], e[3]))), min(H - 1, int(max(e[1], e[3])))
                for r in range(lo, hi + 1):
                    rows_edges[r].append(e)
    cover = [[0.0] * W for _ in range(H)]
    for row in range(H):
        acc = cover[row]
        for s in range(SUB):
            yy = row + (s + 0.5) / SUB
            hits = sorted(ax + (yy - ay) * (qx - ax) / (qy - ay)
                          for ax, ay, qx, qy in rows_edges[row] if min(ay, qy) <= yy < max(ay, qy))
            for l, r in zip(hits[0::2], hits[1::2]):
                l, r = max(0.0, l), min(float(W), r)
                if r <= l:
                    continue
                il, ir = int(l), min(W - 1, int(r))
                if il == ir:
                    acc[il] += (r - l) / SUB
                    continue
                acc[il] += (il + 1 - l) / SUB
                for k in range(il + 1, ir):
                    acc[k] += 1.0 / SUB
                if ir < W:
                    acc[ir] += (r - ir) / SUB
    bg, ink = hexrgb(BG), hexrgb(TEXT)
    grid_a, mark_a = float(THEME["grid"]), float(THEME["mark"])
    rows = []
    for row in range(H):
        on_row = (y0 * MARK_PX + row) % (24 * MARK_PX) == 0   # the grid stroke covers [24k, 24k + 0.5]
        out = bytearray()
        for col in range(W):
            g = grid_a if on_row or (x0 * MARK_PX + col) % (24 * MARK_PX) == 0 else 0.0
            m = mark_a * min(1.0, cover[row][col])
            for ch in range(3):
                v = bg[ch] * (1 - g) + ink[ch] * g
                out.append(int(round(v * (1 - m) + ink[ch] * m)))
        rows.append(out)
    data = base64.b64encode(png(W, H, rows)).decode()
    return ('<image x="%d" y="%d" width="%d" height="%d" preserveAspectRatio="none" '
            'href="data:image/png;base64,%s"/>' % (x0, y0, x1 - x0, y1 - y0, data))


def load_wordmark():
    """The wordmark's path data and frame from wordmark.svg beside this script. It ships with coderprint,
    so a missing or unreadable file is an error, not a panel quietly drawn without it."""
    try:
        with open(WORDMARK_FILE, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        raise RuntimeError("the coderprint wordmark (wordmark.svg) is missing") from None
    box = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', src)
    d = re.search(r'<path d="([MmLlHhVvCcSsQqTtZz0-9eE.,+\- ]+)"', src)
    if not box or not d:
        raise RuntimeError("the coderprint wordmark (wordmark.svg) could not be read")
    return d.group(1), tuple(float(v) for v in box.groups())


def wordmark(word):
    """The coderprint wordmark in the bottom right corner, over the watermark, in the headline's color."""
    d, (bx, by, bw, bh) = word
    s = WORDMARK_WIDTH / bw
    return ('<path d="%s" fill="%s" fill-rule="evenodd" transform="translate(%.2f %.2f) scale(%.5f) '
            'translate(%.2f %.2f)"/>' % (d, TEXT, WORDMARK_RIGHT - WORDMARK_WIDTH, WORDMARK_BOTTOM - bh * s, s,
                                         -bx, -by))


# ---------------------------------------------------------------- drawing


def use_theme(name):
    global BG, LINE, TEXT, MUTED, DIM, OTHER_COLOR, THEME
    THEME = THEMES[name]
    BG, LINE, TEXT, MUTED, DIM, OTHER_COLOR = (THEME[k] for k in ("bg", "line", "text", "muted", "dim", "other"))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text(x, y, s, size, fill, family, weight=400, anchor="start", spacing=0):
    return ('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" font-weight="%d" fill="%s"%s%s>%s</text>'
            % (x, y, family, size, weight, fill, ' text-anchor="%s"' % anchor if anchor != "start" else "",
               ' letter-spacing="%s"' % spacing if spacing else "", esc(s)))


def label(x, y, s, anchor="start", fill=None, size=9.5):
    """The house chrome: small uppercase mono, tracked out."""
    return text(x, y, s.upper(), size, fill or MUTED, MONO, 500, anchor, 1.3)


LABEL_CHAR = 9.5 * 0.6 + 1.3  # rendered width of one label character


def switch(names, lit, x, y):
    """A row of names that looks like a switch, one lit and underlined in green, thin rules between. Each
    name is fitted to its budgeted width, so the underline and the rules line up in any monospace font."""
    gap, out = 26.0 if len(names) == len(THEME_ORDER) else 14.0, ""
    for i, name in enumerate(names):
        w = LABEL_CHAR * len(name)
        on = i == lit
        out += ('<text x="%.1f" y="%.1f" font-family="%s" font-size="9.5" font-weight="%d" fill="%s" '
                'textLength="%.1f" lengthAdjust="spacing">%s</text>'
                % (x, y, MONO, 600 if on else 500, TEXT if on else DIM, w - 1.3, esc(name.upper())))
        if on:
            out += '<rect x="%.1f" y="%.1f" width="%.1f" height="1.5" rx=".75" fill="%s"/>' % (x, y + 4, w - 1.3, GREEN)
        if i < len(names) - 1:
            sep = x + w + gap / 2 - 0.65
            out += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s"/>' % (sep, y - 8, sep, y + 2, LINE)
        x += w + gap
    return out


def switch_width(names):
    gap = 26.0 if len(names) == len(THEME_ORDER) else 14.0
    return LABEL_CHAR * sum(len(n) for n in names) - 1.3 + gap * (len(names) - 1)


def theme_strip(active):
    """paper | sepia | sage | oxblood | ink, centred at the top, with today's theme lit."""
    return switch(THEME_ORDER, THEME_ORDER.index(active), (PANEL_W - switch_width(THEME_ORDER)) / 2, 24)


def window_selector(window):
    """ALL | 10Y | 5Y | 3Y | 2Y | 12M at the chart's top right, the panel's window lit."""
    names = [WINDOWS[k][0] for k in WINDOW_ORDER]
    return switch(names, WINDOW_ORDER.index(window), 560 - switch_width(names), 192)


def stats_block(window, S, new_lines, spark, rows):
    out = label(16, 52, "new lines written · " + WINDOWS[window][1])
    out += text(15, 94, fmt(new_lines), 40, TEXT, SANS, 700)
    peak = float(max(spark) or 1)
    step = 264.0 / len(spark)
    width = max(1.5, step * 0.6)
    for i, v in enumerate(spark):
        x = 16 + i * step
        now = ' class="now"' if i == len(spark) - 1 else ""
        if v:
            h = 3 + 34 * math.sqrt(v / peak)
            out += ('<rect%s x="%.2f" y="%.2f" width="%.2f" height="%.2f" rx="%.2f" fill="%s"/>'
                    % (now, x, 142 - h, width, h, width / 2, GREEN))
        else:
            out += '<rect%s x="%.2f" y="141" width="%.2f" height="1" fill="%s"/>' % (now, x, width, LINE)
    days = math.ceil(S - 1e-9)
    out += label(16, 158, plural(days, "day") + " ago", size=8) + label(280, 158, "today", "end", size=8)
    out += '<line x1="292" y1="42" x2="292" y2="156" stroke="%s"/>' % LINE
    for i, (name, value) in enumerate(rows):
        y = 56 + i * 24
        start = 306 + LABEL_CHAR * len(name) + 6
        stop = 560 - 7.6 * len(value) - 8
        leader = ('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.8" '
                  'stroke-dasharray="0.01 4.5" stroke-linecap="round"/>' % (start, y - 3, stop, y - 3, DIM)
                  if stop > start else "")
        out += label(306, y, name) + leader + text(560, y, value, 13, TEXT, SANS, 600, "end")
    return out


def stream_block(window, stream, column, S, c, has_history, recent_day=None):
    """The language mix on the log axis, flowing into a column for the whole window that is also the
    legend. stream: (age in days, language, lines) within the chart's span; column: every line in the
    window, strays included."""
    out = label(16, 192, "language mix · share of new lines") + window_selector(window)
    if not stream:
        empty = "nothing in the last " + WINDOWS[window][1] if has_history else "no code yet"
        return out + text(222, 300, empty, 12, MUTED, MONO, 400, "middle")
    totals = Counter()
    for _, lang, n in column:
        totals[lang] += n
    top = [lang for lang, _ in totals.most_common() if lang != OTHER][:TOP_N]
    layers = top + ([OTHER] if any(l not in top for l in totals) else [])
    assign_colors(layers)
    amount = {lang: (sum(v for l, v in totals.items() if l not in top) if lang == OTHER else totals[lang])
              for lang in layers}
    grand = float(sum(amount.values()))
    xs, shares, conf, stretches = mix_along(stream, S, c, layers, top, recent_day)
    y_of = lambda v: T1 - (T1 - T0) * v

    base, col_base, fills, edges, mids = [0.0] * len(xs), 0.0, "", "", []
    for j, lang in enumerate(layers):
        upper = [b + shares[j][i] for i, b in enumerate(base)]
        col_top = col_base + amount[lang] / grand
        pts = " ".join("%d,%.1f" % (x, y_of(u)) for x, u in zip(xs, upper))
        back = " ".join("%d,%.1f" % (x, y_of(b)) for x, b in zip(reversed(xs), reversed(base)))
        ue, be, ct, cb = y_of(upper[-1]), y_of(base[-1]), y_of(col_top), y_of(col_base)
        # the stream and the ribbon easing from today's mix into the column, as one shape so no
        # anti-aliased seam shows where they meet
        ribbon = ("C%.1f,%.1f %.1f,%.1f %.1f,%.1f L%.1f,%.1f L%.1f,%.1f L%.1f,%.1f C%.1f,%.1f %.1f,%.1f %.1f,%.1f"
                  % (X1 + 12, ue, XC - 12, ct, XC, ct, XW, ct, XW, cb, XC, cb, XC - 12, cb, X1 + 12, be, X1, be))
        fills += '<path d="M%s %s L%s Z" fill="%s"/>' % (pts, ribbon, back, LAYER_COLORS[lang])
        edges += ('<polyline points="%s" stroke="%s" stroke-width="1" fill="none"/><path d="M%.1f,%.1f C%.1f,%.1f '
                  '%.1f,%.1f %.1f,%.1f L%.1f,%.1f" stroke="%s" stroke-width="1" fill="none"/>'
                  % (pts, BG, X1, ue, X1 + 12, ue, XC - 12, ct, XC, ct, XW, ct, BG))
        mids.append((lang, (ct + cb) / 2, amount[lang] / grand))
        base, col_base = upper, col_top

    # the veil: the background laid over the stream, as opaque as the mix is inferred rather than seen
    stops = "".join('<stop offset="%.4f" stop-color="%s" stop-opacity="%.3f"/>'
                    % ((xs[i] - X0) / float(PLOT_W), BG, VEIL * (1 - conf[i]))
                    for i in sorted(set(range(0, len(xs), 4)) | {len(xs) - 1}))
    veil = ('<defs><linearGradient id="veil" gradientUnits="userSpaceOnUse" x1="%d" y1="0" x2="%d" y2="0">%s'
            '</linearGradient></defs><rect x="%d" y="%d" width="%d" height="%d" fill="url(#veil)"/>'
            % (X0, X1, stops, X0, T0, PLOT_W, T1 - T0))

    # Legend beside the column: labels keep their band's height where they can, spread apart so none
    # collide, stay inside the plot, and an elbow leader ties each one to its band.
    order = sorted(mids, key=lambda m: m[1])
    shown = percents({lang: share for lang, _, share in order})
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
                      text(454, ly, lang.lower(), 10.5, TEXT, MONO, 500),
                      text(560, ly, shown[lang], 10.5, MUTED, MONO, 400, "end")))

    grid = "".join('<text x="34" y="%.1f" text-anchor="end" font-family="%s" font-size="8" fill="%s">%s</text>'
                   % (y_of(v) + 3, MONO, MUTED, s) for v, s in ((1, "100%"), (0.5, "50%"), (0, "0%")))
    grid += ('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-dasharray="2 4"/>'
             % (X0, y_of(0.5), X1, y_of(0.5), LINE))
    # the 0 line: where the dated stream ends and the ribbon into the column begins
    zero = ('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-opacity=".6"/>'
            % (X1, T0 - 2, X1, AXIS_Y, TEXT))
    axis = '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s"/>' % (X0, AXIS_Y, X1, AXIS_Y, LINE)
    for v in pick_ticks(S, c, stretches):
        x = X0 if v == S else x_of_age(v, S, c)
        ink = TEXT if v == 0 else MUTED   # 0 in the text color, the foot of the 0 line
        axis += ('<circle cx="%.1f" cy="%d" r="2.4" fill="%s"/>' % (x, AXIS_Y, ink)
                 + label(x, TICK_Y, tick_label(v, S), "start" if v == S else "middle", ink, 8))
    axis += text(34, TICK_Y, "DAYS", 8, MUTED, MONO, 500, "end")   # untracked, so it stays in the gutter
    return out + grid + fills + edges + veil + zero + axis + legend


# Every mark is drawn in its final state. A browser freezes the animation clock of an SVG image in a
# background tab, and some viewers never start it, so an intro that fades or grows things in shows a
# blank panel there. The one motion is today's bar breathing like the widget's equalizer, and it
# starts at full opacity, so a frozen clock still shows it.
STYLE = ("@media (prefers-reduced-motion: no-preference){"
         "@keyframes breathe{50%{opacity:.45}}.now{animation:breathe 1.8s ease-in-out infinite}}")


def panel_svg(theme, window, S, c, new_lines, spark, rows, stream, column, has_history, mark_polys, turn,
              private, word, recent_day=None):
    use_theme(theme)
    defs = ('<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" '
            'stroke="%s" stroke-opacity="%s" fill="none"/></pattern>' % (TEXT, THEME["grid"]))
    caption = "normalized · by type · %seach line counted once" % ("private repos included · " if private else "")
    body = (flattened_mark(mark_polys, turn)
            + theme_strip(theme)
            + stats_block(window, S, new_lines, spark, rows)
            + '<line x1="16" y1="176" x2="560" y2="176" stroke="%s"/>' % LINE
            + stream_block(window, stream, column, S, c, has_history, recent_day)
            + label(16, 437, caption, size=7.5)
            + wordmark(word))
    # the notice is an element, not a comment, so it survives when the relay merges the panel
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
            'aria-label="%s">\n<metadata>%s</metadata>\n<style>%s</style>\n<defs>%s</defs>\n'
            '<rect width="%d" height="%d" rx="10" fill="%s"/><rect width="%d" height="%d" rx="10" fill="url(#grid)"/>\n'
            '%s\n</svg>\n' % (PANEL_W, PANEL_H, PANEL_W, PANEL_H, ALT, esc(NOTICE), STYLE, defs, PANEL_W, PANEL_H,
                              BG, PANEL_W, PANEL_H, body))


def todays_themes(light=None, dark=None, today=None):
    """Today's light and dark themes: Paper, Sepia and Sage take turns by day, as do Oxblood and Ink."""
    day = (today or dt.datetime.now(dt.timezone.utc).date()).toordinal()
    return light or LIGHT_THEMES[day % len(LIGHT_THEMES)], dark or DARK_THEMES[day % len(DARK_THEMES)]


# ---------------------------------------------------------------- main


def settings():
    """The installer's choices, all checked before any work: window, themes, Spotify user id, relay
    address, mark."""
    window = os.environ.get("CARDS_WINDOW", "").strip().lower() or "all"
    if window not in WINDOWS:
        raise RuntimeError("CARDS_WINDOW must be one of %s" % ", ".join(WINDOW_ORDER))
    light = os.environ.get("CARDS_LIGHT", "").strip().lower() or None
    dark = os.environ.get("CARDS_DARK", "").strip().lower() or None
    if light and light not in LIGHT_THEMES:
        raise RuntimeError("CARDS_LIGHT must be one of %s" % ", ".join(LIGHT_THEMES))
    if dark and dark not in DARK_THEMES:
        raise RuntimeError("CARDS_DARK must be one of %s" % ", ".join(DARK_THEMES))
    uid = os.environ.get("CARDS_SPOTIFY_UID", "").strip()
    if uid and not re.fullmatch(r"[A-Za-z0-9]{1,64}", uid):
        raise RuntimeError("CARDS_SPOTIFY_UID must be letters and digits only")
    relay = os.environ.get("CARDS_RELAY", "").strip().rstrip("/")
    if relay and not re.fullmatch(r"https://[A-Za-z0-9.-]+(/[A-Za-z0-9._/-]*)?", relay):
        raise RuntimeError("CARDS_RELAY must be a plain https address")
    try:
        turn = float(os.environ.get("CARDS_MARK_TURN", "").strip() or 0)
    except ValueError:
        raise RuntimeError("CARDS_MARK_TURN must be a number of degrees") from None
    if not math.isfinite(turn):
        raise RuntimeError("CARDS_MARK_TURN must be a number of degrees")
    data = " ".join(os.environ.get("CARDS_MARK_DATA", "").split())
    return window, light, dark, uid, relay, (mark_outline(data) if data else None), turn, load_wordmark()


def previous_meta(path):
    """Last run's cards.json, or an empty record if it is missing or not what this script writes."""
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def new_readme(block):
    """README.md as bytes, with the panel's block between its markers and every other byte as it was:
    any encoding (undecodable bytes pass through untouched), a byte order mark kept at the very start,
    and the file's own line endings kept, the marker lines included. A README that is only an earlier
    unmarked coderprint block is replaced; any other README gets the block on top."""
    try:
        with open(README, "rb") as f:
            raw = f.read()
    except OSError:
        raw = b""
    bom = raw.startswith(b"\xef\xbb\xbf")
    old = raw[3:].decode("utf-8", "surrogateescape") if bom else raw.decode("utf-8", "surrogateescape")
    eol = "\r\n" if "\r\n" in old else "\n"
    marked = eol.join((README_START, block, README_END))
    a, b = old.find(README_START), old.find(README_END)
    lone = old.strip()
    ours = ("\n" not in lone and (lone.startswith('<a href="%s"' % LINK)
                                  or lone.startswith('<p align="right"><a href="%s"' % LINK)))
    if 0 <= a < b:
        text = old[:a] + marked + old[b + len(README_END):]
    elif not lone or ours:
        text = marked + eol
    else:
        text = marked + eol + eol + old
    return (b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8", "surrogateescape")


def write_all(files):
    """Write every file through a temporary name, and move them into place only once all are written, so
    a failure leaves the old set whole; leftovers are removed either way. files: path to bytes."""
    temps = {}
    try:
        for path, content in files.items():
            temps[path] = path + ".tmp"
            with open(temps[path], "wb") as f:
                f.write(content)
        for path, tmp in temps.items():
            os.replace(tmp, path)
    finally:
        for tmp in temps.values():
            if os.path.exists(tmp):
                os.remove(tmp)


def stop_on_term(*_):
    raise RuntimeError("stopped by the step's time limit")


def main():
    signal.signal(signal.SIGTERM, stop_on_term)   # unwinds through the clean-up below instead of dying
    window, light_choice, dark_choice, uid, relay, mark_polys, turn, word = settings()
    owner = owner_login()
    light, dark = todays_themes(light_choice, dark_choice)
    if relay:
        block = README_MERGED.format(link=LINK, relay=relay, owner=owner, alt=ALT)
    elif uid:
        block = README_PAIR.format(link=LINK, alt=ALT,
                                   spotify_dark=SPOTIFY_URL.format(uid=uid, bg=THEMES[dark]["spotify"]),
                                   spotify_light=SPOTIFY_URL.format(uid=uid, bg=THEMES[light]["spotify"]))
    else:
        block = README_PANEL.format(link=LINK, alt=ALT)
    readme = new_readme(block)   # read before any cloning, so a README problem fails early
    repos = list_repositories(owner)
    private = sum(1 for r in repos if r["isPrivate"])

    meta_path = os.path.join(OUT_DIR, "cards.json")
    before = previous_meta(meta_path)
    was = before.get("repositories")
    if isinstance(was, int) and len(repos) < was and not truthy("FORCE"):
        say("Fewer repositories are visible than last time (%d, was %d). A repository may have been deleted, "
            "or the token may have lost access, so the existing panels are kept. Run the workflow with force "
            "to overwrite." % (len(repos), was))
        return 1

    work = os.environ.get("CLONE_CACHE") or tempfile.mkdtemp(prefix="cards-")
    os.makedirs(work, exist_ok=True)
    try:
        data = collect(owner, repos, work)
    finally:
        if not os.environ.get("CLONE_CACHE"):
            remove_tree(work)

    now, days_back = data["now"], WINDOWS[window][2]
    events = [e for e in data["events"] if e[0] <= now + FUTURE_SLACK]
    commit_times = [t for t in data["commits"] if t <= now + FUTURE_SLACK]
    start = now - days_back * 86400 if days_back else float("-inf")
    column = [(max(0.0, (now - t) / 86400.0), lang, n) for t, lang, n in events if t >= start]
    recent_day = None
    if column:
        oldest, newest, recent_day = real_work(column)
        S = max(0.05, oldest)   # a history hours old starts at its first commit too
        if days_back:
            S = min(S, float(days_back))
        c = knee(newest, S)
    else:
        S, c = float(days_back or 1), 1.0
    stream = [e for e in column if e[0] <= S]
    new_lines = sum(n for _, _, n in column)
    spark = [0] * 52
    for age, _, n in stream:
        spark[min(51, max(0, int((S - age) / S * 52)))] += n
    active, longest, current = activity([t for t in commit_times if t >= start], now)
    rows = [
        ("commits · all branches", "{:,}".format(sum(1 for t in commit_times if t >= start))),
        ("active days", str(active)),
        ("longest streak", plural(longest, "day")),
        ("current streak", plural(current, "day")),
        ("languages written", str(len({l for _, l, _ in column if l != OTHER and l not in PROSE}))),
    ]

    panels = {"panel-light.svg": light, "panel-dark.svg": dark}
    drawn = {os.path.join(OUT_DIR, fname): panel_svg(theme, window, S, c, new_lines, spark, rows, stream, column,
                                                     bool(events), mark_polys, turn, private > 0, word,
                                                     recent_day).encode("utf-8")
             for fname, theme in panels.items()}
    palette = lambda t: {k: THEMES[t][k] for k in ("bg", "text", "muted", "line")}
    meta = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "window": window,
        "span_days": round(S, 2), "repositories": len(repos), "private_repositories": private,
        "commits": int(rows[0][1].replace(",", "")), "new_lines": new_lines,
        "imports_skipped": sum(1 for t in data["imports"] if t >= start), "unparsed_commits": data["mismatched"],
        "future_dated_left_out": len(data["events"]) - len(events),
        "themes": {"light": light, "dark": dark}, "palette": {"light": palette(light), "dark": palette(dark)},
    }
    if uid:
        meta["spotify"] = {"uid": uid}

    os.makedirs(OUT_DIR, exist_ok=True)
    # coderprint writes these four files and never deletes anything. The README goes first, being the one
    # most likely held open by an editor, and cards.json last, so it only ever describes panels in place.
    files = {README: readme}
    files.update(drawn)
    files[meta_path] = (json.dumps(meta, indent=2) + "\n").encode("utf-8")
    try:
        write_all(files)
    except OSError:
        raise RuntimeError("the panel files could not be written") from None
    say("panels written (%s, %s, %s): %d repositories, %s commits, %s new lines, chart over %s, %d import "
        "commits skipped, %d commits unparsed" % (light, dark, window, len(repos), rows[0][1], fmt(new_lines),
                                                   plural(math.ceil(S - 1e-9), "day"), meta["imports_skipped"],
                                                   data["mismatched"]))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except RuntimeError as e:
        say("failed: %s" % e)
        code = 2
    except BaseException as e:  # never let a traceback print data into a public log
        say("failed: %s" % type(e).__name__)
        code = 2
    sys.exit(code)
