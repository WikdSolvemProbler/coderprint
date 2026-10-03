# coderprint's whose each commit is: templates, the owner's identity and their addresses. coderprint.py runs this
# file as part of one module, after the parts before it in PARTS, so it uses their names freely; it is not imported
# on its own.


def templates(owner, profile_owner=None):
    """The template each repository was made from, when that is another account's: {name: owner/name}, or {name:
    None} for a repository whose template GitHub answers with an error for, as it may for a template the token
    cannot see. Asked apart from the listing, so such a template never fails the listing, and each page is asked
    twice before giving up. None when GitHub cannot be asked, or answers with an error that names no repository:
    the files of the templates it would have named would then count as written (see collect)."""
    if ORGANIZATION_SNAPSHOT is not None and owner.lower() in ORGANIZATION_SNAPSHOT.organizations:
        return ORGANIZATION_SNAPSHOT.templates_by_owner[owner.lower()]
    found, cursor = {}, None
    query = """
      query($owner: String!, $cursor: String) { repositoryOwner(login: $owner) {
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
          nodes { name templateRepository { nameWithOwner } } pageInfo { hasNextPage endCursor } } } }"""
    try:
        while True:
            page_args = {"owner": owner}
            if cursor:
                page_args["cursor"] = cursor
            data, errors = again(lambda: answered(query, **page_args))
            page = data["repositoryOwner"]["repositories"]
            unseen = set()   # the places on this page of the repositories an error names
            for e in errors:
                path = e.get("path") if isinstance(e, dict) else None
                if not (isinstance(path, list) and path[:3] == ["repositoryOwner", "repositories", "nodes"]
                        and len(path) > 3 and isinstance(path[3], int)):
                    return None
                unseen.add(path[3])
            for k, node in enumerate(page["nodes"]):
                if not isinstance(node, dict) or not isinstance(node.get("name"), str):
                    return None
                made = (node.get("templateRepository") or {}).get("nameWithOwner") or ""
                if made and made.split("/")[0].lower() != (profile_owner or owner).lower():
                    found[node["name"]] = made
                elif k in unseen and not made:
                    found[node["name"]] = None
            if not page["pageInfo"]["hasNextPage"]:
                return found
            cursor = page["pageInfo"]["endCursor"]
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None


def owner_identity(owner):
    """Whether the account is a person, and a person's account id and profile name, for telling their commits
    from other people's. None when it cannot be read, even on a second try."""
    def ask():
        found = gql("query($owner: String!) { repositoryOwner(login: $owner) { __typename "
                    "... on User { databaseId name } } }", owner=owner)["repositoryOwner"]
        return {"user": found["__typename"] == "User", "id": found.get("databaseId"), "name": found.get("name") or ""}
    try:
        return again(ask)
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None


