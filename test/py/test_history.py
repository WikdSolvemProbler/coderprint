"""Regression checks for how coderprint reads history and git: one check or more for each finding of the history area
(history-F1 to history-F14 and history-U3 to history-U6), gaps-a9-f01, f10, f16, f17, f21 and u03, the vote's M2, M7,
M15 and M19, in_use-IU-04, IU-05, IU-08, IU-09 and IU-12, and the data file's C4-08 and blind-18.
Usage: python test_history.py path/to/coderprint.py. It builds its repositories in a temporary folder with git's own
plumbing, so any path git can hold can be made on any system, runs collect() or main() with every network lookup
replaced by a fake (the cache checks clone local repositories through url.insteadOf), prints one line per check and
exits non-zero if any check fails."""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter

spec = importlib.util.spec_from_file_location("cp_under_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

ROOT = tempfile.mkdtemp(prefix="history-")
OWNER = "owner1"
NOREPLY = "123+owner1@users.noreply.github.com"
ME = ("Owner One", NOREPLY)
T0 = 1700000000
DAY = 86400
SOURCES, LOGINS = {}, {}
results = []
for name in ("GH_TOKEN", "CLONE_CACHE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_COUNT", "CARDS_AUTHOR_EMAILS"):
    os.environ.pop(name, None)


def check(fid, name, ok, detail=""):
    if callable(ok):   # a check that may raise on an older coderprint.py, which lacks what it calls
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(bool(ok))
    print("%s %s %s%s" % ("PASS" if ok else "FAIL", fid, name, "" if ok else "  [got %r]" % (detail,)))


def git(repo, *args, data=None, when=T0, author=ME):
    env = dict(os.environ, GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=author[0],
               GIT_COMMITTER_EMAIL=author[1], GIT_AUTHOR_DATE="%d +0000" % when, GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo] + list(args), input=data, env=env, capture_output=True)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace")


def new_repo(name, branch="main", where=None):
    """A bare repository, its history made with plumbing."""
    path = os.path.join(where or os.path.join(ROOT, "src"), name + (".git" if where else ""))
    subprocess.run(["git", "init", "-q", "--bare", "-b", branch, path], check=True, capture_output=True)
    SOURCES[name] = path
    return path


def tree(repo, files):
    """files: {path: text or bytes, or (mode, text)}; nested folders made with mktree -z, blobs hashed in one call."""
    top, datas = {}, []
    for path, v in files.items():
        node = top
        for part in path.split("/")[:-1]:
            node = node.setdefault(part, {})
        mode, data = v if isinstance(v, tuple) else ("100644", v)
        node[path.split("/")[-1]] = (mode, len(datas))
        datas.append(data.encode("utf-8") if isinstance(data, str) else data)
    folder = tempfile.mkdtemp(prefix="blobs-", dir=ROOT)
    names = []
    for k, data in enumerate(datas):
        names.append(os.path.join(folder, str(k)))
        with open(names[-1], "wb") as f:
            f.write(data)
    shas = git(repo, "hash-object", "-w", "--no-filters", "--stdin-paths",
               data=("\n".join(names) + "\n").encode()).split()
    shutil.rmtree(folder, ignore_errors=True)

    def build(node):
        feed = b""
        for name, v in sorted(node.items()):
            if isinstance(v, dict):
                feed += b"040000 tree " + build(v).encode() + b"\t" + name.encode("utf-8") + b"\x00"
            else:
                feed += ("%s blob %s\t" % (v[0], shas[v[1]])).encode() + name.encode("utf-8") + b"\x00"
        return git(repo, "mktree", "-z", "--missing", data=feed).strip()
    return build(top)


def commit(repo, files, parents=(), msg="c", when=T0, author=ME, ref="refs/heads/main"):
    args = ["commit-tree", tree(repo, files), "-m", msg]
    for p in parents:
        args += ["-p", p]
    sha = git(repo, *args, when=when, author=author).strip()
    if ref:
        git(repo, "update-ref", ref, sha)
    return sha


def history(name, steps, branch="main"):
    """A repository of one branch: steps is [{path: data}], one commit a day, each the whole tree."""
    repo, parents, shas = new_repo(name, branch), [], []
    for k, files in enumerate(steps):
        shas.append(commit(repo, files, parents, "c%d" % k, T0 + k * DAY, ref="refs/heads/" + branch))
        parents = [shas[-1]]
    return repo, shas


def fake_clone(owner, name, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(dest, ignore_errors=True)
    subprocess.run(["git", "clone", "-q", "--bare", SOURCES[name], dest], check=True, capture_output=True)


def writable(func, path, _):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except OSError:
        pass


REAL_CLONE = cp.clone
cp.clone = fake_clone
cp.resolve_authors = lambda owner, samples: {e: LOGINS.get(e) for e in samples}
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
cp.templates = lambda owner: {}
cp.seed_blobs = lambda full_name, dest: None


def run(names, since=None):
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    try:
        return cp.collect(OWNER, [{"name": n, "isPrivate": True} for n in names], work, since)
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e), "events": [], "commits": [], "code": {}, "imports": [],
                "left_out": {}, "import_lines": []}


def lines(d):
    return sum(n for _, _, n in d["events"])


def use(d):
    return d["code"].get("production"), d["code"].get("tests")


def summary(d):
    return (lines(d), use(d), len(d["commits"]), d["left_out"], len(d["imports"]), d.get("error"))


def body(n, tag, indent=""):
    return "".join("%sline_%s_%d = %d\n" % (indent, tag, i, i) for i in range(n))


def module(k, n):
    return "".join("item_%s_%d = compute(%d)\n" % (k, i, i) for i in range(n))


def one(name, files, **kw):
    return history(name, [files], **kw)


# ---------------------------------------------------------------- history-F1, gaps-a9-f10: paths as git quotes them
ODD = {"space": "src/my file.py", "space_dir": "My Project/main.py", "quote": 'src/say "hi".py',
       "backslash": "src/back\\slash.py", "tab": "src/tab\there.py", "newline": "src/new\nline.py",
       "ctrl": "src/bell\x07.py", "quote_space": 'src/say "hi" now.py', "accent_space": "src/café menu.py",
       "unity": "Unity Project/Assets/Player Controller.cs"}
for tag, path in ODD.items():
    one("p_" + tag, {path: body(10, tag)})
    d = run(["p_" + tag])
    check("history-F1", "a path %r counts 10 written, 10 in use" % path, (lines(d), use(d)) == (10, (10, 0)),
          summary(d))
