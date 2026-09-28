"""Regression checks for whose commits are whose: one check or more for each finding of the identity area
(identity-F1 to identity-F6, identity-U1 to identity-U4 and identity-U6), gaps-a9-f06 and a9-f07, the vote's M9, M12,
M20, M25 and M26, in_use-IU-06 and ops-F2.
Usage: python test_identity.py path/to/coderprint.py. It builds its repositories in a temporary folder with git's own
plumbing and runs collect() with every network lookup replaced by a fake, or main() end to end with gh and every clone
from github.com answered from those local repositories, so nothing reaches the network. It prints one line per check
and exits non-zero if any check fails."""
import contextlib
import importlib.util
import io
import json
import os
import re
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
ROOT = tempfile.mkdtemp(prefix="identity-")
OWNER = "owner1"
NOREPLY = "123+owner1@users.noreply.github.com"
ME = ("Owner One", NOREPLY)
COL = ("Col Laborator", "col@collab.example")
T0 = 1700000000
DAY = 86400
SOURCES = {}   # repository name -> bare repository
LINKED = {"col@collab.example": "collaborator"}   # a commit's own author address -> the login GitHub links it to
IDENTITY = {"user": True, "id": 123, "name": "Owner One"}
TEMPLATES, SEEDS, ASKED = {}, {}, []
results = []
for name in ("GH_TOKEN", "CLONE_CACHE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT", "CARDS_AUTHOR_EMAILS", "CARDS_TIME_LIMIT",
             "FORCE", "CARDS_OWNER", "GITHUB_REPOSITORY"):
    os.environ.pop(name, None)


def check(fid, name, ok, detail=""):
    if callable(ok):   # a check that may raise on an older coderprint.py, which lacks what it calls
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(bool(ok))
    print("%s %s %s%s" % ("PASS" if ok else "FAIL", fid, name, "" if ok else "  [got %r]" % (detail,)))


def git(repo, *args, data=None, when=T0, author=ME, committer=None):
    committer = committer or author
    env = dict(os.environ, GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=committer[0],
               GIT_COMMITTER_EMAIL=committer[1], GIT_AUTHOR_DATE="%d +0000" % when,
               GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo] + list(args), input=data, env=env, capture_output=True)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace")


