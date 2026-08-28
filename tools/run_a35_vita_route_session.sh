#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	printf 'Usage: %s {record|replay}\n' "$0" >&2
	exit 2
}

session_mode=${1:-}
[[ $session_mode == record || $session_mode == replay ]] || usage

project_root=$(cd "$(dirname "$0")/.." && pwd)
vdb=$project_root/.agents/skills/vita-automated-runtime/scripts/vdb-ps-vita.sh
validator=$project_root/tools/validate_vita_input_route.py
loading_validator=$project_root/tools/validate_vita_loading_capture.py
dist_root=/mnt/c/Users/steve/AppData/Local/RenegadeVitaBuilder/dist
candidate=A3.5-dev48
expected_self=0e61044df081b36b1a74da88c6157149cc27e818fca26f7bde537d00f710ec23
expected_elf=a4416e16a4678c645e492c91f55c4fc0decae095fb4589d947d9559ee1dc63bd
expected_prior_dev46=bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244
expected_prior_dev45=950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5
expected_prior_dev44=e24e6b7a4b27dc749a1e59ffae7276406fbeea0794c5891c066b75db3055e016
expected_prior_dev43=c81cf891597d97720190b997d79cb67b56fe12911349f31b7ae9e3dfffaba935
expected_prior_dev42=c964465bffe52ab14f2399c2518b2cbb4c8cf76d2b5780f24c20b4c3b43a2cfe
expected_prior_dev41=cc6bd37485ba25b60f7e78f90c5b4845afb85102f82e02ed7760b861d65e9309
expected_prior_dev40=f59209cdecd00dcc398e8c8a13b7af96e2a2c75ad6d737c2ec33b80069ae9461
expected_prior_dev39=ccd306883de8d18f6dd72c2d247e905727c970f31ad095aa52c8b19dde435d0f
expected_prior_dev38=d8293dc331ee4460f5ee4527f08d05085aed263fbfb9846550cf35b575b1184b
expected_prior_dev37=f4d05d0c79d0a63ec9c24a94e875f9a46555d8e813aa6272ec3eb50f20e23bce
expected_prior_dev36=4451964aeefd1c0e5f690852e7111986f28006dc45900aff292b06d8cdb9e636
expected_prior_dev35=1dbb00a3191b1cb11272ee1faf0ca083e480284b9e6d78d7c1c94a287ea3ec56
expected_prior_dev34=72aa828d090d3e74180b03582378c73c25a737b0ea7ffdc728c80564c35260ef
expected_prior_dev33=3f3f0519c16280137ab656d2761f7c659e54170cebeed00a09d316db0d515465
expected_prior_dev32=a45d2a8b54c48e89327eab498bf9a439f497093e85719ffbce76de664a3eef12
expected_prior_dev31=8375f3f30fe57e309bcf2b68b25a1e5f4a3a99f24953bbd36bd940cc2005c424
expected_prior_dev30=c3810e776f21ce7937c6a261893aed92ed3e5e0cafadf99e15020cb91094c52b
expected_prior_dev29=899df03c98153d8888d00192cf7ef40875901f77aaca96b7c7a2434883cd53f0
expected_prior_dev28=5d1226557ac8b2ce5d66c0f9ae8b59977af3fa3bc16fbb2b18ffbc39802b5aed
expected_prior_dev27=aa37b69ed826d4fbf5ad93506727a5aba4426bbddb16741afe48dfdc5bf9806d
expected_prior_dev26=8b2ff768f64d2f6d1ac0e79061eb734bb6c9cfa77246bdaebb82924a44de5b6f
expected_prior_dev25=08cdf12864c0eb67d0675983f61bc7543085f4713d89975015847189f5684d4c
expected_prior_dev24=1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30
expected_prior_dev23=9dbfbce006634472aec5ce13b300d3924f14e6d24fde6e6cd3730acbe22a12cd
expected_prior_dev22=528e1e87b97a88047c0b5ab65f1d7bba6d0f03a9edb37a1bca16b04bc3900bcf
expected_prior_dev21=93ad509992d1f2e286dbcb56648da1bf8fe966911d6fe0707a9ca7f07b9b66ec
expected_prior_dev20=5e4cc4a4ac44173158b5b897a733de6d46fb33390d7233641b760f83a86ce24f
expected_prior_dev19=901fd5a0d7cb137a782ee42c666a91e9d9ca56a7f95397703468b3044f92e125
expected_prior_dev18=058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278
expected_prior_dev17=6df5bc65e1c3846b65e1c659e7d355acc17b090ec22985215f94f02a7280d3ec
expected_prior_dev16=4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f
expected_prior_dev7=7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5
# This route was recorded before the TranslateDB object-factory closure.  The
# corrected dialogue rows change the original remark timing, so replaying it
# against dev47+ is semantically stale even though the v2 checksum is valid.
stale_pre_dialogue_route=5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895
expected_prior_hashes=("$expected_prior_dev46" "$expected_prior_dev45" "$expected_prior_dev44" "$expected_prior_dev43" "$expected_prior_dev42" "$expected_prior_dev41" "$expected_prior_dev40" "$expected_prior_dev39" "$expected_prior_dev38" "$expected_prior_dev37" "$expected_prior_dev36" "$expected_prior_dev35" "$expected_prior_dev34" "$expected_prior_dev33" "$expected_prior_dev32" "$expected_prior_dev31" "$expected_prior_dev30" "$expected_prior_dev29" "$expected_prior_dev28" "$expected_prior_dev27" "$expected_prior_dev26" "$expected_prior_dev25" "$expected_prior_dev24" "$expected_prior_dev23" "$expected_prior_dev22" "$expected_prior_dev21" "$expected_prior_dev20" "$expected_prior_dev19" "$expected_prior_dev18" "$expected_prior_dev17" "$expected_prior_dev16" "$expected_prior_dev7")
vpk=$dist_root/RenegadeVita-$candidate.vpk
candidate_elf=$dist_root/RenegadeVita-$candidate.elf
title_id=RNEGA3101
remote_executable=ux0:/app/$title_id/eboot.bin
remote_log=ux0:/data/renegade/user/logs/a35-dev48-runtime.log
remote_config=ux0:/data/renegade/user/config
remote_record_marker=$remote_config/input-record-once.flag
remote_replay_marker=$remote_config/input-replay-once.flag
remote_route=$remote_config/input-route-v1.bin
remote_retail=ux0:/data/renegade/retail/Data/M00_Tutorial.mix
timestamp=$(date -u +%Y%m%d-%H%M%S)
evidence_root=$project_root/build/device-evidence/a3.5-dev48-route-$session_mode-$timestamp
backup_root=$project_root/build/device-backups/a3.5-dev48-route-$session_mode-$timestamp
mkdir -p "$evidence_root" "$backup_root"
chmod 0700 "$evidence_root" "$backup_root"