history("p_ren", [{"old dir/a b.py": body(20, "ren")}, {"new dir/a b.py": body(20, "ren") + "more = 1\n"}])
d = run(["p_ren"])
check("history-F1", "a spaced path renamed and edited: 21 written, 21 in use", (lines(d), use(d)) == (21, (21, 0)),
      summary(d))
one("p_bin", {"tools/bin and x.ps1": "﻿x = 1\ny = 2\n".encode("utf-16-le")})
d = run(["p_bin"])
check("gaps-a9-f10", "a UTF-16 file (binary to git) named with ' and ' counts: 2 written, 2 in use",
      (lines(d), use(d)) == (2, (2, 0)), summary(d))
check("gaps-a9-f10", "git's quoting undone exactly: C escapes, octal bytes, and a name git would not quote kept",
      lambda: (cp.git_path('"say \\"hi\\".py"'), cp.git_path('"caf\\303\\251\\tx.py"'), cp.git_path("plain.py"))
      == ('say "hi".py', "café\tx.py", "plain.py"))
check("gaps-a9-f10", "a diff label: the tab after a spaced name dropped, the prefix taken off",
      lambda: (cp.diff_path("b/my file.py\t", "b/"), cp.diff_path('"b/say \\"hi\\" now.py"\t', "b/"),
               cp.diff_path("/dev/null", "a/")) == ("my file.py", 'say "hi" now.py', None))
check("gaps-a9-f10", "a diff --git line split exactly, and an ambiguous rename left to its rename lines",
      lambda: (cp.header_paths("a/my file.py b/my file.py"), cp.header_paths("a/x y.py b/z w.py"),
               cp.header_paths('"a/t\\tb.py" "b/t\\tb.py"')) == (("my file.py", "my file.py"), (None, None),
                                                                  ("t\tb.py", "t\tb.py")))

# ---------------------------------------------------------------- gaps-a9-f01: U+2028, U+2029, U+0085 in a path
for sep in (" ", " ", "\u0085"):
    for colon in (True, False):
        name = "sep%x%s" % (ord(sep), "c" if colon else "n")
        path = "a%s%sb.py" % (sep, ":" if colon else "")
        repo, _ = one(name, {path: "print(1)\nprint(2)\n", "ok.py": "x = 1\n"})
        try:
            commits, bad = cp.read_commits(repo, 0)
            paths = [f.path for c in commits for f in c.files]
            got = (len(commits), bad, path in paths, cp.language_of(path))
        except Exception as e:
            got = "%s: %s" % (type(e).__name__, e)
        check("gaps-a9-f01", "read_commits keeps a path holding U+%04X %s a colon whole" % (ord(sep), "and" if colon
                                                                                           else "without"),
              got == (1, 0, True, "Python"), got)
        d = run([name])
        check("gaps-a9-f01", "collect counts it: 3 written, 3 in use (U+%04X, %s colon)" % (ord(sep), "a" if colon
                                                                                              else "no"),
              (lines(d), use(d)) == (3, (3, 0)), summary(d))
one("inline", {"s.js": 'const a = "x y";\nconst b = 2;\nconst c = "p\x0cq";\n'})
d = run(["inline"])
check("gaps-a9-f01", "lines holding U+2028 and a form feed: 3 written, 3 in use", (lines(d), use(d)) == (3, (3, 0)),
      summary(d))

# ---------------------------------------------------------------- gaps-a9-f21: a name holding 0x1F
repo = new_repo("sep1f")
c1 = commit(repo, {"a.py": body(2, "own")}, (), "mine", T0)
commit(repo, {"a.py": body(2, "own"), "b.py": body(3, "eve")}, [c1], "hers", T0 + 60,
       author=("Eve\x1f" + NOREPLY, "eve@example.org"))
LOGINS["eve@example.org"] = "eve"
commits, _ = cp.read_commits(repo, 0)
d = run(["sep1f"])
check("gaps-a9-f21", "a name holding 0x1F shifts no field: Eve's address read as hers, her commit left out",
      sorted(c.email for c in commits) == [NOREPLY, "eve@example.org"] and lines(d) == 2
      and d["left_out"] == {"others": 1}, (sorted(c.email for c in commits), summary(d)))

# ---------------------------------------------------------------- history-F2: the machine's git configuration
repo = new_repo("cfg")
c1 = commit(repo, {"a.py": body(10, "cfa"), "b.py": body(5, "cfb")}, (), "root", T0)
commit(repo, {"a.py": body(10, "cfa") + "x = 1\n", "b.py": body(5, "cfb")}, [c1], "e", T0 + 60)
repo = new_repo("hunks")
c1 = commit(repo, {"h.py": body(10, "hk")}, (), "root", T0)
lines_h = body(10, "hk").splitlines(True)
lines_h[2], lines_h[5] = "changed_two = 2\n", "changed_five = 5\n"
commit(repo, {"h.py": "".join(lines_h)}, [c1], "two hunks", T0 + 60)
attrs = os.path.join(ROOT, "attrs")
with open(attrs, "w") as f:
    f.write("*.py -diff\n")
mailmap = os.path.join(ROOT, "mailmap")
with open(mailmap, "w") as f:
    f.write("Stranger <stranger@example.org> <%s>\n" % NOREPLY)
LOGINS["stranger@example.org"] = "stranger"
CONFIGS = {"log.showRoot=false": "[log]\n\tshowRoot = false\n",
           "core.attributesFile marking *.py -diff": "[core]\n\tattributesFile = %s\n" % attrs.replace("\\", "/"),
           "core.bigFileThreshold=100": "[core]\n\tbigFileThreshold = 100\n",
           "diff.noprefix=true": "[diff]\n\tnoprefix = true\n",
           "diff.mnemonicPrefix=true": "[diff]\n\tmnemonicPrefix = true\n",
           "diff.interHunkContext=10": "[diff]\n\tinterHunkContext = 10\n",
           "a global mailmap naming a stranger": "[mailmap]\n\tfile = %s\n" % mailmap.replace("\\", "/"),
           "log.showSignature=true": "[log]\n\tshowSignature = true\n"}
cfg = os.path.join(ROOT, "gitconfig")
for label, text in CONFIGS.items():
    with open(cfg, "w") as f:
        f.write(text)
    os.environ["GIT_CONFIG_GLOBAL"] = cfg
    d, h = run(["cfg"]), run(["hunks"])
    del os.environ["GIT_CONFIG_GLOBAL"]
    check("history-F2", "under %s: 16 written and in use, and two hunks 12 written, 10 in use" % label,
          (lines(d), use(d), lines(h), use(h)) == (16, (16, 0), 12, (10, 0)), (summary(d), summary(h)))
