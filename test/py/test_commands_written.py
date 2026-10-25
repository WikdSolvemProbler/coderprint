"""Regression checks for running commands (generator/commands.py) and reading the lines each commit wrote
(generator/written.py), for the coderprint.py given as the only argument. Commands are harmless local Python
one-liners, never the network; Windows' job objects are checked against a fake kernel32 and ntdll, so those checks run
on every system. Histories are built in a temporary folder. One line per check; exit 1 on any failure.

  commands
    C1   say and truthy
    C2   time_left: none without a deadline, what is left less the reserve, OutOfTime under five seconds
    C3   run: the output; a non-zero exit is Failed carrying the output; a program that cannot start; a command not
         started past the deadline; a timeout, as RuntimeError, or as OutOfTime when the deadline cut it; an
         interrupt ends the command and passes on; argv never shows in a message
    C4   child_env leaves out other installations' secrets and, for the plain environment, the tokens
    C5   graphql_args, graphql_answer, gql (errors taken as a list, or failing), answered, again
    C6   win32: False off Windows, False when ctypes lacks the calls, the two libraries when it has them
    C7   spawn on Windows: no job, Popen failing, no handle, a failed resume started again plainly, joined or not
    C8   kill_tree: the job ended, else taskkill on the tree (its failure ignored), and kill's OSError ignored
    C9   settle on Windows: pipes left to their threads on a timeout; a wait that times out; close failing
    C10  release closes the job once
  written
    W1   lfs_pointer, header_paths and git_version's fallback
    W2   read_added_code: added and removed lines of code, comments left out, a deleted file pooled under DELETED
    W3   a deleted UTF-16 file is read whole; a deleted file no git can give is read from its diff's lines
    W4   a version whose old version cannot be had is read whole from git (its hunks' added lines counted), and,
         when it cannot be had either, each hunk alone (approximate); with pairs for a watched commit
    W5   a binary file that is not text adds nothing; a UTF-16 file edited is diffed line for line, with pairs
    W6   merges: a version made from its first parent is kept; with tracing its lines take their origins
    W7   tracing: the head's versions get origins, an ls-tree failure stops on OutOfTime, a failing trace is broken
    W8   attributed and attributed_versions: linguist attributes by commit, None when git cannot say
    W9   diff_path; a rename adds only its edit; a symbolic link adds nothing; an old last line that only gains its
         line end is neither added nor removed, and keeps its origin; Standing
"""
import contextlib
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types

for _k in list(os.environ):
    if _k.startswith(("GIT_CONFIG_", "CARDS_")):
        del os.environ[_k]

spec = importlib.util.spec_from_file_location("cp_under_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

ROOT = tempfile.mkdtemp(prefix="cmdw-")
PY = sys.executable
PYNAME = os.path.basename(PY)
NOREPLY = "123+owner1@users.noreply.github.com"
T0 = 1700000000
fails, passes = [], 0


def check(name, ok, detail=""):
    global passes
    if callable(ok):
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    if ok:
        passes += 1
    else:
        fails.append(name)
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, "" if ok else "  [got %r]" % (detail,)), flush=True)


def raised(fn, *a, **k):
    """(exception type name, message, exception) that fn raises, or ("none", repr(result), None)."""
    try:
        r = fn(*a, **k)
    except BaseException as e:   # KeyboardInterrupt included
        return type(e).__name__, str(e), e
    return "none", repr(r), None


# ======================================================================= commands
# ---------------------------------------------------------------- C1
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    cp.say("hello there")
check("C1 say prints its message and a newline", buf.getvalue() == "hello there\n", buf.getvalue())
os.environ["CP_T_FLAG"] = " Yes "
t1 = cp.truthy("CP_T_FLAG")
os.environ["CP_T_FLAG"] = "0"
t2 = cp.truthy("CP_T_FLAG")
del os.environ["CP_T_FLAG"]
check("C1 truthy takes yes/1/true in any case and spacing, and nothing else", (t1, t2, cp.truthy("CP_T_FLAG")) ==
      (True, False, False), (t1, t2))

# ---------------------------------------------------------------- C2
check("C2 no deadline: time_left is None", cp.time_left() is None)
cp.DEADLINE = time.monotonic() + 300
left = cp.time_left(reserve=100)
check("C2 time_left is what is left less the reserve", left in (198, 199, 200), left)
left = cp.time_left()   # RESERVE is 120
check("C2 time_left keeps RESERVE back unless told", left in (178, 179, 180), left)
cp.DEADLINE = time.monotonic() + 124
got = raised(cp.time_left)
check("C2 under five seconds left is OutOfTime", got[:2] == ("OutOfTime", "the run is out of time"), got)
got = raised(cp.run, [PY, "-c", "print(1)"])
check("C3 a command is not started past the deadline, named by its program only",
      got[:2] == ("OutOfTime", "%s was not started: the run is out of time" % PYNAME), got)
cp.DEADLINE = None

# ---------------------------------------------------------------- C3
out = cp.run([PY, "-c", "import sys; sys.stdout.write('out'); sys.stderr.write('err')"])
check("C3 run returns stdout alone, as bytes", out == b"out", out)
got = raised(cp.run, [PY, "-c", "import sys; print('answer'); sys.exit(3)", "secret/clone-url"])
check("C3 a non-zero exit is Failed naming only the program and its code",
      got[:2] == ("Failed", "%s exited 3" % PYNAME) and got[2].output.strip() == b"answer", got)
check("C3 Failed is a RuntimeError, so callers that take RuntimeError take it", isinstance(got[2], RuntimeError))
missing = os.path.join(ROOT, "no-such-program")
got = raised(cp.run, [missing, "https://secret@example.com/x"])
check("C3 a program that cannot start fails as RuntimeError naming only it",
      got[:2] == ("RuntimeError", "no-such-program could not be started"), got)
