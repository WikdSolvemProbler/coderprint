# coderprint's the line readers, which tell code from comments and blank lines. coderprint.py runs this file as part
# of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


# ---------------------------------------------------------------- lines of code

# A line of code is a line of a file in a programming or markup language that is neither blank nor a comment.
# Prose (Markdown, TeX), data (YAML, TOML) and files no language claims are never code.
NOT_CODE = {"Markdown", "TeX", "YAML", "TOML", OTHER}
BLANK, COMMENT, CODE = 0, 1, 2   # how a line reads, one byte a line
KINDS = ("blank", "comment", "code")
UNREAD = "unread"   # the state at a boundary no reading can start from: inside a Python statement (see PythonReader)
# A block comment: its opening as a regular expression; its closing, a plain string that may name the opening's
# group as {0} (Lua's --[==[ closes at ]==]), or a regular expression for the modes that need one; whether it nests;
# where it closes (mode: any, anywhere after its opening; re, at the first match of a regular expression; col0, at
# a line starting with its closing, as Ruby's =end, and then it opens only in column 1 too; alone, on a line holding
# nothing else, as MATLAB's %}, and it opens only alone as well); and whether the rest of the closing line is
# comment too (Ruby's =end, Perl's =cut).
Block = namedtuple("Block", "open close nests mode rest")
# A literal, whose inside is never a comment and whose lines are code: esc ends at its closing unless its escape
# comes before it, dbl at a closing not doubled (Pascal's 'it''s'), both at a closing neither doubled nor escaped
# (SQL's), raw at its closing whatever comes before it (or at a regular expression's match, with esc "re"); esc1,
# dbl1, both1 and raw1 end with their line as well, unless an escape carries one on (C's backslash before a
# newline), and the others run on across lines. A skip is code read in one piece (a character literal); eol runs
# to the end of its line (Zig's \\ lines); here is a heredoc, whose body starts on the next line and ends at a line
# starting with its name (PHP's <<<EOT), which the opening's group holds.
Literal = namedtuple("Literal", "kind open close esc")
E = re.escape   # a plain string as a regular expression


def lit(kind, opening, closing="", esc="\\"):
    return Literal(kind, opening, closing, esc)


def blk(opening, closing, nests=False, mode="any", rest=False):
    """A block comment whose opening is a plain string (see Block)."""
    return Block(E(opening), closing, nests, mode, rest)


class Syntax:
    """How one language writes comments and literals, as its line reader (Lines) reads them: line comments that may
    follow code (line, regular expressions), comments only at a line's start (start), block comments that may follow
    code (blocks) or open only at a line's start (start_blocks), the literals whose insides are never comments
    (literals), lines that start like a comment but are code (code_first: PHP's #[ attributes, the C preprocessor in
    assembly), and characters that make a line a comment in a given column (column: fixed-form Fortran's C in column
    1, COBOL's * in column 7). A tracked language is read whole, literal by literal, so a block comment opened after
    code is seen (int x; /* ...) and a literal's lines are code whatever they hold. An untracked one, whose literals
    cannot be told apart line by line with certainty (Perl's and Ruby's heredocs and regular expressions, MATLAB's
    transpose, a shell's quoting), is read only at the start of each line and after a comment that closes on it:
    the conservative approximation, which counts as code a comment it cannot see there."""

    def __init__(self, line=(), start=(), blocks=(), start_blocks=(), literals=(), code_first=(), column=(),
                 tracked=True, exits=None):
        self.tracked, self.column = tracked, column
        self.blocks = list(start_blocks) + list(blocks)
        self.start_count = len(start_blocks)
        self.literals = list(literals) if tracked else []
        parts = ["(?P<B%d>%s)" % (k, b.open) for k, b in enumerate(self.blocks) if k >= self.start_count]
        parts += ["(?P<S%d>%s)" % (k, f.open) for k, f in enumerate(self.literals)]
        if exits:
            parts.append("(?P<X>%s)" % exits)
        if line:
            parts.append("(?P<L>%s)" % "|".join(line))
        self.code_re = re.compile("|".join(parts)) if parts else None
        self.exit_re = re.compile(exits) if exits else None
        self.start_re = re.compile("(?i)(?:%s)" % "|".join(start)) if start else None
        self.first_re = re.compile("(?:%s)" % "|".join(code_first)) if code_first else None
        self.open_res = [re.compile(b.open) for b in self.blocks]
        self.close_res = [re.compile(b.close) if b.mode != "any" else None for b in self.blocks]
        self.inside_res = {}