def resolve_authors(owner, samples):
    """Whose GitHub account each email address is, asked through one commit that uses it: samples maps an
    address to (repository name, commit hash), in the order to ask them. Returns {address: login, or None when the
    address belongs to no account}. Addresses past RESOLVE_CALLS queries of ALIASES are left out, and so is one
    GitHub answers with an error or with nothing for, as for a repository deleted since it was read. Each query is
    asked twice before giving up. Raises RuntimeError if GitHub cannot be asked, or answers with an error that names
    no address, so the caller never guesses (see collect)."""
    global PROFILE_OWNER
    PROFILE_OWNER = owner
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", owner):
        raise RuntimeError("the account's login cannot be looked up")
    found, groups = {}, {}
    for email, sample in samples.items():
        if not isinstance(sample, (list, tuple)) or len(sample) != 2 or not all(isinstance(s, str) for s in sample):
            continue
        name, sha = sample
        account, name = name.split("/", 1) if "/" in name else (owner, name)
        if (re.fullmatch(r"[A-Za-z0-9-]{1,39}", account)
                and re.fullmatch(r"[A-Za-z0-9._-]{1,100}", name) and name not in (".", "..")
                and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha)):
            groups.setdefault(account.lower(), []).append((email, (name, sha)))
    if ORGANIZATION_SNAPSHOT is not None:
        for account in list(groups):
            if account in ORGANIZATION_SNAPSHOT.organizations:
                evidence = ORGANIZATION_SNAPSHOT.authors_by_owner[account]
                found.update({email: evidence[email] for email, _ in groups.pop(account)
                              if email in evidence and evidence[email] != ""})
    batches = [(account, items[k:k + ALIASES]) for account, items in groups.items()
               for k in range(0, min(len(items), RESOLVE_CALLS * ALIASES), ALIASES)][:RESOLVE_CALLS]
    for account, batch in batches:
        by_repo = {}
        for j, (_, (name, sha)) in enumerate(batch):
            by_repo.setdefault(name, []).append((j, sha))
        query = " ".join('r%d: repository(owner: "%s", name: "%s") { %s }' % (
            r, account, name, " ".join('c%d: object(oid: "%s") { ... on Commit { author { user { login } } } }' % pair
                                       for pair in shas))
            for r, (name, shas) in enumerate(by_repo.items()))
        with repository_access(account):
            data, errors = again(lambda: answered("query { %s }" % query))
        failed = set()   # what an error names: ("r1",) for a whole repository, ("r1", "c3") for one commit
        for e in errors:
            path = e.get("path") if isinstance(e, dict) else None
            if not isinstance(path, list) or not path or not re.fullmatch(r"r\d+", str(path[0])):
                raise RuntimeError("the GitHub API answered with an error")
            failed.add(tuple(str(p) for p in path[:2]))
        for r, (name, shas) in enumerate(by_repo.items()):
            repo = data.get("r%d" % r)
            for j, _ in shas:
                node = repo.get("c%d" % j) if isinstance(repo, dict) else None
                if (("r%d" % r,) in failed or ("r%d" % r, "c%d" % j) in failed or not isinstance(node, dict)
                        or not isinstance(node.get("author"), dict)):
                    continue   # not answered: the address stays unknown
                user = node["author"].get("user")
                found[batch[j][0]] = user.get("login") if isinstance(user, dict) else None
    return found


def author_emails():
    """The addresses CARDS_AUTHOR_EMAILS lists, however the list is written: separated by commas, semicolons, spaces
    or new lines (as a YAML block or folded list gives them), each bare or as git prints it, Name <address>. An entry
    without an @ is no address, and is left out."""
    listed = {e.strip("<>\"'()[]").lower() for e in re.split(r"[\s,;]+", os.environ.get("CARDS_AUTHOR_EMAILS", ""))
              if "@" in e}
    return listed | (ORGANIZATION_SNAPSHOT.author_emails if ORGANIZATION_SNAPSHOT is not None else set())


def agent_name(name):
    """Whether a commit's name is a bot's or a coding agent's own (AGENT_NAME)."""
    return bool(AGENT_NAME.search(name.strip().casefold()))