with open(cfg, "w") as f:
    f.write("[safe]\n\tdirectory = *\n")
os.environ.update(GIT_CONFIG_GLOBAL=cfg, GIT_TEST_ASSUME_DIFFERENT_OWNER="1")
d = run(["cfg"])
del os.environ["GIT_CONFIG_GLOBAL"], os.environ["GIT_TEST_ASSUME_DIFFERENT_OWNER"]
check("history-F2", "the machine's safe.directory still applies (a clone git takes to be another account's)",
      (lines(d), use(d), d["code"].get("unread")) == (16, (16, 0), 0), summary(d))
os.environ["GIT_DIFF_OPTS"] = "--unified=3"
d = run(["hunks"])
del os.environ["GIT_DIFF_OPTS"]
check("history-F2", "GIT_DIFF_OPTS changes nothing: 12 written, 10 in use", (lines(d), use(d)) == (12, (10, 0)),
      summary(d))

# ---------------------------------------------------------------- history-F3: one content under dist/ and src/
one("distsrc", {"dist/index.js": body(25, "ds"), "src/index.js": body(25, "ds")})
d = run(["distsrc"])
check("history-F3", "dist/ beside src/ in one commit: 25 written, 25 in use", (lines(d), use(d)) == (25, (25, 0)),
      summary(d))
one("notes", {"a_notes.txt": body(9, "nt"), "b_tool.py": body(9, "nt")})
d = run(["notes"])
check("history-F3", "a .txt twin sorting first: 9 written", lines(d) == 9, summary(d))

# ---------------------------------------------------------------- history-F4, M7: empty, unborn, tags only
new_repo("empty")
d = run(["empty"])
check("history-F4", "an empty repository is read, not counted without diffs or without a head",
      (d.get("error"), d["code"].get("unread"), d["code"].get("heads_unread"), lines(d)) == (None, 0, 0, 0),
      summary(d))
check("M7", "an empty repository adds nothing and no repository unread", d.get("unread") == 0, d.get("unread"))
repo, _ = one("unborn", {"a.py": body(10, "ub") + "# a comment\n\n"}, branch="dev")
git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
d = run(["unborn"])
check("history-F4", "a HEAD naming no branch: its diffs still read, 10 written not 12, nothing at its head",
      (lines(d), use(d), d["code"].get("unread"), d["code"].get("heads_unread")) == (10, (0, 0), 0, 0), summary(d))
repo, (c,) = one("tagsonly", {"a.py": body(10, "to")})
git(repo, "tag", "v1", c)
git(repo, "update-ref", "-d", "refs/heads/main")
d = run(["tagsonly"])
check("history-F4", "tags only: read, nothing counted, not counted without diffs",
      (d.get("error"), d["code"].get("unread"), d.get("unread")) == (None, 0, 0), summary(d))
bare = os.path.join(ROOT, "late.git")
subprocess.run(["git", "clone", "-q", "--bare", SOURCES["p_space"], bare], check=True, capture_output=True)
cp.DEADLINE = time.monotonic() + cp.RESERVE + 2   # so near that nothing may start
try:
    cp.read_head_code(bare)
    got = "read"
except RuntimeError as e:
    got = str(e)
cp.DEADLINE = None
check("history-F4", "a head not read for want of time is unknown, not empty: read_head_code raises",
      "out of time" in got, got)

# ---------------------------------------------------------------- history-F5: a cached clone follows its origin
srv = os.path.join(ROOT, "srv")
os.makedirs(srv)
saved = dict(os.environ)
os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="url.file:///%s/.insteadOf" % srv.replace("\\", "/"),
                  GIT_CONFIG_VALUE_0="https://github.com/%s/" % OWNER, CLONE_CACHE="1")
cp.clone = REAL_CLONE
cache = os.path.join(ROOT, "cache")
os.makedirs(cache)


def cached(name):
    return cp.collect(OWNER, [{"name": name, "isPrivate": True}], cache)


try:
    r = new_repo("renamed", where=srv)
    commit(r, {"a.py": body(10, "rn") + "# c\n\n"}, (), "c", T0)
    cached("renamed")
    git(r, "branch", "-m", "main", "trunk")
    d = cached("renamed")
    check("history-F5", "a cache after the default branch is renamed: 10 written, 10 in use",
          (lines(d), use(d), d["code"].get("unread")) == (10, (10, 0), 0), summary(d))
    r = new_repo("switched", where=srv)
    c = commit(r, {"a.py": body(10, "sw")}, (), "c", T0)
    cached("switched")
    commit(r, {"a.py": body(10, "sw"), "b.py": body(20, "sw2")}, [c], "c2", T0 + 60, ref="refs/heads/next")
    git(r, "symbolic-ref", "HEAD", "refs/heads/next")
    d = cached("switched")
    check("history-F5", "a cache after the default switches branch: 30 in use", use(d) == (30, 0), summary(d))
    r = new_repo("forced", where=srv)
    c = commit(r, {"a.py": body(10, "fo")}, (), "c", T0)
    bad = commit(r, {"a.py": body(10, "fo"), "s.py": body(50, "oops")}, [c], "x", T0 + 60)
    git(r, "tag", "v1", bad)
    cached("forced")
    git(r, "update-ref", "refs/heads/main", c)
    git(r, "tag", "-d", "v1")
    d = cached("forced")
    check("history-F5", "a cache after a force-push and a deleted tag: 10 written, 1 commit",
          (lines(d), len(d["commits"])) == (10, 1), summary(d))
finally:
    os.environ.clear()
    os.environ.update(saved)
    cp.clone = fake_clone

# ---------------------------------------------------------------- history-F6: gh-pages reached through a tag
repo, (c,) = one("pagestag", {"app.py": body(5, "ptm")})
g = commit(repo, {"site.js": body(40, "ptg")}, (), "site", T0 + 60, ref="refs/heads/gh-pages")
git(repo, "tag", "deploy-1", g)
d = run(["pagestag"])
check("history-F6", "a tag on gh-pages, not the default: 5 written, 1 commit", (lines(d), len(d["commits"])) == (5, 1),
      summary(d))
