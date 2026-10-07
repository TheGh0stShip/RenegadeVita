#!/usr/bin/env python3
"""Compare two RVTB1 tutorial benchmark runs (baseline vs candidate).

Each input is one of:
  * a runtime log (ux0:data/renegade/user/logs/a35-<label>-runtime.log) that
    contains "A4 tutorial-bench:" lines;
  * a summary CSV  (tutorial-bench-<label>-rNN.csv);
  * a frames CSV   (tutorial-bench-<label>-rNN-frames.csv).
A summary CSV automatically uses its sibling -frames.csv when present, so
percentiles are pooled exactly over every measured frame of every pass.
Without raw frames, per-pass statistics are combined by median (worst = max).

Percentiles use the nearest-rank rule of port/platform/renegade_vita_tutorial_bench.h:
rank = ceil(p * n / 100), clamped to 1..n.

A comparison is meaningful only when both runs are valid and every viewpoint
fingerprint matches (same pose and modal MeshClass submission tuple). This
tool never grants acceptance; hardware evidence classes stay separate.

Exit status: 0 comparable, 1 invalid/incomplete input, 2 fingerprint mismatch
(render content or camera changed; explain before trusting the timings).
"""
import argparse
import csv
import json
from pathlib import Path
import re
import statistics
import sys

TIMING_FIELDS = ("p50", "p95", "p99", "worst", "mean")
COUNTER_FIELDS = ("meshes", "vertices", "triangles", "material_passes",
                  "indexed_draws", "indexed_triangles", "texture_binds", "state_changes")
FRAME_FLAG_INVALIDATING = 1 | 2 | 4 | 8


def nearest_rank(ordered, percentile):
    """Mirror of RenegadeVitaTutorialBench::Nearest_Rank (ascending input)."""
    count = len(ordered)
    if count == 0:
        return 0
    rank = (percentile * count + 99) // 100
    rank = min(max(rank, 1), count)
    return ordered[rank - 1]


