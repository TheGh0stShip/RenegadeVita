# Campaign objective/HUD text readiness M01-M11

Read-only scan of `Add_Objective`, `Set_Objective_HUD_Info(_Position)`, `Display_Text` and
`Set_HUD_Help_Text` string IDs, radar markers and `Reveal_Encyclopedia_*` IDs against the retail
`strings.tdb` record sets, plus Unicode coverage of the Vita FreeType font files. Tool:
`tools/audit_objective_text_readiness.py` (extends `tools/audit_mission_text_routes.py`).
Evidence class: host Python source/data scan; no build, launch, emulator or Vita. No retail text is
reproduced (IDs, counts and code points only). It proves no runtime lookup, rendering or layout.

## Verdict

- Unresolved string IDs, M01-M11, both TDB candidates: **0**.
- Non-constant/unresolvable string-ID expressions: **0**.
- Runtime language is English: both retail strings.tdb files store language ID 0 in their variables chunk,
  `TranslateDBClass::m_LanguageID` defaults to LANGID_ENGLISH, and the only game-side
  `Set_Current_Language` (Commando/init.cpp) is commented out. English strings in the referenced IDs are
  ASCII plus U+000A newline, so no non-ASCII glyph is required for English.
- Non-English records: French/German need Latin-1 plus U+0153, covered by Arial MT; Chinese/Korean need
  CJK/Hangul, which Arial MT, Regatta and the user `arial.ttf` fallback do **not** cover. Not a defect for
  English play; a gap if non-English language selection is ever exposed on Vita.
- Encyclopedia reveals: every literal ID has an INI section whose NameID/DescriptionID resolve in both TDBs.

## Inputs

| Input | SHA-256 | Detail |
|---|---|---|
| always.dat strings.tdb | `c2b396d11d4d99f6e83c16b726a1d682883e64eebf7d892de88041696bb922af` | 11655 IDs, translations per ID [5, 7] |
| always.dbs strings.tdb | `61195381b30605a9dc5278d529cfc7d4a0c01666534519b4f3ece5e6196ce374` | 11678 IDs, translations per ID [1] |
| Arial MT (ARI_____.TTF) | `f96ba07bb7b31f6935ba85e2726f70397ad291229c51e6491cd39eda108358b6` | 70788 bytes, 244 Unicode code points (primary) |
| Regatta Condensed (54251___.TTF) | `bca394f59392445732cdfb315fdbb8bdfd650b26fe12bd4151b44f9b5ca8a460` | 30093 bytes, 226 Unicode code points (primary) |
| Arial user fallback (arial.ttf) | `b3658eadae55e682b5f69eb64c439c1ecc8f196c0bb8d4756d145d13bc86476a` | 1045720 bytes, 3506 Unicode code points (fallback) |
| string_ids.h | `63d50eb832b9d558e15c02ac7a7c902f7c1cac90b9448bfcbc3d9561e1aad7cf` | symbolic ID header |

Scope: scripts in each map's discovered binding closure plus the mission owner `.cpp` (scripts not bound
in the closure are "owner-only leads"). Both archive candidates are checked so the result is independent
of mount order.

## Per-mission ID resolution

| Map | Add_Objective | HUD info | Display_Text | HUD help | Unique IDs | Closure IDs | Owner-only IDs | Missing | Unresolved exprs | Radar markers | Encyclopedia reveals |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M01.mix | 20 | 16 | 0 | 40 | 54 | 54 | 0 | 0 | 0 | 0 | 22 |
| M02.mix | 46 | 21 | 0 | 28 | 60 | 60 | 0 | 0 | 0 | 0 | 6 |
| M03.mix | 30 | 14 | 0 | 5 | 35 | 35 | 0 | 0 | 0 | 0 | 0 |
| M04.mix | 18 | 36 | 0 | 3 | 26 | 25 | 1 | 0 | 0 | 9 | 1 |
| M05.mix | 20 | 20 | 0 | 13 | 36 | 36 | 0 | 0 | 0 | 0 | 0 |
| M06.mix | 17 | 6 | 0 | 3 | 25 | 25 | 0 | 0 | 0 | 0 | 0 |
| M07.mix | 20 | 11 | 0 | 16 | 38 | 38 | 0 | 0 | 0 | 0 | 0 |
| M08.mix | 18 | 14 | 0 | 3 | 26 | 26 | 0 | 0 | 0 | 0 | 2 |
| M09.mix | 10 | 7 | 0 | 4 | 17 | 17 | 0 | 0 | 0 | 0 | 0 |
| M10.mix | 48 | 38 | 0 | 2 | 48 | 48 | 0 | 0 | 0 | 0 | 0 |
| M11.mix | 10 | 6 | 0 | 4 | 16 | 16 | 0 | 0 | 0 | 0 | 0 |

Counts are call sites; `Add_Objective` contributes both its title ID and optional long description ID.
A zero ID in an objective/message slot means "none" in the original and is not looked up. Unique IDs
are distinct nonzero IDs per map (Set_HUD_Help_Text(0) is the original clear operation).

## Unresolved IDs per mission

