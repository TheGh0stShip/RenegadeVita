"""Copy explicitly reviewed images and generate their public provenance catalog."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()
    entries = {entry["review"]: entry for entry in json.loads((args.review / "selection.json").read_text())}
    decisions = json.loads(args.decisions.read_text())
    args.destination.mkdir(parents=True, exist_ok=True)
    catalog_path = args.destination / "catalog.json"
    catalog = json.loads(catalog_path.read_text()) if args.append and catalog_path.exists() else []
    for number, caption, kind in decisions:
        entry = entries[number]
        source = args.review / entry["review_file"]
        filename = f"dev{entry['build']}-{number:03d}.png"
        if any(item["file"] == filename for item in catalog):
            raise ValueError(f"catalog already contains {filename}")
        shutil.copyfile(source, args.destination / filename)
        with Image.open(source) as image:
            dimensions = list(image.size)
        platform = "Vita3K"
        if "gallery-psvita" in entry["path"] or entry["root"] == "physical_vita":
            platform = "Physical PS Vita"
        elif "pstv" in entry["path"] or entry["root"] == "physical_pstv":
            platform = "Physical PSTV"
        catalog.append({"build": entry["build"], "file": filename, "caption": caption,
                        "kind": kind, "platform": platform,
                        "source": f"{entry['root']}/{entry['path']}",
                        "attribution": entry["attribution"],
                        "source_sha256": entry["source_sha256"],
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "dimensions": dimensions,
                        "conversion": "lossless BMP-to-PNG; decoded RGBA pixels checked" if entry["path"].endswith(".bmp") else "unchanged PNG copy"})
    (args.destination / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Published {len(catalog)} reviewed captures")


if __name__ == "__main__":
    main()
