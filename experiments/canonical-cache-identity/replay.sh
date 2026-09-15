#!/usr/bin/env bash
# Isolated ARM object/debug-identity experiment; does not change build flags.
set -Eeuo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
work=${1:?Pass a new absolute evidence directory}
case "$work" in /*) ;; *) printf 'Evidence directory must be absolute\n' >&2; exit 2 ;; esac
test ! -e "$work"
mkdir -p "$work"
sdk=${RENEGADE_VITASDK:-/usr/local/vitasdk}
compiler="$sdk/bin/arm-vita-eabi-g++"
printf 'int RenegadeCacheProbe(int value) { return value + 1; }\n' > "$work/source.cpp"
mkdir -p "$work/stable-context"
for mode in baseline mapped; do
    cache="$work/cache-$mode"
    for attempt in a b; do
        directory="$work/$mode-$attempt"
        mkdir -p "$directory"
        flags=()
        if [[ "$mode" == mapped ]]; then
            flags+=("-fdebug-prefix-map=$directory=$work/stable-context")
        fi
        (
            cd "$directory"
            CCACHE_DIR="$cache" CCACHE_BASEDIR="$work" \
                ccache "$compiler" -g -O2 "${flags[@]}" -c "$work/source.cpp" -o source.o
        )
    done
    CCACHE_DIR="$cache" ccache --show-stats > "$work/$mode-stats.txt"
    cat "$work/$mode-stats.txt"
done
cmp "$work/mapped-a/source.o" "$work/mapped-b/source.o"
"$sdk/bin/arm-vita-eabi-readelf" --debug-dump=info "$work/mapped-b/source.o" \
    > "$work/mapped-debug-info.txt"
"$sdk/bin/arm-vita-eabi-objdump" -d "$work/mapped-a/source.o" \
    > "$work/mapped-disassembly.txt"
"$sdk/bin/arm-vita-eabi-objcopy" -O binary --only-section=.text \
    "$work/baseline-a/source.o" "$work/baseline.text"
"$sdk/bin/arm-vita-eabi-objcopy" -O binary --only-section=.text \
    "$work/mapped-a/source.o" "$work/mapped.text"
cmp "$work/baseline.text" "$work/mapped.text"
rg 'DW_AT_(name|comp_dir)' "$work/mapped-debug-info.txt"
printf 'PASS: mapped object identity and baseline/mapped ARM instruction bytes match\n'
