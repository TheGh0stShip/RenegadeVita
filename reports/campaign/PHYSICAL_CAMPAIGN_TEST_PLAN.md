# Physical campaign test plan: M13, M01 to M11, R_Finale, main menu

Evidence class: a plan only. It consolidates routes, deliberate edge cases and
log signatures from `reports/campaign/*` (the Full audit, Soft-lock hunt and
Follow-up sections of every `Mxx_READINESS.md`, plus `CONVERSATION_COMPLETION`,
`AUTOSAVE_CHAIN`, `SCORE_AND_RANKS`, `FAIL_AND_RETRY_FLOW`,
`SCRIPT_ZONE_TUNNELLING`, `ESCORT_ROBUSTNESS`, `ELEVATORS`, `CINEMATIC_LOW_FPS`,
`SESSION_CHAIN_ACCUMULATION`, `OBJECTIVE_STATE_LIFECYCLE`, `M02_SNIPER_CONTROL`,
`WEATHER_BY_MISSION`, `STEALTH_RENDERING`, `reports/VITA_CONTROLS.md`). Every
statement about what the game does came from static source and retail-metadata
review. None of it has been observed on a Vita. Nothing here is accepted until
a returned physical log and your own eyes agree, and a log never proves visual,
audio or control correctness.

Log helper: `python3 tools/extract_campaign_log_signatures.py <pulled log>`
(per-mission breakdown, residual table, rank-write order, flags). Details in
section 3.

Legend: `[ ]` do it and tick it. **N** = normal route step. **E** = deliberate
edge case (a reproduction of a hazard the audits found). **S** = save to make.
**G** = text to grep afterwards.

## 1. Before you start (once)

- [ ] **Candidate must be built from the current main HEAD, not dev240.** The
      packaged `RenegadeVita-A3.5-dev240.elf` does not contain the strings for
      the later patches (PCT watchdog, open-gate fallback, Raveshaw landing
      fallback, elevator entry timeout, M08 texture fallback, `SESSION
      residual`, Circle crouch latch). Check the candidate you are about to
      install (host side, read-only):
      `python3 tools/extract_campaign_log_signatures.py --elf <candidate>.elf`
      Every row you plan to rely on must say `ARMED`. A `MISSING` row means the
      edge case below cannot be confirmed from the log for that candidate. It is
      still worth playing, but only by eye.
- [ ] Retail data is untouched at `ux0:data/renegade/retail/Data/`. For M09,
      note the SHA-256 of `Data/M09.mix`. The audits used
      `059fc7de0c06c31e2aa69e1ab7768de81f3377e18c971ba8f98f41e15f1705c1`;
      an older edition `3132c754…` has different level data.
- [ ] Difficulty: pick **Soldier (middle)** for the main run. On Recruit M04
      pre-marks all three prisoners at the rally point, so Soldier or Commando
      is the only way to test prisoner 3 walking to the rally zone. Replay M04
      on Recruit later if you want both (section 5).
- [ ] Optional, enables conversation-drop telemetry: create an empty file
      `ux0:data/renegade/user/config/script-coverage.flag`. Any file works
      (the runtime only checks that it opens). It records conversation start,
      end, monitor and observer-call events in the flight recorder, which is
      the only way to see the M10/M03/M05/M07/M11 "conversation was dropped"
      cases. It is off by default and its cost has not been measured. Leave it
      on for the whole run and note any change in frame rate.
- [ ] Optional, only on development-checkpoint builds: a single mission can be
      entered directly with `ux0:data/renegade/user/config/dev-mission-launch-v1.txt`
      containing `RVMS1 M05.mix` (format in `reports/DEV140_M01_DIRECT_ENTRY.md`). This does not exercise campaign state or
      transitions, so use it only to repeat an edge case, never for the main run.

### Controls you will need (`reports/VITA_CONTROLS.md`)

| Action | Vita |
| --- | --- |
| Poke PCT, MCT, console, gate, civilian; enter or leave vehicle; ladder | Triangle |
| Quicksave | Select + Square (alternates `quicksaveA.sav` / `quicksaveB.sav`) |
| EVA menu (objectives tab, Save, Load, Quit) | START. D-pad + Cross, or touch. Circle leaves |
| Cycle objective marker | Select tap |
| Sniper scope on/off, remote C4 | L trigger. D-pad Up/Down zoom |
| Fire, plant C4, hold to arm beacon | R trigger (beacon: stand up first, do not move) |
| Crouch | Circle held, or quick tap to latch |
| Movie skip | START, Cross, Circle or Triangle |

### Save hygiene (the engine only has two quicksave slots)

- Quicksave **alternates between two files**, `user/save/quicksaveA.sav` and
  `quicksaveB.sav`, and the next mission overwrites them. For every **S** step
  below, prefer an **EVA > Save with a typed name** (system IME), for example
  `M10_pregate`. Use Select + Square only for throwaway checkpoints.
- A level-start `autosave.sav` is written on the first gameplay frame of M01 to
  M11 (not M13). Each mission overwrites it. That is the leg checkpoint.
- Pull `user/save/` at the end of every leg (section 6).

### Log hygiene (this decides whether your evidence survives)

- **The runtime log is truncated every time the app launches.** Pull
  `ux0:data/renegade/user/logs/<candidate>-runtime.log` before you relaunch.
- It stops accepting normal lines after about **4 MiB per process** and writes
  `[runtime-log] TRUNCATED: session log cap reached`. After that only
  `[LIFECYCLE]`, FATAL, crash, Teardown and `Overall:` lines survive. Two or
  three missions per launch is the safe size, so the run is cut into legs.
- Never resume a leg by relaunching in the middle of a mission unless the step
  says so. A relaunch loses the in-memory campaign state; the autosave
  restores it.

## 2. Run order (legs)

One leg = one app launch. End a leg right after the next mission's first
gameplay frames, once the autosave is written
(`A3.5 save write: path=...autosave.sav ... success=1`). Then EVA > Quit to the
main menu, exit the app, pull logs and saves, relaunch, and start the next leg
with Load > `autosave`. Starting each leg from the autosave also tests the
autosave chain and the load path.

| Leg | Missions | Starts from | Ends at |
| --- | --- | --- | --- |
| 1 | M13, M01 | New Campaign (Soldier) | M02 first frames (autosave) |
| 2 | M02, M03, M04 | `autosave` (M02) | M05 first frames |
| 3 | M05, M06, M07 | `autosave` (M05) | M08 first frames |
| 4 | M08, M09, M10 | `autosave` (M08) | M11 first frames |
| 5 | M11, R_Finale, main menu | `autosave` (M11) | Main menu, then Exit |
| 6 (optional) | M13 to M11 in one process | New Campaign (Recruit) | Main menu |

Leg 6 is a soak: no edge cases, no stops, only to see whether the heap and
vitaGL residual stay flat over 12 handoffs and whether M08/M09 survive late in
a process. The log will hit the cap; the `[LIFECYCLE] SESSION residual` lines
are exempt from it. The reports give no per-mission play times, so budget
each leg as a whole sitting.

## 3. Log signatures

Grep the pulled runtime log with `grep -nE`. Or run the helper, which cuts the
log into per-mission sessions at each `A4 campaign: original selection` line.

### 3a. Expected in every mission session

