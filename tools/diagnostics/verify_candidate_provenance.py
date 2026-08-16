#!/usr/bin/env python3
"""Verify canonical Renegade Vita candidate provenance artifacts.

Inputs:
    1. DIST_DIR
    2. CANDIDATE_LABEL

The verifier requires candidate-prefixed artifacts and a candidate SHA256 manifest,
checks all manifest paths stay within DIST_DIR, validates required SHA-256 hashes
from the manifest, validates VPK contents entries, and writes deterministic JSON
and Markdown reports containing only PASS/FAIL/MISSING statuses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.0"

REQUIRED_FILES = {
    "vpk": "RenegadeVita-{candidate}.vpk",
    "elf": "RenegadeVita-{candidate}.elf",
    "map": "RenegadeVita-{candidate}.map",
    "elf_header": "RenegadeVita-{candidate}.elf-header.txt",
    "symbols": "RenegadeVita-{candidate}.symbols.txt",
    "vpk_contents": "RenegadeVita-{candidate}.vpk-contents.txt",
    "build_report": "{candidate}-BUILD_REPORT.txt",
    "host_log": "{candidate}-HOST-VALIDATION.log",
    "sha_manifest": "{candidate}-SHA256SUMS.txt",
}

EXPECTED_VPK_FILES = ("eboot.bin", "sce_sys/param.sfo")
OUTPUT_BASENAME = "{candidate}-CANDIDATE-PROVENANCE"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_manifest_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    return normalized


def _manifest_entry_lines(manifest_file: Path) -> tuple[list[tuple[str, str]], list[dict[str, object]]]:
    """
    Returns a list of (relative_path, expected_hash) entries and a list of
    parsing anomalies.
    """
    parsed: list[tuple[str, str]] = []
    anomalies: list[dict[str, object]] = []
    if not manifest_file.exists():
        return parsed, anomalies

    text = manifest_file.read_text(encoding="utf-8", errors="replace")
    for index, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m_space = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.*)$", line)
        if m_space:
            declared, target = m_space.groups()
            parsed.append((_normalize_manifest_path(target), declared.lower()))
            continue

        m_colon = re.match(r"^(.*)\s*:\s*([0-9a-fA-F]{64})$", line)
        if m_colon:
            target, declared = m_colon.groups()
            parsed.append((_normalize_manifest_path(target), declared.lower()))
            continue

        anomalies.append({
            "type": "manifest_unparseable",
            "status": "FAIL",
            "path": f"{manifest_file}:line-{index}",
            "text": line,
        })

    return parsed, anomalies


def _manifest_checks(dist_dir: Path, manifest_entries: list[tuple[str, str]]) -> tuple[dict[str, object], dict[str, str], list[dict[str, object]]]:
    """
    Validate every manifest-relative path stays inside DIST_DIR and hash-checks
    entries that are discoverable in-tree.
    """
    safe_checks: list[dict[str, object]] = []
    required_by_path: dict[str, str] = {}
    seen_paths: set[str] = set()

    for rel_path, expected in manifest_entries:
        check: dict[str, object] = {
            "path": rel_path,
            "status": "PASS",
            "declared_sha256": expected.lower(),
        }
        rel_path = rel_path.replace("\\", "/")
        parts = [part for part in rel_path.split("/") if part not in {"", "."}]
        if ".." in parts:
            check["status"] = "FAIL"
            check["reason"] = "manifest path is outside DIST_DIR"
            safe_checks.append(check)
            continue

        check["path"] = rel_path
        candidate_path = dist_dir / Path(*parts)
        # strict containment check, independent of file existence
        try:
            candidate_path.resolve().relative_to(dist_dir.resolve())
        except ValueError:
            check["status"] = "FAIL"
            check["reason"] = "manifest path is outside DIST_DIR"
            safe_checks.append(check)
            continue

        if rel_path in seen_paths:
            check["status"] = "FAIL"
            check["reason"] = "duplicate manifest path"
            safe_checks.append(check)
            continue
        seen_paths.add(rel_path)

        if not candidate_path.is_file():
            check["status"] = "FAIL"
            check["reason"] = "declared file missing"
            safe_checks.append(check)
            continue

        actual = _sha256(candidate_path)
        check["actual_sha256"] = actual
        if actual != expected.lower():
            check["status"] = "FAIL"
            check["reason"] = "sha256 mismatch"
        required_by_path[rel_path] = expected.lower()
        safe_checks.append(check)

    result = {
        "kind": "manifest_path_and_hash",
        "status": "PASS" if all(check["status"] == "PASS" for check in safe_checks) else "FAIL",
        "entries": safe_checks,
    }
    return result, required_by_path, safe_checks


def _required_artifact_checks(
    dist_dir: Path,
    candidate: str,
    manifest_map: dict[str, str],
    manifest_exists: bool,
) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    for key, template in REQUIRED_FILES.items():
        rel_name = template.format(candidate=candidate)
        artifact_path = dist_dir / rel_name
        status = "PASS"
        reason = ""
        declared = manifest_map.get(rel_name)
        actual: str | None = None
        hash_matches = None

        if not artifact_path.exists():
            status = "MISSING"
            reason = "required artifact missing"
        else:
            actual = _sha256(artifact_path)
            if key == "sha_manifest":
                hash_matches = None
            elif not manifest_exists:
                status = "FAIL"
                reason = "sha manifest missing"
            elif declared is None:
                status = "FAIL"
                reason = "artifact missing from manifest"
            elif actual != declared:
                status = "FAIL"
                reason = "sha256 mismatch"
                hash_matches = False
            else:
                hash_matches = True

        checks.append({
            "artifact": key,
            "path": rel_name,
            "status": status,
            "actual_sha256": actual,
            "declared_sha256": declared,
            "hash_matches": hash_matches,
            "reason": reason,
        })

    return checks


def _vpk_contents_check(path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "artifact": "vpk_contents_report",
        "path": path.name,
        "status": "PASS",
        "reason": "",
        "expected_entries": list(EXPECTED_VPK_FILES),
        "actual_entries": [],
    }
    if not path.exists():
        result["status"] = "MISSING"
        result["reason"] = "required artifact missing"
        return result

    lines = [
        _normalize_manifest_path(line)
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]
    result["actual_entries"] = lines
    if len(lines) != len(EXPECTED_VPK_FILES):
        result["status"] = "FAIL"
        result["reason"] = "unexpected vpk contents count"
        return result
    if tuple(sorted(lines)) != tuple(sorted(EXPECTED_VPK_FILES)):
        result["status"] = "FAIL"
        result["reason"] = "unexpected vpk contents entries"
        return result
    return result


def _markdown_report(output: dict[str, object], path: Path) -> None:
    lines = [
        "# Renegade Vita candidate provenance report",
        "",
        f"Candidate: `{output['candidate_label']}`",
        f"Dist directory: `{output['dist_directory']}`",
        f"Overall: {output['overall_status']}",
        "Physical validation: not claimed by this verifier.",
        "",
        "## Checks",
    ]
    for check in output["checks"]:
        artifact = check.get("artifact", check.get("kind", "artifact"))
        status = check["status"]
        reason = check.get("reason", "")
        artifact_path = check.get("path", "")
        lines.append(f"- {status} {artifact}: {artifact_path}{(' (' + reason + ')') if reason else ''}")
    lines.append("")
    lines.append("## Manifest entries")
    for entry in output["manifest"]["entries"]:
        lines.append(
            f"- {entry['status']} {entry['path']} "
            f"declared={entry.get('declared_sha256', 'missing')} "
            f"actual={entry.get('actual_sha256', 'missing')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _output_paths(dist_dir: Path, candidate: str) -> tuple[Path, Path]:
    base = OUTPUT_BASENAME.format(candidate=candidate)
    return dist_dir / f"{base}.json", dist_dir / f"{base}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist_dir", help="directory containing candidate evidence")
    parser.add_argument("candidate_label", help="candidate label used in artifact names")
    args = parser.parse_args(argv)

    dist_dir = Path(args.dist_dir).resolve()
    candidate = args.candidate_label

    if not dist_dir.is_dir():
        print("dist_dir is missing", file=sys.stderr)
        return 2

    checks: list[dict[str, object]] = []

    sha_manifest_name = REQUIRED_FILES["sha_manifest"].format(candidate=candidate)
    manifest_path = dist_dir / sha_manifest_name
    manifest_exists = manifest_path.exists()
    manifest_entries, parse_anomalies = _manifest_entry_lines(manifest_path)
    manifest_result, manifest_map, manifest_entry_checks = _manifest_checks(dist_dir, manifest_entries)

    if not manifest_exists:
        manifest_result["status"] = "FAIL"
        manifest_entry_checks.append({
            "path": sha_manifest_name,
            "status": "MISSING",
            "reason": "manifest file missing",
        })

    required_checks = _required_artifact_checks(dist_dir, candidate, manifest_map, manifest_exists)
    checks.extend(required_checks)

    vpk_contents_path = dist_dir / REQUIRED_FILES["vpk_contents"].format(candidate=candidate)
    vpk_contents_result = _vpk_contents_check(vpk_contents_path)

    if parse_anomalies:
        manifest_entry_checks.extend(parse_anomalies)
        manifest_result["status"] = "FAIL"

    checks.append(vpk_contents_result)

    manifest_summary = {
        "status": manifest_result["status"],
        "entries": manifest_entry_checks,
    }
    checks.insert(0, manifest_result)

    check_statuses = [check["status"] for check in checks]
    overall_status = "PASS" if all(status == "PASS" for status in check_statuses) else "FAIL"
    if not manifest_exists:
        overall_status = "FAIL"

    output = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "candidate_label": candidate,
        "dist_directory": str(dist_dir),
        "overall_status": overall_status,
        "checks": sorted(checks, key=lambda item: str(item.get("artifact", item.get("kind", "")))),
        "manifest": manifest_summary,
        "required_artifact_count": len(REQUIRED_FILES),
    }

    json_path, markdown_path = _output_paths(dist_dir, candidate)
    json_path.write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    _markdown_report(output, markdown_path)

    # Required files and hash mismatches are material; absence of physical-device
    # evidence intentionally keeps this verifier from making physical claims.
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
