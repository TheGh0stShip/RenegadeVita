# Dev115 background investigations

Dev115's checkpoint/EVA candidate remains unchanged by these experiments.

## Host font evidence limitation

The canonical original host runtime checks Font3D pointer existence, not
glyph pixels. An isolated stronger probe was compiled into that original
runtime using canonical ASan objects. It reached original font initialization
but found a 0x0 source surface and `Targa::Open` return -2 (`TGAERR_READ`).

The TGA ABI measurement is decisive for this host failure:

```text
TGA_HEADER_BYTES=18 TGA_FOOTER_BYTES=34 HOST_LONG_BYTES=8
```

Original Targa::Open seeks 26 bytes before EOF and then reads the footer with
`sizeof(TGA2Footer)`. The retained source TGAs have standard 26-byte footers.
Thus the LP64 host reader requests more footer bytes than remain. No digit
pixels were compared, and this does not demonstrate the native ARM HUD cause.
Do not claim bitmap-font correctness from the existing pointer-only host gate.

Probe and evidence: `experiments/hud-font-atlas/` and
`build/hud-font-probe-huUwW4/`. Native HUD digits still require investigation;
no speculative image flip or glyph-layout rewrite was applied.

## Canonical host entrypoint gap

`tools/run_a30_host.sh` executes the non-sanitized interactive binary for M01
and City without building that target in its non-sanitized build list. The
isolated first link found a stale render-function signature in those objects.
ASan/UBSan targets are explicitly rebuilt separately; this finding does not
invalidate their rebuilds or the ARM artifact identity.

The pending generated `host-validation-entrypoints.patch` adds the missing
interactive build target and repairs the standalone dialog validator's missing
mandatory `--dialog-resource-h` argument. Both resulting script copies passed
syntax checks. Integrate after the running canonical process exits, preserving
its existing evidence. Future cross-scene runs must use rebuilt objects.
