#!/usr/bin/env python3
"""Validate campaign flight-recorder sidecars before profiling their data."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path


class BundleError(ValueError):
    pass


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BundleError(f"{path.name}: invalid JSON: {error}") from error


def validate_bundle(root: Path, expected_candidate: str | None = None) -> dict:
    summary_path = root / "campaign-flight-summary.json"
    frames_path = root / "campaign-flight-frames.csv"
    events_path = root / "campaign-flight-events.jsonl"
    tail_path = root / "campaign-flight-log-tail.txt"
    summary = read_json(summary_path)
    candidate = summary.get("candidate")
    if not isinstance(candidate, str) or not candidate:
        raise BundleError("summary has no candidate identity")
    if expected_candidate and candidate != expected_candidate:
        raise BundleError(
            f"candidate mismatch: expected {expected_candidate}, summary says {candidate}"
        )

    try:
        with frames_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            rows = list(reader)
    except OSError as error:
        raise BundleError(f"{frames_path.name}: {error}") from error
    if not rows:
        raise BundleError("frame sidecar is empty")
    if summary.get("frames_recorded") != len(rows):
        raise BundleError(
            f"summary says {summary.get('frames_recorded')} frames, sidecar has {len(rows)}"
        )
    frame_ids = []
    monotonic = []
    frame_times = []
    render_times = []
    simulation_times = []
    for line, row in enumerate(rows, start=2):
        if row.get("candidate") != candidate:
            raise BundleError(
                f"{frames_path.name}:{line}: candidate {row.get('candidate')!r} "
                f"does not match {candidate!r}"
            )
        try:
            frame_ids.append(int(row["frame"]))
            monotonic.append(int(row["monotonic_us"]))
            frame_times.append(int(row["frame_us"]))
            render_times.append(int(row["render_us"]))
            simulation_times.append(int(row["simulation_us"]))
        except (KeyError, ValueError) as error:
            raise BundleError(f"{frames_path.name}:{line}: invalid timing row") from error
    if any(later <= earlier for earlier, later in zip(frame_ids, frame_ids[1:])):
        raise BundleError("frame numbers are not strictly increasing")
    if any(later <= earlier for earlier, later in zip(monotonic, monotonic[1:])):
        raise BundleError("frame monotonic timestamps are not strictly increasing")

    event_count = 0
    try:
        for line, raw in enumerate(events_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as error:
                raise BundleError(f"{events_path.name}:{line}: invalid JSON") from error
            if event.get("candidate") != candidate:
                raise BundleError(
                    f"{events_path.name}:{line}: candidate {event.get('candidate')!r} "
                    f"does not match {candidate!r}"
                )
            event_count += 1
    except OSError as error:
        raise BundleError(f"{events_path.name}: {error}") from error

    try:
        tail = tail_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise BundleError(f"{tail_path.name}: {error}") from error
    identity_lines = [line for line in tail.splitlines()
                      if "Runtime identity:" in line or "[LIFECYCLE] START" in line]
    if identity_lines and any(candidate not in line for line in identity_lines):
        raise BundleError(f"{tail_path.name}: conflicting runtime identity for {candidate}")
    if summary.get("events_recorded") != event_count:
        raise BundleError(
            f"summary says {summary.get('events_recorded')} events, sidecar has {event_count}"
        )

    def percentile(values: list[int], percent: float) -> int:
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1,
                           int((percent / 100.0) * len(ordered) + 0.999999) - 1))
        return ordered[index]

    return {
        "candidate": candidate,
        "frames": len(rows),
        "events": event_count,
        "frame_us": {
            "median": int(statistics.median(frame_times)),
            "p95": percentile(frame_times, 95),
            "p99": percentile(frame_times, 99),
            "max": max(frame_times),
        },
        "mean_render_us": int(statistics.mean(render_times)),
        "mean_simulation_us": int(statistics.mean(simulation_times)),
        "first_frame": frame_ids[0],
        "last_frame": frame_ids[-1],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--candidate")
    args = parser.parse_args()
    try:
        result = validate_bundle(args.bundle, args.candidate)
    except BundleError as error:
        print(f"flight bundle rejected: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