| Text (grep) | Meaning | Healthy |
| --- | --- | --- |
| `A4 campaign: original selection source=Mxx.mix archive=Mxx.mix save=0 mix_valid=1` | Level load. `save=1` after loading a save | Once per mission start |
| `A3.5 mission completion: original Combat event observed success=1` | `Mission_Complete(true)` | Once. `success=0` is a failure |
| `A4 campaign: dispatching observed mission success to original CampaignManager` | Success handed to the campaign | After each success |
| `A4 campaign: original intermission frame=N score/movie=1/0` then `.../0/1` | Score screen, then movie | Score then Movie |
| `A3.5 mission ranks: write=1 op=set key=Mxx value=N entries=K` | Rank saved at the score screen | Keys in order `M13 M01 ... M11`, `entries` +1 each |
| `A4 campaign: original intermission latched next source=Mxx.mix` | Next Level latched | Once |
| `A4 campaign: clean session released; entering original next source=Mxx.mix` | Handoff | Once |
| `A4 campaign: restored original CampaignManager chunk bytes=N source=Mxx.mix` | Next session sees campaign state | Once per handoff |
| `A3.5 save write: path=.../user/save/autosave.sav ... success=1` | Level-start autosave | First frame of M01 to M11, not M13 |
| `[LIFECYCLE] SESSION residual index=N frames=F heap arena/in_use/free/free_chunks=... ram/vram/all_free=...` | Heap and vitaGL after teardown | `in_use` and `all_free` flat between consecutive indexes. A rise of 1 MiB or more per handoff is retained state |
| `A3.5 perf: frames=... avg_fps=... frame_us min/p50/p95/p99/max=... backend_errors=N` | Rolling frame stats | `backend_errors=0` |
| `A3.5 mission ranks: load=1 entries=N` | Rank file read at session start | After first rank write |

### 3b. Problems (should be absent)

`[runtime-log] TRUNCATED` (evidence lost after this line),
`A4 campaign: handoff failure`, `A4 campaign: failed handoff`,
`A4 campaign: rejected invalid session handoff`,
`A4 campaign: rejected save campaign/source mismatch`,
`A4 campaign: original mission MIX unavailable`, `A4 load: local failure`,
`[LIFECYCLE] END status=controlled-failure`, `A3.5 mission ranks: write=0`,
`A3.5 save write: ... success=0`, `unsupported-submit`, any `FATAL`/`crash`,
a `psp2core-*.psp2dmp`.

### 3c. Fallbacks and mission signatures

| Text | Where | Reading |
| --- | --- | --- |
| `A4 M01 cinematic command begin: n=N file=X1C_...` / `... command end: n=N` | M01 intro (first 160 X1 commands) | A last `begin` with no `end` names the stalled command |
| `A4 M01 intro phase: frame=N phase=simulation-begin\|render-begin\|audio-begin\|audio-end` | M01 intro (first 120 frames) | Last line names the stalled frame stage |
| `A4 M01 <what> preparation: model=...`, `A4 cinematic animation preparation: archive=M01.mix named=N ... loaded=N memory_floor=0` | M01 load | `loaded` = `named`, `memory_floor=0` |
| `A4 campaign: retail M08 texture fallback mounted archive=M01.mix for lv8_hbag.tga` (also `archive=M04.mix`) | M01 and M04 load | Present. `retail M08.mix unavailable` is a warning |
| `A4 M01 PCT unlock watchdog: EVA chain did not finish; unlocking pen` | M01 | Should be **absent** on a normal run. Present after the save/load edge case below |
| `A4 M01 open-gate objective fallback` | M01 | Absent normally. Present if the Kane-talk callback was lost |
| `A4 M01 Duncan: beacon handoff reason=...` | M01 | Ion beacon handoff happened once |
| `M13 finale: cinematic Send_Custom target=1500017 resolved=1 type=445009`, `M13 finale: area controller received mission-success custom`, `M13 finale: ion-cannon-strike timer fired`, `M13 finale: ion beacon position`, `M13 finale: finale timer fired` | M13 end | All present, in that order |
| `A4 slow campaign cinematic command: file=X2... us=N` | Any cinematic (first 48) | Hitch finder. Look at `X2`, `XG_`, `X0`, `X1`, `X6`, `X8` |
| `A3.8 Raveshaw jump: grounded landing fallback (vz=...)` | M08 boss | Fix fired. At most 4 per run |
| `A3.5 Mendoza death camera: waypath 3000100 unusable` | M06 | Should be **absent** |
| `A4 elevator entry timeout v1: obj=... elevator=... inside=1 action=request_elevator` | M11 (and M02/M08/M10 AI lifts) | Fallback fired and recovered. `inside=0 action=keep_steering` means the rider is still stuck |
| `A4 animation action forced complete: obj=... anim=...` | M09 (obj 2000010 = Mobius), M11 (Sydney) | Any hit is an animation-update bug to report |
| `A4 death: original popup active dialogs=N`, `A4 <owner>: original reload begin map=Mxx.mix`, `A4 replay: ...`, `A4 load: clean session released; entering original source=...` | Death, restart, load, replay | Fail-and-retry trace |
| `A4 campaign: cleared unconsumed autosave request at session end` | Any | Expected only if you paused and quit/loaded on the very first frame |
| `Circle tap latched original crouch key DIK_LCONTROL` | Any | First quick Circle tap latched crouch |
| `A3.6 power: resume observed` | After sleep or LiveArea round trip | Resume seen |
| `A3.5 mission progress: frame=... objectives=N status_1_6=...` | Periodic | Objective status snapshot for objective-only checks |

### 3d. Lines you will NOT find (do not wait for them)

The Vita build does not define `WWDEBUG`, so `Debug_Say` and `WWDEBUG_SAY`
compile to nothing. These are never in the log: `ScriptZone %d swept entry`,
`Unable to create script: ...`, `native provider missing script ...`,
`SCRIPT_PTR_CHECK` null-guard hits. Judge swept zone entry by the **effect**
(the objective appears, the cinematic starts). The M04, M07 and M11 reports
that say to grep for the script-missing lines are wrong for this build; their
absence means nothing.

## 4. Missions

Every mission ends with the same transition checks, listed once here so the
sections stay short.

- **After Mxx success:** `Mission_Complete` line, Score screen (stats look
  like this mission only, difficulty label is the one you picked, a rank
  star count), then the movie `R_Lnn.bik` (picture and sound, skip works),
  then the next level loads with no leftover letterbox, screen tint or slow
  motion. Rank line `key=Mxx` written exactly once. Autosave line on the
  next mission's first frames.

---

### 4.1 M13 (first mission; no autosave)

Prerequisites: leg 1, New Campaign, fresh process. This is the only mission
that does not write an autosave at its start.

Normal route:
- [ ] **N** Intro `X00_Intro` plays with letterbox, then control returns
      (about 75 s of cinematic). No freeze.
- [ ] **N** A02: engineers drop a replacement tank, you enter it, the rubble
      (`Blockage`) blows after "fire in the hole", the path to A03 opens.
- [ ] **N** A03: humvee drop, the `MX0_A03_01` to `_10` conversations, reach
      the A03 end zone.
- [ ] **N** A04 area zones in order (thin plane pairs near x 38-41, 83-86,
      97-100): medium tank, Obelisk cinematic `X0E`, SAMs, A-10 strike `X0D`,
      ion cannon strike, finale `X0Z_Finale` (flash to white, fades).
