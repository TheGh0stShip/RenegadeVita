#!/usr/bin/env python3
"""Summarize compiler/linker warnings and errors from build logs.

The parser is intentionally strict about recognized diagnostic forms, keeps
deterministic output, preserves representative original lines, and compares
candidate warnings against a baseline as new/persisting/resolved.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

TOOL_VERSION = "1.0.0"
SCHEMA_VERSION = 1
SEVERITY_ORDER = ("error", "linker_error", "warning", "linker_warning")

GCC_LIKE_RE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+)(?::(?P<column>\d+))?:\s*"
    r"(?P<kind>warning|error|fatal error):\s*(?P<message>.*)$",
    re.IGNORECASE,
)

LINKER_DRIVER_RE = re.compile(
    r"^(?P<tool>.+?):\s*(?P<kind>warning|error|fatal error):\s*(?P<message>.*)$",
    re.IGNORECASE,
)
LINKER_DRIVER_EMBEDDED_RE = re.compile(
    r"^(?P<tool>.+?):.*?(?::|\s)(?P<kind>warning|error|fatal error):\s*(?P<message>.*)$",
    re.IGNORECASE,
)

LINKER_TOOL_TOKENS = ("ld", "ld.exe", "lld", "lld.exe", "collect2", "collect2.exe", "gold", "gold.exe")

PATH_LOC_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]|/|\\)(?:[^\s:\"'<>()\[\]]+)"
    r"(?:\.\w+)?(?::\d+){1,2}",
)

PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/]|/|\\)[^\s:\"'<>()\[\]]+")
LINE_COLUMN_RE = re.compile(r"\b(?:line|column)\s+\d+\b", re.IGNORECASE)


def _normalize_signature(message: str) -> str:
    normalized = message.strip()
    normalized = PATH_LOC_RE.sub("<path>", normalized)
    normalized = PATH_RE.sub("<path>", normalized)
    normalized = LINE_COLUMN_RE.sub("<line_col>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_linker_tool(tool: str) -> bool:
    tool_name = Path(tool).name.lower()
    return any(token == tool_name for token in LINKER_TOOL_TOKENS)


def _classify(kind: str, tool: str | None = None) -> str:
    lower = kind.lower()
    if "error" in lower:
        if tool and _is_linker_tool(tool):
            return "linker_error"
        return "error"
    if tool and _is_linker_tool(tool):
        return "linker_warning"
    return "warning"


def _parse_line(raw_line: str) -> dict[str, object] | None:
    gcc_like = GCC_LIKE_RE.match(raw_line)
    if gcc_like:
        kind = gcc_like.group("kind").lower()
        if kind == "note":
            return None
        return {
            "severity": "error" if "error" in kind or "fatal" in kind else "warning",
            "source_file": gcc_like.group("path"),
            "source_line": int(gcc_like.group("line")),
            "source_column": int(gcc_like.group("column")) if gcc_like.group("column") else None,
            "message": gcc_like.group("message").strip(),
            "raw": raw_line.rstrip("\n"),
        }

    linker = LINKER_DRIVER_RE.match(raw_line)
    if linker:
        kind = linker.group("kind").lower()
        # Greedy context in linker diagnostics can extend the regex group past
        # the executable; the first prefix is the only tool identity.
        tool = raw_line.split(":", 1)[0]
        if kind == "note":
            return None
        return {
            "severity": _classify(kind, tool),
            "source_file": None,
            "source_line": None,
            "source_column": None,
            "message": linker.group("message").strip(),
            "raw": raw_line.rstrip("\n"),
            "tool": tool,
        }

    embedded = LINKER_DRIVER_EMBEDDED_RE.match(raw_line)
    if embedded:
        kind = embedded.group("kind").lower()
        # The embedded form may have object/function context after the tool;
        # only the first prefix identifies the linker executable.
        tool = embedded.group("tool").split(":", 1)[0]
        if kind == "note":
            return None
        return {
            "severity": _classify(kind, tool),
            "source_file": None,
            "source_line": None,
            "source_column": None,
            "message": embedded.group("message").strip(),
            "raw": raw_line.rstrip("\n"),
            "tool": tool,
        }

    return None


def _add_occurrence(
    buckets: dict[str, dict[str, object]],
    severity: str,
    signature: str,
    parsed: dict[str, object],
    log_path: str,
    log_line: int,
) -> None:
    entry = buckets.setdefault(
        severity,
        {},
    ).setdefault(signature, {
        "severity": severity,
        "signature": signature,
        "count": 0,
        "representative": None,
        "source_provenance": defaultdict(lambda: {"count": 0, "first_line": None, "last_line": None}),
    })

    entry["count"] = int(entry["count"]) + 1  # type: ignore[index]
    source_file = parsed["source_file"] if parsed["source_file"] is not None else "<tool>"
    source_line = parsed["source_line"]
    provenance = entry["source_provenance"][str(source_file)]  # type: ignore[index]
    provenance["count"] = int(provenance["count"]) + 1  # type: ignore[index]
    if provenance["first_line"] is None or (
        source_line is not None and source_line < provenance["first_line"]  # type: ignore[operator]
    ):
        provenance["first_line"] = source_line
    if provenance["last_line"] is None or (
        source_line is not None and source_line > provenance["last_line"]  # type: ignore[operator]
    ):
        provenance["last_line"] = source_line

    if entry["representative"] is None:  # type: ignore[index]
        entry["representative"] = {
            "source_file": source_file,
            "source_line": source_line,
            "source_column": parsed["source_column"],
            "log_file": log_path,
            "log_line": log_line,
            "raw": parsed["raw"],
        }


def _sort_signature_map(
    signature_map: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for signature in sorted(signature_map):
        record = dict(signature_map[signature])
        provenance_items = []
        for source in sorted(record["source_provenance"]):  # type: ignore[index]
            data = record["source_provenance"][source]  # type: ignore[index]
            provenance_items.append({
                "source_file": source,
                "count": data["count"],
                "first_line": data["first_line"],
                "last_line": data["last_line"],
            })
        record["source_provenance"] = provenance_items
        records.append(record)
    return records


def parse_logs(paths: list[Path]) -> dict[str, list[dict[str, object]]]:
    signature_buckets = {key: {} for key in SEVERITY_ORDER}

    for path in sorted(paths, key=lambda p: p.as_posix()):
        for lineno, raw in enumerate(path.read_bytes().decode("utf-8", errors="replace").splitlines(), 1):
            parsed = _parse_line(raw)
            if not parsed:
                continue
            severity = parsed["severity"]  # type: ignore[index]
            signature = _normalize_signature(parsed["message"])  # type: ignore[index]
            _add_occurrence(
                signature_buckets,
                str(severity),
                signature,
                parsed,
                str(path),
                lineno,
            )

    ordered = {}
    for severity in SEVERITY_ORDER:
        ordered[severity] = _sort_signature_map(signature_buckets[severity])
    return ordered


def _build_totals(signature_sections: dict[str, list[dict[str, object]]]) -> dict[str, int]:
    return {severity: sum(int(item["count"]) for item in signature_sections[severity]) for severity in SEVERITY_ORDER}


def _signature_key(severity: str, signature: str) -> tuple[str, str]:
    return severity, signature


def compare_signature_sets(
    candidate: dict[str, list[dict[str, object]]],
    baseline: dict[str, list[dict[str, object]]],
) -> list[dict[str, object]]:
    flat_candidate: dict[tuple[str, str], dict[str, object]] = {}
    flat_baseline: dict[tuple[str, str], dict[str, object]] = {}

    for severity in SEVERITY_ORDER:
        for entry in candidate[severity]:
            flat_candidate[_signature_key(severity, entry["signature"])] = entry
        for entry in baseline[severity]:
            flat_baseline[_signature_key(severity, entry["signature"])] = entry

    statuses = []
    for key in sorted(set(flat_candidate) | set(flat_baseline)):
        cand = flat_candidate.get(key)
        base = flat_baseline.get(key)
        cand_count = cand["count"] if cand else 0  # type: ignore[index]
        base_count = base["count"] if base else 0  # type: ignore[index]
        if base_count == 0:
            status = "new"
        elif cand_count == 0:
            status = "resolved"
        else:
            status = "persisting"
        severity, signature = key
        statuses.append({
            "status": status,
            "severity": severity,
            "signature": signature,
            "counts": {
                "baseline": base_count,
                "candidate": cand_count,
            },
            "baseline": base,
            "candidate": cand,
        })
    return statuses


def summarize(
    log_paths: list[Path],
    baseline: Path | None = None,
) -> dict[str, object]:
    candidate = parse_logs(log_paths)
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "candidate_logs": [str(path) for path in log_paths],
        "severity_order": list(SEVERITY_ORDER),
        "sections": candidate,
        "totals": _build_totals(candidate),
    }

    if baseline is not None:
        baseline_signatures = parse_logs([baseline])
        payload["baseline_log"] = str(baseline)
        payload["comparison"] = {
            "baseline_signatures": baseline_signatures,
            "diff": compare_signature_sets(candidate, baseline_signatures),
        }
    else:
        payload["baseline_log"] = None
        payload["comparison"] = None
    return payload


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize warning/error signatures from build logs.")
    parser.add_argument("logs", nargs="+", type=Path, help="One or more build logs to summarize")
    parser.add_argument("--baseline", type=Path, help="Optional baseline log for comparison")
    parser.add_argument("--output", type=Path, help="Write JSON summary to this path")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    summary = summarize(args.logs, args.baseline)
    serialized = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
