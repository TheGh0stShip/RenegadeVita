#!/usr/bin/env python3
"""Compare retained, matching M00 benchmark windows; never grant acceptance."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


IDENTITIES = (
    "self_sha256", "retail_sha256", "checkpoint_sha256", "route_sha256",
    "emulator_sha256", "emulator_config_sha256",
)
TIMINGS = (
    "ordinary_frame_us", "input_us", "game_update_us", "physics_us",
    "camera_us", "visibility_us", "render_us", "present_us", "housekeeping_us",
)
WORK = ("meshes", "vertices", "triangles", "indexed_draws", "indexed_triangles")
MEMORY = (
    "user_free_low_water", "cdram_free_low_water", "phycont_free_low_water",
    "vitagl_ram_free_low_water", "vitagl_vram_free_low_water",
    "vitagl_slow_free_low_water", "vitagl_all_free_low_water",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def integer(value, field):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]+", value),
            f"Invalid nonnegative integer: {field}")
    return int(value)


def distribution(values):
    ordered = sorted(values)
    return {
        "samples": len(values),
        "median_us": statistics.median(ordered),
        "p95_us": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "p99_us": ordered[math.ceil(len(ordered) * 0.99) - 1],
        "worst_us": ordered[-1],
        "mean_us": statistics.mean(ordered),
    }


def load_run(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema") == "renegade-render-work-run-v1",
            "Unsupported benchmark manifest schema")
    for field in IDENTITIES + ("csv_sha256",):
        value = manifest.get(field)
        require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value),
                f"Missing or invalid identity: {field}")
    require(type(manifest.get("mode")) is int and 0 <= manifest["mode"] <= 15,
            "Mode must be an integer from 0 through 15")
    for field in ("development_input_disabled", "compiler_idle"):
        require(manifest.get(field) is True, f"Missing run attestation: {field}")
    for field in ("start_frame", "end_frame", "warmup_frames"):
        require(type(manifest.get(field)) is int and manifest[field] >= 0,
                f"Invalid window field: {field}")
    require(manifest["end_frame"] > manifest["start_frame"] >= manifest["warmup_frames"],
            "Window must follow declared warmup and contain multiple frames")
    require(isinstance(manifest.get("csv"), str), "Missing CSV path")
    csv_path = manifest_path.parent / manifest["csv"]
    require(digest(csv_path) == manifest["csv_sha256"], "CSV hash mismatch")
    required = set(TIMINGS + WORK + MEMORY + (
        "frame", "frame_us", "capture_readback_us", "benchmark_active",
        "benchmark_point", "backend_errors", "rejected",
    ))
    rows = []
    previous_frame = -1
    with csv_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        require(required.issubset(reader.fieldnames or []), "Incomplete telemetry columns")
        for raw in reader:
            frame = integer(raw.get("frame"), "frame")
            require(frame > previous_frame, "Duplicate, unordered or restarted frame stream")
            previous_frame = frame
            if not manifest["start_frame"] <= frame <= manifest["end_frame"]:
                continue
            row = {key: integer(raw.get(key), key) for key in required}
            require(row["benchmark_active"] == 1, "Window includes non-benchmark frames")
            require(row["capture_readback_us"] == 0, "Window includes capture readback")
            require(row["ordinary_frame_us"] > 0, "Missing ordinary frame duration")
            require(row["backend_errors"] == 0 and row["rejected"] == 0,
                    "Renderer errors/rejections prohibit a clean comparison")
            rows.append(row)
    expected = manifest["end_frame"] - manifest["start_frame"] + 1
    require(len(rows) == expected, "Missing frames or incomplete benchmark window")
    require(len(rows) >= 120, "At least 120 consecutive benchmark frames are required")
    return manifest, rows, {
        "manifest_sha256": digest(manifest_path),
        "csv_sha256": manifest["csv_sha256"],
        "mode": manifest["mode"],
        "timings": {key: distribution([row[key] for row in rows]) for key in TIMINGS},
        "wall_frame": distribution([row["frame_us"] for row in rows]),
        "memory_free_low_water_bytes": {
            key: min(row[key] for row in rows) for key in MEMORY
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, before, baseline_report = load_run(args.baseline)
    candidate, after, candidate_report = load_run(args.candidate)
    require(baseline["mode"] == 0, "Baseline must select mode zero")
    for key in IDENTITIES + ("start_frame", "end_frame", "warmup_frames"):
        require(baseline[key] == candidate[key], f"Incomparable run identity/window: {key}")
    require([row["benchmark_point"] for row in before] ==
            [row["benchmark_point"] for row in after], "Benchmark point sequence differs")
    # Work columns may be cumulative counters. Exact frame-by-frame equality is
    # intentionally conservative: a changed visibility/workload needs investigation.
    work_matches = all(
        all(left[key] == right[key] for key in WORK)
        for left, right in zip(before, after)
    )
    report = {
        "schema": "renegade-render-work-comparison-v1",
        "status": "COMPARABLE_UNASSESSED" if work_matches else "WORKLOAD_MISMATCH",
        "baseline": baseline_report,
        "candidate": candidate_report,
        "workload_counters_match": work_matches,
        "ordinary_frame_change_percent": {
            key: 100 * (candidate_report["timings"]["ordinary_frame_us"][key] /
                        baseline_report["timings"]["ordinary_frame_us"][key] - 1)
            for key in ("median_us", "p95_us", "p99_us", "worst_us")
        } if work_matches else None,
        "visual_acceptance": "UNASSESSED",
        "physical_acceptance": False,
        "adoption": "DEFERRED",
        "limitations": [
            "Manifest identities and run controls require retained external evidence.",
            "Matching counters do not prove identical world state or visual correctness.",
            "File I/O and shader compilation may remain in ordinary frame costs.",
            "Repeat baseline and candidate runs before interpreting timing differences.",
        ],
    }
    # Exclusive creation preserves earlier evidence, including failed comparisons.
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(report["status"])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        raise SystemExit(f"Comparison refused: {error}")
