"""Conservative M13 discovery envelope; matches are leads, not proven execution.

Starts from the typed audit. Follows exact preset/script tokens in reached
definition records, level records and required script string literals. Never
promotes unrelated whole-database registrations into mission requirements.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from tools.audit_m13_level_owners import chunks, definitions, reference_fields, MixArchive
from tools.check_m13_script_coverage import ROOT, DECLARE, without_comments, selected_owners
from tools.renegade_cinematic_dependency_scan import source_chunk_inventory


def tokens(data):
    return {m.group().decode("ascii").lower() for m in re.finditer(rb"[A-Za-z_][A-Za-z_0-9.-]{3,}", data)}


def discover(receipt, data_root):
    db = MixArchive(data_root / "always.dbs")
    nodes = chunks(db.read_binary("objects.ddb"))
    defs = definitions(nodes, reference_fields(ROOT))
    raw = {f.offset: f.data for m in nodes if m.kind == 0x101
           for g in m.children if g.kind == 0x101 for f in g.children}
    raw_by_id = {key:raw[row['offset']] for key,row in defs.items()}
    archive_name = receipt.get("archive_name", "M13.mix")
    mission = MixArchive(data_root / archive_name)
    for member in sorted(mission.entries):
        if member.endswith('.ddb'):
            overlay_nodes = chunks(mission.read_binary(member))
            overlay_defs = definitions(overlay_nodes, reference_fields(ROOT))
            overlay_raw = {f.offset:f.data for m in overlay_nodes if m.kind==0x101
                           for g in m.children if g.kind==0x101 for f in g.children}
            raw_by_id.update({key:overlay_raw[row['offset']] for key,row in overlay_defs.items()})
            defs.update(overlay_defs)
    names = {v["name"].lower(): k for k, v in defs.items() if v['name']}
    scripts = {}
    for path in sorted((ROOT / "upstream/CnC_Renegade/Code/Scripts").glob("*.cpp")):
        source = without_comments(path.read_text(encoding="latin1"))
        matches = list(DECLARE.finditer(source))
        for i, match in enumerate(matches):
            body = source[match.end():matches[i+1].start() if i+1 < len(matches) else len(source)]
            # Shared tables before the first declaration feed computed names
            # (notably Soldier_Powerup_Table). Include them conservatively.
            literals = re.findall(r'"([^"\n]*)"', source[:matches[0].start()] + body)
            scripts[match[1].lower()] = {"name": match[1], "owner": path.name,
                "tokens": tokens(" ".join(literals).encode("latin1")),
                "commands": set(re.findall(r'Commands\s*->\s*(\w+)\s*\(', body)),
                "dynamic_calls": sorted(set(re.findall(r'Commands\s*->\s*(?:Attach_Script|Create_Object(?:_At_Bone)?|Create_Explosion|Give_PowerUp)\s*\([^;]+;', body)))}
    selected_defs = {r["id"] for r in receipt["selected_definitions"]}
    selected_scripts = {r["name"].lower() for r in receipt["scripts"]["required_scripts"]}
    initial_defs, initial_scripts = selected_defs.copy(), selected_scripts.copy()
    evidence = []
    seen = set()
    pending = [("definition", k) for k in selected_defs] + [("script", k) for k in selected_scripts]
    level_tokens = set()
    for name in mission.entries:
        if name.endswith((".ldd", ".lsd", ".txt")):
            level_tokens.update(tokens(mission.read_binary(name)))
    pending.append(("level_strings", archive_name))
    while pending:
        kind, key = pending.pop()
        if (kind, key) in seen:
            continue
        seen.add((kind, key))
        if kind == "definition":
            row = defs[key]
            found = tokens(raw_by_id[key])
            for ref in row["definition_references"]:
                if ref in defs and ref not in selected_defs:
                    selected_defs.add(ref)
                    pending.append(("definition", ref))
                    evidence.append({"from": [kind, key], "to_definition": ref, "reason": "typed link"})
        elif kind == "script":
            found = scripts[key]["tokens"]
        else:
            found = level_tokens
        for token in sorted(found):
            if token in scripts and token not in selected_scripts:
                selected_scripts.add(token)
                pending.append(("script", token))
                evidence.append({"from": [kind, key], "to_script": token, "reason": "exact token lead"})
            if token in names and names[token] not in selected_defs:
                ref = names[token]
                selected_defs.add(ref)
                pending.append(("definition", ref))
                evidence.append({"from": [kind, key], "to_definition": ref, "name": defs[ref]["name"], "reason": "exact token lead"})
    owners = {scripts[k]["owner"] for k in selected_scripts}
    commands = set().union(*(scripts[n]["commands"] for n in initial_scripts))
    command_source = without_comments((ROOT / "staging/combat/scriptcommands.cpp").read_text(encoding="latin1"))
    bindings = dict(re.findall(r'EngineCommands\.(\w+)\s*=\s*&?\s*(\w+)\s*;', command_source))
    factory_map = source_chunk_inventory(ROOT)["persist_factories"]["by_chunk_id"]
    compdb = json.loads(subprocess.check_output(["ninja", "-C", str(ROOT / "build/vita-fast-candidate"), "-t", "compdb"], text=True))
    compiled = {(Path(r["directory"]) / r["file"]).resolve() for r in compdb if r["output"].startswith("CMakeFiles/RenegadeVitaA31.dir/")}
    factory_types = {defs[n]["factory"] for n in selected_defs}
    missing_factories = [r for f in sorted(factory_types) for r in factory_map.get(f, []) if (ROOT / r["path"]).resolve() not in compiled]
    return {"classification": "conservative discovery envelope; source strings and parameters require call-site verification",
        "typed_script_commands_used": sorted(commands),
        "typed_script_commands_without_source_binding": sorted(commands-bindings.keys()),
        "envelope_definition_factory_types": sorted(factory_types),
        "envelope_unmapped_factory_types": sorted(factory_types-factory_map.keys()),
        "envelope_factory_owners_absent_from_existing_compile_graph": missing_factories,
        "typed_receipt_archive_sha256": receipt["archive_sha256"],
        "definition_count": len(selected_defs), "script_count": len(selected_scripts),
        "additional_scripts": [{k: scripts[n][k] for k in ("name", "owner")} for n in sorted(selected_scripts-initial_scripts)],
        "additional_definitions": [{"id": n, "name": defs[n]["name"]} for n in sorted(selected_defs-initial_defs)],
        "missing_owners": {t: sorted(owners-s) for t,s in selected_owners(ROOT).items()},
        "discovery_edges": evidence,
        "calls_for_review": {scripts[n]["name"]: scripts[n]["dynamic_calls"] for n in sorted(selected_scripts) if scripts[n]["dynamic_calls"]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--typed-receipt", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = discover(json.loads(args.typed_receipt.read_text()), args.data)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k:v for k,v in result.items() if k in ("definition_count", "script_count", "additional_scripts", "missing_owners")}, indent=2))