def closing(form, group):
    """A block's or literal's closing, filled in from its opening's group (Lua's ]==], C++'s )delim")."""
    return form.close.replace("{0}", group or "") if "{0}" in form.close else form.close


def inner(m):
    """The first group inside the alternative the master pattern matched (see Syntax), or None."""
    k = m.lastindex
    if k is None or k + 1 > m.re.groups or m.start(k + 1) < 0 or m.start(k + 1) > m.end(k):
        return None
    return m.group(k + 1)


def never(k, state):
    return False


class LineReader:
    """A reader that reads a file line by line, each line's reading depending only on the line and the state the
    line before it left: None in plain code, or a tuple naming what is open. Every boundary between two lines can
    start a reading, so two readings of a file agree on every line after a boundary where their states agree.
    initial is the state at a file's start; middle the one assumed where a reading must start part way through a
    file with nothing known of what is open there (see LineKinds)."""
    initial = middle = None
    exact = True
    fallback = None

    def read(self, line, state):
        raise NotImplementedError

    def session(self, get, n, eol, b, state, stop):
        """Reads lines b, b + 1 and on (get(i) gives line i as text) from state, until stop(k, state) says so at a
        boundary k: (kinds of lines b to k - 1, states at boundaries b + 1 to k, k)."""
        kinds, states, read = [], [], self.read
        k = b
        while k < n:
            kind, state = read(get(k), state)
            kinds.append(kind)
            states.append(state)
            k += 1
            if stop(k, state):
                break
        return kinds, states, k


