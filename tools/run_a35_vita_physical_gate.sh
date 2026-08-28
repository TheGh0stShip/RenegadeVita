#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
	printf 'Usage: %s {dev6-pause|dev7-effects|dev8-scripts|dev9-m00-closure|dev10-completion-smoke|dev11-progress-smoke}\n' "$0" >&2
	exit 2
}

phase=${1:-}
expected_prior_alternate=
case "$phase" in
	dev6-pause)
		candidate=A3.5-dev6
		mode=pause
		expected_self=293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360
		expected_prior=ec08e891087243a6a44da8db29ef80bf9c485d31a6ef1b0f27423ea9626b59b1
		;;
	dev7-effects)
		candidate=A3.5-dev7
		mode=effects
		expected_self=7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5
		expected_prior=293768e9d79769b9872e1ad9d472c66305310032c74727d6e08a1a444ad52360
		;;
	dev8-scripts)
		candidate=A3.5-dev8
		mode=scripts
		expected_self=7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20
		expected_prior=7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5
		;;
	dev9-m00-closure)
		candidate=A3.5-dev9
		mode=scripts
		expected_self=231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88
		expected_prior=7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5
		expected_prior_alternate=7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20
		;;
	dev10-completion-smoke)
		candidate=A3.5-dev10
		mode=completion-smoke
		expected_self=32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339
		expected_prior=231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88
		;;
	dev11-progress-smoke)
		candidate=A3.5-dev11
		mode=progress-smoke
		expected_self=ceb491c609c92657f63cf3cd978d4f7674f41d360cda86b657929210441681ad
		expected_prior=231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88
		expected_prior_alternate=32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339
		;;
	*) usage ;;
esac

