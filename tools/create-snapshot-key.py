"""Create or reuse a local organization snapshot key and configure profile secrets.

Copyright 2026 Peter Shiller. PolyForm Noncommercial License 1.0.0; see
LICENSE.md and NOTICE.md. The key stays outside Git checkouts and never appears
in command arguments or output.
"""

import argparse
import base64
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


LOGIN = re.compile(r"[A-Za-z0-9-]{1,39}\Z")
REPOSITORY = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
ROOT = Path(__file__).resolve().parents[1]


def repository(value):
    parts = value.split("/")
    if (len(parts) != 2 or not LOGIN.fullmatch(parts[0])
            or not REPOSITORY.fullmatch(parts[1]) or parts[1] in (".", "..")):
        raise argparse.ArgumentTypeError("expected a GitHub OWNER/REPO name")
    return parts


def clean_environment():
    env = dict(os.environ)
    for name in list(env):
        if (name.startswith(("CARDS_", "GIT_")) or name in (
                "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
                "GH_HOST", "GITHUB_HOST", "GH_REPO", "GH_DEBUG", "GITHUB_REPOSITORY")):
            env.pop(name, None)
    env["GH_PROMPT_DISABLED"] = "1"
    env["LC_ALL"] = "C"
    return env


def command(args, deadline, *, env, input_bytes=None, cwd=None, check=True):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise RuntimeError("the setup deadline expired")
    try:
        result = subprocess.run(args, input=input_bytes, cwd=cwd, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=min(30, remaining), check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError("a bounded local GitHub check failed") from None
    if check and result.returncode:
        raise RuntimeError("a bounded local GitHub check failed")
    return result


def outside_git(location, deadline, env):
    result = command(["git", "-C", str(location), "rev-parse", "--absolute-git-dir"],
                     deadline, env=env, check=False)
    if result.returncode == 0:
        raise RuntimeError("the key must be stored outside Git checkouts")
    if result.returncode != 128 or b"not a git repository" not in result.stderr.lower():
        raise RuntimeError("the key location could not be verified")


def key_path(value, deadline, env, *, reuse=False):
    path = Path(os.path.abspath(value))
    parent = path.parent
    # Resolve before and after creation so an existing symlink or Windows
    # junction cannot direct the key into a checkout or a different directory.
    for ancestor in (path, *path.parents):
        if ancestor.exists() and (ancestor.is_symlink() or
                                  (hasattr(os.path, "isjunction") and os.path.isjunction(ancestor))):
            raise RuntimeError("the key path must not contain a link")
    if os.path.normcase(str(path)) != os.path.normcase(os.path.realpath(path)):
        raise RuntimeError("the key path must not contain a link")
    existing = parent
    missing = []
    while not existing.exists():
        if existing == existing.parent:
            raise RuntimeError("the key location could not be verified")
        missing.append(existing)
        existing = existing.parent
    outside_git(existing, deadline, env)
    if reuse and not parent.is_dir():
        raise RuntimeError("the existing key file is unavailable")
    if not reuse:
        for directory in reversed(missing):
            directory.mkdir(mode=0o700)
    if not parent.is_dir() or os.path.normcase(str(path)) != os.path.normcase(os.path.realpath(path)):
        raise RuntimeError("the key path must be a real directory")
    for ancestor in (path, *path.parents):
        if ancestor.exists() and (ancestor.is_symlink() or
                                  (hasattr(os.path, "isjunction") and os.path.isjunction(ancestor))):
            raise RuntimeError("the key path must not contain a link")
    # Git discovers worktrees in ancestors, including linked worktrees whose
    # .git entry is a file. Keep private key material out of every such tree.
    outside_git(parent, deadline, env)
    return path


def protect_windows(raw):
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]

    source = ctypes.create_string_buffer(raw)
    incoming = Blob(len(raw), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    api = ctypes.windll.crypt32
    api.CryptProtectData.argtypes = [ctypes.POINTER(Blob), ctypes.c_wchar_p,
                                    ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                                    wintypes.DWORD, ctypes.POINTER(Blob)]
    api.CryptProtectData.restype = wintypes.BOOL
    if not api.CryptProtectData(ctypes.byref(incoming), None, None, None, None,
                                1, ctypes.byref(outgoing)):
        raise RuntimeError("the local key could not be protected")
    try:
        return b"DPAPI1\n" + ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(outgoing.data, ctypes.c_void_p))