class Lines(LineReader):
    """The line reader for a language's Syntax."""

    def __init__(self, syntax):
        self.syntax = syntax

    def read(self, line, state, bare=None):
        """How line reads, given the state the line before left: (kind, the state it leaves). bare, a list, gets the
        line's code with its literals and comments taken out."""
        s = line[1:] if line[:1] == "\ufeff" else line   # a byte order mark before a file's first line
        if not s.strip():
            return BLANK, state
        code, pos = False, 0
        if state is None:
            start = self.start(s, bare)
            if start is None:
                return COMMENT, None
            code, state, pos = start
        code, state, _ = self.scan(s, pos, state, code, bare)
        return (CODE if code else COMMENT), state

    def start(self, s, bare=None):
        """The start of a line in plain code: None when that alone makes it a comment, else (whether it read code,
        the state, where to read on)."""
        syn, n = self.syntax, len(s)
        for col, chars in syn.column:
            if len(s) > col and s[col] in chars:
                return None
        pos = n - len(s.lstrip())
        m = syn.first_re.match(s, pos) if syn.first_re else None
        if m:
            if bare is not None:
                bare.append(m.group())
            return True, None, m.end()
        for k in range(syn.start_count):
            b = syn.blocks[k]
            m = syn.open_res[k].match(s, pos)
            if m and (b.mode != "col0" or pos == 0) and (b.mode != "alone" or not s[m.end():].strip()):
                return False, ("b", k, 1, closing(b, m.group(1) if m.re.groups else None), False), m.end()
        if syn.start_re and syn.start_re.match(s, pos) and not (syn.code_re and syn.code_re.match(s, pos)):
            return None
        return False, None, pos

    def scan(self, s, pos, state, code, bare):
        """Reads s from pos on in state: (whether it held code, the state at its end, where the reading stopped, which
        is the end unless an exit stopped it, as PHP's ?> does)."""
        syn, n = self.syntax, len(s)
        while True:
            if state is None:
                if pos >= n or not syn.code_re:
                    if s[pos:].strip():
                        code = True
                        if bare is not None:
                            bare.append(s[pos:])
                    return code, None, n
                if syn.tracked:
                    m = syn.code_re.search(s, pos)
                elif code:   # untracked: nothing after code is read
                    return code, None, n
                else:
                    m = syn.code_re.match(s, n - len(s[pos:].lstrip()))
                end = m.start() if m else n
                if s[pos:end].strip():
                    code = True
                    if bare is not None:
                        bare.append(s[pos:end])
                if not m:
                    return code, None, n
                group = m.lastgroup
                if group == "L":
                    if syn.exit_re:   # PHP: a line comment ends where PHP does
                        x = syn.exit_re.search(s, m.end())
                        if x:
                            return code, None, x.start()
                    return code, None, n
                if group == "X":
                    return code, None, m.start()
                k = int(group[1:])
                if group[0] == "B":
                    state, pos = ("b", k, 1, closing(syn.blocks[k], inner(m)), False), m.end()
                    continue
                f = syn.literals[k]
                code = True
                if bare is not None:
                    bare.append(" ")
                if f.kind == "skip":
                    pos = m.end()
                elif f.kind == "eol":
                    return code, None, n
                elif f.kind == "here":
                    return code, ("h", inner(m) or ""), n
                else:
                    state, pos = ("s", k, closing(f, inner(m))), m.end()
            elif state[0] == "b":
                end = self.inside(s, pos, state)
                if isinstance(end, tuple):
                    return code, end, n
                rest = syn.blocks[state[1]].rest
                state, pos = None, end
                if rest:
                    return code, None, n
            elif state[0] == "s":
                f = syn.literals[state[1]]
                end = self.literal_end(s, pos, f, state[2])
                if end < 0:
                    if s[pos:].strip():
                        code = True
                    if f.kind[-1] == "1":
                        # a literal of one line ends with it, unless an escape carries it on (C's backslash)
                        tail = s.rstrip("\r")
                        run = len(tail) - len(tail.rstrip(f.esc)) if f.kind in ("esc1", "both1") and f.esc else 0
                        state = state if run % 2 else None
                    return code, state, n
                code, state, pos = True, None, end
            else:   # ("h", name): a heredoc's body, which a line starting with its name ends
                t = s.lstrip()
                name, code = state[1], True
                after = t[len(name):len(name) + 1]
                if name and t.startswith(name) and not (after.isalnum() or after == "_"):
                    state, pos = None, n - len(t) + len(name)
                    continue
                return code, state, n

    def inside(self, s, pos, state):
        """Where the block comment state names ends in s, searching from pos and counting the comments nested inside
        it where they nest: the position after its closing, or the state still open at the line's end."""
        syn = self.syntax
        _, k, depth, closer, jsx = state
        b = syn.blocks[k]
        if b.mode in ("col0", "alone") and pos:
            return state   # these close only on a line of their own, not on the line that opens them
        if b.mode == "col0":
            m = syn.close_res[k].match(s)
            return m.end() if m else state
        if b.mode == "alone":
            t = s.strip()
            if syn.close_res[k].fullmatch(t):
                return len(s) if depth == 1 else ("b", k, depth - 1, closer, jsx)
            if b.nests and syn.open_res[k].fullmatch(t):
                return ("b", k, depth + 1, closer, jsx)
            return state
        if b.mode == "re":
            m = syn.close_res[k].search(s, pos)
            return m.end() if m else state
        opener = syn.open_res[k] if b.nests else None
        while True:
            c = s.find(closer, pos)
            o = opener.search(s, pos) if opener else None
            if o and (c < 0 or o.start() < c):
                depth, pos = depth + 1, o.end()
            elif c < 0:
                return ("b", k, depth, closer, jsx)
            else:
                depth, pos = depth - 1, c + len(closer)
                if not depth:
                    if jsx:   # JSX's {/* ... */}: the brace closing the comment's braces is not code
                        rest = s[pos:].lstrip()
                        if rest.startswith("}"):
                            pos = len(s) - len(rest) + 1
                    return pos

    def literal_end(self, s, pos, f, closer):
        """Where a literal of form f, closing at closer, ends in s, searching from pos: the position after it, or -1."""
        if f.kind in ("raw", "raw1"):
            if f.esc == "re":
                m = re.compile(closer).search(s, pos)
                return m.end() if m else -1
            k = s.find(closer, pos)
            return k + len(closer) if k >= 0 else -1
        key = (f.kind, closer, f.esc)
        pattern = self.syntax.inside_res.get(key)
        if pattern is None:
            doubled = E(closer) * 2 + "|" if f.kind in ("dbl", "dbl1", "both", "both1") else ""
            escaped = E(f.esc) + r"[\s\S]|" if f.kind in ("esc", "esc1", "both", "both1") and f.esc else ""
            pattern = self.syntax.inside_res[key] = re.compile(escaped + doubled + E(closer))
        for m in pattern.finditer(s, pos):
            if m.group() == closer:
                return m.end()
        return -1