test -x "$vdb"
test -f "$vpk"
test -f "$candidate_elf"
test -f "$validator"
test -f "$loading_validator"

run_json() {
	local receipt=$1
	shift
	"$vdb" --json "$@" >"$receipt"
	jq -e '.ok == true' "$receipt" >/dev/null
}

try_json() {
	local receipt=$1
	shift
	"$vdb" --json "$@" >"$receipt" 2>"$receipt.stderr"
}

json_hash() {
	jq -er '.result.sha256 | select(type == "string" and length == 64)' "$1"
}

remote_exists() {
	local name=$1
	local path=$2
	try_json "$evidence_root/$name-stat.json" fs stat --vdb1 "$path" &&
		jq -e '.ok == true' "$evidence_root/$name-stat.json" >/dev/null 2>&1
}

write_touch() {
	local name=$1
	local path=$2
	if [[ $write_transport == vdb1 ]]; then
		run_json "$evidence_root/$name.json" fs touch --vdb1 "$path"
	else
		local marker_file=$evidence_root/$name.flag
		install -m 0600 /dev/null "$marker_file"
		run_json "$evidence_root/$name.json" fs push "$marker_file" "$path"
	fi
}

write_remove() {
	local name=$1
	local path=$2
	if [[ $write_transport == vdb1 ]]; then
		run_json "$evidence_root/$name.json" fs remove --vdb1 "$path"
	else
		run_json "$evidence_root/$name.json" fs remove "$path"
	fi
}

write_push() {
	local name=$1
	local local_path=$2
	local remote_path=$3
	if [[ $write_transport == vdb1 ]]; then
		run_json "$evidence_root/$name.json" fs push --vdb1 "$local_path" "$remote_path"
	else
		run_json "$evidence_root/$name.json" fs push "$local_path" "$remote_path"
	fi
}

