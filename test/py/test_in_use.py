"""Regression checks for in use, which is now traced through each repository's history with text matching as its
backstop: one check or more for each finding of the in-use area (in_use-IU-01, IU-02, IU-03, IU-10, IU-11, UP-3 and
UP-5), gaps-a9-f09, the vote's M1, M6, M35 and M36, the data file's C4-03 and C4-07, panel-F1 and docs-F1, and the
history shapes the tracing must get right (a revert, a cherry-pick, a rebase, a squash merge with its branch kept and
deleted, a merge whose conflict was resolved, a block moved within and between files, sweeps by the owner and by a bot,
an import later edited, a relay copy, a template, a fork, a stale copy, a future-dated commit, a commit on the window's
first day, and a collaborator's common lines).
Usage: python test_in_use.py path/to/coderprint.py. It builds its repositories in a temporary folder with git, runs
collect() or main() with every network lookup replaced by a fake, and compares what is in use with the truth: git blame
at each head, restricted to the owner's counted commits in the window, where the history can say. Each check prints
the truth, how many lines were traced, how many were matched by text, and the total; the script prints one line per
check and exits non-zero if any check fails."""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

CP_PATH = os.path.abspath(sys.argv[1])


def load():
    spec = importlib.util.spec_from_file_location("cp_%d" % time.perf_counter_ns(), CP_PATH)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


cp = load()
ROOT = tempfile.mkdtemp(prefix="in-use-")
OWNER = "owner1"
NOREPLY = "123+owner1@users.noreply.github.com"
ME = ("Owner One", NOREPLY)
COL = ("Col Laborator", "col@example.com")
BOT = ("pre-commit-ci[bot]", "66853113+pre-commit-ci[bot]@users.noreply.github.com")
WORKFLOW = ("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com")
T0 = 1700000000
DAY = 86400
SOURCES, SEEDS, TEMPLATES = {}, {}, {}
LOGINS = {COL[1]: "collaborator"}
results = []
for name in ("GH_TOKEN", "CLONE_CACHE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT", "CARDS_AUTHOR_EMAILS", "CARDS_TIME_LIMIT",
             "FORCE", "CARDS_OWNER", "GITHUB_REPOSITORY", "CARDS_WINDOW"):
    os.environ.pop(name, None)


def check(fid, name, ok, detail=""):
    if callable(ok):   # a check that may raise on an older coderprint.py, which lacks what it reads
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(bool(ok))
    print("%s %s %s%s" % ("PASS" if ok else "FAIL", fid, name, "" if ok else "  [got %r]" % (detail,)))


def writable(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def remove(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable)
    else:
        shutil.rmtree(path, ignore_errors=True)


def git(repo, *args, when=T0, author=ME, committer=None, check_exit=True):
    committer = committer or author
    env = dict(os.environ, GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=committer[0],
               GIT_COMMITTER_EMAIL=committer[1], GIT_AUTHOR_DATE="%d +0000" % when,
               GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                        "-c", "gc.auto=0", "-c", "maintenance.auto=false",
                        "-c", "advice.detachedHead=false", "-c", "merge.conflictStyle=merge"] + list(args),
                       env=env, capture_output=True, timeout=60)
    if p.returncode and check_exit:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace")


def new_repo(name, branch="main"):
    path = os.path.join(ROOT, "src", name)
    if os.path.isdir(path):
        remove(path)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", "-b", branch, path], check=True, capture_output=True, timeout=60)
    SOURCES[name] = path
    return path


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        f.write(text)


def rm(repo, rel):
    os.remove(os.path.join(repo, rel))


def commit(repo, msg, when, author=ME, committer=None):
    git(repo, "add", "-A", when=when, author=author)
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, when=when, author=author, committer=committer)
    return sha(repo)


def sha(repo, ref="HEAD"):
    return git(repo, "rev-parse", ref).strip()


def all_shas(repo):
    return set(git(repo, "rev-list", "--all").split())


def nonce_commit(repo, msg, when, author=ME, above=None):
    """Commits with a nonce in the body until the new hash sorts after above; the subject stays the same."""
    for k in range(400):
        git(repo, "add", "-A", when=when, author=author)
        git(repo, "commit", "-q", "--allow-empty", "-m", msg, "-m", "nonce %d" % k, when=when, author=author)
        s = sha(repo)
        if above is None or s > above:
            return s
        git(repo, "reset", "-q", "--soft", "HEAD~1", when=when)
    raise SystemExit("no nonce found")


def body(tag, n, indent=""):
    return "".join("%sv_%s_%d = %d\n" % (indent, tag, i, i) for i in range(n))


def funcs(tag, n):   # five lines each: two its own, three common
    return "".join("def %s_%d(x):\n    if x is None:\n        return None\n    y = x * %d  # %s\n    return y\n"
                   % (tag, i, i + 7, tag) for i in range(n))


def guards(n):
    return "".join("    if x is None:\n        return None\n" for _ in range(n))


