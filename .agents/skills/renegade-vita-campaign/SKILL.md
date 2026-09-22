---
name: renegade-vita-campaign
description: Implement the complete original Renegade single-player campaign on native PS Vita, including mission scripts, progression, saves, and verified gameplay.
---

# Renegade Vita Campaign

Implement the complete campaign from New Game through the ending using the original Renegade source and existing Vita demo. Prioritize playable progress, shared fixes, and rapid verification.

## Execution contract

Start implementing after the minimum useful inspection.

Preserve and extend the working demo.

Reuse original gameplay code and existing Vita adaptations.

Complete substantial, coherent milestones.

Continue beyond successful compilation, first rendering, or one playable mission.

Resolve routine engineering decisions independently.

Honor repository instructions and existing permissions.

Ask only when missing access or genuinely ambiguous requirements prevent progress.

Never claim hardware verification without hardware evidence.

For a narrowly scoped user request, respect its scope while preserving campaign compatibility.

## Establish the actual baseline

Inspect repository instructions, current changes, build scripts, source revisions, demo adaptations, dependency versions, available logs, and supported game data.

Determine which original runtime components are actually compiled and linked into the Vita executable. Source existing on disk does not establish runtime integration.

Reproduce the current build. Preserve a known-good artifact and identify one repeatable runtime scenario. Separate environment, packaging, asset, and gameplay failures.

Discover the graphics backend and platform interfaces in use. Do not replace working infrastructure based on assumptions.

## Connect the original campaign runtime

Trace:

New Game -> engine initialization -> asset/preset loading -> script and object registration -> mission initialization -> update/event dispatch -> objectives -> mission completion -> cleanup -> next mission -> ending.

Find missing compilation units, disabled systems, stubs, stripped registrations, and demo shortcuts. Fix shared causes before adding isolated mission workarounds.

Connect all required systems:

Player input, camera, movement, collision, ladders, and interactions.

Physics, animation, weapons, inventory, damage, death, and recovery.

NPC spawning, navigation, AI, combat, and vehicles.

Script timers, custom events, zones, objective prerequisites, and completion callbacks.

HUD, text, menus, mission information, and audio.

Save/load, persistent campaign state, and level transitions.

Tutorial and final ending flow where present in the original campaign.

Derive mission identifiers, ordering, and requirements from source and game data. Do not invent them.

A map rendering is not a functioning mission. Required objectives must work through normal gameplay and transition correctly.

Never silently stub essential behavior, disable required AI, or force objective success. Keep diagnostic mission selection and cheats separate from normal play.

Temporary reductions to nonessential presentation are acceptable when documented. Skipped cinematics must preserve completion callbacks, player-control restoration, and progression. Preserve mission-critical information through a usable alternative.

## Apply Vita and ARM expertise at the right boundaries

Let the compiler translate ordinary C/C++ into ARM code. Investigate actual incompatibilities:

Win32 semantics and Microsoft compiler extensions.

x86 assembly/intrinsics and calling conventions.

ARM/Thumb interworking and floating-point ABI consistency.

Alignment, packing, aliasing, pointer conversions, and serialized layouts.

Threading, synchronization, timers, and resource lifetime.

Filesystem roots, case sensitivity, seeking, and asset lookup.

Preserve serialized formats using explicit handling and appropriate layout checks. Do not globally pack structures or enable aggressive compiler flags to conceal defects.

For rendering failures, follow the existing W3D asset/prototype -> render object -> scene/camera -> mesh/material -> graphics backend path.

Inspect transforms, projection/depth conventions, winding, vertex layout, index width, buffer lifetime, texture formats, blend state, and skinning where symptoms point. Fix the failing interface before considering a renderer replacement.

Use the checked-out dependency source and headers as authoritative for API behavior. Study relevant VitaSDK examples, vitaGL implementations when applicable, ARM documentation, and successful public Vita port patches to resolve specific blockers. Record the useful implementation, assumptions, and local verification.

Distinguish Android ARM binary wrappers from native source ports. Apply techniques only when their execution model and interfaces match. Preserve attribution and license requirements.

## Use a fast build-run-diagnose loop

Use existing build and packaging commands. Inspect VitaDevBridge before assuming its capabilities. Automate authorized deployment, launch, logging, and evidence collection where supported.

For each blocker:

Reproduce it.

Isolate the responsible interface.

Form a testable explanation.

Implement a focused fix.

Verify the relevant behavior.

Keep or revert based on evidence.

Make startup and runtime failures persistent and actionable. Log failing stages, assets, identifiers, and relevant callbacks without flooding output.

Validate data requirements against actual supported files. Distinguish the original PC demo, retail data editions, and our Vita demo. Never invent expected hashes.

If hardware is unavailable, continue useful source integration, host tests, builds, and packaging. Clearly mark runtime behavior unverified. Do not stop all development merely because device testing is temporarily blocked.

Protect user saves; use isolated diagnostic saves.

## Validate progression and persistence

Maintain a compact mission table:

Mission ID | Initialization | Required gameplay/objectives | Normal transition | Save/load | Build/evidence

Use explicit states: unverified, implemented but untested, passed, or failed.

Use diagnostic mission entry points for breadth, then verify ordinary transitions for continuity. Independent map loading does not prove campaign progression.

For transition failures, inspect pending events, timers, observers, references to destroyed objects, physics state, audio/graphics resources, and global mission state.

For save/load, verify object reconstruction, factory registration, reference fixups, script state, objectives, inventory, timers, and post-load initialization. Parsing a save successfully is insufficient.

Check repeated transitions for stale state, leaked resources, and growing memory use.

## Optimize actual blockers

For campaign intro performance, distinguish original simulation clock from
real audio time and measure the longest frame as well as percentiles. Use the
M00 tutorial and M13 intro as repeatable short/heavy routes. The Dev147
Vita3K comparison found original global dependency preloading can create a
late multi-second hitch; never enable it based only on startup improvement.
The renderer's established 4x MSAA stays the default unless a fixed-route
physical A/B shows a safe gain. See `reports/PERFORMANCE_HYPOTHESIS_LEDGER.md`.

Measure before optimizing. Separate simulation, rendering submission, GPU execution, synchronization, loading, and memory pressure. Do not describe graphics-call CPU time as GPU time.

Prioritize correctness and campaign coverage unless performance or memory prevents practical play.

Optimize demonstrated bottlenecks such as redundant state changes, draw submissions, visibility, texture residency/uploads, allocation churn, animation, physics, or loading stalls.

Avoid speculative multithreading, assembly rewrites, global fast-math, or broad architecture changes. Verify behavior and performance after changes.

## Preserve progress and deliver

Maintain concise project notes containing:

Exact build/run commands and supported assets.

Current source/build identifiers.

Working features and confirmed failures.

Mission verification status.

Reusable fixes with cause, limitations, and evidence.

Next executable steps.

Report what changed, what works, evidence, and the next blocker. Produce playable build artifacts when possible.

Distinguish compilation, packaging, launch, rendering, gameplay, and campaign verification. Claim full functional campaign completion only after normal New Game-to-ending progression and required gameplay are verified. Report presentation omissions and performance limitations separately.

Do not publish releases or distribute game assets without authorization.
