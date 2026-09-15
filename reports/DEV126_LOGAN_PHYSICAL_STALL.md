# Dev126 physical Logan progression investigation

Latest physical user return: intro remains below 5 FPS and intro audio is absent.
The presentation-progress guard does not meet physical movie acceptance.
Retrieve Dev126 native pipeline/send/receive/draw and audio output statistics
before further performance changes. Logan gate outcome remains pending.

Dev124 physically boots and reaches M00. User reports controls lock waiting for
Logan after the first gate while NPCs continue moving. Runtime SHA-256
d4277150b7152f0429374434ec43116be01c03f52ad37631fe14e8bc4db3c7bd,
retained in build/device-evidence/dev124-boot-20260914T202219Z/.

POKE conversation completes and enables controls at frame 1342. At frame 1578
controls disable at player (-37.624,-18.941,0.528), with no active conversation.
Player remains stationary through frame 2160 while simulation advances. This
supports an original movement/callback wait, not a globally frozen application.
Mission00 course-exit trigger requests Logan waypath 400074/action COURSE_DONE;
its callback starts the conversation that eventually restores controls. This
route uses original authored waypoints, not the dynamic path solver restored in
Dev118. Exact internal failure remains unmeasured.

Dev126 adds bounded native diagnostics for original actor 400005: action request
acceptance, callbacks, and sampled Goto state/position/path remainder. No forced
control enable, teleport, script completion, timing change or waypoint mutation.
It includes Dev125's tested movie presentation-progress guard and stage timings.
Physical Dev124 also confirms movie drop starvation (4 uploads then >=180 drops).
No Dev126 mission fix or physical acceptance is claimed.

135 focused checks and ARM/package/identity closure pass in
build/dev126-fast-console.log. Original remaining-path getter inspected as
read-only; diagnostics do not evaluate/advance a path. Ordered patch inventory
has 168 entries, SHA-256
fac2fec8ebad414cdcc8184dd6fe8767bfa7d2e4cd9fb6f25ee12d05c9dfb28d.

SELF: 75bdae5d5d6bd837e3e8670a9481392a2d9c5cf0b15bffc489a48daf72dc1935
ELF: b7c3703c6e8afd541840798601411282cf370ae03714642121fe26e81541e801
VPK: 1d5898fc6c20734ee8636e1d5c20b672d51a9dfa0ff85730093eabdcf97c89fb

Deployed with candidate readback and predecessor backup verified; receipt
build/device-evidence/dev126-logan-20260914T203526Z/deployment.json.
Remote launch unavailable. User physical gate repeat is the next required evidence.
Dev124 complete first intro: 230 decoded frames, 4 uploaded, 226 dropped over
18.355 seconds. Movie guard physical improvement remains unmeasured.
