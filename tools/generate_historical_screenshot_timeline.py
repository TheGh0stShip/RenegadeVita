#!/usr/bin/env python3
"""Regenerate the timeline from reviewed, committed screenshot catalogs."""

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

# These labels intentionally describe evidence provenance without publishing
# workstation-specific mount points in GitHub-facing reports.
WORKSPACE_LABEL = "<workspace>"
VITA3K_USER_LABEL = "<vita3k-data-root>/ux0/data/renegade/user"
MANAGED_BUILDER_LABEL = "<managed-builder-root>"
HISTORICAL_VITA_LOGS_LABEL = "<historical-evidence-root>/Vita Logs"
HISTORICAL_PROJECT_LABEL = "<historical-evidence-root>/workspace/active"


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
    ("A3.5-dev87", "a35-dev87-vita-recorder-m00-exterior-npc-t0040s.png", "Recorder-derived exterior NPC view"),
    ("A3.5-dev87", "a35-dev87-vita-recorder-m00-warfactory-door-t0080s.png", "Recorder-derived war-factory door"),
    ("A3.5-dev87", "a35-dev87-vita-recorder-m00-interior-console-t0120s.png", "Recorder-derived interior console"),
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
            "<historical-evidence-root>/Vita Logs/select-capture-p0-f2278-t76344972/",
            "<historical-evidence-root>/Vita Logs/select-capture-p0-f3232-t108422940/",
            "<historical-evidence-root>/Vita Logs/a31-runtime.log",
            "<historical-evidence-root>/Vita Logs/a31.1-runtime.log",
            "<historical-evidence-root>/Vita Logs/a31.4-runtime.log",
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
    {
        "title": "A3.5-dev87 - Returned Physical M00 Recorder Evidence",
        "build": "A3.5-dev87",
        "summary": (
            "Six selected stills are derived from the user-finalized 200.917-second physical-Vita MP4. "
            "They show settled exterior, war-factory, and interior M00 gameplay; the opening black/HUD-only "
            "transition was reviewed and intentionally excluded. This establishes a returned gameplay recording, "
            "not acceptance of Dev87's failed original-menu, subtitle, or intro-A/V gates."
        ),
        "images": [
            ("a35-dev87-vita-recorder-m00-exterior-t0020s.png", "Settled exterior M00 route"),
            ("a35-dev87-vita-recorder-m00-exterior-npc-t0040s.png", "Exterior NPC encounter"),
            ("a35-dev87-vita-recorder-m00-warfactory-door-t0080s.png", "War-factory door approach"),
            ("a35-dev87-vita-recorder-m00-interior-console-t0120s.png", "Interior console/gameplay HUD"),
            ("a35-dev87-vita-recorder-m00-interior-npc-t0160s.png", "Interior NPC encounter"),
            ("a35-dev87-vita-recorder-m00-interior-objective-t0190s.png", "Interior objective-area view"),
        ],
        "sources": [
            "build/device-evidence/a35-dev87-video-return-20260831T060240Z/raw/2026-08-31_004224.mp4 (local-only raw recording)",
            "build/device-evidence/a35-dev87-video-return-20260831T060240Z/README.md",
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


RECENT_CAPTURES = [
    (133, "vita3k/dev133-eva-objectives.png", "Vita3K", "Tutorial EVA objectives", "dev133-reload-return"),
    (134, "vita3k/dev134-eva-data.png", "Vita3K", "Tutorial EVA data screen", "dev134-refinery-return"),
    (195, "vita3k/dev195-purchase-terminal-diagnostic.png", "Vita3K", "Purchase terminal diagnostic; connection interrupted, not successful-join evidence", "dev195-tt-native-01"),
    (197, "pstv/dev197-m13-loading.png", "Physical PSTV", "M13 loading screen; PC keyboard prompts remain visible", "a35-dev197-pstv-20260927 / original-loading-screen-level-ready-t56845132"),
    (197, "pstv/dev197-exit-confirmation.png", "Physical PSTV", "Exit confirmation; this frame alone does not demonstrate completed exit", "a35-dev197-pstv-20260927 / pre-clean-exit-f15-t99517028"),
    (200, "vita3k/dev200-rencorner-purchase-dialog.png", "Vita3K", "RenCorner purchase dialog", "Previously published Dev200 capture"),
    (200, "vita3k/dev200-rencorner-purchase-response.png", "Vita3K", "RenCorner purchase response", "Previously published Dev200 capture"),
    (202, "vita3k/dev202-main-menu.png", "Vita3K", "Main menu", "Previously published Dev202 capture"),
    (202, "vita3k/dev202-practice-loading.png", "Vita3K", "Multiplayer Practice loading screen", "Previously published Dev202 capture"),
    (202, "vita3k/dev202-practice-gameplay.png", "Vita3K", "Multiplayer Practice world and HUD", "Previously published Dev202 capture"),
    (204, "vita3k/dev204-livearea.png", "Vita3K", "LiveArea presentation, not gameplay", "Previously published Dev204 capture"),
    (205, "vita3k/dev205-main-menu.png", "Vita3K", "Main menu; a still does not establish responsiveness", "dev205-campaign-first-menu-01"),
    (206, "vita3k/dev206-single-player-menu.png", "Vita3K", "Single-player menu, not save/load verification", "dev206-save05-reload-01"),
]

def recovered_catalog() -> list[dict]:
    entries = []
    for folder in ("build-captures", "physical-captures"):
        path = ROOT / "docs" / "history" / folder / "catalog.json"
        if path.exists():
            for entry in json.loads(path.read_text()):
                entries.append({**entry, "link": f"history/{folder}/{entry['file']}"})
    return entries


def additional_captures() -> list[dict]:
    entries = recovered_catalog()
    for build, filename, platform, caption, source in RECENT_CAPTURES:
        path = ROOT / "docs" / "media" / filename
        entries.append({"build": build, "link": f"media/{filename}",
                        "platform": platform, "caption": caption, "source": source,
                        "kind": "world" if filename.endswith("-gameplay.png") else "presentation", "sha256": sha256(path),
                        "dimensions": png_dimensions(path)})
    return entries


def chronological_sections() -> list[str]:
    sections = {}
    for section in GAMEPLAY_SECTIONS:
        match = re.search(r"dev(\d+)", section["title"])
        build = int(match.group(1)) if match else 0
        sections[build] = {"title": section["title"], "summary": section["summary"] + " I did not pad this section to 15 with loading screens or diagnostic-only frames.",
                           "images": [(rel_img(name), caption) for name, caption in section["images"]],
                           "sources": list(section["sources"])}
    for label, note, filename in DIAGNOSTIC_ONLY:
        build = int(label.split("dev")[1])
        images = [(filename, "Physical Vita: diagnostic capture")]
        if build == 82:
            images = DEV82_RETURNED_DIAGNOSTICS
            note = "All four raw capture records returned for Dev82 are retained here. They contain three distinct rendered images: two inverted loading presentations, a first-interactive record byte-identical to the full-frame loading image, and a black buffer with partial HUD. These must not be presented as gameplay proof."
        elif build == 86:
            images = DEV86_RETURNED_DIAGNOSTICS
            note = "The exact returned physical capture shows loading artwork, but the original WWUI text regions are blank. It is not a main-menu or gameplay acceptance image."
        sections[build] = {"title": f"{label} - Retained Capture Evidence", "summary": note,
                           "images": [(rel_img(name), caption) for name, caption in images],
                           "sources": []}
    seen = set()
    for entry in additional_captures():
        key = (entry["build"], entry["platform"], entry["sha256"])
        if key in seen:
            if entry["source"] not in sections[entry["build"]]["sources"]:
                sections[entry["build"]]["sources"].append(entry["source"])
            continue
        seen.add(key)
        section = sections.setdefault(entry["build"], {
            "title": f"A3.5-dev{entry['build']} - Retained Capture Evidence",
            "summary": "",
            "images": [], "sources": [],
        })
        section["images"].append((entry["link"], f"{entry['platform']}: {entry['caption']}"))
        if entry["source"] not in section["sources"]:
            section["sources"].append(entry["source"])
    lines = []
    for _, section in sorted(sections.items()):
        lines.extend([f"### {section['title']}", ""])
        if section["summary"]:
            lines.extend([section["summary"], ""])
        lines.extend([image_table(section["images"], columns=5, relative_paths=True), ""])
        if section["sources"]:
            lines.extend(["Source evidence:", "", source_list(section["sources"]), ""])
    return lines


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


def rel_img(name: str) -> str:
    return f"history/screenshots/{name}"


def image_cell(name: str, caption: str, width: int, relative_paths: bool = False) -> str:
    alt = html.escape(caption, quote=True)
    cap = html.escape(caption)
    link = name if relative_paths else rel_img(name)
    return f'<td width="{width}%"><img src="{link}" width="{220 if width <= 25 else 260}" alt="{alt}"><br>{cap}</td>'


def image_table(items: list[tuple[str, str]], columns: int = 5, relative_paths: bool = False) -> str:
    rows: list[str] = ["<table>"]
    width = 100 // columns
    for index in range(0, len(items), columns):
        rows.append("<tr>")
        for name, caption in items[index : index + columns]:
            rows.append(image_cell(name, caption, width, relative_paths))
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
    for entry in additional_captures():
        name = Path(entry["link"]).name
        width, height = entry["dimensions"]
        manifest_rows.append(f"| [`{name}`]({entry['link']}) | A3.5-dev{entry['build']} | {width}x{height} | `{entry['sha256']}` |")

    doc: list[str] = [
        "# Historical Screenshot Timeline",
        "",
        "This page collects web-viewable diagnostic screenshots from the Renegade Vita evidence tree. It is meant to show visual progression on GitHub without publishing retail data, raw dumps, saves, credentials, or a new runtime artifact.",
        "",
        "Evidence policy:",
        "",
        "- Source evidence came from `build/device-evidence/` in the bash workspace, read-only VitaShell FTP pulls recorded under `build/device-evidence/vitashell-gallery-pull-*`, targeted Vita3K AppData checks under `<vita3k-data-root>/ux0/data/renegade/user/`, and older A3.1 developer captures preserved under `<historical-evidence-root>/Vita Logs/`.",
        "- The gallery stores PNGs under `docs/history/` and `docs/media/` so GitHub can render them directly. Physical PS Vita, PSTV, and Vita3K captures are labeled separately.",
        "- Each build may include up to 15 displayed screenshots. World views, cinematics, menus, loading screens, and diagnostics are grouped together under that build in ascending build order.",
        "- Captions identify the platform and visible state. Black buffers are capture diagnostics, not proof that the game displayed a black screen. One historical loading-screen frame is displayed as a regression reference within Dev78's group.",
        "- Vita-pulled screenshots are mapped through each build's own `a35-devXX-runtime.log` capture paths before being included.",
        "- These images are historical evidence. They do not make dev82 physically accepted; dev82 still requires a returned Vita test with matching logs, screenshots/captures, and any crash dumps.",
        "",
        "## Current Capture Completeness",
        "",
        "The gallery is a reviewed history, not a controlled same-camera comparison. Its early A3.1/A3.5 gameplay frames are useful visual context, but later engine-timed captures were often loading, black, or diagnostic buffers. They must not be used to imply an unobserved regression or improvement.",
        "",
        "| Candidate | GitHub-hosted visual state |",
        "| --- | --- |",
        "| A3.1.4 | Accepted historical physical baseline; not acceptance of later builds. |",
        "| A3.5-dev5-Dev87 | Historical physical gameplay and separately labeled diagnostic captures. |",
        "| A3.5-dev104-Dev134 | Tutorial, menu, loading, and black-buffer captures from Vita3K and physical Vita. |",
        "| A3.5-dev135-Dev194 | Campaign world/cinematic captures and separately retained loading or black-buffer diagnostics. |",
        "| A3.5-dev195-Dev206 | Multiplayer, Practice, menu, and loading captures; physical PSTV and Vita3K evidence are labeled separately. |",
        "| A3.5-dev207 | Latest published experimental binary; no runtime capture exists in this reviewed archive. |",
        "",
        "Updated September 27, 2026: 108 numbered builds have retained captures, plus A3.1. No Dev207 runtime image is included. See [current status](CURRENT_STATUS.md) for present verification status and the complete manifest below for all retained images.",
        "",
        "## Quick Gameplay View",
        "",
        "This overview deliberately shows actual gameplay/world frames, including NPC detail crops, rather than one thumbnail from every build. Some later builds only produced loading, black, or diagnostic buffers locally; those are inventoried later but not promoted into this first visual impression.",
        "",
        image_table([(name, f"{build}: {caption}") for build, name, caption in QUICK_GAMEPLAY], columns=5),
        "",
        "## Screenshot Timeline",
        "",
        *chronological_sections(),
    ]


    doc.extend(
        [
            "",
            "## Builds With No Local Or Vita-Pulled Screenshot File",
            "",
            "The original early-build audit did not find matching PNG/BMP/JPG screenshot files for these build groups:",
            "",
            "`" + "`, `".join(MISSING_SCREENSHOT_BUILDS) + "`.",
            "",
            "Those builds should be added later only if matching diagnostic captures are returned or discovered with their evidence directories. Do not fabricate images from logs.",
            "",
            "## Complete Gallery Manifest",
            "",
            "All retained gallery images are listed below, including diagnostic-only captures. Additional provenance is available in the [emulator catalog](history/build-captures/catalog.json), [physical catalog](history/physical-captures/catalog.json), and [coverage summary](history/screenshot-coverage.json).",
            "",
            *manifest_rows,
            "",
        ]
    )
    TIMELINE_PATH.write_text("\n".join(doc), encoding="utf-8")


def file_entry(path: Path, root: Path, source_label: str) -> dict[str, object]:
    stat = path.stat()
    relative_path = str(path.relative_to(root)) if path.is_relative_to(root) else path.name
    return {
        "path": f"{source_label}/{relative_path}",
        "relative_path": relative_path,
        "size": stat.st_size,
        "type": path.suffix.lower().lstrip("."),
    }


def scan_root(label: str, path: Path, public_root: str) -> dict[str, object]:
    extensions = {".png", ".bmp", ".jpg", ".jpeg", ".log", ".txt", ".json", ".csv"}
    files = []
    if path.exists():
        for item in sorted(path.rglob("*")):
            text = str(item)
            if "/retail/" in text or "/retail-pc/" in text:
                continue
            if item.is_file() and item.suffix.lower() in extensions:
                files.append(file_entry(item, path, label))
    counts = defaultdict(int)
    for item in files:
        counts[str(item["type"])] += 1
    return {
        "label": label,
        "root": public_root,
        "exists": path.exists(),
        "file_count": len(files),
        "counts_by_type": dict(sorted(counts.items())),
        "files": files,
    }


def write_inventory() -> None:
    roots = [
        ("github_gallery", SCREENSHOT_DIR, "docs/history/screenshots"),
        ("active_device_evidence", ROOT / "build" / "device-evidence", "build/device-evidence"),
        ("active_logs", ROOT / "logs", "logs"),
        ("active_dist", ROOT / "dist", "dist"),
        ("vita3k_user_appdata", Path("/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K/ux0/data/renegade/user"), VITA3K_USER_LABEL),
        ("missing_c_local_builder_root", Path("/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder"), MANAGED_BUILDER_LABEL),
        ("e_vita_logs", Path("/mnt/e/Projects/RenegadeVitaBuilder/Vita Logs"), HISTORICAL_VITA_LOGS_LABEL),
        ("e_project_logs", Path("/mnt/e/Projects/RenegadeVitaBuilder/workspace/active/logs"), f"{HISTORICAL_PROJECT_LABEL}/logs"),
        ("e_project_dist", Path("/mnt/e/Projects/RenegadeVitaBuilder/dist"), "<historical-evidence-root>/dist"),
    ]
    scans = [scan_root(label, path, public_root) for label, path, public_root in roots]
    manifest = gallery_manifest()
    gallery_by_build = defaultdict(int)
    for item in manifest:
        gallery_by_build[build_ref(str(item["file"]))] += 1

    inventory = {
        "generated_from": WORKSPACE_LABEL,
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
        f"- Bash workspace scanned: `{WORKSPACE_LABEL}`",
        f"- GitHub gallery PNGs: {len(manifest)}",
        "- VitaShell FTP was checked read-only at `10.0.0.202:1337` for `ux0:/data/renegade/user/logs/`, `captures/`, and `screenshots/`; the latest audit found 24 runtime logs, 89 capture directories, and no files in the top-level screenshots folder.",
        "- All 89 live Vita capture directories are now represented locally between `build/device-evidence/vitashell-gallery-pull-20260828/`, `build/device-evidence/vitashell-gallery-pull-secondpass-*`, and `build/device-evidence/vitashell-gallery-pull-listingpass-*`.",
        "- `<managed-builder-root>` was not present; targeted AppData evidence came from the Vita3K user data root instead.",
        "- `<historical-evidence-root>/Vita Logs/` supplied the older A3.1 captures and logs.",
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


def main() -> int:
    write_timeline()
    # Preserve the original evidence inventory; new scans use the explicit
    # inventory_screenshot_sources.py workflow instead of rewriting history.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
