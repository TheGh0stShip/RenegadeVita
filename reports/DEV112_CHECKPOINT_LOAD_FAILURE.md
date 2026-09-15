# Dev112 checkpoint load: confirmed enum-width defect

Dev112 built and installed successfully. Its original save-load route accepted
`save/dev112-post-sydney.sav`, then faulted before gameplay. Pause/resume and
remaining lessons were not reached. The owned emulator was explicitly stopped
after retaining the guest fault; the runner's PROCESS_FAILED result is not an
independent natural process crash or clean game exit.

Evidence: `D:/Vita3K/RenegadeEvidence/Dev112-20260909T044627Z/` and
`build/dev112-host-evidence/checkpoint-load-failure-runtime.log`.
Matching SELF: `ce7862e4f9e5c668b075426dbb1f3a767dc119c3f17cb405c83de7c1980a0bd2`.

First guest fault: PC `0x81120ab2`, LR `0x811218e5`, category register
`0x09031901`. Matching ELF maps this to ConversationMgrClass::Reset_Conversations
via ConversationMgrClass::Load. This precedes the later null-PC cascade.

The compiler uses small enums. Disassembly confirms Save passes length 1 when
writing SaveCategoryID, whereas Load reads sizeof(int), four bytes. In the saved
category chunk at offset 53570, payload starts `01 19 03 09 08`: category 1
followed immediately by original conversation chunk ID 0x08090319. Reading four
bytes produces the observed invalid category exactly. This is a port save-format
defect, not grounds to blame the emulator.

Implemented through the existing registered conversation patch:

- Write an explicit uint32 category, preserving the original retail field width.
- Validate category range before accessing ConversationList.
- Read standard four-byte categories with zero high bytes.
- Accept older native one-byte categories only for an empty category or a
  following original conversation chunk whose size fits the category payload.
- Keep archived saves unchanged and original conversation loading ownership.

Zero-fuzz full staging passed with 161 patches. Updated patch identity:
`d9102d66e1e2ddc94b4051a1709630da9aae980119086d11747f8116ea2a2dc8`.
Corrected conversationmgr.cpp compiled for ARM successfully, retained under
`build/dev112-save-category-fix/compile-after-stage.log`. Earlier probe attempts
failed to find compile_commands.json and then raced staging header replacement;
neither is counted as successful compilation. No dev112 artifact was replaced.

Next candidate: dev113 with the same development checkpoint path enabled.
Required return remains actual original checkpoint restoration, then EVA pause
and the remaining M00 lessons and ending. This source fix is not reload proof.
