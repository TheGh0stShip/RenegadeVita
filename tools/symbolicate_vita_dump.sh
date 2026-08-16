#!/usr/bin/env bash
# Produce an evidence-preserving GDB report for a gzip-wrapped Vita psp2dmp.
# The caller supplies the exact matching candidate artefacts; this tool never
# guesses a build identity or writes to the candidate directory.
set -Eeuo pipefail

if [ "$#" -ne 5 ]; then
	printf 'usage: %s DUMP.psp2dmp CANDIDATE.elf CANDIDATE.map CANDIDATE.symbols.txt REPORT.txt\n' "$0" >&2
	exit 2
fi

rv_dump=$1
rv_elf=$2
rv_map=$3
rv_symbols=$4
rv_report=$5

for rv_input in "$rv_dump" "$rv_elf" "$rv_map" "$rv_symbols"; do
	test -f "$rv_input" || { printf 'missing required input: %s\n' "$rv_input" >&2; exit 2; }
done
command -v gdb >/dev/null 2>&1 || { echo 'gdb is required' >&2; exit 2; }
command -v gzip >/dev/null 2>&1 || { echo 'gzip is required' >&2; exit 2; }
command -v sha256sum >/dev/null 2>&1 || { echo 'sha256sum is required' >&2; exit 2; }
command -v file >/dev/null 2>&1 || { echo 'file is required' >&2; exit 2; }
command -v python3 >/dev/null 2>&1 || { echo 'python3 is required' >&2; exit 2; }

gzip -t -- "$rv_dump" || { echo 'Vita dump is not a valid gzip stream' >&2; exit 2; }
rv_core=$(mktemp "${TMPDIR:-/tmp}/renegade-vita-core.XXXXXX")
trap 'rm -f -- "$rv_core"' EXIT
gzip -cd -- "$rv_dump" > "$rv_core"
if ! file -- "$rv_core" | grep -Eq 'ELF 32-bit LSB core file, ARM'; then
	printf 'decompressed dump is not an ARM ELF core: %s\n' "$(file -- "$rv_core")" >&2
	exit 2
fi
rv_note_report="${rv_report%.txt}.core-notes.json"
python3 "$(dirname "$0")/parse_psp2_core.py" "$rv_dump" --output "$rv_note_report"

{
	echo 'Renegade Vita GDB symbolication report'
	echo 'The exact matching ELF/map/symbol input identity is recorded below.'
	echo 'GDB symbols an ELF core only after the Vita gzip wrapper is decompressed.'
	echo
	printf 'dump=%s\n' "$rv_dump"
	printf 'elf=%s\nmap=%s\nsymbols=%s\n' "$rv_elf" "$rv_map" "$rv_symbols"
	printf 'private_note_inventory=%s\n' "$rv_note_report"
	sha256sum -- "$rv_dump" "$rv_elf" "$rv_map" "$rv_symbols"
	printf 'decompressed_core=%s\n' "$(file -- "$rv_core")"
	echo
	echo '--- gdb ---'
	set +e
	gdb --quiet --batch "$rv_elf" "$rv_core" \
		-ex 'set pagination off' \
		-ex 'info files' \
		-ex 'info threads' \
		-ex 'thread apply all bt' \
		-ex 'info registers' \
		-ex 'quit'
	rv_gdb_status=$?
	set -e
	printf '\ngdb_exit_status=%u\n' "$rv_gdb_status"
	if [ "$rv_gdb_status" -ne 0 ]; then
		echo 'GDB could not completely decode this core; preserve this report and the input hashes.'
	fi
} > "$rv_report" 2>&1

printf 'Symbolication report: %s\n' "$rv_report"
printf 'PSP2 private-note inventory: %s\n' "$rv_note_report"
