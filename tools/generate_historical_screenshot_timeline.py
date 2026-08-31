#!/usr/bin/env python3
"""Generate the GitHub historical screenshot timeline and evidence inventory."""

from __future__ import annotations

import hashlib
import html
import json
import re
import struct
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "docs" / "history" / "screenshots"
TIMELINE_PATH = ROOT / "docs" / "HISTORICAL_SCREENSHOT_TIMELINE.md"
INVENTORY_JSON = ROOT / "reports" / "generated" / "historical_evidence_inventory.json"
INVENTORY_MD = ROOT / "reports" / "HISTORICAL_EVIDENCE_INVENTORY.md"
README_PATH = ROOT / "README.md"


QUICK_GAMEPLAY = [
    ("A3.1", "a31-vita-log-select-capture-f2278.png", "Early visible M00 world"),
    ("A3.1", "a31-vita-log-select-capture-f3232.png", "Second early M00 world view"),
    ("A3.5-dev5", "a35-dev5-spawn-control.png", "Visible M00 world and weapon"),
    ("A3.5-dev5", "a35-dev5-walk-manual.png", "Manual movement capture"),
    ("A3.5-dev5", "a35-dev5-vita-manual-select-interactive-f355-t39869172.png", "Recovered weapon/world frame"),
    ("A3.5-dev7", "a35-dev7-effects-131326.png", "Effects/input gameplay view"),
    ("A3.5-dev7", "a35-dev7-vita-manual-select-interactive-f1527-t61897982.png", "Recovered wall/weapon frame"),
    ("A3.5-dev13", "a35-dev13-selected-frame.png", "NPC/material defect route frame"),
    ("A3.5-dev13", "a35-dev13-npc-crop.png", "NPC material detail crop"),
    ("A3.5-dev16", "a35-dev16-selected-frame.png", "Audio lifecycle route frame"),
    ("A3.5-dev17", "a35-dev17-selected-frame.png", "Route replay frame"),
    ("A3.5-dev18", "a35-dev18-capture2.png", "Crate/world route frame"),
    ("A3.5-dev18", "a35-dev18-vita-manual-select-interactive-f2184-t75384736.png", "Manual gameplay route frame"),
    ("A3.5-dev19", "a35-dev19-vita-manual-select-interactive-f2570-t85917941.png", "NPC route capture"),
    ("A3.5-dev19", "a35-dev19-npc-detail-crop.png", "NPC detail crop"),
]