t = time.monotonic()
got = raised(cp.run, [PY, "-c", "import time; time.sleep(30)"], timeout=1)
check("C3 a command past its timeout is ended and fails as RuntimeError, not OutOfTime",
      got[:2] == ("RuntimeError", "%s timed out after 1 seconds" % PYNAME) and time.monotonic() - t < 15, got)
cp.DEADLINE = time.monotonic() + 6.9
t = time.monotonic()
got = raised(cp.run, [PY, "-c", "import time; time.sleep(30)"], reserve=0)
cp.DEADLINE = None
check("C3 a command the deadline cuts short fails as OutOfTime with the time it had",
      got[:2] == ("OutOfTime", "%s timed out after 6 seconds: the run is out of time" % PYNAME)
      and time.monotonic() - t < 15, got)
cp.DEADLINE = time.monotonic() + 1000
got = raised(cp.run, [PY, "-c", "print(2)"], timeout=5, reserve=0)
cp.DEADLINE = None
check("C3 a timeout shorter than what is left is kept (the command runs)", got[:2] == ("none", "b'2\\n'"), got)


class FakeProc:
    """A stand-in for Popen: what was done to it is recorded in calls."""

    def __init__(self, communicate=None, wait=None, kill=None, poll=None, pipes=True, handle=7, returncode=0):
        self.calls, self._communicate, self._wait, self._kill, self._poll = [], communicate, wait, kill, poll
        self.returncode, self.pid = returncode, 4242
        if handle is not None:
            self._handle = handle
        self.stdin = FakePipe(self.calls, "stdin") if pipes else None
        self.stdout = FakePipe(self.calls, "stdout") if pipes else None
        self.stderr = FakePipe(self.calls, "stderr") if pipes else None

    def communicate(self, timeout=None):
        self.calls.append(("communicate", timeout))
        if self._communicate:
            raise self._communicate
        return b"", b""

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        if self._wait:
            raise self._wait
        return self.returncode

    def kill(self):
        self.calls.append("kill")
        if self._kill:
            raise self._kill

    def poll(self):
        self.calls.append("poll")
        return self._poll


class FakePipe:
    def __init__(self, calls, name, fail=None):
        self.calls, self.name, self.fail = calls, name, fail

    def close(self):
        self.calls.append(("close", self.name))
        if self.fail:
            raise self.fail


real_spawn = cp.spawn
proc = FakeProc(communicate=KeyboardInterrupt())
cp.spawn = lambda args, **kw: proc
got = raised(cp.run, [PY, "-c", "pass"])
cp.spawn = real_spawn
check("C3 an interrupt while a command runs ends it, closes its pipes and passes on",
      got[0] == "KeyboardInterrupt" and "kill" in proc.calls and ("close", "stdout") in proc.calls
      and ("close", "stderr") in proc.calls, (got, proc.calls))

# ---------------------------------------------------------------- C4
env = cp.child_env({"CARDS_ORGANIZATION_TOKENS": "x", "CARDS_AUTHORED_IMPORTS": "y",
                    "CARDS_ORGANIZATION_SNAPSHOT_KEY": "z", "GH_TOKEN": "t", "KEEP": "1"})
check("C4 a given environment loses the other installations' secrets and keeps its token",
      env == {"GH_TOKEN": "t", "KEEP": "1"}, env)
os.environ["GH_TOKEN"], os.environ["GITHUB_TOKEN"] = "a", "b"
env = cp.child_env()
del os.environ["GH_TOKEN"], os.environ["GITHUB_TOKEN"]
check("C4 the plain environment loses GH_TOKEN and GITHUB_TOKEN", "GH_TOKEN" not in env and "GITHUB_TOKEN" not in env
      and env.get("PATH") == os.environ.get("PATH"), sorted(env)[:5])

# ---------------------------------------------------------------- C5
check("C5 graphql_args passes the query and each variable with -f",
      cp.graphql_args("query{x}", {"login": "o", "n": 3}) ==
      ["gh", "api", "graphql", "-f", "query=query{x}", "-f", "login=o", "-f", "n=3"])
check("C5 graphql_answer takes an answer with data", cp.graphql_answer(b'{"data": {"a": 1}}') == {"data": {"a": 1}})
for body in (b'{"data": null, "errors": [{"message": "x"}]}', b'[1]', b'{"errors": []}'):
    got = raised(cp.graphql_answer, body)
    check("C5 graphql_answer fails without data: %s" % body.decode(),
          got[:2] == ("RuntimeError", "the GitHub API returned no data"), got)
real_run = cp.run
seen = []


def fake_gh(answer, fail=False):
    def run(args, env=None, timeout=None, **kw):
        seen.append((args, timeout, kw))
        if fail:
            raise cp.Failed("gh exited 1", answer)
        return answer
    return run


cp.run = fake_gh(b'{"data": {"viewer": {"login": "o"}}}')
got = cp.gql("q", timeout=7, login="o")
check("C5 gql returns the data, passing the timeout and variables",
      got == {"viewer": {"login": "o"}} and seen[-1] == (["gh", "api", "graphql", "-f", "query=q", "-f", "login=o"],
                                                         7, {}), (got, seen[-1]))
cp.gql("q", reserve=33)
check("C5 gql passes a reserve on to run", seen[-1][2] == {"reserve": 33}, seen[-1])
cp.run = fake_gh(b'{"data": {"a": null}, "errors": [{"message": "no access"}]}', fail=True)
got = raised(cp.gql, "q")
check("C5 gql without an errors list fails as gh did", got[:2] == ("Failed", "gh exited 1"), got)
errs = []
got = cp.gql("q", errors=errs)
check("C5 gql with an errors list takes the answer and adds its errors",
      got == {"a": None} and errs == [{"message": "no access"}], (got, errs))
