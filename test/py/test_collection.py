"""Audit fixes on synthetic Git histories, run through collect() of the
coderprint.py given as argv[1]. GitHub lookups are replaced by local fakes.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

CP_PATH = sys.argv[1]
spec = importlib.util.spec_from_file_location("cp", CP_PATH)
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

ROOT = tempfile.mkdtemp(prefix="audit-")
fails, passes = [], 0
OWNER = "owner1"
NOREPLY = "123+owner1@users.noreply.github.com"
T0 = 1700000000


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
        print("ok   ", name)
    else:
        fails.append(name)
        print("FAIL ", name, detail)


def git(repo, *args, when=None, author=("Owner One", NOREPLY), committer=None):
    env = dict(os.environ)
    when = when or T0
    committer = committer or author
    env.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=committer[0],
               GIT_COMMITTER_EMAIL=committer[1], GIT_AUTHOR_DATE="%d +0000" % when,
               GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false"] + list(args),
                       env=env, capture_output=True, timeout=60)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args, p.stderr.decode()))
    return p.stdout.decode()


def new_repo(name, fmt=None):
    path = os.path.join(ROOT, "src", name)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", "-b", "main"] + (["--object-format=" + fmt] if fmt else []) + [path],
                   check=True, timeout=60)
    return path


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="") as f:
        f.write(text)


def commit(repo, msg, when, author=("Owner One", NOREPLY), committer=None):
    git(repo, "add", "-A", when=when, author=author)
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, when=when, author=author, committer=committer)
    return git(repo, "rev-parse", "HEAD").strip()


SOURCES, FAIL_TIMES = {}, {}


def fake_clone(owner, name, dest):
    if FAIL_TIMES.get(name, 0) > 0:
        FAIL_TIMES[name] -= 1
        raise RuntimeError("git exited 128")
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    subprocess.run(["git", "clone", "-q", "--bare", SOURCES[name], dest], check=True, capture_output=True,
                   timeout=60)


LOGINS = {}   # email -> login, what the fake GitHub answers


def fake_resolve(owner, samples):
    return {e: LOGINS.get(e) for e in samples}


if os.environ.get("LOC_DEBUG"):
    import traceback

    def loud(fn):
        def wrapped(*a):
            try:
                return fn(*a)
            except Exception:
                traceback.print_exc()
                raise
        return wrapped
    cp.read_added_code, cp.read_head_code = loud(cp.read_added_code), loud(cp.read_head_code)
cp.clone = fake_clone
cp.resolve_authors = fake_resolve
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
cp.templates = lambda owner: {}
SEEDS = {}
cp.seed_blobs = lambda full_name, dest: SEEDS.get(full_name)


def run_collect(names, since=None):
    SOURCES.clear()
    for n in names:
        SOURCES[n] = os.path.join(ROOT, "src", n)
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    repos = [{"name": n, "isPrivate": True} for n in names]
    data = {"events": [], "commits": [], "imports": [], "import_lines": [], "mismatched": 0, "unread": None,
            "left_out": {}, "copies": None, "code": {}}
    try:   # so the same scenarios can be run against an older coderprint.py, which lacks some keys
        data.update(cp.collect(OWNER, repos, work, since) if since else cp.collect(OWNER, repos, work))
    except Exception as e:
        data["error"] = repr(e)
    return data


def lines(data):
    return sum(n for _, _, n in data["events"])


def use(data):
    c = data.get("code") or {}
    return c.get("production"), c.get("tests")


_tags = iter(range(10 ** 6))


def body(n, indent="", tag=None):
    """n distinct lines; each call makes content of its own unless tag repeats an earlier call's."""
    tag = next(_tags) if tag is None else tag
    return "".join("%sline_%s_%d = %d\n" % (indent, tag, i, i) for i in range(n))


# 1. M6: a formatter sweep and a line-ending sweep add no lines
r = new_repo("sweep")
for i in range(12):
    write(r, "m%d.py" % i, body(100, tag="m%d" % i))