def new_repo(name):
    path = os.path.join(ROOT, "src", name)
    if os.path.isdir(path):
        shutil.rmtree(path, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(path, ignore_errors=True)
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", path], check=True, capture_output=True)
    SOURCES[name] = path
    return path


def tree(repo, files):
    """files: {path: text}; nested folders made with mktree -z, the blobs hashed in one call."""
    folder, names = tempfile.mkdtemp(prefix="blobs-", dir=ROOT), []
    for k, text in enumerate(files.values()):
        names.append(os.path.join(folder, str(k)))
        with open(names[-1], "wb") as f:
            f.write(text.encode("utf-8"))
    shas = git(repo, "hash-object", "-w", "--no-filters", "--stdin-paths",
               data=("\n".join(names) + "\n").encode()).split()
    shutil.rmtree(folder, ignore_errors=True)
    top = {}
    for (path, _), sha in zip(files.items(), shas):
        node = top
        for part in path.split("/")[:-1]:
            node = node.setdefault(part, {})
        node[path.split("/")[-1]] = sha

    def build(node):
        feed = b""
        for name, v in sorted(node.items()):
            if isinstance(v, dict):
                feed += b"040000 tree " + build(v).encode() + b"\t" + name.encode("utf-8") + b"\x00"
            else:
                feed += ("100644 blob %s\t" % v).encode() + name.encode("utf-8") + b"\x00"
        return git(repo, "mktree", "-z", "--missing", data=feed).strip()
    return build(top)


def commit(repo, files, parents=(), msg="c", when=T0, author=ME, committer=None, ref="refs/heads/main"):
    args = ["commit-tree", tree(repo, files), "-m", msg]
    for p in parents:
        args += ["-p", p]
    sha = git(repo, *args, when=when, author=author, committer=committer).strip()
    if ref:
        git(repo, "update-ref", ref, sha)
    return sha


def chain(repo, steps, parent=None):
    """steps: [(files, message, time, author)], each the whole tree, each the child of the one before."""
    shas = []
    for files, msg, when, author in steps:
        shas.append(commit(repo, files, [parent] if parent else [], msg, when, author))
        parent = shas[-1]
    return shas


def writable(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


def body(n, tag, indent=""):
    return "".join("%sline_%s_%d = %d\n" % (indent, tag, i, i) for i in range(n))


def fake_clone(owner, name, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(dest, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "--bare", SOURCES[name], dest], check=True, capture_output=True)


def github_resolve(owner, samples):
    """As GitHub answers: the login linked to the sample commit's own author address, which knows no .mailmap."""
    ASKED.append(dict(samples))
    return {e: LINKED.get(git(SOURCES[name], "show", "-s", "--format=%ae", sha).strip().lower())
            for e, (name, sha) in samples.items()}


cp.clone = fake_clone
cp.resolve_authors = github_resolve
cp.owner_identity = lambda owner: dict(IDENTITY)
cp.templates = lambda owner: dict(TEMPLATES)
cp.seed_blobs = lambda full_name, dest: SEEDS.get(full_name)


def run(names):
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    try:
        return cp.collect(OWNER, [{"name": n, "isPrivate": True} for n in names], work)
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "events": [], "commits": [], "code": {}, "imports": [],
                "left_out": {}, "import_lines": []}


def lines(d):
    return sum(n for _, _, n in d["events"])


def use(d):
    return d["code"].get("production"), d["code"].get("tests")


def summary(d):
    return (lines(d), use(d), len(d["commits"]), d["left_out"], d.get("error"))


def with_emails(value, names):
    os.environ["CARDS_AUTHOR_EMAILS"] = value
    try:
        return run(names)
    finally:
        del os.environ["CARDS_AUTHOR_EMAILS"]


# ---------------------------------------------------------------- identity-F2, IU-06, M20: landed twice, or not
repo = new_repo("scripted")
steps = [({"base.py": body(1, "sc0")}, "base", T0 - DAY, ME)]
files = dict(steps[0][0])
for k in range(5):
    files = dict(files, **{"gen%d.py" % k: body(20, "sc%d" % (k + 1))})
    steps.append((dict(files), "generate", T0, ME))
chain(repo, steps)
d = run(["scripted"])
check("identity-F2", "five scripted commits in one second under one subject: 101 written, 6 commits",
      (lines(d), len(d["commits"])) == (101, 6), summary(d))
repo = new_repo("split")
base = chain(repo, [({"a.py": body(10, "sp0")}, "base", T0 - DAY, ME)])[0]
half = commit(repo, {"a.py": body(10, "sp0"), "b.py": body(5, "sp1")}, [base], "feature", T0)
commit(repo, {"a.py": body(10, "sp0"), "b.py": body(5, "sp1"), "c.py": body(5, "sp2")}, [half], "feature", T0)
d = run(["split"])
check("identity-F2", "a commit split in two halves (git commit -C): 20 written, 3 commits",
      (lines(d), len(d["commits"])) == (20, 3), summary(d))
new_repo("mono-a")
chain(SOURCES["mono-a"], [({"x.py": body(30, "mo1")}, "move the service", T0, ME)])
new_repo("mono-b")
chain(SOURCES["mono-b"], [({"y.py": body(40, "mo2")}, "move the service", T0, ME)])
d = run(["mono-a", "mono-b"])
check("identity-F2", "a monorepo split into two repositories in one second: 70 written, 2 commits",
      (lines(d), len(d["commits"])) == (70, 2), summary(d))
for first in ("tagged", "amended"):
    repo = new_repo("amend-" + first)
    base = commit(repo, {"a.py": body(5, "am0" + first)}, (), "base", T0 - DAY, ref=None)
    old = {"a.py": body(5, "am0" + first), "f.py": body(20, "am1" + first)}
    new = dict(old, **{"g.py": body(15, "am2" + first)})
    one, two = (old, new) if first == "tagged" else (new, old)
    x = commit(repo, one, [base], "feature", T0, ref="refs/heads/main" if first == "amended" else "refs/tags/v1")
    commit(repo, two, [base], "feature", T0, ref="refs/heads/main" if first == "tagged" else "refs/tags/v1")
    d = run(["amend-" + first])
    check("identity-F2", "an amend adding a forgotten file, the original kept by a tag (%s on main): 40 written, 40 in "
          "use, 2 commits" % ("amend" if first == "tagged" else "original"),
          (lines(d), use(d), len(d["commits"]), d["left_out"].get("landed_twice")) == (40, (40, 0), 2, 1), summary(d))
repo = new_repo("amend-line")
base = commit(repo, {"a.py": body(5, "al0")}, (), "base", T0 - DAY, ref=None)
x = commit(repo, {"a.py": body(5, "al0"), "f.py": body(20, "al1")}, [base], "feature", T0, ref="refs/tags/v1")
commit(repo, {"a.py": body(5, "al0"), "f.py": body(20, "al1").replace("= 7\n", "= 70\n")}, [base], "feature", T0)
d = run(["amend-line"])
check("in_use-IU-06", "an amend that rewrote one line, the original kept by a tag: the rewritten line counts again, "
      "26 written, 25 in use, 2 commits", (lines(d), use(d), len(d["commits"])) == (26, (25, 0), 2), summary(d))
a = new_repo("pick-a")
a1 = commit(a, {"f.py": body(20, "pk")}, (), "base", T0 - DAY)
commit(a, {"f.py": body(20, "pk") + "fix = 1\n"}, [a1], "the fix", T0)
b = new_repo("pick-b")
b1 = commit(b, {"g.py": body(20, "pk") + "other = 2\n"}, (), "release", T0 - DAY + 100)
commit(b, {"g.py": body(20, "pk") + "other = 2\nfix = 1\nresolved = 3\n"}, [b1], "the fix", T0)
d = run(["pick-a", "pick-b"])
check("in_use-IU-06", "a backport whose conflict's resolution wrote a line: that line counts, the fix once, 43 "
      "written, 3 commits", (lines(d), len(d["commits"]), d["left_out"].get("landed_twice")) == (43, 3, 1), summary(d))
for order in ("small first", "import first"):
    small, big = new_repo("im-small-" + order[0]), new_repo("im-big-" + order[0])
    shared = body(3, "imp" + order[0])
    imported = {"lib/m%03d.py" % k: body(2, "imq%d%s" % (k, order[0])) for k in range(501)}
    imported["s.py"] = shared + "# carried along\n"   # the same lines of code in another file version
    chain(small, [({"s.py": shared}, "start", T0, ME)])
    chain(big, [(imported, "start", T0, ME)])
    names = ["im-small-" + order[0], "im-big-" + order[0]]
    d = run(names if order == "small first" else names[::-1])
    check("in_use-IU-06", "an import sharing author, second, subject and lines with a small commit (%s): 3 written, "
          "in use 3" % order, (lines(d), use(d)) == (3, (3, 0)), summary(d))

# ---------------------------------------------------------------- identity-F3: a .mailmap changes no one's address
old = new_repo("oldwork")
chain(old, [({"a.py": body(30, "mm1")}, "old job work", T0, ("pete", "me@oldjob.example")),
            ({"a.py": body(30, "mm1"), "b.py": body(40, "mm2")}, "colleague", T0 + 60, COL),
            ({"a.py": body(30, "mm1"), "b.py": body(40, "mm2"), ".mailmap": "pete <me@personal.example> "
              "<me@oldjob.example>\n"}, "mailmap", T0 + 120, ("pete", "me@oldjob.example"))])
new = new_repo("newwork")
chain(new, [({"c.py": body(50, "mm3")}, "today's work", T0 + DAY, ("pete", "me@personal.example")),
            ({"c.py": body(50, "mm3"), "d.py": body(60, "mm4")}, "colleague", T0 + DAY + 60, COL)])
LINKED["me@personal.example"] = OWNER
d = run(["oldwork", "newwork"])
check("identity-F3", "a .mailmap in one repository does not take the owner's linked address, or its 50 lines, off the "
      "card: 80 written, 3 commits, the colleague's 2 left out",
      (lines(d), len(d["commits"]), d["left_out"].get("others")) == (80, 3, 2), summary(d))

# ---------------------------------------------------------------- identity-F4: one commit in two repositories
team = new_repo("team")
c1 = commit(team, {"core.py": body(25, "f4")}, (), "core", T0, ("pete", "pete@laptop.example"))
commit(team, {"core.py": body(25, "f4"), "col.py": body(5, "f4c")}, [c1], "col", T0 + 60, COL)
personal = new_repo("personal")
git(personal, "fetch", "-q", team, "refs/heads/main:refs/heads/main")
git(personal, "update-ref", "refs/heads/main", c1)
d1, d2 = run(["team", "personal"]), run(["personal", "team"])
check("identity-F4", "a commit two repositories hold is the owner's if it is in either, whichever was made first: 25 "
      "and 25", (lines(d1), len(d1["commits"]), lines(d2), len(d2["commits"])) == (25, 1, 25, 1),
      (summary(d1), summary(d2)))

# ---------------------------------------------------------------- identity-F5: the empty file tells no copy
EMPTY = git(new_repo("scratch"), "hash-object", "--stdin", data=b"").strip()
repo = new_repo("from-template")
tmpl = {"t.py": body(40, "tp"), ".gitkeep": ""}
chain(repo, [(tmpl, "Initial commit", T0 - DAY, ME),
             (dict(tmpl, **{"src/app.py": body(12, "f5")}), "code", T0, ME),
             (dict(tmpl, **{"src/app.py": body(12, "f5"), "src/pkg/__init__.py": ""}), "add a package", T0 + DAY, ME)])
TEMPLATES["from-template"] = "someone/template"
SEEDS["someone/template"] = {git(repo, "rev-parse", "HEAD~2:t.py").strip(), EMPTY}
d = run(["from-template"])
TEMPLATES.clear()
SEEDS.clear()
check("identity-F5", "a commit adding only an empty file is a commit though the template holds one, and the template's "
      "own first commit is still a copy: 12 written, 2 commits, 1 copied",
      (lines(d), len(d["commits"]), d["left_out"].get("copied")) == (12, 2, 1), summary(d))

# ---------------------------------------------------------------- identity-F6: a unit separator inside a name
repo = new_repo("separator")
chain(repo, [({"m.py": body(10, "f6")}, "mine", T0, ME),
             ({"m.py": body(10, "f6"), "x.py": body(33, "f6x")}, "odd name", T0 + 60,
              ("Col\x1f%s" % NOREPLY, "col@collab.example"))])
d = run(["separator"])
check("identity-F6", "a name holding 0x1F does not shift the address: 10 written, the collaborator left out",
      (lines(d), d["left_out"].get("others"), d["mismatched"]) == (10, 1, 0), summary(d))

# ---------------------------------------------------------------- identity-U1, M26: author-emails
repo = new_repo("emails")
chain(repo, [({"a.py": body(10, "u1a")}, "mine", T0, ME),
             ({"a.py": body(10, "u1a"), "b.py": body(20, "u1b")}, "work", T0 + 10, ("Pat Q", "me@work.example")),
             ({"a.py": body(10, "u1a"), "b.py": body(20, "u1b"), "c.py": body(30, "u1c")}, "home", T0 + 20,
              ("Pat Q", "me@home.example")),
             ({"a.py": body(10, "u1a"), "b.py": body(20, "u1b"), "c.py": body(30, "u1c"), "d.py": body(40, "u1d")},
              "col", T0 + 30, COL)])
got = {}
for label, value in [("commas", " ME@Work.example ,, me@home.example , "), ("new lines", "me@work.example\nme@home.example\n"),
                     ("spaces", "me@work.example me@home.example"), ("semicolons", "me@work.example; me@home.example"),
                     ("Name <address>", "Pat Q <me@work.example>, \"Pat Q\" <me@home.example>")]:
    got[label] = lines(with_emails(value, ["emails"]))
check("identity-U1", "author-emails in any list form: 60 each", set(got.values()) == {60}, got)
d = with_emails("col@collab.example, me@work.example", ["emails"])
check("M26", "an author-emails address linked to another account is not the owner's: its 40 lines left out, the "
      "rest 60 (me@home.example under the name me@work.example's commits use), 1 refused",
      (lines(d), d["left_out"].get("others"), d.get("authors", {}).get("refused")) == (60, 1, 1),
      (summary(d), d.get("authors")))

# ---------------------------------------------------------------- identity-U2: noreply addresses decided locally
repo = new_repo("noreply-mix")
files, steps = {"m.py": body(10, "u2m")}, []
steps.append((dict(files), "mine", T0, ME))
files["o.py"] = body(7, "u2o")
steps.append((dict(files), "renamed", T0 + 5, ("Owner One", "123+oldlogin@users.noreply.github.com")))
for k in range(6):
    files["c%d.py" % k] = body(3, "u2c%d" % k)
    steps.append((dict(files), "c", T0 + 10 + k, ("C%d" % k, "%d+c%d@users.noreply.github.com" % (900 + k, k))))
chain(repo, steps)
del ASKED[:]
d = run(["noreply-mix"])
asked = sum(len(a) for a in ASKED)
check("identity-U2", "the owner's id-form noreply under an old login counts, others' never do, with no lookup: 17 "
      "written, 0 asked", (lines(d), asked) == (17, 0), (summary(d), asked))
new_repo("bot-alone")
chain(SOURCES["bot-alone"], [({"b.py": body(50, "u2b")}, "agent", T0, ("Copilot",
                                                                           "198982749+Copilot[bot]@users.noreply.github.com"))])
new_repo("other-alone")
chain(SOURCES["other-alone"], [({"o.py": body(40, "u2x")}, "theirs", T0, ("Someone", "555+someone@users.noreply.github.com"))])
d = run(["bot-alone", "other-alone"])
check("identity-U2", "an App's noreply is automation and another account's noreply is theirs, alone or not: 0 written",
      (lines(d), d["left_out"]) == (0, {"automation": 1, "others": 1}), summary(d))
repo = new_repo("oldform")
chain(repo, [({"s.py": body(20, "u2s")}, "before the rename", T0, ("Owner One", "oldlogin@users.noreply.github.com")),
             ({"s.py": body(20, "u2s"), "k.py": body(9, "u2k")}, "col", T0 + 60, COL)])
d = run(["oldform"])
check("identity-U2", "the owner's login-only noreply from before a rename is still looked up and counts under their "
      "name: 20 written", lines(d) == 20, summary(d))

# ---------------------------------------------------------------- identity-U3: bots and agents under their own names
new_repo("agent-alone")
chain(SOURCES["agent-alone"], [({"a.py": body(40, "u3a")}, "agent work", T0, ("Cursor Agent", "agent@agent.example"))])
new_repo("renovate-alone")
chain(SOURCES["renovate-alone"], [({"b.py": body(60, "u3b")}, "renovate", T0, ("Renovate Bot", "bot@renovate.example"))])
d = run(["agent-alone", "renovate-alone"])
check("identity-U3", "a coding agent or a self-hosted bot alone in a repository is automation: 0 written",
      (lines(d), d["left_out"]) == (0, {"automation": 2}), summary(d))
repo = new_repo("agent-beside")
chain(repo, [({"m.py": body(10, "u3m")}, "mine", T0, ME),
             ({"m.py": body(10, "u3m"), "c.py": body(30, "u3c")}, "agent work", T0 + 60,
              ("Cursor Agent", "agent@agent.example"))])
d = run(["agent-beside"])
check("identity-U3", "the same agent beside the owner is automation too: 10 written",
      (lines(d), d["left_out"]) == (10, {"automation": 1}), summary(d))
IDENTITY["name"] = "Jan Bot"
repo = new_repo("jan-shared")
chain(repo, [({"j.py": body(25, "u3j")}, "mine", T0, ("Jan Bot", NOREPLY)),
             ({"j.py": body(25, "u3j"), "k.py": body(5, "u3k")}, "col", T0 + 60, COL)])
new_repo("jan-laptop")
chain(SOURCES["jan-laptop"], [({"l.py": body(40, "u3l")}, "laptop", T0, ("Jan Bot", "jan@laptop.example"))])
d = run(["jan-shared", "jan-laptop"])
IDENTITY["name"] = "Owner One"
check("identity-U3", "an owner whose name ends in Bot keeps their own work: 65 written", lines(d) == 65, summary(d))

# ---------------------------------------------------------------- identity-U4: what makes a repository solo, said
readme = open(os.path.join(os.path.dirname(CP_PATH), "README.md"), encoding="utf-8").read()
check("identity-U4", "README says an unlinked address counts alone only where it is the only address with commits, "
      "the owner's own linked ones included", "the only address with commits, bots aside" in readme
      and "a repository you created on github.com with a README already holds a commit from one" in readme)
repo = new_repo("made-on-github")
chain(repo, [({"README.md": "# x\n"}, "Initial commit", T0, ME),
             ({"README.md": "# x\n", "app.py": body(80, "u4")}, "laptop", T0 + 60, ("laptop", "me@laptop.local"))])
d = run(["made-on-github"])
check("identity-U4", "as it says: laptop commits under another name beside the owner's linked address add nothing",
      lines(d) == 0, summary(d))

# ---------------------------------------------------------------- gaps-a9-f06: a generic name is nobody's
IDENTITY["name"] = "Owner One"
new_repo("server")
chain(SOURCES["server"], [({"srv.py": body(20, "g1")}, "on the server", T0, ("root", NOREPLY))])
repo = new_repo("shared-generic")
chain(repo, [({"x.py": body(30, "g2")}, "mine", T0, ME),
             ({"x.py": body(30, "g2"), "y.py": body(500, "g3")}, "stranger", T0 + 60, ("root", "root@server.example")),
             ({"x.py": body(30, "g2"), "y.py": body(500, "g3"), "z.py": body(4, "g4")}, "mine, laptop", T0 + 120,
              ("Owner One", "owner@laptop.example"))])
d = run(["server", "shared-generic"])
check("gaps-a9-f06", "a stranger named root beside the owner, who once committed as root, is not the owner; the "
      "owner's profile name still is: 54 written, 1 left out", (lines(d), d["left_out"].get("others")) == (54, 1),
      summary(d))
check("gaps-a9-f06", "generic names are nobody's", lambda: {"root", "your name", "vscode", "ubuntu"} <= cp.GENERIC_NAMES)

# ---------------------------------------------------------------- gaps-a9-f07: the lookup's limit, and what it misses
capped = load()
ANSWER, UNANSWERED, calls = {}, set(), []


def fake_gql(query, timeout=None, errors=None, **variables):
    calls.append(1)
    data = {}
    for alias, inner in re.findall(r"(r\d+): repository\([^)]*\) \{ (.*?) \} (?=r\d+:|$)", query + " "):
        repo = {}
        for c, sha in re.findall(r'(c\d+): object\(oid: "([0-9a-f]+)"\)', inner):
            if sha in UNANSWERED:
                repo[c] = None
                if errors is not None:
                    errors.append({"message": "Something went wrong", "path": [alias, c]})
                continue
            login = ANSWER.get(sha)
            repo[c] = {"author": {"user": {"login": login} if login else None}}
        data[alias] = repo
    return data


capped.gql = fake_gql
commits, k = [], 0
repos = [{"name": "big-mirror"}, {"name": "my-tool"}, {"name": "lonely"}, {"name": "shared-x"}]
for i in range(1100):   # 1,100 other people, 3 commits each, each linked to an account of their own
    for j in range(3):
        sha = "%040x" % k
        k += 1
        ANSWER[sha] = "person%d" % i
        commits.append(capped.Commit(T0 + k, 0, sha, False, "p%d@example.org" % i, "Person %d" % i, "s", []))
for r in (0, 1):   # the owner's own linked address, used twice, under a name that is neither profile nor login
    sha = "%040x" % k
    k += 1
    ANSWER[sha] = OWNER
    commits.append(capped.Commit(T0 + k, r, sha, False, "owner.work@corp.example", "P. Owner", "s", []))
commits.append(capped.Commit(T0 + k + 1, 1, "%040x" % (k + 1), False, NOREPLY, "Owner Name", "s", []))
UNANSWERED.update({"%040x" % (k + 2), "%040x" % (k + 3)})   # GitHub answers these with an error
commits.append(capped.Commit(T0 + k + 2, 2, "%040x" % (k + 2), False, "who@unanswered.example", "Who", "s", []))
commits.append(capped.Commit(T0 + k + 3, 3, "%040x" % (k + 3), False, "me@unanswered.example", "Owner Name", "s", []))
commits.append(capped.Commit(T0 + k + 4, 3, "%040x" % (k + 4), False, NOREPLY, "Owner Name", "s", []))
notes = {}
try:
    mine = capped.authorship(OWNER, commits, {"user": True, "id": 123, "name": "Owner Name"}, repos, notes)
except TypeError:   # an older coderprint.py, whose authorship takes no notes
    mine = capped.authorship(OWNER, commits, {"user": True, "id": 123, "name": "Owner Name"}, repos)
check("gaps-a9-f07", "the owner's linked address, used twice among 1,100 others, is asked within the limit and counts "
      "in both repositories", mine is not None and {(0, "owner.work@corp.example"), (1, "owner.work@corp.example")}
      <= mine, (len(calls), sorted(p for p in (mine or ()) if "owner" in p[1])))
check("gaps-a9-f07", "an address GitHub did not answer for counts only under the owner's name, never as alone in a "
      "repository, and is counted as unverified",
      mine is not None and (2, "who@unanswered.example") not in mine and (3, "me@unanswered.example") in mine
      and len(notes.get("unknown", ())) >= 2, (notes.get("unknown"), sorted(p for p in (mine or ()) if p[0] >= 2)))

# ---------------------------------------------------------------- the lookups' own answers: data null, errors, partial
def _raises(f):
    try:
        f()
    except Exception as e:
        return e
    return None


raw = load()
raw.run = lambda args, cwd=None, env=None, timeout=None: b'{"data": null, "errors": [{"message": "x"}]}'
check("identity-F1", "an answer whose data is null fails as GitHub not answering, not as an AttributeError",
      lambda: isinstance(_raises(lambda: raw.gql("query { viewer { login } }")), RuntimeError))
check("identity-F1", "resolve_authors on a null answer raises RuntimeError, and authorship then gives None",
      lambda: isinstance(_raises(lambda: raw.resolve_authors(OWNER, {"a@b.example": ("r", "a" * 40)})), RuntimeError)
      and raw.authorship(OWNER, [raw.Commit(T0, 0, "a" * 40, False, "a@b.example", "A", "s", [])],
                         {"user": True, "id": 123, "name": ""}, [{"name": "r"}]) is None)


def answering(m, status, answer):
    def fake(args, cwd=None, env=None, timeout=None):
        out = json.dumps(answer).encode()
        if status:
            raise m.Failed("gh exited 1", out)
        return out
    return fake


page = {"repositoryOwner": {"repositories": {"nodes": [
    {"name": "a", "templateRepository": None}, {"name": "b", "templateRepository": None},
    {"name": "c", "templateRepository": {"nameWithOwner": "someone/tmpl"}},
    {"name": "d", "templateRepository": {"nameWithOwner": "owner1/mine"}}],
    "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
hidden = {"data": page, "errors": [{"type": "FORBIDDEN", "message": "Resource not accessible by integration",
                                    "path": ["repositoryOwner", "repositories", "nodes", 1, "templateRepository"]}]}
raw.run = answering(raw, 1, hidden)
check("identity-F1", "a template the token cannot see, named in an error beside the data gh exits 1 on, marks only its "
      "own repository as unknown", lambda: raw.templates(OWNER) == {"b": None, "c": "someone/tmpl"})
raw.run = answering(raw, 1, {"data": page, "errors": [{"message": "Something went wrong"}]})
check("identity-F1", "an error that names no repository leaves every template unknown: None",
      lambda: raw.templates(OWNER) is None)
raw.run = answering(raw, 1, {"message": "Bad credentials"})
check("identity-F1", "no answer at all: None", lambda: raw.templates(OWNER) is None)
raw.run = answering(raw, 1, {"data": {"r0": {"c0": {"author": {"user": {"login": "someone"}}}, "c1": None}},
                              "errors": [{"message": "x", "path": ["r0", "c1"]}]})
check("identity-F1", "an error naming one commit leaves only its address unknown",
      lambda: raw.resolve_authors(OWNER, {"x@y.example": ("r", "a" * 40), "z@y.example": ("r", "b" * 40)})
      == {"x@y.example": "someone"})
raw.run = answering(raw, 1, {"data": {"r0": None}, "errors": [{"message": "x"}]})
check("identity-F1", "an error that names no address fails the lookup",
      lambda: isinstance(_raises(lambda: raw.resolve_authors(OWNER, {"x@y.example": ("r", "a" * 40)})), RuntimeError))
tries = []


def flaky(args, cwd=None, env=None, timeout=None):
    tries.append(1)
    if len(tries) == 1:
        raise RuntimeError("gh exited 1")
    return b'{"data": {"repositoryOwner": {"__typename": "User", "databaseId": 123, "name": "Owner One"}}}'


raw.run = flaky
check("identity-F1", "a lookup that fails once is asked again", lambda: raw.owner_identity(OWNER)["id"] == 123
      and len(tries) == 2)

# ---------------------------------------------------------------- ops-F2: a command the deadline cuts short
timed = load()
timed.DEADLINE = time.monotonic() + timed.RESERVE + 1
check("ops-F2", "a command refused for want of time fails as OutOfTime",
      lambda: isinstance(_raises(lambda: timed.run(["git", "--version"])), timed.OutOfTime))
check("ops-F2", "and so does limit()", lambda: isinstance(_raises(timed.limit), timed.OutOfTime))
check("ops-F2", ".git-blame-ignore-revs out of time is not an empty list: it fails, so the repository is left out",
      lambda: isinstance(_raises(lambda: timed.ignored_revs(SOURCES["scripted"])), timed.OutOfTime))
OUT_OF_TIME = getattr(timed, "OutOfTime", None)   # None in an older coderprint.py
timed.DEADLINE = time.monotonic() + timed.RESERVE + 8
e = _raises(lambda: timed.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=60))
check("ops-F2", "a command the deadline cut short fails as OutOfTime",
      OUT_OF_TIME is not None and isinstance(e, OUT_OF_TIME), repr(e))
timed.DEADLINE = None
e = _raises(lambda: timed.run([sys.executable, "-c", "import time; time.sleep(30)"], timeout=2))
check("ops-F2", "one that ran past its own timeout, not the run's, is a plain failure",
      OUT_OF_TIME is not None and isinstance(e, RuntimeError) and not isinstance(e, OUT_OF_TIME), repr(e))
check("ops-F2", "without a deadline a missing .git-blame-ignore-revs lists nothing",
      lambda: timed.ignored_revs(SOURCES["scripted"]) == set())

# ---------------------------------------------------------------- identity-F1, U6, M9, M12, M25, ops-F2: main()
# The account: a public repository with 10 lines of the owner's and 500 of a collaborator's, a public one made from
# another account's template (600 template lines, 5 of the owner's), and a private relay copy of coderprint. The
# true card: 15 lines written, 2 commits, public only.
shared = new_repo("shared")
chain(shared, [({"mine.py": body(10, "m1")}, "mine", T0, ME),
               ({"mine.py": body(10, "m1"), "theirs.py": body(500, "m2")}, "theirs", T0 + 60, COL)])
UP = {"coderprint.py": body(300, "up1"), "lib/compose.js": body(80, "up2"), "api/card.js": body(50, "up3")}
chain(new_repo("upstream"), [(UP, "upstream", T0 - DAY, ("Upstream Author", "up@upstream.example"))])
chain(new_repo("relaycopy"), [(UP, "Initial commit", T0 + 120, ME)])
chain(new_repo("tmplsrc"), [({"t.py": body(600, "tm")}, "template", T0 - DAY, ("Tmpl Author", "t@tmpl.example"))])
chain(new_repo("from-tmpl"), [({"t.py": body(600, "tm")}, "Initial commit", T0 + 200, ME),
                              ({"t.py": body(600, "tm"), "own.py": body(5, "m3")}, "own", T0 + 300, ME)])
chain(new_repo("extra"), [({"e.py": body(3, "m4")}, "extra", T0 + 400, ME)])
REPOS = [{"name": "shared", "isPrivate": False}, {"name": "from-tmpl", "isPrivate": False},
         {"name": "relaycopy", "isPrivate": True}]
REMOTE = {"WikdSolvemProbler/coderprint": "upstream", "someone/tmpl": "tmplsrc"}


class Clock:
    """A clock for the run's deadline that moves only when a clone is made (see emulate)."""

    def __init__(self):
        self.t = 5000.0

    def monotonic(self):
        return self.t

    def __getattr__(self, name):
        return getattr(time, name)


def emulate(m, fail, repos, clock=None, cost=0):
    """m.run with the real deadline check, answering gh and every clone from github.com from the local repositories,
    and failing the test on anything else that would reach GitHub."""
    real_run, asked = m.run, []

    def graphql(query):
        asked.append(query)
        if "templateRepository" in query:
            if "templates" in fail:
                return 1, {"errors": [{"message": "Something went wrong"}]}
            nodes = [{"name": r["name"], "templateRepository": {"nameWithOwner": "someone/tmpl"}
                      if r["name"] == "from-tmpl" else None} for r in repos]
            answer = {"data": {"repositoryOwner": {"repositories": {
                "nodes": nodes, "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}
            if "hidden" in fail:
                k = [r["name"] for r in repos].index("from-tmpl")
                nodes[k]["templateRepository"] = None
                answer["errors"] = [{"type": "FORBIDDEN", "message": "Resource not accessible by integration",
                                     "path": ["repositoryOwner", "repositories", "nodes", k, "templateRepository"]}]
                return 1, answer
            return 0, answer
        if "__typename" in query:
            if "identity" in fail or ("identity once" in fail and sum("__typename" in q for q in asked) == 1):
                return 1, {"message": "Bad credentials"}
            return 0, {"data": {"repositoryOwner": {"__typename": "User", "databaseId": 123, "name": "Owner One"}}}
        if "object(oid" in query:
            if "resolve" in fail:
                return 1, {"message": "API rate limit exceeded"}
            if "null" in fail:
                return 0, {"data": None}
            data = {}
            heads = list(re.finditer(r'r(\d+): repository\(owner: "[^"]+", name: "([^"]+)"\)', query))
            for i, h in enumerate(heads):
                seg = query[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(query)]
                data["r" + h.group(1)] = {"c" + c.group(1): {"author": {"user": (
                    {"login": LINKED[raw_author]} if (raw_author := git(SOURCES[h.group(2)], "show", "-s", "--format=%ae",
                                                                        c.group(2)).strip().lower()) in LINKED
                    else None)}} for c in re.finditer(r'c(\d+): object\(oid: "([0-9a-f]+)"\)', seg)}
            return 0, {"data": data}
        raise AssertionError("an unexpected query")

    def fake_run(args, cwd=None, env=None, timeout=m.TIMEOUT):
        what = os.path.basename(args[0])
        left = m.time_left()   # fails as OutOfTime, as the real run() does
        if what == "gh":
            status, answer = graphql(next(a[6:] for a in args if a.startswith("query=")))
            out = json.dumps(answer).encode()
            if status:
                raise m.Failed("gh exited 1", out)
            return out
        url = next((a for a in args if "github.com" in str(a)), None)
        if url:
            full = url.split("https://github.com/", 1)[1][:-len(".git")]
            if full in fail:
                raise m.Failed("git exited 128")
            if clock is not None and "--filter=blob:none" not in args:   # reading a repository takes time
                if left is not None and cost > left:
                    clock.t += left
                    raise m.OutOfTime("git timed out after %d seconds: the run is out of time" % left)
                clock.t += cost
            subprocess.run(["git", "clone", "-q", "--bare", SOURCES[REMOTE.get(full, full.split("/")[1])], args[-1]],
                           check=True, capture_output=True)
            return b""
        if "--missing=print" in args:   # a clone without file contents lists every file version as missing
            listing = subprocess.run(["git", "-C", args[2], "cat-file", "--batch-all-objects",
                                      "--batch-check=%(objecttype) %(objectname)"], capture_output=True, text=True)
            return "".join("?%s\n" % l.split()[1] for l in listing.stdout.splitlines() if l.startswith("blob ")).encode()
        return real_run(args, cwd=cwd, env=env, timeout=timeout)
    return fake_run


def main_case(fail=(), repos=None, env=None, clock=None, cost=0, limit=None, cut_at_end=False):
    """Runs main() on the account; returns its exit code, the data file (None when none was written) and the log."""
    repos = repos or REPOS
    m = load()
    m.run = emulate(m, set(fail), repos, clock, cost)
    if clock is not None:
        m.time = clock
    if cut_at_end:   # the run's deadline is reached just as the last repository has been read
        real_head, count = m.read_head_code, []

        def head(repo_dir):
            result = real_head(repo_dir)
            count.append(1)
            if len(count) == len(repos):
                m.DEADLINE = time.monotonic() + cp.RESERVE
            return result
        m.read_head_code = head
    folder = tempfile.mkdtemp(prefix="main-", dir=ROOT)
    m.WORK, m.OUT_DIR, m.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    m.owner_login = lambda: OWNER
    m.profile_offset = lambda owner: None
    m.profile_location = lambda owner: ""
    m.list_repositories = lambda owner: [dict(r) for r in repos]
    saved = dict(os.environ)
    os.environ.update(env or {})
    if limit:
        os.environ["CARDS_TIME_LIMIT"] = str(limit)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = m.main()
    except Exception as e:
        code = "raised %s: %s" % (type(e).__name__, e)
    finally:
        os.environ.clear()
        os.environ.update(saved)
    path = os.path.join(folder, "assets", "coderprint.json")
    data = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return code, data, buf.getvalue(), m


def card(data):
    if not data:
        return None
    return (data["quantity"]["written_loc"]["value"], data["activity"]["commits"]["value"], data["scope"]["visibility"],
            data["scope"]["repositories"].get("unread"), data["scope"]["repositories"].get("left_out_as_unattributable"))


code, data, log, _ = main_case()
check("identity-F1", "every lookup answers: the true card, 15 written, 2 commits, public only",
      (code, card(data)) == (0, (15, 2, "public only", 0, 0)), (code, card(data), log[-400:]))
check("gaps-a9-f07", "the data file says how many addresses were not asked about, and points to what that means",
      data is not None and data["scope"].get("unverified_authors", {}).get("addresses") == 0
      and "unverified_author" in data["definitions"], data and data["scope"])
for label, fail, what in [("owner_identity's query fails", ["identity"], "whose each commit's address is"),
                          ("resolve_authors' query fails", ["resolve"], "whose each commit's address is"),
                          ("resolve_authors gets data null", ["null"], "whose each commit's address is"),
                          ("the templates query fails", ["templates"], "which of the repositories were made")]:
    code, data, log, _ = main_case(fail)
    check("identity-F1", "%s: the existing panels are kept, and the log says why" % label,
          code == 1 and data is None and what in log and "::warning::" in log, (code, card(data), log[-300:]))
code, data, log, _ = main_case(["identity once"])
check("M25", "an identity lookup that fails once is asked again, and the card is drawn: 15 written",
      (code, card(data)) == (0, (15, 2, "public only", 0, 0)), (code, card(data), log[-300:]))
code, data, log, _ = main_case(["hidden"])
check("identity-F1", "a template the token cannot see: its repository is left out and counted, the rest drawn, 10 "
      "written", (code, card(data)) == (0, (10, 1, "public only", 0, 1)) and "may hold files from a template" in log,
      (code, card(data), log[-300:]))
code, data, log, _ = main_case(["someone/tmpl"])
check("identity-F1", "the template's clone fails: its repository is left out and counted, the rest drawn, 10 written",
      (code, card(data)) == (0, (10, 1, "public only", 0, 1)), (code, card(data), log[-300:]))
code, data, log, _ = main_case(["WikdSolvemProbler/coderprint"])
check("M12", "coderprint's own clone fails beside a relay copy: the relay copy is left out, loudly, and nothing of it "
      "counts: 15 written, public only", (code, card(data)) == (0, (15, 2, "public only", 0, 1))
      and "relay copy" in log, (code, card(data), log[-300:]))
code, data, log, _ = main_case(["WikdSolvemProbler/coderprint"], repos=REPOS[:2])
check("M12", "coderprint's own clone fails with no relay copy: nothing to leave out, 15 written",
      (code, card(data)) == (0, (15, 2, "public only", 0, 0)), (code, card(data), log[-300:]))
code, data, log, _ = main_case(["someone/tmpl", "WikdSolvemProbler/coderprint"])
check("identity-F1", "two of three repositories that cannot be told apart is too many: the panels are kept",
      code == 1 and data is None and "too many" in log, (code, card(data), log[-300:]))
code, data, log, _ = main_case(cut_at_end=True)
check("ops-F2", "the deadline reached as reading ends leaves no time to ask whose each address is: the panels are "
      "kept, not drawn with others' work", code == 1 and data is None and "whose each commit's address is" in log,
      (code, card(data), log[-300:]))
four = REPOS + [{"name": "extra", "isPrivate": False}]
code, data, log, m = main_case(repos=four, clock=Clock(), cost=100, limit=5000)
check("identity-U6", "ample time: all four read, 18 written", (code, card(data)) == (0, (18, 3, "public only", 0, 0)),
      (code, card(data), log[-300:]))
code, data, log, m = main_case(repos=four, clock=Clock(), cost=100, limit=500)
check("identity-U6", "time runs out in the last repository: it is left out, whose each address is still asked, and "
      "the card is drawn true: 15 written, 1 unread", (code, card(data)) == (0, (15, 2, "public only", 1, 0)),
      (code, card(data), log[-300:]))
check("identity-U6", "and the reserve kept back while reading is given back", m.RESERVE == cp.RESERVE, m.RESERVE)
code, data, log, _ = main_case(env={"CARDS_AUTHOR_EMAILS": "Col Laborator <col@collab.example>"})
check("M26", "an author-emails address that belongs to another account is not counted, and the log says how many, "
      "never which", (code, card(data)) == (0, (15, 2, "public only", 0, 0))
      and "1 address in author-emails belongs to another GitHub account" in log and "collab.example" not in log,
      (code, card(data), log[-300:]))

shutil.rmtree(ROOT, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d" % (results.count(True), results.count(False)))
sys.exit(1 if not all(results) else 0)