repo, (c,) = one("pagesdef", {"site.js": body(10, "gpd")}, branch="gh-pages")
commit(repo, {"app.py": body(7, "gpm")}, (), "m", T0 + 60)
git(repo, "tag", "v1", c)
d = run(["pagesdef"])
check("history-F6", "gh-pages as the default is still read: 17 written, 10 in use",
      (lines(d), use(d)) == (17, (10, 0)), summary(d))
repo, (base,) = one("pagesfork", {"app.py": body(6, "pf")})
site = commit(repo, {"app.py": body(6, "pf"), "docs.js": body(8, "pfd")}, [base], "s", T0 + 60,
              ref="refs/heads/gh-pages")
git(repo, "tag", "site-1", site)
d = run(["pagesfork"])
check("history-F6", "gh-pages branched from main and tagged: main's 6 lines kept, the site's 8 not",
      (lines(d), len(d["commits"])) == (6, 1), summary(d))
repo, (base,) = one("release", {"app.py": body(5, "rl")})
rel = commit(repo, {"app.py": body(5, "rl"), "fix.py": body(3, "rlf")}, [base], "r", T0 + 60, ref=None)
git(repo, "tag", "v2", rel)
d = run(["release"])
check("history-F6", "a release tag on a commit no branch holds is still read: 8 written, 2 commits",
      (lines(d), len(d["commits"])) == (8, 2), summary(d))

# ---------------------------------------------------------------- history-F7, IU-08: symbolic links
one("symlink", {"a.py": body(10, "sl"), "link.py": ("120000", "import_this_module_now"),
                "run.sh": ("120000", "../tools/run.sh")})
d = run(["symlink"])
check("history-F7", "symbolic links add no line: 10 written, 10 in use", (lines(d), use(d)) == (10, (10, 0)),
      summary(d))
history("linkfile", [{"a.py": body(10, "lf"), "l.py": ("120000", "target_name_here")},
                     {"a.py": body(10, "lf"), "l.py": body(4, "lfr")}])
d = run(["linkfile"])
check("in_use-IU-08", "a link turned into a real file counts the file: 14 written, 14 in use",
      (lines(d), use(d)) == (14, (14, 0)), summary(d))

# ---------------------------------------------------------------- history-F8: Git LFS pointers
PTR = "version https://git-lfs.github.com/spec/v1\noid sha256:%s\nsize %d\n"
LFS = "*.js filter=lfs diff=lfs merge=lfs -text\n"
history("lfs", [{"a.py": body(10, "lf8"), "big.js": PTR % ("a" * 64, 123456), "gen.c": PTR % ("b" * 64, 99),
                 ".gitattributes": LFS},
                {"a.py": body(10, "lf8"), "big.js": PTR % ("c" * 64, 654321), "gen.c": PTR % ("b" * 64, 99),
                 ".gitattributes": LFS}])
d = run(["lfs"])
check("history-F8", "Git LFS pointers add no line, new or updated: 10 written, 10 in use",
      (lines(d), use(d)) == (10, (10, 0)), summary(d))
one("sizeline", {"a.tcl": "proc size {n} {return $n}\nsize 12\n"})
d = run(["sizeline"])
check("history-F8", "a real line 'size 12' outside a pointer still counts: 2 written", lines(d) == 2, summary(d))
history("intolfs", [{"big.js": body(6, "il")}, {"big.js": PTR % ("d" * 64, 4242), ".gitattributes": LFS}])
d = run(["intolfs"])
check("history-F8", "a file moved into LFS: its 6 lines written, none in use", (lines(d), use(d)) == (6, (0, 0)),
      summary(d))
check("history-F8", "a pointer is known by git-lfs's own rules",
      lambda: (cp.lfs_pointer((PTR % ("e" * 64, 1)).encode().split(b"\n")[:-1]),
               cp.lfs_pointer(b"version 2\nsize 12\n".split(b"\n")[:-1])) == (True, False))

# ---------------------------------------------------------------- history-F9, IU-05: the head splits lines as git does
for tag, (path, data) in {"u2028": ("a.js", 'const s = "a b";\nlet t = 1;\n'.encode()),
                          "vt": ("a.c", b"int a = 1;\x0bint b = 2;\nint c = 3;\n"),
                          "ff": ("a.py", b"x = 1\x0cy = 2\nz = 3\n"),
                          "nel": ("a.py", "x = 'a\u0085b'\nz = 3\n".encode()),
                          "cr": ("a.py", b"x = 1\ry = 2\rz = 3\r"),
                          "crlf": ("a.py", b"import os\r\nx = 1\r\n# c\r\n\r\ny = 2\r\n")}.items():
    repo, _ = one("agree_" + tag, {path: data})
    plus, head = Counter(), Counter()
    for key, v in cp.read_added_code(repo).items():
        if isinstance(key, tuple) and isinstance(v, tuple):
            plus.update(v[0])
    for (h, t), n in cp.read_head_code(repo).items():
        head[h] += n
    check("history-F9", "%s: the diff's lines of code and the head's are the same" % tag, plus == head and plus,
          (sum(plus.values()), sum(head.values())))
    if tag == "ff":
        d = run(["agree_ff"])
        check("in_use-IU-05", "a line holding a form feed is in use as written: 2 and 2",
              (lines(d), use(d)) == (2, (2, 0)), summary(d))

# ---------------------------------------------------------------- history-F10: landed twice, or two changes
names = []
for k in range(3):
    repo = new_repo("bulk%d" % k)
    c1 = commit(repo, {"a.py": body(10, "b%d" % k)}, (), "start", T0 + k * 1000)
    commit(repo, {"a.py": body(10, "b%d" % k) + "VERSION_%d = '2.0'\nNEW_%d = 1\n" % (k, k)}, [c1], "Bump version",
           T0 + DAY)
    names.append("bulk%d" % k)
d = run(names)
check("history-F10", "one message committed in 3 repositories in one second: 36 written, 36 in use, 6 commits",
      (lines(d), use(d), len(d["commits"])) == (36, (36, 0), 6), summary(d))
repo = new_repo("burst")
c1 = commit(repo, {"a.py": body(5, "u1")}, (), "update", T0)
commit(repo, {"a.py": body(5, "u1"), "b.py": body(7, "u2")}, [c1], "update", T0)
d = run(["burst"])
check("history-F10", "parent and child in one second under one subject: 12 written, 2 commits",
      (lines(d), len(d["commits"])) == (12, 2), summary(d))