def rounded_mean(values):
    """Mirror of RenegadeVitaTutorialBench::Mean (round half up)."""
    if not values:
        return 0
    return (sum(values) + len(values) // 2) // len(values)


def distribution(values):
    ordered = sorted(values)
    return {
        "p50": nearest_rank(ordered, 50),
        "p95": nearest_rank(ordered, 95),
        "p99": nearest_rank(ordered, 99),
        "worst": ordered[-1] if ordered else 0,
        "mean": rounded_mean(values),
    }


BENCH_VERSION = 1
FNV_OFFSET = 2166136261
FNV_PRIME = 16777619


def fnv1a_word(value, word):
    """Mirror of Fnv1a_Word: FNV-1a over the word's four little-endian bytes."""
    for shift in (0, 8, 16, 24):
        value ^= (word >> shift) & 0xFF
        value = (value * FNV_PRIME) & 0xFFFFFFFF
    return value


def viewpoint_fingerprint(viewpoint, pose_crc, mode, version=BENCH_VERSION):
    """Mirror of Viewpoint_Fingerprint."""
    value = fnv1a_word(FNV_OFFSET, version)
    value = fnv1a_word(value, viewpoint)
    value = fnv1a_word(value, pose_crc)
    for word in mode:
        value = fnv1a_word(value, word)
    return value


def modal_tuple(tuples):
    """Mirror of Modal_Tuple: most frequent, ties to the smallest tuple."""
    if not tuples:
        return (0, 0, 0, 0), 0
    counts = {}
    for item in tuples:
        counts[item] = counts.get(item, 0) + 1
    best = max(counts.values())
    return min(item for item, count in counts.items() if count == best), best


VIEWPOINT_LINE = re.compile(
    r"A4 tutorial-bench: run=(?P<run>r\d+) pass=(?P<pass>\d+)/(?P<passes>\d+) "
    r"vp=(?P<vp>\d+)/(?P<count>\d+) name=(?P<name>\S+) valid=(?P<valid>\d) "
    r"frames=(?P<frames>\d+) invalid=(?P<invalid>\d+) flags=(?P<flags>[0-9A-F]+) "
    r"interval_us p50/p95/p99/worst/mean=(?P<p50>\d+)/(?P<p95>\d+)/(?P<p99>\d+)/"
    r"(?P<worst>\d+)/(?P<mean>\d+) .*?"
    r"meshes/vertices/triangles/passes=(?P<meshes>\d+)/(?P<vertices>\d+)/"
    r"(?P<triangles>\d+)/(?P<material_passes>\d+) "
    r"idx_draws/idx_tris=(?P<indexed_draws>\d+)/(?P<indexed_triangles>\d+) "
    r"binds/states=(?P<texture_binds>\d+)/(?P<state_changes>\d+) "
    r"mode=(?P<mode_frames>\d+)/\d+ fingerprint=(?P<fingerprint>[0-9A-F]{8}) "
    r"pose=(?P<pose_crc>[0-9A-F]{8})")
START_LINE = re.compile(
    r"A4 tutorial-bench: start v=(?P<version>\d+) run=(?P<run>r\d+) candidate=(?P<candidate>\S+) "
    r".*?source=(?P<source>\w+) first_person=(?P<first_person>\d)")
ABORT_LINE = re.compile(r"A4 tutorial-bench: aborted run=(?P<run>r\d+) .*reason=(?P<reason>\S+)")
SUMMARY_LINE = re.compile(
    r"A4 tutorial-bench: summary v=\d+ run=(?P<run>r\d+) pass=(?P<pass>\d+)/\d+ .*? "
    r"interval_us p50/p95/p99/worst/mean=(?P<p50>\d+)/(?P<p95>\d+)/(?P<p99>\d+)/"
    r"(?P<worst>\d+)/(?P<mean>\d+)")


def parse_log(path, run=None):
    """Return {"candidate", "run", "rows": [...], "aborted": reason|None}."""
    runs = {}
    order = []
    current = None
    for line in Path(path).read_text(errors="replace").splitlines():
        start = START_LINE.search(line)
        if start:
            current = start.group("run") + "@" + str(len(order))
            runs[current] = {"candidate": start.group("candidate"), "run": start.group("run"),
                             "source": start.group("source"),
                             "first_person": int(start.group("first_person")),
                             "version": int(start.group("version")),
                             "rows": [], "route_rows": [], "aborted": None}
            order.append(current)
            continue
        summary = SUMMARY_LINE.search(line)
        if summary and current is not None:
            runs[current]["route_rows"].append(
                {field: int(summary.group(field)) for field in TIMING_FIELDS})
            continue
        match = VIEWPOINT_LINE.search(line)
        if match and current is not None:
            row = {key: match.group(key) for key in ("run", "name", "fingerprint", "pose_crc")}
            for key in ("pass", "passes", "vp", "count", "valid", "frames", "invalid",
                        "mode_frames") + TIMING_FIELDS + COUNTER_FIELDS:
                row[key] = int(match.group(key))
            row["flags"] = int(match.group("flags"), 16)
            runs[current]["rows"].append(row)
            continue
        abort = ABORT_LINE.search(line)
        if abort and current is not None:
            runs[current]["aborted"] = abort.group("reason")
    selected = [key for key in order if run is None or runs[key]["run"] == run]
    if not selected:
        raise ValueError(f"{path}: no tutorial-bench run{' ' + run if run else ''} found")
    return runs[selected[-1]]


def parse_summary_csv(path):
    rows = []
    route_rows = []
    candidate = run = source = aborted = None
    with Path(path).open(newline="") as stream:
        for record in csv.DictReader(stream):
            candidate, run, source = record["candidate"], record["run"], record["source"]
            if record["viewpoint"] == "ALL":
                if record["valid"] != "1":
                    aborted = f"pass {record['pass']} route not valid (aborted or invalid viewpoint)"
                route_rows.append({field: int(record[f"interval_{field}_us"])
                                   for field in TIMING_FIELDS})
                continue
            row = {"name": record["name"], "fingerprint": record["fingerprint"],
                   "pose_crc": record["pose_crc"], "pass": int(record["pass"]),
                   "vp": int(record["viewpoint"]), "valid": int(record["valid"]),
                   "frames": int(record["frames"]), "invalid": int(record["invalid_frames"]),
                   "mode_frames": int(record["mode_frames"]), "flags": int(record["flags"])}
            for field in TIMING_FIELDS:
                row[field] = int(record[f"interval_{field}_us"])
            for field in COUNTER_FIELDS:
                row[field] = int(record[field])
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no viewpoint rows")
    return {"candidate": candidate, "run": run, "source": source, "rows": rows,
            "route_rows": route_rows, "aborted": aborted}


def parse_frames_csv(path):
    """Measured samples keyed by (pass, viewpoint): (interval_us, flags, counters)."""
    frames = {}
    with Path(path).open(newline="") as stream:
        for record in csv.DictReader(stream):
            if record["measured"] != "1":
                continue
            counters = tuple(int(record[field]) for field in COUNTER_FIELDS)
            frames.setdefault((int(record["pass"]), int(record["viewpoint"])), []).append(
                (int(record["interval_us"]), int(record["flags"]), counters))
    return frames


def verify_fingerprints(data):
    """Recompute each summary fingerprint from the raw measured frames."""
    problems = []
    for row in data["rows"]:
        samples = data["frames"].get((row["pass"], row["vp"]))
        if not samples:
            problems.append(f"pass {row['pass']} viewpoint {row['vp']}: no raw frames")
            continue
        mode, frames = modal_tuple([counters[:4] for _, _, counters in samples])
        expected = viewpoint_fingerprint(row["vp"], int(row["pose_crc"], 16), mode)
        if f"{expected:08X}" != row["fingerprint"].upper() or frames != row["mode_frames"]:
            problems.append(f"pass {row['pass']} viewpoint {row['vp']}: summary fingerprint "
                            f"{row['fingerprint']} does not match raw frames ({expected:08X})")
    return problems


def load(path, run=None):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        if path.name.endswith("-frames.csv"):
            summary_path = path.with_name(path.name[:-len("-frames.csv")] + ".csv")
            data = parse_summary_csv(summary_path)
            data["frames"] = parse_frames_csv(path)
        else:
            data = parse_summary_csv(path)
            sibling = path.with_name(path.stem + "-frames.csv")
            data["frames"] = parse_frames_csv(sibling) if sibling.exists() else None
    else:
        data = parse_log(path, run)
        data["frames"] = None
    data["integrity_problems"] = verify_fingerprints(data) if data["frames"] else []
    return combine(data)


def combine(data):
    """One record per viewpoint across passes."""
    by_vp = {}
    for row in data["rows"]:
        by_vp.setdefault(row["vp"], []).append(row)
    viewpoints = {}
    for vp, rows in sorted(by_vp.items()):
        fingerprints = sorted({row["fingerprint"] for row in rows})
        record = {
            "name": rows[0]["name"],
            "passes": len(rows),
            "valid": all(row["valid"] == 1 for row in rows),
            "fingerprints": fingerprints,
            "stable_fingerprint": len(fingerprints) == 1,
            "pose_crcs": sorted({row["pose_crc"] for row in rows}),
            "mode_share": min(row["mode_frames"] / row["frames"] if row["frames"] else 0.0
                              for row in rows),
        }
        samples = [sample for (pass_index, index), values in (data.get("frames") or {}).items()
                   if index == vp for sample in values]
        if samples:
            record.update(distribution([interval for interval, _, _ in samples]))
            record["pooled_frames"] = len(samples)
            if any(flags & FRAME_FLAG_INVALIDATING for _, flags, _ in samples):
                record["valid"] = False
        else:
            for field in ("p50", "p95", "p99", "mean"):
                record[field] = int(statistics.median(row[field] for row in rows))
            record["worst"] = max(row["worst"] for row in rows)
            record["pooled_frames"] = 0
        for field in COUNTER_FIELDS:
            record[field] = int(statistics.median(row[field] for row in rows))
        viewpoints[vp] = record
    data["viewpoints"] = viewpoints
    all_samples = [interval for values in (data.get("frames") or {}).values()
                   for interval, _, _ in values]
    if all_samples:
        data["route"] = distribution(all_samples)
    elif data.get("route_rows"):
        data["route"] = {field: int(statistics.median(row[field] for row in data["route_rows"]))
                         for field in ("p50", "p95", "p99", "mean")}
        data["route"]["worst"] = max(row["worst"] for row in data["route_rows"])
    else:
        data["route"] = None
    return data


def percent(before, after):
    return 0.0 if before == 0 else (after - before) * 100.0 / before


def compare(baseline, candidate, threshold):
    problems = [f"baseline {problem}" for problem in baseline.get("integrity_problems", [])]
    problems += [f"candidate {problem}" for problem in candidate.get("integrity_problems", [])]
    mismatches = []
    rows = []
    if baseline["aborted"] or candidate["aborted"]:
        problems.append(f"aborted run: baseline={baseline['aborted']} candidate={candidate['aborted']}")
    if baseline.get("source") != candidate.get("source"):
        problems.append(f"start source differs: {baseline.get('source')} vs {candidate.get('source')}")
    if baseline.get("version", BENCH_VERSION) != candidate.get("version", BENCH_VERSION):
        problems.append("benchmark route version differs")
    if None not in (baseline.get("first_person"), candidate.get("first_person")) and \
            baseline["first_person"] != candidate["first_person"]:
        problems.append("first/third-person camera mode differs (first-person weapon view "
                        "is part of every fingerprint)")
    if set(baseline["viewpoints"]) != set(candidate["viewpoints"]):
        problems.append("viewpoint sets differ (incomplete run or different route version)")
    for vp in sorted(set(baseline["viewpoints"]) & set(candidate["viewpoints"])):
        a = baseline["viewpoints"][vp]
        b = candidate["viewpoints"][vp]
        if a["name"] != b["name"]:
            problems.append(f"viewpoint {vp} name differs: {a['name']} vs {b['name']}")
        if not a["valid"] or not b["valid"]:
            problems.append(f"viewpoint {vp} {a['name']} invalid (camera/pause/pose/counter disturbance)")
        fingerprint_match = a["stable_fingerprint"] and b["stable_fingerprint"] and \
            a["fingerprints"] == b["fingerprints"]
        if not fingerprint_match:
            mismatches.append(vp)
        deltas = {field: percent(a[field], b[field]) for field in ("p50", "p95", "p99", "worst")}
        verdict = "neutral"
        if deltas["p50"] <= -threshold and deltas["p95"] <= 0.0:
            verdict = "faster"
        if deltas["p50"] >= threshold or deltas["p95"] >= threshold:
            verdict = "slower"
        rows.append({"vp": vp, "name": a["name"], "fingerprint_match": fingerprint_match,
                     "baseline": {f: a[f] for f in TIMING_FIELDS},
                     "candidate": {f: b[f] for f in TIMING_FIELDS},
                     "delta_percent": deltas, "verdict": verdict,
                     "meshes": (a["meshes"], b["meshes"]),
                     "triangles": (a["triangles"], b["triangles"]),
                     "mode_share": (round(a["mode_share"], 3), round(b["mode_share"], 3))})
    route = None
    if baseline.get("route") and candidate.get("route"):
        route = {"baseline": baseline["route"], "candidate": candidate["route"],
                 "delta_percent": {field: percent(baseline["route"][field], candidate["route"][field])
                                   for field in ("p50", "p95", "p99", "worst")}}
    status = 1 if problems else (2 if mismatches else 0)
    return {"status": status, "problems": problems, "fingerprint_mismatches": mismatches,
            "route": route,
            "baseline": {"candidate": baseline["candidate"], "run": baseline["run"]},
            "candidate": {"candidate": candidate["candidate"], "run": candidate["run"]},
            "threshold_percent": threshold, "rows": rows}


def render(result):
    lines = [f"baseline {result['baseline']['candidate']} {result['baseline']['run']}  vs  "
             f"candidate {result['candidate']['candidate']} {result['candidate']['run']}",
             f"{'vp':>2} {'name':<26} {'fp':<4} {'p50 us':>15} {'p95 us':>15} {'p99 us':>15} "
             f"{'worst us':>15} verdict"]
    for row in result["rows"]:
        cells = []
        for field in ("p50", "p95", "p99", "worst"):
            cells.append(f"{row['baseline'][field]:>6}->{row['candidate'][field]:<6}"
                         f"{row['delta_percent'][field]:+.0f}%")
        lines.append(f"{row['vp']:>2} {row['name']:<26} {'ok' if row['fingerprint_match'] else 'DIFF':<4} "
                     + " ".join(f"{cell:>15}" for cell in cells) + f" {row['verdict']}")
    if result.get("route"):
        route = result["route"]
        cells = [f"{route['baseline'][field]:>6}->{route['candidate'][field]:<6}"
                 f"{route['delta_percent'][field]:+.0f}%" for field in ("p50", "p95", "p99", "worst")]
        lines.append(f"{'':>2} {'ROUTE (all measured frames)':<26} {'':<4} " +
                     " ".join(f"{cell:>15}" for cell in cells))
    for problem in result["problems"]:
        lines.append(f"PROBLEM: {problem}")
    if result["fingerprint_mismatches"]:
        lines.append("FINGERPRINT MISMATCH at viewpoints " +
                     ",".join(str(vp) for vp in result["fingerprint_mismatches"]) +
                     ": rendered content or pose changed; timings are not like-for-like")
    lines.append(["COMPARABLE", "INVALID", "FINGERPRINT-MISMATCH"][result["status"]] +
                 " (unmeasured until both runs are physical-Vita evidence)")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("baseline")
    parser.add_argument("candidate")
    parser.add_argument("--baseline-run", help="rNN to select from a runtime log")
    parser.add_argument("--candidate-run", help="rNN to select from a runtime log")
    parser.add_argument("--threshold", type=float, default=3.0,
                        help="percent change in p50/p95 treated as faster/slower (default 3)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = parser.parse_args(argv)
    try:
        baseline = load(args.baseline, args.baseline_run)
        candidate = load(args.candidate, args.candidate_run)
    except (OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    result = compare(baseline, candidate, args.threshold)
    print(json.dumps(result, indent=2) if args.json else render(result))
    return result["status"]


if __name__ == "__main__":
    sys.exit(main())
