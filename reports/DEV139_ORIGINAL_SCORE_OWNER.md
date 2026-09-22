# Dev139 original score-screen owner

The full-port profile now links original `staging/commando/scorescreen.cpp`
instead of the Vita placeholder `ScoreScreenGameModeClass::Init` and empty
`Save_Stats`. The original score dialog `On_Destroy` calls
`CampaignManager::Continue`, preserving the game's score-to-movie callback.
The M00 demo profile does not select this unit and keeps its prior stub.

Full-port `A3.5-dev139` ARM ELF, SELF, and VPK built. Symbol inspection found
the original `ScoreScreenGameModeClass::Init`, `Save_Stats`, and
`ScoreScreenDialogClass::On_Destroy`. Hygiene and public-doc checks passed.
The VPK contains only `eboot.bin` and `sce_sys/param.sfo`.

| Artifact | SHA-256 |
| --- | --- |
| VPK | `174eb6dced97a390a4fdfaa99708c528ce3b2c096bf6139dc811bf1bc62af4ee` |
| SELF | `541503f7459c70122e9f12d901efcb9b9c29b32149457c81096b9a0e97bc4248` |
| ELF | `ddfdff3ad7e2c5ef5c406e5185788df5e48257d7ab9a9fefd2dd3b1c8db41aad` |

The prior Dev138 Vita3K trial selected Campaign/Soldier and loaded `M13.mix`.
It reported 357 registered scripts, 31 active script instances, and a first
render frame with 108 meshes, 10,560 vertices, 7,116 triangles, and no
rejected or unsupported submissions. The 240-second watchdog ended the run;
inputs were released and the owned emulator process was stopped. Runtime log
and captures are in managed AppData `campaign-dev138-trial-1/`. This is M13
startup/render evidence, not M13 objective or completion evidence.

| Mission ID | Initialization | Required gameplay/objectives | Normal transition | Save/load | Build/evidence |
| --- | --- | --- | --- | --- | --- |
| M13 | passed in Dev138 Vita3K | unverified | unverified | implemented but untested | Dev138 M13 first-frame and script count |
| M01 | unverified | original mission scripts linked, untested | unverified | unverified | Dev139 ARM symbols only |

Immediate blocker: the direct Vita simulation observes `Mission_Complete`,
then tears down and reinitializes `CampaignManager`. Calling `Continue` inside
that frame would invoke original `GameInitMgrClass::End_Game` while the Vita
outer loop still owns teardown. The safe transition needs one persistent
campaign session with original Combat/Score/Movie mode callbacks and no double
unload. Dev139 has not been run on Vita3K or physical Vita.