- [ ] **N** Finale ends (cinematic frame 440), success, Score, `R_L01.bik`, M01.

Edge cases:
- [ ] **E** **A02 fire-in-the-hole race.** As soon as the replacement tank
      appears, run to it and get in at once, before the second engineer has
      walked up. Expected: the rubble still blows about 1 s after he
      registers (new a38 fix). If the rubble never goes, save `M13_a02_stuck`
      and report.
- [ ] **E** **Area-3 reachability probe (not fixed, exploratory).** Stay out
      of the area-3 pair, reach area-3 ground another way, then cross the
      pair backward (1500005 then 1500004). If area-2 timers keep re-arming
      and no Obelisk cinematic starts within about 60 s, you found the
      deferred soft-lock. Save `M13_area3_probe` first; do not rely on it.
- [ ] **E** Sprint across the thin gating zones 1200019, 1400143, 1400004
      (1.7 to 5.1 m) and the A03 end zone 1400069 at full speed. The next
      objective or cinematic must start.
- [ ] **E** Open EVA (START) during the finale cinematic, wait 20 s, resume.
      The cinematic continues from the same point, no burst, no skipped line.
- [ ] **E** **Fail test.** Let Havoc die once (fall or enemy fire).
      `Havoc_Script::Killed` -> failed popup. Pick **Restart**, confirm normal
      speed and that the mission plays on. Use
      D-pad + Cross; a held Cross or Circle must not select anything.
- [ ] **E** Finale presentation (CINEMATIC_PRESENTATION): letterbox bars reach
      all four edges with no sliver, white flash covers the whole frame, the
      fade-to-black ends clear, and M01 starts with no residual bars or tint.
- **S** none required. Optional `M13_prefinale` just before the A10 strike.

G: `M13 finale:` (all five lines), `A3.5 mission completion: ... success=1`,
`A3.5 mission ranks: write=1 op=set key=M13`, `A4 campaign: original
intermission latched next source=M01.mix`, `A4 slow campaign cinematic
command: file=X0` / `MX0`, `[LIFECYCLE] SESSION residual index=1`.

Escalate if: the finale lines stop before `finale timer fired`
(Test_Cinematic never reached frame 440), or Score -> `R_L01` -> M01 does not
advance (the Dev144 Vita3K run did reach R_L01; M01 entry was never seen).

---

### 4.2 M01 (beach, GDI base, Comm Center)

Prerequisites: arrives from the M13 handoff in the same process.
**Known open freeze:** a native freeze during the `X1C_Intro` aircraft
sequence was seen on PSTV (Dev197): it stalls near intro time 1.067 s, where
`X1C_AG_Missile` plays `Missile_Launch_2second`. No fix is claimed. If it
freezes again, leave the device alone for a minute, then pull the log and look
at the last `A4 M01 cinematic command begin` with no `end`, and the last
`A4 M01 intro phase`.

Normal route (fastest deterministic order):
- [ ] **N** Intro reaches control without freezing.
- [ ] **N** Beach to GDI base to Comm Center. **Destroy the Comm Center SAM
      site first.**
- [ ] **N** Enter the Comm Center, poke the PCT (Triangle). Wait for the EVA
      "data acquisition complete" chain (about 8 s) and the unlock objective
      to clear.
- [ ] **N** Wait at least 5 s after the SAM died, then poke the detention pen
      gate (Triangle). Prisoners freed, `M01_OPEN_THE_GATE` accomplished.
      (The old "free prisoners first, then wait 60 s" route is unreachable:
      the gate refuses pokes until 5 s after the SAM dies.)
- [ ] **N** The finale `X1Z_Finale` fades in; success arrives at about 20 s.
- [ ] **N** Score, `R_L02.bik`, M02. Expect no hang during the 20 s.

Edge cases:
- [ ] **E** **PCT save/load watchdog.** Poke the PCT, quicksave within about
      5 s (during the EVA chain), load that save, then do nothing for 40 s.
      Expected: about 30 s after the poke the log prints `A4 M01 PCT unlock
      watchdog` and the pen unlocks. Without the fix the objective would
      stay stuck forever. (Retail-identical soft-lock, now covered.)
- [ ] **E** **"Open the gate" objective.** On a fresh run, kill the SAM first,
      then poke the PCT **while the Kane hologram talk is still playing** in
      the Comm Center. Expected: the "Open the gate" objective appears (via
      the normal callback, or within 30 s with `A4 M01 open-gate objective
      fallback`). It must never stay missing.
- [ ] **E** Save/load around the church and the tailgun commander (before
      leaving the beach): reload, listen for audio anomalies, check the
      tailgun commander and the priest (two duplicate-ID fixes).
- [ ] **E** Save/load near the GDI base artillery and again inside the
      detention pen. After the load the artillery bombs must land in sensible
      places and the pen prisoners must wander normally (two position-table
      fixes). A garbage-position explosion or a prisoner walking to infinity
      is a failure.
- [ ] **E** **Fast-drive the thin zones** with the GDI medium tank (if you
      have it) at full speed: `M01_SniperRifle_02_AirdropZone` (118832, 1.45
      m), the three `M01_Comm_Mainframe_PogZone` zones (108024/26/28), and
      `M01_TriggerZone_GDIBase_BaseCommander` (106267/106268). Each must
      still start its cinematic or objective.
- [ ] **E** Duncan shack: enter the shack zone and get the ion beacon.
      `A4 M01 Duncan:` lines show one handoff only (no double beacon).
- [ ] **E** Pause with START during the finale and during the PCT chain,
      resume. Nothing skips.
- **S** `M01_prePCT` (before poking the PCT), `M01_church` (before the beach
  exit), `M01_pregate` (before the gate).

G: `A4 M01 cinematic command begin/end`, `A4 M01 intro phase`, `A4 M01 ...
preparation`, `A4 cinematic animation preparation: archive=M01.mix`
(`memory_floor=0`, `loaded` = `named`), `A4 campaign: retail M08 texture
fallback mounted archive=M01.mix`, `A4 M01 PCT unlock watchdog`, `A4 M01
open-gate objective fallback`, `A4 M01 Duncan:`, `A4 slow campaign cinematic
command: file=X1`, rank `key=M01`, autosave line for M02.

Ignore (retail-identical, cosmetic): missing `X01_ConYardDrop.txt`, `C_havoc`,
`M01_Nod_HupHup`, `H_A_442A`, `H_A_V11A`, `01-I048E`, two unlocated finale
sounds, and a few oversized WAV headers.

Escalate if: freeze in the intro, the 20 s finale never resolves, the PCT or
gate never unlocks, or a crash after a load.

---

### 4.3 M02 (Nod base, dam, midtro)

Prerequisites: leg 2 starts here from the M02 autosave. Weather is snow 0.3;
the level is primed, so expect a one-off stall on the first frame (the models
put it at tens to over a hundred ms). M02 is the heaviest cinematic mission.

Normal route:
- [ ] **N** `M02_PRIMARY_01_START` plays and objective 201 shows.
- [ ] **N** Clear areas toward the Obelisk and the dam. Watch drop cinematics.
- [ ] **N** Bay door: damage the Dam MCT (1111116) to get key 6 (any damage
      works; it survives at 0.1 health), open the bay door.
