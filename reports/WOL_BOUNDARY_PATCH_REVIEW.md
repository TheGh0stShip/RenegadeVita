# WOL/online boundary patch review

Scope: four staging patches under `port/patches/`. This is a review only: no patches were edited and nothing was built.

## Key cross-cutting finding

The `RENEGADE_VITA_PORT=1` define does **not** tell the Vita target apart from host tests. The Vita
`CMakeLists.txt` (line 577) sets it, and so do the host targets: `tools/host_a30/CMakeLists.txt:91`
and several targets in `tools/host_a30_definitions/CMakeLists.txt` (with `RENEGADE_HOST_ABI_TEST=1`).
Staged Commando sources are also compiled by the host test trees. A `RENEGADE_VITA_PORT` guard
therefore marks code as "port, not pristine upstream". It does not mean "Vita only". To tell the two
apart, use `RENEGADE_HOST_ABI_TEST` or a new explicit define.

Every staged build is a port build, so there is no consumer of the unguarded original path. Wrapping
include swaps in `#if` would leave the original WOL/GameSpy headers on a path that cannot be built,
because those headers are excluded.

## 1. commando-a4-combatgmode-wol-boundary.patch
- **Change:** `combatgmode.cpp` now includes `a31_wol_stub.h` instead of `wolgmode.h`. The WOL game
  mode's declarations come from the port stub, so the real WOL game-mode logic is retired.
- **Behaviour removed:** WOL online play through CombatGameMode. Offline combat logic is unchanged.
- **Target scope:** Affects every build that compiles staged `combatgmode.cpp`, host and Vita alike.
  This is intended, because WOL sources are excluded everywhere.
- **Recommendation:** Keep the patch unguarded. A guard would only re-expose a header that cannot be
  built. The patch is a one-line include swap and is already well scoped.

## 2. commando-a4-gameinitmgr-online-boundary.patch
- **Change:** In `gameinitmgr.cpp` it removes the includes for `natter.h`, `autostart.h`,
  `gamesideservercontrol.h`, `slavemaster.h`, `gamespyadmin.h`, `serversettings.h` and
  `gamespy_qnr.h`. Replacements come from `a4_gameinit_online_boundary.h` and the
  `a31_slavemaster/gamespy/serversettings` stubs.
- **Behaviour removed:** WOL NAT traversal, autostart/slave dedicated-server control, GameSpy QnR and
  admin, and server-settings file handling. The offline GameInitMgr branch is preserved.
- **Target scope:** Same as patch 1: every staged build, including host.
- **Recommendation:** Keep it unguarded. The stubs need to keep returning the original
  "not dedicated / not autostart / no GameSpy" answers, so the offline branch runs unchanged. That
  belongs in the stub headers, not in an `#if` around the includes. Re-review this patch when the
  networking roadmap brings in the LAN/Direct-IP/GameSpy-replacement provider seam (v3.9).

## 3. commando-a36-multihud-optional-network-mode.patch
- **Change:** `GameModeManager::Find("WOL")->Is_Active()` is replaced by
  `Renegade_Network_Mode_Active("WOL")`, which returns false when the mode is not registered.
- **Behaviour change:** When WOL is registered, the result is identical. When it is not registered
  (Direct-IP/LAN-less sessions), the original dereferenced NULL and crashed. Now the "recruit" tag
  is simply skipped. This is a null-safety fix with no semantic change.
- **Target scope:** Every staged build. Behaviour only differs where the original would crash.
- **Recommendation:** Keep it unguarded. It is semantics-preserving and correct on any platform.

## 4. commando-a36-direct-client-round-validity.patch
- **Change:** In `cGameData::Is_Map_Valid`, when Direct-IP client round identity is active,
  `A31ClientConnect::Round_Map_Validity` can decide validity before the original
  `cMiscUtil::File_Exists` check. For a matching round map, validity is based on the
  round-resource/TT resource-group state. It can return **false** even if the file exists, or true
  without the file existing locally.
- **Behaviour change:** This is a real semantic change, but only while an A31 Direct-IP client
  session with round identity is active. Otherwise it returns false and the original path runs.
- **Target scope:** It is already inside `#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) &&
  !RENEGADE_VITA_M00_DEMO`. Only targets that define the frontend option and link
  `a31_client_connect_boundary.cpp` get it. In practice that is the Vita frontend build, plus any host
  test that defines `RENEGADE_A4_ORIGINAL_FRONTEND`.
- **Recommendation:** Do not add a `RENEGADE_VITA_PORT` guard. It would be redundant and would not
  exclude host builds. The existing frontend guard is the right gate. Optionally, document in the
  patch header that this is the provider-seam override of original map validation, so it is easy to
  find during the v3.9 networking review. A host test of the false-despite-file-present case would
  be worth adding.

## Summary
| Patch | Original behaviour affected | Vita only? | Guard with RENEGADE_VITA_PORT? |
|---|---|---|---|
| combatgmode-wol-boundary | WOL game mode retired | No (all staged builds) | No |
| gameinitmgr-online-boundary | NAT/GameSpy/slave/autostart retired | No (all staged builds) | No |
| multihud-optional-network-mode | NULL-deref avoided; otherwise identical | No (benign) | No |
| direct-client-round-validity | Map validity overridden in Direct-IP rounds | Frontend builds only | No (already gated) |
