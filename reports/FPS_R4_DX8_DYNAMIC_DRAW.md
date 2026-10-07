# FPS round 4: DX8_DYNAMIC_DRAW: packed immediate records for DX8-boundary indexed draws

Status: implemented, host-tested, ARM-compiled. **Not measured on hardware.**
Continues recovered branch `fps-r3/dx8-dynamic-draw` (976b7ca, cherry-picked as 6d1bdf6).

## Hypothesis
Every draw that bypasses MeshClass goes through one path:
`DX8Wrapper::Draw_Triangles/Draw_Strip/Draw_Sorting_IB_VB`
(port/renderer/vita/ww3d_dx8_boundary.cpp:3089-3213) -> `Submit_Bound_Triangles` (:1779)
-> `RenegadeVitaRenderer::Submit_Indexed_Triangles` (ww3d_vita_renderer.cpp:4380).
That covers dynamic VB/IB, sorted alpha runs, PointGroup particles, Render2D/HUD/text quads,
decals and streaks. With the default `RVRC1 F`, every unique vertex in a batch costs five vitaGL
calls (ww3d_vita_renderer.cpp:4557):
glColor4ub (4 int-to-float conversions and 4 VDIV.F32), glNormal3f, 2x glMultiTexCoord2f, and
glVertex3f. glVertex3f makes 2-3 `sceClibMemcpy` calls for each vertex in the multitexture layout.
The non-projective, unlit vertex stream is just position, uv, uv2 and RGBA. A port-side decode
into packed records plus one append for each run of up to 128 vertices should produce the same
pool bytes at a fraction of the per-vertex call cost.

The only pretransformed layout, XYZRHW, does not reach this path: the boundary accepts only
FVF 0x152/0x252 (XYZ|N|DIFFUSE|TEX1/2), and everything else is rejected before any emission.
There is no non-indexed DrawPrimitive path in the boundary.

## Change
1. New vitaGL dependency patch `port/renderer/vita/dependency-patches/vitagl-immediate-vertex-records.patch`
   adds `GLboolean vglRenegadeImmediateVertices(const GLfloat *records, GLsizei count)` to ffp.c.
   Each record is 11 floats: `x y z s0 t0 s1 t1 r g b a`, which is vitaGL's unlit multitexture
   layout. The function writes exactly the fields `glVertex3f` writes for the enabled texture units
   (MT 11, tex0 9, untextured 7 floats), advances `legacy_pool_ptr`/`vertex_count` the same way,
   and does not touch `current_vtx`. If `lighting_state`, `renegade_projective_immediate` or
   `count < 0` applies, it writes nothing and returns GL_FALSE. With count 0 it acts as a probe.
   Like `glVertex3f`, it does not check pool capacity.
   It is wired exactly like the six existing patches in `tools/build_vitagl_demo.sh`: a variable,
   a `patch --fuzz=0` step applied last, the build identity hash, a provenance line, and the
   sha256 list. A dry run against the pinned tarball 6e7fe40 with all 6 prior patches applies at
   fuzz 0. The patched ffp.c ARM-compiles with the pinned flags and exports the symbol.
2. `port/renderer/vita/ww3d_vita_indexed_vertex_records.h`: the record type, a 128-record chunk,
   and a constexpr `(float)c/255.0f` table that `Decode_Indexed_Record_Color` uses for the D3DCOLOR
   ARGB-to-RGBA conversion. The header also defines the compile switch
   `RENEGADE_VITA_INDEXED_VERTEX_RECORDS` (default 1).
3. ww3d_vita_renderer.cpp: `Emit_Indexed_Texture_Coordinate` is split into
   `Compute_Indexed_Texture_Coordinate` (:944) plus the GL wrapper (no behaviour change); new
   `Record_Indexed_Texture_Coordinate` (:1019) returns the (s,t) the wrapper passes to GL (PASSTHRU
   with D3DTTFF_DISABLE copies the selected UV, exactly what the count-0 transform computes).
   `Submit_Indexed_Triangles` probes vitaGL after `Begin_Texture_Coordinate_Primitive` (:4649),
   decodes unique batched vertices once into records (:4605) and appends each 128-record run
   (:4629); a refused run and the rest of the draw replay through the original calls in order.
   `end_indexed_batch` (:4657) flushes, then (as before) replays the last corner's attribute calls,
   so vitaGL's current colour/normal/uv/uv2/q equal the per-vertex path. Batching, indices, draw
   order, validation, checksums and statistics are unchanged.

Default-on whenever `RVRC1` bit 8 (indexed work, default F) is set. `RVRC1 7`/`RVRC1 0` keep the
exact previous per-vertex path at runtime; `-DRENEGADE_VITA_INDEXED_VERTEX_RECORDS=0` disables it
at compile time.

## Risk and invalidation argument
No state is cached across draws. The records are scratch, rebuilt for each run from the locked
buffer bytes in the same draw, so there is nothing to invalidate.

