# coderprint's main: its settings, the README block, writing the files and the time limit. coderprint.py runs this
# file as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported
# on its own.


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


def draw_main(owner):
    global DEADLINE, AS_OF, QUANTITY, DATA_URL
    signal.signal(signal.SIGTERM, stop_on_term)   # unwinds through the clean-up below instead of dying
    window, pin, music, relay, mark_polys, turn, word = settings()
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
    if ORGANIZATION_SNAPSHOT is not None:
        card["scope"]["organization_snapshot"] = {
            "as_of": ORGANIZATION_SNAPSHOT.as_of,
            "refresh": "manual",
            "replayed_with_personal_history": True,
            "cross_scope_duplicates": "removed by the same collector",
        }

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


def main(deadline=None):
    """Decrypt frozen organization history before drawing one card from the union of repositories."""
    global DEADLINE, ORGANIZATION_SNAPSHOT
    DEADLINE = deadline if deadline is not None else time_limit()
    owner = owner_login()
    own_card_only(owner)
    path = os.environ.get("CARDS_ORGANIZATION_SNAPSHOT", "").strip()
    key = os.environ.get("CARDS_ORGANIZATION_SNAPSHOT_KEY", "").strip()
    store = snapshot_store(owner)
    if store and not key:
        raise RuntimeError("the private organization snapshot store needs its key; existing panel kept")
    if not path and key and store:
        # This personal App reads the encrypted personal store; it never accesses an organization.
        try:
            meta = json.loads(run(["gh", "api", "--hostname", "github.com", "repos/" + store], env=github_env(), timeout=60))
            if (meta.get("private") is not True or meta.get("owner", {}).get("login", "").lower() != owner.lower()):
                raise RuntimeError()
            # A +json media type makes gh reformat binary ciphertext as JSON and fail.
            body = run(["gh", "api", "--hostname", "github.com", "repos/" + store + "/contents/organization.snapshot",
                        "-H", "Accept: application/vnd.github.raw"], env=github_env(), timeout=120)
            if not 1 <= len(body) <= 48 * 1024 * 1024:
                raise RuntimeError()
            with tempfile.TemporaryDirectory(prefix="coderprint-encrypted-") as temporary:
                encrypted = os.path.join(temporary, "organization.snapshot")
                with open(encrypted, "wb") as stream:
                    stream.write(body)
                return draw_saved_organizations(owner, encrypted, key)
        except (RuntimeError, ValueError, KeyError, TypeError):
            raise RuntimeError("the private organization snapshot could not be read; existing panel kept") from None
    if bool(path) != bool(key):
        raise RuntimeError("organization-snapshot and its key must be supplied together")
    if not path:
        old = previous_meta(os.path.join(OUT_DIR, DATA_FILE)).get("scope", {})
        if isinstance(old, dict) and old.get("organization_snapshot") and not truthy("FORCE"):
            raise RuntimeError("this combined card needs its organization snapshot; the existing panel is kept")
        return draw_main(owner)
    return draw_saved_organizations(owner, path, key)


def draw_saved_organizations(owner, path, key):
    global ORGANIZATION_SNAPSHOT
    # The optional module is beside the Action source, not in the profile checkout.
    spec = importlib.util.spec_from_file_location(
        "coderprint_organization_snapshot", os.path.join(os.path.dirname(__file__), "organization_snapshot.py"))
    storage = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(storage)
    old = previous_meta(os.path.join(OUT_DIR, DATA_FILE)).get("scope", {})
    minimum = old.get("organization_snapshot", {}).get("as_of") if isinstance(old, dict) else None
    saved = storage.load_snapshot(path, key, owner, minimum_day=minimum)
    ORGANIZATION_SNAPSHOT = saved
    try:
        identity = owner_identity(owner)
        if not identity or not identity["user"] or identity["id"] != saved.user_id:
            raise RuntimeError("the saved organization history does not match this GitHub identity")
        return draw_main(owner)
    finally:
        ORGANIZATION_SNAPSHOT = None
        saved.close()
