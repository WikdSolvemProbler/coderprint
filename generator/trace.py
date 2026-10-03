# coderprint's reading git's output, file versions and tracing each line through its history. coderprint.py runs this
# file as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported
# on its own.


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
