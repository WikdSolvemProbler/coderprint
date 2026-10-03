# coderprint's the owner, the tokens and the repositories: listing and cloning them. coderprint.py runs this file as
# part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported on its
# own.


# ---------------------------------------------------------------- collect


def owner_login():
    """The account to report on: CARDS_OWNER in Actions, where the token belongs to an App, else gh's user."""
    return os.environ.get("CARDS_OWNER") or gql("query { viewer { login } }")["viewer"]["login"]


ACCESS_OWNER = None   # credentials for the current repository operation; the profile identity never changes
PROFILE_OWNER = None
PUBLIC_ACCESS = False
ORGANIZATION_SNAPSHOT = None  # authenticated, locally refreshed history; never queried or fetched from GitHub


def organization_settings():
    """Explicit organization scope and optional per-installation tokens; invalid settings never echo their values."""
    organizations = [s.lower() for s in re.split(r"[\s,;]+", os.environ.get("CARDS_ORGANIZATIONS", "").strip()) if s]
    if len(organizations) > 32 or any(not re.fullmatch(r"[A-Za-z0-9-]{1,39}", s) for s in organizations):
        raise RuntimeError("organizations must list at most 32 GitHub organization logins")
    if len(organizations) != len(set(organizations)):
        raise RuntimeError("organizations must list unique GitHub organization logins")
    if ORGANIZATION_SNAPSHOT is not None:
        frozen = [s.lower() for s in ORGANIZATION_SNAPSHOT.organizations]
        if set(organizations) & set(frozen):
            raise RuntimeError("a saved organization must not also be configured for live access")
        organizations += frozen
    only = os.environ.get("CARDS_ORGANIZATION_ONLY", "false").strip().lower()
    if only not in ("true", "false") or only == "true" and not organizations:
        raise RuntimeError("organization-only must be true or false, and needs at least one configured organization")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        raw = json.loads(os.environ.get("CARDS_ORGANIZATION_TOKENS", "").strip() or "{}",
                         object_pairs_hook=unique_object)
    except (ValueError, TypeError):
        raise RuntimeError("organization-tokens must be a JSON object of organization installation tokens") from None
    if not isinstance(raw, dict):
        raise RuntimeError("organization-tokens must be a JSON object of organization installation tokens")
    tokens = {}
    for name, token in raw.items():
        if (not isinstance(name, str) or name.lower() not in organizations or name.lower() in tokens
                or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,4096}", token)):
            raise RuntimeError("organization-tokens must map configured organizations to valid tokens")
        tokens[name.lower()] = token
    return organizations, tokens


def repo_owner(owner, repo):
    return repo.get("owner", owner)


def repo_key(owner, repo):
    account = repo_owner(owner, repo)
    return repo["name"] if account.lower() == owner.lower() else account.lower() + "/" + repo["name"]


def snapshot_store(owner):
    store = os.environ.get("CARDS_SNAPSHOT_STORE", "").strip()
    if not store:
        return ""
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", store):
        raise RuntimeError("snapshot-store must name a personal repository")
    account, name = store.split("/")
    if account.lower() != owner.lower() or name in (".", "..") or name.lower() == owner.lower():
        raise RuntimeError("snapshot-store must name a separate personal repository")
    return store


def active_token():
    organizations, tokens = organization_settings()
    account = (ACCESS_OWNER or "").lower()
    if ORGANIZATION_SNAPSHOT is not None and account in ORGANIZATION_SNAPSHOT.organizations:
        return None
    if PUBLIC_ACCESS:
        return None
    if account in organizations:
        if account in tokens:
            return tokens[account]
        if os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"):
            raise RuntimeError("each configured organization needs its own organization-tokens entry")
        return None   # a local gh session may already have explicitly granted organization access
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def child_env(env=None):
    plain = env is None
    env = dict(os.environ if env is None else env)
    # A process reading one repository has no reason to receive the other installations' credentials.
    env.pop("CARDS_ORGANIZATION_TOKENS", None)
    env.pop("CARDS_AUTHORED_IMPORTS", None)
    env.pop("CARDS_ORGANIZATION_SNAPSHOT_KEY", None)
    if plain:
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    return env


def github_env():
    env = child_env()
    token = active_token()
    if token:
        env["GH_TOKEN"] = token
        env.pop("GITHUB_TOKEN", None)
    elif PUBLIC_ACCESS:
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
    return env


