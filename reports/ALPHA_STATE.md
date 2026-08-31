# First-mission alpha state

## 2026-08-31 — Dev89 local candidate; physical frontend gate still failed

- Workspace: active bash tree on `main`; upstream remains separate and pristine.
- Last completed implementation: Dev89 preserves Dev88's shared glyph-state and BINK-audio reserve fixes, then adds original frontend 800×600 scoping, font fallback/glyph gates, bootstrap display flushing, expanded UI/HUD/M00 pre-cache touches, Render2D texture-stage isolation, BINK late-frame dropping, and native-coordinate target-box scoping. It preserves original UI/movie/HUD/world owners and unchanged retail data.
- Latest canonical candidate: `dist/RenegadeVita-A3.5-dev89.vpk`, VPK SHA-256 `e2754588124910eeea526c056d004986f48f60491ab1a529f6a513248f0757a2`; matching ELF SHA-256 `acd2a60edb65b7cf415000ee1a114a8cbfd96c999ddbed99685900437ca165f9`; diagnostics ZIP SHA-256 `7bc5d18d1f1607cf10e0aee371f51ac4d73f1fe58f69cef60ab9ac86796b9038`. The 19 focused frontend/loading/runtime contracts and canonical 115-contract/549-action closure passed. Dev89 is local only.
- Latest physical checkpoint: Dev87 is a retained frontend usability failure. The matching partial runtime log ends at main-menu activation; the user reports missing menu text, slow/buzzy intro A/V, empty gameplay dialogue text, mangled HUD text, target-box drift, black pre-cache delay, HMVV freeze, and Start crash. It cannot establish Dev89 correctness.
- Media/capture: the later user-finalized Dev87 recorder MP4 was pulled read-only and yielded six labelled M00 stills. Current VitaCompanion `screen.v1` controls panel power only. The exact-title VDB screenshot provider is being prepared independently; no engine-frame timing retune is planned as a visual-evidence substitute.
- Current blocker: physical verification of readable original frontend/dialogue text, paced intro A/V, readable HUD/loading feedback, stable M00 progression, and safe Start/pause/exit.
- Exact next automatic action: finish the public repository/documentation closure and wait for the VDB provider handoff. Do not deploy Dev89, install the VDB provider, launch the title, or modify the Vita without explicit direction.
