"""Read-only M13 level/preset script and persisted-factory owner audit.

Disk fields are explicitly little-endian 32-bit, independent of host ABI.
Does not instantiate game objects, build, run the game, or export asset bytes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

if __package__:
    from .check_m13_script_coverage import ROOT, selected_owners, script_dependencies, without_comments, DECLARE, check_symbols
    from .renegade_cinematic_dependency_scan import MixArchive, scan_all_text, source_chunk_inventory, parse_enum_constants
else:
    from check_m13_script_coverage import ROOT, selected_owners, script_dependencies, without_comments, DECLARE, check_symbols
    from renegade_cinematic_dependency_scan import MixArchive, scan_all_text, source_chunk_inventory, parse_enum_constants


@dataclass
class Chunk:
    kind: int
    offset: int
    data: bytes
    children: list


def chunks(data: bytes, base: int = 0, depth: int = 0) -> list[Chunk]:
    if depth > 64:
        raise ValueError("chunk nesting exceeds limit")
    result = []
    pos = 0
    while pos < len(data):
        if len(data) - pos < 8:
            raise ValueError(f"truncated chunk header at {base + pos}")
        kind, size = struct.unpack_from("<II", data, pos)
        end = pos + 8 + (size & 0x7fffffff)
        if end > len(data):
            raise ValueError(f"chunk outside parent at {base + pos}")
        payload = data[pos + 8:end]
        # ConversationMgr serializes a raw uint32 category before its children.
        # Its entire subsystem is outside this script/factory audit. Do not
        # guess chunk boundaries or confuse its reused local IDs with scripts.
        children = [] if kind == 0x40700 or not size & 0x80000000 else chunks(payload, base + pos + 8, depth + 1)
        result.append(Chunk(kind, base + pos, payload, children))
        pos = end
    return result


def flatten(nodes):
    for node in nodes:
        yield node
        yield from flatten(node.children)


def microchunks(data: bytes) -> list[tuple[int, bytes]]:
    result = []
    pos = 0
    while pos < len(data):
        if len(data) - pos < 2:
            raise ValueError("truncated microchunk header")
        kind, size = data[pos:pos + 2]
        end = pos + 2 + size
        if end > len(data):
            raise ValueError("microchunk outside parent")
        result.append((kind, data[pos + 2:end]))
        pos = end
    return result


def string(data: bytes, encoding: str = "ascii") -> str:
    if not data.endswith(b"\0") or b"\0" in data[:-1]:
        raise ValueError("invalid serialized string")
    return data[:-1].decode(encoding)


def u32(data: bytes) -> int:
    if len(data) != 4:
        raise ValueError("expected original 32-bit field")
    return struct.unpack("<I", data)[0]


def script_bindings(fields, name_kind, parameter_kind, offset):
    """Original loaders append parallel vectors; never collapse repeated IDs."""
    names = [string(value) for kind, value in fields if kind == name_kind]
    parameters = [string(value, "latin1") for kind, value in fields if kind == parameter_kind]
    issues = []
    if len(names) != len(parameters):
        issues.append({"kind": "script_parameter_count_mismatch", "offset": offset,
                       "name_count": len(names), "parameter_count": len(parameters),
                       "unpaired_parameters": parameters[len(names):]})
    return [{"name": name, "parameters": parameters[i] if i < len(parameters) else None}
            for i, name in enumerate(names)], issues


def level_records(nodes: list[Chunk]) -> dict:
    scripts = []
    objects = []
    factories = Counter()
    spawners = []
    physics = []
    binding_issues = []
    object_tokens = {}
    for node in flatten(nodes):
        # Original SimplePersistFactory object's two child chunks identify a
        # real factory use; arbitrary occurrences of a numeric ID do not.
        if len(node.children) == 2 and [c.kind for c in node.children] == [0x100100, 0x100101]:
            token = u32(node.children[0].data)  # pointer TOKEN, never a host pointer
            factories[node.kind] += 1
            for child in flatten(node.children[1].children):
                if child.kind == 910991407:
                    fields = dict(microchunks(child.data))
                    object_tokens[token] = {"instance_id": u32(fields[3]), "definition_id": u32(fields[2])}
        if node.kind == 0x00660055:  # PhysClass::PHYS_CHUNK_VARIABLES
            fields = dict(microchunks(node.data))
            if 6 in fields:
                physics.append({"definition_id": u32(fields[6]), "offset": node.offset})
        if node.kind == 131001135:  # ScriptManager::CHUNKID_SCRIPT_HEADER
            fields = dict(microchunks(node.data))
            scripts.append({"name": string(fields[1]), "offset": node.offset,
                            "parameters": string(fields[2], "latin1") if 2 in fields else None,
                            "binding_kind": "persisted_script",
                            "owner_token": u32(fields[4]) if 4 in fields else None})
            if 2 not in fields:
                binding_issues.append({"kind": "missing_persisted_script_parameters", "offset": node.offset})
        elif node.kind == 910991407:  # BaseGameObj::CHUNKID_VARIABLES
            fields = dict(microchunks(node.data))
            objects.append({"definition_id": u32(fields[2]),
                            "instance_id": u32(fields[3]), "offset": node.offset})
        elif node.kind == 1014991054:  # SpawnerClass::CHUNKID_VARIABLES
            fields = microchunks(node.data)
            identity = dict(fields)
            spawner_id = u32(identity[1]) if 1 in identity else None
            spawners.append({"definition_id": u32(identity[3]), "instance_id": spawner_id,
                             "offset": node.offset})
            if spawner_id is None:
                binding_issues.append({"kind": "missing_spawner_instance_id", "offset": node.offset})
            bindings, issues = script_bindings(fields, 10, 11, node.offset)
            binding_issues.extend(issues)
            scripts.extend({**binding, "offset": node.offset, "owner_token": None,
                            "binding_kind": "spawner_script", "spawner_id": spawner_id}
                           for binding in bindings)
    for script in scripts:
        script["owner"] = object_tokens.get(script["owner_token"])
    return {"script_records": scripts, "objects": objects, "spawners": spawners, "physics": physics,
            "script_binding_issues": binding_issues,
            "persist_factory_counts": {f"0x{k:08x}": v for k, v in sorted(factories.items())},
            "skipped_subsystems": [{"id": "0x00040700", "offset": n.offset}
                                   for n in flatten(nodes) if n.kind == 0x40700]}


def reference_fields(root: Path) -> dict:
    # Use named original fields, never "any uint32 resembling a preset ID".
    specs = [
        ("vehicle.cpp", "CHUNKID_DEF", ["MICROCHUNKID_ENGINE_START_SOUND", "MICROCHUNKID_ENGINE_RUN_SOUND", "MICROCHUNKID_ENGINE_STOP_SOUND", "MICROCHUNKID_ENGINE_OFF_SOUND"]),
        ("cinematicgameobj.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_SOUND_DEF_ID"]),
        ("doors.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_OPEN_SOUND_DEF_ID", "MICROCHUNKID_DEF_CLOSE_SOUND_DEF_ID", "MICROCHUNKID_DEF_UNLOCK_SOUND_DEF_ID", "MICROCHUNKID_DEF_ACCESS_DENIED_SOUND_DEF_ID"]),
        ("elevator.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_DOOR_OPEN_SOUNDID", "MICROCHUNKID_DEF_DOOR_CLOSE_SOUNDID", "MICROCHUNKID_DEF_DOOR_UNLOCK_SOUNDID", "MICROCHUNKID_DEF_DOOR_ACCESS_DENIED_SOUNDID", "MICROCHUNKID_DEF_ELEVATOR_MOVING_SOUNDID"]),
        ("soldier.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_HUMAN_ANIM_OVERRIDE_DEF_ID", "MICROCHUNKID_DEF_HUMAN_LOITER_COLLECTION_DEF_ID", "MICROCHUNKID_DEF_DEATH_SOUND_PRESET"]),
        ("powerup.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_GRANT_WEAPON_ID", "MICROCHUNKID_DEF_GRANT_SOUNDID", "MICROCHUNKID_DEF_IDLE_SOUNDID"]),
        ("beacongameobj.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_ARMED_SOUNDID", "MICROCHUNKID_DEF_POST_CINEMATIC_DEFID", "MICROCHUNKID_DEF_PRE_CINEMATIC_DEFID", "MICROCHUNKID_DEF_EXPLOSION_DEFID"]),
        ("physicalgameobj.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_PHYS_ID", "MICROCHUNKID_DEF_KILLED_EXPLOSION"]),
        ("armedgameobj.cpp", "CHUNKID_DEF", ["MICROCHUNKID_DEF_WEAPON_DEF_ID", "MICROCHUNKID_DEF_SECONDARY_WEAPON_DEF_ID"]),
        ("weaponmanager.cpp", "CHUNKID_WEAPON_DEF", ["MICROCHUNKID_WEAPON_DEF_EJECT_PHYS_DEF_ID", "MICROCHUNKID_WEAPON_DEF_MUZZLE_FLASH_PHYS_DEF_ID", "MICROCHUNKID_WEAPON_DEF_RELOAD_SOUND_DEFID", "MICROCHUNKID_WEAPON_DEF_PRIMARY_AMMO_DEF_ID", "MICROCHUNKID_WEAPON_DEF_SECONDARY_AMMO_DEF_ID", "MICROCHUNKID_WEAPON_DEF_EMPTY_SOUND_DEFID"]),
        ("weaponmanager.cpp", "CHUNKID_AMMO_DEF", ["MICROCHUNKID_AMMO_DEF_EXPLOSION_DEF_ID", "MICROCHUNKID_AMMO_DEF_CONTINUOUS_SOUND_DEF_ID", "MICROCHUNKID_AMMO_DEF_C4_TIMING_SOUND_1_ID", "MICROCHUNKID_AMMO_DEF_C4_TIMING_SOUND_2_ID", "MICROCHUNKID_AMMO_DEF_C4_TIMING_SOUND_3_ID", "MICROCHUNKID_AMMO_DEF_BEACON_DEFID", "MICROCHUNKID_AMMO_DEF_FIRE_SOUND_DEFID"]),
    ]
    result = {}
    for name, prefix, fields in specs:
        symbols = {}
        parse_enum_constants(root / "staging/combat" / name, symbols)
        result[(symbols[prefix + "_PARENT"], symbols[prefix + "_VARIABLES"])] = {symbols[n] for n in fields}
    # Original explosion.cpp uses a C++ octal literal, not decimal.
    source = (root / "staging/combat/explosion.cpp").read_text(encoding="latin1")
    match = re.search(r'CHUNKID_EXPLOSION_DEF_VARIABLES\s*=\s*(0[0-7]+)\s*,', source)
    if not match:
        raise ValueError("review changed original explosion chunk layout")
    variable = int(match[1], 8)
    result[(variable + 1, variable)] = {1, 2}  # PhysDefID, SoundDefID
    return result


def definitions(nodes: list[Chunk], reference_schema=None) -> dict[int, dict]:
    result = {}
    for manager in nodes:
        if manager.kind != 0x101:  # SaveLoad DEFMGR
            continue
        for group in manager.children:
            if group.kind != 0x101:  # DefinitionMgr::CHUNKID_OBJECTS
                continue
            for factory in group.children:
                identity = []
                scripts = []
                bindings = []
                binding_issues = []
                references = []
                for node in flatten(factory.children):
                    if node.kind == 0x100 and not node.children:
                        fields = dict(microchunks(node.data))
                        if 1 in fields and 3 in fields and len(fields[1]) == 4:
                            # DefinitionClass::VARID_INSTANCEID / VARID_NAME
                            try:
                                name = string(fields[3])
                            except (ValueError, UnicodeDecodeError):
                                continue
                            identity.append((u32(fields[1]), name))
                    elif node.kind == 627001057:
                        rows, issues = script_bindings(microchunks(node.data), 2, 3, node.offset)
                        bindings.extend(rows)
                        binding_issues.extend(issues)
                        scripts.extend(row["name"] for row in rows)
                    elif node.kind == 1013991543:  # SpawnerDef variables
                        fields = microchunks(node.data)
                        rows, issues = script_bindings(fields, 18, 19, node.offset)
                        bindings.extend(rows)
                        binding_issues.extend(issues)
                        scripts.extend(row["name"] for row in rows)
                        references.extend(u32(value) for kind, value in fields if kind in (1, 14))
                # Twiddler::Save writes its alternative preset IDs in the
                # direct OBJDATA variables, apart from its nested base ID.
                if factory.kind == 0x102:
                    for body in factory.children:
                        if body.kind == 0x100101:
                            for node in body.children:
                                if node.kind == 0x100:
                                    references.extend(u32(value) for kind, value in microchunks(node.data) if kind == 1)
                for container in flatten([factory]):
                    sibling_ids = {node.kind for node in container.children}
                    for (parent, variables), fields in (reference_schema or {}).items():
                        if parent not in sibling_ids:
                            continue
                        for node in container.children:
                            if node.kind == variables:
                                references.extend(u32(value) for kind, value in microchunks(node.data) if kind in fields)
                if len(identity) != 1:
                    raise ValueError(f"ambiguous definition identity at {factory.offset}: {identity}")
                key, name = identity[0]
                if key in result:
                    raise ValueError(f"duplicate definition ID {key}")
                result[key] = {"name": name, "scripts": scripts,
                               "script_bindings": bindings, "script_binding_issues": binding_issues,
                               "definition_references": sorted(set(references) - {0}),
                               "factory": f"0x{factory.kind:08x}", "offset": factory.offset}
    return result


def audit(root: Path, archive: Path, definitions_archive: Path, native_build: Path, nm: Path, prefixes=("mx0_", "dak_mx0_"), preset_roots=(), deep=False) -> dict:
    mission = MixArchive(archive)
    members = {}
    level_scripts = set()
    definition_ids = set()
    factory_counts = Counter()
    for name in sorted(mission.entries):
        if not name.endswith((".ldd", ".lsd")):
            continue
        data = mission.read_binary(name)
        record = level_records(chunks(data))
        record["sha256"] = hashlib.sha256(data).hexdigest()
        members[name] = record
        level_scripts.update(row["name"] for row in record["script_records"])
        definition_ids.update(row["definition_id"] for row in record["objects"])
        definition_ids.update(row["definition_id"] for row in record["spawners"])
        definition_ids.update(row["definition_id"] for row in record["physics"] if row["definition_id"])
        factory_counts.update(record["persist_factory_counts"])
    ddb = MixArchive(definitions_archive)
    definition_data = ddb.read_binary("objects.ddb")
    defs = definitions(chunks(definition_data), reference_fields(root))
    overlays = []
    for member in sorted(mission.entries):
        if member.endswith('.ddb'):
            payload = mission.read_binary(member)
            additions = definitions(chunks(payload), reference_fields(root))
            overlays.append({'member': member, 'definitions': len(additions),
                             'sha256': hashlib.sha256(payload).hexdigest(),
                             'overridden_ids': sorted(defs.keys() & additions.keys())})
            defs.update(additions)
    if not defs or not members:
        raise ValueError("missing definition database or level members")
    text_scan = scan_all_text(mission)
    created_names = set(text_scan["dependencies"].get("real_object_presets", []))
    created_names.update(preset_roots)
    # Literal creation sites in the required script bodies extend the root
    # preset set; computed names and other definition references remain open.
    roots = level_scripts | set(text_scan["referenced_scripts"])
    pending_names = set()
    unresolved_presets = set()
    missing_ids = sorted(definition_ids - defs.keys())
    by_name = {row["name"].lower(): key for key, row in defs.items()}
    processed_ids = set()
    if __package__:
        from .deep_content_dependencies import DeepContentDependencies
    else:
        from deep_content_dependencies import DeepContentDependencies
    deep_scan = DeepContentDependencies(archive.parent, mission) if deep else None
    parsed_scripts = {}
    for file in (root / "upstream/CnC_Renegade/Code/Scripts").glob("*.cpp"):
        code = without_comments(file.read_text(encoding="latin1"))
        matches = list(DECLARE.finditer(code))
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(code)
            parsed_scripts[match[1].lower()] = code[match.end():end]
    while True:
        closure = script_dependencies(root / "upstream/CnC_Renegade/Code/Scripts", roots, prefixes)
        before_roots = set(roots)
        for row in closure["required_scripts"]:
            created_names.update(re.findall(r'Commands\s*->\s*Create_Object(?:_At_Bone)?\s*\(\s*"([^"]+)"',
                                            parsed_scripts[row["name"].lower()]))
            if deep_scan:
                presets, scripts = deep_scan.from_source(parsed_scripts[row["name"].lower()], row["name"])
                created_names.update(presets)
                roots.update(scripts)
        for name in created_names - pending_names:
            key = by_name.get(name.lower())
            if key is None:
                unresolved_presets.add(name)
            else:
                definition_ids.add(key)
        pending_names.update(created_names)
        new_ids = (definition_ids & defs.keys()) - processed_ids
        if not new_ids and roots == before_roots:
            break
        for key in new_ids:
            roots.update(defs[key]["scripts"])
            definition_ids.update(defs[key]["definition_references"])
        processed_ids.update(new_ids)
    selected = selected_owners(root)
    closure["missing_owners"] = {target: sorted(set(closure["required_owners"]) - owners)
                                 for target, owners in selected.items()}
    known_factories = source_chunk_inventory(root)["persist_factories"]["by_chunk_id"]
    compdb = json.loads(subprocess.check_output(["ninja", "-C", str(native_build), "-t", "compdb"], text=True))
    compiled = {(Path(row["directory"]) / row["file"]).resolve() for row in compdb
                if row["output"].startswith("CMakeFiles/RenegadeVitaA31.dir/")}
    binary = native_build / "RenegadeVitaA31"
    symbols = subprocess.check_output([str(nm), "-C", str(binary)], text=True)
    check_symbols(closure, symbols)
    used_factories = set(factory_counts) | {defs[key]["factory"] for key in processed_ids}
    factory_owners = []
    for kind in sorted(used_factories):
        for owner in known_factories.get(kind, []):
            pattern = (r'^\s*[0-9a-fA-F]+\s+[TtWw]\s+SimplePersistFactoryClass<' +
                       re.escape(owner["class"]) + r',\s*' + str(int(kind, 16)) + r'>::Load\(')
            factory_owners.append({"chunk": kind, **owner,
                                   "defined_load_method_in_existing_elf": bool(re.search(pattern, symbols, re.MULTILINE)),
                                   "in_existing_native_compile_graph": (root / owner["path"]).resolve() in compiled})
    return {"schema_version": 1, "evidence": "read-only retail/source/configured-graph audit",
            "archive_name": archive.name, "script_prefixes": list(prefixes),
            "reviewed_preset_roots": list(preset_roots),
            "deep_content": deep_scan.receipt() if deep_scan else None,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "objects_ddb_sha256": hashlib.sha256(definition_data).hexdigest(),
            "level_definition_overlays": overlays,
            "existing_native_elf_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
            "members": members, "level_script_names": sorted(level_scripts),
            "selected_definitions": [{"id": key, **defs[key]} for key in sorted(processed_ids)],
            "definition_database_count": len(defs), "unresolved_level_definition_ids": missing_ids,
            "unresolved_referenced_definition_ids": sorted(definition_ids - defs.keys()),
            "unresolved_literal_presets": sorted(unresolved_presets), "scripts": closure,
            "persist_factory_owners": factory_owners,
            "unmapped_persist_factories": sorted(used_factories - known_factories.keys()),
            "limits": ["Conversation subsystem skipped deliberately; not a complete binary semantics audit.",
                       "Preset closure covers placed BaseGameObj IDs and literal script/cinematic creation names.",
                       "Traverses physics-only roots, Spawner/Twiddler alternatives and named Physical/Armed/Weapon/Ammo/Explosion/Soldier/Powerup/Beacon links. Other typed links and computed names remain open.",
                       "Existing compile graph is membership evidence, not new compilation or runtime registration."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--definitions", type=Path, required=True)
    parser.add_argument("--native-build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--nm", type=Path, default=Path("/usr/local/vitasdk/bin/arm-vita-eabi-nm"))
    parser.add_argument("--script-prefix", action="append", help="Mission registration prefix; repeatable")
    parser.add_argument("--preset-root", action="append", default=[], help="Manually traced computed preset name; repeatable")
    parser.add_argument("--deep", action="store_true", help="Follow global cinematic text and additional literal preset calls")
    args = parser.parse_args()
    result = audit(args.root, args.archive, args.definitions, args.native_build, args.nm,
                   tuple(args.script_prefix) if args.script_prefix else ("mx0_", "dak_mx0_"), args.preset_root, args.deep)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"level_scripts": len(result["level_script_names"]),
                      "preset_count": len(result["selected_definitions"]),
                      "required_scripts": len(result["scripts"]["required_scripts"]),
                      "missing_script_owners": result["scripts"]["missing_owners"],
                      "missing_factory_owners": [row for row in result["persist_factory_owners"]
                                                 if not row["in_existing_native_compile_graph"]],
                      "unmapped_factories": result["unmapped_persist_factories"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