wait_for_log_marker() {
	local marker=$1
	local prefix=$2
	local attempts=$3
	local delay=$4
	local attempt local_log session_log observed_sessions
	for ((attempt=1; attempt<=attempts; ++attempt)); do
		local_log=$evidence_root/$prefix-$attempt.log
		if try_json "$evidence_root/$prefix-$attempt-pull.json" logs --vdb1 pull "$remote_log" "$local_log"; then
			observed_sessions=$(awk -v candidate="$candidate" \
				'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {count++} END{print count+0}' "$local_log")
			session_log=$evidence_root/$prefix-$attempt-session.log
			awk -v candidate="$candidate" \
				'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {session=""} {session=session $0 ORS} END{printf "%s", session}' \
				"$local_log" >"$session_log"
			if ((observed_sessions > prelaunch_session_count)) && rg -Fq "$marker" "$session_log"; then
				cp "$local_log" "$evidence_root/$prefix-latest.log"
				return 0
			fi
		fi
		try_json "$evidence_root/$prefix-$attempt-status.json" app status "$title_id" || true
		if [[ -f $evidence_root/$prefix-$attempt-status.json ]] &&
			! jq -e '.ok == true and .result.running == true' "$evidence_root/$prefix-$attempt-status.json" >/dev/null 2>&1; then
			return 1
		fi
		sleep "$delay"
	done
	return 1
}

pull_candidate_log() {
	local label=$1
	local local_log=$evidence_root/$label-runtime.log
	if try_json "$evidence_root/$label-runtime-pull.json" logs --vdb1 pull "$remote_log" "$local_log"; then
		awk -v candidate="$candidate" \
			'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {session=""} {session=session $0 ORS} END{printf "%s", session}' \
			"$local_log" >"$evidence_root/$label-latest-session.log"
		sha256sum "$local_log" "$evidence_root/$label-latest-session.log" \
			>"$evidence_root/$label-runtime-SHA256SUMS" 2>/dev/null || true
		return 0
	fi
	return 1
}

launch_app_bounded() {
	local attempt
	for attempt in 1 2 3; do
		if try_json "$evidence_root/app-launch-$attempt.json" app launch --wait-running --timeout 45 "$title_id" &&
			jq -e '.ok == true' "$evidence_root/app-launch-$attempt.json" >/dev/null 2>&1; then
			cp "$evidence_root/app-launch-$attempt.json" "$evidence_root/app-launch.json"
			return 0
		fi
		try_json "$evidence_root/app-launch-$attempt-status.json" app status "$title_id" || true
		if [[ -f $evidence_root/app-launch-$attempt-status.json ]] &&
			jq -e '.ok == true and .result.running == true' "$evidence_root/app-launch-$attempt-status.json" >/dev/null 2>&1; then
			cp "$evidence_root/app-launch-$attempt.json" "$evidence_root/app-launch.json"
			return 0
		fi
		sleep 2
	done
	return 1
}

deployed=0
launch_requested=0
device_reached=0
marker_created=0
new_route_retained=0
old_route_backed_up=0
route_source_uploaded=0
prelaunch_session_count=0
prior_hash=
backup_file=
old_route_backup=$backup_root/input-route-v1-before-$timestamp.bin
write_transport=
remote_stage=ux0:/data/renegade/user/a35-dev48-eboot-$timestamp.stage
active_marker=$remote_record_marker
[[ $session_mode == replay ]] && active_marker=$remote_replay_marker
route_source=${RENEGADE_ROUTE_FILE:-}
minimum_replay_samples=${RENEGADE_MIN_REPLAY_SAMPLES:-4000}
[[ $minimum_replay_samples =~ ^[0-9]+$ ]] || {
	printf 'RENEGADE_MIN_REPLAY_SAMPLES must be a non-negative integer\n' >&2
	exit 2
}

restore_prior_executable() {
	test -n "$backup_file" && test -f "$backup_file" && test -n "$prior_hash" || return 1
	local observed restore_stage
	try_json "$evidence_root/rollback-current-hash.json" fs hash --vdb1 "$remote_executable" || return 1
	observed=$(json_hash "$evidence_root/rollback-current-hash.json") || return 1
	[[ $observed == "$expected_self" ]] || return 1
	if [[ $write_transport == vdb1 ]]; then
		restore_stage=ux0:/data/renegade/user/a35-dev48-rollback-$timestamp.stage
		run_json "$evidence_root/rollback-push.json" fs push --vdb1 "$backup_file" "$restore_stage"
		run_json "$evidence_root/rollback-replace.json" fs replace --vdb1 "$restore_stage" "$remote_executable" \
			--source-sha256 "$prior_hash" --destination-sha256 "$expected_self"
	else
		run_json "$evidence_root/rollback-network-push.json" fs push "$backup_file" "$remote_executable"
	fi
	run_json "$evidence_root/rollback-verify.json" fs hash --vdb1 "$remote_executable"
	[[ $(json_hash "$evidence_root/rollback-verify.json") == "$prior_hash" ]]
}

hash_is_admitted_prior() {
	local hash=$1
	local admitted
	for admitted in "${expected_prior_hashes[@]}"; do
		[[ $hash == "$admitted" ]] && return 0
	done
	return 1
}