cp.run = fake_gh(b'{"data": {"a": 2}, "errors": {"message": "one"}}')
got = cp.answered("q", x=1)
check("C5 answered gives (data, errors), a lone error made a list", got == ({"a": 2}, [{"message": "one"}]), got)
cp.run = fake_gh(b'{"data": {"a": 3}}')
check("C5 answered with no errors gives an empty list", cp.answered("q") == ({"a": 3}, []))
cp.run = real_run
tries = []


def flaky(exc, then=None):
    def ask():
        tries.append(1)
        if len(tries) == 1 or then is None:
            raise exc
        return then
    return ask


for exc in (RuntimeError("x"), ValueError("x"), KeyError("x"), TypeError("x"), AttributeError("x")):
    tries.clear()
    got = cp.again(flaky(exc, "second"))
    check("C5 again asks once more after %s" % type(exc).__name__, got == "second" and len(tries) == 2, (got, tries))
tries.clear()
got = raised(cp.again, flaky(cp.OutOfTime("late"), "second"))
check("C5 again does not ask again when out of time", got[:2] == ("OutOfTime", "late") and len(tries) == 1, got)
tries.clear()
got = raised(cp.again, flaky(RuntimeError("both")))
check("C5 again's second failure passes on", got[:2] == ("RuntimeError", "both") and len(tries) == 2, got)
tries.clear()
got = raised(cp.again, flaky(OSError("other")))
check("C5 again does not retry what it does not expect", got[0] == "OSError" and len(tries) == 1, got)

# ---------------------------------------------------------------- C6 to C10: Windows, faked
REAL_OS, REAL_SUBPROCESS = cp.os, cp.subprocess


class NtOs(types.ModuleType):
    name = "nt"

    def __getattr__(self, attr):
        return getattr(REAL_OS, attr)


class FakeFn:
    def __init__(self, name, log, result):
        self.name, self.log, self.result = name, log, result

    def __call__(self, *args):
        self.log.append((self.name,) + args)
        return self.result(*args) if callable(self.result) else self.result


class FakeLib:
    def __init__(self, log, **results):
        for name, result in results.items():
            setattr(self, name, FakeFn(name, log, result))


def fake_ctypes(log, winDLL):
    ct = types.ModuleType("ctypes")
    wt = types.ModuleType("ctypes.wintypes")
    for n in ("LPCWSTR", "HANDLE", "BOOL", "UINT"):
        setattr(wt, n, n)
    ct.c_void_p, ct.c_long, ct.wintypes = "c_void_p", "c_long", wt
    if winDLL is not None:
        ct.WinDLL = winDLL
    return ct, wt


def with_modules(mods, fn):
    saved = {k: sys.modules.get(k) for k in mods}
    sys.modules.update(mods)
    try:
        return fn()
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


