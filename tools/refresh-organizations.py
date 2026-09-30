"""Manually refresh a personal coderprint card for selected organization work.

Copyright 2026 Peter Shiller. Licensed under the PolyForm Noncommercial License 1.0.0
(LICENSE.md), with the additional permissions and reservations in NOTICE.md.

This is deliberately separate from the personal profile Action. It uses the
operator's existing local gh login and publishes only aggregate generator
outputs, after a complete scan, into the operator's profile checkout.
"""

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


SOURCE = Path(__file__).resolve().parents[1] / "coderprint.py"
START = "<!-- coderprint:organizations:start -->"
END = "<!-- coderprint:organizations:end -->"
FILES = ("coderprint.json", "panel-light.svg", "panel-dark.svg",
         "panel-compact-light.svg", "panel-compact-dark.svg", "blank.svg")
LOGIN = re.compile(r"[A-Za-z0-9-]{1,39}\Z")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")


def load_generator():
    spec = importlib.util.spec_from_file_location("coderprint_manual_organizations", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(args, *, cwd=None, timeout=30):
    """Run only bounded local gh/git preflights; never put credentials in argv."""
    result = subprocess.run(args, cwd=cwd, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError("a required local GitHub or Git check failed") from None
    return result.stdout.decode("utf-8", "replace").strip()


def viewer_login():
    try:
        response = json.loads(command(
            ["gh", "api", "graphql", "-f", "query=query { viewer { login } }"], timeout=60))
        login = response["data"]["viewer"]["login"]
    except (ValueError, KeyError, TypeError):
        raise RuntimeError("the local gh login could not be verified") from None
    if not isinstance(login, str) or not LOGIN.fullmatch(login):
        raise RuntimeError("the local gh login could not be verified")
    return login


def safe_root(path):
    """Reject a profile path reached through a symlink or junction."""
    given = Path(os.path.abspath(path))
    if not given.is_dir() or os.path.normcase(os.path.abspath(given)) != os.path.normcase(os.path.realpath(given)):
        raise RuntimeError("profile-dir must be an existing real directory, not a link")
    return given


def inside(root, path):
    try:
        return os.path.commonpath((os.path.realpath(root), os.path.realpath(path))) == os.path.realpath(root)
    except ValueError:
        return False


def safe_target(root):
    """Read-only preflight; final publication is checked again by write_all."""
    assets = root / "assets"
    org = assets / "organizations"
    for path in (root / "README.md", assets, org, assets / "coderprint.json", assets / "cards.json",
                 *(org / name for name in FILES)):
        if path.is_symlink() or not inside(root, path):
            raise RuntimeError("the profile output contains a link or leads outside profile-dir")
        if path.exists() and path in (assets, org) and not path.is_dir():
            raise RuntimeError("a profile asset directory is not a directory")
        if path.exists() and path not in (assets, org) and not path.is_file():
            raise RuntimeError("a profile output path is not a regular file")


def remote_identity(remote):
    """Accept only an uncredentialed GitHub.com origin; return owner and repo."""
    remote = remote.strip()
    if remote.startswith("git@github.com:"):
        name = remote[len("git@github.com:"):]
    else:
        url = urlsplit(remote)
        if (url.scheme not in ("https", "ssh") or url.hostname != "github.com" or url.port is not None
                or url.query or url.fragment or url.password
                or url.username not in (None, "git") or (url.scheme == "https" and url.username)):
            return None
        name = url.path.lstrip("/")
    name = name.removesuffix(".git")
    parts = name.split("/")
    if len(parts) != 2 or not all(LOGIN.fullmatch(part) for part in parts):
        return None
    return parts


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise RuntimeError("existing coderprint metadata is missing or malformed") from None


def snapshot_day(value):
    if not isinstance(value, str) or not DAY.fullmatch(value):
        raise RuntimeError("organization snapshot has an invalid date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RuntimeError("organization snapshot has an invalid date") from None


def validate_snapshot(card, owner, *, organization):
    if not isinstance(card, dict) or card.get("schema") != "coderprint/1":
        raise RuntimeError("coderprint metadata is missing or malformed")
    account, scope, generator = card.get("account"), card.get("scope"), card.get("generator")
    login = account.get("login") if isinstance(account, dict) else None
    if (not isinstance(login, str) or login.lower() != owner.lower()
            or not isinstance(scope, dict) or not isinstance(generator, dict)
            or generator.get("name") != "coderprint"
            or scope.get("organization_only") is not organization):
        raise RuntimeError("coderprint metadata does not match this profile and scan mode")
    if organization:
        repos = scope.get("repositories")
        visible = repos.get("visible") if isinstance(repos, dict) else None
        orgs = scope.get("organization_repositories")
        if (not isinstance(visible, int) or isinstance(visible, bool) or visible < 1
                or not isinstance(orgs, int) or isinstance(orgs, bool) or orgs != visible
                or scope.get("owned_only") is not False):
            raise RuntimeError("organization snapshot does not contain only organization repositories")
        return snapshot_day(card.get("as_of"))
    if scope.get("owned_only") is not True or scope.get("organization_repositories") != 0:
        raise RuntimeError("personal coderprint metadata contains organization work")
    return None


def valid_legacy_snapshot(card, generator):
    """Recognize only the personal aggregate shape written by the v1.2.0 generator."""
    required = {"generated", "window", "span_days", "repositories", "commits", "new_lines",
                "lines_of_code", "imports_skipped", "lines_skipped_as_import", "commits_left_out",
                "repositories_unread", "unparsed_commits", "future_dated_left_out", "theme", "themes",
                "palette"}
    optional = {"spotify", "apple_music"}
    if not isinstance(card, dict) or not required <= card.keys() or card.keys() - required - optional:
        return False
    if not generator.own_legacy(card) or card["repositories"] < 0:
        return False

    def quantity(value):
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    numbers = ("span_days", "repositories", "commits", "new_lines", "imports_skipped",
               "lines_skipped_as_import", "repositories_unread", "unparsed_commits",
               "future_dated_left_out")
    if any(not quantity(card[key]) for key in numbers) or card["repositories_unread"] > card["repositories"]:
        return False
    if not isinstance(card["window"], str) or card["window"] not in generator.WINDOWS:
        return False
    if not isinstance(card["generated"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z", card["generated"]):
        return False
    try:
        datetime.strptime(card["generated"], "%Y-%m-%dT%H:%MZ")
    except ValueError:
        return False
    loc = card["lines_of_code"]
    loc_keys = {"written", "in_use", "production", "tests", "repositories_counted_without_diffs"}
    if (not isinstance(loc, dict) or set(loc) != loc_keys or any(not quantity(v) for v in loc.values())
            or loc["written"] != card["new_lines"] or loc["in_use"] != loc["production"] + loc["tests"]
            or loc["repositories_counted_without_diffs"] > card["repositories"]):
        return False
    left = card["commits_left_out"]
    if (not isinstance(left, dict) or set(left) != {"others", "automation", "landed_twice"}
            or any(not quantity(v) for v in left.values())):
        return False
    if (not isinstance(card["theme"], str) or not card["theme"]
            or not isinstance(card["themes"], dict) or set(card["themes"]) != {"light", "dark"}
            or any(not isinstance(v, str) or not v for v in card["themes"].values())):
        return False
    palette = card["palette"]
    if (not isinstance(palette, dict) or set(palette) != {"light", "dark"}
            or any(not isinstance(colors, dict) or set(colors) != {"bg", "text", "muted", "line"}
                   or any(not isinstance(value, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", value)
                          for value in colors.values()) for colors in palette.values())):
        return False
    return all(isinstance(card[key], dict) and set(card[key]) == {"uid"}
               and isinstance(card[key]["uid"], str) for key in optional & card.keys())


def validate_profile(root, owner, generator):
    top = command(["git", "rev-parse", "--show-toplevel"], cwd=root, timeout=30)
    if os.path.normcase(os.path.realpath(top)) != os.path.normcase(os.path.realpath(root)):
        raise RuntimeError("profile-dir must be the root of the selected profile repository")
    remote = command(["git", "remote", "get-url", "origin"], cwd=root, timeout=30)
    identity = remote_identity(remote)
    if not identity or any(name.lower() != owner.lower() for name in identity):
        raise RuntimeError("profile-dir is not the selected owner's owner/owner GitHub repository")
    modern = root / "assets" / "coderprint.json"
    if modern.exists():
        validate_snapshot(read_json(modern), owner, organization=False)
        return
    legacy = root / "assets" / "cards.json"
    if not legacy.exists() or not valid_legacy_snapshot(read_json(legacy), generator):
        raise RuntimeError("recognized personal coderprint metadata is missing or malformed")


def selector_text(path, profile, owner, generator):
    if path is None:
        return ""
    selector = Path(os.path.abspath(path))
    if selector.is_symlink() or not selector.is_file() or selector.stat().st_size > 16384:
        raise RuntimeError("authored-imports-file must be a regular private text file of at most 16 KiB")
    try:
        content = selector.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise RuntimeError("authored-imports-file must be UTF-8 text") from None
    # A selector in a Git repository must be ignored, so an accidental commit
    # cannot publish the owner's private import declarations.
    probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=selector.parent,
                           capture_output=True, timeout=30, check=False)
    if probe.returncode == 0:
        repo_root = Path(probe.stdout.decode("utf-8", "replace").strip())
        ignored = subprocess.run(["git", "check-ignore", "-q", "--", str(selector)],
                                 cwd=repo_root, capture_output=True, timeout=30, check=False)
        if ignored.returncode != 0:
            raise RuntimeError("authored-imports-file inside a Git repository must be ignored")
    # Reuse the generator's exact SHA/repository validator, including the owner
    # and configured organization scope. It never bypasses authorship checks.
    os.environ["CARDS_AUTHORED_IMPORTS"] = content
    generator.authored_imports(owner)
    return content


def cache_path(path, profile, owner):
    if path is None:
        return None
    cache = Path(os.path.abspath(path))
    if not cache.is_dir() or cache.is_symlink() or inside(profile, cache):
        raise RuntimeError("clone-cache must be an existing isolated directory outside profile-dir")
    probe = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cache,
                           capture_output=True, timeout=30, check=False)
    if probe.returncode == 0:
        repo_root = Path(probe.stdout.decode("utf-8", "replace").strip())
        ignored = subprocess.run(["git", "check-ignore", "-q", "--", str(cache)],
                                 cwd=repo_root, capture_output=True, timeout=30, check=False)
        if ignored.returncode != 0:
            raise RuntimeError("clone-cache inside a Git repository must be ignored")
    marker = cache / ".coderprint-organizations-cache"
    if marker.is_symlink():
        raise RuntimeError("clone-cache marker is a link")
    if marker.exists():
        if marker.read_text(encoding="utf-8").strip().lower() != owner.lower():
            raise RuntimeError("clone-cache belongs to a different account")
    elif any(cache.iterdir()):
        raise RuntimeError("clone-cache is not an empty or marked organization cache")
    else:
        marker.write_text(owner + "\n", encoding="utf-8")
    return cache


@contextmanager
def isolated_settings(owner, organizations, seconds, cache=None):
    old = dict(os.environ)
    try:
        for key in list(os.environ):
            if key.startswith(("CARDS_", "GIT_CONFIG_")) or key in (
                    "GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "GITHUB_HOST",
                    "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
                    "GITHUB_REPOSITORY", "FORCE", "CLONE_CACHE"):
                os.environ.pop(key, None)
        os.environ.update(CARDS_OWNER=owner, CARDS_ORGANIZATIONS=" ".join(organizations),
                          CARDS_ORGANIZATION_ONLY="true", CARDS_TIME_LIMIT=str(seconds))
        if cache is not None:
            os.environ["CLONE_CACHE"] = str(cache)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def organization_block(generator, day):
    base = "assets/organizations/"
    pictures = generator.README_TWO.format(
        link=generator.LINK, blank=base + "blank.svg",
        alt="Organization contributions, refreshed manually " + day.isoformat(),
        compact_dark=base + "panel-compact-dark.svg", wide_dark=base + "panel-dark.svg",
        compact_light=base + "panel-compact-light.svg", wide_light=base + "panel-light.svg")
    return ("Organization contributions · manually refreshed " + day.isoformat() + "\n\n"
            + "<!-- Machine-readable organization card: " + base + "coderprint.json -->\n"
            + pictures)


def merge_readme(generator, profile, block):
    before = (profile / "README.md").read_bytes()
    start, end = generator.README_START, generator.README_END
    try:
        generator.README_START, generator.README_END = START, END
        result = generator.new_readme(block, str(profile / "README.md"))
        body = before[3:] if before.startswith(b"\xef\xbb\xbf") else before
        old = body.decode("utf-8", "surrogateescape")
        starts, _ = generator.marker_lines(old)
    finally:
        generator.README_START, generator.README_END = start, end
    if starts:
        return result
    # Append an absent organization panel. This preserves every existing byte,
    # including the independently managed personal block, during daily updates.
    eol = b"\r\n" if b"\r\n" in body else b"\n"
    separator = eol if before.endswith((b"\n", b"\r")) else eol + eol
    marked = eol.join([START.encode(), block.replace("\n", eol.decode()).encode(), END.encode()])
    return before + separator + marked + eol


def refresh(argv=None, *, generator=None, viewer=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--organizations", nargs="+", required=True, metavar="LOGIN")
    parser.add_argument("--owner", help="must match the currently signed-in gh viewer")
    parser.add_argument("--time-limit", required=True, type=int, metavar="SECONDS")
    parser.add_argument("--authored-imports-file")
    parser.add_argument("--clone-cache")
    args = parser.parse_args(argv)
    if not 300 <= args.time_limit <= 86400:
        raise RuntimeError("time-limit must be between 300 and 86400 seconds")
    profile = safe_root(args.profile_dir)
    generator = generator or load_generator()
    with isolated_settings("", [], args.time_limit):
        actual = viewer or viewer_login()
        if not LOGIN.fullmatch(actual):
            raise RuntimeError("the local gh viewer is invalid")
        owner = args.owner or actual
        if not LOGIN.fullmatch(owner) or owner.lower() != actual.lower():
            raise RuntimeError("owner must match the current gh viewer")
        # Restore the clean environment with the selected owner and scope.
    with isolated_settings(owner, args.organizations, args.time_limit):
        organizations, _ = generator.organization_settings()
        safe_target(profile)
        validate_profile(profile, owner, generator)
        # Parse the target organization markers before doing any scan.
        merge_readme(generator, profile, "preflight")
        selector_text(args.authored_imports_file, profile, owner, generator)
        cache = cache_path(args.clone_cache, profile, owner)
        if cache is not None:
            os.environ["CLONE_CACHE"] = str(cache)
        with tempfile.TemporaryDirectory(prefix="coderprint-organizations-") as tmp:
            stage = Path(tmp)
            generator.WORK = str(stage)
            generator.OUT_DIR = str(stage / "assets")
            generator.README = str(stage / "README.md")
            generator.RAW_ASSETS = "https://raw.githubusercontent.com/{owner}/{repo}/HEAD/assets/organizations/"
            try:
                status = generator.main()
            except (RuntimeError, OSError, ValueError):
                raise RuntimeError("organization scan failed; existing profile outputs were kept") from None
            if status != 0:
                raise RuntimeError("organization scan did not complete; existing profile outputs were kept")
            source = stage / "assets"
            if set(p.name for p in source.iterdir()) != set(FILES) or any(
                    not (source / name).is_file() or (source / name).is_symlink() for name in FILES):
                raise RuntimeError("organization scan produced an unexpected set of output files")
            payload = {name: (source / name).read_bytes() for name in FILES}
            try:
                card = json.loads(payload["coderprint.json"].decode("utf-8"))
            except (ValueError, UnicodeError):
                raise RuntimeError("organization scan produced malformed metadata") from None
            day = validate_snapshot(card, owner, organization=True)
            if day > datetime.now(timezone.utc).date() + timedelta(days=1):
                raise RuntimeError("organization snapshot date is in the future")
            target = profile / "assets" / "organizations"
            prior = target / "coderprint.json"
            if prior.exists() and day < validate_snapshot(read_json(prior), owner, organization=True):
                raise RuntimeError("organization snapshot is older than the existing one")
            # The generator's schema contains aggregates, never repositories or
            # commits. Reject a full qualified private repo label or selector
            # hash if one somehow leaks into the generated JSON or SVG metadata.
            combined = b"\n".join(payload.values())
            for full, sha in generator.authored_imports(owner):
                if full.encode() in combined or sha.encode() in combined:
                    raise RuntimeError("organization output contains a private selector")
            readme = merge_readme(generator, profile, organization_block(generator, day))
            publish = {target / name: payload[name] for name in FILES}
            publish[profile / "README.md"] = readme
            safe_target(profile)
            if all(path.is_file() and path.read_bytes() == content for path, content in publish.items()):
                return False
            target.mkdir(parents=True, exist_ok=True)
            generator.WORK = str(profile)
            generator.write_all({str(path): content for path, content in publish.items()})
            return True


def main(argv=None):
    try:
        changed = refresh(argv)
    except RuntimeError as error:
        print("Organization refresh failed: " + str(error), file=sys.stderr)
        return 1
    except Exception:
        # OSError may contain local paths and TimeoutExpired may contain argv;
        # an unexpected traceback can expose private repository information.
        print("Organization refresh failed; inspect local outputs before retrying", file=sys.stderr)
        return 1
    print("Organization card refreshed." if changed else "Organization card already current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
