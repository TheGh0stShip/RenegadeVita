#!/usr/bin/env python3
"""Deterministic repository hygiene checks.

The script inspects tracked files only and emits deterministic violations for
tracked artifacts that should not be committed to source control.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


FORBIDDEN_ARTIFACT_EXTENSIONS = {
    ".vpk",
    ".elf",
    ".self",
    ".core",
    ".dmp",
    ".psp2dmp",
    ".psp2core",
    ".dump",
}

FORBIDDEN_PATH_SEGMENTS = {
    "build",
    "dist",
    "logs",
    "log",
    "retail",
    "retail-pc",
}

FORBIDDEN_CRED_PATH_TOKEN_EXTENSIONS = {
    ".pem",
    ".key",
    ".crt",
    ".cer",
    ".p12",
    ".pfx",
    ".keystore",
    ".jks",
}

FORBIDDEN_CRED_BASENAME_PREFIXES = {
    ".env",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "private_key",
    "secret_key",
    "credentials",
    "credential",
    "secret",
    "api_token",
    "password",
}

PLACEHOLDER_TOKENS = {"<managed-dist>", "<managed-log-root>"}

TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".sh",
    ".bash",
    ".zsh",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".cxx",
    ".cmake",
    ".in",
    ".asm",
    ".S",
    ".json",
    ".yml",
    ".yaml",
    ".ini",
    ".xml",
    ".toml",
}

KNOWN_FIXTURE_PREFIXES = {
    "tools/fixtures/psp2_core/",
}

# Reject identity-bearing user-home paths, not generic paths embedded by the
# original engine or the portable build contract.
PATH_WINDOWS_USER_ABS_RE = re.compile(r"[A-Za-z]:\\Users\\[^\\\s\"']+")
PATH_WSL_USER_ABS_RE = re.compile(
    r"(?<![\\w/])/(?:home/[^/\s\"']+/|mnt/[a-z]{1,2}/Users/[^/\s\"']+/|Users/[^/\s\"']+/)"
)
PATH_KEY_MATERIAL_RE = re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH)\s+PRIVATE KEY-----")


def _relpath(repo_root: Path, path: str) -> Path:
    return Path(path).relative_to(repo_root)


def _git_tracked_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    raw = completed.stdout
    if not raw:
        return []
    # git ls-files -z returns a trailing NUL separator.
    return [Path(entry) for entry in raw.split("\x00") if entry]


def _append_violation(violations: list[dict[str, str]], file: Path, rule: str, detail: str) -> None:
    violations.append({"file": file.as_posix(), "rule": rule, "detail": detail})


def _forbidden_path(file: Path) -> str | None:
    for segment in file.parts:
        if segment.lower() in FORBIDDEN_PATH_SEGMENTS:
            return segment
    return None


def _is_allowed_fixture(file: Path) -> bool:
    path = file.as_posix()
    return any(path.startswith(prefix) for prefix in KNOWN_FIXTURE_PREFIXES)


def _is_credential_file(path: Path) -> bool:
    filename = path.name.lower()
    if filename in FORBIDDEN_CRED_BASENAME_PREFIXES:
        return True

    for token in FORBIDDEN_CRED_BASENAME_PREFIXES:
        if filename == token or filename.startswith(f"{token}.") or token in filename:
            if path.suffix.lower() in FORBIDDEN_CRED_PATH_TOKEN_EXTENSIONS or path.suffix == "":
                return True
    return False

def _contains_forbidden_local_paths(path: Path) -> bool | str:
    if path.suffix.lower() not in TEXT_EXTENSIONS:
        # Skip unreadable/binary payloads; this verifier is tracked-file-first
        # and intentionally does not inspect arbitrary binary content.
        return False

    try:
        data = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False

    for line in data.splitlines():
        if any(token in line for token in PLACEHOLDER_TOKENS):
            continue
        # The configurable managed-output default intentionally derives the
        # Windows profile from the current process rather than embedding one.
        if "${USER}" in line:
            continue
        if PATH_WINDOWS_USER_ABS_RE.search(line):
            return "windows_abs_path"
        if PATH_WSL_USER_ABS_RE.search(line):
            return "wsl_abs_path"
    return False


def _readable_symlink_target(path: Path) -> str:
    target = os.readlink(path)
    if target in PLACEHOLDER_TOKENS:
        return ""
    return target


def _is_machine_specific_symlink(path: Path, repo_root: Path) -> bool:
    target = _readable_symlink_target(path)
    if not target:
        return False

    if os.path.isabs(target):
        return True

    resolved = (path.parent / target).resolve()
    try:
        resolved.relative_to(repo_root)
        return False
    except ValueError:
        return True


def _contains_private_material(path: Path) -> bool:
    if path.suffix.lower() not in {".pem", ".key", ".crl", ".csr", ".txt", ".md", ".yaml", ".yml", ".cfg", ".json"}:
        return False
    try:
        data = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return False
    return PATH_KEY_MATERIAL_RE.search(data) is not None


def verify_repo(root: Path) -> list[dict[str, str]]:
    root = root.resolve()
    violations: list[dict[str, str]] = []
    tracked = _git_tracked_files(root)

    for tracked_path in sorted(tracked, key=lambda p: p.as_posix()):
        if tracked_path.is_absolute():
            continue
        full = root / tracked_path
        # A broken symlink must still be examined; it can encode a
        # machine-specific external target even when that target is absent.
        if not full.exists() and not full.is_symlink():
            continue

        if tracked_path.suffix.lower() in FORBIDDEN_ARTIFACT_EXTENSIONS:
            if not _is_allowed_fixture(tracked_path):
                _append_violation(
                    violations,
                    tracked_path,
                    "forbidden_artifact_extension",
                    f"{tracked_path.suffix.lower()} artifact must not be tracked",
                )

        if _is_credential_file(tracked_path):
            _append_violation(violations, tracked_path, "credential_file_signature", "credential-like tracked filename")

        segment = _forbidden_path(tracked_path)
        if segment:
            _append_violation(
                violations,
                tracked_path,
                "forbidden_path_segment",
                f"tracked path segment '{segment}' is disallowed",
            )

        if full.is_symlink() and _is_machine_specific_symlink(full, root):
            _append_violation(
                violations,
                tracked_path,
                "machine_specific_symlink",
                "tracked symlink resolves outside repository or uses an absolute target",
            )

        forbidden_path = _contains_forbidden_local_paths(full)
        if forbidden_path:
            _append_violation(
                violations,
                tracked_path,
                "local_path_leak",
                f"contains forbidden {forbidden_path} pattern",
            )

        if _contains_private_material(full):
            _append_violation(
                violations,
                tracked_path,
                "private_material_contents",
                "file contains private key material block",
            )

    return violations


def run(root: Path) -> int:
    violations = verify_repo(root)
    if violations:
        print(json.dumps({"status": "fail", "violations": violations}, sort_keys=True, indent=2))
        return 1
    print(json.dumps({"status": "pass", "violations": []}, sort_keys=True, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify repo is free of local artifacts and secrets")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to verify (default: cwd)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(args.root.resolve())


if __name__ == "__main__":
    sys.exit(main())
