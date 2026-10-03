# coderprint's the lines of code standing at each head, and Rust's test code. coderprint.py runs this file as part of
# one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its own.


def read_head_code(repo_dir):
    """The lines of code on the default branch as it stands, read whole file by whole file with the readers the
    history is read with, so a line reads alike in both (see Standing). Rust code compiled only in tests counts as
    test code, wherever its file is: inline (rust_lines), or in the file of a module declared so out of line
    (rust_test_files, with the crate roots the repository's Cargo.toml files name). Left out: what counts_as_code
    leaves out, symbolic links and submodules, Git LFS pointers, generated files (generated_output), and the paths the
    default branch's .gitattributes marks (attributed). An empty repository, or one whose HEAD names no branch, has
    nothing standing at its head; a head that cannot be read for any other reason raises RuntimeError.

    With TRACE set (see Trace), each line of code carries the origin its history gave its file version, and a file
    version another account wrote (TRACE.seeded: a template's, or coderprint's own in a relay copy) is left out
    whole, as it is not the owner's."""
    head, trace = Standing(), TRACE
    try:
        run(["git", "-C", repo_dir, "rev-parse", "--quiet", "--verify", "HEAD^{tree}"])
    except RuntimeError as e:
        if "exited" not in str(e):   # out of time, or git could not start: the head is unknown, not missing
            raise
        return head
    listing = run(["git", "-C", repo_dir, "ls-tree", "-r", "-z", "--full-tree", "HEAD"]).decode("utf-8", "replace")
    files, manifests = [], []
    seeded = trace.seeded if trace is not None else ()
    known_at = trace.heads if trace is not None and not trace.broken else {}   # each head version's origins
    for item in listing.split("\x00"):
        meta, _, path = item.partition("\t")
        fields = meta.split()
        blob = len(fields) == 3 and fields[1] == "blob" and fields[0] not in LINKS
        lang = language_of(path) if blob else None
        if counts_as_code(path, lang):
            files.append((fields[2], path, lang))
        elif blob and path.rpartition("/")[2] == "Cargo.toml":
            manifests.append((fields[2], path))
    if not files:
        return head
    skip = attributed(repo_dir, "HEAD", {p for _, p, _ in files})
    if skip is None:
        head.unattributed, skip = True, set()
    files = [f for f in files if f[1] not in skip]
    if not any(lang == "Rust" for _, _, lang in files):
        manifests = []
    web, marked = {}, set()   # each HTML, CSS and JavaScript file's lines, kept until the sites are known
    rust, declared, roots = {}, [], set()   # each Rust file's test flag and place in head; see rust_test_files

    def handle(stream):
        for blob, path, lang in files:
            header = stream.readline().split()
            if len(header) < 3:
                continue
            body = stream.read(int(header[2]))
            stream.read(1)
            text = text_of(body)
            if text is None or body.startswith(b"version ") and lfs_pointer(split_lines(body, b"\n")[0]):
                continue
            # lines end at \n alone, as in the diffs read_added_code reads, so a line holding a form feed or U+2028
            # is one line in both and its text matches (splitlines would cut it in two)
            lines, eol = split_lines(text, "\n")
            if generated_head(lines.__getitem__, len(lines), lang):
                marked.add(path)
                continue
            if blob in seeded:   # another account's file version: none of its lines are the owner's
                continue
            test = is_test(path, lang)
            reader = reader_for(lang, path)[0]
            rows = None
            if lang == "Rust":
                known = len(declared)
                try:
                    kinds, rows = rust_lines(reader, lines, path, test, declared)
                    exact = reader.exact
                except Exception:   # a reading of scopes that went wrong: the file whole, by its path alone
                    del declared[known:]
                    rows = None
            if rows is None:
                kinds, _, exact = read_lines(reader, lines.__getitem__, len(lines), eol)
                rows = [(line_hash(t), test) for t, kind in zip(lines, kinds) if kind == CODE]
                exact = exact and lang != "Rust"
            known = known_at.get(blob)
            if known is not None and len(known) == len(lines):   # each line of code's origin, from its history
                origins = array("q", (known[i] for i, kind in enumerate(kinds) if kind == CODE))
            else:
                origins = None
            if lang in WEB_OUTPUT:
                web[path] = (rows, not exact, origins)
                continue
            start = len(head)
            head.add(rows, not exact, origins, path)
            if lang == "Rust":
                rust[path] = (test, start, len(head))
        for blob, path in manifests:
            header = stream.readline().split()
            if len(header) < 3:
                continue
            body = stream.read(int(header[2]))
            stream.read(1)
            roots.update(cargo_roots(path, body))

    git_lines(["git", "-C", repo_dir, "cat-file", "--batch"], handle,
              feed="".join(blob + "\n" for blob in [f[0] for f in files] + [m[0] for m in manifests]).encode())
    output = generated_output(set(web), marked) if marked else set()
    for path, (rows, rough, origins) in web.items():
        if path not in output:
            head.add(rows, rough, origins, path)
    for path in rust_test_files({p: t for p, (t, _, _) in rust.items()}, declared, roots):
        _, start, end = rust[path]   # a module compiled only in tests: its production lines are test code
        head.tests[start:end] = b"\x01" * (end - start)
    return head


