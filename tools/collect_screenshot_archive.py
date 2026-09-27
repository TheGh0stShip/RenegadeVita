"""Read-only FTP collection of title-owned captures and their build metadata."""
import argparse
from ftplib import FTP, error_perm
import json
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=1337)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with FTP() as ftp:
        ftp.connect(args.host, args.port, timeout=15)
        ftp.login()
        ftp.cwd("ux0:/data/renegade/user/captures")
        listing = []
        # VitaCompanion supports LIST but can reject NLST with 502.
        ftp.retrlines("LIST", listing.append)
        receipts = []
        for line in listing:
            fields = line.split(maxsplit=8)
            if not line.startswith("d") or len(fields) != 9:
                continue
            name = fields[8]
            if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
                continue
            target = args.output / name
            target.mkdir(exist_ok=True)
            files = []
            for filename in ("state.json", "frame.bmp"):
                destination = target / filename
                if destination.is_file():
                    files.append(filename)
                    continue
                temporary = destination.with_suffix(destination.suffix + ".partial")
                try:
                    with temporary.open("wb") as handle:
                        ftp.retrbinary(f"RETR {name}/{filename}", handle.write)
                    temporary.rename(destination)
                    files.append(filename)
                except error_perm:
                    temporary.unlink(missing_ok=True)
            receipts.append({"capture": name, "files": files})
            print(f"{name}: {', '.join(files) or 'no supported files'}", flush=True)
    (args.output / "collection.json").write_text(json.dumps(receipts, indent=2) + "\n")


if __name__ == "__main__":
    main()
