#!/usr/bin/env python3
"""Inventory original campaign script owners and compare them with static-link inputs.

This is a source-only audit: it uses original source files and Scripts.dsp, not
retail mission archives, and makes no claim that a script ran on the device.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.check_m13_script_coverage import DECLARE, without_comments

MISSIONS = [
    ("M00 tutorial", "Mission00.cpp", ("MTU_", "MSK_")),
    ("Mission 0 / M13", "MissionX0.cpp", ("MX0_",)),
    *[(f"Mission {i:02}", f"Mission{i:02}.cpp", (f"M{i:02}_",)) for i in range(1, 8)],
    ("Mission 08", "mission08.cpp", ("M08_",)),
    *[(f"Mission {i:02}", f"Mission{i:02}.cpp", (f"M{i:02}_",)) for i in range(9, 12)],
]
EXPECTED_DECLARATIONS = {
    "Mission00.cpp": 22, "MissionX0.cpp": 31, "Mission01.cpp": 289,
    "Mission02.cpp": 26, "Mission03.cpp": 86, "Mission04.cpp": 138,
    "Mission05.cpp": 111, "Mission06.cpp": 85, "Mission07.cpp": 122,
    "mission08.cpp": 114, "Mission09.cpp": 96, "Mission10.cpp": 79,
    "Mission11.cpp": 171,
}
COMMAND_CALL = re.compile(r"\bCommands\s*->\s*(\w+)\s*\(")
FIND_OBJECT = re.compile(r"\bCommands\s*->\s*Find_Object\s*\(")
FIND_OBJECT_LITERAL = re.compile(r"\bCommands\s*->\s*Find_Object\s*\(\s*(\d+)")
REFERENCE_FILE = re.compile(r'"([^"\n]+\.(?:txt|mp3))"', re.IGNORECASE)


def source_metrics(path: Path) -> dict:
    raw = path.read_text(encoding="latin1")
    code = without_comments(raw)
    declarations = [match[1] for match in DECLARE.finditer(code)]
    calls = COMMAND_CALL.findall(code)
    literal_ids = sorted({int(value) for value in FIND_OBJECT_LITERAL.findall(code)})
    references: dict[str, set[str]] = {"txt": set(), "mp3": set()}
    for value in REFERENCE_FILE.findall(code):
        suffix = value.rsplit(".", 1)[-1].lower()
        references[suffix].add(value)
    return {
        "source": path.name,
        "source_lines": raw.count("\n"),
        "declared_scripts": len(declarations),
        "script_names": declarations,
        "command_call_count": len(calls),
        "commands_used": sorted(set(calls)),
        "find_object_call_count": len(FIND_OBJECT.findall(code)),
        "numeric_find_object_ids": literal_ids,
        "numeric_find_object_id_count": len(literal_ids),
        "cinematic_control_files": sorted(references["txt"]),
        "cinematic_control_file_count": len(references["txt"]),
        "music_files": sorted(references["mp3"]),
        "music_file_count": len(references["mp3"]),
    }


def dsp_sources(path: Path) -> list[str]:
    text = path.read_text(encoding="latin1")
    return sorted(set(re.findall(r"^SOURCE=\.\\([\w.-]+\.cpp)\s*$", text,
                                 re.MULTILINE | re.IGNORECASE)))


def audit(root: Path = ROOT) -> dict:
    source_root = root / "upstream/CnC_Renegade/Code/Scripts"
    cmake_source = (root / "cmake/RenegadeScriptSources.cmake").read_text()
    native_cmake = (root / "CMakeLists.txt").read_text()
    host_cmake = (root / "tools/host_a30_definitions/CMakeLists.txt").read_text()
    rows = []
    all_commands: set[str] = set()
    total_find_calls = 0
    for area, filename, prefixes in MISSIONS:
        metrics = source_metrics(source_root / filename)
        metrics["area"] = area
        metrics["script_prefixes"] = list(prefixes)
        metrics["selected_by_dsp_static_source_function"] = (
            "DLLmain.cpp" not in filename and "RENEGADE_SCRIPT_DSP_SOURCES" in native_cmake
            and "RENEGADE_SCRIPT_DSP_SOURCES" in host_cmake
            and "DLLmain.cpp" in cmake_source and "continue()" in cmake_source)
        metrics["expected_declaration_count"] = EXPECTED_DECLARATIONS[filename]
        metrics["declaration_count_matches_reference"] = (
            metrics["declared_scripts"] == EXPECTED_DECLARATIONS[filename])
        all_commands.update(metrics["commands_used"])
        total_find_calls += metrics["find_object_call_count"]
        rows.append(metrics)

    dsp = dsp_sources(source_root / "Scripts.dsp")
    all_source_units = sorted(path.name for path in source_root.glob("*.cpp"))
    outside_dsp = sorted(set(all_source_units) - set(dsp))
    command_header = (root / "upstream/CnC_Renegade/Code/Combat/scriptcommands.h").read_text(
        encoding="latin1")
    command_table = sorted(set(re.findall(r"\(\s*\*\s*(\w+)\s*\)", command_header)))
    missing_stage_files = sorted(name for name in dsp if name != "DLLmain.cpp"
                                 and not (root / "staging/scripts" / name).is_file())
    expected_campaign_names = {row[1] for row in MISSIONS}
    native_hooks = ("renegade_collect_script_dsp_sources(" in native_cmake
                    and "${RENEGADE_SCRIPT_DSP_SOURCES}" in native_cmake)
    host_hooks = ("renegade_collect_script_dsp_sources(" in host_cmake
                  and "${RENEGADE_SCRIPT_DSP_SOURCES}" in host_cmake)
    return {
        "schema_version": 1,
        "evidence_class": "original source and build-manifest static analysis",
        "campaign_mission_source_count": len(rows),
        "campaign_source_lines": sum(row["source_lines"] for row in rows),
        "declared_script_count": sum(row["declared_scripts"] for row in rows),
        "distinct_script_command_methods_used": len(all_commands),
        "script_command_table_entries": len(command_table),
        "missing_command_table_methods": sorted(set(all_commands) - set(command_table)),
        "find_object_call_count": total_find_calls,
        "original_dsp_source_count": len(dsp),
        "static_original_dsp_source_count": len([name for name in dsp if name != "DLLmain.cpp"]),
        "dllmain_replaced_by_static_provider": (
            "DLLmain.cpp" in dsp and "renegade_script_static_provider.cpp" in native_cmake
            and "renegade_script_static_provider.cpp" in host_cmake),
        "dsp_source_names": dsp,
        "all_script_directory_cpp_count": len(all_source_units),
        "cpp_source_names_outside_dsp": outside_dsp,
        "staged_dsp_source_missing": missing_stage_files,
        "native_target_uses_dsp_manifest": native_hooks,
        "host_target_uses_dsp_manifest": host_hooks,
        "missing_mission_source_units": sorted(
            name for name in expected_campaign_names
            if not (root / "staging/scripts" / name).is_file()),
        "missions": rows,
        "static_source_gate_passed": (
            len(rows) == 13 and all(row["declaration_count_matches_reference"] for row in rows)
            and not set(all_commands) - set(command_table)
            and len(dsp) == 45 and not missing_stage_files
            and native_hooks and host_hooks
            and "DLLmain.cpp" in dsp
            and "renegade_script_static_provider.cpp" in native_cmake
            and "renegade_script_static_provider.cpp" in host_cmake),
        "limits": [
            "Source selection is not proof of successful compilation, linked factory presence, runtime registration, or mission execution.",
            "Level object IDs and retail attachments require matching user-owned retail map data; this audit counts source literals only.",
            "Cinematic and music names are literal source references; level data can introduce additional media and scripts.",
            "The supplied overview reports 3,478 Find_Object calls; this parser counts source expressions after removing comments and should be reconciled if the difference matters.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.root)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(json.dumps({key: result[key] for key in (
            "campaign_mission_source_count", "campaign_source_lines",
            "declared_script_count", "distinct_script_command_methods_used",
            "script_command_table_entries", "find_object_call_count",
            "original_dsp_source_count", "static_original_dsp_source_count",
            "all_script_directory_cpp_count", "cpp_source_names_outside_dsp",
            "missing_mission_source_units", "static_source_gate_passed")},
            indent=2, sort_keys=True))
    else:
        print(payload, end="")
    return 0 if result["static_source_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