- [ ] **N** Midtro zone 400193: `X2K_Midtro` (about 39 s) with letterbox,
      fades and the sniper scope zooming in 21 steps. Afterwards you are on
      the rooftop, 201 done, 205 shown, key 1 granted at about 25 s.
- [ ] **N** Fight Mendoza; enter the end zone 400194 (entering is enough,
      the rope evac is not required). Mission complete, Score, M03.

Edge cases:
- [ ] **E** **Drive fast through objective zones.** Take the buggy, Humvee or
      recon bike and drive straight through at full speed. 23 zones of
      1.4 to 5.5 m gate objectives, cinematics and completion (for example
      401114, 401113, 400273, 400272, 401054, 401123, 401196, 405118,
      400193, 401080, 401101, 401102, 400271, 303203, 401131, 401066,
      400274, 301601, 400270, 400192, 401001, 405117, 405116). Do this
      once in a quiet spot and once in a heavy fight (low fps). If an
      objective does not activate, back up and enter slowly; then note the
      zone and the fps. The swept-entry patch should catch it, but its
      breadcrumb is not logged, so only the objective effect shows it.
- [ ] **E** **Midtro input leak.** During the whole midtro hold the right
      stick fully, press D-pad Up/Down, R trigger, L trigger and Square. The
      camera must not move, the scope zoom must follow the script only, no
      shot is fired, no weapon changes. After the midtro: camera pitch is
      back to normal, FOV is normal, raising the sniper rifle starts at
      the zoom you had before, and the first M03 frames are at normal FOV.
- [ ] **E** Scope look: reticle lines, zoom marker and alpha at 16:9 (the
      scope is stretched to the full screen). Visual judgement only.
- [ ] **E** Enter the end zone 400194 without fighting Mendoza at all. Success
      should fire immediately.
- [ ] **E** Destroy a target (Dam MCT or a tertiary) before crossing its
      activation zone (400269, 400188). The objective may stay pending on the
      HUD and the end screen; that is retail-identical and cosmetic.
- [ ] **E** Quicksave about 10 s into the midtro, load it. The midtro resumes
      and the 25 s keycard still arrives. (Camera/cinematic persistence is a
      shared open item, so a oddity here is worth a note, not a blocker.)
- [ ] **E** Ride a few lifts (M02 has 15 elevator objects: HND_ELEV, DAM_ELEV,
      PWR/OBL/ATR lifts). One ride after a save made mid-ride.
- [ ] **E** Poke the `Level_01_Keycard`-gated doors: confirm the key-1 doors
      open after the 25 s grant, not before.
- **S** `M02_premidtro` (before zone 400193), `M02_predam` (before the bay
  door).

G: `A4 slow campaign cinematic command: file=X2` and `file=XG_` (drop
cinematics), `A3.5 perf` (min fps, p99), `A3.6 frame-profile` (look at the
`Weather` scope), rank `key=M02`, autosave line for M03.

Escalate if: fast pass skips an objective that a slow pass fires, or scope
overlay is missing or garbled, or any input leaks into the midtro.

---

### 4.4 M03 (beach, Nod base, volcano)

Prerequisites: continues from M02 in the same process.

Normal route:
- [ ] **N** The `M03CON039` intro, objectives 1000 and 1001 appear.
- [ ] **N** Beach and shore SAMs, power-up drops, gunboat comes in (protect
      the gunboat).
- [ ] **N** Enter the Nod base; the con-yard zone adds "Access mainframe".
- [ ] **N** **Poke the Comm Center terminal (1100009) first.** M03CON008 plays,
      and, when it ends, Sakura's VTOL ("Boss") appears.
- [ ] **N** Kill Sakura's VTOL. The crash cinematic plays, then the volcano
      (ash, rumble, lava balls every 5 to 7 s), M03CON010, Escape.
- [ ] **N** Destroy the Comm Center (no fail message), follow Escape to exit
      zone 2000817. Success, Score, M04.

Edge cases:
- [ ] **E** **Deliberate fail.** Save `M03_prefail`. Destroy the Comm Center or
      the power plant **before** poking the terminal. A 4 s timer then
      calls failure. Check the Failed popup (Restart / Load / Main Menu),
      Restart works, and a held button does not select.
- [ ] **E** **Keycard objective.** Kill officer 1144682 and take
      `Level_01_Keycard` while M03CON004 is still playing, near the basement
      door zone. Objective 1007 must end up accomplished (it may flash in
      already complete).
- [ ] **E** **West elevator route.** Take the elevator into the Comm Center,
      poke the terminal, then cross the con-yard zone 1144636 heading west.
      "Access mainframe" should appear already accomplished, base entry
      should register.
- [ ] **E** **SAMs early.** Kill both shore SAMs (300058, 300059) from range
      or via the gunboat before entering zone 1100007/1100015. Kill both
      village SAMs before zone 1100006. Objectives 1004 and 1002 must still
      appear and complete (30 s fallback if a key line was playing).
- [ ] **E** Quicksave during the volcano, load, confirm lava balls keep coming
      and ash returns. Quicksave while M03CON008 is playing and load.
- [ ] **E** Beach and inlet reinforcement drops (the paradrop buffer overflow
      fix): play both with no crash.
- [ ] **E** Stand near the Sakura crash: if the volcano and Escape never start
      after Sakura died, save `M03_nocrashcine` (stalled `x3d_sakuracrash`
      frame 356); the exit zone still completes the mission.
- [ ] **E** M03 is the first mission with the large 800x600 TGA texture;
      watch for pop-in.
- **S** `M03_preMCT`, `M03_prevolcano`.

G: rank `key=M03`, `A4 slow campaign cinematic command: file=X3`, `A3.5 mission
progress:` lines (look for an objective entering `status` accomplished the
same frame it is added), `A3.5 perf` through the volcano, autosave line for M04.

Ignore: missing power-up presets, `Explosion_Large_07 ` sound, shotgun/sniper/
mine clip powerups (retail-identical).

Escalate if: Sakura never dies but exit zone also fails to complete, or the
volcano stalls the frame rate under 10 fps.

---

### 4.5 M04 (cargo ship)

Prerequisites: continues from M03. At load expect the M08 texture fallback line.
Weather: rain 5.0 for the entire mission, and a primed first frame.

Normal route:
- [ ] **N** Prisoner objective appears about 3 s after load.
- [ ] **N** Engine room: destroy all four engines; turbine loops stop, klaxon
      and broken-engine loops start, objective 200 completes, power-ups drop.
- [ ] **N** Missile room: sabotage all 4 racks (objective 300). Torpedo room:
      both torpedoes (objective 400).
- [ ] **N** Take the prison key (110) and free the three prisoners (100).
- [ ] **N** Kill the first mate (600) and the captain (700).
- [ ] **N** Sub bay: firefight starts, prisoners gather. Stand in rally zone
      101194 with prisoner 3 on Soldier/Commando. EVA line `00-n048e`, then
      success, Score, M05.

Edge cases:
- [ ] **E** **Torpedo race.** Save `M04_pretorpedo`. Poke **both** torpedoes
      before crossing announce zones 105238/105239, then cross one.
      Objective 400 must appear already accomplished and the rally-zone end
      check must still pass. (Without the a38 fix this was a hard lock.)
- [ ] **E** **Missile briefing drop.** Kill the first mate, collect key 2, then
      enter the missile-room zone about 10 s later while the captain-key line
      is still playing. Racks must be pokable and objective 300 should
      appear about 20 s after entry.
