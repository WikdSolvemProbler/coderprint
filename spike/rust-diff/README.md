# Rust port spike: the diff parser

A throwaway experiment, not wired into the Action: is porting coderprint to Rust worth it?

## What was ported

A full collection run was profiled with `tools/benchmark_history.py` on two public clones. The hottest piece of
Python that stands on its own is `read_added_code`'s parser of the `git log -p` stream (`handle` and `paths` in
`generator/written.py`), so that is what `src/main.rs` reimplements. `reference.py` runs the Python parser exactly as
it stands, and both write every file record they finish (commit, parents, blobs, paths, mode, flags, every hunk and
its raw lines) in the same byte format, so `cmp` proves they agree.

## Results

Python 3.12, Rust 1.97.0 release build, same Linux box, best of three:

| stream | commits | stream size | Python | Rust | speedup | output |
|---|---|---|---|---|---|---|
| pallets/click | 3,380 | 19 MB | 0.73 s | 0.11 s | 6.8x | identical |
| python-poetry/poetry | 3,884 | 38 MB | 1.46 s | 0.21 s | 7.0x | identical |
| edge cases (below) | 6 | 4 KB | | | | identical |

The edge-case repository covers paths with spaces, tabs, quotes and accents, binary files renamed to a name holding
" and ", a rename with an edit, a mode change, a deletion, a merge, a symbolic link, invalid UTF-8 in a line and a
missing newline at end of file.

## What it means for the whole run

| repo | full run (no profiler) | parser share | best case saving |
|---|---|---|---|
| click | 4.9 s | 0.73 s (15%) | about 0.6 s (13%) |
| poetry | 14.1 s | 1.46 s (10%) | about 1.25 s (9%) |

That best case ignores the cost of handing each record back to Python, which a real binding (PyO3 or a subprocess)
would pay and which eats into it. The rest of the run is spread thin: the largest single cost is `PythonReader` in
`generator/readers.py`, which leans on CPython's own `tokenize` for exactness, so a Rust version would have to
reproduce Python's tokenizer bit for bit; the next is git itself, which Rust would not speed up.

**Verdict:** a full port is not worth it. Rust is about 7x faster on the code it replaces, but the hot path is shared
between git, CPython's tokenizer and many small functions, so a whole rewrite would buy roughly 10 to 15% of wall
time while adding a toolchain, a build step for every platform the Action runs on, and a second implementation of
logic that is tuned to the line. If speed ever matters, profile-led Python fixes come first.

## Reproduce

```sh
spike/rust-diff/bench.sh /path/to/any/clone
```
