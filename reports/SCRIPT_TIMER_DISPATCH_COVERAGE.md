# Original timer and custom-event dispatch

Original Start_Timer stores the observer's numeric ID, remaining simulation
time and script timer ID on the owning ScriptableGameObj. Post_Think visits
timer entries in reverse order, subtracts TimeManager frame seconds and calls
Timer_Expired on matching attached observer IDs. If no observer matches, it
prints a debug message and removes the expired entry. Scheduling therefore
does not establish delivery; observer lifetime must be inspected separately.

Send_Custom_Event dispatches immediately for delay<=0, visiting the target's
current observer list synchronously. A positive delay creates a target-owned
custom timer. Its sender is a GameObjReference and can become unavailable
before expiry. Custom type, parameter, remaining time and sender reference are
saved through original chunks. No replacement event bus is introduced.

Both timer classes subtract simulation time. GameObjManager skips Post_Think
for hibernating objects, objects with Post_Think disabled, and objects affected
by cinematic freeze. TimeManager sets simulation frame ticks to zero when
paused or in snapshot mode, then applies the original time scale. It clamps
ordinary simulation frames to200 ms (SLOWEST_FPS5), retaining real elapsed
frame time separately. Thus the supplied research's general claim that frame
drops change nothing for timer sequencing is too broad: a long stall can
advance simulation timers less than real time, and dispatch eligibility also
matters. Preserve these original semantics.

Existing instrumentation reports a bounded number of callbacks slower than
500 ms. It does not retain timer scheduling, missing-observer expiry, complete
custom dispatch or observer-list mutation history. Those remain diagnostic
gaps. A source review confirms ownership and conditions only; it does not
prove live Tutorial, M13 or M01 timer delivery, saved timer restoration, sender
remapping or progression. No build, launch, device action or runtime gate was
performed. Native mission/runtime gates remain0/10.