Equivalence of the GPU stream:
- Position, uv and uv2 are bit copies of the values the per-vertex calls store.
- Colour is either `primary` itself (glColor4f stores the floats unchanged) or the table value.
  The table holds the same correctly rounded IEEE quotient `glColor4ub` computes; all 256 values
  are checked bitwise on host.
- The decision between records and calls is made from the same vitaGL state glVertex3f uses to
  choose its layout.
- Lighting is never enabled by the port (no GL_LIGHTING anywhere). Projective primitives refuse
  records.

Residual risks: a future vitaGL immediate-layout change must update the patch (fuzz 0 fails
if ffp.c context moves); vitaGL must be rebuilt, which `tools/build.sh` does automatically
because the identity hash changes.

## Tests (host, all PASS)
- `RENEGADE_VITAGL_SOURCE_TARBALL=<main>/build/deps/vitagl-demo/source.tar.gz python3 -m unittest tools.test_vita_indexed_vertex_records`
  ran 3 tests, all OK:
  - The build-script wiring check (patch applied last, included in identity and sha256 lists).
  - The production `Submit_Indexed_Triangles` emission slice through a GL sink, for stride 36/44,
    base 0/7, unaligned data and multi-batch draws, at -O2 and with ASan/UBSan, in four modes:
    per-vertex, batched per-vertex, batched records, and records refused on the third append.
    The unlit stream, batches, texture state and full post-draw current attributes are identical
    in every mode. Records mode makes zero glVertex3f calls.
  - Patched pinned vitaGL per-vertex calls versus `vglRenegadeImmediateVertices` (ASan/UBSan):
    pools match bytewise for untextured, tex0 and MT layouts (700 vertices, uneven/empty runs,
    lit and ARGB colours, -0/denormal/huge values), as do `vertex_count`, pool advance and final
    `current_vtx`; lit, projective and negative-count calls are refused without writing.
  - Production `Record_Indexed_Texture_Coordinate` matches `Emit_Indexed_Texture_Coordinate`
    bitwise in (s,t) across 5 modes, 8 flag combinations, 2 UV sources, 2 stages and 16 samples
    each (2560 cases), with identical breadcrumb side effects.
- `tools.test_vitagl_compact_vertices` and `tools.test_vita_projective_coordinates` pass, run with
  the tarball linked read-only for the run. `tools.test_vita_indexed_state_contract` and
  `tools.test_vita_static_mesh_cache` also pass.
- Pre-existing failures, unchanged and listed in HOST_TEST_TRIAGE_2026-10-06:
  - `test_vita_mesh_batch`: mesh anchor drift. Its generic-indexed half now also runs standalone
    through `-DGENERIC_INDEXED_ONLY`.
  - `test_vita_index_preparation`: RENEGADE_FRAME_PROFILE.
  - `test_vita_sampler_cache`: GLint.
- ARM: `arm_tu_check.sh ... port/renderer/vita/ww3d_vita_renderer.cpp` gave `ARM TU OK` with no
  new warnings. The patched vitaGL `ffp.c` ARM-compiled with the pinned flags.

## Expected gain (estimate, unmeasured)
Roughly 150-250 cycles per unique vertex fewer: four VDIVs, about 20 call/branch sequences, and
2-3 sceClibMemcpy calls replaced by a table lookup and one memcpy per 128 vertices in the MT layout.
That is about 0.35-0.55 us per vertex at 444 MHz.

This only matters in proportion to how many DX8-boundary vertices a frame has: HUD and text
glyph quads, particles, alpha-sorted runs and decals. Guess: 0.5-3 ms per frame in M13 combat
with heavy particles or HUD, and about 0 in static scenes. MeshClass submission (the dev238
24-29 ms) is not touched.

## Hardware measurement to take
On the same build, same M13 ambush save and camera, compare
`ux0:data/renegade/user/config/render-work-cache-v1.flag` set to `RVRC1 F` (records) against
`RVRC1 7` (per-vertex, no batching). Ideally also compare against a `-DRENEGADE_VITA_INDEXED_VERTEX_RECORDS=0`
build at `RVRC1 F` to isolate records from batching.

Record the frame-profile scopes "Vita Render Indexed Triangles" and "Vita Render Sorted Draw"
(median/p95/p99), the render stage ms, and `g_mesh_unique_vertices` per frame.

Check visually that HUD text, the radar, particles, smoke and decals are unchanged.

## Not done / follow-ups
- `Draw_Sorting_IB_VB` (ww3d_dx8_boundary.cpp:3089) still copies each sorted run into a dynamic
  VB/IB before submission. It could point the submission at the sorting buffers directly, but the
  saving is small compared with the emission cost.
- The same records mechanism could serve the MeshClass/skin per-corner emission. That belongs to
  the mesh-path owners.
- Client arrays plus glDrawElements were not used. vitaGL's array path changes shader/attribute
  layout (see vitagl-attribute-invalidation.patch), whereas the immediate pool keeps the GPU input
  byte-identical.