commit(r, "write", T0)
for i in range(12):
    write(r, "m%d.py" % i, body(100, "    ", tag="m%d" % i))
write(r, "new_in_sweep.py", body(7))
commit(r, "reformat", T0 + 86400)
for i in range(12):
    write(r, "m%d.py" % i, body(100, "    ", tag="m%d" % i).replace("\n", "\r\n"))
commit(r, "crlf", T0 + 2 * 86400)
for i in range(2):   # a real edit of two files, changing as much as it adds, is below the sweep's size
    write(r, "m%d.py" % i, body(100, "    ", tag="e%d" % i).replace("\n", "\r\n"))
commit(r, "real edit", T0 + 3 * 86400)
d = run_collect(["sweep"])
check("M6 sweeps add nothing but their new file; a small edit counts: 1,200 + 7 + 200 lines, 4 commits",
      lines(d) == 1407 and len(d["commits"]) == 4, (lines(d), len(d["commits"]), d["mismatched"]))
check("M6 nothing unparsed", d["mismatched"] == 0, d["mismatched"])

# 2. M2: a collaborator's commits are not the owner's
r = new_repo("collab")
write(r, "a.py", body(10))
commit(r, "mine", T0)
for k in range(5):
    write(r, "b%d.py" % k, body(50))
    commit(r, "theirs %d" % k, T0 + 3600 * (k + 1), author=("Col Laborator", "col@example.com"))
LOGINS["col@example.com"] = "collaborator"
d = run_collect(["collab"])
check("M2 others left out: 10 lines, 1 commit, 5 others", lines(d) == 10 and len(d["commits"]) == 1
      and d["left_out"].get("others") == 5, (lines(d), len(d["commits"]), d["left_out"]))

# 3. M2: an unlinked laptop address counts in a solo repository, and in a shared one under the owner's name only
r = new_repo("solo")
write(r, "s.py", body(20))
commit(r, "laptop", T0, author=("Whoever", "me@laptop.local"))
r = new_repo("shared")
write(r, "x.py", body(10))
commit(r, "noreply", T0)
write(r, "y.py", body(30))
commit(r, "laptop, own name", T0 + 60, author=("Owner One", "owner@laptop.local"))
write(r, "z.py", body(40))
commit(r, "stranger", T0 + 120, author=("Stranger", "stranger@else.where"))
d = run_collect(["solo", "shared"])
check("M2 unknown kept in a solo repository and under the owner's name: 60 lines, 3 commits",
      lines(d) == 60 and len(d["commits"]) == 3 and d["left_out"].get("others") == 1,
      (lines(d), len(d["commits"]), d["left_out"]))

# 4. M2: an address listed in CARDS_AUTHOR_EMAILS is the owner's even beside a stranger
os.environ["CARDS_AUTHOR_EMAILS"] = "Stranger@Else.Where"
d = run_collect(["shared"])
check("M2 author-emails input: 80 lines", lines(d) == 80, (lines(d), d["left_out"]))
del os.environ["CARDS_AUTHOR_EMAILS"]

# 5. M8: a change cherry-picked into a second repository counts once
a = new_repo("pick-a")
write(a, "f.py", body(100, tag="pk"))
commit(a, "base", T0)
write(a, "f.py", body(100, tag="pk") + "fix = 1\n")
commit(a, "the fix", T0 + 500)
b = new_repo("pick-b")
write(b, "f.py", body(100, tag="pk") + "other = 2\n")
commit(b, "release base", T0 + 100)
write(b, "f.py", body(100, tag="pk") + "other = 2\nfix = 1\n")
commit(b, "the fix", T0 + 500)
d = run_collect(["pick-a", "pick-b"])
check("M8 landed twice counts once: 3 commits", len(d["commits"]) == 3 and d["left_out"].get("landed_twice") == 1,
      (len(d["commits"]), d["left_out"]))