repo = new_repo("amend")
base = commit(repo, {"a.py": body(3, "am0")}, (), "base", T0)
x = commit(repo, {"a.py": body(3, "am0"), "f.py": body(20, "am")}, [base], "feature", T0 + 60, ref=None)
x2 = commit(repo, {"a.py": body(3, "am0"), "f.py": body(20, "am").replace("line_am_7 = 7", "line_am_7 = 70")},
            [base], "feature", T0 + 60)
git(repo, "tag", "v1", x)
d = run(["amend"])
check("history-F10", "an amend that changed a line, reachable from a tag, counts once: 2 commits, 24 written (the "
      "rewritten line counts again, as in_use-IU-06 says)",
      (len(d["commits"]), lines(d), d["left_out"].get("landed_twice")) == (2, 24, 1), summary(d))
a = new_repo("pick-a")
a1 = commit(a, {"f.py": body(20, "pk")}, (), "base", T0)
commit(a, {"f.py": body(20, "pk") + "fix = 1\n"}, [a1], "the fix", T0 + 500)
b = new_repo("pick-b")
b1 = commit(b, {"g.py": body(20, "pk") + "other = 2\n"}, (), "release", T0 + 100)
commit(b, {"g.py": body(20, "pk") + "other = 2\nfix = 1\n"}, [b1], "the fix", T0 + 500)
d = run(["pick-a", "pick-b"])
check("history-F10", "a cherry-pick into a second repository still counts once: 3 commits, 1 landed twice",
      (len(d["commits"]), d["left_out"].get("landed_twice")) == (3, 1), summary(d))
for first in ("docs", "code"):
    repo = new_repo("docfirst_" + first)
    c0 = commit(repo, {"base.py": body(3, "dc0" + first)}, (), "base", T0)
    docs = {"README.md": "# words\n\nmore words\n"}
    code = {"a.py": body(7, "dc" + first)}
    steps = [docs, code] if first == "docs" else [code, docs]
    tree_now, parent = {"base.py": body(3, "dc0" + first)}, c0
    for files in steps:
        tree_now.update(files)
        parent = commit(repo, dict(tree_now), [parent], "update", T0 + 60)
    d = run(["docfirst_" + first])
    check("history-F10", "a docs-only commit and a code commit in one second under one subject, %s first: 10 written, "
          "3 commits" % first, (lines(d), len(d["commits"]), d["left_out"]) == (10, 3, {}), summary(d))

# ---------------------------------------------------------------- history-F11: the retry without rename detection
repo = new_repo("bigmove")
a = {"old/m%03d.py" % k: body(5, "m%d" % k) for k in range(300)}
b = dict(a, **{"old2/n%03d.py" % k: body(5, "n%d" % k) for k in range(300)})
c1 = commit(repo, a, (), "first half", T0)
c2 = commit(repo, b, [c1], "second half", T0 + 2 * DAY)
moved = {p.replace("old2/", "new/").replace("old/", "new/"): t + "e1 = 1\ne2 = 2\ne3 = 3\n" for p, t in b.items()}
commit(repo, moved, [c2], "move and edit", T0 + 4 * DAY)
real_run, state = cp.run, {"done": False}


def timing_out(args, cwd=None, env=None, timeout=cp.TIMEOUT):
    if not state["done"] and "log" in args and "-M" in args and "--raw" in args:
        state["done"] = True
        raise RuntimeError("git timed out after 900 seconds")
    return real_run(args, cwd=cwd, env=env, timeout=timeout)


cp.run = timing_out
d = run(["bigmove"])
cp.run = real_run
check("history-F11", "retried without renames: a move of 600 edited files is no import, 4800 written, 4800 in use",
      (lines(d), use(d), len(d["imports"]), state["done"]) == (4800, (4800, 0), 0, True), summary(d))
history("realimport", [{"old/x.py": body(3, "ri")},
                       dict({"lib/q%03d.py" % k: body(2, "q%d" % k) for k in range(501)},
                            **{"old/x.py": body(3, "ri")})])
d = run(["realimport"])
check("history-F11", "a real import of 501 new files is still one", (len(d["imports"]), lines(d)) == (1, 3), summary(d))

# ---------------------------------------------------------------- history-F12: a hunk inside a docstring or comment
history("docstring", [{"a.py": 'def f():\n    """Doc.\n    """\n    return 1\n'},
                      {"a.py": 'def f():\n    """Doc.\n\n    More prose, and still more.\n    """\n    return 1\n'}])
d = run(["docstring"])
check("history-F12", "two prose lines added inside a docstring add no line of code: 2 written, 2 in use",
      (lines(d), use(d)) == (2, (2, 0)), summary(d))
history("license", [{"a.c": "/*\n * License\n */\nint x = 1;\n"},
                    {"a.c": "/*\n * License\n * and its second line\n */\nint x = 1;\nint y = 2;\n"}])
d = run(["license"])
check("history-F12", "a block comment grown by a line and one new line of code: 2 written", lines(d) == 2, summary(d))

# ---------------------------------------------------------------- history-F13: a byte order mark
one("bom", {"a.py": "﻿# header comment\nx = 1\n", "b.cs": "﻿// a header comment\nusing System;\n",
            "c.py": "﻿\ny = 2\n", "d.cs": "﻿/*\n * License\n */\nclass D {}\n"})
d = run(["bom"])
check("history-F13", "a BOM before a comment, a block comment or a blank line is no code: 4 written, 4 in use",
      (lines(d), use(d)) == (4, (4, 0)), summary(d))
one("bomcode", {"a.cs": "﻿using System;\nclass A {}\n"})
d = run(["bomcode"])
check("history-F13", "a BOM before code keeps it code: 2 written, 2 in use", (lines(d), use(d)) == (2, (2, 0)),
      summary(d))

# ---------------------------------------------------------------- history-F14: a line added to each of many files
files = {"m%02d.py" % k: body(10, "ao%d" % k) for k in range(12)}
history("addone", [files, {p: t + "from typing import Any\n" for p, t in files.items()}])
d = run(["addone"])
check("history-F14", "one new line in each of 12 files is written, not a sweep: 132 written", lines(d) == 132,
      summary(d))
history("reindent", [files, {p: "".join("    " + l for l in t.splitlines(True)) for p, t in files.items()}])
d = run(["reindent"])
check("history-F14", "a re-indent of 12 files is still a sweep: 120 written", lines(d) == 120, summary(d))
twenty = {"f%02d.py" % k: body(10, "fs%d" % k) for k in range(20)}
formatted = {p: ("".join("    " + l for l in t.splitlines(True)) if k < 17 else t + "\n")
             for k, (p, t) in enumerate(sorted(twenty.items()))}
