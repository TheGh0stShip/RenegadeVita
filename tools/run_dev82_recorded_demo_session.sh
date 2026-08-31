#!/usr/bin/env bash
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_title_id=${RENEGADE_DEMO_TITLE_ID:-RNEGA3101}
rv_candidate_label=${RENEGADE_CANDIDATE_LABEL:-A3.5-dev86}
rv_timeout=${RENEGADE_DEMO_TIMEOUT_SECONDS:-900}
rv_launch_timeout=${RENEGADE_DEMO_LAUNCH_TIMEOUT_SECONDS:-45}
rv_vdb=${RENEGADE_VDB:-"$rv_root/.agents/skills/vita-automated-runtime/scripts/vdb-ps-vita.sh"}
rv_timestamp=$(date +%Y%m%d-%H%M%S)
rv_evidence_root=${RENEGADE_DEMO_EVIDENCE_ROOT:-"$rv_root/build/device-evidence/${rv_candidate_label,,}-recorded-demo-$rv_timestamp"}
rv_runtime_log_remote=${RENEGADE_RUNTIME_LOG_REMOTE:-ux0:/data/renegade/user/logs/a35-dev86-runtime.log}

usage() {
	printf '%s\n' \
		"Usage: tools/run_dev82_recorded_demo_session.sh" \
		"" \
		"Requires the Renegade demo recorder plugin to be installed manually first." \
		"The plugin starts recording when RNEGA3101 loads; plain Start stays with Renegade and L+Start finalizes." \
		"This script only launches the title, waits for exit/crash, and pulls the runtime log."
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
	usage
	exit 0
fi
if [ "$#" -ne 0 ]; then
	usage >&2
	exit 2
fi
case "$rv_timeout" in ''|*[!0-9]*|0) printf 'Invalid RENEGADE_DEMO_TIMEOUT_SECONDS: %s\n' "$rv_timeout" >&2; exit 2 ;; esac
case "$rv_launch_timeout" in ''|*[!0-9]*|0) printf 'Invalid RENEGADE_DEMO_LAUNCH_TIMEOUT_SECONDS: %s\n' "$rv_launch_timeout" >&2; exit 2 ;; esac
test -x "$rv_vdb" || {
	printf 'VitaDevBridge helper is unavailable or not executable: %s\n' "$rv_vdb" >&2
	exit 2
}

mkdir -p "$rv_evidence_root"

printf 'Renegade recorded demo session\n' | tee "$rv_evidence_root/summary.txt"
printf 'candidate=%s\n' "$rv_candidate_label" | tee -a "$rv_evidence_root/summary.txt"
printf 'title_id=%s\n' "$rv_title_id" | tee -a "$rv_evidence_root/summary.txt"
printf 'recorder=external Vita-MP4-Recorder-derived plugin, manual install required\n' | tee -a "$rv_evidence_root/summary.txt"
printf 'video_output=ux0:video, imported by the Vita Video app\n' | tee -a "$rv_evidence_root/summary.txt"

"$rv_vdb" --json app launch "$rv_title_id" --wait-running --timeout "$rv_launch_timeout" \
	| tee "$rv_evidence_root/app-launch.json"

set +e
"$rv_vdb" --json app wait "$rv_title_id" --exit-or-crash --timeout "$rv_timeout" \
	| tee "$rv_evidence_root/app-wait.json"
rv_wait_status=${PIPESTATUS[0]}
set -e

set +e
"$rv_vdb" --json logs --vdb1 pull "$rv_runtime_log_remote" "$rv_evidence_root/a35-dev82-runtime.log" \
	| tee "$rv_evidence_root/runtime-log-pull.json"
rv_log_status=${PIPESTATUS[0]}
set -e

printf 'wait_status=%s\n' "$rv_wait_status" | tee -a "$rv_evidence_root/summary.txt"
printf 'runtime_log_pull_status=%s\n' "$rv_log_status" | tee -a "$rv_evidence_root/summary.txt"
printf 'evidence_root=%s\n' "$rv_evidence_root" | tee -a "$rv_evidence_root/summary.txt"
printf 'Stop condition: use L+Start to finalize the recording, or exit the title cleanly for module-stop finalization.\n' | tee -a "$rv_evidence_root/summary.txt"

exit "$rv_wait_status"