collect_crash_baseline() {
	try_json "$evidence_root/crash-prelaunch-snapshot.json" debug crash collect \
		--crash-root ux0:/data \
		--snapshot-only \
		--max-crashes 32 \
		--max-file-bytes 67108864 \
		--max-total-bytes 134217728 \
		--workflow-timeout-seconds 30 || return 0
}

collect_postrun_crashes() {
	local label=$1
	local post_snapshot delta_json dump_dir new_count entry remote_path dump_sha local_name local_dump actual_sha index
	jq -e '.ok == true' "$evidence_root/crash-prelaunch-snapshot.json" >/dev/null 2>&1 || return 0
	[[ -f $candidate_elf ]] || return 0
	post_snapshot="$evidence_root/crash-$label-snapshot.json"
	delta_json="$evidence_root/crash-$label-delta.json"
	dump_dir="$evidence_root/crash-dumps-$label"
	try_json "$post_snapshot" debug crash collect \
		--crash-root ux0:/data \
		--snapshot-only \
		--max-crashes 32 \
		--max-file-bytes 67108864 \
		--max-total-bytes 134217728 \
		--workflow-timeout-seconds 45 || return 0
	jq -e '.ok == true' "$post_snapshot" >/dev/null 2>&1 || return 0
	python3 "$project_root/tools/vdb_crash_snapshot_delta.py" \
		"$evidence_root/crash-prelaunch-snapshot.json" "$post_snapshot" --output "$delta_json" >/dev/null 2>&1 || return 0
	new_count=$(jq -er '.new_count' "$delta_json" 2>/dev/null || echo 0)
	((new_count > 0)) || return 0
	install -d -m 700 "$dump_dir"
	index=0
	while IFS= read -r entry; do
		((index += 1))
		remote_path=$(jq -er '.path' <<<"$entry") || continue
		dump_sha=$(jq -er '.sha256' <<<"$entry") || continue
		local_name=$(basename "$remote_path")
		local_dump="$dump_dir/$local_name"
		try_json "$evidence_root/crash-$label-$index-pull.json" fs pull --vdb1 "$remote_path" "$local_dump" || continue
		[[ -f $local_dump ]] || continue
		actual_sha=$(sha256sum "$local_dump" | cut -d' ' -f1)
		[[ $actual_sha == "$dump_sha" ]] || {
			printf 'crash dump hash mismatch path=%s expected=%s actual=%s\n' "$remote_path" "$dump_sha" "$actual_sha" >"$evidence_root/crash-$label-$index-hash-mismatch.txt"
			continue
		}
		try_json "$evidence_root/crash-$label-$index-report.json" debug crash report \
			"$local_dump" \
			--core-sha256 "$dump_sha" \
			--elf "$candidate_elf" \
			--elf-sha256 "$expected_elf" \
			--module-name RenegadeVitaA31 || true
	done < <(jq -c '.new_entries[]' "$delta_json")
}

cleanup() {
	local status=$?
	trap - EXIT INT TERM
	set +e
	if ((device_reached)); then
		try_json "$evidence_root/final-input-release-all.json" input release all
	fi
	if ((device_reached && launch_requested)); then
		if ((status != 0)); then
			collect_postrun_crashes failure
		fi
		pull_candidate_log failure-before-kill || true
		try_json "$evidence_root/cleanup-app-status.json" app status "$title_id"
		if jq -e '.ok == true and .result.running == true' "$evidence_root/cleanup-app-status.json" >/dev/null 2>&1; then
			try_json "$evidence_root/cleanup-app-kill.json" app kill --wait-exit --timeout 15 "$title_id"
		fi
		pull_candidate_log failure-after-kill || true
	fi
	if ((device_reached && marker_created)) && remote_exists cleanup-active-marker "$active_marker"; then
		write_remove cleanup-active-marker-remove "$active_marker"
	fi
	if ((status != 0 && old_route_backed_up && !new_route_retained)) &&
		[[ $session_mode == record || $route_source_uploaded == 1 ]]; then
		write_push rollback-old-route "$old_route_backup" "$remote_route"
		try_json "$evidence_root/rollback-old-route-hash.json" fs hash --vdb1 "$remote_route"
	fi
	if ((status != 0 && route_source_uploaded && !old_route_backed_up && !new_route_retained)); then
		write_remove rollback-uploaded-route "$remote_route"
	fi
	if ((status != 0 && deployed)); then
		restore_prior_executable >"$evidence_root/rollback-executable.log" 2>&1
		rollback_status=$?
		printf 'failed session executable rollback_status=%d\n' "$rollback_status" >&2
	fi
	if ((device_reached)); then
		try_json "$evidence_root/final-sleep-allow.json" sleep allow
		if [[ $write_transport == vdb1 ]] && remote_exists final-stage "$remote_stage"; then
			try_json "$evidence_root/final-stage-remove.json" fs remove --vdb1 "$remote_stage"
		fi
	fi
	exit "$status"
}
trap cleanup EXIT INT TERM

