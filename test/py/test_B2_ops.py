"""Regression checks for operations, the Action and the README handling (coderprint v1.2.1, area B2_ops), for the
coderprint.py given as the only argument; README.md, SECURITY.md, action.yml and lib/compose.js are read from beside
it. Every history is synthetic and built in temporary folders, and every lookup GitHub would answer is faked: a gh
command is replaced by a local Python one-liner below run(), so run()'s own deadline checks still apply. One line
per check; a section that cannot run to its end (an older coderprint.py lacking what it tests) is one failed check.
Exit 1 on any failure.

  F1   in use is the same whatever PYTHONHASHSEED: a sweep's contested credit goes in git's file order
  F3   the profile's location is read inside RESERVE, which is kept for it, and never out of the last 80 seconds
  F4   a command, and git_lines, stop at their limit although something they started holds the output pipe, and
       on Windows nothing they started is left running (checks that need Windows say skip elsewhere)
  F5   a commit dated at the epoch draws in zones west of UTC, and the day arithmetic is unchanged otherwise
  F6   CARDS_TIME_LIMIT takes ASCII digits only, and a bad value always gets the rule's own message
  F7   when GitHub cannot be asked whose commits these are, the log says so and the panels are kept (as identity-F1
       settles it); README says it too, and coderprint.json says authorship_checked
  U1   a head is held in flat arrays (history-U3's Standing), the same pairs in the same order, 18 bytes a line
  U3   README says the data file and the log give how many repositories were counted
  f02  README markers count only alone on their lines outside code; two blocks or half of one stop the run
  f03  a UTF-16 or UTF-32 README, or one under another name, stops the run and is left as it was
  f04  write_all never writes through a link or outside the repository, and a stray .tmp folder stops nothing
  f05  action.yml's commit step commits exactly coderprint's files past any .gitignore, and the removal of cards.json
  f08  git_auth keeps the settings the environment already passes to git
  f12  repositories read without their line diffs are warned of in the log
  f13  an organization's card goes into its .github repository's profile/README.md, with images that resolve there
  f18  the location is read before cloning, so a collection that used the run's time still has it
  u04  Spotify ids with dots, underscores and hyphens are taken by the Action and by the relay alike
"""
import collections
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types