cp._WIN32 = None
check("C6 win32 is False off Windows", cp.win32() is False and cp._WIN32 is False)
cp.os = NtOs("os")
try:
    cp._WIN32 = None
    ct, wt = fake_ctypes([], None)   # a ctypes with no WinDLL
    got = with_modules({"ctypes": ct, "ctypes.wintypes": wt}, cp.win32)
    check("C6 win32 is False when ctypes lacks WinDLL", got is False, got)
    check("C6 win32 is worked out once", cp.win32() is False)
    log = []
    k = FakeLib(log, CreateJobObjectW=1, AssignProcessToJobObject=1, TerminateJobObject=1, TerminateProcess=1,
                CloseHandle=1)
    n = FakeLib(log, NtResumeProcess=0)
    ct, wt = fake_ctypes(log, lambda name, **kw: {"kernel32": k, "ntdll": n}[name])
    cp._WIN32 = None
    got = with_modules({"ctypes": ct, "ctypes.wintypes": wt}, cp.win32)
    check("C6 win32 gives kernel32 and ntdll with their calls' types set",
          got == (k, n) and k.CreateJobObjectW.argtypes == ["c_void_p", "LPCWSTR"]
          and k.CreateJobObjectW.restype == "HANDLE" and n.NtResumeProcess.restype == "c_long"
          and k.TerminateJobObject.argtypes == ["HANDLE", "UINT"], got)

    popened = []

    def make_sub(popen_results, run=None):
        sub = types.ModuleType("subprocess")
        sub.__dict__.update(REAL_SUBPROCESS.__dict__)
        it = iter(popen_results)

        def Popen(args, **kw):
            popened.append((args, kw.get("creationflags")))
            r = next(it)
            if isinstance(r, BaseException):
                raise r
            return r
        sub.Popen = Popen
        if run is not None:
            sub.run = run
        return sub

    def reset(job=55, assign=1, resume=0, terminate_job=1):
        log.clear()
        popened.clear()
        k.CreateJobObjectW.result, k.AssignProcessToJobObject.result = job, assign
        n.NtResumeProcess.result, k.TerminateJobObject.result = resume, terminate_job

    # no job object can be made: started plainly
    reset(job=0)
    p0 = FakeProc()
    cp.subprocess = make_sub([p0])
    got = cp.spawn(["git", "x"], stdout=1)
    check("C7 without a job object a command starts plainly", got is p0 and popened == [(["git", "x"], None)]
          and not hasattr(p0, "coderprint_job"), (popened, log))
    # joined and resumed
    reset()
    p1 = FakeProc(handle=9)
    cp.subprocess = make_sub([p1])
    got = cp.spawn(["git"], creationflags=0x200)
    check("C7 a command starts suspended in its job, joins it and is resumed",
          got is p1 and popened == [(["git"], 0x200 | cp.CREATE_SUSPENDED)] and p1.coderprint_job == 55
          and ("AssignProcessToJobObject", 55, 9) in log and ("NtResumeProcess", 9) in log
          and not any(e[0] == "CloseHandle" for e in log), (popened, log))
    # not joined: the job is closed
    reset(assign=0)
    p2 = FakeProc(handle=9)
    cp.subprocess = make_sub([p2])
    got = cp.spawn(["git"])
    check("C7 a command that cannot join its job runs without it, the job closed",
          got is p2 and not hasattr(p2, "coderprint_job") and ("CloseHandle", 55) in log, log)
    # Popen fails
    reset()
    cp.subprocess = make_sub([OSError("nope")])
    got = raised(cp.spawn, ["git"])
    check("C7 a Popen that fails closes the job and passes the error on",
          got[:2] == ("OSError", "nope") and ("CloseHandle", 55) in log, (got, log))
    # no handle: a stand-in
    reset()
    p3 = FakeProc(handle=None)
    cp.subprocess = make_sub([p3])
    got = cp.spawn(["git"])
    check("C7 a process with no handle is returned as it is, the job closed",
          got is p3 and ("CloseHandle", 55) in log and not any(e[0] == "AssignProcessToJobObject" for e in log), log)
    # resume fails: ended and started again plainly
    reset(resume=5)
    p4 = FakeProc(handle=9, wait=REAL_SUBPROCESS.TimeoutExpired("git", 5))
    p5 = FakeProc()
    cp.subprocess = make_sub([p4, p5])
    got = cp.spawn(["git"], creationflags=0x10)
    check("C7 a command that cannot be resumed is ended, its pipes closed, and started again plainly",
          got is p5 and popened == [(["git"], 0x10 | cp.CREATE_SUSPENDED), (["git"], 0x10)]
          and ("TerminateProcess", 9, 1) in log and ("CloseHandle", 55) in log
          and ("wait", cp.KILL_GRACE) in p4.calls
          and all(("close", s) in p4.calls for s in ("stdin", "stdout", "stderr")), (popened, log, p4.calls))

    # ---------------------------------------------------------------- C8
    reset()
    p6 = FakeProc()
    p6.coderprint_job = 55
    cp.kill_tree(p6)
    check("C8 kill_tree ends the job, then kills the command itself",
          ("TerminateJobObject", 55, 1) in log and p6.calls == ["kill"], (log, p6.calls))
    ran = []

    def taskkill(args, **kw):
        ran.append((args, kw.get("timeout")))
        if len(ran) > 1:
            raise REAL_SUBPROCESS.TimeoutExpired(args, 30)
    reset(terminate_job=0)
    p7 = FakeProc(poll=None)
    p7.coderprint_job = 55
    cp.subprocess = make_sub([], run=taskkill)
    cp.kill_tree(p7)
    check("C8 a job that cannot be ended: taskkill ends the process tree",
          ran == [(["taskkill", "/F", "/T", "/PID", "4242"], 30)] and p7.calls == ["poll", "kill"], (ran, p7.calls))
    p8 = FakeProc(poll=None, kill=OSError("gone"))
    got = raised(cp.kill_tree, p8)
    check("C8 a taskkill that fails and a kill of a process already gone are let be",
          got[0] == "none" and len(ran) == 2 and p8.calls == ["poll", "kill"], (got, ran))
    p9 = FakeProc(poll=0)
    ran.clear()
    cp.kill_tree(p9)
    check("C8 a process already ended needs no taskkill", ran == [] and p9.calls == ["poll", "kill"], (ran, p9.calls))

    # ---------------------------------------------------------------- C9
    cp.subprocess = REAL_SUBPROCESS
    s1 = FakeProc(communicate=REAL_SUBPROCESS.TimeoutExpired("git", 5))
    cp.settle(s1)
    check("C9 settle leaves pipes still held after KILL_GRACE to their threads",
          s1.calls == [("communicate", cp.KILL_GRACE)], s1.calls)
    s2 = FakeProc(communicate=ValueError("closed"), wait=REAL_SUBPROCESS.TimeoutExpired("git", 5))
    s2.stdout.fail = OSError("bad")
    got = raised(cp.settle, s2)
    check("C9 settle goes on past a pipe already read, a wait that times out and a close that fails",
          got[0] == "none" and s2.calls == [("communicate", cp.KILL_GRACE), ("wait", cp.KILL_GRACE),
                                            ("close", "stdout"), ("close", "stderr")], (got, s2.calls))

    # ---------------------------------------------------------------- C10
    reset()
    r1 = FakeProc()
    r1.coderprint_job = 55
    cp.release(r1)
    cp.release(r1)
    check("C10 release closes the job once", [e for e in log if e[0] == "CloseHandle"] == [("CloseHandle", 55)]
          and r1.coderprint_job is None, log)
finally:
    cp.os, cp.subprocess = REAL_OS, REAL_SUBPROCESS
    cp._WIN32 = None

s3 = FakeProc(pipes=False)
cp.settle(s3)
check("C9 settle elsewhere waits, and a process with no pipes has none to close", s3.calls == [("wait", cp.KILL_GRACE)],
      s3.calls)
r2 = FakeProc()
cp.release(r2)
check("C10 release of a process with no job does nothing", r2.calls == [])


# ======================================================================= written
def git(repo, *args, when=T0, stdin=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Owner One", GIT_AUTHOR_EMAIL=NOREPLY, GIT_COMMITTER_NAME="Owner One",
               GIT_COMMITTER_EMAIL=NOREPLY, GIT_AUTHOR_DATE="%d +0000" % when, GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                        "-c", "core.symlinks=false"] + list(args), env=env, capture_output=True, input=stdin)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace").strip()


_repos = iter(range(10 ** 6))