JS_REGEX = re.compile(r"/(?![*/])(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\[\n])+/[A-Za-z]*")
JS_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw", "yield", "await",
            "instanceof", "export", "default"}
JS_CODE = re.compile(r"(?P<J>\{(?=/\*))|(?P<B>/\*)|(?P<L>//)|(?P<Q>['\"])|(?P<T>`)|(?P<R>/)|(?P<O>\{)|(?P<C>\})")
JS_TEXT = re.compile(r"\\[\s\S]|`|\$\{")


class JsLines(Lines):
    """JavaScript's and TypeScript's reader: Lines for their comments and quoted strings, and besides a template
    literal's text and its ${...} expressions, nested to any depth, a regular expression literal (told from a
    division by what comes before it, as a parser tells them), and JSX's comment {/* ... */}. Its state is None, or
    (frames, inner): the templates and expressions open around the reading (a template as "`", an expression as the
    number of braces open in it), and the comment or quoted string open inside them."""

    def read(self, line, state, bare=None):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        frames, inner_state = state if state is not None else ((), None)
        n = len(s)
        pos = n - len(s.lstrip())
        code = False
        if inner_state is None and not frames and s.startswith("#!", pos):
            return COMMENT, None   # a script's first line
        last = ""   # the code before pos on this line, for telling a regular expression from a division
        while pos < n:
            if inner_state is not None:
                if inner_state[0] == "b":
                    end = self.inside(s, pos, inner_state)
                    if isinstance(end, tuple):
                        inner_state = end
                        break
                    inner_state, pos = None, end
                else:
                    end = self.literal_end(s, pos, self.syntax.literals[inner_state[1]], inner_state[2])
                    code = True
                    if end < 0:
                        tail = s.rstrip("\r")
                        run = len(tail) - len(tail.rstrip("\\"))
                        inner_state = inner_state if run % 2 else None
                        break
                    inner_state, pos, last = None, end, "a"
                continue
            if frames and frames[-1] == "`":   # a template's text
                m = JS_TEXT.search(s, pos)
                if m or s[pos:].strip():
                    code = True
                if not m:
                    break
                pos = m.end()
                if m.group() == "`":
                    frames, last = frames[:-1], "a"
                elif m.group() == "${":
                    frames, last = frames + (0,), "("
                continue
            m = JS_CODE.search(s, pos)
            end = m.start() if m else n
            text = s[pos:end].rstrip()
            if text.strip():
                code, last = True, text
            if not m:
                break
            g, pos = m.lastgroup, m.end()
            if g == "J":   # {/* at a line's start: JSX's comment, whose braces are not code
                if not code:
                    inner_state, pos = ("b", 0, 1, "*/", True), pos + 2
                    continue
                g = "O"
            if g == "B":
                inner_state = ("b", 0, 1, "*/", False)
            elif g == "L":
                break
            elif g == "Q":
                code, inner_state = True, ("s", 0 if m.group() == "'" else 1, m.group())
            elif g == "T":
                code, frames = True, frames + ("`",)
            elif g == "R":
                word = re.search(r"[\w$]+$", last)
                regex = JS_REGEX.match(s, m.start())
                if regex and (not last or last[-1] in "(,=:[!&|?{};+-*%<>~^" or (word and word.group() in JS_WORDS)):
                    pos = regex.end()
                code, last = True, "a" if regex else "/"
            elif g == "O":
                code, last = True, "{"
                if frames:
                    frames = frames[:-1] + (frames[-1] + 1,)
            else:   # }
                code, last = True, "}"
                if frames:
                    frames = frames[:-1] if frames[-1] == 0 else frames[:-1] + (frames[-1] - 1,)
        state = None if not frames and inner_state is None else (frames, inner_state)
        return (CODE if code else COMMENT), state


