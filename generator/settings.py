# coderprint's the settings, the languages by name and extension, the design and the README block. coderprint.py runs
# this file as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not
# imported on its own.


WORK = os.getcwd()   # the profile repository being drawn for
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(WORK, "assets")
README = os.path.join(WORK, "README.md")
IMPORT_FILES = 500
TIMEOUT = 900
DEADLINE = None   # the run's own deadline, on time.monotonic(), when CARDS_TIME_LIMIT sets one (see time_limit)
RESERVE = 120     # seconds kept back from it for reading the profile and drawing and writing the panels
LOOKUP_RESERVE = 60   # and kept back as well while repositories are read, for asking whose each address is after them
UNREAD_SHARE = 0.10   # the panels are redrawn when at most one repository, or this share of them, could not be read
UPSTREAM = "WikdSolvemProbler/coderprint"   # this project, whose files a relay copy holds but did not write
RELAY_FILES = {"api/card.js", "lib/compose.js"}   # files every relay copy of it holds, both of them
# The lookups that tell the owner's code from others', named in collect()'s "unchecked" when GitHub cannot answer
# one: the run then keeps the existing panels rather than count everything as the owner's (see main).
UNCHECKED = {"authorship": "whose each commit's address is",
             "templates": "which of the repositories were made from another account's template"}
ALIASES = 50        # commits looked up in one query when telling whose an email address is
RESOLVE_CALLS = 20  # and at most this many queries a run; addresses past them stay unknown
# Automation that commits under a name or address of its own rather than a [bot] one: git scraping, release
# tooling, and a workflow's commit authored as whoever triggered it, which the committer then gives away.
AUTOMATION_NAMES = {"automated", "github action", "github actions", "github-actions", "actions-user",
                    "semantic-release-bot"}
AUTOMATION_EMAILS = {"action@github.com", "actions@github.com", "actions@users.noreply.github.com",
                     "github-actions@github.com", "41898282+github-actions[bot]@users.noreply.github.com"}
# A GitHub App's own noreply address, which any commit made as the App carries whatever name it gives; and an
# account's own noreply address of the id+login form, whose id no change of login alters (see authorship).
BOT_NOREPLY = re.compile(r"(?:\d+\+)?[^@\s]*\[bot\]@users\.noreply\.github\.com")
NOREPLY = re.compile(r"(\d+)\+[^@\s]+@users\.noreply\.github\.com")
# The name of a bot or a coding agent committing under an identity of its own ("Renovate Bot", "Cursor Agent",
# "release-bot"): its last word is bot or agent. Such a name tells no person's work (see authorship).
AGENT_NAME = re.compile(r"(?:^|[\s._-])(?:bot|agent)$")
# Names a machine, an editor's container or a tutorial gives a commit, which say nothing about who wrote it: one the
# owner's own commits used is never taken as the owner's name for another address (see authorship).
GENERIC_NAMES = {"root", "admin", "administrator", "user", "owner", "ubuntu", "debian", "pi", "vscode", "node",
                 "codespace", "codespaces", "gitpod", "runner", "vagrant", "ec2-user", "docker", "jenkins", "git",
                 "your name", "yourname", "unknown", "localhost", "(none)"}
Commit = namedtuple("Commit", "ts repo sha bot email name subject files")
Change = namedtuple("Change", "blob status path added deleted")
# A sweep: a commit that modifies at least SWEEP_FILES counted files, nearly every one (SWEEP_SHARE) adding
# within SWEEP_BALANCE of what it deletes, as reformatting, re-indenting or a line-ending change does. Its
# balanced files that delete a line add no lines (one that only gains a line was written to). git's own whitespace
# options (-w, -b) would say the same file by file, but on real histories they made reading hundreds of times
# slower and dropped files from the line counts.
SWEEP_FILES, SWEEP_SHARE, SWEEP_BALANCE = 10, 0.9, 0.1
# And a file of such a commit is swept only when its changes are alike: at least SWEEP_ALIKE of its changed lines of
# code still read nearly as they did (difflib's ratio ALIKE_RATIO or more, spacing aside), as a re-indented, re-ended
# or renamed line does (see alike_share). A rewrite that happens to add what it deletes, a migration or a new body,
# is written again, as README says a rewrite is; so is a file that only gains lines.
SWEEP_ALIKE, ALIKE_RATIO = 0.8, 0.6
SWEEP_WATCH = set()   # the commits of the repository being read that could be sweeps, whose changes are paired
NOTICE = ("Drawn by coderprint (https://github.com/WikdSolvemProbler/coderprint): its code, design and wordmark are "
          "Peter Shiller's, licensed as LICENSE.md, design/LICENSE.md and NOTICE.md there say. What the card reports "
          "is its owner's.")

# The span the whole panel covers, chosen once by whoever installs it (CARDS_WINDOW): its selector
# label, its name in prose, and its length in days (None for all time).
WINDOWS = {
    "all": ("ALL", "all time", None), "10y": ("10Y", "10 years", 3652), "5y": ("5Y", "5 years", 1826),
    "3y": ("3Y", "3 years", 1096), "2y": ("2Y", "2 years", 730), "12m": ("12M", "12 months", 365),
}
WINDOW_ORDER = ["all", "10y", "5y", "3y", "2y", "12m"]
LINK = os.environ.get("CARDS_LINK") or "https://github.com/WikdSolvemProbler/coderprint"   # where a click goes