- [ ] **E** Rally zone: walk in before the last objective is done, then
      complete it, then step out and back in. Mission ends only when all
      primaries are done and everyone is inside.
- [ ] **E** Prisoner 3 pathfinding on Soldier/Commando (watch FPS during the
      escort; below about 8 fps the path can rub walls).
- [ ] **E** Engine-room audio load: 51 static loops plus 14 script loops plus
      combat. Listen for dropouts and watch fps.
- [ ] **E** Quicksave during the Big SAM sound sequence and load: the gun
      animation may stall (cosmetic, known).
- [ ] **E** Optional: replay M04 on Recruit from the Load menu: all three
      prisoners are pre-marked, so rally completes without escort.
- **S** `M04_pretorpedo`, `M04_premissile`, `M04_prefirefight`.

G: `A4 campaign: retail M08 texture fallback mounted archive=M04.mix`,
rank `key=M04`, `A3.5 perf` (rain frame cost), `A3.6 frame-profile` (Weather
scope), `A4 replay: ...` if replayed, autosave line for M05.

Escalate if: objective 300/400 never resolves, the end check does not pass
with everything done, or the rally zone ignores prisoner 3.

---

### 4.6 M05 (Dead 6, cathedral)

Prerequisites: continues from M04 in the same leg (leg 3 starts here from the
M05 autosave). If any Dead 6 member (Hotwire, Gunner, Deadeye, Patch) dies the
mission fails by design.

Normal route:
- [ ] **N** `M05_CON001` plays and Mendoza's troop drop (`X5I_TroopDrop7`) lands.
- [ ] **N** Rescue Hotwire (503), Gunner (501), Deadeye (502). Keep them alive.
- [ ] **N** Go to the cathedral, poke Patch (object 100006). `M05_CON014`, music
      change, 504 done, 506 added.
- [ ] **N** Kill the 2 Apaches and 3 artillery pieces (they arrive by transport
      drop and swap at about frame 437).
- [ ] **N** Kill at least 8 Black Hand paratroopers. Remaining enemies die
      (`M05_CATHEDRAL_FREE`), objective 506 completes, success, Score, M06.

Edge cases:
- [ ] **E** **Deadeye during CON004.** Enter the Inn radio zone so `M05_CON004`
      plays, then poke Deadeye while it is still playing. Deadeye must stay
      pokable; a second poke plays CON013 and completes 502. Repeat with
      Gunner while `M05_CON006` plays.
- [ ] **E** **Civilian poke hang.** Poke several resistance civilians near the
      spawners (100104, 100115, 100140, 100227, 100228, 100771, 100772),
      deliberately including any `Civ_Resist_Male_v2b/v2c`. The game must
      never freeze (this was a hard spin loop on the first poke).
- [ ] **E** **Quicksave and reload mid-cathedral** while the Triangle tank or
      the cathedral Apaches are active. They must keep firing at authored
      targets.
- [ ] **E** Cathedral stall: if the count does not finish (a flipped or stuck
      artillery piece), save `M05_stall`, note which vehicle, report.
- [ ] **E** **Fail test.** Save `M05_prefail`. Let a Dead 6 member die. Failed
      popup, Restart, normal speed.
- [ ] **E** Optional ordering: poke Patch before the `M05_CON005` zone plays
      (objective 504 shows pending; cosmetic).
- **S** `M05_preInn`, `M05_precathedral`.

G: rank `key=M05`, `A4 death: original popup active` / `A4 ...: original
reload begin` for the fail test, `A3.5 perf`, autosave line for M06.

Ignore: missing `X5C_Wintroops09/13/19`, `X7B_ApacheStk`, `M05_Inn_Reinforcements`,
`M05_Park_Unit` (retail-identical, optional side waves).

Escalate if: any civilian poke freezes the game, or a mid-battle reload makes
the Apaches or tank stop shooting.

---

### 4.7 M06 (war room, Sydney, Mendoza boss)

Prerequisites: continues from M05. Success is owned by the boss class, not the
script, so objectives never gate it.

Normal route:
- [ ] **N** `M06_CON059` intro plays; when it ends objective 601 "Hack War Room Computer" appears.
- [ ] **N** Hack the war room computer (106952): CON001, `Level_03_Keycard`
      drops, 601 done, 603 added.
- [ ] **N** MidtroB (`X6B_MIDTRO`, about 79 s, custom at frame 2380). Havoc and
      Sydney relocate, 611 "Escort Sydney" appears.
- [ ] **N** Escort Sydney through the collapse zones; MidtroC (`X6C_MIDTRO`)
      triggers; Mendoza spawns, 604 appears.
- [ ] **N** Take Mendoza below 25 % health. Sydney bolts, trips and cowers.
      Keep shooting (1-in-4 chance per hit while she cowers) until the
      face-zoom death camera starts.
- [ ] **N** Wait about 15 s. The death camera runs in slow motion and time
      returns to normal speed. Success, Score, M07.

Edge cases:
- [ ] **E** **Hack at once.** Right after load, poke the war room computer
      before `M06_CON059` finishes. Objective 601 should still appear.
- [ ] **E** **Alarm terminals.** Poke or destroy an alarm terminal before
      entering zone 101055. Objective 609 may stay pending (cosmetic).
- [ ] **E** Free the GDI prisoner (key 3) and see whether MidtroB can be
      reached without hacking. Neither objective nor boss is affected.
- [ ] **E** **Sydney death.** Save `M06_prebattle`. Let Sydney die once:
      611 fails and the Failed popup appears. Pick Restart: the fight restarts
      at normal speed.
- [ ] **E** Boss stall watch: if Sydney or Mendoza stands still for more than
      60 s after you shot him below 25 %, save `M06_bossstall` and report the
      states you see (bolting, tripping, cowering).
- [ ] **E** **Slow-motion carry-over.** During the 15 s death sequence, open
      EVA and choose Load (a previous save). The loaded game must run at
      normal speed.
- [ ] **E** Suspend/resume (PS button to LiveArea and back) during the death
      camera. The camera path should not be skipped. Note what you see; this
      is an unpatched hazard (boss timers use real time).
- [ ] **E** Collapse zones: 4 of the 9 never arm (cosmetic). Do not report
      missing rubble.
- **S** `M06_prehack`, `M06_prebattle`.

G: `A3.5 Mendoza death camera: waypath 3000100 unusable` (must be absent),
rank `key=M06`, `A4 death:`/`A4 ...: original reload begin` (Sydney test),
`A4 slow campaign cinematic command: file=X6`, autosave line for M07.

Escalate if: the death camera does not start, mission complete does not fire
after it, or the next mission starts in slow motion.

---

### 4.8 M07 (nuke, SAMs, inn evacuation, park)

Prerequisites: continues from M06. This mission has a real countdown.

Normal route:
- [ ] **N** `M07_CON001` plays. Objectives 709, 701 and 710 appear. A nuke
      countdown of about 2 minutes starts.
- [ ] **N** Leave the blast radius before impact. Havoc must not be flagged in
      the blast. Nuke cinematic, ash, objective 710 done.
- [ ] **N** Hotwire captures the SAMs with you nearby; then the inn evacuation
      (Sydney2 plus three Dead 6 units climb out). `M07_CON017` adds 703.