def clone_fixture(source, dest, bare=True):
    # Exercise Git's regular object transfer, as production's HTTPS clone does,
    # instead of the local hardlink/copy optimization. No automatic maintenance
    # should race a synthetic repository while the fixture is read.
    args = ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "clone", "-q", "--no-local"]
    if bare:
        args.append("--bare")
    try:
        result = subprocess.run(args + [source, dest], capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise AssertionError("fixture clone exceeded 120 seconds") from None
    if result.returncode:
        # collect intentionally swallows RuntimeError for unread real histories.
        # A synthetic clone failure must instead fail the check with its stderr.
        raise AssertionError("fixture clone exited %d: %s" %
                             (result.returncode, result.stderr.decode("utf-8", "replace")[:300]))


def fake_clone(owner, name, dest):
    if os.path.isdir(dest):
        remove(dest)
    clone_fixture(SOURCES[name], dest)


cp.clone = fake_clone
cp.resolve_authors = lambda owner, samples: {e: LOGINS.get(e) for e in samples}
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
cp.templates = lambda owner: dict(TEMPLATES)
cp.seed_blobs = lambda full_name, dest: SEEDS.get(full_name)


def run(names, since=None, archived=()):
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    repos = [{"name": n, "isPrivate": True, "isArchived": n in archived} for n in names]
    try:
        return cp.collect(OWNER, repos, work, since)
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "events": [], "commits": [], "code": {}, "imports": [],
                "left_out": {}, "import_lines": []}


def lines(d):
    return sum(n for _, _, n in d["events"])


def use(d):
    return d["code"].get("production"), d["code"].get("tests")


def figures(d):
    """(in use, traced, matched by text, written)."""
    c = d["code"]
    return ((c.get("production") or 0) + (c.get("tests") or 0), c.get("traced"), c.get("matched"), lines(d))


def is_code(text):
    s = text.strip()
    return bool(s) and not s.startswith("#")


def truth(names, owner_shas, blame_args=()):
    """Lines of code at each head that git blame gives to one of owner_shas, as (production, tests)."""
    prod = tests = 0
    for n in names:
        repo = SOURCES[n]
        for path in git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines():
            lang = cp.language_of(path)
            if not cp.counts_as_code(path, lang):
                continue
            out = git(repo, "blame", "--line-porcelain", *blame_args, "HEAD", "--", path)
            who = None
            for line in out.split("\n"):
                if len(line) >= 40 and all(ch in "0123456789abcdef" for ch in line[:40]) and " " in line:
                    who = line[:40]
                elif line.startswith("\t") and is_code(line[1:]) and who in owner_shas:
                    if cp.is_test(path):
                        tests += 1
                    else:
                        prod += 1
    return prod, tests


def case(fid, name, d, want, written=None, traced_all=True):
    """One scenario's check: in use equals want (the truth), never exceeds written, and, where every line's history
    is readable, every line in use was traced and none matched by text."""
    total, traced, matched, wrote = figures(d)
    ok = (use(d) == want and total <= wrote and (written is None or wrote == written)
          and (not traced_all or (traced == total and matched == 0)))
    check(fid, "%s: truth %s, traced %s, matched %s, total %s, written %s%s" % (
        name, want, traced, matched, total, wrote, "" if written is None else " (want %d)" % written), ok,
        (use(d), figures(d), d.get("error")))


# ---------------------------------------------------------------- history shapes, against git blame
r = new_repo("revert")
write(r, "a.py", body("r1", 10))
c1 = commit(r, "add a", T0)
git(r, "revert", "--no-edit", "HEAD", when=T0 + DAY)
c2 = sha(r)
git(r, "revert", "--no-edit", "HEAD", when=T0 + 2 * DAY)
c3 = sha(r)
case("SPEC", "revert of a revert", run(["revert"]), truth(["revert"], {c1, c2, c3}), 10)

r = new_repo("revert_col")
write(r, "a.py", body("r2", 10))
c1 = commit(r, "add a", T0)
git(r, "revert", "--no-edit", "HEAD", when=T0 + DAY, author=COL)
git(r, "revert", "--no-edit", "HEAD", when=T0 + 2 * DAY)
c3 = sha(r)
case("SPEC", "a collaborator's revert, the owner's revert of it", run(["revert_col"]), truth(["revert_col"], {c1, c3}),
     10)

# the revert inside the window restores a file version first written before it: that version was counted as written
# once, before the window, so its line is not the window's, though blame names the revert (definition, not history)
r = new_repo("revert_old")
write(r, "a.py", body("r3", 10))
commit(r, "old", T0)
write(r, "a.py", body("r3", 10).replace("v_r3_3 = 3", "v_r3_3 = 33"))
commit(r, "change", T0 + 10 * DAY)
git(r, "revert", "--no-edit", "HEAD", when=T0 + 11 * DAY)
case("SPEC", "a revert inside the window to a version written before it: nothing in use", run(["revert_old"],
     since=T0 + 5 * DAY), (0, 0), 11)

r = new_repo("pick")
write(r, "a.py", body("c1base", 5))
base = commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "a.py", body("c1base", 5) + body("c1feat", 10))
feat = nonce_commit(r, "the feature", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "a.py", body("c1base", 5) + body("c1feat", 10) + "resolved_extra = 1\n")
picked = nonce_commit(r, "the feature", T0 + DAY, above=feat)
case("SPEC", "a cherry-pick whose resolution added a line", run(["pick"]), truth(["pick"], {base, picked}), 16)

r = new_repo("pick_clean")
write(r, "a.py", body("c2base", 5))
base = commit(r, "base", T0)
write(r, "other.py", body("c2other", 3))
m1 = commit(r, "main moves", T0 + DAY)
git(r, "checkout", "-q", "-b", "feat", base)
write(r, "a.py", body("c2base", 5) + body("c2feat", 10))
feat = commit(r, "the feature", T0 + 2 * DAY)
git(r, "checkout", "-q", "main")
git(r, "cherry-pick", feat, when=T0 + 3 * DAY)
case("SPEC", "a clean cherry-pick, both copies kept", run(["pick_clean"]),
     truth(["pick_clean"], {base, m1, sha(r), feat}), 18)

