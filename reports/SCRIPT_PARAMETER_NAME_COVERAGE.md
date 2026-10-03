# Shipped script parameter names and vector parsing

A source-only DSP scan examines1,166 literal parameter-name calls, retaining35
numeric or unsupported argument forms separately. Twenty lookup mismatch
sites appear across seven source files. None is a literal mismatch in the
Mission00, MissionX0 or Mission01 file itself; shared script and authored
parameter scope remain necessary. Non-ASCII names are unresolved because
native locale behavior has not been established.

The audit follows case-insensitive ASCII matching, whitespace stripping,
comma separation and the original511-byte descriptor copy. M00_Action has a
601-byte descriptor, leaving some declared names beyond that boundary. The
known Killable_ByNotStar underscore mismatch remains unchanged. These leads
are original-source behavior, not authorization to rename scripts or expand
the descriptor and change retail gameplay. Source hashes are retained privately.

The shared M00_Play_Sound_Object_Bone_DAY script requests an undeclared Offset.
Its resulting position local is not used by the actual bone-based sound call.
However, the original vector parser declares uninitialized x/y/z and returns
them after an unsuccessful scan. That is undefined behavior even when the
computed position is subsequently unused.

A SHA-anchored zero-fuzz patch initializes the three parser floats to zero.
The existing scan, return, parameter names and descriptor limit are preserved.
Successful components are retained; missing or unparsed components receive
deterministic zero values. Nine source/Python counterexamples pass, including
temporary patch replay. This correction is uncompiled. Compiled parser tests,
authored binding provenance and actual mission behavior remain open. Native
mission/runtime evidence gates remain0/10 under the build/launch hold.
