# Dev111 pause patch correction

The two new additions to
`port/patches/commando-a35-eva-native-dependencies.patch` are not integrated:

- Disable the unavailable Help button without hiding its text.
- Reject map-click teleport in the public M00 demo.

An isolated application of the optional-network patch followed by the native
dependencies patch to copies of pristine upstream Commando files failed with
`patch --batch --fuzz=0`. The pre-existing hunks applied; the new encyclopedia
initialization hunk and map callback hunk failed. Retained output:
`build/dev111-host-evidence/eva-demo-safeguards-patch.log`.

Inspection after failure found the intended context text in upstream, with LF
line endings and matching tabs. A whitespace or CRLF mismatch has not been
demonstrated. Regenerate the additions with normal balanced context and correct
hunk positions rather than relaxing zero-fuzz staging.

The user authorized correction. Both additions now use complete leading and
trailing context. The malformed checkpoint-launch draft has also been replaced
by an opt-in source implementation and a machine-generated runtime diff.
The development checkpoint CMake option defaults OFF for public packages.
This edit does not establish patch application or runtime correctness; retain
the subsequent focused check separately before attempting canonical closure.
The installed dev111 package is unchanged. No new pause/resume behavior, Help
appearance, or teleport exclusion has been demonstrated at runtime.

The original EVA factory remains disabled pending dialog lifetime, input edge,
resume, and orderly world-abandon integration. These safeguards alone do not
make the pause menu functional.
