#!/usr/bin/env python3
"""Parse candidate runtime logs and emit deterministic runtime-field summaries.

The parser only recognizes explicitly labelled fields:
FPS, frame-time-percentile, slow-frame, simulation, rendering,
mesh/triangle/indexed-submission, texture-bind, state-change, memory, and
instrumentation-overhead. Unknown line formats are preserved as raw evidence.

For each parsed field value, the report preserves source file and line provenance.
When exactly two consecutive logs are compared, before/after deltas are computed
only if both logs declare identical content/configuration/camera identifiers.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any
import re

SCHEMA_VERSION = 1
TOOL_VERSION = "1.0.0"

KNOWN_METRICS = (
    "fps",
    "frame_time_min",
    "frame_time_percentile_p50",
    "frame_time_percentile_p95",
    "frame_time_percentile_p99",
    "frame_time_max",
    "slow_frame",
    "slow_over_16_7ms",
    "slow_over_20_0ms",
    "slow_over_33_3ms",
    "slow_over_50_0ms",
    "sync",
    "simulation",
    "rendering",
    "mesh",
    "triangle",
    "indexed_submission",
    "texture_bind",
    "texture_bind_skip",
    "texture_sampler_update",
    "texture_sampler_skip",
    "texture_stage_enable_skip",
    "texture_combiner_skip",
    "texture_unsupported_stage",
    "state_change",
    "render_state_skip",
    "memory",
    "instrumentation_overhead",
)

IDENTITY_KEYS = ("content_id", "configuration_id", "camera_id")
KEY_VALUE_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_-]*)\s*(?:=|:)\s*(\"[^\"]*\"|'[^']*'|[^,\s]+)")
PERCENTILE_RE = re.compile(r"frame[-_ ]?time[-_ ]?percentile(?:[-_]?p?(\d{2}))?", re.IGNORECASE)
TIME_PERCENTILE_RE = re.compile(r"frame[_-]?time[_-]?p(\d{2})", re.IGNORECASE)
FRAME_US_SUMMARY_RE = re.compile(
    r"\bframe_us\s+min/p50/p95(?:/p99)?/max=([0-9.]+)/([0-9.]+)/([0-9.]+)(?:/([0-9.]+))?/([0-9.]+)")
P50_P95_WORST_US_RE = re.compile(r"\bp50/p95/worst_us=([0-9.]+)/([0-9.]+)/([0-9.]+)")
STAGE_US_SUMMARY_RE = re.compile(r"\bstage_us\s+sync/sim/render=([0-9.]+)/([0-9.]+)/([0-9.]+)")


def _canonical_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", raw.strip().lower()).strip("_")


def _to_number(text: str) -> float | int | None:
    value = text.strip().strip("`")
    if not value:
        return None
    try:
        if value.startswith("0x") or value.startswith("0X"):
            return int(value, 16)
        if re.fullmatch(r"[-+]?\d+", value):
            return int(value)
        return float(value)
    except ValueError:
        return None


def _coerce_int_or_float(value: float | int | None) -> str | int | float | None:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _metric_for_key(key: str) -> str | None:
    normalized = _canonical_key(key)
    if normalized in {
        "fps", "avg_fps", "average_fps", "perf_fps", "frame_rate",
        "frame_rate_fps", "frames_per_second",
    }:
        return "fps"
    if normalized in {"slow_frame", "slow_frame_ms"}:
        return "slow_frame"
    if normalized in {
        "slow_over_16ms", "slow_over_16_7ms", "slow_over_16_7_ms",
        "frames_over_16_7ms",
    }:
        return "slow_over_16_7ms"
    if normalized in {
        "slow_over_20ms", "slow_over_20_0ms", "slow_over_20_0_ms",
        "frames_over_20ms", "frames_over_20_0ms",
    }:
        return "slow_over_20_0ms"
    if normalized in {
        "slow_over_33ms", "slow_over_33_3ms", "slow_over_33_3_ms",
        "frames_over_33ms", "frames_over_33_3ms",
    }:
        return "slow_over_33_3ms"
    if normalized in {
        "slow_over_50ms", "slow_over_50_0ms", "slow_over_50_0_ms",
        "frames_over_50ms", "frames_over_50_0ms",
    }:
        return "slow_over_50_0ms"
    if normalized in {"sync", "sync_ms", "sync_us"}:
        return "sync"
    if normalized in {"simulation", "simulation_ms", "simulation_us", "sim_us"}:
        return "simulation"
    if normalized in {"rendering", "rendering_ms", "rendering_us", "render_us"}:
        return "rendering"
    if normalized in {"mesh", "meshes", "mesh_count"}:
        return "mesh"
    if normalized in {"triangle", "triangles", "triangle_count"}:
        return "triangle"
    if normalized in {"indexed_submission", "indexed_submissions", "indexed_submission_count"}:
        return "indexed_submission"
    if normalized in {"texture_bind", "texture_binds", "texturebind", "texture_bind_count"}:
        return "texture_bind"
    if normalized in {"texture_bind_skip", "texture_bind_skips", "texture_bind_skip_count"}:
        return "texture_bind_skip"
    if normalized in {
        "texture_sampler_update", "texture_sampler_updates",
        "texture_sampler_update_count",
    }:
        return "texture_sampler_update"
    if normalized in {
        "texture_sampler_skip", "texture_sampler_skips",
        "texture_sampler_skip_count",
    }:
        return "texture_sampler_skip"
    if normalized in {
        "texture_stage_enable_skip", "texture_stage_enable_skips",
        "texture_stage_enable_skip_count",
    }:
        return "texture_stage_enable_skip"
    if normalized in {
        "texture_combiner_skip", "texture_combiner_skips",
        "texture_combiner_skip_count",
    }:
        return "texture_combiner_skip"
    if normalized in {
        "texture_unsupported_stage", "texture_unsupported_stages",
        "texture_unsupported_stage_count",
    }:
        return "texture_unsupported_stage"
    if normalized in {"state_change", "state_change_count", "state_changes"}:
        return "state_change"
    if normalized in {"render_state_skip", "render_state_skips", "render_state_skip_count"}:
        return "render_state_skip"
    if normalized in {"memory", "memory_bytes", "memory_kib", "memory_mib"}:
        return "memory"
    if normalized in {"instrumentation_overhead", "instrumentation_overhead_ms", "instrumentation_overhead_pct"}:
        return "instrumentation_overhead"
    if normalized in {"frame_time_min", "frame_time_min_us", "min_frame_us"}:
        return "frame_time_min"
    if normalized in {"frame_time_max", "frame_time_max_us", "worst_frame_us", "max_frame_us"}:
        return "frame_time_max"

    match = TIME_PERCENTILE_RE.fullmatch(normalized)
    if match:
        return f"frame_time_percentile_p{match.group(1)}"
    match = PERCENTILE_RE.fullmatch(normalized)
    if match:
        percentile = match.group(1)
        return f"frame_time_percentile_p{percentile}" if percentile else None
    if normalized in {"frame_time_percentile_50", "frame_time_percentile_p50"}:
        return "frame_time_percentile_p50"
    if normalized in {"frame_time_percentile_95", "frame_time_percentile_p95"}:
        return "frame_time_percentile_p95"
    if normalized in {"frame_time_percentile_99", "frame_time_percentile_p99"}:
        return "frame_time_percentile_p99"
    return None


def _structured_runtime_key_values(text: str) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for match in FRAME_US_SUMMARY_RE.finditer(text):
        values.append(("frame_time_min_us", match.group(1)))
        values.append(("frame_time_p50", match.group(2)))
        values.append(("frame_time_p95", match.group(3)))
        if match.group(4):
            values.append(("frame_time_p99", match.group(4)))
        values.append(("frame_time_max_us", match.group(5)))
    for match in P50_P95_WORST_US_RE.finditer(text):
        values.append(("frame_time_p50", match.group(1)))
        values.append(("frame_time_p95", match.group(2)))
        values.append(("frame_time_max_us", match.group(3)))
    for match in STAGE_US_SUMMARY_RE.finditer(text):
        values.append(("sync_us", match.group(1)))
        values.append(("simulation_us", match.group(2)))
        values.append(("rendering_us", match.group(3)))
    return values


def _identity_key(raw: str) -> str | None:
    normalized = _canonical_key(raw)
    if normalized in {"content", "content_id", "content_identifier"}:
        return "content_id"
    if normalized in {"configuration", "configuration_id", "config", "config_id"}:
        return "configuration_id"
    if normalized in {"camera", "camera_id", "camera_identifier"}:
        return "camera_id"
    return None


def _parse_key_values(text: str) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    for key, value in KEY_VALUE_RE.findall(text):
        if (value.startswith(("'", '"')) and value.endswith(("'", '"'))) and len(value) >= 2:
            value = value[1:-1]
        values.append((key, value))
    return values


def _aggregate_metric_values(samples: list[dict[str, Any]]) -> dict[str, Any]:
    values = [sample["value"] for sample in samples if isinstance(sample["value"], (int, float))]
    if not values:
        return {
            "samples": 0,
            "min": None,
            "max": None,
            "mean": None,
        }
    return {
        "samples": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
    }


def _numeric_delta(before: Any, after: Any) -> dict[str, Any]:
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return {"before": before, "after": after, "delta": None, "delta_percent": None}
    delta = after - before
    pct = None
    if before not in (0, 0.0):
        pct = (delta / before) * 100.0
    return {
        "before": before,
        "after": after,
        "delta": delta,
        "delta_percent": pct,
    }


def parse_log(path: Path) -> dict[str, Any]:
    run = {
        "path": str(path),
        "label": path.name,
        "identity": {key: None for key in IDENTITY_KEYS},
        "identity_lines": {},
        "samples": [],
        "metrics": {},
        "unknown_lines": [],
        "unknown_count": 0,
    }

    for metric in KNOWN_METRICS:
        run["metrics"][metric] = []

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line_number, raw_line in enumerate(lines, 1):
        assignments = _parse_key_values(raw_line)
        assignments.extend(_structured_runtime_key_values(raw_line))
        parsed_something = False
        for key, value in assignments:
            identity_field = _identity_key(key)
            metric_field = _metric_for_key(key)
            if identity_field:
                run["identity"][identity_field] = value
                run["identity_lines"].setdefault(identity_field, []).append({
                    "file": str(path),
                    "line": line_number,
                    "value": value,
                    "key": key,
                })
                parsed_something = True
                continue
            if not metric_field:
                if assignments:
                    parsed_something = True
                    # Explicit unknown field: preserve raw evidence.
                    run["unknown_lines"].append({
                        "file": str(path),
                        "line": line_number,
                        "raw": raw_line,
                        "reason": f"unrecognized label '{key}'",
                    })
                    continue
            if not metric_field:
                continue
            numeric = _to_number(value)
            if numeric is None:
                run["unknown_lines"].append({
                    "file": str(path),
                    "line": line_number,
                    "raw": raw_line,
                    "reason": f"non-numeric value for '{key}'",
                })
                parsed_something = True
                continue
            parsed_something = True
            run["samples"].append({
                "metric": metric_field,
                "value": _coerce_int_or_float(numeric),
                "source_file": str(path),
                "source_line": line_number,
                "raw_line": raw_line.strip(),
                "raw_key": key,
            })
            run["metrics"][metric_field].append({
                "value": _coerce_int_or_float(numeric),
                "source_file": str(path),
                "source_line": line_number,
                "raw_key": key,
            })

        if not assignments and raw_line.strip():
            run["unknown_lines"].append({
                "file": str(path),
                "line": line_number,
                "raw": raw_line,
                "reason": "unparsed plain text",
            })
            parsed_something = True

        if not parsed_something:
            continue

    for key in KNOWN_METRICS:
        run["metrics"][key] = _aggregate_metric_values(run["metrics"][key])

    run["unknown_count"] = len(run["unknown_lines"])
    return run


def _identity_tuple(identity: dict[str, str | None]) -> tuple[str | None, str | None, str | None]:
    return (identity["content_id"], identity["configuration_id"], identity["camera_id"])


def _identity_complete(identity: dict[str, str | None]) -> bool:
    return all(identity[key] for key in IDENTITY_KEYS)


def compare_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    comparisons: list[dict[str, Any]] = []
    if len(runs) < 2:
        return comparisons

    for index in range(0, len(runs) - 1, 2):
        before = runs[index]
        after = runs[index + 1]
        before_identity = before["identity"]
        after_identity = after["identity"]

        identities_equal = _identity_tuple(before_identity) == _identity_tuple(after_identity)
        complete = _identity_complete(before_identity) and _identity_complete(after_identity)
        comparison: dict[str, Any] = {
            "before": {"run_index": index, "path": before["path"], "identity": before_identity},
            "after": {"run_index": index + 1, "path": after["path"], "identity": after_identity},
            "state_comparison_eligible": False,
            "ineligible_reason": None,
            "deltas": {},
        }

        if not (identities_equal and complete):
            comparison["ineligible_reason"] = "state identifiers are incompatible or incomplete"
            comparisons.append(comparison)
            continue

        comparison["state_comparison_eligible"] = True
        for metric in KNOWN_METRICS:
            b_stat = before["metrics"].get(metric, {})
            a_stat = after["metrics"].get(metric, {})
            comparison["deltas"][metric] = _numeric_delta(b_stat.get("mean"), a_stat.get("mean"))
        comparisons.append(comparison)
    return comparisons


def make_report(logs: list[Path]) -> dict[str, Any]:
    runs = [parse_log(log) for log in logs]
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": "runtime_log_field_compare",
        "tool_version": TOOL_VERSION,
        "runs": runs,
        "comparisons": compare_runs(runs),
    }
    return report


def write_json(report: dict[str, Any], output: Path) -> None:
    output.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_csv(report: dict[str, Any], output: Path) -> None:
    rows: list[dict[str, Any]] = []

    for run_index, run in enumerate(report["runs"]):
        for sample in sorted(
                run["samples"],
                key=lambda item: (item["source_file"], item["source_line"], item["metric"], item["raw_key"])):
            rows.append({
                "record_type": "sample",
                "pair_index": "",
                "run_index": str(run_index),
                "run_path": run["path"],
                "metric": sample["metric"],
                "value_before": sample["value"],
                "value_after": "",
                "delta": "",
                "delta_percent": "",
                "source_file": sample["source_file"],
                "source_line": sample["source_line"],
                "raw_key": sample["raw_key"],
                "raw_line": sample["raw_line"],
            })

    for pair_index, comparison in enumerate(report["comparisons"]):
        for metric in KNOWN_METRICS:
            delta = comparison["deltas"].get(metric, {})
            if not comparison["state_comparison_eligible"]:
                rows.append({
                    "record_type": "comparison_ineligible",
                    "pair_index": str(pair_index),
                    "run_index": "",
                    "run_path": "",
                    "metric": metric,
                    "value_before": "",
                    "value_after": "",
                    "delta": "",
                    "delta_percent": "",
                    "source_file": "",
                    "source_line": "",
                    "raw_key": "",
                    "raw_line": comparison["ineligible_reason"] or "",
                })
            else:
                rows.append({
                    "record_type": "comparison_delta",
                    "pair_index": str(pair_index),
                    "run_index": "",
                    "run_path": "",
                    "metric": metric,
                    "value_before": delta.get("before", ""),
                    "value_after": delta.get("after", ""),
                    "delta": delta.get("delta", ""),
                    "delta_percent": delta.get("delta_percent", ""),
                    "source_file": "",
                    "source_line": "",
                    "raw_key": "",
                    "raw_line": "",
                })

    fieldnames = [
        "record_type", "pair_index", "run_index", "run_path", "metric",
        "value_before", "value_after", "delta", "delta_percent",
        "source_file", "source_line", "raw_key", "raw_line",
    ]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_markdown(report: dict[str, Any], output: Path) -> None:
    lines = [
        "# Runtime log comparison report",
        "",
        f"Schema version: {report['schema_version']}",
        f"Tool version: {report['tool_version']}",
        "",
        "## Runs",
        "",
        "| Index | Log | Content | Configuration | Camera | Sample count | Unknown lines |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for run_index, run in enumerate(report["runs"]):
        identity = run["identity"]
        lines.append(
            f"| {run_index} | `{run['path']}` | "
            f"`{identity['content_id'] or 'missing'}` | `{identity['configuration_id'] or 'missing'}` | "
            f"`{identity['camera_id'] or 'missing'}` | {len(run['samples'])} | "
            f"{run['unknown_count']} |"
        )

    lines += [
        "",
        "## Per-run metric summary",
        "",
    ]
    for run_index, run in enumerate(report["runs"]):
        lines.append(f"### {run_index}: `{run['path']}`")
        lines.append("")
        for metric in KNOWN_METRICS:
            metric_data = run["metrics"].get(metric, {})
            lines.append(
                f"- {metric}: samples={metric_data.get('samples', 0)} "
                f"min={metric_data.get('min','n/a')} "
                f"mean={metric_data.get('mean','n/a')} "
                f"max={metric_data.get('max','n/a')}"
            )
        lines.append("")

    lines += [
        "## Comparisons",
        "",
    ]
    if not report["comparisons"]:
        lines.append("No comparison pair provided.")
    else:
        for pair_index, comparison in enumerate(report["comparisons"]):
            lines.append(f"### Pair {pair_index}")
            lines.append(
                f"- Before: `{comparison['before']['path']}`"
            )
            lines.append(
                f"- After: `{comparison['after']['path']}`"
            )
            lines.append(
                f"- State comparison eligible: {comparison['state_comparison_eligible']}"
            )
            if comparison["ineligible_reason"]:
                lines.append(
                    f"- Ineligible reason: {comparison['ineligible_reason']}"
                )
            else:
                for metric in KNOWN_METRICS:
                    delta = comparison["deltas"].get(metric, {})
                    delta_percent = "n/a"
                    value = delta.get("delta_percent")
                    if isinstance(value, (int, float)) and not math.isnan(value):
                        delta_percent = f"{value:.3f}"
                    lines.append(
                        f"- {metric}: "
                        f"{delta.get('before', 'n/a')} -> {delta.get('after', 'n/a')} "
                        f"(Δ={delta.get('delta', 'n/a')}, Δ%= {delta_percent})"
                    )
            lines.append("")

    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare runtime log fields with provenance.")
    parser.add_argument("logs", nargs="+", type=Path, metavar="LOG", help="one or more runtime logs")
    parser.add_argument("--json", required=True, dest="json_output", type=Path, help="JSON output file")
    parser.add_argument("--csv", required=True, dest="csv_output", type=Path, help="CSV output file")
    parser.add_argument("--markdown", required=True, dest="markdown_output", type=Path, help="Markdown output file")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = make_report(args.logs)
    write_json(report, args.json_output)
    write_csv(report, args.csv_output)
    write_markdown(report, args.markdown_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