history("formatter", [twenty, formatted])
d = run(["formatter"])
check("history-F14", "a formatter sweep of 20 files, 3 of which only gained a blank line, stays a sweep: 200 written",
      (lines(d), use(d)) == (200, (200, 0)), summary(d))

# ---------------------------------------------------------------- gaps-a9-f16, M15: a rewrite is not a reformat


def old_code(k, n=100):
    return "".join("value_%d_%d = compute(%d, %d)\n" % (k, i, i, k) for i in range(n))


def new_code(k, n=100):
    return "".join("def handler_%d_%d(request): return render(request, 'page%d.html', {'n': %d})\n" % (k, i, i, k)
                   for i in range(n))


history("rewrite", [{"m%d.py" % k: old_code(k) for k in range(12)}, {"m%d.py" % k: new_code(k) for k in range(12)}])
d = run(["rewrite"])
check("gaps-a9-f16", "12 files rewritten at the same length: 2,400 written, 1,200 in use",
      (lines(d), use(d)) == (2400, (1200, 0)), summary(d))
check("M15", "a genuine balanced rewrite of ten or more files is written again", lines(d) == 2400, summary(d))
migrated = {}
for k in range(40):
    text = old_code(k, 20).splitlines(True)
    text[5:8] = ["client_%d = HttpClient(timeout=%d)\n" % (k, j) for j in range(3)]
    migrated["s%d.py" % k] = "".join(text)
history("migrate", [{"s%d.py" % k: old_code(k, 20) for k in range(40)}, migrated])
d = run(["migrate"])
check("gaps-a9-f16", "40 files with 3 lines replaced in each: 920 written", lines(d) == 920, summary(d))
history("indent", [{"m%d.py" % k: old_code(k) for k in range(12)},
                   {"m%d.py" % k: "".join("    " + l for l in old_code(k).splitlines(True)) for k in range(12)}])
d = run(["indent"])
check("gaps-a9-f16", "control: 12 files re-indented stay a sweep: 1,200 written, 1,200 in use",
      (lines(d), use(d)) == (1200, (1200, 0)), summary(d))
history("renameid", [{"m%d.py" % k: old_code(k) for k in range(12)},
                     {"m%d.py" % k: old_code(k).replace("compute(", "evaluate(") for k in range(12)}])
d = run(["renameid"])
check("gaps-a9-f16", "control: one identifier renamed on every line of 12 files stays a sweep: 1,200 and 1,200",
      (lines(d), use(d)) == (1200, (1200, 0)), summary(d))
imports = {"i%d.py" % k: "".join("import mod_%d_%d\n" % (k, i) for i in range(10)) for k in range(12)}
history("isort", [imports, {p: "".join(sorted(t.splitlines(True), reverse=True)) for p, t in imports.items()}])
d = run(["isort"])
check("gaps-a9-f16", "imports sorted in 12 files, lines moved within each, stay a sweep: 120 written, 120 in use",
      (lines(d), use(d)) == (120, (120, 0)), summary(d))
check("gaps-a9-f16", "sweep() without the diffs still reads the shape alone",
      lambda: len(cp.sweep([cp.Change("%040x" % i, "M", "f%d.py" % i, 100, 100) for i in range(12)])) == 12)

# ---------------------------------------------------------------- gaps-a9-f17: moves git reports as deleted and added
N_MOVE, N_EDIT = 1010, 1005   # past git's rename limit (more than 1,000 by 1,000 pairs): deleted and added
repo = new_repo("move")
tree_now, parent = {}, []
for part in range(3):
    for k in range(part * 337, min(N_MOVE, part * 337 + 337)):
        tree_now["a/mod_%d.py" % k] = module(k, 5)
    parent = [commit(repo, dict(tree_now), parent, "add", T0 + part * 2 * DAY)]
moved = {"b/module_%d_v2.py" % k: module(k, 5) + ("edited_%d = True\n" % k if k < N_EDIT else "")
         for k in range(N_MOVE)}
commit(repo, moved, parent, "restructure", T0 + 10 * DAY)
d = run(["move"])
check("gaps-a9-f17", "1,010 files moved to new names, 1,005 edited, past the rename limit: 6,055 written, no import",
      (lines(d), use(d), len(d["imports"])) == (6055, (6055, 0), 0), summary(d))
js = {"src/f%d.js" % k: "".join("function f_%d_%d(a, b) { return a + b + %d; }\n" % (k, i, i) for i in range(60))
      for k in range(15)}
ts = {"src/f%d.ts" % k: "".join(("export function f_%d_%d(a: number, b: number): number { return a + b + %d; }\n"
                                 if i % 2 == 0 else "function f_%d_%d(a, b) { return a + b + %d; }\n") % (k, i, i)
                                for i in range(60)) for k in range(15)}
history("tsconv", [js, ts])
d = run(["tsconv"])
check("gaps-a9-f17", "15 files .js rewritten as .ts, 30 of 60 lines typed: 1,350 written, 900 in use",
      (lines(d), use(d)) == (1350, (900, 0)), summary(d))
old_c = "".join("int f_old_%d(void) {\n    return %d;\n}\n" % (i, i) for i in range(40))
new_c = "".join("int g_new_%d(int a) {\n    return a + %d;\n}\n" % (i, i) for i in range(40))
history("unrelated", [{"old.c": old_c}, {"new.c": new_c}])
d = run(["unrelated"])
check("gaps-a9-f17", "a new file beside an unrelated deletion keeps every line: 240 written, 120 in use",
      (lines(d), use(d)) == (240, (120, 0)), summary(d))

# ---------------------------------------------------------------- gaps-a9-u03: a codebase uploaded in parts
repo, tree_now, parent = new_repo("upload"), {}, []
for part in range(6):
    tree_now.update({"lib/m%d.py" % k: module(k, 10) for k in range(100 * part, 100 * part + 100)})
    parent = [commit(repo, dict(tree_now), parent, "Add files via upload", T0 + 60 * part)]
tree_now["mine.py"] = module("mine", 50)
commit(repo, dict(tree_now), parent, "my first change", T0 + DAY)
d = run(["upload"])
check("gaps-a9-u03", "six uploads of 100 files: 50 written, 50 in use, 6 imports",
      (lines(d), use(d), len(d["imports"])) == (50, (50, 0), 6), summary(d))
