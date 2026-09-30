"""Authenticated, local organization history for a manually refreshed blended card.

Only the version, a random nonce, and ciphertext are stored outside encryption.
Git bundles and private metadata live in memory or a temporary directory whose
name contains no repository identifier. Callers must close a loaded snapshot.

Copyright 2026 Peter Shiller. Licensed under the PolyForm Noncommercial License
1.0.0 (LICENSE.md), with the permissions and reservations in NOTICE.md.
"""

from __future__ import annotations

import base64
import binascii
from datetime import date, datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import zipfile


SCHEMA = "coderprint/organization-snapshot/1"
MAGIC = b"CODERPRINT-ORG-SNAPSHOT\x00\x01"
MAX_CIPHERTEXT = 48 * 1024 * 1024
MAX_UNCOMPRESSED = 256 * 1024 * 1024
MAX_MANIFEST = 8 * 1024 * 1024
MAX_REPOSITORIES = 100
MAX_METADATA_ITEMS = 100000
_LOGIN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_NAME = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_FIELDS = {"schema", "owner", "user_id", "as_of", "organizations", "repositories",
           "templates_by_owner", "authors_by_owner", "seed_blobs_by_source", "authored_imports", "author_emails"}
_REPO_FIELDS = {"owner", "name", "isPrivate", "isArchived", "isDisabled", "isLocked",
                "bundle", "sha256", "default_head", "empty"}


class SnapshotError(RuntimeError):
    """A deliberately generic error suitable for public generator logs."""


def _fail():
    raise SnapshotError("Organization snapshot is invalid or unavailable")


def _login(value):
    return isinstance(value, str) and bool(_LOGIN.fullmatch(value)) and "--" not in value


def _name(value):
    return isinstance(value, str) and bool(_NAME.fullmatch(value)) and value not in (".", "..")


def _full_name(value):
    if not isinstance(value, str) or value.count("/") != 1:
        return False
    owner, name = value.split("/")
    return _login(owner) and _name(name)


