#!/usr/bin/env python3
"""Inventory Renegade cinematic script dependencies without exporting assets."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import struct
import zlib
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any


DEFAULT_ARCHIVES = (
    Path("build/dev136-host/retail/Data/M13.mix"),
    Path("/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/retail/Data/M13.mix"),
)


class MixArchive:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[str, tuple[int, int, int]] = {}
        self._load_index()

    def _load_index(self) -> None:
        size = self.path.stat().st_size
        with self.path.open("rb") as stream:
            header = stream.read(12)
            magic, index_offset, names_offset = struct.unpack("<4sII", header)
            if magic != b"MIX1":
                raise ValueError(f"{self.path}: unsupported MIX magic {magic!r}")
            if not (12 <= index_offset <= size - 4 and 12 <= names_offset <= size - 4):
                raise ValueError(f"{self.path}: invalid MIX offsets")
            stream.seek(index_offset)
            count = struct.unpack("<I", stream.read(4))[0]
            if count > 1000000 or index_offset + 4 + count * 12 > size:
                raise ValueError(f"{self.path}: invalid MIX index bounds")
            index = list(struct.iter_unpack("<III", stream.read(count * 12)))
            stream.seek(names_offset)
            name_count = struct.unpack("<I", stream.read(4))[0]
            if name_count != count:
                raise ValueError(f"{self.path}: name count differs from index count")
            for entry_index in range(count):
                raw_length = stream.read(1)
                if not raw_length:
                    raise ValueError(f"{self.path}: truncated name table")
                length = raw_length[0]
                raw_name = stream.read(length)
                if len(raw_name) != length or not raw_name.endswith(b"\0"):
                    raise ValueError(f"{self.path}: invalid name table entry")
                name = raw_name[:-1].decode("ascii")
                crc, offset, bytes_ = index[entry_index]
                if offset < 12 or bytes_ < 0 or offset + bytes_ > size:
                    raise ValueError(f"{self.path}: invalid payload bounds for {name}")
                self.entries[name.lower()] = (crc, offset, bytes_)

    def read_text(self, name: str) -> str:
        payload = self.read_binary(name)
        return payload.decode("latin1", errors="replace")

    def read_binary(self, name: str) -> bytes:
        entry = self.entries.get(name.lower())
        if entry is None:
            raise KeyError(name)
        crc, offset, bytes_ = entry
        expected_crc = zlib.crc32(name.upper().encode("ascii"))
        if crc != expected_crc:
            raise ValueError(f"{self.path}: CRC/name mismatch for {name}")
        with self.path.open("rb") as stream:
            stream.seek(offset)
            payload = stream.read(bytes_)
        return payload


def parse_command(line: str) -> tuple[int, str, list[str]] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith(";"):
        return None
    match = re.match(r"^(-?\d+)\s+(.+)$", stripped)
    if match is None:
        return None
    frame = int(match.group(1))
    try:
        row = next(csv.reader([match.group(2)], skipinitialspace=True))
    except csv.Error:
        return None
    if not row:
        return None
    command = row[0].strip().lower()
    args = [item.strip().strip('"') for item in row[1:]]
    return frame, command, args


def canonical(values: set[str]) -> list[str]:
    chosen: dict[str, str] = {}
    for value in values:
        if not value:
            continue
        chosen.setdefault(value.lower(), value)
    return [chosen[key] for key in sorted(chosen)]


def scan(archive: MixArchive, entry: str) -> dict[str, Any]:
    queue: deque[str] = deque([entry.lower()])
    visited: set[str] = set()
    dependencies: dict[str, set[str]] = defaultdict(set)
    commands: Counter[str] = Counter()
    command_records: list[dict[str, Any]] = []
    text_references: list[dict[str, str]] = []

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        text = archive.read_text(current)
        for line_number, line in enumerate(text.splitlines(), start=1):
            parsed = parse_command(line)
            if parsed is None:
                continue
            frame, command, args = parsed
            commands[command] += 1
            command_records.append({
                "file": current,
                "line": line_number,
                "frame": frame,
                "command": command,
                "args": args,
            })
            if command == "create_object" and len(args) >= 2:
                dependencies["cinematic_models"].add(args[1])
            elif command == "create_real_object" and len(args) >= 2:
                dependencies["real_object_presets"].add(args[1])
            elif command == "play_animation" and len(args) >= 2:
                dependencies["animations"].add(args[1])
            elif command == "play_audio" and args:
                dependencies["audio"].add(args[0])

            for arg in args:
                candidate = arg.lower()
                if not candidate.endswith(".txt"):
                    candidate = candidate + ".txt"
                if candidate in archive.entries and candidate not in visited:
                    queue.append(candidate)
                    text_references.append({
                        "from": current,
                        "to": candidate,
                        "command": command,
                    })

    return {
        "schema_version": 1,
        "archive": str(archive.path),
        "entry": entry,
        "visited_text_files": sorted(visited),
        "text_references": text_references,
        "command_counts": dict(sorted(commands.items())),
        "dependencies": {
            "cinematic_models": canonical(dependencies["cinematic_models"]),
            "real_object_presets": canonical(dependencies["real_object_presets"]),
            "animations": canonical(dependencies["animations"]),
            "audio": canonical(dependencies["audio"]),
        },
        "command_record_count": len(command_records),
    }


def archive_inventory(archive: MixArchive) -> dict[str, Any]:
    suffix_counts: Counter[str] = Counter()
    entries: list[dict[str, Any]] = []
    for name, (crc, offset, bytes_) in sorted(archive.entries.items()):
        suffix = Path(name).suffix.lower() or "<none>"
        suffix_counts[suffix] += 1
        entries.append({
            "name": name,
            "suffix": suffix,
            "crc32": f"{crc:08x}",
            "offset": offset,
            "bytes": bytes_,
        })
    return {
        "entry_count": len(entries),
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "entries": entries,
    }


def scan_all_text(archive: MixArchive) -> dict[str, Any]:
    combined_dependencies: dict[str, set[str]] = defaultdict(set)
    per_file: dict[str, Any] = {}
    all_commands: Counter[str] = Counter()
    referenced_scripts: set[str] = set()
    custom_messages: set[str] = set()
    object_slots: Counter[str] = Counter()

    for name in sorted(entry for entry in archive.entries if entry.endswith(".txt")):
        text = archive.read_text(name)
        commands: Counter[str] = Counter()
        dependencies: dict[str, set[str]] = defaultdict(set)
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            parsed = parse_command(line)
            if parsed is None:
                continue
            frame, command, args = parsed
            commands[command] += 1
            all_commands[command] += 1
            if args:
                object_slots[f"{command}:{args[0]}"] += 1
            record = {
                "line": line_number,
                "frame": frame,
                "command": command,
                "args": args,
            }
            records.append(record)
            if command == "create_object" and len(args) >= 2:
                dependencies["cinematic_models"].add(args[1])
                combined_dependencies["cinematic_models"].add(args[1])
            elif command == "create_real_object" and len(args) >= 2:
                dependencies["real_object_presets"].add(args[1])
                combined_dependencies["real_object_presets"].add(args[1])
            elif command == "play_animation" and len(args) >= 2:
                dependencies["animations"].add(args[1])
                combined_dependencies["animations"].add(args[1])
            elif command == "play_audio" and args:
                dependencies["audio"].add(args[0])
                combined_dependencies["audio"].add(args[0])
            elif command == "attach_script" and len(args) >= 2:
                referenced_scripts.add(args[1])
                dependencies["scripts"].add(args[1])
                combined_dependencies["scripts"].add(args[1])
            elif command == "send_custom" and len(args) >= 3:
                custom_messages.add(args[2])
                dependencies["custom_messages"].add(args[2])
                combined_dependencies["custom_messages"].add(args[2])

        per_file[name] = {
            "command_counts": dict(sorted(commands.items())),
            "dependencies": {
                key: canonical(value)
                for key, value in sorted(dependencies.items())
            },
            "command_record_count": len(records),
        }

    return {
        "text_file_count": len(per_file),
        "command_counts": dict(sorted(all_commands.items())),
        "dependencies": {
            key: canonical(value)
            for key, value in sorted(combined_dependencies.items())
        },
        "referenced_scripts": canonical(referenced_scripts),
        "custom_messages": canonical(custom_messages),
        "slot_command_counts": dict(sorted(object_slots.items())),
        "files": per_file,
    }


def source_inventory(root: Path) -> dict[str, Any]:
    source_roots = [root / "staging" / "scripts", root / "staging" / "combat", root / "port"]
    patterns = ("M13", "MX0_", "X00", "x00", "Test_Cinematic", "Mission00", "M00_")
    files: list[dict[str, Any]] = []
    script_registrations: set[str] = set()
    function_names: set[str] = set()
    includes: set[str] = set()

    for source_root in source_roots:
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*")):
            if path.suffix.lower() not in (".cpp", ".h", ".hpp", ".c"):
                continue
            try:
                text = path.read_text(encoding="latin1")
            except OSError:
                continue
            matched_lines = []
            for line_number, line in enumerate(text.splitlines(), start=1):
                if any(pattern in line for pattern in patterns):
                    matched_lines.append({
                        "line": line_number,
                        "text": line.strip()[:240],
                    })
            for script_match in re.finditer(r'DECLARE_SCRIPT\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)', text):
                script_registrations.add(script_match.group(1))
            for include_match in re.finditer(r'^\s*#\s*include\s+[<"]([^>"]+)[>"]', text, re.MULTILINE):
                includes.add(include_match.group(1))
            for line in text.splitlines():
                stripped = line.strip()
                if ("(" not in stripped or ")" not in stripped or stripped.endswith(";") or
                        stripped.startswith(("#", "//", "/*", "*"))):
                    continue
                if not any(pattern.lower() in stripped.lower()
                           for pattern in ("m13", "mx0", "x00", "mission00", "cinematic")):
                    continue
                prefix = stripped.split("(", 1)[0].strip()
                if not prefix:
                    continue
                function_names.add(prefix.split()[-1].strip("*&"))
            if matched_lines:
                files.append({
                    "path": str(path.relative_to(root)),
                    "matched_lines": matched_lines[:80],
                    "match_count": len(matched_lines),
                })

    return {
        "source_roots": [str(path.relative_to(root)) for path in source_roots if path.exists()],
        "script_registrations_count": len(script_registrations),
        "script_registrations": canonical(script_registrations),
        "interesting_functions": canonical(function_names),
        "include_count": len(includes),
        "includes": canonical(includes),
        "matched_file_count": len(files),
        "matched_files": files,
    }


def parse_microchunks(payload: bytes, start: int, end: int, limit: int = 256) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    offset = start
    while offset + 2 <= end and len(records) < limit:
        chunk_id = payload[offset]
        length = payload[offset + 1]
        data_start = offset + 2
        data_end = data_start + length
        if data_end > end:
            records.append({
                "offset": offset,
                "id": chunk_id,
                "length": length,
                "truncated": True,
            })
            break
        value: dict[str, Any] = {}
        data = payload[data_start:data_end]
        if data and all((32 <= byte < 127) or byte == 0 for byte in data):
            value["ascii"] = data.rstrip(b"\0").decode("ascii", errors="replace")
        if length in (1, 2, 4):
            value["uint_le"] = int.from_bytes(data, "little", signed=False)
        records.append({
            "offset": offset,
            "id": chunk_id,
            "length": length,
            **value,
        })
        offset = data_end
    return records


def walk_chunks(payload: bytes, start: int = 0, end: int | None = None,
                depth: int = 0, limit: int = 50000) -> list[dict[str, Any]]:
    if end is None:
        end = len(payload)
    records: list[dict[str, Any]] = []
    offset = start
    while offset + 8 <= end and len(records) < limit:
        raw_id, raw_size = struct.unpack_from("<II", payload, offset)
        has_children = bool(raw_size & 0x80000000)
        size = raw_size & 0x7FFFFFFF
        data_start = offset + 8
        data_end = data_start + size
        record: dict[str, Any] = {
            "offset": offset,
            "depth": depth,
            "id": f"0x{raw_id:08x}",
            "size": size,
            "has_children": has_children,
        }
        if data_end > end:
            record["truncated"] = True
            records.append(record)
            break
        if has_children:
            records.append(record)
            records.extend(walk_chunks(payload, data_start, data_end, depth + 1,
                                       limit - len(records)))
        elif depth == 0 and size > 0:
            microchunks = parse_microchunks(payload, data_start, data_end, limit=64)
            if microchunks:
                record["microchunks"] = microchunks
            records.append(record)
        offset = data_end
    if offset != end and len(records) < limit:
        records.append({
            "offset": offset,
            "depth": depth,
            "trailing_bytes": end - offset,
        })
    return records


def chunk_inventory(archive: MixArchive) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name in sorted(entry for entry in archive.entries if entry.endswith((".ldd", ".lsd"))):
        payload = archive.read_binary(name)
        chunks = walk_chunks(payload)
        top_level = [record for record in chunks if record.get("depth") == 0 and "id" in record]
        top_level_counts = Counter(record["id"] for record in top_level)
        all_id_counts = Counter(record["id"] for record in chunks if "id" in record)
        max_depth = max((int(record.get("depth", 0)) for record in chunks), default=0)
        files[name] = {
            "bytes": len(payload),
            "chunk_count": sum(1 for record in chunks if "id" in record),
            "max_depth": max_depth,
            "top_level_chunk_count": len(top_level),
            "top_level_counts": dict(sorted(top_level_counts.items())),
            "top_level_chunks": top_level,
            "most_common_chunk_ids": dict(all_id_counts.most_common(64)),
            "sample_chunks": chunks[:256],
        }
    return {
        "file_count": len(files),
        "files": files,
        "limits": [
            "Chunk inventory records headers, child flags, sizes and small microchunk metadata only; it does not instantiate PersistFactory objects.",
            "Object definition names, pointer fixups, and script observer state still require original-engine SaveLoad instrumentation.",
        ],
    }


def mission_inventory(archive: MixArchive, root: Path) -> dict[str, Any]:
    text_scan = scan_all_text(archive)
    source_scan = source_inventory(root)
    binary_scan = chunk_inventory(archive)
    source_scripts_lower = {name.lower() for name in source_scan["script_registrations"]}
    data_scripts = set(text_scan["referenced_scripts"])
    return {
        "schema_version": 1,
        "archive": str(archive.path),
        "archive_inventory": archive_inventory(archive),
        "text_inventory": text_scan,
        "binary_inventory": binary_scan,
        "source_inventory": source_scan,
        "gaps": {
            "data_scripts_without_source_declare_name_match": canonical({
                name for name in data_scripts if name.lower() not in source_scripts_lower
            }),
        },
        "limits": [
            "MIX inventory records names, sizes, offsets, CRCs and script text dependencies only; it does not export retail payloads.",
            "LDD/LSD binary inventory records chunk structure only; object graph semantics still require original-engine SaveLoad instrumentation.",
            "W3D internal texture/material references and DDB preset transitive references still require original-engine or dedicated binary inventory.",
            "Source inventory is static text coverage; it does not prove compiled linkage or runtime execution.",
        ],
    }


def extract_runtime_string_array(source: str, array_name: str) -> set[str]:
    match = re.search(
        r"const char \*const\s+" + re.escape(array_name) + r"\[\]\s*=\s*\{(?P<body>.*?)\};",
        source,
        re.DOTALL,
    )
    if match is None:
        return set()
    return set(re.findall(r'"([^"]+)"', match.group("body")))


def compare_source(scan_result: dict[str, Any], source_path: Path) -> dict[str, Any]:
    source = source_path.read_text(encoding="utf-8")
    prepared_models = extract_runtime_string_array(source, "prepare_models")
    prepared_hanims = extract_runtime_string_array(source, "prepare_hanims")
    prepared_presets = extract_runtime_string_array(source, "prepare_presets")

    deps = scan_result["dependencies"]
    models = set(deps["cinematic_models"])
    animations = set(deps["animations"])
    presets = set(deps["real_object_presets"])

    def missing_authored(required: set[str], prepared: set[str]) -> set[str]:
        prepared_lower = {value.lower() for value in prepared}
        return {value for value in required if value.lower() not in prepared_lower}

    def extra_prepared(required: set[str], prepared: set[str]) -> set[str]:
        required_lower = {value.lower() for value in required}
        return {value for value in prepared if value.lower() not in required_lower}

    runtime_preparation_scope = []
    if prepared_models:
        runtime_preparation_scope.append("cinematic_models")
    if prepared_hanims:
        runtime_preparation_scope.append("animations")
    if prepared_presets:
        runtime_preparation_scope.append("real_object_presets")

    return {
        "source": str(source_path),
        "runtime_preparation_scope": runtime_preparation_scope,
        "prepared_counts": {
            "cinematic_models": len(prepared_models),
            "animations": len(prepared_hanims),
            "real_object_presets": len(prepared_presets),
        },
        "missing": {
            "cinematic_models": canonical(missing_authored(models, prepared_models)),
            "animations": canonical(missing_authored(animations, prepared_hanims)),
            "real_object_presets": canonical(missing_authored(presets, prepared_presets)),
        },
        "extra": {
            "cinematic_models": canonical(extra_prepared(models, prepared_models)),
            "animations": canonical(extra_prepared(animations, prepared_hanims)),
            "real_object_presets": canonical(extra_prepared(presets, prepared_presets)),
        },
    }


def default_archive() -> Path:
    for path in DEFAULT_ARCHIVES:
        if path.exists():
            return path
    raise FileNotFoundError("no default M13.mix found; pass --archive")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=None)
    parser.add_argument("--entry", default="x00_intro.txt")
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--fail-on-missing-source-prep", action="store_true")
    parser.add_argument("--mission-inventory", action="store_true")
    parser.add_argument("--project-root", type=Path, default=Path("."))
    args = parser.parse_args()

    archive = MixArchive(args.archive if args.archive is not None else default_archive())
    if args.mission_inventory:
        result = mission_inventory(archive, args.project_root.resolve())
    else:
        result = scan(archive, args.entry)
    if args.source is not None and not args.mission_inventory:
        result["source_comparison"] = compare_source(result, args.source)
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    if not args.quiet:
        print(payload, end="")
    if args.fail_on_missing_source_prep and args.source is not None:
        missing = result["source_comparison"]["missing"]
        scope = result["source_comparison"].get("runtime_preparation_scope", missing.keys())
        if any(missing[key] for key in scope):
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
