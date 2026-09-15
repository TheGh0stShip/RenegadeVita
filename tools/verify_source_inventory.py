"""Check reported source identities against the source manifests, not fixed totals."""
import argparse
import json
from pathlib import Path

if __package__:
    from .generate_integration_report import (
        STAGED_ORIGINAL_OWNER_SOURCES, read_native_source_sets, read_world_manifest,
    )
else:
    from generate_integration_report import (
        STAGED_ORIGINAL_OWNER_SOURCES, read_native_source_sets, read_world_manifest,
    )


def verify_report(root, report, milestone):
    if report.get("milestone") != milestone:
        raise ValueError("Source inventory candidate identity mismatch")
    native = read_native_source_sets(root)
    selections = (
        ("original_translation_units", "original_source_files_compiled", read_world_manifest(root)),
        ("staged_original_owner_paths", "staged_original_owner_files",
         sorted(STAGED_ORIGINAL_OWNER_SOURCES.values())),
        ("vita_translation_units", "vita_platform_renderer_validation_files",
         native["RENEGADE_A30_PORT_SOURCES"]),
        ("a4_frontend_boundary_paths", "a4_frontend_boundary_files",
         native["RENEGADE_A4_FRONTEND_PORT_SOURCES"]),
    )
    for paths_key, count_key, expected in selections:
        if report.get(paths_key) != expected or report.get(count_key) != len(expected):
            raise ValueError(f"Source inventory mismatch: {paths_key} / {count_key}")
    return tuple(len(expected) for _, _, expected in selections)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--milestone", required=True)
    args = parser.parse_args()
    counts = verify_report(args.root, json.loads(args.report.read_text()), args.milestone)
    print(*counts)


if __name__ == "__main__":
    main()
