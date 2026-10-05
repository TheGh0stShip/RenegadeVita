# A3.6 source review follow-up

## Transparent-sort allocation correction

The committed radix-sort workspace discarded all existing buffers before five
throwing array allocations. Vita builds use `-fno-exceptions`, so an allocation
failure in an explosion-heavy scene could terminate the title and partial
allocation could not recover. The local follow-up allocates a complete
replacement with `std::nothrow`, publishes it only after every allocation
succeeds, and otherwise uses the original sorting implementation while
retaining the prior workspace. This correction is source-only and has not been
staged, compiled, or run under the active validation hold.

## Remaining audit priorities

Three GPT-5.6 source audits separated current dirty-source closure from the
last built candidate. Dev238 predates the selected autosave consumer,
death/failure/restart handlers, campaign-catalog readiness, reload observer
retention, save admission, and Practice core-restart work. Its artifact cannot
serve as evidence for those changes.

Static-mesh replay validity still does not cover every mutable texture, shader,
geometry, UV, colour and index input. Raw cached object pointers also require
retained ownership or guaranteed invalidation before release. This must be
corrected before the cache is accepted. Lazy DXT materialization and the
independent texture, geometry and audio budgets require separate follow-up.

The custom `RVL1` beacon is not the original LAN protocol and cannot populate
original `cGameData`/`cGameChannelList`. Authentic LAN closure must select and
port `LanGameModeClass`/`cLanChat`, detach its game-channel path from WWOnline,
admit the original LAN dialogs/resources behind a narrow gate, and extend the
native launch latch for LAN host/client ownership. GameSpy/WOL remains excluded.

The first static-cache follow-up now invalidates model-scoped entries at the
released mutation entry points for passes, materials, textures, shaders,
writable arrays, geometry/UV/colour uniqueness and alternate material changes.
This closes normal setter-driven replacement before cached raw state can be
released or replayed. Code that retains a writable array pointer and mutates it
later without re-entering the model remains under review; no executed evidence
has been produced.

The native DDS follow-up now treats failed lazy materialization as a real
`GetSurfaceLevel`/`LockRect` failure instead of allocating a blank CPU surface.
It also limits unchanged-block DXT upload to complete requested mip chains;
files whose chain includes sub-4x4 tail levels retain the existing full decode
path and its logical mip contract. These changes remain uncompiled and
unexecuted.

Local main is synchronized to `9f05633`, including `e336772`, `deb708b`,
`6ef36bb`, `6d800bb`, and `522dabb`. The baseline remains `d0f993b`.
The overhaul report's host/compile results are inherited evidence, not newly
executed checks or physical acceptance. The user has stopped tests and device
interaction. No build, test, install, launch, input, or device retrieval was
performed during this review.

Initial inspection covered the overhaul report, rooted write staging and
availability, async log ring, static-mesh replay state restoration, audio/cache
and thread placement entry points, build flags, and powerup text lifetime.
This is not a completed review of every changed implementation.

Two narrow source corrections are pending validation:

- `port/platform/renegade_async_log.h`: the writer previously synced only
  after draining the queue. Continuous producers could indefinitely defer the
  documented periodic sync and explicit flush. Check the sync deadline and
  flush target between written spans. File I/O remains on the worker outside
  the producer mutex. A blocking sink still cannot have a guaranteed deadline.
- `port/filesystem/renegade_file_factory.cpp`: allocation fallback previously
  discarded the staged-flush return value before writing more bytes. A failed
  flush now returns zero for the triggering write instead of proceeding at an
  uncertain file position and reporting that write as successful.

Further local source corrections retain a sticky write-failure flag after a
failed staged flush. Subsequent writes return zero until a successful reopen;
`Has_Write_Failed()` exposes the condition without changing the original void
Close signature. Close-time failure is retained. The subsequent selected
save-owner patches below connect this status to original save callers; runtime
write completion, structural validity and reload fidelity remain unverified.

The async worker now checks every sink write/sync result, terminates on failure,
and wakes flush waiters without advancing written/synced counters for the
failed operation. New runtime lines use the existing direct-write fallback
after worker failure. Pending lines from the failed sink are not recovered;
partial writes can exist. This is failure containment, not durable-log proof.
All corrections remain source-inspected only, with no executed validation.

Next source review priorities are GPU-cache mutation/lifetime and draw-state
equivalence, sorted-geometry state merging, texture upload/lazy surface
ownership, audio-cache lifetime and memory headroom, and asynchronous shutdown.
No performance gain, save recovery, visual parity, or hardware stability is
accepted. Source edits remain local pending validation authorization.

Save-owner continuation adds three selected staging patches. A native-only
FileClass status query keeps the original void Close interface; the rooted
provider retains RawFileClass error callbacks, including final-close errors.
SaveGameManager checks creation/open failure and records write status before
returning the file to its factory. Original Quick_Save returns on failed write
without toggling the slot registry or displaying the success help text.
This status describes provider write completion, not save structure validity,
reload compatibility or power-loss durability. No serialization order or disk
fields change. The native-only virtual interface addition requires all affected
translation units to be rebuilt together before any candidate use. Neither
staging patches nor compilation have been executed under the current hold.

Manual-save continuation also connects the writer status before original dialog
close and uses original WWUI failure popups. Failed slot-factory queries stop
probing. Existing restored-player binding rejections request guarded failed-load
menu recovery without changing admission checks. Terminal-state popup restoration
and the reported save freeze remain unresolved. See MANUAL_SAVE_FAILURE_WIRING.md.