# A folder whose name ends in a vendor word holds others' code whatever comes before it (s01t00_vendor,
# go-vendor, lib_vendored), while one that only starts with it is the owner's own (src/vendor_portal).
VENDOR_ENDS = tuple(sep + word for sep in "_-" for word in ("vendor", "vendors", "vendored")) + ("_target",)
EXCLUDED_DIRS = {   # whole folder names
    "node_modules", "vendor", "vendors", "vendored", "_vendor", "third_party", "thirdparty", "target",
    ".next", "__pycache__", ".venv", "venv", "site-packages", ".goldens", ".fixtures", ".dart_tool", ".idea", ".lake",
    ".mvn", ".nuxt", ".stack-work", ".svelte-kit", ".terraform", ".yarn", "3rd-party", "3rd_party", "3rdparty",
    "__generated__", "_build", "_esy", "_opam", "_site", "bower_components", "carthage", "deriveddata", "dist-newstyle",
    "elm-stuff", "flow-typed", "godeps", "htmlcov", "lake-packages", "pods", "testdata", "third-party",
    "jspm_packages", "web_modules",
}
# Folders a build writes its output to. At the top of a repository or of a module (build/, app/build/, dist/) nothing
# in them counts: CMake's, Gradle's and Android's builds write C, C++ and Java there (R.java, CMakeCCompilerId.c), and
# setuptools copies Python there. Below a folder of source (SOURCE_DIRS) the same names are packages of the owner's
# own code (Go's internal/build and cmd/dist, a Java package named coverage under src/main/java, src/out), so there
# only web output (HTML, CSS, JavaScript and TypeScript declarations) is left out. Source kept in a top-level build/
# or coverage/ folder (as coverage.py keeps its own) is left out with the output: the conservative reading.
OUTPUT_DIRS = {"dist", "build", "out", "coverage"}
SOURCE_DIRS = {"src", "source", "sources", "lib", "pkg", "internal", "cmd", "packages", "scripts", "tools"}
# Vendor folders by convention only at a repository's root (C and C++ projects' extern/ and external/, Elixir's and
# C projects' deps/), where the same names deeper down are usually the owner's own modules (src/external/api.ts)
ROOT_VENDOR_DIRS = {"extern", "external", "deps"}
# and at any depth, a pair of folders: WordPress's installed plugins, Unity's third-party plugins
VENDOR_PAIRS = {("wp-content", "plugins"), ("assets", "plugins")}
EXCLUDED_EXTS = {
    ".json", ".jsonl", ".lock", ".golden", ".csv", ".tsv", ".log", ".txt", ".aux", ".toc", ".out", ".bbl", ".blg",
    ".synctex", ".gz", ".map", ".snap", ".db", ".sqlite", ".svg", ".ipynb", ".pdf", ".xml", ".csproj", ".diff",
    ".filters", ".fsproj", ".gcode", ".geojson", ".har", ".iml", ".json5", ".jsonc", ".ma", ".ndjson", ".nib", ".obj",
    ".patch", ".pbxproj", ".plist", ".po", ".pot", ".proj", ".props", ".resx", ".rktd", ".sagews", ".sarif", ".sln",
    ".stl", ".storyboard", ".tab", ".targets", ".vbproj", ".vcxproj", ".webmanifest", ".xcuserstate",
    ".xcworkspacedata", ".xib", ".xlf", ".xliff",
    # notebooks, which hold their output cells beside their input, as .ipynb does: Mathematica's and its CDF
    ".nb", ".nbp", ".cdf",
    # what the Unity and Godot editors write: scenes, prefabs, assets, import settings and resources
    ".meta", ".unity", ".prefab", ".mat", ".anim", ".controller", ".overridecontroller", ".asset", ".physicmaterial",
    ".mask", ".mixer", ".playable", ".spriteatlas", ".terrainlayer", ".lighting", ".shadergraph", ".shadersubgraph",
    ".asmdef", ".asmref", ".tscn", ".tres", ".import",
}
EXCLUDED_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "cargo.lock", "poetry.lock", "uv.lock", ".gitignore",
    ".gitattributes", ".gitkeep", ".gitmodules", ".git-blame-ignore-revs", ".mailmap", "license", ".bash_history", ".rapp.history", ".rhistory", ".secrets.baseline",
    ".terraform.lock.hcl", "aclocal.m4", "bun.lockb", "cargo.toml.orig", "config.guess", "config.sub", "configure",
    "cpplint.py", "dotnet-install.ps1", "dotnet-install.sh", "erlang.mk", "go.sum", "gradlew", "gradlew.bat",
    "juliamanifest.toml", "libtool.m4", "ltoptions.m4", "ltsugar.m4", "ltversion.m4", "lt~obsolete.m4", "manifest.toml",
    "mvnw", "mvnw.cmd", "package.resolved", "ppport.h", "waf",
    "makefile.coq", "makefile.coq.conf",   # what coq_makefile writes
}
EXCLUDED_PREFIXES = (".pnp.",)   # Yarn's Plug'n'Play loader
EXCLUDED_SUFFIXES = (   # minified, and generated from a schema or a designer
    ".min.js", ".min.css", "-min.js", "-min.css", ".designer.cs", ".designer.vb", ".feature.cs", ".zep.c", ".zep.h",
    ".zep.php", "_tlb.pas", ".pb.go", "_pb2.py", "_pb2.pyi", "_pb2_grpc.py", ".pb.cc", ".pb.h", "_pb.js", "_grpc_pb.js",
    "_pb.d.ts", ".pb.swift", ".g.dart", ".freezed.dart",
)
# Languages by extension, named and grouped as GitHub's Linguist does, with coderprint's own folds: CSS
# preprocessors count as CSS, prose markups as Markdown and SQL dialects as SQL. An extension several
# languages share (.h, .m, .pl, .v, .fs, .cls and others) is left out, so it counts as Other, unless one
# of them writes far more of it than the rest (.pm is Perl, .r is R, .gd is GDScript).
LANGUAGES = {
    ".py": "Python", ".pyi": "Python", ".pyw": "Python", ".py3": "Python", ".gyp": "Python", ".gypi": "Python",
    ".lmi": "Python", ".pyde": "Python", ".pyp": "Python", ".pyt": "Python", ".tac": "Python", ".wsgi": "Python",
    ".xpy": "Python", ".smk": "Python", ".snakefile": "Python", ".pyx": "Cython", ".pxd": "Cython", ".pxi": "Cython",
    ".rs": "Rust", ".ts": "TypeScript", ".cts": "TypeScript", ".mts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript", ".es6": "JavaScript",
    "._js": "JavaScript", ".bones": "JavaScript", ".jake": "JavaScript", ".javascript": "JavaScript",
    ".jsb": "JavaScript", ".jscad": "JavaScript", ".jsfl": "JavaScript", ".jslib": "JavaScript", ".jsm": "JavaScript",
    ".jspre": "JavaScript", ".jss": "JavaScript", ".njs": "JavaScript", ".pac": "JavaScript", ".sjs": "JavaScript",
    ".ssjs": "JavaScript", ".xsjs": "JavaScript", ".xsjslib": "JavaScript", ".tex": "TeX", ".sty": "TeX", ".ltx": "TeX",
    ".dtx": "TeX", ".ins": "TeX", ".bbx": "TeX", ".cbx": "TeX", ".lbx": "TeX", ".mkii": "TeX", ".mkiv": "TeX",
    ".mkvi": "TeX", ".bib": "TeX", ".bibtex": "TeX", ".md": "Markdown", ".markdown": "Markdown", ".mdown": "Markdown",
    ".mdwn": "Markdown", ".mkd": "Markdown", ".mkdn": "Markdown", ".mkdown": "Markdown", ".ronn": "Markdown",
    ".livemd": "Markdown", ".workbook": "Markdown", ".mdx": "Markdown", ".rst": "Markdown", ".rest": "Markdown",
    ".adoc": "Markdown", ".asciidoc": "Markdown", ".org": "Markdown", ".rmd": "Markdown", ".qmd": "Markdown",
    ".lean": "Lean", ".hlean": "Lean", ".ps1": "PowerShell", ".psm1": "PowerShell", ".psd1": "PowerShell",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ksh": "Shell", ".bats": "Shell", ".command": "Shell",
    ".zsh-theme": "Shell", ".tool": "Shell", ".pacscript": "Shell", ".sbatch": "Shell", ".slurm": "Shell",
    ".fish": "Shell", ".tcsh": "Shell", ".csh": "Shell", ".nu": "Nushell", ".css": "CSS", ".scss": "CSS",
    ".sass": "CSS", ".less": "CSS", ".styl": "CSS", ".pcss": "CSS", ".postcss": "CSS", ".html": "HTML", ".htm": "HTML",
    ".xhtml": "HTML", ".xht": "HTML", ".hta": "HTML", ".erb": "HTML", ".rhtml": "HTML", ".heex": "HTML",
    ".leex": "HTML", ".cshtml": "HTML", ".razor": "HTML", ".phtml": "HTML", ".ecr": "HTML", ".yml": "YAML",
    ".yaml": "YAML", ".sublime-syntax": "YAML", ".toml": "TOML", ".sql": "SQL", ".ddl": "SQL", ".mysql": "SQL",
    ".prc": "SQL", ".udf": "SQL", ".viw": "SQL", ".pgsql": "SQL", ".pls": "SQL", ".plsql": "SQL", ".pck": "SQL",
    ".pkb": "SQL", ".pks": "SQL", ".plb": "SQL", ".bdy": "SQL", ".fnc": "SQL", ".spc": "SQL", ".tpb": "SQL",
    ".tps": "SQL", ".trg": "SQL", ".vw": "SQL", ".db2": "SQL", ".vbs": "VBScript", ".go": "Go", ".c": "C", ".cats": "C",
    ".idc": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".c++": "C++", ".cppm": "C++", ".ixx": "C++",
    ".hpp": "C++", ".hh": "C++", ".hxx": "C++", ".h++": "C++", ".inl": "C++", ".ipp": "C++", ".tcc": "C++",
    ".tpp": "C++", ".txx": "C++", ".ino": "C++", ".java": "Java", ".jav": "Java", ".jsh": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".ktm": "Kotlin", ".swift": "Swift", ".rb": "Ruby", ".builder": "Ruby", ".eye": "Ruby",
    ".gemspec": "Ruby", ".god": "Ruby", ".jbuilder": "Ruby", ".mspec": "Ruby", ".podspec": "Ruby", ".prawn": "Ruby",
    ".rabl": "Ruby", ".rake": "Ruby", ".rbi": "Ruby", ".rbuild": "Ruby", ".rbw": "Ruby", ".rbx": "Ruby", ".ru": "Ruby",
    ".ruby": "Ruby", ".thor": "Ruby", ".watchr": "Ruby", ".lua": "Lua", ".nse": "Lua", ".pd_lua": "Lua", ".rbxs": "Lua",
    ".rockspec": "Lua", ".wlua": "Lua", ".luau": "Luau", ".jl": "Julia", ".wl": "Wolfram", ".wls": "Wolfram",
    ".wlt": "Wolfram", ".mt": "Wolfram", ".mathematica": "Wolfram", ".hs": "Haskell", ".hs-boot": "Haskell", ".hsc": "Haskell", ".lhs": "Haskell", ".ml": "OCaml",
    ".mli": "OCaml", ".mll": "OCaml", ".mly": "OCaml", ".eliom": "OCaml", ".eliomi": "OCaml", ".ml4": "OCaml",
    ".sml": "Standard ML", ".sig": "Standard ML", ".fun": "Standard ML", ".bat": "Batchfile", ".cmd": "Batchfile",
    ".cs": "C#", ".csx": "C#", ".cake": "C#", ".linq": "C#", ".fsi": "F#", ".fsx": "F#", ".vb": "Visual Basic .NET",
    ".vbhtml": "Visual Basic .NET", ".php": "PHP", ".php3": "PHP", ".php4": "PHP", ".php5": "PHP", ".phps": "PHP",
    ".phpt": "PHP", ".aw": "PHP", ".ctp": "PHP", ".hack": "Hack", ".hhi": "Hack", ".blade": "Blade", ".twig": "Twig",
    ".jinja": "Jinja", ".jinja2": "Jinja", ".j2": "Jinja", ".vue": "Vue", ".svelte": "Svelte", ".astro": "Astro",
    ".hbs": "Handlebars", ".handlebars": "Handlebars", ".mustache": "Mustache", ".ejs": "EJS", ".ect": "EJS",
    ".jst": "EJS", ".liquid": "Liquid", ".njk": "Nunjucks", ".pug": "Pug", ".jade": "Pug", ".haml": "Haml",
    ".slim": "Slim", ".mako": "Mako", ".mao": "Mako", ".gohtml": "Go Template", ".gotmpl": "Go Template",
    ".xslt": "XSLT", ".xsl": "XSLT", ".dart": "Dart", ".mm": "Objective-C++", ".matlab": "MATLAB", ".scala": "Scala",
    ".sbt": "Scala", ".kojo": "Scala", ".sc": "Scala", ".groovy": "Groovy", ".gvy": "Groovy", ".gtpl": "Groovy",
    ".grt": "Groovy", ".gradle": "Gradle", ".clj": "Clojure", ".cljs": "Clojure", ".cljc": "Clojure",
    ".cljx": "Clojure", ".cljscm": "Clojure", ".cl2": "Clojure", ".hic": "Clojure", ".boot": "Clojure", ".ex": "Elixir",
    ".exs": "Elixir", ".erl": "Erlang", ".hrl": "Erlang", ".xrl": "Erlang", ".yrl": "Erlang", ".escript": "Erlang",
    ".gleam": "Gleam", ".elm": "Elm", ".purs": "PureScript", ".res": "ReScript", ".resi": "ReScript", ".re": "Reason",
    ".rei": "Reason", ".coffee": "CoffeeScript", "._coffee": "CoffeeScript", ".cjsx": "CoffeeScript",
    ".iced": "CoffeeScript", ".litcoffee": "CoffeeScript", ".rkt": "Racket", ".rktl": "Racket", ".scrbl": "Racket",
    ".scm": "Scheme", ".ss": "Scheme", ".sld": "Scheme", ".sps": "Scheme", ".lisp": "Common Lisp",
    ".asd": "Common Lisp", ".ny": "Common Lisp", ".podsl": "Common Lisp", ".el": "Emacs Lisp", ".emacs": "Emacs Lisp",
    ".fnl": "Fennel", ".janet": "Janet", ".hy": "Hy", ".pm": "Perl", ".perl": "Perl", ".ph": "Perl", ".plx": "Perl",
    ".psgi": "Perl", ".raku": "Raku", ".rakumod": "Raku", ".pm6": "Raku", ".pl6": "Raku", ".p6": "Raku", ".6pl": "Raku",
    ".6pm": "Raku", ".p6l": "Raku", ".p6m": "Raku", ".nqp": "Raku", ".r": "R", ".rsx": "R", ".coq": "Rocq Prover",
    ".thy": "Isabelle", ".agda": "Agda", ".lagda": "Agda", ".idr": "Idris", ".lidr": "Idris", ".fst": "F*",
    ".fsti": "F*", ".dfy": "Dafny", ".tla": "TLA", ".als": "Alloy", ".sage": "Sage", ".gap": "GAP", ".gi": "GAP",
    ".m2": "Macaulay2", ".stan": "Stan", ".do": "Stata", ".ado": "Stata", ".doh": "Stata", ".mata": "Stata",
    ".matah": "Stata", ".ihlp": "Stata", ".sthlp": "Stata", ".sas": "SAS", ".sci": "Scilab", ".sce": "Scilab",
    ".asy": "Asymptote", ".typ": "Typst", ".gnuplot": "Gnuplot", ".gnu": "Gnuplot", ".plot": "Gnuplot", ".zig": "Zig",
    ".nim": "Nim", ".nims": "Nim", ".nimble": "Nim", ".nimrod": "Nim", ".cr": "Crystal", ".odin": "Odin",
    ".mojo": "Mojo", ".carbon": "Carbon", ".vala": "Vala", ".vapi": "Vala", ".hx": "Haxe", ".hxsl": "Haxe",
    ".sol": "Solidity", ".vy": "Vyper", ".move": "Move", ".cairo": "Cairo", ".f": "Fortran", ".f77": "Fortran",
    ".for": "Fortran", ".fpp": "Fortran", ".f90": "Fortran", ".f95": "Fortran", ".f03": "Fortran", ".f08": "Fortran",
    ".adb": "Ada", ".ads": "Ada", ".ada": "Ada", ".cob": "COBOL", ".cbl": "COBOL", ".cobol": "COBOL", ".cpy": "COBOL",
    ".ccp": "COBOL", ".pas": "Pascal", ".dpr": "Pascal", ".lpr": "Pascal", ".pascal": "Pascal", ".asm": "Assembly",
    ".s": "Assembly", ".nasm": "Assembly", ".nas": "Assembly", ".a51": "Assembly", ".x68": "Assembly", ".ll": "LLVM",
    ".mlir": "MLIR", ".wat": "WebAssembly", ".wast": "WebAssembly", ".cu": "Cuda", ".cuh": "Cuda", ".metal": "Metal",
    ".hlsl": "HLSL", ".hlsli": "HLSL", ".fx": "HLSL", ".fxh": "HLSL", ".cginc": "HLSL", ".glsl": "GLSL",
    ".vert": "GLSL", ".frag": "GLSL", ".geom": "GLSL", ".tesc": "GLSL", ".tese": "GLSL", ".fp": "GLSL", ".frg": "GLSL",
    ".fsh": "GLSL", ".fshader": "GLSL", ".glslf": "GLSL", ".glslv": "GLSL", ".gshader": "GLSL", ".rchit": "GLSL",
    ".rmiss": "GLSL", ".vrx": "GLSL", ".vs": "GLSL", ".vsh": "GLSL", ".vshader": "GLSL", ".wgsl": "WGSL",
    ".shader": "ShaderLab", ".veo": "Verilog", ".sv": "SystemVerilog", ".svh": "SystemVerilog", ".vh": "SystemVerilog",
    ".vhd": "VHDL", ".vhdl": "VHDL", ".vhf": "VHDL", ".vhi": "VHDL", ".vho": "VHDL", ".vhs": "VHDL", ".vht": "VHDL",
    ".vhw": "VHDL", ".tcl": "Tcl", ".tm": "Tcl", ".adp": "Tcl", ".sdc": "Tcl", ".xdc": "Tcl", ".awk": "Awk",
    ".gawk": "Awk", ".mawk": "Awk", ".nawk": "Awk", ".auk": "Awk", ".sed": "sed", ".m4": "M4", ".mk": "Makefile",
    ".mak": "Makefile", ".make": "Makefile", ".makefile": "Makefile", ".mkfile": "Makefile", ".cmake": "CMake",
    ".dockerfile": "Dockerfile", ".containerfile": "Dockerfile", ".just": "Just", ".bzl": "Starlark",
    ".star": "Starlark", ".tf": "HCL", ".tfvars": "HCL", ".hcl": "HCL", ".nomad": "HCL", ".tofu": "HCL", ".nix": "Nix",
    ".bicep": "Bicep", ".bicepparam": "Bicep", ".dhall": "Dhall", ".jsonnet": "Jsonnet", ".libsonnet": "Jsonnet",
    ".cue": "CUE", ".pkl": "Pkl", ".nf": "Nextflow", ".proto": "Protocol Buffer", ".graphql": "GraphQL",
    ".gql": "GraphQL", ".graphqls": "GraphQL", ".thrift": "Thrift", ".capnp": "Cap'n Proto", ".g4": "ANTLR",
    ".y": "Yacc", ".yacc": "Yacc", ".lex": "Lex", ".swg": "SWIG", ".swig": "SWIG", ".bbappend": "BitBake",
    ".bbclass": "BitBake", ".pri": "QMake", ".feature": "Gherkin", ".story": "Gherkin", ".nsi": "NSIS", ".nsh": "NSIS",
    ".iss": "Inno Setup", ".isl": "Inno Setup", ".ahk": "AutoHotkey", ".ah1": "AutoHotkey", ".ah2": "AutoHotkey",
    ".ahkl": "AutoHotkey", ".applescript": "AppleScript", ".scpt": "AppleScript", ".pde": "Processing",
    ".prolog": "Prolog", ".yap": "Prolog", ".pwn": "Pawn", ".sma": "Pawn", ".mmd": "Mermaid", ".mermaid": "Mermaid",
    ".vim": "Vim script", ".vimrc": "Vim script", ".vmb": "Vim script", ".jq": "jq", ".apex": "Apex", ".qml": "QML",
    ".qbs": "QML", ".ftlh": "FreeMarker", ".di": "D", ".gdb": "GDB", ".gdbinit": "GDB", ".aspx": "ASP.NET",
    ".ascx": "ASP.NET", ".asax": "ASP.NET", ".ashx": "ASP.NET", ".asmx": "ASP.NET", ".axd": "ASP.NET", ".cocci": "SmPL",
    ".nasl": "NASL", ".pb": "PureBasic", ".pbi": "PureBasic", ".ampl": "AMPL", ".xs": "XS", ".aidl": "AIDL",
    ".fth": "Forth", ".4th": "Forth", ".forth": "Forth", ".frt": "Forth", ".rego": "Open Policy Agent",
    ".robot": "RobotFramework", ".scad": "OpenSCAD", ".smt2": "SMT", ".smt": "SMT",
    ".gd": "GDScript",   # GAP's declaration files too, but Godot's scripts are about four times as common
}
# Two-part suffixes, tried before the extension, so .blade.php is Blade and not PHP.
SUFFIXES = {
    ".blade.php": "Blade", ".html.eex": "HTML", ".html.tmpl": "Go Template", ".gradle.kts": "Gradle",
    ".app.src": "Erlang", ".coffee.md": "CoffeeScript", ".cmake.in": "CMake", ".sh.in": "Shell", ".rs.in": "Rust",
    ".tcl.in": "Tcl", ".zig.zon": "Zig", ".lagda.md": "Agda", ".lagda.tex": "Agda", ".lagda.rst": "Agda",
    ".lagda.org": "Agda", ".lagda.typ": "Agda", ".lagda.tree": "Agda",
}
# Whole file names, lowercase, tried first: files with no extension (Dockerfile, Makefile) and names whose
# extension would mislead or is excluded (CMakeLists.txt).
NAMES = {
    "dockerfile": "Dockerfile", "containerfile": "Dockerfile", "makefile": "Makefile", "gnumakefile": "Makefile",
    "bsdmakefile": "Makefile", "kbuild": "Makefile", "mkfile": "Makefile", "makefile.am": "Makefile",
    "makefile.in": "Makefile", "makefile.inc": "Makefile", "makefile.frag": "Makefile", "makefile.boot": "Makefile",
    "makefile.pc": "Makefile", "makefile.wat": "Makefile", "makefile.sco": "Makefile", "cmakelists.txt": "CMake",
    "meson.build": "Meson", "meson_options.txt": "Meson", "configure.ac": "M4", "build.bazel": "Starlark",
    "module.bazel": "Starlark", "workspace.bazel": "Starlark", "workspace.bzlmod": "Starlark", "buck": "Starlark",
    "tiltfile": "Starlark", "justfile": "Just", ".justfile": "Just", "earthfile": "Earthly", "procfile": "Procfile",
    "jenkinsfile": "Groovy", "gemfile": "Ruby", "rakefile": "Ruby", "podfile": "Ruby", "vagrantfile": "Ruby",
    "brewfile": "Ruby", "capfile": "Ruby", "guardfile": "Ruby", "fastfile": "Ruby", "dangerfile": "Ruby",
    "berksfile": "Ruby", "thorfile": "Ruby", "puppetfile": "Ruby", "jarfile": "Ruby", "mavenfile": "Ruby",
    "buildfile": "Ruby", "deliverfile": "Ruby", "snapfile": "Ruby", "steepfile": "Ruby", "appraisals": "Ruby",
    ".irbrc": "Ruby", ".pryrc": "Ruby", ".simplecov": "Ruby", "sconstruct": "Python", "sconscript": "Python",
    "wscript": "Python", ".gclient": "Python", "snakefile": "Python", "jakefile": "JavaScript",
    "cakefile": "CoffeeScript", "phakefile": "PHP", ".php_cs": "PHP", ".php_cs.dist": "PHP", "makefile.pl": "Perl",
    "cpanfile": "Perl", "rexfile": "Perl", "latexmkrc": "Perl", ".latexmkrc": "Perl", "emakefile": "Erlang",
    "rebar.config": "Erlang", "nextflow.config": "Nextflow", "pipfile": "TOML", ".clang-format": "YAML",
    ".clang-tidy": "YAML", ".clangd": "YAML", ".gemrc": "YAML", "citation.cff": "YAML", "_helpers.tpl": "Go Template",
    ".luacheckrc": "Lua", ".rprofile": "R", "contents.lr": "Markdown", "riemann.config": "Clojure", "nim.cfg": "Nim",
    "lexer.x": "Lex", ".gdbinit": "GDB", ".bashrc": "Shell", ".bash_profile": "Shell", ".bash_aliases": "Shell",
    ".bash_functions": "Shell", ".bash_logout": "Shell", ".profile": "Shell", ".zshrc": "Shell", ".zshenv": "Shell",
    ".zprofile": "Shell", ".zlogin": "Shell", ".zlogout": "Shell", ".kshrc": "Shell", ".cshrc": "Shell",
    ".login": "Shell", ".xinitrc": "Shell", ".xsession": "Shell", ".envrc": "Shell", "pkgbuild": "Shell",
    "bashrc": "Shell", "bash_profile": "Shell", "bash_aliases": "Shell", "bash_logout": "Shell", "zshrc": "Shell",
    "zshenv": "Shell", "zprofile": "Shell", "zlogin": "Shell", "zlogout": "Shell", "kshrc": "Shell", "cshrc": "Shell",
    "xinitrc": "Shell", ".vimrc": "Vim script", "_vimrc": "Vim script", "vimrc": "Vim script", ".gvimrc": "Vim script",
    "gvimrc": "Vim script", ".nvimrc": "Vim script", "nvimrc": "Vim script", ".exrc": "Vim script",
    ".emacs": "Emacs Lisp", "_emacs": "Emacs Lisp", ".spacemacs": "Emacs Lisp", ".gnus": "Emacs Lisp",
    ".viper": "Emacs Lisp", "cask": "Emacs Lisp", "eask": "Emacs Lisp",
}
# Whole file names matched as written, whose lowercase would claim a build script of anyone's (a file named build)
CASED_NAMES = {"BUILD": "Starlark", "WORKSPACE": "Starlark"}   # Bazel's, as Linguist names them
OTHER = "Other"
PROSE = {"Markdown"}  # not a programming language, so it is left out of the stats row's languages count

