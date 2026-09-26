#!/usr/bin/env python3
"""Provision a private TT client seed; never accepts a key on the command line."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import re
import sys


def derive(serial):
    # Restrict this provisioning route to the user's numeric retail edition.
    if not re.fullmatch(r"(?:[0-9]{22}|[0-9]{6}-[0-9]{6}-[0-9]{6}-[0-9]{4})", serial):
        raise ValueError("Expected a 22-digit retail serial (optional printed hyphens)")
    return hashlib.md5(serial.replace("-", "").encode("ascii")).hexdigest()


def store(path, seed):
    if not re.fullmatch(r"[0-9a-f]{32}", seed):
        raise ValueError("Invalid seed")
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError("Identity directory must be private (mode 0700)")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(seed + "\n")
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("Use a terminal with hidden input; no command-line or piped keys")
    try:
        store(args.output, derive(getpass.getpass("Retail serial (hidden): ")))
    except (OSError, ValueError) as error:
        parser.exit(1, "Identity not written: %s\n" % error)
    print("Private derived identity written; raw serial not stored.")
