#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_cache=${RENEGADE_TT_REFERENCE_CACHE:-/tmp/renegade-vita-tt-reference/4.8.4-r9000}
rv_archive=$rv_cache/source-4.8.4.zip
rv_diff=$rv_cache/source-diff-4.8.4.diff
rv_audit=$rv_cache/TT-4.8.4-r9000-AUDIT.json

mkdir -p -- "$rv_cache"
chmod 0700 "$rv_cache"
if [[ ! -f "$rv_archive" ]]; then
	curl -fsSL --retry 3 -o "$rv_archive" \
		https://www.tiberiantechnologies.org/files/source-4.8.4.zip
fi
if [[ ! -f "$rv_diff" ]]; then
	curl -fsSL --retry 3 -o "$rv_diff" \
		https://www.tiberiantechnologies.org/files/source-diff-4.8.4.diff
fi

printf '5bf9acce0663514ea5e84ff5e0c16fb1  %s\n' "$rv_archive" | md5sum -c -
printf 'c746d12f7bbe06b99e3a15b6856ab3f4  %s\n' "$rv_diff" | md5sum -c -
printf '8d3c2df2af0b2a7bb49b4e1a0353947b49fc2b228f849024e1a7bf18a0fddfcd  %s\n' "$rv_archive" | sha256sum -c -
printf '6a73ca645b1591b3c0456bb34c859d8b4644a64401503ae0f30a8ee68d1e314b  %s\n' "$rv_diff" | sha256sum -c -
python3 "$rv_root/tools/audit_tt_reference.py" \
	--archive "$rv_archive" \
	--diff "$rv_diff" \
	--root "$rv_root" \
	--output "$rv_audit"
printf 'TT reference audit retained outside source tree: %s\n' "$rv_audit"
