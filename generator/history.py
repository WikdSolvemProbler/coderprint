# coderprint's reading a clone's history the same way on every machine, and its sweeps. coderprint.py runs this file
# as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its
# own.


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
    frozen = None
    if ORGANIZATION_SNAPSHOT is not None:
        frozen = ORGANIZATION_SNAPSHOT.seed_blobs_by_source.get(full_name.lower())
        if full_name.split("/")[0].lower() in ORGANIZATION_SNAPSHOT.organizations:
            if frozen is None:
                raise RuntimeError("the saved organization template evidence is incomplete")
            return set(frozen)
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
    return ({line[1:].strip() for line in out.decode("ascii", "replace").splitlines() if line.startswith("?")}
            | set(frozen or ()))