@contextmanager
def repository_access(owner, public=False):
    global ACCESS_OWNER, PUBLIC_ACCESS
    previous, prior_public, ACCESS_OWNER, PUBLIC_ACCESS = ACCESS_OWNER, PUBLIC_ACCESS, owner, public
    try:
        yield
    finally:
        ACCESS_OWNER = previous
        PUBLIC_ACCESS = prior_public


def authored_imports(owner):
    """Exact upload commits the owner identifies as their existing work; this never overrides authorship."""
    entries = [s for s in re.split(r"[\s,;]+", os.environ.get("CARDS_AUTHORED_IMPORTS", "").strip()) if s]
    allowed = set(organization_settings()[0]) | {owner.lower()}
    result = set()
    if len(entries) > 256:
        raise RuntimeError("authored-imports may list at most 256 repository and commit pairs")
    for entry in entries:
        match = re.fullmatch(r"([A-Za-z0-9-]{1,39})/([A-Za-z0-9._-]{1,100})@([0-9a-fA-F]{40}|[0-9a-fA-F]{64})", entry)
        if not match or match[1].lower() not in allowed or match[2] in (".", ".."):
            raise RuntimeError("authored-imports must list configured owner/repository@full-commit-hash pairs")
        result.add((match[1].lower() + "/" + match[2].lower(), match[3].lower()))
    if ORGANIZATION_SNAPSHOT is not None:
        result |= ORGANIZATION_SNAPSHOT.uploads
    return result


def list_repositories(owner):
    """Every non-fork repository the account owns, a page of 100 at a time, bar the profile repository, with
    whether it can be read (a disabled or locked repository is counted but never cloned) and whether it is archived
    (its history is read, its head is not in use)."""
    global PROFILE_OWNER
    PROFILE_OWNER = owner
    organizations, _ = organization_settings()
    nodes, cursor = [], None
    while os.environ.get("CARDS_ORGANIZATION_ONLY", "false").strip().lower() != "true":
        page_args = {"owner": owner}
        if cursor:
            page_args["cursor"] = cursor
        data = gql("""
          query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
            repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                         orderBy: {field: CREATED_AT, direction: ASC}) {
              nodes { name isPrivate isDisabled isLocked isArchived } pageInfo { hasNextPage endCursor } } } }""",
                   **page_args)
        if not data.get("repositoryOwner"):
            raise RuntimeError("GitHub has no account named by CARDS_OWNER")
        page = data["repositoryOwner"]["repositories"]
        nodes += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    nodes = [r for r in nodes if r["name"].lower() != owner.lower()]
    store = snapshot_store(owner)
    if store:
        account, name = store.split("/")
        nodes = [r for r in nodes if r["name"].lower() != name.lower()]
    for organization in organizations:
        if ORGANIZATION_SNAPSHOT is not None and organization in ORGANIZATION_SNAPSHOT.organizations:
            nodes += [dict(r) for r in ORGANIZATION_SNAPSHOT.repositories if r["owner"].lower() == organization]
            continue
        cursor, seen, found = None, set(), set()
        with repository_access(organization):
            while True:
                page_args = {"owner": organization}
                if cursor:
                    page_args["cursor"] = cursor
                data = gql("""query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
                    __typename repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false,
                    orderBy: {field: CREATED_AT, direction: ASC}) {
                    nodes { name isPrivate isDisabled isLocked isArchived } pageInfo { hasNextPage endCursor } } } }""",
                    **page_args)
                account = data.get("repositoryOwner")
                if not isinstance(account, dict) or account.get("__typename") != "Organization":
                    raise RuntimeError("a configured organization could not be read")
                page = account["repositories"]
                for repo in page["nodes"]:
                    name = repo.get("name") if isinstance(repo, dict) else None
                    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) or name in (".", ".."):
                        raise RuntimeError("a configured organization returned invalid repository metadata")
                    if name.lower() in found:
                        raise RuntimeError("a configured organization returned duplicate repository metadata")
                    nodes.append(dict(repo, owner=organization))
                    found.add(name.lower())
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]
                if not isinstance(cursor, str) or not cursor or cursor in seen:
                    raise RuntimeError("a configured organization returned invalid pagination")
                seen.add(cursor)
        if not found:
            raise RuntimeError("no repositories are visible in a configured organization; check its read token")
    return nodes