PHP_OPEN = re.compile(r"(?i)<\?(?:php(?=\s|$)|=|(?=\s|$))|<!--")


class PhpLines(Lines):
    """PHP's reader: a PHP file starts as HTML, whose comments are <!-- -->, until <?php (or <?=) opens PHP, whose
    comments and literals Lines reads, until ?> closes it again, even inside a line comment. Its state is Lines'
    inside PHP, or ("html",) or ("html-comment",) outside it."""
    initial, middle = ("html",), None

    def read(self, line, state, bare=None):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        n, pos, code = len(s), 0, False
        while pos < n:
            if state == ("html-comment",):
                k = s.find("-->", pos)
                if k < 0:
                    break
                state, pos = ("html",), k + 3
            elif state == ("html",):
                m = PHP_OPEN.search(s, pos)
                if s[pos:m.start() if m else n].strip():
                    code = True
                if not m:
                    break
                pos = m.end()
                if m.group() == "<!--":
                    state = ("html-comment",)
                else:
                    code, state = True, None
            else:
                if state is None and not s[:pos].strip():   # PHP from the line's start
                    start = self.start(s, bare)
                    if start is None:
                        break
                    here, state, pos = start
                    code = code or here
                here, state, stop = self.scan(s, pos, state, False, bare)
                code = code or here
                if stop >= n:
                    break
                state, pos = ("html",), stop + 2
        return (CODE if code else COMMENT), state


class PyLines(LineReader):
    """Python's line reader, for a file Python's tokenizer cannot read (see PythonReader): docstrings and other
    strings standing alone as statements are block comments, and a triple-quoted string opened after code
    (x = \"\"\") is code to its end, its closing quotes opening nothing. A string starting its own line inside a call
    or a list reads as a docstring, where the tokenizer would know better."""
    exact = False

    def read(self, line, state):
        s = line.strip()
        if s[:1] == "\ufeff":
            s = s[1:].lstrip()
        if not s:
            return BLANK, state
        if state is not None and state[0] == "str":   # inside a string opened after code: code to its end
            if state[1] in s:
                quote = open_string(s, state[1])
                return CODE, (("str", quote) if quote else None)
            return CODE, state
        code = False
        while True:
            if state is not None:   # inside a docstring
                k = s.find(state[1])
                if k < 0:
                    return (CODE if code else COMMENT), state
                s, state = s[k + 3:].strip(), None
                if not s:
                    return (CODE if code else COMMENT), None
            doc = DOCSTRING.match(s)
            if not doc:
                break
            quote, s = doc.group(1), s[doc.end():]
            state = ("doc", quote)
        if s.startswith("#"):
            return (CODE if code else COMMENT), None
        if '"""' in s or "'''" in s:
            quote, header = open_string(s), HEADER_DOCSTRING.match(s)
            if quote and header and header.group(1) == quote and quote not in s[header.end():]:
                return CODE, ("doc", quote)   # def f(): """Doc... opens a docstring after the header's code
            if quote:
                return CODE, ("str", quote)
        return CODE, None


