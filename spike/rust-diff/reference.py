#!/usr/bin/env python3
"""The Python side of the spike: read_added_code's parser of `git log -p` output (its handle and paths, copied
from generator/written.py as they stand), run on a saved stream, writing every file record it finishes in the
canonical form the Rust parser writes too. Usage: reference.py STREAM OUT"""
import importlib.util
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cp", os.path.join(HERE, "..", "..", "coderprint.py"))
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)
git_path, diff_path, header_paths, HUNK = cp.git_path, cp.diff_path, cp.header_paths, cp.HUNK


def field(out, value):
    if value is None:
        out += b"-"
    else:
        data = value.encode("utf-8", "surrogateescape") if isinstance(value, str) else value
        out += b"%d:" % len(data) + data


def parse(stream, out):
    state = {"sha": None, "merge": False, "parents": [], "file": None, "header": False, "hunk": None, "side": None}

    # ---- copied from read_added_code (generator/written.py): paths, then finish reduced to writing the record
    def paths(f):
        if f["labels"]:
            return
        old, new = f["from"] or f["git_paths"][0], f["to"] or f["git_paths"][1]
        if (old is None or new is None) and f["binary_line"]:
            m = re.match(r"Binary files (.*) and (.*) differ$", f["binary_line"])
            if m:
                old, new = old or diff_path(m.group(1), "a/"), new or diff_path(m.group(2), "b/")
        f["old_path"] = None if f["created"] else old
        f["new_path"] = None if f["deleted"] else new

    def finish():
        f = state["file"]
        state["file"] = None
        if f is None:
            return
        paths(f)
        out.extend(b"F ")
        field(out, state["sha"])
        out.extend(b" %d " % state["merge"])
        field(out, " ".join(state["parents"]))
        for key in ("old_blob", "new_blob", "old_path", "new_path", "mode", "from", "to"):
            out.extend(b" ")
            field(out, f[key])
        out.extend(b" %d%d%d\n" % (f["binary"], f["created"], f["deleted"]))
        for a, b, c, d, minus, plus, eol6, eol7 in f["hunks"]:
            out.extend(b"H %d %d %d %d %d %d %d %d\n" % (a, b, c, d, len(minus), len(plus), eol6, eol7))
            for line in minus + plus:
                field(out, line)
                out.extend(b"\n")

    # ---- handle, verbatim
    def handle(stream):
        s = state
        for raw in stream:
            if raw.startswith(b"\x00"):
                finish()
                ids = raw[1:].decode("ascii", "replace").split()   # the commit, then its parents
                s.update(sha=ids[0] if ids else None, merge=len(ids) > 2, parents=ids[1:], header=False)
                continue
            if raw.startswith(b"diff --git "):
                finish()
                s.update(header=True, hunk=None, side=None,
                         file={"old_blob": None, "new_blob": None, "old_path": None, "new_path": None, "mode": None,
                               "binary": False, "hunks": [], "labels": False, "created": False, "deleted": False,
                               "from": None, "to": None, "binary_line": None,
                               "git_paths": header_paths(raw[11:].decode("utf-8", "replace").rstrip("\n"))})
                continue
            f = s["file"]
            if f is None:
                continue
            if s["header"]:
                if raw.startswith(b"@@"):
                    s["header"] = False
                else:
                    line = raw.decode("utf-8", "replace").rstrip("\n")
                    if line.startswith("index "):
                        fields = line[6:].split(" ")
                        ids = fields[0].split("..")
                        if len(ids) == 2 and all(re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", x) for x in ids):
                            f["old_blob"], f["new_blob"] = ids
                        if len(fields) > 1:
                            f["mode"] = fields[1]
                    elif line.startswith(("new file mode ", "new mode ", "deleted file mode ")):
                        f["mode"] = line.split()[-1]
                        f["created"] = f["created"] or line.startswith("new file")
                        f["deleted"] = f["deleted"] or line.startswith("deleted")
                    elif line.startswith(("rename from ", "copy from ")):
                        f["from"] = git_path(line.split(" ", 2)[2])
                    elif line.startswith(("rename to ", "copy to ")):
                        f["to"] = git_path(line.split(" ", 2)[2])
                    elif line.startswith("--- "):
                        f["old_path"], f["labels"] = diff_path(line[4:], "a/"), True
                    elif line.startswith("+++ "):
                        f["new_path"], f["labels"] = diff_path(line[4:], "b/"), True
                    elif line.startswith("Binary files "):
                        f["binary"], f["binary_line"] = True, line
                    continue
            if raw.startswith(b"@@"):
                m = HUNK.match(raw)
                if m:
                    a, b, c, d = (int(x) if x is not None else 1 for x in m.groups())
                    s["hunk"] = [a, b, c, d, [], [], False, False]
                    f["hunks"].append(s["hunk"])
                s["side"] = None
            elif s["hunk"] is not None:
                body = raw[1:-1] if raw.endswith(b"\n") else raw[1:]
                if raw.startswith(b"+"):
                    s["hunk"][5].append(body)
                    s["side"] = 7
                elif raw.startswith(b"-"):
                    s["hunk"][4].append(body)
                    s["side"] = 6
                elif raw.startswith(b"\\") and s["side"]:   # "\ No newline at end of file", of the line before it
                    s["hunk"][s["side"]] = True
        finish()

    handle(stream)


if __name__ == "__main__":
    out = bytearray()
    with open(sys.argv[1], "rb") as stream:
        started = time.perf_counter()
        parse(stream, out)
        elapsed = time.perf_counter() - started
    with open(sys.argv[2], "wb") as f:
        f.write(out)
    print("python parse: %.3fs" % elapsed, file=sys.stderr)