repo, tree_now, parent = new_repo("busy"), {}, []
for k in range(50):
    tree_now["src/f%d.py" % k] = module("b%d" % k, 10)
    parent = [commit(repo, dict(tree_now), parent, "work %d" % k, T0 + 600 * k)]
d = run(["busy"])
check("gaps-a9-u03", "control: 50 small commits in a day: 500 written, no import",
      (lines(d), len(d["imports"])) == (500, 0), summary(d))
one("kit", {"app/c%d.ts" % k: module("k%d" % k, 4) for k in range(480)})
d = run(["kit"])
check("gaps-a9-u03", "control: a 480-file starter kit in one commit counts: 1,920 written, no import",
      (lines(d), len(d["imports"])) == (1920, 0), summary(d))
repo, tree_now, parent = new_repo("tsparts"), {}, []
for part in range(6):
    tree_now.update({"src/f%d.js" % k: "".join("function f_%d_%d(a, b) { return a + %d; }\n" % (k, i, i)
                                               for i in range(10)) for k in range(100 * part, 100 * part + 100)})
    parent = [commit(repo, dict(tree_now), parent, "js", T0 + part * 2 * DAY)]
for part in range(6):
    for k in range(100 * part, 100 * part + 100):
        del tree_now["src/f%d.js" % k]
        tree_now["src/f%d.ts" % k] = "".join(("function f_%d_%d(a: number, b: number) { return a + %d; }\n" if i % 2
                                              else "function f_%d_%d(a, b) { return a + %d; }\n") % (k, i, i)
                                             for i in range(10))
    parent = [commit(repo, dict(tree_now), parent, "convert", T0 + 20 * DAY + 60 * part)]
d = run(["tsparts"])
check("gaps-a9-u03", "600 files converted .js to .ts in six commits of 100 are no import: 9,000 written",
      (lines(d), len(d["imports"])) == (9000, 0), summary(d))

# ---------------------------------------------------------------- M2, M19, data-C4-08: the import rule counts code
one("mdmix", dict({"docs/p%d.md" % k: "# page %d\n\nwords\n" % k for k in range(495)},
                  **{"src/t%d.py" % k: body(2, "md%d" % k) for k in range(10)}))
d = run(["mdmix"])
check("M2", "495 Markdown files and 10 of Python are no import: 20 written, 20 in use",
      (lines(d), use(d), len(d["imports"])) == (20, (20, 0), 0), summary(d))
one("mdmix2", dict({"docs/p%d.md" % k: "# page %d\n" % k for k in range(150)},
                   **{"src/u%d.py" % k: body(2, "mu%d" % k) for k in range(400)}))
d = run(["mdmix2"])
check("data-C4-08", "400 Python files and 150 Markdown files are no import: 800 written",
      (lines(d), len(d["imports"])) == (800, 0), summary(d))
check("M19", "prose, data and unknown files never count toward the 500", lines(d) == 800, summary(d))
one("codeimport", {"src/q%d.py" % k: "# a comment\nx_%d = %d\n" % (k, k) for k in range(501)})
d = run(["codeimport"])
check("data-blind-18", "an import records the lines of code it held, not git's lines: 501 of 1,002",
      (len(d["imports"]), [n for _, n in d["import_lines"]], d["code"].get("approximate_imports")) == (1, [501], []),
      (d["import_lines"], d["code"].get("approximate_imports")))
real_added = cp.read_added_code
cp.read_added_code = lambda repo_dir: (_ for _ in ()).throw(RuntimeError("git exited 1"))
d = run(["codeimport"])
cp.read_added_code = real_added
check("data-blind-18", "without diffs, git's count stands and is marked approximate: 1,002 of 1,002",
      ([n for _, n in d["import_lines"]], [n for _, n in d["code"].get("approximate_imports", [])]) == ([1002], [1002]),
      (d["import_lines"], d["code"].get("approximate_imports")))

# ---------------------------------------------------------------- in_use-IU-04: a write and its sweep in one second
wrong = []
for trial in range(12):
    repo = new_repo("order%d" % trial)
    files = {"r%d.py" % k: body(10, "o%d_%d" % (trial, k)) for k in range(12)}
    c1 = commit(repo, files, (), "write", T0)
    c2 = commit(repo, {p: t.replace("line_", "row_") for p, t in files.items()}, [c1], "rename %d" % trial, T0)
    d = run(["order%d" % trial])
    if (lines(d), use(d)) != (120, (120, 0)):
        wrong.append((trial, c2 < c1, summary(d)))
check("in_use-IU-04", "a write and the sweep renaming it in one second, 12 hash orders: 120 written, 120 in use",
      not wrong, wrong)

# ---------------------------------------------------------------- in_use-IU-09, history-U6: a head that cannot be read
one("nohead", {"a.py": body(10, "nh") + "# a comment\n\n"})
real_head = cp.read_head_code
cp.read_head_code = lambda repo_dir: (_ for _ in ()).throw(RuntimeError("git exited 128"))
d = run(["nohead"])
cp.read_head_code = real_head
check("history-U6", "a head that cannot be read keeps the diffs: 10 written exactly, nothing in use, counted apart",
      (lines(d), use(d), d["code"].get("unread"), d["code"].get("heads_unread")) == (10, (0, 0), 0, 1), summary(d))
history("iu9b", [{"b.py": body(12, "sh")}, {"b.py": "".join(body(12, "sh").splitlines(True)[:2])}])
commit(new_repo("iu9a"), {"a.py": body(12, "sh") + body(2, "own")}, (), "a copy of the lines", T0 + 3600)
unread_slot = os.path.basename(cp.slot("", OWNER, "iu9a"))


def failing(repo_dir):
    if os.path.basename(repo_dir) == unread_slot:
        raise RuntimeError("git exited 1")
    return real_added(repo_dir)


cp.read_added_code = failing
d = run(["iu9a", "iu9b"])
cp.read_added_code = real_added
check("in_use-IU-09", "a repository whose diffs cannot be read adds nothing in use, though its head reads: (2, 0)",
      (use(d), d["code"].get("unread")) == ((2, 0), 1), summary(d))
srv2 = os.path.join(ROOT, "srv2")
os.makedirs(srv2)
saved = dict(os.environ)
os.environ.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="url.file:///%s/.insteadOf" % srv2.replace("\\", "/"),
                  GIT_CONFIG_VALUE_0="https://github.com/%s/" % OWNER, CLONE_CACHE="1")
