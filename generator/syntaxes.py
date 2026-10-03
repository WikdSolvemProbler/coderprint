# coderprint's every counted language's syntax, and which reader reads it. coderprint.py runs this file as part of
# one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# Every counted language's syntax (see Syntax). A plain prefix is escaped (SL); C-family strings are quoted and
# escaped with a backslash on one line (Q1) and character literals are read whole (C_CHAR, and PRIME_CHAR where a
# name may end in a quote, as Haskell's foldl' does, or a quote opens a lifetime, as Rust's 'a does).
SL = lambda *p: tuple(E(x) for x in p)   # noqa: E731
Q1 = lambda q: lit("esc1", E(q), q)      # noqa: E731
QM = lambda q: lit("esc", E(q), q)       # noqa: E731
C_CHAR = lit("skip", r"(?:(?<=u8)|(?<![0-9]))'(?:\\.|[^\\'\n])+'")   # after a digit, C++'s 1'000 separator
PRIME_CHAR = lit("skip", r"(?<![\w'])b?'(?:\\.[^'\s]*|[^\\'\n])'")
C_BLOCK, C_NEST = blk("/*", "*/"), blk("/*", "*/", nests=True)
C_STR = (Q1('"'), C_CHAR)
CPP_STR = (lit("raw", r'(?:u8|[uUL])?R"([^()\\\s]{0,16})\(', '){0}"'),) + C_STR
PY_LIKE = (QM("'''"), QM('"""'), Q1("'"), Q1('"'))
HTML_BLOCK = blk("<!--", "-->")
HS_LINE = (r"--+(?![-!#$%&*+./<=>?@\\^|~:])",)   # --> is an operator, not a comment
HS_BLOCK = Block(r"\{-(?!#)", "-}", True, "any", False)   # {-# LANGUAGE #-} is a pragma, not a comment
ML_NEST = blk("(*", "*)", nests=True)
ML_NEST_NO_OP = Block(r"\(\*(?!\))", "*)", True, "any", False)   # F#'s (*) is the operator, not a comment


def c_like(line=("//",), blocks=(C_BLOCK,), literals=C_STR, **more):
    return Syntax(line=SL(*line), blocks=blocks, literals=literals, **more)


def hash_like(literals=(), tracked=True, **more):
    return Syntax(line=SL("#"), literals=literals, tracked=tracked and bool(literals), **more)