DOCSTRING = re.compile(r"""(?i)(?:[rubf]{1,2})?('''|\"\"\")""")
HEADER_DOCSTRING = re.compile(r"""(?:async\s+def|def|class)\b[^#]*:\s*(?:[rRuUbBfF]{1,2})?('''|\"\"\")""")


def open_string(s, quote=None):
    """The triple quote a line of Python leaves open at its end, given the one open at its start, or None. A #
    outside a string ends the line; a backslash escapes the character after it; an ordinary string stays on its
    line."""
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if quote:
            if c == "\\":
                i += 2
            elif s.startswith(quote, i):
                quote, i = None, i + 3
            else:
                i += 1
        elif c == "#":
            return None
        elif c in "'\"":
            if s.startswith(c * 3, i):
                quote, i = c * 3, i + 3
            else:
                i += 1
                while i < n and s[i] != c:
                    i += 2 if s[i] == "\\" else 1
                i += 1
        else:
            i += 1
    return quote


def token_types(*names):
    return {getattr(tokenize, name) for name in names if hasattr(tokenize, name)}


F_PARTS = token_types("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END")   # an f-string, read in parts (3.12 on)
F_START, F_END = token_types("FSTRING_START"), token_types("FSTRING_END")
T_START, T_END = token_types("TSTRING_START"), token_types("TSTRING_END")   # a template string (3.14 on)
BRACKETS = {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}
COMPOUND = {"def", "class", "if", "elif", "else", "for", "while", "try", "except", "finally", "with", "async", "match",
            "case"}   # the words that open a compound statement, whose header's colon a body may follow


class ReadFailed(Exception):
    """Python's tokenizer could not read a file."""


