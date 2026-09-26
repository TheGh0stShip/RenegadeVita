#!/usr/bin/env python3
"""Create an asset-free MIX1 input for the official TT PackageEditor oracle."""

import argparse
from pathlib import Path
import struct
import zlib


FIXTURE_FILES = {
    "vita_probe.txt": b"Renegade Vita TTFS compatibility fixture\n",
    "vita_bytes.bin": bytes(range(256)) * 3,
}
EDGE_FILES = {"empty.dat": b"", "A space.TXT": b"space and case\n",
              "repeat.bin": b"compressible-but-raw\n" * 1000}


def make_mix(files: dict[str, bytes]) -> bytes:
    payload = bytearray()
    entries = []
    names = bytearray(struct.pack("<I", len(files)))
    for name, data in files.items():
        encoded = name.encode("ascii") + b"\0"
        if len(encoded) > 255:
            raise ValueError("MIX1 filename too long")
        entries.append((zlib.crc32(name.upper().encode("ascii")), 12 + len(payload), len(data)))
        payload.extend(data)
        names.extend(bytes([len(encoded)]) + encoded)
    index = struct.pack("<I", len(entries)) + b"".join(
        struct.pack("<III", *entry) for entry in sorted(entries))
    return struct.pack("<4sII", b"MIX1", 12 + len(payload), 12 + len(payload) + len(index)) + payload + index + names


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--edge-cases", action="store_true")
    args = parser.parse_args()
    with args.output.open("xb") as stream:
        stream.write(make_mix(EDGE_FILES if args.edge_cases else FIXTURE_FILES))
