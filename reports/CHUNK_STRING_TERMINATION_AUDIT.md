# Chunk string termination audit (report only, no patches)

Macros: `staging/wwlib/chunkio.h:374-381`.
- `READ_MICRO_CHUNK_STRING(cload,id,var,size)`: bound is only `WWASSERT` (compiled out in release) -> overflow of fixed `char[]` when chunk length > size, and no terminator if stored bytes lack NUL.
- `READ_MICRO_CHUNK_WWSTRING`: `Get_Buffer(len)` uses `Uninitialised_Grow`; reads exactly `len` bytes. Terminated only if the writer stored the NUL (original writers do via `WRITE_MICRO_CHUNK_WWSTRING`, len+1). Zero-length or truncated/tampered chunk leaves uninitialised bytes / stale tail.
- `READ_MICRO_CHUNK_WIDESTRING`: same, `(len+1)/2` wchar buffer; odd length leaves half a wchar uninitialised.

Scope: loaders fed by user-writable files under `ux0:data/renegade/user/` (saves, input configs, options). Definition loaders reading retail `always.dat`/`.ddb` (globalsettings, vehicle, powerup, CNCModeSettings, terrainmaterial, etc.) are lower risk and excluded from priority list.

## Prioritized list

| P | Site | Source file | Use of string | Impact |
|---|------|-------------|---------------|--------|
| 1 | `staging/ww3d2/rendobj.cpp:1197` | save game (render obj persist factory) | `char name[]` -> `Create_Render_Obj(name)`, trace log | Stack overflow (assert-only bound) + unterminated C string into asset lookup/strcmp. Highest: memory corruption from a crafted/corrupt .sav. |
| 1 | `staging/ww3d2/dazzle.cpp:1454` | save game (dazzle persist factory) | `char dazzle_type[]` -> dazzle type lookup by name | Same as above: stack overflow + unterminated strcmp. |
| 2 | `staging/combat/savegame.cpp:432` | `.sav` header | `MapFilename` -> level/mix path load | Unterminated path into file factory open; garbage path / over-read. |
| 2 | `staging/combat/savegame.cpp:601` | `.sav` header peek (load menu) | `map_filename` -> path/menu | Same, runs while merely listing saves (no user intent to load). |
| 2 | `staging/combat/savegame.cpp:434`, `:603` | `.sav` header | `Description` (WideString) -> menu text rendering | Unterminated wide string over-read in UI list; odd length -> partial wchar. |
| 3 | `staging/commando/inputconfigmgr.cpp:718` | input config manager (user config) | `filename` -> loads that input config file | Unterminated path into file open. |
| 3 | `staging/commando/inputconfig.cpp:126` | input config entry | `Filename` -> config file path | Same. |
| 3 | `staging/commando/inputconfig.cpp:125` | input config entry | `DisplayName` (WideString) -> menu text | Wide over-read in controls menu. |
| 4 | `staging/combat/ccamera.cpp:495-497` | save game (camera state) | camera profile names -> profile lookup by name | Unterminated strcmp; lookup failure/over-read. |
| 4 | `staging/combat/action.cpp:3127`, `:3133` | save game (action state) | anim / conversation names -> asset/conversation lookup | Over-read into anim manager / conversation lookup. |
| 5 | Other save-state WWSTRING reads in combat (`soldier.cpp`, `smartgameobj.cpp`, `physicalgameobj.cpp`, `damageablegameobj.cpp`, `transition.cpp`, `cinematicgameobj.cpp`, `weaponmanager.cpp`) | save state where present (definition vs. state not individually verified in timebox) | mostly asset names | Same class; verify per site. |

## Recommended fix direction (not applied)
Central fix in a staging patch to `chunkio.h`: for `STRING` clamp to `size-1` and force `var[size-1]=0` / skip excess; for WW/WIDE variants zero-fill or terminate at `len` after read (and treat len 0 as empty). Keeps original call sites untouched.

Caveat: 8-minute timebox; P5 sites not individually classified.
