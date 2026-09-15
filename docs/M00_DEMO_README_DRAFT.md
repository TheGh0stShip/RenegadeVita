# Renegade Vita M00 Demo

Release notes draft. This is not a release announcement or a claim that the
current development candidate has passed all acceptance checks.

## What this demo is

A native PlayStation Vita port of the original Command & Conquer: Renegade
engine, limited to the complete M00 Tutorial. The full game port remains the
long-term project; the demo does not replace that goal.

The intended ending is a slow fade, a thank-you message, dependency credits,
and safe termination without loading M01. End-to-end runtime validation of
that sequence is still pending.

## Your game data

The application package does not include the retail game, movies, music,
textures, fonts, or save games. Provide your own retail data unchanged at:

`ux0:data/renegade/retail/Data/`

Writable settings, logs and saves belong under:

`ux0:data/renegade/user/`

Do not merge writable files into the retail Data directory. Back up existing
user saves before changing development candidates. Do not distribute your
retail files or saves with the application.

## Development evidence is not release acceptance

The Dev115 Vita3K run reloaded an original M00 checkpoint, opened a readable
original EVA pause screen, and returned to gameplay. That does not establish
full tutorial completion or physical Vita/PSTV acceptance.

Dev116 is intended to correct the numeric HUD atlas initialization and
disable the unsupported demo Options action while keeping its label visible.
Its final build and visual results must be recorded before this draft is
promoted into release notes. No sustained 60 FPS claim is made.

Vita3K save-overwrite behavior is under investigation. Preserve existing
checkpoints; a newly created save is not considered reusable until its
structure and original-engine reload have both been validated.

## Credits and source

Original game: Westwood Studios / Electronic Arts.
Native port: Renegade Vita project.
Platform and graphics: VitaSDK, vitaGL, vitaShaRK and SceShaccCgExt contributors.
Movie decoding: FFmpeg contributors.
Fonts and libraries: FreeType, zlib, libpng, bzip2 and minizip contributors.
Platform support: taiHEN and math-neon contributors.

The repository's LICENSE.md points to the controlling upstream license and
additional terms. A public release must identify its matching source and
dependency notices rather than relying only on these short credits.

## Before publishing

Replace this draft with the accepted candidate identity, package SHA-256,
matching source location, tested installation steps, verified control map,
known limitations, and the actual M00 start-to-finish evidence. Keep host,
Vita3K, PS Vita and PSTV results explicitly distinguished.
