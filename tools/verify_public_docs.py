#!/usr/bin/env python3
"""Validate public documentation links and evidence-status guardrails."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DOCUMENTS = (
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "VERSIONING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "docs/ARCHITECTURE.md",
    "docs/BUILDING.md",
    "docs/CONTROLS.md",
    "docs/CURRENT_STATUS.md",
    "docs/DEMO_CAPTURE.md",
    "docs/DEVELOPMENT.md",
    "docs/EVIDENCE.md",
    "docs/HISTORICAL_SCREENSHOT_TIMELINE.md",
    "docs/HISTORICAL_CAPTURE_CAMPAIGN.md",
    "docs/INSTALLING.md",
    "docs/QUICKSTART.md",
    "docs/TROUBLESHOOTING.md",
)

REQUIRED_TEXT = {
    "README.md": ("A3.1.4", "A3.5-dev93", "not a public game release"),
    "docs/CURRENT_STATUS.md": ("A3.5-dev87", "A3.5-dev93", "Local-only"),
    "docs/EVIDENCE.md": ("capture.screen.v1", "physical Vita"),
    "docs/HISTORICAL_SCREENSHOT_TIMELINE.md": ("Dev87", "not a controlled same-camera comparison"),
    "docs/HISTORICAL_CAPTURE_CAMPAIGN.md": ("dev1 through dev93", "post-render M00 PNG", "READY"),
}

LINK = re.compile(r"!?(?:\[[^\]]*\])\(([^)\s]+)(?:\s+[^)]*)?\)")


def is_external(target: str) -> bool:
    return target.startswith(("#", "/", "http://", "https://", "mailto:", "tel:"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []

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

    if failures:
        print("\n".join(f"FAIL: {failure}" for failure in failures), file=sys.stderr)
        return 1
    print(f"PASS: validated {len(DOCUMENTS)} public documents")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