run_json "$evidence_root/status.json" status
device_reached=1
run_json "$evidence_root/device-info.json" debug device-info
jq -e '.result.model == "ps_vita"' "$evidence_root/device-info.json" >/dev/null
run_json "$evidence_root/capabilities.json" capabilities --with-debugger
if jq -e '
	.result.providers.debugger.available == true and
	(.result.providers.debugger.capabilities | index("file.write.v1")) and
	(.result.providers.debugger.capabilities | index("file.replace.v1"))
' "$evidence_root/capabilities.json" >/dev/null; then
	write_transport=vdb1
elif jq -e '
	.result.device.capabilities as $capabilities |
	($capabilities | index("file.write.v1")) and
	($capabilities | index("file.rename.v1"))
' "$evidence_root/status.json" >/dev/null; then
	write_transport=vitacompanion-ftp
else
	printf 'no admitted file-write/rename transport is available for the exact PS Vita\n' >&2
	exit 4
fi
printf 'candidate_write_transport=%s\n' "$write_transport"

run_json "$evidence_root/input-release-all.json" input release all
run_json "$evidence_root/screen-on.json" screen on
run_json "$evidence_root/sleep-prevent.json" sleep prevent
run_json "$evidence_root/preflight-app-status-before.json" app status "$title_id"
if jq -e '.result.running == true' "$evidence_root/preflight-app-status-before.json" >/dev/null; then
	run_json "$evidence_root/preflight-app-kill.json" app kill --wait-exit --timeout 15 "$title_id"
fi
run_json "$evidence_root/preflight-app-status.json" app status "$title_id"
jq -e '.result.running == false' "$evidence_root/preflight-app-status.json" >/dev/null

run_json "$evidence_root/installed-hash.json" fs hash --vdb1 "$remote_executable"
prior_hash=$(json_hash "$evidence_root/installed-hash.json")
if [[ $prior_hash != "$expected_self" ]] && ! hash_is_admitted_prior "$prior_hash"; then
			printf 'installed executable hash is outside the exact dev48/prior route gate: %s\n' "$prior_hash" >&2
	exit 3
fi

candidate_eboot=$evidence_root/$candidate-eboot.bin
unzip -p "$vpk" eboot.bin >"$candidate_eboot"
chmod 0600 "$candidate_eboot"
[[ $(sha256sum "$candidate_eboot" | cut -d' ' -f1) == "$expected_self" ]]
[[ $(sha256sum "$candidate_elf" | cut -d' ' -f1) == "$expected_elf" ]]

if [[ $prior_hash != "$expected_self" ]]; then
	backup_file=$backup_root/$title_id-$prior_hash.bin
	run_json "$evidence_root/installed-backup-pull.json" fs pull --vdb1 "$remote_executable" "$backup_file"
	chmod 0600 "$backup_file"
	[[ $(sha256sum "$backup_file" | cut -d' ' -f1) == "$prior_hash" ]]
	if [[ $write_transport == vdb1 ]]; then
		run_json "$evidence_root/candidate-stage-push.json" fs push --vdb1 "$candidate_eboot" "$remote_stage"
		run_json "$evidence_root/candidate-stage-hash.json" fs hash --vdb1 "$remote_stage"
		[[ $(json_hash "$evidence_root/candidate-stage-hash.json") == "$expected_self" ]]
		run_json "$evidence_root/candidate-replace.json" fs replace --vdb1 "$remote_stage" "$remote_executable" \
			--source-sha256 "$expected_self" --destination-sha256 "$prior_hash"
	else
		run_json "$evidence_root/candidate-network-prior-hash.json" fs hash --vdb1 "$remote_executable"
		[[ $(json_hash "$evidence_root/candidate-network-prior-hash.json") == "$prior_hash" ]]
		run_json "$evidence_root/candidate-network-replace.json" fs push "$candidate_eboot" "$remote_executable"
	fi
	deployed=1
fi
run_json "$evidence_root/installed-candidate-hash.json" fs hash --vdb1 "$remote_executable"
[[ $(json_hash "$evidence_root/installed-candidate-hash.json") == "$expected_self" ]]
run_json "$evidence_root/retail-before-hash.json" fs hash --vdb1 "$remote_retail"
retail_hash=$(json_hash "$evidence_root/retail-before-hash.json")