for name, flags, want in (("rebase", (), 28), ("rebase_dates", ("--ignore-date",), 18)):
    r = new_repo(name)
    write(r, "a.py", body(name + "base", 5))
    commit(r, "base", T0)
    git(r, "checkout", "-q", "-b", "feat")
    write(r, "a.py", body(name + "base", 5) + body(name + "f1", 10))
    commit(r, "f1", T0 + DAY)
    if not flags:
        write(r, "a.py", body(name + "base", 5) + body(name + "f1", 10) + body(name + "f2", 10))
        commit(r, "f2", T0 + 2 * DAY)
    git(r, "branch", "feat-old")
    git(r, "checkout", "-q", "main")
    write(r, "a.py", body(name + "main", 3) + body(name + "base", 5))
    commit(r, "main moves", T0 + 3 * DAY)
    git(r, "checkout", "-q", "feat")
    git(r, "rebase", "-q", *flags, "main", when=T0 + 4 * DAY)
    git(r, "checkout", "-q", "main")
    git(r, "merge", "-q", "--ff-only", "feat", when=T0 + 4 * DAY)
    case("SPEC" if not flags else "in_use-IU-10", "a rebase%s, the old branch kept" % (" --ignore-date" if flags else ""),
         run([name]), truth([name], all_shas(r)), want)

r = new_repo("squash")
write(r, "app.py", body("q1base", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
for k in range(3):
    write(r, "app.py", body("q1base", 5) + body("q1feat", 10 * (k + 1)))
    commit(r, "feature part %d" % k, T0 + (k + 1) * DAY)
git(r, "checkout", "-q", "main")
write(r, "app.py", body("q1top", 5) + body("q1base", 5))
commit(r, "main moves", T0 + 5 * DAY)
git(r, "merge", "-q", "--squash", "feat", when=T0 + 6 * DAY)
commit(r, "Feature (#1)", T0 + 6 * DAY)
shas = all_shas(r)
case("in_use-IU-10", "a squash merge with the branch kept, after main moved: written once", run(["squash"]),
     truth(["squash"], shas), 40)
git(r, "branch", "-q", "-D", "feat")
case("SPEC", "the same squash with the branch deleted", run(["squash"]), truth(["squash"], shas), 40)

r = new_repo("conflict")
write(r, "a.py", body("m1base", 5) + "shared_marker = 1\n")
base = commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "a.py", body("m1base", 5) + "side = 'feat'\n")
f = commit(r, "feat side", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "a.py", body("m1base", 5) + "side = 'main'\n")
m = commit(r, "main side", T0 + 2 * DAY)
git(r, "merge", "-q", "feat", when=T0 + 3 * DAY, check_exit=False)
write(r, "a.py", body("m1base", 5) + "side = 'both'\nresolution_line = 1\n")
commit(r, "merge feat", T0 + 3 * DAY)
d = run(["conflict"])
case("SPEC", "a merge whose conflict's resolution wrote two lines: those are the merge's, not in use", d,
     truth(["conflict"], {base, f, m}), 8)
# the resolution re-adds a line the owner wrote and deleted: its history is the merge's own, so text decides it
r = new_repo("conflict_back")
write(r, "a.py", body("m2base", 5) + "gone_line = 1\n")
base = commit(r, "base", T0)
write(r, "a.py", body("m2base", 5))
commit(r, "drop it", T0 + DAY / 2)
git(r, "checkout", "-q", "-b", "feat")
write(r, "a.py", body("m2base", 5) + "side = 'feat'\n")
commit(r, "feat side", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "a.py", body("m2base", 5) + "side = 'main'\n")
commit(r, "main side", T0 + 2 * DAY)
git(r, "merge", "-q", "feat", when=T0 + 3 * DAY, check_exit=False)
write(r, "a.py", body("m2base", 5) + "side = 'both'\ngone_line = 1\n")
commit(r, "merge feat", T0 + 3 * DAY)
d = run(["conflict_back"])
total, traced, matched, wrote = figures(d)
check("SPEC", "a line only a merge's resolution put back is matched by text, the rest traced: traced 5, matched 1",
      (total, traced, matched) == (6, 5, 1), figures(d))

r = new_repo("merge_both")
write(r, "a.py", body("mb", 5))
base = commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "a.py", body("mb", 5) + body("mbfeat", 6))
commit(r, "feat", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "a.py", body("mbtop", 4) + body("mb", 5))
commit(r, "main", T0 + 2 * DAY)
git(r, "merge", "-q", "--no-edit", "feat", when=T0 + 3 * DAY)
d = run(["merge_both"])
case("SPEC", "a merge git resolved on its own: the branch's lines traced through it", d,
     truth(["merge_both"], all_shas(r)), 15)
# git older than 2.31 cannot give a merge's diff from its first parent: its lines are then matched by text instead
real_version = cp.git_version
cp.git_version = lambda: (2, 30)
d = run(["merge_both"])
cp.git_version = real_version
total, traced, matched, wrote = figures(d)
check("SPEC", "without merges' diffs (git before 2.31) the merge's version at the head falls back to text: 15, all "
      "matched", (total, traced, matched, wrote) == (15, 0, 15, 15), figures(d))

