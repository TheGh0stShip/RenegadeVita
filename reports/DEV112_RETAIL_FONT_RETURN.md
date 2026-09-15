# Dev112 retail font dependency

The first fresh canonical host run stopped at its original Arial font probe:
`ARI_____.TTF` was unavailable through the emulator retail root used as the
host input. No ARM package was produced by that run. Failure evidence remains
in `build/dev112-host-evidence/canonical-launch.log`.

The established Steam source root (`retail-pc`, a symlink to the user's Steam
installation) contains two loose fonts outside `Data/`:

- `54251___.TTF`: 30,093 bytes.
- `ARI_____.TTF`: 70,788 bytes.

The runtime had already resolved Regatta from its existing asset chain. The
emulator's user font directory contained a different `arial.ttf` fallback,
not the original loose Arial MT font. No claim is made that the `Data/`
archives were incomplete; a Data-only manifest does not cover root-level fonts.

With Vita3K stopped, the original Arial MT file was copied to the previously
absent `user/fonts/ARI_____.TTF`. The existing fallback and retail files were
not overwritten. Source and destination SHA-256 both equal:

`f96ba07bb7b31f6935ba85e2726f70397ad291229c51e6491cd39eda108358b6`

Receipt: `build/dev112-host-evidence/original-arial-font.sha256`.
This is the user's private retail font, not a redistributable demo asset.
The copy is not proof of native font selection or corrected HUD digits.

Canonical host validation was restarted against the established Steam root,
with new evidence in `build/dev112-host-evidence/canonical-source-root.log`.
The prior failed log is retained. No completed canonical closure is claimed here.

Setup follow-up: distinguish Data archive coverage from loose-font coverage;
validate required original font availability or an explicitly supported
user-font fallback before declaring a fresh emulator setup ready.