# 6. M14: the owner's commit made by a workflow (committer github-actions[bot]) is automation
r = new_repo("scrape")
write(r, "scrape.py", body(15))
commit(r, "script", T0)
for k in range(30):
    write(r, "data.py", "x = %d\n" % k)
    commit(r, "data", T0 + 86400 * (k + 1),
           committer=("github-actions[bot]", "41898282+github-actions[bot]@users.noreply.github.com"))
write(r, "more.py", body(5))
commit(r, "Automated refresh", T0 + 86400 * 40, author=("Automated", "actions@users.noreply.github.com"))
d = run_collect(["scrape"])
check("M14 automation left out: 15 lines, 1 commit", lines(d) == 15 and len(d["commits"]) == 1
      and d["left_out"].get("automation") == 31, (lines(d), len(d["commits"]), d["left_out"]))

# 7. M3: node_modules does not make an import, and a real import records its lines
r = new_repo("beginner")
for k in range(600):
    write(r, "node_modules/p%d/index.js" % k, "module.exports = %d\n" % k)
write(r, "app.js", body(600))
commit(r, "first", T0)
d = run_collect(["beginner"])
check("M3 own code beside node_modules counts: 600 lines, no import", lines(d) == 600 and not d["imports"],
      (lines(d), len(d["imports"])))
r = new_repo("bigimport")
for k in range(501):
    write(r, "src/m%d.py" % k, body(2))
commit(r, "import", T0)
d = run_collect(["bigimport"])
check("M3 501 counted files is an import with 1,002 lines recorded", lines(d) == 0 and len(d["imports"]) == 1
      and d["import_lines"] == [(T0, 1002)], (lines(d), d["import_lines"]))

# 8. M5: a submodule is left out, gh-pages is not read
r = new_repo("subs")
write(r, "main.py", body(10))
commit(r, "main", T0)
sub = new_repo("inner")
write(sub, "lib.py", body(7))
commit(sub, "lib", T0)
git(r, "-c", "protocol.file.allow=always", "submodule", "add", "-q", sub, "inner", when=T0 + 10)
commit(r, "add submodule", T0 + 10)
git(r, "checkout", "-q", "--orphan", "gh-pages")
git(r, "rm", "-rq", "--cached", ".")
write(r, "site/index.html", "<p>x</p>\n" * 2000)
commit(r, "site", T0 + 20)
git(r, "checkout", "-q", "-f", "main")   # gh-pages is read only when it is the default branch
d = run_collect(["subs"])
check("M5 submodule and gh-pages left out: 10 lines, parsed", d["mismatched"] == 0
      and all(l != "HTML" for _, l, _ in d["events"]) and lines(d) == 10, (d["events"], d["mismatched"]))

# 9. M6: .git-blame-ignore-revs
r = new_repo("ignorer")
write(r, "a.py", body(50, tag="ig"))
commit(r, "write", T0)
write(r, "a.py", body(50, tag="ig").replace("_", "__"))
sweep = commit(r, "rename all", T0 + 100)
write(r, ".git-blame-ignore-revs", "# sweep\n%s\n" % sweep)
commit(r, "ignore it", T0 + 200)
d = run_collect(["ignorer"])
check("M6 a listed sweep adds no lines but is a commit: 50 lines, 3 commits",
      lines(d) == 50 and len(d["commits"]) == 3, (lines(d), len(d["commits"])))

# 10. M17: a repository that fails twice is left out; one that fails once is retried
r = new_repo("flaky")
write(r, "f.py", body(9))
commit(r, "f", T0)
r = new_repo("broken")
write(r, "g.py", body(11))
commit(r, "g", T0)
FAIL_TIMES.update(flaky=1, broken=2)
d = run_collect(["flaky", "broken"])
check("M17 retried once, then left out and counted", lines(d) == 9 and d["unread"] == 1, (lines(d), d["unread"]))

