# A3.5-dev1 correctness and flight-recorder gate

Status: **host-validated hardware candidate; not physically accepted.**

| Evidence gate | Status | Evidence |
| --- | --- | --- |
| Frozen A3.2-dev1 identities verified | PASS | VPK/ELF/map/symbol/dump SHA-256 values match the supplied identities. |
| A3.2 crash localized | PASS | Matching map/symbols put main-thread PC `0x810DACB6` in `HumanStateClass::Update_Animation`; deterministic staging fixes the omitted weapon-style table comma and guards invalid indices. |
| PSP2 core metadata extraction | PASS, bounded | `tools/parse_psp2_core.py` validates the gzip ELF envelope and extracts public thread metadata without inventing private register fields. |
| Button release semantics | PASS | Host contract: 10 checks, including press/held/release/tap and independent actions. |
| Axis convention and camera response | PASS | Host contract: 22 checks; physical up maps to forward/look-up and invert-Y remains a distinct setting. |
| WW3D shader state mapping | PASS, unit scope | Host contract: 4 checks for opaque, cutout, alpha, and additive state. Hardware muzzle material is not yet verified. |
| Renderer lifecycle idempotence | PASS | Host contract: 11 checks across two logical sessions and one native initialization. |
| Perspective-correct normal mesh path | ARM-built; hardware pending | The backend now submits original positions with model/view/projection matrices, retaining homogeneous W. |
| Full retained host integration | PASS | Canonical A2/A3 host gate: retained runtime plus ASan, LeakSanitizer, and targeted UBSan cycles passed. |
| ARM ELF/VPK/package integrity | PASS | 2026-08-16 canonical build produced ELF32 ARM, SELF/VPK validation, SHA manifest, and a no-retail diagnostic ZIP. |
| Physical Vita controls/visuals/lifecycle | PENDING | Authoritative A3.5 acceptance gate. |

The A3.2-dev1 hardware failures remain release-blocking until the A3.5-dev1
candidate demonstrates the corrected behavior on physical Vita. Host tests and
an ARM build are not a substitute for this gate.