class PythonReader:
    """Python and Cython, read by Python's own tokenizer (tokenize), with Python's docstring rule: a statement that
    is only a string (a docstring, or a string standing alone as a block comment) is a comment; bytes are code. A
    reading starts where the tokenizer can be put exactly as the whole file would have it, errors included: where a
    statement ends outside any bracket, its state the indentation open there (the tuple of each level's leading
    whitespace); and inside a statement already known to be code, between the lines of its brackets ("(", the
    indentation, the brackets open, its first word) or of its triple-quoted string ('"', the same, and the string's
    opening). Every other boundary, inside a statement that may yet prove a docstring or inside an f-string, is
    UNREAD. A file the tokenizer cannot read (mixed tabs, a stray null byte) is read by PyLines instead,
    approximately."""
    initial = ()
    exact = True

    def __init__(self):
        self.fallback = PyLines()

    def session(self, get, n, eol, b, stack, stop):
        """Reads lines b and on, from boundary b in the state stack, until stop(k, state) says so at a boundary k
        where a reading can start: (kinds of lines b to k - 1, states at boundaries b + 1 to k, k). Raises
        ReadFailed where the tokenizer fails."""
        opened, first, pure, opening = [], "", None, ""
        if stack and stack[0] in ("(", '"'):   # inside a statement of code: its brackets, and perhaps a string
            opened, first, pure = list(stack[2]), stack[3], False
            opening = stack[4] if stack[0] == '"' else ""
            stack = stack[1]
        prefix = ["if 1:\n"] + [w + "if 1:\n" for w in stack[:-1]] + [stack[-1] + "pass\n"] if stack else []
        if pure is False:   # the statement's start, as far as the tokenizer's state goes: its word, brackets, string
            prefix.append((first or "0") + " " + "".join(opened) + opening + "\n")
        top, feed = len(prefix), {"next": b}

        def readline():
            if prefix:
                return prefix.pop(0)
            i = feed["next"]
            if i >= n:
                return ""
            feed["next"] = i + 1
            text = get(i)
            if i == 0 and text[:1] == "\ufeff":
                text = text[1:]
            return text + ("\n" if i < n - 1 or eol else "")

        marks, clean, levels, strings = set(), {}, list(stack), []   # strings: the f- and t-strings open
        k, shift = n, b - top - 1   # where the reading stops; a token's row, less shift, is its line
        # The statement being read: pure is None before its first token, "(" while it holds only parentheses, True
        # while only strings and parentheses, False once it holds code. held: the rows of its tokens while it may
        # still be only strings; exprs: those of the expressions in its f-strings' braces, which are code anyway.
        # opened: the brackets open in it; first: its first word, which may open a compound statement.
        held, exprs = [], []
        STRING, OP, NAME, NL, NEWLINE = tokenize.STRING, tokenize.OP, tokenize.NAME, tokenize.NL, tokenize.NEWLINE
        INDENT, DEDENT, skip = tokenize.INDENT, tokenize.DEDENT, (tokenize.COMMENT, tokenize.ENCODING, tokenize.ENDMARKER)

        def mark(rows):
            for a, z in rows:
                if a == z:
                    marks.add(a)
                else:
                    marks.update(range(a, z + 1))

        try:
            for tok in tokenize.generate_tokens(readline):
                t, text, a, z = tok[0], tok[1], tok[2][0] + shift, tok[3][0] + shift
                if z < b:
                    continue   # the prefix's own
                if t == NEWLINE or t == NL:
                    if t == NEWLINE or (not opened and not strings and pure is None):
                        if pure is True:
                            mark(exprs)
                        elif pure == "(":
                            mark(held)
                        pure, held, exprs, first, opened = None, [], [], "", []
                        clean[a + 1] = state = tuple(levels)
                    elif opened and not strings and pure is False:   # between the lines of a statement of code
                        clean[a + 1] = state = ("(", tuple(levels), "".join(opened), first)
                    else:
                        continue
                    if stop(a + 1, state):
                        k = a + 1
                        break
                    continue
                if t == INDENT:
                    levels.append(text)
                    continue
                if t == DEDENT:
                    if levels:
                        levels.pop()
                    continue
                if t in skip:
                    continue
                if t == OP and not opened and not strings and (text == ";" or text == ":" and first in COMPOUND):
                    if text == ":":   # a compound statement's header: a body may follow it on its line
                        marks.add(a)
                    if pure is True:
                        mark(exprs)
                    elif pure == "(":
                        mark(held)
                    pure, held, exprs, first = None, [], [], ""
                    continue
                if t == OP and text in BRACKETS:
                    if BRACKETS[text] > 0:
                        opened.append(text)
                    elif opened:
                        opened.pop()
                if t in F_START:
                    strings.append("f")
                elif t in T_START:
                    strings.append("t")
                if pure is None:
                    first = text if t == NAME else ""
                if pure is False:
                    if a == z:
                        marks.add(a)
                    else:
                        marks.update(range(a, z + 1))
                        quote = text.find(text[-1]) if t == STRING else -1
                        if quote >= 0 and text[quote:quote + 3] == text[-1] * 3 and not strings:
                            # inside a triple-quoted string of a statement of code: a reading can start there
                            state = None
                            for inner in range(max(a, b) + 1, z + 1):
                                clean[inner] = state = ('"', tuple(levels), "".join(opened), first,
                                                        text[:quote + 3])
                                if stop(inner, state):
                                    k = inner
                                    break
                            if k < n:
                                break
                else:
                    in_f = bool(strings) and "t" not in strings
                    if in_f or t in F_PARTS or (t == STRING and "b" not in text[:text.find(text[-1])].lower()):
                        pure = True
                        held.append((a, z))
                        if in_f and t not in F_PARTS:
                            exprs.append((a, z))
                    elif t == OP and text in "()" and not strings:
                        pure = pure or "("
                        held.append((a, z))
                    else:
                        mark(held)
                        mark(((a, z),))
                        pure, held, exprs = False, [], []
                if (t in F_END or t in T_END) and strings:
                    strings.pop()
        except (tokenize.TokenError, SyntaxError, ValueError, IndexError):
            raise ReadFailed() from None
        if pure is True:
            mark(exprs)
        elif pure == "(":
            mark(held)
        kinds = []
        for i in range(b, k):
            text = get(i)
            if i == 0 and text[:1] == "\ufeff":
                text = text[1:]
            kinds.append(BLANK if not text.strip() else CODE if i in marks else COMMENT)
        return kinds, [clean.get(j, UNREAD) for j in range(b + 1, k + 1)], k


