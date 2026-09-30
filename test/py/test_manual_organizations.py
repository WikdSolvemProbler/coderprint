"""Offline checks for the separate, manually refreshed organization card."""

from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(sys.argv[1]).resolve()
sys.argv = [sys.argv[0]]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("manual_organizations_test", SOURCE.parent / "tools" / "refresh-organizations.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=60, check=True)
    return result.stdout.decode("utf-8", "replace").strip()


def metadata(only=False, day=None, visible=1):
    return {"schema": "coderprint/1", "generator": {"name": "coderprint"},
            "as_of": day or datetime.now(timezone.utc).date().isoformat(),
            "account": {"login": "owner1"},
            "scope": {"organization_only": only, "owned_only": not only,
                      "organization_repositories": visible if only else 0,
                      "repositories": {"visible": visible}}}


class Generator:
    def __init__(self, source):
        self.real = helper.load_generator()
        self.README_START = self.real.README_START
        self.README_END = self.real.README_END
        self.README_TWO = self.real.README_TWO
        self.LINK = self.real.LINK
        self.main_calls = 0
        self.fail = False
        self.day = datetime.now(timezone.utc).date().isoformat()
        self.visible = 1
        self.secret = "super-private-org-repository"

    def organization_settings(self):
        return self.real.organization_settings()

    def authored_imports(self, owner):
        return self.real.authored_imports(owner)

    def marker_lines(self, text):
        old_start, old_end = self.real.README_START, self.real.README_END
        try:
            self.real.README_START, self.real.README_END = self.README_START, self.README_END
            return self.real.marker_lines(text)
        finally:
            self.real.README_START, self.real.README_END = old_start, old_end

    def new_readme(self, block, path):
        old_start, old_end = self.real.README_START, self.real.README_END
        try:
            self.real.README_START, self.real.README_END = self.README_START, self.README_END
            return self.real.new_readme(block, path)
        finally:
            self.real.README_START, self.real.README_END = old_start, old_end

    def write_all(self, files):
        self.real.WORK = self.WORK
        return self.real.write_all(files)

    def main(self):
        self.main_calls += 1
        assert os.environ["CARDS_ORGANIZATION_ONLY"] == "true"
        assert os.environ["CARDS_ORGANIZATIONS"] == "testorg"
        assert os.environ["CARDS_OWNER"] == "owner1"
        assert all(name not in os.environ for name in
                   ("GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "GITHUB_HOST",
                    "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"))
        assert "CARDS_RELAY" not in os.environ and "GIT_CONFIG_COUNT" not in os.environ
        assert Path(self.WORK) != self.profile
        if self.fail:
            return 1
        out = Path(self.OUT_DIR)
        out.mkdir(parents=True)
        (out / "coderprint.json").write_text(json.dumps(metadata(True, self.day, self.visible)), encoding="utf-8")
        for name in helper.FILES[1:]:
            (out / name).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
        return 0


class ManualOrganizations(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="manual-org-test-")
        self.addCleanup(self.tmp.cleanup)
        self.profile = Path(self.tmp.name) / "profile"
        self.profile.mkdir()
        git(self.profile, "init", "-q")
        git(self.profile, "remote", "add", "origin", "https://github.com/owner1/owner1.git")
        (self.profile / "assets").mkdir()
        (self.profile / "assets" / "coderprint.json").write_text(json.dumps(metadata()), encoding="utf-8")
        self.personal = (b"# Profile\r\n\r\n<!-- coderprint:start -->\r\n"
                         b"PERSONAL PANEL\r\n<!-- coderprint:end -->\r\n"
                         b"Manual prose stays unchanged.\r\n")
        (self.profile / "README.md").write_bytes(self.personal)
        self.generator = Generator(SOURCE)
        self.generator.profile = self.profile

    def args(self, **kwargs):
        value = ["--profile-dir", str(self.profile), "--owner", "owner1",
                 "--organizations", "testorg", "--time-limit", "300"]
        for key, arg in kwargs.items():
            value.extend(["--" + key.replace("_", "-"), str(arg)])
        return value

    def refresh(self, **kwargs):
        return helper.refresh(self.args(**kwargs), generator=self.generator, viewer="owner1")

    def output(self):
        target = self.profile / "assets" / "organizations"
        return {path.relative_to(self.profile).as_posix(): path.read_bytes()
                for path in [self.profile / "README.md", *(target / n for n in helper.FILES)] if path.exists()}

    def test_publish_repeat_replace_and_personal_block_preserved(self):
        self.assertTrue(self.refresh())
        first = self.output()
        readme = first["README.md"]
        self.assertTrue(readme.startswith(self.personal))
        self.assertEqual(readme.count(helper.START.encode()), 1)
        self.assertEqual(readme.count(helper.END.encode()), 1)
        self.assertIn(b"assets/organizations/panel-light.svg", readme)
        self.assertNotIn(self.generator.secret.encode(), b"\n".join(first.values()))
        self.assertFalse(self.refresh())
        self.assertEqual(self.output(), first)
        self.generator.visible = 2
        self.assertTrue(self.refresh())
        updated = self.output()
        self.assertEqual(updated["README.md"], readme)
        self.assertEqual(updated["README.md"].count(helper.START.encode()), 1)
        self.assertEqual(json.loads(updated["assets/organizations/coderprint.json"])["scope"]["repositories"]["visible"], 2)

    def test_failed_or_incomplete_scan_preserves_existing_outputs(self):
        self.refresh()
        before = self.output()
        self.generator.fail = True
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            self.refresh()
        self.assertEqual(self.output(), before)
        self.generator.fail = False
        self.generator.day = (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat()
        with self.assertRaisesRegex(RuntimeError, "future"):
            self.refresh()
        self.assertEqual(self.output(), before)

    def test_inherited_gh_host_and_tokens_are_scrubbed_then_restored(self):
        inherited = {"GH_HOST": "enterprise.example", "GITHUB_HOST": "enterprise.example",
                     "GH_TOKEN": "private-token", "GITHUB_TOKEN": "other-private-token",
                     "GH_ENTERPRISE_TOKEN": "enterprise-token"}
        with patch.dict(os.environ, inherited):
            self.assertTrue(self.refresh())
            for name, value in inherited.items():
                self.assertEqual(os.environ[name], value)

    def test_bad_markers_rejected_before_scan(self):
        for readme in (self.personal + helper.START.encode(),
                       self.personal + helper.END.encode() + b"\n" + helper.START.encode(),
                       self.personal + (helper.START + "\n" + helper.END + "\n" + helper.START).encode()):
            (self.profile / "README.md").write_bytes(readme)
            with self.assertRaises(RuntimeError):
                self.refresh()
            self.assertEqual(self.generator.main_calls, 0)
            self.assertFalse((self.profile / "assets" / "organizations").exists())

    def test_reject_mismatched_identity_and_nested_profile(self):
        self.refresh()
        self.generator.main_calls = 0
        personal_path = self.profile / "assets" / "coderprint.json"
        personal_path.write_text(json.dumps(metadata(True)), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "scan mode"):
            self.refresh()
        self.assertEqual(self.generator.main_calls, 0)
        personal_path.write_text(json.dumps(metadata()), encoding="utf-8")
        nested = self.profile / "nested"
        nested.mkdir()
        (nested / "assets").mkdir()
        (nested / "assets" / "coderprint.json").write_bytes(personal_path.read_bytes())
        (nested / "README.md").write_bytes(self.personal)
        with self.assertRaisesRegex(RuntimeError, "root"):
            helper.refresh(self.args(profile_dir=nested), generator=self.generator, viewer="owner1")
        self.assertEqual(self.generator.main_calls, 0)

    def test_reject_linked_output(self):
        self.refresh()
        original = self.output()
        target = self.profile / "assets" / "organizations" / "blank.svg"
        target.unlink()
        outside = Path(self.tmp.name) / "outside.svg"
        outside.write_text("outside", encoding="utf-8")
        try:
            target.symlink_to(outside)
        except OSError:
            self.skipTest("symlinks unavailable on this host")
        with self.assertRaisesRegex(RuntimeError, "link"):
            self.refresh()
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")

    def test_reject_older_snapshot_without_changing_files(self):
        self.refresh()
        original = self.output()
        self.generator.day = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(RuntimeError, "older"):
            self.refresh()
        self.assertEqual(self.output(), original)

    def test_reject_unignored_cache_before_scan(self):
        cache = self.profile / "cache"
        cache.mkdir()
        with self.assertRaisesRegex(RuntimeError, "outside"):
            self.refresh(clone_cache=cache)
        self.assertEqual(self.generator.main_calls, 0)
        # The production cache must be outside the profile checkout even if it
        # is ignored there, so use a separate Git repository for this check.
        external = Path(self.tmp.name) / "other-repo"
        external.mkdir()
        git(external, "init", "-q")
        external_cache = external / "cache"
        external_cache.mkdir()
        with self.assertRaisesRegex(RuntimeError, "ignored"):
            self.refresh(clone_cache=external_cache)
        self.assertEqual(self.generator.main_calls, 0)
        (external / ".gitignore").write_text("cache/\n", encoding="utf-8")
        self.assertTrue(self.refresh(clone_cache=external_cache))
        self.assertEqual((external_cache / ".coderprint-organizations-cache").read_text(encoding="utf-8").strip(), "owner1")
    def test_private_import_selector_must_be_ignored_and_stays_private(self):
        selector = self.profile / "private-imports.txt"
        selector.write_text("testorg/" + self.generator.secret + "@" + "a" * 40 + "\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "ignored"):
            self.refresh(authored_imports_file=selector)
        self.assertEqual(self.generator.main_calls, 0)
        (self.profile / ".gitignore").write_text("private-imports.txt\n", encoding="utf-8")
        self.assertTrue(self.refresh(authored_imports_file=selector))
        published = b"\n".join(self.output().values())
        self.assertNotIn(self.generator.secret.encode(), published)
        self.assertNotIn(b"a" * 40, published)
        self.assertNotIn(b"private-imports.txt", published)


if __name__ == "__main__":
    unittest.main()