- [ ] **N** Optional vehicle drop at `M07_Activate_Present`.
- [ ] **N** Destroy both park SSM launchers (100796, 100798). About 5 s later
      success, Score, M08.

Edge cases:
- [ ] **E** **Nuke fail.** Save `M07_prenuke` right after `M07_CON001` ends.
      Stay in the blast. Expect failure (710 fails), Failed popup, Restart.
- [ ] **E** **Hotwire SAM capture during a key line.** Bring Hotwire to the SAM
      approach zone (100684) at a moment when a key conversation is playing,
      for example a blast-zone line (`M07_CON013/014`) or an objective-zone
      line (`M07_CON018` to `022`). You stay nearby, since you trigger
      `M07_Move_Hotwire` in that zone. About 15 s later Hotwire must still go
      and capture the SAMs. If Hotwire stands idle for 30 s, save
      `M07_hotwire_idle` and report.
- [ ] **E** **Rope climb save.** Quicksave while an evacuee is on the rope, load.
      Hotwire must not stay attached to the rope; if the
      `M07_Hotwire_Dead` zone fails the mission, note it.
- [ ] **E** Five evacuations all proceed (the buffer-overflow fix). If the
      count stops at four, save `M07_evac4`.
- [ ] **E** Fast pass through the thin cinematic zones 101131 (0.7 m), 100756
      (1.72 m), 101151 (3.09 m) in a vehicle.
- [ ] **E** Audio: `Raveshaw_Act on Instinct` plays when expected (the name has
      no extension).
- [ ] **E** SSM repair AI: engineers may repair the launchers and delay the
      kills; that is design.
- [ ] **E** Suspend/resume during the countdown: the countdown does not jump.
- **S** `M07_prenuke`, `M07_preevac`, `M07_prepark`.

G: rank `key=M07`, `A3.6 power: resume observed`, `A4 death:` for the nuke
fail, `A3.5 perf` (ash cost), autosave line for M08.

Ignore: `Ramjet_Weapon_Powerup`, `M07_Activate_V01` (100952), `Set_Wind` rejection.

Escalate if: nuke timing differs wildly from 2 minutes, or Hotwire idles.

---

### 4.9 M08 (Petra, research facility, Raveshaw)

Prerequisites: continues from M07, or leg 4 starts here from the M08 autosave.
This is the high memory band: 217 TGA textures (about 53 MiB GPU plus 27 MiB
CPU copies) against a 48 MiB prepare budget. At load expect the load to take
visibly longer and textures to arrive lazily.

Normal route:
- [ ] **N** Start with a pistol only; objective 801; `08-Sniper.mp3`.
- [ ] **N** Take the warden's Level 2 keycard, leave the prison, enter the 802
      zone (`M08_CON001`).
- [ ] **N** Cross Petra canyon (Apache waves and the Sakura escort are optional)
      and enter the research facility (803 zone, `M08_CON002`).
- [ ] **N** Take the elevator into zone 1500225. `X8A_MIDTRO` plays to its fade.
      Havoc relocates, 803 done, 805 added, `Raveshaw_Act on Instinct.mp3`.
- [ ] **N** Fight Raveshaw until he collapses from the catwalk circle. About
      2 s after landing: success, Score, M09.

Edge cases:
- [ ] **E** **Boss jump landing.** Provoke jumps: jump down from the catwalk,
      and stand where he jumps to you. If he ever stands still after a jump
      for more than 15 s, the fix should have unstuck him within a frame or
      two; the log shows `A3.8 Raveshaw jump: grounded landing fallback`.
      A frozen boss with no such line means the fix is not enough: save
      `M08_bossfrozen`.
- [ ] **E** Quicksave **before** the midtro and **inside** the arena; reload
      both. A save made mid-midtro must still relocate Havoc at frame 1940.
- [ ] **E** Open EVA during `X8A_MIDTRO`, wait, resume. Nothing skips.
- [ ] **E** Stay 2 to 8 m from Raveshaw but out of reach (above him). He keeps
      chasing (retail-identical); move away more than 8 m or down to him and
      the fight resumes.
- [ ] **E** **Stealth tank** (Nod stealth tank, player and hostile): look at
      a hostile one inside and outside 25 m. Screenshot it. `unsupported-submit`
      must be absent from the log.
- [ ] **E** Optional, crash hunt: destroy the `(Raveshaw Ammo)` object he is
      walking to or holding (a use-after-free candidate; it is not known
      whether the object can be destroyed). If the game crashes, keep the dump.
- [ ] **E** Memory and pop-in: record fps in canyon and arena; watch for
      missing textures.
- **S** `M08_premidtro`, `M08_prearena`.

G: `A3.8 Raveshaw jump: grounded landing fallback`, `A3.5 perf` (fps,
`backend_errors`), `[LIFECYCLE] SESSION residual` around M08, rank
`key=M08`, `A4 slow campaign cinematic command: file=X8`, `unsupported-submit`
(must be absent), autosave line for M09.

Ignore: missing `X8I_TroopDrop*`, `H_A_X8A_MLoop`, `M08_Sakura` second move.

Escalate if: Raveshaw freezes, a crash in the arena, or heavy texture
corruption.

---

### 4.10 M09 (Mobius, lab, suit, surface)

Prerequisites: continues from M08. Weather is the densest in the campaign
(rain 10.0 in two zone pairs, about 6,500 particles, about 7 ms per frame on
a 33 ms budget by the model). Closure textures: 40 MiB of the 48 MiB budget.
Check the visual:
the lab geometry `LAB_VIZ_10/11` must be visible (that mesh exists only in
the M09 copy of `res_vis.w3d`).

Normal route:
- [ ] **N** About 5 s after load, `D07` then `P01` play. Objectives 900 and 901
      appear. Mobius starts following.
- [ ] **N** Escort Mobius through the lab, scripted lifts and the key-10 doors
      to the suit zone 2000612. `X9C_MIDTRO` plays, 901 done, 902 added.
- [ ] **N** Surface zones 2000614/2000954: 902 done, 903 added, flyover.
- [ ] **N** Havoc and Mobius both inside the evac zone 1202054. After 1 s success,
      Score, M10.

Edge cases:
- [ ] **E** **Run from Mobius at the start.** In the first minute of `D07`/`P01`
      walk far away from his starting point. If the conversation is cut by
      distance, objective 901 and Mobius following must still start about
      1 s later (a38 fix); no line `A4 ...` is written for it.
- [ ] **E** **Keycard door.** At the keycard door zone 2000458, enter ahead of
      Mobius and wait at least 2 s. The door check must still happen when
      both keycards are collected.
- [ ] **E** **Lifts.** Ride every scripted lift with Mobius. Try to leave him
      behind on a one-way lift (1265150, 1265149, 1265126). If Mobius is
      stranded, save `M09_mobius_stuck`: nothing recovers him.
- [ ] **E** Run ahead 25 m or more after the `NO_FOLLOW` zone 1100238. Walk back
      through the last Goto zone; Mobius should recover.
- [ ] **E** Enter the evac zone alone, wait for Mobius, step out and back in.
- [ ] **E** **Fail test.** Save `M09_prefail`. Let Mobius die: failure popup,
      Restart.
- [ ] **E** Weather: stand in rain 10.0 on open ground and in a roofed spot.
      Compare fps. Walk in and out of the weather zones several times.