# Rust: an attribute's start; a cfg attribute, outer or inner (#!); a #[path] naming a module's file; a module,
# declared out of line (mod name;) or inline, its body in braces; an item's first word after its visibility, and
# the words that start an item a comma cannot end (a where clause's or a generic list's commas are its own), where
# anything else under an attribute (a field, a variant, a match arm, an argument) ends at a comma of its own level.
RUST_ATTR = re.compile(r"#\s*!?\s*\[")
RUST_CFG = re.compile(r"#\s*(!?)\s*\[\s*cfg\s*\((.*)\)\s*\]", re.S)
RUST_PATH = re.compile(r'#\s*\[\s*path\s*=\s*"([^"]*)"\s*\]')
RUST_MOD = re.compile(r"(?:pub(?:\s*\([^)]*\))?\s+)?(?:unsafe\s+)?mod\s+(?:r#)?(\w+)\s*(;|\{|$)")
RUST_ITEM = re.compile(r"(?:pub(?:\s*\([^)]*\))?\s+|crate\s+)?(\w+)")
RUST_ITEMS = {"fn", "struct", "enum", "union", "impl", "trait", "mod", "use", "type", "const", "static", "extern",
              "unsafe", "async", "macro_rules", "let", "auto", "default", "safe"}
# A crate root, by Cargo's own layout: its submodules' files sit beside it (see rust_test_files)
RUST_ROOT_NAMES, RUST_ROOT_DIRS = ("lib.rs", "main.rs", "build.rs"), ("bin", "examples", "tests", "benches")
CARGO_TARGETS = {"lib", "bin", "example", "test", "bench"}


def rust_lines(reader, lines, path, test, declared):
    """A Rust file read with its reader (see Lines): (kinds, one byte a line; each line of code as [line_hash,
    whether it is test code]). A line is test code when the whole file is (test, by its path), or inside what is
    compiled only in tests (cfg_test): an item under an outer attribute such as #[cfg(test)] or #[cfg(all(test,
    unix))], from its first attribute to its end (its braces closed, a semicolon, or, for a field, a variant or a
    match arm, a comma of its own level), or everything of the module an inner #![cfg(test)] opens, the whole file
    at its top. Brackets and semicolons are read in each line's code alone, outside its strings, characters and
    comments. Each module declared out of line (mod name;) is added to declared as (path, the folders of the inline
    modules around it, its name, the file its #[path] gives or None, whether it is compiled only in tests)."""
    kinds, rows = bytearray(), []
    state = reader.initial
    level = 0         # brackets of every kind open before the line
    scope = None      # the test scope open: [the level it ends at, whether a comma of that level ends it]
    pending = None    # an attribute still open at a line's end: its text so far
    attrs, raw, first, at = [], [], 0, 0   # the attributes read for the item to come, their lines, first row, level
    inline = []       # the inline modules around: [folder, level of the body, entered, first row, line of the header]
    for n, text in enumerate(lines):
        bare = []
        kind, state = reader.read(text, state, bare)
        kinds.append(kind)
        code = "".join(bare)
        s = rest = code.strip()
        row = len(rows)
        if kind == CODE:
            rows.append([line_hash(text), test])
        if scope is not None and s and s[0] in ")]}" and level <= scope[0]:
            scope = None   # what held the item closes here, so the item ended before
        if pending is not None or RUST_ATTR.match(s):
            if pending is None and not attrs:
                first, at = row, level
            joined = s if pending is None else pending + " " + s
            raw.append(text)
            found = rust_attributes(joined)
            rest, pending = "", None
            if found is None:
                if len(joined) < 4000:   # read on, but not for ever
                    pending = joined
                else:
                    attrs, raw = [], []
            else:
                got, rest = found
                for a in got:
                    m = RUST_CFG.fullmatch(a)
                    if not re.match(r"#\s*!", a):
                        attrs.append(a)
                    elif m and scope is None and cfg_test(m.group(2)):   # inner: the module it opens, or the file
                        if inline and inline[-1][2] and inline[-1][1] == level:
                            start, scope = inline[-1][3], [level - 1, False]
                        elif level <= 0:
                            start, scope = 0, [level - 1, False]
                        else:
                            start, scope = row, [level - 1, False]
                        for r in rows[start:]:
                            r[1] = True
                if not attrs:
                    raw = []
        if rest:
            given, held = None, bool(attrs)
            if rest[0] in ")]}":
                attrs, raw = [], []   # attributes that end a block hold no item
            elif attrs:
                if scope is None and any(m and not m.group(1) and cfg_test(m.group(2))
                                         for m in map(RUST_CFG.fullmatch, attrs)):
                    word = RUST_ITEM.match(rest)
                    scope = [at, not (rest[0] == "{" or word is not None and word.group(1) in RUST_ITEMS)]
                    for r in rows[first:]:
                        r[1] = True
                p = RUST_PATH.search("\n".join(raw))
                given = p.group(1).replace("\\", "/") if p else None
                attrs, raw = [], []
            m = RUST_MOD.match(rest) if "mod" in rest else None
            if m and m.group(2) == ";":
                declared.append((path, tuple(i[0] for i in inline), m.group(1), given, test or scope is not None))
            elif m:   # an inline module's #[path] names a folder, which rust_test_files does not follow
                inline.append([None if given else m.group(1), level + 1, False, first if held else row, n])
        if scope is not None and kind == CODE:
            rows[row][1] = True
        level += (code.count("(") + code.count("[") + code.count("{")
                  - code.count(")") - code.count("]") - code.count("}"))
        while inline:
            top = inline[-1]
            if level >= top[1]:
                top[2] = True
                break
            if not top[2] and (top[4] == n or not s):
                break   # a header whose brace is still to come
            inline.pop()
        if scope is not None and level <= scope[0] and ("}" in code or rest.endswith(";")
                                                         or scope[1] and rest.endswith(",")):
            scope = None   # the item closed
    return bytes(kinds), rows


