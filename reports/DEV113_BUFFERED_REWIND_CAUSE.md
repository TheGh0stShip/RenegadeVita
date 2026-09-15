# Dev113 host regression: buffered rewind

The regression introduced by the conversation compatibility reader is isolated.
No corrective source edit has been made in this work unit.

## Controlled A/B evidence

An isolated host executable linked the pre-change conversationmgr.cpp against
the same current ASan objects. It passed both original M00 in-process cycles,
including 120 rendered frames. The current conversation reader reproducibly
fails in soldier post-load. Main host artifacts and native packages were not
overwritten by this comparison.

Evidence: `build/dev113-host-evidence/interactive-before-fix.log` (exit 0),
`asan-postload-reproduce.log` (exit 134), and retained isolated build commands.

## Causal trace

`Read_Conversation_Category` calls `ChunkLoadClass::Peek_Next_Chunk`, which reads
an eight-byte header and restores the stream using Seek(-8, SEEK_CUR).
GDB stopped on that exact call with BufferAvailable=12583 and BufferOffset=3801.
Evidence: `build/dev113-host-evidence/buffered-rewind-gdb.log`.

`staging/wwlib/bufffile.cpp:220` resets its buffer for negative relative seeks
before passing the offset to its base file. Reset_Buffer zeros BufferAvailable,
but the underlying file cursor is still ahead by those unread bytes. Thus the
rewind is relative to the read-ahead cursor rather than the logical cursor.
The new peek exposes that existing buffered-file defect and skips required
serialized objects. This is why many physics/model pointer registrations are
absent; null HumanPhys is downstream, not the owning cause.

## Proposed correction

For a negative SEEK_CUR, subtract unread BufferAvailable from the requested
offset before resetting the buffer and delegating to the base file. Preserve
absolute seeks, end-relative seeks and forward buffered consumption. Keep
original BufferedFileClass ownership, use a deterministic registered patch,
and retain old checkpoints unchanged. Do not null-guard soldier post-load or
bypass the sanitizer gate.

The assistant disclosed its introduced regression and is requesting the user's
decision before correcting it, as required by the active editing instruction.
No build, debugger or emulator remains running. Dev113 canonical session 77073
is terminal. The post-Sydney checkpoint request remains queued.