- [ ] **E** Quicksave mid-escort and load. Mobius still follows.
- [ ] **E** `res_vis.w3d` visual check as above.
- **S** `M09_prelift`, `M09_presuit`, `M09_preevac`.

G: rank `key=M09`, `A4 animation action forced complete: obj=2000010` (any
hit is a bug), `A4 slow campaign cinematic command: file=X9`, `A3.5 perf`,
`A3.6 frame-profile` (Weather scope), no `original mission MIX unavailable`,
autosave line for M10.

Escalate if: Mobius stuck anywhere, objective 901 never appears, evac zone
never completes with both inside.

---

### 4.11 M10 (Nod base, gates, ion cannon)

Prerequisites: continues from M09. Seven primaries are counted by *sends*, not
by distinct objectives: 1001 Power Plant, 1002 Con Yard, 1004 Comm Center,
1005 SE gate, 1006 NE gate, 1007 NW gate, 1012 Level-1 key. 1003 is the
beacon and only arrives last.

Normal route:
- [ ] **N** Objective 1003 appears about 0.5 s in; `M10CON064` plays.
- [ ] **N** Kill the Refinery key carrier (2000890), pick up the Level-1 key (1012).
- [ ] **N** Use the key on the SE, NW and NE gate consoles. SE: `M10CON002`
      then 1005. NW and NE complete on the poke itself.
- [ ] **N** Destroy the Power Plant (`M10CON014` -> 1001), Comm Center
      (`M10CON011` -> 1004) and Con Yard (`M10CON005` -> 1002); let each
      follow-up line finish.
- [ ] **N** On the seventh primary `M10CON019` plays and the GDI drop cinematic
      `X10I_GDI_Drop_PowerUp` creates the Ion Cannon beacon powerup. Pick it
      up. About 5 s later success, Score, M11.

Edge cases (this is the one the audits are most nervous about):
- [ ] **E** **Poke the SE gate during a key conversation.** Get the Level-1 key
      first. Then stand where a key line is playing (right after load
      `M10CON064`, or a zone briefing such as `M10CON004` Con Yard, `010`
      Comm Center or `015` Power Plant) and poke the SE console with the key.
      Expected: 1005 completes **on the poke**, no `M10CON002` line plays.
      Before the fix 1005 was lost for good.
- [ ] **E** **Building kill during a key briefing.** Destroy a building while
      the key briefing for the same target is playing: Power Plant during
      `M10CON015`, Comm Center during `M10CON010`, Con Yard during `M10CON004`.
      The primary (1001, 1004, 1002) must still count at once, with no
      follow-up line. Do this for at least one building and tell me which.
- [ ] **E** Normal order on the other two buildings, so both paths are seen.
- [ ] **E** **Save mid-conversation.** Kill a building, quicksave while its
      follow-up line plays, load. The objective must arrive when the line
      ends. Make this with `script-coverage.flag` on.
- [ ] **E** Count: after six primaries nothing happens; the seventh triggers
      the cinematic. Duplicate sends (for example poking a gate twice) can
      over-count, which only fires early, never blocks.
- [ ] **E** Pick up the beacon with full beacon ammo: it must still grant.
- [ ] **E** Stealth-tank drops and the cargo-plane drop zone (1100161) and
      `DME_Cinematic_Zone` (1110056): drive through at full speed in the
      Mammoth tank. Look at stealth visuals and fps.
- [ ] **E** Mammoth tank and MRLS vehicles: enter and exit repeatedly.
- [ ] **E** Ride the elevators (16 ElevatorPhys in M10), one after a save
      made mid-ride.
- **S** `M10_pregate`, `M10_prebuildings`, `M10_pre7th`.

G: rank `key=M10`, with the telemetry flag: conversation monitor and
observer records for actions 100014, 100005, 100011, 100002 (monitor record
first with `action_id=0`, then `transition end` with reason `INTERRUPTED`,
then the kind-3 observer call, then the objective, all in one frame on the
preempted path). Also `Text_File_Open` of `X10I_GDI_Drop_PowerUp.txt`,
`A4 slow campaign cinematic command: file=X10`, autosave line for M11.

Ignore: missing `X10A_Apache_0x`/`X10A_Trnspt_0x` flyovers, `M03CON068`,
`v_GDI_trnspt` animation (retail-identical).

Escalate if: any primary fails to count, the beacon never appears, or the 5 s
timer never fires.

---

### 4.12 M11 (final mission: Petrova, Sydney, nuke, silo)

Prerequisites: continues from M10, or leg 5 starts here from the M11
autosave. Last mission: Score, `R_Finale.BIK`, main menu follow.

Normal route:
- [ ] **N** Intro conversations; objectives 1 and 2.
- [ ] **N** Museum (1 done), power-core entry conversation (3 added), power
      core (3 done).
- [ ] **N** Kill Petrova: `Level_03_Keycard` drops and opens the route. Real
      Sydney appears after the keycard through `X11N_MIDTRO` (frame 494).
- [ ] **N** Initial Sydney conversation ends: 2 done, 4 "protect Sydney" added.
      She walks waypaths, rally zones and elevators.
- [ ] **N** EVA nuke conversation adds objective 5 with the switch marker.
- [ ] **N** Keep Sydney alive to the missile switch. Her console attack, then
      `M11_End_Mission_Conversation`, then the `H_A_CON2` animation, then
      success.
- [ ] **N** Score, `R_Finale.BIK`, main menu (see 4.13).

Edge cases:
- [ ] **E** **Silo top zone.** After Sydney has gone past elevator 2, drop back
      to silo level 2 and walk into the top zone `M11_Silo_ElevatorZone01_Top`
      (100705) again. Sydney must keep going to the missile switch and must
      not walk back down (a38 route-monotonic fix). If she turns back, save
      `M11_sydney_rewind`.
- [ ] **E** **Cryo cages.** Kill caged mutants with one hit (explosive
      weapon). No hang and no stack-overflow crash (a38 recursion bound).
- [ ] **E** **End conversation preempted.** If geometry allows, be inside
      Seth's or Kane's room zone (101103, or the `KanesRoom` zone) as Sydney
      finishes the console animation. The end conversation must replay about
      2 s later and the mission must complete. This is hard to time; skip it
      if you cannot reach the zone.
- [ ] **E** **Rally zones.** Stand inside a rally zone before Sydney arrives;
      nothing happens until you step out and back in. This is original.
- [ ] **E** **Escort and lifts.** Watch Sydney at every lift leg (`WAR_ELEV01`,
      `L11_ELVMUT` x2, the silo lifts). `A4 elevator entry timeout` with
      `inside=1` means the fallback rescued her. If she stands at a lift
      for more than 30 s, save `M11_sydney_lift` and report.
- [ ] **E** **Sydney or end switch dies.** Save `M11_prefail`. Let Sydney die:
      failure. Also destroy the end switch: failure.
- [ ] **E** Petrova's stealth reinforcements: stealth visuals and fps.
- [ ] **E** Quicksave mid-escort and mid-lift, load.
- [ ] **E** Sydney animation watchdog: `A4 animation action forced complete`
      with Sydney's object ID means her console animation stalled for 5 s and
      was forced. Report any hit.
- **S** `M11_prePetrova`, `M11_preescort`, `M11_preswitch`, `M11_prefail`.