# The design lives in design/, apart from this code and under its own license (design/LICENSE.md): the
# themes (design/themes.json), the chart's colors (design/palette.json) and the wordmark
# (design/wordmark.svg). design/README.md says how they were made. Without design/ the generator draws in a
# plain look of its own, defined here: one grey theme in a lite and a nite, a few generic colors and no
# wordmark. A design/ that is there but cannot be read is an error, not a card quietly drawn plain.
DESIGN_DIR = os.path.join(HERE, "design")
PLAIN = {
    "order": ["plain"], "variants": {"plain": ["plain", "plain-nite"]},
    "themes": {
        "plain": dict(dark=False, bg="#ffffff", line="#d0d7de", text="#1f2328", muted="#59636e", dim="#8c959f",
                      prose="#afb8c1", other="#d8dee4", spotify="1f2328", grid=".05", mark=".08"),
        "plain-nite": dict(dark=True, bg="#010409", line="#30363d", text="#e6edf3", muted="#9198a1",
                           dim="#6e7681", prose="#c9d1d9", other="#3d444d", spotify="010409", grid=".035",
                           mark=".09"),
    },
    "green": "#2da44e", "red": "#cf222e", "yellow": "#bf8700", "yellow_lite": "#9a6700", "colors": {},
    "shared": {c: [] for c in ("#0969da", "#bf8700", "#8250df", "#1a7f37", "#bc4c00", "#0550ae", "#6639ba",
                               "#57606a")},
}


