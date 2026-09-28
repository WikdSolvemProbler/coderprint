"""Regression checks for how coderprint tells test code from production: one check or more for each finding of the
tests area (tests-F1 to tests-F7 and tests-U1) and for in_use-IU-07. Usage: python test_tests.py path/to/coderprint.py.
It builds its repositories in a temporary folder, runs read_head_code() and collect() with every network lookup
replaced by a fake, prints one line per check and exits non-zero if any check fails.

Rust fixtures mark every line T| (test code) or P| (production); the expected split counts only the lines the
file's reader calls code, so a check judges the split alone."""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile

spec = importlib.util.spec_from_file_location("cp_under_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

ROOT = tempfile.mkdtemp(prefix="tests-")
NOREPLY = "123+owner1@users.noreply.github.com"
T0 = 1700000000
DAY = 86400
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


_names = iter(range(10 ** 6))


def build(commits, name=None):
    """commits: a list of (time, {path: text, or None to delete}); returns the repository's name."""
    name = name or "r%d" % next(_names)
    path = os.path.join(ROOT, "src", name)
    os.makedirs(path)
    subprocess.run(["git", "init", "-q", "-b", "main", path], check=True, capture_output=True)
    for when, files in commits:
        for rel, data in files.items():
            p = os.path.join(path, rel)
            if data is None:
                os.remove(p)
                continue
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as f:
                f.write(data.encode("utf-8"))
        git(path, "add", "-A", when=when)
        git(path, "commit", "-q", "--allow-empty", "-m", "c", when=when)
    SOURCES[name] = path
    return name


def fake_clone(owner, name, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    subprocess.run(["git", "clone", "-q", "--bare", SOURCES[name], dest], check=True, capture_output=True)


cp.clone = fake_clone
cp.resolve_authors = lambda owner, samples: {e: None for e in samples}
cp.owner_identity = lambda owner: {"user": True, "id": 123, "name": "Owner One"}
cp.templates = lambda owner: {}
cp.seed_blobs = lambda full_name, dest: None


def collect(names, since=None):
    work = tempfile.mkdtemp(prefix="work-", dir=ROOT)
    return cp.collect("owner1", [{"name": n, "isPrivate": True} for n in names], work, since)


def split(data):
    return data["code"]["production"], data["code"]["tests"]


def fixture(files):
    """({path: text}, the (production, tests) its T| and P| marks give) for {path: marked text}."""
    texts, want = {}, [0, 0]
    for rel, marked in files.items():
        raw = marked.strip("\n").split("\n")
        assert all(line[:2] in ("T|", "P|") for line in raw), rel
        text = "\n".join(line[2:] for line in raw) + "\n"
        texts[rel] = text
        lang = cp.language_of(rel)
        if not cp.counts_as_code(rel, lang):
            continue
        reader = cp.reader_for(lang, rel)[0]
        lines, eol = cp.split_lines(text, "\n")
        kinds = cp.read_lines(reader, lines.__getitem__, len(lines), eol)[0]
        for line, kind in zip(raw, kinds):
            if kind == cp.CODE:
                want[line[:2] == "T|"] += 1
    return texts, tuple(want)


def head_split(texts):
    """(production, tests) of read_head_code over one commit of texts."""
    head = cp.read_head_code(SOURCES[build([(T0, texts)])])
    return (sum(n for (h, t), n in head.items() if not t), sum(n for (h, t), n in head.items() if t))


def rust_case(fid, name, files, want=None):
    """A Rust case read at the head: its split against its marks (or want, where the marks are not the point)."""
    texts, marks = fixture(files)
    try:
        got = head_split(texts)
    except Exception as e:
        got = "error: %s: %s" % (type(e).__name__, e)
    want = want or marks
    check(fid, "%s: (production, tests) %s" % (name, want), got == want, got)


def collected(fid, name, files, want):
    """A case run through collect(): its published (production, tests) against want."""
    try:
        got = split(collect([build([(T0, files)])]))
    except Exception as e:
        got = "error: %s: %s" % (type(e).__name__, e)
    check(fid, "%s: published (production, tests) %s" % (name, want), got == want, got)


TAIL = "T|    #[test]\nT|    fn t() {\nT|        assert_eq!(super::f(), 1);\nT|    }\nT|}\n"
HEAD = "P|pub fn f() -> u8 {\nP|    1\nP|}\n"

# ---------------------------------------------------------------- tests-F1 and in_use-IU-07: brackets in literals
rust_case("tests-F1", "an unbalanced '{' in a test's string, production after the module", {"src/lib.rs": """
P|pub fn parse(s: &str) -> usize {
P|    s.len()
P|}
T|#[cfg(test)]
T|mod tests {
T|    use super::*;
T|    #[test]
T|    fn open_brace() {
T|        assert_eq!(parse("{"), 1);
T|    }
T|}
P|pub fn after_open() -> u8 {
P|    1
P|}
"""})
rust_case("tests-F1", "a '}' in a test's string does not close the module early", {"src/lib.rs": """
P|pub fn render() -> String {
P|    String::from("x")
P|}
T|#[cfg(test)]
T|mod tests {
T|    use super::*;
T|    #[test]
T|    fn no_brace() {
T|        assert!(!render().ends_with("}"));
T|    }
T|    #[test]
T|    fn renders_x() {
T|        let expected = String::from("x");
T|        assert_eq!(render(), expected);
T|    }
T|}
"""})
rust_case("tests-F1", "a '{' character literal and a comment holding a brace", {"src/lib.rs": """
P|pub fn is_open(c: char) -> bool {
P|    c == '('
P|}
T|#[cfg(test)]
T|mod tests {
T|    #[test]
T|    fn brace_char() {
T|        assert!(!super::is_open('{')); // not an opener {
T|    }
T|}
P|pub fn after_chars() -> u8 {
P|    2
P|}
"""})
rust_case("tests-F1", "a doc comment naming `Foo {}` between the attribute and its item", {"src/lib.rs": """
P|pub struct Foo {}
T|#[cfg(test)]
T|/// Builds a `Foo {}` for the tests.
T|fn make_foo() -> Foo {
T|    let made = Foo {};
T|    made
T|}
P|pub fn after_doc() -> u8 {
P|    3
P|}
"""})
rust_case("tests-F1", "a multi-line raw string of truncated JSON in a test", {"src/lib.rs": """
P|pub fn load(s: &str) -> bool {
P|    s.len() > 2
P|}
T|#[cfg(test)]
T|mod tests {
T|    #[test]
T|    fn truncated_json() {
T|        let input = r#"
T|            {"a": [1, 2
T|        "#;
T|        assert!(super::load(input));
T|    }
T|}
P|pub struct After {
P|    pub x: u8,
P|}
"""})
rust_case("tests-F1", "#[cfg(test)] inside a raw string and inside a block comment opens nothing", {"src/lib.rs": r"""
P|pub const SRC: &str = r#"
P|#[cfg(test)]
P|mod tests {
P|"#;
P|/*
P|#[cfg(test)]
P|mod tests {
P|*/
P|pub fn after() -> u8 {
P|    1
P|}
"""})
rust_case("tests-F1", "lifetimes, loop labels, byte characters, escapes and a nested comment across lines", {
    "src/lib.rs": r"""
P|pub struct W<'a> { s: &'a str }
P|impl<'a> W<'a> {
P|    pub fn q(&self) -> char { '"' }
P|}
P|pub fn f() -> &'static [u8] {
P|    'outer: loop {
P|        break 'outer;
P|    }
P|    /* a /* nested { */
P|    still comment } */
P|    b"\\"
P|}
T|#[cfg(test)]
T|mod tests {
T|    const A: &str = "\\";
T|    const B: &str = "\"{";
T|    const C: char = '\'';
T|    const D: u8 = b'{';
T|    const E: char = '\u{7b}';
T|    fn t() { let _ = (A, B, C, D, E, super::W { s: "}" }.q()); }
T|}
P|pub fn g() -> u8 {
P|    3
P|}
"""})
S09 = {
    "char": ("pub fn a() -> i32 {\n    1\n}\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n"
             "        let c = '{';\n        assert_eq!(c, '{');\n    }\n}\npub fn b() -> i32 {\n    2\n}\n"
             "pub fn c() -> i32 {\n    3\n}\n", (9, 8)),
    "string": ("pub fn a() -> i32 {\n    1\n}\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n"
               "        assert_eq!(format!(\"}}\"), \"}\");\n    }\n}\npub fn b() -> i32 {\n    2\n}\n", (6, 7)),
    "comment": ("#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() { // closes with }\n        assert!(true);\n"
                "    }\n}\npub fn b() -> i32 {\n    2\n}\n", (3, 7)),
    "lifetime": ("pub struct P<'a> { s: &'a str }\n#[cfg(test)]\nmod tests {\n    use super::*;\n"
                 "    fn mk<'a>(s: &'a str) -> P<'a> {\n        P { s }\n    }\n    #[test]\n    fn t() {\n"
                 "        let c = 'x';\n        assert_eq!(mk(\"a\").s, \"a\");\n    }\n}\n"
                 "pub fn after() -> i32 {\n    1\n}\n", (4, 12)),
    "escaped quote": ("#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        let s = \"a\\\"{\";\n"
                      "        assert_eq!(s.len(), 3);\n    }\n}\npub fn c() -> i32 {\n    3\n}\n", (3, 8)),
    # the line "/* end */ }" is code since lines-F1 (code after a closed comment counts), so the module has 7
    # lines where the finding's verifier counted 6; what is checked is that the module closes on it
    "closed after a block comment": ("#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {\n        assert!(true);\n"
                                     "    }\n/* end */ }\npub fn b() -> i32 {\n    2\n}\n", (3, 7)),
}
for name, (text, want) in S09.items():
    collected("in_use-IU-07", name, {"src/lib.rs": text}, want)

# ---------------------------------------------------------------- tests-F2: every cfg that holds only in tests
for name, attribute in [("all(test, feature)", '#[cfg(all(test, feature = "slow"))]'),
                        ("all(unix, test)", "#[cfg(all(unix, test))]"), ("spaced", "#[cfg( test )]"),
                        ("spaced outside", "#[ cfg(test) ]"), ("after another attribute",
                                                               "#[allow(unused_imports)] #[cfg(test)]"),
                        ("not(not(test))", "#[cfg(not(not(test)))]"),
                        ("an option with arguments", '#[cfg(all(test, version("1.80")))]')]:
    rust_case("tests-F2", name, {"src/lib.rs": HEAD + "T|%s\nT|mod tests {\n" % attribute + TAIL})
rust_case("tests-F2", "a rustfmt-wrapped cfg over four lines", {"src/lib.rs": HEAD + (
    'T|#[cfg(all(\nT|    test,\nT|    target_os = "linux",\nT|    not(miri),\nT|))]\nT|mod tests {\n') + TAIL})
for name, attribute in [("any(test, feature) can hold outside tests", '#[cfg(any(test, feature = "testing"))]'),
                        ("not(test)", "#[cfg(not(test))]"), ("a feature named test", '#[cfg(feature = "test")]'),
                        ("all(test, not(test)) is never compiled", "#[cfg(all(test, not(test)))]"),
                        ("any() is never compiled", "#[cfg(any())]"), ("cfg_attr is not cfg",
                                                                       "#[cfg_attr(test, derive(Debug))]")]:
    rust_case("tests-F2", name + ", production", {"src/lib.rs": HEAD + "P|%s\nP|mod support {\n" % attribute
                                                  + TAIL.replace("T|", "P|")})
rust_case("tests-F2", "a module file that marks itself #![cfg(test)]", {
    "src/lib.rs": "P|pub mod support;\n" + HEAD,
    "src/support.rs": "T|//! Fakes for the tests.\nT|#![allow(dead_code)]\nT|#![cfg(test)]\nT|use super::f;\n"
                      "T|pub fn fixture() -> u8 {\nT|    f() + 1\nT|}\n"})
rust_case("tests-F2", "#![cfg(test)] inside an inline module: the whole module, its header too", {"src/lib.rs": """
P|pub fn f() -> u8 {
P|    1
P|}
T|mod helpers {
T|    #![cfg(test)]
T|    pub fn fake() -> u8 { 0 }
T|}
P|pub fn g() -> u8 {
P|    3
P|}
"""})
rust_case("tests-F2", "a test-only field, variant and match arm end at their comma or at the block's end", {
    "src/lib.rs": """
P|pub enum E {
P|    A,
T|    #[cfg(test)]
T|    Fake(u8),
P|    B,
T|    #[cfg(test)]
T|    Last
P|}
P|pub struct S {
P|    pub a: u8,
T|    #[cfg(test)]
T|    pub calls: Vec<u8>,
P|    pub b: u8,
P|}
P|pub fn pick(e: E) -> u8 {
P|    match e {
T|        #[cfg(test)]
T|        E::Fake(n) => n,
P|        _ => 0,
P|    }
P|}
"""})
rust_case("tests-F2", "a test-only generic item keeps its where clause's commas", {"src/lib.rs": """
T|#[cfg(test)]
T|impl<A, B> From<(A, B)> for S
T|where
T|    A: Into<u8>,
T|    B: Into<u8>,
T|{
T|    fn from(_: (A, B)) -> S { S }
T|}
P|pub struct S;
P|#[cfg(any(test, feature = "x"))]
P|pub fn either() {}
"""})
rust_case("tests-F2", "an item's first code after doc comments, Allman braces and a derive", {"src/lib.rs": """
T|#[cfg(test)]
T|/* helper; see { below
T|   } */
T|#[derive(Debug)]
T|struct Fake
T|{
T|    a: u8,
T|}
T|#[cfg(test)] // see the fixtures below;
T|mod tests
T|{
T|    fn t() {}
T|}
P|pub fn after() -> u8 {
P|    5
P|}
"""})
rust_case("tests-F2", "lines starting with # in a macro body do not swallow the file", {"src/lib.rs": """
P|macro_rules! m {
P|    ($(#[$meta:meta])* $name:ident) => {
P|        $(#[$meta])*
P|        pub struct $name;
P|    };
P|}
T|#[cfg(test)]
T|mod tests {
T|    #[test]
T|    fn t() {}
T|}
P|pub fn g() -> u8 {
P|    3
P|}
"""})
check("tests-F2", "cfg_test reads the predicate forms", lambda: [cp.cfg_test(p) for p in (
    "test", " test ", 'all(test, feature = "x")', "all(unix, all(test, windows))", "any(test, all(test, unix))",
    "any(test, unix)", "not(test)", "all(not(test), unix)", "tests", 'feature = "test"', "any()",
    "all(test, not(test))")] == [True] * 5 + [False] * 7)
check("tests-F2", "cfg_test: 5,000 nested all( without a RecursionError",
      lambda: cp.cfg_test("all(" * 5000 + "test" + ")" * 5000) and not cp.cfg_test("all(" * 5000 + "unix" + ")" * 5000))
check("tests-F2", "cfg_test: what is not a predicate falls back to the word test alone",
      lambda: not cp.cfg_test("all(test") and not cp.cfg_test("not(test, unix)") and cp.cfg_test("test"))

# ---------------------------------------------------------------- tests-F3: test modules declared out of line
rust_case("tests-F3", "#[cfg(test)] mod proptests; beside lib.rs", {
    "src/lib.rs": HEAD + "T|#[cfg(test)]\nT|mod proptests;",
    "src/proptests.rs": "T|use super::f;\nT|#[test]\nT|fn prop() {\nT|    assert_eq!(f(), 1);\nT|}"})
rust_case("tests-F3", "declared in foo.rs, its file in foo/", {
    "src/lib.rs": "P|pub mod foo;", "src/foo.rs": HEAD + "T|#[cfg(test)]\nT|mod helpers;",
    "src/foo/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}"})
rust_case("tests-F3", "declared in a/mod.rs, its file a/fakes/mod.rs with a submodule of its own", {
    "src/lib.rs": "P|pub mod a;", "src/a/mod.rs": HEAD + "T|#[cfg(test)]\nT|mod fakes;",
    "src/a/fakes/mod.rs": "T|pub mod clock;\nT|pub fn fake() -> u8 {\nT|    0\nT|}",
    "src/a/fakes/clock.rs": "T|pub fn now() -> u64 {\nT|    0\nT|}"})
rust_case("tests-F3", "#[path] names the file, and that file's modules sit beside it", {
    "src/lib.rs": HEAD + 'T|#[cfg(test)]\nT|#[path = "support/x_fixtures.rs"]\nT|mod fixtures;',
    "src/support/x_fixtures.rs": "T|mod clock;\nT|pub fn fake() -> u8 {\nT|    0\nT|}",
    "src/support/clock.rs": "T|pub fn now() -> u64 {\nT|    0\nT|}"})
rust_case("tests-F3", "a production module of the same file name elsewhere stays production", {
    "src/lib.rs": "P|pub mod util;\nT|#[cfg(test)]\nT|mod helpers;",
    "src/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}",
    "src/util/mod.rs": "P|pub mod helpers;", "src/util/helpers.rs": "P|pub fn real() -> u8 {\nP|    1\nP|}"})
rust_case("tests-F3", "the Substrate pattern: #[cfg(test)] mod mock; and mod tests;", {
    "src/lib.rs": HEAD + "T|#[cfg(test)]\nT|mod mock;\nT|#[cfg(test)]\nT|mod tests;",
    "src/mock.rs": "T|pub fn new_test_ext() -> u8 {\nT|    0\nT|}",
    "src/tests.rs": "T|use crate::mock::*;\nT|fn t() {\nT|    new_test_ext();\nT|}"})
rust_case("tests-F3", "a folder whose name ends in bin (robin) is not a crate root's", {
    "src/lib.rs": "P|pub mod robin;", "src/robin.rs": "P|pub mod foo;\nP|pub mod helpers;",
    "src/robin/foo.rs": HEAD + "T|#[cfg(test)]\nT|mod helpers;",
    "src/robin/foo/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}",
    "src/robin/helpers.rs": "P|pub fn real() -> u8 {\nP|    2\nP|}"})
rust_case("tests-F3", "a binary in src/bin: its test module sits beside it", {
    "src/bin/tool.rs": "P|fn main() {\nP|    let _ = 1;\nP|}\nT|#[cfg(test)]\nT|mod helpers;",
    "src/bin/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}"})
rust_case("tests-F3", "inside an inline module, the module's folder", {
    "src/lib.rs": "P|pub mod helpers;\nP|mod outer {\nT|    #[cfg(test)]\nT|    mod helpers;\nP|}",
    "src/helpers.rs": "P|pub fn real() -> u8 {\nP|    1\nP|}",
    "src/outer/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}"})
rust_case("tests-F3", "a file both a test module and a production module declare stays production", {
    "src/lib.rs": 'P|pub mod shared;\nT|#[cfg(test)]\nT|#[path = "shared.rs"]\nT|mod shared_again;',
    "src/shared.rs": "P|pub fn both() -> u8 {\nP|    1\nP|}"})
rust_case("tests-F3", "the backstop: a file in a test module's folder that no declaration names", {
    "src/lib.rs": HEAD + "T|#[cfg(test)]\nT|mod fakes;",
    "src/fakes.rs": 'T|include!("fakes/generated.rs");',
    "src/fakes/generated.rs": "T|pub fn made() -> u8 {\nT|    7\nT|}"})
MANIFEST = {"Cargo.toml": 'P|[package]\nP|name = "x"\nP|\nP|[lib]\nP|path = "src/mylib.rs"\n',
            "src/mylib.rs": HEAD + "T|#[cfg(test)]\nT|mod helpers;",
            "src/helpers.rs": "T|pub fn fake() -> u8 {\nT|    0\nT|}"}
rust_case("tests-F3", "a crate root Cargo.toml names by its [lib] path", MANIFEST)
if getattr(cp, "tomllib", None) is not None:
    held, cp.tomllib = cp.tomllib, None
    try:
        rust_case("tests-F3", "the same Cargo.toml read by its lines, without tomllib", MANIFEST)
    finally:
        cp.tomllib = held
rust_case("tests-F3", "without that Cargo.toml the file is not found, and stays production",
          {k: v for k, v in MANIFEST.items() if k != "Cargo.toml"}, want=(6, 2))
check("tests-F3", "cargo_roots reads bins, examples, the build script and a malformed file by its lines", lambda: (
    cp.cargo_roots("crates/a/Cargo.toml", b'[package]\nbuild = "gen/build.rs"\n[[bin]]\nname = "t"\npath = "cli.rs"\n'
                   b'[[example]]\npath = "ex/one.rs"\n[dependencies]\npath = "not/a/root.rs"\n')
    == {"crates/a/gen/build.rs", "crates/a/cli.rs", "crates/a/ex/one.rs"}
    and cp.cargo_roots("Cargo.toml", b'[lib]\npath = "src/x.rs"\n[lib]\n') == {"src/x.rs"}))

# a reading of scopes that fails falls back to the file's path, and says so
held = cp.rust_lines
cp.rust_lines = lambda *a: 1 / 0
try:
    d = collect([build([(T0, {"src/lib.rs": "fn a() -> u8 {\n    1\n}\n#[cfg(test)]\nmod t {\n    fn t() {}\n}\n"})])])
    got = split(d), d["code"]["approximate_in_use"]
except Exception as e:
    got = "error: %s: %s" % (type(e).__name__, e)
finally:
    cp.rust_lines = held
check("tests-F2", "a Rust file whose scopes cannot be read counts by its path, marked approximate",
      got == ((7, 0), 7), got)

# ---------------------------------------------------------------- tests-F4: test folders as build tools name them
tag = iter(range(10 ** 6))


def body(n, fmt="int v_%d_%d = %d;\n"):
    t = next(tag)
    return "".join(fmt % (t, i, i) for i in range(n))


PY = "v_%d_%d = %d\n"
FOLDERS = {
    "dotnet": {"src/MyApp/Services/Clock.cs": (body(10), False), "MyApp.Tests/ClockTests.cs": (body(6), True),
               "MyApp.Tests/Helpers/FakeClock.cs": (body(8), True), "MyApp.UnitTests/Usings.cs": (body(3), True),
               "src/MyApp.IntegrationTests/CustomWebApplicationFactory.cs": (body(12), True)},
    "android": {"app/src/main/java/com/acme/Main.kt": (body(10), False),
                "app/src/androidTest/java/com/acme/HiltTestRunner.kt": (body(7), True),
                "lib/src/testFixtures/java/com/acme/Builders.java": (body(6), True),
                "lib/src/integrationTest/java/com/acme/Containers.java": (body(4), True),
                "shared/src/commonTest/kotlin/com/acme/FakeRepo.kt": (body(8), True)},
    "xcode": {"MyApp/ContentView.swift": (body(10), False), "MyAppTests/Helpers/Stubs.swift": (body(6), True),
              "MyAppUITests/MyAppUITestsLaunchTests.swift": (body(4), True)},
    "go and js": {"internal/server/server.go": (body(10), False), "internal/testutil/fake_server.go": (body(9), True),
                  "web/src/app.ts": (body(10), False),
                  "web/src/__fixtures__/user.ts": (body(4), True), "web/src/__test__/render.ts": (body(5), True),
                  "web/cypress/support/commands.ts": (body(6), True),
                  "packages/test-utils/src/index.ts": (body(7), True)},
    "python": {"app/core.py": (body(10, PY), False), "integration-tests/helpers.py": (body(6, PY), True),
               "e2e-tests/pages.py": (body(5, PY), True), "unit_tests/factories.py": (body(4, PY), True),
               "unittests/support.py": (body(3, PY), True), "bench/run.py": (body(2, PY), True)},
    "production that stays so": {"SpeedTest/ContentView.swift": (body(5), False),
                                 "quant/BackTest/Engine.cs": (body(4), False),
                                 "src/pytest_timeout/plugin.py": (body(3, PY), False),
                                 "src/_pytest/fixtures.py": (body(2, PY), False),
                                 "src/latest/index.ts": (body(2), False), "src/contests/list.py": (body(2, PY), False)},
}
for name, files in FOLDERS.items():
    want = (sum(t.count("\n") for t, k in files.values() if not k), sum(t.count("\n") for t, k in files.values() if k))
    collected("tests-F4", name, {p: t for p, (t, _) in files.items()}, want)
    wrong = [p for p, (_, k) in files.items() if cp.is_test(p) != k]
    check("tests-F4", "is_test on every path of %s" % name, not wrong, wrong)

# ---------------------------------------------------------------- tests-F5: names test runners give their tests
NAMES = {"app/core.py": (body(10, PY), False), "conftest.py": (body(6, PY), True),
         "app/conftest.py": (body(4, PY), True), "web/src/Button.tsx": (body(10), False),
         "web/src/Button.cy.tsx": (body(5), True), "api/src/app.e2e-spec.ts": (body(7), True),
         "lib/index.test-d.ts": (body(3), True), "jvm/src/com/acme/IOTest.java": (body(4), True),
         "dotnet/Api/APITests.cs": (body(6), True), "ios/App/LoginUITests.swift": (body(8), True),
         "ios/App/Login.swift": (body(9), False), "src/Latest.java": (body(2), False),
         "src/Contest.java": (body(2), False), "src/attestation.py": (body(2, PY), False)}
want = (sum(t.count("\n") for t, k in NAMES.values() if not k), sum(t.count("\n") for t, k in NAMES.values() if k))
collected("tests-F5", "conftest.py, x.cy.tsx, x.e2e-spec.ts, x.test-d.ts and IOTest-style classes",
          {p: t for p, (t, _) in NAMES.items()}, want)
wrong = [p for p, (_, k) in NAMES.items() if cp.is_test(p) != k]
check("tests-F5", "is_test on every name", not wrong, wrong)

# ---------------------------------------------------------------- tests-F6: spec names only where tests use them
GO, RS = "var v_%d_%d = %d\n", "pub const V_%d_%d: u32 = %d;\n"
SPECS = {"pkg/job/spec.go": (body(9, GO), False), "pkg/apis/pod_spec.go": (body(7, GO), False),
         "pkg/apis/pod_spec_test.go": (body(3, GO), True), "src/package_id_spec.rs": (body(8, RS), False),
         "src/spec.rs": (body(5, RS), False), "loader/spec.py": (body(6, PY), False),
         "java/src/main/java/com/acme/crypto/RsaKeySpec.java": (body(4), False),
         "lib/user_spec.rb": (body(5, PY), True), "web/src/app.spec.ts": (body(4), True),
         "web/src/utilSpec.js": (body(3), True), "groovy/src/FooSpec.groovy": (body(2), True),
         "src/FooSpec.kt": (body(2), True), "lib/foo_spec.cr": (body(2, PY), True)}
want = (sum(t.count("\n") for t, k in SPECS.values() if not k), sum(t.count("\n") for t, k in SPECS.values() if k))
collected("tests-F6", "spec.go, spec.rs, spec.py and KeySpec.java are production; RSpec and Jasmine specs tests",
          {p: t for p, (t, _) in SPECS.items()}, want)
wrong = [p for p, (_, k) in SPECS.items() if cp.is_test(p) != k]
check("tests-F6", "is_test on every spec name", not wrong, wrong)
check("tests-F6", "is_test takes the language when given", lambda: cp.is_test("src/spec.x", "Ruby")
      and not cp.is_test("src/spec.x", "Go"))

# ---------------------------------------------------------------- tests-F7: a symbolic link is not code
name = build([(T0, {"src/helper.py": "def helper():\n    return 1\n", "src/other.py": "def other():\n    return 2\n"})])
repo = SOURCES[name]
for k, target in enumerate(("../src/helper.py", "../src/other.py")):   # a link, then the same link retargeted
    blob = git(repo, "hash-object", "-w", "--stdin", stdin=target.encode()).strip()
    git(repo, "update-index", "--add", "--cacheinfo", "120000,%s,tests/helper.py" % blob)
    git(repo, "commit", "-q", "-m", "link", when=T0 + 60 * (k + 1))
d = collect([name])
written = sum(n for _, _, n in d["events"])
check("tests-F7", "a link and its retarget write nothing and are not in use", written == 4 and split(d) == (4, 0),
      (written, split(d)))

# ---------------------------------------------------------------- tests-U1: a common line split by where it was written


def ruby(folder):
    old_prod = "".join("def old_%d\n  %d\nend\n" % (i, i) for i in range(30))
    old_test = "".join("it 'works %d' do\n  expect(%d)\nend\n" % (i, i) for i in range(30))
    new_prod = "".join("def new_%d\n  %d\nend\n" % (i, i) for i in range(5))
    return build([(T0, {"src/old.rb": old_prod, "%s/old_%s.rb" % (folder, folder.rstrip("s")): old_test}),
                  (T0 + 10 * DAY, {"src/new.rb": new_prod})])


a, b = split(collect([ruby("spec")], T0 + 5 * DAY)), split(collect([ruby("test")], T0 + 5 * DAY))
check("tests-U1", "the window's 15 production lines are production whichever folder holds the tests",
      a == (15, 0) and b == (15, 0), (a, b))
name = build([(T0, {"lib/a.rb": "def a\n  1\nend\n" * 4, "spec/a_spec.rb": "it 'x' do\n  1\nend\n" * 2})])
d = collect([name])
check("tests-U1", "every written line still matched once: 12 production and 6 test lines, 18 written",
      split(d) == (12, 6) and sum(n for _, _, n in d["events"]) == 18, (split(d), d["events"]))

shutil.rmtree(ROOT, ignore_errors=True)
print("PASS %d FAIL %d" % (sum(results), len(results) - sum(results)))
sys.exit(0 if all(results) else 1)
