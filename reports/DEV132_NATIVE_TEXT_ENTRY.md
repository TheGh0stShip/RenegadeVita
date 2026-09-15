# Dev132 native save-description entry

The original Save dialog can create and reload default descriptions, but the
platform had no keyboard provider. Cross on its focused edit field previously
dispatched IDOK immediately. Dev132 connects the original EditCtrl to Vita's
system IME; original WWUI owns the text, change notification and Save command.
Cross or a completed touch inside an editable field opens the keyboard. A
failed keyboard initialization cannot fall through and save accidentally.

The provider retains bounded UTF16 buffers until OS termination succeeds,
commits only accepted valid text, cancels when its edit owner is destroyed, and
holds menu input until controller/touch release. Rendering uses the existing
vitaGL common-dialog presentation path; no new renderer or menu loop.

API reference: VitaSDK's native IME sample and installed SDK headers:
https://github.com/vitasdk/samples/blob/master/ime/src/main.c
https://docs.vitasdk.org/group__SceImeUser.html
https://github.com/TheOfficialFloW/VitaShell/blob/master/ime_dialog.c
The required IME module is loaded explicitly, and unloaded only if this boundary
loaded it. The standard language mask follows VitaShell's GPL-3.0-or-later
native provider; no conversion routines or source tree were imported.
The sample's separate renderer is not copied. Existing native GXM ownership and
physical 960x544 target are preserved. No emulator timing or API workaround.

Validation: build/dev132-text-entry-tests.log passes ASan/UBSan for both native
16-bit and host character widths. Tests cover ownership, rejection of malformed
or unterminated output, native termination failure, cancellation, repeated
entry and release suppression. Deterministic incremental staging passes 181
patches, inventory SHA256
1c672b6b0b1a8f66485a1585aa7f549e592f441c6b328f3afe844dc20c6c9793.
First original host compile found the missing ES_READONLY compatibility flag;
the central boundary now defines its original 0x0800 value. Retained normal and
UBSan integration rebuilds and two original M00 cycles each PASS. Logs:
build/dev132-host.log and build/dev132-ubsan.log. All 15 text-entry/frontend/
touch integration checks pass. All 151 focused checks, incremental ARM build,
ELF/SELF/VPK and candidate identity pass (build/dev132-fast-console.log).
This is incremental closure, not a canonical tools/build.sh pass. Native IME
imports and provider symbols are present in the matching ELF. Runtime follows.

Runtime return: build/dev132-keyboard-return/return-receipt.json (168 files).
Cross opens native IME; Cancel preserves text and creates no save. Accepted
text appears in the original edit field and creates no save until explicit
Save. Manual saveviva is written to new savegame03.sav, parsed as an original
M00 save, listed and loaded through full session teardown. Touch reopens IME
after loading; overwrite No preserves the exact file, Yes writes the changed
Manual savevivax description. Save-page Delete removes only that disposable
file; all 14 original saves remain byte-identical. Private backups and hash
receipts are under build/dev132-private-menu-save (save bytes not distributed).
Native END clean is recorded. Runner PROCESS_FAILED/null exit is retained
separately; it does not prove a zero process exit code. All 15 native input
steps released, as did window-message touch/keyboard steps.

The extended check FAILED repeated Load: after one successful load, touching
Load or activating it with Cross leaves EVA unchanged. Save still opens.
Source inspection found original RenegadeDialogMgr::Shutdown deletes all
FactoryArray entries, while Initialize does not recreate them. Native full
reload re-enters this lifetime; its Load auto-link has no factory. Dev133 must
restore initialization ownership and verify multiple load cycles. The earlier
Dev130 assumption that an ignored Load click was just a transition is not
sufficient. No full pause-menu pass is claimed. Load-page Delete was not reached;
dev132-r1-load-delete-select-no.json is a misnamed input receipt that moved the
Save edit caret and has no Delete result.

Dev131 remains frozen with controller No/Yes/Delete/Exit passing separately at
build/dev131-controller-return/return-receipt.json (84 files). Its host and ARM
artifacts are at build/dev131-closed-incremental/receipt.json (30 files).
Cycle Objectives and naturally populated Vehicle/Building pages remain open.
Physical testing is held. Full-demo, native 60 FPS and release acceptance remain
unproven; 0/10 release gates.