def load_design(folder=DESIGN_DIR):
    """design/'s themes and palette merged into one dict, or PLAIN when there is no design/ folder."""
    if not os.path.isdir(folder):
        return PLAIN
    design = {}
    for name in ("themes.json", "palette.json"):
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                design.update(json.load(f))
        except (OSError, ValueError):
            raise RuntimeError("the design in design/%s is missing or cannot be read" % name) from None
    return design


DESIGN = load_design()
# Each version of a theme: a lite for a visitor in light mode and a nite for one in dark mode. "spotify" is
# the widget's background when it is shown on its own, which only comes with white text, so a lite takes a
# deep tone of its own ink and a nite its own page; the relay instead recolors the widget to the version.
THEMES = {name: dict(tokens) for name, tokens in DESIGN["themes"].items()}
THEME_ORDER = list(DESIGN["order"])   # the strip's order, and the daily turn's
VARIANTS = {name: tuple(pair) for name, pair in DESIGN["variants"].items()}   # each theme's lite and nite
GREEN = DESIGN["green"]   # the bars that echo the Spotify widget's equalizer
RED = DESIGN["red"]       # the Pareto line, the one bright mark on the chart; and everything written, lit
YELLOW = DESIGN.get("yellow", PLAIN["yellow"])                  # what is still in use, lit, on a nite
YELLOW_LITE = DESIGN.get("yellow_lite", PLAIN["yellow_lite"])   # and on a lite, where the nite's would be too pale
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"   # the widget's stack
MONO = ("'IBM Plex Mono', ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', "
        "monospace")
