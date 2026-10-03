# coderprint's card as data (assets/coderprint.json) and the wide panel's SVG. coderprint.py runs this file as part
# of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


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
