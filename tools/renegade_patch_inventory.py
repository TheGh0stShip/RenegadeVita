#!/usr/bin/env python3
"""Derive patch identity from the executable, ordered zero-fuzz staging list."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex


# Retained historical evidence, deliberately excluded from native staging.
RETIRED = {"wwnet-a31-network-posix.patch",
           "combat-a35-weaponview-reload-motion.patch",
           "combat-a35-weaponview-reload-visible-fallback.patch"}
RECEIPT = "staging/PATCH_INVENTORY.json"
REQUIRED_FLAGS = {"--batch", "--forward", "--fuzz=0", "--no-backup-if-mismatch", "-p1"}
MANUAL_COUNT = re.compile(
    r'EXPECTED_PATCH_COUNT\s*=\s*[0-9]+|patch_count["\']?\s*[:=]\s*[0-9]+'
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse_applications(source):
    """Parse the constrained patch commands, not their indentation/layout.

    Shell continuations join physical lines before tokenization. shlex handles
    whitespace, quotes, redirection and comments; this is deliberately not an
    evaluator for arbitrary shell programs or command substitutions.
    """
    applications = []
    logical_source = source.replace("\r\n", "\n").replace("\\\n", "")
    for line in logical_source.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if not re.match(r"patch(?:\s|$)", stripped):
            if re.search(r"\$(?:rv_root|\{rv_root\})/port/patches/", stripped):
                raise ValueError("Patch reference outside a standalone patch command")
            continue
        lexer = shlex.shlex(line, posix=True, punctuation_chars="<>;&|()")
        lexer.whitespace_split = True
        tokens = list(lexer)
        if tokens and tokens[-1] == ";":
            tokens.pop()
        if tokens.count("<") != 1 or tokens.index("<") != len(tokens) - 2:
            raise ValueError("Patch command requires exactly one input patch and no shell chaining")
        reference = re.fullmatch(
            r"\$(?:rv_root|\{rv_root\})/(?P<path>port/patches/[A-Za-z0-9_.-]+\.patch)",
            tokens[-1],
        )
        flags = set()
        directory = None
        arguments = iter(tokens[1:-2])
        for argument in arguments:
            if argument == "-d" and directory is None:
                value = next(arguments, "")
                target = re.fullmatch(
                    r"\$(?:rv_stage|\{rv_stage\})(?:/(?P<directory>[A-Za-z0-9_]+))?", value
                )
                if target is None:
                    raise ValueError("Patch target must be the staging root or a direct staged module")
                directory = target["directory"] or ""
            elif argument in REQUIRED_FLAGS and argument not in flags:
                flags.add(argument)
            else:
                raise ValueError(f"Unknown or repeated patch argument: {argument}")
        if reference is None or directory is None or flags != REQUIRED_FLAGS:
            raise ValueError("Patch command must retain all required zero-fuzz flags and rooted paths")
        applications.append({"path": reference["path"], "directory": directory})
    if not applications:
        raise ValueError("No registered patch applications in staging")
    return applications


def load_inventory(root):
    root = Path(root)
    script = root / "tools/stage_sources.sh"
    source = script.read_text(encoding="utf-8")
    matches = parse_applications(source)
    paths = [match["path"] for match in matches]
    if len(set(paths)) != len(paths):
        raise ValueError("A patch is registered more than once in tools/stage_sources.sh")
    registered = {Path(path).name for path in paths}
    if registered & RETIRED:
        raise ValueError("A retired evidence-only patch was registered for application")
    present = {path.name for path in (root / "port/patches").glob("*.patch")}
    missing = registered - present
    unregistered = present - registered - RETIRED
    if missing or unregistered:
        raise ValueError(f"Patch registry mismatch: missing={sorted(missing)}, unregistered={sorted(unregistered)}")
    # Prevent reintroducing a separately maintained count in either build path.
    for relative in ("tools/generate_integration_report.py", "tools/build.sh",
                     "tools/build_fast_candidate.sh"):
        if MANUAL_COUNT.search((root / relative).read_text(encoding="utf-8")):
            raise ValueError(f"Manual patch count forbidden in {relative}; derive it from staging")
    entries = []
    for match in matches:
        path = root / match["path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Patch must be a regular, non-symlink file: {path}")
        payload = path.read_bytes()
        if not payload or b"--- " not in payload or b"+++ " not in payload:
            raise ValueError(f"Patch lacks a unified-diff file header: {path}")
        entries.append({"path": match["path"],
                        "stage_directory": (match["directory"] or "").lstrip("/"),
                        "sha256": digest(payload)})
    identity = {"schema": 1, "registry": "tools/stage_sources.sh",
                "stage_script_sha256": digest(source.encode("utf-8")),
                "patch_count": len(entries), "patches": entries}
    identity["registry_sha256"] = digest(json.dumps(identity, sort_keys=True).encode("utf-8"))
    return identity


def require_staging_receipt(root, inventory):
    receipt = Path(root) / RECEIPT
    if not receipt.is_file() or receipt.is_symlink():
        raise ValueError("Successful patch staging receipt is missing; run tools/stage_sources.sh")
    if json.loads(receipt.read_text(encoding="utf-8")) != inventory:
        raise ValueError("Staging patch identities/order are stale; run tools/stage_sources.sh")


def require_report(path, inventory):
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = [{key: entry.get(key) for key in ("path", "stage_directory", "sha256")}
               for entry in report.get("patches", [])]
    if report.get("patch_count") != inventory["patch_count"] or entries != inventory["patches"]:
        raise ValueError("Integration report patch identities/order differ from successful staging")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--count", action="store_true")
    parser.add_argument("--check-staging", action="store_true")
    parser.add_argument("--write-staging-receipt", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    inventory = load_inventory(args.root)
    if args.write_staging_receipt:
        # Called only at the successful end of the set -e staging script.
        destination = args.root / RECEIPT
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
        temporary.replace(destination)
    if args.check_staging or args.report:
        require_staging_receipt(args.root, inventory)
    if args.report:
        require_report(args.report, inventory)
    if args.count:
        print(inventory["patch_count"])
    else:
        print(f"Patch inventory PASS: {inventory['patch_count']} ordered patches; "
              f"sha256={inventory['registry_sha256']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError) as error:
        raise SystemExit(f"Patch inventory preflight failed: {error}")