GAMEPLAY_SECTIONS = [
    {
        "title": "A3.1 - Developer M00 Capture Evidence",
        "build": "A3.1",
        "summary": (
            "4 gameplay/world screenshots found in the preserved Vita Logs directory on E:. "
            "They provide an earlier physical visual baseline before the later A3.5 route evidence."
        ),
        "images": [
            ("a31-vita-log-select-capture-f2278.png", "Select capture frame 2278"),
            ("a31-vita-log-select-capture-f2278-annotated.png", "Annotated select capture frame 2278"),
            ("a31-vita-log-select-capture-f3232.png", "Select capture frame 3232"),
            ("a31-vita-log-select-capture-f3232-annotated.png", "Annotated select capture frame 3232"),
        ],
        "sources": [
            "/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/select-capture-p0-f2278-t76344972/",
            "/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/select-capture-p0-f3232-t108422940/",
            "/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/a31-runtime.log",
            "/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/a31.1-runtime.log",
            "/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/a31.4-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev5 - Visible M00 and Movement Evidence",
        "build": "A3.5-dev5",
        "summary": (
            "12 useful gameplay/world screenshots found after the second Vita pull. "
            "Dark VitaGL logo and near-black diagnostic frames are kept in the manifest only, not padded into this gameplay section."
        ),
        "images": [
            ("a35-dev5-spawn-control.png", "Spawn/control capture"),
            ("a35-dev5-spawn-control-raw-bmp.png", "Spawn/control raw BMP conversion"),
            ("a35-dev5-spawn-control-annotated-bmp.png", "Spawn/control annotated"),
            ("a35-dev5-walk-manual.png", "Manual walk capture"),
            ("a35-dev5-walk-manual-raw-bmp.png", "Manual walk raw BMP conversion"),
            ("a35-dev5-walk-manual-annotated-bmp.png", "Manual walk annotated"),
            ("a35-dev5-vita-manual-select-interactive-f355-t39869172.png", "Recovered manual-select gameplay"),
            ("a35-dev5-vita-manual-select-interactive-f355-t39869172-annotated.png", "Recovered manual-select annotated"),
            ("a35-dev5-vita-first-interactive-player-frame-f1-t98830083.png", "Recovered first-interactive overhead frame"),
            ("a35-dev5-vita-first-interactive-player-frame-f1-t98830083-annotated.png", "Recovered first-interactive overhead annotated"),
            ("a35-dev5-vita-first-static-world-frame-p0-f1-t30385339.png", "Recovered static-world frame"),
            ("a35-dev5-vita-first-static-world-frame-p0-f1-t30385339-annotated.png", "Recovered static-world annotated"),
        ],
        "sources": [
            "build/device-evidence/a35-dev5-recursive-create-20260824/",
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev5/",
            "build/device-evidence/vitashell-gallery-pull-listingpass-20260828-213810/captures/",
            "build/device-evidence/vitashell-gallery-pull-listingpass-20260828-213810/logs/a35-dev5-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev7 - Input, Effects, and Weapon/World Evidence",
        "build": "A3.5-dev7",
        "summary": (
            "7 useful gameplay/world screenshots found. Dark startup frames and magenta diagnostic buffers remain in the manifest, "
            "but this section only shows actual in-game/world samples."
        ),
        "images": [
            ("a35-dev7-effects-130626-capture2.png", "Effects capture 130626 gameplay view"),
            ("a35-dev7-effects-130626.png", "Selected effects capture 130626"),
            ("a35-dev7-effects-131326-capture2.png", "Effects capture 131326 gameplay view"),
            ("a35-dev7-effects-131326.png", "Selected effects capture 131326"),
            ("a35-dev7-effects-131654-capture2.png", "Effects capture 131654 gameplay view"),
            ("a35-dev7-effects-131654.png", "Selected effects capture 131654"),
            ("a35-dev7-vita-manual-select-interactive-f1527-t61897982.png", "Recovered manual-select gameplay"),
        ],
        "sources": [
            "build/device-evidence/a3.5-dev7-effects-20260824-130626/",
            "build/device-evidence/a3.5-dev7-effects-20260824-131326/",
            "build/device-evidence/a3.5-dev7-effects-20260824-131654/",
            "build/device-evidence/a3.5-dev7-effects-20260824-132016/",
            "build/device-evidence/vitashell-gallery-pull-listingpass-20260828-213810/captures/",
            "build/device-evidence/vitashell-gallery-pull-listingpass-20260828-213810/logs/a35-dev7-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev13 - Route Record With NPC/Material Defects",
        "build": "A3.5-dev13",
        "summary": (
            "5 gameplay samples found. The NPC crop is intentionally featured because it gives a useful close-up of the material defect."
        ),
        "images": [
            ("a35-dev13-selected-frame.png", "Selected gameplay frame"),
            ("a35-dev13-selected-frame-raw-bmp.png", "Selected frame raw BMP conversion"),
            ("a35-dev13-npc-crop.png", "NPC material detail crop"),
            ("a35-dev13-vita-manual-select-interactive-f4209-t108871313.png", "Recovered manual-select route frame"),
            ("a35-dev13-vita-manual-select-interactive-f4209-t108871313-annotated.png", "Recovered manual-select annotated"),
        ],
        "sources": [
            "build/device-evidence/a3.5-dev13-route-record-20260824-144843/",
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev13/",
            "build/device-evidence/vitashell-gallery-pull-20260828/logs/a35-dev13-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev16 - Audio Lifecycle Route Evidence",
        "build": "A3.5-dev16",
        "summary": "6 gameplay route samples found from the audio lifecycle path.",
        "images": [
            ("a35-dev16-capture2.png", "Captured route frame"),
            ("a35-dev16-capture2-annotated.png", "Captured route frame annotated"),
            ("a35-dev16-selected-frame.png", "Selected route frame"),
            ("a35-dev16-selected-frame-raw-bmp.png", "Selected route frame raw BMP conversion"),
            ("a35-dev16-vita-manual-select-interactive-f1255-t58957010.png", "Recovered manual-select route frame"),
            ("a35-dev16-vita-manual-select-interactive-f1255-t58957010-annotated.png", "Recovered manual-select annotated"),
        ],
        "sources": [
            "build/device-evidence/a3.5-dev16-route-record-20260824-190103/",
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev16/",
            "build/device-evidence/vitashell-gallery-pull-20260828/logs/a35-dev16-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev17 - Route Replay Evidence",
        "build": "A3.5-dev17",
        "summary": "6 gameplay replay samples found from the retained tutorial route path.",
        "images": [
            ("a35-dev17-capture2.png", "Captured replay frame"),
            ("a35-dev17-capture2-annotated.png", "Captured replay frame annotated"),
            ("a35-dev17-selected-frame.png", "Selected replay frame"),
            ("a35-dev17-selected-frame-raw-bmp.png", "Selected replay raw BMP conversion"),
            ("a35-dev17-vita-manual-select-interactive-f1255-t58773849.png", "Recovered manual-select replay frame"),
            ("a35-dev17-vita-manual-select-interactive-f1255-t58773849-annotated.png", "Recovered manual-select annotated"),
        ],
        "sources": [
            "build/device-evidence/a3.5-dev17-route-replay-20260824-192336/",
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev17/",
            "build/device-evidence/vitashell-gallery-pull-20260828/logs/a35-dev17-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev18 - Failed/Superseded Route Replay Evidence",
        "build": "A3.5-dev18",
        "summary": (
            "6 gameplay/world samples found. The same build also has loading frames, but they are not displayed here."
        ),
        "images": [
            ("a35-dev18-capture2.png", "Captured route frame"),
            ("a35-dev18-capture2-annotated.png", "Captured route frame annotated"),
            ("a35-dev18-vita-manual-select-interactive-f1255-t60224261.png", "Recovered manual-select gameplay"),
            ("a35-dev18-vita-manual-select-interactive-f1255-t60224261-annotated.png", "Recovered manual-select annotated"),
            ("a35-dev18-vita-manual-select-interactive-f2184-t75384736.png", "Recovered later manual-select gameplay"),
            ("a35-dev18-vita-manual-select-interactive-f2184-t75384736-annotated.png", "Recovered later manual-select annotated"),
        ],
        "sources": [
            "build/device-evidence/a3.5-dev18-route-replay-20260824-200820/",
            "build/device-evidence/a3.5-dev18-route-record-20260824-201137/",
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev18/",
            "build/device-evidence/vitashell-gallery-pull-20260828/logs/a35-dev18-runtime.log",
        ],
    },
    {
        "title": "A3.5-dev19 - Pistol/Gate Crash Route Evidence",
        "build": "A3.5-dev19",
        "summary": (
            "5 gameplay samples found. The new NPC crop is generated from the full dev19 route frame for close-up material review."
        ),
        "images": [
            ("a35-dev19-vita-manual-select-interactive-f2570-t85917941.png", "Recovered NPC route frame"),
            ("a35-dev19-vita-manual-select-interactive-f2570-t85917941-annotated.png", "Recovered NPC route annotated"),
            ("a35-dev19-npc-detail-crop.png", "NPC detail crop"),
            ("a35-dev19-vita-manual-select-interactive-f4146-t118405956.png", "Recovered later route frame"),
            ("a35-dev19-vita-manual-select-interactive-f4146-t118405956-annotated.png", "Recovered later route annotated"),
        ],
        "sources": [
            "build/device-evidence/vitashell-gallery-pull-20260828/captures/a35-dev19/",
            "build/device-evidence/vitashell-gallery-pull-20260828/logs/a35-dev19-runtime.log",
        ],
    },
]


DIAGNOSTIC_ONLY = [
    ("A3.5-dev6", "2 dark/logo diagnostic frames recovered; no useful gameplay screenshot was found.", "a35-dev6-vita-first-interactive-player-frame-f1-t31158328.png"),
    ("A3.5-dev12", "4 black/logo diagnostic frames recovered; dev12 skin-geometry evidence is stronger in logs than screenshots.", "a35-dev12-first-frame.png"),
    ("A3.5-dev20", "2 loading/menu-state frames recovered; no gameplay screenshot was found.", "a35-dev20-vita-first-interactive-player-frame-f1-t30968807.png"),
    ("A3.5-dev21", "2 loading/menu-state frames recovered; no gameplay screenshot was found.", "a35-dev21-vita-first-interactive-player-frame-f1-t30678441.png"),
    ("A3.5-dev24", "2 loading/menu-state frames recovered; no gameplay screenshot was found.", "a35-dev24-vita-first-interactive-player-frame-f1-t31590612.png"),
    ("A3.5-dev42", "8 magenta/loading diagnostic frames recovered; no gameplay screenshot was found.", "a35-dev42-vita-first-interactive-player-frame-f1-t33048100.png"),
    ("A3.5-dev43", "15 magenta/loading route frames recovered; no useful gameplay screenshot was found.", "a35-dev43-loading-record.png"),
    ("A3.5-dev44", "4 magenta/loading diagnostic frames recovered; no gameplay screenshot was found.", "a35-dev44-vita-first-interactive-player-frame-f1-t32936764.png"),
    ("A3.5-dev45", "8 magenta/loading route frames recovered; no gameplay screenshot was found.", "a35-dev45-loading-replay.png"),
    ("A3.5-dev46", "10 magenta/loading/no-dialogue diagnostic frames recovered; no useful gameplay screenshot was found.", "a35-dev46-loading-replay.png"),
    ("A3.5-dev47", "4 magenta/loading TranslateDB diagnostic frames recovered; no gameplay screenshot was found.", "a35-dev47-vita-first-interactive-player-frame-f1-t32303654.png"),
    ("A3.5-dev78", "8 physical loading-regression frames recovered; no gameplay screenshot was returned for dev78.", "a35-dev78-loading-physical.png"),
    ("A3.5-dev79", "4 physical loading/control-candidate frames recovered; no gameplay screenshot was returned for dev79.", "a35-dev79-vita-first-interactive-player-frame-f1-t39743964.png"),
    ("A3.5-dev82", "Four returned physical capture records are visibly preserved in the dedicated Dev82 diagnostic gallery: two distinct loading presentations are vertically inverted, the t64590857 first-interactive record is byte-identical to the full-frame loading image, and t88041059 is black except for a small HUD fragment. None establishes gameplay acceptance.", "a35-dev82-vita-original-loading-screen-t67280479.png"),
    ("A3.5-dev86", "One returned physical original-loading-screen frame is visibly preserved in the dedicated Dev86 diagnostic gallery. It shows the original loading artwork and color panels but no legible original UI labels; it is not a main-menu or gameplay acceptance image.", "a35-dev86-vita-original-loading-screen-level-ready-t119137636-annotated.png"),
]


DEV82_RETURNED_DIAGNOSTICS = [
    (
        "a35-dev82-vita-original-loading-screen-t54494725.png",
        "Original loading frame t54494725 — full-frame vertically inverted loading UI",
    ),
    (
        "a35-dev82-vita-original-loading-screen-t67280479.png",
        "Original loading frame t67280479 — letterboxed vertically inverted loading UI",
    ),
    (
        "a35-dev82-vita-first-interactive-frame-t64590857.png",
        "First interactive record t64590857 — byte-identical to full-frame inverted loading image",
    ),
    (
        "a35-dev82-vita-first-interactive-frame-t88041059.png",
        "First interactive frame t88041059 — black framebuffer with partial weapon/ammo HUD",
    ),
]


DEV86_RETURNED_DIAGNOSTICS = [
    (
        "a35-dev86-vita-original-loading-screen-level-ready-t119137636-annotated.png",
        "Original loading screen at level-ready — returned physical capture; original loading panels render, but original UI labels are absent",
    ),
]


README_IMAGES = [
    "a31-vita-log-select-capture-f2278.png",
    "a35-dev5-spawn-control.png",
    "a35-dev5-walk-manual.png",
    "a35-dev5-vita-manual-select-interactive-f355-t39869172.png",
    "a35-dev7-effects-131326.png",
    "a35-dev7-vita-manual-select-interactive-f1527-t61897982.png",
    "a35-dev13-selected-frame.png",
    "a35-dev13-npc-crop.png",
    "a35-dev16-selected-frame.png",
    "a35-dev17-selected-frame.png",
    "a35-dev18-capture2.png",
    "a35-dev18-vita-manual-select-interactive-f2184-t75384736.png",
    "a35-dev19-vita-manual-select-interactive-f2570-t85917941.png",
    "a35-dev19-npc-detail-crop.png",
    "a35-dev19-vita-manual-select-interactive-f4146-t118405956.png",
]


MISSING_SCREENSHOT_BUILDS = [
    "A3.5-dev1",
    "A3.5-dev14",
    "A3.5-dev22",
    "A3.5-dev23",
    "A3.5-dev34",
    "A3.5-dev36",
    "A3.5-dev37",
    "A3.5-dev38",
    "A3.5-dev40",
    "A3.5-dev41",
]


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG: {path}")
    return struct.unpack(">II", header[16:24])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def label_from_filename(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r"^a31-vita-log-", "", stem)
    stem = re.sub(r"^a35-dev\d+-", "", stem)
    stem = stem.replace("t", "t")
    words = stem.replace("-", " ").replace("_", " ").split()
    return " ".join(word.upper() if word in {"bmp", "png"} else word.capitalize() for word in words)


def rel_img(name: str) -> str:
    return f"history/screenshots/{name}"


def image_cell(name: str, caption: str, width: int) -> str:
    alt = html.escape(caption, quote=True)
    cap = html.escape(caption)
    return f'<td width="{width}%"><img src="{rel_img(name)}" width="{220 if width <= 25 else 260}" alt="{alt}"><br>{cap}</td>'


def image_table(items: list[tuple[str, str]], columns: int = 5) -> str:
    rows: list[str] = ["<table>"]
    width = 100 // columns
    for index in range(0, len(items), columns):
        rows.append("<tr>")
        for name, caption in items[index : index + columns]:
            rows.append(image_cell(name, caption, width))
        rows.append("</tr>")
    rows.append("</table>")
    return "\n".join(rows)


def source_list(paths: list[str]) -> str:
    return "\n".join(f"- `{path}`" for path in paths)


def gallery_manifest() -> list[dict[str, object]]:
    manifest = []
    for path in sorted(SCREENSHOT_DIR.glob("*.png")):
        width, height = png_dimensions(path)
        manifest.append(
            {
                "file": path.name,
                "dimensions": f"{width}x{height}",
                "sha256": sha256(path),
            }
        )
    return manifest


def build_ref(name: str) -> str:
    if name.startswith("a31-"):
        return "A3.1"
    match = re.match(r"a35-dev(\d+)-", name)
    if match:
        return f"A3.5-dev{match.group(1)}"
    return "Unclassified"


def validate_files() -> None:
    missing = []
    for _, filename, _ in QUICK_GAMEPLAY:
        if not (SCREENSHOT_DIR / filename).is_file():
            missing.append(filename)
    for section in GAMEPLAY_SECTIONS:
        for filename, _ in section["images"]:
            if not (SCREENSHOT_DIR / filename).is_file():
                missing.append(filename)
    for _, _, filename in DIAGNOSTIC_ONLY:
        if not (SCREENSHOT_DIR / filename).is_file():
            missing.append(filename)
    for filename, _ in DEV82_RETURNED_DIAGNOSTICS:
        if not (SCREENSHOT_DIR / filename).is_file():
            missing.append(filename)
    for filename, _ in DEV86_RETURNED_DIAGNOSTICS:
        if not (SCREENSHOT_DIR / filename).is_file():
            missing.append(filename)
    if missing:
        raise SystemExit("missing gallery files:\n" + "\n".join(sorted(set(missing))))


def write_timeline() -> None:
    validate_files()
    manifest = gallery_manifest()
    manifest_rows = [
        "| Gallery file | Build | Dimensions | SHA-256 |",
        "| --- | --- | --- | --- |",
    ]
    for item in manifest:
        name = str(item["file"])
        manifest_rows.append(
            f"| [`{name}`](history/screenshots/{name}) | {build_ref(name)} | {item['dimensions']} | `{item['sha256']}` |"
        )

    doc: list[str] = [
        "# Historical Screenshot Timeline",
        "",
        "This page collects web-viewable diagnostic screenshots from the Renegade Vita evidence tree. It is meant to show visual progression on GitHub without publishing retail data, raw dumps, saves, credentials, or a new runtime artifact.",
        "",
        "Evidence policy:",
        "",
        "- Source evidence came from `build/device-evidence/` in the bash workspace, read-only VitaShell FTP pulls recorded under `build/device-evidence/vitashell-gallery-pull-*`, targeted Vita3K AppData checks under `/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/user/`, and older A3.1 developer captures preserved under `/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/`.",
        "- The gallery stores PNG copies under `docs/history/screenshots/` so GitHub can render them directly.",
        "- Each build may include up to 15 displayed screenshots, but gameplay/world captures are the only images shown in the gameplay timeline. Builds with fewer than 15 gameplay captures list every useful local or Vita-pulled gameplay sample found.",
        "- One historical loading-screen frame is displayed as a regression reference. Other loading, black-screen, logo, and magenta diagnostic captures remain available through the complete manifest and inventory instead of being used as gameplay filler, except the four exact returned Dev82 diagnostic frames shown separately below.",
        "- Vita-pulled screenshots are mapped through each build's own `a35-devXX-runtime.log` capture paths before being included.",
        "- These images are historical evidence. They do not make dev82 physically accepted; dev82 still requires a returned Vita test with matching logs, screenshots/captures, and any crash dumps.",
        "",
        "## Quick Gameplay View",
        "",
        "This overview deliberately shows actual gameplay/world frames, including NPC detail crops, rather than one thumbnail from every build. Some later builds only produced loading, black, or diagnostic buffers locally; those are inventoried later but not promoted into this first visual impression.",
        "",
        image_table([(name, f"{build}: {caption}") for build, name, caption in QUICK_GAMEPLAY], columns=5),
        "",
        "## Gameplay Timeline",
        "",
    ]

    for section in GAMEPLAY_SECTIONS:
        images = list(section["images"])
        doc.extend(
            [
                f"### {section['title']}",
                "",
                f"{section['summary']} I did not pad this section to 15 with loading screens or diagnostic-only frames.",
                "",
                image_table(images, columns=5),
                "",
                "Source evidence:",
                "",
                source_list(section["sources"]),
                "",
            ]
        )

    doc.extend(
        [
            "## One Loading-Screen Regression Reference",
            "",
            "The gallery keeps one displayed loading-screen reference because the late dev78/dev79 loading regression is part of the story dev82 targets. The rest of the displayed sample images above are gameplay/world captures.",
            "",
            image_table([("a35-dev78-loading-physical.png", "A3.5-dev78 physical loading regression frame")], columns=1),
            "",
            "## A3.5-dev82 — Returned Physical Diagnostic Evidence",
            "",
            "All four raw capture records returned for Dev82 are displayed here, rather than being reduced to a manifest link. There are three distinct rendered images: the two original-loading frames show different vertically inverted loading presentations (`loadscreen_vflip=1`); the `t64590857` first-interactive record is byte-identical to the full-frame loading image; and the `t88041059` first-interactive record is a black framebuffer with only a partial weapon/ammo HUD. The user subsequently reported reaching a live world after additional input, but these first-frame captures do not show that later state and must not be presented as gameplay proof.",
            "",
            image_table(DEV82_RETURNED_DIAGNOSTICS, columns=2),
            "",
            "Source evidence:",
            "",
            source_list(
                [
                    "build/device-evidence/a35-dev82-user-return-20260830-205700/captures/original-loading-screen-t54494725/",
                    "build/device-evidence/a35-dev82-user-return-20260830-205700/captures/original-loading-screen-t67280479/",
                    "build/device-evidence/a35-dev82-user-return-20260830-205700/captures/first-interactive-frame-t64590857/",
                    "build/device-evidence/a35-dev82-user-return-20260830-205700/captures/first-interactive-frame-t88041059/",
                    "build/device-evidence/a35-dev82-user-return-20260830-205700/a35-dev82-runtime.log",
                ]
            ),
            "",
            "## A3.5-dev86 — Returned Physical Frontend Diagnostic Evidence",
            "",
            "The exact returned physical capture is shown here as a diagnostic, not a pass. Its phase is `original-loading-screen` / `level-ready`: the original loading artwork and colored panels render, while the original WWUI text regions are blank. The user separately reported a textless main menu; no main-menu image was returned, so this image is not presented as one.",
            "",
            image_table(DEV86_RETURNED_DIAGNOSTICS, columns=1),
            "",
            "Source evidence:",
            "",
            source_list(
                [
                    "build/device-evidence/a35-dev86-user-return-20260831T011721Z/captures/original-loading-screen-level-ready-t119137636/frame-annotated.bmp",
                    "build/device-evidence/a35-dev86-user-return-20260831T011721Z/a35-dev86-runtime-user-report.log",
                ]
            ),
            "",
            "## Diagnostic-Only Screenshot Inventory",
            "",
            "These builds have local or Vita-pulled screenshots, but the available images are loading, black/logo, magenta diagnostic, or otherwise not useful as gameplay samples. They stay in the GitHub manifest below, and the underlying logs remain inventoried in `reports/HISTORICAL_EVIDENCE_INVENTORY.md`.",
            "",
            "| Build | Displayed gameplay count | Screenshot evidence status | Representative manifest file |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for build, note, filename in DIAGNOSTIC_ONLY:
        doc.append(f"| {build} | 0 | {note} | [`{filename}`](history/screenshots/{filename}) |")

    doc.extend(
        [
            "",
            "## Builds With No Local Or Vita-Pulled Screenshot File",
            "",
            "The current bash workspace, VitaShell FTP pull, targeted C/AppData check, and E: Vita Logs check did not find matching PNG/BMP/JPG screenshot files for these build groups:",
            "",
            "`" + "`, `".join(MISSING_SCREENSHOT_BUILDS) + "`.",
            "",
            "Those builds should be added later only if matching diagnostic captures are returned or discovered with their evidence directories. Do not fabricate images from logs.",
            "",
            "## Complete Gallery Manifest",
            "",
            f"The GitHub gallery currently contains {len(manifest)} PNG files. Every file below is stored under `docs/history/screenshots/`; not every file is displayed as a timeline thumbnail because black/loading/diagnostic frames would obscure the gameplay progression.",
            "",
            *manifest_rows,
            "",
        ]
    )
    TIMELINE_PATH.write_text("\n".join(doc), encoding="utf-8")


def file_entry(path: Path, root: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path),
        "relative_path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        "size": stat.st_size,
        "type": path.suffix.lower().lstrip("."),
    }


def scan_root(label: str, path: Path) -> dict[str, object]:
    extensions = {".png", ".bmp", ".jpg", ".jpeg", ".log", ".txt", ".json", ".csv"}
    files = []
    if path.exists():
        for item in sorted(path.rglob("*")):
            text = str(item)
            if "/retail/" in text or "/retail-pc/" in text:
                continue
            if item.is_file() and item.suffix.lower() in extensions:
                files.append(file_entry(item, path))
    counts = defaultdict(int)
    for item in files:
        counts[str(item["type"])] += 1
    return {
        "label": label,
        "root": str(path),
        "exists": path.exists(),
        "file_count": len(files),
        "counts_by_type": dict(sorted(counts.items())),
        "files": files,
    }


def write_inventory() -> None:
    roots = [
        ("github_gallery", SCREENSHOT_DIR),
        ("active_device_evidence", ROOT / "build" / "device-evidence"),
        ("active_logs", ROOT / "logs"),
        ("active_dist", ROOT / "dist"),
        ("vita3k_user_appdata", Path("/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/user")),
        ("missing_c_local_builder_root", Path("/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder")),
        ("e_vita_logs", Path("/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs")),
        ("e_project_logs", Path("/mnt/e/Projects/RenegadeVitaBuilder/workspace/active/logs")),
        ("e_project_dist", Path("/mnt/e/Projects/RenegadeVitaBuilder/dist")),
    ]
    scans = [scan_root(label, path) for label, path in roots]
    manifest = gallery_manifest()
    gallery_by_build = defaultdict(int)
    for item in manifest:
        gallery_by_build[build_ref(str(item["file"]))] += 1

    inventory = {
        "generated_from": str(ROOT),
        "policy": "No retail data, saves, credentials, raw dumps, or VPK payloads are committed by this inventory.",
        "gallery_png_count": len(manifest),
        "gallery_by_build": dict(sorted(gallery_by_build.items())),
        "scanned_roots": scans,
        "diagnostic_only_builds": [build for build, _, _ in DIAGNOSTIC_ONLY],
        "missing_screenshot_builds": MISSING_SCREENSHOT_BUILDS,
    }
    INVENTORY_JSON.parent.mkdir(parents=True, exist_ok=True)
    INVENTORY_JSON.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Historical Evidence Inventory",
        "",
        "This inventory records where previous Renegade Vita screenshots and logs were found for the GitHub historical gallery. It intentionally excludes retail data, saves, credentials, raw dumps, and VPK payloads.",
        "",
        f"- Bash workspace scanned: `{ROOT}`",
        f"- GitHub gallery PNGs: {len(manifest)}",
        "- VitaShell FTP was checked read-only at `10.0.0.202:1337` for `ux0:/data/renegade/user/logs/`, `captures/`, and `screenshots/`; the latest audit found 24 runtime logs, 89 capture directories, and no files in the top-level screenshots folder.",
        "- All 89 live Vita capture directories are now represented locally between `build/device-evidence/vitashell-gallery-pull-20260828/`, `build/device-evidence/vitashell-gallery-pull-secondpass-*`, and `build/device-evidence/vitashell-gallery-pull-listingpass-*`.",
        "- `/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder` was not present; targeted AppData evidence came from the Vita3K user data root instead.",
        "- `/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs/` supplied the older A3.1 captures and logs.",
        "",
        "## Gallery By Build",
        "",
        "| Build | PNGs in GitHub gallery |",
        "| --- | ---: |",
    ]
    for build, count in sorted(gallery_by_build.items()):
        lines.append(f"| {build} | {count} |")

    lines.extend(
        [
            "",
            "## Scanned Roots",
            "",
            "| Label | Exists | Files | Type counts | Root |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for scan in scans:
        counts = ", ".join(f"{key}:{value}" for key, value in scan["counts_by_type"].items()) or "-"
        lines.append(
            f"| {scan['label']} | {scan['exists']} | {scan['file_count']} | {counts} | `{scan['root']}` |"
        )

    lines.extend(
        [
            "",
            "## Diagnostic-Only Or Loading-Only Screenshot Groups",
            "",
            "These builds have screenshot files but no useful gameplay screenshot in the current local/Vita/AppData/E: evidence set:",
            "",
            "`" + "`, `".join(build for build, _, _ in DIAGNOSTIC_ONLY) + "`.",
            "",
            "## Builds With Logs But No Screenshot File",
            "",
            "`" + "`, `".join(MISSING_SCREENSHOT_BUILDS) + "`.",
            "",
            "The full machine-readable inventory is `reports/generated/historical_evidence_inventory.json`.",
            "",
        ]
    )
    INVENTORY_MD.write_text("\n".join(lines), encoding="utf-8")


def write_readme() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    start = readme.index("## Historical Visual Progress")
    end = readme.index("## Current State")
    cells = []
    for filename in README_IMAGES:
        caption = label_from_filename(filename)
        cells.append(
            f'<td width="20%"><img src="docs/history/screenshots/{filename}" width="180" alt="{html.escape(caption, quote=True)}"></td>'
        )
    rows = ["<table>"]
    for index in range(0, len(cells), 5):
        rows.append("<tr>")
        rows.extend(cells[index : index + 5])
        rows.append("</tr>")
    rows.append("</table>")
    replacement = "\n".join(
        [
            "## Historical Visual Progress",
            "",
            "The first project artifact a GitHub reader sees is a gameplay-first visual progression grid. It deliberately excludes black/logo, magenta diagnostic, and loading-only frames; the clearly labelled Dev82 and Dev86 blocks below are exceptions so returned physical evidence is visible without being misrepresented as gameplay.",
            "The full [historical screenshot timeline](docs/HISTORICAL_SCREENSHOT_TIMELINE.md) includes every useful gameplay screenshot found per build, the exact returned Dev82 and Dev86 diagnostic frames, and a complete manifest of all GitHub-hosted evidence PNGs.",
            "",
            *rows,
            "",
            "### A3.5-dev82 — Returned Physical Diagnostic Frames",
            "",
            "These are the four raw physical-Vita capture records returned for Dev82. They document two inverted loading presentations, a byte-identical loading-image capture marked first-interactive, and a black initial interactive capture with a partial HUD; they are diagnostic evidence only, not gameplay acceptance.",
            "",
            image_table(DEV82_RETURNED_DIAGNOSTICS, columns=2).replace('src="history/screenshots/', 'src="docs/history/screenshots/'),
            "",
            "### A3.5-dev86 — Returned Physical Frontend Diagnostic Frame",
            "",
            "This returned original-loading-screen capture is diagnostic only. Original loading artwork and colored panels render, but the original UI text regions are blank; it is neither a main-menu frame nor gameplay acceptance.",
            "",
            image_table(DEV86_RETURNED_DIAGNOSTICS, columns=1).replace('src="history/screenshots/', 'src="docs/history/screenshots/'),
            "",
            "",
        ]
    )
    README_PATH.write_text(readme[:start] + replacement + readme[end:], encoding="utf-8")


def main() -> int:
    write_timeline()
    write_inventory()
    write_readme()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
