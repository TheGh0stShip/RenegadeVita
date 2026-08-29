#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	printf 'Usage: %s [--probe-only] [--scan-arp] [--remote-dir DIR] [--port PORT] [IP ...]\n' "$0" >&2
	printf 'Verify and upload the current A3.5-dev82 VPK to a reachable VitaShell FTP endpoint.\n' >&2
	printf 'Default IPs come from RENEGADE_VITA_IPS or the known PS Vita/PSTV addresses.\n' >&2
}

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
candidate_label=A3.5-dev82
vpk_path="$rv_root/dist/RenegadeVita-A3.5-dev82.vpk"
remote_dir=ux0:/data/renegade/user
ftp_port=${RENEGADE_VITASHELL_FTP_PORT:-1337}
probe_only=${RENEGADE_DEV82_UPLOAD_PROBE_ONLY:-0}
scan_arp=${RENEGADE_DEV82_UPLOAD_SCAN_ARP:-0}
declare -a requested_ips=()

while (($# > 0)); do
	case "$1" in
		-h|--help)
			usage
			exit 0
			;;
		--probe-only)
			probe_only=1
			shift
			;;
		--scan-arp)
			scan_arp=1
			shift
			;;
		--remote-dir)
			(($# >= 2)) || { usage; exit 2; }
			remote_dir=$2
			shift 2
			;;
		--port)
			(($# >= 2)) || { usage; exit 2; }
			ftp_port=$2
			shift 2
			;;
		--*)
			usage
			exit 2
			;;
		*)
			requested_ips+=("$1")
			shift
			;;
	esac
done

timestamp=$(date +%Y%m%d-%H%M%S)
evidence_dir=${RENEGADE_DEV82_UPLOAD_EVIDENCE_DIR:-"$rv_root/build/device-evidence/a35-dev82-upload-probe-$timestamp"}
mkdir -p "$evidence_dir"
transcript="$evidence_dir/upload-probe.txt"

log() {
	printf '%s\n' "$*" | tee -a "$transcript"
}

require_tool() {
	command -v "$1" >/dev/null 2>&1 || {
		log "missing required tool: $1"
		exit 2
	}
}

require_tool sha256sum
require_tool python3
require_tool timeout
require_tool bash

test -f "$vpk_path" || {
	log "missing VPK: $vpk_path"
	exit 2
}

expected_sha=$(python3 - "$rv_root/reports/BUILD_STATE.json" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    state = json.load(handle)
print(state["a3_5_dev82_m00_tutorial_full_correction_candidate"]["vpk_sha256"])
PY
)
actual_sha=$(sha256sum "$vpk_path" | awk '{print $1}')
if [[ "$actual_sha" != "$expected_sha" ]]; then
	log "VPK hash mismatch for $candidate_label"
	log "expected: $expected_sha"
	log "actual:   $actual_sha"
	exit 1
fi

log "$candidate_label upload probe"
log "vpk=$vpk_path"
log "sha256=$actual_sha"
log "remote_dir=$remote_dir"
log "ftp_port=$ftp_port"

declare -a ips=()
if ((${#requested_ips[@]} > 0)); then
	ips+=("${requested_ips[@]}")
elif [[ -n ${RENEGADE_VITA_IPS:-} ]]; then
	# shellcheck disable=SC2206
	ips+=(${RENEGADE_VITA_IPS})
else
	ips+=(10.0.0.202 10.0.0.186)
fi

if [[ "$scan_arp" == "1" ]] && command -v powershell.exe >/dev/null 2>&1; then
	while IFS= read -r arp_ip; do
		[[ -n "$arp_ip" ]] && ips+=("$arp_ip")
	done < <(powershell.exe -NoProfile -Command '$ips = Get-NetNeighbor -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -eq "Wi-Fi" -and $_.State -in @("Reachable","Stale","Probe") -and $_.IPAddress -like "10.0.0.*" } | Select-Object -ExpandProperty IPAddress -Unique; $ips' 2>/dev/null | tr -d '\r')
fi

mapfile -t ips < <(printf '%s\n' "${ips[@]}" | awk 'NF && !seen[$0]++')

probe_tcp() {
	local ip=$1
	local port=$2
	timeout 4 bash -c "</dev/tcp/$ip/$port" >/dev/null 2>&1
}

uploaded=0
for ip in "${ips[@]}"; do
	log "probe ftp://$ip:$ftp_port/"
	if ! probe_tcp "$ip" "$ftp_port"; then
		log "closed_or_unreachable $ip:$ftp_port"
		continue
	fi
	log "open $ip:$ftp_port"
	if [[ "$probe_only" == "1" ]]; then
		continue
	fi
	"$rv_root/tools/upload_vpk_ftp.sh" "$ip" "$vpk_path" "$remote_dir" 2>&1 | tee -a "$transcript"
	uploaded=1
	log "uploaded $candidate_label to ftp://$ip:$ftp_port/$remote_dir/$(basename "$vpk_path")"
	break
done

if [[ "$probe_only" == "1" ]]; then
	log "probe_only=1; no upload attempted"
	exit 0
fi

if [[ "$uploaded" != "1" ]]; then
	log "no reachable VitaShell FTP endpoint found; upload not attempted"
	exit 1
fi
