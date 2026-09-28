#!/usr/bin/env python3
"""Measure collection on an existing public Git clone, with network identity lookups stubbed.

This exercises real history as an organization (all authors), not live account attribution.
Run under an external process-tree deadline. The collection also has its own deadline.
"""
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=60).decode().strip()


def peak_memory():
    if os.name != "nt":
        import resource
        import sys
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak if sys.platform == "darwin" else peak * 1024
    class Memory(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in (
                "peak_working_set", "working_set", "peak_paged", "paged",
                "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]
    memory = Memory()
    memory.cb = ctypes.sizeof(memory)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Memory), ctypes.c_ulong]
    query.restype = ctypes.c_int
    if not query(kernel.GetCurrentProcess(), ctypes.byref(memory), memory.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return memory.peak_working_set


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("implementation", type=Path)
    parser.add_argument("repository", type=Path)
    parser.add_argument("--seconds", type=int, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 86400:
        parser.error("--seconds must be between 1 and 86400")
    args.work.mkdir(parents=True, exist_ok=True)
    repo = args.repository.resolve()
    source = args.implementation.resolve()
    identity = {
        "implementation_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "repository_head": git(repo, "rev-parse", "HEAD"),
        "repository_commits": int(git(repo, "rev-list", "--count", "--all")),
        "identity_mode": "offline organization; all authors eligible",
        "deadline_seconds": args.seconds,
    }
    print(json.dumps(identity), flush=True)
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "CLONE_CACHE", "CARDS_AUTHOR_EMAILS"):
        os.environ.pop(name, None)
    spec = importlib.util.spec_from_file_location("benchmark_coderprint", source)
    cp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cp)
    cp.clone = lambda owner, name, dest: subprocess.run(
        ["git", "clone", "--quiet", "--bare", "--shared", str(repo), dest],
        check=True, capture_output=True, timeout=60)
    cp.owner_identity = lambda owner: {"user": False, "id": None, "name": ""}
    cp.templates = lambda owner: {}
    cp.seed_blobs = lambda full_name, dest: set()
    cp.resolve_authors = lambda owner, samples: {}
    cp.DEADLINE = time.monotonic() + args.seconds
    work = tempfile.mkdtemp(prefix="collection-", dir=args.work.resolve())
    started = time.perf_counter()
    data = cp.collect("benchmark", [{"name": "public-history", "isPrivate": False}], work)
    code = data["code"]
    result = dict(identity, elapsed_seconds=round(time.perf_counter() - started, 3),
                  peak_process_memory_bytes=peak_memory(),
                  written_loc=sum(n for _, _, n in data["events"]),
                  counted_commits=len(data["commits"]),
                  production_loc=code.get("production"), tests_loc=code.get("tests"),
                  traced_loc=code.get("traced"), matched_loc=code.get("matched"),
                  diagnostics={k: data.get(k) for k in ("unread", "unchecked", "unsure", "unparsed")},
                  code_diagnostics={k: code.get(k) for k in ("unread", "heads_unread", "attributes_unread")})
    total = (result["production_loc"] or 0) + (result["tests_loc"] or 0)
    result["in_use_within_written"] = total <= result["written_loc"]
    result["trace_partition_matches"] = (result["traced_loc"] is None or
                                          total == result["traced_loc"] + result["matched_loc"])
    rendered = json.dumps(result, indent=2, default=lambda value: sorted(value))
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered, flush=True)
    if not result["in_use_within_written"] or not result["trace_partition_matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
