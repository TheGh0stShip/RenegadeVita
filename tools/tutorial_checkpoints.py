#!/usr/bin/env python3
"""Archive, catalogue and relaunch original M00 saves without changing their bytes.

capture     archive an unchanged native save into the local immutable vault
restore     copy a vault master into a new (or byte-identical) user/save slot
launch      restore, then queue the RVCP1 one-shot or RVTC1 sticky request that
            a RENEGADE_DEVELOPMENT_CHECKPOINT=1 build consumes at startup
catalog     list saves and vault masters with the metadata the original save
            itself exposes (map, description, objectives) and a derived segment
verify-log  compare the first post-load objective line of a runtime log with
            the objectives serialized in the save that was launched
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from datetime import datetime, timezone

MAX_SAVE = 64 * 1024 * 1024
DEFAULT_VAULT = Path(__file__).resolve().parents[1] / "build/tutorial-checkpoints"
RECEIPTS = "_receipts"  # Not a valid checkpoint ID, so never a vault entry.

# Combat/savegame.cpp: top-level envelope and its level-info microchunks.
LEVEL_INFO = 1011991648
LEVEL_DATA = LEVEL_INFO + 1
MICRO_MAP, MICRO_MISSION, MICRO_DESCRIPTION = 1, 2, 3
# wwsaveload/saveloadids.h CHUNKID_COMBAT_BEGIN; combat/combatsaveload.cpp
# CHUNKID_OBJECTIVES (CHUNKID_GAMEOBJMANAGER + 8); combat/objectives.cpp.
CHUNKID_COMBAT = 0x00040000
COMBAT_OBJECTIVES = 916991654 + 8
OBJECTIVE_ENTRY = 629001432
OBJECTIVE_MANAGER_VARIABLES = OBJECTIVE_ENTRY + 1
OBJECTIVE_VARIABLES = 629001440
OBJECTIVE_ID, OBJECTIVE_TYPE, OBJECTIVE_STATUS, OBJECTIVE_AGE = 1, 2, 3, 11
STATUS_NAMES = {0: "pending", 1: "accomplished", 2: "failed", 3: "hidden"}
STATUS_HIDDEN = 3

# Scripts/Mission00.cpp objective owners. Each entry: short name, the lesson
# that follows completion, reveal and completion conversations (line refs in
# reports/tutorial/TUT_R1_DEV_CHECKPOINTS.md).
M00_OBJECTIVES = {
    1: ("sydney", "sydney-hud-lesson", "MTU_LOGAN_EVA", "MTU_SYDNEY_START"),
    2: ("gunner", "gunner-range", "MTU_SYDNEY_RADAR", "MTU_GUNNER_START"),
    3: ("hotwire", "hotwire-vehicles", "MTU_GUNNER_ENDING", "MTU_HOTWIRE_INTRO"),
    4: ("mobius", "mobius-refinery", "MTU_LOGAN_WHATSNEXT", "MTU_MOBIUS_REFINERY"),
    5: ("petrova", "petrova-power-plant", "MTU_LOGAN_PREPARE_POWER", "MTU_PETROVA_POWER"),
    6: ("officers", "mission-end", "MTU_LIEUTENANT_AFTER", "MTU_TYPE_COUNT_OFFICERS"),
}
SEGMENTS = ["logan-course"] + [
    name for entry in M00_OBJECTIVES.values() for name in ("to-" + entry[0], entry[1])]

SAVE_WRITE = re.compile(r"A3\.5 save write: path=(?P<path>\S+) bytes=(?P<bytes>-?\d+) "
                        r"elapsed_us=\d+ success=(?P<success>[01])")
PROGRESS = re.compile(r"A3\.5 mission progress: frame=(?P<frame>\d+) .*?"
                      r"status_1_6=(?P<status>-?\d+(?:/-?\d+){5}) active_conversations=\d+ "
                      r"active=(?P<active>\S+)")
HANDOFFS = (
    re.compile(r"A4 checkpoint: (?P<kind>.*?) handoff latched=(?P<latched>[01]) "
               r"source=(?P<source>[^;\s]+)"),
    re.compile(r"A4 (?P<kind>load): original source handoff after completed session "
               r"teardown source=(?P<source>[^;\s]+)"),
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", value):
        raise ValueError("Checkpoint IDs must be 1-48 letters, digits, hyphens or underscores")
    return value


def slot_name(value):
    # Same grammar as A31DevelopmentCheckpoint::Parse_Save_Slot_Request.
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.[sS][aA][vV]", value):
        raise ValueError("Use a simple .sav basename: letter/digit first, at most 64-character stem")
    return value


def chunks(data, start, end, what):
    offset = start
    while offset < end:
        if offset + 8 > end:
            raise ValueError(f"Truncated {what} chunk header")
        chunk, size_flags = struct.unpack_from("<II", data, offset)
        body = offset + 8
        stop = body + (size_flags & 0x7fffffff)
        if stop > end:
            raise ValueError(f"{what} chunk exceeds its bounds")
        yield chunk, body, stop
        offset = stop


def micro_chunks(data, start, end, what):
    cursor = start
    while cursor < end:
        if cursor + 2 > end:
            raise ValueError(f"Truncated {what} microchunk")
        kind, length = data[cursor], data[cursor + 1]
        cursor += 2
        if cursor + length > end:
            raise ValueError(f"{what} microchunk exceeds its chunk bounds")
        yield kind, data[cursor:cursor + length]
        cursor += length


def parse_level_info(data, start, end):
    """Mirror the Vita Read_Player_Save_Level_Info admission rules."""
    seen = {}
    for kind, value in micro_chunks(data, start, end, "original save level-info"):
        if kind in (MICRO_MAP, MICRO_MISSION, MICRO_DESCRIPTION):
            if kind in seen:
                raise ValueError("Ambiguous map identity" if kind == MICRO_MAP else
                                 "Duplicate original save level-info microchunk")
            seen[kind] = value
    if len(seen) != 3:
        raise ValueError("Original save level info lacks map, mission or description")
    raw_map, mission, wide = seen[MICRO_MAP], seen[MICRO_MISSION], seen[MICRO_DESCRIPTION]
    if not 1 <= len(raw_map) <= 512 or raw_map.find(b"\0") != len(raw_map) - 1:
        raise ValueError("Original save map name is not one NUL-terminated string")
    map_name = raw_map[:-1].decode("latin-1")
    if len(map_name) <= 4 or not map_name.lower().endswith(".lsd"):
        raise ValueError("Original save map name must name a .lsd level")
    if len(mission) != 4:
        raise ValueError("Original save mission description must be one 32-bit ID")
    units = [wide[index:index + 2] for index in range(0, len(wide), 2)]
    if (not 2 <= len(wide) <= 4096 or len(wide) % 2 or b"\0\0" not in units or
            units.index(b"\0\0") != len(units) - 1):
        raise ValueError("Original save description is not one NUL-terminated UTF-16 string")
    return {
        "map": map_name,
        "mission_description_id": struct.unpack("<i", mission)[0],
        "description": wide[:-2].decode("utf-16-le", errors="replace"),
    }


def parse_objectives(data, start, end):
    """Objectives from LEVEL_DATA > CHUNKID_COMBAT > CHUNKID_OBJECTIVES, or None."""
    combat = [entry for entry in chunks(data, start, end, "level-data") if entry[0] == CHUNKID_COMBAT]
    if len(combat) != 1:
        return None
    manager = [entry for entry in chunks(data, combat[0][1], combat[0][2], "combat")
               if entry[0] == COMBAT_OBJECTIVES]
    if len(manager) != 1:
        return None
    objectives = {}
    for chunk, body, stop in chunks(data, manager[0][1], manager[0][2], "objective-manager"):
        if chunk == OBJECTIVE_MANAGER_VARIABLES:
            continue
        if chunk != OBJECTIVE_ENTRY:
            raise ValueError("Unexpected objective-manager chunk")
        variables = [entry for entry in chunks(data, body, stop, "objective")
                     if entry[0] == OBJECTIVE_VARIABLES]
        if len(variables) != 1:
            raise ValueError("Objective entry lacks exactly one variables chunk")
        fields = {}
        for kind, value in micro_chunks(data, variables[0][1], variables[0][2], "objective"):
            if kind in (OBJECTIVE_ID, OBJECTIVE_TYPE, OBJECTIVE_STATUS, OBJECTIVE_AGE):
                if kind in fields or len(value) != 4:
                    raise ValueError("Malformed objective microchunk")
                fields[kind] = value
        if len(fields) != 4:
            raise ValueError("Objective lacks ID, type, status or age")
        identifier = struct.unpack("<i", fields[OBJECTIVE_ID])[0]
        if identifier in objectives:
            raise ValueError("Duplicate objective ID")
        objectives[identifier] = {
            "id": identifier,
            "type": struct.unpack("<i", fields[OBJECTIVE_TYPE])[0],
            "status": struct.unpack("<i", fields[OBJECTIVE_STATUS])[0],
            # Original Age resets when an objective leaves HIDDEN, then grows
            # with game time while visible (ObjectiveManager::Update).
            "age_seconds": round(struct.unpack("<f", fields[OBJECTIVE_AGE])[0], 1),
        }
    return [objectives[key] for key in sorted(objectives)]


def parse_save_bytes(data):
    """Validate the native envelope (LEVEL_INFO then nonempty LEVEL_DATA only)."""
    info, objectives, objective_error, order = None, None, None, []
    for chunk, body, stop in chunks(data, 0, len(data), "original save"):
        order.append(chunk)
        if chunk == LEVEL_INFO and order == [LEVEL_INFO]:
            info = parse_level_info(data, body, stop)
        elif chunk == LEVEL_DATA and order == [LEVEL_INFO, LEVEL_DATA]:
            if stop == body:
                raise ValueError("Original save has empty level data")
            try:
                objectives = parse_objectives(data, body, stop)
            except ValueError as error:
                objective_error = str(error)
        else:
            raise ValueError("Original save envelope must be level info then level data only")
    if order != [LEVEL_INFO, LEVEL_DATA]:
        raise ValueError("Original save envelope must be level info then level data only")
    info["objectives"] = objectives
    if objective_error:
        info["objectives_error"] = objective_error
    return info


def is_tutorial(info):
    return info["map"].lower() == "m00_tutorial.lsd"


def status_vector(objectives):
    """The runtime 'status_1_6=' rendering: IDs 1..6, -1 when absent."""
    by_id = {objective["id"]: objective["status"] for objective in objectives or ()}
    return "/".join(str(by_id.get(identifier, -1)) for identifier in range(1, 7))


def derive_segment(objectives):
    """Name the tutorial segment from the youngest visible original objective.

    Derived from serialized objective status/age only; it does not assert the
    player's exact position or that the named lesson was completed.
    """
    if not objectives:
        return {"segment": "unknown", "basis": "no original objective chunk"}
    visible = [entry for entry in objectives if entry["status"] != STATUS_HIDDEN]
    if not visible:
        return {"segment": "logan-course", "basis": "all objectives hidden (before MTU_LOGAN_EVA)"}
    latest = min(visible, key=lambda entry: (entry["age_seconds"], -entry["id"]))
    owner = M00_OBJECTIVES.get(latest["id"])
    if owner is None:
        return {"segment": "unknown", "basis": f"objective {latest['id']} is not an M00 objective"}
    status = STATUS_NAMES.get(latest["status"], str(latest["status"]))
    segment = {"pending": "to-" + owner[0], "accomplished": owner[1]}.get(status, status + "-" + owner[0])
    return {
        "segment": segment,
        "basis": f"objective {latest['id']} {status} {latest['age_seconds']:.1f}s of game time before saving",
        "objective_owner": {"revealed_by": owner[2], "completed_by": owner[3]},
        "accomplished": [entry["id"] for entry in objectives if entry["status"] == 1],
        "pending": [entry["id"] for entry in objectives if entry["status"] == 0],
    }


def describe(info):
    result = dict(info)
    result["status_1_6"] = status_vector(info.get("objectives"))
    result.update(derive_segment(info.get("objectives")) if is_tutorial(info) else
                  {"segment": "not-tutorial", "basis": "map is not M00_Tutorial.lsd"})
    return result


def read_regular(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Save must be a regular file, not a symlink")
    before = path.stat()
    if not 16 <= before.st_size <= MAX_SAVE:
        raise ValueError("Save size is outside the bounded native-save range")
    data = path.read_bytes()
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Save changed while being captured; wait for saving to finish")
    return data, after


def read_save(path):
    data, _ = read_regular(path)
    info = parse_save_bytes(data)
    if not is_tutorial(info):
        raise ValueError("Not an original M00 tutorial save with level data")
    return data, info["map"]


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def user_tree(path):
    if path.is_symlink() or path.name.lower() != "user":
        raise ValueError("Use the actual Renegade user directory, not retail or a symlink")
    user = path.resolve(strict=True)
    if (user / "save").is_symlink():
        raise ValueError("Save directory cannot be a symlink")
    return user


def content_identity(value):
    value = value or os.environ.get("RENEGADE_RETAIL_CONTENT_ID", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("content-id (or RENEGADE_RETAIL_CONTENT_ID) must be a SHA256 hex identity")
    return value.lower()


def load_master(vault, checkpoint_id):
    checkpoint = vault / safe_name(checkpoint_id)
    if checkpoint.is_symlink() or (checkpoint / "manifest.json").is_symlink():
        raise ValueError("Checkpoint master cannot be a symlink")
    metadata = json.loads((checkpoint / "manifest.json").read_text(encoding="ascii"))
    if metadata.get("schema") != 1 or metadata.get("id") != checkpoint_id:
        raise ValueError("Checkpoint manifest identity mismatch")
    data, map_name = read_save(checkpoint / "checkpoint.sav")
    if digest(data) != metadata.get("save_sha256") or map_name != metadata.get("map"):
        raise ValueError("Checkpoint master integrity mismatch")
    return metadata, data


def restore_master(vault, checkpoint_id, user, content_id, compatibility, slot):
    metadata, data = load_master(vault, checkpoint_id)
    if metadata.get("content_id") != content_id or metadata.get("compatibility") != compatibility:
        raise ValueError("Retail content or save compatibility epoch differs; do not reuse this checkpoint")
    slot = slot_name(slot or ("rv_cp_" + checkpoint_id + ".sav"))
    saves = user / "save"
    saves.mkdir(exist_ok=True)
    destination = saves / slot
    try:
        write_new(destination, data)  # Exclusive create: never overwrite live slots.
        reused = False
    except FileExistsError:
        # Relaunching the same checkpoint is the tester loop; an identical slot
        # is reused, any other content is left untouched and refused.
        existing, _ = read_regular(destination)
        if existing != data:
            raise ValueError(f"{slot} already exists with different bytes; choose another --slot")
        reused = True
    return destination, data, reused


def vault_entries(vault):
    if not vault.is_dir():
        return []
    return sorted(entry.name for entry in vault.iterdir()
                  if entry.is_dir() and not entry.is_symlink() and entry.name != RECEIPTS)


def select_by_segment(vault, segment):
    matches = []
    for checkpoint_id in vault_entries(vault):
        try:
            _, data = load_master(vault, checkpoint_id)
        except (OSError, ValueError, UnicodeError):
            continue
        if describe(parse_save_bytes(data))["segment"] == segment:
            matches.append(checkpoint_id)
    if len(matches) != 1:
        raise ValueError(f"Segment {segment!r} matches {len(matches)} vault checkpoints"
                         f"{': ' + ', '.join(matches) if matches else ''}; pass --id")
    return matches[0]


def scan_logs(paths):
    """Ordered save writes and launch handoffs, each with its nearest progress line."""
    writes, handoffs = [], []
    for path in paths:
        last_progress, waiting = None, []
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for number, line in enumerate(stream, 1):
                progress = PROGRESS.search(line)
                if progress:
                    last_progress = {"line": number, "frame": int(progress["frame"]),
                                     "status_1_6": progress["status"], "active": progress["active"]}
                    for handoff in waiting:
                        handoff["first_progress"] = last_progress
                    waiting = []
                    continue
                write = SAVE_WRITE.search(line)
                if write:
                    writes.append({"log": str(path), "line": number,
                                   "slot": re.split(r"[\\/]", write["path"])[-1],
                                   "bytes": int(write["bytes"]), "success": write["success"] == "1",
                                   "progress_before": last_progress})
                    continue
                for pattern in HANDOFFS:
                    match = pattern.search(line)
                    if match:
                        handoff = {"log": str(path), "line": number, "kind": match["kind"],
                                   "latched": match.groupdict().get("latched", "1") == "1",
                                   "slot": re.split(r"[\\/]", match["source"])[-1],
                                   "first_progress": None}
                        handoffs.append(handoff)
                        waiting.append(handoff)
                        break
    return writes, handoffs


def correlate(entry, size, writes):
    """Last successful log write of this slot; objective agreement is the check."""
    candidates = [write for write in writes
                  if write["success"] and write["slot"].lower() == entry["slot"].lower()]
    if not candidates:
        return {"status": "NO_LOG_WRITE"}
    write = candidates[-1]
    progress = write["progress_before"] or {}
    agrees = progress.get("status_1_6") == entry["status_1_6"]
    return {
        "status": "LOG_OBJECTIVES_AGREE" if agrees else "LOG_OBJECTIVES_DIFFER",
        "log": write["log"], "line": write["line"], "bytes_match": write["bytes"] == size,
        "status_1_6": progress.get("status_1_6"), "active_conversation": progress.get("active"),
        "frame": progress.get("frame"),
    }


def catalog(args):
    rows, logs = [], scan_logs(args.log or [])[0]
    sources = []
    if args.user_dir:
        saves = args.user_dir / "save"
        if saves.is_symlink() or not saves.is_dir():
            raise ValueError("user-dir must contain a real save directory")
        sources += [("user", path) for path in sorted(saves.iterdir())
                    if path.suffix.lower() == ".sav"]
    if args.with_vault or not (args.user_dir or args.save):
        sources += [("vault", args.vault / name / "checkpoint.sav") for name in vault_entries(args.vault)]
    sources += [("file", path) for path in args.save or ()]
    for origin, path in sources:
        entry = {"origin": origin, "path": str(path),
                 "slot": path.parent.name if origin == "vault" else path.name}
        rows.append(entry)
        try:
            data, stat = read_regular(path)
            entry.update(bytes=len(data), sha256=digest(data),
                         modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat())
            entry.update(describe(parse_save_bytes(data)))
            entry["native_envelope"] = "PASS"
        except (OSError, ValueError, UnicodeError) as error:
            entry["native_envelope"] = "REJECTED: " + str(error)
            continue
        if origin == "vault":
            try:
                manifest = json.loads((path.parent / "manifest.json").read_text(encoding="ascii"))
                entry["manifest"] = {key: manifest.get(key) for key in (
                    "segment_status", "created_by_build", "compatibility", "content_id", "source_slot")}
                entry["manifest_hash_match"] = manifest.get("save_sha256") == entry["sha256"]
            except (OSError, ValueError, UnicodeError) as error:
                entry["manifest_error"] = str(error)
        elif origin == "user" and logs:
            entry["log"] = correlate(entry, entry["bytes"], logs)
    return rows


def format_rows(rows):
    lines = [f"{'origin':6} {'slot/id':34} {'segment':22} {'status_1_6':13} {'description':14} basis"]
    for row in rows:
        if row["native_envelope"] != "PASS":
            lines.append(f"{row['origin']:6} {row['slot'][:34]:34} {row['native_envelope']}")
            continue
        extra = f" [{row['log']['status']}]" if "log" in row else ""
        lines.append(f"{row['origin']:6} {row['slot'][:34]:34} {row['segment']:22} "
                     f"{row['status_1_6']:13} {row['description'][:14]:14} {row['basis']}{extra}")
    return "\n".join(lines)


def write_receipt(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")


def request_module():
    try:
        from . import request_tutorial_checkpoint
    except ImportError:
        import request_tutorial_checkpoint
    return request_tutorial_checkpoint


def verify_log(args):
    if args.id:
        _, data = load_master(args.vault.resolve(), args.id)
        slot = slot_name(args.slot or ("rv_cp_" + args.id + ".sav"))
    else:
        data, _ = read_regular(args.save)
        slot = args.slot or args.save.name
    expected = describe(parse_save_bytes(data))
    handoffs = [entry for entry in scan_logs(args.log)[1]
                if entry["slot"].lower() == slot.lower() and entry["latched"]]
    record = {"slot": slot, "expected_status_1_6": expected["status_1_6"],
              "segment": expected["segment"],
              "scope": "objective state only; world/script restoration is not proven"}
    if not handoffs:
        record["status"] = "NO_HANDOFF_FOUND"
    elif handoffs[-1]["first_progress"] is None:
        record.update(status="NO_PROGRESS_AFTER_HANDOFF", handoff=handoffs[-1])
    else:
        observed = handoffs[-1]["first_progress"]
        record.update(handoff={key: handoffs[-1][key] for key in ("log", "line", "kind")},
                      observed=observed,
                      status="OBJECTIVES_MATCH_AFTER_LOAD"
                      if observed["status_1_6"] == expected["status_1_6"] else
                      "OBJECTIVES_DIFFER_AFTER_LOAD")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("capture", "restore", "launch", "catalog", "verify-log"))
    parser.add_argument("--id", type=safe_name)
    parser.add_argument("--segment", choices=SEGMENTS, help="launch: pick the one vault master whose derived segment matches")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--user-dir", type=Path)
    parser.add_argument("--content-id", help="Operator-supplied SHA256 identity of unchanged retail content "
                        "(default: RENEGADE_RETAIL_CONTENT_ID)")
    parser.add_argument("--compatibility", default="original-m00-save-v1", help="Save compatibility epoch, not a dev build number")
    parser.add_argument("--slot", help="Existing basename in user/save for capture; target basename for restore/launch")
    parser.add_argument("--build", help="Creating build, recorded as provenance only")
    evidence_group = parser.add_mutually_exclusive_group()
    evidence_group.add_argument("--passed-evidence", type=Path, help="Retained evidence for the operator-confirmed passed segment")
    evidence_group.add_argument("--evidence", type=Path, help="Retained checkpoint receipt; does not claim segment completion")
    parser.add_argument("--offline", action="store_true", help="Confirm the game is stopped before restoring")
    parser.add_argument("--sticky", action="store_true", help="launch: write the retained RVTC1 tutorial-checkpoint-v1.flag")
    parser.add_argument("--receipt", type=Path, help="launch: new receipt path (default under the vault)")
    parser.add_argument("--save", type=Path, action="append", help="catalog/verify-log: an individual .sav file")
    parser.add_argument("--log", type=Path, action="append", help="catalog/verify-log: runtime log to correlate")
    parser.add_argument("--with-vault", action="store_true", help="catalog: include the vault with --user-dir/--save")
    parser.add_argument("--json", type=Path, help="catalog: also write the full catalogue to this new file")
    args = parser.parse_args()
    vault = args.vault.resolve()
    args.vault = vault

    if args.action == "catalog":
        rows = catalog(args)
        print(format_rows(rows))
        if args.json:
            write_receipt(args.json, {"schema": 1, "rows": rows})
        return
    if args.action == "verify-log":
        if not args.log or bool(args.id) == bool(args.save) or (args.save and len(args.save) != 1):
            raise ValueError("verify-log requires --log and exactly one of --id or --save")
        args.save = args.save[0] if args.save else None
        record = verify_log(args)
        print(json.dumps(record, indent=2))
        if record["status"] != "OBJECTIVES_MATCH_AFTER_LOAD":
            sys.exit(1)
        return

    if not args.user_dir:
        raise ValueError(f"{args.action} requires --user-dir")
    user = user_tree(args.user_dir)
    if vault == user or user in vault.parents:
        raise ValueError("Keep immutable checkpoint masters outside the live user tree")
    content_id = content_identity(args.content_id)
    if args.action == "capture":
        if not args.id or not args.slot or not args.build or not (args.passed_evidence or args.evidence):
            raise ValueError("Capture requires id, slot, build, and evidence or passed-evidence")
        slot = args.slot
        if not re.fullmatch(r"[A-Za-z0-9_-]+\.sav", slot, re.IGNORECASE):
            raise ValueError("slot must be a simple .sav basename")
        data, map_name = read_save(user / "save" / slot)
        evidence = (args.passed_evidence or args.evidence).resolve(strict=True)
        if not evidence.is_file() or evidence.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Use a bounded evidence receipt, not an arbitrary directory or dump")
        derived = describe(parse_save_bytes(data))
        metadata = {
            "schema": 1, "id": args.id, "map": map_name, "save_sha256": digest(data),
            "content_id": content_id, "content_id_source": "OPERATOR_SUPPLIED",
            "compatibility": args.compatibility, "created_by_build": args.build,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "segment_status": "OPERATOR_ATTESTED_PASSED" if args.passed_evidence else "UNASSESSED",
            "source_slot": slot,
            "evidence_path": str(evidence), "evidence_sha256": digest(evidence.read_bytes()),
            "cross_build_load_validated": False,
            "derived_segment": derived["segment"], "derived_status_1_6": derived["status_1_6"],
            "derived_segment_source": "ORIGINAL_SAVE_OBJECTIVES",
        }
        checkpoint = vault / args.id
        vault.mkdir(parents=True, exist_ok=True)
        checkpoint.mkdir()  # Never replace an existing master.
        write_new(checkpoint / "checkpoint.sav", data)
        write_new(checkpoint / "manifest.json", (json.dumps(metadata, indent=2) + "\n").encode("ascii"))
        (checkpoint / "checkpoint.sav").chmod(0o444)
        (checkpoint / "manifest.json").chmod(0o444)
        print(json.dumps({"status": "ARCHIVED_UNCHANGED_NATIVE_SAVE", "checkpoint": str(checkpoint),
                          "save_sha256": digest(data), "derived_segment": derived["segment"]}))
        return

    if not args.offline:
        raise ValueError(f"{args.action.capitalize()} requires --offline; stop the game first")
    if args.action == "launch" and args.segment and not args.id:
        args.id = select_by_segment(vault, args.segment)
    if not args.id:
        raise ValueError(f"{args.action} requires --id" + (" or --segment" if args.action == "launch" else ""))
    destination, data, reused = restore_master(vault, args.id, user, content_id, args.compatibility, args.slot)
    status = "REUSED_IDENTICAL_SLOT" if reused else "RESTORED_NEW_SLOT"
    if args.action == "restore":
        print(json.dumps({"status": status + "_NOT_LOAD_VALIDATION", "slot": str(destination),
                          "save_sha256": digest(data)}))
        return
    derived = describe(parse_save_bytes(data))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    receipt = args.receipt or vault / RECEIPTS / f"{args.id}-{stamp}.json"
    record = request_module().queue_request(user, destination.name, receipt, sticky=args.sticky)
    prefix = "RVTC1 sticky tutorial" if args.sticky else "developer {M00|campaign-save}"
    print(json.dumps({
        "status": status + "_LAUNCH_QUEUED_LOAD_UNASSESSED", "checkpoint": args.id,
        "slot": str(destination), "segment": derived["segment"], "basis": derived["basis"],
        "request": record["request"], "receipt": str(receipt),
        "expected_log": [f"A4 checkpoint: {prefix} handoff latched=1 source=save/{destination.name}",
                         f"A3.5 mission progress: frame=0 ... status_1_6={derived['status_1_6']}"],
        "requires_build": "RENEGADE_DEVELOPMENT_CHECKPOINT=1",
    }, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, UnicodeError) as error:
        raise SystemExit(str(error))