def rust_attributes(s):
    """The attributes a line of Rust code starts with, and what follows them; None while one is still open."""
    attrs = []
    while True:
        m = RUST_ATTR.match(s)
        if not m:
            return attrs, s
        depth = 0
        for i in range(m.end() - 1, len(s)):
            depth += (s[i] == "[") - (s[i] == "]")
            if not depth:
                break
        else:
            return None
        attrs.append(s[:i + 1])
        s = s[i + 1:].lstrip()


def cfg_test(predicate):
    """Whether code under #[cfg(predicate)] is compiled only when tests are: the predicate is false whenever test is,
    and not false always. It is worked out in Kleene's three-valued logic with every option but test unknown (unix,
    feature = "x", miri, an option given arguments), which is exact where the answer does not turn on how those
    options relate: all(test, unix) is test code, while any(test, feature = "x"), compiled whenever the feature is
    on, is production, and so is all(test, not(test)), which is never compiled. A predicate it cannot read counts
    as test code only when it is the word test itself, as it did before this reading. Nested to any depth."""
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[A-Za-z_]\w*|\S', predicate)
    try:
        return cfg_value(tokens, False) is False and cfg_value(tokens, True) is not False
    except ValueError:
        return predicate.strip() == "test"


def cfg_value(tokens, test):
    """A cfg predicate's value, as tokens, when test is as given: True, False or None when it turns on other options.
    Raises ValueError on what is not a predicate."""
    stack = [["all", []]]   # the predicate, as the one term of an all()
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t == ",":
            i += 1
        elif t == ")":
            if len(stack) < 2:
                raise ValueError("a ) with no (")
            op, values = stack.pop()
            if op == "all":
                value = False if False in values else True if all(v is True for v in values) else None
            elif op == "any":
                value = True if True in values else False if all(v is False for v in values) else None
            elif op == "not":
                if len(values) != 1:
                    raise ValueError("not() takes one predicate")
                value = None if values[0] is None else not values[0]
            else:   # an option given arguments, as version("1.80") is
                value = None
            stack[-1][1].append(value)
            i += 1
        elif t[0] == '"':
            stack[-1][1].append(None)
            i += 1
        elif t[0].isalpha() or t[0] == "_":
            after = tokens[i + 1] if i + 1 < n else ""
            if after == "(":
                stack.append([t, []])
                i += 2
            elif after == "=":   # a name and a value, as feature = "x" is (its string emptied or not)
                i += 3 if i + 2 < n and tokens[i + 2][0] == '"' else 2
                stack[-1][1].append(None)
            else:
                stack[-1][1].append(test if t == "test" else None)
                i += 1
        else:
            raise ValueError(t)
    if len(stack) != 1 or len(stack[0][1]) != 1:
        raise ValueError("not one predicate")
    return stack[0][1][0]