def authorship(owner, commits, identity, repos, notes=None):
    """The addresses whose commits are the owner's, as (repository, address). The owner's noreply addresses are
    theirs, a noreply address of the id+login form is theirs by their account id whatever login it was made under
    and otherwise another account's, and every other address is looked up on GitHub, with no lookup needed for a
    noreply address of either form. One that belongs to another account is someone else's; so is one listed in
    CARDS_AUTHOR_EMAILS that does, and every other listed address is the owner's. One that belongs to none is the
    owner's under a name the owner's own commits, login or profile use (a name a machine or a tutorial gives, as
    GENERIC_NAMES, or a bot's or an agent's, tells no one), and otherwise in a repository with no other human address
    (a solo repository is its owner's, whatever laptop it was committed from), unless its name is a bot's or a
    coding agent's own (AGENT_NAME); the owner's own linked addresses count as other addresses there. One GitHub was
    not asked about, past the lookup's limit or unanswered, counts only under such a name.

    In another account's organization repositories, the name and solo-repository fallbacks are disabled:
    only a linked owner address, owner noreply identity or explicitly listed non-conflicting address counts.

    The lookup asks first the addresses listed in CARDS_AUTHOR_EMAILS, then those found in more of the account's
    repositories (the owner's own recur; a mirrored project's thousand authors each sit in one), those under a
    name the owner uses, those alone in a repository, and then the most used, so the ones whose answer is likeliest
    to change what counts are asked within its limit. Returns None, so every commit counts, for an organization,
    whose members' work is all its own, or when GitHub cannot be asked (see collect). notes, when given, gets
    "agents": the (repository, address) pairs left out as a bot's or an agent's, "refused": how many listed
    addresses belong to another account, and "unknown": the addresses GitHub was not asked about."""
    if not identity or not identity["user"]:
        return None
    mine = {"%s@users.noreply.github.com" % owner.lower()}
    if identity["id"]:
        mine.add("%d+%s@users.noreply.github.com" % (identity["id"], owner.lower()))
    human = [c for c in commits if not c.bot]
    # a noreply address of the id+login form names its account by an id no change of login alters, so it needs no
    # lookup; one of the older login-only form is looked up like any address, since the owner's own from before a
    # change of login no longer resolves, and then counts by the rules below
    noreply = {}
    for e in {c.email for c in human}:
        m = NOREPLY.fullmatch(e)
        if m and identity["id"]:
            noreply[e] = int(m.group(1)) == identity["id"]
    mine |= {e for e, own in noreply.items() if own}
    listed = author_emails()
    uses, where, called, per_repo, samples = Counter(), {}, {}, {}, {}
    for c in human:
        uses[c.email] += 1
        where.setdefault(c.email, set()).add(c.repo)
        called.setdefault(c.email, set()).add(c.name.casefold())
        per_repo.setdefault(c.repo, set()).add(c.email)
        # Prefer an organization sample so a shared address cannot inherit a personal repository's fallback.
        if c.email not in samples or repo_owner(owner, repos[c.repo]).lower() != owner.lower():
            samples[c.email] = (repo_key(owner, repos[c.repo]), c.sha)

    def own_names():   # the names the owner's own commits, login and profile use, that tell a person
        found = {n for n in (c.name.casefold() for c in human if c.email in mine)
                 if n not in GENERIC_NAMES and not agent_name(n)}
        return (found | {owner.casefold(), identity["name"].casefold()}) - {""}
    alone = {next(iter(emails)) for emails in per_repo.values() if len(emails) == 1}
    known = own_names()
    rank = lambda e: (e not in listed, -len(where[e]), not called[e] & known, e not in alone, -uses[e], e)
    asked = {e: samples[e] for e in sorted(uses, key=rank) if e not in mine and e not in noreply}
    try:
        login = resolve_authors(owner, asked)
    except (RuntimeError, ValueError, KeyError, TypeError, AttributeError):
        return None
    for email, who in login.items():
        if who and who.lower() == owner.lower():
            mine.add(email)
    theirs = ({e for e, who in login.items() if who and who.lower() != owner.lower()}
              | {e for e, own in noreply.items() if not own})
    mine |= listed - theirs
    unknown = set(asked) - set(login) - mine
    names = own_names()
    owned, agents = set(), set()
    for c in human:
        pair = (c.repo, c.email)
        organization = repo_owner(owner, repos[c.repo]).lower() != owner.lower()
        if c.email in mine or (not organization and c.email not in theirs and c.name.casefold() in names):
            owned.add(pair)
        elif c.email in theirs or c.email in unknown:
            continue
        elif agent_name(c.name):
            agents.add(pair)
        elif not organization and len(per_repo[c.repo]) == 1:
            owned.add(pair)
    if notes is not None:
        notes.update(agents=agents, refused=len(listed & theirs & set(uses)), unknown=unknown)
    return owned


def slot(work, owner, name):
    """A cache folder named by a hash of the repository, so it is stable and writes no name to disk."""
    return os.path.join(work, hashlib.sha256((owner + "/" + name).lower().encode()).hexdigest()[:16] + ".git")
