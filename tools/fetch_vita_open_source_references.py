#!/usr/bin/env python3
"""Fetch pinned Vita open-source references into an external cache.

This tool records provenance for study/reference material only. It intentionally
keeps external source outside the repository and does not import code into the
Renegade Vita tree.
"""

from __future__ import annotations

import argparse
import datetime as _datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised only on broken hosts.
    raise SystemExit("PyYAML is required: install python3-yaml or pip install PyYAML") from exc


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "tools" / "vita_open_source_references.yml"
DEFAULT_REPORT = ROOT / "reports" / "generated" / "vita_open_source_reference_fetch.json"
DEFAULT_FETCHER = ROOT / ".agents" / "skills" / "vita-open-source-reuse" / "scripts" / "fetch-reference.sh"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ALLOWED_POLICIES = {
    "compatible_design_reference",
    "compatible_study_reference",
    "compatible_tooling_reference",
    "linked_library_reference",
    "study_only_experimental",
    "study_only_no_code_copy",
    "study_only_per_file_review",
    "study_only_unknown_license",
}


def _path_is_safe(value: str) -> bool:
    path = pathlib.PurePosixPath(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts


def load_manifest(path: pathlib.Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        manifest = yaml.safe_load(stream)
    if not isinstance(manifest, dict):
        raise ValueError("manifest root must be a mapping")
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    references = manifest.get("references")
    if not isinstance(references, list) or not references:
        raise ValueError("manifest must contain a non-empty references list")

    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for index, ref in enumerate(references):
        if not isinstance(ref, dict):
            raise ValueError(f"reference {index} must be a mapping")
        ref_id = ref.get("id")
        if not isinstance(ref_id, str) or not ID_RE.match(ref_id):
            raise ValueError(f"reference {index} has invalid id")
        if ref_id in seen:
            raise ValueError(f"duplicate reference id: {ref_id}")
        seen.add(ref_id)

        repository = ref.get("repository")
        if not isinstance(repository, str) or not repository.startswith("https://github.com/"):
            raise ValueError(f"{ref_id}: repository must be a canonical GitHub HTTPS URL")
        commit = ref.get("commit")
        if not isinstance(commit, str) or not COMMIT_RE.match(commit):
            raise ValueError(f"{ref_id}: commit must be a full 40-character lowercase sha")
        policy = ref.get("license_policy")
        if policy not in ALLOWED_POLICIES:
            raise ValueError(f"{ref_id}: unsupported license_policy {policy!r}")
        blockers = ref.get("blockers")
        if not isinstance(blockers, list) or not all(isinstance(item, str) and item for item in blockers):
            raise ValueError(f"{ref_id}: blockers must be a non-empty string list")
        sparse_paths = ref.get("sparse_paths")
        if not isinstance(sparse_paths, list) or not all(isinstance(item, str) and _path_is_safe(item) for item in sparse_paths):
            raise ValueError(f"{ref_id}: sparse_paths must be non-empty relative paths")
        if "GPL-2.0-only" in str(ref.get("license", "")) and policy != "study_only_no_code_copy":
            raise ValueError(f"{ref_id}: GPL-2.0-only references must be study_only_no_code_copy")
        if "NOASSERTION" in str(ref.get("license", "")) and not policy.startswith("study_only_"):
            raise ValueError(f"{ref_id}: unknown-license references must remain study-only")
        validated.append(ref)
    return validated


def manifest_identity(path: pathlib.Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def select_references(references: list[dict[str, Any]], ids: list[str] | None) -> list[dict[str, Any]]:
    if not ids:
        return references
    requested = set(ids)
    selected = [ref for ref in references if ref["id"] in requested]
    missing = sorted(requested.difference(ref["id"] for ref in selected))
    if missing:
        raise ValueError(f"unknown reference id(s): {', '.join(missing)}")
    return selected


def parse_fetcher_output(output: str) -> tuple[str, str]:
    checkout = ""
    commit = ""
    for line in output.splitlines():
        if line.startswith("checkout="):
            checkout = line.split("=", 1)[1]
        elif line.startswith("commit="):
            commit = line.split("=", 1)[1]
    if not checkout or not commit:
        raise RuntimeError("fetch-reference.sh did not report checkout and commit")
    return checkout, commit


def fetch_reference(ref: dict[str, Any], cache_root: pathlib.Path, fetcher: pathlib.Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["RENEGADE_VITA_REFERENCE_CACHE"] = str(cache_root)
    command = [str(fetcher), ref["repository"], ref["commit"], *ref["sparse_paths"]]
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip().splitlines()
        tail = detail[-1] if detail else f"exit {exc.returncode}"
        raise RuntimeError(f"{ref['id']}: reference fetch failed: {tail}") from exc
    checkout, observed_commit = parse_fetcher_output(completed.stdout)
    checkout_path = pathlib.Path(checkout)
    tracked_files = subprocess.check_output(
        ["git", "-C", str(checkout_path), "ls-files", "-t"],
        text=True,
    ).splitlines()
    materialized_files = [
        line[2:]
        for line in tracked_files
        if not line.startswith("S ") and len(line) > 2
    ]
    if observed_commit != ref["commit"]:
        raise RuntimeError(f"{ref['id']}: fetched {observed_commit}, expected {ref['commit']}")
    if not materialized_files:
        raise RuntimeError(f"{ref['id']}: sparse checkout produced no files")
    unmatched_paths = [
        requested
        for requested in ref["sparse_paths"]
        if requested not in materialized_files
        and not any(item.startswith(f"{requested.rstrip('/')}/") for item in materialized_files)
    ]
    if unmatched_paths:
        raise RuntimeError(f"{ref['id']}: sparse path(s) did not materialize: {', '.join(unmatched_paths)}")
    return {
        "id": ref["id"],
        "status": "FETCHED",
        "repository": ref["repository"],
        "commit": observed_commit,
        "checkout": str(checkout_path),
        "file_count": len(materialized_files),
        "files": materialized_files,
        "sparse_paths": list(ref["sparse_paths"]),
        "license": ref["license"],
        "license_policy": ref["license_policy"],
        "blockers": list(ref["blockers"]),
    }


def planned_reference(ref: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ref["id"],
        "status": "PLANNED_DRY_RUN",
        "repository": ref["repository"],
        "commit": ref["commit"],
        "file_count": None,
        "sparse_paths": list(ref["sparse_paths"]),
        "license": ref["license"],
        "license_policy": ref["license_policy"],
        "blockers": list(ref["blockers"]),
    }


def write_report(path: pathlib.Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")


def build_report(
    *,
    manifest_path: pathlib.Path,
    cache_root: pathlib.Path,
    dry_run: bool,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": 1,
        "generated_at_utc": _datetime.datetime.now(_datetime.UTC).replace(microsecond=0).isoformat(),
        "dry_run": dry_run,
        "cache_root": str(cache_root),
        "manifest": manifest_identity(manifest_path),
        "external_sources_imported_to_repo": False,
        "references": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache", type=pathlib.Path, default=pathlib.Path(os.environ.get("RENEGADE_VITA_REFERENCE_CACHE", "/tmp/renegade-vita-reference-cache")))
    parser.add_argument("--fetcher", type=pathlib.Path, default=DEFAULT_FETCHER)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--id", dest="ids", action="append", help="Fetch only one reference id; may be repeated")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true", help="List reference ids and exit")
    args = parser.parse_args(argv)

    manifest = load_manifest(args.manifest)
    references = validate_manifest(manifest)
    references = select_references(references, args.ids)

    if args.list:
        for ref in references:
            print(ref["id"])
        return 0

    if not args.dry_run:
        if not args.fetcher.is_file():
            raise SystemExit(f"fetcher is unavailable: {args.fetcher}")
        args.cache.mkdir(parents=True, exist_ok=True)

    results = []
    for ref in references:
        if args.dry_run:
            results.append(planned_reference(ref))
        else:
            results.append(fetch_reference(ref, args.cache, args.fetcher))

    report = build_report(
        manifest_path=args.manifest,
        cache_root=args.cache,
        dry_run=args.dry_run,
        results=results,
    )
    write_report(args.report, report)
    print(json.dumps({
        "status": "PASSED",
        "dry_run": args.dry_run,
        "references": len(results),
        "report": str(args.report),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
