#!/usr/bin/env bash
# Assemble reproducible, non-retail evidence for one explicitly named A3.5
# development candidate.  The candidate label is part of the input so a later
# build cannot accidentally collect an earlier candidate's provenance.
# Optional paths come explicitly from the hardware tester; only evidence types
# are admitted, and this host tool never accesses a Vita filesystem.
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_dist=${1:?usage: collect_a35_diagnostics.sh DIST_DIR OUTPUT_ZIP CANDIDATE_LABEL [returned evidence...]}
rv_output=${2:?usage: collect_a35_diagnostics.sh DIST_DIR OUTPUT_ZIP CANDIDATE_LABEL [returned evidence...]}
rv_candidate=${3:?usage: collect_a35_diagnostics.sh DIST_DIR OUTPUT_ZIP CANDIDATE_LABEL [returned evidence...]}
shift 3
case "$rv_candidate" in A[0-9]*.[0-9]*-dev[0-9]*) ;; *) echo "invalid candidate label: $rv_candidate" >&2; exit 2 ;; esac

rv_dist=$(realpath -e -- "$rv_dist")
rv_output=$(realpath -m -- "$rv_output")
test -d "$rv_dist"
test -d "$(dirname -- "$rv_output")"
case "$rv_output" in *.zip) ;; *) echo "diagnostic output must end in .zip" >&2; exit 2 ;; esac
rm -f -- "$rv_output"
rv_stage=$(mktemp -d)
trap 'rm -rf -- "$rv_stage"' EXIT
mkdir -p "$rv_stage/candidate" "$rv_stage/device-return"

for rv_name in \
	RenegadeVita-"$rv_candidate".vpk RenegadeVita-"$rv_candidate".elf \
	RenegadeVita-"$rv_candidate".map RenegadeVita-"$rv_candidate".elf-header.txt \
	RenegadeVita-"$rv_candidate".symbols.txt RenegadeVita-"$rv_candidate".vpk-contents.txt \
	"$rv_candidate"-BUILD_REPORT.txt "$rv_candidate"-HOST-VALIDATION.log \
	"$rv_candidate"-COMPILER_LOG.txt "$rv_candidate"-EXPECTED-RUNTIME-LOG.txt \
	"$rv_candidate"-SOURCE_INTEGRATION_REPORT.json "$rv_candidate"-HARDWARE-CANDIDATE.txt \
	"$rv_candidate"-MILESTONE-GATE.md "$rv_candidate"-CRASH-SYMBOLICATION.txt \
	"$rv_candidate"-IDENTITY-VERIFICATION.json; do
	test -f "$rv_dist/$rv_name" && cp -- "$rv_dist/$rv_name" "$rv_stage/candidate/"
done

rv_copy_evidence() {
	rv_file=$1
	case "$rv_file" in
		*.log|*.txt|*.json|*.csv|*.bmp|*.png|*.jpg|*.jpeg|*.psp2dmp) ;;
		*) echo "refusing unrecognised evidence file: $rv_file" >&2; exit 2 ;;
	esac
	rv_digest=$(sha256sum -- "$rv_file" | awk '{print $1}')
	cp -- "$rv_file" "$rv_stage/device-return/${rv_digest}-$(basename -- "$rv_file")"
}

for rv_evidence in "$@"; do
	test -e "$rv_evidence" || { echo "returned evidence is missing: $rv_evidence" >&2; exit 2; }
	if test -f "$rv_evidence"; then
		rv_copy_evidence "$rv_evidence"
	elif test -d "$rv_evidence"; then
		find "$rv_evidence" -type f \( -name '*.log' -o -name '*.txt' -o -name '*.json' -o \
			-name '*.csv' -o -name '*.bmp' -o -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' \
			-o -name '*.psp2dmp' \) -print0 | sort -z |
			while IFS= read -r -d '' rv_file; do rv_copy_evidence "$rv_file"; done
	else
		echo "refusing non-regular evidence path: $rv_evidence" >&2
		exit 2
	fi
done

{
	echo "Renegade Vita $rv_candidate diagnostic manifest"
	echo "source_revision=3e00c3a1b97381bb28be89a35b856375e0629a08"
	echo "generated_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
	echo "device_return_files=$(find "$rv_stage/device-return" -type f | wc -l)"
	find "$rv_stage" -type f -print0 | sort -z | xargs -0 sha256sum
} > "$rv_stage/MANIFEST-SHA256.txt"
(
	cd "$rv_stage"
	zip -q -r "$rv_output" candidate device-return MANIFEST-SHA256.txt
)
echo "Diagnostics bundle: $rv_output"
