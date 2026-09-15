# Dev105: original first-frame fallback and saved-player reuse

Dev104 fast SELF 2f2b35c61c6b333888adbb8db72980e26d6b80379c4128db95ee82503f2f64e1
reached original M00 loading capture (PASS), player creation and 60 prewarm
frames. Its next failure was native controlled teardown, not the Dev102 host
access violation. The initial gameplay frame submitted 192 meshes and 8387
triangles with completed render closure, but a render-target allocation probe
incremented rejected/unsupported draw counters and tripped the first-frame gate.

Original Create_Projector_Render_Target tries UNKNOWN even when explicit
render-target formats are unsupported. Static/dynamic projector owners handle
NULL. Dev105 preserves that capability/fallback and logs it separately from
actual draw rejection. It does not implement offscreen shadows, claim visual
parity, weaken the first-frame gate, or accept non-default render-target binds.

Original cNetwork and cPlayerManager save/load restore player identity;
SmartGameObj and Combat restore/remap player body and camera. cGod::Think has
an original saved-player relink branch. Dev105 avoids Create_Player's rejoin
deletion for saves, requires one restored local player and matching star owner,
checks the resulting link, and preserves loaded first-person state. Fresh M00
creation is unchanged. M00 scripts serialize progression variables, and the
original mission quicksave path exists; runtime round-trip proof remains open.

Retail claims must distinguish loose-file misses, archived availability and
successful runtime consumption. hd_reticle.dds is present in emulator
Data/always.dat at offset 60926184, size 5616, DDS 64x64, entry SHA-256
053335f8917ba9b3fa4a6ac346b99e61aea77bd66676605c6694fb456dde60d8.
Only metadata was retained; no retail extraction or modification occurred.
Dev105 permits one reticle success breadcrumb beyond the ordinary 24-texture
log limit so its runtime decode/upload can be established specifically.

The workspace retail-pc symlink targets a missing old C: Steam install. Steam's
current installation is E:/SteamLibrary/steamapps/common/Command & Conquer
Renegade. Full source/emulator Data hashing uses that root, not the stale link;
the first manifest attempt failed before hashing. Comparison is pending.

Next: fast ARM/package closure, matching M00 runtime past first frame, then
original quicksave/restore on a proven segment. No physical Vita/PSTV testing,
full M00 completion, checkpoint compatibility or 60 FPS+ acceptance is claimed.
