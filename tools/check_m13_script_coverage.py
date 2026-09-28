"""Check M13 script source selection; this does not establish runtime behavior.

Seed every original MX0/DAK_MX0 registration, not only cinematic text names.
Follow literal Commands->Attach_Script dependencies to their original owners.
Dynamic names and retail preset attachments still need runtime reconciliation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
DECLARE = re.compile(r'\bDECLARE_SCRIPT\s*\(\s*(\w+)\s*,')
ATTACH = re.compile(r'Commands\s*->\s*Attach_Script\s*\([^,;]+,\s*"(\w+)"')


def without_comments(text: str) -> str:
    return TOKEN.sub(lambda m: " " if m[0].startswith(("//", "/*")) else m[0], text)


def script_dependencies(directory: Path, extra_roots=(), prefixes=("mx0_", "dak_mx0_")) -> dict:
    scripts = {}
    duplicates = set()
    for path in sorted(directory.glob("*.cpp")):
        source = without_comments(path.read_text(encoding="latin1"))
        declarations = list(DECLARE.finditer(source))
        for index, match in enumerate(declarations):
            end = declarations[index + 1].start() if index + 1 < len(declarations) else len(source)
            name = match[1]
            key = name.lower()
            if key in scripts:
                duplicates.add(key)
            scripts[key] = {"name": name, "owner": path.name,
                            "attachments": sorted(set(ATTACH.findall(source[match.end():end])))}
    pending = [name for name in scripts if name.startswith(prefixes)]
    if not pending and prefixes:
        raise ValueError(f"no original script registrations found for {prefixes}")
    roots = sorted(set(pending + [name.lower() for name in extra_roots]))
    pending = roots.copy()
    visited = set()
    missing = set()
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        if name in duplicates:
            raise ValueError(f"ambiguous original script registration: {name}")
        if name not in scripts:
            missing.add(name)
            continue
        pending.extend(n.lower() for n in scripts[name]["attachments"])
    required = [scripts[name] for name in sorted(visited - missing)]
    return {"roots": roots, "required_scripts": required,
            "required_owners": sorted({row["owner"] for row in required}),
            "unresolved_literal_scripts": sorted(missing),
            "limits": ["Static literal attachment closure, not C++ control-flow or runtime verification.",
                       f"Includes registrations with prefixes {prefixes} conservatively, including diagnostic branches.",
                       "Dynamic script names, preset-only scripts and save-state restoration need separate coverage."]}


def cmake_block(text: str, command: str, name: str) -> str:
    match = re.search(r'\b' + command + r'\s*\(\s*' + name + r'\b([^)]*)\)', text)
    if not match:
        raise ValueError(f"missing CMake {command}({name}) source block")
    return match[1]


def selected_owners(root: Path) -> dict[str, set[str]]:
    native = re.sub(r'#[^\n]*', '', (root / "CMakeLists.txt").read_text())
    host = re.sub(r'#[^\n]*', '', (root / "tools/host_a30_definitions/CMakeLists.txt").read_text())
    native_blocks = cmake_block(native, "set", "RENEGADE_A31_INTERACTIVE_ORIGINAL_SOURCES")
    native_blocks += cmake_block(native, "set", "RENEGADE_CAMPAIGN_SCRIPT_SOURCES")
    host_block = cmake_block(host, "add_executable", "a31_interactive_runtime")
    return {
        "vita": set(re.findall(r'\$\{RENEGADE_SCRIPT_SOURCE\}/([\w.]+\.cpp)', native_blocks)),
        "host": set(re.findall(r'\$\{RV_SCRIPT_SOURCE\}/([\w.]+\.cpp)', host_block)),
    }


def audit(root: Path) -> dict:
    reference = json.loads((root / "tools/m13_reference_coverage.json").read_text())
    result = script_dependencies(root / "upstream/CnC_Renegade/Code/Scripts",
                                 reference["retail_text_script_roots"])
    required = set(result["required_owners"])
    result["missing_owners"] = {target: sorted(required - selected)
                                for target, selected in selected_owners(root).items()}
    result["source_selection_passed"] = not (result["unresolved_literal_scripts"] or
                                             any(result["missing_owners"].values()))
    return result


def check_symbols(result: dict, symbols: str) -> None:
    # nm -C defined factory methods; a name in .rodata or an undefined symbol
    # is insufficient. Runtime registry execution is still a separate gate.
    linked = {match[1].lower() for match in re.finditer(
        r'^\s*[0-9a-fA-F]+\s+[TtWw]\s+ScriptRegistrant<([^>]+)>::Create\(\)',
        symbols, re.MULTILINE)}
    result["missing_linked_factories"] = sorted(
        row["name"] for row in result["required_scripts"]
        if row["name"].lower() not in linked)
    result["linked_factories_passed"] = not result["missing_linked_factories"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--symbols", type=Path, help="Existing demangled nm output; no build or launch")
    args = parser.parse_args()
    result = audit(args.root)
    if args.symbols:
        check_symbols(result, args.symbols.read_text())
    payload = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(payload)
    print(payload, end="")
    passed = result["source_selection_passed"] and result.get("linked_factories_passed", True)
    if not passed:
        print("M13 script coverage FAILED: " + json.dumps({
            "missing_owners": result["missing_owners"],
            "unresolved_scripts": result["unresolved_literal_scripts"],
            "missing_factories": result.get("missing_linked_factories", []),
        }), file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
