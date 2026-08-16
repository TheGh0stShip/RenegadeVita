#!/usr/bin/env bash
# Assemble reproducible, non-retail evidence for one A3.2-dev1 candidate.
# Optional paths are explicitly supplied by the hardware tester; only known
# log/capture/dump/image extensions are accepted and no Vita filesystem is
# accessed from the host.
set -Eeuo pipefail

rv_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
rv_dist=${1:?usage: collect_a32_diagnostics.sh DIST_DIR OUTPUT_ZIP [returned evidence...]}
rv_output=${2:?usage: collect_a32_diagnostics.sh DIST_DIR OUTPUT_ZIP [returned evidence...]}
shift 2

rv_dist=$(realpath -e -- "$rv_dist")
rv_output=$(realpath -m -- "$rv_output")
test -d "$rv_dist"
test -d "$(dirname -- "$rv_output")"
case "$rv_output" in
	*.zip) ;;
	*) echo "diagnostic output must end in .zip" >&2; exit 2 ;;
esac
rm -f -- "$rv_output"
rv_stage=$(mktemp -d)
trap 'rm -rf -- "$rv_stage"' EXIT
mkdir -p "$rv_stage/candidate" "$rv_stage/device-return"

for rv_name in \
	RenegadeVita-A3.2-dev1.vpk RenegadeVita-A3.2-dev1.elf \
	RenegadeVita-A3.2-dev1.map RenegadeVita-A3.2-dev1.elf-header.txt \
	RenegadeVita-A3.2-dev1.symbols.txt RenegadeVita-A3.2-dev1.vpk-contents.txt \
	A3.2-dev1-BUILD_REPORT.txt A3.2-dev1-HOST-VALIDATION.log \
	A3.2-dev1-COMPILER_LOG.txt A3.2-dev1-EXPECTED-RUNTIME-LOG.txt \
	A3.2-dev1-SOURCE_INTEGRATION_REPORT.json A3.2-dev1-HARDWARE-CANDIDATE.txt; do
	test -f "$rv_dist/$rv_name" && cp -- "$rv_dist/$rv_name" "$rv_stage/candidate/"
done


rv_copy_evidence() {
	rv_file=$1
	case "$rv_file" in
		*.log|*.txt|*.json|*.csv|*.bmp|*.png|*.jpg|*.jpeg|*.psp2dmp) ;;
		*) echo "refusing unrecognised evidence file: $rv_file" >&2; exit 2 ;;
	esac
	# A content prefix preserves duplicate basenames without retaining arbitrary
	# source paths in the diagnostic archive.
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
	echo "Renegade Vita A3.2-dev1 diagnostic manifest"
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
