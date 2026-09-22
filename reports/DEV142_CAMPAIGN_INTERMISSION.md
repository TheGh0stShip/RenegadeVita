# Dev142 campaign intermission candidate

The full-port mission-success boundary now dispatches the observed original
Combat completion to `CampaignManager::Continue`. The original score dialog,
movie game mode, and campaign callbacks run in a frontend presentation loop.
When original `GameInitMgrClass::Start_Game` selects the next campaign map, the
Vita boundary captures `CampaignManager::Save` into an in-memory `RAMFileClass`
chunk and rebuilds the next session through its existing original loader.
`CampaignManager::Load` restores the chunk after the new catalog initializes.
The original `GameInitMgrClass::End_Game` owns completion teardown; the direct
runtime skips its duplicate level, radar, and session cleanup in that case.
The M00 demo branch remains unchanged. Original `ramfile.cpp` is now linked
only in the full-port profile.

Evidence: 19 focused host contracts/parser checks passed; full-port ARM
ELF/SELF/VPK built with development checkpoint OFF; package inventory is only
`eboot.bin` and `sce_sys/param.sfo`; repo hygiene and public-doc checks passed.
VPK SHA-256: `52927e6cf8f521ad025b2921343ddc2f0c678e88f2817a55eb8228694b24520e`.
SELF SHA-256: `c1a483eb9c81bd02256f213486986ea53e96cedaf077fc3381eaa0983bfcba92`.

This is compiled integration, not a runtime transition pass. Normal M13
objective success, Score dismissal, movie callback, state reload, M01 entry,
and repeated transition resource behavior are unverified. Next: use an
isolated diagnostic completion event to exercise this exact path in Vita3K,
fix observed failures, then verify ordinary M13 objective completion.
