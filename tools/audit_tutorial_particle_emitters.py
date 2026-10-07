#!/usr/bin/env python3
"""Inventory original W3D particle emitters for the tutorial route (diagnostic only).

Reads unchanged retail archives through the existing pure-Python MIX reader and
decodes W3D_CHUNK_EMITTER (0x500) definitions with the field layout of
staging/ww3d2/w3d_file.h. Derived buffer sizes follow the original
ParticleEmitterClass constructor (part_emt.cpp):

    max_num = BurstSize * emit_rate * (max_age + 1)   (float math, int truncation)
    capped by MaxEmissions when > 0, then max(max_num, 2)
    LodCount (runtime clones) = min(max_num, 17)       (part_buf.cpp copy ctor)

and the per-particle visual arrays the ParticleBufferClass Reset_* functions
allocate. Nothing here is a runtime format: the output is a JSON summary for
reports. No compiler, emulator, device or retail write is involved.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from renegade_cinematic_dependency_scan import MixArchive  # noqa: E402

W3D_CHUNK_EMITTER = 0x500
W3D_CHUNK_EMITTER_HEADER = 0x501
W3D_CHUNK_EMITTER_INFO = 0x503
W3D_CHUNK_EMITTER_INFOV2 = 0x504
W3D_CHUNK_EMITTER_PROPS = 0x505
W3D_CHUNK_EMITTER_LINE_PROPERTIES = 0x509
W3D_CHUNK_EMITTER_ROTATION_KEYFRAMES = 0x50A
W3D_CHUNK_EMITTER_FRAME_KEYFRAMES = 0x50B
W3D_CHUNK_EMITTER_BLUR_TIME_KEYFRAMES = 0x50C

RENDER_MODES = {0: "tri", 1: "quad", 2: "line", 3: "linegrp_tetra", 4: "linegrp_prism"}

EPS_BYTE = 0.0038          # part_buf.cpp Reset_Colors/Reset_Opacity
EPS_SIZE = 1.0e-12          # part_buf.cpp Reset_Size
EPS_ORIENT = 2.77777778e-4  # Reset_Rotations
EPS_FRAME = 0.1            # Reset_Frames


def iter_chunks(data: bytes, start: int = 0, end: int | None = None):
    end = len(data) if end is None else end
    pos = start
    while pos + 8 <= end:
        chunk_id, raw_size = struct.unpack_from("<II", data, pos)
        size = raw_size & 0x7FFFFFFF
        body = pos + 8
        if body + size > end:
            return
        yield chunk_id, body, size
        pos = body + size


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def original_max_num(burst: int, rate: float, lifetime: float, max_emissions: float) -> int:
    burst = burst if burst != 0 else 1
    max_age = lifetime if lifetime > 0.0 else 1.0
    product = f32(f32(float(burst) * f32(rate)) * f32(max_age + 1.0))
    max_num = int(product) if math.isfinite(product) else 0
    max_particles = int(max_emissions) if math.isfinite(max_emissions) else 0
    if max_particles > 0:
        max_num = min(max_num, max_particles)
    return max(max_num, 2)


def decode_emitter(data: bytes, body: int, size: int) -> dict | None:
    record: dict = {"version": None}
    rotation = frame = blur = None
    for chunk_id, sub, sub_size in iter_chunks(data, body, body + size):
        if chunk_id == W3D_CHUNK_EMITTER_HEADER and sub_size >= 20:
            version, name = struct.unpack_from("<I16s", data, sub)
            record["version"] = version
            record["name"] = name.split(b"\0", 1)[0].decode("latin1")
        elif chunk_id == W3D_CHUNK_EMITTER_INFO and sub_size >= 260 + 4 * 16:
            texture = data[sub:sub + 260].split(b"\0", 1)[0].decode("latin1")
            (start_size, end_size, lifetime, rate, max_emissions, vel_rand,
             pos_rand, fade, gravity, elasticity) = struct.unpack_from("<10f", data, sub + 260)
            record.update(texture=texture, lifetime=lifetime, emission_rate=rate,
                          max_emissions=max_emissions)
        elif chunk_id == W3D_CHUNK_EMITTER_INFOV2 and sub_size >= 4:
            burst = struct.unpack_from("<I", data, sub)[0]
            # BurstSize + two 32-byte randomizers + two floats + 16-byte shader
            mode_offset = sub + 4 + 32 + 32 + 8 + 16
            render_mode, frame_mode = struct.unpack_from("<II", data, mode_offset)
            record.update(burst_size=burst, render_mode=render_mode, frame_mode=frame_mode)
        elif chunk_id == W3D_CHUNK_EMITTER_PROPS and sub_size >= 40:
            ck, ok, sk = struct.unpack_from("<III", data, sub)
            color_rand = struct.unpack_from("<4B", data, sub + 12)
            opacity_rand, size_rand = struct.unpack_from("<ff", data, sub + 16)
            record.update(color_keys=max(ck - 1, 0), opacity_keys=max(ok - 1, 0),
                          size_keys=max(sk - 1, 0),
                          color_random=max(color_rand[:3]) / 255.0,
                          opacity_random=opacity_rand, size_random=size_rand)
        elif chunk_id == W3D_CHUNK_EMITTER_ROTATION_KEYFRAMES and sub_size >= 24:
            count, rnd, orient_rnd = struct.unpack_from("<Iff", data, sub)
            start = struct.unpack_from("<ff", data, sub + 16)[1]
            rotation = (count, rnd, orient_rnd, start)
        elif chunk_id == W3D_CHUNK_EMITTER_FRAME_KEYFRAMES and sub_size >= 16:
            count, rnd = struct.unpack_from("<If", data, sub)
            frame = (count, rnd)
        elif chunk_id == W3D_CHUNK_EMITTER_BLUR_TIME_KEYFRAMES and sub_size >= 12:
            count, rnd = struct.unpack_from("<If", data, sub)
            blur = (count, rnd)
    if "name" not in record or "lifetime" not in record:
        return None
    v2 = (record["version"] or 0) > 0x00010000 and "render_mode" in record
    if not v2:
        record.update(burst_size=1, render_mode=0, frame_mode=0, color_keys=1,
                      opacity_keys=1, size_keys=1, color_random=0.0,
                      opacity_random=0.0, size_random=0.0, legacy_v1=True)
    mode = record["render_mode"]
    record["render_mode_name"] = RENDER_MODES.get(mode, str(mode))
    record["max_num"] = original_max_num(record["burst_size"], record["emission_rate"],
                                         record["lifetime"], record["max_emissions"])
    record["lod_count"] = min(record["max_num"], 17)
    linegroup = mode in (3, 4)
    arrays = []
    if record["color_keys"] > 0 or record["color_random"] >= EPS_BYTE:
        arrays.append("color")
    if record["opacity_keys"] > 0 or abs(record["opacity_random"]) >= EPS_BYTE:
        arrays.append("alpha")
    if record["size_keys"] > 0 or abs(record["size_random"]) >= EPS_SIZE:
        arrays.append("size")
    if rotation is not None:
        count, rnd, orient_rnd, start = rotation
        if count > 0 or abs(rnd) >= EPS_ORIENT or abs(orient_rnd) >= EPS_ORIENT or abs(start) >= EPS_ORIENT:
            arrays.append("orientation")
    if frame is not None and (frame[0] > 0 or abs(frame[1]) >= EPS_FRAME):
        arrays.append("ucoord" if linegroup else "frame")
    if linegroup:
        arrays.append("tailposition")
    record["visual_arrays"] = arrays
    lifetime = record["lifetime"] if record["lifetime"] > 0 else 1.0
    continuous = int(record["max_emissions"]) <= 0
    steady = record["burst_size"] * max(record["emission_rate"], 0.0) * lifetime
    record["continuous"] = continuous
    record["steady_live_estimate"] = int(min(record["max_num"], steady)) if continuous else None
    return record


def scan_archive(path: Path) -> list[dict]:
    archive = MixArchive(path)
    out = []
    for name in sorted(archive.entries):
        if not name.endswith(".w3d"):
            continue
        data = archive.read_binary(name)
        for chunk_id, body, size in iter_chunks(data):
            if chunk_id == W3D_CHUNK_EMITTER:
                record = decode_emitter(data, body, size)
                if record is not None:
                    record["archive"] = path.name
                    record["file"] = name
                    out.append(record)
    return out


def reference_text(path: Path, suffixes: tuple[str, ...]) -> bytes:
    archive = MixArchive(path)
    blobs = []
    for name in sorted(archive.entries):
        if name.endswith(suffixes):
            blobs.append(archive.read_binary(name).lower())
    return b"\n".join(blobs)


def summarize(records: list[dict], tutorial_refs: bytes, always_refs: bytes) -> dict:
    for record in records:
        key = record["name"].lower().encode("latin1")
        stem = Path(record["file"]).stem.lower().encode("latin1")
        record["referenced_by_m00_level"] = key in tutorial_refs or stem in tutorial_refs
        record["referenced_by_always_ini"] = key in always_refs or stem in always_refs
    tutorial = [r for r in records if r["archive"].lower() == "m00_tutorial.mix" or r["referenced_by_m00_level"]]

    def aggregate(rows: list[dict]) -> dict:
        if not rows:
            return {"count": 0}
        max_nums = sorted(r["max_num"] for r in rows)
        overhead = [r["max_num"] / max(r["steady_live_estimate"], 1)
                    for r in rows if r["continuous"] and r["steady_live_estimate"]]
        return {
            "count": len(rows),
            "max_num_median": max_nums[len(max_nums) // 2],
            "max_num_p90": max_nums[min(len(max_nums) - 1, int(len(max_nums) * 0.9))],
            "max_num_max": max_nums[-1],
            "lod_count_below_17": sum(1 for r in rows if r["lod_count"] < 17),
            "render_modes": {m: sum(1 for r in rows if r["render_mode_name"] == m)
                             for m in sorted({r["render_mode_name"] for r in rows})},
            "continuous": sum(1 for r in rows if r["continuous"]),
            "with_visual_arrays": sum(1 for r in rows if r["visual_arrays"]),
            "mean_visual_arrays": round(sum(len(r["visual_arrays"]) for r in rows) / len(rows), 2),
            "continuous_max_num_over_steady_live_median":
                round(sorted(overhead)[len(overhead) // 2], 2) if overhead else None,
        }

    keep = ("archive", "file", "name", "render_mode_name", "lifetime", "emission_rate",
            "burst_size", "max_emissions", "max_num", "lod_count", "continuous",
            "steady_live_estimate", "visual_arrays", "referenced_by_m00_level",
            "referenced_by_always_ini")
    top = sorted(tutorial, key=lambda r: r["max_num"], reverse=True)[:25]
    return {
        "schema": "renegade-vita-particle-emitter-inventory-v1",
        "all_emitters": aggregate(records),
        "tutorial_emitters": aggregate(tutorial),
        "surface_or_weapon_ini_emitters": aggregate([r for r in records if r["referenced_by_always_ini"]]),
        "tutorial_top_by_max_num": [{k: r[k] for k in keep} for r in top],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="retail Data directory (read only)")
    parser.add_argument("--json", type=Path, help="write the summary here instead of stdout")
    args = parser.parse_args(argv)
    archives = [p for p in (args.data / n for n in ("M00_Tutorial.mix", "always.dat", "Always2.dat", "always3.dat")) if p.exists()]
    records: list[dict] = []
    for path in archives:
        records.extend(scan_archive(path))
    tutorial_refs = reference_text(args.data / "M00_Tutorial.mix", (".ldd", ".lsd", ".w3d"))
    always_refs = reference_text(args.data / "always.dat", (".ini",))
    summary = summarize(records, tutorial_refs, always_refs)
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.json:
        args.json.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