cp.clone = REAL_CLONE
cache2 = os.path.join(ROOT, "cache2")
os.makedirs(cache2)
try:
    r = new_repo("master", branch="master", where=srv2)
    commit(r, {"a.py": body(20, "ms") + "# c\n\n"}, (), "c", T0, ref="refs/heads/master")
    cp.collect(OWNER, [{"name": "master", "isPrivate": True}], cache2)
    git(r, "branch", "-m", "master", "main")
    d = cp.collect(OWNER, [{"name": "master", "isPrivate": True}], cache2)
    check("in_use-IU-09", "a cached clone after master is renamed main: 20 written, 20 in use, nothing unread",
          (lines(d), use(d), d["code"].get("unread"), d["code"].get("heads_unread")) == (20, (20, 0), 0, 0), summary(d))
finally:
    os.environ.clear()
    os.environ.update(saved)
    cp.clone = fake_clone

# ---------------------------------------------------------------- in_use-IU-12: .git-blame-ignore-revs in upper case
repo = new_repo("ignorer")
three = {"%s.py" % n: body(10, "ig" + n) for n in "abc"}
c1 = commit(repo, three, (), "write", T0)
c2 = commit(repo, {p: t.replace("line_", "row_") for p, t in three.items()}, [c1], "rename", T0 + 100)
commit(repo, dict({p: t.replace("line_", "row_") for p, t in three.items()},
                  **{".git-blame-ignore-revs": "# the rename\n%s\n" % c2.upper()}), [c2], "ignore it", T0 + 200)
d = run(["ignorer"])
check("in_use-IU-12", "a hash in upper case in .git-blame-ignore-revs is honoured: 30 written, 30 in use",
      (lines(d), use(d), len(d["commits"])) == (30, (30, 0), 3), summary(d))

# ---------------------------------------------------------------- history-U3: the head as flat arrays
repo, _ = one("flat", {"src/a.py": body(3000, "fl"), "tests/test_a.py": body(1000, "flt")})
head = cp.read_head_code(repo)
size = sum(sys.getsizeof(x) for x in (getattr(head, "hashes", head), getattr(head, "tests", b""),
                                      getattr(head, "rough", b"")))
check("history-U3", "the head is held in a few bytes a line (under 16), not a Counter of tuples",
      lambda: head.hashes.typecode == "q" and len(head) == 4000 and size < 16 * 4000, size)
check("history-U3", "and reads as the Counter did: 3,000 production, 1,000 tests",
      lambda: (sum(n for (h, t), n in head.items() if not t),
               sum(n for (h, t), n in head.items() if t)) == (3000, 1000))

# ---------------------------------------------------------------- history-U4: UTF-16 sources
one("utf16", {"a.ps1": "Write-Host 'one'\n$x = 2\n", "b.ps1": "﻿Write-Host 'one'\n$x = 2\n".encode("utf-16-le")})
d = run(["utf16"])
check("history-U4", "a UTF-16 script counts as its UTF-8 twin: 4 written, 4 in use", (lines(d), use(d)) == (4, (4, 0)),
      summary(d))

# ---------------------------------------------------------------- history-U5: copies with edits, uncounted names
try:
    readme = open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "README.md"), encoding="utf-8").read()
except OSError:
    readme = ""
check("history-U5", "README says an edited copy counts whole and a file first under an uncounted name never counts",
      "that changes even one line is a new file version" in readme
      and "never counts, even once it is renamed" in readme)
history("copyedit", [{"a.py": body(40, "ce")}, {"a.py": body(40, "ce"), "b.py": body(40, "ce").replace("= 7", "= 70")}])
d = run(["copyedit"])
check("history-U5", "a copy with one line changed counts every line it adds: 80 written", lines(d) == 80, summary(d))
history("txt2py", [{"notes.txt": body(5, "tp")}, {"notes.py": body(5, "tp")}])
d = run(["txt2py"])
check("history-U5", "a file first committed as .txt, renamed .py unchanged, never counts: 0 written", lines(d) == 0,
      summary(d))

# ---------------------------------------------------------------- data-C4-08, data-blind-18, history-U6: the data file
NOW = float(int(time.time()) // DAY * DAY + 20 * 3600)
folder = tempfile.mkdtemp(prefix="data-", dir=ROOT)
cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
cp.owner_login = lambda: "someone"
cp.profile_offset = lambda owner: None
cp.profile_location = lambda owner: ""
cp.list_repositories = lambda owner: [{"name": "a", "isPrivate": True}]
real_collect = cp.collect
cp.collect = lambda owner, repos, work, since=None: {
    "events": [(NOW - 5 * DAY, "Python", 100)], "commits": [NOW - 5 * DAY], "imports": [NOW - DAY],
    "import_lines": [(NOW - DAY, 777)], "mismatched": 0, "unread": 0, "left_out": {}, "copies": set(), "now": NOW,
    "code": {"production": 50, "tests": 0, "unread": 0, "heads_unread": 1, "approximate_imports": [(NOW - DAY, 77)]}}
saved = dict(os.environ)
os.environ.update(CLONE_CACHE=os.path.join(folder, "cache"), FORCE="1")
try:
    code = cp.main()
finally:
    os.environ.clear()
    os.environ.update(saved)
    cp.collect = real_collect
data = json.load(open(os.path.join(folder, "assets", "coderprint.json"), encoding="utf-8"))
imp = data["left_out"]["imports"]
check("data-blind-18", "left_out.imports points to an import definition and says how much rests on git's count",
      (imp.get("loc_skipped"), imp.get("approximate_loc"), imp.get("definition")) == (777, 77, "#/definitions/import"),
      imp)
definition = data["definitions"].get("import", {})
check("data-C4-08", "the import definition says only files of code count toward 500, and names the upload in parts",
      "files of code" in definition.get("means", "") and "50 new files" in definition.get("means", "")
      and "not written" in definition.get("means", "") and "commit and an active day" in definition.get("method", ""),
      definition)
check("history-U6", "scope says how many repositories were read without their head",
      data["scope"]["repositories"].get("read_without_head") == 1, data["scope"]["repositories"])
refs = set(__import__("re").findall(r'"#/definitions/([a-z_]+)"', json.dumps(data)))
check("data-C4-08", "every definition the data file refers to exists", refs <= set(data["definitions"]),
      refs - set(data["definitions"]))

shutil.rmtree(ROOT, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d" % (results.count(True), results.count(False)))
sys.exit(1 if not all(results) else 0)
