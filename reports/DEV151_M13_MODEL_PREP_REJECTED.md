# Dev151: M13 model pre-create rejected

This full-port-only candidate created and released the original
`X00_AG_Explode` WW3D render object after M13 load and before simulation.
No game object, script, mission flag, or retail data was changed.

The isolated Vita3K/OpenGL run measured preparation at 5,884,570 us and
the later original slot-19 `Set_Model` at 6,005,398 us. Object allocation
was 373 us. The warmup did not remove the live ambush stall and added about
5.9 s to loading. It is **rejected** and will be removed in the next source
candidate. No audio-sync, visual, or physical Vita acceptance is claimed.

Evidence: managed AppData `campaign-dev151-modelprep-m13-1/` receipt/log;
SELF SHA-256
`c7c65ef3001f21ace248b68d3963dc7b0e6b61df262f69eabbb1c8721cae025d`;
asset-free VPK SHA-256
`068d5645c2b4b0dd52ffeef082798e002f711bd73800bc5cc7960d9391390b01`.
ARM SELF/VPK compilation and packaging pass; run timed out unassessed.

Next: time original `PhysClass::Set_Model_By_Name` around
`WW3DAssetManager::Create_Render_Obj` and `PhysClass::Set_Model` to
distinguish expensive per-instance creation from scene notification.
