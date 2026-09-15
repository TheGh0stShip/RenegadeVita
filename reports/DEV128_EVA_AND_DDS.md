# Dev128: EVA correction and native texture residency

Latest user return: pause Map is black, statistics text is missing, and other
pause items remain incomplete. Continue automated Vita3K checks. Physical
testing remains held while optimization continues toward 60 FPS.

The user directs independent checks of every pause tab and button. Do not
delegate discovery of additional failures to the user; Help, Save, Load and
Options are included in the continuing implementation and runtime audit.

User reiterates: do not tune the port for Vita3K. Native Vita ARM/GXM, memory,
texture and CPU limits remain the implementation target. Vita3K is restricted
to initial functional regression checks; emulator frame timings cannot select
native performance changes or establish physical acceptance. No game Vulkan
backend, emulator-specific graphics shortcut or resolution/MSAA reduction.

## Demonstrated causes and corrections

- Retained Dev127 host debugger reached the first original M00 render with
  `MapTextureName=always\\overlay\\map\\map_lvl-tut.tga`, scale 2.43, but
  `MapSize=(0,0)`. Original `Clear_Cloud_Cells` returns immediately for this
  size. Native textures load lazily. Both MapMgr and MapCtrl now call the
  original texture's idempotent Init before reading dimensions; marker atlas
  dimensions receive the same correction. No retail or exploration change.
  Baseline: `build/dev128-eva-owner-gdb.log`.
- The RC translator omitted implicit WS_VISIBLE/WS_CHILD and control-specific
  styles. Original DialogText::Render requires WS_VISIBLE, explaining absent
  static labels and numeric statistics. Restore RC defaults, including center
  and right alignment, disabled controls, and explicit NOT style removal.
  Independent LLVM RC comparison passes all 116 controls in all 13 selected
  frontend resources. Original builtin class ordinals are normalized for that
  comparison; styles, IDs, rectangles, titles and extra data are compared.
  Evidence: `build/dev128-resource-styles.log`, `build/dev128-dialog-validation.log`.
- Restoring visibility exposed an original unavailable-renderer row-iteration
  bug in the retained host: Find_Row_Start for a subsequent row returned the
  current row, making StyleMgr loop indefinitely. The debugger captures the
  exact loop in `build/dev128-host-text-stall-child-gdb.log`; the initial host
  run hit its 120-second bound. Returning no subsequent row in that unavailable
  state passes production row tests under ASan/UBSan and preserves ready-state
  wrapping. Evidence: `build/dev128-text-row-regression-final.log`.
- Help/Save/Load/Options are deliberately disabled by previous demo source
  selection. Do not call them functional. The four encyclopedia tabs still
  require visual checks of original revealed entries, models and descriptions.
- Stronger host debugging found a separate DDS disk-layout defect: the original
  serialized surface descriptor contains a pointer, which expands on LP64.
  The actual 512x512 DDS header is found, but the host rejects its shifted fields
  and substitutes the 2x2 diagnostic texture. The current host map readiness
  assertion only checks positive dimensions and does not prove real map pixels.
  Vita's 32-bit layout is already the expected disk width. Correct the host
  representation to that fixed disk width and strengthen the independent
  fixture after Dev128 artifact closure. Evidence:
  `build/dev128-map-dds-constructor-gdb.log` and
  `build/dev128-map-retail-metadata.json`. Native visual validation remains open.

## DDS optimization under validation

The original DDS/CPU surfaces remain owners. Eligible retained DXT1/DXT5 mip
chains upload original blocks into one native UBC allocation, with validated
Morton layout. Writable surface updates transactionally replace the complete
GPU chain with retained BGRA surfaces converted into native RGBA storage.
Failed allocation/upload preserves the old GPU object and all CPU surfaces.
Mode bit 4 selects this path alongside direct atlas upload; mode 0 is baseline.
ASan/UBSan passes 800 compressed cases (9,762,188 blocks), 12 retained surface
chains, and eight actual production owner transactions including texture-name
exhaustion. `build/dev128-dds-chain-sanitizers.log`.
No native frame-time improvement or compressed visual acceptance yet.
The pinned native vitaGL dependency build passed:
`build/dev128-vitagl-build.log`. Original map payload metadata confirms 512x512
and valid DDS without writing retail pixels: `build/dev128-map-retail-metadata.json`.

## Current plan

1. Finish retained M00 host checks, including map readiness before first frame
   and exact original statistics player identity. ARM dependency build follows
   independent DDS layout/ownership checks.
2. Build checkpoint-enabled Dev128; retain ELF/SELF/VPK, symbols, dependency and
   source identity. Dev127 is frozen in `build/dev127-closed-canonical/` with
   42 hash-verified artifacts/dependency records before shared outputs change.
3. Install only the emulator title with backup/readback; load the unchanged
   archived refinery checkpoint and inspect each original EVA page. Resume
   gameplay, retain captures/logs and release all synthetic inputs.
4. Continue measured renderer routes and whole-demo checks. Emulator FPS does
   not establish physical performance. Release acceptance remains 0/10.
