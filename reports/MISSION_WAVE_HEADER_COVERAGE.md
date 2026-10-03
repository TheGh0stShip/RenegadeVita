# Tutorial, Scorpion Hunters and M01 audio bounds

The read-only retail scan examines authored conversation references in
M00_Tutorial, M13 (Scorpion Hunters), and M01. It checks actual candidate byte
lengths, RIFF/chunk bounds, format metadata and ADPCM block headers. Archive,
definition-database and strings provenance are retained privately. Alternative
strings candidates remain separate; header admission is not decoded playback.

Tutorial has 221 candidate WAVs and M13 has 566. Their complete headers pass
this scan. M01 has 122 candidates: 111 pass and 11 declare RIFF lengths seven
or eight bytes larger than their actual files. These eleven also contain raw
trailers after the declared data chunk. This establishes a source/data bounds
problem, not a measured native crash or proof of missing audible dialogue.

Original SoundBuffer allocates the actual file length. Original Sound3DHandle
previously passed only its pointer to the provider, which derived a decode
length from the untrusted RIFF header. A deterministic staging patch now
forwards the actual buffer length to a bounded provider API. The existing
decoder retains its strict checks. No retail file is changed. The legacy
pointer-only API remains for compatibility and cannot independently establish
allocation bounds; the original engine caller uses the bounded API.

The stream path independently reads the actual file size and passes the vector's
size to decoding. It does not share the original pointer-only 3D caller defect.
Source inspection confirms strict decoding rejects an oversized RIFF image;
matching original-provider compatibility evidence is needed before accepting
these eleven files with a different parsing policy.

Conversation timing also needs validation. Original SoundBuffer statistics
initialize duration to zero and populate it only when bounded header inspection
succeeds. AudibleSound copies that duration from the buffer. Soldier dynamic
dialogue starts with a two-second default, but replaces it with the duration
of any created speech object, including zero. ActiveConversation assigns that
result to its next-remark timer and advances after the timer expires, subject
to audience checks. Thus a created speech object with failed statistics could
advance on the next update rather than retaining the default pause.

The provider's statistics mode allows truncated data chunks for header-only
inspection; it still rejects an overlong non-data chunk. The raw trailers in
the eleven files are therefore relevant to both statistics and playback.
This is a conditional source-path risk, not observed mission behavior. Sound
creation, preset choice, actor state and actual statistics must be captured
before claiming that a particular conversation or callback advances early.
Get_Conversation_Time separately falls back to two seconds when the summed
duration is nonpositive; that fallback does not clamp each spoken remark.

The new boundary is uncompiled and untested at runtime under the existing
build/launch hold. The eleven files' decode compatibility remains open.
PCM/ADPCM sample reconstruction, audible presentation, logical sounds,
conversation timing and full mission progression require further evidence.
Native mission/runtime gates remain 0/10.

Validation: 245 focused Python/source checks and 38 publication/future-entry
checks pass. The original-owner patch replays in a temporary source copy with
zero fuzz. Future C++ regression cases are added but uncompiled. There are
294 registered staging patches; the existing staging receipt remains stale
until staging is permitted. Private audit receipts were refreshed after the
provider source edit. No generated retail content is published.
