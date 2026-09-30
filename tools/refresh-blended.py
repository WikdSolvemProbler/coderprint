"""Refresh frozen organization history locally and draw one deduplicated coderprint card.

Copyright 2026 Peter Shiller. PolyForm Noncommercial License 1.0.0; see LICENSE.md and NOTICE.md.
No organization App is used. Only authenticated ciphertext goes into the private snapshot store.
"""

import argparse
import base64
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
FILES = ("coderprint.json", "panel-light.svg", "panel-dark.svg", "panel-compact-light.svg",
         "panel-compact-dark.svg", "blank.svg")


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


manual = module("coderprint_manual_preflight", ROOT / "tools" / "refresh-organizations.py")


@contextmanager
def environment(values):
    old = dict(os.environ)
    try:
        for name in list(os.environ):
            if (name.startswith(("CARDS_", "GIT_")) or name in (
                    "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN",
                    "GH_HOST", "GITHUB_HOST", "GH_REPO", "GH_DEBUG")):
                os.environ.pop(name)
        for name in ("GIT_COMMON_DIR", "GITHUB_REPOSITORY", "CLONE_CACHE", "FORCE"):
            os.environ.pop(name, None)
        os.environ.update(values)
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


def key_text(path):
    """Windows keys are DPAPI protected for this Windows account, outside every checkout."""
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 8192:
        raise RuntimeError("the snapshot key file is unavailable")
    raw = path.read_bytes()
    if raw.startswith(b"DPAPI1\n"):
        if os.name != "nt":
            raise RuntimeError("this snapshot key belongs to a Windows account")
        from ctypes import wintypes
        class Blob(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]
        buf = ctypes.create_string_buffer(raw[7:])
        incoming = Blob(len(raw) - 7, ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte)))
        outgoing = Blob()
        api = ctypes.windll.crypt32
        api.CryptUnprotectData.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        api.CryptUnprotectData.restype = wintypes.BOOL
        if not api.CryptUnprotectData(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
            raise RuntimeError("the snapshot key could not be unlocked")
        try:
            raw = ctypes.string_at(outgoing.data, outgoing.size)
        finally:
            ctypes.windll.kernel32.LocalFree(ctypes.cast(outgoing.data, ctypes.c_void_p))
    else:
        if os.name == "nt" or path.stat().st_mode & 0o077:
            raise RuntimeError("the snapshot key file must be private and protected")
        try:
            raw = base64.b64decode(raw.strip(), validate=True)
        except ValueError:
            raise RuntimeError("the snapshot key is invalid") from None
    if len(raw) != 32:
        raise RuntimeError("the snapshot key is invalid")
    return base64.b64encode(raw).decode("ascii")


def preflight(profile, store, owner):
    for root, profile_repo in ((profile, True), (store, False)):
        top = manual.command(["git", "rev-parse", "--show-toplevel"], cwd=root)
        if os.path.normcase(os.path.realpath(top)) != os.path.normcase(os.path.realpath(root)):
            raise RuntimeError("each output directory must be its own Git checkout")
        origin = manual.remote_identity(manual.command(["git", "remote", "get-url", "origin"], cwd=root))
        if (origin is None or origin[0].lower() != owner.lower()
                or (origin[1].lower() == owner.lower()) is not profile_repo):
            raise RuntimeError("output origins must belong to this personal GitHub account")
        if manual.command(["git", "status", "--porcelain"], cwd=root):
            raise RuntimeError("the output checkouts must have no local changes")
    name = manual.remote_identity(manual.command(["git", "remote", "get-url", "origin"], cwd=store))
    result = json.loads(manual.command(["gh", "api", "repos/" + "/".join(name)], timeout=30))
    if result.get("private") is not True or result.get("owner", {}).get("login", "").lower() != owner.lower():
        raise RuntimeError("the snapshot store must be a private personally owned repository")
    manual.safe_target(profile)
    target = store / "organization.snapshot"
    if target.is_symlink() or not manual.inside(store, target) or target.exists() and not target.is_file():
        raise RuntimeError("the snapshot output path is unsafe")
    return "/".join(name)


def without_organization_block(cp, raw):
    """Remove only our former separate block, preserving every unrelated README byte."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")) or b"\x00" in raw:
        raise RuntimeError("the profile README encoding is unsupported")
    bom = b"\xef\xbb\xbf" if raw.startswith(b"\xef\xbb\xbf") else b""
    text = raw[len(bom):].decode("utf-8", "surrogateescape")
    markers = cp.README_START, cp.README_END
    try:
        cp.README_START, cp.README_END = manual.START, manual.END
        starts, ends = cp.marker_lines(text)
    finally:
        cp.README_START, cp.README_END = markers
    if len(starts) > 1 or len(ends) > 1 or len(starts) != len(ends) or starts and ends[0] < starts[0]:
        raise RuntimeError("the former organization block markers are ambiguous")
    if starts:
        a, b = text.find(manual.START, starts[0]), text.find(manual.END, ends[0]) + len(manual.END)
        text = text[:a] + text[b:]
    return bom + text.encode("utf-8", "surrogateescape")


def build(cp, owner, orgs, cache, bundles, uploads):
    identity = cp.owner_identity(owner)
    if not identity or not identity["user"] or not identity["id"]:
        raise RuntimeError("the personal GitHub identity could not be verified")
    repos = cp.list_repositories(owner)
    templates, authors, seeds, saved, paths = {}, {}, {}, [], {}
    for org in orgs:
        templates[org] = cp.templates(org, owner)
        if templates[org] is None:
            raise RuntimeError("organization template evidence could not be verified")
        authors[org] = {}
    samples = {org: {} for org in orgs}
    for index, repo in enumerate(repos):
        account, name = repo["owner"], repo["name"]
        row = dict(repo, bundle=None, sha256=None, default_head=None, empty=False)
        if not (repo["isDisabled"] or repo["isLocked"]):
            dest = cp.slot(str(cache), account, name)
            with cp.repository_access(account):
                cp.clone(account, name, dest)
            if cp.run(["git", "-C", dest, "rev-parse", "--is-shallow-repository"]).strip() != b"false":
                raise RuntimeError("organization history is incomplete")
            if list(Path(dest).glob("objects/pack/*.promisor")) or (Path(dest) / "objects/info/alternates").exists():
                raise RuntimeError("organization history is incomplete")
            cp.run(["git", "-C", dest, "fsck", "--full"], timeout=120)
            commits, bad = cp.read_commits(dest, index)
            if bad:
                raise RuntimeError("organization commits could not be read completely")
            for commit in commits:
                if not commit.bot:
                    samples[account.lower()].setdefault(commit.email, (account + "/" + name, commit.sha))
            refs = cp.run(["git", "-C", dest, "for-each-ref", "--format=%(refname)"])
            row["empty"] = not bool(refs.strip())
            try:
                row["default_head"] = cp.run(["git", "-C", dest, "symbolic-ref", "HEAD"]).decode().strip()
            except RuntimeError:
                row["default_head"] = cp.run(["git", "-C", dest, "rev-parse", "HEAD"]).decode().strip()
            if not row["empty"]:
                file = bundles / (str(index) + ".bundle")
                cp.run(["git", "-C", dest, "bundle", "create", str(file), "--all"], timeout=120)
                row.update(bundle="repositories/%d.bundle" % index, sha256=hashlib.sha256(file.read_bytes()).hexdigest())
                paths[row["bundle"]] = file
        saved.append(row)
    for org, wanted in samples.items():
        entries = list(wanted.items())
        # Each manual batch respects the existing resolver's request cap.
        for offset in range(0, len(entries), cp.RESOLVE_CALLS * cp.ALIASES):
            part = dict(entries[offset:offset + cp.RESOLVE_CALLS * cp.ALIASES])
            found = cp.resolve_authors(owner, part)
            authors[org].update({email: found.get(email, "") for email in part})
    for source in {s for table in templates.values() for s in table.values() if s}:
        value = cp.seed_blobs(source, str(cache / ("seed-%d.git" % len(seeds))))
        if value is None:
            raise RuntimeError("organization template history could not be verified")
        seeds[source] = sorted(value)
    return {
        "schema": "coderprint/organization-snapshot/1", "owner": owner, "user_id": identity["id"],
        "as_of": datetime.now(timezone.utc).date().isoformat(), "organizations": orgs, "repositories": saved,
        "templates_by_owner": templates, "authors_by_owner": authors, "seed_blobs_by_source": seeds,
        "authored_imports": sorted(uploads), "author_emails": sorted(cp.author_emails()),
    }, paths


def run(args):
    deadline = time.monotonic() + args.time_limit
    profile, store = manual.safe_root(args.profile_dir), manual.safe_root(args.snapshot_dir)
    orgs = [org.lower() for org in args.organizations]
    if len(orgs) != len(set(orgs)) or not orgs or any(not manual.LOGIN.fullmatch(org) for org in orgs):
        raise RuntimeError("organizations must list unique GitHub logins")
    with environment({}):
        owner = manual.viewer_login()
        if args.owner and args.owner.lower() != owner.lower():
            raise RuntimeError("the local gh login must match the requested owner")
        if owner.lower() in orgs:
            raise RuntimeError("the personal owner is not an organization scope")
        store_name = preflight(profile, store, owner)
        key = key_text(args.key_file)
        meta = manual.read_json(profile / "assets/coderprint.json") if (profile / "assets/coderprint.json").exists() else manual.read_json(profile / "assets/cards.json")
        if meta.get("schema"):
            if (meta.get("schema") != "coderprint/1" or meta.get("account", {}).get("login", "").lower() != owner.lower()
                    or meta.get("generator", {}).get("name") != "coderprint" or meta.get("scope", {}).get("organization_only") is not False):
                raise RuntimeError("the existing card does not match this personal profile")
        presentation = meta.get("presentation", meta)
        cp = manual.load_generator()
        storage = module("coderprint_manual_snapshot_storage", ROOT / "organization_snapshot.py")
        with tempfile.TemporaryDirectory(prefix="coderprint-blended-") as temporary:
            temp = Path(temporary)
            (temp / "bundles").mkdir()
            (temp / "cache").mkdir()
            (temp / "profile/assets").mkdir(parents=True)
            values = {"CARDS_OWNER": owner, "CARDS_ORGANIZATIONS": " ".join(orgs),
                      "CARDS_ORGANIZATION_ONLY": "true",
                      "CARDS_TIME_LIMIT": str(args.time_limit)}
            with environment(values):
                cp.DEADLINE = deadline
                manual.selector_text(args.authored_imports_file, profile, owner, cp)
                declarations = {name + "@" + sha for name, sha in cp.authored_imports(owner)}
                manifest, paths = build(cp, owner, orgs, temp / "cache", temp / "bundles", declarations)
            cipher = temp / "organization.snapshot"
            storage.write_snapshot(cipher, key, manifest, paths)
            (temp / "profile/README.md").write_bytes(without_organization_block(cp, (profile / "README.md").read_bytes()))
            if (profile / "assets/coderprint.json").exists():
                (temp / "profile/assets/coderprint.json").write_bytes((profile / "assets/coderprint.json").read_bytes())
            elif (profile / "assets/cards.json").exists():
                (temp / "profile/assets/cards.json").write_bytes((profile / "assets/cards.json").read_bytes())
            values = {"CARDS_OWNER": owner, "CARDS_WINDOW": meta.get("window", {}).get("id", "all") if isinstance(meta.get("window"), dict) else meta.get("window", "all"),
                      "CARDS_ORGANIZATION_SNAPSHOT": str(cipher), "CARDS_ORGANIZATION_SNAPSHOT_KEY": key,
                      "CARDS_SNAPSHOT_STORE": store_name, "CARDS_TIME_LIMIT": str(args.time_limit),
                      "CARDS_RELAY": args.relay or ""}
            for service in ("spotify", "apple_music"):
                if isinstance(presentation.get(service), dict):
                    values["CARDS_" + ("SPOTIFY_UID" if service == "spotify" else "APPLE_MUSIC_UID")] = presentation[service]["uid"]
            old_dir = Path.cwd()
            try:
                os.chdir(temp / "profile")
                with environment(values):
                    cp.WORK = str(temp / "profile")
                    cp.README = str(temp / "profile/README.md")
                    cp.OUT_DIR = str(temp / "profile/assets")
                    if cp.main(deadline=deadline):
                        raise RuntimeError("the combined refresh did not complete; existing card retained")
            finally:
                os.chdir(old_dir)
            card = json.loads((temp / "profile/assets/coderprint.json").read_text())
            if (card["account"]["login"].lower() != owner.lower() or card["scope"]["organization_only"]
                    or card["scope"]["organization_repositories"] != len(manifest["repositories"])):
                raise RuntimeError("the combined output could not be verified")
            outputs = {profile / "README.md": (temp / "profile/README.md").read_bytes()}
            outputs.update({profile / "assets" / name: (temp / "profile/assets" / name).read_bytes()
                            for name in FILES if (temp / "profile/assets" / name).exists()})
            manual.safe_target(profile)
            cp.WORK = str(store)
            cp.write_all({str(store / "organization.snapshot"): cipher.read_bytes()})
            cp.WORK = str(profile)
            cp.write_all({str(path): content for path, content in outputs.items()})
            legacy = profile / "assets/cards.json"
            if cp.own_legacy(cp.previous_meta(legacy)):
                legacy.unlink()
            print("One combined card and its encrypted private snapshot are ready to publish.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--profile-dir", required=True)
    p.add_argument("--snapshot-dir", required=True)
    p.add_argument("--key-file", required=True)
    p.add_argument("--organizations", required=True, nargs="+")
    p.add_argument("--owner")
    p.add_argument("--authored-imports-file")
    p.add_argument("--relay")
    p.add_argument("--time-limit", type=int, required=True)
    args = p.parse_args()
    if not 300 <= args.time_limit <= 86400:
        p.error("time-limit must be 300 to 86400 seconds")
    try:
        run(args)
    except Exception:
        print("The blended refresh could not complete; nothing was pushed. Review any local output changes before retrying.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