def git_auth(owner, name):
    """How git authenticates. With GH_TOKEN set (Actions), the token rides in an environment-only
    header, never on a command line. Otherwise gh's own credential helper answers."""
    if (ACCESS_OWNER is not None and ACCESS_OWNER.lower() != owner.lower()
            or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner)
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) or name in (".", "..")):
        raise RuntimeError("the repository URL does not match its credential scope")
    token = active_token()
    clean = ["-c", "credential.helper=", "-c", "http.extraheader=", "-c", "http.https://github.com/.extraheader="]
    env = github_env()
    count = env.get("GIT_CONFIG_COUNT", "").strip()
    count = int(count) if re.fullmatch(r"[0-9]{1,4}", count) else 0
    settings = [(env.get("GIT_CONFIG_KEY_%d" % k, ""), env.get("GIT_CONFIG_VALUE_%d" % k, "")) for k in range(count)]
    settings = [(key, value) for key, value in settings
                if key and not key.lower().endswith(".extraheader") and key.lower() != "credential.helper"]
    for key in list(env):
        if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")) or key == "GIT_CONFIG_PARAMETERS":
            env.pop(key)
    for k, (key, value) in enumerate(settings):
        env["GIT_CONFIG_KEY_%d" % k], env["GIT_CONFIG_VALUE_%d" % k] = key, value
    env["GIT_CONFIG_COUNT"] = str(len(settings))
    if PUBLIC_ACCESS:
        return clean, env
    if not token:
        return clean + ["-c", "credential.helper=!gh auth git-credential"], env
    basic = base64.b64encode(("x-access-token:" + token).encode()).decode()
    # after any settings the environment already passes this way (a self-hosted runner's certificate bundle or
    # proxy), not over them; a count git would refuse anyway is replaced
    n = len(settings)
    path = "%s/%s.git" % (owner, name)
    env.update({"GIT_CONFIG_COUNT": str(n + 1), "GIT_CONFIG_KEY_%d" % n: "http.https://github.com/%s.extraheader" % path,
                "GIT_CONFIG_VALUE_%d" % n: "AUTHORIZATION: basic " + basic, "GIT_TERMINAL_PROMPT": "0"})
    return clean, env


@contextmanager
def clone_directory(dest, env):
    """Isolate an initial clone from the caller checkout's local Git config.

    actions/checkout can include a separate write-token config from its own
    Git directory. An initial `git clone` launched there can send that header
    along with coderprint's read-token header. A fresh child directory and a
    ceiling at its parent keep Git from discovering any ancestor checkout,
    including when CLONE_CACHE itself lives inside one. Global proxy and CA
    configuration still apply.
    """
    absolute = os.path.abspath(dest)
    parent = os.path.realpath(os.path.dirname(absolute))
    with tempfile.TemporaryDirectory(prefix=".coderprint-clone-", dir=parent) as scratch:
        selected = dict(env)
        selected["GIT_CEILING_DIRECTORIES"] = parent
        for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
            selected.pop(name, None)
        yield os.path.realpath(scratch), selected, absolute


def clone(owner, name, dest):
    """Bare clone of every branch and tag. Output is swallowed, because it would name the repository. A cached
    clone (CLONE_CACHE) is pointed at this repository's address before fetching, so a slot can never read another,
    and is brought to what a fresh clone would hold: its branches and tags fetched and those deleted upstream pruned,
    so a tag a force-push left behind brings in nothing, and its HEAD pointed where the repository's own points now,
    so a default branch renamed or switched since is the one read at the head."""
    if ORGANIZATION_SNAPSHOT is not None and owner.lower() in ORGANIZATION_SNAPSHOT.organizations:
        ORGANIZATION_SNAPSHOT.restore_repository(
            owner, name, dest, types.SimpleNamespace(run=run, child_env=child_env, remove_tree=remove_tree))
        return
    flags, env = git_auth(owner, name)
    url = "https://github.com/%s/%s.git" % (owner, name)
    if os.path.isdir(dest):
        run(["git", "-C", dest, "remote", "set-url", "origin", url])
        run(["git", "-C", dest] + flags + ["fetch", "--quiet", "--prune", "origin", "+refs/heads/*:refs/heads/*",
                                           "+refs/tags/*:refs/tags/*"], env=env)
        said = run(["git", "-C", dest] + flags + ["ls-remote", "--symref", "origin", "HEAD"], env=env)
        points = re.search(r"(?m)^ref: (refs/heads/[^\t\n]+)\tHEAD$", said.decode("utf-8", "replace"))
        if points:
            run(["git", "-C", dest, "symbolic-ref", "HEAD", points.group(1)])
        return
    with clone_directory(dest, env) as (cwd, selected, absolute):
        run(["git"] + flags + ["clone", "--bare", "--quiet", url, absolute], cwd=cwd, env=selected)
