"""Cross-check the full M13 MIX scan with two original-engine host cycles."""

import argparse
import json
from collections import Counter
from pathlib import Path


KINDS = (
    "linked_script",
    "script_registry_summary",
    "object",
    "observer",
    "cinematic_preset",
    "w3d",
    "w3d_dep",
    "inventory_summary",
    "preset_summary",
    "w3d_summary",
)


def require_linked_scripts(scan: dict, linked_scripts: set[str]) -> set[str]:
    # Text-only attachment lists omitted all of Area 2 and its helper owners.
    # Refuse old inventories instead of silently accepting partial coverage.
    dependencies = scan.get("script_dependency_inventory")
    if not dependencies or dependencies["unresolved_literal_scripts"]:
        raise ValueError("M13 requires a complete source script dependency inventory")
    required = {row["name"].lower() for row in dependencies["required_scripts"]}
    required.update(name.lower() for name in scan["text_inventory"]["referenced_scripts"])
    missing = sorted(required - {name.lower() for name in linked_scripts})
    if missing:
        raise ValueError(f"M13 script factories absent from executable: {missing}")
    return required


def runtime_cycles(path: Path) -> list[dict[str, list[list[str]]]]:
    cycles = []
    current = {kind: [] for kind in KINDS}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split("\t")
        if not parts[0].startswith("m13."):
            continue
        kind = parts[0][4:]
        if kind not in current:
            continue
        current[kind].append(parts[1:])
        if kind == "w3d_summary":
            cycles.append(current)
            current = {item: [] for item in KINDS}
    if any(current.values()):
        raise ValueError("incomplete M13 runtime inventory cycle")
    return cycles


def summarize(scan: dict, cycles: list[dict[str, list[list[str]]]]) -> dict:
    if len(cycles) != 2:
        raise ValueError(f"expected two host cycles, got {len(cycles)}")
    first, second = cycles
    for kind in KINDS:
        left = [tuple(row) for row in first[kind]]
        right = [tuple(row) for row in second[kind]]
        if kind == "object":
            def object_key(row: tuple[str, ...]) -> tuple[str, ...]:
                return row if int(row[0]) < 1_000_000_000 else ("dynamic",) + row[1:]
            left = [object_key(row) for row in left]
            right = [object_key(row) for row in right]
        if kind == "observer":
            def observer_key(row: tuple[str, ...]) -> tuple[str, str]:
                owner = row[0] if int(row[0]) < 1_000_000_000 else "dynamic"
                return owner, row[2]
            left = [observer_key(row) for row in left]
            right = [observer_key(row) for row in right]
        if Counter(left) != Counter(right):
            raise ValueError(f"M13 {kind} inventory differs across host cycles")

    entries = scan["archive_inventory"]["entries"]
    archive_w3d = {entry["name"].lower() for entry in entries
                   if entry["suffix"].lower() == ".w3d"}
    scanned_w3d = {row[0].lower() for row in first["w3d"]}
    if not archive_w3d <= scanned_w3d:
        raise ValueError("original W3D scanner missed an M13 archive entry")
    level_assets = scan["level_asset_dependencies"]["files"]
    level_w3d = {name.lower() for name in level_assets
                 if name.lower().endswith(".w3d") and name.lower() != ".w3d"}
    if not level_w3d <= scanned_w3d:
        raise ValueError("original W3D scanner missed an M13.dep preload name")
    presets = {name.lower() for name in
               scan["text_inventory"]["dependencies"]["real_object_presets"]}
    resolved_presets = {row[0].lower() for row in first["cinematic_preset"]}
    if presets != resolved_presets:
        raise ValueError("cinematic preset census differs from all-text scan")
    if any(row[1] == "0" for row in first["cinematic_preset"]):
        raise ValueError("M13 cinematic preset missing from original definitions")
    linked_scripts = {row[0].lower() for row in first["linked_script"]}
    required_scripts = require_linked_scripts(scan, linked_scripts)
    if not first["script_registry_summary"] or len(first["linked_script"]) != int(first["script_registry_summary"][0][0]):
        raise ValueError("M13 script registry summary disagrees with linked factories")
    if len(first["object"]) != int(first["inventory_summary"][0][0]):
        raise ValueError("M13 object summary disagrees with object records")
    if len(first["observer"]) != int(first["inventory_summary"][0][2]):
        raise ValueError("M13 observer summary disagrees with observer records")

    dependencies = first["w3d_dep"]
    dependency_status = Counter(row[2] for row in dependencies)
    return {
        "schema_version": 1,
        "archive_entry_count": len(entries),
        "archive_suffix_counts": scan["archive_inventory"]["suffix_counts"],
        "level_asset_dependency_records": len(level_assets),
        "level_asset_unique_names": len({name.lower() for name in level_assets}),
        "level_asset_suffix_counts": scan["level_asset_dependencies"]["suffix_counts"],
        "level_asset_placeholder_records": sum(name.lower() == ".w3d" for name in level_assets),
        "cinematic_text_files": scan["text_inventory"]["text_file_count"],
        "cinematic_commands": scan["text_inventory"]["command_counts"],
        "referenced_scripts": len(scan["text_inventory"]["referenced_scripts"]),
        "scripts_without_source_name_match": scan["gaps"]["data_scripts_without_source_declare_name_match"],
        "initialized_objects": len(first["object"]),
        "initialized_physical_objects": int(first["inventory_summary"][0][1]),
        "attached_observers": len(first["observer"]),
        "linked_script_factories": len(linked_scripts),
        "required_script_factories_resolved": len(required_scripts),
        "cinematic_presets_resolved": len(resolved_presets),
        "w3d_archive_files": len(archive_w3d),
        "w3d_dependency_closure": len(scanned_w3d),
        "w3d_dependency_edges": len(dependencies),
        "w3d_dependency_status": dict(dependency_status),
        "unopenable_w3d_names": sorted({row[0] for row in first["w3d"]
                                         if row[1] == "0"}),
        "unresolved_w3d_references": [row[:2] for row in dependencies
                                      if row[2] == "unresolved"],
        "two_cycle_agreement": True,
        "limits": [item for item in scan["limits"]
                   if not item.startswith("W3D internal texture/material references")]
        + [
            "Original W3D dependency scanning covers its supported chunks and file references; it does not prove every runtime material or texture lookup.",
            "DDB preset transitive references beyond loaded objects and cinematic preset names remain to be inventoried.",
            "Runtime object census is after 120 host frames; later scripted spawns and mission transitions are not covered.",
            "Raw W3D dependency availability is not visual rendering verification.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scan", type=Path)
    parser.add_argument("runtime_log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.scan.read_text(encoding="utf-8")),
                       runtime_cycles(args.runtime_log))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