# 11. M13 and M3: another account's file versions count as seen; a commit of nothing else is a copy
r = new_repo("relaycopy")
write(r, "upstream.py", body(300, tag="up1"))
write(r, "lib/up.js", body(200, tag="up2"))
commit(r, "Initial commit", T0, author=("Owner One", NOREPLY))
blobs = set(git(r, "rev-list", "--objects", "--all").split())
SEEDS[cp.UPSTREAM] = blobs
write(r, "mine.py", body(12))
commit(r, "my change", T0 + 100)
d = run_collect(["relaycopy"])
check("M13 upstream seeded: 12 lines, 1 commit, 1 copied", lines(d) == 12 and len(d["commits"]) == 1
      and d["left_out"].get("copied") == 1 and not d["copies"], (lines(d), len(d["commits"]), d["left_out"]))
r = new_repo("purecopy")
write(r, "upstream.py", body(300, tag="up1"))
write(r, "lib/up.js", body(200, tag="up2"))
commit(r, "Initial commit", T0)
d = run_collect(["purecopy"])
check("M13 a repository of only upstream files is a copy", d["copies"] == {"purecopy"} and lines(d) == 0,
      d["copies"])
del SEEDS[cp.UPSTREAM]

# 12. S8: vendor as a whole folder name only
r = new_repo("vendors")
write(r, "src/vendor_portal/views.py", body(8))
write(r, "vendor/lib.py", body(90))
write(r, "s01t00_vendor/lib.rs", body(70))
write(r, "deps/go-vendor/x.go", body(60))
commit(r, "v", T0)
d = run_collect(["vendors"])
check("S8 vendor_portal counts; vendor/, s01t00_vendor/ and go-vendor/ do not: 8 lines", lines(d) == 8, lines(d))

# 13. S8: a SHA-256 repository is read
try:
    r = new_repo("sha256", fmt="sha256")
    write(r, "h.py", body(6))
    commit(r, "h", T0)
    d = run_collect(["sha256"])
    check("S8 SHA-256 history read: 6 lines", lines(d) == 6 and d["mismatched"] == 0, (lines(d), d["mismatched"]))
except SystemExit as e:
    print("skip  SHA-256 (this git cannot make one):", e)

# 14. organization: every member's work counts
cp.owner_identity = lambda owner: {"user": False, "id": None, "name": ""}
d = run_collect(["collab"])
check("M2 off for an organization: 260 lines, 6 commits", lines(d) == 260 and len(d["commits"]) == 6,
      (lines(d), len(d["commits"])))
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}

# 15. lookup failure: every commit counts rather than guessing
def broken_resolve(owner, samples):
    raise RuntimeError("gh exited 1")
cp.resolve_authors = broken_resolve
d = run_collect(["collab"])
check("M2 lookup failure counts everything", lines(d) == 260, lines(d))
cp.resolve_authors = fake_resolve

# 16. Lines of code: comments, blank lines, prose and data are not code
r = new_repo("comments")
write(r, "a.py", "# header comment\nimport os\n\ndef f():\n    \"\"\"Doc\n    more doc\n    \"\"\"\n"
                 "    x = 1  # a trailing comment is on a line of code\n    return x\n'''\nblock\n'''\n")
write(r, "b.ts", "// one\n/* two\n   three */\nconst y = 2;\n\n/** four */\nexport default y;\n")
write(r, "README.md", "words\n" * 30)
write(r, "notes.txt", "words\n" * 10)
write(r, "config.yaml", "a: 1\n" * 5)
commit(r, "c", T0)
d = run_collect(["comments"])
check("LOC comments, blanks, markdown, text and YAML left out: 6 lines, all in use", lines(d) == 6
      and use(d) == (6, 0), (lines(d), d["events"], use(d)))

# 17. Lines of code: test code by path, and Rust's inline test modules
r = new_repo("tests")
write(r, "src/main.py", body(10))
write(r, "tests/test_a.py", body(20))
write(r, "src/a_test.go", body(5))
write(r, "src/App.test.ts", body(7))
write(r, "src/FooTest.java", body(3))
write(r, "src/contest.py", body(4))
write(r, "src/lib.rs", "#[cfg(test)]\nuse std::fmt;\nfn a() -> i32 {\n    1\n}\n#[cfg(test)]\nmod tests {\n"
                       "    use super::*;\n    #[test]\n    fn t() {\n        assert_eq!(a(), 1);\n    }\n}\n")
