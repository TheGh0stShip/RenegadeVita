# Dev234 pause-route stream allocation failure

## Physical evidence and integrity limits

The user reports a crash after Select+Start in M13 and confirms a crash-dump
screen, later dismissed. Start reaches original menu-toggle input; quicksave
is Select+Square. No save write/reload has been verified.

The matching log ends at START menu routing after final M13 conversation.
Private log SHA-256:
`a468506eab90257576b17efa63900ec97ffe249817cdfe71a5e362ce42beab99`.
Installed SELF:
`2311c5b24d70f46f84b4601ec56cdd274fa6829ac452ab0f6f51cb20e1ba5354`.

Initial dump queries filtered completed `.psp2dmp` files and missed the new
temporary file. A bounded directory check found a `.psp2dmp.tmp` matching
process44638429 (hex2a920dd). Only that file was pulled; no device file was
renamed or changed. Private evidence resides under
`build/device-evidence/A3.5-dev234-20261004/`:

- `select-start-crash.psp2dmp.tmp`,725104 bytes, SHA-256
  `a099d448272dcfc68895d21e259c8d0c092a14e5f31e24d3885c510c19789ee6`.
- `select-start-partial-notes.json`, labelled incomplete-core evidence.
- `runtime-select-start-crash.log`.

The standard parser rejects ELF segments extending beyond the saved bounds.
Four segments are incomplete. A separate bounded extraction reads only
complete PT_NOTE ranges, checks every aligned name/data record against its
range, then uses the existing source-derived thread/module parsers. This
does not validate a complete core or establish a complete backtrace.

Intact source-derived notes relocate PC to0x8163560a, libc `_kill_r`'s deliberate
abort trap. A bounded128-word scan of the available main-stack segment is
heuristic. It contains terminate/throw/operator-new addresses and return
0x813476ae. Matching disassembly shows an operator-new call at0x813476aa inside
`AIL_open_stream_by_sample`, loading the encoded stream image. Other words
identify audio stream/sound-scene activity; they are not verified unwind frames.
The strongest lead is an uncaught stream-image allocation failure, separate
from the already-contained WAVE PCM decoding allocation.

## Provider correction and focused validation

`port/audio/vita/renegade_miles_provider.cpp` previously resized a byte vector
after opening the stream source. Allocation failure escaped before source
close and before the WAVE decoder's allocation guard.

Dev236 replaces this image with a local unique array allocated using
`new (std::nothrow)`. Failure closes the source and returns the existing
provider error; incomplete reads release the local buffer, and successful
reads transfer ownership only after close. This also avoids zero-initializing
a buffer that the file read fills. Encoded content, original file callbacks,
decoder, sound ownership, loop behavior and simulation remain unchanged.
No global exception policy, mute, gameplay fallback or retail file change.

The production-provider failure-injection fixture verifies null stream,
specific error, exactly one source close, then successful retry and cleanup.
The existing production-decoder test still verifies prior output preservation
on PCM allocation failure. Both audio tests pass, including the separate
sanitized mixer/lifecycle test. All 502 host checks, six ARM compile/link
actions and seven packaging actions pass. Vita3K installed hashes match;
the emulator was not launched. Dev236 includes dev235's original cinematic
dispatch restoration. The physical executable was replaced using old/new
hash guards and independently verified against SELF SHA-256
`da500f03613e134430de390cc9b3b2b63782d90bb200f6a61866191b84387d34`.

## Open gates

Reproduce original fresh Recruit startup, cinematic ordering, pause/resume,
Select+Square checkpoint creation, original Load Game restoration and final
score/M01 transition on matching hardware. Heap pressure and dropped audio
are unresolved; allocation guards establish failure handling, not adequate
memory or faithful audible output. More uncaught allocations may exist.
The reported severe M13 performance remains open; use retained per-stage,
frame-time and memory data plus a fixed route before adopting optimizations.
No corrected physical result or PSTV acceptance is claimed.
