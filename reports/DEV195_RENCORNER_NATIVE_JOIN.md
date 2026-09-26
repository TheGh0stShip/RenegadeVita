# Dev195: Native RenCorner Join

Development checkpoint, not full multiplayer or physical Vita acceptance.

## Verified

The ARMv7 ILP32 executable ran in Vita3K with the existing OpenGL configuration,
requested RenCorner at 51.222.10.72:5001, downloaded and mounted five TTFS
packages, and loaded the negotiated C&C_City_U1.mix. The original network
owners received player ID 2 and its controlled Soldier. Captures show the world,
weapon, HUD and purchase terminal. Bounded backwards/forwards input changed
position; all six synthetic input steps have release receipts. START completed
original session teardown and returned to the main menu.

The session completed 9,723 frames with no reported renderer error. Its measured
Vita3K average was 59.578 FPS, median 16.463 ms, p95 17.912 ms and worst 1,870.567 ms.
This is a short, mostly stationary scene, not a representative benchmark,
lag-free claim or physical Vita performance result. No audible-quality claim
follows from the mixer counters.

The public server snapshot at 2026-09-25T04:29:29+02:00 lists PSVita on GDI with
zero score/kills/deaths. The client requested PS Vita with a space; the public
listing does not preserve it. The normalization boundary is not yet proven.
This confirms public listing, not the user's observation of a join message.

The four-minute runner ended with TIMEOUT_UNASSESSED after the game had already
returned to the menu. That runner status is retained; it is not a game crash or
an unqualified full-run PASS. Gameplay session teardown itself logged PASS.

## Requirements

Use the full unchanged user-owned retail Data tree at
`ux0:data/renegade/retail/Data/`, including its configuration/fonts and movies.
Do not replace it with the PC demo or the Vita tutorial-demo data subset.
Writable configuration is under `ux0:data/renegade/user/config/`.

This experimental direct entry requires a privately provisioned
`tt-identity-v1.txt` and a trusted PEM CA bundle named `cacert.pem`. The existing
`tools/configure_client_identity.py --output PRIVATE_PATH` prompts privately
for a supported retail serial; use a private directory and never publish the
result. TLS certificate validation remains enabled. No credentials, CA bundle,
retail files or server packages are included in the VPK.

One-shot request `direct-ip-launch-v1.txt` contains `tt://51.222.10.72:5001`
followed by a newline. It is consumed on launch. No request means the ordinary
frontend/campaign path. Server packages are downloaded into the separate
`ux0:data/renegade/cache/ttfs/` cache through original archive factories.

## Build And Evidence

Fast candidate, not canonical acceptance:

```sh
RENEGADE_CANDIDATE_LABEL=A3.5-dev195 RENEGADE_BUILD_JOBS=4 \
RENEGADE_INCREMENTAL_STAGE=1 bash tools/build_fast_candidate.sh
```

171 fast contracts and the original DDS alias executable test pass. Original
state-machine callbacks/save-load, loaded replication, factory and ABI tests
also pass. There are 266 deterministic patches. Corresponding source preserves original
Combat/WWNet ownership and separate demo/full-port profiles.

- ELF: cf0bc71915616a53a14ad8286184eb74429e97e6a4ef5d621e3ac52dfbd3be64
- SELF: 28468b0b6fd5ce3e7ee6d804c55d51a3cac1becea46e6da141bbeefb2291cb2e
- VPK: 04f4615dc9d9f891c2f36d8782f41b66580de35b6c90346a0cea0e5d417eaf61

The VPK contains only eboot.bin and sce_sys/param.sfo. Vita3K installation and
readback hashes match. Local candidate evidence is `dev195-tt-native-01` under
the managed log root; it retains the runner receipt, captures and runtime log.
Runtime log hash: c9a772343cd3bebcdbcdcc924c454d2e63911e9acfcda512103dce16034417af.
Private identity and other players' records are not part of public evidence.

## Remaining

Purchase-terminal Action inputs were received but no purchase dialog appeared.
The native gameplay loop lacks the original mainloop's ongoing dialog update/
render dispatch; verify terminal activation/range and connect that owner before
claiming purchase support. Early multiplayer text also displayed malformed
glyphs. START currently leaves the remote session, rather than providing a full
multiplayer pause/menu flow. Round transitions, vehicles, combat, death/respawn,
chat and sustained multiplayer performance remain unaccepted. A known 1,032-byte
float-visibility animation-channel leak remains. Physical Vita testing pending.
