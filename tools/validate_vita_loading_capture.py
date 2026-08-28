#!/usr/bin/env python3

"""Validate one returned A3.5 loading-screen capture bundle.

This intentionally does not claim visual acceptance. It proves that the
returned evidence is candidate-matched, schema-v4, native-size, nonblank,
spatially broad enough to reject a tiny/misplaced loading bar as the "screen",
and records the renderer/loading ownership facts required before a human visual
gate can accept a route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


EXPECTED_FRAMEBUFFER = (960, 544)
EXPECTED_LOGICAL = (640, 480)
BMP_FILE_HEADER = struct.Struct("<2sIHHI")
BMP_INFO_HEADER_PREFIX = struct.Struct("<IiiHHI")
MIN_CONTENT_WIDTH_RATIO = 0.74
MIN_CONTENT_HEIGHT_RATIO = 0.70


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: object) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def inspect_bmp(path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    data = path.read_bytes()
    checks: list[dict[str, object]] = []
    info: dict[str, object] = {"bytes": len(data)}

    checks.append(check("bmp_minimum_header", len(data) >= 54, len(data)))
    if len(data) < 54:
        return info, checks

    signature, file_size, _reserved1, _reserved2, pixel_offset = BMP_FILE_HEADER.unpack_from(data, 0)
    dib_size, width, height, planes, bits_per_pixel, compression = BMP_INFO_HEADER_PREFIX.unpack_from(data, 14)
    abs_height = abs(height)
    row_bytes = ((width * bits_per_pixel + 31) // 32) * 4 if width > 0 else 0
    pixel_bytes = row_bytes * abs_height
    info.update(
        signature=signature.decode("ascii", errors="replace"),
        file_size=file_size,
        pixel_offset=pixel_offset,
        dib_size=dib_size,
        width=width,
        height=height,
        planes=planes,
        bits_per_pixel=bits_per_pixel,
        compression=compression,
        row_bytes=row_bytes,
        pixel_bytes=pixel_bytes,
    )
    checks.extend(
        (
            check("bmp_signature", signature == b"BM", info["signature"]),
            check("bmp_file_size_matches", file_size == len(data), {"header": file_size, "actual": len(data)}),
            check("bmp_dib_header_supported", dib_size >= 40, dib_size),
            check("bmp_dimensions", (width, abs_height) == EXPECTED_FRAMEBUFFER, {"width": width, "height": height}),
            check("bmp_planes", planes == 1, planes),
            check("bmp_24bpp", bits_per_pixel == 24, bits_per_pixel),
            check("bmp_uncompressed", compression == 0, compression),
            check("bmp_pixel_range", pixel_offset >= 54 and pixel_offset + pixel_bytes <= len(data), {"offset": pixel_offset, "pixel_bytes": pixel_bytes}),
        )
    )

    nonblack = 0
    min_x = width
    min_y = abs_height
    max_x = -1
    max_y = -1
    edge_band = max(1, min(width, abs_height) // 20) if width > 0 and abs_height > 0 else 1
    edge_counts = {"left": 0, "right": 0, "top": 0, "bottom": 0}
    edge_totals = {
        "left": edge_band * abs_height if width > 0 else 1,
        "right": edge_band * abs_height if width > 0 else 1,
        "top": width * edge_band if abs_height > 0 else 1,
        "bottom": width * edge_band if abs_height > 0 else 1,
    }
    quadrant_counts = {"top_left": 0, "top_right": 0, "bottom_left": 0, "bottom_right": 0}
    quadrant_totals = {
        "top_left": max(1, (width // 2) * (abs_height // 2)),
        "top_right": max(1, (width - width // 2) * (abs_height // 2)),
        "bottom_left": max(1, (width // 2) * (abs_height - abs_height // 2)),
        "bottom_right": max(1, (width - width // 2) * (abs_height - abs_height // 2)),
    }
    quantized: set[tuple[int, int, int]] = set()
    if width > 0 and abs_height > 0 and bits_per_pixel == 24 and pixel_offset + pixel_bytes <= len(data):
        for row in range(abs_height):
            start = pixel_offset + row * row_bytes
            for x in range(width):
                blue, green, red = data[start + x * 3 : start + x * 3 + 3]
                if max(red, green, blue) > 8:
                    nonblack += 1
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, row)
                    max_y = max(max_y, row)
                    if x < edge_band:
                        edge_counts["left"] += 1
                    if x >= width - edge_band:
                        edge_counts["right"] += 1
                    if row < edge_band:
                        edge_counts["bottom"] += 1
                    if row >= abs_height - edge_band:
                        edge_counts["top"] += 1
                    top_half = row >= abs_height // 2
                    left_half = x < width // 2
                    if top_half and left_half:
                        quadrant_counts["top_left"] += 1
                    elif top_half:
                        quadrant_counts["top_right"] += 1
                    elif left_half:
                        quadrant_counts["bottom_left"] += 1
                    else:
                        quadrant_counts["bottom_right"] += 1
                if len(quantized) < 512:
                    quantized.add((red >> 4, green >> 4, blue >> 4))
    total_pixels = max(width * abs_height, 1)
    nonblack_ratio = nonblack / total_pixels
    if nonblack > 0:
        content_width = max_x - min_x + 1
        content_height = max_y - min_y + 1
        bbox = {"left": min_x, "bottom": min_y, "right": max_x, "top": max_y, "width": content_width, "height": content_height}
    else:
        content_width = 0
        content_height = 0
        bbox = None
    edge_ratios = {
        key: edge_counts[key] / max(edge_totals[key], 1)
        for key in sorted(edge_counts)
    }
    quadrant_ratios = {
        key: quadrant_counts[key] / max(quadrant_totals[key], 1)
        for key in sorted(quadrant_counts)
    }
    info.update(
        nonblack_pixels=nonblack,
        nonblack_ratio=nonblack_ratio,
        quantized_color_count=len(quantized),
        content_bbox=bbox,
        content_width_ratio=content_width / max(width, 1),
        content_height_ratio=content_height / max(abs_height, 1),
        edge_nonblack_ratios=edge_ratios,
        quadrant_nonblack_ratios=quadrant_ratios,
    )
    checks.extend(
        (
            check("bmp_not_blank_black", nonblack_ratio >= 0.10, {"nonblack_ratio": round(nonblack_ratio, 6), "nonblack_pixels": nonblack}),
            check("bmp_color_variation", len(quantized) >= 16, len(quantized)),
            check("bmp_content_width_extent", content_width >= int(EXPECTED_FRAMEBUFFER[0] * MIN_CONTENT_WIDTH_RATIO), {"content_width": content_width, "minimum": int(EXPECTED_FRAMEBUFFER[0] * MIN_CONTENT_WIDTH_RATIO), "bbox": bbox}),
            check("bmp_content_height_extent", content_height >= int(EXPECTED_FRAMEBUFFER[1] * MIN_CONTENT_HEIGHT_RATIO), {"content_height": content_height, "minimum": int(EXPECTED_FRAMEBUFFER[1] * MIN_CONTENT_HEIGHT_RATIO), "bbox": bbox}),
        )
    )
    return info, checks


def validate(candidate: str, frame: Path, state: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    frame_info, frame_checks = inspect_bmp(frame)
    checks.extend(frame_checks)
    state_json = json.loads(state.read_text(encoding="utf-8"))
    visual_raw = state_json.get("loading_visual_gate")
    visual = visual_raw if isinstance(visual_raw, dict) else {}
    expected_runtime_log = f"ux0:data/renegade/user/logs/{candidate.lower().replace('.', '')}-runtime.log"
    # Candidate labels use A3.5-devNN; runtime logs use a35-devNN.
    expected_runtime_log = expected_runtime_log.replace("a35-", "a35-").replace("a35dev", "a35-dev")

    checks.extend(
        (
            check("state_schema_v4", state_json.get("schema_version") == 4, state_json.get("schema_version")),
            check("state_candidate", state_json.get("milestone") == candidate, state_json.get("milestone")),
            check("state_build_label", candidate in str(state_json.get("build_label", "")), state_json.get("build_label")),
            check("state_runtime_log", state_json.get("runtime_log_path") == expected_runtime_log, state_json.get("runtime_log_path")),
            check("state_phase", state_json.get("phase") == "original-loading-screen", state_json.get("phase")),
            check("state_reason", state_json.get("reason") == "level-ready", state_json.get("reason")),
            check("visual_gate_present", isinstance(visual_raw, dict), type(visual_raw).__name__),
        )
    )
    expected_visual = {
        "active": True,
        "framebuffer_width": EXPECTED_FRAMEBUFFER[0],
        "framebuffer_height": EXPECTED_FRAMEBUFFER[1],
        "original_logical_width": EXPECTED_LOGICAL[0],
        "original_logical_height": EXPECTED_LOGICAL[1],
        "native_display_width": EXPECTED_FRAMEBUFFER[0],
        "native_display_height": EXPECTED_FRAMEBUFFER[1],
        "logical_to_native_fullscreen": False,
        "original_loading_screen_owner": True,
        "direct_vitagl_overlay_disabled": True,
        "loading_texture_v_flip_enabled": True,
        "gameplay_texture_v_unchanged": True,
    }
    if isinstance(visual, dict):
        for key, expected in expected_visual.items():
            checks.append(check(f"visual_gate_{key}", visual.get(key) == expected, {"actual": visual.get(key), "expected": expected}))

    status = "PASS" if all(item["passed"] for item in checks) else "FAIL"
    return {
        "schema_version": 1,
        "status": status,
        "candidate": candidate,
        "frame": str(frame),
        "state": str(state),
        "frame_sha256": sha256(frame),
        "state_sha256": sha256(state),
        "frame_info": frame_info,
        "state_summary": {
            "schema_version": state_json.get("schema_version"),
            "milestone": state_json.get("milestone"),
            "phase": state_json.get("phase"),
            "reason": state_json.get("reason"),
            "runtime_log_path": state_json.get("runtime_log_path"),
            "loading_visual_gate": visual if isinstance(visual, dict) else None,
        },
        "claim_boundary": "metadata, native BMP, color variation, and broad content extent only; physical visual acceptance still requires user observation",
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--frame", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = validate(args.candidate, args.frame, args.state)
    except (OSError, json.JSONDecodeError, struct.error) as error:
        result = {
            "schema_version": 1,
            "status": "FAIL",
            "candidate": args.candidate,
            "frame": str(args.frame),
            "state": str(args.state),
            "error": str(error),
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