def load_key(path):
    spec = importlib.util.spec_from_file_location("coderprint_blended_key", ROOT / "tools" / "refresh-blended.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.key_text(path)


def create_key(path):
    raw = os.urandom(32)
    data = protect_windows(raw) if os.name == "nt" else base64.b64encode(raw) + b"\n"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RuntimeError("the key already exists; pass --reuse to keep it") from None
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != "nt":
            os.chmod(path, 0o600)
        return load_key(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def api_repo(name, deadline, env):
    result = command(["gh", "api", "repos/" + "/".join(name)], deadline, env=env)
    try:
        return json.loads(result.stdout)
    except (ValueError, UnicodeError):
        raise RuntimeError("the GitHub repository could not be verified") from None


def setup(args):
    deadline = time.monotonic() + args.time_limit
    env = clean_environment()
    owner = args.profile[0]
    if args.profile[0].lower() != args.profile[1].lower():
        raise RuntimeError("the profile must be OWNER/OWNER")
    if args.snapshot_store[0].lower() != owner.lower() or args.snapshot_store[1].lower() == owner.lower():
        raise RuntimeError("the snapshot store must be a separate personally owned repository")
    viewer = command(["gh", "api", "user"], deadline, env=env)
    try:
        login = json.loads(viewer.stdout)["login"]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("the local GitHub login could not be verified") from None
    if not isinstance(login, str) or login.lower() != owner.lower():
        raise RuntimeError("the local GitHub login must match the profile owner")
    profile = api_repo(args.profile, deadline, env)
    store = api_repo(args.snapshot_store, deadline, env)
    if (profile.get("owner", {}).get("login", "").lower() != owner.lower()
            or profile.get("name", "").lower() != owner.lower()
            or store.get("owner", {}).get("login", "").lower() != owner.lower()
            or store.get("name", "").lower() != args.snapshot_store[1].lower()
            or store.get("private") is not True):
        raise RuntimeError("the profile or private snapshot store could not be verified")
    path = key_path(args.key_file, deadline, env, reuse=args.reuse)
    if args.reuse:
        key = load_key(path)
    else:
        key = create_key(path)
    # Configure the store first; the encryption key is the last secret set.
    # An interrupted setup can be retried with --reuse without changing it.
    profile_name = "/".join(args.profile)
    command(["gh", "secret", "set", "CODERPRINT_ORGANIZATION_SNAPSHOT_REPOSITORY",
             "--repo", profile_name], deadline, env=env,
            input_bytes="/".join(args.snapshot_store).encode("ascii"))
    command(["gh", "secret", "set", "CODERPRINT_ORGANIZATION_SNAPSHOT_KEY",
             "--repo", profile_name], deadline, env=env, input_bytes=key.encode("ascii"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", required=True)
    parser.add_argument("--profile", required=True, type=repository)
    parser.add_argument("--snapshot-store", required=True, type=repository)
    parser.add_argument("--time-limit", required=True, type=int)
    parser.add_argument("--reuse", action="store_true")
    args = parser.parse_args()
    if not 30 <= args.time_limit <= 120:
        parser.error("time-limit must be 30 to 120 seconds")
    try:
        setup(args)
    except Exception:
        print("Snapshot key setup could not complete. Keep any local key and retry with --reuse.",
              file=sys.stderr)
        return 1
    print("Snapshot key and private store are configured for the profile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
