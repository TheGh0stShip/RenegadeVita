#!/usr/bin/env python3
"""Validate public documentation links and evidence-status guardrails."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DOCUMENTS = (
    "README.md",
    "CHANGELOG.md",
    "LICENSE-NOTICE.md",
    "CONTRIBUTING.md",
    "VERSIONING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "docs/ARCHITECTURE.md",
    "docs/BUILDING.md",
    "docs/BRANDING.md",
    "docs/CONTROLS.md",
    "docs/CURRENT_STATUS.md",
    "docs/DEMO_CAPTURE.md",
    "docs/DEVELOPMENT.md",
    "docs/EVIDENCE.md",
    "docs/HISTORICAL_SCREENSHOT_TIMELINE.md",
    "docs/HISTORICAL_CAPTURE_CAMPAIGN.md",
    "docs/INSTALLING.md",
    "docs/MULTIPLAYER.md",
    "docs/QUICKSTART.md",
    "docs/TROUBLESHOOTING.md",
    "docs/releases/A3.5-dev202.md",
    "docs/releases/A3.5-dev203.md",
    "docs/releases/A3.5-dev204.md",
)

LICENSE_FILES = {
    "LICENSE": "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
    "EA-SOURCE-LICENSE.md": "c13278f0aa0fc48b06dc6e623ef7349788b9d79eff74fd50fefebd5315846005",
}

CURRENT_CANDIDATE_DOCUMENTS = (
    "README.md",
    "CHANGELOG.md",
    "docs/BUILDING.md",
    "docs/CURRENT_STATUS.md",
    "docs/INSTALLING.md",
    "docs/MULTIPLAYER.md",
    "docs/QUICKSTART.md",
)

REQUIRED_TEXT = {
    "README.md": ("A3.1.4", "not a finished game release", "physical Vita"),
    "LICENSE-NOTICE.md": ("GNU GPL version 3", "EA additional terms"),
    "docs/CURRENT_STATUS.md": ("A3.1.4", "Physical Vita", "Campaign status"),
    "docs/MULTIPLAYER.md": ("TLS certificate and hostname verification", "Current Limits"),
    "docs/EVIDENCE.md": ("capture.screen.v1", "physical Vita"),
    "docs/HISTORICAL_SCREENSHOT_TIMELINE.md": ("Dev87", "not a controlled same-camera comparison"),
    "docs/HISTORICAL_CAPTURE_CAMPAIGN.md": ("dev1 through dev93", "post-render M00 PNG", "READY"),
}

LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")


def is_external(target: str) -> bool:
    return target.startswith(("#", "/", "http://", "https://", "mailto:", "tel:"))


def validate(root: Path) -> list[str]:
    root = root.resolve()
    failures: list[str] = []
    for relative, expected_hash in LICENSE_FILES.items():
        path = root / relative
        if not path.is_file():
            failures.append(f"missing complete license file: {relative}")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            failures.append(f"{relative}: license text differs from reviewed source")
    try:
        state = json.loads((root / "reports/BUILD_STATE.json").read_text(encoding="utf-8"))
        candidate = state["public_candidate"]
        label = candidate["label"]
        if not isinstance(label, str) or not re.fullmatch(r"A\d+\.\d+-dev\d+", label):
            raise ValueError("invalid public candidate label")
        report = (root / candidate["report"]).resolve()
        if not report.is_relative_to(root) or not report.is_file():
            raise ValueError("public candidate report is missing or outside the repository")
        for relative in CURRENT_CANDIDATE_DOCUMENTS:
            document = root / relative
            if document.is_file() and label not in document.read_text(encoding="utf-8"):
                failures.append(f"{relative}: missing current candidate {label}")
        for relative in ("README.md", "docs/BUILDING.md", "docs/QUICKSTART.md"):
            document = root / relative
            if document.is_file() and re.search(
                    r"RENEGADE_CANDIDATE_LABEL=A\d+\.\d+-dev\d+\b",
                    document.read_text(encoding="utf-8")):
                failures.append(f"{relative}: build example reuses a published candidate label")
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append(f"invalid public candidate metadata: {error}")

    for relative in DOCUMENTS:
        document = root / relative
        if not document.is_file():
            failures.append(f"missing required public document: {relative}")
            continue
        text = document.read_text(encoding="utf-8")
        for required in REQUIRED_TEXT.get(relative, ()):
            if required not in text:
                failures.append(f"{relative}: missing required status text {required!r}")
        for raw_target in LINK.findall(text):
            target = raw_target.strip("<>").split("#", 1)[0]
            if not target or is_external(target):
                continue
            resolved = (document.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                failures.append(f"{relative}: link escapes repository: {raw_target}")
                continue
            if not resolved.exists():
                failures.append(f"{relative}: missing linked path: {raw_target}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    failures = validate(args.root)
    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        return 1
    print(f"PASS: validated {len(DOCUMENTS)} public documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
