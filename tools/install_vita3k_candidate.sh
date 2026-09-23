#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_candidate=${1:?usage: install_vita3k_candidate.sh CANDIDATE VPK}
rv_vpk=${2:?usage: install_vita3k_candidate.sh CANDIDATE VPK}
rv_vfs=${RENEGADE_VITA3K_VFS:-/mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K}
rv_exe=${RENEGADE_VITA3K_EXE:-/mnt/d/Vita3K/Vita3K.exe}
rv_receipts="$rv_root/build/vita3k-backups"

if [[ ! -d "$rv_vfs" ]]; then
	echo "Vita3K VFS not found: $rv_vfs" >&2
	exit 2
fi
if [[ ! -f "$rv_exe" ]]; then
	echo "Vita3K executable not found: $rv_exe" >&2
	exit 2
fi
if [[ ! -s "$rv_vpk" ]]; then
	echo "candidate VPK missing or empty: $rv_vpk" >&2
	exit 2
fi

rv_result=$(python3 "$rv_root/tools/prepare_vita3k_demo.py" \
	--vpk "$rv_vpk" --vfs "$rv_vfs" --evidence-root "$rv_receipts" \
	--candidate "$rv_candidate")
printf '%s\n' "$rv_result"
rv_receipt=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["receipt"])' "$rv_result")
python3 - "$rv_receipt" "$rv_vpk" "$rv_vfs" "$rv_candidate" <<'PY'
import hashlib
import json
import sys
import zipfile
from pathlib import Path

receipt_path = Path(sys.argv[1])
vpk_path = Path(sys.argv[2])
vfs_path = Path(sys.argv[3])
candidate = sys.argv[4]
receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
assert receipt["candidate"] == candidate
assert receipt["title_id"] == "RNEGA3101"
assert receipt["status"] == "INSTALLED_NOT_LAUNCHED"
assert receipt["retail_modified"] is False
def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
assert digest(vpk_path.read_bytes()) == receipt["vpk_sha256"]
with zipfile.ZipFile(vpk_path) as archive:
    expected_eboot = digest(archive.read("eboot.bin"))
    expected_param = digest(archive.read("sce_sys/param.sfo"))
installed = {
    "eboot.bin": digest((vfs_path / "ux0/app/RNEGA3101/eboot.bin").read_bytes()),
    "sce_sys/param.sfo": digest((vfs_path / "ux0/app/RNEGA3101/sce_sys/param.sfo").read_bytes()),
}
expected = {"eboot.bin": expected_eboot, "sce_sys/param.sfo": expected_param}
assert installed == expected, f"installed Vita3K title hashes do not match candidate: {installed}"
assert {entry["name"]: entry["installed_sha256"] for entry in receipt["files"]} == expected
print(f"Vita3K install verified: {candidate} RNEGA3101; launch not requested", file=sys.stderr)
PY
