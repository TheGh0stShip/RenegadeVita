# M00 loading and menu readiness source batch

Status: implemented source changes only; unbuilt, unstaged and untested.
No emulator launch or physical access. Dev110 installed binary predates this work.

## User return

Loading gives way to a black/partial-HUD interval, broken pickup imagery and
visible world assembly for less than ten seconds. In-game pause reportedly
crashes. Demo-only unavailable options must retain text and remain visible but
not accept focus, hover highlighting or activation.

## Implemented

- Original render-frame boundary now accepts a presentation flag. Normal callers
  retain swapping; the 60 scene warmup frames call End_Render(false), then the
  original loading owner clears/renders/presents the display. No gameplay input,
  physics, scripts or objective advancement is added during warmup.
- Loading animation uses native monotonic elapsed presentation time instead of
  paused simulation time. Original milestones occupy 0-90%; referenced-texture
  preparation occupies 90-95%; hidden scene frames occupy 95-99.9%. Completion
  reaches 100% only after the warmup render envelope succeeds.
- Original asset-manager texture references are snapshotted after level load.
  Uninitialized textures retained by another original owner receive Init before
  gameplay, with loading repaint every eight attempted textures. Temporary refs
  are released. No retail archive scan or second asset cache is introduced.
- Preparation is bounded to 2048 pending references and a soft 32 MiB additional
  native texture-residency budget, checked between indivisible decodes. A single
  texture can exceed that budget; it is not a total process-memory guarantee.
  Deferred counts are logged, and deferred assets retain normal lazy loading.
- Demo main-menu Internet, LAN, practice and options entries remain rendered
  with original labels but disabled. Direct command dispatch is gated too.
  Demo menu-entry navigation skips disabled/hidden controls, and focus, click,
  hover, pressed-state and cursor paths reject disabled items.

## Confirmed pause gaps, not repaired by this batch

The native startup menu explicitly shuts down RenegadeDialogMgr before gameplay.
Gameplay Start is still an explicit exit workaround; the native simulation
menu-toggle only suspends/resumes Combat without presenting a dialog.
The selected single-player dialog factory leaves EVA absent, and
LOC_ENCYCLOPEDIA is compiled out. Original Combat_Keyboard routes ESC there.
Restoring only the key binding would not restore the original pause UI.
The reported crash itself needs matching crash evidence; these source defects
do not prove its fault address or whether it is emulator-specific.

Next pause unit: restore the original in-game dialog owner and its needed
factory/resource dependencies with correct StyleMgr/input/Combat lifetime,
then remove the exit workaround. Do not substitute the main menu, whose
activation calls GameInitMgr::Shutdown.

## Remaining preparation and visual gaps

This is not full-M00 cache coverage or guaranteed shader precompilation.
Original DEP loading creates model dependencies, not every future script-spawned
resource, voice, effect or GPU program variant. The 60 frames still exercise only
the current original camera, not the entire tutorial. Do not move the player or
advance scripts to manufacture cache coverage. Scene/HUD visual readiness,
pickup imagery, progress animation and memory high-water need later validation.
Long indivisible loads can still stall repaint; no unsafe concurrent GL worker
was added. Secondary single-player menu restrictions remain to be completed.

Keep builds/tests and physical access held. Full demo acceptance remains 0/10.
