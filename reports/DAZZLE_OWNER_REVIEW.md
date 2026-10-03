# Original dazzle owner review

Source review on 2026-10-03 covers original dazzle presentation required by
cinematic child objects, including 15 inspected M01 helicopter light records.
Located declarations do not establish runtime effects.

The native source restoration retains the original visibility, blink,
intensity/history and layer submission body on Vita. Original Combat owns
layer creation, visibility raycasts and the flush between scene and HUD.
WW3D initialization now restores original DAZZLE.INI type/lensflare loading;
interactive initialization requests full mode. Shutdown restores original
type cleanup before asset release. Headless host rendering remains skipped.
The correction is uncompiled; active staging was not regenerated.

The original draw generates dynamic XYZNDUV2 vertices and 16-bit quad indices,
selects separate base offsets for halo, dazzle and lensflare, and uses identity
world/view/projection matrices before restoring the prior matrices. The native
indexed boundary accepts the 44-byte layout, preserves buffer offsets and
checks referenced vertices against backing capacity. Its projection conversion
maps Direct3D 0..W depth to GL -W..W even for identity projection.

Original default shaders disable culling, depth writes and fog. Both use
additive ONE/ONE blending and texture/vertex modulation; dazzle depth comparison
is ALWAYS, halo comparison is LEQUAL. Native shader translation selects the
corresponding GL blend/depth functions and write/cull state. Fog is applied
before the shader cache shortcut. Indexed submission binds textures first,
then reapplies original shader and texture-stage state before geometry.
No source mismatch was established in these inspected paths.

Both inspected retail core archives contain DAZZLE.INI with vehicle and blinking
light types, but the members differ. Archive precedence, actual loaded types,
texture residency, visibility delivery, blend/depth execution and physical
pixels remain unverified. Source/member hashes are retained privately.

Further read-only inspection: each core definition version has 27 nonempty
dazzle/halo/lensflare texture references. All have filename candidates in the
two inspected core archives, including DDS/TGA extension candidates; these
are discovery matches rather than demonstrated loader choices. Private metadata
retains repeated type references and hashes without exporting texture bytes.
The interactive factory list is root, Data, Always2.dat, Always.dbs, Always.dat,
then tutorial. Original lookup tries its temporary factory, search-start entry,
then remaining entries in insertion order. Constructor defaults are no temporary
factory and search index zero; selected mission archives are appended after
WW3D initialization. Thus core lookup prefers Always2 over Always when no loose
override is available. Actual physical files and successful loading remain open.

Validation: 11 combined source-only tests for restoration replay, HLOD
declarations and prelit discovery pass. Restoration replay uses fixed input
hashes and zero fuzz and compares the native rendering body against upstream.
These tests do not execute the renderer or establish ARM/hardware correctness.
No build, launch, active staging or retail mutation was performed.
