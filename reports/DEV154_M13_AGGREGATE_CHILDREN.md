# Dev154: M13 explosion aggregate child creation

The full-port-only WW3D trace identifies `X00_AG_Explode` as an aggregate.
Class ID 25 describes the resulting HLOD render object, not the prototype
subclass. Earlier Dev153 wording that inferred an HLOD constructor from this
ID was incorrect.

In matching `campaign-dev154-children-m13-1` Vita3K/OpenGL direct-M13
evidence, the aggregate created base model `X00_EXPLODE` in 184 us, then
processed 91 authored subobjects. Child `Create_Render_Object` calls totaled
6,634,366 us; attachment and release totaled 207 us. Whole aggregate
creation took 6,636,045 us. A separate Dev154 run measured 7,734,234 us
for this aggregate, so the cost varies but remains multi-second.

This rejects per-attachment bounds-update batching as a meaningful fix.
Dev151's create/release prewarm also failed because live per-instance creation
still ran. Next: test a retained assembled template with fresh per-use clones;
reject it if clone cost or memory remains impractical.

Evidence: managed AppData `campaign-dev154-children-m13-1/`, matching
SELF SHA-256 `e89f3402e43ac431400cea0a6cdfcc6127114f74b0d161316227e07ef830e77d`,
asset-free VPK SHA-256 `2b28cd505a312e6998f2a1be34a1ad770772dd32f6017d42159c2319baba4175`.
ARM SELF/VPK and 195 ordered staging patches pass. The 120-second run ended
`TIMEOUT_UNASSESSED`; no physical Vita, visual, A/V sync, actor-sequence,
campaign-completion, or 60 FPS result is claimed.
