#!/usr/bin/env bash
set -Eeuo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
host="$root/build/host-a31-asan"
out=$(mktemp -d "$root/build/hud-fixed-layout-XXXXXX")
mkdir -p "$out/include" "$out/objects" "$out/user" "$out/cache" "$out/mods"
original="$root/upstream/CnC_Renegade/Code/wwlib/TARGA.H"
{
    printf '#include <stdint.h>\n'
    sed -E 's/long([[:space:]]+)(Extension|Developer|KeyColor|ColorCor|PostStamp|ScanLine);/int32_t\1\2;/' "$original"
    printf '\nstatic_assert(sizeof(TGAHeader) == 18, "TGA header disk layout");\n'
    printf 'static_assert(sizeof(TGA2Footer) == 26, "TGA footer disk layout");\n'
    printf 'static_assert(sizeof(TGA2Extension) == 495, "TGA extension disk layout");\n'
} > "$out/include/TARGA.H"
diff -u --label a/TARGA.H --label b/TARGA.H "$original" "$out/include/TARGA.H" > "$out/targa-layout.patch" || test "$?" -eq 1
ninja -C "$host" -t commands a31_m00_interactive_runtime > "$out/commands.txt"
ninja -C "$host" -t deps > "$out/dependencies.txt"
main_object='CMakeFiles/a31_interactive_runtime.dir/a31_interactive_main.cpp.o'
{
    awk '/^[^[:space:]]/ { object=$1; sub(/:$/, "", object) } /\/TARGA[.]H$/ { print object }' "$out/dependencies.txt"
    printf '%s\n' "$main_object"
} | sort -u > "$out/affected-objects.txt"
mapfile -t links < <(rg ' -o a31_m00_interactive_runtime ' "$out/commands.txt")
test "${#links[@]}" -eq 1
link=${links[0]}
main_source="$root/tools/host_a30_definitions/a31_interactive_main.cpp"
awk -v initialize="${RENEGADE_PROBE_INIT_FORMATS:-0}" '/Font3DInstanceClass \*large_font =/ && initialize == "1" { print "\t\t\tInit_D3D_To_WW3_Conversion();" } /REF_PTR_RELEASE\(large_font\);/ { print "\t\t\tconst bool large_digits = Probe_Original_HUD_Digit_Atlas(large_font, \"FONT12x16.TGA\");"; print "\t\t\tconst bool small_digits = Probe_Original_HUD_Digit_Atlas(small_font, \"FONT6x8.TGA\");"; print "\t\t\tif (!large_digits || !small_digits) passed = false;" } { print } /REF_PTR_RELEASE\(small_font\);/ { print "\t\t\tif (!passed) break;" }' "$main_source" > "$out/main.cpp"
index=0
while IFS= read -r object; do
    # Only replace objects actually linked into this original runtime.
    [[ "$link" == *"$object"* ]] || continue
    mapfile -t commands < <(rg -F -- " -o $object " "$out/commands.txt")
    test "${#commands[@]}" -eq 1
    command=${commands[0]}
    replacement="$out/objects/$index.o"
    command=${command//"$object"/"$replacement"}
    if [[ "$object" == "$main_object" ]]; then
        command=${command//"$main_source"/"$out/main.cpp"}
        command=${command/ -c / -include "$out/include/TARGA.H" -include "$root/experiments/hud-font-atlas/probe.h" -c }
    else
        command=${command/ -c / -include "$out/include/TARGA.H" -c }
    fi
    (cd "$host" && bash -c "$command") > "$out/objects/$index-compile.log" 2>&1
    link=${link//"$object"/"$replacement"}
    index=$((index + 1))
done < "$out/affected-objects.txt"
test "$index" -gt 1
link=${link/ -o a31_m00_interactive_runtime / -o "$out/runtime" }
(cd "$host" && bash -c "$link") > "$out/link.log" 2>&1
printf 'FIXED_LAYOUT_HOST_PROBE_READY objects=%s evidence=%s\n' "$index" "$out"
set +e
ASAN_OPTIONS='abort_on_error=1:detect_leaks=0:halt_on_error=1' timeout 120s \
    "$out/runtime" "$root/retail-pc" "$out/user" "$out/cache" "$out/mods" > "$out/runtime.log" 2>&1
status=$?
set -e
rg 'HUD_DIGIT_|ERROR: AddressSanitizer|interactive runtime:' "$out/runtime.log" || true
printf 'FIXED_LAYOUT_HOST_PROBE_EXIT=%s evidence=%s\n' "$status" "$out"
exit "$status"