- M01.mix: none
- M02.mix: none
- M03.mix: none
- M04.mix: none
- M05.mix: none
- M06.mix: none
- M07.mix: none
- M08.mix: none
- M09.mix: none
- M10.mix: none
- M11.mix: none

## Objective cross-reference leads (heuristic, not defects)

`Set_Objective_*` targets whose `Add_Objective` was not found with the same ID token in the scanned
scripts. Causes are helper functions passing a variable ID (`id`, `type`), numeric IDs added through a
helper or custom event, cross-script constants, and commented-out source. Token matching only; they say
nothing about string-ID resolution above and need dataflow tracing before being called defects.

- M01.mix: `M01_BARN_OBJECTIVE_JDG`, `M01_BARN_ROUNDUP_OBJECTIVE_JGD`
- M02.mix: `213`, `type`
- M03.mix: `1000`, `1001`, `1007`, `1008`, `1010`
- M05.mix: `type`
- M06.mix: `type`
- M07.mix: `type`
- M08.mix: `type`
- M09.mix: `id`, `type`
- M10.mix: `id`, `type`

M01 `M01_BARN_OBJECTIVE_JDG` and `M01_BARN_ROUNDUP_OBJECTIVE_JGD` do have literal `Add_Objective` calls
(Mission01.cpp lines 2042 and 2117), so those two are scanner scope misses, not missing objectives.
M03 numeric IDs 1000-1010 appear in `Set_Objective_HUD_Info*`; the nearby `Add_Objective` lines are
commented out in Mission03.cpp (78-82), so the live add path for them is unverified.

## Radar markers

`Add_Radar_Marker` and `Set_Objective_Radar_Blip*` carry no string ID, only shape (0-4) and color (0-7)
enums. M04 is the only map with direct `Add_Radar_Marker` calls (9). Literal shape/color values outside
scriptcommands.h ranges: 0.

## Encyclopedia reveals

`Reveal_Encyclopedia_*` take INI `ID=` values (characters/weapons/vehicles/buildings.ini in always.dat).
Each literal ID was matched to its section and the section NameID/DescriptionID checked in both TDBs.

| Map | Reveals | INI section found | Text IDs missing |
|---|---:|---:|---:|
| M01.mix | 22 | 22 | 0 |
| M02.mix | 6 | 6 | 0 |
| M04.mix | 1 | 1 | 0 |
| M08.mix | 2 | 2 | 0 |

`Display_Encyclopedia_Event_UI` uses the GlobalSettings event string ID (definition data) and
`Toolkit_Powerup` reveals via a script parameter; neither is a literal script argument, so both are outside
this scan. EVA/radar/objective voice and the Add_Objective description-sound field are audio, not text.

## Glyph / font support

Per `stylemgr.ini`, HUD/objective/in-game text and subtitles use Arial MT (ARI_____.TTF, first in the
provider candidate list); titles/menus use Regatta Condensed LET (54251___.TTF). `FT_Load_Char`
succeeds for an unmapped code point by rendering .notdef, so a gap shows a box instead of failing. The
coverage is a cmap lookup, not rendered-pixel evidence. Code points are those in IDs referenced by
M01-M11 scripts. U+000A is a row break handled by the sentence layout and excluded from the counts.

| TDB candidate | Language | Non-ASCII code points | Uncovered by Arial MT | Uncovered by Regatta | Uncovered by arial.ttf |
|---|---|---:|---:|---:|---:|
| always.dat | 0 English | 0 | 0 | 0 | 0 |
| always.dat | 1 French | 9 | 0 | 0 | 0 |
| always.dat | 2 German | 6 | 0 | 0 | 0 |
| always.dat | 4 Chinese | 725 | 724 | 724 | 724 |
| always.dat | 6 Korean | 446 | 446 | 446 | 446 |
| always.dbs | 0 English | 0 | 0 | 0 | 0 |

English (language 0) has no non-ASCII code point in either candidate. always.dbs carries one
translation per ID. Spanish (index 3) and Japanese (index 5) produced no gap rows: no non-ASCII code point
in the referenced IDs (or no distinct string); not separately verified beyond that.

Uncovered code points are U+4E00-9FFF style CJK ideographs, U+3000 punctuation (Chinese) and
U+AC00-D7A3 Hangul syllables (Korean) except U+2026, which Arial MT covers. U+000A aside, French/German
code points are all covered by Arial MT and Regatta.

## Reproduce

```sh
python3 -m tools.audit_objective_text_readiness --data /path/to/retail/Data \
  --font-dir /path/with/ARI_____.TTF --font-dir /path/with/user/fonts --owner-scan \
  --output-directory build/objective-text-readiness-YYYYMMDD --report reports/campaign/OBJECTIVE_TEXT_READINESS.md
```

Detailed JSON stays in ignored `build/`. Limits: script-argument source scan only; TDB/INI/font presence
does not prove display, translation selection, wrapping, glyph rasterization or physical correctness.
Physical Vita font availability (loose ARI_____.TTF outside Data/) is a separate gate; the emulator
retail tree carries it only through the `user/fonts` fallback.
