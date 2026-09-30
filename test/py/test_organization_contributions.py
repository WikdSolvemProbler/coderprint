"""Local regressions for explicit organization scope and authored upload opt-in.

Usage: python test_organization_contributions.py path/to/coderprint.py
No fixture connects to GitHub. Git subprocesses have their own finite deadline.
"""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location("cp_organization_test", sys.argv[1])
cp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cp)

OWNER = "owner1"
ORG = "fixtureorg"
OWNER_EMAIL = "123+owner1@users.noreply.github.com"
IDENTITY = {"user": True, "id": 123, "name": "Owner One"}
SETTINGS = {
    "GH_TOKEN": "base-test-token",
    "CARDS_ORGANIZATIONS": ORG,
    "CARDS_ORGANIZATION_TOKENS": json.dumps({ORG: "org-test-token"}),
}


def fixture_env():
    env = dict(os.environ)
    env.pop("CARDS_ORGANIZATION_TOKENS", None)
    env.pop("CARDS_AUTHORED_IMPORTS", None)
    return env


def git(path, *args, author=("Owner One", OWNER_EMAIL)):
    env = fixture_env()
    env.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1],
               GIT_COMMITTER_NAME=author[0], GIT_COMMITTER_EMAIL=author[1],
               GIT_AUTHOR_DATE="1700000000 +0000", GIT_COMMITTER_DATE="1700000000 +0000")
    result = subprocess.run(
        ["git", "-C", str(path), "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *args],
        env=env, capture_output=True, timeout=60, check=False,
    )
    if result.returncode:
        raise AssertionError("local git fixture failed: " + result.stderr.decode("utf-8", "replace"))
    return result.stdout.decode("utf-8", "replace").strip()


def create_repo(root, directory, files):
    path = root / directory
    path.mkdir(parents=True)
    result = subprocess.run(["git", "init", "-q", "-b", "main", str(path)],
                            env=fixture_env(), capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise AssertionError("local git init failed: " + result.stderr.decode("utf-8", "replace"))
    for name, content in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "Authored source")
    return path, git(path, "rev-parse", "HEAD")


class OrganizationContributions(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, SETTINGS, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)
        cp.ACCESS_OWNER = None

    def test_repository_keys_preserve_personal_legacy_and_separate_same_name(self):
        personal = {"name": "shared"}
        organization = {"owner": "FixtureOrg", "name": "shared"}
        self.assertEqual(cp.repo_owner(OWNER, personal), OWNER)
        self.assertEqual(cp.repo_owner(OWNER, organization), "FixtureOrg")
        self.assertEqual(cp.repo_key(OWNER, personal), "shared")
        self.assertEqual(cp.repo_key(OWNER, organization), "fixtureorg/shared")
        self.assertNotEqual(cp.repo_key(OWNER, personal), cp.repo_key(OWNER, organization))

    def test_settings_validate_scope_and_keep_tokens_out_of_child_environment(self):
        with mock.patch.dict(os.environ, {
            "CARDS_ORGANIZATIONS": "FixtureOrg, second-org; THIRDorg",
            "CARDS_ORGANIZATION_TOKENS": '{"FIXTUREORG":"secret-fixture"}',
        }):
            self.assertEqual(cp.organization_settings(),
                             (["fixtureorg", "second-org", "thirdorg"], {"fixtureorg": "secret-fixture"}))
            self.assertNotIn("CARDS_ORGANIZATION_TOKENS", cp.child_env())
            self.assertNotIn("CARDS_AUTHORED_IMPORTS",
                             cp.child_env({"CARDS_AUTHORED_IMPORTS": "fixtureorg/shared@" + "a" * 40}))
        for organizations, tokens in (
            ("fixtureorg,FixtureOrg", "{}"),
            (", ".join("o%d" % n for n in range(33)), "{}"),
            ("bad/org", "{}"),
            ("fixtureorg", "{broken"),
            ("fixtureorg", '{"unlisted":"secret-fixture"}'),
            ("fixtureorg", '{"fixtureorg":42}'),
            ("fixtureorg", '{"fixtureorg":"first","fixtureorg":"secret-fixture"}'),
            ("fixtureorg", '{"fixtureorg":"first","FIXTUREORG":"secret-fixture"}'),
        ):
            with self.subTest(organizations=organizations, tokens=tokens):
                with mock.patch.dict(os.environ, {"CARDS_ORGANIZATIONS": organizations,
                                                   "CARDS_ORGANIZATION_TOKENS": tokens}):
                    with self.assertRaises(RuntimeError) as error:
                        cp.organization_settings()
                    self.assertNotIn("secret-fixture", str(error.exception))

    def test_repository_access_routes_credentials_and_restores_after_exception(self):
        self.assertEqual(cp.active_token(), "base-test-token")
        with self.assertRaisesRegex(ValueError, "fixture"):
            with cp.repository_access(ORG):
                self.assertEqual(cp.active_token(), "org-test-token")
                self.assertEqual(cp.github_env()["GH_TOKEN"], "org-test-token")
                self.assertNotIn("CARDS_ORGANIZATION_TOKENS", cp.github_env())
                flags, env = cp.git_auth(ORG, "shared")
                self.assertIn("credential.helper=", flags)
                self.assertIn("http.https://github.com/.extraheader=", flags)
                self.assertEqual(env["GIT_CONFIG_KEY_0"],
                                 "http.https://github.com/%s/shared.git.extraheader" % ORG)
                self.assertIn("AUTHORIZATION: basic ", env["GIT_CONFIG_VALUE_0"])
                self.assertNotIn("base-test-token", env["GIT_CONFIG_VALUE_0"])
                self.assertNotIn("CARDS_ORGANIZATION_TOKENS", env)
                self.assertEqual(os.environ["GH_TOKEN"], "base-test-token")
                raise ValueError("fixture")
        self.assertEqual(cp.active_token(), "base-test-token")
        self.assertEqual(os.environ["GH_TOKEN"], "base-test-token")

    def test_plain_read_environment_strips_tokens_but_gql_selects_one(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "secondary-test-token"}):
            for env in (cp.child_env(), cp.read_env()):
                self.assertNotIn("GH_TOKEN", env)
                self.assertNotIn("GITHUB_TOKEN", env)
                self.assertNotIn("CARDS_ORGANIZATION_TOKENS", env)
            chosen = []
            def fake_run(args, **kwargs):
                chosen.append(kwargs["env"])
                return b'{"data":{"viewer":{"login":"owner1"}}}'
            with mock.patch.object(cp, "run", side_effect=fake_run):
                self.assertEqual(cp.gql("query { viewer { login } }")["viewer"]["login"], OWNER)
                with cp.repository_access(ORG):
                    self.assertEqual(cp.gql("query { viewer { login } }")["viewer"]["login"], OWNER)
            self.assertEqual([env["GH_TOKEN"] for env in chosen],
                             ["base-test-token", "org-test-token"])
            self.assertTrue(all("GITHUB_TOKEN" not in env and
                                "CARDS_ORGANIZATION_TOKENS" not in env for env in chosen))
            # An explicitly chosen subprocess environment survives spawn's child_env copy.
            self.assertEqual(cp.child_env(chosen[1])["GH_TOKEN"], "org-test-token")

    def test_github_token_only_personal_install_selects_gh_token_for_gql(self):
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "github-only-token"}):
            os.environ.pop("GH_TOKEN", None)
            self.assertEqual(cp.active_token(), "github-only-token")
            self.assertNotIn("GITHUB_TOKEN", cp.github_env())
            self.assertEqual(cp.github_env()["GH_TOKEN"], "github-only-token")
            flags, env = cp.git_auth(OWNER, "shared")
            self.assertEqual(env["GH_TOKEN"], "github-only-token")
            self.assertNotIn("GITHUB_TOKEN", env)
            self.assertIn("credential.helper=", flags)

    def test_git_auth_removes_inherited_headers_and_helpers(self):
        inherited = {
            "GIT_CONFIG_COUNT": "4",
            "GIT_CONFIG_KEY_0": "http.proxy",
            "GIT_CONFIG_VALUE_0": "http://proxy.invalid:3128",
            "GIT_CONFIG_KEY_1": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_1": "AUTHORIZATION: basic inherited-secret",
            "GIT_CONFIG_KEY_2": "credential.helper",
            "GIT_CONFIG_VALUE_2": "!unsafe-helper",
            "GIT_CONFIG_KEY_3": "http.https://other.invalid/.extraheader",
            "GIT_CONFIG_VALUE_3": "AUTHORIZATION: basic other-secret",
            "GIT_CONFIG_PARAMETERS": "'http.extraheader=AUTHORIZATION: basic parameter-secret'",
        }
        with mock.patch.dict(os.environ, inherited), cp.repository_access(ORG):
            flags, env = cp.git_auth(ORG, "shared")
            self.assertEqual(env["GIT_CONFIG_COUNT"], "2")
            self.assertEqual(env["GIT_CONFIG_KEY_0"], "http.proxy")
            self.assertEqual(env["GIT_CONFIG_VALUE_0"], inherited["GIT_CONFIG_VALUE_0"])
            self.assertEqual(env["GIT_CONFIG_KEY_1"],
                             "http.https://github.com/%s/shared.git.extraheader" % ORG)
            self.assertNotIn("GIT_CONFIG_PARAMETERS", env)
            self.assertNotIn("inherited-secret", str(env))
            self.assertNotIn("other-secret", str(env))
            self.assertNotIn("parameter-secret", str(env))
            self.assertNotIn("unsafe-helper", str(env))
            self.assertIn("credential.helper=", flags)
            observed = subprocess.run(["git", *flags, "config", "--list"], env=env,
                                      capture_output=True, timeout=60, check=True).stdout.decode(
                                          "utf-8", "replace")
            self.assertIn("http.proxy=http://proxy.invalid:3128", observed)
            for leaked in ("inherited-secret", "other-secret", "parameter-secret", "unsafe-helper"):
                self.assertNotIn(leaked, observed)

    def test_git_auth_rejects_mismatched_repository_owner(self):
        with cp.repository_access(ORG):
            with self.assertRaises((RuntimeError, ValueError)) as error:
                cp.git_auth(OWNER, "shared")
            self.assertNotIn("org-test-token", str(error.exception))
            with self.assertRaises((RuntimeError, ValueError, TypeError)):
                cp.git_auth()
            for bad_owner, bad_name in (
                (ORG, "../shared"),
                (ORG, "shared/other"),
                (ORG, ".."),
                ("bad/owner", "shared"),
                (ORG, "shared?token=leak"),
            ):
                with self.subTest(owner=bad_owner, name=bad_name):
                    with self.assertRaises((RuntimeError, ValueError)):
                        cp.git_auth(bad_owner, bad_name)

    def test_listing_adds_org_owner_without_overwriting_personal_same_name(self):
        def fake_gql(query, **kwargs):
            if kwargs["owner"] == OWNER:
                return {"repositoryOwner": {"repositories": {
                    "nodes": [{"name": "shared", "isPrivate": True}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
            self.assertEqual(cp.active_token(), "org-test-token")
            return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                "nodes": [{"name": "shared", "isPrivate": True}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}

        with mock.patch.object(cp, "gql", side_effect=fake_gql):
            repos = cp.list_repositories(OWNER)
        self.assertEqual([cp.repo_key(OWNER, r) for r in repos], ["shared", "fixtureorg/shared"])
        self.assertNotIn("owner", repos[0])
        self.assertEqual(repos[1]["owner"], ORG)
        self.assertEqual(cp.active_token(), "base-test-token")

    def test_listing_omits_first_cursor_and_uses_next_page_cursor(self):
        calls = []
        def fake_gql(query, **kwargs):
            calls.append(dict(kwargs))
            account = kwargs["owner"]
            if account == OWNER:
                self.assertNotIn("cursor", kwargs)
                return {"repositoryOwner": {"repositories": {
                    "nodes": [{"name": "personal"}],
                    "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
            self.assertEqual(account, ORG)
            if "cursor" not in kwargs:
                return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                    "nodes": [{"name": "first"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "real-cursor"}}}}
            self.assertEqual(kwargs["cursor"], "real-cursor")
            return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                "nodes": [{"name": "second"}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        with mock.patch.object(cp, "gql", side_effect=fake_gql):
            repos = cp.list_repositories(OWNER)
        self.assertEqual(calls, [{"owner": OWNER}, {"owner": ORG},
                                 {"owner": ORG, "cursor": "real-cursor"}])
        self.assertEqual([cp.repo_key(OWNER, r) for r in repos],
                         ["personal", ORG + "/first", ORG + "/second"])

    def test_organization_only_skips_personal_discovery_and_requires_org_scope(self):
        asked = []
        def fake_gql(query, **kwargs):
            asked.append(kwargs["owner"])
            self.assertEqual(kwargs["owner"], ORG)
            return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                "nodes": [{"name": "shared", "isPrivate": True}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        with mock.patch.dict(os.environ, {"CARDS_ORGANIZATION_ONLY": "true"}):
            with mock.patch.object(cp, "gql", side_effect=fake_gql):
                repos = cp.list_repositories(OWNER)
            self.assertEqual(asked, [ORG])
            self.assertEqual([cp.repo_key(OWNER, r) for r in repos], [ORG + "/shared"])
        with mock.patch.dict(os.environ, {"CARDS_ORGANIZATIONS": "",
                                          "CARDS_ORGANIZATION_TOKENS": "{}",
                                          "CARDS_ORGANIZATION_ONLY": "true"}):
            with self.assertRaises(RuntimeError):
                cp.organization_settings()

    def test_listing_rejects_wrong_account_and_cyclic_org_pagination(self):
        def page(query, **kwargs):
            if kwargs["owner"] == OWNER:
                return {"repositoryOwner": {"repositories": {
                    "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
            return {"repositoryOwner": {"__typename": "User", "repositories": {
                "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        with mock.patch.object(cp, "gql", side_effect=page):
            with self.assertRaisesRegex(RuntimeError, "organization") as error:
                cp.list_repositories(OWNER)
        self.assertNotIn(ORG, str(error.exception))

        def cyclic(query, **kwargs):
            if kwargs["owner"] == OWNER:
                return {"repositoryOwner": {"repositories": {
                    "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
            return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                "nodes": [{"name": "second" if kwargs.get("cursor") else "shared"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "repeat"}}}}
        with mock.patch.object(cp, "gql", side_effect=cyclic):
            with self.assertRaisesRegex(RuntimeError, "pagination"):
                cp.list_repositories(OWNER)

        def duplicate(query, **kwargs):
            if kwargs["owner"] == OWNER:
                return {"repositoryOwner": {"repositories": {
                    "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
            return {"repositoryOwner": {"__typename": "Organization", "repositories": {
                "nodes": [{"name": "shared"}, {"name": "SHARED"}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        with mock.patch.object(cp, "gql", side_effect=duplicate):
            with self.assertRaisesRegex(RuntimeError, "repository"):
                cp.list_repositories(OWNER)

    def test_org_template_is_external_to_profile_even_when_org_owned(self):
        def fake_answered(query, **kwargs):
            self.assertEqual(kwargs["owner"], ORG)
            return {"repositoryOwner": {"repositories": {
                "nodes": [{"name": "shared",
                           "templateRepository": {"nameWithOwner": ORG + "/base"}}],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}, []
        with mock.patch.object(cp, "answered", side_effect=fake_answered):
            self.assertEqual(cp.templates(ORG, profile_owner=OWNER), {"shared": ORG + "/base"})
            self.assertEqual(cp.templates(ORG), {})

    def test_author_lookup_uses_qualified_org_sample_and_org_token(self):
        sha = "a" * 40
        seen = []
        def fake_answered(query, **kwargs):
            seen.append((query, cp.active_token()))
            return {"r0": {"c0": {"author": {"user": {"login": OWNER}}}}}, []
        with mock.patch.object(cp, "answered", side_effect=fake_answered):
            self.assertEqual(cp.resolve_authors(OWNER, {"linked@example.test": (ORG + "/shared", sha)}),
                             {"linked@example.test": OWNER})
        self.assertEqual(len(seen), 1)
        self.assertIn('repository(owner: "%s", name: "shared")' % ORG, seen[0][0])
        self.assertEqual(seen[0][1], "org-test-token")
        self.assertEqual(cp.active_token(), "base-test-token")

    def test_org_authorship_never_uses_name_or_solo_fallback(self):
        personal = {"name": "shared"}
        organization = {"owner": ORG, "name": "shared"}
        repos = [personal, organization, {"owner": ORG, "name": "solo"}]
        entries = [
            (0, OWNER_EMAIL, "Owner One"),
            (1, OWNER_EMAIL, "Owner One"),
            (1, "linked@example.test", "Another Name"),
            (1, "unknown@example.test", "Owner One"),
            (1, "listed@example.test", "Other Name"),
            (1, "refused@example.test", "Other Name"),
            (2, "solo@example.test", "Owner One"),
        ]
        commits = [cp.Commit(1700000000 + n, repo, "%040x" % (n + 1), False, email, name, "fixture", [])
                   for n, (repo, email, name) in enumerate(entries)]
        linked = {"linked@example.test": OWNER, "refused@example.test": "someone-else"}
        with mock.patch.object(cp, "resolve_authors", side_effect=lambda owner, samples:
                               {e: linked.get(e) for e in samples}), mock.patch.dict(
                                   os.environ, {"CARDS_AUTHOR_EMAILS":
                                                "listed@example.test refused@example.test"}):
            notes = {}
            owned = cp.authorship(OWNER, commits, IDENTITY, repos, notes)
        self.assertIn((1, OWNER_EMAIL), owned)
        self.assertIn((1, "linked@example.test"), owned)
        self.assertIn((1, "listed@example.test"), owned)
        self.assertNotIn((1, "unknown@example.test"), owned)
        self.assertNotIn((1, "refused@example.test"), owned)
        self.assertNotIn((2, "solo@example.test"), owned)
        self.assertEqual(notes["refused"], 1)

    def test_card_data_reports_org_scope_as_aggregates_without_private_identifiers(self):
        now = 1700000000
        repos = [{"owner": ORG, "name": "secret-private-repo", "isPrivate": True}]
        data = {
            "events": [(now - 10, "Lean", 3)], "commits": [now - 10],
            "imports": [], "import_lines": [], "mismatched": 0, "unread": 0,
            "left_out": {}, "left_out_times": [], "unsure": set(),
            "authored_imports": [(now - 10, 2)],
            "code": {"production": 2, "tests": 0, "unread": 0},
            "authors": {"unknown": 0, "commits": 0, "refused": 0},
        }
        with mock.patch.dict(os.environ, {"CARDS_ORGANIZATION_ONLY": "true"}), mock.patch.object(
                cp, "QUANTITY", {"written": 3, "production": 2, "tests": 0}):
            card = cp.card_data(
                OWNER, "all", now, None, float("-inf"), 1.0, repos, True, data,
                (1, 1, 1, 1, 1), [0] * 52, [0] * 52,
                [(0.1, "Lean", 3)], [(0.1, "Lean", 3)], {}, OWNER)
        scope = card["scope"]
        self.assertEqual(scope["organization_repositories"], 1)
        self.assertTrue(scope["organization_only"])
        self.assertFalse(scope["owned_only"])
        self.assertEqual(scope["repositories"]["visible"], 1)
        self.assertEqual(scope["declared_authored_uploads"]["commits"], 1)
        self.assertEqual(scope["declared_authored_uploads"]["loc"], 2)
        text = json.dumps(card)
        for private in ("secret-private-repo", ORG, "org-test-token",
                        "CARDS_ORGANIZATION_TOKENS", "other@example.test"):
            self.assertNotIn(private, text)

    def test_unread_organization_keeps_existing_readme_panels_and_data(self):
        with tempfile.TemporaryDirectory(prefix="organization-preserve-") as tmp:
            root = Path(tmp)
            assets = root / "assets"
            assets.mkdir()
            readme = root / "README.md"
            panel = assets / "panel-dark.svg"
            data_file = assets / "coderprint.json"
            originals = {
                readme: b"# Previous card\n",
                panel: b"<svg>previous panel</svg>",
                data_file: b'{"previous":"card"}',
            }
            for path, content in originals.items():
                path.write_bytes(content)
            unread = {
                "unchecked": [], "organization_unread": 1, "unread": 1,
                "unsure": set(), "now": int(time.time()),
            }
            with mock.patch.object(cp, "WORK", str(root)), mock.patch.object(
                    cp, "OUT_DIR", str(assets)), mock.patch.object(
                    cp, "README", str(readme)), mock.patch.object(
                    cp, "settings", return_value=("all", None, None, None, None, None, None)), mock.patch.object(
                    cp, "owner_login", return_value=OWNER), mock.patch.object(
                    cp, "own_card_only", return_value=None), mock.patch.object(
                    cp, "profile_repository", return_value=(OWNER, str(readme))), mock.patch.object(
                    cp, "repositories_last_time", return_value=None), mock.patch.object(
                    cp, "profile_offset", return_value=None), mock.patch.object(
                    cp, "profile_location", return_value=""), mock.patch.object(
                    cp, "list_repositories", return_value=[
                        {"owner": ORG, "name": "secret-private-repo", "isPrivate": True}]), mock.patch.object(
                    cp, "collect", return_value=unread), mock.patch.dict(
                    os.environ, {"CLONE_CACHE": str(root / "cache"), "FORCE": "1"}):
                message = io.StringIO()
                with contextlib.redirect_stdout(message):
                    code = cp.main()
            self.assertEqual(code, 1)
            self.assertIn("organization repository could not be read or attributed", message.getvalue())
            self.assertNotIn("secret-private-repo", message.getvalue())
            self.assertNotIn("org-test-token", message.getvalue())
            for path, content in originals.items():
                self.assertEqual(path.read_bytes(), content)

    def test_exact_authored_upload_override_after_authorship_filter(self):
        with tempfile.TemporaryDirectory(prefix="organization-contributions-") as tmp:
            root = Path(tmp)
            personal, _ = create_repo(root, "personal-shared", {"personal.lean": "def personal := 1\n"})
            imported = {"Upload/File%03d.lean" % n: "def uploaded%03d := %d\n" % (n, n)
                        for n in range(501)}
            organization, upload_sha = create_repo(root, "organization-shared", imported)
            outsider_files = {"Other/File%03d.lean" % n: "def other%03d := %d\n" % (n, n)
                             for n in range(501)}
            for name, content in outsider_files.items():
                target = organization / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            git(organization, "add", "-A", author=("Owner One", "other@example.test"))
            git(organization, "commit", "-q", "-m", "Other authored upload",
                author=("Owner One", "other@example.test"))
            outsider_sha = git(organization, "rev-parse", "HEAD")
            sources = {(OWNER, "shared"): personal, (ORG, "shared"): organization}
            clone_calls = []

            def fake_clone(account, name, dest):
                clone_calls.append((account.lower(), name))
                source = sources[(account.lower(), name)]
                result = subprocess.run(["git", "clone", "-q", "--bare", str(source), dest],
                                        env=fixture_env(), capture_output=True, timeout=60, check=False)
                if result.returncode:
                    raise AssertionError("local clone failed: " +
                                         result.stderr.decode("utf-8", "replace"))

            repos = [{"name": "shared", "isPrivate": True},
                     {"owner": ORG, "name": "shared", "isPrivate": True}]
            patches = (
                mock.patch.object(cp, "clone", side_effect=fake_clone),
                mock.patch.object(cp, "owner_identity", return_value=IDENTITY),
                mock.patch.object(cp, "templates", return_value={}),
                mock.patch.object(cp, "seed_blobs", return_value=set()),
                mock.patch.object(cp, "resolve_authors", side_effect=lambda owner, samples:
                                  {email: "collaborator" if email == "other@example.test" else None
                                   for email in samples}),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                def collect_with(override):
                    work = root / ("work-" + str(len(clone_calls)))
                    work.mkdir()
                    with mock.patch.dict(os.environ, {"CARDS_AUTHORED_IMPORTS": override}):
                        return cp.collect(OWNER, repos, str(work))

                normal = collect_with("")
                wrong = collect_with(ORG + "/shared@" + "f" * 40)
                allowed = collect_with(ORG + "/shared@" + upload_sha)
                outsider_allowed = collect_with(ORG + "/shared@" + outsider_sha)
            self.assertEqual(set(clone_calls), {(OWNER, "shared"), (ORG, "shared")})
            self.assertEqual(sum(n for _, _, n in normal["events"]), 1)
            self.assertEqual(sum(n for _, _, n in wrong["events"]), 1)
            self.assertEqual(sum(n for _, _, n in allowed["events"]), 502)
            self.assertEqual(sum(n for _, _, n in outsider_allowed["events"]), 1)
            self.assertGreaterEqual(len(normal["imports"]), 1)
            self.assertEqual(len(allowed["imports"]), 0)
            self.assertEqual(normal["authored_imports"], [])
            self.assertEqual(wrong["authored_imports"], [])
            self.assertEqual(allowed["authored_imports"], [(1700000000, 501)])
            self.assertEqual(outsider_allowed["authored_imports"], [])


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]], verbosity=2)