r = new_repo("move_within")
write(r, "a.py", body("v1top", 5) + body("v1fn", 20))
c1 = commit(r, "write", T0)
write(r, "a.py", body("v1fn", 20) + body("v1top", 5))
c2 = commit(r, "move the function up", T0 + DAY)
case("in_use-UP-3", "a block moved within its file is not written again: 25", run(["move_within"]),
     truth(["move_within"], {c1, c2}), 25)

r = new_repo("move_between")
write(r, "a.py", body("v2a", 5) + body("v2fn", 20))
write(r, "b.py", body("v2b", 5))
c1 = commit(r, "write", T0)
write(r, "a.py", body("v2a", 5))
write(r, "b.py", body("v2b", 5) + body("v2fn", 20))
c2 = commit(r, "move the function to b", T0 + DAY)
case("M36", "a block moved into another file is not written again: 30", run(["move_between"]),
     truth(["move_between"], {c1, c2}), 30)

r = new_repo("move_col")
write(r, "a.py", body("v3a", 5) + body("v3fn", 20))
write(r, "b.py", body("v3b", 5))
c1 = commit(r, "write", T0)
write(r, "a.py", body("v3a", 5))
write(r, "b.py", body("v3b", 5) + body("v3fn", 20))
commit(r, "move the function to b", T0 + DAY, author=COL)
case("SPEC", "a collaborator moves the owner's function: still the owner's (blame -C)", run(["move_col"]),
     truth(["move_col"], {c1}, ("-C", "-C")), 30)

r = new_repo("lone")
write(r, "a.py", "def f(x):\n    y = x\n    return None\n")
c1 = commit(r, "write", T0)
write(r, "a.py", "def f(x):\n    y = x + 1\n    z = y\n    return None\n")
c2 = commit(r, "edit", T0 + DAY)
write(r, "a.py", "def g(x):\n    return None\n\n\ndef f(x):\n    y = x + 1\n    z = y\n")
c3 = commit(r, "a lone line moved is written", T0 + 2 * DAY)
d = run(["lone"])
check("in_use-UP-3", "a run of fewer than 3 matched lines is written, not moved: 3 + 2 + 2 written",
      lines(d) == 7, figures(d))

r = new_repo("reindent")
write(r, "a.py", body("ri", 4))
c1 = commit(r, "write", T0)
write(r, "a.py", "if True:\n" + body("ri", 4, "    "))
c2 = commit(r, "wrap it in an if", T0 + DAY)
case("in_use-UP-3", "a block only re-indented is moved, not written: 4 + 1", run(["reindent"]),
     truth(["reindent"], {c1, c2}, ("-w",)), 5)

# ---------------------------------------------------------------- IU-02: sweeps by anyone; IU-03: where credit goes


def quoted(tag, n):
    return "".join("v_%s_%d = 'text %d'\n" % (tag, i, i) for i in range(n))


for name, sweeper, listed, committer in (("bot_listed", BOT, True, None), ("bot_found", BOT, False, None),
                                         ("col_listed", COL, True, None), ("col_found", COL, False, None),
                                         ("own_listed", ME, True, None), ("own_found", ME, False, None),
                                         ("own_workflow", ME, True, WORKFLOW)):
    r = new_repo(name)
    for k in range(12):
        write(r, "pkg/m%d.py" % k, quoted("%s%d" % (name, k), 20))
    w = commit(r, "write", T0)
    for k in range(12):
        write(r, "pkg/m%d.py" % k, quoted("%s%d" % (name, k), 20).replace("'", '"'))
    s = commit(r, "style: black", T0 + DAY, author=sweeper, committer=committer)
    shas = {w}
    if listed:
        write(r, ".git-blame-ignore-revs", "# black\n%s\n" % s)
        shas.add(commit(r, "ignore the black sweep", T0 + 2 * DAY))
    case("in_use-IU-02", "a sweep by %s (%s) keeps the owner's 240" % (name, "listed" if listed else "found"),
         run([name]), truth([name], shas, ("--ignore-rev", s)), 240)

r = new_repo("pairing")
for k in range(12):
    write(r, "p%d.py" % k, body("old%d" % k, 5))
commit(r, "old work", T0)
for k in range(12):
    write(r, "p%d.py" % k, body("old%d" % k, 5) + body("new%d" % k, 5))
new = commit(r, "new work", T0 + 10 * DAY)
for k in range(12):
    write(r, "p%d.py" % k, (body("old%d" % k, 5) + body("new%d" % k, 5)).replace("v_", "w_"))
sw = commit(r, "rename v_ to w_", T0 + 11 * DAY)
for k in range(12):
    write(r, "p%d.py" % k, body("new%d" % k, 5).replace("v_", "w_"))
dele = commit(r, "drop the old code", T0 + 12 * DAY)
case("in_use-IU-03", "a sweep hands each line on to the line in its place: 60 after the old lines go",
     run(["pairing"], since=T0 + 5 * DAY), truth(["pairing"], {new, dele}, ("--ignore-rev", sw)), 120)
