# coderprint's moves, imports, landings and collect(), which reads every repository. coderprint.py runs this file as
# part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its
# own.


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