remote_exists conflicting-record "$remote_record_marker" && {
	printf 'record marker already exists; refusing to overwrite one-shot state\n' >&2
	exit 5
}
remote_exists conflicting-replay "$remote_replay_marker" && {
	printf 'replay marker already exists; refusing to overwrite one-shot state\n' >&2
	exit 5
}

if [[ $session_mode == record ]]; then
	if remote_exists old-route "$remote_route"; then
		run_json "$evidence_root/old-route-pull.json" fs pull --vdb1 "$remote_route" "$old_route_backup"
		chmod 0600 "$old_route_backup"
		run_json "$evidence_root/old-route-hash.json" fs hash --vdb1 "$remote_route"
		[[ $(sha256sum "$old_route_backup" | cut -d' ' -f1) == $(json_hash "$evidence_root/old-route-hash.json") ]]
		old_route_backed_up=1
		write_remove old-route-remove "$remote_route"
	fi
else
	if [[ -n $route_source ]]; then
		test -f "$route_source"
		python3 "$validator" --reject-truncated "$route_source" >"$evidence_root/route-source-validation.json"
		source_sample_count=$(jq -er '.sample_count' "$evidence_root/route-source-validation.json")
		if ((source_sample_count < minimum_replay_samples)); then
			printf 'selected replay route has only %u samples; minimum is %u\n' "$source_sample_count" "$minimum_replay_samples" >&2
			exit 10
		fi
		if remote_exists old-route "$remote_route"; then
			run_json "$evidence_root/old-route-pull.json" fs pull --vdb1 "$remote_route" "$old_route_backup"
			chmod 0600 "$old_route_backup"
			run_json "$evidence_root/old-route-hash.json" fs hash --vdb1 "$remote_route"
			[[ $(sha256sum "$old_route_backup" | cut -d' ' -f1) == $(json_hash "$evidence_root/old-route-hash.json") ]]
			old_route_backed_up=1
		fi
		write_push replay-route-source-upload "$route_source" "$remote_route"
		route_source_uploaded=1
		run_json "$evidence_root/replay-route-source-hash.json" fs hash --vdb1 "$remote_route"
		[[ $(json_hash "$evidence_root/replay-route-source-hash.json") == $(sha256sum "$route_source" | cut -d' ' -f1) ]]
	fi
	remote_exists replay-route "$remote_route" || {
		printf 'no recorded input route exists on the PS Vita\n' >&2
		exit 6
	}
	run_json "$evidence_root/replay-route-before-pull.json" fs pull --vdb1 "$remote_route" "$evidence_root/input-route-v1-before.bin"
	python3 "$validator" --reject-truncated "$evidence_root/input-route-v1-before.bin" >"$evidence_root/route-before-validation.json"
	replay_sample_count=$(jq -er '.sample_count' "$evidence_root/route-before-validation.json")
	if ((replay_sample_count < minimum_replay_samples)); then
		printf 'admitted replay route has only %u samples; minimum is %u\n' "$replay_sample_count" "$minimum_replay_samples" >&2
		exit 10
	fi
	replay_route_hash=$(sha256sum "$evidence_root/input-route-v1-before.bin" | cut -d' ' -f1)
	if [[ $replay_route_hash == "$stale_pre_dialogue_route" ]]; then
		printf 'replay route is stale for %s: it predates the TranslateDB dialogue-timing fix; run record to create a fresh route\n' "$candidate" >&2
		exit 11
	fi
fi

write_touch "$session_mode-marker-create" "$active_marker"
marker_created=1
remote_exists active-marker "$active_marker"

if try_json "$evidence_root/prelaunch-log-pull.json" logs --vdb1 pull "$remote_log" "$evidence_root/prelaunch-runtime.log"; then
	prelaunch_session_count=$(awk -v candidate="$candidate" \
		'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {count++} END{print count+0}' \
		"$evidence_root/prelaunch-runtime.log")
fi

if [[ $session_mode == record ]]; then
	printf '\nPRELAUNCH_USER_NOTICE candidate=%s\n' "$candidate"
	printf 'LOADING_SCREEN_VISUAL_GATE candidate=%s requirement=background_upright_aspect_fit_text_bar_aligned_progress_moving\n' "$candidate"
	printf 'If the loading screen is still wrong, abort now or press START after control returns; do not continue into route recording. No log-only result will be treated as visual acceptance.\n'
	printf 'If the loading screen is acceptable, begin playing as soon as the real M00 view accepts your controls; do not wait for the later telemetry-ready notice. The runner records both readiness checkpoints.\n\n'
