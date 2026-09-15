# Original EVA pause integration after dev111

Source changes retain the original WWUI input provider, dialog factories,
backdrop and StyleMgr after frontend-to-M00 handoff. Start now reaches original
menu-toggle input and requests an outer-loop pause rather than immediate exit.

The native presentation boundary suspends original Combat, opens original EVA,
services original menu/dialog/network/audio owners, and resumes through original
`GameInitMgrClass::Continue_Game`. It does not invoke the desktop Combat keyboard
handler or require window focus. Entry seeds held key states; leaving consumes
the menu button's gameplay edge. Frontend logical resolution is scoped to pause.

Unavailable Help, save and load controls remain visible but disabled. Existing
original quicksave and the opt-in original checkpoint startup path remain
separate development tools. The original confirmed exit action is labelled
Exit Demo and requests outer-loop teardown, rather than unloading Combat in an
EVA callback. Dialogs are flushed before world destruction, with full WWUI and
StyleMgr shutdown after Combat and TextDisplay release their font references.

The registered EVA dependency patch is generated from source differences,
not hand-counted hunks. Its previous viewer-index and map safeguards remain.

Status: implementation only. No ARM, emulator or physical pause acceptance is
claimed. Required next evidence: source/patch closure, repeated Start/back/resume
without movement or focus dependence, objectives/map tabs, options return,
cancelled exit, confirmed orderly exit, and checkpoint reload on a matching build.

Full M00 completion, HUD digits, elevator artifact resolution and 60 FPS remain
unproven. This is not a release-ready demo declaration.
