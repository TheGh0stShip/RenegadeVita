# Dev109 HUD path triage during user-owned M00 run

## Evidence and ownership

User confirmed they are controlling Dev109-native-20260909T011450Z. Do not
inject input, restart, or replace that running title while they progress.
The first native automation session was explicitly stopped by reported Start,
not by missing retail files or an initialization failure. Canonical Dev109
compiles separately; no renderer source was modified during this investigation.

window-051.png shows M00 basic movement, readable tutorial/Logan labels,
remaining edge/glyph artifacts, distorted-looking numeric HUD text and a solid
Data Disc icon area. This is one captured frame, not an acceptance sequence.

## Original owners narrowed

- Health/shield and ammo counts use Render2DTextClass with Font3DInstanceClass.
  Their font atlas is distinct from FreeType sentence text. Follow original
  font3d.cpp surface loading, proportionalization and atlas coordinates first.
- Tutorial help and target labels use Render2DSentenceClass. Existing staging
  patches already normalize U and V against separate texture dimensions and
  allocate the sentence texture using both width and height. Repeating that
  correction is not an evidence-backed next fix.
- HUDClass::Add_Data_Link supplies hud_cd_rom.tga through original Powerup_Add.
  Distinguish actual icon texture contents, original DDS alias resolution and
  alpha/blend state before assigning the solid region to a missing asset.

No root cause or remediation is claimed yet. Next source investigation should
inspect the numeric-font atlas geometry independently of sentence glyphs, then
compare the original Data Disc icon with its candidate draw. Preserve original
engine ownership and unchanged retail data. Do not shift NPC boxes globally
based on this single view, and do not count this trace as visual acceptance.

## User-confirmed grey Data Disc square: owner distinction

User specifically reports the left-hand Data Disc region as a grey square.
Original M00 mission objective POGs are POG_M00_1_01.tga through
POG_M00_1_06.tga, selected by Set_Objective_HUD_Info[_Position]. These are
separate from the HUDClass::Add_Data_Link pickup display, which selects
hud_cd_rom.tga and IDS_Power_up_DataDisc_01. Therefore the displayed caption
is important: do not substitute a mission POG or globally change objective UVs
merely because both widgets occupy the left HUD. The earlier statement naming
hud_cd_rom.tga identifies the Data Link source path, not a verified runtime
texture-to-draw association.

Initial matching gameplay telemetry reports zero source/invalid/unsupported/
decode/upload-failure/checker counters. This does not prove correct icon texels,
UVs or alpha state, but does not support calling this a missing-file fallback.
The boundary TGA surface path opens/decodes actual original Targa data and
copies rows, rather than explicitly supplying a constant grey icon. Next useful
evidence is the specific icon's source pixels/dimensions and submitted UV/blend
state. No retail bytes or compiling source were changed.

## Narrow ordering defect identified; Dev110 correction prepared

Powerup_Add calls Render2DClass::Set_Texture, immediately reads Get_Width and
caches UV normalization only if that width is positive. Render2D Set_Texture
currently only assigns the reference. Vita TextureClass skips original thumbnail
metadata initialization and fills Width/Height in its later lazy Init. Thus a
first-use zero-width texture leaves the 0..64 pixel rectangle unnormalized;
later texture loading cannot repair the already-cached UVs. This is a concrete
ordering hazard consistent with the solid icon, not proof of its exact draw.

Prepared build/dev110-host-evidence/ww3d2-render2d-texture-readiness.patch calls
the existing idempotent TextureClass::Init at native Render2D assignment, before
dimension-dependent callers proceed. It preserves original ownership, performs
no retail rewrite and does not globally preload world textures. It is NOT yet
registered, applied, compiled or runtime-proven: Dev109 canonical is still using
its unchanged source snapshot. Integrate after that build ends, then reproduce
the Data Disc pickup and inspect the image. Keep numeric-font work separate.