fi
collect_crash_baseline
launch_requested=1
launch_app_bounded
if ! wait_for_log_marker "A3.1 breadcrumb: first original render frame PASS" readiness 15 3; then
	printf 'candidate did not reach original render readiness within 45 seconds\n' >&2
	exit 7
fi
if ! wait_for_log_marker "star/control=1/1" tutorial-control 30 2; then
	printf 'candidate did not reach original M00 player/control handoff within 60 seconds after first render\n' >&2
	exit 8
fi
route_activation_ready=0
if wait_for_log_marker "gameplay activation: active=1" route-activation 5 2; then
	route_activation_ready=1
else
	printf 'route activation was not observed before the manual window; continuing so an active player is not pulled out of the game\n' >&2
fi
if [[ $session_mode == record ]]; then
	printf '\nTELEMETRY_READY candidate=%s route_activation_observed=%s\n' "$candidate" "$route_activation_ready"
	printf 'Walk, look, jump/crouch, and use Square. If Logan appears to freeze you near jump training, wait about 10 seconds for original control to return, then keep going past the ladder until the pistol is granted. Fire only after the original tutorial grants the pistol. Inspect Havoc, NPC bodies, and sky. Press Select once, then START to finish.\n\n'
else
	printf 'REPLAY_ACTIVE candidate=%s route_sha256=%s\n' "$candidate" "$replay_route_hash"
fi

run_json "$evidence_root/app-exit-wait.json" app wait --exit-or-crash --timeout 600 "$title_id"
if jq -e '.result.observed == "crashed" or ((.result.status.native_result // 0) != 0)' "$evidence_root/app-exit-wait.json" >/dev/null 2>&1; then
	collect_postrun_crashes nonclean-exit
fi
run_json "$evidence_root/app-final-status.json" app status "$title_id"
jq -e '.result.running == false' "$evidence_root/app-final-status.json" >/dev/null
run_json "$evidence_root/input-release-after.json" input release all
run_json "$evidence_root/runtime-final-pull.json" logs --vdb1 pull "$remote_log" "$evidence_root/runtime-final.log"

	awk -v candidate="$candidate" \
		'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {session=""} {session=session $0 ORS} END{printf "%s", session}' \
		"$evidence_root/runtime-final.log" >"$evidence_root/latest-session.log"
	rg -Fq "[LIFECYCLE] END status=clean candidate=$candidate" "$evidence_root/latest-session.log"
	rg -Fq "Capture: PASS candidate=$candidate phase=original-loading-screen reason=level-ready" "$evidence_root/latest-session.log"
	rg -Fq "first original deformed skin submission" "$evidence_root/latest-session.log"
	rg -q 'A3\.5 skin: submissions=[1-9][0-9]* deformed_vertices=[1-9][0-9]* deformation_failures=0' "$evidence_root/latest-session.log"
	rg -q 'A3\.5 indexed: submissions=[1-9][0-9]* triangles=[1-9][0-9]* state_applications=[1-9][0-9]* rejected=0' "$evidence_root/latest-session.log"

if [[ $session_mode == record ]]; then
	rg -Fq "record admitted: version=2 max_samples=18000 timebase=recorded-delta-us" "$evidence_root/latest-session.log"
	rg -q 'record shutdown: committed=1 samples=[1-9][0-9]* truncated=0' "$evidence_root/latest-session.log"
else
	rg -q 'replay admitted: version=[12] samples=[1-9][0-9]* truncated=0' "$evidence_root/latest-session.log"
	rg -Fq "replay complete: injecting clean exit" "$evidence_root/latest-session.log"
	rg -Fq "START exit request detected" "$evidence_root/latest-session.log"
fi

run_json "$evidence_root/route-final-pull.json" fs pull --vdb1 "$remote_route" "$evidence_root/input-route-v1.bin"
python3 "$validator" --reject-truncated "$evidence_root/input-route-v1.bin" >"$evidence_root/route-validation.json"
route_hash=$(sha256sum "$evidence_root/input-route-v1.bin" | cut -d' ' -f1)
if ! rg -q 'A3\.5 effects:.* weapon=Weapon_Pistol_Player/[1-9][0-9]* .*fired_total=[1-9][0-9]*' "$evidence_root/latest-session.log"; then
	printf 'route did not reach original weapon/pistol progression; preserving evidence and rejecting this recording\\n' >&2
	exit 9
fi
if [[ $session_mode == replay ]]; then
	[[ $route_hash == "$replay_route_hash" ]]
fi

