#!/usr/bin/env python3
"""Run GitHub's publication gates on an exact Git tree, without local extras."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", help="commit/tree to check; defaults to staged index")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    command = (["git", "rev-parse", "--verify", f"{args.ref}^{{tree}}"]
               if args.ref else ["git", "write-tree"])
    tree = subprocess.check_output(command, cwd=root, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="renegade-publication-") as directory:
        snapshot = Path(directory)
        # git archive excludes ignored and unstaged files, just like CI checkout.
        archive = subprocess.Popen(["git", "archive", tree], cwd=root,
                                   stdout=subprocess.PIPE)
        try:
            unpack = subprocess.run(["tar", "-xf", "-", "-C", str(snapshot)],
                                    stdin=archive.stdout, check=False)
        finally:
            archive.stdout.close()
        archived = archive.wait()
        if archived or unpack.returncode:
            raise RuntimeError("could not materialize publication tree")
        subprocess.run(["git", "init", "-q"], cwd=snapshot, check=True)
        subprocess.run(["git", "add", "--all"], cwd=snapshot, check=True)
        for check in (
            [sys.executable, "tools/verify_public_docs.py", "--root", "."],
            [sys.executable, "tools/verify_repo_hygiene.py", "--root", "."],
            [sys.executable, "-m", "unittest", "tools.test_verify_public_docs",
             "tools.test_verify_repo_hygiene"],
        ):
            subprocess.run(check, cwd=snapshot, check=True)
    print(f"PASS: exact publication tree {tree}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
