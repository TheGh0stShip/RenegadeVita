# Renegade Vita M00 demo

The durable destination is the complete native Renegade Vita port. This demo
is an interim community showcase of the Renegade Vita project's work, not the
finished port. Full campaign and original-system coverage remain on the main
roadmap; demo-specific restrictions must be isolated in a selectable profile.

This native demo permits only the original `M00_Tutorial.mix` launch. Original
Combat mission success triggers a three-second fade, ten-second thank-you
message, and twenty-second credits scene before original session teardown and
return to the main menu. Death and failed objectives never count as tutorial
completion. Start opens the original EVA pause screen.

The credits acknowledge Westwood Studios / Electronic Arts, VitaSDK, vitaGL,
vitaShaRK, SceShaccCgExt, FFmpeg, mpg123, FreeType, zlib, libpng, bzip2, minizip,
taiHEN, math-neon, and the PlayStation Vita homebrew community. Original retail
menu imagery supplies the backdrop; no third-party logo artwork is imported.

Credits do not replace license notices or corresponding-source obligations.
Preserve the original source/dependency notices when assembling a release.
The source license does not grant permission to distribute retail game data.
No retail archives, movies, fonts, saves, or configuration belonging to a
user may be included in the VPK or public diagnostics. Users provide their
own unchanged shared retail data and tutorial archive at
`ux0:data/renegade/retail/Data/`. Other installed retail missions must not be
deleted or modified; the demo simply does not launch or pre-index them.

Release acceptance requires the entire authentic M00 route, both original
intro movies, readable menus/loading/HUD, correct targeting boxes, the
success/fade/message/credits/menu-return sequence, and crash-free lifecycle evidence.
Vita3K is a separate preliminary evidence class. Both PS Vita and PSTV must
be tested before claiming final hardware acceptance or 60 FPS performance.
