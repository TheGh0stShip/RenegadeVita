#!/usr/bin/env python3
"""Read one original MIX1 image and emit metadata only, never retail payloads."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import zlib


def font_grid_reference(rgba):
    """Describe original Font3D grid packing without retaining retail pixels."""
    if rgba.width % 16 or rgba.height % 16 or rgba.width > 8 * rgba.height:
        raise ValueError("Expected an original 16 by 16 bitmap-font grid")
    cell_width, cell_height = rgba.width // 16, rgba.height // 16
    atlas_size = 128 if rgba.width < 256 else 256
    alpha = rgba.getchannel("A")
    x = y = 0
    overflow = []
    digits = {}
    occupied_pixels = 0
    for code in range(256):
        left, top = (code % 16) * cell_width, (code // 16) * cell_height
        cell = alpha.crop((left, top, left + cell_width, top + cell_height))
        bounds = cell.getbbox()
        width = bounds[2] - bounds[0] if bounds and code <= 0x80 else 0
        if width and x + width > atlas_size:
            x = 0
            y += cell_height
            if y + cell_height > atlas_size:
                overflow.append(code)
                # Match original Font3D's overflow fallback, but report it.
                y -= cell_height
        if width:
            occupied_pixels += sum(value != 0 for value in cell.tobytes())
        if 48 <= code <= 57:
            digits[chr(code)] = {
                "source_cell": [left, top, cell_width, cell_height],
                "alpha_bounds_in_cell": list(bounds) if bounds else None,
                "packed_rect": [x, y, width, cell_height],
                "alpha_sha256": hashlib.sha256(cell.tobytes()).hexdigest(),
            }
        x += width
    return {
        "owner_reference": "Original Font3DDataClass grid/proportional packing",
        "native_surface_copy_and_draw": "UNASSESSED",
        "atlas_size": [atlas_size, atlas_size],
        "cell_size": [cell_width, cell_height],
        "packing_overflow_character_codes": overflow,
        "retained_glyph_nonzero_alpha_pixels": occupied_pixels,
        "digits": digits,
        "retail_pixels_written": False,
    }


def inspect(archive, name, font_grid=False):
    from PIL import Image

    size = archive.stat().st_size
    with archive.open("rb") as stream:
        header = stream.read(12)
        magic, index_offset, names_offset = struct.unpack("<4sII", header)
        if magic != b"MIX1" or not (12 <= index_offset <= size - 4 and
                                      12 <= names_offset <= size - 4):
            raise ValueError("Invalid original MIX1 header")
        stream.seek(index_offset)
        count = struct.unpack("<I", stream.read(4))[0]
        if count > 1000000 or index_offset + 4 + count * 12 > size:
            raise ValueError("Invalid MIX1 index bounds")
        index = stream.read(count * 12)
        entries = list(struct.iter_unpack("<III", index))
        key = zlib.crc32(name.upper().encode("ascii"))
        matches = [entry for entry in entries if entry[0] == key]
        stream.seek(names_offset)
        if struct.unpack("<I", stream.read(4))[0] != count:
            raise ValueError("MIX1 name count differs from index")
        named = False
        for _ in range(count):
            raw_length = stream.read(1)
            if not raw_length or raw_length[0] == 0:
                raise ValueError("Invalid MIX1 filename length")
            raw = stream.read(raw_length[0])
            if len(raw) != raw_length[0] or not raw.endswith(b"\0"):
                raise ValueError("Truncated MIX1 filename")
            if raw[:-1].decode("ascii").casefold() == name.casefold():
                named = True
        if not named or len(matches) != 1:
            raise ValueError("Requested name lacks one unambiguous indexed entry")
        _, offset, length = matches[0]
        if offset < 12 or length <= 0 or length > 32 * 1024 * 1024 or offset + length > size:
            raise ValueError("Invalid or oversized image payload")
        stream.seek(offset)
        payload = stream.read(length)
    with Image.open(io.BytesIO(payload)) as source:
        if source.width * source.height > 16 * 1024 * 1024:
            raise ValueError("Image exceeds diagnostic pixel limit")
        image_format = source.format
        rgba = source.convert("RGBA")
        alpha = rgba.getchannel("A").histogram()
        colors = rgba.getcolors(maxcolors=65536)
        result = {
            "schema": 1,
            "evidence_class": "HOST_RETAIL_IMAGE_DECODE",
            "decoder": "Pillow; not the native engine decoder",
            "archive": str(archive), "archive_bytes": size,
            "index_sha256": hashlib.sha256(header + index).hexdigest(),
            "entry": name, "crc32": f"{key:08x}",
            "offset": offset, "bytes": length,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "format": image_format, "width": rgba.width, "height": rgba.height,
            "source_mode": source.mode,
            "tga_pixel_depth": payload[16] if image_format == "TGA" else None,
            "transparent_pixels": alpha[0], "opaque_pixels": alpha[255],
            "partial_alpha_pixels": sum(alpha[1:255]),
            "distinct_rgba_colors": len(colors) if colors is not None else ">65536",
            "decoded_rgba_sha256": hashlib.sha256(rgba.tobytes()).hexdigest(),
            "native_decoder_and_draw_correctness": "UNASSESSED",
            "retail_payload_written": False,
        }
        if font_grid:
            result["font_grid_reference"] = font_grid_reference(rgba)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--entry", required=True)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--font-grid", action="store_true",
                        help="Include original bitmap-font digit/packing metadata")
    args = parser.parse_args()
    result = inspect(args.archive, args.entry, args.font_grid)
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, struct.error, ImportError) as error:
        raise SystemExit(str(error))
