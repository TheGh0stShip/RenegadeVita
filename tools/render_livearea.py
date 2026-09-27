#!/usr/bin/env python3
"""Render the original Renegade Vita identity for one candidate label."""

from __future__ import annotations

import argparse
import re
import shutil
import struct
import subprocess
from pathlib import Path


SIZES = {"icon0.png": (128, 128), "bg0.png": (840, 500),
         "startup.png": (280, 158), "pic0.png": (960, 544)}


def png_geometry(path: Path) -> tuple[int, int, int]:
    return png_geometry_bytes(path.read_bytes()[:26])


def png_geometry_bytes(data: bytes) -> tuple[int, int, int]:
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"not a PNG: {path}")
    return *struct.unpack(">II", data[16:24]), data[25]


def render(candidate: str, assets: Path, output: Path) -> None:
    if not re.fullmatch(r"A[0-9]+\.[0-9]+-dev[0-9]+", candidate):
        raise ValueError(f"invalid candidate label: {candidate}")
    convert = shutil.which("convert")
    if not convert:
        raise RuntimeError("ImageMagick convert is required to render LiveArea artwork")
    output.mkdir(parents=True, exist_ok=True)
    banner = (assets / "branding/renegade-vita-banner.svg").read_text(encoding="utf-8")
    if banner.count("__CANDIDATE__") != 1:
        raise ValueError("banner must contain one candidate placeholder")
    prepared = output / "candidate-banner.svg"
    prepared.write_text(banner.replace("__CANDIDATE__", candidate), encoding="utf-8")
    startup = (assets / "branding/renegade-vita-startup.svg").read_text(encoding="utf-8")
    if startup.count("__CANDIDATE__") != 1:
        raise ValueError("startup art must contain one candidate placeholder")
    prepared_startup = output / "candidate-startup.svg"
    prepared_startup.write_text(startup.replace("__CANDIDATE__", candidate), encoding="utf-8")
    sources = {
        "icon0.png": assets / "branding/renegade-vita-mark.svg",
        "bg0.png": prepared,
        "startup.png": prepared_startup,
        "pic0.png": prepared,
    }
    for name, source in sources.items():
        width, height = SIZES[name]
        target = output / name
        subprocess.run([convert, "-background", "none", str(source),
                        "-resize", f"{width}x{height}!", "-strip",
                        f"PNG8:{target}"], check=True)
        if png_geometry(target) != (width, height, 3):
            raise ValueError(f"invalid Vita indexed-PNG format: {target}")
    prepared.unlink()
    prepared_startup.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.candidate, args.assets, args.output)


if __name__ == "__main__":
    main()
