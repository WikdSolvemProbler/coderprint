"""Synthetic authenticated snapshot and offline Git restore regression checks."""

import base64
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile


SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "coderprint.py"
sys.argv = [sys.argv[0]]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("snapshot_test_module", SOURCE.parent / "organization_snapshot.py")
snapshot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snapshot)


KEY = base64.b64encode(b"s" * 32).decode("ascii")
OTHER_KEY = base64.b64encode(b"t" * 32).decode("ascii")


def git(directory, *args, env=None):
    return subprocess.run(["git", "-C", str(directory), *args], capture_output=True,
                          timeout=30, check=True, env=env).stdout.decode("utf-8").strip()


class OrganizationSnapshot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="snapshot-fixture-")
        cls.root = Path(cls.temporary.name)
        cls.repo = cls.root / "source"
        cls.repo.mkdir()
        git(cls.repo, "init", "-q", "-b", "main")
        git(cls.repo, "config", "user.name", "Synthetic Author")
        git(cls.repo, "config", "user.email", "author@example.test")
        (cls.repo / "sample.py").write_text("print('synthetic')\n", encoding="utf-8")
        git(cls.repo, "add", "sample.py")
        git(cls.repo, "commit", "-qm", "synthetic first")
        git(cls.repo, "branch", "alternate")
        git(cls.repo, "tag", "v-fixture")
        git(cls.repo, "update-ref", "refs/notes/fixture", "HEAD")
        (cls.repo / "sample.py").write_text("print('synthetic second')\n", encoding="utf-8")
        git(cls.repo, "commit", "-qam", "synthetic second")
        cls.commit = git(cls.repo, "rev-parse", "HEAD")
        cls.bundle = cls.root / "complete.bundle"
        git(cls.repo, "bundle", "create", str(cls.bundle), "--all")
        cls.digest = hashlib.sha256(cls.bundle.read_bytes()).hexdigest()
        cls.base = {
            "schema": snapshot.SCHEMA, "owner": "Owner1", "user_id": 123,
            "as_of": datetime.now(timezone.utc).date().isoformat(), "organizations": ["FixtureOrg"],
            "repositories": [{"owner": "FixtureOrg", "name": "synthetic-project",
                              "isPrivate": True, "isArchived": False, "isDisabled": False,
                              "isLocked": False, "empty": False,
                              "bundle": "repositories/0.bundle", "sha256": cls.digest,
                              "default_head": "refs/heads/main"}],
            "templates_by_owner": {"fixtureorg": {"synthetic-project": "TemplateOwner/template"}},
            "authors_by_owner": {"fixtureorg": {"author@example.test": "Owner1",
                                                "unlinked@example.test": None,
                                                "unknown@example.test": ""}},
            "seed_blobs_by_source": {"TemplateOwner/template": ["a" * 40]},
            "authored_imports": ["FixtureOrg/synthetic-project@" + cls.commit],
            "author_emails": ["local@example.test"],
        }

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="snapshot-test-")
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "history.enc"
        self.manifest = copy.deepcopy(self.base)

    def write(self, manifest=None):
        snapshot.write_snapshot(self.path, KEY, manifest or self.manifest, [self.bundle])

    def encrypted_zip(self, entries):
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in entries:
                archive.writestr(name, data)
        nonce = os.urandom(12)
        ciphertext = snapshot._aes()(snapshot._key(KEY)).encrypt(nonce, output.getvalue(), snapshot._aad("owner1"))
        self.path.write_bytes(snapshot.MAGIC + nonce + ciphertext)

    def manifest_entries(self, manifest=None):
        return [("manifest.json", json.dumps(manifest or self.manifest)),
                ("repositories/0.bundle", self.bundle.read_bytes())]

    def reject_load(self, **kwargs):
        with self.assertRaises(snapshot.SnapshotError) as caught:
            with snapshot.load_snapshot(self.path, kwargs.pop("key", KEY), kwargs.pop("owner", "owner1"), **kwargs):
                pass
        self.assertNotIn("synthetic-project", str(caught.exception))
        self.assertNotIn(str(self.path), str(caught.exception))
        self.assertNotIn(KEY, str(caught.exception))

    def test_authenticated_roundtrip_and_nonce_randomness(self):
        self.write()
        first = self.path.read_bytes()
        self.assertTrue(first.startswith(snapshot.MAGIC))
        for secret in (b"FixtureOrg", b"synthetic-project", b"author@example.test", b"synthetic second"):
            self.assertNotIn(secret, first)
        self.write()
        self.assertNotEqual(first, self.path.read_bytes())
        with snapshot.load_snapshot(self.path, KEY, "OWNER1") as loaded:
            self.assertEqual(loaded.user_id, 123)
            self.assertEqual(loaded.author_emails, {"local@example.test"})
            self.assertEqual(loaded.uploads, {("fixtureorg/synthetic-project", self.commit)})
            self.assertTrue(loaded.has_repository("FIXTUREORG", "SYNTHETIC-PROJECT"))
            self.assertFalse(loaded.has_repository("other", "synthetic-project"))
            self.assertEqual(loaded.seed_blobs_by_source["templateowner/template"], {"a" * 40})
            self.assertEqual(loaded.authors_by_owner["fixtureorg"]["unknown@example.test"], "")
            temporary = loaded._temporary.name
            self.assertTrue(Path(temporary).exists())
        self.assertFalse(Path(temporary).exists())

    def test_wrong_key_owner_tamper_and_unknown_version_fail(self):
        self.write()
        self.reject_load(key=OTHER_KEY)
        self.reject_load(owner="another-owner")
        artifact = bytearray(self.path.read_bytes())
        artifact[-1] ^= 1
        self.path.write_bytes(artifact)
        self.reject_load()
        artifact[len(snapshot.MAGIC) - 1] = 2
        self.path.write_bytes(artifact)
        self.reject_load()

    def test_key_encoding_is_strict(self):
        self.write()
        for key in ("", KEY + "\n", base64.b64encode(b"short").decode(), KEY[:-1] + "_", None):
            with self.subTest(key_length=len(key) if isinstance(key, str) else None):
                self.reject_load(key=key)

    def test_future_stale_and_invalid_dates_fail(self):
        self.write()
        tomorrow = (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        self.reject_load(minimum_day=tomorrow)
        for value in ("2026-02-30", "2026-1-01", "today", tomorrow):
            self.manifest["as_of"] = value
            self.encrypted_zip(self.manifest_entries())
            self.reject_load()

    def test_malformed_manifest_rejected_before_replacement(self):
        self.write()
        good = self.path.read_bytes()
        mutations = [
            lambda m: m.update(user_id=True),
            lambda m: m.update(schema="coderprint/organization-snapshot/99"),
            lambda m: m.update(owner="bad/owner"),
            lambda m: m.update(organizations=["FixtureOrg", "fixtureorg"]),
            lambda m: m.update(organizations=["Owner1"]),
            lambda m: m["repositories"].append(copy.deepcopy(m["repositories"][0])),
            lambda m: m["repositories"][0].update(bundle="../outside.bundle"),
            lambda m: m["repositories"][0].update(default_head="refs/heads/main.lock"),
            lambda m: m["repositories"][0].update(default_head=None),
            lambda m: m["repositories"][0].update(isPrivate="true"),
            lambda m: m["repositories"][0].update(sha256="0" * 64),
            lambda m: m["repositories"][0].update(owner="AnotherOrg"),
            lambda m: m["repositories"][0].update(bundle=None, sha256=None),
            lambda m: m.update(author_emails=["unsafe\n@example.test"]),
            lambda m: m.update(author_emails=["duplicate@example.test"] * 2),
            lambda m: m["templates_by_owner"]["fixtureorg"].update(unlisted="Owner/template"),
            lambda m: m["seed_blobs_by_source"].update({"TemplateOwner/template": ["a" * 40] * 2}),
            lambda m: m["authored_imports"].append(m["authored_imports"][0]),
            lambda m: m.update(extra="not accepted"),
        ]
        for mutation in mutations:
            manifest = copy.deepcopy(self.base)
            mutation(manifest)
            with self.subTest(mutation=mutations.index(mutation)):
                with self.assertRaises(snapshot.SnapshotError):
                    self.write(manifest)
                self.assertEqual(self.path.read_bytes(), good)
        self.assertEqual(list(self.path.parent.glob(".snapshot-*.tmp")), [])

    def test_zip_traversal_duplicates_symlinks_extra_and_bad_hash_fail(self):
        symlink = zipfile.ZipInfo("repositories/1.bundle")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        additions = [("../outside", b"bad"), ("repositories/0.bundle", b"duplicate"),
                     (symlink, b"destination"), ("extra.json", b"{}"),
                     ("repositories/00.bundle", b"bad")]
        for extra in additions:
            with self.subTest(kind=str(extra[0])):
                with patch("warnings.warn"):
                    self.encrypted_zip(self.manifest_entries() + [extra])
                self.reject_load()
        manifest = copy.deepcopy(self.base)
        manifest["repositories"][0]["sha256"] = "0" * 64
        self.encrypted_zip(self.manifest_entries(manifest))
        self.reject_load()
        entries = self.manifest_entries()
        entries[0] = ("manifest.json", json.dumps(self.manifest)[:-1] + ',"owner":"owner1"}')
        self.encrypted_zip(entries)
        self.reject_load()

    def test_expansion_ciphertext_and_repository_limits_fail(self):
        self.write()
        with patch.object(snapshot, "MAX_CIPHERTEXT", 10):
            self.reject_load()
        with patch.object(snapshot, "MAX_UNCOMPRESSED", 100):
            self.reject_load()
            with self.assertRaises(snapshot.SnapshotError):
                self.write()
        with patch.object(snapshot, "MAX_MANIFEST", 10):
            self.reject_load()
        manifest = copy.deepcopy(self.base)
        manifest["repositories"] *= 101
        with self.assertRaises(snapshot.SnapshotError):
            self.write(manifest)

    def test_incomplete_bundle_rejected(self):
        incomplete = Path(self.tmp.name) / "partial.bundle"
        git(self.repo, "bundle", "create", str(incomplete), "HEAD~1..HEAD")
        self.manifest["repositories"][0]["sha256"] = hashlib.sha256(incomplete.read_bytes()).hexdigest()
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.write_snapshot(self.path, KEY, self.manifest, [incomplete])
        self.encrypted_zip([("manifest.json", json.dumps(self.manifest)),
                            ("repositories/0.bundle", incomplete.read_bytes())])
        self.reject_load()

    def runner(self, calls):
        def run(args, env=None, timeout=None):
            self.assertGreater(timeout, 0)
            calls.append((args, env))
            self.assertEqual(env["GIT_ALLOW_PROTOCOL"], "file")
            self.assertFalse(any("SNAPSHOT" in name.upper() or name.startswith("CARDS_") for name in env))
            self.assertNotIn("GH_TOKEN", env)
            return subprocess.run(args, capture_output=True, env=env, timeout=min(timeout, 30), check=True).stdout
        return SimpleNamespace(run=run)

    def test_restore_preserves_all_refs_default_head_and_no_remote(self):
        self.write()
        calls = []
        dest = Path(self.tmp.name) / "restored.git"
        with patch.dict(os.environ, {"CARDS_SNAPSHOT_KEY": KEY, "MY_SNAPSHOT_SECRET": KEY, "GH_TOKEN": "fixture-token"}):
            with snapshot.load_snapshot(self.path, KEY, "owner1") as loaded:
                loaded.restore_repository("fixtureorg", "synthetic-project", dest, self.runner(calls))
        self.assertEqual(git(dest, "show-ref"), git(self.repo, "show-ref"))
        self.assertEqual(git(dest, "symbolic-ref", "HEAD"), "refs/heads/main")
        self.assertEqual(git(dest, "rev-parse", "HEAD"), self.commit)
        self.assertEqual(git(dest, "remote"), "")
        self.assertTrue(all("https://" not in str(args) and "fetch" not in args for args, _ in calls))
        with snapshot.load_snapshot(self.path, KEY, "owner1") as loaded:
            with self.assertRaises(snapshot.SnapshotError):
                loaded.restore_repository("fixtureorg", "synthetic-project", dest, self.runner([]))

    def test_restore_detached_head(self):
        self.manifest["repositories"][0]["default_head"] = self.commit
        self.write()
        dest = Path(self.tmp.name) / "detached.git"
        with snapshot.load_snapshot(self.path, KEY, "owner1") as loaded:
            loaded.restore_repository("fixtureorg", "synthetic-project", dest, self.runner([]))
        self.assertEqual((dest / "HEAD").read_text().strip(), self.commit)

    def test_empty_and_unread_repositories(self):
        empty = self.manifest["repositories"][0]
        empty.update(empty=True, bundle=None, sha256=None, default_head="refs/heads/unborn")
        self.manifest["authored_imports"] = []
        snapshot.write_snapshot(self.path, KEY, self.manifest, [])
        dest = Path(self.tmp.name) / "empty.git"
        with snapshot.load_snapshot(self.path, KEY, "owner1") as loaded:
            loaded.restore_repository("fixtureorg", "synthetic-project", dest, self.runner([]))
        self.assertEqual(git(dest, "symbolic-ref", "HEAD"), "refs/heads/unborn")
        self.assertEqual(git(dest, "for-each-ref"), "")
        empty.update(empty=False, isDisabled=True, default_head=None)
        snapshot.write_snapshot(self.path, KEY, self.manifest, [])
        with snapshot.load_snapshot(self.path, KEY, "owner1") as loaded:
            with self.assertRaises(snapshot.SnapshotError):
                loaded.restore_repository("fixtureorg", "synthetic-project", Path(self.tmp.name) / "unread.git", self.runner([]))

    def test_missing_and_symlink_target_rejected(self):
        self.reject_load()
        directory = Path(self.tmp.name) / "folder"
        directory.mkdir()
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.write_snapshot(directory, KEY, self.manifest, [self.bundle])
        self.write()
        linked = Path(self.tmp.name) / "linked.enc"
        try:
            linked.symlink_to(self.path)
        except OSError:
            return  # Windows can require an administrator to create symlinks.
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.load_snapshot(linked, KEY, "owner1")
        with self.assertRaises(snapshot.SnapshotError):
            snapshot.write_snapshot(linked, KEY, self.manifest, [self.bundle])

    def load_collector(self):
        spec = importlib.util.spec_from_file_location("snapshot_collector_test", SOURCE)
        cp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cp)
        return cp

    def test_full_collector_union_matches_live_and_never_queries_offline_org(self):
        cp = self.load_collector()
        personal = Path(self.tmp.name) / "personal"
        git(self.repo, "clone", "--quiet", str(self.repo), str(personal))
        git(personal, "config", "user.name", "Synthetic Author")
        git(personal, "config", "user.email", "author@example.test")
        (personal / "personal.py").write_text("personal_quantity = 3\n", encoding="utf-8")
        git(personal, "add", "personal.py")
        git(personal, "commit", "-qm", "personal extra work")
        self.manifest["templates_by_owner"] = {"fixtureorg": {}}
        self.manifest["seed_blobs_by_source"] = {}
        self.manifest["authored_imports"] = []
        self.manifest["author_emails"] = ["author@example.test"]
        self.write()
        real_run = cp.run
        offline = False
        org_queries, org_transfers = [], []

        def low_level_run(args, **kwargs):
            args = list(args)
            for index, arg in enumerate(args):
                if isinstance(arg, str) and arg.startswith("https://github.com/"):
                    if "/fixtureorg/" in arg:
                        self.assertFalse(offline, "offline restore attempted a GitHub organization transfer")
                        org_transfers.append(arg)
                        args[index] = str(self.repo)
                    elif "/owner1/" in arg:
                        args[index] = str(personal)
                    else:
                        self.fail("unexpected synthetic GitHub transfer")
            return real_run(args, **kwargs)

        def gql(query, **kwargs):
            account = kwargs["owner"].lower()
            if account == "fixtureorg":
                self.assertFalse(offline, "offline scope made an organization listing query")
                org_queries.append("listing")
            name = "synthetic-project" if account == "fixtureorg" else "personal-project"
            return {"repositoryOwner": {"__typename": "Organization" if account == "fixtureorg" else "User",
                    "repositories": {"nodes": [{"name": name, "isPrivate": True, "isArchived": False,
                                                 "isDisabled": False, "isLocked": False}],
                                     "pageInfo": {"hasNextPage": False, "endCursor": None}}}}

        def answered(query, **kwargs):
            org = kwargs.get("owner", "").lower() == "fixtureorg" or 'owner: "fixtureorg"' in query
            if org:
                self.assertFalse(offline, "offline attribution or templates made an organization query")
                org_queries.append("metadata")
            if "templateRepository" in query:
                name = "synthetic-project" if org else "personal-project"
                return {"repositoryOwner": {"repositories": {"nodes": [{"name": name}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None}}}}, []
            aliases = re.findall(r"c(\d+): object", query)
            repos = re.findall(r"r(\d+): repository", query)
            node = {"author": {"user": {"login": "owner1"}}}
            return {"r" + r: {"c" + c: node for c in aliases} for r in repos}, []

        settings = {"CARDS_ORGANIZATIONS": "fixtureorg", "GH_TOKEN": "synthetic-personal-token",
                    "CARDS_ORGANIZATION_TOKENS": '{"fixtureorg":"synthetic-org-token"}',
                    "CARDS_AUTHORED_IMPORTS": "", "CARDS_AUTHOR_EMAILS": "author@example.test"}
        with patch.dict(os.environ, settings), patch.object(cp, "run", side_effect=low_level_run), \
                patch.object(cp, "gql", side_effect=gql), patch.object(cp, "answered", side_effect=answered), \
                patch.object(cp, "owner_identity", return_value={"user": True, "id": 123, "name": "Synthetic Author"}), \
                patch.object(cp, "seed_blobs", return_value=set()):
            live_work = Path(self.tmp.name) / "live-work"
            live_work.mkdir()
            live = cp.collect("owner1", cp.list_repositories("owner1"), str(live_work))
            self.assertTrue(org_queries)
            self.assertTrue(org_transfers)
            org_queries.clear()
            org_transfers.clear()
            offline = True
            with snapshot.load_snapshot(self.path, KEY, "owner1") as saved, \
                    patch.object(cp, "ORGANIZATION_SNAPSHOT", saved), \
                    patch.dict(os.environ, {"CARDS_ORGANIZATIONS": "", "CARDS_ORGANIZATION_TOKENS": "",
                                            "CARDS_AUTHOR_EMAILS": ""}):
                offline_work = Path(self.tmp.name) / "offline-work"
                offline_work.mkdir()
                replay = cp.collect("owner1", cp.list_repositories("owner1"), str(offline_work))
        self.assertEqual(org_queries, [])
        self.assertEqual(org_transfers, [])
        self.assertEqual(live["unchecked"], [])
        self.assertEqual(live["unread"], 0)
        self.assertEqual(len(live["commits"]), 3)
        self.assertEqual(sum(n for _, _, n in live["events"]), 3)
        self.assertEqual(int(git(self.repo, "rev-list", "--count", "HEAD"))
                         + int(git(personal, "rev-list", "--count", "HEAD")), 5)
        live.pop("now")
        replay.pop("now")
        self.assertEqual(replay, live)

    def test_invalid_or_missing_snapshot_keeps_existing_card(self):
        cp = self.load_collector()
        output = Path(self.tmp.name) / "assets"
        output.mkdir()
        metadata = output / cp.DATA_FILE
        metadata.write_text(json.dumps({"scope": {"organization_snapshot": {
            "as_of": self.manifest["as_of"]}}}), encoding="utf-8")
        panel = output / "panel-light.svg"
        panel.write_bytes(b"existing published card")
        original = {metadata: metadata.read_bytes(), panel: panel.read_bytes()}
        with patch.object(cp, "OUT_DIR", str(output)), patch.object(cp, "owner_login", return_value="owner1"), \
                patch.object(cp, "draw_main") as draw, patch.dict(os.environ, {
                    "CARDS_ORGANIZATION_SNAPSHOT": str(self.path), "CARDS_ORGANIZATION_SNAPSHOT_KEY": KEY, "FORCE": "false"}):
            with self.assertRaises(RuntimeError):
                cp.main()
            self.write()
            changed = bytearray(self.path.read_bytes())
            changed[-1] ^= 1
            self.path.write_bytes(changed)
            with self.assertRaises(RuntimeError):
                cp.main()
            with patch.dict(os.environ, {"CARDS_ORGANIZATION_SNAPSHOT": "", "CARDS_ORGANIZATION_SNAPSHOT_KEY": ""}):
                with self.assertRaises(RuntimeError):
                    cp.main()
            draw.assert_not_called()
        for path, before in original.items():
            self.assertEqual(path.read_bytes(), before)

    def first_setup_card(self, cp):
        output = Path(self.tmp.name) / "first-setup-assets"
        output.mkdir()
        metadata = output / cp.DATA_FILE
        # This ordinary personal card has never carried organization_snapshot.
        metadata.write_text(json.dumps({"scope": {"owned_only": True}}), encoding="utf-8")
        panel = output / "panel-light.svg"
        panel.write_bytes(b"existing personal card before first combined setup")
        return output, {metadata: metadata.read_bytes(), panel: panel.read_bytes()}

    def first_setup_settings(self, **changes):
        return dict({"GITHUB_REPOSITORY": "owner1/owner1", "CARDS_SNAPSHOT_STORE": "owner1/history-store",
                     "CARDS_ORGANIZATION_SNAPSHOT": "", "CARDS_ORGANIZATION_SNAPSHOT_KEY": KEY,
                     "CARDS_ORGANIZATIONS": "", "CARDS_ORGANIZATION_TOKENS": "", "FORCE": "false",
                     "GH_TOKEN": "synthetic-personal-token"}, **changes)

    def test_first_store_setup_without_key_aborts_before_draw_or_network(self):
        cp = self.load_collector()
        output, original = self.first_setup_card(cp)
        for force in ("false", "true"):
            with self.subTest(force=force), patch.object(cp, "OUT_DIR", str(output)), \
                    patch.object(cp, "owner_login", return_value="owner1"), \
                    patch.object(cp, "draw_main") as draw, patch.object(cp, "run") as run, \
                    patch.object(cp, "owner_identity") as identity, patch.dict(os.environ,
                        self.first_setup_settings(CARDS_ORGANIZATION_SNAPSHOT_KEY="", FORCE=force)):
                with self.assertRaisesRegex(RuntimeError, "store needs its key"):
                    cp.main()
                draw.assert_not_called()
                run.assert_not_called()
                identity.assert_not_called()
                for path, before in original.items():
                    self.assertEqual(path.read_bytes(), before)

    def test_remote_private_personal_store_download_authenticates_then_draws(self):
        cp = self.load_collector()
        output, original = self.first_setup_card(cp)
        self.write()
        ciphertext = self.path.read_bytes()
        commands, decrypted_directories = [], []

        def run(args, **kwargs):
            commands.append(args)
            self.assertEqual(args[:4], ["gh", "api", "--hostname", "github.com"])
            self.assertNotIn("CARDS_ORGANIZATION_SNAPSHOT_KEY", kwargs["env"])
            self.assertGreater(kwargs["timeout"], 0)
            if args[4] == "repos/owner1/history-store":
                return b'{"private":true,"owner":{"login":"OWNER1"}}'
            self.assertEqual(args[4], "repos/owner1/history-store/contents/organization.snapshot")
            self.assertEqual(args[5:], ["-H", "Accept: application/vnd.github.raw+json"])
            return ciphertext

        def draw(owner):
            self.assertEqual(owner, "owner1")
            saved = cp.ORGANIZATION_SNAPSHOT
            self.assertIsNotNone(saved)
            self.assertEqual(saved.user_id, 123)
            self.assertEqual(saved.organizations, ["fixtureorg"])
            self.assertTrue(saved.has_repository("fixtureorg", "synthetic-project"))
            decrypted_directories.append(saved._temporary.name)
            self.assertTrue(Path(saved._temporary.name).exists())
            return 17

        with patch.object(cp, "OUT_DIR", str(output)), patch.object(cp, "owner_login", return_value="owner1"), \
                patch.object(cp, "draw_main", side_effect=draw) as draw_mock, \
                patch.object(cp, "run", side_effect=run), patch.object(cp, "owner_identity", return_value={
                    "user": True, "id": 123, "name": "Synthetic Author"}), \
                patch.dict(os.environ, self.first_setup_settings()):
            self.assertEqual(cp.main(), 17)
            draw_mock.assert_called_once_with("owner1")
        self.assertEqual(len(commands), 2)
        self.assertIsNone(cp.ORGANIZATION_SNAPSHOT)
        self.assertTrue(all(not Path(directory).exists() for directory in decrypted_directories))
        for path, before in original.items():
            self.assertEqual(path.read_bytes(), before)

    def test_remote_store_rejections_are_generic_and_preserve_first_setup_card(self):
        cp = self.load_collector()
        output, original = self.first_setup_card(cp)
        valid_meta = b'{"private":true,"owner":{"login":"owner1"}}'
        cases = [
            [b'{"private":false,"owner":{"login":"owner1"}}'],
            [b'{"private":true,"owner":{"login":"other-owner"}}'],
            [b"invalid metadata JSON"],
            [valid_meta, b""],
            [valid_meta, b"tampered ciphertext with private metadata must not escape"],
            [RuntimeError("synthetic private source path and credential")],
        ]
        for index, responses in enumerate(cases):
            with self.subTest(case=index), patch.object(cp, "OUT_DIR", str(output)), \
                    patch.object(cp, "owner_login", return_value="owner1"), \
                    patch.object(cp, "draw_main") as draw, patch.object(cp, "owner_identity") as identity, \
                    patch.object(cp, "run", side_effect=responses), \
                    patch.dict(os.environ, self.first_setup_settings()):
                with self.assertRaises(RuntimeError) as caught:
                    cp.main()
                self.assertEqual(str(caught.exception), "the private organization snapshot could not be read; existing panel kept")
                draw.assert_not_called()
                identity.assert_not_called()
                self.assertIsNone(cp.ORGANIZATION_SNAPSHOT)
                for path, before in original.items():
                    self.assertEqual(path.read_bytes(), before)
        with patch.object(cp, "OUT_DIR", str(output)), patch.object(cp, "owner_login", return_value="owner1"), \
                patch.object(cp, "draw_main") as draw, patch.object(cp, "run") as run, \
                patch.dict(os.environ, self.first_setup_settings(CARDS_SNAPSHOT_STORE="owner1/../unsafe")):
            with self.assertRaisesRegex(RuntimeError, "snapshot-store must name a personal repository"):
                cp.main()
            draw.assert_not_called()
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