# The chart's language colors, the same in every theme; only prose and Other follow the theme. A language
# listed in "colors" has its own; every other named language shares one of the "shared" colors, and those
# are also the spares a layer moves to when its own color would crowd one ranked above it (assign_colors).
COLORS = dict(DESIGN["colors"])
SHARED = {color: tuple(langs) for color, langs in DESIGN["shared"].items()}
COLORS.update((lang, color) for color, langs in SHARED.items() for lang in langs)
SPARE = list(SHARED)
MIN_APART = 12.0       # CIEDE2000: no two languages drawn together look closer than this
# The names too long to sit beside their share in a legend, wide or compact (at 0.6 em, beside the widest
# share, 100%), go by a shorter name their writers use there; the description for screen readers keeps the
# full name.
LEGEND_NAMES = {"Visual Basic .NET": "vb.net", "Open Policy Agent": "rego", "Protocol Buffer": "protobuf",
                "RobotFramework": "robot", "Objective-C++": "obj-c++", "SystemVerilog": "sysverilog"}
PANEL_W, PANEL_H = 576, 445

# The chart's geometry: the stream runs x0..x1 (x1 is now), a ribbon eases each layer into the column
# xc..xw, the legend sits right of it; the plot runs t0 (100%) to t1 (0%), ticks on the axis line.
X0, X1, XC, XW, T0, T1, AXIS_Y, TICK_Y = 40, 404, 428, 442, 202, 392, 406, 421
PLOT_W = X1 - X0
TOP_N = 8
H_X = 5.0             # kernel width, in panel units, so it scales with the axis whatever the span
ALPHA_FRAC = 0.05     # the bridge's pull: 5% of the typical lines per day within a kernel
NBINS = 4000          # events are pooled into this many slices of the log axis before the kernel runs
G_QUIET = 24.0        # a quiet stretch has to be at least this wide on the axis to count as one
QUIET_DAYS = 7.0      # and at least this long in time
VEIL = 0.55           # the veil's opacity where the mix rests on no evidence at all
TICK_CHAR = 8 * 0.6 + 1.3   # rendered width of one tick-label character
G_MIN = 2 * TICK_CHAR       # clear space kept between neighbouring tick labels
SNAP = 4.0                  # a data tick may sit at most this far from the moment it marks
MAX_TICKS = 6
LADDER = [1, 7, 30, 365, 90, 180] + [365 * k for k in range(2, 61)]   # round spans, in the order tried
FUTURE_SLACK = 86400        # a commit dated further ahead than this is a broken clock, and is left out