def build(commits, path=None):
    """commits: a list of {path: text or bytes, or None to delete}, one commit a day apart. The commits' hashes."""
    if path is None:
        path = os.path.join(ROOT, "r%d" % next(_repos))
        subprocess.run(["git", "init", "-q", "-b", "main", path], check=True, capture_output=True)
    shas = []
    for files in commits:
        for rel, data in files.items():
            p = os.path.join(path, rel)
            if data is None:
                os.remove(p)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data.encode("utf-8") if isinstance(data, str) else data)
        git(path, "add", "-A", when=T0 + len(shas) * 86400)
        git(path, "commit", "-q", "--allow-empty", "-m", "c", when=T0 + len(shas) * 86400)
        shas.append(git(path, "rev-parse", "HEAD"))
    return path, shas


def blob(repo, rev_path):
    return git(repo, "rev-parse", rev_path)


def H(*texts):
    return [cp.line_hash(t) for t in texts]


def got_of(added, key):
    v = added.get(key)
    return None if v is None else (list(v[0]), list(v[1]))


def code_keys(added):
    return {k for k in added if k not in (cp.APPROXIMATE, cp.ALIKE, cp.PAIRS)}


REAL_CAT = cp.CatFile


class DenyCat(REAL_CAT):
    """git cat-file that cannot give the blobs in DENY (all of them when DENY is None)."""
    DENY = set()

    def ask(self, name):
        if DenyCat.DENY is None or name in DenyCat.DENY:
            return None
        return REAL_CAT.ask(self, name)


@contextlib.contextmanager
def reading(deny=(), version_lines=None, trace=None, watch=()):
    """read_added_code's surroundings: blobs git cannot give, how many lines are held, a Trace, watched commits."""
    saved = cp.CatFile, cp.VERSION_LINES, cp.TRACE, set(cp.SWEEP_WATCH)
    DenyCat.DENY = None if deny is None else set(deny)
    cp.CatFile = DenyCat
    if version_lines is not None:
        cp.VERSION_LINES = version_lines
    cp.TRACE = trace
    cp.SWEEP_WATCH.clear()
    cp.SWEEP_WATCH.update(watch)
    try:
        yield
    finally:
        cp.CatFile, cp.VERSION_LINES, cp.TRACE = saved[:3]
        cp.SWEEP_WATCH.clear()
        cp.SWEEP_WATCH.update(saved[3])


# ---------------------------------------------------------------- W1
OID = b"oid sha256:" + b"ab" * 32
check("W1 an LFS pointer is one", cp.lfs_pointer([b"version https://git-lfs.github.com/spec/v1", OID, b"size 12"]))
check("W1 a pointer with a line that is no key and value is not one",
      cp.lfs_pointer([b"version https://git-lfs.github.com/spec/v1", OID, b"size 12", b"Garbage"]) is False)
check("W1 a pointer of an unknown spec, or no size, is not one",
      not cp.lfs_pointer([b"version https://example.com/spec", OID, b"size 12"])
      and not cp.lfs_pointer([b"version https://git-lfs.github.com/spec/v1", OID]))
check("W1 header_paths reads plain and quoted names", cp.header_paths("a/x b/x") == ("x", "x")
      and cp.header_paths('"a/x y" "b/x y"') == ("x y", "x y")
      and cp.header_paths('a/p q "b/r\\ts"') == ("p q", "r\ts"), cp.header_paths('a/p q "b/r\\ts"'))
check("W1 header_paths gives nothing for names it cannot split or that lack their a/ and b/",
      cp.header_paths("a/x y b/z w") == (None, None) and cp.header_paths('"x/a" "y/b"') == (None, None)
      and cp.header_paths("c/x d/x") == (None, None))
saved_version = list(cp.GIT_VERSION)
cp.GIT_VERSION.clear()
cp.run = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("git could not be started"))
v = cp.git_version()
cp.run = lambda *a, **k: b"git version 2.45.1.windows.1\n"
v2 = (cp.git_version(), cp.git_version())
cp.run = lambda *a, **k: b"no version\n"
cp.GIT_VERSION.clear()
v3 = cp.git_version()
cp.run = real_run
cp.GIT_VERSION[:] = saved_version
check("W1 git_version is (0,) when git cannot run, and that is not kept", v == (0,) and v2[0] == (2, 45), (v, v2))
check("W1 git_version is (0,) for an answer naming no version", v3 == (0,), v3)
check("W1 git_version is read once", v2[1] == (2, 45), v2)

# ---------------------------------------------------------------- W2, W3
PS1 = "﻿$a = 1\n# c\n$b = 2\n".encode("utf-16-le")
repo, shas = build([{"a.py": "x = 1\n# note\ny = 2\n", "README.txt": "hi\n", "s.ps1": PS1},
                    {"a.py": "x = 1\ny = 3\nz = 4\n"},
                    {"a.py": None, "README.txt": None, "s.ps1": None}])
with reading():
    added = cp.read_added_code(repo)
A1, A2, S1 = blob(repo, shas[0] + ":a.py"), blob(repo, shas[1] + ":a.py"), blob(repo, shas[0] + ":s.ps1")
check("W2 a new file's lines of code are added, its comment left out",
      got_of(added, (shas[0], A1)) == (H("x = 1", "y = 2"), []), got_of(added, (shas[0], A1)))
check("W2 an edit adds its new lines and removes its old ones",
      got_of(added, (shas[1], A2)) == (H("y = 3", "z = 4"), H("y = 2")), got_of(added, (shas[1], A2)))
check("W2 a UTF-16 file git calls binary is read as text", got_of(added, (shas[0], S1)) == (H("$a = 1", "$b = 2"), []),
      got_of(added, (shas[0], S1)))
