# Performance

## Would a Rust port pay off? (October 2026)

No. A spike ported the hottest self-contained part of the generator to Rust and measured it against the Python.
The code lives in closed pull request #20; this page keeps the result.

**What was ported.** A full collection was profiled with `tools/benchmark_history.py`. The hottest piece of Python
that stands on its own is `read_added_code`'s parser of the `git log -p` stream (`handle` and `paths` in
`generator/written.py`). The Rust version wrote byte-identical records to the Python on every stream tried: two real
histories, and a small repository of edge cases (paths with spaces, tabs, quotes and accents, binary files renamed
to a name holding " and ", a rename with an edit, a mode change, a deletion, a merge, a symbolic link, invalid UTF-8
in a line, and a missing newline at end of file).

| Stream | Commits | Size | Python 3.12 | Rust 1.97 | Speedup |
| --- | ---: | ---: | ---: | ---: | ---: |
| pallets/click | 3,380 | 19 MB | 0.73 s | 0.11 s | 6.8x |
| python-poetry/poetry | 3,884 | 38 MB | 1.46 s | 0.21 s | 7.0x |

**What that means for a whole run.** The parser is a small share of the collection:

| Repository | Full collection | Parser share | Best-case saving |
| --- | ---: | ---: | ---: |
| click | 4.9 s | 0.73 s (15%) | about 0.6 s |
| poetry | 14.1 s | 1.46 s (10%) | about 1.25 s |

The best case leaves out the cost of handing each record back to Python, which a real binding would pay. The largest
single cost is `PythonReader` in `generator/readers.py`. It already re-reads only the lines around each edit
(`read_edited` in `generator/syntaxes.py`), so what remains is CPython's own `tokenize`, which a Rust version would
have to reproduce exactly to keep the line counts right. The next largest cost is git itself, which a port would not
change.

**Decision.** Stay in Python. A full port would save roughly 10 to 15% of wall time while adding a toolchain, a build
for every platform the Action runs on, and a second implementation of finely tuned counting logic. If speed ever
matters, profile first and fix the Python.

These are single measurements on one Linux machine, best of three for the parser timings, without the profiler for
the full collections.
