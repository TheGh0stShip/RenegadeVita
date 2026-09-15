# Native HUD atlas root cause and correction

## Controlled host comparison

After correcting the independent LP64 TGA header layout in an isolated probe,
both original HUD TGAs loaded successfully, but their CPU surface formats
were UNKNOWN and the glyph comparison could not proceed:
`build/hud-fixed-layout-qJGlwo/runtime.log`.

The original desktop WW3D::Init calls `Init_D3D_To_WW3_Conversion`. The native
branch returns before that call and omitted its equivalent. This leaves the
reverse format table zero-initialized, so SurfaceClass::Get_Description loses
the format required by original font bounding and atlas copies.

Adding the original initialization call before font construction produced:

- FONT12x16: 10 digits, 1,712 compared pixels, zero mismatches per cycle.
- FONT6x8: 10 digits, 384 compared pixels, zero mismatches per cycle.
- Two original M00 host cycles passed under AddressSanitizer.

Matching output: `build/hud-fixed-layout-c7e3LD/runtime.log`. The comparison
checks original alpha bounds, dimensions, UV placement and each packed pixel.
It proves CPU atlas consistency only, not native GPU sampling or visible HUD.

## Integrated source

- `ww3d2-a35-format-table-init.patch` restores the original call in native
  WW3D::Init rather than adding a new renderer or per-frame workaround.
- `wwlib-a35-targa-fixed-width.patch` fixes six serialized 32-bit fields and
  asserts 18/26/495-byte header/footer/extension layouts. The uppercase original
  header is copied into staging; pristine upstream and retail remain unchanged.
  This repairs host validation while preserving the original ARM file layout.
- The original host interactive test now compares both digit atlases rather
  than merely checking Font3D pointers.
- The canonical host runner builds its non-sanitized interactive target before
  cross-scene tests, and the standalone dialog validator receives its mandatory
  resource-header argument.
- The regenerated existing EVA dependency patch disables the demo Options
  button and rejects its command while retaining its label. Other dependency
  changes in that patch are preserved. No manually maintained count was added.

These changes were integrated only after Dev115 canonical completion. They
are not present in the immutable Dev115 package being tested for checkpoint
reactivation and original EVA resources.

## Dev115 identity

VPK: `eb25ec548ee74514fd98e501142f3a765376ba1d8f63a08da6bced9c93ae0af1`

ELF: `e561362adf2d5ecdf92db0a90380fc4640ba70647fb2078185b5d577c9c9bf65`

SELF: `10b2b1dfdc337913d6a4801d1a3e73a4f1e618331b250a8dd329562bf4a8a74f`

Checkpoint request retains post-Sydney save hash
`f651d389877c6df19dc2fa95b1c636627a331e2f451d46f286599c56f8981ec7`.
Runtime acceptance remains pending.