def _email(value):
    return (isinstance(value, str) and 0 < len(value) <= 320
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail()
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail()


def _head(value):
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    if _SHA.fullmatch(value):
        return True
    return (value.startswith("refs/heads/") and len(value) <= 1024
            and not any(ord(c) <= 32 or ord(c) == 127 or c in "~^:?*[\\" for c in value)
            and ".." not in value and "@{" not in value and "//" not in value
            and all(p and not p.startswith(".") and not p.endswith((".", ".lock"))
                    for p in value.split("/")))


def _key(value):
    try:
        if not isinstance(value, str) or len(value) != 44:
            _fail()
        result = base64.b64decode(value, validate=True)
        if len(result) != 32 or base64.b64encode(result).decode("ascii") != value:
            _fail()
        return result
    except (ValueError, binascii.Error):
        _fail()


def _aes():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        return AESGCM
    except ImportError:
        raise SnapshotError("Organization snapshots require the cryptography dependency") from None


def _aad(owner):
    if not _login(owner):
        _fail()
    return (SCHEMA + "\x00" + owner.lower()).encode("ascii")


def _validate(manifest, owner=None, minimum_day=None, now_day=None):
    if not isinstance(manifest, dict) or set(manifest) != _FIELDS or manifest["schema"] != SCHEMA:
        _fail()
    if not _login(manifest["owner"]) or (owner is not None and manifest["owner"].lower() != owner.lower()):
        _fail()
    if type(manifest["user_id"]) is not int or not 0 < manifest["user_id"] < 2**63:
        _fail()
    as_of = _day(manifest["as_of"])
    today = _day(now_day) if now_day is not None else datetime.now(timezone.utc).date()
    if as_of > today or (minimum_day is not None and as_of < _day(minimum_day)):
        _fail()
    orgs = manifest["organizations"]
    if not isinstance(orgs, list) or not 1 <= len(orgs) <= MAX_REPOSITORIES or not all(_login(o) for o in orgs):
        _fail()
    org_keys = {o.lower() for o in orgs}
    if len(org_keys) != len(orgs) or manifest["owner"].lower() in org_keys:
        _fail()
    repos = manifest["repositories"]
    if not isinstance(repos, list) or len(repos) > MAX_REPOSITORIES:
        _fail()
    identities = set()
    names_by_owner = {o: set() for o in org_keys}
    bundles = set()
    for index, repo in enumerate(repos):
        if not isinstance(repo, dict) or set(repo) != _REPO_FIELDS:
            _fail()
        if not _login(repo["owner"]) or repo["owner"].lower() not in org_keys or not _name(repo["name"]):
            _fail()
        identity = (repo["owner"].lower(), repo["name"].lower())
        if identity in identities or any(type(repo[f]) is not bool for f in ("isPrivate", "isArchived", "isDisabled", "isLocked", "empty")):
            _fail()
        identities.add(identity)
        names_by_owner[identity[0]].add(identity[1])
        bundle = repo["bundle"]
        unread = repo["isDisabled"] or repo["isLocked"]
        if bundle is None:
            if not (unread or repo["empty"]) or repo["sha256"] is not None:
                _fail()
            if not _head(repo["default_head"]):
                _fail()
            if repo["empty"] and (not isinstance(repo["default_head"], str)
                                  or not repo["default_head"].startswith("refs/heads/")):
                _fail()
        else:
            if repo["empty"] or bundle != "repositories/%d.bundle" % index or bundle in bundles:
                _fail()
            if not isinstance(repo["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", repo["sha256"]):
                _fail()
            if repo["default_head"] is None or not _head(repo["default_head"]):
                _fail()
            bundles.add(bundle)
    for field in ("templates_by_owner", "authors_by_owner"):
        mapping = manifest[field]
        if not isinstance(mapping, dict) or set(mapping) != org_keys:
            _fail()
        count = 0
        for org, values in mapping.items():
            if values is None:
                continue
            if not isinstance(values, dict):
                _fail()
            count += len(values)
            seen = set()
            for name, value in values.items():
                if field == "templates_by_owner":
                    if not _name(name) or name.lower() not in names_by_owner[org] or name.lower() in seen:
                        _fail()
                    seen.add(name.lower())
                    if value is not None and not _full_name(value):
                        _fail()
                elif (not _email(name) or (value not in (None, "") and not _login(value))):
                    _fail()
            if count > MAX_METADATA_ITEMS:
                _fail()
    seeds = manifest["seed_blobs_by_source"]
    if not isinstance(seeds, dict) or len(seeds) > MAX_METADATA_ITEMS:
        _fail()
    count, seen = 0, set()
    for source, blobs in seeds.items():
        if not _full_name(source) or source.lower() in seen:
            _fail()
        seen.add(source.lower())
        if blobs is None:
            continue
        if not isinstance(blobs, list) or any(not isinstance(s, str) or not _SHA.fullmatch(s) for s in blobs):
            _fail()
        count += len(blobs)
        if len(set(blobs)) != len(blobs) or count > MAX_METADATA_ITEMS:
            _fail()
    uploads = manifest["authored_imports"]
    if not isinstance(uploads, list) or len(uploads) > 256:
        _fail()
    seen = set()
    for entry in uploads:
        if not isinstance(entry, str) or entry.count("@") != 1:
            _fail()
        source, sha = entry.split("@")
        if not _full_name(source) or not _SHA.fullmatch(sha):
            _fail()
        if tuple(source.lower().split("/")) not in identities or entry.lower() in seen:
            _fail()
        seen.add(entry.lower())
    emails = manifest["author_emails"]
    if (not isinstance(emails, list) or len(emails) > MAX_METADATA_ITEMS
            or not all(_email(email) for email in emails) or len(set(emails)) != len(emails)):
        _fail()
    return bundles


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail()
        result[key] = value
    return result


def _bundle_header(path, head):
    """Reject prerequisite/filter bundles: restore must be complete and offline."""
    with open(path, "rb") as stream:
        header = bytearray()
        while len(header) <= 65536:
            line = stream.readline(65537 - len(header))
            header.extend(line)
            if line == b"\n":
                break
            if not line:
                _fail()
        else:
            _fail()
    lines = bytes(header).splitlines()
    if not lines or lines[0] not in (b"# v2 git bundle", b"# v3 git bundle") or lines[-1] != b"":
        _fail()
    refs = {}
    for line in lines[1:-1]:
        if line.startswith(b"@"):
            if line not in (b"@object-format=sha1", b"@object-format=sha256") or lines[0] != b"# v3 git bundle":
                _fail()
            continue
        try:
            sha, ref = line.decode("utf-8").split(" ", 1)
        except (ValueError, UnicodeError):
            _fail()
        if not _SHA.fullmatch(sha) or ref in refs or (ref != "HEAD" and not ref.startswith("refs/")):
            _fail()
        refs[ref] = sha
    if not refs or (head is not None and head not in refs and head not in refs.values()):
        _fail()


def _safe_target(path):
    target = Path(path)
    # Refuse symlink/reparse destinations and parents before atomic publication.
    for part in (target, *target.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & 0x400):
            _fail()
    if target.exists() and not target.is_file():
        _fail()
    if not target.parent.is_dir():
        _fail()
    return target


def write_snapshot(path, key_base64, manifest, bundle_paths):
    """Validate, encrypt, then atomically replace an artifact; never stage plaintext."""
    key, aad = _key(key_base64), _aad(manifest.get("owner") if isinstance(manifest, dict) else None)
    expected = _validate(manifest)
    temporary = None
    try:
        target = _safe_target(path)
        if isinstance(bundle_paths, dict):
            paths = dict(bundle_paths)
        elif isinstance(bundle_paths, (list, tuple)):
            bundled = [r for r in manifest["repositories"] if r["bundle"] is not None]
            if len(bundle_paths) != len(bundled):
                _fail()
            paths = {r["bundle"]: p for r, p in zip(bundled, bundle_paths)}
        else:
            _fail()
        if set(paths) != expected:
            _fail()
        encoded = json.dumps(manifest, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("utf-8")
        total = len(encoded)
        if total > MAX_MANIFEST:
            _fail()
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.writestr("manifest.json", encoded)
            for repo in manifest["repositories"]:
                name = repo["bundle"]
                if name is None:
                    continue
                source = Path(paths[name])
                if not source.is_file() or source.is_symlink():
                    _fail()
                size = source.stat().st_size
                total += size
                if size <= 0 or total > MAX_UNCOMPRESSED:
                    _fail()
                _bundle_header(source, repo["default_head"])
                digest = hashlib.sha256()
                actual = 0
                with source.open("rb") as stream, archive.open(name, "w") as destination:
                    while chunk := stream.read(1024 * 1024):
                        actual += len(chunk)
                        if actual > size:
                            _fail()
                        digest.update(chunk)
                        destination.write(chunk)
                if actual != size or digest.hexdigest() != repo["sha256"]:
                    _fail()
        plaintext = output.getvalue()
        if len(plaintext) + 16 > MAX_CIPHERTEXT:
            _fail()
        nonce = os.urandom(12)
        ciphertext = _aes()(key).encrypt(nonce, plaintext, aad)
        fd, temporary = tempfile.mkstemp(prefix=".snapshot-", suffix=".tmp", dir=target.parent)
        with os.fdopen(fd, "wb") as stream:
            stream.write(MAGIC + nonce + ciphertext)
            stream.flush()
            os.fsync(stream.fileno())
        _safe_target(target)
        os.replace(temporary, target)
        temporary = None
    except SnapshotError:
        raise
    except (OSError, ValueError, TypeError, zipfile.BadZipFile, RuntimeError):
        _fail()
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def _restore_env():
    env = {}
    for name, value in os.environ.items():
        upper = name.upper()
        if (upper.startswith(("GIT_", "CARDS_")) or "SNAPSHOT" in upper
                or upper in {"GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN"}):
            continue
        env[name] = value
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL="file")
    return env


class Snapshot:
    def __init__(self, manifest, temporary):
        self.owner = manifest["owner"]
        self.user_id = manifest["user_id"]
        self.as_of = manifest["as_of"]
        self.organizations = [organization.lower() for organization in manifest["organizations"]]
        self.repositories = manifest["repositories"]
        self.templates_by_owner = manifest["templates_by_owner"]
        self.authors_by_owner = manifest["authors_by_owner"]
        self.seed_blobs_by_source = {k.lower(): None if v is None else set(v)
                                     for k, v in manifest["seed_blobs_by_source"].items()}
        self.uploads = {(source.lower(), sha) for source, sha in
                        (entry.split("@") for entry in manifest["authored_imports"])}
        self.author_emails = set(manifest["author_emails"])
        self._temporary = temporary

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None

    def has_repository(self, owner, name):
        return any(r["owner"].lower() == owner.lower() and r["name"].lower() == name.lower()
                   for r in self.repositories)

    def restore_repository(self, owner, name, dest, cp):
        """Restore all refs from a local complete bundle using the caller's bounded runner."""
        created = False
        try:
            repo = next((r for r in self.repositories if r["owner"].lower() == owner.lower()
                         and r["name"].lower() == name.lower()), None)
            if (self._temporary is None or repo is None or repo["isDisabled"] or repo["isLocked"]
                    or repo["bundle"] is None and not repo["empty"]):
                _fail()
            target = Path(dest)
            if target.exists() or target.is_symlink():
                _fail()
            env = _restore_env()
            created = True
            if repo["empty"]:
                cp.run(["git", "init", "--bare", "--quiet", str(target)], env=env, timeout=60)
            else:
                source = Path(self._temporary.name) / repo["bundle"]
                cp.run(["git", "clone", "--mirror", "--quiet", str(source), str(target)], env=env, timeout=300)
            head = repo["default_head"]
            if head is not None:
                command = ["symbolic-ref", "HEAD", head] if head.startswith("refs/") else ["update-ref", "--no-deref", "HEAD", head]
                cp.run(["git", "-C", str(target)] + command, env=env, timeout=60)
            if not repo["empty"]:
                cp.run(["git", "-C", str(target), "remote", "remove", "origin"], env=env, timeout=60)
                cp.run(["git", "-C", str(target), "fsck", "--full", "--strict", "--no-reflogs"], env=env, timeout=300)
        except SnapshotError:
            raise
        except Exception:
            if created and hasattr(cp, "remove_tree") and target.is_dir():
                try:
                    cp.remove_tree(str(target))
                except Exception:
                    pass
            _fail()


def load_snapshot(path, key_base64, owner, minimum_day=None, now_day=None):
    """Authenticate before parsing; strictly validate ZIP and manifest before exposing data."""
    key, aad = _key(key_base64), _aad(owner)
    temporary = None
    try:
        source = _safe_target(path)
        with source.open("rb") as stream:
            artifact = stream.read(len(MAGIC) + 12 + MAX_CIPHERTEXT + 1)
        if (not artifact.startswith(MAGIC) or len(artifact) < len(MAGIC) + 12 + 16
                or len(artifact) > len(MAGIC) + 12 + MAX_CIPHERTEXT):
            _fail()
        offset = len(MAGIC)
        plaintext = _aes()(key).decrypt(artifact[offset:offset + 12], artifact[offset + 12:], aad)
        with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
            infos = archive.infolist()
            if not 1 <= len(infos) <= MAX_REPOSITORIES + 1:
                _fail()
            names, total = set(), 0
            for info in infos:
                mode = info.external_attr >> 16
                if (info.filename in names or info.filename != info.orig_filename
                        or info.filename not in {"manifest.json"} and not re.fullmatch(r"repositories/(?:0|[1-9][0-9]?)\.bundle", info.filename)
                        or info.is_dir() or info.flag_bits & 1
                        or stat.S_IFMT(mode) not in (0, stat.S_IFREG)
                        or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or info.file_size <= 0):
                    _fail()
                names.add(info.filename)
                total += info.file_size
                if total > MAX_UNCOMPRESSED or (info.filename == "manifest.json" and info.file_size > MAX_MANIFEST):
                    _fail()
            if "manifest.json" not in names:
                _fail()
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"), object_pairs_hook=_json_object)
            expected = _validate(manifest, owner, minimum_day, now_day)
            if names != expected | {"manifest.json"}:
                _fail()
            temporary = tempfile.TemporaryDirectory(prefix="coderprint-snapshot-")
            root = Path(temporary.name)
            (root / "repositories").mkdir()
            for repo in manifest["repositories"]:
                name = repo["bundle"]
                if name is None:
                    continue
                destination = root / name
                digest = hashlib.sha256()
                size = 0
                with archive.open(name) as stream, destination.open("xb") as output:
                    while chunk := stream.read(1024 * 1024):
                        size += len(chunk)
                        if size > archive.getinfo(name).file_size:
                            _fail()
                        digest.update(chunk)
                        output.write(chunk)
                if size != archive.getinfo(name).file_size or digest.hexdigest() != repo["sha256"]:
                    _fail()
                _bundle_header(destination, repo["default_head"])
        result = Snapshot(manifest, temporary)
        temporary = None
        return result
    except SnapshotError:
        raise
    except Exception:
        _fail()
    finally:
        if temporary is not None:
            temporary.cleanup()
