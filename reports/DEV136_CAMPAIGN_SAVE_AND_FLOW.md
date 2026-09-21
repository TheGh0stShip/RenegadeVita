# Dev136 campaign save handoff and retail flow

The full-port frontend previously accepted only M00 when re-entering after a
session teardown. It now validates a queued original `.sav` with the existing
single-player archive resolver and admits the save only if the source resolves
to a campaign/tutorial archive. The demo profile retains its M00-only guard.
This fixes a shared boundary for Load and pause-menu reload; **save restoration
on Vita is not yet verified**.

The original `CampaignManager::Init` loaded 36 flow entries from user-owned
retail `campaign.ini` through the existing MIX/FileFactory chain. An opt-in
host harness trace (`RENEGADE_TRACE_CAMPAIGN_FLOW=1`) established the order:
M13, then M01 through M11. Each level is followed by `Score` and a movie;
the final movie is `Data\Movies\R_Finale.bik`. This is catalog evidence,
not transition evidence. Tutorial M00 is separate from the catalog sequence.

| Mission | Load/init | Gameplay/scripts | Objectives complete | Next transition | Save/load | Physical Vita |
| --- | --- | --- | --- | --- | --- | --- |
| M00 Tutorial | Prior demo evidence | Partial prior demo evidence | Open | Separate from campaign | Prior M00 evidence | Prior M00 only |
| M13 | Vita3K Dev135 | Movement/fire/pause only | Open | M01 open | Dev136 ARM path only | Open |
| M01 | Prior host harness | Open | Open | M02 open | Open | Open |
| M02 | Open | Open | Open | M03 open | Open | Open |
| M03 | Open | Open | Open | M04 open | Open | Open |
| M04 | Open | Open | Open | M05 open | Open | Open |
| M05 | Open | Open | Open | M06 open | Open | Open |
| M06 | Open | Open | Open | M07 open | Open | Open |
| M07 | Open | Open | Open | M08 open | Open | Open |
| M08 | Open | Open | Open | M09 open | Open | Open |
| M09 | Open | Open | Open | M10 open | Open | Open |
| M10 | Open | Open | Open | M11 open | Open | Open |
| M11 | Open | Open | Open | Finale open | Open | Open |

The original source's completion path is `CombatManager::Mission_Complete` ->
`CombatGameMiscHandlerClass::Mission_Complete` -> pending flag ->
`CombatGameModeClass::Think` -> `CampaignManager::Continue`. The Vita direct
simulation path instead installs an observation handler and calls
`CombatManager::Think` directly; it tears down after observing success. No
normal level-to-score/movie/next-level transition is currently connected.
This is the next shared blocker. It must preserve the original score/movie
callback semantics and avoid re-entrant teardown within a frame.

Verification: 13 focused frontend contracts pass. Full-port ARM build and
ELF/SELF/VPK packaging pass. VPK contains only `eboot.bin` and
`sce_sys/param.sfo`; SHA-256 is
`2e770738b23ba0e5d4b00b8ee6c2126025f8f02bb8c1e1403d13ec8db4ec71dc`.
The catalog host run reached the retail flow trace but failed an isolated
Arial frontend probe before M13 simulation. No Dev136 Vita3K or physical
runtime, save roundtrip, or mission transition is claimed.