G: `A3.5 mission completion: ... success=1` then the flight-recorder
conversation record for `M11_End_Mission_Conversation` with reason ENDED,
`A4 elevator entry timeout v1`, `A4 animation action forced complete`,
rank `key=M11`, `A4 campaign: original intermission frame` showing `score/movie`
for the finale movie.

Ignore: `M11_ObeliskWall_FodderGuy*` and `M11_TempleRoof_FodderGuy02` scripts
(retail-identical misses), `X11C_BN_Sydney` bone animation, Petrova taunt
`M00GCTK_KIOV0004I1MBPT_SND`.

Escalate if: Sydney stalls anywhere, the end conversation never plays, or the
finale movie does not start.

---

### 4.13 R_Finale, main menu, end of campaign

- [ ] **N** Score screen, then `R_Finale.BIK`. Video and audio play; skip with
      START or Cross works. (Movies R_L02 to R_L11 and R_Finale have only been
      shown to exist; decode on a physical Vita is unverified.)
- [ ] **N** After the movie the main menu appears (no credits step; credits are
      under the main menu).
- [ ] **N** The Load menu lists the completed missions with ranks. Count 12.
- [ ] **E** Replay one completed mission on a different difficulty from the Load
      menu. `A4 replay: original CampaignManager started source=Mxx.mix
      difficulty=N`. Score label matches.
- [ ] **E** From the main menu choose **New Campaign** once (it should start
      M13 again) and back out; then Exit. The process must exit cleanly to
      LiveArea, no hang.
- [ ] **E** Relaunch and check `A3.5 mission ranks: load=1 entries=12`.
- [ ] **E** Check `user/config/mission-ranks-v1.cfg` has 12 entries (send it).

G: all twelve `A3.5 mission ranks: write=1 op=set key=...` lines in order,
`A4 replay: ...`, `[LIFECYCLE] END status=...`.

---

## 5. Cross-cutting checks (do while playing, no separate session)

Controls (`VITA_CONTROLS.md`):
- [ ] Left stick movement, right stick look, vehicle drive and turret aim.
- [ ] Circle quick tap latches crouch; tap again, Triangle or a menu releases
      it. Beacons do not arm while crouched, so release first. Rear touch
      toggles first/third person by accident; note if it happens.
- [ ] Select + Square is awkward with one thumb; use EVA > Save when it hurts.
- [ ] Death popup: D-pad + Cross only, a held button does not select, Circle
      quits the death popup with no confirmation (original; note if you hit it).

Low fps and tunnelling (`SCRIPT_ZONE_TUNNELLING`, `CINEMATIC_LOW_FPS`):
- [ ] In the heaviest scenes (M02 fights, M04 rain, M09 rain, M08 canyon) cross
      a gating zone at speed and see if it fires. Report the mission, zone and fps.
- [ ] Open EVA during one cinematic per mission that has one; nothing skips or
      bursts after resume. `A3.6 power: resume observed` after a LiveArea trip.

Escort and elevators (`ESCORT_ROBUSTNESS`, `ELEVATORS`):
- [ ] Lifts in M01, M02, M04, M08, M10 and M11: a rider must not fall through
      or be left behind. Rides during fast play and once after a save made mid-ride.
- [ ] Frame rate never drops under about 10 fps during Mobius (M09) and
      Sydney (M11) legs; below about 8 fps path clipping gets worse.

Weather and perf (`WEATHER_BY_MISSION`): M02 snow, M04 rain, M09 rain 10.0 are
the only measurable weather costs; use `A3.5 perf` and the `Weather` scope in
`A3.6 frame-profile`. M07 ash 0.15 is trivial.

Stealth (`STEALTH_RENDERING`): M07 park, M08, M09, M10, M11 Petrova. A hostile
fully cloaked unit beyond its fade distance is invisible by design (15 m soldier,
25 m vehicle). The danger is the opposite: an enemy you can never see even
when adjacent. Screenshot one inside and one outside fade distance.

Late-process save (`SCRIPT_TIMER_LOW_FPS` engine fix): make a quicksave late in
a long leg (at least 30 minutes uptime), exit the app, relaunch and load it.
Soldiers must act normally. Before the fix, face actions could hold for
as long as the uptime difference.

Fail and retry (`FAIL_AND_RETRY_FLOW`): across the run kill the player once on
foot and once in a vehicle, each with a different choice: Restart, Load,
Main Menu. Restart is at normal speed. Quit reaches the main menu. Loading a
different save from the popup works. Look for `A4 death: original popup
active` and `A4 ...: original reload begin`.

Objective and HUD state (`OBJECTIVE_STATE_LIFECYCLE`):
- [ ] Cycle objective markers with Select until the last pog, complete that
      objective, and confirm the arrow moves to the first remaining one (M05
      to M10). Then die with the pog index above 0 and Restart; no crash.
- [ ] Reveal an encyclopedia entry, quicksave at once, relaunch, load. The
      entry is still in the EVA encyclopedia.
- [ ] After "load a save, then die, then Restart" the encyclopedia and
      weapons reset (original behaviour, F3 pending a decision). Note it.

Autosave chain (`AUTOSAVE_CHAIN`): every handoff writes `autosave.sav` on the
first gameplay frame; a Restart after loading an autosave comes back without
the carried weapons (original). Loading the autosave from the Load menu
resumes at the right mission with the carried inventory.

Memory (`SESSION_CHAIN_ACCUMULATION`): table of `[LIFECYCLE] SESSION residual`
lines per leg. `in_use` and `all_free` should be flat. Report any step of 1
MiB or more, and where it happens.

Pause and quit hygiene: START opens EVA (not a stall). Quit from EVA reaches
the main menu; Exit from there returns to LiveArea. Any hang gets a screenshot
and `psp2core-*.psp2dmp` if one was written.

## 6. What to send back

After **each** leg, before relaunching:

1. `ux0:data/renegade/user/logs/<candidate>-runtime.log` (it is overwritten by
   the next launch). Also `<candidate>-startup-precache.txt` from the same folder.
2. `ux0:data/renegade/user/captures/` (the whole folder): the flight-recorder
   bundle `campaign-flight-summary.json`, `campaign-flight-frames.csv`,
   `campaign-flight-events.jsonl`, `campaign-flight-log-tail.txt`, plus any
   screenshots or captures.
3. `ux0:data/renegade/user/save/`: `autosave.sav`, `quicksaveA.sav`,
   `quicksaveB.sav` and every named save from the **S** steps. Name them by
   mission.
4. Any `psp2core-*.psp2dmp` (wherever the Vita wrote it, typically under
   `ux0:data/`), together with the exact time of the crash and the mission.
5. After the last leg: `ux0:data/renegade/user/config/mission-ranks-v1.cfg`.

With the logs, write down in a few lines per mission:
- candidate name, difficulty, mission, how long the leg took;
- which **E** steps you did and what you saw (pass, fail, could not reach);
- every freeze, crash, missing sound, missing texture, wrong colour or HUD
  glitch with the approximate place;
- screenshots for stealth units, the sniper scope, bars and fades, and the
  M09 lab geometry.

Do not send retail game files (`Data/`). Saves are fine. No credentials or
unrelated files.

On return, `tools/extract_campaign_log_signatures.py` is run over each log and
the legs are analysed in order. Anything marked "Escalate" above is the first
thing to look at.
