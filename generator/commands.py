# coderprint's running commands, gh and its GraphQL queries, within the run's time limit. coderprint.py runs this
# file as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported
# on its own.


def say(msg):
    print(msg, flush=True)


def truthy(name):
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


class OutOfTime(RuntimeError):
    """The run's deadline (see time_limit) left no time to start a command, or cut one short. A repository that
    cannot be read in time is left out and counted, but running out of time is never a reason to count differently:
    what would have told the owner's code from others' is not guessed at."""


class Failed(RuntimeError):
    """A command that exited with an error. output holds what it printed, which for gh is GitHub's answer even when
    that answer carries errors; like the message it is never printed, since it can name a private repository."""

    def __init__(self, message, output=b""):
        RuntimeError.__init__(self, message)
        self.output = output


def time_left(reserve=None):
    """How long a command may still run under the run's deadline (see time_limit): what is left less reserve
    (RESERVE unless given), or None without a deadline. Fails as OutOfTime when that is under five seconds."""
    if DEADLINE is None:
        return None
    left = DEADLINE - time.monotonic() - (RESERVE if reserve is None else reserve)
    if left < 5:
        raise OutOfTime("the run is out of time")
    return int(left)


def run(args, cwd=None, env=None, timeout=TIMEOUT, reserve=None):
    """Run a command. Failures carry only the program's name: argv can hold a clone URL, which would
    name a private repository in a public log, so no exception that carries argv leaves here. Under a
    deadline (see time_limit) a command gets no longer than the run has left, less reserve (RESERVE unless
    given), and one the deadline cuts short fails as OutOfTime. A command that runs past its time is ended with
    everything it started (kill_tree)."""
    what = os.path.basename(args[0])
    try:
        left = time_left(reserve)
    except OutOfTime:
        raise OutOfTime("%s was not started: the run is out of time" % what) from None
    cut = left is not None and (timeout is None or left < timeout)
    if cut:
        timeout = left
    try:
        p = spawn(args, cwd=cwd, env=child_env(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        raise RuntimeError("%s could not be started" % what) from None
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(p)
        settle(p)
        if cut:
            raise OutOfTime("%s timed out after %d seconds: the run is out of time" % (what, timeout)) from None
        raise RuntimeError("%s timed out after %d seconds" % (what, timeout)) from None
    except BaseException:   # the step's time limit (Stopped) or an interrupt: nothing is left running
        kill_tree(p)
        settle(p)
        raise
    finally:
        release(p)
    if p.returncode != 0:
        raise Failed("%s exited %d" % (what, p.returncode), out)
    return out


# How a command is ended with everything it started. On Windows a killed program's children live on and keep
# its output pipes: git-remote-https under a clone, and the real git under Git for Windows' cmd\git.exe, which
# PowerShell and cmd find first. Reading to the end, or waiting for the pipes as subprocess.run does after a
# timeout, would then outlast any limit. So each command starts suspended inside a job object of its own, joined
# before it runs a single instruction, and ending the job ends every process it holds, even one whose parent has
# already exited. Where a job cannot be made, the command starts as it always did and is ended by its process tree
# (taskkill /T), which finds what its live processes started; and a pipe that something still holds after that is
# waited on for KILL_GRACE seconds at most. Elsewhere a command is killed as subprocess.run kills it.
CREATE_SUSPENDED = 0x00000004
KILL_GRACE = 5
_WIN32 = None


def win32():
    """kernel32's job object calls and ntdll's NtResumeProcess, set up once; False where they cannot be had."""
    global _WIN32
    if _WIN32 is None:
        _WIN32 = False
        if os.name == "nt":
            try:
                import ctypes
                from ctypes import wintypes
                k = ctypes.WinDLL("kernel32", use_last_error=True)
                n = ctypes.WinDLL("ntdll")
                for fn, args, res in ((k.CreateJobObjectW, [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
                                      (k.AssignProcessToJobObject, [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
                                      (k.TerminateJobObject, [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
                                      (k.TerminateProcess, [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
                                      (k.CloseHandle, [wintypes.HANDLE], wintypes.BOOL),
                                      (n.NtResumeProcess, [wintypes.HANDLE], ctypes.c_long)):
                    fn.argtypes, fn.restype = args, res
                _WIN32 = (k, n)
            except Exception:   # no ctypes, or a Windows without these calls: the process tree instead
                _WIN32 = False
    return _WIN32


def spawn(args, **popen):
    """subprocess.Popen, and on Windows inside a job object of its own (see above), kept as the process's
    coderprint_job for kill_tree and release. A command that cannot be resumed after joining is ended before it
    ran and started again the plain way."""
    api = win32() if os.name == "nt" else False
    job = api[0].CreateJobObjectW(None, None) if api else None
    if not job:
        return subprocess.Popen(args, **popen)
    kernel, ntdll = api
    flags = popen.pop("creationflags", 0)
    try:
        proc = subprocess.Popen(args, creationflags=flags | CREATE_SUSPENDED, **popen)
    except BaseException:
        kernel.CloseHandle(job)
        raise
    handle = getattr(proc, "_handle", None)
    if handle is None:   # not a process this module can reach (a stand-in for Popen): nothing to join or resume
        kernel.CloseHandle(job)
        return proc
    handle = int(handle)
    joined = bool(kernel.AssignProcessToJobObject(job, handle))
    if ntdll.NtResumeProcess(handle) != 0:   # still suspended: it has run nothing, so start it again
        kernel.TerminateProcess(handle, 1)
        try:
            proc.wait(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            pass
        for pipe in (proc.stdin, proc.stdout, proc.stderr):
            if pipe:
                pipe.close()
        kernel.CloseHandle(job)
        return subprocess.Popen(args, creationflags=flags, **popen)
    if joined:
        proc.coderprint_job = job
    else:
        kernel.CloseHandle(job)
    return proc


def kill_tree(proc):
    """End a command and everything it started: its job object on Windows, or failing that its process tree; and
    the command itself, as subprocess.run does."""
    job = getattr(proc, "coderprint_job", None)
    ended = bool(job and win32() and win32()[0].TerminateJobObject(job, 1))
    if not ended and os.name == "nt" and proc.poll() is None:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def settle(proc):
    """After kill_tree: wait for the command, and on Windows for its output pipes, whose reader threads end once
    nothing holds them. A pipe still held after KILL_GRACE seconds is left open for its thread to finish with, since
    closing it would wait as long; elsewhere the pipes are closed, as subprocess.run closes them."""
    if os.name == "nt":
        try:
            proc.communicate(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            return
        except (OSError, ValueError):
            pass
    try:
        proc.wait(timeout=KILL_GRACE)
    except subprocess.TimeoutExpired:
        pass
    for pipe in (proc.stdout, proc.stderr):
        if pipe:
            try:
                pipe.close()
            except OSError:
                pass


def release(proc):
    """Close a command's job object once it is done with (its processes are not ended by that)."""
    job = getattr(proc, "coderprint_job", None)
    if job and win32():
        win32()[0].CloseHandle(job)
        proc.coderprint_job = None


def graphql_args(query, variables):
    args = ["gh", "api", "graphql", "-f", "query=" + query]
    for k, v in variables.items():
        args += ["-f", "%s=%s" % (k, v)]
    return args


def graphql_answer(out):
    """gh's output as GitHub's answer, {"data": {...}, "errors": [...]}. An answer whose data is missing or null, as
    GitHub gives when a query fails as a whole, fails here."""
    data = json.loads(out.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("data"), dict):
        raise RuntimeError("the GitHub API returned no data")
    return data


def gql(query, timeout=TIMEOUT, errors=None, reserve=None, **variables):
    """GitHub's answer to a query, its data. An answer that carries errors fails, as gh exits 1 on it, unless errors
    is a list: the answer is then taken, since gh prints it all the same, and its errors are added to the list. A
    field an error names, such as one the token may not see, is null in the data. Fails when there is no data.
    reserve: the time kept back from the deadline, as run() takes it, RESERVE unless given."""
    args = graphql_args(query, variables)
    more = {} if reserve is None else {"reserve": reserve}
    if errors is None:
        return graphql_answer(run(args, env=github_env(), timeout=timeout, **more))["data"]
    try:
        out = run(args, env=github_env(), timeout=timeout, **more)
    except Failed as e:
        out = e.output
    answer = graphql_answer(out)
    found = answer.get("errors") or []
    errors.extend(found if isinstance(found, list) else [found])
    return answer["data"]


def answered(query, **variables):
    """GitHub's answer to a query as (data, errors), taking an answer that carries errors beside its data (see gql)."""
    errors = []
    return gql(query, errors=errors, **variables), errors


def again(ask):
    """ask(), and once more if it fails, as a repository is read: a lookup that tells the owner's code from others'
    is worth a second try before the run gives up on it. Running out of time is not tried again."""
    try:
        return ask()
    except OutOfTime:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return ask()