check("W3 deleted files' lines of code are pooled under DELETED, a UTF-16 one read whole and a text file left out",
      got_of(added, (shas[2], cp.DELETED)) == ([], H("x = 1", "y = 3", "z = 4", "$a = 1", "$b = 2")),
      got_of(added, (shas[2], cp.DELETED)))
check("W2 nothing is approximate, and no commit was watched", added[cp.APPROXIMATE] == {} and added[cp.ALIKE] == {}
      and added[cp.PAIRS] == {} and code_keys(added) == {(shas[0], A1), (shas[1], A2), (shas[0], S1),
                                                         (shas[2], cp.DELETED)}, sorted(code_keys(added)))
tr = cp.Trace()
with reading(trace=tr):
    added_t = cp.read_added_code(repo)
check("W3 traced, the same lines are read", all(got_of(added_t, k) == got_of(added, k) for k in code_keys(added)))
check("W3 traced, the deleted lines carry the origins their versions gave them",
      list(tr.gone[(shas[2], cp.DELETED)]) == [tr.base[(shas[0], A1)], tr.base[(shas[1], A2)],
                                               tr.base[(shas[1], A2)] + 1, tr.base[(shas[0], S1)],
                                               tr.base[(shas[0], S1)] + 1], list(tr.gone[(shas[2], cp.DELETED)]))

LFS = "version https://git-lfs.github.com/spec/v1\noid sha256:%s\nsize 12\n" % ("ab" * 32)
repo, shas = build([{"a.py": "x = 1\n# note\ny = 2\n", "lfs.py": LFS, "b.py": "b = 1\n"},
                    {"a.py": None, "lfs.py": None}])
tr = cp.Trace()
with reading(deny=None, version_lines=0, trace=tr):
    added = cp.read_added_code(repo)
check("W3 a deleted file no git can give is read from its diff's lines, a pointer's lines none",
      got_of(added, (shas[1], cp.DELETED)) == ([], H("x = 1", "y = 2")), got_of(added, (shas[1], cp.DELETED)))
check("W3 traced, those lines have no known origins", list(tr.gone[(shas[1], cp.DELETED)]) == [0, 0],
      tr.gone.get((shas[1], cp.DELETED)))

# ---------------------------------------------------------------- W4
repo, shas = build([{"a.py": "x = 1\n# note\ny = 2\n", "b.py": "b = 1\n"},
                    {"a.py": "x = 9\n# note\ny = 3\nz = 4\n"}])
A1, A2 = blob(repo, shas[0] + ":a.py"), blob(repo, shas[1] + ":a.py")
KEY = (shas[1], A2)
with reading(deny={A1}, version_lines=0, watch={shas[1]}):
    added = cp.read_added_code(repo)
check("W4 a version whose old version cannot be had is read whole: its hunks' lines added and removed",
      got_of(added, KEY) == (H("x = 9", "y = 3", "z = 4"), H("x = 1", "y = 2")), got_of(added, KEY))
check("W4 read whole by the exact reader, it is not approximate", KEY not in added[cp.APPROXIMATE],
      added[cp.APPROXIMATE])
check("W4 a watched commit's changed lines are paired, hunk by hunk",
      KEY in added[cp.ALIKE] and KEY in added[cp.PAIRS] and 0 <= added[cp.ALIKE][KEY] <= 1,
      (added[cp.ALIKE], added[cp.PAIRS]))
alike_whole = added[cp.ALIKE].get(KEY)
with reading(deny=None, version_lines=0, watch={shas[1]}):
    added = cp.read_added_code(repo)
check("W4 when neither version can be had each hunk is read alone, the same lines",
      got_of(added, KEY) == (H("x = 9", "y = 3", "z = 4"), H("x = 1", "y = 2")), got_of(added, KEY))
check("W4 and its added lines are counted approximate", added[cp.APPROXIMATE].get(KEY) == 3, added[cp.APPROXIMATE])
check("W4 read alone, a watched commit's hunks pair alike", added[cp.ALIKE].get(KEY) == alike_whole,
      (added[cp.ALIKE], alike_whole))
repo, shas = build([{"gen.py": "x = 0\n", "b.py": "b = 1\n"},
                    {"gen.py": "# Code generated by protoc. DO NOT EDIT.\nx = 1\n"}])
G2 = blob(repo, shas[1] + ":gen.py")
with reading(deny=None, version_lines=0):
    added = cp.read_added_code(repo)
check("W4 a generator's mark in a hunk read alone marks the file generated",
      added.get((shas[1], G2)) == cp.GENERATED_VERSION, added.get((shas[1], G2)))

# ---------------------------------------------------------------- W5
PS1B = "﻿$a = 1\n# c\n$b = 2\n$c = 3\n".encode("utf-16-le")
repo, shas = build([{"s.ps1": PS1, "bin.py": b"x = 1\x00\n"},
                    {"s.ps1": PS1B, "bin.py": b"x = 2\x00\n"}])
S1, S2, B1 = blob(repo, shas[0] + ":s.ps1"), blob(repo, shas[1] + ":s.ps1"), blob(repo, shas[0] + ":bin.py")
with reading(watch={shas[1]}):
    added = cp.read_added_code(repo)
check("W5 a binary file that is not text adds nothing", code_keys(added) == {(shas[0], S1), (shas[1], S2)},
      sorted(code_keys(added)))
check("W5 a UTF-16 file edited is diffed line for line", got_of(added, (shas[1], S2)) == (H("$c = 3"), []),
      got_of(added, (shas[1], S2)))
check("W5 a watched UTF-16 edit is paired", added[cp.PAIRS].get((shas[1], S2)) is not None
      and added[cp.ALIKE].get((shas[1], S2)) == 0.0, (added[cp.ALIKE], added[cp.PAIRS]))
tr = cp.Trace()
with reading(deny={S1}, trace=tr):
    added = cp.read_added_code(repo)
