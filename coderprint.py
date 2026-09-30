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

WORK = os.getcwd()   # the profile repository being drawn for
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(WORK, "assets")
README = os.path.join(WORK, "README.md")
IMPORT_FILES = 500
TIMEOUT = 900
DEADLINE = None   # the run's own deadline, on time.monotonic(), when CARDS_TIME_LIMIT sets one (see time_limit)
RESERVE = 120     # seconds kept back from it for reading the profile and drawing and writing the panels
LOOKUP_RESERVE = 60   # and kept back as well while repositories are read, for asking whose each address is after them
UNREAD_SHARE = 0.10   # the panels are redrawn when at most one repository, or this share of them, could not be read
UPSTREAM = "WikdSolvemProbler/coderprint"   # this project, whose files a relay copy holds but did not write
RELAY_FILES = {"api/card.js", "lib/compose.js"}   # files every relay copy of it holds, both of them
# The lookups that tell the owner's code from others', named in collect()'s "unchecked" when GitHub cannot answer
# one: the run then keeps the existing panels rather than count everything as the owner's (see main).
UNCHECKED = {"authorship": "whose each commit's address is",
             "templates": "which of the repositories were made from another account's template"}
ALIASES = 50        # commits looked up in one query when telling whose an email address is
RESOLVE_CALLS = 20  # and at most this many queries a run; addresses past them stay unknown
# Automation that commits under a name or address of its own rather than a [bot] one: git scraping, release
# tooling, and a workflow's commit authored as whoever triggered it, which the committer then gives away.
AUTOMATION_NAMES = {"automated", "github action", "github actions", "github-actions", "actions-user",
                    "semantic-release-bot"}
AUTOMATION_EMAILS = {"action@github.com", "actions@github.com", "actions@users.noreply.github.com",
                     "github-actions@github.com", "41898282+github-actions[bot]@users.noreply.github.com"}
# A GitHub App's own noreply address, which any commit made as the App carries whatever name it gives; and an
# account's own noreply address of the id+login form, whose id no change of login alters (see authorship).
BOT_NOREPLY = re.compile(r"(?:\d+\+)?[^@\s]*\[bot\]@users\.noreply\.github\.com")
NOREPLY = re.compile(r"(\d+)\+[^@\s]+@users\.noreply\.github\.com")
# The name of a bot or a coding agent committing under an identity of its own ("Renovate Bot", "Cursor Agent",
# "release-bot"): its last word is bot or agent. Such a name tells no person's work (see authorship).
AGENT_NAME = re.compile(r"(?:^|[\s._-])(?:bot|agent)$")
# Names a machine, an editor's container or a tutorial gives a commit, which say nothing about who wrote it: one the
# owner's own commits used is never taken as the owner's name for another address (see authorship).
GENERIC_NAMES = {"root", "admin", "administrator", "user", "owner", "ubuntu", "debian", "pi", "vscode", "node",
                 "codespace", "codespaces", "gitpod", "runner", "vagrant", "ec2-user", "docker", "jenkins", "git",
                 "your name", "yourname", "unknown", "localhost", "(none)"}
Commit = namedtuple("Commit", "ts repo sha bot email name subject files")
Change = namedtuple("Change", "blob status path added deleted")
# A sweep: a commit that modifies at least SWEEP_FILES counted files, nearly every one (SWEEP_SHARE) adding
# within SWEEP_BALANCE of what it deletes, as reformatting, re-indenting or a line-ending change does. Its
# balanced files that delete a line add no lines (one that only gains a line was written to). git's own whitespace
# options (-w, -b) would say the same file by file, but on real histories they made reading hundreds of times
# slower and dropped files from the line counts.
SWEEP_FILES, SWEEP_SHARE, SWEEP_BALANCE = 10, 0.9, 0.1
# And a file of such a commit is swept only when its changes are alike: at least SWEEP_ALIKE of its changed lines of
# code still read nearly as they did (difflib's ratio ALIKE_RATIO or more, spacing aside), as a re-indented, re-ended
# or renamed line does (see alike_share). A rewrite that happens to add what it deletes, a migration or a new body,
# is written again, as README says a rewrite is; so is a file that only gains lines.
SWEEP_ALIKE, ALIKE_RATIO = 0.8, 0.6
SWEEP_WATCH = set()   # the commits of the repository being read that could be sweeps, whose changes are paired
NOTICE = ("Drawn by coderprint (https://github.com/WikdSolvemProbler/coderprint): its code, design and wordmark are "
          "Peter Shiller's, licensed as LICENSE.md, design/LICENSE.md and NOTICE.md there say. What the card reports "
          "is its owner's.")

# The span the whole panel covers, chosen once by whoever installs it (CARDS_WINDOW): its selector
# label, its name in prose, and its length in days (None for all time).
WINDOWS = {
    "all": ("ALL", "all time", None), "10y": ("10Y", "10 years", 3652), "5y": ("5Y", "5 years", 1826),
    "3y": ("3Y", "3 years", 1096), "2y": ("2Y", "2 years", 730), "12m": ("12M", "12 months", 365),
}
WINDOW_ORDER = ["all", "10y", "5y", "3y", "2y", "12m"]
LINK = os.environ.get("CARDS_LINK") or "https://github.com/WikdSolvemProbler/coderprint"   # where a click goes

# A folder whose name ends in a vendor word holds others' code whatever comes before it (s01t00_vendor,
# go-vendor, lib_vendored), while one that only starts with it is the owner's own (src/vendor_portal).
VENDOR_ENDS = tuple(sep + word for sep in "_-" for word in ("vendor", "vendors", "vendored")) + ("_target",)
EXCLUDED_DIRS = {   # whole folder names
    "node_modules", "vendor", "vendors", "vendored", "_vendor", "third_party", "thirdparty", "target",
    ".next", "__pycache__", ".venv", "venv", "site-packages", ".goldens", ".fixtures", ".dart_tool", ".idea", ".lake",
    ".mvn", ".nuxt", ".stack-work", ".svelte-kit", ".terraform", ".yarn", "3rd-party", "3rd_party", "3rdparty",
    "__generated__", "_build", "_esy", "_opam", "_site", "bower_components", "carthage", "deriveddata", "dist-newstyle",
    "elm-stuff", "flow-typed", "godeps", "htmlcov", "lake-packages", "pods", "testdata", "third-party",
    "jspm_packages", "web_modules",
}
# Folders a build writes its output to. At the top of a repository or of a module (build/, app/build/, dist/) nothing
# in them counts: CMake's, Gradle's and Android's builds write C, C++ and Java there (R.java, CMakeCCompilerId.c), and
# setuptools copies Python there. Below a folder of source (SOURCE_DIRS) the same names are packages of the owner's
# own code (Go's internal/build and cmd/dist, a Java package named coverage under src/main/java, src/out), so there
# only web output (HTML, CSS, JavaScript and TypeScript declarations) is left out. Source kept in a top-level build/
# or coverage/ folder (as coverage.py keeps its own) is left out with the output: the conservative reading.
OUTPUT_DIRS = {"dist", "build", "out", "coverage"}
SOURCE_DIRS = {"src", "source", "sources", "lib", "pkg", "internal", "cmd", "packages", "scripts", "tools"}
# Vendor folders by convention only at a repository's root (C and C++ projects' extern/ and external/, Elixir's and
# C projects' deps/), where the same names deeper down are usually the owner's own modules (src/external/api.ts)
ROOT_VENDOR_DIRS = {"extern", "external", "deps"}
# and at any depth, a pair of folders: WordPress's installed plugins, Unity's third-party plugins
VENDOR_PAIRS = {("wp-content", "plugins"), ("assets", "plugins")}
EXCLUDED_EXTS = {
    ".json", ".jsonl", ".lock", ".golden", ".csv", ".tsv", ".log", ".txt", ".aux", ".toc", ".out", ".bbl", ".blg",
    ".synctex", ".gz", ".map", ".snap", ".db", ".sqlite", ".svg", ".ipynb", ".pdf", ".xml", ".csproj", ".diff",
    ".filters", ".fsproj", ".gcode", ".geojson", ".har", ".iml", ".json5", ".jsonc", ".ma", ".ndjson", ".nib", ".obj",
    ".patch", ".pbxproj", ".plist", ".po", ".pot", ".proj", ".props", ".resx", ".rktd", ".sagews", ".sarif", ".sln",
    ".stl", ".storyboard", ".tab", ".targets", ".vbproj", ".vcxproj", ".webmanifest", ".xcuserstate",
    ".xcworkspacedata", ".xib", ".xlf", ".xliff",
    # notebooks, which hold their output cells beside their input, as .ipynb does: Mathematica's and its CDF
    ".nb", ".nbp", ".cdf",
    # what the Unity and Godot editors write: scenes, prefabs, assets, import settings and resources
    ".meta", ".unity", ".prefab", ".mat", ".anim", ".controller", ".overridecontroller", ".asset", ".physicmaterial",
    ".mask", ".mixer", ".playable", ".spriteatlas", ".terrainlayer", ".lighting", ".shadergraph", ".shadersubgraph",
    ".asmdef", ".asmref", ".tscn", ".tres", ".import",
}
EXCLUDED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock", "poetry.lock", "uv.lock", ".gitignore",
    ".gitattributes", ".gitkeep", ".gitmodules", ".git-blame-ignore-revs", ".mailmap", "license", ".bash_history", ".rapp.history", ".rhistory", ".secrets.baseline",
    ".terraform.lock.hcl", "aclocal.m4", "bun.lockb", "cargo.toml.orig", "config.guess", "config.sub", "configure",
    "cpplint.py", "dotnet-install.ps1", "dotnet-install.sh", "erlang.mk", "go.sum", "gradlew", "gradlew.bat",
    "juliamanifest.toml", "libtool.m4", "ltoptions.m4", "ltsugar.m4", "ltversion.m4", "lt~obsolete.m4", "manifest.toml",
    "mvnw", "mvnw.cmd", "package.resolved", "ppport.h", "waf",
    "makefile.coq", "makefile.coq.conf",   # what coq_makefile writes
}
EXCLUDED_PREFIXES = (".pnp.",)   # Yarn's Plug'n'Play loader
EXCLUDED_SUFFIXES = (   # minified, and generated from a schema or a designer
    ".min.js", ".min.css", "-min.js", "-min.css", ".designer.cs", ".designer.vb", ".feature.cs", ".zep.c", ".zep.h",
    ".zep.php", "_tlb.pas", ".pb.go", "_pb2.py", "_pb2.pyi", "_pb2_grpc.py", ".pb.cc", ".pb.h", "_pb.js", "_grpc_pb.js",
    "_pb.d.ts", ".pb.swift", ".g.dart", ".freezed.dart",
)
# Languages by extension, named and grouped as GitHub's Linguist does, with coderprint's own folds: CSS
# preprocessors count as CSS, prose markups as Markdown and SQL dialects as SQL. An extension several
# languages share (.h, .m, .pl, .v, .fs, .cls and others) is left out, so it counts as Other, unless one
# of them writes far more of it than the rest (.pm is Perl, .r is R, .gd is GDScript).
LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".pyw": "Python", ".py3": "Python", ".gyp": "Python", ".gypi": "Python",
    ".lmi": "Python", ".pyde": "Python", ".pyp": "Python", ".pyt": "Python", ".tac": "Python", ".wsgi": "Python",
    ".xpy": "Python", ".smk": "Python", ".snakefile": "Python", ".pyx": "Cython", ".pxd": "Cython", ".pxi": "Cython",
    ".rs": "Rust", ".ts": "TypeScript", ".cts": "TypeScript", ".mts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript", ".es6": "JavaScript",
    "._js": "JavaScript", ".bones": "JavaScript", ".jake": "JavaScript", ".javascript": "JavaScript",
    ".jsb": "JavaScript", ".jscad": "JavaScript", ".jsfl": "JavaScript", ".jslib": "JavaScript", ".jsm": "JavaScript",
    ".jspre": "JavaScript", ".jss": "JavaScript", ".njs": "JavaScript", ".pac": "JavaScript", ".sjs": "JavaScript",
    ".ssjs": "JavaScript", ".xsjs": "JavaScript", ".xsjslib": "JavaScript", ".tex": "TeX", ".sty": "TeX", ".ltx": "TeX",
    ".dtx": "TeX", ".ins": "TeX", ".bbx": "TeX", ".cbx": "TeX", ".lbx": "TeX", ".mkii": "TeX", ".mkiv": "TeX",
    ".mkvi": "TeX", ".bib": "TeX", ".bibtex": "TeX", ".md": "Markdown", ".markdown": "Markdown", ".mdown": "Markdown",
    ".mdwn": "Markdown", ".mkd": "Markdown", ".mkdn": "Markdown", ".mkdown": "Markdown", ".ronn": "Markdown",
    ".livemd": "Markdown", ".workbook": "Markdown", ".mdx": "Markdown", ".rst": "Markdown", ".rest": "Markdown",
    ".adoc": "Markdown", ".asciidoc": "Markdown", ".org": "Markdown", ".rmd": "Markdown", ".qmd": "Markdown",
    ".lean": "Lean", ".hlean": "Lean", ".ps1": "PowerShell", ".psm1": "PowerShell", ".psd1": "PowerShell",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ksh": "Shell", ".bats": "Shell", ".command": "Shell",
    ".zsh-theme": "Shell", ".tool": "Shell", ".pacscript": "Shell", ".sbatch": "Shell", ".slurm": "Shell",
    ".fish": "Shell", ".tcsh": "Shell", ".csh": "Shell", ".nu": "Nushell", ".css": "CSS", ".scss": "CSS",
    ".sass": "CSS", ".less": "CSS", ".styl": "CSS", ".pcss": "CSS", ".postcss": "CSS", ".html": "HTML", ".htm": "HTML",
    ".xhtml": "HTML", ".xht": "HTML", ".hta": "HTML", ".erb": "HTML", ".rhtml": "HTML", ".heex": "HTML",
    ".leex": "HTML", ".cshtml": "HTML", ".razor": "HTML", ".phtml": "HTML", ".ecr": "HTML", ".yml": "YAML",
    ".yaml": "YAML", ".sublime-syntax": "YAML", ".toml": "TOML", ".sql": "SQL", ".ddl": "SQL", ".mysql": "SQL",
    ".prc": "SQL", ".udf": "SQL", ".viw": "SQL", ".pgsql": "SQL", ".pls": "SQL", ".plsql": "SQL", ".pck": "SQL",
    ".pkb": "SQL", ".pks": "SQL", ".plb": "SQL", ".bdy": "SQL", ".fnc": "SQL", ".spc": "SQL", ".tpb": "SQL",
    ".tps": "SQL", ".trg": "SQL", ".vw": "SQL", ".db2": "SQL", ".vbs": "VBScript", ".go": "Go", ".c": "C", ".cats": "C",
    ".idc": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".c++": "C++", ".cppm": "C++", ".ixx": "C++",
    ".hpp": "C++", ".hh": "C++", ".hxx": "C++", ".h++": "C++", ".inl": "C++", ".ipp": "C++", ".tcc": "C++",
    ".tpp": "C++", ".txx": "C++", ".ino": "C++", ".java": "Java", ".jav": "Java", ".jsh": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".ktm": "Kotlin", ".swift": "Swift", ".rb": "Ruby", ".builder": "Ruby", ".eye": "Ruby",
    ".gemspec": "Ruby", ".god": "Ruby", ".jbuilder": "Ruby", ".mspec": "Ruby", ".podspec": "Ruby", ".prawn": "Ruby",
    ".rabl": "Ruby", ".rake": "Ruby", ".rbi": "Ruby", ".rbuild": "Ruby", ".rbw": "Ruby", ".rbx": "Ruby", ".ru": "Ruby",
    ".ruby": "Ruby", ".thor": "Ruby", ".watchr": "Ruby", ".lua": "Lua", ".nse": "Lua", ".pd_lua": "Lua", ".rbxs": "Lua",
    ".rockspec": "Lua", ".wlua": "Lua", ".luau": "Luau", ".jl": "Julia", ".wl": "Wolfram", ".wls": "Wolfram",
    ".wlt": "Wolfram", ".mt": "Wolfram", ".mathematica": "Wolfram", ".hs": "Haskell", ".hs-boot": "Haskell", ".hsc": "Haskell", ".lhs": "Haskell", ".ml": "OCaml",
    ".mli": "OCaml", ".mll": "OCaml", ".mly": "OCaml", ".eliom": "OCaml", ".eliomi": "OCaml", ".ml4": "OCaml",
    ".sml": "Standard ML", ".sig": "Standard ML", ".fun": "Standard ML", ".bat": "Batchfile", ".cmd": "Batchfile",
    ".cs": "C#", ".csx": "C#", ".cake": "C#", ".linq": "C#", ".fsi": "F#", ".fsx": "F#", ".vb": "Visual Basic .NET",
    ".vbhtml": "Visual Basic .NET", ".php": "PHP", ".php3": "PHP", ".php4": "PHP", ".php5": "PHP", ".phps": "PHP",
    ".phpt": "PHP", ".aw": "PHP", ".ctp": "PHP", ".hack": "Hack", ".hhi": "Hack", ".blade": "Blade", ".twig": "Twig",
    ".jinja": "Jinja", ".jinja2": "Jinja", ".j2": "Jinja", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".hbs": "Handlebars", ".handlebars": "Handlebars", ".mustache": "Mustache", ".ejs": "EJS", ".ect": "EJS",
    ".jst": "EJS", ".liquid": "Liquid", ".njk": "Nunjucks", ".pug": "Pug", ".jade": "Pug", ".haml": "Haml",
    ".slim": "Slim", ".mako": "Mako", ".mao": "Mako", ".gohtml": "Go Template", ".gotmpl": "Go Template",
    ".xslt": "XSLT", ".xsl": "XSLT", ".dart": "Dart", ".mm": "Objective-C++", ".matlab": "MATLAB", ".scala": "Scala",
    ".sbt": "Scala", ".kojo": "Scala", ".sc": "Scala", ".groovy": "Groovy", ".gvy": "Groovy", ".gtpl": "Groovy",
    ".grt": "Groovy", ".gradle": "Gradle", ".clj": "Clojure", ".cljs": "Clojure", ".cljc": "Clojure",
    ".cljx": "Clojure", ".cljscm": "Clojure", ".cl2": "Clojure", ".hic": "Clojure", ".boot": "Clojure", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".hrl": "Erlang", ".xrl": "Erlang", ".yrl": "Erlang", ".escript": "Erlang",
    ".gleam": "Gleam", ".elm": "Elm", ".purs": "PureScript", ".res": "ReScript", ".resi": "ReScript", ".re": "Reason",
    ".rei": "Reason", ".coffee": "CoffeeScript", "._coffee": "CoffeeScript", ".cjsx": "CoffeeScript",
    ".iced": "CoffeeScript", ".litcoffee": "CoffeeScript", ".rkt": "Racket", ".rktl": "Racket", ".scrbl": "Racket",
    ".scm": "Scheme", ".ss": "Scheme", ".sld": "Scheme", ".sps": "Scheme", ".lisp": "Common Lisp",
    ".asd": "Common Lisp", ".ny": "Common Lisp", ".podsl": "Common Lisp", ".el": "Emacs Lisp", ".emacs": "Emacs Lisp",
    ".fnl": "Fennel", ".janet": "Janet", ".hy": "Hy", ".pm": "Perl", ".perl": "Perl", ".ph": "Perl", ".plx": "Perl",
    ".psgi": "Perl", ".raku": "Raku", ".rakumod": "Raku", ".pm6": "Raku", ".pl6": "Raku", ".p6": "Raku", ".6pl": "Raku",
    ".6pm": "Raku", ".p6l": "Raku", ".p6m": "Raku", ".nqp": "Raku", ".r": "R", ".rsx": "R", ".coq": "Rocq Prover",
    ".thy": "Isabelle", ".agda": "Agda", ".lagda": "Agda", ".idr": "Idris", ".lidr": "Idris", ".fst": "F*",
    ".fsti": "F*", ".dfy": "Dafny", ".tla": "TLA", ".als": "Alloy", ".sage": "Sage", ".gap": "GAP", ".gi": "GAP",
    ".m2": "Macaulay2", ".stan": "Stan", ".do": "Stata", ".ado": "Stata", ".doh": "Stata", ".mata": "Stata",
    ".matah": "Stata", ".ihlp": "Stata", ".sthlp": "Stata", ".sas": "SAS", ".sci": "Scilab", ".sce": "Scilab",
    ".asy": "Asymptote", ".typ": "Typst", ".gnuplot": "Gnuplot", ".gnu": "Gnuplot", ".plot": "Gnuplot", ".zig": "Zig",
    ".nim": "Nim", ".nims": "Nim", ".nimble": "Nim", ".nimrod": "Nim", ".cr": "Crystal", ".odin": "Odin",
    ".mojo": "Mojo", ".carbon": "Carbon", ".vala": "Vala", ".vapi": "Vala", ".hx": "Haxe", ".hxsl": "Haxe",
    ".sol": "Solidity", ".vy": "Vyper", ".move": "Move", ".cairo": "Cairo", ".f": "Fortran", ".f77": "Fortran",
    ".for": "Fortran", ".fpp": "Fortran", ".f90": "Fortran", ".f95": "Fortran", ".f03": "Fortran", ".f08": "Fortran",
    ".adb": "Ada", ".ads": "Ada", ".ada": "Ada", ".cob": "COBOL", ".cbl": "COBOL", ".cobol": "COBOL", ".cpy": "COBOL",
    ".ccp": "COBOL", ".pas": "Pascal", ".dpr": "Pascal", ".lpr": "Pascal", ".pascal": "Pascal", ".asm": "Assembly",
    ".s": "Assembly", ".nasm": "Assembly", ".nas": "Assembly", ".a51": "Assembly", ".x68": "Assembly", ".ll": "LLVM",
    ".mlir": "MLIR", ".wat": "WebAssembly", ".wast": "WebAssembly", ".cu": "Cuda", ".cuh": "Cuda", ".metal": "Metal",
    ".hlsl": "HLSL", ".hlsli": "HLSL", ".fx": "HLSL", ".fxh": "HLSL", ".cginc": "HLSL", ".glsl": "GLSL",
    ".vert": "GLSL", ".frag": "GLSL", ".geom": "GLSL", ".tesc": "GLSL", ".tese": "GLSL", ".fp": "GLSL", ".frg": "GLSL",
    ".fsh": "GLSL", ".fshader": "GLSL", ".glslf": "GLSL", ".glslv": "GLSL", ".gshader": "GLSL", ".rchit": "GLSL",
    ".rmiss": "GLSL", ".vrx": "GLSL", ".vs": "GLSL", ".vsh": "GLSL", ".vshader": "GLSL", ".wgsl": "WGSL",
    ".shader": "ShaderLab", ".veo": "Verilog", ".sv": "SystemVerilog", ".svh": "SystemVerilog", ".vh": "SystemVerilog",
    ".vhd": "VHDL", ".vhdl": "VHDL", ".vhf": "VHDL", ".vhi": "VHDL", ".vho": "VHDL", ".vhs": "VHDL", ".vht": "VHDL",
    ".vhw": "VHDL", ".tcl": "Tcl", ".tm": "Tcl", ".adp": "Tcl", ".sdc": "Tcl", ".xdc": "Tcl", ".awk": "Awk",
    ".gawk": "Awk", ".mawk": "Awk", ".nawk": "Awk", ".auk": "Awk", ".sed": "sed", ".m4": "M4", ".mk": "Makefile",
    ".mak": "Makefile", ".make": "Makefile", ".makefile": "Makefile", ".mkfile": "Makefile", ".cmake": "CMake",
    ".dockerfile": "Dockerfile", ".containerfile": "Dockerfile", ".just": "Just", ".bzl": "Starlark",
    ".star": "Starlark", ".tf": "HCL", ".tfvars": "HCL", ".hcl": "HCL", ".nomad": "HCL", ".tofu": "HCL", ".nix": "Nix",
    ".bicep": "Bicep", ".bicepparam": "Bicep", ".dhall": "Dhall", ".jsonnet": "Jsonnet", ".libsonnet": "Jsonnet",
    ".cue": "CUE", ".pkl": "Pkl", ".nf": "Nextflow", ".proto": "Protocol Buffer", ".graphql": "GraphQL",
    ".gql": "GraphQL", ".graphqls": "GraphQL", ".thrift": "Thrift", ".capnp": "Cap'n Proto", ".g4": "ANTLR",
    ".y": "Yacc", ".yacc": "Yacc", ".lex": "Lex", ".swg": "SWIG", ".swig": "SWIG", ".bbappend": "BitBake",
    ".bbclass": "BitBake", ".pri": "QMake", ".feature": "Gherkin", ".story": "Gherkin", ".nsi": "NSIS", ".nsh": "NSIS",
    ".iss": "Inno Setup", ".isl": "Inno Setup", ".ahk": "AutoHotkey", ".ah1": "AutoHotkey", ".ah2": "AutoHotkey",
    ".ahkl": "AutoHotkey", ".applescript": "AppleScript", ".scpt": "AppleScript", ".pde": "Processing",
    ".prolog": "Prolog", ".yap": "Prolog", ".pwn": "Pawn", ".sma": "Pawn", ".mmd": "Mermaid", ".mermaid": "Mermaid",
    ".vim": "Vim script", ".vimrc": "Vim script", ".vmb": "Vim script", ".jq": "jq", ".apex": "Apex", ".qml": "QML",
    ".qbs": "QML", ".ftlh": "FreeMarker", ".di": "D", ".gdb": "GDB", ".gdbinit": "GDB", ".aspx": "ASP.NET",
    ".ascx": "ASP.NET", ".asax": "ASP.NET", ".ashx": "ASP.NET", ".asmx": "ASP.NET", ".axd": "ASP.NET", ".cocci": "SmPL",
    ".nasl": "NASL", ".pb": "PureBasic", ".pbi": "PureBasic", ".ampl": "AMPL", ".xs": "XS", ".aidl": "AIDL",
    ".fth": "Forth", ".4th": "Forth", ".forth": "Forth", ".frt": "Forth", ".rego": "Open Policy Agent",
    ".robot": "RobotFramework", ".scad": "OpenSCAD", ".smt2": "SMT", ".smt": "SMT",
    ".gd": "GDScript",   # GAP's declaration files too, but Godot's scripts are about four times as common
}
# Two-part suffixes, tried before the extension, so .blade.php is Blade and not PHP.
SUFFIXES = {
    ".blade.php": "Blade", ".html.eex": "HTML", ".html.tmpl": "Go Template", ".gradle.kts": "Gradle",
    ".app.src": "Erlang", ".coffee.md": "CoffeeScript", ".cmake.in": "CMake", ".sh.in": "Shell", ".rs.in": "Rust",
    ".tcl.in": "Tcl", ".zig.zon": "Zig", ".lagda.md": "Agda", ".lagda.tex": "Agda", ".lagda.rst": "Agda",
    ".lagda.org": "Agda", ".lagda.typ": "Agda", ".lagda.tree": "Agda",
}
# Whole file names, lowercase, tried first: files with no extension (Dockerfile, Makefile) and names whose
# extension would mislead or is excluded (CMakeLists.txt).
NAMES = {
    "dockerfile": "Dockerfile", "containerfile": "Dockerfile", "makefile": "Makefile", "gnumakefile": "Makefile",
    "bsdmakefile": "Makefile", "kbuild": "Makefile", "mkfile": "Makefile", "makefile.am": "Makefile",
    "makefile.in": "Makefile", "makefile.inc": "Makefile", "makefile.frag": "Makefile", "makefile.boot": "Makefile",
    "makefile.pc": "Makefile", "makefile.wat": "Makefile", "makefile.sco": "Makefile", "cmakelists.txt": "CMake",
    "meson.build": "Meson", "meson_options.txt": "Meson", "configure.ac": "M4", "build.bazel": "Starlark",
    "module.bazel": "Starlark", "workspace.bazel": "Starlark", "workspace.bzlmod": "Starlark", "buck": "Starlark",
    "tiltfile": "Starlark", "justfile": "Just", ".justfile": "Just", "earthfile": "Earthly", "procfile": "Procfile",
    "jenkinsfile": "Groovy", "gemfile": "Ruby", "rakefile": "Ruby", "podfile": "Ruby", "vagrantfile": "Ruby",
    "brewfile": "Ruby", "capfile": "Ruby", "guardfile": "Ruby", "fastfile": "Ruby", "dangerfile": "Ruby",
    "berksfile": "Ruby", "thorfile": "Ruby", "puppetfile": "Ruby", "jarfile": "Ruby", "mavenfile": "Ruby",
    "buildfile": "Ruby", "deliverfile": "Ruby", "snapfile": "Ruby", "steepfile": "Ruby", "appraisals": "Ruby",
    ".irbrc": "Ruby", ".pryrc": "Ruby", ".simplecov": "Ruby", "sconstruct": "Python", "sconscript": "Python",
    "wscript": "Python", ".gclient": "Python", "snakefile": "Python", "jakefile": "JavaScript",
    "cakefile": "CoffeeScript", "phakefile": "PHP", ".php_cs": "PHP", ".php_cs.dist": "PHP", "makefile.pl": "Perl",
    "cpanfile": "Perl", "rexfile": "Perl", "latexmkrc": "Perl", ".latexmkrc": "Perl", "emakefile": "Erlang",
    "rebar.config": "Erlang", "nextflow.config": "Nextflow", "pipfile": "TOML", ".clang-format": "YAML",
    ".clang-tidy": "YAML", ".clangd": "YAML", ".gemrc": "YAML", "citation.cff": "YAML", "_helpers.tpl": "Go Template",
    ".luacheckrc": "Lua", ".rprofile": "R", "contents.lr": "Markdown", "riemann.config": "Clojure", "nim.cfg": "Nim",
    "lexer.x": "Lex", ".gdbinit": "GDB", ".bashrc": "Shell", ".bash_profile": "Shell", ".bash_aliases": "Shell",
    ".bash_functions": "Shell", ".bash_logout": "Shell", ".profile": "Shell", ".zshrc": "Shell", ".zshenv": "Shell",
    ".zprofile": "Shell", ".zlogin": "Shell", ".zlogout": "Shell", ".kshrc": "Shell", ".cshrc": "Shell",
    ".login": "Shell", ".xinitrc": "Shell", ".xsession": "Shell", ".envrc": "Shell", "pkgbuild": "Shell",
    "bashrc": "Shell", "bash_profile": "Shell", "bash_aliases": "Shell", "bash_logout": "Shell", "zshrc": "Shell",
    "zshenv": "Shell", "zprofile": "Shell", "zlogin": "Shell", "zlogout": "Shell", "kshrc": "Shell", "cshrc": "Shell",
    "xinitrc": "Shell", ".vimrc": "Vim script", "_vimrc": "Vim script", "vimrc": "Vim script", ".gvimrc": "Vim script",
    "gvimrc": "Vim script", ".nvimrc": "Vim script", "nvimrc": "Vim script", ".exrc": "Vim script",
    ".emacs": "Emacs Lisp", "_emacs": "Emacs Lisp", ".spacemacs": "Emacs Lisp", ".gnus": "Emacs Lisp",
    ".viper": "Emacs Lisp", "cask": "Emacs Lisp", "eask": "Emacs Lisp",
}
# Whole file names matched as written, whose lowercase would claim a build script of anyone's (a file named build)
CASED_NAMES = {"BUILD": "Starlark", "WORKSPACE": "Starlark"}   # Bazel's, as Linguist names them
OTHER = "Other"
PROSE = {"Markdown"}  # not a programming language, so it is left out of the stats row's languages count

# The design lives in design/, apart from this code and under its own license (design/LICENSE.md): the
# themes (design/themes.json), the chart's colors (design/palette.json) and the wordmark
# (design/wordmark.svg). design/README.md says how they were made. Without design/ the generator draws in a
# plain look of its own, defined here: one grey theme in a lite and a nite, a few generic colors and no
# wordmark. A design/ that is there but cannot be read is an error, not a card quietly drawn plain.
DESIGN_DIR = os.path.join(HERE, "design")
PLAIN = {
    "order": ["plain"], "variants": {"plain": ["plain", "plain-nite"]},
    "themes": {
        "plain": dict(dark=False, bg="#ffffff", line="#d0d7de", text="#1f2328", muted="#59636e", dim="#8c959f",
                      prose="#afb8c1", other="#d8dee4", spotify="1f2328", grid=".05", mark=".08"),
        "plain-nite": dict(dark=True, bg="#010409", line="#30363d", text="#e6edf3", muted="#9198a1",
                           dim="#6e7681", prose="#c9d1d9", other="#3d444d", spotify="010409", grid=".035",
                           mark=".09"),
    },
    "green": "#2da44e", "red": "#cf222e", "yellow": "#bf8700", "yellow_lite": "#9a6700", "colors": {},
    "shared": {c: [] for c in ("#0969da", "#bf8700", "#8250df", "#1a7f37", "#bc4c00", "#0550ae", "#6639ba",
                               "#57606a")},
}


def load_design(folder=DESIGN_DIR):
    """design/'s themes and palette merged into one dict, or PLAIN when there is no design/ folder."""
    if not os.path.isdir(folder):
        return PLAIN
    design = {}
    for name in ("themes.json", "palette.json"):
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                design.update(json.load(f))
        except (OSError, ValueError):
            raise RuntimeError("the design in design/%s is missing or cannot be read" % name) from None
    return design


DESIGN = load_design()
# Each version of a theme: a lite for a visitor in light mode and a nite for one in dark mode. "spotify" is
# the widget's background when it is shown on its own, which only comes with white text, so a lite takes a
# deep tone of its own ink and a nite its own page; the relay instead recolors the widget to the version.
THEMES = {name: dict(tokens) for name, tokens in DESIGN["themes"].items()}
THEME_ORDER = list(DESIGN["order"])   # the strip's order, and the daily turn's
VARIANTS = {name: tuple(pair) for name, pair in DESIGN["variants"].items()}   # each theme's lite and nite
GREEN = DESIGN["green"]   # the bars that echo the Spotify widget's equalizer
RED = DESIGN["red"]       # the Pareto line, the one bright mark on the chart; and everything written, lit
YELLOW = DESIGN.get("yellow", PLAIN["yellow"])                  # what is still in use, lit, on a nite
YELLOW_LITE = DESIGN.get("yellow_lite", PLAIN["yellow_lite"])   # and on a lite, where the nite's would be too pale
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"   # the widget's stack
MONO = ("'IBM Plex Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', "
        "monospace")
# The chart's language colors, the same in every theme; only prose and Other follow the theme. A language
# listed in "colors" has its own; every other named language shares one of the "shared" colors, and those
# are also the spares a layer moves to when its own color would crowd one ranked above it (assign_colors).
COLORS = dict(DESIGN["colors"])
SHARED = {color: tuple(langs) for color, langs in DESIGN["shared"].items()}
COLORS.update((lang, color) for color, langs in SHARED.items() for lang in langs)
SPARE = list(SHARED)
MIN_APART = 12.0       # CIEDE2000: no two languages drawn together look closer than this
# The names too long to sit beside their share in a legend, wide or compact (at 0.6 em, beside the widest
# share, 100%), go by a shorter name their writers use there; the description for screen readers keeps the
# full name.
LEGEND_NAMES = {"Visual Basic .NET": "vb.net", "Open Policy Agent": "rego", "Protocol Buffer": "protobuf",
                "RobotFramework": "robot", "Objective-C++": "obj-c++", "SystemVerilog": "sysverilog"}
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

# Local days (see "Days" above). places.tsv.gz is built by tools/build_places.py from GeoNames data,
# licensed under Creative Commons Attribution 4.0.
PLACES_FILE = os.path.join(HERE, "places.tsv.gz")
PROFILE_TIMEOUT = 10        # seconds for the whole read of the public profile page
LOCATION_TIMEOUT = 30       # seconds for the query that reads the profile's location
PROFILE_LIMIT = 4 << 20     # a profile page larger than this is not read
LOCATION_LIMIT = 256        # characters of a location that are read
CLEAR_SHARE = 0.75          # a location has a zone only when one zone's rules cover this share of its people
JOINT_SHARE = 0.25          # places named together share a zone whose rules cover this share of each one's people
BIG_TOWN = 500000           # a town this big keeps a same-named region elsewhere from reading as clear ("Washington")
CODE_SHARE = 0.05           # beside a word nothing knows, a country's code that also abbreviates regions is read as
                            # the country if those regions hold less than this share of its people, as the regions if
                            # they hold more than twice its people, and otherwise not at all
# zones alike on every one of these days count days alike: from 2005, before which little history is dated, to two
# years past today, so zones that parted before 2016, as Indianapolis and New York did, stay apart
RULES_DAYS = (dt.date(2005, 1, 1).toordinal(),
              max(dt.date(2028, 1, 1), dt.date.today() + dt.timedelta(days=731)).toordinal())
PART_SPLIT = r"[,;/|()\[\]\n•·]+|\s[-–—]\s"   # how a location's parts are separated
SEGMENT_SPLIT = r"[;/|\n•·]|\s[-–—]\s"   # the separators among those that start another place, as commas and brackets do not
JOINERS = r"\s*(?:&|\+|->|→|↔|\band\b)\s*"   # how one part names two places ("Tokyo & Seoul"), if it is no name itself
# pronouns written as a set ("he/him", "they/them", "it/its"), taken out of a location before it is read
PRONOUNS = (r"(?i)\b(?:he|she|they|it|xe|ze|ey|fae|any)\s*/\s*(?:him|his|her|hers|they|them|their|theirs|it|its|xem|xyr|"
            r"zir|hir|em|faer|all|pronouns)(?:\s*/\s*(?:him|his|her|hers|they|them|their|theirs|it|its|xem|zir|all))*\b")
# letters that plain Unicode folding keeps apart from the letter people type for them ("København", "Łódź")
FOLD_LETTERS = str.maketrans({"ø": "o", "đ": "d", "ð": "d", "æ": "ae", "œ": "oe", "ł": "l", "þ": "th", "ı": "i",
                              "ħ": "h"})
NOT_PLACES = {"asia", "apac", "emea", "north", "south", "east", "west",   # words in profiles that towns share
              "he", "him", "his", "she", "her", "hers", "they", "them", "theirs", "he him", "she her", "they them",
              "he they", "she they", "it its", "any pronouns",
              # ordinary words, and names people write in jest, that are also a region or a town ("Islands",
              # "Spring", "The Valley", "Paradise", "Atlantis")
              "islands", "lakes", "unity", "plateau", "littoral", "maritime", "kara", "savanes", "oriental", "sud",
              "centro", "volta", "the valley", "west bay", "north shore", "south shore", "uptown", "spring", "bay",
              "union", "temple", "liberty", "forest", "university", "airport", "jupiter", "paradise", "atlantis",
              "nan", "troy", "zion", "eden", "crystal", "erlang", "orion", "shangri la", "vulcan",
              # names people write for somewhere other than the only places the table holds under them
              "surrey", "durham", "carolina", "labrador", "franconia", "coromandel", "st johns", "north jersey",
              "south jersey", "central jersey", "canton"}
LONE_WORDS = {"am", "pm", "est", "edt", "cst", "cdt", "mst", "mdt", "pst", "pdt", "akst", "hst", "et", "pt", "gmt", "utc",
              "bst", "cet", "cest", "eet", "eest", "wet", "ist", "jst", "kst", "aest", "aedt", "acst", "awst", "nzst",
              "nzdt", "sgt", "hkt", "pht", "wib", "ict", "msk", "cat", "eat", "wat", "sast", "brt", "art", "myt",
              "pkt", "npt", "gst", "ast", "adt", "nst", "ndt"}   # times of day and time zones, no place when alone
FILLER = {"remote", "remotely", "home", "home office", "anywhere", "everywhere", "worldwide", "earth", "planet earth",
          "global", "online", "internet", "the internet", "wfh", "work from home", "hybrid", "digital nomad", "nomad",
          "open to relocation", "relocation", "localhost"}   # words beside a place that name no place
# words around a place's name that are not part of it ("Greater London", "Based in Nairobi", "Oslo area",
# "Tokyo-to"), dropped only from a part the table does not know as written
LEAD_WORDS = ("based in", "living in", "located in", "currently in", "currently", "now in", "now", "in", "near",
              "the", "el", "al", "greater", "grand", "metro", "metropolitan", "downtown", "central", "inner", "upstate",
              "rural", "north", "south", "east", "west", "northern", "southern", "eastern", "western")
TRAIL_WORDS = ("area", "region", "metro area", "metropolitan area", "metropolitan region", "metro", "metropolitan",
               "county", "province", "prefecture", "district", "municipality", "department", "oblast",
               "governorate", "territory", "and surroundings", "surroundings", "office", "hq", "selatan", "utara",
               "barat", "timur", "pusat", "to", "fu", "ken", "shi", "si", "ku", "gu", "do")
# those that mark a city's surroundings: a name found only by dropping one is not read as a region that holds none
# of its towns ("Greater Washington" is not Washington State)
AREA_WORDS = {"greater", "grand", "metro", "metropolitan", "downtown", "inner", "area", "region", "metro area",
              "metropolitan area", "metropolitan region", "and surroundings", "surroundings"}
TAGS = {"ai", "ml"}         # read as places only when they are the whole location
KEEP_CODES = {"usa", "uae"}  # three letters that do mean a country when written alone, in any case
Place = namedtuple("Place", "id country region people zone")

# The current theme's colors; use_theme() sets them before each panel is drawn.
BG = LINE = TEXT = MUTED = DIM = OTHER_COLOR = ""
AS_OF = None   # the run's own day, written at the bars' right end so a panel that stops refreshing is dated
QUANTITY = None   # the headline's figures: lines of code written in the window, and of them production and tests
                  # still in use (see collect)
THEME = {}
LAYER_COLORS = {}

# The watermark sits behind the chart's column, 120 panel units across (scaled down further if a tall
# or turned outline would not fit), centred here, turned MARK_TURN degrees. The angle is part of the
# panel's design, not a setting.
MARK_WIDTH = 120
MARK_TURN = 10
MARK_CENTRE = (492, 372)
MARK_PX = 2          # raster pixels per panel unit; 2 lines them up exactly with the half-unit grid stroke
MARK_LIMIT = (8, 8, 566, 435)   # the raster stays clear of the panel's rounded corners
MARK_MAX_CHARS = 49152          # what a GitHub secret can hold
MARK_MAX_COORD = 1e6

# The coderprint wordmark: its letters, read from design/wordmark.svg, whose viewBox frames them, drawn in
# the headline's color in the bottom right corner, over the watermark.
WORDMARK_FILE = os.path.join(DESIGN_DIR, "wordmark.svg")
WORDMARK_WIDTH, WORDMARK_RIGHT, WORDMARK_BOTTOM = 118.0, 560.0, 438.0   # ends where the values end

SPOTIFY_URL = ("https://spotify-github-profile.kittinanx.com/api/view?uid={uid}"
               "&cover_image=true&theme=default&show_offline=false&background_color={bg}&interchange=false"
               "&profanity=false&hide_remaster=false")
# rayriffy/apple-music-github-profile's card of the track last played on Apple Music. It takes only a light
# or dark theme and the uid: no background, so beside the panel it keeps its own colors.
APPLE_MUSIC_URL = "https://music-profile.rayriffy.com/theme/{theme}.svg?uid={uid}"
ALT = ("Lines of code written and still in use, commit activity and language mix across the account's own "
       "repositories, not forks")
README_START, README_END = "<!-- coderprint:start -->", "<!-- coderprint:end -->"
# With a relay (CARDS_RELAY), the panel and the music card arrive as one merged image, so neither can
# show up before the other; with neither a relay nor a music card, the panel is shown alone. Either way
# the block holds two pictures, one for each color scheme, each showing the compact card on a screen 540
# CSS px wide or less and the wide one otherwise (Layout, above, says why it takes this shape): first a
# blank source for the other scheme, then the compact card, then the wide one. Every address is absolute:
# GitHub would resolve relative ones as well, and absolute ones also hold where nothing resolves them.
README_TWO = (
    '<a href="{link}#gh-dark-mode-only"><picture>'
    '<source media="(prefers-color-scheme: light)" srcset="{blank}">'
    '<source media="(max-width: 540px)" srcset="{compact_dark}">'
    '<img width="100%" alt="{alt}" src="{wide_dark}">'
    '</picture></a>'
    '<a href="{link}#gh-light-mode-only"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{blank}">'
    '<source media="(max-width: 540px)" srcset="{compact_light}">'
    '<img width="100%" alt="{alt}" src="{wide_light}">'
    '</picture></a>')
# the profile repository's: owner/owner for a person, owner/.github for an organization (profile_repository)
RAW_ASSETS = "https://raw.githubusercontent.com/{owner}/{repo}/HEAD/assets/"
BLANK_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="896" height="1" viewBox="0 0 896 1"/>\n'
# With a music card but no relay, two images side by side. One line with no whitespace between the tags:
# GitHub pads any image with align="right" by 20px, so a float would push the panel below the card, and
# a space between two inline images could wrap them. Inline and gapless, the two always fit, and their
# heights match: 64.1/35.6 = 576/320 beside the Spotify widget (320x445), and 32.0% beside Apple Music's
# card (345x534), since 64.1% x 445/576 x 345/534 = 32.0%.
README_PAIR = (
    '<p align="right">'
    '<a href="{link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{base}assets/panel-dark.svg">'
    '<source media="(prefers-color-scheme: light)" srcset="{base}assets/panel-light.svg">'
    '<img width="64.1%" alt="{alt}" src="{base}assets/panel-dark.svg">'
    '</picture></a>'
    '<a href="{music_link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{music_dark}">'
    '<source media="(prefers-color-scheme: light)" srcset="{music_light}">'
    '<img width="{music_width}" alt="{music_alt}" src="{music_dark}">'
    '</picture></a>'
    '</p>')


def say(msg):
    print(msg, flush=True)


def truthy(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


class OutOfTime(RuntimeError):
    """The run's deadline (see time_limit) left no time to start a command, or cut one short. A repository that
    cannot be read in time is left out and counted, but running out of time is never a reason to count differently:
    what would have told the owner's code from others' is not guessed at."""


class Failed(RuntimeError):
    """A command that exited with an error. output holds what it printed, which for gh is GitHub's answer even when
    that answer carries errors; like the message it is never printed, since it can name a private repository."""

    def __init__(self, message, output=b""):
        RuntimeError.__init__(self, message)
        self.output = output


def time_left(reserve=None):
    """How long a command may still run under the run's deadline (see time_limit): what is left less reserve
    (RESERVE unless given), or None without a deadline. Fails as OutOfTime when that is under five seconds."""
    if DEADLINE is None:
        return None
    left = DEADLINE - time.monotonic() - (RESERVE if reserve is None else reserve)
    if left < 5:
        raise OutOfTime("the run is out of time")
    return int(left)


def run(args, cwd=None, env=None, timeout=TIMEOUT, reserve=None):
    """Run a command. Failures carry only the program's name: argv can hold a clone URL, which would
    name a private repository in a public log, so no exception that carries argv leaves here. Under a
    deadline (see time_limit) a command gets no longer than the run has left, less reserve (RESERVE unless
    given), and one the deadline cuts short fails as OutOfTime. A command that runs past its time is ended with
    everything it started (kill_tree)."""
    what = os.path.basename(args[0])
    try:
        left = time_left(reserve)
    except OutOfTime:
        raise OutOfTime("%s was not started: the run is out of time" % what) from None
    cut = left is not None and (timeout is None or left < timeout)
    if cut:
        timeout = left
    try:
        p = spawn(args, cwd=cwd, env=child_env(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise RuntimeError("%s could not be started" % what) from None
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(p)
        settle(p)
        if cut:
            raise OutOfTime("%s timed out after %d seconds: the run is out of time" % (what, timeout)) from None
        raise RuntimeError("%s timed out after %d seconds" % (what, timeout)) from None
    except BaseException:   # the step's time limit (Stopped) or an interrupt: nothing is left running
        kill_tree(p)
        settle(p)
        raise
    finally:
        release(p)
    if p.returncode != 0:
        raise Failed("%s exited %d" % (what, p.returncode), out)
    return out


# How a command is ended with everything it started. On Windows a killed program's children live on and keep
# its output pipes: git-remote-https under a clone, and the real git under Git for Windows' cmd\git.exe, which
# PowerShell and cmd find first. Reading to the end, or waiting for the pipes as subprocess.run does after a
# timeout, would then outlast any limit. So each command starts suspended inside a job object of its own, joined
# before it runs a single instruction, and ending the job ends every process it holds, even one whose parent has
# already exited. Where a job cannot be made, the command starts as it always did and is ended by its process tree
# (taskkill /T), which finds what its live processes started; and a pipe that something still holds after that is
# waited on for KILL_GRACE seconds at most. Elsewhere a command is killed as subprocess.run kills it.
CREATE_SUSPENDED = 0x00000004
KILL_GRACE = 5
_WIN32 = None


def win32():
    """kernel32's job object calls and ntdll's NtResumeProcess, set up once; False where they cannot be had."""
    global _WIN32
    if _WIN32 is None:
        _WIN32 = False
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                k = ctypes.WinDLL("kernel32", use_last_error=True)
                n = ctypes.WinDLL("ntdll")
                for fn, args, res in ((k.CreateJobObjectW, [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
                                      (k.AssignProcessToJobObject, [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
                                      (k.TerminateJobObject, [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
                                      (k.TerminateProcess, [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
                                      (k.CloseHandle, [wintypes.HANDLE], wintypes.BOOL),
                                      (n.NtResumeProcess, [wintypes.HANDLE], ctypes.c_long)):
                    fn.argtypes, fn.restype = args, res
                _WIN32 = (k, n)
            except Exception:   # no ctypes, or a Windows without these calls: the process tree instead
                _WIN32 = False
    return _WIN32


def spawn(args, **popen):
    """subprocess.Popen, and on Windows inside a job object of its own (see above), kept as the process's
    coderprint_job for kill_tree and release. A command that cannot be resumed after joining is ended before it
    ran and started again the plain way."""
    api = win32() if os.name == "nt" else False
    job = api[0].CreateJobObjectW(None, None) if api else None
    if not job:
        return subprocess.Popen(args, **popen)
    kernel, ntdll = api
    flags = popen.pop("creationflags", 0)
    try:
        proc = subprocess.Popen(args, creationflags=flags | CREATE_SUSPENDED, **popen)
    except BaseException:
        kernel.CloseHandle(job)
        raise
    handle = getattr(proc, "_handle", None)
    if handle is None:   # not a process this module can reach (a stand-in for Popen): nothing to join or resume
        kernel.CloseHandle(job)
        return proc
    handle = int(handle)
    joined = bool(kernel.AssignProcessToJobObject(job, handle))
    if ntdll.NtResumeProcess(handle) != 0:   # still suspended: it has run nothing, so start it again
        kernel.TerminateProcess(handle, 1)
        try:
            proc.wait(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            pass
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            if pipe:
                pipe.close()
        kernel.CloseHandle(job)
        return subprocess.Popen(args, creationflags=flags, **popen)
    if joined:
        proc.coderprint_job = job
    else:
        kernel.CloseHandle(job)
    return proc


def kill_tree(proc):
    """End a command and everything it started: its job object on Windows, or failing that its process tree; and
    the command itself, as subprocess.run does."""
    job = getattr(proc, "coderprint_job", None)
    ended = bool(job and win32() and win32()[0].TerminateJobObject(job, 1))
    if not ended and os.name == "nt" and proc.poll() is None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def settle(proc):
    """After kill_tree: wait for the command, and on Windows for its output pipes, whose reader threads end once
    nothing holds them. A pipe still held after KILL_GRACE seconds is left open for its thread to finish with, since
    closing it would wait as long; elsewhere the pipes are closed, as subprocess.run closes them."""
    if os.name == "nt":
        try:
            proc.communicate(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            return
        except (OSError, ValueError):
            pass
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    for pipe in (proc.stdout, proc.stderr):
        if pipe:
            try:
                pipe.close()
            except OSError:
                pass


def release(proc):
    """Close a command's job object once it is done with (its processes are not ended by that)."""
    job = getattr(proc, "coderprint_job", None)
    if job and win32():
        win32()[0].CloseHandle(job)
        proc.coderprint_job = None


def graphql_args(query, variables):
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for k, v in variables.items():
        args += ["-f", "%s=%s" % (k, v)]
    return args


def graphql_answer(out):
    """gh's output as GitHub's answer, {"data": {...}, "errors": [...]}. An answer whose data is missing or null, as
    GitHub gives when a query fails as a whole, fails here."""
    data = json.loads(out.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        raise RuntimeError("the GitHub API returned no data")
    return data


def gql(query, timeout=TIMEOUT, errors=None, reserve=None, **variables):
    """GitHub's answer to a query, its data. An answer that carries errors fails, as gh exits 1 on it, unless errors
    is a list: the answer is then taken, since gh prints it all the same, and its errors are added to the list. A
    field an error names, such as one the token may not see, is null in the data. Fails when there is no data.
    reserve: the time kept back from the deadline, as run() takes it, RESERVE unless given."""
    args = graphql_args(query, variables)
    more = {} if reserve is None else {"reserve": reserve}
    if errors is None:
        return graphql_answer(run(args, env=github_env(), timeout=timeout, **more))["data"]
    try:
        out = run(args, env=github_env(), timeout=timeout, **more)
    except Failed as e:
        out = e.output
    answer = graphql_answer(out)
    found = answer.get("errors") or []
    errors.extend(found if isinstance(found, list) else [found])
    return answer["data"]


def answered(query, **variables):
    """GitHub's answer to a query as (data, errors), taking an answer that carries errors beside its data (see gql)."""
    errors = []
    return gql(query, errors=errors, **variables), errors


def again(ask):
    """ask(), and once more if it fails, as a repository is read: a lookup that tells the owner's code from others'
    is worth a second try before the run gives up on it. Running out of time is not tried again."""
    try:
        return ask()
    except OutOfTime:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return ask()


# ---------------------------------------------------------------- collect


def owner_login():
    """The account to report on: CARDS_OWNER in Actions, where the token belongs to an App, else gh's user."""
    return os.environ.get("CARDS_OWNER") or gql("query { viewer { login } }")["viewer"]["login"]


ACCESS_OWNER = None   # credentials for the current repository operation; the profile identity never changes
PROFILE_OWNER = None
PUBLIC_ACCESS = False


def organization_settings():
    """Explicit organization scope and optional per-installation tokens; invalid settings never echo their values."""
    organizations = [s.lower() for s in re.split(r"[\s,;]+", os.environ.get("CARDS_ORGANIZATIONS", "").strip()) if s]
    if len(organizations) > 32 or any(not re.fullmatch(r"[A-Za-z0-9-]{1,39}", s) for s in organizations):
        raise RuntimeError("organizations must list at most 32 GitHub organization logins")
    if len(organizations) != len(set(organizations)):
        raise RuntimeError("organizations must list unique GitHub organization logins")
    only = os.environ.get("CARDS_ORGANIZATION_ONLY", "false").strip().lower()
    if only not in ("true", "false") or only == "true" and not organizations:
        raise RuntimeError("organization-only must be true or false, and needs at least one configured organization")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        raw = json.loads(os.environ.get("CARDS_ORGANIZATION_TOKENS", "").strip() or "{}",
                         object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        raise RuntimeError("organization-tokens must be a JSON object of organization installation tokens") from None
    if not isinstance(raw, dict):
        raise RuntimeError("organization-tokens must be a JSON object of organization installation tokens")
    tokens = {}
    for name, token in raw.items():
        if (not isinstance(name, str) or name.lower() not in organizations or name.lower() in tokens
                or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,4096}", token)):
            raise RuntimeError("organization-tokens must map configured organizations to valid tokens")
        tokens[name.lower()] = token
    return organizations, tokens


def repo_owner(owner, repo):
    return repo.get("owner", owner)


def repo_key(owner, repo):
    account = repo_owner(owner, repo)
    return repo["name"] if account.lower() == owner.lower() else account.lower() + "/" + repo["name"]


def active_token():
    organizations, tokens = organization_settings()
    account = (ACCESS_OWNER or "").lower()
    if PUBLIC_ACCESS:
        return None
    if account in organizations:
        if account in tokens:
            return tokens[account]
        if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
            raise RuntimeError("each configured organization needs its own organization-tokens entry")
        return None   # a local gh session may already have explicitly granted organization access
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def child_env(env=None):
    plain = env is None
    env = dict(os.environ if env is None else env)
    # A process reading one repository has no reason to receive the other installations' credentials.
    env.pop("CARDS_ORGANIZATION_TOKENS", None)
    env.pop("CARDS_AUTHORED_IMPORTS", None)
    if plain:
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    return env


def github_env():
    env = child_env()
    token = active_token()
    if token:
        env["GH_TOKEN"] = token
        env.pop("GITHUB_TOKEN", None)
    elif PUBLIC_ACCESS:
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    return env


@contextmanager
def repository_access(owner, public=False):
    global ACCESS_OWNER, PUBLIC_ACCESS
    previous, prior_public, ACCESS_OWNER, PUBLIC_ACCESS = ACCESS_OWNER, PUBLIC_ACCESS, owner, public
    try:
        yield
    finally:
        ACCESS_OWNER = previous
        PUBLIC_ACCESS = prior_public


def authored_imports(owner):
    """Exact upload commits the owner identifies as their existing work; this never overrides authorship."""
    entries = [s for s in re.split(r"[\s,;]+", os.environ.get("CARDS_AUTHORED_IMPORTS", "").strip()) if s]
    allowed = set(organization_settings()[0]) | {owner.lower()}
    result = set()
    if len(entries) > 256:
        raise RuntimeError("authored-imports may list at most 256 repository and commit pairs")
    for entry in entries:
        match = re.fullmatch(r"([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})@([0-9a-fA-F]{40}|[0-9a-fA-F]{64})", entry)
        if not match or match[1].lower() not in allowed or match[2] in (".", ".."):
            raise RuntimeError("authored-imports must list configured owner/repository@full-commit-hash pairs")
        result.add((match[1].lower() + "/" + match[2].lower(), match[3].lower()))
    return result


def list_repositories(owner):
    """Every non-fork repository the account owns, a page of 100 at a time, bar the profile repository, with
    whether it can be read (a disabled or locked repository is counted but never cloned) and whether it is archived
    (its history is read, its head is not in use)."""
    global PROFILE_OWNER
    PROFILE_OWNER = owner
    organizations, _ = organization_settings()
    nodes, cursor = [], None
    while os.environ.get("CARDS_ORGANIZATION_ONLY", "false").strip().lower() != "true":
        page_args = {"owner": owner}
        if cursor:
            page_args["cursor"] = cursor
        data = gql("""
          query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
            repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                         orderBy: {field: CREATED_AT, direction: ASC}) {
              nodes { name isPrivate isDisabled isLocked isArchived } pageInfo { hasNextPage endCursor } } } }""",
                   **page_args)
        if not data.get("repositoryOwner"):
            raise RuntimeError("GitHub has no account named by CARDS_OWNER")
        page = data["repositoryOwner"]["repositories"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    nodes = [r for r in nodes if r["name"].lower() != owner.lower()]
    for organization in organizations:
        cursor, seen, found = None, set(), set()
        with repository_access(organization):
            while True:
                page_args = {"owner": organization}
                if cursor:
                    page_args["cursor"] = cursor
                data = gql("""query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
                    __typename repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                    orderBy: {field: CREATED_AT, direction: ASC}) {
                    nodes { name isPrivate isDisabled isLocked isArchived } pageInfo { hasNextPage endCursor } } } }""",
                    **page_args)
                account = data.get("repositoryOwner")
                if not isinstance(account, dict) or account.get("__typename") != "Organization":
                    raise RuntimeError("a configured organization could not be read")
                page = account["repositories"]
                for repo in page["nodes"]:
                    name = repo.get("name") if isinstance(repo, dict) else None
                    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) or name in (".", ".."):
                        raise RuntimeError("a configured organization returned invalid repository metadata")
                    if name.lower() in found:
                        raise RuntimeError("a configured organization returned duplicate repository metadata")
                    nodes.append(dict(repo, owner=organization))
                    found.add(name.lower())
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]
                if not isinstance(cursor, str) or not cursor or cursor in seen:
                    raise RuntimeError("a configured organization returned invalid pagination")
                seen.add(cursor)
        if not found:
            raise RuntimeError("no repositories are visible in a configured organization; check its read token")
    return nodes


def git_auth(owner, name):
    """How git authenticates. With GH_TOKEN set (Actions), the token rides in an environment-only
    header, never on a command line. Otherwise gh's own credential helper answers."""
    if (ACCESS_OWNER is not None and ACCESS_OWNER.lower() != owner.lower()
            or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) or name in (".", "..")):
        raise RuntimeError("the repository URL does not match its credential scope")
    token = active_token()
    clean = ["-c", "credential.helper=", "-c", "http.extraheader=", "-c", "http.https://github.com/.extraheader="]
    env = github_env()
    count = env.get("GIT_CONFIG_COUNT", "").strip()
    count = int(count) if re.fullmatch(r"[0-9]{1,4}", count) else 0
    settings = [(env.get("GIT_CONFIG_KEY_%d" % k, ""), env.get("GIT_CONFIG_VALUE_%d" % k, "")) for k in range(count)]
    settings = [(key, value) for key, value in settings
                if key and not key.lower().endswith(".extraheader") and key.lower() != "credential.helper"]
    for key in list(env):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) or key == "GIT_CONFIG_PARAMETERS":
            env.pop(key)
    for k, (key, value) in enumerate(settings):
        env["GIT_CONFIG_KEY_%d" % k], env["GIT_CONFIG_VALUE_%d" % k] = key, value
    env["GIT_CONFIG_COUNT"] = str(len(settings))
    if PUBLIC_ACCESS:
        return clean, env
    if not token:
        return clean + ["-c", "credential.helper=!gh auth git-credential"], env
    basic = base64.b64encode(("x-access-token:" + token).encode()).decode()
    # after any settings the environment already passes this way (a self-hosted runner's certificate bundle or
    # proxy), not over them; a count git would refuse anyway is replaced
    n = len(settings)
    path = "%s/%s.git" % (owner, name)
    env.update({"GIT_CONFIG_COUNT": str(n + 1), "GIT_CONFIG_KEY_%d" % n: "http.https://github.com/%s.extraheader" % path,
                "GIT_CONFIG_VALUE_%d" % n: "AUTHORIZATION: basic " + basic, "GIT_TERMINAL_PROMPT": "0"})
    return clean, env


@contextmanager
def clone_directory(dest, env):
    """Isolate an initial clone from the caller checkout's local Git config.

    actions/checkout can include a separate write-token config from its own
    Git directory. An initial `git clone` launched there can send that header
    along with coderprint's read-token header. A fresh child directory and a
    ceiling at its parent keep Git from discovering any ancestor checkout,
    including when CLONE_CACHE itself lives inside one. Global proxy and CA
    configuration still apply.
    """
    absolute = os.path.abspath(dest)
    parent = os.path.realpath(os.path.dirname(absolute))
    with tempfile.TemporaryDirectory(prefix=".coderprint-clone-", dir=parent) as scratch:
        selected = dict(env)
        selected["GIT_CEILING_DIRECTORIES"] = parent
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            selected.pop(name, None)
        yield os.path.realpath(scratch), selected, absolute


def clone(owner, name, dest):
    """Bare clone of every branch and tag. Output is swallowed, because it would name the repository. A cached
    clone (CLONE_CACHE) is pointed at this repository's address before fetching, so a slot can never read another,
    and is brought to what a fresh clone would hold: its branches and tags fetched and those deleted upstream pruned,
    so a tag a force-push left behind brings in nothing, and its HEAD pointed where the repository's own points now,
    so a default branch renamed or switched since is the one read at the head."""
    flags, env = git_auth(owner, name)
    url = "https://github.com/%s/%s.git" % (owner, name)
    if os.path.isdir(dest):
        run(["git", "-C", dest, "remote", "set-url", "origin", url])
        run(["git", "-C", dest] + flags + ["fetch", "--quiet", "--prune", "origin", "+refs/heads/*:refs/heads/*",
                                           "+refs/tags/*:refs/tags/*"], env=env)
        said = run(["git", "-C", dest] + flags + ["ls-remote", "--symref", "origin", "HEAD"], env=env)
        points = re.search(r"(?m)^ref: (refs/heads/[^\t\n]+)\tHEAD$", said.decode("utf-8", "replace"))
        if points:
            run(["git", "-C", dest, "symbolic-ref", "HEAD", points.group(1)])
        return
    with clone_directory(dest, env) as (cwd, selected, absolute):
        run(["git"] + flags + ["clone", "--bare", "--quiet", url, absolute], cwd=cwd, env=selected)


# git reads a clone the same way on every machine. A local run inherits the machine's own git settings, and some of
# them change what a history reads as: log.showRoot=false hides every root commit's files, a global or system
# attributes file can mark code as binary or change its diff, a low core.bigFileThreshold makes big files binary, a
# global mailmap renames authors, and diff.noprefix, diff.mnemonicPrefix, diff.interHunkContext, diff.algorithm,
# diff.renameLimit and diff.submodule change what the diffs look like. Each is pinned to git's own default for every
# command that reads a history (the prefixes are given on the command line as well); the machine's other settings,
# safe.directory among them, still apply.
READ_CONFIG = ["-c", "core.quotepath=off", "-c", "log.showRoot=true", "-c", "log.showSignature=false",
               "-c", "core.attributesFile=" + os.devnull, "-c", "core.bigFileThreshold=512m",
               "-c", "mailmap.file=" + os.devnull, "-c", "i18n.logOutputEncoding=UTF-8",
               "-c", "diff.noprefix=false", "-c", "diff.mnemonicPrefix=false", "-c", "diff.interHunkContext=0",
               "-c", "diff.algorithm=myers", "-c", "diff.renameLimit=1000", "-c", "diff.submodule=short"]


def read_env():
    """The environment a reading git runs in: the system attributes file left out (GIT_ATTR_NOSYSTEM), and the
    variables that would change a diff's shape (GIT_DIFF_OPTS, GIT_EXTERNAL_DIFF) removed."""
    env = dict(child_env(), GIT_ATTR_NOSYSTEM="1")
    for name in ("GIT_DIFF_OPTS", "GIT_EXTERNAL_DIFF"):
        env.pop(name, None)
    return env


GIT_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def git_path(text):
    """A path as git prints it outside -z output, unquoted. Even with core.quotepath off, git puts a path that holds
    a double quote, a backslash or a control character (a tab, a newline) in double quotes, with C escapes and octal
    bytes; every other byte it prints as it is. Undoing that is exact; a quoted name git would not have written is
    kept as it stands."""
    if len(text) < 2 or text[0] != '"' or text[-1] != '"':
        return text
    out, i, s = bytearray(), 0, text[1:-1]
    while i < len(s):
        if s[i] == "\\" and s[i + 1:i + 2] in GIT_ESCAPES:
            out.append(GIT_ESCAPES[s[i + 1]])
            i += 2
        elif s[i] == "\\" and re.fullmatch(r"[0-7]{3}", s[i + 1:i + 4]):
            out.append(int(s[i + 1:i + 4], 8) & 0xFF)
            i += 4
        elif s[i] == "\\":
            return text   # not git's quoting
        else:
            out += s[i].encode("utf-8")
            i += 1
    return out.decode("utf-8", "replace")


def language_of(path):
    """The language a path counts toward, or None when it is excluded. A whole file name (Dockerfile,
    CMakeLists.txt, .bashrc) is tried first, so it wins over an excluded extension; then a two-part suffix
    (.blade.php), then the extension. A file with neither, or an extension no language claims alone, is
    Other. Vendored folders (EXCLUDED_DIRS, ROOT_VENDOR_DIRS, VENDOR_PAIRS) and a build's output (OUTPUT_DIRS) are
    left out."""
    parts = path.replace("\\", "/").split("/")
    folders = [seg.lower() for seg in parts[:-1]]
    output = source = False
    for s in folders:
        if s in EXCLUDED_DIRS or s.endswith(VENDOR_ENDS):
            return None
        if s in OUTPUT_DIRS:
            if not source:   # a build's output folder (see OUTPUT_DIRS)
                return None
            output = True
        source = source or s in SOURCE_DIRS
    if folders and folders[0] in ROOT_VENDOR_DIRS or any(pair in VENDOR_PAIRS for pair in zip(folders, folders[1:])):
        return None
    if parts[-1] in CASED_NAMES:
        return CASED_NAMES[parts[-1]]
    name = parts[-1].lower()
    if name in EXCLUDED_NAMES or name.endswith(EXCLUDED_SUFFIXES) or name.startswith(EXCLUDED_PREFIXES):
        return None
    if name in NAMES:
        return NAMES[name]
    stem, ext = os.path.splitext(name)
    if (name.startswith(("dockerfile.", "containerfile.")) and ext not in LANGUAGES and ext not in EXCLUDED_EXTS
            and ext != ".dockerignore"):
        return "Dockerfile"   # Dockerfile.dev, Dockerfile.prod: one Dockerfile per build, but not its ignore list
    if ext in EXCLUDED_EXTS:
        return None
    lang = SUFFIXES.get(os.path.splitext(stem)[1] + ext) or LANGUAGES.get(ext, OTHER)
    if output and (lang in ("HTML", "CSS", "JavaScript") or name.endswith((".d.ts", ".d.mts", ".d.cts"))):
        return None
    return lang


def automated(name, email, committer, committer_email):
    """Whether a commit is automation's: a [bot] author or committer, a GitHub App's own noreply address
    (BOT_NOREPLY) whatever name it carries, or a name or address automation uses (AUTOMATION_NAMES,
    AUTOMATION_EMAILS). GitHub's own web committer, which marks the owner's edits and merges on github.com, is not
    automation."""
    names = (name.strip().lower(), committer.strip().lower())
    return (any(n.endswith("[bot]") or n in AUTOMATION_NAMES for n in names)
            or any(e in AUTOMATION_EMAILS or BOT_NOREPLY.fullmatch(e)
                   for e in (email.strip().lower(), committer_email.strip().lower())))


def pages_only(repo_dir):
    """The commits only a gh-pages branch that is not the default holds. --exclude keeps the branch itself out of
    --all, but a tag on one of its commits would still bring them in, built bundles and all."""
    if not run(["git", "-C", repo_dir, "for-each-ref", "refs/heads/gh-pages"]).strip():
        return set()
    try:
        if run(["git", "-C", repo_dir, "symbolic-ref", "-q", "HEAD"]).strip() == b"refs/heads/gh-pages":
            return set()   # the default, and read as such
    except RuntimeError as e:
        if "exited" not in str(e):   # a detached HEAD exits 1; running out of time is not that
            raise
    out = run(["git", "-C", repo_dir, "rev-list", "refs/heads/gh-pages", "--not", "--exclude=gh-pages", "--branches"])
    return set(out.decode("ascii", "replace").split())


def read_commits(repo_dir, index, renames=True):
    """Every non-merge commit on every branch but gh-pages (see pages_only), with its author's name and address, its
    subject and each file's new blob and lines added and deleted, children before their parents (--date-order), so
    collect can read the commits of one second parent first. Submodules and symbolic links (LINKS) are left out.
    Records are split on NUL and a record's fields on newlines: git strips newlines from every name and address and a
    subject never holds one, while a name may hold any other control character, 0x1F included. Lines are split on
    newlines alone, never where str.splitlines would also split (U+2028, U+2029, U+0085, 0x1C to 0x1E), which
    core.quotepath=off leaves unquoted in a path; the characters git does quote are unquoted (git_path). Addresses are
    read as committed (%ae, %ce), not as a .mailmap would rewrite them (a bare clone reads HEAD:.mailmap), since
    GitHub, which says whose an address is (see authorship), reads them so; the names are read as committed too. The
    subject is never printed or written."""
    if not run(["git", "-C", repo_dir, "for-each-ref", "--count=1", "refs/heads"]).strip():
        return [], 0  # an empty repository has nothing to read
    pages = pages_only(repo_dir)
    out = run(["git", "-C", repo_dir] + READ_CONFIG + [
               "log", "--exclude=refs/heads/gh-pages", "--all", "--date-order", "--no-merges",
               "-M" if renames else "--no-renames", "--no-abbrev", "--no-textconv", "--no-ext-diff", "--no-color",
               "--raw", "--numstat", "--format=%x00%H%n%at%n%an%n%ae%n%cn%n%ce%n%s"],
              env=read_env()).decode("utf-8", "replace")
    commits, mismatched = [], 0
    for block in out.split("\x00")[1:]:
        parts = block.split("\n", 7)
        body = parts.pop() if len(parts) == 8 else ""
        if (len(parts) != 7 or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", parts[0])
                or not parts[1].isdigit()):
            mismatched += 1
            continue
        sha, ts, author, email, committer, committer_email, subject = parts
        if sha in pages:
            continue
        raw, num, broken = [], [], False
        for line in body.split("\n"):
            if line.startswith(":"):
                meta, _, paths = line.partition("\t")
                fields = meta.split()
                if len(fields) < 5 or not fields[4]:
                    broken = True
                    break
                raw.append((fields[3], fields[4][0], git_path(paths.split("\t")[-1]), fields[1]))
            elif line.count("\t") >= 2:
                a, d, _ = line.split("\t", 2)
                num.append((None, None) if a == "-" else (int(a), int(d)))
        if broken or len(raw) != len(num):
            mismatched += 1
            continue
        files = [Change(blob, status, path, added, deleted)
                 for (blob, status, path, mode), (added, deleted) in zip(raw, num) if mode not in LINKS]
        commits.append(Commit(int(ts), index, sha, automated(author, email, committer, committer_email),
                              email.strip().lower(), author.strip(), subject, files))
    return commits, mismatched


def balanced_files(counted):
    """A commit's modified counted files that add about what they delete (see SWEEP_FILES), and all it modified."""
    changed = [f for f in counted if f.status in ("M", "R") and f.added]
    return [f for f in changed if abs(f.added - f.deleted) <= max(1, SWEEP_BALANCE * max(f.added, f.deleted))], changed


def sweep(counted, alike=None, sha=None):
    """The files of a commit that only reformat (see SWEEP_FILES): when at least SWEEP_FILES of its modified counted
    files add about what they delete and nearly all are like that, those of them that delete a line (one that only
    gains a line was written to, not reformatted) and, where alike holds the commit's changes (read_added_code's
    ALIKE, by (commit, blob)), whose changed lines still read alike (SWEEP_ALIKE): a rewrite that happens to add what
    it deletes is written again. A file whose changes could not be paired stays swept, as the shape alone says.
    Otherwise none. First writes are never touched, so a sweep cannot hide new files."""
    balanced, changed = balanced_files(counted)
    if len(balanced) >= SWEEP_FILES and len(balanced) >= SWEEP_SHARE * len(changed):
        swept = {f for f in balanced if f.deleted}
        if alike is not None:
            swept = {f for f in swept if alike.get((sha, f.blob), SWEEP_ALIKE) >= SWEEP_ALIKE}
        return swept
    return set()


def could_sweep(files):
    """Whether any part of a commit's files could make a sweep (see sweep): at least SWEEP_FILES of them balanced.
    collect has read_added_code pair the changed lines of these commits only (SWEEP_WATCH)."""
    return len(balanced_files(files)[0]) >= SWEEP_FILES


def alike(a, b):
    """Whether two lines of code, spacing collapsed, read nearly alike (ALIKE_RATIO), as a re-indented, re-ended or
    renamed line does and a rewritten one does not."""
    if a == b:
        return True
    m = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return m.real_quick_ratio() >= ALIKE_RATIO and m.quick_ratio() >= ALIKE_RATIO and m.ratio() >= ALIKE_RATIO


def alike_share(hunks):
    """The share of a file's changed lines of code that still read alike: hunks is [(removed lines, added lines)], each
    line's text with its spacing collapsed. A line removed in one place and added unchanged in another (sorted
    imports) is alike wherever it went; the rest are paired in order within each hunk. None when nothing pairs."""
    same = Counter(t for removed, _ in hunks for t in removed) & Counter(t for _, added in hunks for t in added)
    pairs = matched = sum(same.values())
    left = (same.copy(), same.copy())

    def rest(lines, budget):   # the lines not already matched unchanged elsewhere in the file
        kept = []
        for t in lines:
            if budget[t] > 0:
                budget[t] -= 1
            else:
                kept.append(t)
        return kept

    for removed, added in hunks:
        for a, b in zip(rest(removed, left[0]), rest(added, left[1])):
            pairs += 1
            matched += alike(a, b)
    return matched / float(pairs) if pairs else None


def ignored_revs(repo_dir):
    """The commits a repository names in .git-blame-ignore-revs on its default branch: sweeps its owner
    marked as reformatting, not writing. They still count as commits, but add no lines. git reads a hash in either
    case, and so does this."""
    try:
        text = run(["git", "-C", repo_dir, "show", "HEAD:.git-blame-ignore-revs"], timeout=60)
    except OutOfTime:
        raise   # not known to list nothing: the repository is left out and counted instead (see read_repository)
    except RuntimeError:
        return set()
    listed = re.findall(r"(?mi)^[ \t]*([0-9a-f]{64}|[0-9a-f]{40})\b", text.decode("utf-8", "replace"))
    return {h.lower() for h in listed}


def read_repository(owner, name, dest, index):
    """Clone and read one repository, trying each once more on failure, the second time without rename
    detection if the first timed out (moving many paths at once slows it down past any limit); a move that retry
    reads as files deleted and added is still a move, not an import (see moved_files). Returns its commits, how
    many could not be parsed, and the commits it marks as sweeps."""
    renames = True
    for attempt in (1, 2):
        try:
            clone(owner, name, dest)
            commits, bad = read_commits(dest, index, renames)
            return commits, bad, ignored_revs(dest)
        except RuntimeError as e:
            if attempt == 2 or isinstance(e, OutOfTime) or "out of time" in str(e):
                raise
            renames = renames and "timed out" not in str(e)
            if os.path.isdir(dest):   # a clone that failed part way is started again, not fetched into
                remove_tree(dest)


def seed_blobs(full_name, dest):
    """Every file version in the whole history of a repository someone else wrote (a template, or coderprint
    itself in a relay copy), read from a clone without file contents: git lists a file version it does not
    hold with a leading "?". None if it cannot be read, even on a second try; collect then leaves out the
    repositories whose files it would have told apart."""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", full_name):
        return None
    def read():
        try:
            account, name = full_name.split("/", 1)
            public = account.lower() not in organization_settings()[0] and account.lower() != (PROFILE_OWNER or "").lower()
            with repository_access(account, public=public):
                flags, env = git_auth(account, name)
                with clone_directory(dest, env) as (cwd, selected, absolute):
                    run(["git"] + flags + ["clone", "--bare", "--quiet", "--filter=blob:none",
                                           "https://github.com/%s.git" % full_name, absolute],
                        cwd=cwd, env=selected, timeout=300)
            return run(["git", "-C", dest, "rev-list", "--objects", "--all", "--missing=print"], timeout=300)
        finally:
            if os.path.isdir(dest):
                remove_tree(dest)
    try:
        out = again(read)
    except RuntimeError:
        return None
    return {line[1:].strip() for line in out.decode("ascii", "replace").splitlines() if line.startswith("?")}


def templates(owner, profile_owner=None):
    """The template each repository was made from, when that is another account's: {name: owner/name}, or {name:
    None} for a repository whose template GitHub answers with an error for, as it may for a template the token
    cannot see. Asked apart from the listing, so such a template never fails the listing, and each page is asked
    twice before giving up. None when GitHub cannot be asked, or answers with an error that names no repository:
    the files of the templates it would have named would then count as written (see collect)."""
    found, cursor = {}, None
    query = """
      query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
          nodes { name templateRepository { nameWithOwner } } pageInfo { hasNextPage endCursor } } } }"""
    try:
        while True:
            page_args = {"owner": owner}
            if cursor:
                page_args["cursor"] = cursor
            data, errors = again(lambda: answered(query, **page_args))
            page = data["repositoryOwner"]["repositories"]
            unseen = set()   # the places on this page of the repositories an error names
            for e in errors:
                path = e.get("path") if isinstance(e, dict) else None
                if not (isinstance(path, list) and path[:3] == ["repositoryOwner", "repositories", "nodes"]
                        and len(path) > 3 and isinstance(path[3], int)):
                    return None
                unseen.add(path[3])
            for k, node in enumerate(page["nodes"]):
                if not isinstance(node, dict) or not isinstance(node.get("name"), str):
                    return None
                made = (node.get("templateRepository") or {}).get("nameWithOwner") or ""
                if made and made.split("/")[0].lower() != (profile_owner or owner).lower():
                    found[node["name"]] = made
                elif k in unseen and not made:
                    found[node["name"]] = None
            if not page["pageInfo"]["hasNextPage"]:
                return found
            cursor = page["pageInfo"]["endCursor"]
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None


def owner_identity(owner):
    """Whether the account is a person, and a person's account id and profile name, for telling their commits
    from other people's. None when it cannot be read, even on a second try."""
    def ask():
        found = gql("query($owner: String!) { repositoryOwner(login: $owner) { __typename "
                    "... on User { databaseId name } } }", owner=owner)["repositoryOwner"]
        return {"user": found["__typename"] == "User", "id": found.get("databaseId"), "name": found.get("name") or ""}
    try:
        return again(ask)
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None


def resolve_authors(owner, samples):
    """Whose GitHub account each email address is, asked through one commit that uses it: samples maps an
    address to (repository name, commit hash), in the order to ask them. Returns {address: login, or None when the
    address belongs to no account}. Addresses past RESOLVE_CALLS queries of ALIASES are left out, and so is one
    GitHub answers with an error or with nothing for, as for a repository deleted since it was read. Each query is
    asked twice before giving up. Raises RuntimeError if GitHub cannot be asked, or answers with an error that names
    no address, so the caller never guesses (see collect)."""
    global PROFILE_OWNER
    PROFILE_OWNER = owner
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
        raise RuntimeError("the account's login cannot be looked up")
    found, groups = {}, {}
    for email, sample in samples.items():
        if not isinstance(sample, (list, tuple)) or len(sample) != 2 or not all(isinstance(s, str) for s in sample):
            continue
        name, sha = sample
        account, name = name.split("/", 1) if "/" in name else (owner, name)
        if (re.fullmatch(r"[A-Za-z0-9-]{1,39}", account)
                and re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) and name not in (".", "..")
                and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha)):
            groups.setdefault(account.lower(), []).append((email, (name, sha)))
    batches = [(account, items[k:k + ALIASES]) for account, items in groups.items()
               for k in range(0, min(len(items), RESOLVE_CALLS * ALIASES), ALIASES)][:RESOLVE_CALLS]
    for account, batch in batches:
        by_repo = {}
        for j, (_, (name, sha)) in enumerate(batch):
            by_repo.setdefault(name, []).append((j, sha))
        query = " ".join('r%d: repository(owner: "%s", name: "%s") { %s }' % (
            r, account, name, " ".join('c%d: object(oid: "%s") { ... on Commit { author { user { login } } } }' % pair
                                       for pair in shas))
            for r, (name, shas) in enumerate(by_repo.items()))
        with repository_access(account):
            data, errors = again(lambda: answered("query { %s }" % query))
        failed = set()   # what an error names: ("r1",) for a whole repository, ("r1", "c3") for one commit
        for e in errors:
            path = e.get("path") if isinstance(e, dict) else None
            if not isinstance(path, list) or not path or not re.fullmatch(r"r\d+", str(path[0])):
                raise RuntimeError("the GitHub API answered with an error")
            failed.add(tuple(str(p) for p in path[:2]))
        for r, (name, shas) in enumerate(by_repo.items()):
            repo = data.get("r%d" % r)
            for j, _ in shas:
                node = repo.get("c%d" % j) if isinstance(repo, dict) else None
                if (("r%d" % r,) in failed or ("r%d" % r, "c%d" % j) in failed or not isinstance(node, dict)
                        or not isinstance(node.get("author"), dict)):
                    continue   # not answered: the address stays unknown
                user = node["author"].get("user")
                found[batch[j][0]] = user.get("login") if isinstance(user, dict) else None
    return found


def author_emails():
    """The addresses CARDS_AUTHOR_EMAILS lists, however the list is written: separated by commas, semicolons, spaces
    or new lines (as a YAML block or folded list gives them), each bare or as git prints it, Name <address>. An entry
    without an @ is no address, and is left out."""
    return {e.strip("<>\"'()[]").lower() for e in re.split(r"[\s,;]+", os.environ.get("CARDS_AUTHOR_EMAILS", ""))
            if "@" in e}


def agent_name(name):
    """Whether a commit's name is a bot's or a coding agent's own (AGENT_NAME)."""
    return bool(AGENT_NAME.search(name.strip().casefold()))


def authorship(owner, commits, identity, repos, notes=None):
    """The addresses whose commits are the owner's, as (repository, address). The owner's noreply addresses are
    theirs, a noreply address of the id+login form is theirs by their account id whatever login it was made under
    and otherwise another account's, and every other address is looked up on GitHub, with no lookup needed for a
    noreply address of either form. One that belongs to another account is someone else's; so is one listed in
    CARDS_AUTHOR_EMAILS that does, and every other listed address is the owner's. One that belongs to none is the
    owner's under a name the owner's own commits, login or profile use (a name a machine or a tutorial gives, as
    GENERIC_NAMES, or a bot's or an agent's, tells no one), and otherwise in a repository with no other human address
    (a solo repository is its owner's, whatever laptop it was committed from), unless its name is a bot's or a
    coding agent's own (AGENT_NAME); the owner's own linked addresses count as other addresses there. One GitHub was
    not asked about, past the lookup's limit or unanswered, counts only under such a name.

    In another account's organization repositories, the name and solo-repository fallbacks are disabled:
    only a linked owner address, owner noreply identity or explicitly listed non-conflicting address counts.

    The lookup asks first the addresses listed in CARDS_AUTHOR_EMAILS, then those found in more of the account's
    repositories (the owner's own recur; a mirrored project's thousand authors each sit in one), those under a
    name the owner uses, those alone in a repository, and then the most used, so the ones whose answer is likeliest
    to change what counts are asked within its limit. Returns None, so every commit counts, for an organization,
    whose members' work is all its own, or when GitHub cannot be asked (see collect). notes, when given, gets
    "agents": the (repository, address) pairs left out as a bot's or an agent's, "refused": how many listed
    addresses belong to another account, and "unknown": the addresses GitHub was not asked about."""
    if not identity or not identity["user"]:
        return None
    mine = {"%s@users.noreply.github.com" % owner.lower()}
    if identity["id"]:
        mine.add("%d+%s@users.noreply.github.com" % (identity["id"], owner.lower()))
    human = [c for c in commits if not c.bot]
    # a noreply address of the id+login form names its account by an id no change of login alters, so it needs no
    # lookup; one of the older login-only form is looked up like any address, since the owner's own from before a
    # change of login no longer resolves, and then counts by the rules below
    noreply = {}
    for e in {c.email for c in human}:
        m = NOREPLY.fullmatch(e)
        if m and identity["id"]:
            noreply[e] = int(m.group(1)) == identity["id"]
    mine |= {e for e, own in noreply.items() if own}
    listed = author_emails()
    uses, where, called, per_repo, samples = Counter(), {}, {}, {}, {}
    for c in human:
        uses[c.email] += 1
        where.setdefault(c.email, set()).add(c.repo)
        called.setdefault(c.email, set()).add(c.name.casefold())
        per_repo.setdefault(c.repo, set()).add(c.email)
        # Prefer an organization sample so a shared address cannot inherit a personal repository's fallback.
        if c.email not in samples or repo_owner(owner, repos[c.repo]).lower() != owner.lower():
            samples[c.email] = (repo_key(owner, repos[c.repo]), c.sha)

    def own_names():   # the names the owner's own commits, login and profile use, that tell a person
        found = {n for n in (c.name.casefold() for c in human if c.email in mine)
                 if n not in GENERIC_NAMES and not agent_name(n)}
        return (found | {owner.casefold(), identity["name"].casefold()}) - {""}
    alone = {next(iter(emails)) for emails in per_repo.values() if len(emails) == 1}
    known = own_names()
    rank = lambda e: (e not in listed, -len(where[e]), not called[e] & known, e not in alone, -uses[e], e)
    asked = {e: samples[e] for e in sorted(uses, key=rank) if e not in mine and e not in noreply}
    try:
        login = resolve_authors(owner, asked)
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None
    for email, who in login.items():
        if who and who.lower() == owner.lower():
            mine.add(email)
    theirs = ({e for e, who in login.items() if who and who.lower() != owner.lower()}
              | {e for e, own in noreply.items() if not own})
    mine |= listed - theirs
    unknown = set(asked) - set(login) - mine
    names = own_names()
    owned, agents = set(), set()
    for c in human:
        pair = (c.repo, c.email)
        organization = repo_owner(owner, repos[c.repo]).lower() != owner.lower()
        if c.email in mine or (not organization and c.email not in theirs and c.name.casefold() in names):
            owned.add(pair)
        elif c.email in theirs or c.email in unknown:
            continue
        elif agent_name(c.name):
            agents.add(pair)
        elif not organization and len(per_repo[c.repo]) == 1:
            owned.add(pair)
    if notes is not None:
        notes.update(agents=agents, refused=len(listed & theirs & set(uses)), unknown=unknown)
    return owned


def slot(work, owner, name):
    """A cache folder named by a hash of the repository, so it is stable and writes no name to disk."""
    return os.path.join(work, hashlib.sha256((owner + "/" + name).lower().encode()).hexdigest()[:16] + ".git")


# ---------------------------------------------------------------- lines of code

# A line of code is a line of a file in a programming or markup language that is neither blank nor a comment.
# Prose (Markdown, TeX), data (YAML, TOML) and files no language claims are never code.
NOT_CODE = {"Markdown", "TeX", "YAML", "TOML", OTHER}
BLANK, COMMENT, CODE = 0, 1, 2   # how a line reads, one byte a line
KINDS = ("blank", "comment", "code")
UNREAD = "unread"   # the state at a boundary no reading can start from: inside a Python statement (see PythonReader)
# A block comment: its opening as a regular expression; its closing, a plain string that may name the opening's
# group as {0} (Lua's --[==[ closes at ]==]), or a regular expression for the modes that need one; whether it nests;
# where it closes (mode: any, anywhere after its opening; re, at the first match of a regular expression; col0, at
# a line starting with its closing, as Ruby's =end, and then it opens only in column 1 too; alone, on a line holding
# nothing else, as MATLAB's %}, and it opens only alone as well); and whether the rest of the closing line is
# comment too (Ruby's =end, Perl's =cut).
Block = namedtuple("Block", "open close nests mode rest")
# A literal, whose inside is never a comment and whose lines are code: esc ends at its closing unless its escape
# comes before it, dbl at a closing not doubled (Pascal's 'it''s'), both at a closing neither doubled nor escaped
# (SQL's), raw at its closing whatever comes before it (or at a regular expression's match, with esc "re"); esc1,
# dbl1, both1 and raw1 end with their line as well, unless an escape carries one on (C's backslash before a
# newline), and the others run on across lines. A skip is code read in one piece (a character literal); eol runs
# to the end of its line (Zig's \\ lines); here is a heredoc, whose body starts on the next line and ends at a line
# starting with its name (PHP's <<<EOT), which the opening's group holds.
Literal = namedtuple("Literal", "kind open close esc")
E = re.escape   # a plain string as a regular expression


def lit(kind, opening, closing="", esc="\\"):
    return Literal(kind, opening, closing, esc)


def blk(opening, closing, nests=False, mode="any", rest=False):
    """A block comment whose opening is a plain string (see Block)."""
    return Block(E(opening), closing, nests, mode, rest)


class Syntax:
    """How one language writes comments and literals, as its line reader (Lines) reads them: line comments that may
    follow code (line, regular expressions), comments only at a line's start (start), block comments that may follow
    code (blocks) or open only at a line's start (start_blocks), the literals whose insides are never comments
    (literals), lines that start like a comment but are code (code_first: PHP's #[ attributes, the C preprocessor in
    assembly), and characters that make a line a comment in a given column (column: fixed-form Fortran's C in column
    1, COBOL's * in column 7). A tracked language is read whole, literal by literal, so a block comment opened after
    code is seen (int x; /* ...) and a literal's lines are code whatever they hold. An untracked one, whose literals
    cannot be told apart line by line with certainty (Perl's and Ruby's heredocs and regular expressions, MATLAB's
    transpose, a shell's quoting), is read only at the start of each line and after a comment that closes on it:
    the conservative approximation, which counts as code a comment it cannot see there."""

    def __init__(self, line=(), start=(), blocks=(), start_blocks=(), literals=(), code_first=(), column=(),
                 tracked=True, exits=None):
        self.tracked, self.column = tracked, column
        self.blocks = list(start_blocks) + list(blocks)
        self.start_count = len(start_blocks)
        self.literals = list(literals) if tracked else []
        parts = ["(?P<B%d>%s)" % (k, b.open) for k, b in enumerate(self.blocks) if k >= self.start_count]
        parts += ["(?P<S%d>%s)" % (k, f.open) for k, f in enumerate(self.literals)]
        if exits:
            parts.append("(?P<X>%s)" % exits)
        if line:
            parts.append("(?P<L>%s)" % "|".join(line))
        self.code_re = re.compile("|".join(parts)) if parts else None
        self.exit_re = re.compile(exits) if exits else None
        self.start_re = re.compile("(?i)(?:%s)" % "|".join(start)) if start else None
        self.first_re = re.compile("(?:%s)" % "|".join(code_first)) if code_first else None
        self.open_res = [re.compile(b.open) for b in self.blocks]
        self.close_res = [re.compile(b.close) if b.mode != "any" else None for b in self.blocks]
        self.inside_res = {}


def closing(form, group):
    """A block's or literal's closing, filled in from its opening's group (Lua's ]==], C++'s )delim")."""
    return form.close.replace("{0}", group or "") if "{0}" in form.close else form.close


def inner(m):
    """The first group inside the alternative the master pattern matched (see Syntax), or None."""
    k = m.lastindex
    if k is None or k + 1 > m.re.groups or m.start(k + 1) < 0 or m.start(k + 1) > m.end(k):
        return None
    return m.group(k + 1)


def never(k, state):
    return False


class LineReader:
    """A reader that reads a file line by line, each line's reading depending only on the line and the state the
    line before it left: None in plain code, or a tuple naming what is open. Every boundary between two lines can
    start a reading, so two readings of a file agree on every line after a boundary where their states agree.
    initial is the state at a file's start; middle the one assumed where a reading must start part way through a
    file with nothing known of what is open there (see LineKinds)."""
    initial = middle = None
    exact = True
    fallback = None

    def read(self, line, state):
        raise NotImplementedError

    def session(self, get, n, eol, b, state, stop):
        """Reads lines b, b + 1 and on (get(i) gives line i as text) from state, until stop(k, state) says so at a
        boundary k: (kinds of lines b to k - 1, states at boundaries b + 1 to k, k)."""
        kinds, states, read = [], [], self.read
        k = b
        while k < n:
            kind, state = read(get(k), state)
            kinds.append(kind)
            states.append(state)
            k += 1
            if stop(k, state):
                break
        return kinds, states, k


class Lines(LineReader):
    """The line reader for a language's Syntax."""

    def __init__(self, syntax):
        self.syntax = syntax

    def read(self, line, state, bare=None):
        """How line reads, given the state the line before left: (kind, the state it leaves). bare, a list, gets the
        line's code with its literals and comments taken out."""
        s = line[1:] if line[:1] == "\ufeff" else line   # a byte order mark before a file's first line
        if not s.strip():
            return BLANK, state
        code, pos = False, 0
        if state is None:
            start = self.start(s, bare)
            if start is None:
                return COMMENT, None
            code, state, pos = start
        code, state, _ = self.scan(s, pos, state, code, bare)
        return (CODE if code else COMMENT), state

    def start(self, s, bare=None):
        """The start of a line in plain code: None when that alone makes it a comment, else (whether it read code,
        the state, where to read on)."""
        syn, n = self.syntax, len(s)
        for col, chars in syn.column:
            if len(s) > col and s[col] in chars:
                return None
        pos = n - len(s.lstrip())
        m = syn.first_re.match(s, pos) if syn.first_re else None
        if m:
            if bare is not None:
                bare.append(m.group())
            return True, None, m.end()
        for k in range(syn.start_count):
            b = syn.blocks[k]
            m = syn.open_res[k].match(s, pos)
            if m and (b.mode != "col0" or pos == 0) and (b.mode != "alone" or not s[m.end():].strip()):
                return False, ("b", k, 1, closing(b, m.group(1) if m.re.groups else None), False), m.end()
        if syn.start_re and syn.start_re.match(s, pos) and not (syn.code_re and syn.code_re.match(s, pos)):
            return None
        return False, None, pos

    def scan(self, s, pos, state, code, bare):
        """Reads s from pos on in state: (whether it held code, the state at its end, where the reading stopped, which
        is the end unless an exit stopped it, as PHP's ?> does)."""
        syn, n = self.syntax, len(s)
        while True:
            if state is None:
                if pos >= n or not syn.code_re:
                    if s[pos:].strip():
                        code = True
                        if bare is not None:
                            bare.append(s[pos:])
                    return code, None, n
                if syn.tracked:
                    m = syn.code_re.search(s, pos)
                elif code:   # untracked: nothing after code is read
                    return code, None, n
                else:
                    m = syn.code_re.match(s, n - len(s[pos:].lstrip()))
                end = m.start() if m else n
                if s[pos:end].strip():
                    code = True
                    if bare is not None:
                        bare.append(s[pos:end])
                if not m:
                    return code, None, n
                group = m.lastgroup
                if group == "L":
                    if syn.exit_re:   # PHP: a line comment ends where PHP does
                        x = syn.exit_re.search(s, m.end())
                        if x:
                            return code, None, x.start()
                    return code, None, n
                if group == "X":
                    return code, None, m.start()
                k = int(group[1:])
                if group[0] == "B":
                    state, pos = ("b", k, 1, closing(syn.blocks[k], inner(m)), False), m.end()
                    continue
                f = syn.literals[k]
                code = True
                if bare is not None:
                    bare.append(" ")
                if f.kind == "skip":
                    pos = m.end()
                elif f.kind == "eol":
                    return code, None, n
                elif f.kind == "here":
                    return code, ("h", inner(m) or ""), n
                else:
                    state, pos = ("s", k, closing(f, inner(m))), m.end()
            elif state[0] == "b":
                end = self.inside(s, pos, state)
                if isinstance(end, tuple):
                    return code, end, n
                rest = syn.blocks[state[1]].rest
                state, pos = None, end
                if rest:
                    return code, None, n
            elif state[0] == "s":
                f = syn.literals[state[1]]
                end = self.literal_end(s, pos, f, state[2])
                if end < 0:
                    if s[pos:].strip():
                        code = True
                    if f.kind[-1] == "1":
                        # a literal of one line ends with it, unless an escape carries it on (C's backslash)
                        tail = s.rstrip("\r")
                        run = len(tail) - len(tail.rstrip(f.esc)) if f.kind in ("esc1", "both1") and f.esc else 0
                        state = state if run % 2 else None
                    return code, state, n
                code, state, pos = True, None, end
            else:   # ("h", name): a heredoc's body, which a line starting with its name ends
                t = s.lstrip()
                name, code = state[1], True
                after = t[len(name):len(name) + 1]
                if name and t.startswith(name) and not (after.isalnum() or after == "_"):
                    state, pos = None, n - len(t) + len(name)
                    continue
                return code, state, n

    def inside(self, s, pos, state):
        """Where the block comment state names ends in s, searching from pos and counting the comments nested inside
        it where they nest: the position after its closing, or the state still open at the line's end."""
        syn = self.syntax
        _, k, depth, closer, jsx = state
        b = syn.blocks[k]
        if b.mode in ("col0", "alone") and pos:
            return state   # these close only on a line of their own, not on the line that opens them
        if b.mode == "col0":
            m = syn.close_res[k].match(s)
            return m.end() if m else state
        if b.mode == "alone":
            t = s.strip()
            if syn.close_res[k].fullmatch(t):
                return len(s) if depth == 1 else ("b", k, depth - 1, closer, jsx)
            if b.nests and syn.open_res[k].fullmatch(t):
                return ("b", k, depth + 1, closer, jsx)
            return state
        if b.mode == "re":
            m = syn.close_res[k].search(s, pos)
            return m.end() if m else state
        opener = syn.open_res[k] if b.nests else None
        while True:
            c = s.find(closer, pos)
            o = opener.search(s, pos) if opener else None
            if o and (c < 0 or o.start() < c):
                depth, pos = depth + 1, o.end()
            elif c < 0:
                return ("b", k, depth, closer, jsx)
            else:
                depth, pos = depth - 1, c + len(closer)
                if not depth:
                    if jsx:   # JSX's {/* ... */}: the brace closing the comment's braces is not code
                        rest = s[pos:].lstrip()
                        if rest.startswith("}"):
                            pos = len(s) - len(rest) + 1
                    return pos

    def literal_end(self, s, pos, f, closer):
        """Where a literal of form f, closing at closer, ends in s, searching from pos: the position after it, or -1."""
        if f.kind in ("raw", "raw1"):
            if f.esc == "re":
                m = re.compile(closer).search(s, pos)
                return m.end() if m else -1
            k = s.find(closer, pos)
            return k + len(closer) if k >= 0 else -1
        key = (f.kind, closer, f.esc)
        pattern = self.syntax.inside_res.get(key)
        if pattern is None:
            doubled = E(closer) * 2 + "|" if f.kind in ("dbl", "dbl1", "both", "both1") else ""
            escaped = E(f.esc) + r"[\s\S]|" if f.kind in ("esc", "esc1", "both", "both1") and f.esc else ""
            pattern = self.syntax.inside_res[key] = re.compile(escaped + doubled + E(closer))
        for m in pattern.finditer(s, pos):
            if m.group() == closer:
                return m.end()
        return -1


JS_REGEX = re.compile(r"/(?![*/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\[\n])+/[A-Za-z]*")
JS_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "yield", "await",
            "instanceof", "export", "default"}
JS_CODE = re.compile(r"(?P<J>\{(?=/\*))|(?P<B>/\*)|(?P<L>//)|(?P<Q>['\"])|(?P<T>`)|(?P<R>/)|(?P<O>\{)|(?P<C>\})")
JS_TEXT = re.compile(r"\\[\s\S]|`|\$\{")


class JsLines(Lines):
    """JavaScript's and TypeScript's reader: Lines for their comments and quoted strings, and besides a template
    literal's text and its ${...} expressions, nested to any depth, a regular expression literal (told from a
    division by what comes before it, as a parser tells them), and JSX's comment {/* ... */}. Its state is None, or
    (frames, inner): the templates and expressions open around the reading (a template as "`", an expression as the
    number of braces open in it), and the comment or quoted string open inside them."""

    def read(self, line, state, bare=None):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        frames, inner_state = state if state is not None else ((), None)
        n = len(s)
        pos = n - len(s.lstrip())
        code = False
        if inner_state is None and not frames and s.startswith("#!", pos):
            return COMMENT, None   # a script's first line
        last = ""   # the code before pos on this line, for telling a regular expression from a division
        while pos < n:
            if inner_state is not None:
                if inner_state[0] == "b":
                    end = self.inside(s, pos, inner_state)
                    if isinstance(end, tuple):
                        inner_state = end
                        break
                    inner_state, pos = None, end
                else:
                    end = self.literal_end(s, pos, self.syntax.literals[inner_state[1]], inner_state[2])
                    code = True
                    if end < 0:
                        tail = s.rstrip("\r")
                        run = len(tail) - len(tail.rstrip("\\"))
                        inner_state = inner_state if run % 2 else None
                        break
                    inner_state, pos, last = None, end, "a"
                continue
            if frames and frames[-1] == "`":   # a template's text
                m = JS_TEXT.search(s, pos)
                if m or s[pos:].strip():
                    code = True
                if not m:
                    break
                pos = m.end()
                if m.group() == "`":
                    frames, last = frames[:-1], "a"
                elif m.group() == "${":
                    frames, last = frames + (0,), "("
                continue
            m = JS_CODE.search(s, pos)
            end = m.start() if m else n
            text = s[pos:end].rstrip()
            if text.strip():
                code, last = True, text
            if not m:
                break
            g, pos = m.lastgroup, m.end()
            if g == "J":   # {/* at a line's start: JSX's comment, whose braces are not code
                if not code:
                    inner_state, pos = ("b", 0, 1, "*/", True), pos + 2
                    continue
                g = "O"
            if g == "B":
                inner_state = ("b", 0, 1, "*/", False)
            elif g == "L":
                break
            elif g == "Q":
                code, inner_state = True, ("s", 0 if m.group() == "'" else 1, m.group())
            elif g == "T":
                code, frames = True, frames + ("`",)
            elif g == "R":
                word = re.search(r"[\w$]+$", last)
                regex = JS_REGEX.match(s, m.start())
                if regex and (not last or last[-1] in "(,=:[!&|?{};+-*%<>~^" or (word and word.group() in JS_WORDS)):
                    pos = regex.end()
                code, last = True, "a" if regex else "/"
            elif g == "O":
                code, last = True, "{"
                if frames:
                    frames = frames[:-1] + (frames[-1] + 1,)
            else:   # }
                code, last = True, "}"
                if frames:
                    frames = frames[:-1] if frames[-1] == 0 else frames[:-1] + (frames[-1] - 1,)
        state = None if not frames and inner_state is None else (frames, inner_state)
        return (CODE if code else COMMENT), state


PHP_OPEN = re.compile(r"(?i)<\?(?:php(?=\s|$)|=|(?=\s|$))|<!--")


class PhpLines(Lines):
    """PHP's reader: a PHP file starts as HTML, whose comments are <!-- -->, until <?php (or <?=) opens PHP, whose
    comments and literals Lines reads, until ?> closes it again, even inside a line comment. Its state is Lines'
    inside PHP, or ("html",) or ("html-comment",) outside it."""
    initial, middle = ("html",), None

    def read(self, line, state, bare=None):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        n, pos, code = len(s), 0, False
        while pos < n:
            if state == ("html-comment",):
                k = s.find("-->", pos)
                if k < 0:
                    break
                state, pos = ("html",), k + 3
            elif state == ("html",):
                m = PHP_OPEN.search(s, pos)
                if s[pos:m.start() if m else n].strip():
                    code = True
                if not m:
                    break
                pos = m.end()
                if m.group() == "<!--":
                    state = ("html-comment",)
                else:
                    code, state = True, None
            else:
                if state is None and not s[:pos].strip():   # PHP from the line's start
                    start = self.start(s, bare)
                    if start is None:
                        break
                    here, state, pos = start
                    code = code or here
                here, state, stop = self.scan(s, pos, state, False, bare)
                code = code or here
                if stop >= n:
                    break
                state, pos = ("html",), stop + 2
        return (CODE if code else COMMENT), state


class PyLines(LineReader):
    """Python's line reader, for a file Python's tokenizer cannot read (see PythonReader): docstrings and other
    strings standing alone as statements are block comments, and a triple-quoted string opened after code
    (x = \"\"\") is code to its end, its closing quotes opening nothing. A string starting its own line inside a call
    or a list reads as a docstring, where the tokenizer would know better."""
    exact = False

    def read(self, line, state):
        s = line.strip()
        if s[:1] == "\ufeff":
            s = s[1:].lstrip()
        if not s:
            return BLANK, state
        if state is not None and state[0] == "str":   # inside a string opened after code: code to its end
            if state[1] in s:
                quote = open_string(s, state[1])
                return CODE, (("str", quote) if quote else None)
            return CODE, state
        code = False
        while True:
            if state is not None:   # inside a docstring
                k = s.find(state[1])
                if k < 0:
                    return (CODE if code else COMMENT), state
                s, state = s[k + 3:].strip(), None
                if not s:
                    return (CODE if code else COMMENT), None
            doc = DOCSTRING.match(s)
            if not doc:
                break
            quote, s = doc.group(1), s[doc.end():]
            state = ("doc", quote)
        if s.startswith("#"):
            return (CODE if code else COMMENT), None
        if '"""' in s or "'''" in s:
            quote, header = open_string(s), HEADER_DOCSTRING.match(s)
            if quote and header and header.group(1) == quote and quote not in s[header.end():]:
                return CODE, ("doc", quote)   # def f(): """Doc... opens a docstring after the header's code
            if quote:
                return CODE, ("str", quote)
        return CODE, None


DOCSTRING = re.compile(r"""(?i)(?:[rubf]{1,2})?('''|\"\"\")""")
HEADER_DOCSTRING = re.compile(r"""(?:async\s+def|def|class)\b[^#]*:\s*(?:[rRuUbBfF]{1,2})?('''|\"\"\")""")


def open_string(s, quote=None):
    """The triple quote a line of Python leaves open at its end, given the one open at its start, or None. A #
    outside a string ends the line; a backslash escapes the character after it; an ordinary string stays on its
    line."""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if quote:
            if c == "\\":
                i += 2
            elif s.startswith(quote, i):
                quote, i = None, i + 3
            else:
                i += 1
        elif c == "#":
            return None
        elif c in "'\"":
            if s.startswith(c * 3, i):
                quote, i = c * 3, i + 3
            else:
                i += 1
                while i < n and s[i] != c:
                    i += 2 if s[i] == "\\" else 1
                i += 1
        else:
            i += 1
    return quote


def token_types(*names):
    return {getattr(tokenize, name) for name in names if hasattr(tokenize, name)}


F_PARTS = token_types("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END")   # an f-string, read in parts (3.12 on)
F_START, F_END = token_types("FSTRING_START"), token_types("FSTRING_END")
T_START, T_END = token_types("TSTRING_START"), token_types("TSTRING_END")   # a template string (3.14 on)
BRACKETS = {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}
COMPOUND = {"def", "class", "if", "elif", "else", "for", "while", "try", "except", "finally", "with", "async", "match",
            "case"}   # the words that open a compound statement, whose header's colon a body may follow


class ReadFailed(Exception):
    """Python's tokenizer could not read a file."""


class PythonReader:
    """Python and Cython, read by Python's own tokenizer (tokenize), with Python's docstring rule: a statement that
    is only a string (a docstring, or a string standing alone as a block comment) is a comment; bytes are code. A
    reading starts where the tokenizer can be put exactly as the whole file would have it, errors included: where a
    statement ends outside any bracket, its state the indentation open there (the tuple of each level's leading
    whitespace); and inside a statement already known to be code, between the lines of its brackets ("(", the
    indentation, the brackets open, its first word) or of its triple-quoted string ('"', the same, and the string's
    opening). Every other boundary, inside a statement that may yet prove a docstring or inside an f-string, is
    UNREAD. A file the tokenizer cannot read (mixed tabs, a stray null byte) is read by PyLines instead,
    approximately."""
    initial = ()
    exact = True

    def __init__(self):
        self.fallback = PyLines()

    def session(self, get, n, eol, b, stack, stop):
        """Reads lines b and on, from boundary b in the state stack, until stop(k, state) says so at a boundary k
        where a reading can start: (kinds of lines b to k - 1, states at boundaries b + 1 to k, k). Raises
        ReadFailed where the tokenizer fails."""
        opened, first, pure, opening = [], "", None, ""
        if stack and stack[0] in ("(", '"'):   # inside a statement of code: its brackets, and perhaps a string
            opened, first, pure = list(stack[2]), stack[3], False
            opening = stack[4] if stack[0] == '"' else ""
            stack = stack[1]
        prefix = ["if 1:\n"] + [w + "if 1:\n" for w in stack[:-1]] + [stack[-1] + "pass\n"] if stack else []
        if pure is False:   # the statement's start, as far as the tokenizer's state goes: its word, brackets, string
            prefix.append((first or "0") + " " + "".join(opened) + opening + "\n")
        top, feed = len(prefix), {"next": b}

        def readline():
            if prefix:
                return prefix.pop(0)
            i = feed["next"]
            if i >= n:
                return ""
            feed["next"] = i + 1
            text = get(i)
            if i == 0 and text[:1] == "\ufeff":
                text = text[1:]
            return text + ("\n" if i < n - 1 or eol else "")

        marks, clean, levels, strings = set(), {}, list(stack), []   # strings: the f- and t-strings open
        k, shift = n, b - top - 1   # where the reading stops; a token's row, less shift, is its line
        # The statement being read: pure is None before its first token, "(" while it holds only parentheses, True
        # while only strings and parentheses, False once it holds code. held: the rows of its tokens while it may
        # still be only strings; exprs: those of the expressions in its f-strings' braces, which are code anyway.
        # opened: the brackets open in it; first: its first word, which may open a compound statement.
        held, exprs = [], []
        STRING, OP, NAME, NL, NEWLINE = tokenize.STRING, tokenize.OP, tokenize.NAME, tokenize.NL, tokenize.NEWLINE
        INDENT, DEDENT, skip = tokenize.INDENT, tokenize.DEDENT, (tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER)

        def mark(rows):
            for a, z in rows:
                if a == z:
                    marks.add(a)
                else:
                    marks.update(range(a, z + 1))

        try:
            for tok in tokenize.generate_tokens(readline):
                t, text, a, z = tok[0], tok[1], tok[2][0] + shift, tok[3][0] + shift
                if z < b:
                    continue   # the prefix's own
                if t == NEWLINE or t == NL:
                    if t == NEWLINE or (not opened and not strings and pure is None):
                        if pure is True:
                            mark(exprs)
                        elif pure == "(":
                            mark(held)
                        pure, held, exprs, first, opened = None, [], [], "", []
                        clean[a + 1] = state = tuple(levels)
                    elif opened and not strings and pure is False:   # between the lines of a statement of code
                        clean[a + 1] = state = ("(", tuple(levels), "".join(opened), first)
                    else:
                        continue
                    if stop(a + 1, state):
                        k = a + 1
                        break
                    continue
                if t == INDENT:
                    levels.append(text)
                    continue
                if t == DEDENT:
                    if levels:
                        levels.pop()
                    continue
                if t in skip:
                    continue
                if t == OP and not opened and not strings and (text == ";" or text == ":" and first in COMPOUND):
                    if text == ":":   # a compound statement's header: a body may follow it on its line
                        marks.add(a)
                    if pure is True:
                        mark(exprs)
                    elif pure == "(":
                        mark(held)
                    pure, held, exprs, first = None, [], [], ""
                    continue
                if t == OP and text in BRACKETS:
                    if BRACKETS[text] > 0:
                        opened.append(text)
                    elif opened:
                        opened.pop()
                if t in F_START:
                    strings.append("f")
                elif t in T_START:
                    strings.append("t")
                if pure is None:
                    first = text if t == NAME else ""
                if pure is False:
                    if a == z:
                        marks.add(a)
                    else:
                        marks.update(range(a, z + 1))
                        quote = text.find(text[-1]) if t == STRING else -1
                        if quote >= 0 and text[quote:quote + 3] == text[-1] * 3 and not strings:
                            # inside a triple-quoted string of a statement of code: a reading can start there
                            state = None
                            for inner in range(max(a, b) + 1, z + 1):
                                clean[inner] = state = ('"', tuple(levels), "".join(opened), first,
                                                        text[:quote + 3])
                                if stop(inner, state):
                                    k = inner
                                    break
                            if k < n:
                                break
                else:
                    in_f = bool(strings) and "t" not in strings
                    if in_f or t in F_PARTS or (t == STRING and "b" not in text[:text.find(text[-1])].lower()):
                        pure = True
                        held.append((a, z))
                        if in_f and t not in F_PARTS:
                            exprs.append((a, z))
                    elif t == OP and text in "()" and not strings:
                        pure = pure or "("
                        held.append((a, z))
                    else:
                        mark(held)
                        mark(((a, z),))
                        pure, held, exprs = False, [], []
                if (t in F_END or t in T_END) and strings:
                    strings.pop()
        except (tokenize.TokenError, SyntaxError, ValueError, IndexError):
            raise ReadFailed() from None
        if pure is True:
            mark(exprs)
        elif pure == "(":
            mark(held)
        kinds = []
        for i in range(b, k):
            text = get(i)
            if i == 0 and text[:1] == "\ufeff":
                text = text[1:]
            kinds.append(BLANK if not text.strip() else CODE if i in marks else COMMENT)
        return kinds, [clean.get(j, UNREAD) for j in range(b + 1, k + 1)], k


class Indented(LineReader):
    """A reader for an indented syntax, whose comment runs over the lines indented beneath its first, whatever
    they hold (Sass's .sass files, Pug, Slim, Haml): state None, or the indentation of the comment's first line."""

    def __init__(self, markers):
        self.markers = re.compile(markers)

    def read(self, line, state):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        indent = len(s) - len(s.lstrip())
        if state is not None and indent > state:
            return COMMENT, state
        if self.markers.match(s, indent):
            return COMMENT, indent
        return CODE, None


class Literate(LineReader):
    """A literate source, prose around code, whose prose reads as comment and code as its language reads it: Bird
    tracks (> at the start of a line) and \\begin{code} blocks in literate Haskell and Idris and LaTeX literate Agda
    (style tex), fenced blocks in Markdown and Typst literate Agda (md: a bare fence or ```agda holds code, a fence
    naming another language an example), src blocks in Org (org), and indented blocks in literate CoffeeScript
    (indent). Its state is (where the reading is: prose, code or example; the code reader's state)."""
    initial = ("prose", None)

    def __init__(self, code, style):
        self.code, self.style = code, style
        self.initial, self.middle = ("prose", code.initial), ("code", code.middle)

    def read(self, line, state):
        where, inside = state
        s = line.strip()
        if s[:1] == "\ufeff":
            s = s[1:].lstrip()
        if not s:
            return BLANK, state
        style = self.style
        if style == "tex":
            if line.startswith(">"):   # a Bird track: the rest of the line is code
                kind, inside = self.code.read(line[1:], inside)
                return kind, (where, inside)
            if s.startswith(("\\begin{code}", "\\end{code}")):
                return COMMENT, ("code" if s.startswith("\\begin") else "prose", inside)
        elif style == "md" and s.startswith("```"):
            info = s.strip("`").strip().lower()
            if info or where == "prose":   # a fence naming a language opens a block; a bare one only outside one
                return COMMENT, ("code" if info in ("", "agda") else "example", inside)
            return COMMENT, ("prose", inside)
        elif style == "org" and s.lower().startswith(("#+begin_src", "#+end_src")):
            return COMMENT, ("code" if s.lower().startswith("#+begin_src agda") else "prose", inside)
        elif style == "indent":
            if line.startswith(("    ", "\t")):
                kind, inside = self.code.read(line, inside)
                return kind, (where, inside)
            return COMMENT, state
        if where == "code":
            kind, inside = self.code.read(line, inside)
            return kind, (where, inside)
        return COMMENT, state


LITERATE = {".lhs": "tex", ".lidr": "tex", ".lagda": "tex", ".lagda.tex": "tex", ".lagda.md": "md",
            ".lagda.typ": "md", ".lagda.org": "org", ".litcoffee": "indent", ".coffee.md": "indent"}


def literate_style(path):
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return next((style for suffix, style in LITERATE.items() if name.endswith(suffix)), None)


# Every counted language's syntax (see Syntax). A plain prefix is escaped (SL); C-family strings are quoted and
# escaped with a backslash on one line (Q1) and character literals are read whole (C_CHAR, and PRIME_CHAR where a
# name may end in a quote, as Haskell's foldl' does, or a quote opens a lifetime, as Rust's 'a does).
SL = lambda *p: tuple(E(x) for x in p)   # noqa: E731
Q1 = lambda q: lit("esc1", E(q), q)      # noqa: E731
QM = lambda q: lit("esc", E(q), q)       # noqa: E731
C_CHAR = lit("skip", r"(?:(?<=u8)|(?<![0-9]))'(?:\\.|[^\\'\n])+'")   # after a digit, C++'s 1'000 separator
PRIME_CHAR = lit("skip", r"(?<![\w'])b?'(?:\\.[^'\s]*|[^\\'\n])'")
C_BLOCK, C_NEST = blk("/*", "*/"), blk("/*", "*/", nests=True)
C_STR = (Q1('"'), C_CHAR)
CPP_STR = (lit("raw", r'(?:u8|[uUL])?R"([^()\\\s]{0,16})\(', '){0}"'),) + C_STR
PY_LIKE = (QM("'''"), QM('"""'), Q1("'"), Q1('"'))
HTML_BLOCK = blk("<!--", "-->")
HS_LINE = (r"--+(?![-!#$%&*+./<=>?@\\^|~:])",)   # --> is an operator, not a comment
HS_BLOCK = Block(r"\{-(?!#)", "-}", True, "any", False)   # {-# LANGUAGE #-} is a pragma, not a comment
ML_NEST = blk("(*", "*)", nests=True)
ML_NEST_NO_OP = Block(r"\(\*(?!\))", "*)", True, "any", False)   # F#'s (*) is the operator, not a comment


def c_like(line=("//",), blocks=(C_BLOCK,), literals=C_STR, **more):
    return Syntax(line=SL(*line), blocks=blocks, literals=literals, **more)


def hash_like(literals=(), tracked=True, **more):
    return Syntax(line=SL("#"), literals=literals, tracked=tracked and bool(literals), **more)


SYNTAXES = {
    **{lang: c_like() for lang in ("C", "Objective-C++", "Solidity", "GLSL", "HLSL", "Protocol Buffer", "AIDL",
                                   "Stan", "Verilog", "SystemVerilog", "ShaderLab", "Processing", "Yacc", "Lex",
                                   "SWIG", "XS", "SmPL", "Pawn", "OpenSCAD", "Move", "ANTLR", "Asymptote")},
    **{lang: c_like(literals=CPP_STR) for lang in ("C++", "Cuda", "Metal")},
    "C#": c_like(literals=(lit("raw", r'\$*("{3,})', "{0}"), lit("dbl", r'\$?@\$?"', '"')) + C_STR),
    "Java": c_like(literals=(QM('"""'),) + C_STR),
    "Kotlin": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(lit("raw", E('"""'), '"""'),) + C_STR),
    "Scala": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(lit("raw", E('"""'), '"""'), Q1('"'), PRIME_CHAR)),
    "Swift": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(
        lit("raw", r'(#+)"""', '"""{0}'), lit("raw1", r'(#+)"', '"{0}'), QM('"""'), Q1('"'))),
    "Go": c_like(literals=(lit("raw", "`", "`"),) + C_STR),
    "Rust": c_like(blocks=(C_NEST,), literals=(lit("raw", r'(?<![\w])[bc]?r(#*)"', '"{0}'), QM('"'), PRIME_CHAR)),
    "Dart": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(
        lit("raw", r"(?<!\w)r'''", "'''"), lit("raw", r'(?<!\w)r"""', '"""'), QM("'''"), QM('"""'),
        lit("raw1", r"(?<!\w)r'", "'"), lit("raw1", r'(?<!\w)r"', '"'), Q1("'"), Q1('"'))),
    **{lang: c_like(line=("//", "#!"), literals=(QM("'''"), QM('"""'), Q1("'"), Q1('"')))
       for lang in ("Groovy", "Gradle", "Nextflow")},
    "D": c_like(line=("//", "#!"), blocks=(C_BLOCK, blk("/+", "+/", nests=True)), literals=(
        lit("raw", r'(?<!\w)r"', '"'), lit("raw", "`", "`"), QM('"'), C_CHAR)),
    "Zig": c_like(literals=(lit("eol", r"\\\\"),) + C_STR),
    "Odin": c_like(blocks=(C_NEST,), literals=(lit("raw", "`", "`"),) + C_STR),
    "WGSL": c_like(blocks=(C_NEST,)),
    "Vala": c_like(literals=(lit("raw", E('"""'), '"""'),) + C_STR),
    "Haxe": c_like(literals=(QM("'"), QM('"'))),
    "Apex": c_like(literals=(Q1("'"),)),
    "Thrift": c_like(line=("//", "#"), literals=(Q1('"'), Q1("'"))),
    "Jsonnet": c_like(line=("//", "#"), literals=(lit("raw", r"\|\|\|-?", "|||"), lit("dbl1", E('@"'), '"'),
                                                  lit("dbl1", E("@'"), "'"), Q1('"'), Q1("'"))),
    "CUE": c_like(literals=(QM('"""'), QM("'''"), Q1('"'), Q1("'"))),
    "Pkl": c_like(literals=(QM('"""'), Q1('"'))),
    "Bicep": c_like(literals=(lit("raw", "'''", "'''"), Q1("'"))),
    "Carbon": c_like(literals=(lit("raw", "'''", "'''"),) + C_STR),
    "Cairo": c_like(literals=(Q1('"'), Q1("'"))),
    "Gleam": c_like(literals=(QM('"'),)),
    "ReScript": c_like(literals=(lit("esc", "`", "`"), Q1('"'), PRIME_CHAR)),
    "Reason": c_like(literals=(lit("raw", r"\{([a-z_]*)\|", "|{0}}"), Q1('"'), PRIME_CHAR)),
    "Dafny": c_like(literals=(lit("dbl", E('@"'), '"'), Q1('"'), PRIME_CHAR)),
    "GraphQL": Syntax(line=SL("#"), literals=(QM('"""'), Q1('"'))),
    "CSS": c_like(literals=(lit("raw1", r"url\((?!\s*[\"'])", ")"), Q1('"'), Q1("'"))),
    "SQL": Syntax(line=SL("--"), start=SL("#"), blocks=(C_BLOCK,), literals=(
        lit("both1", "'", "'"), lit("dbl1", '"', '"'), lit("raw1", "`", "`"))),
    "PHP": Syntax(line=(E("//"), r"#(?!\[)"), blocks=(C_BLOCK,), literals=(
        QM("'"), QM('"'), lit("here", r"<<<[ \t]*[\"']?([A-Za-z_]\w*)[\"']?")), exits=r"\?>"),
    "Hack": Syntax(line=(E("//"), r"#(?!\[)"), blocks=(C_BLOCK,), literals=(
        QM("'"), QM('"'), lit("here", r"<<<[ \t]*[\"']?([A-Za-z_]\w*)[\"']?"))),
    "Lua": Syntax(line=SL("--"), blocks=(Block(r"--\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), Q1('"'), Q1("'"))),
    "Luau": Syntax(line=SL("--"), blocks=(Block(r"--\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), Q1('"'), Q1("'"), Q1("`"))),
    "Haskell": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(Q1('"'), PRIME_CHAR)),
    "Elm": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(QM('"""'), Q1('"'), PRIME_CHAR)),
    # PureScript's block comments, unlike Haskell's, do not nest
    "PureScript": Syntax(line=HS_LINE, blocks=(Block(r"\{-", "-}", False, "any", False),), literals=(
        lit("raw", E('"""'), '"""'), Q1('"'), PRIME_CHAR)),
    "Agda": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(Q1('"'), PRIME_CHAR)),
    "Idris": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(QM('"""'), Q1('"'), PRIME_CHAR)),
    "Dhall": Syntax(line=SL("--"), blocks=(blk("{-", "-}", nests=True),), literals=(
        lit("raw", "''", r"''(?!')", esc="re"), Q1('"'))),
    "Lean": Syntax(line=SL("--"), blocks=(blk("/-", "-/", nests=True),), literals=(QM('"'), PRIME_CHAR)),
    "OCaml": Syntax(blocks=(ML_NEST,), literals=(lit("raw", r"\{([a-z_]*)\|", "|{0}}"), QM('"'), PRIME_CHAR)),
    "Standard ML": Syntax(blocks=(ML_NEST,), literals=(lit("skip", r'#"(?:\\.|[^"\\])"'), QM('"'))),
    "F#": Syntax(line=SL("//"), blocks=(ML_NEST_NO_OP,), literals=(
        lit("raw", E('"""'), '"""'), lit("dbl", r'\$?@\$?"', '"'), QM('"'), PRIME_CHAR)),
    "F*": Syntax(line=SL("//"), blocks=(ML_NEST_NO_OP,), literals=(QM('"'), PRIME_CHAR)),
    "Rocq Prover": Syntax(blocks=(ML_NEST,), literals=(lit("dbl", '"', '"'),)),
    "Isabelle": Syntax(blocks=(ML_NEST,), literals=(lit("raw", '"', '"'), lit("raw", "\u2039", "\u203a"))),
    "Wolfram": Syntax(blocks=(ML_NEST,), literals=(QM('"'),)),
    "AppleScript": Syntax(line=SL("--", "#"), blocks=(ML_NEST,), literals=(Q1('"'),)),
    "Pascal": Syntax(line=SL("//"), blocks=(Block(r"\{(?!\$)", "}", False, "any", False),
                                             Block(r"\(\*(?!\$)", "*)", False, "any", False)),
                     literals=(lit("dbl1", "'", "'"),)),   # {$IFDEF} and (*$R+*) are compiler directives: code
    "TLA": Syntax(line=SL("\\*"), blocks=(ML_NEST,), literals=(Q1('"'),)),
    "WebAssembly": Syntax(line=SL(";;"), blocks=(blk("(;", ";)", nests=True),), literals=(Q1('"'),)),
    "Nim": Syntax(line=SL("#"), blocks=(blk("##[", "]##", nests=True), blk("#[", "]#", nests=True)), literals=(
        lit("raw", E('"""'), '"""'), lit("dbl1", r'(?<!\w)[rR]"', '"'), Q1('"'), C_CHAR)),
    "Julia": Syntax(line=SL("#"), blocks=(blk("#=", "=#", nests=True),), literals=(
        QM('"""'), QM('"'), QM("```"), QM("`"), lit("skip", r"(?<![\w)\]}'.])'(?:\\.[^'\s]*|[^\\'\n])'"))),
    "PowerShell": Syntax(line=SL("#"), blocks=(blk("<#", "#>"),), literals=(
        lit("raw", r'@"(?=\s*$)', r'^"@', esc="re"), lit("raw", r"@'(?=\s*$)", r"^'@", esc="re"),
        lit("esc", '"', '"', esc="`"), lit("dbl", "'", "'"))),
    "CoffeeScript": Syntax(line=SL("#"), start_blocks=(Block(r"###(?!#)", "###", False, "any", False),), literals=(
        lit("raw", "///", "///"), QM('"""'), QM("'''"), QM('"'), QM("'"))),
    "Elixir": Syntax(line=SL("#"), literals=(QM('"""'), QM("'''"), QM('"'), QM("'"), lit("skip", r"\?(?:\\.|\S)"))),
    "Erlang": Syntax(line=SL("%"), literals=(QM('"""'), QM('"'), Q1("'"), lit("skip", r"\$(?:\\.|.)"))),
    "Prolog": Syntax(line=SL("%"), blocks=(C_BLOCK,), literals=(
        lit("skip", r"(?<!\w)0'(?:\\.|''|.)"), QM('"'), Q1("'"))),
    "R": Syntax(line=SL("#"), literals=(QM('"'), QM("'"), lit("raw1", "`", "`"))),
    "Meson": Syntax(line=SL("#"), literals=(lit("raw", "'''", "'''"), Q1("'"))),
    "GAP": Syntax(line=SL("#"), literals=(lit("raw", E('"""'), '"""'), Q1('"'), C_CHAR)),
    "jq": Syntax(line=SL("#"), literals=(Q1('"'),)),
    "Cap'n Proto": Syntax(line=SL("#"), literals=(Q1('"'),)),
    "Open Policy Agent": Syntax(line=SL("#"), literals=(lit("raw", "`", "`"), Q1('"'))),
    "Janet": Syntax(line=SL("#"), literals=(lit("raw", r"(`+)", "{0}"), QM('"'))),
    **{lang: Syntax(line=SL("#"), literals=PY_LIKE) for lang in ("Starlark", "Mojo", "Sage", "Vyper", "GDScript")},
    **{lang: Syntax(line=SL(";"), blocks=(blk("#|", "|#", nests=True),), literals=(
        lit("skip", r"#\\(?:x[0-9a-fA-F]+|[A-Za-z]+|.)"), QM('"'))) for lang in ("Common Lisp", "Scheme", "Racket")},
    "Emacs Lisp": Syntax(line=SL(";"), literals=(lit("skip", r"(?<![\w-])\?\\?."), QM('"'))),
    "Clojure": Syntax(line=SL(";"), literals=(lit("skip", r"\\(?:newline|space|tab|u[0-9a-fA-F]{4}|.)"), QM('"'))),
    "Fennel": Syntax(line=SL(";"), literals=(QM('"'),)),
    "Hy": Syntax(line=SL(";"), literals=(lit("raw", r"#\[(\w*)\[", "]{0}]"), QM('"'))),
    "CMake": Syntax(line=SL("#"), blocks=(Block(r"#\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), QM('"'))),
    "Nix": Syntax(line=SL("#"), blocks=(C_BLOCK,), literals=(lit("raw", "''", r"''(?![$'\\])", esc="re"), QM('"'))),
    "Alloy": c_like(line=("//", "--")),
    "AMPL": c_like(line=("#",)),
    # languages read at the start of each line only (see Syntax): their literals cannot be followed line by line
    **{lang: hash_like() for lang in ("Shell", "Nushell", "Makefile", "Dockerfile", "Crystal", "Tcl", "Awk", "sed",
                                      "Just", "Procfile", "Gnuplot", "Earthly", "BitBake", "GDB", "Gherkin", "NASL",
                                      "QMake", "RobotFramework")},
    "Perl": hash_like(start_blocks=(Block(r"=[A-Za-z]", r"=cut\b", False, "col0", True),
                                    Block(r"__(?:END|DATA)__\s*$", r"(?!)", False, "col0", False))),
    "Ruby": hash_like(start_blocks=(Block(r"=begin\b", r"=end\b", False, "col0", True),
                                    Block(r"__END__\s*$", r"(?!)", False, "col0", False))),
    "Raku": hash_like(start_blocks=(Block(r"=begin\b", r"^\s*=end\b", False, "re", True),)),
    "M4": Syntax(line=SL("#"), start=(r"dnl(?![\w])",), tracked=False),
    "MATLAB": Syntax(line=SL("%"), start_blocks=(Block(r"%\{", r"%\}", True, "alone", False),), tracked=False),
    "Scilab": Syntax(line=SL("//"), blocks=(C_BLOCK,), tracked=False),
    "Stata": Syntax(line=SL("//"), start=SL("*"), blocks=(C_BLOCK,), tracked=False),
    "SAS": Syntax(start_blocks=(Block(r"%?\*", r";", False, "re", False),), blocks=(C_BLOCK,), tracked=False),
    "Macaulay2": Syntax(line=SL("--"), blocks=(blk("-*", "*-"),), tracked=False),
    "Typst": Syntax(line=SL("//"), blocks=(C_BLOCK,), tracked=False),
    "Forth": Syntax(line=(r"\\(?=\s|$)",), blocks=(Block(r"\((?=\s)", ")", False, "any", False),), tracked=False),
    "Fortran": Syntax(line=SL("!"), tracked=False),
    "Ada": Syntax(line=SL("--"), tracked=False),
    "VHDL": Syntax(line=SL("--"), blocks=(C_BLOCK,), tracked=False),
    "COBOL": Syntax(line=SL("*>"), column=((6, "*/"),), tracked=False),
    "Assembly": Syntax(line=SL(";", "//", "#"), start=SL("@"), blocks=(C_BLOCK,), tracked=False, code_first=(
        r"#\s*(?:include|define|undef|ifn?def|if|else|elif|endif|error|warning|pragma|line)\b",)),
    "LLVM": Syntax(line=SL(";"), tracked=False),
    "SMT": Syntax(line=SL(";"), tracked=False),
    "PureBasic": Syntax(line=SL(";"), tracked=False),
    "MLIR": Syntax(line=SL("//"), tracked=False),
    "Mermaid": Syntax(line=SL("%%"), tracked=False),
    "Batchfile": Syntax(start=(r"@?rem(?![\w])", E("::")), tracked=False),
    "VBScript": Syntax(line=SL("'"), start=(r"rem(?![\w])",), tracked=False),
    "Visual Basic .NET": Syntax(line=SL("'"), start=(r"rem(?![\w])",), tracked=False),
    "Vim script": Syntax(line=SL('"', "#"), tracked=False),
    "HCL": Syntax(line=SL("#", "//"), blocks=(C_BLOCK,), tracked=False),
    "NSIS": Syntax(line=SL(";", "#"), blocks=(C_BLOCK,), tracked=False),
    "Inno Setup": Syntax(line=SL(";", "//"), tracked=False),
    "AutoHotkey": Syntax(line=SL(";"), blocks=(C_BLOCK,), tracked=False),
    # markup and templates: their comments may follow markup anywhere on a line; they hold no literals to follow
    "HTML": Syntax(blocks=(HTML_BLOCK, blk("<%#", "%>"), blk("@*", "*@"), blk("<%!--", "--%>"))),
    "XSLT": Syntax(blocks=(HTML_BLOCK,)),
    **{lang: Syntax(line=SL("//"), start_blocks=(C_BLOCK,), blocks=(HTML_BLOCK,)) for lang in ("Vue", "Svelte", "Astro")},
    **{lang: Syntax(blocks=(blk("{#", "#}"), HTML_BLOCK)) for lang in ("Jinja", "Nunjucks")},
    "Twig": Syntax(line=SL("//"), blocks=(blk("{#", "#}"), C_BLOCK, HTML_BLOCK)),
    "Blade": Syntax(line=SL("//"), blocks=(blk("{{--", "--}}"), C_BLOCK, HTML_BLOCK)),
    "Handlebars": Syntax(blocks=(blk("{{!--", "--}}"), blk("{{!", "}}"), HTML_BLOCK)),
    "Mustache": Syntax(blocks=(blk("{{!", "}}"),)),
    "EJS": Syntax(blocks=(blk("<%#", "%>"), HTML_BLOCK)),
    "Liquid": Syntax(blocks=(Block(r"\{%-?\s*comment\s*-?%\}", r"\{%-?\s*endcomment\s*-?%\}", False, "re", False),
                             Block(r"\{%-?\s*#", r"-?%\}", False, "re", False), HTML_BLOCK)),
    "Go Template": Syntax(blocks=(Block(r"\{\{-?\s*/\*", r"\*/\s*-?\}\}", False, "re", False), HTML_BLOCK)),
    "FreeMarker": Syntax(blocks=(blk("<#--", "-->"), HTML_BLOCK)),
    "ASP.NET": Syntax(blocks=(blk("<%--", "--%>"), HTML_BLOCK)),
    "Mako": Syntax(line=SL("##"), blocks=(blk("<%doc>", "</%doc>"), HTML_BLOCK)),
}
# An extension several languages share counts as Other, and Other is otherwise not code (NOT_CODE). One whose every
# sharer comments compatibly still holds code, drawn as Other: a header (.h) is C, C++ or Objective-C, which all
# comment as C does; .m is Objective-C or MATLAB (// and %, /* */ and %{ %}, but not Mathematica's (* *), which
# would take a function-pointer call such as (*handler)(x) for a comment); .fs is F#, Forth or a GLSL fragment
# shader; .v is Verilog or Rocq.
SHARED_CODE = {
    ".h": SYNTAXES["C++"],
    ".m": Syntax(line=SL("//", "%"), start_blocks=(C_BLOCK, Block(r"%\{", r"%\}", True, "alone", False)),
                 tracked=False),
    ".fs": Syntax(line=(E("//"), r"\\(?=\s|$)"), start_blocks=(ML_NEST_NO_OP, C_BLOCK), tracked=False),
    ".v": Syntax(line=SL("//"), start_blocks=(C_BLOCK, ML_NEST), tracked=False),
}
FIXED_FORM = {".f", ".f77", ".for", ".fpp"}   # fixed-form Fortran, where C, c, * or ! in column 1 is a comment
READERS = {}


def counts_as_code(path, lang):
    """Whether a file of this language at this path holds lines of code (see NOT_CODE and SHARED_CODE)."""
    return bool(lang) and (lang not in NOT_CODE or lang == OTHER and os.path.splitext(path.lower())[1] in SHARED_CODE)


def reader_for(lang, path):
    """The reader of a file of this language at this path, and a key naming it: files read alike share a key, so
    a reading of one file version serves every path it stands at (see Version)."""
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    ext = os.path.splitext(name)[1]
    style = literate_style(name)
    if style:
        key = (lang, style)
    elif lang in ("Python", "Cython"):
        key = ("Python",)
    elif ext == ".sass" or lang in ("Pug", "Slim", "Haml"):
        key = (lang, ext if ext == ".sass" else "")
    elif lang == "Fortran" and ext in FIXED_FORM:
        key = (lang, "fixed")
    elif lang == OTHER:
        key = (lang, ext)
    else:
        key = (lang,)
    reader = READERS.get(key)
    if reader is None:
        if style:
            reader = Literate(reader_for(lang, "x")[0], style)
        elif key == ("Python",):
            reader = PythonReader()
        elif ext == ".sass":
            reader = Indented(r"/\*|//")
        elif lang in ("Pug", "Slim", "Haml"):
            reader = Indented({"Pug": r"//", "Slim": r"/", "Haml": r"-#|/"}[lang])
        elif key[1:] == ("fixed",):
            reader = Lines(Syntax(line=SL("!"), column=((0, "Cc*!"),), tracked=False))
        elif lang in ("JavaScript", "TypeScript", "QML"):
            reader = JsLines(Syntax(blocks=(C_BLOCK,), literals=(Q1("'"), Q1('"'))))
        elif lang == "PHP":
            reader = PhpLines(SYNTAXES["PHP"])
        else:
            syntax = SHARED_CODE.get(ext) if lang == OTHER else SYNTAXES.get(lang)
            reader = Lines(syntax or Syntax())
        READERS[key] = reader
    return reader, key


class LineKinds:
    """Consecutive lines of one language read one at a time, as its line reader reads them, from a file's start (or,
    with at_start False, from part way through one): kind(line) is code, comment or blank. Python's is PyLines, since
    the tokenizer reads whole statements (see read_lines), which is how coderprint reads every file."""

    def __init__(self, lang, path="", at_start=True):
        reader = reader_for(lang, path or "x")[0]
        self.reader = reader.fallback or reader
        self.state = self.reader.initial if at_start else self.reader.middle

    def kind(self, line):
        kind, self.state = self.reader.read(line, self.state)
        return KINDS[kind]


def read_lines(reader, get, n, eol):
    """How every line of a file reads, as its reader reads the whole file: (kinds, one byte a line; the state at
    each boundary, or None where every state is None; whether the reading is exact, not the fallback's)."""
    try:
        kinds, states, _ = reader.session(get, n, eol, 0, reader.initial, never)
        exact = reader.exact
        first = reader.initial
    except ReadFailed:
        fallback = reader.fallback
        kinds, states, _ = fallback.session(get, n, eol, 0, fallback.initial, never)
        exact, first = False, fallback.initial
    states = [first] + states
    return bytes(kinds), (None if all(x is None for x in states) else states), exact


def state_at(states, k):
    return None if states is None else states[k]


def read_edited(reader, old, get, n, eol, edits):
    """How the lines of a new file version read, from the old version's reading (old: kinds and states by reader)
    and the edits that made one from the other, [(old start, old end, new start, new end)] in order: the new file
    is read only from the last boundary before each edit where a reading can start, until its reading agrees with
    the old one again, and every other line reads as it did. The result is the whole file's reading, line for line
    (see LineReader). Raises ReadFailed as the reader does."""
    old_kinds, old_states = old
    old_n, m = len(old_kinds), len(edits)
    kinds = bytearray(n)
    held = [None if old_states is None else [None] * (n + 1)]   # the states, None while every one is None
    shift = [0]   # a new line's index less its old one, past the first k edits
    for o_start, o_end, n_start, n_end in edits:
        shift.append(shift[-1] + (n_end - n_start) - (o_end - o_start))
    if held[0] is not None:
        held[0][0] = old_states[0]
    j = e = 0   # read up to boundary j of the new file, past the first e edits

    def behind(edit, k):
        """Whether an edit lies wholly before boundary k: its new lines before it, or, when it only deletes, at it."""
        return edit[3] <= k and (edit[2] < k or edit[2] == edit[3])

    def copy(start, end, by):   # lines unchanged, read as they were
        if end > start:
            kinds[start:end] = old_kinds[start - by:end - by]
            if old_states is not None:
                held[0][start + 1:end + 1] = old_states[start + 1 - by:end + 1 - by]

    while e < m:
        n_start = edits[e][2]
        b = n_start   # the last boundary before the edit, and not before j, where a reading can start
        while b > j and state_at(old_states, b - shift[e]) == UNREAD:
            b -= 1
        copy(j, b, shift[e])
        passed = [e]

        def agrees(k, state):
            """Whether boundary k is past the edits begun and outside every edit, with the old reading's state."""
            while passed[0] < m and behind(edits[passed[0]], k):
                passed[0] += 1
            if passed[0] == e or (passed[0] < m and edits[passed[0]][2] < k):
                return False
            back = k - shift[passed[0]]
            return state != UNREAD and 0 <= back <= old_n and state_at(old_states, back) == state

        start = state_at(held[0], b)
        if agrees(b, start):   # an edit that only deletes, and leaves the reading as it was
            j, e = b, passed[0]
            continue
        got, got_states, k = reader.session(get, n, eol, b, start, agrees)
        kinds[b:k] = bytes(got)
        if held[0] is None and any(x is not None for x in got_states):
            held[0] = [None] * (n + 1)
        if held[0] is not None:
            held[0][b + 1:k + 1] = got_states
        j, e = k, (passed[0] if k < n else m)
    copy(j, n, shift[m])
    return bytes(kinds), held[0]


GEN_LINES, GEN_HTML_LINES = 5, 40
# Generated files, known as GitHub's Linguist knows them, by what their first lines say rather than by their name:
# a comment that opens with a generator's mark within the first GEN_LINES lines ("// Code generated by sqlc. DO NOT
# EDIT.", "// <auto-generated />", "# Generated by Django 4.2", "# This file is auto-generated from the current state
# of the database", "/*! tailwindcss v3"), an HTML page whose first GEN_HTML_LINES lines name its generator (Hugo,
# Jekyll, Hexo, MkDocs, Javadoc, Doxygen), which with enough such pages makes every HTML, CSS and JavaScript file in
# their folder and below the site's output (generated_output), and a .ts file that is Qt Linguist's XML. A file that
# only mentions such words is not one, and neither is one whose comment only says not to edit something: "do not
# edit" marks a file only beside a word of generating.
SITE_PAGES, ROOT_SITE_PAGES = 3, 10
GEN_OPENERS = ("//", "#", "/*", "*", "--", ";", "<!--", "%", "{-", "(*", "<")
GENERATED = re.compile(r"(?:code generated|generated by|this (?:file|code) (?:is|was|has been) (?:auto-?|automatically "
                       r")?generated|this is (?:auto-?|code )?generated|auto-?generated|automatically generated|"
                       r"@generated|do not edit\b.*\bgenerat\w*|tailwindcss v\d)\b", re.I)
GENERATOR = re.compile(r"<meta\s[^>]*name=[\"']?generator\b|<!--\s*generated by\b", re.I)
WEB_OUTPUT = {"HTML", "CSS", "JavaScript"}


def generated_line(text, lang, n):
    """Whether line n, counted from 1, of a file in lang marks the whole file as generated (see GENERATED)."""
    s = text.lstrip().lstrip("﻿")
    if n <= GEN_LINES and s.startswith(GEN_OPENERS) and GENERATED.match(s.lstrip("/#*;!<{%(- \t")):
        return True
    if lang == "HTML" and n <= GEN_HTML_LINES and GENERATOR.search(s):
        return True
    return lang == "TypeScript" and n == 1 and s.startswith(("<?xml", "<!DOCTYPE TS", "<TS "))


def generated_head(get, n, lang):
    """Whether a file's first lines mark it as generated (generated_line)."""
    return any(generated_line(get(i), lang, i + 1) for i in range(min(n, GEN_HTML_LINES)))


def generated_output(paths, marked):
    """The paths among paths that are generated: those marked (a generator's mark in their first lines), and every
    HTML, CSS or JavaScript file of a generated site: under the deepest folder holding all the marked HTML pages that
    share a top-level folder, when there are at least SITE_PAGES of them (docs/ for docs/index.html, docs/404.html and
    docs/posts/a/index.html), or anywhere, when at least ROOT_SITE_PAGES marked pages include one at the top level (a
    site built into the root of owner.github.io). A page or two naming a generator, as a hand-written page copied from
    a template can, marks only itself, never the owner's scripts and styles beside it."""
    groups, pages = {}, 0
    for p in marked:
        if language_of(p) == "HTML":
            pages += 1
            folders = os.path.dirname(p).split("/") if "/" in p else []
            groups.setdefault(folders[0] if folders else "", []).append(folders)
    sites = {"/".join(os.path.commonprefix(folders)) for top, folders in groups.items()
             if top and len(folders) >= SITE_PAGES}
    if "" in groups and pages >= ROOT_SITE_PAGES:
        sites.add("")
    inside = lambda p: any(not s or p.startswith(s + "/") for s in sites)   # noqa: E731
    return {p for p in paths if p in marked or (sites and language_of(p) in WEB_OUTPUT and inside(p))}


def text_of(data):
    """A blob's text: UTF-16 or UTF-32 by its byte order mark (as Windows tools save PowerShell and resource
    scripts), else UTF-8, unless it holds a null byte in its first 8,000 bytes, which is how git tells a binary
    file; None for a binary file."""
    if data.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        return data.decode("utf-32", "replace")
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", "replace")
    if b"\x00" in data[:8000]:
        return None
    return data.decode("utf-8", "replace")


def split_lines(data, sep):
    """A file's lines, as git counts them, and whether it ends with a newline."""
    lines = data.split(sep)
    if lines[-1]:
        return lines, False
    lines.pop()
    return lines, bool(lines)


# Test code, by where it lives: a folder of tests anywhere in the path, or a file named as one (test_x.py,
# x_test.go, x.test.ts, XTest.java, conftest.py, and this project's own xTEST.py); Rust's code compiled only in
# tests is found inside the files at the head (see rust_lines and rust_test_files).
TEST_DIRS = {"test", "tests", "__tests__", "__test__", "spec", "specs", "testing", "e2e", "integration_tests",
             "__mocks__", "mocks", "fixtures", "__fixtures__", "test_utils", "testutils", "testutil",
             "testhelpers", "testsupport", "cypress", "bench", "benches", "benchmark", "benchmarks"}
# A folder named for tests the way build tools name one: a word such as tests or IntegrationTests after a dot, dash
# or underscore (.NET's MyApp.Tests and MyApp.UnitTests, integration-tests, unit_tests), a source set in lower camel
# case ending in Test (Android's androidTest, Kotlin Multiplatform's commonTest), a camel-case name ending in Tests
# (Xcode's MyAppTests and MyAppUITests), or test and a capital (Gradle's testFixtures, testDebug). An app named
# SpeedTest and a pytest plugin's pytest_x package stay production.
TEST_DIR_WORD = re.compile(r"(?:x|rs|js|ts|go|e2e|unit|int|smoke|integration|functional|acceptance|system|ui)?tests?",
                           re.I)
TEST_DIR_CAMEL = re.compile(r"^[a-z][A-Za-z0-9]*[a-z0-9]Test$|[a-z0-9](?:UI)?Tests$|^test[A-Z]")
TEST_WORD = re.compile(r"^(?:x|rs|py|js|ts|go|e2e|unit|int|smoke)?tests?$|^conftest$", re.I)
CAMEL_TEST = re.compile(r"(?:[A-Za-z0-9](?:Test|Tests)|[a-z0-9]IT)\.[A-Za-z]+$")   # FooTest, IOTest, LoginUITests
# x.test.ts, and what test runners name their own: Cypress's x.cy.tsx, NestJS's x.e2e-spec.ts, tsd's x.test-d.ts
TEST_SUFFIX = re.compile(r"\.(?:test|cy|e2e-spec|e2e-test|test-d)\.[A-Za-z]+$", re.I)
# A file named as a spec (user_spec.rb, app.spec.ts, FooSpec.groovy) is a test only in the languages whose test
# frameworks name them so (RSpec, Jasmine, Mocha, busted, Spock, ScalaTest, Kotest, Quick, hspec, phpspec, ESpec);
# elsewhere spec.go, package_id_spec.rs, spec.py or KeySpec.java holds a specification, and is production
SPEC_LANGUAGES = {"Ruby", "JavaScript", "TypeScript", "CoffeeScript", "Lua", "Crystal", "Groovy", "Scala", "Kotlin",
                  "Swift", "Haskell", "PHP", "Elixir"}
SPEC_WORD = re.compile(r"^specs?$", re.I)
CAMEL_SPEC = re.compile(r"[a-z0-9]Spec\.[A-Za-z]+$")
SPEC_SUFFIX = re.compile(r"\.(?:spec|spec-d)\.[A-Za-z]+$", re.I)


@functools.lru_cache(maxsize=1 << 16)
def is_test(path, lang=None):
    """Whether a file is test code, by its folders and its name (see TEST_DIRS), in its language (see
    SPEC_LANGUAGES); lang is language_of(path) when not given."""
    parts = path.replace("\\", "/").split("/")
    if any(p.lower() in TEST_DIRS or TEST_DIR_CAMEL.search(p)
           or any(TEST_DIR_WORD.fullmatch(w) for w in re.split(r"[._\-]", p) if w) for p in parts[:-1]):
        return True
    name = parts[-1]
    words = [w for w in re.split(r"[_.\-]", name.split(".")[0]) if w]
    if CAMEL_TEST.search(name) or TEST_SUFFIX.search(name) or any(map(TEST_WORD.match, words)):
        return True
    return (lang or language_of(path)) in SPEC_LANGUAGES and bool(
        CAMEL_SPEC.search(name) or SPEC_SUFFIX.search(name) or any(map(SPEC_WORD.match, words)))


def line_hash(text):
    """A line's text with its whitespace collapsed, as a number that lasts only as long as this run."""
    return hash(" ".join(text.split()))


def limit():
    """How long a command may run: TIMEOUT, or less when the run's deadline is nearer (see time_left)."""
    try:
        left = time_left()
    except OutOfTime:
        raise OutOfTime("git was not started: the run is out of time") from None
    return TIMEOUT if left is None else min(TIMEOUT, left)


def git_lines(args, handle, feed=None, env=None):
    """Runs git and hands each line of its output to handle as it arrives, so an output of any size is never held
    whole. feed, if given, is written to git's input from another thread, so neither pipe can fill and stall.
    Fails as run() does, naming only the program, and like it ends git with everything git started (kill_tree)
    when its time is up, so nothing left behind can keep the output open past the limit."""
    seconds = limit()
    try:
        proc = spawn(args, stdin=subprocess.PIPE if feed is not None else subprocess.DEVNULL,
                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env)
    except OSError:
        raise RuntimeError("git could not be started") from None
    if feed is not None:
        def write():
            try:
                proc.stdin.write(feed)
            except OSError:
                pass
            finally:
                try:
                    proc.stdin.close()
                except OSError:
                    pass
        threading.Thread(target=write, daemon=True).start()
    timer = threading.Timer(seconds, kill_tree, (proc,))
    timer.start()
    try:
        handle(proc.stdout)
        while proc.stdout.read(1 << 16):   # anything handle left, so git is never stuck writing it
            pass
        proc.wait()   # git ends on its own once its output is read; the timer still bounds the wait
    finally:
        timer.cancel()
        timer.join()   # a kill already under way finishes before the job it ends is let go
        if proc.poll() is None:
            kill_tree(proc)
        proc.stdout.close()
        code = proc.wait()
        release(proc)
    if code != 0:
        raise RuntimeError("git exited %d, or ran past its %d seconds" % (code, seconds))


class CatFile:
    """git cat-file --batch kept open on one repository, for the file versions a reading needs whole: one reached
    only through a merge, or one no longer held (see Versions). Under the run's deadline like any git command, and
    like git_lines ended with everything it started (kill_tree) when its time is up."""

    def __init__(self, repo_dir):
        self.repo_dir, self.proc, self.timer, self.failed = repo_dir, None, None, False

    def get(self, blob):
        """blob's content, or None when git cannot give it."""
        got = self.ask(blob)
        return got[2] if got is not None and got[1] == b"blob" else None

    def ask(self, name):
        """(object name, type, content) of what name names, a blob's id or a commit's path (commit:path), or None
        when it names nothing or git cannot say. What git answers is always read whole, so the next answer lines up."""
        if self.failed or "\n" in name:
            return None
        try:
            if self.proc is None:
                seconds = limit()
                self.proc = spawn(["git", "-C", self.repo_dir, "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.timer = threading.Timer(seconds, kill_tree, (self.proc,))
                self.timer.daemon = True
                self.timer.start()
            self.proc.stdin.write(name.encode("utf-8", "surrogateescape") + b"\n")
            self.proc.stdin.flush()
            header = self.proc.stdout.readline().split()
            if len(header) < 2:
                self.failed = True
                return None
            if len(header) != 3 or not header[2].isdigit():   # missing, or ambiguous: nothing follows
                return None
            size = int(header[2])
            body = self.proc.stdout.read(size)
            self.proc.stdout.read(1)
            if len(body) != size:
                self.failed = True
                return None
            return header[0].decode("ascii", "replace"), header[1], body
        except (OSError, ValueError, RuntimeError):
            self.failed = True
            return None

    def close(self):
        if self.timer:
            self.timer.cancel()
            self.timer.join()   # a kill already under way finishes before the job it ends is let go
        if self.proc:
            for pipe in (self.proc.stdin, self.proc.stdout):
                try:
                    pipe.close()
                except OSError:
                    pass
            if self.proc.poll() is None:
                kill_tree(self.proc)
            self.proc.wait()
            release(self.proc)


class Version:
    """A file version's lines, as bytes, whether it ends with a newline, its readings by reader key: (kinds,
    states, whether exact), and, while its history is traced, each line's origin (see Trace), or None."""
    __slots__ = ("lines", "eol", "readings", "origins")

    def __init__(self, lines, eol):
        self.lines, self.eol, self.readings, self.origins = lines, eol, {}, None

    def text(self):
        """A function giving line i as text, decoded when asked, as git's diffs are read line by line."""
        lines = self.lines
        return lambda i: lines[i].decode("utf-8", "replace")


VERSION_LINES = 3000000   # the lines of file versions held at once while reading a repository's history


class Versions:
    """The file versions of one repository read so far, the least recently used let go once more than
    VERSION_LINES lines are held, and git to fetch any other whole (CatFile)."""

    def __init__(self, repo_dir):
        self.held, self.count, self.cat = {}, 0, CatFile(repo_dir)

    def get(self, blob):
        """The version blob names, held or fetched, or None when git cannot give it or it is binary."""
        version = self.held.pop(blob, None)
        if version is None:
            data = self.cat.get(blob)
            if data is None or b"\x00" in data[:8000]:
                return None
            version = Version(*split_lines(data, b"\n"))
            self.count += len(version.lines)
        self.held[blob] = version
        self.trim()
        return version

    def put(self, blob, version):
        old = self.held.pop(blob, None)
        self.count += len(version.lines) - (len(old.lines) if old else 0)
        self.held[blob] = version
        self.trim()

    def trim(self):
        while self.count > VERSION_LINES and len(self.held) > 1:
            blob = next(iter(self.held))
            self.count -= len(self.held.pop(blob).lines)


def reading_of(version, reader, key):
    """version's reading by reader (cached under key): (kinds, states, exact)."""
    got = version.readings.get(key)
    if got is None:
        got = version.readings[key] = read_lines(reader, version.text(), len(version.lines), version.eol)
    return got


def blob_id(lines, eol, like):
    """The git object name of a file of these lines, in the hash of the object name like (SHA-1 or SHA-256)."""
    data = b"\n".join(lines) + (b"\n" if eol else b"")
    # Match Git's object format; SHA-1 here is an object identifier, not a security signature.
    h = hashlib.sha256() if len(like) == 64 else hashlib.sha1()  # nosemgrep: python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1
    h.update(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def applied(old, hunks):
    """The file an old version and a diff's hunks make, as (lines, ends with a newline), and the edits in it
    [(old start, old end, new start, new end)], or None when the hunks do not fit the old version."""
    lines, edits, o = [], [], 0
    no_newline = None   # when the new file's last line is a hunk's, whether git said it has no newline
    for old_start, old_count, new_start, new_count, minus, plus, _, plus_no_newline in hunks:
        a = old_start - 1 if old_count else old_start
        if a < o or a + old_count > len(old.lines) or old.lines[a:a + old_count] != minus or len(plus) != new_count:
            return None
        lines.extend(old.lines[o:a])
        edits.append((a, a + old_count, len(lines), len(lines) + len(plus)))
        lines.extend(plus)
        o = a + old_count
        no_newline = plus_no_newline if plus and o >= len(old.lines) else None
    lines.extend(old.lines[o:])
    if not lines:
        eol = False
    elif o < len(old.lines):   # the last line is the old file's own last line
        eol = old.eol
    elif no_newline is not None:
        eol = not no_newline
    else:   # the old file's last lines gone: the new last line had a newline after it
        eol = True
    return lines, eol, edits


def line_edits(old_lines, new_lines, repo_dir=None):
    """The edits that make one list of lines another, as git would diff them: git diff --no-index on the two as
    files, or difflib where that cannot run."""
    if repo_dir is not None:
        folder = tempfile.mkdtemp(prefix="cp-")
        try:
            paths = []
            for name, lines in (("a", old_lines), ("b", new_lines)):
                paths.append(os.path.join(folder, name))
                with open(paths[-1], "wb") as f:
                    f.write("".join(line + "\n" for line in lines).encode("utf-8", "surrogatepass"))
            seconds = min(60, limit())
            # started and ended as run() starts and ends a command (spawn, kill_tree), but taking git's exit 1,
            # which says the two differ
            p = spawn(["git"] + READ_CONFIG + ["diff", "--no-index", "--no-color", "-U0", "--no-ext-diff",
                                               "--no-textconv", paths[0], paths[1]],
                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=read_env())
            try:
                out, _ = p.communicate(timeout=seconds)
            except BaseException:
                kill_tree(p)
                settle(p)
                raise
            finally:
                release(p)
            if p.returncode in (0, 1):
                edits = []
                for m in re.finditer(rb"(?m)^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", out):
                    a, b, c, d = (int(x) if x is not None else 1 for x in m.groups())
                    a0 = a - 1 if b else a
                    c0 = c - 1 if d else c
                    edits.append((a0, a0 + b, c0, c0 + d))
                return edits
        except (OSError, subprocess.SubprocessError, RuntimeError):
            pass
        finally:
            shutil.rmtree(folder, ignore_errors=True)
    edits = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes():
        if tag != "equal":
            edits.append((i1, i2, j1, j2))
    return edits


HUNK = re.compile(rb"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
LINKS = {"160000", "120000"}   # a submodule, and a symbolic link, whose blob is its target's path, not code
APPROXIMATE = "approximate"    # read_added_code's key for the lines each file version adds that rest on a fallback
GENERATED_VERSION = ((), ())   # what read_added_code holds for a version of a generated file (see generated_output)
# read_added_code's key, with a commit's hash, for the lines of code of every file the commit deletes. When git does
# not pair a deleted file with the file it became (past its rename limit, or edited past its similarity threshold, as
# a .js file rewritten as .ts is), those lines are what the commit moved (see moved_files).
DELETED = "deleted"
ALIKE = "alike"   # read_added_code's key for how alike each watched version's changed lines read (see sweep)
PAIRS = "pairs"   # and for the removed line each added line of a watched version takes the place of (see pair_lines)
# What a line is known to be (see Trace): an origin above 0 is the id of the line of code a file version's diff added,
# whose fate collect decides; UNKNOWN_ORIGIN, a line history cannot place (a version read with no version before it at
# hand, a merge's line neither parent holds); OTHER_ORIGIN, a line that is not one counted as written in the window.
# OWN_PRODUCTION and OWN_TEST appear only in what collect decides: a line counted as written in the window, in
# production or in test code.
UNKNOWN_ORIGIN, OTHER_ORIGIN, OWN_PRODUCTION, OWN_TEST = 0, -1, -3, -4
TRACE = None   # the Trace of the repository being read, set by collect around read_added_code and read_head_code
# A moved block: at least MOVED_BLOCK consecutive lines of code a commit adds, in one hunk, each of which a line of the
# same text the same commit removes (spacing aside) can account for. It is moved, not written, so a function moved
# within its file or into another adds nothing; a lone brace or return added beside a deletion is no block.
MOVED_BLOCK = 3


class Trace:
    """Where each line of one repository's file versions came from, read with its history (read_added_code) and looked
    up at its head (read_head_code), so that collect can tell whose each line standing there is by its history rather
    than by its text. Each line of code a version's diff adds gets an id of its own, from base[(commit, blob)] up in the
    order the version's added lines are listed (read_added_code's added[(commit, blob)][0]). Every other line keeps the
    origin it had in the version before, so a version's origins are its parent's with the diff applied: known once for
    a blob and kept with it (Version.origins), wherever that blob appears again. A version read with no version before
    it at hand knows only the lines it adds. gone[(commit, blob)] holds the origins of the lines of code the diff
    removed, as added[...][1] lists them, and gone[(commit, DELETED)] those of the files the commit deleted;
    bounds[(commit, blob)] where each hunk's added lines end, when there is more than one hunk; allocs every range of
    ids given out, as [its first id, (commit, blob)], the key None where a second reading of one key replaced it; heads
    the origins of the versions standing at the head, kept whatever else is let go; extra the origins of versions no
    Version holds (UTF-16 files); seeded the file versions other accounts wrote (see collect), which the head leaves
    out. broken is set when tracing met something it could not follow: the repository is then read as though it were
    not traced, every line at its head left to the backstop (see collect), and its diffs still count."""
    __slots__ = ("next", "base", "gone", "bounds", "allocs", "heads", "extra", "seeded", "broken")

    def __init__(self, start=1, seeded=()):
        self.next, self.base, self.gone, self.bounds, self.allocs = start, {}, {}, {}, []
        self.heads, self.extra, self.seeded, self.broken = {}, {}, seeded, False

    def known(self, blob, held=None):
        """The origins already known for blob, or None."""
        if held is not None and held.origins is not None:
            return held.origins
        got = self.heads.get(blob)
        return got if got is not None else self.extra.get(blob)

    def keep(self, blob, origins):
        """Keeps a head version's origins for read_head_code, the first time they are known."""
        if blob in self.heads and self.heads[blob] is None:
            self.heads[blob] = origins

    def allot(self, key, n):
        """The first of n new ids for the lines of code the version key adds."""
        first = self.next
        self.next += n
        was = self.base.get(key)
        if was is not None:   # the same key read twice (two paths, one content): the earlier ids name nothing now
            for a in self.allocs:
                if a[0] == was and a[1] == key:
                    a[1] = None
        self.base[key] = first
        self.allocs.append([first, key])
        return first


class Bank:
    """Lines of code by line_hash, each with its origin, each to be taken once: what a commit removed, what an earlier
    landing of one change wrote, what a branch wrote that the default branch has not taken yet."""
    __slots__ = ("lines",)

    def __init__(self):
        self.lines = {}

    def put(self, h, origin):
        q = self.lines.get(h)
        if q is None:
            q = self.lines[h] = deque()
        q.append(origin)

    def count(self, h):
        q = self.lines.get(h)
        return len(q) if q else 0

    def take(self, h):
        """The origin of one line of text h, taken, or None when none is left."""
        q = self.lines.get(h)
        return q.popleft() if q else None

    def __bool__(self):
        return any(self.lines.values())


def pair_lines(hunks):
    """For each line of code a version adds, in order, the index of the removed line of code whose place it takes, or
    -1: hunks is [(removed lines, added lines)], each line's text with its spacing collapsed. A line whose text is a
    removed line's, anywhere in the file, takes that one's place, as a line only re-indented does, or one moved when
    imports are sorted; the rest are paired in order within each hunk, as a renamed or re-quoted line is."""
    removed = [t for gone, _ in hunks for t in gone]
    came = [t for _, got in hunks for t in got]
    free = {}
    for i, t in enumerate(removed):
        free.setdefault(t, deque()).append(i)
    pair, used = array("l", [-1]) * len(came), bytearray(len(removed))
    for j, t in enumerate(came):
        q = free.get(t)
        if q:
            i = q.popleft()
            pair[j], used[i] = i, 1
    i0 = j0 = 0
    for gone, got in hunks:
        rest = [i for i in range(i0, i0 + len(gone)) if not used[i]]
        for i, j in zip(rest, [j for j in range(j0, j0 + len(got)) if pair[j] < 0]):
            pair[j], used[i] = i, 1
        i0, j0 = i0 + len(gone), j0 + len(got)
    return pair


# A Git LFS pointer: a file kept elsewhere, whose text in the repository is three lines naming it
LFS_SPECS = (b"https://git-lfs.github.com/spec/v1", b"https://hawser.github.com/spec/v1")
LFS_LINE = re.compile(rb"version https://(?:git-lfs|hawser)\.github\.com/spec/v1|oid sha256:[0-9a-f]{64}|size [0-9]+|"
                      rb"ext-[0-9]+-\S+ \S+")


def lfs_pointer(lines):
    """Whether a file version, as its lines (bytes), is a Git LFS pointer, as git-lfs itself decides: under 1,024
    bytes, a version line naming the pointer spec first, then key and value lines, an oid of sha256 and a size among
    them. Its lines name a file kept elsewhere; they are no code."""
    if not lines or not lines[0].startswith(b"version ") or sum(len(line) + 1 for line in lines) >= 1024:
        return False
    keys = {}
    for line in lines:
        m = re.fullmatch(rb"([a-z0-9.-]+) (\S.*)", line)
        if not m:
            return False
        keys[m.group(1)] = m.group(2)
    return (keys.get(b"version") in LFS_SPECS and keys.get(b"size", b"").isdigit()
            and re.fullmatch(rb"sha256:[0-9a-f]{64}", keys.get(b"oid", b"")) is not None)


GIT_VERSION = []


def git_version():
    """The installed git's version as a tuple of numbers, (0,) when it cannot be told."""
    if not GIT_VERSION:
        try:
            found = re.search(r"(\d+)\.(\d+)", run(["git", "version"], timeout=60).decode("ascii", "replace"))
            GIT_VERSION.append(tuple(int(x) for x in found.groups()) if found else (0,))
        except RuntimeError:
            return (0,)
    return GIT_VERSION[0]


def diff_path(text, prefix):
    """A path from a diff's ---/+++ label, unquoted (git_path), or None for /dev/null. git ends a label whose name
    holds a space with a tab, after the closing quote when there is one; prefix is the a/ or b/ the command gives."""
    if text.endswith("\t"):
        text = text[:-1]
    if text == "/dev/null":
        return None
    path = git_path(text)
    return path[len(prefix):] if path.startswith(prefix) else path


QUOTED = r'"(?:[^"\\]|\\.)*"'


def header_paths(text):
    """The old and new paths a "diff --git a/x b/y" line names, without their prefixes, or (None, None) where they
    cannot be told apart for certain: an unquoted name holding a space splits in more than one place, and is read only
    when both halves name the same file, as they do for every change but a rename or a copy, whose paths the rename
    and copy lines give exactly."""
    m = re.match(r"(%s) (.*)$" % QUOTED, text) or re.match(r"([^\"]*) (%s)$" % QUOTED, text)
    if m:
        a, b = git_path(m.group(1)), git_path(m.group(2))
    else:
        half = len(text) // 2
        a, b = text[:half], text[half + 1:]
        if len(text) % 2 == 0 or text[half:half + 1] != " " or a[2:] != b[2:]:
            return None, None
    if not (a.startswith("a/") and b.startswith("b/")):
        return None, None
    return a[2:], b[2:]


def read_added_code(repo_dir):
    """The lines of code each file version adds and removes, from its commit's diff with no context, so what a
    commit adds is exactly its added lines: {(commit, blob): (array of the added lines' line_hash, array of the
    removed lines')}. A comment or blank line is left out; so are files that are not code (counts_as_code), and
    every version of a file that any version shows to be generated (generated_output).

    Each line is read as the whole file version reads it, not as its diff alone would show it: the diff's hunks are
    applied to the version before (held from reading it, or fetched with cat-file), the result checked against the
    new version's object name, and the new version read from its reading of the old one (read_edited), so a line
    added inside a comment or string opened above its hunk reads as it does at the head. Where no version before
    can be had and the new one cannot be fetched either, each hunk is read alone and its lines are counted under
    APPROXIMATE ({(commit, blob): lines}), as are lines of a Python version its tokenizer could not read. A version
    git calls binary is read whole when its text can be decoded (UTF-16, as Windows tools save scripts), diffed
    line for line against the version before.

    A file a commit deletes has its lines of code pooled, as removed lines, under (commit, DELETED), so collect can
    tell a move git did not pair from new code (see moved_files). A Git LFS pointer holds no code (lfs_pointer). For
    each commit in SWEEP_WATCH, ALIKE holds how alike each version's changed lines read, {(commit, blob): share}
    (see sweep), and PAIRS which removed line each added line takes the place of (pair_lines). Paths are read exactly,
    whatever they hold (diff_path, header_paths).

    With TRACE set (see Trace), every version read also gets each line's origin: its parent's lines keep theirs, its
    added lines new ids, and a merge's lines, made from its first parent's version, the origin of the same text in the
    version its other parents hold at that path, or none."""
    added, where, marked, approximate, similar, paired = {}, {}, set(), {}, {}, {}
    added[APPROXIMATE], added[ALIKE], added[PAIRS] = approximate, similar, paired
    versions = Versions(repo_dir)
    watch = set(SWEEP_WATCH)
    state = {"sha": None, "merge": False, "parents": [], "file": None, "header": False, "hunk": None, "side": None}
    trace = TRACE
    if trace is not None:   # the versions at the head, whose origins are kept whatever else is let go
        try:
            listing = run(["git", "-C", repo_dir, "ls-tree", "-r", "-z", "--full-tree", "HEAD"])
        except OutOfTime:
            raise
        except RuntimeError:   # an empty repository, or a HEAD naming no branch: nothing stands there
            listing = b""
        for item in listing.split(b"\x00"):
            meta = item.partition(b"\t")[0].split()
            if len(meta) == 3 and meta[1] == b"blob":
                trace.heads.setdefault(meta[2].decode("ascii", "replace"), None)

    def paths(f):
        """The file's old and new paths, None where it has none (created, or deleted): from its ---/+++ labels, or,
        where it has none (a binary file), from its rename or copy lines and its diff --git line, and last from its
        Binary files line, where a name holding " and " could be misread."""
        if f["labels"]:
            return
        old, new = f["from"] or f["git_paths"][0], f["to"] or f["git_paths"][1]
        if (old is None or new is None) and f["binary_line"]:
            m = re.match(r"Binary files (.*) and (.*) differ$", f["binary_line"])
            if m:
                old, new = old or diff_path(m.group(1), "a/"), new or diff_path(m.group(2), "b/")
        f["old_path"] = None if f["created"] else old
        f["new_path"] = None if f["deleted"] else new

    def finish():
        f = state["file"]
        state["file"] = None
        if f is None:
            return
        paths(f)
        if f["mode"] in LINKS:
            return
        if not f["new_path"]:   # a file deleted: its lines are what the commit may have moved
            if f["old_path"] and f["old_blob"] and f["old_blob"].strip("0") and not state["merge"]:
                deleted(f)
            return
        if f["new_blob"] is None:
            return
        path = f["new_path"]
        lang = language_of(path)
        if not counts_as_code(path, lang):
            return
        if state["merge"]:
            hold(f, lang)
            return
        key = (state["sha"], f["new_blob"])
        got = version_lines(f, lang, [] if state["sha"] in watch else None)
        if got is None:
            return
        plus, minus, rough, head, pairs = got
        added[key] = (plus, minus)
        where[key] = path
        if rough:
            approximate[key] = rough
        if head:
            marked.add(path)
        if pairs is not None:
            share = alike_share(pairs)
            similar[key] = (0.0 if plus else 1.0) if share is None else share
            paired[key] = pair_lines(pairs)

    def carried(olds, n, edits):
        """The origins of a version of n lines that edits [(old start, old end, new start, new end)] made from a version
        whose lines' origins are olds (None where unknown): each line outside the edits keeps its old line's origin,
        and each line inside them is UNKNOWN_ORIGIN until the caller says otherwise."""
        origin = array("q", bytes(8 * n))
        if olds is None:
            return origin
        o = m = 0
        for a, b, c, d in edits:
            if c - m != a - o or a < o:
                return array("q", bytes(8 * n))   # edits that do not fit the old version: nothing is known
            origin[m:c] = olds[o:a]
            o, m = b, d
        if n - m != len(olds) - o:
            return array("q", bytes(8 * n))
        origin[m:n] = olds[o:]
        return origin

    def traced(f, n, olds, edits, came_at, other_at, kept_at, gone_at, n_minus, bounds, have=None, extra=False):
        """Records the origins of a version read (see Trace): olds, the version before's (None where unknown); edits,
        what made one from the other (empty where the version was read whole); came_at, the new places of the lines
        of code it adds, in order, which take new ids; other_at, of the other lines it adds; kept_at, [(new place, old
        place)] of lines a hunk lists but keeps; gone_at, the old places of the lines of code it removes (None where
        unknown, n_minus of them). extra: the version is one no Version holds (UTF-16). Returns the version's
        origins."""
        key = (state["sha"], f["new_blob"])
        origin = carried(olds, n, edits)
        first = trace.allot(key, len(came_at)) if came_at else 0
        for j, i in enumerate(came_at):
            origin[i] = first + j
        for i in other_at:
            origin[i] = OTHER_ORIGIN
        for i, k in kept_at:
            origin[i] = olds[k] if olds is not None else UNKNOWN_ORIGIN
        if n_minus:
            trace.gone[key] = (array("q", (olds[k] for k in gone_at)) if olds is not None and gone_at is not None
                               else array("q", bytes(8 * n_minus)))
        if len(bounds) > 1:
            trace.bounds[key] = bounds
        known = trace.known(f["new_blob"], have)
        if known is None and len(origin) == n:
            known = origin
            if extra:
                trace.extra[f["new_blob"]] = origin
        if known is not None:
            trace.keep(f["new_blob"], known)
        return known

    def deleted(f):
        """A deleted file's lines of code, added to its commit's (commit, DELETED): read from the whole version where
        it can be had, and from the diff's own lines otherwise; with their origins, where traced."""
        path = f["old_path"]
        lang = language_of(path)
        if not counts_as_code(path, lang):
            return
        reader, rkey = reader_for(lang, path)
        old = None if f["binary"] else versions.get(f["old_blob"])
        texts, olds, at = [], None, []
        if old is not None:
            if not lfs_pointer(old.lines):
                kinds, get = reading_of(old, reader, rkey)[0], old.text()
                at = [i for i in range(len(old.lines)) if kinds[i] == CODE]
                texts = [get(i) for i in at]
                olds = old.origins if old.origins is not None and len(old.origins) == len(old.lines) else None
        else:
            data = versions.cat.get(f["old_blob"])
            text = text_of(data) if data is not None else None
            if text is not None:   # decoded whole (UTF-16), unless it is a pointer
                if not (data.startswith(b"version ") and lfs_pointer(split_lines(data, b"\n")[0])):
                    lines, eol = split_lines(text, "\n")
                    kinds = read_lines(reader, lines.__getitem__, len(lines), eol)[0]
                    at = [i for i in range(len(lines)) if kinds[i] == CODE]
                    texts = [lines[i] for i in at]
                    olds = trace.extra.get(f["old_blob"]) if trace is not None else None
                    olds = olds if olds is not None and len(olds) == len(lines) else None
            elif not f["binary"] and not all(LFS_LINE.fullmatch(line) for h in f["hunks"] for line in h[4]):
                rd = reader.fallback or reader
                st = rd.initial
                for h in f["hunks"]:
                    for line in h[4]:
                        t = line.decode("utf-8", "replace")
                        kind, st = rd.read(t, st)
                        if kind == CODE:
                            texts.append(t)
        pooled = added.setdefault((state["sha"], DELETED), (array("q"), array("q")))
        pooled[1].extend(line_hash(t) for t in texts)
        if trace is not None and not trace.broken:
            gone = trace.gone.setdefault((state["sha"], DELETED), array("q"))
            if olds is not None:
                gone.extend(olds[i] for i in at)
            else:
                gone.extend(array("q", bytes(8 * len(texts))))

    def hold(f, lang):
        """A merge's version of a file, made from its first parent's as a commit's is, so a commit after the merge
        finds it at hand; a merge adds no lines of its own (its branch's were counted where they were written).
        Only a version the merge made from one at hand is kept: any other is fetched if a later commit needs it. While
        traced, its origins are its first parent's lines' and, for the lines it brings in, the origins of the same
        text in the version its other parents hold at that path (merged); a version whose origins are known is kept
        for them whether or not its reading could be made from its first parent's."""
        reader, rkey = reader_for(lang, f["new_path"])
        if f["binary"]:
            return
        have = versions.held.get(f["new_blob"])
        wanted = trace is not None and not trace.broken and trace.known(f["new_blob"], have) is None
        if have is not None and rkey in have.readings and not wanted:
            return
        old = versions.held.get(f["old_blob"]) if f["old_blob"] and f["old_blob"].strip("0") else None
        made = applied(old, f["hunks"]) if old is not None else None
        if made is None or blob_id(made[0], made[1], f["new_blob"]) != f["new_blob"]:
            return
        new = have if have is not None else Version(made[0], made[1])
        base = old.readings.get(rkey)
        if rkey not in new.readings and base is not None and base[2]:
            try:
                new.readings[rkey] = read_edited(reader, base[:2], new.text(), len(new.lines), new.eol,
                                                 made[2]) + (True,)
            except ReadFailed:
                pass
        if wanted:
            try:
                new.origins = merged(f, old, made)
                trace.keep(f["new_blob"], new.origins)
            except Exception:   # what tracing cannot follow leaves the head to the backstop, and the diffs still count
                trace.broken = True
        if rkey not in new.readings and new.origins is None:
            return
        versions.put(f["new_blob"], new)

    def merged(f, old, made):
        """The origins of a merge's version of a file, made from its first parent's (old) by made: the first parent's
        lines keep theirs, and each line the merge brings in takes the origin of a line of the same text, spacing
        aside, in the version another parent holds at that path, or none (a line of the merge's own, as a conflict's
        resolution is, or one from a version whose origins are not known)."""
        lines, _, edits = made
        olds = old.origins if old.origins is not None and len(old.origins) == len(old.lines) else None
        origin = carried(olds, len(lines), edits)
        theirs = Bank()
        for p in state["parents"][1:]:
            got = versions.cat.ask("%s:%s" % (p, f["new_path"]))
            if got is None or got[1] != b"blob":
                continue
            known = trace.known(got[0], versions.held.get(got[0]))
            other = split_lines(got[2], b"\n")[0]
            if known is None or len(known) != len(other):
                continue
            for line, o in zip(other, known):
                theirs.put(line_hash(line.decode("utf-8", "replace")), o)
        for a, b, c, d in edits:
            for i in range(c, d):
                o = theirs.take(line_hash(lines[i].decode("utf-8", "replace")))
                origin[i] = UNKNOWN_ORIGIN if o is None else o
        return origin

    def version_lines(f, lang, pairs):
        """(added lines' hashes, removed lines', how many added lines rest on a fallback, whether generated, and, when
        pairs is a list, each hunk's removed and added lines of code with their spacing collapsed, for sweep). While
        traced, the version's origins are recorded too (traced)."""
        reader, rkey = reader_for(lang, f["new_path"])
        old_path = f["old_path"] or f["new_path"]
        old_lang = language_of(old_path) or lang
        old_reader, okey = reader_for(old_lang, old_path) if old_path != f["new_path"] else (reader, rkey)
        blank_old = not f["old_blob"] or not f["old_blob"].strip("0")
        if f["binary"]:
            return binary_lines(f, lang, reader, rkey, old_reader, okey, blank_old, pairs)
        have = versions.held.get(f["new_blob"])
        old = Version([], False) if blank_old else versions.get(f["old_blob"])
        made = applied(old, f["hunks"]) if old is not None else None
        if made is not None and blob_id(made[0], made[1], f["new_blob"]) != f["new_blob"]:
            made = None
        if made is None:
            data = versions.cat.get(f["new_blob"])
            if data is None or b"\x00" in data[:8000]:
                return hunk_lines(f, reader, old_reader, pairs)
            new = Version(*split_lines(data, b"\n"))
            edits = None
        else:
            new, edits = Version(made[0], made[1]), made[2]
        get, n = new.text(), len(new.lines)
        if edits is not None:
            base = old.readings.get(rkey) or reading_of(old, reader, rkey)
            if base[2]:   # read from the old version's reading, where that was the exact reader's
                try:
                    kinds, states = read_edited(reader, base[:2], get, n, new.eol, edits)
                    new.readings[rkey] = (kinds, states, True)
                except ReadFailed:
                    pass
        kinds, _, exact = reading_of(new, reader, rkey)
        versions.put(f["new_blob"], new)
        # a Git LFS pointer, old or new, adds and removes no line of code
        new_pointer = lfs_pointer(new.lines)
        old_pointer = (lfs_pointer(old.lines) if old is not None
                       else any(h[4] for h in f["hunks"]) and all(LFS_LINE.fullmatch(line)
                                                                  for h in f["hunks"] for line in h[4]))
        plus, minus, rough = array("q"), array("q"), 0
        old_kinds = old_get = None
        track = trace is not None and not trace.broken
        came_at, other_at, kept_at, gone_at, bounds = [], [], [], [], array("l")
        for h, (a, b, c, d) in zip(f["hunks"], edits or ()):
            first, came, gone = c, [], []
            if h[6] and h[4] and h[5] and h[5][0].rstrip(b"\r") == h[4][-1].rstrip(b"\r"):
                first, b = c + 1, b - 1   # the old last line only gained its line end: not removed, not written
                kept_at.append((c, b))
            for i in range(first, d if not new_pointer else first):
                if kinds[i] == CODE:
                    came.append(get(i))
                    rough += not exact
                    if track:
                        came_at.append(i)
                elif track:
                    other_at.append(i)
            if b > a and not old_pointer:
                if old_kinds is None:
                    old_get, old_kinds = old.text(), reading_of(old, old_reader, okey)[0]
                at = [i for i in range(a, b) if old_kinds[i] == CODE]
                gone = [old_get(i) for i in at]
                if track:
                    gone_at.extend(at)
            plus.extend(line_hash(t) for t in came)
            minus.extend(line_hash(t) for t in gone)
            bounds.append(len(plus))
            if pairs is not None:
                pairs.append(([" ".join(t.split()) for t in gone], [" ".join(t.split()) for t in came]))
        if edits is None:   # the new version read whole, as fetched: its added lines are the hunks' own
            gone_at = None   # and what it removed cannot be placed in a version before
            for old_start, old_count, new_start, new_count, gone_lines, _, _, _ in f["hunks"]:
                came, gone = [], []
                c = new_start - 1 if new_count else new_start
                for i in range(c, min(c + new_count, n) if not new_pointer else c):
                    if kinds[i] == CODE:
                        came.append(get(i))
                        rough += not exact
                        if track:
                            came_at.append(i)
                    elif track:
                        other_at.append(i)
                reader_old = old_reader.fallback or old_reader
                st = reader_old.initial if old_start <= 1 else reader_old.middle
                for line in gone_lines if not old_pointer else ():
                    text = line.decode("utf-8", "replace")
                    kind, st = reader_old.read(text, st)
                    if kind == CODE:
                        gone.append(text)
                plus.extend(line_hash(t) for t in came)
                minus.extend(line_hash(t) for t in gone)
                bounds.append(len(plus))
                if pairs is not None:
                    pairs.append(([" ".join(t.split()) for t in gone], [" ".join(t.split()) for t in came]))
        if track:
            olds = None
            if edits is not None:
                olds = array("q") if blank_old else old.origins
                if olds is not None and len(olds) != len(old.lines):
                    olds = None
            try:
                new.origins = traced(f, n, olds, edits or (), came_at, other_at, kept_at, gone_at, len(minus),
                                     bounds, have)
            except Exception:   # what tracing cannot follow leaves the head to the backstop, and the diffs still count
                trace.broken = True
        # a version's first lines are read for a generator's mark unless they are the version before's, at its path
        fresh_head = edits is None or blank_old or old_path != f["new_path"] or any(c < GEN_HTML_LINES
                                                                                    for a, b, c, d in edits)
        return plus, minus, rough, fresh_head and generated_head(get, n, lang), pairs

    def hunk_lines(f, reader, old_reader, pairs):
        """Each hunk read alone, from where a file starts when the hunk does and from plain code otherwise: the
        approximation when no whole version can be had. A side whose every line is a Git LFS pointer's is none."""
        plus, minus, rough, head = array("q"), array("q"), 0, False
        lang = language_of(f["new_path"])
        pointer = [all(LFS_LINE.fullmatch(line) for h in f["hunks"] for line in h[k]) for k in (4, 5)]
        for old_start, old_count, new_start, new_count, gone, came, _, _ in f["hunks"]:
            texts = ([], [])   # removed, added
            for lines, start, side, rd in ((came, new_start, 1, reader), (gone, old_start, 0, old_reader)):
                rd = rd.fallback or rd
                st = rd.initial if start <= 1 else rd.middle
                for n, line in enumerate(lines if not pointer[side] else (), start):
                    text = line.decode("utf-8", "replace")
                    kind, st = rd.read(text, st)
                    if kind == CODE:
                        texts[side].append(text)
                    if side and n <= GEN_HTML_LINES and generated_line(text, lang, n):
                        head = True
            plus.extend(line_hash(t) for t in texts[1])
            minus.extend(line_hash(t) for t in texts[0])
            rough += len(texts[1])
            if pairs is not None:
                pairs.append(tuple([" ".join(t.split()) for t in side] for side in texts))
        return plus, minus, rough, head, pairs

    def binary_lines(f, lang, reader, rkey, old_reader, okey, blank_old, pairs):
        """A version git calls binary, read as text when it decodes as text (text_of)."""
        data = versions.cat.get(f["new_blob"])
        new_text = text_of(data) if data is not None else None
        if new_text is None:
            return None
        old_data = b"" if blank_old else versions.cat.get(f["old_blob"])
        old_text = (text_of(old_data) if old_data is not None else None) or ""
        new_lines, new_eol = split_lines(new_text, "\n") if new_text else ([], False)
        old_lines, old_eol = split_lines(old_text, "\n") if old_text else ([], False)
        kinds, _, exact = read_lines(reader, new_lines.__getitem__, len(new_lines), new_eol)
        old_kinds = read_lines(old_reader, old_lines.__getitem__, len(old_lines), old_eol)[0] if old_lines else b""
        plus, minus, rough = array("q"), array("q"), 0
        edits = line_edits(old_lines, new_lines, repo_dir)
        came_at, other_at, gone_at, bounds = [], [], [], array("l")
        for a, b, c, d in edits:
            got = [i for i in range(c, d) if kinds[i] == CODE]
            at = [i for i in range(a, b) if old_kinds[i] == CODE]
            came, gone = [new_lines[i] for i in got], [old_lines[i] for i in at]
            came_at.extend(got)
            other_at.extend(i for i in range(c, d) if kinds[i] != CODE)
            gone_at.extend(at)
            plus.extend(line_hash(t) for t in came)
            minus.extend(line_hash(t) for t in gone)
            bounds.append(len(plus))
            rough += 0 if exact else len(came)
            if pairs is not None:
                pairs.append(([" ".join(t.split()) for t in gone], [" ".join(t.split()) for t in came]))
        if trace is not None and not trace.broken:
            olds = array("q") if blank_old else trace.known(f["old_blob"])
            if old_data is None or olds is not None and len(olds) != len(old_lines):
                olds = None
            try:
                traced(f, len(new_lines), olds, edits, came_at, other_at, [], gone_at, len(minus), bounds,
                       extra=True)
            except Exception:   # what tracing cannot follow leaves the head to the backstop, and the diffs still count
                trace.broken = True
        return plus, minus, rough, generated_head(new_lines.__getitem__, len(new_lines), lang), pairs

    def handle(stream):
        s = state
        for raw in stream:
            if raw.startswith(b"\x00"):
                finish()
                ids = raw[1:].decode("ascii", "replace").split()   # the commit, then its parents
                s.update(sha=ids[0] if ids else None, merge=len(ids) > 2, parents=ids[1:], header=False)
                continue
            if raw.startswith(b"diff --git "):
                finish()
                s.update(header=True, hunk=None, side=None,
                         file={"old_blob": None, "new_blob": None, "old_path": None, "new_path": None, "mode": None,
                               "binary": False, "hunks": [], "labels": False, "created": False, "deleted": False,
                               "from": None, "to": None, "binary_line": None,
                               "git_paths": header_paths(raw[11:].decode("utf-8", "replace").rstrip("\n"))})
                continue
            f = s["file"]
            if f is None:
                continue
            if s["header"]:
                if raw.startswith(b"@@"):
                    s["header"] = False
                else:
                    line = raw.decode("utf-8", "replace").rstrip("\n")
                    if line.startswith("index "):
                        fields = line[6:].split(" ")
                        ids = fields[0].split("..")
                        if len(ids) == 2 and all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", x) for x in ids):
                            f["old_blob"], f["new_blob"] = ids
                        if len(fields) > 1:
                            f["mode"] = fields[1]
                    elif line.startswith(("new file mode ", "new mode ", "deleted file mode ")):
                        f["mode"] = line.split()[-1]
                        f["created"] = f["created"] or line.startswith("new file")
                        f["deleted"] = f["deleted"] or line.startswith("deleted")
                    elif line.startswith(("rename from ", "copy from ")):
                        f["from"] = git_path(line.split(" ", 2)[2])
                    elif line.startswith(("rename to ", "copy to ")):
                        f["to"] = git_path(line.split(" ", 2)[2])
                    elif line.startswith("--- "):
                        f["old_path"], f["labels"] = diff_path(line[4:], "a/"), True
                    elif line.startswith("+++ "):
                        f["new_path"], f["labels"] = diff_path(line[4:], "b/"), True
                    elif line.startswith("Binary files "):
                        f["binary"], f["binary_line"] = True, line
                    continue
            if raw.startswith(b"@@"):
                m = HUNK.match(raw)
                if m:
                    a, b, c, d = (int(x) if x is not None else 1 for x in m.groups())
                    s["hunk"] = [a, b, c, d, [], [], False, False]
                    f["hunks"].append(s["hunk"])
                s["side"] = None
            elif s["hunk"] is not None:
                body = raw[1:-1] if raw.endswith(b"\n") else raw[1:]
                if raw.startswith(b"+"):
                    s["hunk"][5].append(body)
                    s["side"] = 7
                elif raw.startswith(b"-"):
                    s["hunk"][4].append(body)
                    s["side"] = 6
                elif raw.startswith(b"\\") and s["side"]:   # "\ No newline at end of file", of the line before it
                    s["hunk"][s["side"]] = True
        finish()

    # --no-textconv: a text conversion (Git for Windows ships one for PDF and Word files) starts a program for
    # every version of every such file, and what it prints is not what the file holds. --reverse --topo-order:
    # every version is read after the one before it, so its reading is at hand. Merges come with their diffs from
    # their first parents (git 2.31 and later), only to make their versions (see hold); an older git leaves them out.
    merges = ["--diff-merges=first-parent"] if git_version() >= (2, 31) else ["--no-merges"]
    try:
        git_lines(["git", "-C", repo_dir] + READ_CONFIG + ["log", "--exclude=refs/heads/gh-pages", "--all"]
                  + merges + ["--reverse", "--topo-order", "-M", "-p", "-U0", "--full-index", "--no-color",
                              "--no-ext-diff", "--no-textconv", "--src-prefix=a/", "--dst-prefix=b/",
                              "--format=%x00%H %P"], handle, env=read_env())
    finally:
        versions.cat.close()
    if marked:
        output = generated_output(set(where.values()), marked)
        for key, path in where.items():
            if path in output:
                added[key] = GENERATED_VERSION
                approximate.pop(key, None)
    return added


LINGUIST = ("linguist-vendored", "linguist-generated", "linguist-documentation")


def attributed(repo_dir, source, paths):
    """The paths among paths that the .gitattributes files of the commit source mark linguist-vendored,
    linguist-generated or linguist-documentation: the owner's own word, which GitHub's language bar also takes, on
    what is not code they wrote (a path marked false stays counted). None when git cannot say: check-attr's --source
    needs git 2.40."""
    paths = sorted(p for p in paths if p)
    if not paths:
        return set()
    found = set()

    def handle(stream):
        items = stream.read().split(b"\x00")
        for k in range(0, len(items) - 2, 3):
            if items[k + 2] in (b"set", b"true"):
                found.add(items[k].decode("utf-8", "replace"))

    try:
        git_lines(["git", "-C", repo_dir] + READ_CONFIG + ["check-attr", "--source=" + source, "-z", "--stdin"]
                  + list(LINGUIST), handle, feed="".join(p + "\x00" for p in paths).encode("utf-8", "surrogateescape"),
                  env=read_env())
    except RuntimeError:
        return None
    return found


def attributed_versions(repo_dir, commits):
    """The file versions of commits that the repository's .gitattributes files mark as not the owner's code (see
    attributed), each judged by the attributes its own commit held: {(commit, path)}, or None when git cannot say.
    A commit holds the attributes of the last commit before it, along its first parents, that changed a .gitattributes
    file; commits of a repository whose .gitattributes never mention linguist attributes are read no further."""
    try:
        blobs = run(["git", "-C", repo_dir] + READ_CONFIG + ["log", "--all", "--format=", "--raw", "--no-renames",
                                                             "--no-abbrev", "--", ":(glob)**/.gitattributes"],
                    timeout=limit(), env=read_env()).decode("utf-8", "replace")
    except RuntimeError:
        return None
    ids = sorted({line.split()[3] for line in blobs.split("\n") if line.startswith(":") and len(line.split()) > 4}
                 - {"0" * 40, "0" * 64})
    if not ids:
        return set()
    mentioned = [False]

    def look(stream):
        body = stream.read()
        mentioned[0] = b"linguist-" in body

    try:
        git_lines(["git", "-C", repo_dir, "cat-file", "--batch"], look, feed="".join(i + "\n" for i in ids).encode())
        if not mentioned[0]:
            return set()
        listing = run(["git", "-C", repo_dir, "rev-list", "--all", "--topo-order", "--reverse", "--parents"],
                      timeout=limit()).decode("ascii", "replace").split("\n")
        feed = "".join(line.split()[0] + (" " + line.split()[1] if len(line.split()) > 1 else "") + "\n"
                       for line in listing if line.strip())
        changed = set()

        def touched(stream):
            for raw in stream:
                text = raw.decode("utf-8", "replace").strip()
                if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", text):
                    changed.add(text)

        git_lines(["git", "-C", repo_dir] + READ_CONFIG + ["diff-tree", "--stdin", "--root", "-r", "--name-only", "--",
                                                          ":(glob)**/.gitattributes"], touched, feed=feed.encode(),
                  env=read_env())
    except RuntimeError:
        return None
    source = {}
    for line in listing:
        parts = line.split()
        if parts:
            source[parts[0]] = parts[0] if parts[0] in changed else source.get(parts[1]) if len(parts) > 1 else None
    wanted = {}
    for c in commits:
        s = source.get(c.sha)
        if s:
            wanted.setdefault(s, set()).update(f.path for f in c.files)
    marked = set()
    by_source = {}
    for s, paths in wanted.items():
        got = attributed(repo_dir, s, paths)
        if got is None:
            return None
        by_source[s] = got
    for c in commits:
        got = by_source.get(source.get(c.sha))
        if got:
            marked.update((c.sha, f.path) for f in c.files if f.path in got)
    return marked


class Standing:
    """The lines of code standing at a head, one entry a line in the order they were read, a few bytes a line where a
    Counter of (line_hash, test) held a tuple and an entry for each: hashes, each line's line_hash; tests, 1 where it
    is test code; rough, 1 where a fallback read it (a Python file its tokenizer could not read, a Rust file whose
    test scopes could not be read); origins, each line's origin as its history gives it (see Trace), UNKNOWN_ORIGIN
    where it gives none; files, (path, first line, end) for each file's lines. unattributed is True when
    .gitattributes could not be read. items() gives the lines as a Counter of (line_hash, whether test code) would."""
    __slots__ = ("hashes", "tests", "rough", "origins", "files", "unattributed")

    def __init__(self):
        self.hashes, self.tests, self.rough, self.unattributed = array("q"), bytearray(), bytearray(), False
        self.origins, self.files = array("q"), []

    def __len__(self):
        return len(self.hashes)

    def add(self, rows, rough, origins=None, path=None):
        """rows: (line_hash, whether test code) for each line; rough: whether a fallback read them; origins: each
        one's origin, or None where none is known; path: the file they stand in."""
        start = len(self.hashes)
        for h, t in rows:
            self.hashes.append(h)
            self.tests.append(1 if t else 0)
        self.rough.extend(bytes([1 if rough else 0]) * len(rows))
        self.origins.extend(origins if origins is not None and len(origins) == len(rows)
                            else array("q", bytes(8 * len(rows))))
        if path is not None:
            self.files.append((path, start, len(self.hashes)))

    def items(self):
        return Counter(zip(self.hashes, map(bool, self.tests))).items()


def read_head_code(repo_dir):
    """The lines of code on the default branch as it stands, read whole file by whole file with the readers the
    history is read with, so a line reads alike in both (see Standing). Rust code compiled only in tests counts as
    test code, wherever its file is: inline (rust_lines), or in the file of a module declared so out of line
    (rust_test_files, with the crate roots the repository's Cargo.toml files name). Left out: what counts_as_code
    leaves out, symbolic links and submodules, Git LFS pointers, generated files (generated_output), and the paths the
    default branch's .gitattributes marks (attributed). An empty repository, or one whose HEAD names no branch, has
    nothing standing at its head; a head that cannot be read for any other reason raises RuntimeError.

    With TRACE set (see Trace), each line of code carries the origin its history gave its file version, and a file
    version another account wrote (TRACE.seeded: a template's, or coderprint's own in a relay copy) is left out
    whole, as it is not the owner's."""
    head, trace = Standing(), TRACE
    try:
        run(["git", "-C", repo_dir, "rev-parse", "--quiet", "--verify", "HEAD^{tree}"])
    except RuntimeError as e:
        if "exited" not in str(e):   # out of time, or git could not start: the head is unknown, not missing
            raise
        return head
    listing = run(["git", "-C", repo_dir, "ls-tree", "-r", "-z", "--full-tree", "HEAD"]).decode("utf-8", "replace")
    files, manifests = [], []
    seeded = trace.seeded if trace is not None else ()
    known_at = trace.heads if trace is not None and not trace.broken else {}   # each head version's origins
    for item in listing.split("\x00"):
        meta, _, path = item.partition("\t")
        fields = meta.split()
        blob = len(fields) == 3 and fields[1] == "blob" and fields[0] not in LINKS
        lang = language_of(path) if blob else None
        if counts_as_code(path, lang):
            files.append((fields[2], path, lang))
        elif blob and path.rpartition("/")[2] == "Cargo.toml":
            manifests.append((fields[2], path))
    if not files:
        return head
    skip = attributed(repo_dir, "HEAD", {p for _, p, _ in files})
    if skip is None:
        head.unattributed, skip = True, set()
    files = [f for f in files if f[1] not in skip]
    if not any(lang == "Rust" for _, _, lang in files):
        manifests = []
    web, marked = {}, set()   # each HTML, CSS and JavaScript file's lines, kept until the sites are known
    rust, declared, roots = {}, [], set()   # each Rust file's test flag and place in head; see rust_test_files

    def handle(stream):
        for blob, path, lang in files:
            header = stream.readline().split()
            if len(header) < 3:
                continue
            body = stream.read(int(header[2]))
            stream.read(1)
            text = text_of(body)
            if text is None or body.startswith(b"version ") and lfs_pointer(split_lines(body, b"\n")[0]):
                continue
            # lines end at \n alone, as in the diffs read_added_code reads, so a line holding a form feed or U+2028
            # is one line in both and its text matches (splitlines would cut it in two)
            lines, eol = split_lines(text, "\n")
            if generated_head(lines.__getitem__, len(lines), lang):
                marked.add(path)
                continue
            if blob in seeded:   # another account's file version: none of its lines are the owner's
                continue
            test = is_test(path, lang)
            reader = reader_for(lang, path)[0]
            rows = None
            if lang == "Rust":
                known = len(declared)
                try:
                    kinds, rows = rust_lines(reader, lines, path, test, declared)
                    exact = reader.exact
                except Exception:   # a reading of scopes that went wrong: the file whole, by its path alone
                    del declared[known:]
                    rows = None
            if rows is None:
                kinds, _, exact = read_lines(reader, lines.__getitem__, len(lines), eol)
                rows = [(line_hash(t), test) for t, kind in zip(lines, kinds) if kind == CODE]
                exact = exact and lang != "Rust"
            known = known_at.get(blob)
            if known is not None and len(known) == len(lines):   # each line of code's origin, from its history
                origins = array("q", (known[i] for i, kind in enumerate(kinds) if kind == CODE))
            else:
                origins = None
            if lang in WEB_OUTPUT:
                web[path] = (rows, not exact, origins)
                continue
            start = len(head)
            head.add(rows, not exact, origins, path)
            if lang == "Rust":
                rust[path] = (test, start, len(head))
        for blob, path in manifests:
            header = stream.readline().split()
            if len(header) < 3:
                continue
            body = stream.read(int(header[2]))
            stream.read(1)
            roots.update(cargo_roots(path, body))

    git_lines(["git", "-C", repo_dir, "cat-file", "--batch"], handle,
              feed="".join(blob + "\n" for blob in [f[0] for f in files] + [m[0] for m in manifests]).encode())
    output = generated_output(set(web), marked) if marked else set()
    for path, (rows, rough, origins) in web.items():
        if path not in output:
            head.add(rows, rough, origins, path)
    for path in rust_test_files({p: t for p, (t, _, _) in rust.items()}, declared, roots):
        _, start, end = rust[path]   # a module compiled only in tests: its production lines are test code
        head.tests[start:end] = b"\x01" * (end - start)
    return head


# Rust: an attribute's start; a cfg attribute, outer or inner (#!); a #[path] naming a module's file; a module,
# declared out of line (mod name;) or inline, its body in braces; an item's first word after its visibility, and
# the words that start an item a comma cannot end (a where clause's or a generic list's commas are its own), where
# anything else under an attribute (a field, a variant, a match arm, an argument) ends at a comma of its own level.
RUST_ATTR = re.compile(r"#\s*!?\s*\[")
RUST_CFG = re.compile(r"#\s*(!?)\s*\[\s*cfg\s*\((.*)\)\s*\]", re.S)
RUST_PATH = re.compile(r'#\s*\[\s*path\s*=\s*"([^"]*)"\s*\]')
RUST_MOD = re.compile(r"(?:pub(?:\s*\([^)]*\))?\s+)?(?:unsafe\s+)?mod\s+(?:r#)?(\w+)\s*(;|\{|$)")
RUST_ITEM = re.compile(r"(?:pub(?:\s*\([^)]*\))?\s+|crate\s+)?(\w+)")
RUST_ITEMS = {"fn", "struct", "enum", "union", "impl", "trait", "mod", "use", "type", "const", "static", "extern",
              "unsafe", "async", "macro_rules", "let", "auto", "default", "safe"}
# A crate root, by Cargo's own layout: its submodules' files sit beside it (see rust_test_files)
RUST_ROOT_NAMES, RUST_ROOT_DIRS = ("lib.rs", "main.rs", "build.rs"), ("bin", "examples", "tests", "benches")
CARGO_TARGETS = {"lib", "bin", "example", "test", "bench"}


def rust_lines(reader, lines, path, test, declared):
    """A Rust file read with its reader (see Lines): (kinds, one byte a line; each line of code as [line_hash,
    whether it is test code]). A line is test code when the whole file is (test, by its path), or inside what is
    compiled only in tests (cfg_test): an item under an outer attribute such as #[cfg(test)] or #[cfg(all(test,
    unix))], from its first attribute to its end (its braces closed, a semicolon, or, for a field, a variant or a
    match arm, a comma of its own level), or everything of the module an inner #![cfg(test)] opens, the whole file
    at its top. Brackets and semicolons are read in each line's code alone, outside its strings, characters and
    comments. Each module declared out of line (mod name;) is added to declared as (path, the folders of the inline
    modules around it, its name, the file its #[path] gives or None, whether it is compiled only in tests)."""
    kinds, rows = bytearray(), []
    state = reader.initial
    level = 0         # brackets of every kind open before the line
    scope = None      # the test scope open: [the level it ends at, whether a comma of that level ends it]
    pending = None    # an attribute still open at a line's end: its text so far
    attrs, raw, first, at = [], [], 0, 0   # the attributes read for the item to come, their lines, first row, level
    inline = []       # the inline modules around: [folder, level of the body, entered, first row, line of the header]
    for n, text in enumerate(lines):
        bare = []
        kind, state = reader.read(text, state, bare)
        kinds.append(kind)
        code = "".join(bare)
        s = rest = code.strip()
        row = len(rows)
        if kind == CODE:
            rows.append([line_hash(text), test])
        if scope is not None and s and s[0] in ")]}" and level <= scope[0]:
            scope = None   # what held the item closes here, so the item ended before
        if pending is not None or RUST_ATTR.match(s):
            if pending is None and not attrs:
                first, at = row, level
            joined = s if pending is None else pending + " " + s
            raw.append(text)
            found = rust_attributes(joined)
            rest, pending = "", None
            if found is None:
                if len(joined) < 4000:   # read on, but not for ever
                    pending = joined
                else:
                    attrs, raw = [], []
            else:
                got, rest = found
                for a in got:
                    m = RUST_CFG.fullmatch(a)
                    if not re.match(r"#\s*!", a):
                        attrs.append(a)
                    elif m and scope is None and cfg_test(m.group(2)):   # inner: the module it opens, or the file
                        if inline and inline[-1][2] and inline[-1][1] == level:
                            start, scope = inline[-1][3], [level - 1, False]
                        elif level <= 0:
                            start, scope = 0, [level - 1, False]
                        else:
                            start, scope = row, [level - 1, False]
                        for r in rows[start:]:
                            r[1] = True
                if not attrs:
                    raw = []
        if rest:
            given, held = None, bool(attrs)
            if rest[0] in ")]}":
                attrs, raw = [], []   # attributes that end a block hold no item
            elif attrs:
                if scope is None and any(m and not m.group(1) and cfg_test(m.group(2))
                                         for m in map(RUST_CFG.fullmatch, attrs)):
                    word = RUST_ITEM.match(rest)
                    scope = [at, not (rest[0] == "{" or word is not None and word.group(1) in RUST_ITEMS)]
                    for r in rows[first:]:
                        r[1] = True
                p = RUST_PATH.search("\n".join(raw))
                given = p.group(1).replace("\\", "/") if p else None
                attrs, raw = [], []
            m = RUST_MOD.match(rest) if "mod" in rest else None
            if m and m.group(2) == ";":
                declared.append((path, tuple(i[0] for i in inline), m.group(1), given, test or scope is not None))
            elif m:   # an inline module's #[path] names a folder, which rust_test_files does not follow
                inline.append([None if given else m.group(1), level + 1, False, first if held else row, n])
        if scope is not None and kind == CODE:
            rows[row][1] = True
        level += (code.count("(") + code.count("[") + code.count("{")
                  - code.count(")") - code.count("]") - code.count("}"))
        while inline:
            top = inline[-1]
            if level >= top[1]:
                top[2] = True
                break
            if not top[2] and (top[4] == n or not s):
                break   # a header whose brace is still to come
            inline.pop()
        if scope is not None and level <= scope[0] and ("}" in code or rest.endswith(";")
                                                         or scope[1] and rest.endswith(",")):
            scope = None   # the item closed
    return bytes(kinds), rows


def rust_attributes(s):
    """The attributes a line of Rust code starts with, and what follows them; None while one is still open."""
    attrs = []
    while True:
        m = RUST_ATTR.match(s)
        if not m:
            return attrs, s
        depth = 0
        for i in range(m.end() - 1, len(s)):
            depth += (s[i] == "[") - (s[i] == "]")
            if not depth:
                break
        else:
            return None
        attrs.append(s[:i + 1])
        s = s[i + 1:].lstrip()


def cfg_test(predicate):
    """Whether code under #[cfg(predicate)] is compiled only when tests are: the predicate is false whenever test is,
    and not false always. It is worked out in Kleene's three-valued logic with every option but test unknown (unix,
    feature = "x", miri, an option given arguments), which is exact where the answer does not turn on how those
    options relate: all(test, unix) is test code, while any(test, feature = "x"), compiled whenever the feature is
    on, is production, and so is all(test, not(test)), which is never compiled. A predicate it cannot read counts
    as test code only when it is the word test itself, as it did before this reading. Nested to any depth."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\S', predicate)
    try:
        return cfg_value(tokens, False) is False and cfg_value(tokens, True) is not False
    except ValueError:
        return predicate.strip() == "test"


def cfg_value(tokens, test):
    """A cfg predicate's value, as tokens, when test is as given: True, False or None when it turns on other options.
    Raises ValueError on what is not a predicate."""
    stack = [["all", []]]   # the predicate, as the one term of an all()
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t == ",":
            i += 1
        elif t == ")":
            if len(stack) < 2:
                raise ValueError("a ) with no (")
            op, values = stack.pop()
            if op == "all":
                value = False if False in values else True if all(v is True for v in values) else None
            elif op == "any":
                value = True if True in values else False if all(v is False for v in values) else None
            elif op == "not":
                if len(values) != 1:
                    raise ValueError("not() takes one predicate")
                value = None if values[0] is None else not values[0]
            else:   # an option given arguments, as version("1.80") is
                value = None
            stack[-1][1].append(value)
            i += 1
        elif t[0] == '"':
            stack[-1][1].append(None)
            i += 1
        elif t[0].isalpha() or t[0] == "_":
            after = tokens[i + 1] if i + 1 < n else ""
            if after == "(":
                stack.append([t, []])
                i += 2
            elif after == "=":   # a name and a value, as feature = "x" is (its string emptied or not)
                i += 3 if i + 2 < n and tokens[i + 2][0] == '"' else 2
                stack[-1][1].append(None)
            else:
                stack[-1][1].append(test if t == "test" else None)
                i += 1
        else:
            raise ValueError(t)
    if len(stack) != 1 or len(stack[0][1]) != 1:
        raise ValueError("not one predicate")
    return stack[0][1][0]


def cargo_roots(manifest, data):
    """The crate roots a Cargo.toml names by path, from the repository's top: [lib] path, each [[bin]], [[example]],
    [[test]] and [[bench]] path, and [package] build. Read with tomllib where Python has it; by its lines otherwise,
    or when tomllib refuses the file: a section's name and the path = "..." or build = "..." lines under it, the
    approximation, which misses a path written in an inline table."""
    folder = manifest.rpartition("/")[0]
    text = data.decode("utf-8", "replace")
    found, table = [], None
    if tomllib is not None:
        try:
            table = tomllib.loads(text)
        except ValueError:   # tomllib's TOMLDecodeError is a ValueError
            table = None
    if table is not None:
        for key in CARGO_TARGETS:
            got = table.get(key)
            for target in (got if isinstance(got, list) else [got]):
                if isinstance(target, dict):
                    found.append(target.get("path"))
        package = table.get("package")
        if isinstance(package, dict):
            found.append(package.get("build"))
    else:
        section = None
        for line in text.splitlines():
            m = re.match(r"\s*\[\[?\s*([\w.-]+)\s*\]\]?\s*(?:#.*)?$", line)
            if m:
                section = m.group(1)
                continue
            m = re.match(r"\s*(path|build)\s*=\s*[\"']([^\"']*)[\"']", line)
            if m and (m.group(1) == "path" and section in CARGO_TARGETS or m.group(1) == "build"
                      and section == "package"):
                found.append(m.group(2))
    return {posixpath.normpath(posixpath.join(folder, p.replace("\\", "/")))
            for p in found if isinstance(p, str) and p}


def rust_test_files(files, declared, roots):
    """The Rust files at the head that are compiled only in tests because a module compiled only in tests holds them
    (files: {path: whether its path makes it test code}; declared: from rust_lines; roots: from cargo_roots). A
    module declared out of line in a test scope, or in a file compiled only in tests, has its file found as rustc
    finds it: name.rs, else name/mod.rs, in the declaring file's folder when that file is a crate root, a mod.rs or a
    file a #[path] named, and in the folder named after it otherwise, under the folders of any inline modules around
    the declaration, or where its #[path] says; and so on down through that file's own modules. A declaration inside
    an inline module given a #[path] of its own is not followed. A file a production module also declares stays
    production. A crate root is one a Cargo.toml names, or by Cargo's layout a lib.rs, main.rs or build.rs or a file
    directly in a bin, examples, tests or benches folder, unless a module declares it. As a backstop for modules
    made in ways not read here (by a macro, or include!), a file in the folder of a test module's file that no
    declaration names is test code as well. Returns the files that are test code only by these rules."""
    if not declared:
        return set()

    def resolve(where, inline, name, given, owners):
        """The file of the module name declared in where, or None; owners are the files whose modules sit beside
        them, as a mod.rs file's do."""
        folder, _, base = where.rpartition("/")
        folder = folder + "/" if folder else ""
        if not base.endswith(".rs") or None in inline:
            return None
        own = folder if base == "mod.rs" or where in owners else folder + base[:-3] + "/"
        within = "".join(f + "/" for f in inline)
        if given is not None:
            found = [(folder if not inline else own + within) + given]
        else:
            found = [own + within + name + ".rs", own + within + name + "/mod.rs"]
        for p in found:
            p = posixpath.normpath(p)
            if p in files:
                return p
        return None

    named = {p for p in files if p.rpartition("/")[2] in RUST_ROOT_NAMES
             or p.rpartition("/")[0].rpartition("/")[2] in RUST_ROOT_DIRS}
    listed = roots & set(files)
    first = [resolve(*d[:4], named | listed) for d in declared]
    by_path = {t for t, d in zip(first, declared) if t is not None and d[3] is not None}   # read as a mod.rs is
    owners = (named - set(first)) | listed | by_path
    claims = {}   # each module's file: the files that declare it, and whether each declares it only in tests
    for where, inline, name, given, scoped in declared:
        target = resolve(where, inline, name, given, owners)
        if target is not None and target != where:
            claims.setdefault(target, []).append((where, scoped))
    test = {p for p, t in files.items() if t}
    ordered, seen = sorted(files), set()
    grown = True
    while grown:   # until no file is added: a file found test code may declare modules of its own
        grown = False
        for target, by in claims.items():
            if target not in test and any(s or w in test for w, s in by) \
                    and not any(not s and w not in test for w, s in by):
                test.add(target)
                grown = True
        for target in [t for t in claims if t in test and not files[t] and t not in seen]:   # the backstop
            seen.add(target)
            below = target[:-len("mod.rs")] if target.endswith("/mod.rs") else target[:-3] + "/"
            k = bisect.bisect_left(ordered, below)
            while k < len(ordered) and ordered[k].startswith(below):
                if ordered[k] not in claims and ordered[k] not in owners and ordered[k] not in test:
                    test.add(ordered[k])
                    grown = True
                k += 1
    return {p for p in test if not files[p]}


NO_LINES = ((), ())   # a file version whose diff added and removed no line of code
# The empty file, in SHA-1 and SHA-256 repositories: every template and project holds one (a .gitkeep, an empty
# __init__.py), so it tells no copy (see collect).
# Both Git object formats are required for compatibility; these are not security signatures.
EMPTY_BLOBS = {hashlib.sha1(b"blob 0\0").hexdigest(), hashlib.sha256(b"blob 0\0").hexdigest()}  # nosemgrep: python.lang.security.insecure-hash-algorithms.insecure-hash-algorithm-sha1


def move_credit(pool, added, sha, files):
    """What a sweep did to files, in the pool of written lines: each written line of code it removed hands its
    place to the line that took that place (pair_lines: the line of the same text, spacing aside, else the line in the
    same place of the same hunk), so the pool never grows and the place stays on the line that replaced the owner's,
    not on a neighbour's. A line only re-spaced hands its place to itself. The pool is keyed by (line_hash, whether
    the file it was written in is test code), a removed line taken from its own file's kind first. A version whose
    lines were not paired hands its places on in order, to the first lines it added. The files are taken in the order
    of their paths, so the same history always leaves the same pool."""
    pairing = added.get(PAIRS, {})
    for f in sorted(files, key=lambda f: (f.path, f.blob)):
        plus, minus = added.get((sha, f.blob), NO_LINES)
        kind, pair = is_test(f.path), pairing.get((sha, f.blob))
        if pair is None:
            moved = 0
            for h in minus:
                if moved == len(plus):
                    break
                for key in ((h, kind), (h, not kind)):
                    if pool[key] > 0:
                        pool[key] -= 1
                        moved += 1
                        break
            pool.update((h, kind) for h in plus[:moved])
            continue
        for j, i in enumerate(pair):
            if 0 <= i < len(minus) and j < len(plus):
                for key in ((minus[i], kind), (minus[i], not kind)):
                    if pool[key] > 0:
                        pool[key] -= 1
                        pool[(plus[j], kind)] += 1
                        break


# A file a commit adds is taken as moved from one it deletes, where git did not pair the two (see DELETED), when the
# commit deletes a file of the same name but for its folder and extension (f.js rewritten as f.ts), or when at least
# MOVED_SHARE of its lines of code are among the lines of code the deleted files held, as at least half of a file's
# content is what git's own rename detection asks for. A moved file adds only the lines it changed, and is no new
# file for the import rule; a new file beside an unrelated deletion shares only lines as common as a lone closing
# brace, and keeps every line it adds.
MOVED_SHARE = 0.5
# An existing codebase uploaded in parts (github.com takes 100 files an upload): an author's run of commits to one
# repository, each adding at least IMPORT_CHUNK new files of code within IMPORT_GAP seconds of the one before, that
# adds more than IMPORT_FILES in all is an import, as one commit of that size is. A busy day of small commits is not.
IMPORT_CHUNK, IMPORT_GAP = 50, 3600


def stem_of(path):
    """A file's name without its folder or extension, folded: what a move that also converts a file keeps."""
    return os.path.splitext(path.replace("\\", "/").rpartition("/")[2])[0].lower()


def moved_files(c, added):
    """The paths of the files commit c adds that it moved from files it deletes (see MOVED_SHARE), judged by their
    lines of code where the diffs were read (added), and by their names alone where they were not."""
    code = lambda f: counts_as_code(f.path, language_of(f.path))   # noqa: E731
    adds = [f for f in c.files if f.status == "A" and code(f)]
    stems = {stem_of(f.path) for f in c.files if f.status == "D" and code(f)}
    if not adds or not stems:
        return set()
    gone = Counter(added.get((c.sha, DELETED), NO_LINES)[1]) if added is not None else Counter()
    moved = set()
    for f in adds:
        plus = added.get((c.sha, f.blob), NO_LINES)[0] if added is not None else ()
        if stem_of(f.path) in stems or plus and sum(min(n, gone[h]) for h, n in Counter(plus).items()) >= (
                MOVED_SHARE * len(plus)):
            moved.add(f.path)
    return moved


def moved_out(plus, gone):
    """plus without the lines found in gone, a Counter of the lines of code a commit's deleted files held, each
    matched once: what a moved file changed."""
    kept = array("q")
    for h in plus:
        if gone[h] > 0:
            gone[h] -= 1
        else:
            kept.append(h)
    return kept


def new_code_files(c, added, theirs, moved, files=None):
    """The files of code commit c brings in new, for the import rule: added, not moved (moved_files), not marked by
    the repository's .gitattributes (theirs), and not generated; of files when given, else of all its files."""
    return [f for f in (c.files if files is None else files)
            if f.status == "A" and f.added is not None and f.path not in moved and (c.sha, f.path) not in theirs
            and counts_as_code(f.path, language_of(f.path))
            and (added is None or added.get((c.sha, f.blob)) is not GENERATED_VERSION)]


def import_runs(commits, new_files):
    """The hashes of the commits that bring in a codebase in parts (see IMPORT_CHUNK): new_files(c) is how many new
    files of code commit c adds. A commit of the author's own adding fewer ends the run."""
    found, runs = set(), {}
    for c in sorted(commits, key=lambda c: (c.repo, c.email, c.ts)):
        new, key = new_files(c), (c.repo, c.email)
        now = runs.get(key)
        if new < IMPORT_CHUNK:
            runs.pop(key, None)
            continue
        if now is None or c.ts - now["last"] > IMPORT_GAP:
            now = runs[key] = {"shas": [], "files": 0, "last": c.ts}
        now["shas"].append(c.sha)
        now["files"] += new
        now["last"] = c.ts
        if now["files"] > IMPORT_FILES:
            found.update(now["shas"])
    return found


def change_of(c, added):
    """The lines of code a commit's diff adds, and those it removes, as one set, or None where its repository's
    diffs could not be read: what tells one change landed twice from two changes that only share an author, an author
    second and a subject."""
    if added is None:
        return None
    lines = set()
    for key in [(c.sha, f.blob) for f in c.files] + [(c.sha, DELETED)]:
        plus, minus = added.get(key, NO_LINES)
        lines.update((True, h) for h in plus)
        lines.update((False, h) for h in minus)
    return lines


def same_change(a, b):
    """Whether two commits under one author, author second and subject are one change landed twice (a cherry-pick, a
    rebase, an amend), by their changes (change_of): yes when either's is unknown, as its repository's diffs could not
    be read, and when neither changes a line of code; no when only one does; otherwise yes when they share at least
    half of the smaller one's lines, as an amend that changed a line still does."""
    if a is None or b is None:
        return True
    if not a or not b:
        return not a and not b
    return 2 * len(a & b) >= min(len(a), len(b))


def spend(counter, h):
    """Takes one h out of counter, if it holds one: whether a line an earlier landing of the same change counted is
    being landed again (see collect)."""
    if counter[h] > 0:
        counter[h] -= 1
        return True
    return False


def window_holds(t, since, now):
    """Whether a commit made at t counts inside a window that starts at since (None, or -inf, for all time), as the run
    reckons it at now: the one test what is written, what is in use and what an import skipped are all cut by, so
    they can never disagree. main starts a limited window at a day's start in the owner's zone (first_day), so a day
    is inside or outside whole; a commit dated more than FUTURE_SLACK past now has a broken clock and never counts."""
    return (since is None or t >= since) and t <= now + FUTURE_SLACK


# A landing: a file version on the default branch whose added lines of code are nearly all (LANDING_SHARE, among them
# at least LANDING_LINES different lines) lines the owner's commits on another branch added to the same file and the
# default branch has not taken yet, as a squash merge, or a rebase that reset author dates, writes them again with the
# branch kept. They were written once, on the branch. A direct commit that shares a few common lines (a closing brace,
# return None) with such a branch is not a landing, and counts in full. No commit says it is a squash, so this is
# judged by the lines alone.
LANDING_SHARE, LANDING_LINES = 0.8, 3


def is_landing(waiting, plus):
    """Whether the added lines of code plus land what a branch wrote to the same file (waiting, a Bank; see
    LANDING_SHARE)."""
    counts = Counter(plus)
    matched = sum(min(n, waiting.count(h)) for h, n in counts.items())
    return bool(plus) and matched >= LANDING_SHARE * len(plus) and sum(
        1 for h in counts if waiting.count(h)) >= LANDING_LINES


def moved_blocks(plus, places, ends, removed):
    """What a commit moved into a file version (see MOVED_BLOCK): the runs of places (in order, of plus, the version's
    added lines) that follow one another within a hunk (ends: where each hunk's added lines end) and are each matched
    by a line of the same text among removed (Banks, drawn on in order), at least MOVED_BLOCK long. Takes a removed line
    for each and returns {place: the removed line's origin}."""
    links, run, want, starts = {}, [], Counter(), set(ends)

    def close():
        if len(run) >= MOVED_BLOCK:
            for j in run:
                for bank in removed:
                    o = bank.take(plus[j])
                    if o is not None:
                        links[j] = o
                        break
        del run[:]
        want.clear()

    last = None
    for j in places:
        if run and (j != last + 1 or j in starts):
            close()
        h = plus[j]
        if sum(bank.count(h) for bank in removed) > want[h]:
            run.append(j)
            want[h] += 1
        else:
            close()
        last = j
    close()
    return links


def collect(owner, repos, work, since=None):
    """Every counted file version as (time, language, lines of code), oldest first, plus the times of the
    owner's commits, of skipped imports and of the commits left out, with why, over the whole history; the
    window is applied afterwards. A file version's lines of code are the lines of code its commit's diff adds
    (read_added_code); for a repository whose diffs cannot be read, its added lines, comments and blank lines
    included, counted in code["unread"].

    What is still in use is read at each default branch's head: every line of code there that the owner wrote in
    the window, where wrote means exactly the lines counted as written by a commit inside it (window_holds: from
    since, a day's start, or all time when None, to FUTURE_SLACK past the run's now, which is returned as "now" for
    main to cut what is written by), each written line counted at most once across every repository, so what is in
    use is never more than what was written; split into production and test code. Each line is traced through its
    history (Trace): it counts when the line it came from was counted as written in the window, and a line from anyone
    else's work, or from the owner's before the window, counts nothing, whatever its text. A sweep by anyone, a move
    within one commit (moved_files, moved_blocks), a second landing of one change and a landing of a kept branch's
    lines (is_landing) write nothing, and hand each line they change on to the line they leave in its place, in the
    trace as in the pool of written lines (move_credit): a renamed line is still the owner's. A line history cannot
    place is matched by its text, spacing aside, against the written lines no traced line took (the backstop):
    code["traced"] and code["matched"] say how many of each. An archived repository's head is not read, and adds
    nothing in use (code["archived"]).

    Only the owner's own commits count (see authorship); others', automation's and copies' add no lines and
    no commits, and their file versions count as seen, so no later commit is credited with them. A commit held by
    more than one repository, as in a fork or a mirror, counts once, and is the owner's if it is theirs in any of
    them. So does one change landed twice under new hashes (a cherry-pick, a rebase with the branch kept, an amend
    still reachable from a tag), known by its author's address, author time and subject and by sharing most of its
    lines of code (see same_change): different changes that only share the first three, one message committed in
    several repositories at once, both count. A second landing adds no commit, and of its lines only those no earlier
    landing counted as written. Commits of one author second are read parent first, as git lists them (read_commits).
    File versions another account wrote, from the template a repository was made from or from coderprint itself
    in a relay copy, count as seen before anything is read; a commit that adds nothing else (the empty file aside,
    which every template holds) is not the owner's work and does not count. A repository that cannot be read, even
    on a second try, is left out and counted in "unread"; one made from a template whose files cannot be listed or
    seen, or a relay copy when coderprint's own cannot be, is left out too and named in "unsure".

    A lookup that tells the owner's code from others' and that GitHub cannot answer, even on a second try, is named
    in "unchecked" (UNCHECKED), since everything would then count as the owner's; main then keeps the existing
    panels. The lookups that need no commits are made before any repository is read, and a run that cannot make them
    reads nothing; while repositories are read LOOKUP_RESERVE is kept back for the one that needs them, so a run
    that reads until its deadline still asks it and leaves out only the repositories it had no time for.
    "authors" says how many addresses GitHub was not asked about ("unknown"), how many commits count under them
    ("commits"), and how many addresses CARDS_AUTHOR_EMAILS lists that belong to another account ("refused").
    The file versions a repository's .gitattributes marks as vendored, generated or documentation
    (attributed_versions) count nowhere, and neither do generated files (generated_output). A version that counts is
    taken before the same content under a path that does not, in one commit (src/ beside dist/). A file moved to a
    new name while being edited, which git reports as deleted and added past its rename limit or similarity
    threshold, adds only what it changed (moved_files), and a block moved within one commit adds nothing
    (moved_blocks). A squash merge, or a rebase that reset author dates, that lands lines a kept branch already
    wrote (is_landing) adds only what the branch did not. An import, of more than IMPORT_FILES new files of code in
    one commit or in a run of commits (import_runs), adds no lines.

    An empty repository, or one of tags alone, has nothing to read. A repository whose head cannot be read still
    counts what its diffs add, and adds nothing in use (code["heads_unread"]); one whose diffs cannot be read adds
    nothing in use either. code["approximate"] lists (time, lines) for the lines written whose reading rests on a
    fallback (see read_added_code), numstat's counts for a repository whose diffs cannot be read among them, and
    code["approximate_in_use"] the lines in use read so, code["approximate_imports"] the lines of imports counted by
    numstat; code["attributes_unread"] counts the repositories whose .gitattributes git could not read."""
    global RESERVE, TRACE, PROFILE_OWNER
    PROFILE_OWNER = owner
    now = time.time()   # the run's now, returned: main cuts what is written by it too (window_holds)
    all_commits, mismatched, unread, ignore = [], 0, 0, set()
    organization_unread = 0
    uploads = authored_imports(owner)
    credited_uploads = []
    code, head = {}, {}   # by repository: what each file version adds, and what stands at the head
    skip, attributes_unread = {}, 0   # by repository: the (commit, path) its .gitattributes marks as not its own
    order = {}   # (repository, commit): its place in git's listing, children first (see read_commits)
    traces = {}   # by repository: its Trace, where its history was read
    line_of = {}   # by repository: the commits its default branch holds, or None where that cannot be read
    # every range of ids the traces gave out, in order: its first id, and (repository, (commit, blob)), or None where a
    # second reading of the same version replaced it (see Trace.allot)
    bases, owners, next_id, archived = array("q"), [], 1, 0
    # The lookups that need no commits come first, so a run that reads until its deadline still has them, and a run
    # that could not tell the owner's code from others' stops before it reads anything (see main).
    unchecked = set()   # the lookups GitHub could not answer (UNCHECKED)
    made, identity = templates(owner), owner_identity(owner)
    accounts = {repo_owner(owner, r).lower() for r in repos if repo_owner(owner, r).lower() != owner.lower()}
    if accounts and identity is not None and not identity["user"]:
        unchecked.add("authorship")
    if made is not None:
        for account in sorted(accounts):
            with repository_access(account):
                extra = templates(account, owner)
            if extra is None:
                made = None
                break
            made.update({account + "/" + name: source for name, source in extra.items()})
    if made is None:
        unchecked.add("templates")
    if identity is None:
        unchecked.add("authorship")
    if unchecked:
        return {"events": [], "commits": [], "imports": [], "import_lines": [], "mismatched": 0, "unread": 0,
                "left_out": {}, "left_out_times": [], "unchecked": sorted(unchecked), "unsure": set(), "copies": set(),
                "authors": {"unknown": 0, "commits": 0, "refused": 0},
                "code": {"production": 0, "tests": 0, "unread": 0, "heads_unread": 0, "approximate": [],
                         "approximate_in_use": 0, "approximate_imports": [], "attributes_unread": 0, "traced": 0,
                         "matched": 0, "archived": 0},
                "now": now}
    seeded, unlisted = set(), set()   # the file versions other accounts wrote; the sources that could not be listed
    sources = {t for t in made.values() if t} | ({UPSTREAM} if owner.lower() != UPSTREAM.split("/")[0].lower() else set())
    for k, full_name in enumerate(sorted(sources)):
        blobs = seed_blobs(full_name, os.path.join(work, "seed-%d.git" % k))
        if blobs is None:
            unlisted.add(full_name)
        else:
            seeded |= blobs
    # A repository made from a template whose files cannot be listed, or seen at all, holds files no one can tell from
    # the owner's own, so it is left out and counted, as one that cannot be read is; so is a relay copy when
    # coderprint's own files cannot be listed (below). Guessing either way would count others' code or drop the owner's.
    readable = {repo_key(owner, r) for r in repos if not (r.get("isDisabled") or r.get("isLocked"))}
    unsure = {name for name, t in made.items() if t is None or t in unlisted} & readable
    saved, RESERVE = RESERVE, RESERVE + LOOKUP_RESERVE   # reading stops in time for the lookup after it (authorship)
    try:
        for i, r in enumerate(repos):
            if r.get("isDisabled") or r.get("isLocked") or repo_key(owner, r) in unsure:
                continue   # counted in the listing, never cloned
            account = repo_owner(owner, r)
            dest = slot(work, account, r["name"])
            try:
                with repository_access(account):
                    commits, bad, sweeps = read_repository(account, r["name"], dest, i)
                marked = attributed_versions(dest, commits) if commits else set()
                skip[i] = marked or set()
                if commits:   # read while the clone is still on disk; each apart, so a head that cannot be read costs
                    # no diffs. read_added_code pairs the changed lines of the commits that could be sweeps (sweep),
                    # and of those .git-blame-ignore-revs lists, and traces where every line came from (Trace).
                    SWEEP_WATCH.clear()
                    SWEEP_WATCH.update(c.sha for c in commits if could_sweep([f for f in c.files if f.added is not None
                                                                              and language_of(f.path)
                                                                              and (c.sha, f.path) not in skip[i]]))
                    SWEEP_WATCH.update(sweeps)
                    trace = TRACE = Trace(next_id, seeded)
                    try:
                        try:
                            code[i] = read_added_code(dest)
                        except RuntimeError:
                            code[i] = None
                        finally:
                            SWEEP_WATCH.clear()
                        try:   # an archived repository is retired: its head is not in use, though its history counts
                            head[i] = Standing() if r.get("isArchived") else read_head_code(dest)
                        except RuntimeError:
                            head[i] = None
                    finally:
                        TRACE = None
                    next_id = trace.next
                    if code[i] is not None and not trace.broken:   # a broken trace leaves the head to the backstop
                        traces[i] = trace
                        for first, version in trace.allocs:
                            bases.append(first)
                            owners.append(None if version is None else (i, version))
                    trace.heads = trace.extra = trace.allocs = None   # read into head[i] and bases; let go
                    try:   # the commits the default branch holds; the rest sit on other branches (see LANDING_SHARE)
                        listed = run(["git", "-C", dest, "rev-list", "HEAD"])
                        line_of[i] = set(listed.decode("ascii", "replace").split())
                    except RuntimeError:
                        line_of[i] = None
                else:   # an empty repository, or one of tags alone: read, and nothing in it
                    code[i], head[i] = {}, Standing()
                archived += bool(r.get("isArchived"))
                if marked is None or getattr(head[i], "unattributed", False):
                    attributes_unread += 1
            except RuntimeError:
                unread += 1
                organization_unread += account.lower() != owner.lower()
                continue
            finally:
                if not os.environ.get("CLONE_CACHE") and os.path.isdir(dest):
                    remove_tree(dest)   # one clone on disk at a time
            for k, c in enumerate(commits):
                order[(i, c.sha)] = k
            all_commits += commits
            mismatched += bad
            ignore |= sweeps
    finally:
        RESERVE = saved

    if UPSTREAM in unlisted:   # a relay copy, known by holding both of RELAY_FILES, is left out (see above)
        held = {}
        for c in all_commits:
            held.setdefault(c.repo, set()).update(f.path for f in c.files if f.path in RELAY_FILES)
        relay = {i for i, paths in held.items() if paths >= RELAY_FILES}
        unsure |= {repo_key(owner, repos[i]) for i in relay}
        all_commits = [c for c in all_commits if c.repo not in relay]
        for i in relay:
            code.pop(i, None)
            head.pop(i, None)
            traces.pop(i, None)
    notes = {}
    mine = authorship(owner, all_commits, identity, repos, notes)
    if identity["user"] and mine is None:
        unchecked.add("authorship")   # every commit would count, others' included
    # a commit held by several repositories is the owner's if it is theirs in any of them, whichever is read first
    owned = None if mine is None else {c.sha for c in all_commits if (c.repo, c.email) in mine}
    agents = {c.sha for c in all_commits if (c.repo, c.email) in notes.get("agents", ())}
    unknown, unverified = notes.get("unknown", set()), 0   # addresses GitHub was not asked about, and their commits

    moves = {}   # (repository, commit): the paths of the files it moved (moved_files)

    def moved(c):
        if (c.repo, c.sha) not in moves:
            moves[(c.repo, c.sha)] = moved_files(c, code.get(c.repo))
        return moves[(c.repo, c.sha)]

    parts = import_runs([c for c in all_commits if not c.bot], lambda c: len(new_code_files(
        c, code.get(c.repo), skip.get(c.repo) or (), moved(c))))
    twins = {k for k, n in Counter((c.email, c.ts, c.subject) for c in all_commits).items() if n > 1}
    # keys: (address, author time, subject) -> each change counted under it, as [its lines (change_of), or None where
    # they are unknown, a Counter of the lines of code its landings counted as written, or None, and those lines' ids
    # by line_hash (see Trace), or None]
    seen, shas, keys = set(seeded), set(), {}
    events, commit_times, import_times, import_lines, approximate, rough_imports = [], [], [], [], [], []
    left_out, left_times = Counter(), []   # commits left out, by why: over the whole history, and each one's time
    pool = Counter()   # the lines of code counted as written in the window, in every repository, by line_hash and
    # whether the file they were written in is test code
    holding, writing = set(), set()   # repositories with any file version, and with one not another's
    # What collect decided for the lines of code each file version added, where traced (see Trace): (commit, blob) ->
    # one origin for all of them, or an array of one for each: OWN_PRODUCTION or OWN_TEST for a line counted as written
    # in the window, OTHER_ORIGIN for one that is not, and the origin of the line it carries on for a line a sweep, a
    # move or a second landing handed on (a Bank's). first_of: blob -> (repository, (commit, blob)) of the commit that
    # first held it, whose decision stands for every later version of the same content. touched: (repository, path) of
    # every file the owner's counted commits changed.
    decided, first_of, touched = {}, {}, set()
    # (repository, path): what the owner's commits on branches other than the default wrote there, as a Bank, and the
    # file versions they left, until the default branch lands them (see LANDING_SHARE)
    side, side_blobs = {}, {}

    def ids_of(c, f):
        t = traces.get(c.repo)
        return None if t is None else t.base.get((c.sha, f.blob))

    def settle(c, f, n, links, kept, own):
        """Records what was decided for the n lines of code version f of commit c added: own for the places in kept,
        the origin links gives for the places it holds, OTHER_ORIGIN for the rest."""
        if not n or ids_of(c, f) is None:
            return
        if not links and len(kept) in (0, n):
            decided[(c.sha, f.blob)] = own if kept else OTHER_ORIGIN
            return
        values = array("q", [OTHER_ORIGIN]) * n
        for j in kept:
            values[j] = own
        for j, o in links.items():
            values[j] = o
        decided[(c.sha, f.blob)] = values

    def settle_all(c, files, value):
        """Records value for every line of code the versions files of commit c added, where nothing else was."""
        for f in files:
            if (c.sha, f.blob) not in decided and ids_of(c, f) is not None:
                decided[(c.sha, f.blob)] = value

    def removed_banks(c, files, added):
        """The lines of code commit c removed from files, and those of the files it deleted, with their origins
        (Trace.gone), as two Banks."""
        t = traces.get(c.repo)
        changed, gone = Bank(), Bank()
        versions = list(dict.fromkeys((c.sha, f.blob) for f in files if f.status != "D"))   # in the commit's order
        for version, bank in [(v, changed) for v in versions] + [((c.sha, DELETED), gone)]:
            minus = added.get(version, NO_LINES)[1]
            origins = t.gone.get(version) if t is not None else None
            if origins is not None and len(origins) != len(minus):
                origins = None
            for i, h in enumerate(minus):
                bank.put(h, origins[i] if origins is not None else UNKNOWN_ORIGIN)
        return changed, gone

    def hand_on(c, f, added):
        """A swept version: each line it added carries the origin of the removed line whose place it took (pair_lines),
        and adds nothing."""
        t = traces.get(c.repo)
        version = (c.sha, f.blob)
        plus, minus = added.get(version, NO_LINES)
        pair = added.get(PAIRS, {}).get(version)
        origins = t.gone.get(version) if t is not None else None
        links = {}
        for j in range(len(plus)):
            i = pair[j] if pair is not None and j < len(pair) else (j if j < len(minus) else -1)
            if 0 <= i < len(minus):
                links[j] = origins[i] if origins is not None and i < len(origins) else UNKNOWN_ORIGIN
        settle(c, f, len(plus), links, (), OTHER_ORIGIN)

    def take(c, fresh, swept, added, theirs, written, in_window, repeat=None, repeat_ids=None, wrote=None,
             wrote_ids=None, on_side=False):
        """The lines of code the fresh versions of commit c add: counted as written when written is true (the owner's
        own commit), each traced in any case. A version it swept carries its lines on (hand_on); a file it moved from
        one it deleted adds only what it changed, and a block it moved within or between files (moved_blocks) adds
        nothing, each moved line carrying its origin on; so does a line an earlier landing of the same change counted
        (repeat) or a branch wrote that this lands (is_landing). A version that counts is taken before the same content
        under a path that does not (src/ beside dist/), whichever way the two paths sort."""
        rough = added.get(APPROXIMATE, {}) if added is not None else {}
        chosen = []   # [version, language, its added lines, the places still counted, {place: origin carried on}]
        for f in sorted(fresh, key=lambda f: not counts_as_code(f.path, language_of(f.path))
                        or (c.sha, f.path) in theirs):
            if f.blob in seen:
                continue
            seen.add(f.blob)
            lang = language_of(f.path)
            if added is not None and f in swept:
                hand_on(c, f, added)
                continue
            if not counts_as_code(f.path, lang) or f in swept or (c.sha, f.path) in theirs:
                settle_all(c, [f], OTHER_ORIGIN)
                continue
            if added is None:
                lines = f.added or 0
                if written and lines:   # numstat's count, comments and blank lines and all
                    approximate.append((c.ts, lines))
                    events.append((c.ts, lang, lines))
                continue
            plus = added.get((c.sha, f.blob), NO_LINES)[0]
            chosen.append([f, lang, plus, list(range(len(plus))), {}])
        if not chosen:
            return
        banks, mv = None, moved(c)
        for w in chosen:
            f, lang, plus, places, links = w
            if f.status == "A" and f.path in mv:   # moved here from a file this commit deleted: only its changes
                if banks is None:
                    banks = removed_banks(c, [x for x in c.files if x not in swept], added)
                rest = []
                for j in places:
                    o = banks[1].take(plus[j])
                    if o is None:
                        rest.append(j)
                    else:
                        links[j] = o
                w[3] = places = rest
            if wrote is not None:
                base = ids_of(c, f)
                for j in places:
                    wrote[plus[j]] += 1
                    wrote_ids.append((plus[j], UNKNOWN_ORIGIN if base is None else base + j))
            if repeat is not None:   # only what no earlier landing of this change counted
                rest = []
                for j in places:
                    if spend(repeat, plus[j]):
                        q = repeat_ids.get(plus[j])
                        links[j] = q.pop() if q else UNKNOWN_ORIGIN
                    else:
                        rest.append(j)
                w[3] = rest
        if banks is None:
            banks = removed_banks(c, [x for x in c.files if x not in swept], added)
        if banks[0] or banks[1]:
            t = traces.get(c.repo)
            for w in chosen:
                f, lang, plus, places, links = w
                got = moved_blocks(plus, places, t.bounds.get((c.sha, f.blob), ()) if t is not None else (), banks)
                if got:
                    links.update(got)
                    w[3] = [j for j in places if j not in got]
        for f, lang, plus, places, links in chosen:
            where = (c.repo, f.path)
            if written and not on_side and side.get(where) and is_landing(side[where], [plus[j] for j in places]):
                rest = []   # written once already, on its branch
                for j in places:
                    o = side[where].take(plus[j])
                    if o is None:
                        rest.append(j)
                    else:
                        links[j] = o
                places = rest
            kind = is_test(f.path, lang)
            settle(c, f, len(plus), links, places,
                   (OWN_TEST if kind else OWN_PRODUCTION) if written and in_window else OTHER_ORIGIN)
            if not written:
                continue
            if on_side:   # waits for the default branch to land it
                bank, base = side.setdefault(where, Bank()), ids_of(c, f)
                for j in places:
                    bank.put(plus[j], UNKNOWN_ORIGIN if base is None else base + j)
                side_blobs.setdefault(where, set()).add(f.blob)
            lines = len(places)
            if in_window:
                pool.update((plus[j], kind) for j in places)
            if rough.get((c.sha, f.blob)):
                approximate.append((c.ts, min(lines, rough[(c.sha, f.blob)])))
            if lines:
                events.append((c.ts, lang, lines))

    # commits of one second parent first: a sweep read before the lines it rewrites would hand on nothing
    for c in sorted(all_commits, key=lambda c: (c.ts, c.repo, -order[(c.repo, c.sha)])):
        if c.sha in shas:
            continue
        organization = repo_owner(owner, repos[c.repo]).lower() != owner.lower()
        # A mirror with unknown organization attribution must wait for the copy whose authorship was established.
        if organization and mine is not None and (c.repo, c.email) not in mine and c.sha in owned:
            continue
        shas.add(c.sha)
        live = [f for f in c.files if f.status != "D" and not f.blob.startswith("0000000")]
        fresh = [f for f in live if f.blob not in seen]
        for f in fresh:
            first_of.setdefault(f.blob, (c.repo, (c.sha, f.blob)))
        key = (c.email, c.ts, c.subject)
        added = code.get(c.repo)
        change = change_of(c, added) if key in twins else None
        # the empty file is in every template, so a commit adding only empty files beside others' is no copy
        kept = [f for f in live if f.blob not in EMPTY_BLOBS]
        copied = bool(kept) and all(f.blob in seeded for f in kept)
        if live:
            holding.add(c.repo)
            if not copied:
                writing.add(c.repo)
        main_line = line_of.get(c.repo)
        on_side = main_line is not None and c.sha not in main_line
        if side and main_line is not None and not on_side:
            for f in live:   # a branch's own file version on the default branch: it landed as it was
                if f.blob in side_blobs.get((c.repo, f.path), ()):
                    side.pop((c.repo, f.path), None)
                    side_blobs.pop((c.repo, f.path), None)
        theirs_commit = owned is not None and (c.sha not in owned or (organization and (c.repo, c.email) not in mine))
        why = ("automation" if c.bot or (theirs_commit and c.sha in agents) else "others" if theirs_commit
               else "copied" if copied else None)
        theirs = skip.get(c.repo) or ()
        counted = [f for f in fresh if f.added is not None and language_of(f.path) and (c.sha, f.path) not in theirs]
        in_window = added is not None and window_holds(c.ts, since, now)
        if why:   # seen all the same, so no later commit is credited with this content
            if why != "copied" and added is not None:
                # a sweep someone else ran (a formatter bot, a collaborator, the owner's own workflow) writes none of
                # the owner's lines it touches, so they stay the owner's, as the owner's own sweep leaves them; so does
                # a move of them
                handed = set(c.files) if c.sha in ignore else sweep(counted, added.get(ALIKE, {}), c.sha)
                if handed and in_window:
                    move_credit(pool, added, c.sha, handed)
                take(c, fresh, handed, added, theirs, False, in_window)
            settle_all(c, fresh, OTHER_ORIGIN)   # a copy's lines are others', and so is all else they did not hand on
            seen.update(f.blob for f in fresh)
            left_out[why] += 1
            left_times.append((c.ts, why))
            continue
        # One change landed again under a new hash (same_change) is no commit of its own, and what its earlier landings
        # counted as written is not written again; what it adds that they did not, an amend's new file or a line a
        # conflict's resolution wrote, is new writing, under every rule below. Where either's lines are unknown there
        # is nothing to tell its new lines by, so it adds nothing.
        record, repeat, repeat_ids, wrote, wrote_ids = None, None, None, None, None
        if key in twins:
            landings = [rec for rec in keys.get(key, ()) if same_change(change, rec[0])]
            if landings:
                left_out["landed_twice"] += 1
                left_times.append((c.ts, "landed_twice"))
                if change is None or any(rec[1] is None for rec in landings):
                    settle_all(c, fresh, UNKNOWN_ORIGIN)   # nothing to tell its lines by: the backstop decides
                    seen.update(f.blob for f in fresh)
                    continue
                record, repeat, repeat_ids = landings[0], Counter(), {}
                for rec in landings:
                    repeat |= rec[1]
                    for h, got in rec[2].items():
                        repeat_ids.setdefault(h, []).extend(got)
                record[0] = record[0] | change
            else:
                record = [change, None, None] if change is None else [change, Counter(), {}]
                keys.setdefault(key, []).append(record)
            if record[1] is not None:
                wrote, wrote_ids = Counter(), []
        if repeat is None:
            commit_times.append(c.ts)
            if c.email in unknown:
                unverified += 1
        touched.update((c.repo, f.path) for f in c.files)
        # the import rule counts new files of code only: prose, data, generated files and files moved from ones the
        # commit deletes are not new code (see IMPORT_FILES and moved_files)
        code_files = [f for f in counted if counts_as_code(f.path, language_of(f.path))
                      and (added is None or added.get((c.sha, f.blob)) is not GENERATED_VERSION)]
        brought = c.sha not in ignore and (c.sha in parts or len(new_code_files(c, added, theirs, moved(c), counted))
                                           > IMPORT_FILES)
        declared = (repo_owner(owner, repos[c.repo]).lower() + "/" + repos[c.repo]["name"].lower(), c.sha) in uploads
        claimed_upload = brought and declared
        if claimed_upload:
            # This is an explicit claim about one upload, after all author, bot, template and file filters.
            brought = False
        if c.sha in ignore or brought:
            if repeat is not None:
                pass   # its first landing already brought it in, or handed its lines on
            elif brought:   # an existing codebase brought in, not written: its lines of code, as written would count them
                import_times.append(c.ts)
                if added is None:   # numstat's count, comments and blank lines and all
                    lines = sum(f.added for f in code_files)
                    if lines:
                        rough_imports.append((c.ts, lines))
                else:
                    lines = sum(len(added.get((c.sha, f.blob), NO_LINES)[0]) for f in code_files)
                import_lines.append((c.ts, lines))
            elif in_window:
                move_credit(pool, added, c.sha, c.files)
            if not brought and added is not None:   # a listed sweep: each line it changed keeps its origin
                take(c, fresh, set(c.files), added, theirs, False, in_window)
            settle_all(c, fresh, OTHER_ORIGIN)   # an import's lines were not written
            seen.update(f.blob for f in fresh)
            continue
        swept = sweep(counted, added.get(ALIKE, {}) if added is not None else None, c.sha)
        if in_window and swept and repeat is None:
            move_credit(pool, added, c.sha, swept)
        if repeat is not None and side and main_line is not None and not on_side and added is not None:
            for f in fresh:   # the same change landed on the default branch: what its side landing left is taken
                waiting = side.get((c.repo, f.path))
                if waiting:
                    for h in added.get((c.sha, f.blob), NO_LINES)[0]:
                        waiting.take(h)
        before = len(events)
        take(c, fresh, swept, added, theirs, True, in_window, repeat, repeat_ids, wrote, wrote_ids, on_side)
        if claimed_upload and repeat is None and in_window:
            credited_uploads.append((c.ts, sum(n for _, _, n in events[before:])))
        if wrote:
            record[1] |= wrote
            for h, o in wrote_ids:
                record[2].setdefault(h, []).append(o)

    # What stands at each head. A line whose history places it (Trace) counts when the line it came from was counted
    # as written in the window, once for each such line however many heads hold it, and takes that line from the pool,
    # so in use never passes written; a line that came from anyone else's work, or from the owner's outside the window,
    # counts nothing, whatever its text. A line history cannot place is matched afterwards by its text (the backstop).
    def locate(o):
        """(repository, (commit, blob), place among its added lines) of the line of code id o names, or None."""
        p = bisect.bisect_right(bases, o) - 1
        if p < 0 or owners[p] is None:
            return None
        repo, version = owners[p]
        added = code.get(repo)
        j = o - bases[p]
        return (repo, version, j) if added is not None and j < len(added.get(version, NO_LINES)[0]) else None

    mapped = {}   # (repository, (commit, blob)) -> the place of each of its added lines among its first holder's

    def through_first(repo, version, j):
        """Added line j of a version whose content another commit first held: that commit's line of the same text, as
        (repository, version, place), or what it is known to be when there is none."""
        blob = version[1]
        if blob in seeded:
            return OTHER_ORIGIN
        first = first_of.get(blob)
        if first is None or first[1] == version:
            # a version no commit collect read held (a merge's alone, an unparsed commit's), or its first holder read
            # without its lines traced (a fork's history read another way): nothing to say
            return UNKNOWN_ORIGIN
        places = mapped.get((repo, version))
        if places is None:
            there = code.get(first[0])
            bank = Bank()
            for k, h in enumerate(there.get(first[1], NO_LINES)[0] if there is not None else ()):
                bank.put(h, k)
            places = array("l")
            for h in code[repo].get(version, NO_LINES)[0]:
                k = bank.take(h)
                places.append(-1 if k is None else k)
            mapped[(repo, version)] = places
        return (first[0], first[1], places[j]) if places[j] >= 0 else UNKNOWN_ORIGIN

    def resolve(o):
        """What a line of origin o is: (OWN_PRODUCTION or OWN_TEST, and where it was decided so), or (OTHER_ORIGIN or
        UNKNOWN_ORIGIN, None). A chain that runs on past any history's length is taken as unknown."""
        for _ in range(100000):
            if o <= 0:
                return o, None
            at = locate(o)
            if at is None:
                return UNKNOWN_ORIGIN, None
            d = decided.get(at[1])
            if d is None:
                at = through_first(*at)
                if not isinstance(at, tuple):
                    return at, None
                d = decided.get(at[1], UNKNOWN_ORIGIN)
            v = d if isinstance(d, int) else (d[at[2]] if at[2] < len(d) else OTHER_ORIGIN)
            if v in (OWN_PRODUCTION, OWN_TEST):
                return v, at
            o = v
        return UNKNOWN_ORIGIN, None

    in_use = [0, 0]   # production, tests
    rough_in_use = traced = matched = 0   # of them, lines a fallback read, lines traced, and lines matched by text
    standing_for = {}   # (commit, blob) -> which of its added lines a line at a head already counts for
    loose = []   # [repository, standing, the places of its lines history cannot place]
    for i, s in head.items():
        if s is None or code.get(i) is None:   # a repository whose diffs could not be read adds nothing in use
            continue
        origins = getattr(s, "origins", None)
        if origins is None or len(origins) != len(s):
            origins = array("q", bytes(8 * len(s)))
        unknown_at = []
        for k in range(len(s)):
            try:
                v, at = resolve(origins[k]) if origins[k] else (UNKNOWN_ORIGIN, None)
            except Exception:   # a history tracing cannot follow: the line is left to the backstop
                v, at = UNKNOWN_ORIGIN, None
            if at is None:
                if v == UNKNOWN_ORIGIN:
                    unknown_at.append(k)
                continue
            repo, version, j = at
            plus = code[repo][version][0]
            mask = standing_for.get(version)
            if mask is None:
                mask = standing_for[version] = bytearray(len(plus))
            if mask[j]:
                continue   # a copy of a line already in use (a fork, a file copied): it was written once
            h, t, t0 = s.hashes[k], s.tests[k], 1 if v == OWN_TEST else 0
            for p in ((h, t), (h, 1 - t), (plus[j], t0), (plus[j], 1 - t0)):   # its text now, or as written
                if pool[p] > 0:
                    pool[p] -= 1
                    mask[j] = 1
                    in_use[t] += 1
                    traced += 1
                    rough_in_use += s.rough[k]
                    break
        if unknown_at:
            loose.append((i, s, unknown_at))
    # The backstop: a line whose history is unknown is matched by its text, spacing aside, against the written lines no
    # traced line took. One written in code of its own kind (production or tests) is taken first, and a line in a file
    # the owner's counted commits changed before any other, so a line common to several, such as a lone brace, is
    # placed where the owner wrote rather than in whichever repository or file is read first; the totals are the same
    # whatever the order. A line a fallback read is matched before one read exactly, so approximate_in_use says how
    # many of those in use it could be.
    plan = []
    for i, s, places in loose:
        mine = bytearray(len(s))
        for path, a, b in getattr(s, "files", ()):
            if (i, path) in touched:
                mine[a:b] = b"\x01" * (b - a)
        tiers = ([k for k in places if mine[k]], [k for k in places if not mine[k]])
        plan.append((s, [sorted(tier, key=lambda k: not s.rough[k]) for tier in tiers], bytearray(len(s))))
    for same in (True, False):
        for tier in (0, 1):
            for s, tiers, taken in plan:
                for k in tiers[tier]:
                    if taken[k]:
                        continue
                    test = s.tests[k]
                    p = (s.hashes[k], test if same else 1 - test)
                    if pool[p] > 0:
                        pool[p] -= 1
                        taken[k] = 1
                        in_use[test] += 1
                        matched += 1
                        rough_in_use += s.rough[k]
    return {"events": events, "commits": commit_times, "imports": import_times, "import_lines": import_lines,
            "mismatched": mismatched, "unread": unread, "left_out": dict(left_out), "left_out_times": left_times,
            "unchecked": sorted(unchecked), "unsure": unsure, "copies": {repo_key(owner, repos[k]) for k in holding - writing},
            "organization_unread": organization_unread, "authored_imports": credited_uploads,
            "authors": {"unknown": len(unknown), "commits": unverified, "refused": notes.get("refused", 0)},
            "code": {"production": in_use[0], "tests": in_use[1], "unread": sum(1 for v in code.values() if v is None),
                     "heads_unread": sum(1 for v in head.values() if v is None),
                     "approximate": approximate, "approximate_in_use": rough_in_use,
                     "approximate_imports": rough_imports, "attributes_unread": attributes_unread,
                     "traced": traced, "matched": matched, "archived": archived},
            "now": now}


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


# ---------------------------------------------------------------- days


def place_key(text):
    """A place name as the place table stores it: accents dropped, case folded, anything but letters and digits
    turned into single spaces, and a run of single letters joined, so "São Paulo" and "sao paulo" are one name
    and "D.C." is "dc", as "U.S.A." is "usa"."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold().translate(FOLD_LETTERS)
    words, run = [], ""
    for word in "".join(ch if ch.isalnum() else " " for ch in text).split():
        if len(word) == 1 and word.isalpha():
            run += word
            continue
        if run:
            words.append(run)
            run = ""
        words.append(word)
    return " ".join(words + [run] if run else words)


_places = None


def load_places():
    """The place table: which countries, regions and cities each name can mean, which regions each short code
    confirms, which cities each name can mean only when the rest of the location points at them, and every city
    by country and by region. Read once; if the file is missing or damaged the table is empty, so no location is
    recognised and days stay as they would be without one."""
    global _places
    if _places is None:
        countries, regions, cities, in_country, in_region, codes, also = {}, {}, {}, {}, {}, {}, {}
        try:
            with gzip.open(PLACES_FILE, "rt", encoding="utf-8") as f:
                for line in f:
                    row = line.rstrip("\n").split("\t")
                    if row[0] == "C" and len(row) == 3:
                        for key in row[2].split("|"):
                            countries.setdefault(key, set()).add(row[1])
                    elif row[0] in ("A", "Q") and len(row) == 4:
                        for key in row[3].split("|"):
                            (regions if row[0] == "A" else codes).setdefault(key, set()).add((row[1], row[2]))
                    elif row[0] == "P" and len(row) in (7, 8):
                        place = Place(int(row[1]), row[2], row[3], int(row[4]), row[5])
                        for key in row[6].split("|"):
                            cities.setdefault(key, []).append(place)
                        for key in row[7].split("|") if len(row) == 8 else ():
                            also.setdefault(key, []).append(place)
                        in_country.setdefault(place.country, []).append(place)
                        in_region.setdefault((place.country, place.region), []).append(place)
        except (OSError, EOFError, ValueError, zlib.error):
            countries, regions, cities, in_country, in_region, codes, also = {}, {}, {}, {}, {}, {}, {}
        _places = (countries, regions, cities, in_country, in_region, codes, also)
    return _places


def location_parts(location, countries, regions, cities, codes=(), notes=None):
    """A location's parts as place keys, in order and each once. A part the table does not know as written is
    read without words around a name ("Greater London", "Based in Nairobi", "Oslo area"), split where a known
    city meets a country, region or region code ("Santa Clara CA", "Delhi NCR"), or split where it joins two
    places ("Tokyo & Seoul", "Raleigh-Durham"). Pronouns ("he/him"), words that towns happen to share but
    profiles use for something else ("Asia", "North", "Spring"), "AI" and "ML" beside a place, and words like
    "Remote" that name no place are dropped. If notes is a dict, notes["area"] gets the parts found only by
    dropping words that mark a city's surroundings ("Greater Washington"), and notes["segment"] the places each
    part belongs to, numbered: parts joined by commas or brackets are one place and what qualifies it ("Berlin,
    New Hampshire"), while a slash, bar, dash, line or "&" starts another ("SF / Berlin")."""
    known = lambda k: k in cities or k in countries or k in regions or k in codes
    area = set()

    def read(text, depth=0):   # the places a part names, each as a list of keys
        key = place_key(text)
        if not key or key in NOT_PLACES or known(key):
            return [[key]] if key else []
        for form in (key, place_key(text.replace("&", " and "))):   # "Trinidad & Tobago", "St Kitts & Nevis"
            for name in (form, re.sub(r"^st ", "saint ", form), re.sub(r"^saint ", "st ", form)):
                if known(name):
                    return [[name]]
        bare, dropped = key, False
        while not known(bare) and bare not in NOT_PLACES:
            lead = next((w for w in LEAD_WORDS if bare.startswith(w + " ")), None)
            trail = None if lead else next((w for w in TRAIL_WORDS if bare.endswith(" " + w)), None)
            if not lead and not trail:
                break
            dropped = dropped or (lead or trail) in AREA_WORDS
            bare = bare[len(lead) + 1:] if lead else bare[:-len(trail) - 1]
        if known(bare) or bare in NOT_PLACES:
            if dropped:
                area.add(bare)
            return [[bare]]
        words = bare.split()
        for k in (1, 2):
            head, tail = " ".join(words[:-k]), " ".join(words[-k:])
            if head in cities and (tail in countries or tail in regions or tail in codes):
                return [[head, tail]]
        pieces = [p for p in re.split(JOINERS, text) if p.strip()]
        if len(pieces) < 2:   # "Raleigh-Durham": a hyphen joins two places only when both are known
            pieces = [p for p in text.split("-") if p.strip()]
            pieces = pieces if all(known(place_key(p)) for p in pieces) else []
        if len(pieces) > 1 and depth == 0:
            return [place for p in pieces for place in read(p, 1)]
        return [[key]]

    bits = re.split("(%s)" % PART_SPLIT, re.sub(PRONOUNS, ",", location[:LOCATION_LIMIT]))
    parts, where, place = [], {}, 0
    for n in range(0, len(bits), 2):
        place += bool(n and re.search(SEGMENT_SPLIT, bits[n - 1]))
        for k, keys in enumerate(read(bits[n])):
            place += k > 0
            for key in keys:
                parts.append(key)
                where.setdefault(key, set()).add(place)
    parts = [p for p in dict.fromkeys(parts) if p not in NOT_PLACES]
    parts = [p for p in parts if p not in TAGS] if len(parts) > 1 else parts
    if notes is not None:
        notes["area"], notes["segment"] = area, where
    return [p for p in parts if p not in FILLER]


def location_places(location):
    """The places a profile's location names, as one group of candidate cities per place named.

    Every city in a group agrees with each other part of the location that names a country or region, so
    "Santa Clara, CA" is the one in California and "Toronto, CA" the one in Canada. A region code that is
    only a local abbreviation ("MH", "NCR", "SG" for St. Gallen) confirms a place but never rules one out,
    and alone names nothing. Parts that only name a city come first. If the other parts rule out every town
    of such a part: when one of them is itself a town ("Istanbul, Berlin") each town part is a group of its
    own; when one is a code ("Cape Town, SA", "Berlin, NH", "Monza, MB") the location is not understood and
    nothing is returned; when they are names written with the city ("Kent, UK", "Jackson, Wyoming") the city
    part is dropped and the rest is read, but not when they are another place ("Berlin / India"). A name
    counts as a town here unless it names a region that holds none of its towns and more people than they
    do ("Wyoming", "Ontario"). A city's other names that are some other place's own name ("Santa Cruz" for
    Santa Cruz de la Sierra) count only when the rest of the location points at it ("Santa Cruz, Bolivia").
    Otherwise a named region competes with towns of its name when it holds more people than they do
    ("Ontario" is the province, "Manchester" the city), a region and a country of one name compete
    ("Georgia"), and a country named alone stands for all its cities.

    Nothing is returned for what cannot be read with confidence: a code beside a word nothing knows ("Bormio
    (SO)", "Bunnik, UT", "Estes Park, CO"), since most short codes are some other country's too; a postal code
    the table cannot place ("Kent, WA 98032"); a clear city that another place's qualifier would move
    ("London / Toronto, Canada"); a region found only by dropping words that mark a city's surroundings
    ("Greater Washington"); a time of day, a time zone ("EST") or a dotted code ("N.A.") written alone; and a
    three-letter country code written alone unless in capitals ("DEU", not "Mac"). A name read two ways in
    different zones, as regions of two countries ("Punjab") or a region and a big city of the name
    ("Washington"), is one group per reading, which a shown time zone can choose between. A local abbreviation
    that names regions of a city's own country but none holding it ("Tambaú, PB") leaves that city out. A group
    that holds another group's places, as a country holds its capital, and a repeated group are dropped."""
    countries, regions, cities, in_country, in_region, codes, also = load_places()
    notes = {}
    parts = location_parts(location, countries, regions, cities, codes, notes)
    where = notes["segment"]

    def known(p):
        return p in cities or p in countries or p in regions or p in codes

    def nations(p):
        return countries.get(p, ())

    def named(p):   # names a country or region, and so rules out places elsewhere
        return p in countries or p in regions

    def is_code(p):   # a country's or region's code, as against a name ("UK", "England")
        up = p.upper()
        return (up in countries.get(p, ()) or (len(p) == 3 and p not in KEEP_CODES and p in countries)
                or any(code == up for _, code in regions.get(p, ())))

    def code(p):   # any short code: a country's or region's, a region's two-letter abbreviation, a local one
        return (p in codes and not named(p)) or (len(p) <= 3 and is_code(p)) or (len(p) == 2 and p in regions)

    def people(places):
        return sum(max(pl.people, 1) for pl in places)

    def outweighed(p):   # names a region that holds none of its towns and more people than they do ("Wyoming")
        towns = cities.get(p, ())
        return any(not any((t.country, t.region) == key for t in towns)
                   and people(in_region.get(key, ())) > people(towns) for key in sorted(regions.get(p, ())))

    parts = [p for p in parts if p not in notes["area"] or not outweighed(p)]
    lone = len(parts) == 1
    raw = [s for s in re.split(PART_SPLIT, location[:LOCATION_LIMIT]) if s.strip()]
    loud = {place_key(s) for s in raw if s.strip().isupper()}
    dotted = {place_key(s) for s in raw if re.fullmatch(r"\s*[^\W\d_](?:\s*\.\s*[^\W\d_])+\s*\.?\s*", s)}
    if lone and (parts[0] in LONE_WORDS or parts[0] in dotted and (code(parts[0]) or len(parts[0]) < 3
                                                                  and parts[0] not in countries)):
        return []
    if lone and len(parts[0]) == 3 and parts[0] in countries and parts[0] not in KEEP_CODES | loud:
        return []
    unknown = [i for i, p in enumerate(parts) if not known(p)]
    if any(len(w) >= 3 and any(c.isdigit() for c in w) for i in unknown for w in parts[i].split()):
        return []
    if unknown and all(code(p) for p in parts if known(p)):
        return []

    def only_code(p):   # a local abbreviation beside other parts, which only confirms
        return p in codes and not named(p) and not lone

    def short_code(p):   # a country's code that is also a region's ("CO" is Colombia and Colorado)
        return not lone and len(p) <= 3 and p in countries and (p in regions or p in codes)

    def read(parts):
        judges = {q: (frozenset(nations(q)), frozenset(regions.get(q, ())) | frozenset(codes.get(q, ())))
                  for q in parts if named(q)}
        others = [[judges[q] for j, q in enumerate(parts) if j != i and q in judges] for i in range(len(parts))]
        near = [[judges[q] for j, q in enumerate(parts) if j != i and q in judges
                 and where.get(q, set()) & where.get(parts[i], set())] for i in range(len(parts))]

        def agrees(place, i, among=others):
            key = (place.country, place.region)
            return all(place.country in ns or key in rs for ns, rs in among[i])

        def towns(i, p, table, ns=()):
            return {pl.id: pl for pl in table.get(p, ()) if (not ns or pl.country in ns) and agrees(pl, i)}

        def fitting(i, p):   # a country's name is a town abroad only if the rest points there ("Armenia, Quindio")
            found = towns(i, p, cities, nations(p))
            if found or not others[i]:
                return found
            return towns(i, p, also, nations(p)) or towns(i, p, cities)

        # each part's own towns, whatever the other parts say, for when they rule each other out; a part that
        # names a region outweighing its towns ("Washington", "Oregon") is not read as those towns
        own = {p: {pl.id: pl for pl in cities.get(p, ()) if not nations(p) or pl.country in nations(p)}
               for p in parts if not only_code(p)}
        town = [p for p in parts if own.get(p) and not outweighed(p)]
        city = [i for i, p in enumerate(parts) if p in cities and not named(p) and not only_code(p)]
        if city:
            groups = [fitting(i, parts[i]) for i in city]
            for i, group in zip(city, groups):   # another place's qualifier moved a clear city elsewhere
                if group and len(near[i]) < len(others[i]):   # ("London / Toronto, Canada" is not London, Ontario)
                    plain = clear_zone([pl for pl in cities.get(parts[i], ()) if agrees(pl, i, near)])
                    moved = clear_zone(group.values())
                    if plain and (moved is None or rules_id(moved) != rules_id(plain)):
                        return []
            if all(groups):
                return groups
            rulers = [q for q in parts if named(q)]
            if any(q in town for q in rulers):   # a part that rules the city out is a town itself
                return [own[p] for p in town]
            out = {i for i, g in zip(city, groups) if not g}
            if any(is_code(q) or code(q) for q in rulers):
                return []
            if any(not where.get(parts[i], set()) & where.get(q, set()) for i in out for q in rulers):
                return []   # the city and what rules it out are two places ("Berlin / India")
            return read([p for i, p in enumerate(parts) if i not in out])
        groups, found = [], False
        for i, p in enumerate(parts):
            if not named(p):
                continue
            group = {} if found else fitting(i, p)   # "Kent, Washington": the first part is the town
            found = found or bool(group)
            if short_code(p):   # beside other parts, "CO" or "LA" is read only as a town ("LA, CA")
                groups += [group] if group else []
                continue
            alone, lands = people(group.values()), {}
            for key in sorted(regions.get(p, ())):   # each region of the name that outweighs its towns, by country
                if not any((pl.country, pl.region) == key for pl in group.values()):
                    pool = {pl.id: pl for pl in in_region.get(key, ()) if agrees(pl, i)}
                    if people(pool.values()) > alone:
                        lands.setdefault(key[0], {}).update(pool)
            pools = {k: pl for land in lands.values() for k, pl in land.items()}
            zone = clear_zone(list(group.values()) + list(pools.values())) if pools else None
            # a name read two ways in different zones is one group per reading, which a shown time zone can choose
            # between: regions of two countries ("Punjab"), or a region and a big city of the name ("Washington")
            if len({rules_id(z) if z else None for z in map(clear_zone, map(dict.values, lands.values()))}) > 1:
                groups += [g for g in [group] + list(lands.values()) if g]
                continue
            if pools and any(pl.people >= BIG_TOWN and (zone is None or rules_id(pl.zone) != rules_id(zone))
                             for pl in group.values()):
                groups.append(group)
                group = {}
            group.update(pools)
            if p in regions:
                group.update((pl.id, pl) for cc in sorted(nations(p)) for pl in in_country.get(cc, ())
                             if agrees(pl, i))
            if group:
                groups.append(group)
        if groups:
            return groups
        if len(town) > 1:   # named places that rule each other out ("Tokyo, Seoul"), not "Washington, Oregon"
            return [own[p] for p in town]
        for i, p in enumerate(parts):
            land = {pl.id: pl for cc in sorted(nations(p)) for pl in in_country.get(cc, ()) if agrees(pl, i)}
            if short_code(p):
                area = {pl.id: pl for key in sorted(codes.get(p, ())) for pl in in_region.get(key, ())
                        if agrees(pl, i)}
                a, n = people(area.values()), people(land.values())
                land = {} if p in regions or CODE_SHARE * n <= a <= 2 * n else area if a > n else land
            if land:
                groups.append(land)
        if not groups and not any(named(p) or p in cities for p in parts):
            groups = [{pl.id: pl for key in sorted(codes[p]) for pl in in_region.get(key, ())}
                      for p in parts if only_code(p)]
        return groups

    groups = []
    for group in read(parts):
        for p in parts:   # a local abbreviation keeps the places it confirms, if it confirms any, and a group
            if only_code(p):   # it contradicts, one in its country but none in its regions, is not read ("Tambaú, PB")
                hit = {k: pl for k, pl in group.items() if (pl.country, pl.region) in codes[p]}
                lands = {cc for cc, _ in codes[p]}
                group = hit or ({} if any(pl.country in lands for pl in group.values()) else group)
        if group:
            groups.append(group)
    sets = [frozenset(g) for g in groups]
    return [list(g.values()) for k, g in enumerate(groups)
            if sets[k] not in sets[:k] and not any(s < sets[k] for s in sets)]


_rules, _rule_ids = {}, {}


def zone_rules(zone):
    """A zone's offset from UTC, in minutes, at noon UTC on every day of RULES_DAYS, or None if this
    machine has no rules for it. The offset is read once a week and on every day of a week in which it
    changes, so a change undone within the same week would not be seen; no zone in the place table has had
    one since 2005."""
    got = _zone(zone)
    return got and got[1]


def rules_id(zone):
    """A small number that two zones share exactly when they count days alike: their zone_rules are equal and
    their clocks change at the same minutes, so Asia/Beirut, which changes at local midnight, is not
    Europe/Athens, which changes at 01:00 UTC on the same days. None if the machine has no rules for it."""
    got = _zone(zone)
    return got and got[0]


def _zone(zone):
    if zone not in _rules:
        try:
            tz, seen = zoneinfo.ZoneInfo(zone), {}
            epoch = dt.date(1970, 1, 1).toordinal()

            def offset(minute):   # the zone's offset from UTC, in minutes, at a minute counted from 1970
                if minute not in seen:
                    seen[minute] = int(dt.datetime.fromtimestamp(minute * 60, tz).utcoffset().total_seconds()) // 60
                return seen[minute]

            def noon(day):
                return offset((day - epoch) * 1440 + 720)

            first, last = RULES_DAYS[0], RULES_DAYS[1] - 1
            rules, changes = [], []
            for start in range(first, last, 7):
                end = min(start + 7, last)
                if noon(start) == noon(end):
                    rules += [noon(start)] * (end - start)
                    continue
                for day in range(start, end):
                    rules.append(noon(day))
                    if noon(day) != noon(day + 1):   # the first minute after this noon with the next noon's offset
                        lo, hi = (day - epoch) * 1440 + 720, (day + 1 - epoch) * 1440 + 720
                        while hi - lo > 1:
                            mid = (lo + hi) // 2
                            lo, hi = (mid, hi) if offset(mid) == noon(day) else (lo, mid)
                        changes.append(hi)
            rules = tuple(rules + [noon(last)])
            _rules[zone] = _rule_ids.setdefault((rules, tuple(changes)), (len(_rule_ids), rules))
        except (AttributeError, ValueError, OSError, KeyError, OverflowError):   # KeyError: ZoneInfoNotFoundError
            _rules[zone] = None
    return _rules[zone]


def clear_zone(places):
    """The zone whose rules cover at least CLEAR_SHARE of the people in these places, or None. Zones that
    count days alike are one here, as America/New_York and America/Detroit are; the zone named is the one
    of its biggest place."""
    people, biggest = {}, {}
    for place in places:
        rid = rules_id(place.zone)
        if rid is None:
            continue
        n = max(place.people, 1)
        people[rid] = people.get(rid, 0) + n
        if (n, place.zone) > biggest.get(rid, (0, "")):
            biggest[rid] = (n, place.zone)
    if not people:
        return None
    top = max(people, key=people.get)
    return biggest[top][1] if people[top] >= CLEAR_SHARE * sum(people.values()) else None


def zone_offset(zone, now):
    """A zone's offset from UTC at now, in minutes."""
    return int(dt.datetime.fromtimestamp(now, zoneinfo.ZoneInfo(zone)).utcoffset().total_seconds()) // 60


def shared_zone(groups):
    """With several places named, the zone whose rules cover at least JOINT_SHARE of the people of every one
    of them, when exactly one zone's rules do ("Cambridge / Boston" is Boston's), named by its biggest place;
    otherwise None."""
    common = None
    for group in groups:
        people = {}
        for place in group:
            rid = rules_id(place.zone)
            if rid is not None:
                people[rid] = people.get(rid, 0) + max(place.people, 1)
        total = sum(people.values())
        share = {rid for rid, n in people.items() if n >= JOINT_SHARE * total}
        common = share if common is None else common & share
    if not common or len(common) != 1:
        return None
    rid = common.pop()
    return max(((max(p.people, 1), p.zone) for g in groups for p in g if rules_id(p.zone) == rid))[1]


def local_zone(offset, location, now, seen=None):
    """The time zone days are counted in. offset is the profile's shown time zone, in minutes from UTC,
    read at seen, and always wins: the location only chooses among the zones with that offset then, which
    fixes daylight saving for past days, and "USA" at UTC-7 in summer is Los Angeles because that zone's
    rules cover 75% of the people there, so the choice can differ between a summer and a winter run. A
    location that names places in different zones ("SF / NYC") chooses nothing, and one that names places a
    zone covers well ("Cambridge / Boston") chooses that zone. With no shown time zone, the location's own
    zone. With neither, or no clear answer, the shown offset fixed for all past days, so their daylight
    saving is ignored, or UTC."""
    try:
        groups = location_places(location) if location else []
        if offset is not None:
            instants, fits = {now, now if seen is None else seen}, {}
            for zone in {p.zone for g in groups for p in g}:
                fits[zone] = rules_id(zone) is not None and any(zone_offset(zone, t) == offset for t in instants)
            groups = [[p for p in g if fits[p.zone]] for g in groups]
            sets = [frozenset(p.id for p in g) for g in groups]
            groups = [g for k, g in enumerate(groups) if g and sets[k] not in sets[:k]]
        zones = [clear_zone(g) for g in groups]
        if zones and all(zones) and len({rules_id(z) for z in zones}) == 1:
            biggest = max(range(len(groups)), key=lambda k: sum(max(p.people, 1) for p in groups[k]))
            return zoneinfo.ZoneInfo(zones[biggest])
        zone = shared_zone(groups) if len(groups) > 1 else None
        if zone:
            return zoneinfo.ZoneInfo(zone)
    except Exception:   # this only refines how days are counted, so nothing in it may stop the run
        pass
    if offset is not None:
        return dt.timezone(dt.timedelta(minutes=offset))
    return dt.timezone.utc


def zone_database():
    """Whether this Python has time zone rules at all (Windows needs the tzdata package for them)."""
    try:
        zoneinfo.ZoneInfo("America/New_York")
        return True
    except Exception:
        return False


class GitHubOnly(urllib.request.HTTPRedirectHandler):
    """Follows a redirect only to another https page on github.com; any other is refused as an error."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if target.scheme != "https" or target.hostname != "github.com":
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def profile_page(owner, deadline, into):
    """Reads the owner's public profile page into the list into, as (bytes, when read), unless it is not
    from github.com over https, is larger than PROFILE_LIMIT or is not all read by deadline. Each read waits
    at most until deadline, so a page sent slowly cannot outlast it."""
    request = urllib.request.Request("https://github.com/" + owner, headers={"User-Agent": "coderprint"})
    body = bytearray()
    try:
        with urllib.request.build_opener(GitHubOnly).open(request, timeout=PROFILE_TIMEOUT) as page:
            final = urllib.parse.urlsplit(page.geturl())
            if final.scheme != "https" or final.hostname != "github.com":
                return
            while len(body) <= PROFILE_LIMIT:
                left = deadline - time.monotonic()
                if left <= 0:
                    return
                try:
                    page.fp.raw._sock.settimeout(left)
                except AttributeError:
                    pass
                chunk = page.read1(1 << 16)
                if not chunk:
                    break
                body += chunk
    except Exception:   # any failure to read is a page not read
        return
    if len(body) <= PROFILE_LIMIT and time.monotonic() <= deadline:
        into.append((bytes(body), time.time()))


def profile_offset(owner):
    """The offset from UTC, in minutes, of the local time GitHub shows on the owner's public profile, and
    when it was read; None when the profile shows none, shows two that differ, or cannot be read within
    PROFILE_TIMEOUT, redirects and slow replies included. The page is fetched signed out, as any visitor
    sees it, and only over https from github.com."""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner or ""):
        return None
    deadline, read = time.monotonic() + PROFILE_TIMEOUT, []
    reader = threading.Thread(target=profile_page, args=(owner, deadline, read), daemon=True)
    reader.start()
    reader.join(max(0.0, deadline - time.monotonic()) + 0.5)
    if not read:
        return None
    body, seen = read[0]
    found = set()
    at = body.find(b"<profile-timezone")
    while at >= 0:   # every element, each byte scanned a bounded number of times
        after = at + 1   # not an element (a longer tag's name, or text): look again from the next byte
        if body[at + 17:at + 18] in (b" ", b"\t", b"\r", b"\n", b"/", b">"):   # not <profile-timezone-tooltip>
            end = body.find(b">", at, at + 2048)
            if end < 0:   # a tag left open: go on from the last tag begun within reach, else past it
                end = at + 2048
                after = body.rfind(b"<", at + 1, end)
                after = after if after >= 0 else end
            else:
                after = end
            m = re.search(rb'\sdata-hours-ahead-of-utc="([^"]*)"', body[at:end])
            if m:
                number = re.fullmatch(rb"[-+]?[0-9]{1,2}(?:\.[0-9]{1,4})?", m.group(1))
                minutes = float(number.group()) * 60 if number else None
                good = minutes is not None and minutes == round(minutes) and -720 <= minutes <= 840
                found.add(int(round(minutes)) if good and not round(minutes) % 15 else None)
        at = body.find(b"<profile-timezone", max(after, at + 1))
    if len(found) != 1 or None in found:
        return None
    return found.pop(), seen


def profile_location(owner):
    """The location on the owner's public profile, or "" when there is none or it cannot be read. Reading the
    profile is what RESERVE is kept for, so the query may use it, all but what drawing and writing need."""
    try:
        data = gql("query($owner: String!) { repositoryOwner(login: $owner) { "
                   "... on User { location } ... on Organization { location } } }",
                   timeout=LOCATION_TIMEOUT, reserve=RESERVE - PROFILE_TIMEOUT - LOCATION_TIMEOUT, owner=owner)
    except (RuntimeError, ValueError):
        return ""
    found = data.get("repositoryOwner") if isinstance(data, dict) else None
    location = found.get("location") if isinstance(found, dict) else None
    return location[:LOCATION_LIMIT] if isinstance(location, str) else ""


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
    """A lossless PNG from rows of RGB bytes, with the standard library only: indexed, at the fewest bits a
    pixel needs, when there are 256 colors or fewer, and otherwise RGB with each row's filter chosen by
    the usual smallest-sum rule; the smaller of that and no filtering at all is kept."""
    rows = [bytes(r) for r in rows]
    colors = Counter(r[k:k + 3] for r in rows for k in range(0, len(r), 3))

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xffffffff)

    if len(colors) <= 256:
        palette = [c for c, _ in colors.most_common()]
        index = {c: k for k, c in enumerate(palette)}
        data = [bytes(index[r[k:k + 3]] for k in range(0, len(r), 3)) for r in rows]
        bpp, ctype = 1, 3
        depth = next(b for b in (1, 2, 4, 8) if len(palette) <= 1 << b)
        if depth < 8:
            per = 8 // depth
            packed = []
            for r in data:
                out = bytearray()
                for k in range(0, len(r), per):
                    byte = 0
                    for j in range(per):
                        byte = (byte << depth) | (r[k + j] if k + j < len(r) else 0)
                    out.append(byte)
                packed.append(bytes(out))
            data = packed
        extra = chunk(b"PLTE", b"".join(palette))
    else:
        data, bpp, ctype, depth, extra = rows, 3, 2, 8, b""

    def filtered(prev, cur):
        best = None
        for ft in range(5):
            out = bytearray([ft])
            for k in range(len(cur)):
                a = cur[k - bpp] if k >= bpp else 0
                b = prev[k] if prev is not None else 0
                c = prev[k - bpp] if prev is not None and k >= bpp else 0
                if ft == 0:
                    p = 0
                elif ft == 1:
                    p = a
                elif ft == 2:
                    p = b
                elif ft == 3:
                    p = (a + b) >> 1
                else:
                    pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                    p = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                out.append((cur[k] - p) & 0xff)
            score = sum(v if v < 128 else 256 - v for v in out[1:])
            if best is None or score < best[0]:
                best = (score, out)
        return bytes(best[1])

    candidates = [zlib.compress(b"".join(b"\x00" + r for r in data), 9)]
    if depth == 8:   # filters work on whole bytes, so packed indexes gain nothing from them
        prev, parts = None, []
        for r in data:
            parts.append(filtered(prev, r))
            prev = r
        candidates.append(zlib.compress(b"".join(parts), 9))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, depth, ctype, 0, 0, 0))
            + extra + chunk(b"IDAT", min(candidates, key=len)) + chunk(b"IEND", b""))


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
    """The wordmark's path data and frame from design/wordmark.svg, or None in the plain look, which has
    none. When design/ is there, a missing or unreadable wordmark is an error, not a panel quietly drawn
    without it."""
    if not os.path.isdir(DESIGN_DIR):
        return None
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
    """The coderprint wordmark in the bottom right corner, over the watermark, in the headline's color;
    nothing in the plain look."""
    if word is None:
        return ""
    d, (bx, by, bw, bh) = word
    s = WORDMARK_WIDTH / bw
    # the glow wraps the path rather than sitting on it, so the filter is not scaled with the letters
    return glow("glowS", '<path d="%s" fill="%s" fill-rule="evenodd" transform="translate(%.2f %.2f) scale(%.5f) '
                'translate(%.2f %.2f)"/>' % (relative_path(d), TEXT, WORDMARK_RIGHT - WORDMARK_WIDTH,
                                             WORDMARK_BOTTOM - bh * s, s, -bx, -by))


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


# ---------------------------------------------------------------- the card as data
# assets/coderprint.json says everything the card says, built from the very values the panels are drawn from,
# with what each figure means, for a reader that is not a person looking at the pictures. Like the panels it
# holds aggregates only, by whole days: never a repository, a path, a commit's text, an address or a time of
# day. Within coderprint/1 fields are only ever added, so a reader ignores the ones it does not know.
SCHEMA = "coderprint/1"
VERSION = "1.2.1"
UPSTREAM_URL = "https://github.com/" + UPSTREAM
DATA_FILE, LEGACY_DATA_FILE = "coderprint.json", "cards.json"
DATA_URL = None   # the data file's public address, set by main, which the panels name in their metadata
DATA_NOTE = ("Machine-readable: the card's figures, what each means and how it was counted, schema %s, at %s"
             % (SCHEMA, "{url}"))
# What each figure means, once, for every figure that refers to it (#/definitions/<term>). "means" is the
# definition, "method" how it is counted where that matters, "leaves_out" what it never includes and
# "limits" what it cannot tell.
DEFINITIONS = {
    "line_of_code": {
        "means": "A line of a source file that is neither blank nor only a comment, judged by the comment syntax of "
                 "the file's language; a line of code with a comment after it is code, and so is every line of a "
                 "string. A Python docstring, or any string standing alone as a statement, is a comment.",
        "method": "Each file version is read whole, as the language reads it: Python by its own tokenizer, the C "
                  "family and most others with their strings and character literals followed and nested comments "
                  "nested. A line added to a file reads as the whole new version reads it, so a line added inside a "
                  "comment or string opened above it reads alike in written and in use. An extension several "
                  "languages share counts, drawn as Other, where they all comment alike (.h, .m, .fs and .v).",
        "leaves_out": "Markdown, TeX, YAML, TOML, plain text, the prose of a literate source, notebooks, data files "
                      "(JSON, CSV, XML, SVG and the like), any file whose name or extension no language claims, and "
                      "one whose extension several languages share and comment differently (.pl); vendored folders, a "
                      "build's output, generated files (by folder, by name, or by a generator's mark in their first "
                      "lines), lock files, submodules, symbolic links, and the paths a repository's .gitattributes "
                      "marks linguist-vendored, linguist-generated or linguist-documentation.",
        "limits": "A few languages whose strings cannot be followed line by line (shell, Perl, Ruby, MATLAB and "
                  "others) are read by their comment syntax at the start of each line only, so a comment opened "
                  "after code there counts as code. Where a language has no known comment syntax, every line that "
                  "is not blank is code. approximate_loc says how many of a figure's lines rest on a "
                  "fallback: a Python file its tokenizer could not read, a Rust file whose test code could not be "
                  "told apart (its lines then count by its path alone), a file version no diff could be read "
                  "against, or a repository whose diffs could not be read, whose added lines count as they are. A "
                  "Python file its tokenizer cannot read is read line by line instead, where a line that starts "
                  "with three quotes counts as a comment, and so do the lines up to the closing three: a docstring "
                  "above all, but any string written so. A file version no diff could be read against is read hunk "
                  "by hunk, where a hunk that starts inside a block comment opened above it is read as code."},
    "written": {
        "means": "Lines of code the account's owner added in the window, each file version counted once: the first "
                 "time its exact content appears in any of the account's repositories or branches.",
        "method": "Read from each commit's own diff. A line rewritten counts again; deleting a line takes nothing off. "
                  "A file moved to a new name while being edited adds only the lines it changed, whether or not git "
                  "paired the two names, and a block of 3 or more lines moved within one commit, inside its file or "
                  "into another, spacing aside (so a block only re-indented is moved too), adds nothing. For a "
                  "repository whose diffs could not be read, git's own count of "
                  "added lines stands instead, comments and blank lines included (approximate_loc; "
                  "scope.repositories.read_without_line_diffs).",
        "leaves_out": "Commits by other accounts or by automation; reformatting sweeps (ten or more files at once, "
                      "each adding about what it deletes and its changed lines still reading nearly as they did) and "
                      "commits listed in .git-blame-ignore-revs; what a change landed twice lands again (only lines "
                      "its first landing did not count are new); imports (see import); files from a template or from "
                      "a relay copy of coderprint."},
    "import": {
        "means": "An existing codebase brought in, not written: a commit adding more than 500 new files of code, or a "
                 "run of the author's commits to one repository, each adding at least 50 new files of code within an "
                 "hour of the one before, that adds more than 500 in all, as uploading a project through github.com "
                 "100 files at a time does. Only files of code count toward the 500: Markdown, YAML, TOML, plain text "
                 "and files no language claims do not, and neither does a file the commit moved from one it deleted.",
        "method": "It counts as a commit and an active day but adds no lines, written or in use. "
                  "left_out.imports.loc_skipped counts the lines of code its files add, read as written is read; of "
                  "them, approximate_loc are counted as git counts lines, blank and comment lines included, for a "
                  "repository whose diffs could not be read.",
        "limits": "A codebase brought in more slowly than that, in commits more than an hour apart or of fewer than 50 "
                  "files each, counts as written."},
    "in_use": {
        "means": "Lines of code standing today at the head of each repository's default branch that the owner wrote "
                 "in the window, where wrote means exactly the lines counted as written: each written line counts in "
                 "use at most once across all the account's repositories, so in use never exceeds written, and a file "
                 "copied into a second repository, or a fork, is in use once. An archived repository's head is left "
                 "out (scope.repositories.archived); its history still counts as written. Wherever lines are compared "
                 "by their text (see method), the text is compared with its ends trimmed and every run of whitespace "
                 "made one space, so a re-indented line matches but b=2 does not match b = 2.",
        "method": "Traced through each repository's history: every file version's lines are the version before's with "
                  "the diff applied, so each line keeps the change that added it, and counts when that line was "
                  "counted as written in the window, whatever its text. A line from anyone else's commit, an import, "
                  "a template or a relay copy, or from the owner's own before the window, counts nothing. A "
                  "reformatting sweep, whoever made it, a block moved within one commit, a change landed again and a "
                  "squash of a kept branch write nothing, and hand each line they change on to the line they leave in "
                  "its place. "
                  "A merge's lines take the origin of the same text in the version it merged in. A line whose origin "
                  "the history cannot give (one in a file version no diff could be read against, one only a merge's "
                  "own conflict resolution wrote, or one in a version only a merge made where git is too old to show "
                  "merges) is matched instead by its text, compared as means says, against the written lines no traced "
                  "line took, a line of its own kind (production or tests) and in a file the owner changed first. "
                  "traced_loc counts the lines traced and matched_by_text_loc those matched by text.",
        "limits": "A line matched by text can match a line of the same text the owner wrote elsewhere, a lone closing "
                  "brace above all, so only matched_by_text_loc rests on that approximation. A squash merge is told "
                  "from a direct commit by its lines alone (at least 80% of its added lines, among them 3 different "
                  "ones, waiting on a kept branch), so a direct commit made almost wholly of an abandoned branch's "
                  "lines counts as landing them. It says nothing about whether the code is deployed or run. A "
                  "repository whose head or whose diffs could not be read adds nothing in use "
                  "(scope.repositories.read_without_head, read_without_line_diffs), so for such an account in use "
                  "can fall below what still stands."},
    "production": {"means": "Lines in use that are not test code."},
    "test": {
        "means": "Lines in use that are test code: in a folder of tests (such as tests, __tests__, spec, e2e, "
                 "MyApp.Tests or androidTest), in a file named as a test (test_x.py, x_test.go, x.test.ts, XTest.java, "
                 "conftest.py, and x_spec.rb or x.spec.ts in the languages whose test frameworks name them so), or in "
                 "Rust code compiled only in tests (a #[cfg(test)] or #[cfg(all(test, ...))] item or module, inline or "
                 "in its own file).",
        "limits": "Decided by where a line lives and by naming conventions, not by what it does. Rust code under a "
                  "cfg predicate that can hold outside tests, such as any(test, feature = \"x\"), counts as "
                  "production, and a module's file is found by rustc's own rules, so one only a macro declares is "
                  "test code only inside its test module's folder."},
    "retained_fraction": {
        "means": "Lines in use divided by lines written: how much of the window's writing the heads still hold.",
        "limits": "A ratio of two totals, so it carries the limits of both. In use counts only lines counted as "
                  "written, each once, so the ratio is never more than 1."},
    "commit": {
        "means": "A commit that is not a merge, on any branch (gh-pages, and what only it holds, only when it is the "
                 "default), by the owner: counted once however many repositories hold it, and once when the same "
                 "change landed twice (one author, author second and subject, and most of the same lines of code). "
                 "An import and a commit listed in .git-blame-ignore-revs still count, though they add no lines "
                 "written, and so does a reformatting sweep, whose reformatted files add none.",
        "leaves_out": "Commits by other accounts or by automation (a bot, a workflow, or a bot or coding agent "
                      "committing under an identity of its own that no account holds); commits whose every file "
                      "version is one from a template or from a relay copy of coderprint; commits git's log gave in a "
                      "form that could not be read (left_out.unparsed_commits); and commits dated more than a day in "
                      "the future."},
    "unverified_author": {
        "means": "An author address GitHub was not asked about, since a run asks about at most 1,000 addresses, those "
                 "likeliest to change what counts first, or did not answer for.",
        "method": "Its commits count as the owner's only under the owner's own name or login, never as the only "
                  "address in a repository, as an address GitHub says belongs to no account would. addresses counts "
                  "them, and commits the commits counted under them.",
        "limits": "Such an address may belong to another account whose holder uses the owner's name."},
    "active_day": {"means": "A day with at least one counted commit."},
    "streak": {"means": "A run of consecutive active days. The current streak may end yesterday, since today is not "
                        "over."},
    "day": {"means": "A whole calendar day in the time zone the owner's public profile gives. When it shows a local "
                     "time: the zone its location names among those at that time's offset, where the location names "
                     "one clearly, and otherwise that offset as it was on the day of the run, fixed for every day, "
                     "so daylight saving is ignored. When it shows none: the zone its location names clearly. "
                     "Otherwise UTC. A run with no time zone database takes no zone from the location, so its days "
                     "fall at the shown offset, fixed, or in UTC. Every time is taken as the start of its day before "
                     "anything is counted, and no time of day, and no zone, is written in this file."},
    "language": {"means": "The language a file counts toward, from its name or extension alone, named and grouped "
                          "much as GitHub Linguist names and groups languages (TSX as TypeScript, HTML templates as "
                          "HTML), with coderprint's own folds: CSS preprocessors count as CSS, prose markups as "
                          "Markdown and SQL dialects as SQL. In share_of_loc and by_slice, Other gathers every "
                          "language under 1% of the window's lines of code. The chart and its legends "
                          "(languages.legend) name at most eight languages and draw every other one as Other too, "
                          "and share_of_loc marks such a language drawn_as Other."},
    "languages_counted": {"means": "Languages with at least 1% of the window's lines of code, Other not among them."},
    "slice": {"means": "One of 52 equal parts of the chart's span, oldest first. The span runs from the start of the "
                       "day of the oldest real work in the window (with no lines of code in it, of the oldest "
                       "commit) to the moment the card was drawn; with neither, it covers the whole window from its "
                       "first moment, or for all time the 24 hours before the card was drawn. It is never shorter "
                       "than 0.05 of a day.",
              "method": "A day of real work holds at least 10 lines of code, or 5% of what the median day with lines "
                        "of code holds, if that is more. Of the oldest three such days, one that is more than a year "
                        "before the next and holds, with every day before it, under 1% of all lines is not where the "
                        "span starts, and neither is any day before it. Commits and lines of code before the span "
                        "count in every headline and stats figure but in no slice: series.commits_before_span and "
                        "series.loc_before_span say how many.",
              "limits": "series.days counts the calendar days from series.from to series.to, both included, and "
                        "slice_days is days / 52. The span really runs to the moment the card was drawn, which is "
                        "not recorded, so it is shorter than days, by less than a day when it starts at the start "
                        "of a day, and a slice shorter than slice_days by as much over 52. For the same reason a "
                        "day near the edge of a slice can fall in the slice on either side of it, depending on the "
                        "hour of the run, as the activity bars draw it."},
}
DATA_PRIVACY = {
    "contains": "Aggregates over every repository counted, by whole days.",
    "never_contains": ["source code", "repository names", "file names or paths", "commit messages", "email addresses",
                       "times of day"],
}


def data_text(card):
    """The data file's text: indented for a person to read, with each list of numbers, such as a series of 52
    slices, on one line."""
    text = json.dumps(card, indent=1, ensure_ascii=False)
    return re.sub(r"\[\s+(-?\d[\d.]*(?:,\s+-?\d[\d.]*)*)\s+\]",
                  lambda m: "[" + ", ".join(v.strip() for v in m.group(1).split(",")) + "]", text) + "\n"


def figure(value, unit, provenance, term, **more):
    """One figure of the data file: its value, its unit, whether it is counted from history (measured),
    computed from other figures (derived) or as drawn (display), and where its meaning is defined."""
    return dict(value=value, unit=unit, provenance=provenance, definition="#/definitions/" + term, **more)


def iso_day(t, zone):
    """The calendar day holding the time t in zone, as YYYY-MM-DD."""
    return moment(t, zone).date().isoformat()


def days_between(first, last):
    """The calendar days from first to last, both YYYY-MM-DD, counting both."""
    return (dt.date.fromisoformat(last) - dt.date.fromisoformat(first)).days + 1


def own_legacy(meta):
    """Whether a cards.json, read by previous_meta, is this script's own from before coderprint.json: every release
    that wrote one gave it the day's palettes as an object and the count of repositories as a whole number. A file
    of that name holding anything else is someone else's, and is never read or removed."""
    count = meta.get("repositories")
    return isinstance(meta.get("palette"), dict) and isinstance(count, int) and not isinstance(count, bool)


def card_data(owner, window, now, zone, start, S, repos, private, data, stats, spark, commits, stream, column,
              presentation, profile=None):
    """The data file's content (see SCHEMA), built from the values the panels are drawn from. start: the
    window's first moment, or -inf for all time; S: the chart's span in days; stats: commits, active days,
    longest streak, current streak and languages counted, as drawn; presentation: what the relay reads;
    profile: the repository the profile README is in, the owner's own name when not given."""
    written, use, prod, tests, P, U = story_figures()
    kept, prod_pct, tests_pct = kept_shares(P, U, (written, prod, tests))
    n_commits, active, longest, current, counted = stats
    readable = sum(1 for r in repos if not (r.get("isDisabled") or r.get("isLocked")))
    totals, small = folded(column)
    grand = float(sum(totals.values()))
    names = sorted(totals, key=lambda l: (l == OTHER, -totals[l], l))
    by_slice = {l: [0] * 52 for l in names}
    for age, lang, n in stream:   # the same slices as the activity bars (see main)
        by_slice[OTHER if lang in small else lang][min(51, max(0, int((S - age) / S * 52)))] += n
    loc = data.get("code") or {}
    rough = sum(n for t, n in loc.get("approximate", ()) if window_holds(t, start, now))
    unsure, authors = data.get("unsure") or (), data.get("authors") or {}
    # of what is in use, how many lines their history placed and how many were matched by their text (see collect);
    # a collect that does not say counts every line as matched, which is what an earlier one did
    traced = min(loc.get("traced", 0), use)
    # The legend as the chart draws it (legend_layers): the biggest languages by name and every other one as Other,
    # each share rounded over those layers in the order the legend lists them, top of the column first, so a tie
    # is settled as the legend settles it (mix_chart). A language has a share as drawn only when the legend draws
    # it as a layer of its own holding exactly its lines; one it draws inside Other is marked so.
    _, layers, amount = legend_layers(totals)
    drawn = percents({l: amount[l] / grand for l in reversed(layers)}) if grand else {}

    def share(l):
        row = {"language": l, "loc": totals[l], "share": round(totals[l] / grand, 4),
               "as_drawn": drawn[l] if amount.get(l) == totals[l] else None}
        if l not in amount:
            row["drawn_as"] = OTHER
        return row

    # Commits left out, over the window when collect gave each one's time, cut by the one test that cuts what is
    # written, in use and imported (window_holds: start is the first whole day main counts, and a commit more than a
    # day ahead of the run never counts), and over the whole history, as collect counts them, when it did not or a
    # time could not be placed; left_out.over says which.
    try:
        left = Counter(why for t, why in data["left_out_times"] if window_holds(t, start, now))
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        left = None
    timed, left = left is not None, left if left is not None else data["left_out"]
    # the chart's span in whole calendar days, from its two dates alone: S runs to the moment of the run, so its
    # fraction of a day, written out, would tell at what time of the owner's day the card was drawn
    s_from, s_to = iso_day(now - S * 86400, zone), iso_day(now, zone)
    span = days_between(s_from, s_to)
    return {
        "schema": SCHEMA,
        "schema_note": "Fields are only ever added within %s; ignore any you do not know. #/definitions says what each "
                       "term means." % SCHEMA,
        "generator": {"name": "coderprint", "version": VERSION, "source": UPSTREAM_URL,
                      "methodology": UPSTREAM_URL + "#how-it-counts"},
        "as_of": iso_day(now, zone),
        "account": {"login": owner, "profile": "https://github.com/" + owner},
        "window": {"id": window, "name": WINDOWS[window][1], "days": WINDOWS[window][2],
                   # the first day counted: main starts the window at a whole day (first_day), and a start that
                   # is not one would count from the next
                   "from": iso_day(first_day(start, zone), zone) if start != float("-inf") else None,
                   "to": iso_day(now, zone),
                   "definition": "#/definitions/day"},
        "scope": {
            "repositories": {"visible": len(repos), "read": readable - data["unread"] - len(unsure),
                             "unread": data["unread"],
                             "read_without_line_diffs": loc.get("unread", 0),
                             "read_without_head": loc.get("heads_unread", 0),
                             "read_without_gitattributes": loc.get("attributes_unread", 0),
                             "archived": loc.get("archived", 0),
                             "left_out_as_unattributable": len(unsure)},
            "owned_only": not any(repo_owner(owner, r).lower() != owner.lower() for r in repos), "forks": "excluded",
            "organization_repositories": sum(repo_owner(owner, r).lower() != owner.lower() for r in repos),
            "organization_only": os.environ.get("CARDS_ORGANIZATION_ONLY", "false").strip().lower() == "true",
            # the repository named after the account is left out (list_repositories): a person's profile
            # repository, but not an organization's, which is its .github repository
            "profile_repository": "excluded" if (profile or owner).lower() == owner.lower() else "counted",
            "visibility": "public and private" if private else "public only",
            "branches": "every branch; gh-pages only when it is the default",
            "authorship": "the personal owner's own commits, including configured organizations; an organization's own card counts every member",
            # whether GitHub was asked whose each commit is: true in every file written, since a run that could not
            # ask keeps the existing panels and this file with them (see collect's "unchecked" and main)
            "authorship_checked": not data.get("unchecked"),
            "organization_authorship": "GitHub-linked owner identity or explicitly listed, non-conflicting address",
            "declared_authored_uploads": {"commits": len(data.get("authored_imports", [])),
                                         "loc": sum(n for _, n in data.get("authored_imports", [])),
                                         "provenance": "owner declaration, filtered by authorship and file exclusions"},
            "unverified_authors": {"addresses": authors.get("unknown", 0), "commits": authors.get("commits", 0),
                                   "definition": "#/definitions/unverified_author"}},
        "quantity": {
            "written_loc": figure(written, "lines of code", "measured", "written", approximate_loc=min(rough, written)),
            "in_use_loc": figure(use, "lines of code", "measured", "in_use", equals="production_loc + test_loc",
                                 approximate_loc=min(loc.get("approximate_in_use", 0), use),
                                 traced_loc=traced, matched_by_text_loc=use - traced),
            "production_loc": figure(prod, "lines of code", "measured", "production"),
            "test_loc": figure(tests, "lines of code", "measured", "test"),
            "retained_fraction": figure(round(use / float(written), 4) if written else None, "fraction", "derived",
                                        "retained_fraction", equals="in_use_loc / written_loc"),
            # the percentages as whole numbers, and as the ring's middle writes them, which says <1% for a share
            # above nothing that rounds to 0
            "as_drawn": {"provenance": "display", "written": fmt(written), "in_use": fmt(use),
                         "production": fmt(prod), "tests": fmt(tests), "kept_percent": kept,
                         "production_percent": prod_pct, "test_percent": tests_pct,
                         "kept_label": share_label(kept, U), "production_label": share_label(prod_pct, P),
                         "test_label": share_label(tests_pct, U - P)},
        },
        "activity": {
            "commits": figure(n_commits, "commits", "measured", "commit"),
            "active_days": figure(active, "days", "measured", "active_day"),
            "longest_streak_days": figure(longest, "days", "measured", "streak"),
            "current_streak_days": figure(current, "days", "measured", "streak"),
            "series": {"provenance": "measured", "definition": "#/definitions/slice", "slices": 52,
                       "from": s_from, "to": s_to, "days": span, "slice_days": round(span / 52.0, 2),
                       "loc_written": list(spark), "commits": list(commits),
                       # what the headline counts and no slice holds: the window before the span starts
                       "commits_before_span": n_commits - sum(commits), "loc_before_span": written - sum(spark)},
        },
        "languages": {
            "counted": figure(counted, "languages", "derived", "languages_counted", minimum_share=FOLD),
            "share_of_loc": [share(l) for l in names],
            "legend": {"provenance": "display", "definition": "#/definitions/language",
                       "as_drawn": {l: drawn[l] for l in layers}},
            "by_slice": {"provenance": "measured", "definition": "#/definitions/slice", "unit": "lines of code",
                         "loc": by_slice},
        },
        "left_out": {
            "over": {"commits": "window" if timed else "whole history", "imports": "window",
                     "future_dated_file_versions": "whole history", "unparsed_commits": "whole history"},
            "commits": {"by_other_accounts": left.get("others", 0), "automation": left.get("automation", 0),
                        "landed_twice": left.get("landed_twice", 0), "template_or_relay_copy": left.get("copied", 0)},
            "imports": {"commits": sum(1 for t in data["imports"] if window_holds(t, start, now)),
                        "loc_skipped": sum(n for t, n in data["import_lines"] if window_holds(t, start, now)),
                        "approximate_loc": sum(n for t, n in loc.get("approximate_imports", ())
                                               if window_holds(t, start, now)),
                        "definition": "#/definitions/import"},
            "future_dated_file_versions": sum(1 for t, _, _ in data["events"] if t > now + FUTURE_SLACK),
            "unparsed_commits": data["mismatched"],
        },
        "privacy": DATA_PRIVACY,
        "definitions": DEFINITIONS,
        "presentation": presentation,
    }


def caption_parts(private):
    """What the panel counts, in three parts, each short enough for a line of the compact caption and all three
    for one line of the wide one: whose repositories, which of them, and what a line is (a line added in a new
    file version, so a rewrite counts again)."""
    scope = "your code, no forks" if organization_settings()[0] else "own repos, no forks"
    return [scope, "public + private" if private else "public only", "each file version counted once"]


def panel_svg(theme, window, S, c, new_lines, spark, rows, stream, column, has_history, mark_polys, turn,
              private, word, recent_day=None, since=None, commits=None):
    """One version of a theme's panel (theme: a key of THEMES). since: the day the chart starts, written out
    (see day_label); commits: commits in each of the activity bars' slices."""
    use_theme(theme)
    chart, grow = stream_block(window, stream, column, S, c, has_history, recent_day)
    block, story = stats_block(window, S, new_lines, spark, rows, since, commits)
    body = (flattened_mark(mark_polys, turn)
            + theme_strip(theme)
            + block
            + '<line x1="16" y1="176" x2="560" y2="176" stroke="%s"/>' % LINE
            + chart
            + label(16, 437, " · ".join(caption_parts(private)), size=7.5)
            + wordmark(word))
    return document(body, rows, grow + story, words(window, new_lines, spark, rows, column, since))


# The panel's corners are rounded, bar the bottom two when SQUARE_FOOT is set: the compact panel's, which
# the relay sets on a strip, so the background, the grid and the vignette run on into the strip with no
# notch where the two meet.
SQUARE_FOOT = False


def outline(fill):
    """The panel's whole area, PANEL_W x PANEL_H, filled with fill."""
    if not SQUARE_FOOT:
        return '<rect width="%d" height="%d" rx="10" fill="%s"/>' % (PANEL_W, PANEL_H, fill)
    return ('<path d="M0,10A10,10 0 0 1 10,0H%dA10,10 0 0 1 %d,10V%dH0Z" fill="%s"/>'
            % (PANEL_W - 10, PANEL_W, PANEL_H, fill))


def document(body, rows, grow, title_desc):
    """A drawn panel as its SVG file, PANEL_W x PANEL_H: the background and the grid, in a nite the
    glow and the vignette, the title and description for screen readers, the notice and the style sheet."""
    title, desc = title_desc
    defs = ('<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" '
            'stroke="%s" stroke-opacity="%s" fill="none"/></pattern>' % (TEXT, THEME["grid"])
            + (glow_defs() if THEME["dark"] else ""))
    if THEME["dark"]:
        body += outline("url(#vignette)")
    # the monospace stack is named once, on a group around everything, instead of on every label
    mono = ' font-family="%s"' % MONO
    body = "<g%s>%s</g>" % (mono, body.replace(mono, "").replace(' font-weight="400"', ""))
    # the notice is an element, not a comment, so it survives when the relay merges the panel; so is the pointer
    # to the data file, which says in words what the pictures say in pixels
    note = NOTICE + (" " + DATA_NOTE.format(url=DATA_URL) + "." if DATA_URL else "")
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" '
            'aria-labelledby="cp-title cp-desc">\n<title id="cp-title">%s</title><desc id="cp-desc">%s</desc>\n'
            '<metadata>%s</metadata>\n<style>%s</style>\n<defs>%s</defs>\n'
            '%s%s\n'
            '%s\n</svg>\n' % (PANEL_W, PANEL_H, PANEL_W, PANEL_H, esc(title), esc(desc), esc(note),
                              style_sheet(rows, grow), defs, outline(BG), outline("url(#grid)"), body))


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


# ---------------------------------------------------------------- main


def settings():
    """The installer's choices, all checked before any work: window, a pinned theme, the music card (a
    Spotify or an Apple Music user id, never both), relay address, mark."""
    window = os.environ.get("CARDS_WINDOW", "").strip().lower() or "all"
    if window not in WINDOWS:
        raise RuntimeError("CARDS_WINDOW must be one of %s" % ", ".join(WINDOW_ORDER))
    # the old settings, a theme for each mode: every theme now comes in both, so one pin covers both modes,
    # and a run that still sets either stops rather than draw something the installer did not ask for
    old = [name for name in ("CARDS_LIGHT", "CARDS_DARK") if os.environ.get(name, "").strip()]
    if old:
        raise RuntimeError("%s no longer read, since every theme now has a version for light mode and one for "
                           "dark: unset %s, and pin one theme in both with CARDS_THEME (the theme input), one of %s"
                           % (" and ".join(old) + (" are" if len(old) > 1 else " is"),
                              "them" if len(old) > 1 else "it", ", ".join(THEME_ORDER)))
    pin = os.environ.get("CARDS_THEME", "").strip().lower() or None
    if pin and pin not in VARIANTS:
        raise RuntimeError("CARDS_THEME must be one of %s" % ", ".join(THEME_ORDER))
    uid = os.environ.get("CARDS_SPOTIFY_UID", "").strip()
    # today's random ids, and older accounts' user names, which may hold dots, underscores and hyphens: all of them
    # safe in a query string as they are (the relay's UID in lib/compose.js takes the same)
    if uid and not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", uid):
        raise RuntimeError("CARDS_SPOTIFY_UID must be letters, digits, dots, underscores and hyphens only, at most "
                           "64 characters")
    apple = os.environ.get("CARDS_APPLE_MUSIC_UID", "").strip()
    if apple and not re.fullmatch(r"[A-Za-z0-9.]{1,64}", apple):
        raise RuntimeError("CARDS_APPLE_MUSIC_UID must be letters, digits and dots only, at most 64 characters")
    if uid and apple:
        raise RuntimeError("CARDS_SPOTIFY_UID and CARDS_APPLE_MUSIC_UID are both set; the panel shows one music "
                           "card, so set spotify-uid or apple-music-uid, not both")
    relay = os.environ.get("CARDS_RELAY", "").strip().rstrip("/")
    if relay and not re.fullmatch(r"https://[A-Za-z0-9.-]+(/[A-Za-z0-9._/-]*)?", relay):
        raise RuntimeError("CARDS_RELAY must be a plain https address")
    data = " ".join(os.environ.get("CARDS_MARK_DATA", "").split())
    music = ("spotify", uid) if uid else ("apple_music", apple) if apple else None
    return window, pin, music, relay, (mark_outline(data) if data else None), MARK_TURN, load_wordmark()


def previous_meta(path):
    """A JSON file this script wrote last run, or an empty record if it is missing or not a JSON object."""
    try:
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def repositories_last_time():
    """How many repositories the last run saw: from coderprint.json, or from the cards.json runs before it
    wrote (own_legacy), never from anyone else's file of that name; None when neither says."""
    scope = previous_meta(os.path.join(OUT_DIR, DATA_FILE)).get("scope")
    was = scope.get("repositories", {}).get("visible") if isinstance(scope, dict) and isinstance(
        scope.get("repositories"), dict) else None
    if was is None:
        legacy = previous_meta(os.path.join(OUT_DIR, LEGACY_DATA_FILE))
        was = legacy.get("repositories") if own_legacy(legacy) else None
    return was if isinstance(was, int) and not isinstance(was, bool) else None


def marker_lines(text):
    """Where the README's own markers are: the start of each line that is a marker and nothing else (spacing
    aside, indented at most three spaces, as Markdown allows before it reads a line as code), outside fenced
    code, as ([starts], [ends]). A marker quoted in a sentence, a code span or a code fence is text about
    coderprint, not the block."""
    starts, ends, fence, pos = [], [], None, 0
    for line in text.split("\n"):
        opener = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if fence:
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence) \
                    and not line[opener.end():].strip():
                fence = None
        elif opener:
            fence = opener.group(1)
        elif re.fullmatch(r" {0,3}%s[ \t\r]*" % re.escape(README_START), line):
            starts.append(pos)
        elif re.fullmatch(r" {0,3}%s[ \t\r]*" % re.escape(README_END), line):
            ends.append(pos)
        pos += len(line) + 1
    return starts, ends


def new_readme(block, path=None):
    """The profile README (path, README unless given) as bytes, with the panel's block between its markers and
    every other byte as it was: any encoding that keeps ASCII as ASCII (undecodable bytes pass through
    untouched), a byte order mark kept at the very start, and the file's own line endings kept, the marker lines
    included. The markers are the ones alone on their lines outside fenced code (marker_lines). A README that is
    only an earlier unmarked coderprint block is replaced; any other README gets the block on top. Whatever
    would cost the owner text stops the run before any work instead: more than one pair of markers, or half a
    pair; a README in UTF-16 or UTF-32, which a block in UTF-8 would garble; or no README of that name beside
    one of another name (README.rst, readme.md on a case-sensitive file system), which would be left as it is
    while a new file held the panel."""
    path = path or README
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        raw = b""
        folder = os.path.dirname(path) or "."
        try:
            others = [n for n in os.listdir(folder) if n.lower().startswith("readme")
                      and n != os.path.basename(path) and os.path.isfile(os.path.join(folder, n))]
        except OSError:
            others = []
        if others:
            raise RuntimeError("the profile repository's README is not named %s; rename it %s, the only file "
                               "coderprint edits" % ((os.path.basename(path),) * 2))
    # UTF-16 and UTF-32 (Notepad's "Unicode") hold NUL bytes wherever ASCII text stands, which no text in an
    # encoding that keeps ASCII as ASCII does; GitHub shows such a file as binary
    if raw.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")) or b"\x00" in raw:
        raise RuntimeError("%s is not UTF-8 text (it looks like UTF-16 or UTF-32); save it as UTF-8"
                           % os.path.basename(path))
    bom = raw.startswith(b"\xef\xbb\xbf")
    old = raw[3:].decode("utf-8", "surrogateescape") if bom else raw.decode("utf-8", "surrogateescape")
    eol = "\r\n" if "\r\n" in old else "\n"
    marked = eol.join([README_START] + block.split("\n") + [README_END])
    starts, ends = marker_lines(old)
    if len(starts) > 1 or len(ends) > 1 or len(starts) != len(ends) or (starts and ends[0] < starts[0]):
        raise RuntimeError("%s must hold exactly one %s line and one %s line after it, each on a line of its own, "
                           "or neither; it holds %d and %d" % (os.path.basename(path), README_START, README_END,
                                                               len(starts), len(ends)))
    a = old.find(README_START, starts[0]) if starts else -1
    b = old.find(README_END, ends[0]) if ends else -1
    lone = old.strip()
    ours = ("\n" not in lone and (lone.startswith('<a href="%s"' % LINK)
                                  or lone.startswith('<a href="%s#gh-dark-mode-only"' % LINK)
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
    a failure leaves the old set whole; leftovers are removed either way. files: path to bytes. Each temporary
    file is made new under a name nothing holds (mkstemp), so an existing file, folder or link of any name is
    never written through; and nothing is written through a link or outside the profile repository (WORK)."""
    root = os.path.realpath(WORK)
    for path in files:
        where = os.path.realpath(os.path.dirname(path))
        try:
            outside = os.path.commonpath([root, where]) != root
        except ValueError:   # on another drive
            outside = True
        if os.path.islink(path) or outside:
            raise RuntimeError("README.md or assets is a link or leads outside this repository, and coderprint "
                               "writes only inside it")
    mask = os.umask(0)   # the mode a file made the plain way would have, where mkstemp makes it private
    os.umask(mask)
    temps = {}
    try:
        for path, content in files.items():
            fd, temps[path] = tempfile.mkstemp(prefix=".coderprint-", suffix=".tmp", dir=os.path.dirname(path))
            with os.fdopen(fd, "wb") as f:
                f.write(content)
            os.chmod(temps[path], 0o666 & ~mask)
        for path, tmp in temps.items():
            os.replace(tmp, path)
    finally:
        for tmp in temps.values():
            if os.path.exists(tmp):
                os.remove(tmp)


class Stopped(BaseException):
    """The step's time limit. A BaseException, so no best-effort handler (the profile reads) can swallow it
    and let a stopped run carry on to write panels."""


def stop_on_term(*_):
    raise Stopped("stopped by the step's time limit")


def time_limit():
    """The run's deadline from CARDS_TIME_LIMIT, the seconds its step allows (action.yml passes the
    time-limit input), or None to run without one. Each command then gets only what is left (see run)."""
    limit = os.environ.get("CARDS_TIME_LIMIT", "").strip()
    if not limit:
        return None
    # ASCII digits only, as action.yml's check and timeout take them; leading zeros aside, at most five of them,
    # since int() refuses a value thousands of digits long with an error of its own
    digits = limit.lstrip("0") or "0"
    if not re.fullmatch(r"[0-9]{1,5}", digits) or not 300 <= int(digits) <= 86400:
        raise RuntimeError("CARDS_TIME_LIMIT must be a whole number of seconds from 300 to 86400")
    return time.monotonic() + int(digits)


def own_card_only(owner):
    """A card is its owner's own resume, drawn by the owner's choice. In Actions the account reported on
    must be the one the workflow's repository belongs to, so no one runs coderprint from their repository
    over someone else's account, an employer's over its staff's included."""
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo and repo.split("/")[0].lower() != owner.lower():
        raise RuntimeError("coderprint draws a card only for the account whose repository it runs in")


def profile_repository(owner):
    """The repository GitHub shows the profile README from, and where that README sits in it: owner/owner's
    README.md for a person; for an organization, whose profile is its .github repository's profile/README.md,
    that one, when the Action runs in .github."""
    here = os.environ.get("GITHUB_REPOSITORY", "").partition("/")[2]
    if here.lower() == ".github":
        return ".github", os.path.join(WORK, "profile", "README.md")
    return owner, README


def main():
    global DEADLINE, AS_OF, QUANTITY, DATA_URL
    signal.signal(signal.SIGTERM, stop_on_term)   # unwinds through the clean-up below instead of dying
    window, pin, music, relay, mark_polys, turn, word = settings()
    DEADLINE = time_limit()
    owner = owner_login()
    own_card_only(owner)
    profile, readme_path = profile_repository(owner)
    if relay and profile != owner:   # the relay reads the data file and the panels from owner/owner only
        raise RuntimeError("the relay does not serve an organization's card yet; leave relay unset in the "
                           ".github repository")
    light, dark = todays_themes(pin)   # keys of THEMES: today's theme's lite and nite
    apple = bool(music) and music[0] == "apple_music"
    raw = RAW_ASSETS.format(owner=owner, repo=profile)
    DATA_URL = raw + DATA_FILE
    # a comment inside the markers: GitHub keeps it in the file and draws nothing for it, so a reader of the
    # README's text finds the data file and a visitor sees the same card
    pointer = "<!-- %s -->" % DATA_NOTE.format(url="assets/%s (%s)" % (DATA_FILE, DATA_URL))

    two = bool(relay) or not music   # the two-picture block, which switches to a compact card on phones

    def readme_block(alt):
        return pointer + "\n" + pictures(alt)

    def pictures(alt):
        if not two:
            uid = music[1]
            if apple:
                pair = dict(music_link="https://github.com/rayriffy/apple-music-github-profile", music_width="32.0%",
                            music_alt="Last played on Apple Music",
                            music_dark=APPLE_MUSIC_URL.format(theme="dark", uid=uid),
                            music_light=APPLE_MUSIC_URL.format(theme="light", uid=uid))
            else:
                pair = dict(music_link="https://github.com/kittinan/spotify-github-profile", music_width="35.6%",
                            music_alt="Now playing on Spotify",
                            music_dark=SPOTIFY_URL.format(uid=uid, bg=THEMES[dark]["spotify"]),
                            music_light=SPOTIFY_URL.format(uid=uid, bg=THEMES[light]["spotify"]))
            # relative to README.md at the root, as ever; profile/README.md, an organization's, needs the address
            base = "" if profile == owner else raw[:-len("assets/")]
            return README_PAIR.format(link=LINK, alt=alt, base=base, **pair)
        if relay:
            card = lambda mode, layout="": relay + "?user=" + owner + "&mode=" + mode + layout
            wide, compact = card, lambda mode: card(mode, "&layout=compact")
            alt += ", and last played on Apple Music" if apple else ", and now playing on Spotify"
        else:
            wide = lambda mode: raw + "panel-" + mode + ".svg"
            compact = lambda mode: raw + "panel-compact-" + mode + ".svg"
        return README_TWO.format(link=LINK, blank=raw + "blank.svg", alt=alt, wide_dark=wide("dark"),
                                 compact_dark=compact("dark"), wide_light=wide("light"),
                                 compact_light=compact("light"))

    new_readme(readme_block(ALT), readme_path)   # read before any cloning, so a README problem fails early
    repos = list_repositories(owner)

    data_path, legacy_path = os.path.join(OUT_DIR, DATA_FILE), os.path.join(OUT_DIR, LEGACY_DATA_FILE)
    was = repositories_last_time()
    if was is not None and len(repos) < was and not truthy("FORCE"):
        say("Fewer repositories are visible than last time (%d, was %d). A repository may have been deleted, "
            "or the token may have lost access, so the existing panels are kept. Run the workflow with force "
            "to overwrite." % (len(repos), was))
        return 1

    # The zone comes first: every time is moved to the start of its own day there, so nothing drawn or written
    # tells when in a day anyone worked. Without that, the chart's last day, drawn hours wide, and the data file
    # together placed each commit of the past week within half an hour. The window is cut once, here, at the start of
    # its first whole day in that zone, and collect cuts what is in use exactly where what is written is cut below
    # (window_holds, with the now collect returns), so in use can never count a line written leaves out. What the
    # profile shows is read before any cloning: the time GitHub shows there (a page read, bounded by
    # PROFILE_TIMEOUT) and the location (a gh command). Read after a collection that used the run's time, they
    # would take the reserve kept for drawing, or not start at all, and days would fall in UTC.
    days_back = WINDOWS[window][2]
    begun = time.time()
    shown, location = profile_offset(owner), profile_location(owner)
    offset, seen = shown if shown else (None, None)
    zone = local_zone(offset, location, begun, seen)
    start = first_day(begun - days_back * 86400, zone) if days_back else float("-inf")
    work =os.environ.get("CLONE_CACHE") or tempfile.mkdtemp(prefix="cards-")
    os.makedirs(work, exist_ok=True)
    try:
        data = collect(owner, repos, work, start if days_back else None)
    finally:
        if not os.environ.get("CLONE_CACHE"):
            remove_tree(work)
    readable = sum(1 for r in repos if not (r.get("isDisabled") or r.get("isLocked")))
    if data.get("unchecked"):   # the run cannot tell the owner's code from others', so it publishes nothing
        say("::warning::GitHub could not be asked %s, even on a second try, so this run cannot tell the owner's code "
            "from what others wrote, and the existing panels are kept. The next run tries again."
            % " or ".join(UNCHECKED[u] for u in data["unchecked"]))
        return 1
    if data.get("organization_unread") or any("/" in name for name in data.get("unsure", ())):
        say("::warning::A configured organization repository could not be read or attributed; the existing panels "
            "are kept. Check the organization installation's read access and rerun.")
        return 1
    unsure = data.get("unsure") or set()
    if data["unread"]:
        say("::warning::%d of %d repositories could not be read, even on a second try, and %s left out of the panel"
            % (data["unread"], readable, "is" if data["unread"] == 1 else "are"))
    if unsure:
        say("::warning::%d of %d repositories may hold files from a template, or from coderprint in a relay copy, that "
            "GitHub could not list, so the owner's code there cannot be told apart, and %s left out of the panel"
            % (len(unsure), readable, "is" if len(unsure) == 1 else "are"))
    if data["unread"] + len(unsure) > max(1, int(UNREAD_SHARE * readable)):
        say("That is too many to draw without, so the existing panels are kept. The next run tries again.")
        return 1
    # drawn all the same, as README says, but never silently: a repository too big to read line by line in time is
    # so on every run, so keeping the panels for it would keep them for good
    blind = (data.get("code") or {}).get("unread", 0)
    if blind:
        say("::warning::%d of the %d repositories read could not be read line by line, so %s added lines count "
            "whole, comments and blank lines included, and none of them as in use"
            % (blind, readable - data["unread"] - len(unsure), "its" if blind == 1 else "their"))
    refused = (data.get("authors") or {}).get("refused", 0)
    if refused:   # a count only: an address is never printed
        say("::warning::%d %s in author-emails %s to another GitHub account, and %s commits are not counted as the "
            "owner's" % ((refused, "address", "belongs", "its") if refused == 1 else
                         (refused, "addresses", "belong", "their")))
    # a repository holding only others' file versions (a relay copy), or left out, makes nothing of the owner's private
    private = sum(1 for r in repos if r["isPrivate"] and repo_key(owner, r) not in data["copies"] and repo_key(owner, r) not in unsure)

    now = data["now"]
    if not zone_database():   # said whatever the profile shows, so the line tells a reader nothing about it
        say("note: this Python has no time zone database (pip install tzdata), so days are counted in UTC "
            "or at a fixed offset")
    AS_OF = day_label(now, zone)
    # the window's test (window_holds) cuts the future here and the window's start below, on whole days: start is a
    # day's start, so a day-started time is inside it exactly when the moment itself is
    events = [(day_start(t, zone), lang, n) for t, lang, n in data["events"] if window_holds(t, None, now)]
    commit_times = [day_start(t, zone) for t in data["commits"] if window_holds(t, None, now)]
    column = [(max(0.0, (now - t) / 86400.0), lang, n) for t, lang, n in events if t >= start]
    dated = [t for t in commit_times if t >= start]
    recent_day = None
    if column:
        oldest, newest, recent_day = real_work(column)
        S = max(0.05, oldest)   # a history hours old starts at its first commit too
        if days_back:
            S = min(S, float(days_back))
        c = knee(newest, S)
    elif dated:   # commits but no counted lines (notebooks, data): the bars still span the commits
        S = max(0.05, (now - min(dated)) / 86400.0)
        if days_back:
            S = min(S, float(days_back))
        c = knee(max(0.0, (now - max(dated)) / 86400.0), S)
    else:
        S, c = float(days_back or 1), 1.0
    stream = [e for e in column if e[0] <= S]
    new_lines = sum(n for _, _, n in column)
    spark, commits = [0] * 52, [0] * 52   # lines, and commits, in each 52nd of the chart's span
    for age, _, n in stream:
        spark[min(51, max(0, int((S - age) / S * 52)))] += n
    for t in commit_times:
        age = max(0.0, (now - t) / 86400.0)
        if age <= S:
            commits[min(51, int((S - age) / S * 52))] += 1
    active, longest, current = activity(dated, now, zone)
    # every language at 1% or more of the window's lines, as the chart draws them, named in the legend or not
    counted = sum(1 for l in folded(column)[0] if l != OTHER and l not in PROSE)
    stats = (len(dated), active, longest, current, counted)   # drawn in the rows and written to the data file
    rows = [
        ("commits · all branches", "{:,}".format(stats[0])),
        ("active days", "{:,}".format(active)),
        ("longest streak", plural(longest, "day")),
        ("current streak", plural(current, "day")),
        (LANGUAGES_ROW, str(counted)),
    ]

    loc = data.get("code") or {}
    QUANTITY = {"written": new_lines, "production": loc.get("production", 0), "tests": loc.get("tests", 0)}
    since = day_label(now - S * 86400, zone) if (column or dated) and S >= 1 else None
    readme = new_readme(readme_block(esc(alt_text(window, new_lines, rows))), readme_path)
    panels = [("panel-light.svg", light, panel_svg), ("panel-dark.svg", dark, panel_svg),
              ("panel-compact-light.svg", light, compact_panel_svg),
              ("panel-compact-dark.svg", dark, compact_panel_svg)]
    drawn = {os.path.join(OUT_DIR, fname): draw(theme, window, S, c, new_lines, spark, rows, stream, column,
                                                bool(events), mark_polys, turn, private > 0, word,
                                                recent_day, since, commits).encode("utf-8")
             for fname, theme, draw in panels}
    palette = lambda t: {k: THEMES[t][k] for k in ("bg", "text", "muted", "line")}
    # what the relay reads (lib/compose.js readCards): the day's palettes and the music card's service, keyed
    # spotify or apple_music; the rest names the drawings, for a reader of the data file
    presentation = {"theme": theme_of(light), "themes": {"light": light, "dark": dark},
                    "palette": {"light": palette(light), "dark": palette(dark)},
                    "panels": {"wide": {"light": "panel-light.svg", "dark": "panel-dark.svg"},
                               "compact": {"light": "panel-compact-light.svg", "dark": "panel-compact-dark.svg"}}}
    if music:
        presentation[music[0]] = {"uid": music[1]}
    card = card_data(owner, window, now, zone, start, S, repos, private > 0, data, stats, spark, commits, stream,
                     column, presentation, profile)

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(readme_path), exist_ok=True)   # an organization's profile/ folder
    # coderprint writes these files (the README, the wide panels, the compact panels, the blank image when
    # the README block shows it, and coderprint.json), and deletes only its own cards.json (own_legacy), which
    # coderprint.json replaced. A relay copy deployed before this release reads only cards.json, so README says
    # to update the relay before moving the Action; this release's relay reads either. The README goes first,
    # being the one most likely held open by an editor, and the data file last, so it only ever describes
    # panels in place.
    files = {readme_path: readme}
    files.update(drawn)
    if two:
        files[os.path.join(OUT_DIR, "blank.svg")] = BLANK_SVG
    files[data_path] = data_text(card).encode("utf-8")
    try:
        write_all(files)
        if own_legacy(previous_meta(legacy_path)):   # this script's own, from before coderprint.json
            os.remove(legacy_path)
    except OSError:
        raise RuntimeError("the panel files could not be written") from None
    left = card["left_out"]
    say("panels written (%s, %s, %s): %d repositor%s, %s commits, lines of code %s written and %s in use (%s "
        "production, %s tests), chart over %s, %d import commits skipped, %d commits unparsed, commits left out: %s"
        % (light, dark, window, len(repos), "y" if len(repos) == 1 else "ies", rows[0][1], fmt(new_lines),
           fmt(QUANTITY["production"] + QUANTITY["tests"]), fmt(QUANTITY["production"]), fmt(QUANTITY["tests"]),
           plural(math.ceil(S - 1e-9), "day"), left["imports"]["commits"], data["mismatched"],
           ", ".join("%d %s" % (n, why.replace("_", " ")) for why, n in sorted(data["left_out"].items())) or "none"))
    return 0


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
