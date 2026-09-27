"""Prepare local contact sheets; never publish automatically.

Pillow is used only for review thumbnails and lossless BMP-to-PNG conversion.
Original screenshots are not retouched or regenerated.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-build", type=int, default=100)
    parser.add_argument("--build", type=int, action="append", default=[])
    args = parser.parse_args()
    roots = {label: Path(path) for label, path in (arg.split("=", 1) for arg in args.root)}
    groups = collections.defaultdict(list)
    for entry in json.loads(args.inventory.read_text())["captures"]:
        if len(entry["candidate_builds"]) != 1:
            continue
        build = entry["candidate_builds"][0]
        if args.build and build not in args.build:
            continue
        if build < args.min_build or entry["root"] == "published" or "annotated" in entry["path"]:
            continue
        groups[build].append(entry)
    args.output.mkdir(parents=True, exist_ok=True)
    selected = []
    for build, entries in sorted(groups.items()):
        def score(entry):
            name = entry["path"]
            return (0 if "manual-select-visible-gameplay" in name else
                    1 if "visible-" in name else 2 if "window-" in name else
                    3 if "pre-clean-exit" in name else 4,
                    0 if name.endswith(".png") else 1, name)
        entries.sort(key=score)
        # Offer distinct views to the reviewer instead of silently accepting one.
        options = [entries[0], entries[len(entries) // 2], entries[-1]]
        # Black game-owned buffers must not hide a valid emulator-window capture.
        visible = [entry for entry in entries if Path(entry["path"]).name.startswith(("visible-", "window-"))]
        if visible:
            options.append(visible[0])
        seen = set()
        for entry in options:
            source = roots[entry["root"]] / entry["path"]
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            number = len(selected)
            destination = args.output / f"review-{number:03d}-dev{build}.png"
            with Image.open(source) as original:
                if source.suffix == ".png":
                    shutil.copyfile(source, destination)
                else:
                    original.save(destination)
                with Image.open(destination) as converted:
                    if original.convert("RGBA").tobytes() != converted.convert("RGBA").tobytes():
                        raise ValueError(f"pixel conversion mismatch: {source}")
            selected.append({**entry, "review": number, "build": build,
                             "source_sha256": digest, "review_file": destination.name})
    (args.output / "selection.json").write_text(json.dumps(selected, indent=2) + "\n")
    for start in range(0, len(selected), 24):
        sheet = Image.new("RGB", (1200, 6 * 205), "#eeeeee")
        draw = ImageDraw.Draw(sheet)
        for offset, entry in enumerate(selected[start:start + 24]):
            x, y = (offset % 4) * 300, (offset // 4) * 205
            with Image.open(args.output / entry["review_file"]) as original:
                original.thumbnail((296, 177))
                sheet.paste(original, (x, y + 24))
            draw.text((x + 4, y + 5), f"#{entry['review']} Dev{entry['build']}", fill="black")
        sheet.save(args.output / f"sheet-{start // 24:02d}.png")
    print(f"Prepared {len(selected)} candidates for {len(groups)} builds")


if __name__ == "__main__":
    main()
