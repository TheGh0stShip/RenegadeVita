# Dev150: M13 slot-19 Set_Model stall

Status: full-port-only diagnostic, not a performance fix. Demo and unchanged
retail data remain separate. No physical Vita evidence.

The isolated Vita3K/OpenGL M13 direct-entry route reproduced the ambush
freeze in the original `Invisible_Object` 1500000007's script timer. Its
`Test_Cinematic` command `Create_Object, 19` calls original
`Commands->Set_Model`. Retail M13 control text identifies slot 19 as
`X00_AG_Explode`; the unchanged archive contains its W3D. In the matching
run, object creation took 377 us and Set_Model took 6,166,481 us. The
enclosing timer took 6,168,914 us. This is process-clock CPU-side time,
not a GPU measurement. The original path is
`Set_Model -> PhysClass::Set_Model_By_Name -> WW3DAssetManager::Create_Render_Obj`
followed by original physical-model ownership.

Evidence: managed AppData `campaign-dev150-slot19-m13-1/` receipt and
runtime log. SELF SHA-256
`1ba9212ececdb4406e4e6dccb59da0740c12444e1392b6deb6296dbf0136493a`;
asset-free VPK SHA-256
`9a848325db20e90003be95a97ed9acc29104900ad8bd5c52a9d6000b3b971f79`.
ARM SELF/VPK and 190 ordered staging patches pass. The run ended at its
120-second watchdog and is unassessed for visual/A/V correctness.

Next: time a loading-time creation/release of this exact WW3D render object
and repeat M13. If the live Set_Model still stalls, distinguish asset-manager
prototype creation from `PhysClass::Set_Model` scene notification rather than
keeping a speculative prewarm. Regress M00 and compare fixed-route frame
percentiles, clock drift, and authored actor/rocket sequence. Native Vita
performance acceptance remains pending.

VitaSDK's ELF converter rejected an oversized intermediate diagnostic once
it crossed segment 0 (`Cannot allocate 3936 bytes for SCE data`). Retiring
previously answered scene/render/Combat probes restored a packageable build.