# Local days (see "Days" above). places.tsv.gz is built by tools/build_places.py from GeoNames data,
# licensed under Creative Commons Attribution 4.0.
PLACES_FILE = os.path.join(HERE, "places.tsv.gz")
PROFILE_TIMEOUT = 10        # seconds for the whole read of the public profile page
LOCATION_TIMEOUT = 30       # seconds for the query that reads the profile's location
PROFILE_LIMIT = 4 << 20     # a profile page larger than this is not read
LOCATION_LIMIT = 256        # characters of a location that are read
CLEAR_SHARE = 0.75          # a location has a zone only when one zone's rules cover this share of its people
JOINT_SHARE = 0.25          # places named together share a zone whose rules cover this share of each one's people
BIG_TOWN = 500000           # a town this big keeps a same-named region elsewhere from reading as clear ("Washington")
CODE_SHARE = 0.05           # beside a word nothing knows, a country's code that also abbreviates regions is read as
                            # the country if those regions hold less than this share of its people, as the regions if
                            # they hold more than twice its people, and otherwise not at all
# zones alike on every one of these days count days alike: from 2005, before which little history is dated, to two
# years past today, so zones that parted before 2016, as Indianapolis and New York did, stay apart
RULES_DAYS = (dt.date(2005, 1, 1).toordinal(),
              max(dt.date(2028, 1, 1), dt.date.today() + dt.timedelta(days=731)).toordinal())