SRC = os.path.abspath(sys.argv[1])
REPO = os.path.dirname(SRC)
ROOT = tempfile.mkdtemp(prefix="b2-ops-")
NOW = float(int(time.time()) // 86400 * 86400 + 20 * 3600)   # 20:00 UTC today
T0 = 1700000000
OWNER = "owner1"
NOREPLY = "123+owner1@users.noreply.github.com"
WINDOWS = os.name == "nt"
START, END = "<!-- coderprint:start -->", "<!-- coderprint:end -->"
fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  %s" % (detail,)), flush=True)


def skip(name, why):
    print("skip %s  (%s)" % (name, why), flush=True)


def section(name):
    """Runs the function it decorates at once; one that stops early is a failed check, not a crash."""
    def run_it(fn):
        try:
            fn()
        except Exception as e:
            check("%s: the checks ran to their end" % name, False, "%s: %s" % (type(e).__name__, str(e)[:300]))
        return fn
    return run_it


def load():
    spec = importlib.util.spec_from_file_location("cp_%d" % time.perf_counter_ns(), SRC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read(path, mode="r"):
    with open(path, mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


README_TEXT = read(os.path.join(REPO, "README.md"))


# ---------------------------------------------------------------- synthetic histories

def git(repo, *args, when=T0, author=("Owner One", NOREPLY)):
    env = dict(os.environ, GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1], GIT_COMMITTER_NAME=author[0],
               GIT_COMMITTER_EMAIL=author[1], GIT_AUTHOR_DATE="@%d +0000" % when,
               GIT_COMMITTER_DATE="@%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false"] + list(args),
                       env=env, capture_output=True)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace")


def new_repo(name):
    path = os.path.join(ROOT, "src", name)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", "-b", "main", path], check=True, capture_output=True)
    return path


def write(repo, rel, text):
    p = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        f.write(text)


def commit(repo, msg, when, author=("Owner One", NOREPLY)):
    git(repo, "add", "-A", when=when, author=author)
    git(repo, "commit", "-q", "--allow-empty", "-m", msg, when=when, author=author)


def body(n, tag, indent=""):
    return "".join("%s%s_%d = %d\n" % (indent, tag, i, i) for i in range(n))


def offline(cp, logins=None, identity=None):
    """collect() on the repositories under ROOT/src, with GitHub's answers faked."""
    def clone(owner, name, dest):
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        subprocess.run(["git", "clone", "-q", "--bare", os.path.join(ROOT, "src", name), dest], check=True,
                       capture_output=True)
    cp.clone = clone
    cp.resolve_authors = lambda owner, samples: {e: (logins or {}).get(e) for e in samples}
    cp.owner_identity = lambda owner: identity if identity is not None else {"user": True, "id": 123,
                                                                                  "name": "Owner One"}
    cp.templates = lambda owner: {}
    cp.seed_blobs = lambda full_name, dest: None


def collect(cp, names, since=None):
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    return cp.collect(OWNER, [{"name": n, "isPrivate": True} for n in names], work, since)


def fake_gh(cp, answers):
    """gh answered by a Python one-liner the module starts itself, through its own subprocess, so run()'s deadline
    checks apply as in a real run: answers maps a word of the query to the JSON printed; any other query exits 1.
    Returns the list of queries started."""
    real, started = subprocess, []

    def rewrite(args):
        if os.path.basename(args[0]) not in ("gh", "gh.exe"):
            return args
        query = args[args.index("-f") + 1]
        started.append(query)
        answer = next((a for word, a in answers.items() if word in query), None)
        return [sys.executable, "-c", "import sys; sys.exit(1)" if answer is None else
                "import sys; sys.stdout.write(%r)" % json.dumps(answer)]
    fake = types.SimpleNamespace(**{k: getattr(real, k) for k in dir(real) if not k.startswith("__")})
    fake.run = lambda args, **kw: real.run(rewrite(args), **kw)
    fake.Popen = lambda args, **kw: real.Popen(rewrite(args), **kw)
    cp.subprocess = fake
    return started


def ev(days_ago, lang="Python", n=10, hour=9):
    t = NOW - days_ago * 86400
    return (t // 86400 * 86400 + hour * 3600, lang, n)


BASE = [ev(d, n=100 + d) for d in range(1, 30)]


def run_main(cp, folder=None, events=BASE, extra=None, env=None, repos=None, owner="someone", stub_profile=True,
             collect_with=None):
    """main() on faked data, as `python3 coderprint.py` runs it: (exit code or "failed: ...", log lines, folder)."""
    folder = folder or tempfile.mkdtemp(prefix="run-", dir=ROOT)
    cp.WORK, cp.OUT_DIR, cp.README = folder, os.path.join(folder, "assets"), os.path.join(folder, "README.md")
    cp.owner_login = lambda: owner
    if stub_profile:
        cp.profile_offset = lambda o: None
        cp.profile_location = lambda o: ""
    cp.list_repositories = lambda o: repos or [{"name": "a", "isPrivate": True}]
    data = {"events": events, "commits": [e[0] for e in events], "imports": [], "import_lines": [], "mismatched": 0,
            "unread": 0, "left_out": {}, "copies": set(), "now": NOW,
            "code": {"production": 0, "tests": 0, "unread": 0}}
    data.update(extra or {})
    cp.collect = collect_with or (lambda owner, repos, work, since=None: data)
    log = []
    cp.say = lambda msg: log.append(msg)
    old = dict(os.environ)
    for k in [k for k in os.environ if k.startswith("CARDS_") or k in ("GITHUB_REPOSITORY", "GH_TOKEN")]:
        del os.environ[k]
    os.environ.update({"CLONE_CACHE": os.path.join(folder, "cache"), "FORCE": "1", "CARDS_THEME": "ink",
                       **(env or {})})
    try:
        code = cp.main()
    except (RuntimeError, cp.Stopped) as e:
        code = "failed: %s" % e
    except BaseException as e:
        code = "failed: %s (%s)" % (type(e).__name__, e)
    finally:
        os.environ.clear()
        os.environ.update(old)
    return code, log, folder


def data_file(folder):
    path = os.path.join(folder, "assets", "coderprint.json")
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


# ---------------------------------------------------------------- F1: one result whatever the hash seed

if len(sys.argv) > 2 and sys.argv[2] == "child":   # one collect() in a fresh process, for F1
    shutil.rmtree(ROOT, ignore_errors=True)
    ROOT = sys.argv[3]
    cp = load()
    offline(cp)
    d = collect(cp, [sys.argv[4]])
    print(json.dumps([sum(n for _, _, n in d["events"]), d["code"]["production"], d["code"]["tests"]]))
    sys.exit(0)


@section("F1")
def _():
    for name, delete in (("split", False), ("gone", True)):
        # two identical copies (one file version: 20 written lines), then a sweep renames them differently, so the
        # credit is contested; "gone" deletes the tests copy afterwards, so the headline's in use depends on it
        r = new_repo(name)
        write(r, "src/a.py", body(20, "v"))
        write(r, "tests/b.py", body(20, "v"))
        for k in range(10):
            write(r, "src/f%d.py" % k, body(10, "f%d" % k))
        commit(r, "write", T0)
        write(r, "src/a.py", body(20, "x"))
        write(r, "tests/b.py", body(20, "y"))
        for k in range(10):
            write(r, "src/f%d.py" % k, body(10, "f%d" % k, indent="    "))
        commit(r, "format", T0 + 86400)
        if delete:
            os.remove(os.path.join(r, "tests", "b.py"))
            commit(r, "drop b", T0 + 2 * 86400)
        outcomes = collections.defaultdict(list)
        for seed in range(6):
            p = subprocess.run([sys.executable, os.path.abspath(__file__), SRC, "child", ROOT, name],
                               env=dict(os.environ, PYTHONHASHSEED=str(seed)), capture_output=True, text=True,
                               timeout=300)
            outcomes[p.stdout.strip() or "error: " + p.stderr.strip()[-200:]].append(seed)
        check("F1 %s: one outcome over PYTHONHASHSEED 0..5, credit in git's file order (written, production, tests)"
              % name, len(outcomes) == 1 and list(outcomes)[0] == "[120, 120, 0]", dict(outcomes))


# ---------------------------------------------------------------- F3 and f18: the location and the reserve

@section("F3")
def _():
    cp = load()
    started = fake_gh(cp, {"location": {"data": {"repositoryOwner": {"location": "Berlin"}}},
                           "viewer": {"data": {"viewer": {"login": OWNER}}}})
    cp.DEADLINE = time.monotonic() + cp.RESERVE + 3
    got = cp.profile_location(OWNER)
    check("F3 with RESERVE + 3 s left the location is read", got == "Berlin" and len(started) == 1, (got, started))
    try:
        cp.gql("query { viewer { login } }")
        other = "started"
    except RuntimeError as e:
        other = str(e)
    check("F3 any other command is still refused inside RESERVE", "out of time" in other, other)
    kept = cp.RESERVE - cp.PROFILE_TIMEOUT - cp.LOCATION_TIMEOUT
    cp.DEADLINE = time.monotonic() + kept + 3
    del started[:]
    got = cp.profile_location(OWNER)
    check("F3 the location query never takes the last %d seconds, kept for drawing and writing" % kept,
          got == "" and not started, (got, started))


@section("f18")
def _():
    for pressed in (False, True):
        cp = load()
        fake_gh(cp, {"location": {"data": {"repositoryOwner": {"location": "Berlin, Germany"}}}})
        order, seen_location = [], []
        real_location, real_zone = cp.profile_location, cp.local_zone

        def location(o):
            order.append("location")
            return real_location(o)

        def zone(offset, loc, now, seen=None):
            seen_location.append(loc)
            return real_zone(offset, loc, now, seen)

        def collect_late(owner, repos, work, since=None):
            order.append("collect")
            if pressed:   # the clones used the run's time: less is left than the location query may use
                cp.DEADLINE = time.monotonic() + 30
            return {"events": BASE, "commits": [e[0] for e in BASE], "imports": [], "import_lines": [],
                    "mismatched": 0, "unread": 0, "left_out": {}, "copies": set(), "now": NOW,
                    "code": {"production": 0, "tests": 0, "unread": 0}}
        cp.profile_offset, cp.profile_location, cp.local_zone = (lambda o: None), location, zone
        code, log, folder = run_main(cp, env={"CARDS_TIME_LIMIT": "1100"}, stub_profile=False,
                                     collect_with=collect_late)
        check("f18 %s: the location is read before any cloning and reaches the zone" % (
            "a collection that used the run's time" if pressed else "a run with time to spare"),
              code == 0 and order == ["location", "collect"] and seen_location == ["Berlin, Germany"],
              (code, order, seen_location, log[-1:]))


# ---------------------------------------------------------------- F4: limits hold though a child keeps the pipe

@section("F4")
def _():
    cp = load()
    spawn = getattr(cp, "spawn", subprocess.Popen)
    kill_tree = getattr(cp, "kill_tree", lambda p: p.kill())
    release = getattr(cp, "release", lambda p: None)
    sh = shutil.which("sh")
    exec_path = subprocess.run(["git", "--exec-path"], capture_output=True, text=True).stdout.strip()
    launchers = sorted({os.path.normpath(p) for p in (os.path.join(exec_path, "..", "..", "..", "cmd", "git.exe"),
                                                       r"C:\Program Files\Git\cmd\git.exe")
                        if WINDOWS and os.path.isfile(p)})
    gits = [("git on PATH", "git")] + [("Git for Windows' cmd\\git.exe launcher", p) for p in launchers[:1]]
    for label, git_exe in gits:
        t = time.monotonic()
        try:
            cp.run([git_exe, "-c", "alias.slow=!sleep 20", "slow"], timeout=3)
            msg = "returned"
        except RuntimeError as e:
            msg = str(e)
        took = time.monotonic() - t
        check("F4 run(timeout=3) via %s stops within 8 s though git's child holds the pipe" % label,
              took < 8 and "timed out after 3 seconds" in msg, "%.1f s, %s" % (took, msg))

    if sh:
        mark = os.path.join(ROOT, "orphan-alive")
        t = time.monotonic()
        try:
            cp.run([sh, "-c", "(sleep 8; echo alive > '%s') & exit 0" % mark.replace("\\", "/")], timeout=3)
            msg = "returned"
        except RuntimeError as e:
            msg = str(e)
        took = time.monotonic() - t
        check("F4 run(timeout=3) stops within 8 s though the command has exited and what it left holds the pipe",
              took < 8 and "timed out" in msg, "%.1f s, %s" % (took, msg))
        if WINDOWS:
            time.sleep(max(0.0, 10 - (time.monotonic() - t)))
            check("F4 what an exited command left running is ended with it (its job object)", not os.path.exists(mark))
        else:
            skip("F4 what an exited command left running is ended with it", "Windows only; elsewhere unchanged")
    else:
        skip("F4 an exited command's leftover holding the pipe", "no sh on PATH")

    if not WINDOWS:
        skip("F4 git_lines past its limit with a child holding the pipe", "Windows only; elsewhere unchanged")
        return
    for label, git_exe in gits:
        cp.DEADLINE = time.monotonic() + cp.RESERVE + 6.9   # limit() gives git 6 seconds
        t = time.monotonic()
        try:
            cp.git_lines([git_exe, "-c", "alias.slow=!sleep 20", "slow"], lambda stream: stream.read())
            msg = "returned"
        except RuntimeError as e:
            msg = str(e)
        took = time.monotonic() - t
        check("F4 git_lines with 6 s left via %s stops within 11 s" % label, took < 11 and "ran past" in msg,
              "%.1f s, %s" % (took, msg))
    cp.DEADLINE = None
    if not launchers:
        skip("F4 kill_tree ends the launcher's git", "no cmd\\git.exe launcher here")
        return
    p = spawn([launchers[0], "hash-object", "--stdin"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    time.sleep(1.5)
    kill_tree(p)
    done = threading.Event()
    threading.Thread(target=lambda: (p.stdout.read(), done.set()), daemon=True).start()
    ended = done.wait(5)   # the output ends only when the real git the launcher started has ended too
    p.stdin.close()
    release(p)
    check("F4 kill_tree ends the git that Git for Windows' launcher started", ended)


# ---------------------------------------------------------------- F5: the epoch, west of UTC

@section("F5")
def _():
    cp = load()
    west = dt.timezone(dt.timedelta(hours=-8))
    try:
        got = (cp.day_start(0, west), cp.day_label(0, west))
    except (OSError, OverflowError, ValueError) as e:
        got = "%s: %s" % (type(e).__name__, e)
    check("F5 day_start and day_label of the epoch at UTC-8: 31DEC1969, starting at -57600",
          got == (-57600, "31DEC1969"), got)
    zones = [dt.timezone(dt.timedelta(minutes=m)) for m in range(-720, 841, 45)] + [dt.timezone.utc]
    times = [43200, 86399.5, 951782400.25, 1700000000, 1711846800.000001, NOW, 2000000000.75]
    wall = lambda m: (m.replace(tzinfo=None), m.utcoffset())
    moment = getattr(cp, "moment", None)
    check("F5 moment() is datetime.fromtimestamp wherever that works", moment is not None and all(
        wall(moment(t, z)) == wall(dt.datetime.fromtimestamp(t, z)) for t in times for z in zones))
    for minutes in (60, -480, 0):
        cp = load()
        cp.profile_offset, cp.profile_location = (lambda o, m=minutes: (m, NOW)), (lambda o: "")
        events = [(0.0, "Python", 5), (NOW - 5 * 86400, "Python", 5)]
        code, log, folder = run_main(cp, events=events, stub_profile=False,
                                     extra={"commits": [0.0, NOW - 5 * 86400]})
        check("F5 a commit dated 01JAN1970 draws at %+d minutes" % minutes,
              code == 0 and data_file(folder) is not None, (code, log[-1:]))


# ---------------------------------------------------------------- F6: CARDS_TIME_LIMIT

@section("F6")
def _():
    cp = load()
    results = {}
    values = ("\u00b3\u2070\u2070", "\u0663\u0660\u0660", "\uff13\uff10\uff10", "9" * 5000, "86401", "000", "299",
              "abc", "300", "0300", " 1100 ", "86400")
    for value in values:
        os.environ["CARDS_TIME_LIMIT"] = value
        try:
            results[value] = "accepted %d" % round(cp.time_limit() - time.monotonic())
        except RuntimeError as e:
            results[value] = str(e)
        except Exception as e:
            results[value] = "crashed: %s" % type(e).__name__
    del os.environ["CARDS_TIME_LIMIT"]
    rule = "CARDS_TIME_LIMIT must be a whole number of seconds from 300 to 86400"
    bad = [v for v in values[:8] if results[v] != rule]
    check("F6 digits of other scripts, 5,000 digits and values out of range get the rule's own message", not bad,
          {v[:12]: results[v] for v in bad})
    good = {"300": 300, "0300": 300, " 1100 ": 1100, "86400": 86400}
    check("F6 ASCII digits in range are taken, leading zeros aside",
          all(results[v] == "accepted %d" % n for v, n in good.items()), {v: results[v] for v in good})


# ---------------------------------------------------------------- F7: authorship that could not be checked

@section("F7")
def _():
    r = new_repo("collab")
    write(r, "a.py", body(10, "own"))
    commit(r, "mine", T0)
    for k in range(5):
        write(r, "b%d.py" % k, body(50, "col%d" % k))
        commit(r, "theirs %d" % k, T0 + 3600 * (k + 1), author=("Col Laborator", "col@example.invalid"))
    # Merged with identity-F1, which settles the same failure more strictly: a run that cannot ask GitHub whose each
    # commit is names the lookup in "unchecked", and main keeps the existing panels with a warning, so no card ever
    # counts others' commits; the finding's "a visible statement that this run could not tell them apart" is that
    # warning, and every data file written says authorship_checked true.
    cp = load()
    offline(cp, logins={"col@example.invalid": "collaborator"})
    d = collect(cp, ["collab"])
    check("F7 a checked run is not marked: 10 lines, 5 others left out", not d.get("unchecked")
          and sum(n for _, _, n in d["events"]) == 10 and d["left_out"].get("others") == 5,
          (d.get("unchecked"), d["left_out"]))
    cp.resolve_authors = lambda owner, samples: (_ for _ in ()).throw(RuntimeError("gh exited 1"))
    d = collect(cp, ["collab"])
    check("F7 a lookup that fails is marked unchecked", "authorship" in (d.get("unchecked") or ()),
          d.get("unchecked"))
    cp.owner_identity = lambda owner: None
    d = collect(cp, ["collab"])
    check("F7 an account that cannot be read is marked unchecked too", "authorship" in (d.get("unchecked") or ()),
          d.get("unchecked"))
    cp = load()
    offline(cp, identity={"user": False, "id": None, "name": ""})
    d = collect(cp, ["collab"])
    check("F7 an organization, which counts every member by design, is not marked", not d.get("unchecked"),
          d.get("unchecked"))
    warning = "the existing panels are kept"
    code, log, folder = run_main(load(), extra={"unchecked": ["authorship"]})
    check("F7 a run that could not ask warns in the log and keeps the panels, writing nothing",
          code == 1 and any(line.startswith("::warning::") and warning in line for line in log)
          and data_file(folder) is None, (code, log[:2]))
    code, log, folder = run_main(load())
    scope = (data_file(folder) or {}).get("scope", {})
    check("F7 a checked run has no warning and authorship_checked true", code == 0
          and not any(warning in line for line in log) and scope.get("authorship_checked") is True, (code, scope))
    check("F7 README says a run that could not ask keeps the previous panels",
          "When GitHub cannot be asked, even on a second try, whose an address is" in README_TEXT
          and "the previous panels are kept, since the run could not tell your code" in README_TEXT)


# ---------------------------------------------------------------- U1: the head in arrays

@section("U1")
def _():
    r = new_repo("head")
    write(r, "a.py", "x = 1\ny = 2\n# a comment\nx = 1\n")
    write(r, "tests/test_b.py", "x = 1\n")
    commit(r, "head", T0)
    cp = load()
    bare = os.path.join(ROOT, "head.git")
    subprocess.run(["git", "clone", "-q", "--bare", r, bare], check=True, capture_output=True)
    standing = cp.read_head_code(bare)
    h = cp.line_hash
    expected = [((h("x = 1"), False), 2), ((h("y = 2"), False), 1), ((h("x = 1"), True), 1)]
    check("U1 read_head_code holds the same pairs in the same order as a Counter would", list(standing.items())
          == expected and all(type(t) is bool for (_, t), _ in standing.items()), list(standing.items()))
    # Merged with history-U3, whose Standing holds each line of code in flat arrays (its line_hash, whether it is test
    # code, whether a fallback read it, and the origin its history gives it, which tracing in use needs), where this
    # finding's held each distinct pair once with a count: a few bytes a line either way, against a Counter's 125.
    per_line = (standing.hashes.itemsize + 1 + 1 + standing.origins.itemsize
                if all(hasattr(standing, k) for k in ("hashes", "tests", "rough", "origins")) else None)
    check("U1 18 bytes a line of code, in flat arrays", not isinstance(standing, collections.Counter)
          and per_line == 18 and len(standing.hashes) == len(standing.tests) == len(standing.origins) == 4, per_line)
    offline(cp)
    d = collect(cp, ["head"])
    check("U1 in use read through the arrays: 3 production, 1 test",
          (d["code"]["production"], d["code"]["tests"]) == (3, 1), d["code"])


@section("U3")
def _():
    check("U3 README says the data file and the log give how many repositories were counted",
          "also give how many repositories it counted" in README_TEXT and "tell how many are private" in README_TEXT)


# ---------------------------------------------------------------- f02 and f03: the README

def readme_run(raw, name="README.md"):
    """new_readme on a README holding raw, twice: (first result or error, second result, the file untouched)."""
    folder = tempfile.mkdtemp(prefix="readme-", dir=ROOT)
    cp = load()
    cp.WORK, cp.README = folder, os.path.join(folder, "README.md")
    if raw is not None:
        with open(os.path.join(folder, name), "wb") as f:
            f.write(raw)
    try:
        first = cp.new_readme("NEW PANEL")
    except RuntimeError as e:
        return "error: %s" % e, None, raw is None or read(os.path.join(folder, name), "rb") == raw
    with open(os.path.join(folder, "README.md"), "wb") as f:
        f.write(first)
    return first, cp.new_readme("NEW PANEL"), True


@section("f02")
def _():
    own = "".join("My own line %d about my work.\n" % k for k in range(20))
    block = "%s\nOLD PANEL\n%s\n" % (START, END)
    for label, prefix, eol in (("a start marker quoted in prose above the real block",
                                "# Me\nThis profile uses coderprint, which writes after %s\n" % START, "\n"),
                               ("both markers in one sentence above the real block",
                                "# Me\ncoderprint writes between `%s` and `%s`.\n" % (START, END), "\n"),
                               ("a fenced example above the real block",
                                "# Me\n```html\n%s\nexample\n%s\n```\n" % (START, END), "\n"),
                               ("a tilde fence and a four-space example above the real block",
                                "# Me\n~~~\n%s\n~~~\n\n    %s\n    %s\n\n" % (START, START, END), "\n"),
                               ("a real block with CRLF endings", "# Me\n", "\r\n")):
        text = (prefix + block + own).replace("\n", eol)
        expected = (prefix + "%s\nNEW PANEL\n%s\n" % (START, END) + own).replace("\n", eol).encode()
        first, second, _ = readme_run(text.encode("utf-8"))
        check("f02 %s: every byte outside the real block kept, the block rewritten, a rerun identical" % label,
              first == expected and second == expected, first[:200] if isinstance(first, bytes) else first)
    first, _, _ = readme_run(("# Me\ncoderprint writes between `%s` and `%s`.\n%s" % (START, END, own)).encode())
    out = first.decode() if isinstance(first, bytes) else first
    check("f02 a README that only quotes the markers gets the block on top and keeps its text",
          isinstance(first, bytes) and out.startswith(START + "\nNEW PANEL\n" + END) and own in out, out[:120])
    for label, text, counts in (("two real blocks", "# Me\n" + block + own + block, "2 and 2"),
                                ("a start marker with no end", "# Me\n%s\nOLD\n%s" % (START, own), "1 and 0"),
                                ("an end marker before the start", "# Me\n%s\nOLD\n%s\n" % (END, START), "1 and 1")):
        first, _, untouched = readme_run(text.encode())
        check("f02 %s stops the run and leaves the README as it was" % label,
              isinstance(first, str) and "must hold exactly one" in first and counts in first and untouched, first)


@section("f03")
def _():
    for label, raw in (("UTF-16LE with a byte order mark", "\ufeff# Me\nWords.\n".encode("utf-16-le")),
                       ("UTF-16BE with a byte order mark", "\ufeff# Me\nWords.\n".encode("utf-16-be")),
                       ("UTF-32LE with a byte order mark", "\ufeff# Me\nWords.\n".encode("utf-32-le")),
                       ("UTF-16LE without one", "# Me\nWords.\n".encode("utf-16-le"))):
        first, _, untouched = readme_run(raw)
        check("f03 a README in %s stops the run and is left as it was" % label,
              isinstance(first, str) and "is not UTF-8 text" in first and untouched, first)
    for name in ("README.rst", "README", "readme.markdown"):
        first, _, untouched = readme_run(b"# Me\nWords.\n", name)
        check("f03 only %s present stops the run and leaves it as it was" % name,
              isinstance(first, str) and "is not named README.md" in first and untouched, first)
    first, _, _ = readme_run(None)
    check("f03 no README at all still gets a new one holding the block",
          isinstance(first, bytes) and first.decode().startswith(START), first)
    for label, raw in (("cp1252", "# Hi, I'm Ren\xe9e\n".encode("cp1252")), ("UTF-8 with a byte order mark",
                                                                          b"\xef\xbb\xbf# About\n")):
        first, second, _ = readme_run(raw)
        check("f03 a README in %s is still edited in place, its bytes kept" % label,
              isinstance(first, bytes) and first.endswith(raw[3:] if raw.startswith(b"\xef") else raw)
              and first == second, first)


# ---------------------------------------------------------------- f04: write_all

@section("f04")
def _():
    cp = load()
    work = tempfile.mkdtemp(prefix="repo-", dir=ROOT)
    outside = tempfile.mkdtemp(prefix="outside-", dir=ROOT)
    cp.WORK = work
    link = os.path.join(work, "assets")
    try:
        os.symlink(outside, link, target_is_directory=True)
        made = True
    except OSError:
        made = WINDOWS and subprocess.run(["cmd", "/c", "mklink", "/J", link, outside],
                                          capture_output=True).returncode == 0
    if made:
        try:
            cp.write_all({os.path.join(work, "README.md"): b"x", os.path.join(link, "panel-dark.svg"): b"<svg/>"})
            msg = "written"
        except RuntimeError as e:
            msg = str(e)
        check("f04 an assets folder that leads outside the repository is refused, and nothing is written anywhere",
              "leads outside this repository" in msg and not os.listdir(outside)
              and not os.path.exists(os.path.join(work, "README.md")), (msg, os.listdir(outside)))
        os.rmdir(link) if WINDOWS else os.remove(link)
    else:
        skip("f04 an assets folder that leads outside the repository", "this machine can make neither a link nor "
             "a junction")
    os.makedirs(os.path.join(work, "assets", "coderprint.json.tmp"))
    os.makedirs(os.path.join(work, "assets", "panel-dark.svg.tmp"))
    try:
        cp.write_all({os.path.join(work, "assets", "coderprint.json"): b"{}\n",
                      os.path.join(work, "assets", "panel-dark.svg"): b"<svg/>\n"})
        msg = "written"
    except (RuntimeError, OSError) as e:
        msg = "%s: %s" % (type(e).__name__, e)
    left = sorted(os.listdir(os.path.join(work, "assets")))
    check("f04 folders named like the old temporary files stop nothing, and no temporary file is left",
          msg == "written" and read(os.path.join(work, "assets", "coderprint.json")) == "{}\n"
          and left == ["coderprint.json", "coderprint.json.tmp", "panel-dark.svg", "panel-dark.svg.tmp"], (msg, left))
    if not WINDOWS:
        mask = os.umask(0)
        os.umask(mask)
        mode = os.stat(os.path.join(work, "assets", "coderprint.json")).st_mode & 0o777
        check("f04 files get the mode a plain write would give them", mode == 0o666 & ~mask, oct(mode))


# ---------------------------------------------------------------- f05 and f13: action.yml's commit step

ASSETS = ["assets/panel-light.svg", "assets/panel-dark.svg", "assets/panel-compact-light.svg",
          "assets/panel-compact-dark.svg", "assets/blank.svg", "assets/coderprint.json"]


def commit_step(script, repo_name, ignore, readme="README.md", legacy=False, stray=False):
    """Runs the step against a local bare remote: (exit code, files on the pushed branch, stderr, root README)."""
    env = dict(os.environ, GIT_AUTHOR_NAME="Owner One", GIT_AUTHOR_EMAIL=NOREPLY, GIT_COMMITTER_NAME="Owner One",
               GIT_COMMITTER_EMAIL=NOREPLY, GITHUB_REPOSITORY=repo_name)
    sh_ = lambda cwd, *args: subprocess.run(list(args), cwd=cwd, env=env, capture_output=True, text=True)
    root = tempfile.mkdtemp(prefix="action-", dir=ROOT)
    remote, work = os.path.join(root, "remote.git"), os.path.join(root, "work")
    sh_(root, "git", "init", "-q", "--bare", "-b", "main", remote)
    sh_(root, "git", "clone", "-q", remote, work)
    sh_(work, "git", "checkout", "-q", "-b", "main")
    write(work, "README.md", "# The repository's own README\n")
    if ignore:
        write(work, ".gitignore", ignore)
    if legacy:   # a cards.json an earlier version committed, which this version removes
        write(work, "assets/cards.json", '{"palette": {}}\n')
        sh_(work, "git", "add", "-f", "assets/cards.json")
    sh_(work, "git", "add", "-A")
    sh_(work, "git", "-c", "commit.gpgsign=false", "commit", "-q", "-m", "init")
    sh_(work, "git", "push", "-q", "origin", "main")
    for f in ASSETS:
        write(work, f, "<svg/>\n" if f.endswith(".svg") else "{}\n")
    write(work, readme, "%s\nx\n%s\n" % (START, END))
    if legacy:
        os.remove(os.path.join(work, "assets", "cards.json"))
    if stray:   # a leftover temporary file, and a cards.json of the owner's own that .gitignore keeps out
        write(work, "assets/.coderprint-left.tmp", "stray\n")
        if not legacy:
            write(work, "assets/cards.json", '{"hello": 1}\n')
    p = subprocess.run([shutil.which("bash"), "--noprofile", "--norc", "-eo", "pipefail", "-c", script], cwd=work,
                       env=env, capture_output=True, text=True, timeout=300)
    pushed = sh_(root, "git", "--git-dir", remote, "ls-tree", "-r", "--name-only", "main").stdout.split()
    root_readme = sh_(root, "git", "--git-dir", remote, "show", "main:README.md").stdout
    return p.returncode, pushed, p.stderr.strip(), root_readme


@section("f05 and f13 (action.yml)")
def _():
    if not shutil.which("bash"):
        skip("f05 and f13 action.yml's commit step", "no bash")
        return
    action = read(os.path.join(REPO, "action.yml"))
    step = action.split("- name: Commit the panel if it changed", 1)[1]
    script = re.sub(r"(?m)^ {8}", "", step.split("run: |\n", 1)[1])
    for ignore in ("", "*.svg\n", "*.json\n", "assets/\n", "README.md\n"):
        code, pushed, err, _ = commit_step(script, "owner1/owner1", ignore)
        missing = [f for f in ASSETS + ["README.md"] if f not in pushed]
        check("f05 %s: the step succeeds and every file coderprint wrote is pushed" % (
            "no .gitignore" if not ignore else "a .gitignore ignoring " + ignore.strip()),
              code == 0 and not missing, (code, missing, err[:200]))
    code, pushed, err, _ = commit_step(script, "owner1/owner1", "", legacy=True, stray=True)
    check("f05 the removal of the old cards.json is committed, and nothing else in assets is",
          code == 0 and "assets/cards.json" not in pushed and not any("coderprint-left" in f for f in pushed)
          and all(f in pushed for f in ASSETS), (code, pushed, err[:200]))
    code, pushed, err, _ = commit_step(script, "owner1/owner1", "assets/cards.json\n", stray=True)
    check("f05 a cards.json the owner keeps out with .gitignore, which coderprint never wrote, stays out",
          code == 0 and "assets/cards.json" not in pushed and all(f in pushed for f in ASSETS),
          (code, pushed, err[:200]))
    for name in ("acme/.github", "acme/.GitHub"):
        code, pushed, err, root_readme = commit_step(script, name, "*.svg\n", readme="profile/README.md")
        check("f13 %s: profile/README.md and the assets are pushed, the repository's own README untouched" % name,
              code == 0 and "profile/README.md" in pushed and all(f in pushed for f in ASSETS)
              and root_readme == "# The repository's own README\n", (code, pushed, err[:200]))


# ---------------------------------------------------------------- f08: git_auth

@section("f08")
def _():
    cp = load()
    old = dict(os.environ)
    try:
        os.environ.update({"GH_TOKEN": "fake-token-for-a-test", "GIT_CONFIG_COUNT": "2",
                           "GIT_CONFIG_KEY_0": "http.sslCAInfo", "GIT_CONFIG_VALUE_0": "/etc/ssl/runner-ca.pem",
                           "GIT_CONFIG_KEY_1": "http.proxy", "GIT_CONFIG_VALUE_1": "http://proxy.invalid:3128"})
        flags, env = cp.git_auth("owner1", "example")
        listed = subprocess.run(["git", "config", "--list", "--show-scope"], env=env, cwd=ROOT, capture_output=True,
                                text=True).stdout
        keys = sorted({line.split("\t", 1)[1].split("=", 1)[0] for line in listed.splitlines()
                       if line.startswith("command\t")})
        check("f08 git sees the runner's own settings and coderprint's header",
              keys == ["http.https://github.com/owner1/example.git.extraheader", "http.proxy", "http.sslcainfo"], keys)
        os.environ["GIT_CONFIG_COUNT"] = "junk"
        flags, env = cp.git_auth("owner1", "example")
        check("f08 a count git would refuse is replaced", env["GIT_CONFIG_COUNT"] == "1"
              and env["GIT_CONFIG_KEY_0"] == "http.https://github.com/owner1/example.git.extraheader", env["GIT_CONFIG_COUNT"])
    finally:
        os.environ.clear()
        os.environ.update(old)


# ---------------------------------------------------------------- f12: repositories read without line diffs

@section("f12")
def _():
    ten = [{"name": "r%d" % k, "isPrivate": False} for k in range(10)]
    code, log, folder = run_main(load(), repos=ten, extra={"code": {"production": 0, "tests": 0, "unread": 6}})
    said = [line for line in log if "could not be read line by line" in line]
    check("f12 6 of 10 read without line diffs: drawn, and the log warns", code == 0 and said
          and said[0].startswith("::warning::6 of the 10 repositories read"), (code, said))
    code, log, folder = run_main(load(), repos=ten)
    check("f12 no warning when every repository was read line by line",
          code == 0 and not any("line by line" in line for line in log), log)
    check("f12 README says such a repository is warned of in the log", "is warned of in the run's log" in README_TEXT)


# ---------------------------------------------------------------- f13: an organization's card

@section("f13")
def _():
    raw_org = "https://raw.githubusercontent.com/acme/.github/HEAD/assets/"
    for label, env in (("alone", {}), ("with a Spotify card", {"CARDS_SPOTIFY_UID": "abc123"})):
        folder = tempfile.mkdtemp(prefix="org-", dir=ROOT)
        write(folder, "README.md", "# The .github repository\n")
        code, log, _ = run_main(load(), folder=folder, owner="acme", env=dict(env, GITHUB_REPOSITORY="acme/.GitHub"))
        profile = os.path.join(folder, "profile", "README.md")
        text = read(profile) if os.path.exists(profile) else ""
        panels = [u for u in re.findall(r'(?:srcset|src)="([^"]+)"', text) if "panel" in u or "blank" in u]
        check("f13 %s: the block goes into profile/README.md, every panel image under acme/.github" % label,
              code == 0 and panels and all(u.startswith(raw_org) for u in panels)
              and read(os.path.join(folder, "README.md")) == "# The .github repository\n", (code, panels, log[-1:]))
        meta = re.search(r"<metadata>(.*?)</metadata>", read(os.path.join(folder, "assets", "panel-dark.svg")), re.S)
        check("f13 %s: the panels name the data file where it is" % label,
              meta is not None and raw_org + "coderprint.json" in meta.group(1))
    folder = tempfile.mkdtemp(prefix="org-", dir=ROOT)
    code, log, _ = run_main(load(), folder=folder, owner="acme",
                            env={"GITHUB_REPOSITORY": "acme/.github",
                                 "CARDS_RELAY": "https://relay.example.invalid/api/card"})
    check("f13 an organization with a relay stops before any work, writing nothing",
          isinstance(code, str) and "relay does not serve an organization's card yet" in code
          and not os.listdir(folder), (code, os.listdir(folder)))
    code, log, folder = run_main(load(), env={"GITHUB_REPOSITORY": "someone/someone", "CARDS_SPOTIFY_UID": "abc123"})
    text = read(os.path.join(folder, "README.md"))
    check("f13 a person's card is where it always was, with the same relative images beside a music card",
          code == 0 and 'srcset="assets/panel-dark.svg"' in text and not os.path.exists(os.path.join(folder,
                                                                                                    "profile")),
          (code, text[:200]))
    check("f13 README and SECURITY.md say where an organization's panel goes",
          "`.github` repository, where the panel goes into `profile/README.md`" in README_TEXT
          and "profile/README.md" in read(os.path.join(REPO, "SECURITY.md")))


# ---------------------------------------------------------------- u04: Spotify ids

@section("u04")
def _():
    cp = load()
    said = {}
    for uid in ("john.doe_99", "anna-lisa", "31abcdefghijklmnopqrstuvwxyz", "../x", "abc&evil=1", "a" * 65,
                "\u00e9", "a b"):
        old = dict(os.environ)
        for k in [k for k in os.environ if k.startswith("CARDS_")]:
            del os.environ[k]
        os.environ["CARDS_SPOTIFY_UID"] = uid
        try:
            cp.settings()
            said[uid] = "accepted"
        except RuntimeError as e:
            said[uid] = str(e)
        finally:
            os.environ.clear()
            os.environ.update(old)
    check("u04 settings() takes ids with dots, underscores and hyphens",
          all(said[u] == "accepted" for u in ("john.doe_99", "anna-lisa", "31abcdefghijklmnopqrstuvwxyz")), said)
    check("u04 and still refuses anything a query string would need escaped, or too long",
          all(said[u].startswith("CARDS_SPOTIFY_UID must be") for u in ("../x", "abc&evil=1", "a" * 65, "\u00e9",
                                                                        "a b")), said)
    compose = read(os.path.join(REPO, "lib", "compose.js"))
    check("u04 the relay takes the same ids (lib/compose.js UID)", "const UID = /^[A-Za-z0-9._-]{1,64}$/;" in compose)


shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d %s" % (passes, len(fails), fails))
sys.exit(1 if fails else 0)
