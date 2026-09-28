# M13 aggressive source discovery — 2026-09-27

No fourth mission-required missing .cpp is confirmed by this sweep. The
three confirmed, still unintegrated owners remain Mission03.cpp,
Test_RMV_Toolkit.cpp and Toolkit_Sounds.cpp, in addition to the five units
source-selected earlier. No C++ build, game launch, install or device action.

## Expanded evidence

- Added original PhysClass definition roots: 143 records in M13.ldd and six
  in M13.lsd. Disk IDs remain explicitly unsigned little-endian 32-bit.
- Added named Soldier animation/loiter/death-sound, Powerup weapon/sound,
  and Beacon cinematic/explosion/sound links to the typed traversal.
- Typed closure grows from 301 to **326 presets**, retaining **75 required
  scripts**. **43 persistence-factory types** now have both native compile
  graph membership and defined Load methods in the unchanged Dev207 ELF.
- All **102 ScriptCommands callbacks** referenced by these 75 script bodies
  have non-null function-name assignments in staged original scriptcommands.cpp.
  This is source evidence, not a runtime callback/behavior test.
- A separate conservative exact-token traversal covers **1,118 possible
  presets and 77 script names**, including shared pre-declaration tables,
  binary level/preset strings, parameters, script literals and typed links.
  This is a discovery envelope, not 1,118 proven gameplay dependencies.
- Original conversationmgr.cpp, conversation.cpp, activeconversation.cpp
  and scriptcommands.cpp appear in the configured native compile graph.
  Conversation binary semantics remain outside the typed parser.

## Leads checked rather than counted as missing gameplay

The envelope finds Mission11.cpp through M11_VoltRifleGuy_Script_JDG on preset
81930210, Nod_RocketSoldier_2SF_VoltAutoRifle. The incoming reference is the
**first column** of Soldier_Powerup_Table in Toolkit_Powerup.cpp: a lookup
prefix for an already existing soldier. The actual creation calls use columns
two and three (weapon pickup and pickup Twiddler). This path does not prove
M13 creates that soldier. Mission11.cpp stays an unconfirmed lead; do not add
it to the mission-required missing-file count from this evidence.

The same shared-table overreach finds M00_Change_L3Mutant_RadarMarker_JDG,
already owned by source-selected Toolkit.cpp. Generic strings such as Default
also match unrelated definitions. Three envelope factory IDs absent from the
runtime factory map are editor definitions: 0x50001 tile, 0x50016 VIS point,
0x50019 dummy object (EditorChunkIDs.h, base 0x50000 in saveloadids.h).
They are not evidence that the game needs the LevelEdit translation units.
All mapped envelope definition-factory owners are in the native compile graph.

Remaining indirect creation sites were inventoried: Test_Cinematic consumes
text presets/script names; soldier pickups use Soldier_Powerup_Table; building
speakers use the Explosion_Name parameter. Exact-token discovery includes
those strings but does not establish branch execution or numeric parameter
meaning. No replacement implementation or speculative source integration.

## Reproduction and limits

```sh
python3 tools/audit_m13_level_owners.py \
  --archive build/host-m13-diagnostic/retail/Data/M13.mix \
  --definitions build/host-m13-diagnostic/retail/Data/always.dbs \
  --native-build build/vita-fast-candidate \
  --output build/dev208-m13-aggressive-typed.json
python3 -m tools.discover_m13_indirect_owners \
  --typed-receipt build/dev208-m13-aggressive-typed.json \
  --data build/host-m13-diagnostic/retail/Data \
  --output build/dev208-m13-aggressive-discovery.json
python3 -m unittest tools.test_m13_level_owners tools.test_m13_script_coverage tools.test_m13_mission_inventory tools.test_script_provider_contract
```

24 Python tests pass, including a new physics-only root/pointer-token width
regression. Discovery receipts retain metadata and predecessor edges, not
retail payloads. Input archive/database/ELF hashes are retained in the typed
receipt and match the preceding additional-owner audit.

Eighteen typed referenced IDs do not resolve in this database; they remain
data-reference questions. Computed strings, numeric script parameters, every
possible typed link, active conversation state, preprocessor/runtime branch
semantics and actual registration/execution are not exhaustively verified.
The existing 62-script candidate gate still needs the expanded typed roots.
No native acceptance gate has closed: 0/7 corrected-source reference segments.
