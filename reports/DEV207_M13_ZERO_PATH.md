# Dev207 M13 zero-distance AI path

Dev206's Vita3K reload of the user-owned M13 `savegame05.sav` completed the
original load/post-load path and advanced gameplay, but both GDI engineers
acquired NaN positions within the first few hundred frames. Dev206's
zero-distance jump guard did not prevent this. No Campaign-first or M01
hardware pass is inferred from that run.

An isolated copy of the unchanged save (SHA-256
`f63495330797522cd84973cbc26606c99637cfdb7fc6c6517bcc732bc17054c1`)
reproduced the first invalid engineer at host simulation frame 321. Narrow
host-only traps showed finite physics state and frame time, then a NaN AI
controller vector. The original `PathClass::Evaluate_Next_Point` was handed a
saved route with identical start/destination, zero total distance, no path
actions, and infinite look-ahead time. Its spline evaluation produced the
invalid target. The source patch completes coincident-node paths directly;
pending authored path actions remain dispatched through the original action
state. No movement or objective is forged.

The private-save host replay now requires both engineers to exist and have
finite position/velocity on every frame. Two ASan-enabled 600-frame cycles
passed, with both engineers present at frame 600. A direct zero-length
`PathClass` contract passed in both cycles. A separate original M01 save
(`savegame04.sav`, isolated copy SHA-256
`5cbce6ca544f4b50852b843bbfd2840fc3a797915d04c9302359f9ad93edc072`)
and the M01 smoke each completed two 1,800-frame host cycles. These host
paths do not reproduce or clear the Vita3K/physical M01 intro freeze.

The focused contracts and ARMv7 compile/link passed; Dev207 ELF SHA-256 is
`187cfec06117cd0549a8fbb3df387bc5f90908bbb25fe650b84bb6630f95db9d`.
Dev207 VPK SHA-256 is
`17712335a08305af3f49c364ba99c3e6d82c6a3343d18882663e757fdf4b3e08`.
Package inventory and Vita3K title-scoped install/readback passed; receipt:
`build/vita3k-backups/A3.5-dev207-setup-20260927T170429734890Z/setup-receipt.json`.
The user authorized replacing the Dev206 Vita3K session after its log was
preserved. Dev207 has not been launched or physically tested.

LeakSanitizer still reports 40,872 bytes in 34 allocations after two M13
save-replay cycles, including saved GotoAction paths and a loaded animation.
That lifecycle leak is not attributed to the zero-distance guard and remains
open. A longer M13 host intro replay reached an unsupported host-only sorting
renderer call, so it is not an intro pass. Next: inspect saved-action
ownership/level teardown, verify engineer behavior in a Dev207 runtime run,
and isolate the M01 native freeze separately.
