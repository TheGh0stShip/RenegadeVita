# Flight recorder event sequence validation

The existing bounded event ring now exports its original numeric sequence
counter with each event. Frame numbers and timestamps remain separate fields.
This helps identify duplicate, reordered or missing exported records without
claiming that every original game event was instrumented.

The bundle validator accepts historical records with no sequence field and
new records with sequences. It rejects mixed modes within one sidecar,
noninteger or out-of-range counters, and gaps or duplicate/reversed sequences.
The first retained sequence can be nonzero: earlier events may have been
evicted before a flush. Contiguity does not prove capture began before gameplay
or that the recorder retained the complete mission.

Ten focused Python/source checks pass, including nonzero retained starts,
missing/reordered records, invalid widths/types and legacy compatibility.
The C++ exporter change is uncompiled under the build/launch hold. Pending
conversation hooks are a separate local integration and are not part of this
publication. Native mission/runtime evidence gates remain 0/10.