PART_SPLIT = r"[,;/|()\[\]\n•·]+|\s[-–—]\s"   # how a location's parts are separated
SEGMENT_SPLIT = r"[;/|\n•·]|\s[-–—]\s"   # the separators among those that start another place, as commas and brackets do not
JOINERS = r"\s*(?:&|\+|->|→|↔|\band\b)\s*"   # how one part names two places ("Tokyo & Seoul"), if it is no name itself
# pronouns written as a set ("he/him", "they/them", "it/its"), taken out of a location before it is read
PRONOUNS = (r"(?i)\b(?:he|she|they|it|xe|ze|ey|fae|any)\s*/\s*(?:him|his|her|hers|they|them|their|theirs|it|its|xem|xyr|"
            r"zir|hir|em|faer|all|pronouns)(?:\s*/\s*(?:him|his|her|hers|they|them|their|theirs|it|its|xem|zir|all))*\b")
# letters that plain Unicode folding keeps apart from the letter people type for them ("København", "Łódź")
FOLD_LETTERS = str.maketrans({"ø": "o", "đ": "d", "ð": "d", "æ": "ae", "œ": "oe", "ł": "l", "þ": "th", "ı": "i",
                              "ħ": "h"})
NOT_PLACES = {"asia", "apac", "emea", "north", "south", "east", "west",   # words in profiles that towns share
              "he", "him", "his", "she", "her", "hers", "they", "them", "theirs", "he him", "she her", "they them",
              "he they", "she they", "it its", "any pronouns",
              # ordinary words, and names people write in jest, that are also a region or a town ("Islands",
              # "Spring", "The Valley", "Paradise", "Atlantis")
              "islands", "lakes", "unity", "plateau", "littoral", "maritime", "kara", "savanes", "oriental", "sud",
              "centro", "volta", "the valley", "west bay", "north shore", "south shore", "uptown", "spring", "bay",
              "union", "temple", "liberty", "forest", "university", "airport", "jupiter", "paradise", "atlantis",
              "nan", "troy", "zion", "eden", "crystal", "erlang", "orion", "shangri la", "vulcan",
              # names people write for somewhere other than the only places the table holds under them
              "surrey", "durham", "carolina", "labrador", "franconia", "coromandel", "st johns", "north jersey",
              "south jersey", "central jersey", "canton"}
LONE_WORDS = {"am", "pm", "est", "edt", "cst", "cdt", "mst", "mdt", "pst", "pdt", "akst", "hst", "et", "pt", "gmt", "utc",
              "bst", "cet", "cest", "eet", "eest", "wet", "ist", "jst", "kst", "aest", "aedt", "acst", "awst", "nzst",
              "nzdt", "sgt", "hkt", "pht", "wib", "ict", "msk", "cat", "eat", "wat", "sast", "brt", "art", "myt",
              "pkt", "npt", "gst", "ast", "adt", "nst", "ndt"}   # times of day and time zones, no place when alone
FILLER = {"remote", "remotely", "home", "home office", "anywhere", "everywhere", "worldwide", "earth", "planet earth",
          "global", "online", "internet", "the internet", "wfh", "work from home", "hybrid", "digital nomad", "nomad",
          "open to relocation", "relocation", "localhost"}   # words beside a place that name no place
