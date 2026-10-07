#!/usr/bin/env python3
"""Content-addressed cache for third-party Vita dependency builds.

The dependency scripts (tools/build_vitagl_demo.sh, build_ffmpeg_bink_vita.sh,
build_ttfs_https_vita.sh) call this helper through tools/dependency_cache.sh.
The cache is opt-in; when it is disabled the scripts never run this file.

Subcommands
  key      Hash the build inputs into a 64-hex key.  Inputs are hashed by
           content, never by path, so two worktrees with the same inputs
           compute the same key.
  restore  Copy a verified entry into a tree.  Exit 0 on a verified hit,
           3 when there is no entry, 4 when the entry is rejected.
  store    Publish installed outputs as a new entry (atomic rename).
  verify   Re-hash one entry or every entry and recompute each key.

Entry layout: <cache>/<name>/<key>/manifest.json plus payload/<outputs>.
Restored files get fresh modification times on purpose: a library restored
with an old mtime could be older than a linked ELF, and ninja would then skip
the relink that the changed library requires.

Python standard library only.
"""

from __future__ import annotations

import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import shutil
import socket
import sys
import tempfile
from pathlib import Path

KEY_SCHEMA = "renegade-dependency-cache-key/v1"
ENTRY_SCHEMA = "renegade-dependency-cache-entry/v1"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
KEY_PATTERN = re.compile(r"^[0-9a-f]{64}$")

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_MISS = 3
EXIT_REJECTED = 4

_CHUNK = 1 << 20


class CacheError(Exception):
    """An input, entry or destination cannot be used."""


class EntryRejected(CacheError):
    """A cache entry exists but failed verification."""