project_root=$(cd "$(dirname "$0")/.." && pwd)
vdb=$project_root/.agents/skills/vita-automated-runtime/scripts/vdb-ps-vita.sh
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
vpk=$dist_root/RenegadeVita-$candidate.vpk
title_id=RNEGA3101
remote_executable=ux0:/app/$title_id/eboot.bin
remote_log=ux0:/data/renegade/user/logs/${candidate,,}-runtime.log
remote_log=${remote_log//a3.5-/a35-}
timestamp=$(date -u +%Y%m%d-%H%M%S)
evidence_root=$project_root/build/device-evidence/${candidate,,}-$mode-$timestamp
backup_root=$project_root/build/device-backups/${candidate,,}-$mode-$timestamp
mkdir -p "$evidence_root" "$backup_root"
chmod 0700 "$evidence_root" "$backup_root"

test -x "$vdb"
test -f "$vpk"
if [[ $phase == dev7-effects ]]; then
	dev6_receipt=${RENEGADE_DEV6_GATE_RECEIPT:-}
	test -n "$dev6_receipt" || {
		printf 'RENEGADE_DEV6_GATE_RECEIPT must name the exact prior dev6 PASS receipt\n' >&2
		exit 2
	}
	jq -e '.candidate == "A3.5-dev6" and .mode == "pause" and .status == "PASS"' "$dev6_receipt" >/dev/null
	cp "$dev6_receipt" "$evidence_root/dev6-prerequisite-validation.json"
elif [[ $phase == dev8-scripts || $phase == dev9-m00-closure ]]; then
	dev6_receipt=${RENEGADE_DEV6_GATE_RECEIPT:-}
	test -n "$dev6_receipt" || {
		printf 'RENEGADE_DEV6_GATE_RECEIPT must name the exact prior dev6 PASS receipt\n' >&2
		exit 2
	}
	jq -e '.candidate == "A3.5-dev6" and .mode == "pause" and .status == "PASS"' "$dev6_receipt" >/dev/null
	dev7_receipt=${RENEGADE_DEV7_GATE_RECEIPT:-}
	test -n "$dev7_receipt" || {
		printf 'RENEGADE_DEV7_GATE_RECEIPT must name the exact prior dev7 PASS receipt\n' >&2
		exit 2
	}
	jq -e '.candidate == "A3.5-dev7" and .mode == "effects" and .status == "PASS"' "$dev7_receipt" >/dev/null
	cp "$dev6_receipt" "$evidence_root/dev6-prerequisite-validation.json"
	cp "$dev7_receipt" "$evidence_root/dev7-prerequisite-validation.json"
elif [[ $phase == dev10-completion-smoke || $phase == dev11-progress-smoke ]]; then
	dev9_receipt=${RENEGADE_DEV9_GATE_RECEIPT:-}
	test -n "$dev9_receipt" || {
		printf 'RENEGADE_DEV9_GATE_RECEIPT must name the exact prior dev9 PASS receipt\n' >&2
		exit 2
	}
	jq -e '.candidate == "A3.5-dev9" and .mode == "scripts" and .status == "PASS"' "$dev9_receipt" >/dev/null
	cp "$dev9_receipt" "$evidence_root/dev9-prerequisite-validation.json"
fi

run_json() {
	local receipt=$1
	shift
	if ! "$vdb" --json "$@" >"$receipt"; then
		return 1
	fi
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

tap() {
	local name=$1
	local target=$2
	run_json "$evidence_root/$name-press.json" input press "$target"
	sleep 0.2
	run_json "$evidence_root/$name-release.json" input release "$target"
}

hold_button_with_refresh() {
	local name=$1
	local target=$2
	local refresh
	run_json "$evidence_root/$name-press.json" input press "$target"
	# VitaCompanion occasionally acknowledges one long digital hold without the
	# bit reaching SceCtrl after prior lifecycle activity. Reasserting the same
	# pressed bit is idempotent and mirrors VDB's bounded emulation refresh.
	for refresh in $(seq 1 8); do
		sleep 0.5
		run_json "$evidence_root/$name-refresh-$refresh.json" input press "$target"
	done
	sleep 0.5
	run_json "$evidence_root/$name-release.json" input release "$target"
}

wait_for_log_marker() {
	local marker=$1
	local prefix=$2
	local attempts=$3
	local delay=$4
	local attempt local_log receipt session_log observed_sessions
	for ((attempt=1; attempt<=attempts; ++attempt)); do
		local_log=$evidence_root/$prefix-$attempt.log
		receipt=$evidence_root/$prefix-$attempt-pull.json
		if try_json "$receipt" logs --vdb1 pull "$remote_log" "$local_log"; then
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

deployed=0
readiness_reached=0
launch_requested=0
device_reached=0
prelaunch_session_count=0
prior_hash=
backup_file=
write_transport=
remote_stage=ux0:/data/renegade/user/${candidate,,}-eboot-$timestamp.stage

restore_prior_executable() {
	test -n "$backup_file" && test -f "$backup_file" && test -n "$prior_hash" || return 1
	local observed restore_stage
	try_json "$evidence_root/rollback-current-hash.json" fs hash --vdb1 "$remote_executable" || return 1
	observed=$(json_hash "$evidence_root/rollback-current-hash.json") || return 1
	[[ $observed == "$expected_self" ]] || return 1
	if [[ $write_transport == vdb1 ]]; then
		restore_stage=ux0:/data/renegade/user/${candidate,,}-rollback-$timestamp.stage
		run_json "$evidence_root/rollback-push.json" fs push --vdb1 "$backup_file" "$restore_stage"
		run_json "$evidence_root/rollback-replace.json" fs replace --vdb1 "$restore_stage" "$remote_executable" \
			--source-sha256 "$prior_hash" --destination-sha256 "$expected_self"
	else
		# VitaCompanion's TransferService uploads to a digest-bound temporary
		# name, verifies it, and renames it over the destination. The exact
		# current SELF was rechecked above and VDB1 verifies the restored hash.
		run_json "$evidence_root/rollback-network-push.json" fs push "$backup_file" "$remote_executable"
	fi
	run_json "$evidence_root/rollback-verify.json" fs hash --vdb1 "$remote_executable"
	[[ $(json_hash "$evidence_root/rollback-verify.json") == "$prior_hash" ]]
}

cleanup() {
	local status=$?
	trap - EXIT INT TERM
	set +e
	if ((device_reached)); then
		try_json "$evidence_root/final-input-release-all.json" input release all
	fi
	if ((device_reached && launch_requested)); then
		try_json "$evidence_root/cleanup-app-status.json" app status "$title_id"
		if jq -e '.ok == true and .result.running == true' "$evidence_root/cleanup-app-status.json" >/dev/null 2>&1; then
			try_json "$evidence_root/cleanup-app-kill.json" app kill --wait-exit --timeout 15 "$title_id"
		fi
	fi
	if ((status != 0 && deployed && !readiness_reached)); then
		restore_prior_executable >"$evidence_root/rollback.log" 2>&1
		rollback_status=$?
		printf 'launch/readiness failure rollback_status=%d\n' "$rollback_status" >&2
	fi
	if ((device_reached)); then
		try_json "$evidence_root/final-sleep-allow.json" sleep allow
		if [[ $write_transport == vdb1 ]]; then
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
if [[ $prior_hash != "$expected_prior" &&
	( -z $expected_prior_alternate || $prior_hash != "$expected_prior_alternate" ) &&
	$prior_hash != "$expected_self" ]]; then
	printf 'installed executable hash is outside the exact %s gate: %s\n' "$candidate" "$prior_hash" >&2
	exit 3
fi

candidate_eboot=$evidence_root/$candidate-eboot.bin
unzip -p "$vpk" eboot.bin >"$candidate_eboot"
chmod 0600 "$candidate_eboot"
[[ $(sha256sum "$candidate_eboot" | cut -d' ' -f1) == "$expected_self" ]]

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
		# Recheck the compare side immediately before the bounded FTP upload.
		run_json "$evidence_root/candidate-network-prior-hash.json" fs hash --vdb1 "$remote_executable"
		[[ $(json_hash "$evidence_root/candidate-network-prior-hash.json") == "$prior_hash" ]]
		run_json "$evidence_root/candidate-network-replace.json" fs push "$candidate_eboot" "$remote_executable"
	fi
	deployed=1
fi
run_json "$evidence_root/installed-candidate-hash.json" fs hash --vdb1 "$remote_executable"
[[ $(json_hash "$evidence_root/installed-candidate-hash.json") == "$expected_self" ]]

if try_json "$evidence_root/prelaunch-log-pull.json" logs --vdb1 pull "$remote_log" "$evidence_root/prelaunch-runtime.log"; then
	prelaunch_session_count=$(awk -v candidate="$candidate" \
		'index($0, "[LIFECYCLE] START") == 1 && index($0, "candidate=" candidate) {count++} END{print count+0}' \
		"$evidence_root/prelaunch-runtime.log")
fi

run_json "$evidence_root/app-launch.json" app launch --wait-running --timeout 15 "$title_id"
launch_requested=1
# The observed VitaGL-to-playable transition is about 30 seconds. Keep a
# bounded 45-second readiness window so the interaction route starts only
# after the original first render frame on a slower boot.
if ! wait_for_log_marker "A3.1 breadcrumb: first original render frame PASS" readiness 15 3; then
	printf 'candidate did not reach original interactive readiness within 45 seconds\n' >&2
	exit 5
fi
readiness_reached=1

if [[ $mode == progress-smoke ]]; then
	# The first rendered frame can occur while original M00 tutorial dialogue
	# intentionally owns the controls. Wait for the original scripts to make
	# objective 1 pending and re-enable the player before sending movement.
	if ! wait_for_log_marker "A3.5 mission progress: objective 1 pending and original player control available" tutorial-control 30 2; then
		printf 'candidate did not reach the original M00 player-control handoff within 60 seconds after first render\n' >&2
		exit 6
	fi
fi

if [[ $mode == pause ]]; then
	tap pause triangle
	wait_for_log_marker "A3.5 pause: original Combat suspended" pause-observation 5 1
	run_json "$evidence_root/paused-forward-press.json" input press left-stick 128 32
	run_json "$evidence_root/paused-look-press.json" input press right-stick 210 128
	sleep 3
	run_json "$evidence_root/paused-forward-release.json" input release left-stick
	run_json "$evidence_root/paused-look-release.json" input release right-stick
	tap resume triangle
	wait_for_log_marker "A3.5 pause: original Combat resumed" resume-observation 5 1
fi

# Exercise primary fire before synthetic analog input. Physical dev7 probes
# proved VitaCompanion's mixed analog/digital emulation can lose a later R
# hold, while this standing post-readiness route delivers raw 0x200 and reaches
# original WeaponClass. Recorded native replay will remove this bridge-only
# ordering constraint from later comparison runs.
hold_button_with_refresh fire r

# Bounded post-readiness interaction route. It walks and looks for several
# seconds, changes position, jumps, fires the primary weapon, and attempts the
# original Square action at multiple positions. No mission state is injected.
run_json "$evidence_root/walk-look-forward-press.json" input press left-stick 128 32
run_json "$evidence_root/walk-look-right-press.json" input press right-stick 205 128
sleep 4
run_json "$evidence_root/walk-look-forward-release.json" input release left-stick
run_json "$evidence_root/walk-look-right-release.json" input release right-stick
run_json "$evidence_root/strafe-press.json" input press left-stick 220 128
sleep 3
run_json "$evidence_root/strafe-release.json" input release left-stick
tap jump cross
sleep 3
run_json "$evidence_root/action-walk-press.json" input press left-stick 128 48
run_json "$evidence_root/action-press.json" input press square
sleep 3
run_json "$evidence_root/action-release.json" input release square
run_json "$evidence_root/action-walk-release.json" input release left-stick
tap action-second square
tap action-third square
tap capture select
sleep 4
tap clean-exit start
run_json "$evidence_root/app-exit-wait.json" app wait --exit-or-crash --timeout 20 "$title_id"
run_json "$evidence_root/app-final-status.json" app status "$title_id"
jq -e '.result.running == false' "$evidence_root/app-final-status.json" >/dev/null
run_json "$evidence_root/runtime-final-pull.json" logs --vdb1 pull "$remote_log" "$evidence_root/runtime-final.log"

awk '/^\[LIFECYCLE\] START/{session=""} {session=session $0 ORS} END{printf "%s", session}' \
	"$evidence_root/runtime-final.log" >"$evidence_root/latest-session.log"
# The engine logs Vita paths without the slash after the mount point, while
# VitaDevBridge accepts only canonical `ux0:/...` paths. Normalize only the
# fixed capture root extracted from this candidate's latest lifecycle session.
mapfile -t capture_paths < <(rg -o 'path=ux0:data/renegade/user/captures/[^ ]+' "$evidence_root/latest-session.log" |
	sed -e 's/^path=//' -e 's#^ux0:data/#ux0:/data/#' | sort -u)
capture_index=0
for capture_path in "${capture_paths[@]}"; do
	((capture_index+=1))
	try_json "$evidence_root/capture-$capture_index-archive.json" fs archive --vdb1 "$capture_path" "$evidence_root/capture-$capture_index.zip" || true
done
state_capture=$(printf '%s\n' "${capture_paths[@]}" | rg 'manual-select' | tail -1 || true)
if [[ -z $state_capture ]]; then
	# A short Select tap is not guaranteed to produce a capture before the
	# clean-exit request. The runtime's pre-clean-exit flush is the same bounded,
	# candidate-scoped telemetry and contains the final post-interaction state.
	state_capture=$(printf '%s\n' "${capture_paths[@]}" | rg 'pre-clean-exit' | tail -1 || true)
fi
test -n "$state_capture"
run_json "$evidence_root/manual-state-pull.json" fs pull --vdb1 "$state_capture/state.json" "$evidence_root/manual-state.json"
try_json "$evidence_root/selected-capture-frame-pull.json" fs pull --vdb1 "$state_capture/frame.bmp" "$evidence_root/selected-capture-frame.bmp" || true
try_json "$evidence_root/selected-capture-frames-pull.json" fs pull --vdb1 "$state_capture/frames.csv" "$evidence_root/selected-capture-frames.csv" || true
try_json "$evidence_root/selected-capture-summary-pull.json" fs pull --vdb1 "$state_capture/summary.txt" "$evidence_root/selected-capture-summary.txt" || true
python3 "$project_root/tools/validate_a35_physical_gate.py" --candidate "$candidate" --mode "$mode" \
	--log "$evidence_root/runtime-final.log" --state "$evidence_root/manual-state.json" >"$evidence_root/gate-validation.json"

printf 'physical_gate=PASS candidate=%s evidence=%s\n' "$candidate" "$evidence_root"