check("W5 a UTF-16 edit whose old version cannot be had adds all its lines of code",
      got_of(added, (shas[1], S2)) == (H("$a = 1", "$b = 2", "$c = 3"), []), got_of(added, (shas[1], S2)))
check("W5 traced, its lines' origins are new, kept apart for a version no Version holds",
      list(tr.extra.get(S2, [])) == [tr.base[(shas[1], S2)], cp.OTHER_ORIGIN, tr.base[(shas[1], S2)] + 1,
                                        tr.base[(shas[1], S2)] + 2], list(tr.extra.get(S2, [])))


class BadTrace(cp.Trace):
    __slots__ = ()

    def allot(self, key, n):
        raise ValueError("cannot follow")


tr = BadTrace()
with reading(trace=tr):
    added = cp.read_added_code(repo)
check("W5 a trace that fails is broken, and the diffs still count",
      tr.broken and got_of(added, (shas[1], S2)) == (H("$c = 3"), []), (tr.broken, got_of(added, (shas[1], S2))))

# ---------------------------------------------------------------- W6
repo, shas = build([{"a.py": "a = 1\nb = 2\nc = 3\nd = 4\ne = 5\n", "b.py": "b = 1\n", "bin.py": b"x\x00\n"}])
git(repo, "checkout", "-q", "-b", "side")
_, side = build([{"a.py": "a = 10\nb = 2\nc = 3\nd = 4\ne = 5\n", "b.py": "b = 2\n", "bin.py": b"y\x00\n"}], repo)
git(repo, "checkout", "-q", "main")
_, main2 = build([{"a.py": "a = 1\nb = 2\nc = 3\nd = 4\ne = 50\n"}], repo)
git(repo, "merge", "-q", "--no-edit", "side", when=T0 + 5 * 86400)
merge = git(repo, "rev-parse", "HEAD")
AM, AS, AMAIN = blob(repo, "HEAD:a.py"), blob(repo, side[0] + ":a.py"), blob(repo, main2[0] + ":a.py")
with reading():
    added = cp.read_added_code(repo)
check("W6 a merge adds no lines of its own",
      not any(k[0] == merge for k in code_keys(added)) and got_of(added, (side[0], AS)) == (H("a = 10"), H("a = 1"))
      and got_of(added, (main2[0], AMAIN)) == (H("e = 50"), H("e = 5")), sorted(code_keys(added)))
tr = cp.Trace()
with reading(trace=tr):
    added = cp.read_added_code(repo)
first = tr.base[(shas[0], blob(repo, shas[0] + ":a.py"))]
check("W6 traced, the merge's version takes each line's origin from the parent that wrote it",
      list(tr.heads.get(AM) or []) == [tr.base[(side[0], AS)], first + 1, first + 2, first + 3,
                                       tr.base[(main2[0], AMAIN)]], (list(tr.heads.get(AM) or []), tr.base))
tr = cp.Trace()
with reading(trace=tr, version_lines=0):
    added = cp.read_added_code(repo)
check("W6 a merge whose first parent's version is no longer held keeps nothing, and still adds nothing",
      not any(k[0] == merge for k in code_keys(added)) and not tr.broken, sorted(code_keys(added)))


class BadMergeTrace(cp.Trace):
    __slots__ = ()

    def keep(self, blob, origins):
        if blob == AM:
            raise ValueError("cannot follow")
        cp.Trace.keep(self, blob, origins)


tr = BadMergeTrace()
with reading(trace=tr):
    added = cp.read_added_code(repo)
check("W6 a merge tracing cannot follow breaks the trace, and the diffs still count",
      tr.broken and got_of(added, (side[0], AS)) == (H("a = 10"), H("a = 1")), tr.broken)

# ---------------------------------------------------------------- W7
real_run = cp.run


def run_failing(exc):
    def run(args, *a, **k):
        if "ls-tree" in args:
            raise exc
        return real_run(args, *a, **k)
    return run


cp.run = run_failing(cp.OutOfTime("git was not started: the run is out of time"))
with reading(trace=cp.Trace()):
    got = raised(cp.read_added_code, repo)
cp.run = run_failing(RuntimeError("git exited 128"))
tr = cp.Trace()
with reading(trace=tr):
    got2 = raised(cp.read_added_code, repo)
cp.run = real_run
check("W7 traced, running out of time listing the head stops the reading",
      got[:2] == ("OutOfTime", "git was not started: the run is out of time"), got)
check("W7 traced, a head git cannot list holds nothing, and the history is still read",
      got2[0] == "none" and tr.heads == {} and tr.base, (got2[:2], tr.heads))
empty = os.path.join(ROOT, "empty")
subprocess.run(["git", "init", "-q", "-b", "main", empty], check=True, capture_output=True)
tr = cp.Trace()
with reading(trace=tr):
    got = raised(cp.read_added_code, empty)
check("W7 an empty repository, traced, is read as nothing",
      got[:2] == ("none", "{'approximate': {}, 'alike': {}, 'pairs': {}}") and tr.heads == {}, got[:2])

# ---------------------------------------------------------------- W8
check("W8 attributed of no paths is an empty set, git not run", cp.attributed("/nonexistent", "HEAD", ["", None]) == set())
repo, shas = build([{"src/a.py": "a = 1\n", "gen/x.py": "x = 1\n"},
                    {".gitattributes": "gen/* linguist-generated\ndocs/* linguist-documentation=false\n",
                     "gen/x.py": "x = 2\n", "docs/d.py": "d = 1\n"},
                    {"gen/x.py": "x = 3\n", "src/a.py": "a = 2\n"},
                    {".gitattributes": "docs/* linguist-documentation\n", "gen/x.py": "x = 4\n", "docs/d.py": "d = 2\n"}])