class EntryMissing(CacheError):
    """No cache entry exists for the requested name and key."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            block = handle.read(_CHUNK)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _excluded(relative: str, excludes: list[str]) -> bool:
    base = posixpath.basename(relative)
    return any(fnmatch.fnmatchcase(relative, pattern) or fnmatch.fnmatchcase(base, pattern)
               for pattern in excludes)


def tree_digest(root: Path, excludes: list[str]) -> str:
    """Hash relative paths and contents of every file below root.

    Modes and timestamps are ignored.  Symbolic links are recorded by their
    target text and never followed.  Excluded names match either the
    relative POSIX path or the basename.
    """
    if not root.is_dir():
        raise CacheError(f"tree input is not a directory: {root}")
    records = []
    for current, directories, files in os.walk(root, followlinks=False):
        directories.sort()
        for name in sorted(files + [d for d in directories if (Path(current) / d).is_symlink()]):
            path = Path(current) / name
            relative = path.relative_to(root).as_posix()
            if _excluded(relative, excludes):
                continue
            if path.is_symlink():
                records.append(f"L\0{relative}\0{os.readlink(path)}\n")
            elif path.is_file():
                records.append(f"F\0{relative}\0{sha256_file(path)}\n")
            else:
                raise CacheError(f"tree input contains a special file: {path}")
    digest = hashlib.sha256()
    digest.update(("excludes\0" + "\0".join(excludes) + "\n").encode("utf-8"))
    for record in records:
        digest.update(record.encode("utf-8", "surrogateescape"))
    return f"{digest.hexdigest()}:{len(records)}"


def _split_label(raw: str, option: str) -> tuple[str, str]:
    label, separator, value = raw.partition("=")
    if not separator or not label or not re.match(r"^[A-Za-z0-9_.-]+$", label):
        raise CacheError(f"{option} expects LABEL=VALUE, got {raw!r}")
    return label, value


def build_components(entries: list[tuple[str, str]], excludes: list[str]) -> list[list[str]]:
    """Resolve ordered (kind, raw) CLI entries into hashed key components."""
    components = []
    for kind, raw in entries:
        if kind in ("source", "patch", "script"):
            path = Path(raw)
            if not path.is_file():
                raise CacheError(f"--{kind} input is missing: {raw}")
            components.append([kind, path.name, sha256_file(path)])
        elif kind == "file":
            label, value = _split_label(raw, "--file")
            path = Path(value)
            if not path.is_file():
                raise CacheError(f"--file {label} input is missing: {value}")
            components.append(["file", label, sha256_file(path)])
        elif kind == "value":
            label, value = _split_label(raw, "--value")
            components.append(["value", label, value])
        elif kind == "flags":
            components.append(["flags", "", raw])
        elif kind == "tree":
            label, value = _split_label(raw, "--tree")
            components.append(["tree", label, tree_digest(Path(value), excludes)])
        else:  # pragma: no cover - argparse restricts kinds
            raise CacheError(f"unknown key component kind: {kind}")
    if not components:
        raise CacheError("a key needs at least one input")
    return components


def canonical_key_document(name: str, components: list[list[str]]) -> str:
    return json.dumps({"schema": KEY_SCHEMA, "name": name, "components": components},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_key(name: str, components: list[list[str]]) -> tuple[str, str]:
    validate_name(name)
    document = canonical_key_document(name, components)
    return sha256_text(document), document


def validate_name(name: str) -> None:
    if not NAME_PATTERN.match(name):
        raise CacheError(f"invalid dependency name: {name!r}")


def validate_key(key: str) -> None:
    if not KEY_PATTERN.match(key):
        raise CacheError(f"invalid cache key: {key!r}")


def validate_relative(path: str) -> str:
    if (not path or path.startswith("/") or "\\" in path or "\0" in path
            or posixpath.normpath(path) != path or path in (".", "..")
            or path.split("/")[0] == ".." or "/../" in f"/{path}/"
            or path.split("/")[0].startswith(".depcache")):
        raise CacheError(f"output path must be a normalized relative path: {path!r}")
    return path


def entry_dir(cache_dir: Path, name: str, key: str) -> Path:
    validate_name(name)
    validate_key(key)
    return cache_dir / name / key


def _collect_outputs(source_root: Path, outputs: list[str]) -> tuple[list[str], list[str]]:
    """Return (files, directories) below source_root for the output roots."""
    files: list[str] = []
    directories: list[str] = []
    for output in outputs:
        path = source_root / output
        if path.is_symlink():
            raise CacheError(f"refusing to cache a symbolic link: {path}")
        if path.is_file():
            files.append(output)
        elif path.is_dir():
            directories.append(output)
            for current, subdirs, names in os.walk(path, followlinks=False):
                subdirs.sort()
                for subdir in subdirs:
                    child = Path(current) / subdir
                    if child.is_symlink():
                        raise CacheError(f"refusing to cache a symbolic link: {child}")
                    directories.append(child.relative_to(source_root).as_posix())
                for name in sorted(names):
                    child = Path(current) / name
                    if child.is_symlink() or not child.is_file():
                        raise CacheError(f"refusing to cache a non-regular file: {child}")
                    files.append(child.relative_to(source_root).as_posix())
        else:
            raise CacheError(f"output is missing: {path}")
    return sorted(set(files)), sorted(set(directories))


def load_manifest(entry: Path, name: str, key: str) -> dict:
    manifest_path = entry / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise EntryRejected(f"manifest unreadable: {error}") from error
    if not isinstance(manifest, dict) or manifest.get("schema") != ENTRY_SCHEMA:
        raise EntryRejected("manifest schema mismatch")
    if manifest.get("name") != name or manifest.get("key") != key:
        raise EntryRejected("manifest name/key does not match the requested entry")
    files = manifest.get("files")
    directories = manifest.get("directories")
    outputs = manifest.get("outputs")
    if not isinstance(files, list) or not isinstance(directories, list) or not isinstance(outputs, list):
        raise EntryRejected("manifest file lists are malformed")
    for record in files:
        if (not isinstance(record, dict) or not isinstance(record.get("path"), str)
                or not isinstance(record.get("sha256"), str) or not isinstance(record.get("size"), int)
                or not isinstance(record.get("mode"), int)):
            raise EntryRejected("manifest file record is malformed")
        try:
            validate_relative(record["path"])
        except CacheError as error:
            raise EntryRejected(str(error)) from error
    for item in directories + outputs:
        if not isinstance(item, str):
            raise EntryRejected("manifest path list is malformed")
        try:
            validate_relative(item)
        except CacheError as error:
            raise EntryRejected(str(error)) from error
    components = manifest.get("key_components")
    if components is not None:
        if sha256_text(canonical_key_document(name, components)) != key:
            raise EntryRejected("recorded key components do not hash to the entry key")
    return manifest


def verify_entry(entry: Path, name: str, key: str) -> dict:
    """Verify manifest and payload; return the manifest or raise EntryRejected."""
    if not entry.is_dir():
        raise EntryRejected("entry is not a directory")
    manifest = load_manifest(entry, name, key)
    payload = entry / "payload"
    expected_files = {record["path"]: record for record in manifest["files"]}
    expected_dirs = set(manifest["directories"])
    actual_files = set()
    actual_dirs = set()
    if payload.is_dir():
        for current, subdirs, names in os.walk(payload, followlinks=False):
            for subdir in subdirs:
                child = Path(current) / subdir
                if child.is_symlink():
                    raise EntryRejected(f"payload contains a symbolic link: {child}")
                actual_dirs.add(child.relative_to(payload).as_posix())
            for name_ in names:
                child = Path(current) / name_
                if child.is_symlink() or not child.is_file():
                    raise EntryRejected(f"payload contains a non-regular file: {child}")
                actual_files.add(child.relative_to(payload).as_posix())
    elif expected_files or expected_dirs:
        raise EntryRejected("payload directory is missing")
    implied_dirs = set()
    for path in list(expected_files) + list(expected_dirs):
        parent = posixpath.dirname(path)
        while parent:
            implied_dirs.add(parent)
            parent = posixpath.dirname(parent)
    if actual_files != set(expected_files):
        missing = sorted(set(expected_files) - actual_files)
        extra = sorted(actual_files - set(expected_files))
        raise EntryRejected(f"payload file set differs (missing={missing[:3]} extra={extra[:3]})")
    if actual_dirs != (expected_dirs | implied_dirs):
        raise EntryRejected("payload directory set differs from the manifest")
    for path, record in expected_files.items():
        target = payload / path
        if target.stat().st_size != record["size"]:
            raise EntryRejected(f"payload size mismatch: {path}")
        if sha256_file(target) != record["sha256"]:
            raise EntryRejected(f"payload hash mismatch: {path}")
    return manifest


def _directory_mode() -> int:
    """Mode a plain mkdir would give a new directory under the current umask."""
    mask = os.umask(0)
    os.umask(mask)
    return 0o777 & ~mask


def _copy_verified(source: Path, target: Path, expected_sha: str, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    os.chmod(target, mode & 0o777)
    if sha256_file(target) != expected_sha:
        raise EntryRejected(f"copied file does not match its manifest hash: {target}")


def restore(cache_dir: Path, name: str, key: str, destination: Path, outputs: list[str],
            replace_destination: bool = False) -> None:
    """Restore a verified entry; raise EntryMissing on a miss."""
    outputs = [validate_relative(output) for output in outputs]
    entry = entry_dir(cache_dir, name, key)
    if not entry.exists():
        raise EntryMissing(str(entry))
    manifest = verify_entry(entry, name, key)
    if manifest["outputs"] != outputs:
        raise EntryRejected(f"entry outputs {manifest['outputs']} differ from requested {outputs}")
    payload = entry / "payload"
    destination = destination.absolute()
    if replace_destination:
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.depcache-", dir=destination.parent))
        os.chmod(staging, _directory_mode())
    else:
        destination.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".depcache-restore-", dir=destination))
    try:
        for directory in manifest["directories"]:
            (staging / directory).mkdir(parents=True, exist_ok=True)
        for record in manifest["files"]:
            _copy_verified(payload / record["path"], staging / record["path"],
                           record["sha256"], record["mode"])
        if replace_destination:
            old = None
            if destination.exists() or destination.is_symlink():
                old = Path(tempfile.mkdtemp(prefix=f".{destination.name}.depcache-old-",
                                            dir=destination.parent))
                os.rename(destination, old / "previous")
            try:
                os.rename(staging, destination)
            except OSError:
                if old is not None:
                    os.rename(old / "previous", destination)
                raise
            if old is not None:
                shutil.rmtree(old, ignore_errors=True)
        else:
            for output in outputs:
                staged = staging / output
                target = destination / output
                target.parent.mkdir(parents=True, exist_ok=True)
                if staged.is_dir() and target.is_dir() and not target.is_symlink():
                    previous = staging / ".previous" / output
                    previous.parent.mkdir(parents=True, exist_ok=True)
                    os.rename(target, previous)
                elif target.is_dir() and not target.is_symlink():
                    raise CacheError(f"refusing to replace directory {target} with a file")
                os.replace(staged, target)
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)


def check_complete(source_root: Path, outputs: list[str], ignore: list[str]) -> None:
    """Require outputs (top-level names) to cover every top-level entry.

    Used for prefixes that are later restored with --replace-dest, so a build
    that starts installing a new top-level directory cannot be cached without
    it.
    """
    nested = [output for output in outputs if "/" in output]
    if nested:
        raise CacheError(f"--require-complete needs top-level outputs, got {nested}")
    if not source_root.is_dir():
        raise CacheError(f"source tree is missing: {source_root}")
    unexpected = sorted(child.name for child in source_root.iterdir()
                        if child.name not in outputs
                        and not any(fnmatch.fnmatchcase(child.name, pattern) for pattern in ignore))
    if unexpected:
        raise CacheError(f"{source_root} has entries outside the cached outputs: {unexpected}")


def store(cache_dir: Path, name: str, key: str, source_root: Path, outputs: list[str],
          key_components: list[list[str]] | None = None, require_complete: bool = False,
          ignore: list[str] | None = None) -> str:
    """Publish an entry.  Returns 'stored', 'present' or 'replaced'."""
    outputs = [validate_relative(output) for output in outputs]
    entry = entry_dir(cache_dir, name, key)
    if key_components is not None and sha256_text(canonical_key_document(name, key_components)) != key:
        raise CacheError("key components do not hash to the requested key")
    source_root = source_root.absolute()
    if require_complete:
        check_complete(source_root, outputs, ignore or [])
    files, directories = _collect_outputs(source_root, outputs)
    outcome = "stored"
    if entry.exists():
        try:
            manifest = verify_entry(entry, name, key)
            if manifest["outputs"] == outputs:
                return "present"
        except EntryRejected:
            pass
        _discard(entry)
        outcome = "replaced"
    entry.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".tmp-{key[:16]}-", dir=entry.parent))
    os.chmod(temporary, _directory_mode())
    try:
        records = []
        for directory in directories:
            (temporary / "payload" / directory).mkdir(parents=True, exist_ok=True)
        for relative in files:
            source = source_root / relative
            before = sha256_file(source)
            target = temporary / "payload" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            mode = source.stat().st_mode & 0o777
            os.chmod(target, mode)
            if sha256_file(target) != before or sha256_file(source) != before:
                raise CacheError(f"output changed while it was being cached: {source}")
            records.append({"path": relative, "sha256": before, "size": target.stat().st_size,
                            "mode": mode})
        manifest = {
            "schema": ENTRY_SCHEMA,
            "name": name,
            "key": key,
            "outputs": outputs,
            "directories": directories,
            "files": records,
            "producer": {
                "root": str(source_root),
                "host": socket.gethostname(),
                "created_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        }
        if key_components is not None:
            manifest["key_components"] = key_components
        manifest_path = temporary / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=1, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.rename(temporary, entry)
        except OSError:
            # Another builder published the same key first; keep theirs if valid.
            verify_entry(entry, name, key)
            return "present"
        return outcome
    finally:
        if temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def _discard(entry: Path) -> None:
    trash = Path(tempfile.mkdtemp(prefix=f".rejected-{entry.name[:16]}-", dir=entry.parent))
    os.rename(entry, trash / "entry")
    shutil.rmtree(trash, ignore_errors=True)


def verify_cache(cache_dir: Path, name: str | None, key: str | None) -> list[tuple[str, str, str]]:
    """Return (name, key, status) rows; status is 'ok' or a rejection reason."""
    rows = []
    if name and key:
        candidates = [(name, key)]
    else:
        candidates = []
        if cache_dir.is_dir():
            for name_dir in sorted(cache_dir.iterdir()):
                if not name_dir.is_dir() or not NAME_PATTERN.match(name_dir.name):
                    continue
                if name and name_dir.name != name:
                    continue
                for key_dir in sorted(name_dir.iterdir()):
                    if KEY_PATTERN.match(key_dir.name):
                        candidates.append((name_dir.name, key_dir.name))
    for entry_name, entry_key in candidates:
        try:
            verify_entry(entry_dir(cache_dir, entry_name, entry_key), entry_name, entry_key)
            rows.append((entry_name, entry_key, "ok"))
        except CacheError as error:
            rows.append((entry_name, entry_key, f"rejected: {error}"))
    return rows


class _OrderedInput(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        entries = getattr(namespace, "entries", None) or []
        entries.append((self.dest, values))
        namespace.entries = entries


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)

    key = commands.add_parser("key", help="print the content key for a dependency build")
    key.add_argument("--name", required=True)
    for kind, text in (("source", "pinned source archive (content hashed)"),
                       ("patch", "patch file, in application order"),
                       ("script", "build script (content hashed)"),
                       ("file", "LABEL=PATH, e.g. a toolchain binary (content hashed)"),
                       ("value", "LABEL=VALUE, e.g. compiler version text"),
                       ("flags", "compiler/configure flags string"),
                       ("tree", "LABEL=DIR, every file below DIR (content hashed)")):
        key.add_argument(f"--{kind}", dest=kind, action=_OrderedInput, help=text)
    key.add_argument("--tree-exclude", action="append", default=[],
                     help="glob excluded from every --tree (relative path or basename)")
    key.add_argument("--explain-out", help="write the canonical key document here")

    restore_cmd = commands.add_parser("restore", help="restore a verified entry")
    store_cmd = commands.add_parser("store", help="publish installed outputs")
    for sub in (restore_cmd, store_cmd):
        sub.add_argument("--cache-dir", required=True)
        sub.add_argument("--name", required=True)
        sub.add_argument("--key", required=True)
        sub.add_argument("outputs", nargs="+", help="output paths relative to the tree")
    restore_cmd.add_argument("--dest", required=True)
    restore_cmd.add_argument("--replace-dest", action="store_true",
                             help="replace the whole destination with exactly the outputs")
    store_cmd.add_argument("--src", required=True)
    store_cmd.add_argument("--key-json", help="canonical key document written by 'key --explain-out'")
    store_cmd.add_argument("--require-complete", action="store_true",
                           help="refuse unless the outputs cover every top-level entry of --src")
    store_cmd.add_argument("--ignore", action="append", default=[],
                           help="top-level glob tolerated by --require-complete (e.g. a stamp)")

    verify = commands.add_parser("verify", help="verify cache entries")
    verify.add_argument("--cache-dir", required=True)
    verify.add_argument("--name")
    verify.add_argument("--key")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "key":
            components = build_components(getattr(arguments, "entries", None) or [],
                                          arguments.tree_exclude)
            key, document = compute_key(arguments.name, components)
            if arguments.explain_out:
                Path(arguments.explain_out).write_text(document + "\n", encoding="utf-8")
            print(key)
            return EXIT_OK
        if arguments.command == "restore":
            try:
                restore(Path(arguments.cache_dir), arguments.name, arguments.key,
                        Path(arguments.dest), arguments.outputs, arguments.replace_dest)
            except EntryMissing:
                print(f"Dependency cache: miss {arguments.name} {arguments.key}")
                return EXIT_MISS
            except EntryRejected as error:
                print(f"Dependency cache: rejected {arguments.name} {arguments.key}: {error}",
                      file=sys.stderr)
                return EXIT_REJECTED
            print(f"Dependency cache: verified hit {arguments.name} {arguments.key}")
            return EXIT_OK
        if arguments.command == "store":
            components = None
            if arguments.key_json:
                document = json.loads(Path(arguments.key_json).read_text(encoding="utf-8"))
                if document.get("schema") != KEY_SCHEMA or document.get("name") != arguments.name:
                    raise CacheError("key document does not describe this dependency")
                components = document.get("components")
            outcome = store(Path(arguments.cache_dir), arguments.name, arguments.key,
                            Path(arguments.src), arguments.outputs, components,
                            arguments.require_complete, arguments.ignore)
            print(f"Dependency cache: {outcome} {arguments.name} {arguments.key}")
            return EXIT_OK
        if arguments.command == "verify":
            rows = verify_cache(Path(arguments.cache_dir), arguments.name, arguments.key)
            for row in rows:
                print("\t".join(row))
            return EXIT_OK if rows and all(row[2] == "ok" for row in rows) else EXIT_REJECTED
    except (CacheError, OSError, ValueError) as error:
        print(f"Dependency cache: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    return EXIT_USAGE  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