check("in_use-IU-03", "pair_lines: the same text first, anywhere in the file, then in order within each hunk",
      lambda: list(cp.pair_lines([(["a", "b"], ["b2", "a"]), (["c"], ["x", "c2"])])) == [1, 0, 2, -1]
      and list(cp.pair_lines([(["a", "b"], ["a2", "b2"])])) == [0, 1]
      and list(cp.pair_lines([(["x"], []), (["y"], ["y", "x"])])) == [1, 0], "pair_lines")

r = new_repo("rename_sweep")
for i in range(12):
    write(r, "r%d.py" % i, body("rn%d" % i, 10))
w = commit(r, "write", T0)
for i in range(12):
    write(r, "r%d.py" % i, body("rn%d" % i, 10).replace("v_", "row_"))
s = commit(r, "rename v_ to row_", T0 + 100)
case("SPEC", "a rename sweep: 120 written, 120 in use", run(["rename_sweep"]),
     truth(["rename_sweep"], {w}, ("--ignore-rev", s)), 120)

# ---------------------------------------------------------------- IU-10: landings of a kept branch (verifier's cases)
r = new_repo("sq3")
write(r, "app.py", body("sq3base", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "app.py", body("sq3base", 5) + funcs("fa", 3))
commit(r, "feature", T0 + DAY)
git(r, "checkout", "-q", "main")
git(r, "merge", "-q", "--squash", "feat", when=T0 + 2 * DAY)
commit(r, "Feature (#1)", T0 + 2 * DAY)
write(r, "app.py", body("sq3base", 5) + funcs("fa", 3) + funcs("fb", 3))
commit(r, "more work", T0 + 3 * DAY)
case("in_use-IU-10", "a squash with no divergence, branch kept, then direct work in the file", run(["sq3"]),
     truth(["sq3"], all_shas(r)), 35)

r = new_repo("sq4")
write(r, "app.py", body("sq4base", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "app.py", body("sq4base", 5) + funcs("fa", 3))
commit(r, "feature", T0 + DAY)
git(r, "checkout", "-q", "main")
git(r, "merge", "-q", "--squash", "feat", when=T0 + 2 * DAY)
commit(r, "Feature (#1)", T0 + 2 * DAY)
write(r, "app.py", body("sq4base", 5) + funcs("fa", 3) + "def g(x):\n" + guards(2) + "    return x\n")
commit(r, "guards", T0 + 3 * DAY)
case("in_use-IU-10", "the same, then a direct commit of common lines counts in full", run(["sq4"]),
     truth(["sq4"], all_shas(r)), 26)

r = new_repo("rbm")
write(r, "app.py", body("rbbase", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "app.py", body("rbbase", 5) + funcs("fa", 3))
side = nonce_commit(r, "feature", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "other.py", body("rbother", 3))
commit(r, "main moves elsewhere", T0 + 2 * DAY)
git(r, "checkout", "-q", "-b", "landing")
write(r, "app.py", body("rbbase", 5) + funcs("fa", 3))
nonce_commit(r, "feature", T0 + DAY, above=side)
git(r, "checkout", "-q", "main")
git(r, "merge", "-q", "--ff-only", "landing", when=T0 + 3 * DAY)
git(r, "branch", "-q", "-D", "landing")
write(r, "app.py", body("rbbase", 5) + funcs("fa", 3) + funcs("fb", 3))
commit(r, "more work", T0 + 4 * DAY)
case("in_use-IU-10", "rebase and merge, branch kept, then direct work", run(["rbm"]), truth(["rbm"], all_shas(r)), 38)

r = new_repo("abandoned")
write(r, "app.py", body("abbase", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "idea")
write(r, "app.py", body("abbase", 5) + funcs("fa", 3))
commit(r, "an idea", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "app.py", body("abbase", 5) + funcs("fb", 3))
commit(r, "the real thing", T0 + 3 * DAY)
case("in_use-IU-10", "an abandoned branch, then different work in the same file", run(["abandoned"]),
     truth(["abandoned"], all_shas(r)), 35)

r = new_repo("squash_resolved")
write(r, "app.py", body("q3base", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "feat")
write(r, "app.py", body("q3base", 5) + body("q3feat", 12))
commit(r, "feature", T0 + DAY)
git(r, "checkout", "-q", "main")
write(r, "app.py", body("q3top", 4) + body("q3base", 5))
commit(r, "main moves", T0 + 2 * DAY)
write(r, "app.py", body("q3top", 4) + body("q3base", 5) + body("q3feat", 12) + "resolved = 1\n")
commit(r, "Feature (#2)", T0 + 3 * DAY)
case("in_use-IU-10", "a squash after main moved, with a resolution line", run(["squash_resolved"]),
     truth(["squash_resolved"], all_shas(r)), 22)

r = new_repo("two_branches")
write(r, "app.py", body("twbase", 5))
commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "x")
write(r, "app.py", body("twbase", 5) + body("twx", 12))
commit(r, "x", T0 + DAY)
git(r, "checkout", "-q", "main")
git(r, "checkout", "-q", "-b", "y")
write(r, "app.py", body("twbase", 5) + body("twy", 12))
commit(r, "y", T0 + DAY + 60)
git(r, "checkout", "-q", "main")
write(r, "app.py", body("twtop", 4) + body("twbase", 5))
commit(r, "main moves", T0 + 2 * DAY)
write(r, "app.py", body("twtop", 4) + body("twbase", 5) + body("twx", 12))
commit(r, "X (#1)", T0 + 3 * DAY)
write(r, "app.py", body("twtop", 4) + body("twbase", 5) + body("twx", 12) + body("twy", 12))
commit(r, "Y (#2)", T0 + 4 * DAY)
case("in_use-IU-10", "two branches on one file, each squashed after main moved", run(["two_branches"]),
     truth(["two_branches"], all_shas(r)), 33)

r = new_repo("unmerged")
write(r, "a.py", body("u1base", 5))
base = commit(r, "base", T0)
git(r, "checkout", "-q", "-b", "wip")
write(r, "b.py", body("u1wip", 40))
commit(r, "wip", T0 + DAY)
git(r, "checkout", "-q", "main")
case("in_use-IU-10", "guard: work only on an unmerged branch is written, not in use", run(["unmerged"]),
     truth(["unmerged"], {base}), 45)

# ---------------------------------------------------------------- content: common lines, imports, copies, forks
r = new_repo("common")
fn = "".join("def f%d():\n    x_%d = %d\n    return None\n\n\ndef g%d():\n    pass\n\n\n" % (k, k, k, k) for k in range(20))
write(r, "mine.py", fn)
c1 = commit(r, "mine", T0)
rm(r, "mine.py")
c2 = commit(r, "drop mine", T0 + DAY)
theirs = "".join("def h%d():\n    y_%d = %d\n    return None\n\n\ndef k%d():\n    pass\n\n\n" % (k, k, k, k)
                 for k in range(20))
write(r, "theirs.py", theirs)
commit(r, "theirs", T0 + 2 * DAY, author=COL)
case("SPEC", "a collaborator's common lines (return None, pass) are not the owner's", run(["common"]),
     truth(["common"], {c1, c2}), 100)

r = new_repo("imported")
for k in range(501):
    write(r, "lib/m%d.py" % k, body("imp%d" % k, 2))
commit(r, "import", T0)
for k in range(3):
    write(r, "lib/m%d.py" % k, body("imp%d" % k, 2) + body("edit%d" % k, 5))
e = commit(r, "edit three", T0 + DAY)
case("SPEC", "an import later edited: only the edits", run(["imported"]), truth(["imported"], {e}), 15)

a = new_repo("origin_repo")
write(a, "shared.py", body("fk", 30))
write(a, "core.py", body("fkcore", 10))
fk1 = commit(a, "write", T0)
write(a, "core.py", body("fkcore", 10) + body("fkmore", 5))
fk2 = commit(a, "more", T0 + DAY)
b = os.path.join(ROOT, "src", "fork_repo")
clone_fixture(a, b, bare=False)
SOURCES["fork_repo"] = b
write(b, "extra.py", body("fkextra", 7))
fk3 = commit(b, "fork's own", T0 + 2 * DAY)
d = run(["origin_repo", "fork_repo"])
case("SPEC", "a fork holds the same history: each written line in use once, 45 + 7", d, (52, 0), 52)

a = new_repo("stale_a")
write(a, "f.py", body("st", 30))
commit(a, "write", T0)
b = new_repo("stale_b")
write(b, "f.py", body("st", 30))
commit(b, "copy it in", T0 + DAY)
write(a, "f.py", "".join(body("st", 30).splitlines(True)[:20]))
commit(a, "trim", T0 + 2 * DAY)
case("SPEC", "a stale copy in a second repository: every written line still stands once, 30 of 30", run(["stale_a",
     "stale_b"]), (30, 0), 30)

# M1: a relay copy of coderprint deployed by someone else, beside their own lines, which they deleted
r = new_repo("relay")
mine_js = "".join("function mine%d(x) {\n  return x;\n}\nmodule.exports.mine%d = mine%d;\n" % (k, k, k) for k in range(8))
write(r, "src/own.js", mine_js)
commit(r, "my script", T0)
rm(r, "src/own.js")
commit(r, "drop it", T0 + DAY)
upstream = "".join("function up%d(x) {\n  return x;\n}\nmodule.exports.mine%d = mine%d;\n" % (k, k, k) for k in range(8))
write(r, "api/card.js", upstream)
write(r, "lib/compose.js", upstream.replace("up", "compose"))
commit(r, "Deploy the relay", T0 + 2 * DAY)
SEEDS[cp.UPSTREAM] = set(git(r, "rev-list", "--objects", "--all").split()) - set(
    git(r, "rev-list", "--objects", "HEAD~1").split())
d = run(["relay"])
del SEEDS[cp.UPSTREAM]
case("M1", "a relay copy's files at the head are not the owner's, whatever their text", d, (0, 0), 32)

r = new_repo("template")
write(r, "tpl.py", body("tpl", 40))
write(r, "tpl2.py", body("tpl2", 10))
commit(r, "Initial commit", T0)
SEEDS["someone/template"] = set(git(r, "rev-list", "--objects", "--all").split())
TEMPLATES["template"] = "someone/template"
write(r, "tpl.py", body("tpl", 40) + body("t1own", 6))
own = commit(r, "my edits", T0 + DAY)
case("SPEC", "a repository made from a template, then edited: only the edits", run(["template"]),
     truth(["template"], {own}), 6)
TEMPLATES.clear()
SEEDS.clear()

# IU-11: a line common to the owner's production code and a collaborator's tests, in either order
a = new_repo("p1a")
write(a, "tests/test_x.py", "value = 1\n" * 5)
commit(a, "tests", T0, author=COL)
b = new_repo("p1b")
write(b, "src/x.py", "value = 1\n" * 5 + "other = 2\n")
commit(b, "prod", T0 + DAY)
case("in_use-IU-11", "the collaborator's repository read first: production 6", run(["p1a", "p1b"]), (6, 0), 6)
case("in_use-IU-11", "the owner's repository read first: production 6", run(["p1b", "p1a"]), (6, 0), 6)

# M35: an archived repository's head is not in use; its history still counts as written
r = new_repo("retired")
write(r, "old.py", body("arch", 12))
commit(r, "old work", T0)
d = run(["retired", "p1b"], archived=("retired",))
check("M35", "an archived repository: 12 written, nothing of it in use, counted in code['archived']",
      (lines(d), use(d), d["code"].get("archived")) == (18, (6, 0), 1), figures(d))

# the same history always gives the same figures, whatever Python's string hashing does in a run: here one block stood
# in two files, written before the window in one and inside it in the other, and a commit moved one copy to a third
r = new_repo("twin_blocks")
write(r, "a.py", body("ta", 3) + body("tw", 5))
commit(r, "a", T0)
write(r, "b.py", body("tb", 3) + body("tw", 5))
commit(r, "b", T0 + 10 * DAY)
write(r, "a.py", body("ta", 3))
write(r, "b.py", body("tb", 3))
write(r, "c.py", body("tc", 2) + body("tw", 5))
commit(r, "move one copy", T0 + 11 * DAY)
probe = os.path.join(ROOT, "probe.py")
with open(probe, "w", encoding="utf-8") as f:
    f.write("import importlib.util, shutil, subprocess, sys, tempfile\n"
            "spec = importlib.util.spec_from_file_location('cp', sys.argv[1])\n"
            "cp = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(cp)\n"
            "def clone(o, n, d):\n"
            "    p = subprocess.run(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', 'clone', '-q',\n"
            "                        '--bare', '--no-local', sys.argv[2], d], capture_output=True, timeout=120)\n"
            "    if p.returncode:\n"
            "        raise AssertionError('fixture clone exited %%d: %%s' %%\n"
            "                             (p.returncode, p.stderr.decode('utf-8', 'replace')[:300]))\n"
            "cp.clone = clone\n"
            "cp.resolve_authors = lambda o, s: {}\n"
            "cp.owner_identity = lambda o: {'user': True, 'id': 123, 'name': 'Owner One'}\n"
            "cp.templates = lambda o: {}\n"
            "cp.seed_blobs = lambda n, d: None\n"
            "d = cp.collect('owner1', [{'name': 'x', 'isPrivate': True}], tempfile.mkdtemp(), %d)\n"
            "c = d['code']\n"
            "print(sum(n for _, _, n in d['events']), c['production'], c['tests'], c['traced'], c['matched'])\n"
            % (T0 + 5 * DAY))
outs = set()
for seed in ("1", "2", "3"):
    p = subprocess.run([sys.executable, probe, CP_PATH, r], capture_output=True,
                       env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1"), timeout=180)
    if p.returncode:
        raise AssertionError("hash-seed fixture exited %d: %s" %
                             (p.returncode, p.stderr.decode("utf-8", "replace")[-300:]))
    outs.add(p.stdout.decode().strip().splitlines()[-1] if p.stdout.strip() else p.stderr.decode()[-200:])
check("SPEC", "the same history gives the same figures under three string hash seeds: %s" % sorted(outs),
      len(outs) == 1, outs)

# ---------------------------------------------------------------- the backstop: what history cannot give, text matches
Trace = cp.Trace
real_keep = Trace.keep
Trace.keep = lambda self, blob, origins: None   # no head version's origins kept: every line falls to the backstop
d = run(["common"])
backstop = figures(d)
d2 = run(["p1a", "p1b"])
Trace.keep = real_keep
check("SPEC", "with no history at the heads, text matching still runs: the common lines match (the old figure, 40)",
      backstop[:3] == (40, 0, 40), backstop)
check("in_use-IU-11", "the backstop matches in the files the owner changed first: production 6 from either order",
      use(d2) == (6, 0) and figures(d2)[2] == 6, figures(d2))
real_allot = Trace.allot


def failing(self, key, n):
    raise ValueError("a history tracing cannot follow")


Trace.allot = failing   # tracing breaks at its first added line: the repository's diffs must still count
d = run(["rename_sweep"])
Trace.allot = real_allot
check("SPEC", "tracing that fails part way leaves the head to text matching and the diffs counted: 120 written, 120 "
      "in use, all matched", figures(d) == (120, 0, 120, 120) and d["code"].get("unread") == 0, figures(d))
real_lines = cp.VERSION_LINES
cp.VERSION_LINES = 1   # versions let go at once: later versions are read with no origins for what they keep
d = run(["rename_sweep", "move_between", "squash"])
cp.VERSION_LINES = real_lines
total, traced, matched, wrote = figures(d)
check("SPEC", "versions let go before their children are read fall back to text, and the total stands: 190",
      total == 190 and traced + matched == total, figures(d))

# ---------------------------------------------------------------- IU-01, a9-f09, M6, C4-03, panel-F1, docs-F1: the window
now = time.time()
r = new_repo("future")
write(r, "a.py", body("now", 10))
commit(r, "real", int(now - 30 * DAY))
write(r, "b.py", body("fut", 100))
commit(r, "wrong clock", int(now + 3 * 365 * DAY))
d = run(["future"])
check("gaps-a9-f09", "collect: a commit dated years ahead is not in use: 10 of 110 at the head", use(d) == (10, 0),
      figures(d))


def run_main(names, window="all", offset=None):
    """main() on the named repositories with the real collect; (exit code, coderprint.json)."""
    folder = tempfile.mkdtemp(prefix="main-", dir=ROOT)
    cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    cp.owner_login = lambda: OWNER
    cp.profile_offset = lambda owner: offset
    cp.profile_location = lambda owner: ""
    cp.list_repositories = lambda owner: [{"name": n, "isPrivate": True} for n in names]
    saved = dict(os.environ)
    os.environ.update({"FORCE": "1", "CARDS_WINDOW": window})
    try:
        code = cp.main()
    except Exception as e:
        code = "%s: %s" % (type(e).__name__, e)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    try:
        with open(os.path.join(folder, "assets", "coderprint.json"), encoding="utf-8") as f:
            return code, json.load(f)
    except OSError:
        return code, None


def headline(data):
    q = data["quantity"]
    return q["written_loc"]["value"], q["in_use_loc"]["value"]


code, data = run_main(["future"])
check("docs-F1", "main, all time: a future-dated commit is neither written nor in use: 10 and 10",
      data is not None and headline(data) == (10, 10) and data["left_out"]["future_dated_file_versions"] == 1,
      (code, data and headline(data)))
check("C4-03", "retained_fraction is never over 1", data is not None
      and data["quantity"]["retained_fraction"]["value"] <= 1, data and data["quantity"]["retained_fraction"])
check("in_use-UP-5", "coderprint.json says how many lines in use were traced and how many matched by text",
      data is not None and data["quantity"]["in_use_loc"].get("traced_loc") == 10
      and data["quantity"]["in_use_loc"].get("matched_by_text_loc") == 0, data and data["quantity"]["in_use_loc"])

for offset, label in ((None, "UTC"), ((9 * 60, None), "UTC+9")):
    zone = cp.local_zone(offset[0] if offset else None, "", time.time(), None)
    now = time.time()
    first = cp.first_day(now - 365 * DAY, zone)
    ok_all, seen = True, []
    for hour, tag in ((1, "early"), (22, "late")):
        name = "edge_%s_%s" % (label.replace("+", ""), tag)
        r = new_repo(name)
        write(r, "old.py", body(name, 50))
        commit(r, "on the window's first day", int(first + hour * 3600))
        for k in range(501):
            write(r, "imp/m%d.py" % k, "x_%d = %d\n" % (k, k))
        commit(r, "import on the first day", int(first + hour * 3600 + 60))
        write(r, "new.py", body(name + "new", 10))
        commit(r, "recent", int(now - 5 * DAY))
        code, data = run_main([name], window="12m", offset=offset)
        if data is None:
            ok_all = False
            seen.append((tag, code))
            continue
        seen.append((tag, headline(data), data["left_out"]["imports"]["commits"]))
    check("panel-F1", "12m at %s: a first-day commit early or late in its day is written and in use alike, and so is "
          "its import: %s" % (label, seen), len(seen) == 2 and ok_all and seen[0][1:] == seen[1][1:] == ((60, 60), 1),
          seen)
    partial = now - 365 * DAY + 600
    if partial < first - 60:   # the part of a day before the window's first whole day
        name = "edge_%s_partial" % label.replace("+", "")
        r = new_repo(name)
        write(r, "old.py", body(name, 500))
        commit(r, "before the first whole day", int(partial))
        write(r, "new.py", body(name + "new", 10))
        commit(r, "recent", int(now - 5 * DAY))
        code, data = run_main([name], window="12m", offset=offset)
        check("in_use-IU-01", "12m at %s: lines on the day before the window's first whole day are neither written "
              "nor in use: 10 and 10" % label, data is not None and headline(data) == (10, 10),
              (code, data and headline(data)))
    else:
        check("in_use-IU-01", "12m at %s: (the run is too near midnight to build a partial first day)" % label, True)
check("M6", "collect and main cut the window with one test", lambda: cp.window_holds(100, 100, 0)
      and not cp.window_holds(99, 100, 0) and not cp.window_holds(cp.FUTURE_SLACK + 1, None, 0)
      and cp.window_holds(cp.FUTURE_SLACK, None, 0), "window_holds")

# ---------------------------------------------------------------- the data file's words
defs = cp.DEFINITIONS
check("C4-07", "written's method says what stands where diffs could not be read, and in use claims no upper bound",
      "could not be read" in defs["written"]["method"] and "upper bound" not in json.dumps(defs["in_use"]),
      (defs["written"]["method"], defs["in_use"].get("limits")))
check("SPEC", "the in_use definition says it is traced, what falls back to text, and never exceeds written",
      "Traced" in defs["in_use"]["method"] and "matched_by_text_loc" in defs["in_use"]["method"]
      and "never exceeds written" in defs["in_use"]["means"], defs["in_use"])
# the source is coderprint.py and, from the release that split it, the parts it runs from generator/
parts = os.path.join(os.path.dirname(CP_PATH), "generator")
source = "".join(open(path, encoding="utf-8").read() for path in [CP_PATH] + sorted(
    os.path.join(parts, f) for f in (os.listdir(parts) if os.path.isdir(parts) else ()) if f.endswith(".py")))
check("M35", "the repository listing asks whether each repository is archived", "isArchived" in source)

remove(ROOT)
print("RESULT %d of %d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