mapfile -t capture_paths < <(rg -o 'path=ux0:data/renegade/user/captures/[^ ]+' "$evidence_root/latest-session.log" |
	sed -e 's/^path=//' -e 's#^ux0:data/#ux0:/data/#' | sort -u)
loading_capture=$(printf '%s\n' "${capture_paths[@]}" | rg 'original-loading-screen-level-ready' | tail -1 || true)
test -n "$loading_capture"
run_json "$evidence_root/loading-screen-frame-pull.json" fs pull --vdb1 "$loading_capture/frame.bmp" "$evidence_root/loading-screen-frame.bmp"
run_json "$evidence_root/loading-screen-state-pull.json" fs pull --vdb1 "$loading_capture/state.json" "$evidence_root/loading-screen-state.json"
python3 "$loading_validator" \
	--candidate "$candidate" \
	--frame "$evidence_root/loading-screen-frame.bmp" \
	--state "$evidence_root/loading-screen-state.json" \
	>"$evidence_root/loading-screen-validation.json"
try_json "$evidence_root/loading-screen-annotated-frame-pull.json" fs pull --vdb1 "$loading_capture/frame-annotated.bmp" "$evidence_root/loading-screen-frame-annotated.bmp" || true
try_json "$evidence_root/loading-screen-summary-pull.json" fs pull --vdb1 "$loading_capture/summary.txt" "$evidence_root/loading-screen-summary.txt" || true
try_json "$evidence_root/loading-screen-frames-pull.json" fs pull --vdb1 "$loading_capture/frames.csv" "$evidence_root/loading-screen-frames.csv" || true

run_json "$evidence_root/retail-after-hash.json" fs hash --vdb1 "$remote_retail"
[[ $(json_hash "$evidence_root/retail-after-hash.json") == "$retail_hash" ]]
new_route_retained=1

capture_index=0
	for capture_path in "${capture_paths[@]}"; do
		((capture_index+=1))
		try_json "$evidence_root/capture-$capture_index-archive.json" fs archive --vdb1 "$capture_path" "$evidence_root/capture-$capture_index.zip" || true
	done
	state_capture=$(printf '%s\n' "${capture_paths[@]}" | rg 'manual-select' | tail -1 || true)
	if [[ -z $state_capture ]]; then
		state_capture=$(printf '%s\n' "${capture_paths[@]}" | rg 'pre-clean-exit' | tail -1 || true)
fi
test -n "$state_capture"
run_json "$evidence_root/selected-state-pull.json" fs pull --vdb1 "$state_capture/state.json" "$evidence_root/selected-state.json"
try_json "$evidence_root/selected-frame-pull.json" fs pull --vdb1 "$state_capture/frame.bmp" "$evidence_root/selected-frame.bmp" || true
try_json "$evidence_root/selected-frames-pull.json" fs pull --vdb1 "$state_capture/frames.csv" "$evidence_root/selected-frames.csv" || true
try_json "$evidence_root/selected-summary-pull.json" fs pull --vdb1 "$state_capture/summary.txt" "$evidence_root/selected-summary.txt" || true

jq -n \
	--arg candidate "$candidate" \
	--arg mode "$session_mode" \
	--arg self_sha256 "$expected_self" \
		--arg route_sha256 "$route_hash" \
		--arg retail_sha256 "$retail_hash" \
		--arg write_transport "$write_transport" \
		--arg loading_capture "$loading_capture" \
		--arg loading_validation "$evidence_root/loading-screen-validation.json" \
		--arg evidence "$evidence_root" \
		'{schema_version:1,status:"PASS",candidate:$candidate,mode:$mode,self_sha256:$self_sha256,route_sha256:$route_sha256,retail_m00_sha256:$retail_sha256,write_transport:$write_transport,loading_screen_capture_path:$loading_capture,loading_screen_validation_path:$loading_validation,evidence_root:$evidence,loading_screen_visual_gate:"schema-v4 metadata, native BMP, and broad full-frame content extent validated; operator observation still required before visual acceptance",claim_boundary:"runtime and capture evidence only; visual correctness requires physical user observation"}' \
		>"$evidence_root/session-receipt.json"
	sha256sum "$evidence_root/latest-session.log" "$evidence_root/input-route-v1.bin" \
		"$evidence_root/route-validation.json" "$evidence_root/loading-screen-frame.bmp" \
		"$evidence_root/loading-screen-state.json" "$evidence_root/loading-screen-validation.json" \
		"$evidence_root/session-receipt.json" \
		>"$evidence_root/SHA256SUMS"

printf 'route_session=PASS mode=%s candidate=%s route_sha256=%s evidence=%s\n' \
	"$session_mode" "$candidate" "$route_hash" "$evidence_root"