class Indented(LineReader):
    """A reader for an indented syntax, whose comment runs over the lines indented beneath its first, whatever
    they hold (Sass's .sass files, Pug, Slim, Haml): state None, or the indentation of the comment's first line."""

    def __init__(self, markers):
        self.markers = re.compile(markers)

    def read(self, line, state):
        s = line[1:] if line[:1] == "\ufeff" else line
        if not s.strip():
            return BLANK, state
        indent = len(s) - len(s.lstrip())
        if state is not None and indent > state:
            return COMMENT, state
        if self.markers.match(s, indent):
            return COMMENT, indent
        return CODE, None


class Literate(LineReader):
    """A literate source, prose around code, whose prose reads as comment and code as its language reads it: Bird
    tracks (> at the start of a line) and \\begin{code} blocks in literate Haskell and Idris and LaTeX literate Agda
    (style tex), fenced blocks in Markdown and Typst literate Agda (md: a bare fence or ```agda holds code, a fence
    naming another language an example), src blocks in Org (org), and indented blocks in literate CoffeeScript
    (indent). Its state is (where the reading is: prose, code or example; the code reader's state)."""
    initial = ("prose", None)

    def __init__(self, code, style):
        self.code, self.style = code, style
        self.initial, self.middle = ("prose", code.initial), ("code", code.middle)

    def read(self, line, state):
        where, inside = state
        s = line.strip()
        if s[:1] == "\ufeff":
            s = s[1:].lstrip()
        if not s:
            return BLANK, state
        style = self.style
        if style == "tex":
            if line.startswith(">"):   # a Bird track: the rest of the line is code
                kind, inside = self.code.read(line[1:], inside)
                return kind, (where, inside)
            if s.startswith(("\\begin{code}", "\\end{code}")):
                return COMMENT, ("code" if s.startswith("\\begin") else "prose", inside)
        elif style == "md" and s.startswith("```"):
            info = s.strip("`").strip().lower()
            if info or where == "prose":   # a fence naming a language opens a block; a bare one only outside one
                return COMMENT, ("code" if info in ("", "agda") else "example", inside)
            return COMMENT, ("prose", inside)
        elif style == "org" and s.lower().startswith(("#+begin_src", "#+end_src")):
            return COMMENT, ("code" if s.lower().startswith("#+begin_src agda") else "prose", inside)
        elif style == "indent":
            if line.startswith(("    ", "\t")):
                kind, inside = self.code.read(line, inside)
                return kind, (where, inside)
            return COMMENT, state
        if where == "code":
            kind, inside = self.code.read(line, inside)
            return kind, (where, inside)
        return COMMENT, state


LITERATE = {".lhs": "tex", ".lidr": "tex", ".lagda": "tex", ".lagda.tex": "tex", ".lagda.md": "md",
            ".lagda.typ": "md", ".lagda.org": "org", ".litcoffee": "indent", ".coffee.md": "indent"}


def literate_style(path):
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return next((style for suffix, style in LITERATE.items() if name.endswith(suffix)), None)