# words around a place's name that are not part of it ("Greater London", "Based in Nairobi", "Oslo area",
# "Tokyo-to"), dropped only from a part the table does not know as written
LEAD_WORDS = ("based in", "living in", "located in", "currently in", "currently", "now in", "now", "in", "near",
              "the", "el", "al", "greater", "grand", "metro", "metropolitan", "downtown", "central", "inner", "upstate",
              "rural", "north", "south", "east", "west", "northern", "southern", "eastern", "western")
TRAIL_WORDS = ("area", "region", "metro area", "metropolitan area", "metropolitan region", "metro", "metropolitan",
               "county", "province", "prefecture", "district", "municipality", "department", "oblast",
               "governorate", "territory", "and surroundings", "surroundings", "office", "hq", "selatan", "utara",
               "barat", "timur", "pusat", "to", "fu", "ken", "shi", "si", "ku", "gu", "do")
# those that mark a city's surroundings: a name found only by dropping one is not read as a region that holds none
# of its towns ("Greater Washington" is not Washington State)
AREA_WORDS = {"greater", "grand", "metro", "metropolitan", "downtown", "inner", "area", "region", "metro area",
              "metropolitan area", "metropolitan region", "and surroundings", "surroundings"}
TAGS = {"ai", "ml"}         # read as places only when they are the whole location
KEEP_CODES = {"usa", "uae"}  # three letters that do mean a country when written alone, in any case
Place = namedtuple("Place", "id country region people zone")

# The current theme's colors; use_theme() sets them before each panel is drawn.
BG = LINE = TEXT = MUTED = DIM = OTHER_COLOR = ""
AS_OF = None   # the run's own day, written at the bars' right end so a panel that stops refreshing is dated
QUANTITY = None   # the headline's figures: lines of code written in the window, and of them production and tests
                  # still in use (see collect)
THEME = {}
LAYER_COLORS = {}

# The watermark sits behind the chart's column, 120 panel units across (scaled down further if a tall
# or turned outline would not fit), centred here, turned MARK_TURN degrees. The angle is part of the
# panel's design, not a setting.
MARK_WIDTH = 120
MARK_TURN = 10
MARK_CENTRE = (492, 372)
MARK_PX = 2          # raster pixels per panel unit; 2 lines them up exactly with the half-unit grid stroke
MARK_LIMIT = (8, 8, 566, 435)   # the raster stays clear of the panel's rounded corners
MARK_MAX_CHARS = 49152          # what a GitHub secret can hold
MARK_MAX_COORD = 1e6

# The coderprint wordmark: its letters, read from design/wordmark.svg, whose viewBox frames them, drawn in
# the headline's color in the bottom right corner, over the watermark.
WORDMARK_FILE = os.path.join(DESIGN_DIR, "wordmark.svg")
WORDMARK_WIDTH, WORDMARK_RIGHT, WORDMARK_BOTTOM = 118.0, 560.0, 438.0   # ends where the values end

SPOTIFY_URL = ("https://spotify-github-profile.kittinanx.com/api/view?uid={uid}"
               "&cover_image=true&theme=default&show_offline=false&background_color={bg}&interchange=false"
               "&profanity=false&hide_remaster=false")
# rayriffy/apple-music-github-profile's card of the track last played on Apple Music. It takes only a light
# or dark theme and the uid: no background, so beside the panel it keeps its own colors.
APPLE_MUSIC_URL = "https://music-profile.rayriffy.com/theme/{theme}.svg?uid={uid}"
ALT = ("Lines of code written and still in use, commit activity and language mix across the account's own "
       "repositories, not forks")
README_START, README_END = "<!-- coderprint:start -->", "<!-- coderprint:end -->"
# With a relay (CARDS_RELAY), the panel and the music card arrive as one merged image, so neither can
# show up before the other; with neither a relay nor a music card, the panel is shown alone. Either way
# the block holds two pictures, one for each color scheme, each showing the compact card on a screen 540
# CSS px wide or less and the wide one otherwise (Layout, above, says why it takes this shape): first a
# blank source for the other scheme, then the compact card, then the wide one. Every address is absolute:
# GitHub would resolve relative ones as well, and absolute ones also hold where nothing resolves them.
README_TWO = (
    '<a href="{link}#gh-dark-mode-only"><picture>'
    '<source media="(prefers-color-scheme: light)" srcset="{blank}">'
    '<source media="(max-width: 540px)" srcset="{compact_dark}">'
    '<img width="100%" alt="{alt}" src="{wide_dark}">'
    '</picture></a>'
    '<a href="{link}#gh-light-mode-only"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{blank}">'
    '<source media="(max-width: 540px)" srcset="{compact_light}">'
    '<img width="100%" alt="{alt}" src="{wide_light}">'
    '</picture></a>')
# the profile repository's: owner/owner for a person, owner/.github for an organization (profile_repository)
RAW_ASSETS = "https://raw.githubusercontent.com/{owner}/{repo}/HEAD/assets/"
BLANK_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="896" height="1" viewBox="0 0 896 1"/>\n'
# With a music card but no relay, two images side by side. One line with no whitespace between the tags:
# GitHub pads any image with align="right" by 20px, so a float would push the panel below the card, and
# a space between two inline images could wrap them. Inline and gapless, the two always fit, and their
# heights match: 64.1/35.6 = 576/320 beside the Spotify widget (320x445), and 32.0% beside Apple Music's
# card (345x534), since 64.1% x 445/576 x 345/534 = 32.0%.
README_PAIR = (
    '<p align="right">'
    '<a href="{link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{base}assets/panel-dark.svg">'
    '<source media="(prefers-color-scheme: light)" srcset="{base}assets/panel-light.svg">'
    '<img width="64.1%" alt="{alt}" src="{base}assets/panel-dark.svg">'
    '</picture></a>'
    '<a href="{music_link}"><picture>'
    '<source media="(prefers-color-scheme: dark)" srcset="{music_dark}">'
    '<source media="(prefers-color-scheme: light)" srcset="{music_light}">'
    '<img width="{music_width}" alt="{music_alt}" src="{music_dark}">'
    '</picture></a>'
    '</p>')
