#!/usr/bin/env python3
"""coderprint: lines of code written and still in use, commit activity and the language mix over time, built
from every repository an account owns and optionally its work in selected organizations, public and private,
and drawn for its GitHub profile README.

Copyright 2026 Peter Shiller. Licensed under the PolyForm Noncommercial License 1.0.0 (LICENSE.md), with the
additional permissions and the reservations in NOTICE.md; the design in design/ is licensed apart.

It runs as a GitHub Action in the profile repository (see action.yml), or locally from that
repository's folder while signed in with gh. It reads with GH_TOKEN, ideally a read-only token from the
account's own GitHub App, and writes assets/panel-light.svg, assets/panel-dark.svg, their compact
versions for phones (assets/panel-compact-light.svg and assets/panel-compact-dark.svg), assets/coderprint.json,
an empty assets/blank.svg when the README block needs one (see Layout), and a marked block in README.md
(profile/README.md in an organization's .github repository, see profile_repository), leaving the rest of the
README alone. It needs only the Python standard library, gh and git, and no
outside service ever sees the code.

Privacy: Actions logs on a public repository are public, so this script never prints or writes a
repository name, a file path, commit text or an email address, and names none of the private repositories itself. The
panels and assets/coderprint.json hold aggregates only.

What counts as a line of code: a line of a programming or markup language's file that is neither blank nor a
comment (see NOT_CODE and SYNTAXES), each file read whole as its language reads it: Python by its own tokenizer,
most others with their literals followed (see read_lines). Prose (Markdown, TeX, a literate source's prose), data
(YAML, TOML), notebooks and files no language claims are not code. Written: the lines of code added in a file
version, read from its commit's diff as the whole version reads them (see read_added_code) and counted once, the
first time its exact content appears in any repository or branch; a commit that only reformats many files at
once (see sweep) adds nothing for the files whose lines still read alike. In use: the lines of code on each
default branch today that the owner wrote in the window, each written line once, traced through each line's history
(see Trace) and matched by text only where the history cannot say, split into production and test code by where they
live (see is_test). Copies, moves (those git does not pair as well, see moved_files, and blocks moved within a commit,
see moved_blocks), merges, branch landings (a kept branch's squash as well, see LANDING_SHARE) and cross-repository
imports all reuse content that already exists, so they add nothing. Only the owner's own
commits count (see authorship); others', automation's, and a second landing of one change add nothing. A
commit that adds more than IMPORT_FILES brand-new files of code, or a run of commits that adds them in parts
(see import_runs), is treated as bringing in an existing codebase, not writing one: it is a commit, but adds no
lines, unless the owner declares that exact upload as their existing authored work (authored_imports).
That declaration never bypasses attribution, generated-file or copy exclusions. A path is read exactly,
whatever it holds, and the settings of the machine's git that would change what a
history reads as are pinned (see READ_CONFIG), so a local run reads what the Action reads. File versions from
another account's template, or from coderprint itself in a relay copy, count as already written. Vendored
folders, generated output (by folder, by name, or by a generator's mark in a file's first lines), lockfiles,
submodules, symbolic links, Git LFS pointers and data files never count, nor do the paths a repository's
.gitattributes marks linguist-vendored, linguist-generated or linguist-documentation, nor a gh-pages branch
that is not the default, even where a tag reaches it (see pages_only). Every time is moved
to the start of its day before anything is drawn or written. A file's language is read from its name or
extension alone, named as GitHub's Linguist names it (the legends shorten the few names too long for them:
Visual Basic .NET is vb.net there). An extension several languages share counts as Other (.h, .m, .pl, .v),
unless one of them writes far more of it than the rest (.pm counts as Perl, .gd as GDScript); Other holds code
only where every sharer comments compatibly (.h, .m, .fs, .v; see SHARED_CODE).
Known limits: a merge's own conflict resolution is not counted, and in use matches it by text; a line rewritten
counts again; and a squash merge whose branch was deleted collapses its days into one.

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
exactly 100%. At most six tick marks, now always among them, chosen by the data and never crowding.
Languages under 1% of the window's lines are drawn as Other. Each language has one color, the same in
every theme: the widely written have one to themselves, and the rest share one only with languages a
developer seldom writes alongside. When two drawn together would still look alike (CIEDE2000 under
12), the lower-ranked is drawn in a spare instead, so its color then turns on what it is drawn beside.
A thin red Pareto line runs over the stream: the running share of every line in the chart, from 0% at
its left edge to 100% at now. In the activity bars above, each slice's lines rise in green and its
commits hang below in red; each burst is labelled with its lines, and the bars' left end with the day
they start.

Motion: only ever added to a finished panel, and none for a visitor who asks for reduced motion.
Today's activity bar breathes; in the stats rows one dot at a time hops along a row's leader and its
value lights green as the dot arrives; the Pareto line draws itself, fast where lines came fast and
slow across quiet time, then holds; and the headline tells its story (see STORY): the ring and the bar fill
to everything written and glow red with its figure, fall back to what is in use and glow yellow, then to
production, then tests fill back in, each glowing green. A viewer whose animation clock never starts sees the
whole panel.

The watermark: CARDS_MARK_DATA holds its outline as SVG path data (straight segments, filled
even-odd), passed from a secret so the path data is never written to the repository. It is drawn into
the panel as pixels, merged with the background and grid into one image; what is drawn can be seen,
and traced, like any picture. The coderprint wordmark sits over it in the bottom right corner.

Layout: the panel is 576x445. With a relay (CARDS_RELAY), the README shows the panel and the music card
(Spotify's, or the track last played on Apple Music) merged into one image, so neither arrives before
the other, and on a screen 540 CSS px wide or less, a phone's, the relay's compact card instead: the
compact panel over a music strip. With a music card but no relay, the panel sits at 64.1% beside the
Spotify widget at 35.6% (320x445, so the heights match on any screen) or the Apple Music card at 32.0%
(345x534, likewise). With neither, the panel fills the width, and on a phone the compact panel does. The
blocks that switch to a compact card hold two pictures, one for each color scheme. GitHub hides the one
linked to #gh-dark-mode-only in light mode and the other in dark; for a visitor who fixed a theme
rather than following the system's, it also rewrites every source that names a color scheme to always
or never match, and leaves width-only sources alone. So each picture starts with a blank source for the
other scheme, then the compact card for narrow screens, then the wide one. The blank is assets/blank.svg.
It and, without a relay, the panels are addressed absolutely, on raw.githubusercontent.com in the profile
repository (owner/owner), where the Action runs. GitHub would resolve relative addresses there too, in a
srcset as in a src (README_PAIR relies on that); absolute ones only keep the block whole where Markdown
is rendered with no repository to resolve against, as GitHub's Markdown API renders it. Nothing here
repeats what the GitHub profile already shows (name, status, links, location, contribution count).

The compact panel: on a phone the README is about 81 CSS px narrower than the screen, so the merged card is
drawn at about a third of its size and its labels at 3 or 4 px. The compact panel carries the wide one's
numbers, bars, chart, legend and motion at 360x806 (its chart heading shortens to LANGUAGE MIX), drawn at
0.78 to 0.97 of its size on a phone, with nothing that must be read under 10 units: the headline's tiles,
ring and bar run full width with the activity bars under them, the stats run full width and the legend
goes under the chart in two columns. Its bottom corners are square,
since the relay joins it to a strip beneath. The README shows it on screens 540 CSS px wide or less (see
Layout), through the relay or on its own.

Days: active days and streaks count calendar days in the owner's own time zone, and only when the
public profile already shows it. The local time GitHub displays on a profile gives the zone's offset
from UTC today, and the profile's location, looked up in a table of places built from GeoNames, gives a
zone. The shown time zone always wins: the location can only choose among the zones with that offset
today, which settles daylight saving for past days, and a location that says otherwise is ignored. A
location that could mean places in different zones ("Santa Clara", "USA", "SF / NYC") settles nothing:
days then fall at the shown offset, fixed for all past days so their daylight saving is ignored, or with
no shown time zone, in UTC. The zone is never printed or written anywhere.

Themes: the five house themes, Paper, Sepia, Sage, Oxblood and Ink, each in two versions: a lite for a
visitor in light mode and a nite for one in dark mode. They, the chart's colors and the wordmark come from
design/, which is licensed apart from this code; without it the script draws in a plain grey look. GitHub tells a README image which mode the visitor
uses (a <picture> with prefers-color-scheme), so the script draws one panel for each. One theme a day for
everyone, the five in turn by the UTC date, drawn as its lite for light mode and its nite for dark;
CARDS_THEME pins one theme in both. A strip at the top names all five with the drawn version's theme lit.
The strip and the window selector look like switches on purpose: an image cannot switch anything, so a
click goes to where the widget is installed.
"""
import base64
import bisect
import datetime as dt
import difflib
import functools
import gzip
import hashlib
import http.client
import importlib.util
import itertools
import json
import math
import os
import posixpath
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tokenize
import types
import unicodedata
import urllib.parse
import urllib.request
import zlib
from array import array
from collections import Counter, deque, namedtuple
from contextlib import contextmanager
from fractions import Fraction

