#!/usr/bin/env python3
"""Compare observed original-game runtime evidence with named route milestones.

This reports what a bounded session did and did not observe. An unobserved
milestone is never evidence that the retail game or source implementation is
missing it. Runtime sidecars must belong to one candidate and one map/session.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.validate_campaign_flight_bundle import BundleError, validate_bundle
from tools.analyze_script_lookups import analyze_lookups


def read_events(path: Path, candidate: str, archive: str) -> list[dict]:
    events = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path.name}:{line_number}: invalid JSON") from error
        if event.get("candidate") != candidate or event.get("archive", "").lower() != archive.lower():
            raise ValueError(f"{path.name}:{line_number}: mixed candidate or archive")
        events.append(event)
    return events


def read_progress(log: Path, candidate: str) -> list[dict]:
    text = log.read_text(encoding="utf-8", errors="replace")
    identities = re.findall(r"Runtime identity:.*?candidate=([^\s,]+)", text)
    if identities and any(value != candidate for value in identities):
        raise ValueError(f"{log.name}: conflicting candidate identity")
    rows = []
    pattern = re.compile(
        r"A3\.5 mission progress: frame=(\d+).*?objectives=(\d+) "
        r"status_1_6=(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+) "
        r"active_conversations=(\d+) active=([^ ]+)"
    )
    for match in pattern.finditer(text):
        rows.append({"frame": int(match[1]), "objectives": int(match[2]),
                     "objective_status": [int(match[i]) for i in range(3, 9)],
                     "active_conversations": int(match[9]), "conversation": match[10]})
    return rows


def make_report(bundle: Path, *, expected_candidate: str, archive: str,
                runtime_log: Path | None = None, reference: Path | None = None) -> dict:
    plain_summary = bundle / "campaign-flight-summary.json"
    named_prefix = f"{archive.rsplit('.', 1)[0].lower()}-"
    named_summary = bundle / f"{named_prefix}campaign-flight-summary.json"
    if plain_summary.exists():
        try:
            plain_archive = json.loads(plain_summary.read_text(encoding="utf-8")).get("archive", "")
        except (OSError, json.JSONDecodeError):
            plain_archive = ""
    else:
        plain_archive = ""
    prefix = "" if plain_archive.lower() == archive.lower() or not named_summary.exists() else named_prefix
    summary_path = bundle / f"{prefix}campaign-flight-summary.json"
    # Flight sidecars are sometimes retained as one session per archive with
    # prefixed filenames. Normalize those without copying or rewriting evidence.
    if summary_path.name != "campaign-flight-summary.json":
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        from tempfile import TemporaryDirectory
        temporary = TemporaryDirectory(prefix="renegade-gap-analysis-")
        import atexit
        atexit.register(temporary.cleanup)
        normalized = Path(temporary.name)
        for source_name, target_name in (
            (summary_path.name, "campaign-flight-summary.json"),
            (f"{prefix}campaign-flight-events.jsonl", "campaign-flight-events.jsonl"),
            (f"{prefix}campaign-flight-frames.csv", "campaign-flight-frames.csv"),
            (f"{prefix}campaign-flight-log-tail.txt", "campaign-flight-log-tail.txt"),
        ):
            source = bundle / source_name
            if source.exists():
                (normalized / target_name).write_bytes(source.read_bytes())
        bundle_for_validation = normalized
    else:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        from tempfile import TemporaryDirectory
        temporary = TemporaryDirectory(prefix="renegade-gap-analysis-")
        import atexit
        atexit.register(temporary.cleanup)
        bundle_for_validation = Path(temporary.name)
        for source_name in ("campaign-flight-summary.json", "campaign-flight-events.jsonl",
                            "campaign-flight-frames.csv", "campaign-flight-log-tail.txt"):
            source = bundle / source_name
            if source.exists():
                (bundle_for_validation / source_name).write_bytes(source.read_bytes())
        tail = bundle_for_validation / "campaign-flight-log-tail.txt"
        if not tail.exists():
            tail.write_text("", encoding="utf-8")
    try:
        timing = validate_bundle(bundle_for_validation, expected_candidate)
    except BundleError as error:
        raise ValueError(str(error)) from error
    if summary.get("archive", "").lower() != archive.lower():
        raise ValueError(f"archive mismatch: expected {archive}, summary says {summary.get('archive')}")
    events = read_events(bundle_for_validation / "campaign-flight-events.jsonl", expected_candidate, archive)
    frame_rows = []
    with (bundle_for_validation / "campaign-flight-frames.csv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("candidate") != expected_candidate or row.get("archive", "").lower() != archive.lower():
                raise ValueError("frame CSV contains mixed candidate or archive")
            frame_rows.append(row)

    mission = summary.get("mission", {})
    sidecar_conversations = set()
    if mission.get("conversation"):
        sidecar_conversations.add(str(mission["conversation"]))
    progress_rows = []
    if runtime_log:
        progress_rows = read_progress(runtime_log, expected_candidate)
    log_conversations = sorted({row["conversation"] for row in progress_rows
                                if row["conversation"] not in ("none", "")})

    route = json.loads(reference.read_text(encoding="utf-8")) if reference else None
    milestones = []
    if route:
        for segment in route.get("segments", []):
            # Runtime route markers are deliberately explicit. Current flight
            # recorder does not record these semantic markers, so only report
            # a match if a future event names the segment exactly.
            hits = [event for event in events if event.get("category") == "route"
                    and event.get("name") == segment["id"]]
            milestones.append({"id": segment["id"], "behavior": segment["behavior"],
                               "source_owners": segment.get("owners", []),
                               "status": "observed" if hits else "not_observed",
                               "evidence_frames": [event.get("frame") for event in hits]})
    elif archive.lower() == "m01.mix":
        opening = "M01_Press_F1_Conversation" in sidecar_conversations
        milestones.append({"id": "opening_conversation", "status": "observed" if opening else "not_observed",
                           "evidence_source": "runtime conversation snapshot"})
        milestones.append({"id": "subsequent_campaign_route", "status": "not_observed",
                           "evidence_source": "no explicit route-segment markers in recorder"})

    runtime_log_summary = None
    if runtime_log:
        log_text = runtime_log.read_text(encoding="utf-8", errors="replace")
        completion = re.findall(
            r"A3\.5 mission completion: original Combat event observed success=(\d+) frame=(\d+)",
            log_text)
        runtime_log_summary = {
            "candidate_verified": True,
            "matching_archive_mentions": len(re.findall(re.escape(archive), log_text, re.IGNORECASE)),
            "mission_completion_markers": [
                {"success": int(success), "frame": int(frame)}
                for success, frame in completion],
            "note": "Persistent runtime logs can contain multiple sessions; these markers are not merged with the sidecar session.",
        }

    return {
        "schema_version": 1,
        "candidate": expected_candidate,
        "archive": archive,
        "evidence_class": "physical runtime sidecars and/or returned runtime log",
        "scope": {"first_frame": timing["first_frame"], "last_frame": timing["last_frame"],
                  "frames": timing["frames"], "events": timing["events"],
                  "session_reason": summary.get("reason"), "load_source": summary.get("load_source")},
        "observed": {"mission_snapshots_in_log": len(progress_rows),
                     "flight_sidecar_conversations": sorted(sidecar_conversations),
                     "candidate_log_conversations_not_session_merged": log_conversations,
                     "objective_count_max": max((row["objectives"] for row in progress_rows),
                                                 default=mission.get("objective_count")),
                     "sidecar_mission_snapshot": mission if mission else None},
        "candidate_log_observations_not_session_merged": runtime_log_summary,
        "lookup_observations": analyze_lookups(summary, expected_candidate=expected_candidate,
                                              archive=archive),
        "route_milestones": milestones,
        "unobserved_route_milestones": [row["id"] for row in milestones
                                        if row["status"] == "not_observed"],
        "limits": ["Not observed means this bounded trace did not prove the milestone; it does not prove the feature is missing.",
                   "Source selection, linked factories, retail attachments, rendering, audio, and visual correctness require separate evidence.",
                   "A save reload proves only the restored checkpoint and actions captured in that session."]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="directory containing one flight sidecar bundle")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--runtime-log", type=Path)
    parser.add_argument("--reference", type=Path, help="optional JSON with named route segments")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = make_report(args.bundle, expected_candidate=args.candidate,
                             archive=args.archive, runtime_log=args.runtime_log,
                             reference=args.reference)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
