"""Inventory capture candidates without copying private files into publication.

Pass LABEL=PATH roots explicitly. Output paths are relative to those roots;
directory build numbers are candidate attribution, not runtime verification.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import subprocess


def inventory(roots):
    entries = []
    scans = []
    for label, root in roots:
        result = subprocess.run(
            ["rg", "--files", "--hidden", "--no-ignore", str(root),
             "-g", "*.png", "-g", "*.bmp", "-g", "*.jpg", "-g", "*.jpeg",
             "-g", "!**/.git/**", "-g", "!**/node_modules/**"],
            capture_output=True, text=True, check=False,
        )
        scans.append({"root": label, "exists": root.exists(), "scan_returncode": result.returncode})
        for raw in sorted(result.stdout.splitlines()):
            path = Path(raw)
            relative = path.relative_to(root).as_posix()
            low = relative.lower()
            if any(part in low for part in (
                "/sce_sys/", "/vs0/", "/retail/", "/retail-pc/", "/.git/",
                "vita3k-src", "/dependencies/", "/_deps/", "/upstream/",
                "/tt-reference/", "/reference/", "/vendor/", "/external/",
            )):
                continue
            builds = sorted(set(int(n) for n in re.findall(r"dev(\d+)(?!\d)", low)))
            capture = any(word in low for word in (
                "capture", "screenshot", "visible-", "window-", "frame", "vita logs",
                "emulator", "device-evidence", "vita3k/", "pstv/",
            ))
            if not capture:
                continue
            attribution = "directory or filename; requires review"
            state = path.parent / "state.json"
            if state.is_file():
                try:
                    metadata = json.loads(state.read_text())
                    matched = re.search(r"A3\.5-dev(\d+)", str(metadata.get("build_label", metadata.get("milestone", ""))))
                    if matched:
                        builds = [int(matched.group(1))]
                        attribution = "capture state.json build label"
                except (ValueError, OSError):
                    attribution = "unreadable capture metadata; requires review"
            entries.append({"root": label, "path": relative, "candidate_builds": builds,
                            "attribution": attribution,
                            "size": path.stat().st_size})
    return {"scans": scans, "captures": entries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", default=[], help="LABEL=PATH")
    parser.add_argument("--summary-from", type=Path, action="append", default=[], help="Combine local inventories into a path-free public coverage summary")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.summary_from:
        inventories = [json.loads(path.read_text()) for path in args.summary_from]
        entries = [entry for data in inventories for entry in data["captures"]]
        counts = collections.Counter(build for entry in entries for build in entry["candidate_builds"])
        result = {"schema_version": 1, "audit_date": "2026-09-27",
                  "policy": "Candidate file counts include duplicates and annotated copies; selected images are separately reviewed. No absolute source paths or private metadata are published.",
                  "scans": [scan for data in inventories for scan in data["scans"]],
                  "candidate_file_counts_by_build": dict(sorted(counts.items())),
                  "unassigned_candidate_files": sum(not entry["candidate_builds"] for entry in entries)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(f"Coverage summary: {len(counts)} builds")
        return
    if not args.root:
        parser.error("provide --root or --summary-from")
    roots = [(label, Path(path).resolve()) for label, path in (value.split("=", 1) for value in args.root)]
    result = inventory(roots)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    counts = collections.Counter(build for entry in result["captures"] for build in entry["candidate_builds"])
    print(json.dumps({"scans": result["scans"], "capture_candidates": len(result["captures"]),
                      "by_candidate_build": dict(sorted(counts.items()))}, indent=2))


if __name__ == "__main__":
    main()