try:
    import zoneinfo
except ImportError:   # Python before 3.9: days stay in UTC or at the profile's fixed offset
    zoneinfo = None
try:
    import tomllib
except ImportError:   # Python before 3.11: a Cargo.toml is read by its lines instead (see cargo_roots)
    tomllib = None


# The generator's code lives in generator/, one file for each part of the work, and runs here in the order PARTS lists
# as this one module: a part uses the names the parts before it define, and a name replaced on this module (as the
# regression checks replace run or clone) is replaced for every part. The files are read beside this one, not from
# the profile repository being drawn for.
PARTS = ("settings", "commands", "github", "history", "identity", "readers", "syntaxes", "classify", "trace",
         "written", "in_use", "collect", "days", "chart", "watermark", "draw", "headline", "card_data", "compact",
         "main")
for _part in PARTS:
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "generator", _part + ".py")
    with open(_path, encoding="utf-8") as _file:
        _code = compile(_file.read(), _path, "exec")
    exec(_code, globals())  # nosemgrep: python.lang.security.audit.exec-detected.exec-detected
del _part, _path, _file, _code


if __name__ == "__main__":
    try:
        code = main()
    except (RuntimeError, Stopped) as e:
        say("failed: %s" % e)
        code = 2
    except BaseException as e:  # never let a traceback print data into a public log
        say("failed: %s" % type(e).__name__)
        code = 2
    sys.exit(code)
