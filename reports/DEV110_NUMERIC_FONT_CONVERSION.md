# Original numeric Font3D atlas conversion

## Source evidence

Original HUD selects FONT12x16.TGA for large counters and FONT6x8.TGA for small
counters. Read-only inspection of installed always.dat found both original
entries with valid names/CRC indexes. Pillow host decoding reports:

- FONT12x16.TGA: 192x256, 32-bit RGBA, 5000 opaque pixels, 44152 transparent.
- FONT6x8.TGA: 96x128, 32-bit RGBA, 1205 opaque pixels, 11083 transparent.

Candidate-scoped metadata/hash receipts are under build/dev110-host-evidence.
No retail payload was written or modified; host decoding is not native proof.

## Concrete conversion gap

Original Font3D calls Make_Proportional then Minimize_Font_Image, which creates
an A4R4G4B4 atlas, clears it and copies each glyph from the source surface.
Desktop SurfaceClass::Copy uses D3DXLoadSurfaceFromSurface for differing formats.
The native replacement instead returns immediately whenever formats differ.
Its TGA loader retains the source format. Thus the 32-bit-to-16-bit glyph copies
are discarded instead of converted. Original FindBB uses inclusive output
bounds, as does the replacement; do not apply an unrelated bounding-box offset.

## Prepared correction

build/dev110-host-evidence/font-surface-conversion.patch adds only the required
ARGB/XRGB8888-to-A4R4G4B4 copy path, preserving clipping, source/destination pitch,
alpha nibbles and existing same-format memmove behavior. Other unsupported
conversions remain unchanged rather than accepting arbitrary pixel layouts.
This is a port-source proposal, not an upstream staging patch. It is not yet
applied, compiled or visually proven. Integrate with the quicksave dispatch and
Render2D readiness corrections after Dev109 canonical completes. Then validate
actual numeric text, not just nonzero source pixels or package success.
