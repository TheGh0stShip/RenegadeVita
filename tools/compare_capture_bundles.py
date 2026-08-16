#!/usr/bin/env python3
"""Compare two Renegade Vita developer capture bundles."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from pathlib import Path
from typing import Any


def load_bundle(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    state_path = path / "state.json"
    frames_path = path / "frames.csv"
    if not state_path.is_file() or not frames_path.is_file():
        raise ValueError(f"{path}: expected state.json and frames.csv")
    with state_path.open(encoding="utf-8") as stream:
        state = json.load(stream)
    with frames_path.open(newline="", encoding="utf-8") as stream:
        frames = list(csv.DictReader(stream))
    if state.get("schema_version") not in (1, 2):
        raise ValueError(f"{path}: unsupported capture schema")
    return state, frames


def numbers(frames: list[dict[str, str]], key: str) -> list[float]:
    values: list[float] = []
    for frame in frames:
        value = frame.get(key, "")
        if value != "":
            values.append(float(value))
    return values


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return math.nan
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def performance(frames: list[dict[str, str]]) -> dict[str, float]:
    ordinary = numbers(frames, "ordinary_frame_us")
    mean_us = statistics.fmean(ordinary) if ordinary else math.nan
    return {
        "samples": float(len(ordinary)),
        "min_ms": min(ordinary) / 1000.0 if ordinary else math.nan,
        "mean_ms": mean_us / 1000.0,
        "median_ms": statistics.median(ordinary) / 1000.0 if ordinary else math.nan,
        "p95_ms": percentile(ordinary, 0.95) / 1000.0,
        "p99_ms": percentile(ordinary, 0.99) / 1000.0,
        "max_ms": max(ordinary) / 1000.0 if ordinary else math.nan,
        "mean_fps": 1_000_000.0 / mean_us if ordinary and mean_us else math.nan,
        "slow_over_16_7ms": float(sum(value > 16_667.0 for value in ordinary)),
        "slow_over_33_3ms": float(sum(value > 33_333.0 for value in ordinary)),
        "capture_stall_ms": sum(numbers(frames, "capture_readback_us")) / 1000.0,
    }


STAGES = (
    "input_us", "game_update_us", "physics_us", "camera_us", "visibility_us",
    "render_us", "present_us", "housekeeping_us",
)


def stage_performance(frames: list[dict[str, str]]) -> dict[str, float]:
    result: dict[str, float] = {}
    for stage in STAGES:
        values = numbers(frames, stage)
        result[f"{stage}.samples"] = float(len(values))
        result[f"{stage}.mean_ms"] = statistics.fmean(values) / 1000.0 if values else math.nan
        result[f"{stage}.p95_ms"] = percentile(values, 0.95) / 1000.0
    return result


PATHS = {
    "semantic": [
        "world.definitions", "world.static_objects", "world.dynamic_objects",
        "world.lights", "world.render_object_nodes", "world.meshes",
        "world.vertices", "world.polygons", "world.prototypes",
        "world.visibility_objects", "world.visibility_sectors",
        "world.definition_checksum", "world.object_checksum",
        "world.render_checksum", "world.prototype_checksum",
        "player.present", "player.object_id", "player.definition", "player.type",
    ],
    "renderer": [
        "renderer.draw_calls", "renderer.mesh_submissions", "renderer.vertices",
        "renderer.triangles", "renderer.indexed_draw_calls",
        "renderer.indexed_triangles", "renderer.material_passes",
        "renderer.textures_resident", "renderer.texture_bytes_resident",
        "renderer.texture_uploads", "renderer.texture_binds",
        "renderer.state_changes", "renderer.rejected", "renderer.unsupported",
        "renderer.backend_errors", "renderer.geometry_checksum",
        "renderer.indexed_checksum",
    ],
    "memory": [
        "memory.system_user_free", "memory.system_cdram_free",
        "memory.system_phycont_free", "memory.vitagl_ram_free",
        "memory.vitagl_vram_free", "memory.vitagl_slow_free",
        "memory.vitagl_all_free", "memory.system_user_free_low_water",
        "memory.system_cdram_free_low_water",
        "memory.system_phycont_free_low_water",
        "memory.vitagl_ram_free_low_water",
        "memory.vitagl_vram_free_low_water",
        "memory.vitagl_slow_free_low_water",
        "memory.vitagl_all_free_low_water",
    ],
}


def lookup(value: dict[str, Any], path: str) -> Any:
    current: Any = value
    for component in path.split("."):
        if not isinstance(current, dict) or component not in current:
            return None
        current = current[component]
    return current


def change(before: Any, after: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"before": before, "after": after, "changed": before != after}
    if isinstance(before, (int, float)) and not isinstance(before, bool) and \
            isinstance(after, (int, float)) and not isinstance(after, bool):
        item["delta"] = after - before
        item["percent"] = ((after - before) * 100.0 / before) if before else None
    return item


def compare(first_path: Path, second_path: Path) -> dict[str, Any]:
    first_state, first_frames = load_bundle(first_path)
    second_state, second_frames = load_bundle(second_path)
    output: dict[str, Any] = {
        "before": str(first_path), "after": str(second_path), "performance": {},
        "stages": {}, "semantic": {}, "renderer": {}, "memory": {},
    }
    first_perf = performance(first_frames)
    second_perf = performance(second_frames)
    for key in first_perf:
        output["performance"][key] = change(first_perf[key], second_perf[key])
    first_stages = stage_performance(first_frames)
    second_stages = stage_performance(second_frames)
    for key in first_stages:
        output["stages"][key] = change(first_stages[key], second_stages[key])
    for category, paths in PATHS.items():
        for path in paths:
            output[category][path] = change(
                lookup(first_state, path), lookup(second_state, path))
    return output


def format_value(value: Any) -> str:
    if isinstance(value, float):
        return "n/a" if math.isnan(value) else f"{value:.3f}"
    return str(value)


def print_text(result: dict[str, Any]) -> None:
    print(f"Capture comparison\n  before: {result['before']}\n  after:  {result['after']}")
    for category in ("performance", "stages", "memory", "renderer", "semantic"):
        print(f"\n{category.capitalize()}")
        for name, item in result[category].items():
            marker = "CHANGED" if item["changed"] else "same"
            suffix = ""
            if "delta" in item:
                suffix = f" delta={format_value(item['delta'])}"
                if item.get("percent") is not None:
                    suffix += f" ({item['percent']:+.2f}%)"
            print(f"  {name}: {format_value(item['before'])} -> "
                  f"{format_value(item['after'])} [{marker}]{suffix}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        result = compare(args.before, args.after)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    else:
        print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