check("W8 attributed gives the paths a commit's attributes mark, not one marked false",
      cp.attributed(repo, shas[1], ["gen/x.py", "docs/d.py", "src/a.py"]) == {"gen/x.py"})
check("W8 attributed is None when git cannot say", cp.attributed(repo, "nosuchref", ["gen/x.py"]) is None)
NS = types.SimpleNamespace
commits = [NS(sha=s, files=[NS(path=p) for p in ("src/a.py", "gen/x.py", "docs/d.py")]) for s in shas]
got = cp.attributed_versions(repo, commits)
check("W8 attributed_versions judges each commit by the attributes it held",
      got == {(shas[1], "gen/x.py"), (shas[2], "gen/x.py"), (shas[3], "docs/d.py")}, got)
check("W8 attributed_versions is None outside a repository",
      cp.attributed_versions(os.path.join(ROOT, "nowhere"), commits) is None)
real_attributed, real_git_lines = cp.attributed, cp.git_lines
cp.attributed = lambda *a: None
got = cp.attributed_versions(repo, commits)
cp.attributed = real_attributed


def git_lines_failing(args, handle, feed=None, env=None):
    if "diff-tree" in args:
        raise RuntimeError("git exited 128")
    return real_git_lines(args, handle, feed=feed, env=env)


cp.git_lines = git_lines_failing
got2 = cp.attributed_versions(repo, commits)
cp.git_lines = real_git_lines
check("W8 attributed_versions is None when a commit's attributes cannot be read", got is None, got)
check("W8 attributed_versions is None when the commits that changed them cannot be told", got2 is None, got2)
repo, shas = build([{"a.py": "a = 1\n"}, {".gitattributes": "*.py text eol=lf\n", "a.py": "a = 2\n"}])
commits = [NS(sha=s, files=[NS(path="a.py")]) for s in shas]
check("W8 attributes that never mention linguist mark nothing", cp.attributed_versions(repo, commits) == set())
repo, shas = build([{"a.py": "a = 1\n"}])
check("W8 a repository with no .gitattributes marks nothing", cp.attributed_versions(repo, commits[:1]) == set())

# ---------------------------------------------------------------- W9: paths, renames, links, line ends, Standing
check("W9 diff_path drops the prefix and the tab after a name holding a space, and reads quoted names",
      (cp.diff_path("b/x y.py\t", "b/"), cp.diff_path("/dev/null", "a/"), cp.diff_path('"b/\\303\\251.py"', "b/"),
       cp.diff_path("c/x.py", "b/")) == ("x y.py", None, "é.py", "c/x.py"),
      (cp.diff_path("b/x y.py\t", "b/"), cp.diff_path('"b/\\303\\251.py"', "b/")))
BODY = "".join("v%d = %d\n" % (i, i) for i in range(12))
repo, shas = build([{"old.py": BODY, "end.py": "x = 1"}])
os.remove(os.path.join(repo, "old.py"))
with open(os.path.join(repo, "new.py"), "w") as fh:
    fh.write(BODY + "w = 99\n")
os.symlink("new.py", os.path.join(repo, "link.py"))
_, more = build([{"end.py": "x = 1\ny = 2\n"}], repo)
N2, E2 = blob(repo, more[0] + ":new.py"), blob(repo, more[0] + ":end.py")
for traced in (False, True):
    for deny in ((), {blob(repo, shas[0] + ":end.py")}):
        tr = cp.Trace() if traced else None
        with reading(trace=tr, deny=deny, version_lines=0 if deny else None):
            added = cp.read_added_code(repo)
        how = "%s%s" % ("traced, " if traced else "", "old version denied" if deny else "old version at hand")
        check("W9 (%s) a renamed file adds only what its edit added" % how,
              got_of(added, (more[0], N2)) == (H("w = 99"), []), got_of(added, (more[0], N2)))
        check("W9 (%s) a symbolic link adds nothing" % how,
              {k for k in code_keys(added) if k[0] == more[0]} == {(more[0], N2), (more[0], E2)},
              sorted(code_keys(added)))
        check("W9 (%s) a last line that only gains its line end is neither added nor removed" % how,
              got_of(added, (more[0], E2)) == (H("y = 2"), []), got_of(added, (more[0], E2)))
        if traced and not deny:
            check("W9 (%s) the kept last line keeps its origin, the new one a new id" % how,
                  list(tr.heads.get(E2) or []) == [tr.base[(shas[0], blob(repo, shas[0] + ":end.py"))],
                                                   tr.base[(more[0], E2)]], list(tr.heads.get(E2) or []))
with reading(deny=None, version_lines=0):   # no version at all: each hunk read alone (hunk_lines)
    added = cp.read_added_code(repo)
check("W9 (hunks read alone) a last line that only gains its line end is neither added nor removed",
      got_of(added, (more[0], E2)) == (H("y = 2"), []), got_of(added, (more[0], E2)))
st = cp.Standing()
st.add([(11, False), (12, True)], False, path="a.py")
st.add([(11, False)], True, origins=cp.array("q", [7]))
st.add([(13, True)], False, origins=cp.array("q", [1, 2]), path="b.py")
check("W9 Standing holds each line, its test flag, roughness, origin and file",
      (len(st), list(st.hashes), list(st.tests), list(st.rough), list(st.origins), st.files) ==
      (4, [11, 12, 11, 13], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 7, 0], [("a.py", 0, 2), ("b.py", 3, 4)]),
      (list(st.origins), st.files))
check("W9 Standing.items counts lines as a Counter of (hash, test) would",
      dict(st.items()) == {(11, False): 2, (12, True): 1, (13, True): 1}, dict(st.items()))

shutil.rmtree(ROOT, ignore_errors=True)
print("%d passed, %d failed" % (passes, len(fails)))
sys.exit(1 if fails else 0)
