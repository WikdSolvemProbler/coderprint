"""Regression checks for how coderprint reads lines of code and which files are code: one check or more for each
finding of the lines area (lines-F1 to lines-U8, gaps-a9-f11, f14, f15, f20 and u02, and the vote's M3 and M14).
Usage: python test_lines.py path/to/coderprint.py. It builds its repositories in a temporary folder, runs collect()
with every network lookup replaced by a fake, prints one line per check and exits non-zero if any check fails."""
import importlib.util
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

spec = importlib.util.spec_from_file_location("cp_under_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

ROOT = tempfile.mkdtemp(prefix="lines-")
NOREPLY = "123+owner1@users.noreply.github.com"
T0 = 1700000000
SOURCES = {}
results = []


def check(fid, name, ok, detail=""):
    if callable(ok):   # a check that may raise on an older coderprint.py, which lacks what it calls
        try:
            ok = ok()
        except Exception as e:
            ok, detail = False, "%s: %s" % (type(e).__name__, e)
    results.append(bool(ok))
    print("%s %s %s%s" % ("PASS" if ok else "FAIL", fid, name, "" if ok else "  [got %r]" % (detail,)))


def git(repo, *args, when=T0, stdin=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Owner One", GIT_AUTHOR_EMAIL=NOREPLY, GIT_COMMITTER_NAME="Owner One",
               GIT_COMMITTER_EMAIL=NOREPLY, GIT_AUTHOR_DATE="%d +0000" % when, GIT_COMMITTER_DATE="%d +0000" % when)
    p = subprocess.run(["git", "-C", repo, "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                        "-c", "core.symlinks=false"] + list(args), env=env, capture_output=True, input=stdin)
    if p.returncode:
        raise SystemExit("git %s failed: %s" % (args[:2], p.stderr.decode("utf-8", "replace")))
    return p.stdout.decode("utf-8", "replace")


def build(name, commits):
    """commits: a list of {path: text or bytes, or None to delete}, one commit a day apart."""
    path = os.path.join(ROOT, "src", name)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", "-b", "main", path], check=True, capture_output=True)
    for k, files in enumerate(commits):
        for rel, data in files.items():
            p = os.path.join(path, rel)
            if data is None:
                os.remove(p)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data.encode("utf-8") if isinstance(data, str) else data)
        git(path, "add", "-A", when=T0 + k * 86400)
        git(path, "commit", "-q", "--allow-empty", "-m", "c%d" % k, when=T0 + k * 86400)
    SOURCES[name] = path
    return path


def fake_clone(owner, name, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    subprocess.run(["git", "clone", "-q", "--bare", SOURCES[name], dest], check=True, capture_output=True)


cp.clone = fake_clone
cp.resolve_authors = lambda owner, samples: {e: None for e in samples}
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
cp.templates = lambda owner: {}
cp.seed_blobs = lambda full_name, dest: None
_names = iter(range(10 ** 6))


def collect(commits, name=None, data=False):
    """(written, in use in production, in use in tests, imports) for a history, or the whole result with data."""
    name = name or "r%d" % next(_names)
    if name not in SOURCES:
        build(name, commits)
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    try:
        d = cp.collect("owner1", [{"name": name, "isPrivate": True}], work)
    except Exception as e:
        return "error: %s: %s" % (type(e).__name__, e)
    if data:
        return d
    return sum(n for _, _, n in d["events"]), d["code"]["production"], d["code"]["tests"], len(d["imports"])


def kinds(lang, text, path="x"):
    """How every line of text reads as a whole file of lang at path: C code, M comment, B blank. On a coderprint.py
    from before whole-file readers, its LineKinds line by line."""
    try:
        if not hasattr(cp, "read_lines"):
            reader = cp.LineKinds(lang)
            return "".join({"code": "C", "comment": "M", "blank": "B"}[reader.kind(t)] for t in text.split("\n")[:-1])
        reader = cp.reader_for(lang, path)[0]
        lines, eol = cp.split_lines(text, "\n")
        got, _, _ = cp.read_lines(reader, lines.__getitem__, len(lines), eol)
        return "".join("BMC"[k] for k in got)
    except Exception as e:
        return "error: %s: %s" % (type(e).__name__, e)


def exact(lang, text, path="x"):
    reader = cp.reader_for(lang, path)[0]
    lines, eol = cp.split_lines(text, "\n")
    return cp.read_lines(reader, lines.__getitem__, len(lines), eol)[2]


# ---------------------------------------------------------------- lines-F1 and M14: Python read by its tokenizer
k = kinds("Python", 'SQL = """\nSELECT 1\n"""\ndef f():\n    return 1\n')
check("lines-F1", "the closing quotes of an assigned string open nothing", k == "CCCCC", k)
k = kinds("Python", 'def f():\n    r"""Doc\n    more\n    """\n    return 1\n')
check("lines-F1", "a prefixed docstring is a comment", k == "CMMMC", k)
k = kinds("Python", 'text = textwrap.dedent("""\n    hello\n""")\nx = 1\n')
check("lines-F1", "a string passed to a call is code to its end, and the code after it too", k == "CCCC", k)
k = kinds("Python", 'items = [\n    """one""",\n    """two"""\n]\n')
check("lines-F1", "a string starting its own line inside a list is code (the tokenizer knows)", k == "CCCC", k)
S1 = ('QUERY = """\nSELECT *\nFROM t\n"""\n\n\ndef f():\n    return 1\n\n\n'
      'def g():\n    text = textwrap.dedent("""\n        hello\n    """)\n    return text\n')
got = collect([{"a.py": S1}])
check("lines-F1", "collect: a SQL string and two functions, 11 written, 11 in use", got == (11, 11, 0, 0), got)
k = kinds("Python", 'parser = argparse.ArgumentParser(description="""\nTool.\n""")\na = 1\nb = 2\nreturn_ = a + b\n')
check("M14", "code after a line starting with closing triple quotes is code", k == "CCCCCC", k)
k = kinds("Python", 'def f():\n    """Doc.""" ; x = 1\n')
check("lines-F1", "a docstring and code on one line is code", k == "CC", k)
k = kinds("Python", 'def f(): """Doc\n    more\n    """\nx = 1\n')
check("lines-F1", "a docstring after a def's colon on its line is a comment", k == "CMMC", k)
k = kinds("Python", "data = b'''\nraw\n'''\ny = 2\n")
check("lines-F1", "bytes are code", k == "CCCC", k)
k = kinds("Python", "if 1:\n\tx = 1\n        y = 2\n")
check("lines-F1", "a file the tokenizer cannot read falls back to the line reader, marked approximate",
      lambda: k == "CCC" and not exact("Python", "if 1:\n\tx = 1\n        y = 2\n"), k)

# ---------------------------------------------------------------- M3: C comments after code, Rust test braces
k = kinds("C", "int x = 1; /* start\n   still comment\n   end */ int y = 2;\nint z;\n")
check("M3", "a C block comment opened after code runs to its end, and code after it is code", k == "CMCC", k)
rust = ('fn a() -> i32 {\n    1\n}\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n'
        '        assert_eq!(format!("{}", 1), "}");\n        let c = \'{\';\n        assert_eq!(c, \'{\');\n'
        '    }\n}\nfn b() -> i32 {\n    2\n}\n')
got = collect([{"src/lib.rs": rust}])
check("M3", "a Rust test module holding braces in strings: 6 production, 9 test lines", got == (15, 6, 9, 0), got)

# ---------------------------------------------------------------- lines-F7, U4: headers and shared extensions
check("lines-F7", "a .h header holds code", lambda: cp.counts_as_code("a.h", cp.language_of("a.h")))
got = collect([{"src/a.c": '#include "a.h"\n\nint add(int a, int b) {\n    return a + b;\n}\n',
                "src/a.h": "#ifndef A_H\n#define A_H\n/* adds */\nint add(int a, int b);\n#endif\n"}])
check("lines-F7", "collect: a .c file and its header, 8 lines", got == (8, 8, 0, 0), got)
check("lines-U4", ".m, .fs and .v hold code, .pl does not",
      lambda: all(cp.counts_as_code(p, cp.language_of(p)) for p in ("App/View.m", "src/Main.fs", "rtl/top.v"))
      and not cp.counts_as_code("script.pl", cp.language_of("script.pl")))
k = kinds(cp.OTHER, "// objc\n%{\nmatlab block\n%}\n(*handler)(x);\n% matlab\n", "View.m")
check("lines-U4", ".m reads Objective-C and MATLAB comments, and (* as code", k == "MMMMCM", k)
k = kinds(cp.OTHER, "\\ forth\n(* f# *)\nlet f = List.fold (*) 1\n// c\n", "Main.fs")
check("lines-U4", ".fs reads F# and Forth comments, and F#'s (*) as the operator", k == "MMCM", k)
k = kinds(cp.OTHER, "(* rocq *)\n// verilog\nmodule top;\n", "top.v")
check("lines-U4", ".v reads Verilog and Rocq comments", k == "MMC", k)

# ---------------------------------------------------------------- lines-F8: the import rule counts code files
S4 = {"pkg/m%d.py" % n: "a_%d = %d\nb_%d = %d\n" % (n, n, n, n) for n in range(450)}
S4.update({"docs/p%d.md" % n: "# page %d\n" % n for n in range(60)})
got = collect([S4])
check("lines-F8", "450 Python files and 60 Markdown pages are not an import: 900 lines", got == (900, 900, 0, 0), got)
got = collect([{"src/m%d.py" % n: "x_%d = 1\ny_%d = 2\n" % (n, n) for n in range(501)}])
check("lines-F8", "501 Python files still are an import", got == (0, 0, 0, 1), got)

# ---------------------------------------------------------------- lines-F2: a byte order mark
k = kinds("C#", "\ufeff/*\n * licence\n */\nusing System;\n")
check("lines-F2", "a byte order mark before a block comment", k == "MMMC", k)
S2b = ('\ufeff"""Module doc.\n\nMore.\n"""\nimport os\nWIDTH = 80\nHEIGHT = 24\n\n\ndef f():\n    """Doc."""\n'
       '    return os.sep\n')
got = collect([{"b.py": S2b}])
check("lines-F2", "collect: a byte order mark and a module docstring, 5 lines", got == (5, 5, 0, 0), got)

# ---------------------------------------------------------------- lines-F11: every language's comment syntax
langs = set(cp.LANGUAGES.values()) | set(cp.SUFFIXES.values()) | set(cp.NAMES.values())
langs |= set(getattr(cp, "CASED_NAMES", {}).values())
special = {"Python", "Cython", "JavaScript", "TypeScript", "QML", "PHP", "Pug", "Slim", "Haml"}
table = getattr(cp, "SYNTAXES", None) or getattr(cp, "COMMENTS", {})
missing = sorted(l for l in langs if l not in cp.NOT_CODE and l not in table and l not in special)
check("lines-F11", "every counted language has a comment syntax", not missing, missing)
for lang, text, want in (
        ("PHP", "<?php\n#[Route('/x')]\n# c\n// d\n", "CCMM"), ("PHP", "<div>\n<!-- note -->\n<?php echo 1; ?>\n", "CMC"),
        ("PHP", "<?php\n$s = 'it is\n# still a string';\n# comment\n", "CCCM"),
        ("PHP", "<?php\n$t = <<<EOT\n# text\nEOT;\n# c\n", "CCCCM"),
        ("Assembly", "#include <a.h>\n#define N 4\n# comment\n; comment\n// c\nmov r0, #1\n", "CCMMMC"),
        ("Vue", "<template>\n  <!-- note -->\n  <div/>\n</template>\n", "CMCC"), ("Svelte", "<!-- note -->\n<div/>\n", "MC"),
        ("Stata", "* a\n// b\n#delimit ;\nregress y x\n", "MMCC"), ("SAS", "* a\n  b;\ndata x; run;\n", "MMC"),
        ("Hy", "; c\n(print 1)\n", "MC"), ("Perl", "=pod\n\nText\n\n=cut\nprint 1;\n__END__\ndata\n", "MBMBMCMM"),
        ("Ruby", "=begin\ndoc\n=end trailing words\nputs 1\n", "MMMC"),
        ("Lua", "--[==[ a\n b ]] c\n]==]\nx = 1\ns = [[\n-- not a comment\n]]\n", "MMMCCCC"),
        ("Batchfile", "REM a\n@REM b\nrem\n:: c\n@echo off\n", "MMMMC"), ("CoffeeScript", "#### banner\nx = 1\n", "MC"),
        ("CoffeeScript", "###\nblock\n###\nx = 1\n", "MMMC"), ("Hack", "// c\n/* d */\nfunction f(): void {}\n", "MMC"),
        ("Twig", "{# c #}\n<p>{{ x }}</p>\n", "MC"), ("Nim", "#[ a\n #[ b ]#\n ]#\necho 1\n", "MMMC"),
        ("JavaScript", "#!/usr/bin/env node\nconsole.log(1)\n", "MC"), ("M4", "dnl a\ndnl---\nAC_INIT([x])\n", "MMC"),
        ("GraphQL", "# c\ntype Q { a: Int }\n", "MC"), ("Dafny", "// a\nmethod M() {}\n", "MC"),
        ("Forth", "\\ a comment\n( stack note )\n: sq dup * ;\n", "MMC"), ("TLA", "\\* a\n(* b *)\nInit == x = 0\n", "MMC"),
        ("WebAssembly", ";; a\n(; b (; c ;) ;)\n(module)\n", "MMC"), ("Mermaid", "%% c\ngraph TD\n", "MC"),
        ("Pascal", "{$mode objfpc}\n{ note }\n(* note *)\nbegin end.\n", "CMMC"),
        ("Haskell", "{-# LANGUAGE GADTs #-}\n-- c\nx --> y = 1\n", "CMC"),
        ("CMake", "#[[ a\n b ]]\nproject(x)\n", "MMC"), ("Elixir", '@doc """\n# Examples\n"""\ndef f, do: 1\n', "CCCC"),
        ("SQL", "-- a\nSELECT '--x', 'it''s /* no' /* yes\n*/\n", "MCM"), ("COBOL", "      * comment\n       MOVE A TO B.\n", "MC"),
        ("MATLAB", "%{\n a\n%}\nx = 1;\n", "MMMC"), ("Julia", "#= a\n#= b =#\n c =#\nx = a'\n", "MMMC"),
        ("PowerShell", "<#\n.SYNOPSIS\n#>\n$s = @\"\n# text\n\"@\nWrite-Output 1\n", "MMMCCCC"),
        ("Liquid", "{% comment %}\nnote\n{% endcomment %}\n<p/>\n", "MMMC"), ("Go Template", "{{/* a */}}\n<p/>\n", "MC"),
        ("HTML", "<!-- nav --> <nav>\n<%# erb %>\n@* razor *@\n<p/>\n", "CMMC")):
    k = kinds(lang, text)
    check("lines-F11", "%s: %r" % (lang, text[:24]), k == want, k)

# ---------------------------------------------------------------- lines-F12: literate sources
S9 = ("# Naturals\n\nThe naturals are defined inductively.\nWe then add them.\n\n```agda\ndata N : Set where\n"
      "  zero : N\n  suc  : N -> N\n```\n\nThat is all.\n")
got = collect([{"Nat.lagda.md": S9}])
check("lines-F12", "collect: literate Agda, 3 lines in the fence", got == (3, 3, 0, 0), got)
got = collect([{"Main.lhs": "This is prose.\nIt explains.\n\n> main :: IO ()\n> main = pure ()\n\nMore prose.\n"}])
check("lines-F12", "collect: literate Haskell, 2 Bird-track lines", got == (2, 2, 0, 0), got)
k = kinds("Agda", "prose\n```haskell\nexample\n```\n```\ncode\n````\nprose\n", "a.lagda.md")
check("lines-F12", "a fence naming another language is an example; a longer closing fence closes", k == "MMMMMCMM", k)
got = collect([{"Nat.lagda.md": S9}, {"Nat.lagda.md": S9.replace("  suc  : N -> N\n", "  suc  : N -> N\n  two  : N\n")}])
check("lines-F12", "collect: a constructor added inside the fence later, 4 written, 4 in use", got == (4, 4, 0, 0), got)
got = collect([{"Nat.lagda.md": S9}, {"Nat.lagda.md": S9.replace("We then add them.\n", "We then add them.\nAnd more.\n")}])
check("lines-U1", "collect: prose added to a literate source later is not written", got == (3, 3, 0, 0), got)

# ---------------------------------------------------------------- lines-F15: notebooks
check("lines-F15", "Mathematica notebooks are not code", all(cp.language_of(p) is None for p in ("a.nb", "a.nbp", "a.cdf")))
got = collect([{"plot.nb": "(* Wolfram Notebook *)\nNotebook[{\nCell[BoxData[\"x\"]]\n}]\n"}])
check("lines-F15", "collect: a .nb notebook adds no lines", got == (0, 0, 0, 0), got)

# ---------------------------------------------------------------- lines-F9, gaps-a9-f11: CSS preprocessors' //
k = kinds("CSS", "// colours\n$red: #f00;\n.a { background: url(//cdn.x/a.png); } /* b\n c */\n")
check("lines-F9", "SCSS // comments, a url(//...) and a comment after code", k == "MCCM", k)
got = collect([{"a.scss": "// colours\n$red: #f00;\n// the button\n.btn { color: $red; }\n",
                "b.less": "// c\n@x: 1;\n.a { width: @x; }\n", "c.css": "/* c */\n.c { color: red; }\n"}])
check("gaps-a9-f11", "collect: SCSS, Less and CSS, 5 lines of code", got == (5, 5, 0, 0), got)

# ---------------------------------------------------------------- lines-F17: Sass's indented syntax
got = collect([{"a.sass": "/* note\n   more\n.a\n  color: red\n// c\n  still c\n.b\n  color: blue\n"}])
check("lines-F17", "collect: a .sass comment ends where its indentation does, 4 lines", got == (4, 4, 0, 0), got)
got = collect([{"b.scss": "/* note\n   more */\n.a { color: red; }\n"}])
check("lines-F17", "collect: .scss keeps /* */, 1 line", got == (1, 1, 0, 0), got)
check("lines-F17", "Pug, Slim and Haml comments run over their indented lines",
      kinds("Pug", "//\n  note\ndiv\n") == "MMC" and kinds("Haml", "-# a\n  b\n%p\n") == "MMC"
      and kinds("Slim", "/ a\n  b\np\n") == "MMC")

# ---------------------------------------------------------------- lines-F3: code after a block comment closes
k = kinds("C", "/* w */ int w = 1;\n/* a\n b */ int h;\n/* a */ // b\n")
check("lines-F3", "code after a block comment's end is code, a comment after it a comment", k == "CMCM", k)
got = collect([{"d.c": "/* width */ int w = 1;\n/* height\n   in px */ int h = 2;\n"}])
check("lines-F3", "collect: code after comments close, 2 lines", got == (2, 2, 0, 0), got)

# ---------------------------------------------------------------- lines-F5: nested comments
for lang, text, want in (("Rust", "/* a\n /* b */\n c\n*/\nfn main() {}\n", "MMMMC"), ("C", "/* a\n /* b */\nint c;\n", "MMC"),
                         ("Swift", "/* a /* b */ c\n d */\nlet x = 1\n", "MMC"),
                         ("Kotlin", "/* a\n/* b */\n*/\nval x = 1\n", "MMMC"),
                         ("Haskell", "{- a\n{- b -}\n c -}\nmain = pure ()\n", "MMMC"),
                         ("OCaml", "(* a\n(* b *)\n c *)\nlet x = 1\n", "MMMC"), ("Lean", "/- a /- b -/\n -/\ndef x := 1\n", "MMC"),
                         ("D", "/+ a /+ b +/\n +/\nint x;\n", "MMC"), ("Dhall", "{- a {- b -}\n-}\n1\n", "MMC"),
                         ("PureScript", "{- a {- b -}\nx = 1\n", "MC")):
    k = kinds(lang, text)
    check("lines-F5", "%s block comments %s" % (lang, "do not nest" if lang in ("C", "PureScript") else "nest"),
          k == want, k)
got = collect([{"m.rs": "/* disabled:\n   /* inner note */\n   fn old() {}\n*/\nfn main() {}\n"}])
check("lines-F5", "collect: a Rust nested comment, 1 line", got == (1, 1, 0, 0), got)

# ---------------------------------------------------------------- lines-F13: lines split alike
got = collect([{"s.js": 'const sep = "a\u2028b";\nexport default sep;\n'}])
check("lines-F13", "collect: a line holding U+2028 is in use", got == (2, 2, 0, 0), got)
got = collect([{"f.c": "int a;\x0c int b;\nint c;\n"}])
check("lines-F13", "collect: a line holding a form feed is in use", got == (2, 2, 0, 0), got)

# ---------------------------------------------------------------- lines-F14: no final newline
got = collect([{"n.py": "x = 1"}, {"n.py": "x = 1\ny = 2\n"}])
check("lines-F14", "collect: appending to a file with no final newline, 2 written", got == (2, 2, 0, 0), got)
got = collect([{"w.py": "x = 1\r\ny = 1"}, {"w.py": "x = 1\r\ny = 1\r\nz = 2\r\n"}])
check("lines-F14", "collect: the same with carriage returns, 3 written", got == (3, 3, 0, 0), got)

# ---------------------------------------------------------------- lines-F16: symbolic links
link = build("links", [{"real.py": "x = 1\n"}])
blob = git(link, "hash-object", "-w", "--stdin", stdin=b"real.py").strip()
git(link, "update-index", "--add", "--cacheinfo", "120000,%s,alias.py" % blob)
git(link, "commit", "-q", "-m", "link", when=T0 + 86400)
got = collect(None, name="links")
check("lines-F16", "collect: a symbolic link named like code is not a line of code", got == (1, 1, 0, 0), got)

# ---------------------------------------------------------------- lines-U1 (lines-F6): hunks read as the whole file
S5a = 'def f():\n    """Summary.\n\n    Details.\n    """\n    return 1\n'
S5b = 'def f():\n    """Summary.\n\n    Details.\n    More details.\n    Args: none.\n    Returns: one.\n    """\n    return 1\n'
got = collect([{"f.py": S5a}, {"f.py": S5b}])
check("lines-U1", "collect: three docstring lines added later, 2 written (lines-F6)", got == (2, 2, 0, 0), got)
S5j = "class A {\n    /**\n     * Adds.\n     */\n    int add(int a) { return a; }\n}\n"
S5k = ("class A {\n    /**\n     * Adds.\n     * @param a the value\n     * @return the value\n     */\n"
       "    int add(int a) { return a; }\n}\n")
got = collect([{"A.java": S5j}, {"A.java": S5k}])
check("lines-U1", "collect: two Javadoc lines added later, 3 written", got == (3, 3, 0, 0), got)
P1 = 'QUERY = """\nSELECT a\nFROM t\n"""\n\n\ndef f():\n    return 1\n'
P2 = 'QUERY = """\nSELECT a\nFROM t\nWHERE a > 1\n"""\n\n\ndef f():\n    return 1\n\n\ndef g():\n    return 2\n'
got = collect([{"q.py": P1}, {"q.py": P2}])
check("lines-U1", "collect: a line added inside a string, then two functions, 9 written", got == (9, 9, 0, 0), got)
C1 = "int a;\n/* start\nint b;\n*/\nint c;\n"
C2 = "int a;\n/* start\nint b;\nint b2;\n*/\nint c;\nint d;\n"
got = collect([{"c.c": C1}, {"c.c": C2}])
check("lines-U1", "collect: a line added inside a C comment is not written, code below is", got == (3, 3, 0, 0), got)
got = collect([{"o.py": 'x = 1\ny = 2\n'}, {"o.py": 'x = 1\n"""\ny = 2\n'}, {"o.py": 'x = 1\n"""\ny = 2\n"""\nz = 3\n'}])
check("lines-U1", "collect: a commit that opens a docstring above untouched lines, then closes it", got == (3, 2, 0, 0),
      got)


def random_edits(lang, path, pieces, trials=200):
    """Whether every random edit of random files reads, from the old reading, line for line as the whole new file."""
    random.seed(11)
    reader = cp.reader_for(lang, path)[0]
    for trial in range(trials):
        old = [random.choice(pieces) for i in range(random.randrange(1, 25))]
        new = list(old)
        a = random.randrange(len(new) + 1)
        b = min(len(new), a + random.randrange(3))
        ins = [random.choice(pieces) for _ in range(random.randrange(3))]
        new[a:b] = ins
        base = cp.read_lines(reader, old.__getitem__, len(old), True)
        whole = cp.read_lines(reader, new.__getitem__, len(new), True)
        if not base[2]:
            continue
        try:
            inc = cp.read_edited(reader, base[:2], new.__getitem__, len(new), True, [(a, b, a, a + len(ins))])
        except cp.ReadFailed:
            if whole[2]:
                return False
            continue
        if inc[0] != whole[0] or not whole[2]:
            return False
    return True


check("lines-U1", "an edited C version reads line for line as the whole file does (200 random edits)",
      lambda: random_edits("C", "x.c", ["int a;", "/* x", "*/", "// c", '"/*"', "x */ y;", "/* y", '"*/"', "q;"]))
check("lines-U1", "an edited Python version reads line for line as the whole file does (200 random edits)",
      lambda: random_edits("Python", "x.py", ["x = 1", '"""', "doc", "f(", ")", "    y = 2", "if x:", "# c", "'''",
                                              "s = '''", "]", "a = [", "", "def f():"]))

# ---------------------------------------------------------------- lines-U2: literals understood
for lang, text, want in (
        ("C", "int x = 1; /* start\n   still comment\n   end */\nint y;\n", "CMMC"),
        ("JavaScript", 'const g = "src/**/*.js";\nconst h = 1;\n', "CC"),
        ("Go", "var s = `\n// not a comment\n/* nor this`\nvar t = 1 /* c\n*/\n", "CCCCM"),
        ("C#", 'var s = @"C:\\dir\\"; /* c\n// still c */\nvar r = """\n// text\n""";\n', "CMCCC"),
        ("C++", 'auto s = R"x(/* not )" a comment */)x";\nint y; /* c\n*/\n', "CCM"),
        ("Java", 'String t = """\n    // text\n    """;\nint a; /* c\n */\n', "CCCCM"),
        ("Kotlin", 'val s = """\n// text\n"""\n', "CCC"), ("Rust", "let s = \"a\n// in string\";\nlet c = '\"'; // c\n", "CCC"),
        ("Rust", "fn f<'a>(x: &'a str) -> &'a str { x } /* c\n*/\n", "CM"),
        ("C++", "int n = 1'000; /* c\n*/\n", "CM"), ("Swift", 'let s = #"a "/*" b"#\nlet t = 1\n', "CC"),
        ("Python", 'x = "/*"\n# c\n', "CM")):
    k = kinds(lang, text)
    check("lines-U2", "%s: %r" % (lang, text[:26]), k == want, k)

# ---------------------------------------------------------------- lines-U3: JSX comments
k = kinds("JavaScript", "return (\n  <div>\n    {/* note */}\n  </div>\n);\n")
check("lines-U3", "a JSX comment line is a comment", k == "CCMCC", k)
k = kinds("TypeScript", "<div>\n  {/* a\n   b */}\n  {x}{/* c */}\n</div>\n")
check("lines-U3", "a JSX comment across lines, and one after code", k == "CMMCC", k)
k = kinds("JavaScript", "const t = `a ${ `b ${c}` }\n// in template\n`;\nconst r = /\\/*x/; // c\nlet z = 1;\n")
check("lines-U3", "templates nest and a regular expression is not a comment", k == "CCCCC", k)

# ---------------------------------------------------------------- lines-U5: names
names = {"BUILD": "Starlark", "pkg/WORKSPACE": "Starlark", "build": cp.OTHER, "Dockerfile.dev": "Dockerfile",
         "Containerfile.prod": "Dockerfile", "Dockerfile.txt": None, "Dockerfile.json": None,
         "Dockerfile.dockerignore": cp.OTHER, "Dockerfile.md": "Markdown"}
got = {p: cp.language_of(p) for p in names}
check("lines-U5", "Bazel files and Dockerfile variants by name", got == names, got)

# ---------------------------------------------------------------- lines-U6, gaps-a9-u02: .gitattributes
got = collect([{".gitattributes": "gen/*.ts linguist-generated=true\n", "gen/api.ts": "export const a = 1;\n",
                "src/app.ts": "export const b = 2;\n"}])
check("lines-U6", "collect: a file marked linguist-generated counts nowhere", got == (1, 1, 0, 0), got)
got = collect([{".gitattributes": "static/** linguist-vendored\ndocs/** linguist-documentation\n"
                                  "gen/** linguist-generated\ngen/keep.ts -linguist-generated\n",
                "static/lib.js": "var a = 1;\n", "docs/ex.py": "x = 1\n", "gen/g.ts": "let g = 1;\n",
                "gen/keep.ts": "let k = 1;\n", "src/app.ts": "let s = 1;\n"}])
check("gaps-a9-u02", "collect: vendored, documentation and generated paths out, one unmarked kept", got == (2, 2, 0, 0),
      got)
got = collect([{"src/p.ts": "let a = 1;\n"}, {"src/p.ts": "let a = 1;\nlet b = 2;\n"},
               {".gitattributes": "src/p.ts linguist-generated\n", "src/p.ts": "let a = 1;\nlet b = 2;\nlet c = 3;\n"}])
check("gaps-a9-u02", "collect: each version judged by the attributes of its own commit", got == (2, 0, 0, 0), got)

# ---------------------------------------------------------------- lines-U7: fixed-form Fortran
check("lines-U7", "C, c, * or ! in column 1 of .f is a comment",
      kinds("Fortran", "C     comment\n*     comment\n      PROGRAM P\n      END\n", "a.f") == "MMCC")
check("lines-U7", "free-form .f90 keeps a line starting call as code", kinds("Fortran", "call foo()\n! c\n", "a.f90") == "CM")

# ---------------------------------------------------------------- lines-U8: UTF-16 sources
u16 = lambda s: "\ufeff".encode("utf-16-le") + s.encode("utf-16-le")   # noqa: E731
got = collect([{"s.ps1": u16("Write-Output 1\r\n# c\r\nWrite-Output 2\r\n")},
               {"s.ps1": u16("Write-Output 1\r\n# c\r\nWrite-Output 2\r\nWrite-Output 3\r\n")}])
check("lines-U8", "collect: a UTF-16 PowerShell script and a line added later, 3 written, 3 in use", got == (3, 3, 0, 0),
      got)

# ---------------------------------------------------------------- gaps-a9-f14: generated files by their first lines
gen = {"api/zz_generated.go": "// Code generated by controller-gen. DO NOT EDIT.\n\npackage v1\nvar A = 1\n",
       "app/migrations/0001_initial.py": "# Generated by Django 4.2.7 on 2023-11-14 10:00\nx = 1\n",
       "static/out.css": "/*! tailwindcss v3.4.1 | MIT License */\n.a { margin: 0; }\n",
       "tr/app_de.ts": '<?xml version="1.0" encoding="utf-8"?>\n<TS version="2.1">\n</TS>\n',
       "tools/hand.py": "# Tool that lints auto-generated files marked DO NOT EDIT.\nx = 1\ny = 2\n",
       "settings.py": "# Do not edit the order of these settings\nA = 1\n"}
for i in range(4):
    gen["docs/p%d/index.html" % i] = ('<html><head><meta name="generator" content="Hugo 0.120">\n</head>\n'
                                      "<body><p>%d</p></body>\n</html>\n" % i)
gen["docs/js/search.js"] = "var s = 1;\nvar t = 2;\n"
gen["site/about.html"] = "<p>about</p>\n"
got = collect([gen])
check("gaps-a9-f14", "collect: generated files and a generated site out, hand-written files that mention it kept",
      got == (4, 4, 0, 0), got)

# ---------------------------------------------------------------- gaps-a9-f15: a build's output folders
source = ["internal/build/util.go", "src/main/java/com/acme/coverage/Policy.java", "cmd/dist/build.go",
          "packages/build/src/index.ts", "src/out/writer.rs", "tools/build/gen.py"]
output = ["dist/bundle.js", "build/index.html", "coverage/lcov-report/index.html", "out/index.js",
          "app/build/generated/R.java", "build/lib/pkg/mod.py", "src/out/bundle.js", "packages/ui/dist/index.d.ts"]
check("gaps-a9-f15", "source under build, dist, out or coverage below a source folder counts; output does not",
      all(cp.language_of(p) for p in source) and not any(cp.language_of(p) for p in output),
      ([p for p in source if not cp.language_of(p)], [p for p in output if cp.language_of(p)]))

# ---------------------------------------------------------------- gaps-a9-f20: vendor folders
vendored = ["jspm_packages/x/a.js", "web_modules/preact.js", "external/glfw/src/window.c", "extern/pybind11/a.h",
            "deps/lua/src/lapi.c", "Assets/Plugins/x.cs", "wp-content/plugins/akismet/a.php", "site/wp-content/plugins/b.php"]
own = ["src/external/api.ts", "app/deps/auth.py", "Assets/Scripts/Player.cs", "wp-content/themes/t/functions.php"]
check("gaps-a9-f20", "vendor folders out, the owner's folders of like names in",
      not any(cp.language_of(p) for p in vendored) and all(cp.language_of(p) for p in own),
      ([p for p in vendored if cp.language_of(p)], [p for p in own if not cp.language_of(p)]))

# ---------------------------------------------------------------- the data file says what rests on a fallback
d = collect([{"t.py": "if 1:\n\tx = 1\n        y = 2\n", "ok.py": "z = 1\n"}], data=True)
check("data", "collect: lines read by the fallback are counted as approximate, written and in use",
      lambda: sum(n for _, n in d["code"]["approximate"]) == 3 and d["code"]["approximate_in_use"] == 3,
      d if isinstance(d, str) else d["code"])
# the source is coderprint.py and, from the release that split it, the parts it runs from generator/
parts = os.path.join(os.path.dirname(os.path.abspath(sys.argv[1])), "generator")
source = "".join(open(path, encoding="utf-8").read() for path in [sys.argv[1]] + sorted(
    os.path.join(parts, f) for f in (os.listdir(parts) if os.path.isdir(parts) else ()) if f.endswith(".py")))
check("data", "the data file's written and in use figures carry approximate_loc", "approximate_loc=" in source)

# ---------------------------------------------------------------- reading cost stays near a single pass
body = "".join('def f%d(x):\n    """Doc %d."""\n    return x + %d\n\n' % (i, i, i) for i in range(400))
history = [{"big.py": body}]
for n in range(1, 60):
    body = body.replace("return x + %d\n" % n, "return x + %d  # edited\n    y = %d\n" % (n, n), 1)
    history.append({"big.py": body})
build("big", history)
started = time.perf_counter()
got = collect(None, name="big")
spent = time.perf_counter() - started
check("lines-U1", "collect: 60 versions of a 1,600-line file read in %.1f s, 918 written, 859 in use" % spent,
      got == (918, 859, 0, 0) and spent < 60, got)

table = ["TABLE = {\n"] + ['    "k%d": %d,\n' % (i, i) for i in range(5000)] + ["}\n"]
history = [{"table.py": "".join(table)}]
for n in range(40):
    table[1 + 100 * n + 50] = '    "k%d": -%d,\n' % (100 * n + 49, n)
    history.append({"table.py": "".join(table)})
build("table", history)
started = time.perf_counter()
got = collect(None, name="table")
spent = time.perf_counter() - started
check("lines-U1", "collect: 40 edits inside a 5,000-line literal read in %.1f s, 5,042 written, 5,002 in use" % spent,
      got == (5042, 5002, 0, 0) and spent < 60, got)

# a true merge, both sides editing one file, then an edit after it: the merge's version is made from its first parent
m = build("merged", [{"f.py": "a = 1\nb = 2\nc = 3\n"}])
git(m, "checkout", "-q", "-b", "side", when=T0 + 86400)
with open(os.path.join(m, "f.py"), "w", newline="") as fh:
    fh.write("a = 10\nb = 2\nc = 3\n")
git(m, "commit", "-qam", "side", when=T0 + 86400)
git(m, "checkout", "-q", "main", when=T0 + 2 * 86400)
with open(os.path.join(m, "f.py"), "w", newline="") as fh:
    fh.write("a = 1\nb = 2\nc = 30\n")
git(m, "commit", "-qam", "main", when=T0 + 2 * 86400)
git(m, "merge", "-q", "--no-edit", "side", when=T0 + 3 * 86400)
with open(os.path.join(m, "f.py"), "a", newline="") as fh:
    fh.write('"""\nd = 4 was here\n"""\n')
git(m, "commit", "-qam", "after", when=T0 + 4 * 86400)
got = collect(None, name="merged")
check("lines-U1", "collect: a merge of two edits, then a docstring after it: 5 written, 3 in use", got == (5, 3, 0, 0), got)

shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d" % (sum(results), len(results) - sum(results)))
sys.exit(0 if all(results) else 1)
