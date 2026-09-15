# Pending cursor-edge clamp

User reports a thin vertical line far to the right of the original menu cursor,
moving with it in the Dev102 emulator session. This is a new reported cosmetic
defect, not an accepted screenshot-based diagnosis.

Original `ScreenCursorClass::Render` submits the complete texture-sized quad
with UVs (0,0)-(1,1). `Set_Texture` initializes the texture but does not clamp
addressing. Edge wrapping under native filtering is the narrow causal hypothesis:
cursor pixels near the left edge can reappear at the opposite edge. Original
WWUI map rendering already uses the same public U/V clamp methods.

`DEV103_CURSOR_CLAMP.patch` prepares Vita-only U/V clamp calls in the original
cursor texture owner. It preserves cursor geometry, hotspot, UVs, authored retail
pixels, desktop behavior, and shared text/world rendering. It does not hide the
cursor or apply a global sampler change.

Resume update: the Dev102 canonical log reports BUILD SUCCESS and no compiler
process remains. The clamp is now integrated as
`port/patches/wwui-a35-vita-cursor-clamp.patch`, registered in deterministic
staging with expected patch count 146 for Dev103. Build and visual confirmation
are pending. The proposal below records why integration was initially held.

Historical status: prepared but NOT integrated, staged, compiled, or visually validated.
The Dev102 canonical build is still compiling its frozen staged snapshot. Do
not modify its active patch identity or generated source while it runs. This
proposal is retained outside active port patches to avoid changing that build's
145-patch identity. Next source unit should install it as a dedicated WWUI patch,
register deterministic staging, update the expected patch count, and include it
in the next coherent candidate rather than rebuilding solely for this blemish.

No tests or hardware actions were performed for this report. M00 progression
remains higher priority than this minor cosmetic defect. A later matching cursor
capture is required before describing the visible line as fixed.