commit(r, "t", T0)
d = run_collect(["tests"])
check("LOC production 10 + 4 + 3 Rust, tests 35 + 10 Rust", use(d) == (17, 45), use(d))

# 18. Lines of code: a deleted line is not in use; another's line at the head is not the owner's
r = new_repo("deleting")
write(r, "a.py", body(20, tag="del"))
commit(r, "write", T0)
write(r, "a.py", "".join(body(20, tag="del").splitlines(True)[:12]))
write(r, "b.py", body(9))
commit(r, "trim", T0 + 60, author=("Col Laborator", "col@example.com"))
d = run_collect(["deleting"])
check("LOC 20 written, 12 in use", lines(d) == 20 and use(d) == (12, 0), (lines(d), use(d)))
d = run_collect(["collab"])
check("LOC a collaborator's lines at the head are not in use: 10", use(d) == (10, 0), use(d))

# 19. Lines of code: a sweep's lines are still the owner's; an import's are not
d = run_collect(["sweep"])
check("LOC reformatted and re-ended lines stay in use: 1,207 of 1,407", lines(d) == 1407 and use(d) == (1207, 0),
      (lines(d), use(d)))
d = run_collect(["ignorer"])
check("LOC a listed sweep's lines are in use: 50", use(d) == (50, 0), use(d))
d = run_collect(["bigimport"])
check("LOC an import is not in use", use(d) == (0, 0), use(d))

# 20. Lines of code: only what was added since the window's start is in use for that window
r = new_repo("window")
write(r, "old.py", body(10))
commit(r, "old", T0)
write(r, "new.py", body(5))
commit(r, "new", T0 + 2 * 86400)
d = run_collect(["window"], since=T0 + 86400)
check("LOC window: 5 of the 15 at the head were added in it", use(d) == (5, 0), use(d))

# 20b. Lines of code: a file copied into a second repository is in use once, as it was written once
a = new_repo("copy-a")
write(a, "shared.py", body(30, tag="cp"))
commit(a, "write", T0)
b = new_repo("copy-b")
write(b, "shared.py", body(30, tag="cp"))
write(b, "own.py", body(5))
commit(b, "copy in", T0 + 100)
d = run_collect(["copy-a", "copy-b"])
check("LOC copied across repositories: 35 written, 35 in use", lines(d) == 35 and use(d) == (35, 0),
      (lines(d), use(d)))

# 20c. Lines of code: a rename across many files is a sweep; the renamed lines stay in use, never more than written
r = new_repo("rename")
for i in range(12):
    write(r, "r%d.py" % i, body(10, tag="rn%d" % i))
commit(r, "write", T0)
for i in range(12):
    write(r, "r%d.py" % i, body(10, tag="rn%d" % i).replace("line_", "row_"))
commit(r, "rename line_ to row_", T0 + 100)
d = run_collect(["rename"])
check("LOC a rename sweep: 120 written, 120 in use", lines(d) == 120 and use(d) == (120, 0), (lines(d), use(d)))

# 21. Lines of code: a repository whose diffs cannot be read falls back to numstat and is counted
real = cp.read_added_code
cp.read_added_code = lambda repo_dir: (_ for _ in ()).throw(RuntimeError("git exited 1"))
d = run_collect(["comments"])
cp.read_added_code = real
check("LOC unreadable diffs: numstat counts comments and blanks (19 lines), none in use, 1 counted",
      lines(d) == 19 and use(d) == (0, 0) and d["code"].get("unread") == 1, (lines(d), use(d), d["code"]))

shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d %s" % (passes, len(fails), fails))
sys.exit(1 if fails else 0)
