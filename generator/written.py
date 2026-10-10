# coderprint's the lines of code each commit wrote (read_added_code) and .gitattributes. coderprint.py runs this file
# as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its
# own.


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


def gained_line_end(hunk):
    """Whether a hunk's only change to the old last line is the line end it gains: git lists that line as removed
    ("\\ No newline at end of file") and again as added, though nobody wrote or removed it."""
    gone, came, gone_eof = hunk[4], hunk[5], hunk[6]
    return bool(gone_eof and gone and came and came[0].rstrip(b"\r") == gone[-1].rstrip(b"\r"))


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
            if gained_line_end(h):
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
            for h in f["hunks"]:
                old_start, old_count, new_start, new_count, gone_lines = h[:5]
                came, gone = [], []
                c = new_start - 1 if new_count else new_start
                end = min(c + new_count, n)
                if gained_line_end(h):   # as with edits above: neither removed nor written
                    gone_lines = gone_lines[:-1]
                    if c < end:
                        kept_at.append((c, None))   # no version before is had, so its origin stays unknown
                    c += 1
                for i in range(c, end if not new_pointer else c):
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
        for h in f["hunks"]:
            old_start, old_count, new_start, new_count, gone, came = h[:6]
            if gained_line_end(h):   # the old last line only gained its line end: neither removed nor written
                gone, came, new_start = gone[:-1], came[1:], new_start + 1
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