def cargo_roots(manifest, data):
    """The crate roots a Cargo.toml names by path, from the repository's top: [lib] path, each [[bin]], [[example]],
    [[test]] and [[bench]] path, and [package] build. Read with tomllib where Python has it; by its lines otherwise,
    or when tomllib refuses the file: a section's name and the path = "..." or build = "..." lines under it, the
    approximation, which misses a path written in an inline table."""
    folder = manifest.rpartition("/")[0]
    text = data.decode("utf-8", "replace")
    found, table = [], None
    if tomllib is not None:
        try:
            table = tomllib.loads(text)
        except ValueError:   # tomllib's TOMLDecodeError is a ValueError
            table = None
    if table is not None:
        for key in CARGO_TARGETS:
            got = table.get(key)
            for target in (got if isinstance(got, list) else [got]):
                if isinstance(target, dict):
                    found.append(target.get("path"))
        package = table.get("package")
        if isinstance(package, dict):
            found.append(package.get("build"))
    else:
        section = None
        for line in text.splitlines():
            m = re.match(r"\s*\[\[?\s*([\w.-]+)\s*\]\]?\s*(?:#.*)?$", line)
            if m:
                section = m.group(1)
                continue
            m = re.match(r"\s*(path|build)\s*=\s*[\"']([^\"']*)[\"']", line)
            if m and (m.group(1) == "path" and section in CARGO_TARGETS or m.group(1) == "build"
                      and section == "package"):
                found.append(m.group(2))
    return {posixpath.normpath(posixpath.join(folder, p.replace("\\", "/")))
            for p in found if isinstance(p, str) and p}


def rust_test_files(files, declared, roots):
    """The Rust files at the head that are compiled only in tests because a module compiled only in tests holds them
    (files: {path: whether its path makes it test code}; declared: from rust_lines; roots: from cargo_roots). A
    module declared out of line in a test scope, or in a file compiled only in tests, has its file found as rustc
    finds it: name.rs, else name/mod.rs, in the declaring file's folder when that file is a crate root, a mod.rs or a
    file a #[path] named, and in the folder named after it otherwise, under the folders of any inline modules around
    the declaration, or where its #[path] says; and so on down through that file's own modules. A declaration inside
    an inline module given a #[path] of its own is not followed. A file a production module also declares stays
    production. A crate root is one a Cargo.toml names, or by Cargo's layout a lib.rs, main.rs or build.rs or a file
    directly in a bin, examples, tests or benches folder, unless a module declares it. As a backstop for modules
    made in ways not read here (by a macro, or include!), a file in the folder of a test module's file that no
    declaration names is test code as well. Returns the files that are test code only by these rules."""
    if not declared:
        return set()

    def resolve(where, inline, name, given, owners):
        """The file of the module name declared in where, or None; owners are the files whose modules sit beside
        them, as a mod.rs file's do."""
        folder, _, base = where.rpartition("/")
        folder = folder + "/" if folder else ""
        if not base.endswith(".rs") or None in inline:
            return None
        own = folder if base == "mod.rs" or where in owners else folder + base[:-3] + "/"
        within = "".join(f + "/" for f in inline)
        if given is not None:
            found = [(folder if not inline else own + within) + given]
        else:
            found = [own + within + name + ".rs", own + within + name + "/mod.rs"]
        for p in found:
            p = posixpath.normpath(p)
            if p in files:
                return p
        return None

    named = {p for p in files if p.rpartition("/")[2] in RUST_ROOT_NAMES
             or p.rpartition("/")[0].rpartition("/")[2] in RUST_ROOT_DIRS}
    listed = roots & set(files)
    first = [resolve(*d[:4], named | listed) for d in declared]
    by_path = {t for t, d in zip(first, declared) if t is not None and d[3] is not None}   # read as a mod.rs is
    owners = (named - set(first)) | listed | by_path
    claims = {}   # each module's file: the files that declare it, and whether each declares it only in tests
    for where, inline, name, given, scoped in declared:
        target = resolve(where, inline, name, given, owners)
        if target is not None and target != where:
            claims.setdefault(target, []).append((where, scoped))
    test = {p for p, t in files.items() if t}
    ordered, seen = sorted(files), set()
    grown = True
    while grown:   # until no file is added: a file found test code may declare modules of its own
        grown = False
        for target, by in claims.items():
            if target not in test and any(s or w in test for w, s in by) \
                    and not any(not s and w not in test for w, s in by):
                test.add(target)
                grown = True
        for target in [t for t in claims if t in test and not files[t] and t not in seen]:   # the backstop
            seen.add(target)
            below = target[:-len("mod.rs")] if target.endswith("/mod.rs") else target[:-3] + "/"
            k = bisect.bisect_left(ordered, below)
            while k < len(ordered) and ordered[k].startswith(below):
                if ordered[k] not in claims and ordered[k] not in owners and ordered[k] not in test:
                    test.add(ordered[k])
                    grown = True
                k += 1
    return {p for p in test if not files[p]}
