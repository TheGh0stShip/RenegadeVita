#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	printf 'usage: %s [BASELINE_CRASH_SNAPSHOT.json]\n' "$0" >&2
	printf 'Collect a read-only VDB crash snapshot, pull new dumps, verify hashes, and run VDB PSP2 report.\n' >&2
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
	usage
	exit 0
fi
if (($# > 1)); then
	usage
	exit 2
fi

project_root=$(cd "$(dirname "$0")/.." && pwd)
candidate=${RENEGADE_CRASH_CANDIDATE:-A3.5-dev38}
default_builder_root=${RENEGADE_BUILDER_ROOT:-}
if [[ -z "$default_builder_root" ]]; then
	managed_builder_root="/mnt/c/Users/${USER}/AppData/Local/RenegadeVitaBuilder"
	if [[ -d "$managed_builder_root" && -w "$managed_builder_root" ]]; then
		default_builder_root=$managed_builder_root
	else
		default_builder_root=$project_root
	fi
fi
dist_root=${RENEGADE_DIST_ROOT:-$default_builder_root/dist}
candidate_elf=${RENEGADE_CRASH_ELF:-$dist_root/RenegadeVita-$candidate.elf}
crash_root=${RENEGADE_CRASH_ROOT:-ux0:/data}
helper=${RENEGADE_VDB_HELPER:-$project_root/.agents/skills/vita-automated-runtime/scripts/vdb-ps-vita.sh}
default_baseline=$project_root/build/device-evidence/a3.5-dev37-readonly-crash-retry-20260825T003102Z/crash-snapshot.json
baseline_snapshot=${1:-${RENEGADE_CRASH_BASELINE:-$default_baseline}}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
evidence_root=${RENEGADE_CRASH_EVIDENCE_ROOT:-$project_root/build/device-evidence/$candidate-manual-crash-$timestamp}

test -x "$helper"
test -f "$candidate_elf"
expected_elf=${RENEGADE_CRASH_ELF_SHA256:-$(sha256sum "$candidate_elf" | cut -d' ' -f1)}
install -d -m 700 "$evidence_root"

run_json() {
	local output=$1
	shift
	"$helper" --json "$@" >"$output" 2>"$output.stderr"
}

snapshot_json=$evidence_root/crash-snapshot.json
run_json "$snapshot_json" debug crash collect \
	--crash-root "$crash_root" \
	--snapshot-only \
	--max-crashes 64 \
	--max-file-bytes 67108864 \
	--max-total-bytes 134217728 \
	--workflow-timeout-seconds 45
jq -e '.ok == true and .result.device_mutation == false' "$snapshot_json" >/dev/null

selection_json=$evidence_root/crash-selection.json
if [[ -f "$baseline_snapshot" ]]; then
	delta_json=$evidence_root/crash-delta.json
	python3 "$project_root/tools/vdb_crash_snapshot_delta.py" "$baseline_snapshot" "$snapshot_json" --output "$delta_json" >/dev/null
	jq --arg baseline "$baseline_snapshot" \
		'{schema_version:1, selection:"new_since_baseline", baseline:$baseline, selected:.new_entries}' \
		"$delta_json" >"$selection_json"
else
	jq '{schema_version:1, selection:"latest_without_baseline", baseline:null, selected:([.result.snapshot.entries[] | select(.path and .sha256 and .size >= 0)] | sort_by(.path) | .[-1:] )}' "$snapshot_json" >"$selection_json"
fi

selected_count=$(jq '.selected | length' "$selection_json")
dump_dir=$evidence_root/crash-dumps
if ((selected_count == 0)); then
	jq --arg candidate "$candidate" --arg crash_root "$crash_root" --arg evidence_root "$evidence_root" \
		'{candidate:$candidate, crash_root:$crash_root, evidence_root:$evidence_root, selected_count:0, status:"NO_NEW_CRASH_DUMP"}' \
		<<<'{}' >"$evidence_root/crash-collection-summary.json"
	printf 'manual_crash_collection=NO_NEW_CRASH_DUMP evidence_root=%s\n' "$evidence_root"
	exit 0
fi

install -d -m 700 "$dump_dir"
index=0
while IFS= read -r entry; do
	((index += 1))
	remote_path=$(jq -er '.path' <<<"$entry")
	dump_sha=$(jq -er '.sha256' <<<"$entry")
	local_name=$(basename "$remote_path")
	local_dump=$dump_dir/$local_name
	run_json "$evidence_root/crash-$index-pull.json" fs pull --vdb1 "$remote_path" "$local_dump"
	test -f "$local_dump"
	actual_sha=$(sha256sum "$local_dump" | cut -d' ' -f1)
	if [[ "$actual_sha" != "$dump_sha" ]]; then
		printf 'crash dump hash mismatch path=%s expected=%s actual=%s\n' "$remote_path" "$dump_sha" "$actual_sha" >"$evidence_root/crash-$index-hash-mismatch.txt"
		exit 3
	fi
	python3 "$project_root/tools/parse_psp2_core.py" "$local_dump" --output "$dump_dir/$local_name.core-notes.json" >"$dump_dir/$local_name.parse.txt"
	run_json "$evidence_root/crash-$index-vdb-report.json" debug crash report \
		"$local_dump" \
		--core-sha256 "$dump_sha" \
		--elf "$candidate_elf" \
		--elf-sha256 "$expected_elf" \
		--module-name RenegadeVitaA31
done < <(jq -c '.selected[]' "$selection_json")

jq --arg candidate "$candidate" --arg crash_root "$crash_root" --arg evidence_root "$evidence_root" --argjson selected_count "$selected_count" \
	'{candidate:$candidate, crash_root:$crash_root, evidence_root:$evidence_root, selected_count:$selected_count, status:"ANALYZED"}' \
	<<<'{}' >"$evidence_root/crash-collection-summary.json"
printf 'manual_crash_collection=ANALYZED selected=%s evidence_root=%s\n' "$selected_count" "$evidence_root"