SYNTAXES = {
    **{lang: c_like() for lang in ("C", "Objective-C++", "Solidity", "GLSL", "HLSL", "Protocol Buffer", "AIDL",
                                   "Stan", "Verilog", "SystemVerilog", "ShaderLab", "Processing", "Yacc", "Lex",
                                   "SWIG", "XS", "SmPL", "Pawn", "OpenSCAD", "Move", "ANTLR", "Asymptote")},
    **{lang: c_like(literals=CPP_STR) for lang in ("C++", "Cuda", "Metal")},
    "C#": c_like(literals=(lit("raw", r'\$*("{3,})', "{0}"), lit("dbl", r'\$?@\$?"', '"')) + C_STR),
    "Java": c_like(literals=(QM('"""'),) + C_STR),
    "Kotlin": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(lit("raw", E('"""'), '"""'),) + C_STR),
    "Scala": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(lit("raw", E('"""'), '"""'), Q1('"'), PRIME_CHAR)),
    "Swift": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(
        lit("raw", r'(#+)"""', '"""{0}'), lit("raw1", r'(#+)"', '"{0}'), QM('"""'), Q1('"'))),
    "Go": c_like(literals=(lit("raw", "`", "`"),) + C_STR),
    "Rust": c_like(blocks=(C_NEST,), literals=(lit("raw", r'(?<![\w])[bc]?r(#*)"', '"{0}'), QM('"'), PRIME_CHAR)),
    "Dart": c_like(line=("//", "#!"), blocks=(C_NEST,), literals=(
        lit("raw", r"(?<!\w)r'''", "'''"), lit("raw", r'(?<!\w)r"""', '"""'), QM("'''"), QM('"""'),
        lit("raw1", r"(?<!\w)r'", "'"), lit("raw1", r'(?<!\w)r"', '"'), Q1("'"), Q1('"'))),
    **{lang: c_like(line=("//", "#!"), literals=(QM("'''"), QM('"""'), Q1("'"), Q1('"')))
       for lang in ("Groovy", "Gradle", "Nextflow")},
    "D": c_like(line=("//", "#!"), blocks=(C_BLOCK, blk("/+", "+/", nests=True)), literals=(
        lit("raw", r'(?<!\w)r"', '"'), lit("raw", "`", "`"), QM('"'), C_CHAR)),
    "Zig": c_like(literals=(lit("eol", r"\\\\"),) + C_STR),
    "Odin": c_like(blocks=(C_NEST,), literals=(lit("raw", "`", "`"),) + C_STR),
    "WGSL": c_like(blocks=(C_NEST,)),
    "Vala": c_like(literals=(lit("raw", E('"""'), '"""'),) + C_STR),
    "Haxe": c_like(literals=(QM("'"), QM('"'))),
    "Apex": c_like(literals=(Q1("'"),)),
    "Thrift": c_like(line=("//", "#"), literals=(Q1('"'), Q1("'"))),
    "Jsonnet": c_like(line=("//", "#"), literals=(lit("raw", r"\|\|\|-?", "|||"), lit("dbl1", E('@"'), '"'),
                                                  lit("dbl1", E("@'"), "'"), Q1('"'), Q1("'"))),
    "CUE": c_like(literals=(QM('"""'), QM("'''"), Q1('"'), Q1("'"))),
    "Pkl": c_like(literals=(QM('"""'), Q1('"'))),
    "Bicep": c_like(literals=(lit("raw", "'''", "'''"), Q1("'"))),
    "Carbon": c_like(literals=(lit("raw", "'''", "'''"),) + C_STR),
    "Cairo": c_like(literals=(Q1('"'), Q1("'"))),
    "Gleam": c_like(literals=(QM('"'),)),
    "ReScript": c_like(literals=(lit("esc", "`", "`"), Q1('"'), PRIME_CHAR)),
    "Reason": c_like(literals=(lit("raw", r"\{([a-z_]*)\|", "|{0}}"), Q1('"'), PRIME_CHAR)),
    "Dafny": c_like(literals=(lit("dbl", E('@"'), '"'), Q1('"'), PRIME_CHAR)),
    "GraphQL": Syntax(line=SL("#"), literals=(QM('"""'), Q1('"'))),
    "CSS": c_like(literals=(lit("raw1", r"url\((?!\s*[\"'])", ")"), Q1('"'), Q1("'"))),
    "SQL": Syntax(line=SL("--"), start=SL("#"), blocks=(C_BLOCK,), literals=(
        lit("both1", "'", "'"), lit("dbl1", '"', '"'), lit("raw1", "`", "`"))),
    "PHP": Syntax(line=(E("//"), r"#(?!\[)"), blocks=(C_BLOCK,), literals=(
        QM("'"), QM('"'), lit("here", r"<<<[ \t]*[\"']?([A-Za-z_]\w*)[\"']?")), exits=r"\?>"),
    "Hack": Syntax(line=(E("//"), r"#(?!\[)"), blocks=(C_BLOCK,), literals=(
        QM("'"), QM('"'), lit("here", r"<<<[ \t]*[\"']?([A-Za-z_]\w*)[\"']?"))),
    "Lua": Syntax(line=SL("--"), blocks=(Block(r"--\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), Q1('"'), Q1("'"))),
    "Luau": Syntax(line=SL("--"), blocks=(Block(r"--\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), Q1('"'), Q1("'"), Q1("`"))),
    "Haskell": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(Q1('"'), PRIME_CHAR)),
    "Elm": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(QM('"""'), Q1('"'), PRIME_CHAR)),
    # PureScript's block comments, unlike Haskell's, do not nest
    "PureScript": Syntax(line=HS_LINE, blocks=(Block(r"\{-", "-}", False, "any", False),), literals=(
        lit("raw", E('"""'), '"""'), Q1('"'), PRIME_CHAR)),
    "Agda": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(Q1('"'), PRIME_CHAR)),
    "Idris": Syntax(line=HS_LINE, blocks=(HS_BLOCK,), literals=(QM('"""'), Q1('"'), PRIME_CHAR)),
    "Dhall": Syntax(line=SL("--"), blocks=(blk("{-", "-}", nests=True),), literals=(
        lit("raw", "''", r"''(?!')", esc="re"), Q1('"'))),
    "Lean": Syntax(line=SL("--"), blocks=(blk("/-", "-/", nests=True),), literals=(QM('"'), PRIME_CHAR)),
    "OCaml": Syntax(blocks=(ML_NEST,), literals=(lit("raw", r"\{([a-z_]*)\|", "|{0}}"), QM('"'), PRIME_CHAR)),
    "Standard ML": Syntax(blocks=(ML_NEST,), literals=(lit("skip", r'#"(?:\\.|[^"\\])"'), QM('"'))),
    "F#": Syntax(line=SL("//"), blocks=(ML_NEST_NO_OP,), literals=(
        lit("raw", E('"""'), '"""'), lit("dbl", r'\$?@\$?"', '"'), QM('"'), PRIME_CHAR)),
    "F*": Syntax(line=SL("//"), blocks=(ML_NEST_NO_OP,), literals=(QM('"'), PRIME_CHAR)),
    "Rocq Prover": Syntax(blocks=(ML_NEST,), literals=(lit("dbl", '"', '"'),)),
    "Isabelle": Syntax(blocks=(ML_NEST,), literals=(lit("raw", '"', '"'), lit("raw", "\u2039", "\u203a"))),
    "Wolfram": Syntax(blocks=(ML_NEST,), literals=(QM('"'),)),
    "AppleScript": Syntax(line=SL("--", "#"), blocks=(ML_NEST,), literals=(Q1('"'),)),
    "Pascal": Syntax(line=SL("//"), blocks=(Block(r"\{(?!\$)", "}", False, "any", False),
                                             Block(r"\(\*(?!\$)", "*)", False, "any", False)),
                     literals=(lit("dbl1", "'", "'"),)),   # {$IFDEF} and (*$R+*) are compiler directives: code
    "TLA": Syntax(line=SL("\\*"), blocks=(ML_NEST,), literals=(Q1('"'),)),
    "WebAssembly": Syntax(line=SL(";;"), blocks=(blk("(;", ";)", nests=True),), literals=(Q1('"'),)),
    "Nim": Syntax(line=SL("#"), blocks=(blk("##[", "]##", nests=True), blk("#[", "]#", nests=True)), literals=(
        lit("raw", E('"""'), '"""'), lit("dbl1", r'(?<!\w)[rR]"', '"'), Q1('"'), C_CHAR)),
    "Julia": Syntax(line=SL("#"), blocks=(blk("#=", "=#", nests=True),), literals=(
        QM('"""'), QM('"'), QM("```"), QM("`"), lit("skip", r"(?<![\w)\]}'.])'(?:\\.[^'\s]*|[^\\'\n])'"))),
    "PowerShell": Syntax(line=SL("#"), blocks=(blk("<#", "#>"),), literals=(
        lit("raw", r'@"(?=\s*$)', r'^"@', esc="re"), lit("raw", r"@'(?=\s*$)", r"^'@", esc="re"),
        lit("esc", '"', '"', esc="`"), lit("dbl", "'", "'"))),
    "CoffeeScript": Syntax(line=SL("#"), start_blocks=(Block(r"###(?!#)", "###", False, "any", False),), literals=(
        lit("raw", "///", "///"), QM('"""'), QM("'''"), QM('"'), QM("'"))),
    "Elixir": Syntax(line=SL("#"), literals=(QM('"""'), QM("'''"), QM('"'), QM("'"), lit("skip", r"\?(?:\\.|\S)"))),
    "Erlang": Syntax(line=SL("%"), literals=(QM('"""'), QM('"'), Q1("'"), lit("skip", r"\$(?:\\.|.)"))),
    "Prolog": Syntax(line=SL("%"), blocks=(C_BLOCK,), literals=(
        lit("skip", r"(?<!\w)0'(?:\\.|''|.)"), QM('"'), Q1("'"))),
    "R": Syntax(line=SL("#"), literals=(QM('"'), QM("'"), lit("raw1", "`", "`"))),
    "Meson": Syntax(line=SL("#"), literals=(lit("raw", "'''", "'''"), Q1("'"))),
    "GAP": Syntax(line=SL("#"), literals=(lit("raw", E('"""'), '"""'), Q1('"'), C_CHAR)),
    "jq": Syntax(line=SL("#"), literals=(Q1('"'),)),
    "Cap'n Proto": Syntax(line=SL("#"), literals=(Q1('"'),)),
    "Open Policy Agent": Syntax(line=SL("#"), literals=(lit("raw", "`", "`"), Q1('"'))),
    "Janet": Syntax(line=SL("#"), literals=(lit("raw", r"(`+)", "{0}"), QM('"'))),
    **{lang: Syntax(line=SL("#"), literals=PY_LIKE) for lang in ("Starlark", "Mojo", "Sage", "Vyper", "GDScript")},
    **{lang: Syntax(line=SL(";"), blocks=(blk("#|", "|#", nests=True),), literals=(
        lit("skip", r"#\\(?:x[0-9a-fA-F]+|[A-Za-z]+|.)"), QM('"'))) for lang in ("Common Lisp", "Scheme", "Racket")},
    "Emacs Lisp": Syntax(line=SL(";"), literals=(lit("skip", r"(?<![\w-])\?\\?."), QM('"'))),
    "Clojure": Syntax(line=SL(";"), literals=(lit("skip", r"\\(?:newline|space|tab|u[0-9a-fA-F]{4}|.)"), QM('"'))),
    "Fennel": Syntax(line=SL(";"), literals=(QM('"'),)),
    "Hy": Syntax(line=SL(";"), literals=(lit("raw", r"#\[(\w*)\[", "]{0}]"), QM('"'))),
    "CMake": Syntax(line=SL("#"), blocks=(Block(r"#\[(=*)\[", "]{0}]", False, "any", False),), literals=(
        lit("raw", r"\[(=*)\[", "]{0}]"), QM('"'))),
    "Nix": Syntax(line=SL("#"), blocks=(C_BLOCK,), literals=(lit("raw", "''", r"''(?![$'\\])", esc="re"), QM('"'))),
    "Alloy": c_like(line=("//", "--")),
    "AMPL": c_like(line=("#",)),
    # languages read at the start of each line only (see Syntax): their literals cannot be followed line by line
    **{lang: hash_like() for lang in ("Shell", "Nushell", "Makefile", "Dockerfile", "Crystal", "Tcl", "Awk", "sed",
                                      "Just", "Procfile", "Gnuplot", "Earthly", "BitBake", "GDB", "Gherkin", "NASL",
                                      "QMake", "RobotFramework")},
    "Perl": hash_like(start_blocks=(Block(r"=[A-Za-z]", r"=cut\b", False, "col0", True),
                                    Block(r"__(?:END|DATA)__\s*$", r"(?!)", False, "col0", False))),
    "Ruby": hash_like(start_blocks=(Block(r"=begin\b", r"=end\b", False, "col0", True),
                                    Block(r"__END__\s*$", r"(?!)", False, "col0", False))),
    "Raku": hash_like(start_blocks=(Block(r"=begin\b", r"^\s*=end\b", False, "re", True),)),
    "M4": Syntax(line=SL("#"), start=(r"dnl(?![\w])",), tracked=False),
    "MATLAB": Syntax(line=SL("%"), start_blocks=(Block(r"%\{", r"%\}", True, "alone", False),), tracked=False),
    "Scilab": Syntax(line=SL("//"), blocks=(C_BLOCK,), tracked=False),
    "Stata": Syntax(line=SL("//"), start=SL("*"), blocks=(C_BLOCK,), tracked=False),
    "SAS": Syntax(start_blocks=(Block(r"%?\*", r";", False, "re", False),), blocks=(C_BLOCK,), tracked=False),
    "Macaulay2": Syntax(line=SL("--"), blocks=(blk("-*", "*-"),), tracked=False),
    "Typst": Syntax(line=SL("//"), blocks=(C_BLOCK,), tracked=False),
    "Forth": Syntax(line=(r"\\(?=\s|$)",), blocks=(Block(r"\((?=\s)", ")", False, "any", False),), tracked=False),
    "Fortran": Syntax(line=SL("!"), tracked=False),
    "Ada": Syntax(line=SL("--"), tracked=False),
    "VHDL": Syntax(line=SL("--"), blocks=(C_BLOCK,), tracked=False),
    "COBOL": Syntax(line=SL("*>"), column=((6, "*/"),), tracked=False),
    "Assembly": Syntax(line=SL(";", "//", "#"), start=SL("@"), blocks=(C_BLOCK,), tracked=False, code_first=(
        r"#\s*(?:include|define|undef|ifn?def|if|else|elif|endif|error|warning|pragma|line)\b",)),
    "LLVM": Syntax(line=SL(";"), tracked=False),
    "SMT": Syntax(line=SL(";"), tracked=False),
    "PureBasic": Syntax(line=SL(";"), tracked=False),
    "MLIR": Syntax(line=SL("//"), tracked=False),
    "Mermaid": Syntax(line=SL("%%"), tracked=False),
    "Batchfile": Syntax(start=(r"@?rem(?![\w])", E("::")), tracked=False),
    "VBScript": Syntax(line=SL("'"), start=(r"rem(?![\w])",), tracked=False),
    "Visual Basic .NET": Syntax(line=SL("'"), start=(r"rem(?![\w])",), tracked=False),
    "Vim script": Syntax(line=SL('"', "#"), tracked=False),
    "HCL": Syntax(line=SL("#", "//"), blocks=(C_BLOCK,), tracked=False),
    "NSIS": Syntax(line=SL(";", "#"), blocks=(C_BLOCK,), tracked=False),
    "Inno Setup": Syntax(line=SL(";", "//"), tracked=False),
    "AutoHotkey": Syntax(line=SL(";"), blocks=(C_BLOCK,), tracked=False),
    # markup and templates: their comments may follow markup anywhere on a line; they hold no literals to follow
    "HTML": Syntax(blocks=(HTML_BLOCK, blk("<%#", "%>"), blk("@*", "*@"), blk("<%!--", "--%>"))),
    "XSLT": Syntax(blocks=(HTML_BLOCK,)),
    **{lang: Syntax(line=SL("//"), start_blocks=(C_BLOCK,), blocks=(HTML_BLOCK,)) for lang in ("Vue", "Svelte", "Astro")},
    **{lang: Syntax(blocks=(blk("{#", "#}"), HTML_BLOCK)) for lang in ("Jinja", "Nunjucks")},
    "Twig": Syntax(line=SL("//"), blocks=(blk("{#", "#}"), C_BLOCK, HTML_BLOCK)),
    "Blade": Syntax(line=SL("//"), blocks=(blk("{{--", "--}}"), C_BLOCK, HTML_BLOCK)),
    "Handlebars": Syntax(blocks=(blk("{{!--", "--}}"), blk("{{!", "}}"), HTML_BLOCK)),
    "Mustache": Syntax(blocks=(blk("{{!", "}}"),)),
    "EJS": Syntax(blocks=(blk("<%#", "%>"), HTML_BLOCK)),
    "Liquid": Syntax(blocks=(Block(r"\{%-?\s*comment\s*-?%\}", r"\{%-?\s*endcomment\s*-?%\}", False, "re", False),
                             Block(r"\{%-?\s*#", r"-?%\}", False, "re", False), HTML_BLOCK)),
    "Go Template": Syntax(blocks=(Block(r"\{\{-?\s*/\*", r"\*/\s*-?\}\}", False, "re", False), HTML_BLOCK)),
    "FreeMarker": Syntax(blocks=(blk("<#--", "-->"), HTML_BLOCK)),
    "ASP.NET": Syntax(blocks=(blk("<%--", "--%>"), HTML_BLOCK)),
    "Mako": Syntax(line=SL("##"), blocks=(blk("<%doc>", "</%doc>"), HTML_BLOCK)),
}
# An extension several languages share counts as Other, and Other is otherwise not code (NOT_CODE). One whose every
# sharer comments compatibly still holds code, drawn as Other: a header (.h) is C, C++ or Objective-C, which all
# comment as C does; .m is Objective-C or MATLAB (// and %, /* */ and %{ %}, but not Mathematica's (* *), which
# would take a function-pointer call such as (*handler)(x) for a comment); .fs is F#, Forth or a GLSL fragment
# shader; .v is Verilog or Rocq.
SHARED_CODE = {
    ".h": SYNTAXES["C++"],
    ".m": Syntax(line=SL("//", "%"), start_blocks=(C_BLOCK, Block(r"%\{", r"%\}", True, "alone", False)),
                 tracked=False),
    ".fs": Syntax(line=(E("//"), r"\\(?=\s|$)"), start_blocks=(ML_NEST_NO_OP, C_BLOCK), tracked=False),
    ".v": Syntax(line=SL("//"), start_blocks=(C_BLOCK, ML_NEST), tracked=False),
}
FIXED_FORM = {".f", ".f77", ".for", ".fpp"}   # fixed-form Fortran, where C, c, * or ! in column 1 is a comment
READERS = {}


def counts_as_code(path, lang):
    """Whether a file of this language at this path holds lines of code (see NOT_CODE and SHARED_CODE)."""
    return bool(lang) and (lang not in NOT_CODE or lang == OTHER and os.path.splitext(path.lower())[1] in SHARED_CODE)


def reader_for(lang, path):
    """The reader of a file of this language at this path, and a key naming it: files read alike share a key, so
    a reading of one file version serves every path it stands at (see Version)."""
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    ext = os.path.splitext(name)[1]
    style = literate_style(name)
    if style:
        key = (lang, style)
    elif lang in ("Python", "Cython"):
        key = ("Python",)
    elif ext == ".sass" or lang in ("Pug", "Slim", "Haml"):
        key = (lang, ext if ext == ".sass" else "")
    elif lang == "Fortran" and ext in FIXED_FORM:
        key = (lang, "fixed")
    elif lang == OTHER:
        key = (lang, ext)
    else:
        key = (lang,)
    reader = READERS.get(key)
    if reader is None:
        if style:
            reader = Literate(reader_for(lang, "x")[0], style)
        elif key == ("Python",):
            reader = PythonReader()
        elif ext == ".sass":
            reader = Indented(r"/\*|//")
        elif lang in ("Pug", "Slim", "Haml"):
            reader = Indented({"Pug": r"//", "Slim": r"/", "Haml": r"-#|/"}[lang])
        elif key[1:] == ("fixed",):
            reader = Lines(Syntax(line=SL("!"), column=((0, "Cc*!"),), tracked=False))
        elif lang in ("JavaScript", "TypeScript", "QML"):
            reader = JsLines(Syntax(blocks=(C_BLOCK,), literals=(Q1("'"), Q1('"'))))
        elif lang == "PHP":
            reader = PhpLines(SYNTAXES["PHP"])
        else:
            syntax = SHARED_CODE.get(ext) if lang == OTHER else SYNTAXES.get(lang)
            reader = Lines(syntax or Syntax())
        READERS[key] = reader
    return reader, key


class LineKinds:
    """Consecutive lines of one language read one at a time, as its line reader reads them, from a file's start (or,
    with at_start False, from part way through one): kind(line) is code, comment or blank. Python's is PyLines, since
    the tokenizer reads whole statements (see read_lines), which is how coderprint reads every file."""

    def __init__(self, lang, path="", at_start=True):
        reader = reader_for(lang, path or "x")[0]
        self.reader = reader.fallback or reader
        self.state = self.reader.initial if at_start else self.reader.middle

    def kind(self, line):
        kind, self.state = self.reader.read(line, self.state)
        return KINDS[kind]


def read_lines(reader, get, n, eol):
    """How every line of a file reads, as its reader reads the whole file: (kinds, one byte a line; the state at
    each boundary, or None where every state is None; whether the reading is exact, not the fallback's)."""
    try:
        kinds, states, _ = reader.session(get, n, eol, 0, reader.initial, never)
        exact = reader.exact
        first = reader.initial
    except ReadFailed:
        fallback = reader.fallback
        kinds, states, _ = fallback.session(get, n, eol, 0, fallback.initial, never)
        exact, first = False, fallback.initial
    states = [first] + states
    return bytes(kinds), (None if all(x is None for x in states) else states), exact


def state_at(states, k):
    return None if states is None else states[k]


def read_edited(reader, old, get, n, eol, edits):
    """How the lines of a new file version read, from the old version's reading (old: kinds and states by reader)
    and the edits that made one from the other, [(old start, old end, new start, new end)] in order: the new file
    is read only from the last boundary before each edit where a reading can start, until its reading agrees with
    the old one again, and every other line reads as it did. The result is the whole file's reading, line for line
    (see LineReader). Raises ReadFailed as the reader does."""
    old_kinds, old_states = old
    old_n, m = len(old_kinds), len(edits)
    kinds = bytearray(n)
    held = [None if old_states is None else [None] * (n + 1)]   # the states, None while every one is None
    shift = [0]   # a new line's index less its old one, past the first k edits
    for o_start, o_end, n_start, n_end in edits:
        shift.append(shift[-1] + (n_end - n_start) - (o_end - o_start))
    if held[0] is not None:
        held[0][0] = old_states[0]
    j = e = 0   # read up to boundary j of the new file, past the first e edits

    def behind(edit, k):
        """Whether an edit lies wholly before boundary k: its new lines before it, or, when it only deletes, at it."""
        return edit[3] <= k and (edit[2] < k or edit[2] == edit[3])

    def copy(start, end, by):   # lines unchanged, read as they were
        if end > start:
            kinds[start:end] = old_kinds[start - by:end - by]
            if old_states is not None:
                held[0][start + 1:end + 1] = old_states[start + 1 - by:end + 1 - by]

    while e < m:
        n_start = edits[e][2]
        b = n_start   # the last boundary before the edit, and not before j, where a reading can start
        while b > j and state_at(old_states, b - shift[e]) == UNREAD:
            b -= 1
        copy(j, b, shift[e])
        passed = [e]

        def agrees(k, state):
            """Whether boundary k is past the edits begun and outside every edit, with the old reading's state."""
            while passed[0] < m and behind(edits[passed[0]], k):
                passed[0] += 1
            if passed[0] == e or (passed[0] < m and edits[passed[0]][2] < k):
                return False
            back = k - shift[passed[0]]
            return state != UNREAD and 0 <= back <= old_n and state_at(old_states, back) == state

        start = state_at(held[0], b)
        if agrees(b, start):   # an edit that only deletes, and leaves the reading as it was
            j, e = b, passed[0]
            continue
        got, got_states, k = reader.session(get, n, eol, b, start, agrees)
        kinds[b:k] = bytes(got)
        if held[0] is None and any(x is not None for x in got_states):
            held[0] = [None] * (n + 1)
        if held[0] is not None:
            held[0][b + 1:k + 1] = got_states
        j, e = k, (passed[0] if k < n else m)
    copy(j, n, shift[m])
    return bytes(kinds), held[0]
