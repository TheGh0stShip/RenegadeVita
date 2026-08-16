#!/usr/bin/env python3
"""Produce bounded post-run evidence bundles for a Renegade Vita candidate.

The tool is intentionally conservative:
- discovers only files whose names include the candidate label,
- never guesses missing evidence,
- inspects diagnostic ZIP members through ``zipfile`` without extraction,
- keeps output JSON deterministically sorted with stable whitespace.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path


SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.0"

EXPECTED_LIFECYCLE_MARKERS = ("START", "END")
EXPECTED_PERFORMANCE_MARKERS = ("FRAME",)


def _sha256_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_stream(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def _normalize(text: str) -> str:
    normalized = text.lower().strip()
    normalized = re.sub(r"0x[0-9a-f]+", "<addr>", normalized)
    normalized = re.sub(r"\b\d+\b", "<num>", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def _parse_key_values(text: str) -> dict[str, str]:
    pairs = re.findall(r"\b([A-Za-z_][\w-]*)\s*=\s*(\"[^\"]*\"|'[^']*'|[^,\s]+)", text)
    values = {}
    for key, value in pairs:
        if ((value.startswith('"') and value.endswith('"')) or
                (value.startswith("'") and value.endswith("'"))):
            value = value[1:-1]
        values[key.lower()] = value
    return values


def _first_token(text: str) -> str:
    for token in text.split():
        if token:
            return token
    return ""


def _parse_event(payload: str) -> str:
    values = _parse_key_values(payload)
    event = values.get("event") or values.get("marker") or values.get("state")
    if not event:
        event = values.get("status") if payload.strip().lower().startswith(("status=", "state=")) else ""
    if not event:
        event = _first_token(payload)
    return (event or "UNKNOWN").upper()


def _parse_status(payload: str) -> str | None:
    values = _parse_key_values(payload)
    for key in ("status", "result", "outcome"):
        if key in values:
            return values[key].lower()
    return None


def _parse_performance_values(payload: str) -> dict[str, str]:
    values = _parse_key_values(payload)
    # Keep unparsed text for traceability when performance keys are not k=v.
    if "marker" not in values and "event" not in values and "name" not in values:
        token = _first_token(payload)
        if token:
            values["marker"] = token
    return values


def _to_number(value: str) -> str | int | float:
    lowered = value.lower()
    try:
        if "." in lowered or "e" in lowered:
            return float(lowered)
        return int(lowered, 10)
    except ValueError:
        return value


def _classify_termination(
    lifecycle_events: list[dict[str, object]],
    has_runtime_log: bool,
    has_crash_dump: bool,
) -> tuple[str, str]:
    for event in lifecycle_events:
        marker = (event.get("event") or "").upper()
        status = (event.get("status") or "").lower()
        if "CRASH" in marker or status in {"crash", "crashed", "fault", "fatal"}:
            return "crash", "explicit crash lifecycle marker"
        if status in {"clean", "exit", "success", "normal"} or "CLEAN" in marker:
            return "clean", "explicit clean lifecycle marker"
    if has_crash_dump:
        return "crash", "crash dump present"
    if has_runtime_log:
        return "unknown", "runtime log parsed without explicit termination marker"
    return "unknown", "no runtime evidence supplied"


def _read_declared_hashes(files: list[Path]) -> dict[str, str]:
    declarations: dict[str, str] = {}
    for hash_file in files:
        is_sha256_file = hash_file.suffix.lower() == ".sha256"
        is_sha256sums_file = hash_file.name.upper().endswith("SHA256SUMS.TXT")
        if not (is_sha256_file or is_sha256sums_file):
            continue
        try:
            lines = hash_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            m_space = re.match(r"^([0-9a-fA-F]{64})\s+(\S+)$", text)
            if m_space:
                digest, target = m_space.groups()
                declarations[target.lower()] = digest.lower()
                continue
            m_colon = re.match(r"^(\S+)\s*:\s*([0-9a-fA-F]{64})$", text)
            if m_colon:
                target, digest = m_colon.groups()
                declarations[target.lower()] = digest.lower()
    return declarations


def _read_text_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> str:
    if info.is_dir() or info.file_size <= 0:
        return ""
    if info.file_size > 1024 * 1024:
        return ""
    with zf.open(info) as stream:
        data = stream.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _scan_text_for_evidence(
    source: str,
    text: str,
    lifecycle_events: list[dict[str, object]],
    performance_records: list[dict[str, object]],
    message_log: list[tuple[str, int, str]],
    anomaly_markers: list[dict[str, str]],
) -> None:
    lifecycle_marker = re.compile(r"^\s*\[LIFECYCLE\]\s*(.*)$", re.IGNORECASE)
    performance_marker = re.compile(r"^\s*\[(?:PERF|PERFORMANCE)\]\s*(.*)$", re.IGNORECASE)
    for index, line in enumerate(text.splitlines(), 1):
        lifecycle_match = lifecycle_marker.match(line)
        if lifecycle_match:
            payload = lifecycle_match.group(1).strip()
            record = {
                "source": source,
                "line": index,
                "event": _parse_event(payload),
                "status": _parse_status(payload),
                "text": payload,
            }
            lifecycle_events.append(record)
            message_log.append((source, index, _normalize(payload)))
            continue

        performance_match = performance_marker.match(line)
        if performance_match:
            payload = performance_match.group(1).strip()
            parsed = _parse_performance_values(payload)
            label = (parsed.get("marker")
                     or parsed.get("event")
                     or parsed.get("name")
                     or "FRAME")
            record = {
                "source": source,
                "line": index,
                "label": str(label).upper(),
                "timestamp": index,
                "metrics": {key: _to_number(value) for key, value in parsed.items()},
            }
            if "frame" in record["metrics"]:
                try:
                    record["frame"] = int(record["metrics"]["frame"])
                except (TypeError, ValueError):
                    pass
            performance_records.append(record)
            message_log.append((source, index, _normalize(payload)))

        if "[ANOMALY]" in line:
            anomaly_markers.append({"source": source, "line": index, "text": line.strip()})


def _discover_candidate_files(dist_root: Path, candidate: str) -> list[Path]:
    candidate_norm = candidate.lower()
    candidates = []
    for path in sorted((path for path in dist_root.rglob("*") if path.is_file()), key=lambda p: p.as_posix().lower()):
        if candidate_norm in path.name.lower():
            candidates.append(path)
    return candidates


def _inspect_zip_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, source: str) -> dict[str, object]:
    with zf.open(info) as stream:
        digest = _sha256_stream(stream)
    entry = {
        "name": info.filename,
        "compressed_size": info.compress_size,
        "size": info.file_size,
        "crc": f"0x{info.CRC:08x}",
        "sha256": digest,
    }
    return entry


def _collect_zip_contents(
    zip_path: Path,
    lifecycle_events: list[dict[str, object]],
    performance_records: list[dict[str, object]],
    message_log: list[tuple[str, int, str]],
    anomaly_markers: list[dict[str, str]],
) -> dict[str, object]:
    members = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in sorted(zf.infolist(), key=lambda item: item.filename.lower()):
            members.append(_inspect_zip_member(zf, info, zip_path.as_posix()))
            if not info.is_dir():
                text = _read_text_member(zf, info)
                if text:
                    _scan_text_for_evidence(f"{zip_path.as_posix()}!{info.filename}", text, lifecycle_events,
                                            performance_records, message_log, anomaly_markers)
    return {
        "path": zip_path.relative_to(zip_path.anchor).as_posix() if zip_path.is_absolute() else zip_path.as_posix(),
        "file_count": len(members),
        "members": members,
    }


def _build_artifacts(
    dist_root: Path,
    candidate: str,
    runtime_log: Path | None,
    declared_hashes: dict[str, str],
) -> tuple[
    list[dict[str, object]],
    dict[str, object],
    list[dict[str, str]],
    bool,
    list[dict[str, object]],
    list[dict[str, object]],
]:
    discovered = _discover_candidate_files(dist_root, candidate)
    lifecycle_events: list[dict[str, object]] = []
    performance_records: list[dict[str, object]] = []
    message_log: list[tuple[str, int, str]] = []
    anomalies: list[dict[str, str]] = []
    hash_mismatches = []
    crash_dump_present = False

    entries = []
    for path in discovered:
        rel_path = path.relative_to(dist_root).as_posix()
        entry: dict[str, object] = {
            "path": rel_path,
            "size": path.stat().st_size,
            "sha256": _sha256_bytes(path),
        }
        lower_name = path.name.lower()
        suffix = path.suffix.lower()

        if suffix == ".zip":
            entry["kind"] = "diagnostic_zip"
            with zipfile.ZipFile(path) as zf:
                members = []
                file_count = 0
                for info in sorted(zf.infolist(), key=lambda item: item.filename.lower()):
                    members.append(_inspect_zip_member(zf, info, rel_path))
                    if not info.is_dir():
                        file_count += 1
                        text = _read_text_member(zf, info)
                        if text:
                            _scan_text_for_evidence(f"{rel_path}!{info.filename}", text, lifecycle_events,
                                                    performance_records, message_log, anomalies)
            entry["zip_members"] = {
                "file_count": file_count,
                "members": members,
            }

        elif suffix in {".psp2dmp", ".psp2core", ".dmp"} or lower_name.startswith("psp2core-"):
            entry["kind"] = "crash_dump"
            entry["sha256"] = _sha256_bytes(path)
            crash_dump_present = True
            entry["action"] = "inventory_only"
        else:
            entry["kind"] = "artifact"

        declared = declared_hashes.get(lower_name)
        if declared:
            entry["declared_sha256"] = declared
            entry["hash_matches"] = declared == str(entry["sha256"])
            if not entry["hash_matches"]:
                mismatch = {
                    "type": "hash_mismatch",
                    "path": rel_path,
                    "declared": declared,
                    "actual": str(entry["sha256"]),
                    "kind": "candidate_artifact",
                }
                anomalies.append(mismatch)
                hash_mismatches.append(mismatch)
        entries.append(entry)

    if runtime_log is not None:
        if runtime_log.exists():
            _scan_text_for_evidence(runtime_log.as_posix(), runtime_log.read_text(encoding="utf-8", errors="replace"),
                                   lifecycle_events, performance_records, message_log, anomalies)
        else:
            anomalies.append({
                "type": "missing_optional_file",
                "path": runtime_log.as_posix(),
                "reason": "runtime log path was supplied but file is missing",
            })

    counts = Counter(message for _, _, message in message_log)
    repeated = []
    for message, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        if count > 1:
            locations = [{"source": source, "line": line}
                         for source, line, current in message_log
                         if current == message]
            repeated.append({
                "normalized_message": message,
                "count": count,
                "locations": locations,
            })
    if repeated:
        anomalies.extend({"type": "repeated_normalized_message", "message": item["normalized_message"],
                          "count": item["count"], "locations": item["locations"]} for item in repeated)

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "candidate_label": candidate,
        "discovered_files": sorted(entries, key=lambda entry: entry["path"]),
        "file_count": len(entries),
        "hash_mismatches": hash_mismatches,
        "crash_dump_present": crash_dump_present,
        "message_summary": {
            "lifecycle_events": len(lifecycle_events),
            "performance_events": len(performance_records),
        },
    }
    return entries, manifest, anomalies, crash_dump_present, lifecycle_events, performance_records


def _build_summary(
    candidate: str,
    dist_root: Path,
    runtime_log: Path | None,
    lifecycle_events: list[dict[str, object]],
    performance_records: list[dict[str, object]],
    manifest: dict[str, object],
    anomalies: list[dict[str, str]],
    crash_dump_present: bool,
    user_observation: str,
) -> dict[str, object]:
    observed_lifecycle = [str(value) for value in sorted({str(event["event"]) for event in lifecycle_events})]
    observed_perf = [str(value) for value in sorted({str(record["label"]) for record in performance_records})]
    missing_lifecycle = [marker for marker in EXPECTED_LIFECYCLE_MARKERS if marker not in observed_lifecycle]
    missing_performance = [marker for marker in EXPECTED_PERFORMANCE_MARKERS if marker not in observed_perf]

    has_runtime_log = runtime_log is not None and runtime_log.exists()
    termination, reason = _classify_termination(lifecycle_events, has_runtime_log, crash_dump_present)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_label": candidate,
        "dist_directory": dist_root.as_posix(),
        "user_observation": {
            "source": "cli",
            "text": user_observation,
        },
        "runtime_log": {
            "provided": str(runtime_log) if runtime_log else None,
            "present": has_runtime_log,
        },
        "artifacts": manifest,
        "termination": {
            "classification": termination,
            "rationale": reason,
        },
        "marker_summary": {
            "expected_lifecycle_markers": list(EXPECTED_LIFECYCLE_MARKERS),
            "actual_lifecycle_markers": observed_lifecycle,
            "missing_lifecycle_markers": missing_lifecycle,
            "expected_performance_markers": list(EXPECTED_PERFORMANCE_MARKERS),
            "actual_performance_markers": observed_perf,
            "missing_performance_markers": missing_performance,
        },
    }
    return summary


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_performance_csv(path: Path, records: list[dict[str, object]]) -> None:
    fieldnames = {"timestamp", "source", "line", "label", "frame"}
    metric_fields = set()
    for record in records:
        metrics = record.get("metrics", {})
        metric_fields.update([key for key in metrics.keys()])
    fieldnames.update(metric_fields)
    headers = sorted(fieldnames)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        for record in records:
            metrics = record.get("metrics", {})
            row: dict[str, object] = {
                "timestamp": record.get("timestamp"),
                "source": record.get("source"),
                "line": record.get("line"),
                "label": record.get("label"),
                "frame": record.get("frame", ""),
            }
            for key in metric_fields:
                value = metrics.get(key, "")
                row[key] = value
            writer.writerow(row)


def _write_markdown(path: Path, summary: dict[str, object], anomalies: list[dict[str, str]], performance_count: int) -> None:
    marker_summary = summary["marker_summary"]
    lines = [
        "# Renegade Vita post-run report",
        "",
        f"Candidate: `{summary['candidate_label']}`",
        f"Dist root: `{summary['dist_directory']}`",
        "",
        "## Machine evidence",
        "",
        f"- Termination: {summary['termination']['classification']} ({summary['termination']['rationale']})",
        f"- Observed lifecycle markers: {', '.join(marker_summary['actual_lifecycle_markers']) or 'none'}",
        f"- Observed performance markers: {', '.join(marker_summary['actual_performance_markers']) or 'none'}",
        f"- Performance samples: {performance_count}",
        "",
        "## Marker expected/actual",
        "",
        f"- Lifecycle expected: {', '.join(marker_summary['expected_lifecycle_markers'])}",
        f"- Lifecycle missing: {', '.join(marker_summary['missing_lifecycle_markers']) or 'none'}",
        f"- Performance expected: {', '.join(marker_summary['expected_performance_markers'])}",
        f"- Performance missing: {', '.join(marker_summary['missing_performance_markers']) or 'none'}",
        "",
    ]
    if anomalies:
        lines.extend(["## Machine anomalies", ""])
        for anomaly in anomalies:
            lines.append(f"- {anomaly['type']}: {anomaly}")
    else:
        lines.extend(["## Machine anomalies", "", "- none"])
    lines.extend(["", "## User observation", "", summary["user_observation"]["text"] or "none"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_completion(output_dir: Path, summary: dict[str, object], artifacts: dict[str, object],
                     anomalies: list[dict[str, str]]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "candidate_label": summary["candidate_label"],
        "termination": summary["termination"]["classification"],
        "artifact_file_count": artifacts["file_count"],
        "anomaly_count": len(anomalies),
        "expected_markers_complete": (
            not summary["marker_summary"]["missing_lifecycle_markers"] and
            not summary["marker_summary"]["missing_performance_markers"]
        ),
        "artifact_manifest": "artifact_manifest.json",
        "session_summary": "session_summary.json",
        "performance_metrics": "performance_metrics.csv",
        "anomalies": "anomalies.json",
        "postrun_report": "postrun_report.md",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate_label", help="candidate string used in artifact names")
    parser.add_argument("dist_directory", help="directory to discover candidate artifacts")
    parser.add_argument("output_directory", help="directory for generated report files")
    parser.add_argument("--runtime-log", dest="runtime_log", help="optional runtime log path")
    parser.add_argument("--user-observation", default="", help="free-form user observation text")
    args = parser.parse_args(argv)

    dist_root = Path(args.dist_directory).resolve()
    output_root = Path(args.output_directory).resolve()
    runtime_log = Path(args.runtime_log).resolve() if args.runtime_log else None

    if not dist_root.is_dir():
        print("dist directory is missing", file=sys.stderr)
        return 2

    discovered = _discover_candidate_files(dist_root, args.candidate_label)
    hash_declarations = _read_declared_hashes(discovered)
    entries, manifest, anomalies, has_crash_dump, lifecycle_events, performance_records = _build_artifacts(
        dist_root, args.candidate_label, runtime_log, hash_declarations
    )
    del entries

    summary = _build_summary(args.candidate_label, dist_root, runtime_log, lifecycle_events, performance_records,
                             manifest, anomalies, has_crash_dump, args.user_observation)

    output_root.mkdir(parents=True, exist_ok=True)
    artifact_path = output_root / "artifact_manifest.json"
    session_path = output_root / "session_summary.json"
    performance_path = output_root / "performance_metrics.csv"
    anomalies_path = output_root / "anomalies.json"
    report_path = output_root / "postrun_report.md"
    completion_path = output_root / "completion.json"

    _write_json(artifact_path, manifest)
    _write_json(session_path, summary)
    _write_performance_csv(performance_path, performance_records)
    _write_json(anomalies_path, sorted(anomalies, key=lambda item: (item.get("type", ""), item.get("path", ""))))
    _write_markdown(report_path, summary, anomalies, len(performance_records))
    _write_json(completion_path, _build_completion(output_root, summary, manifest, anomalies))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
