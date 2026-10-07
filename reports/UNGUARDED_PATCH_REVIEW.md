# Unguarded Patch Review

Scope: six staging patches under `port/patches/` with no `RENEGADE_VITA_PORT`/`__vita__` guard. Review only; no patch was edited and nothing was built.

| Patch | Change | Platform-specific? | Guard needed? |
|---|---|---|---|
| `ww3d2-a315-dds-vita.patch` | `ddsfile.cpp`: declares `unsigned level` in the mip-level `for` loop. Fixes the MSVC6 for-scope/undeclared-variable problem that modern C++ rejects. | No. It is a compiler-conformance fix. The file name says "vita", but the code behaves the same on every platform. | No |
| `scripts-a35-host-m03-pointer-exchange.patch` | `Mission03.cpp`: swaps the `(int)&has_escort` / `(int *)param` pointer-through-int custom events for a pointer-exchange helper. | Yes, for 64-bit host ABI tests. On 32-bit ARM Vita, the original casts are valid. | Already guarded by `RENEGADE_HOST_ABI_TEST`. The `#else` branch keeps the original code. A Vita guard would be wrong. |
| `commando-a35-suspend-viewer-lifecycle.patch` | `combatgmode.cpp` Suspend: hides the objective viewer only if it is currently displayed. | Partly. The trigger (the native frontend suspending Combat before the first level) is port-specific, but the check is harmless everywhere. | No. Hiding an already-hidden viewer does nothing, so original behavior is kept. |
| `commando-a36-campaign-state-source-binding.patch` | Adds `CampaignManager::Current_Level_Matches_Archive()`, which parses `"Level <map>"` from the current campaign-flow entry. Purely additive. | No. Portable C plus the existing `stricmp` compat. | No. It has no effect unless a caller uses it. Callers that are Vita-only should keep their own guard. |
| `commando-a36-save-campaign-source-binding.patch` | Adds `Loaded_Save_State_Matches_Archive()`, which handles the Tutorial, REPLAY_LEVEL and REPLAY_SCORE states and then falls back to the helper above. Additive. Depends on the previous patch, so order matters. | No | No (same reasoning) |
| `commando-a36-campaign-backdrop-selection.patch` | `campaign.cpp`: backdrop lookup now takes the **first** match and breaks; the failure test uses a `found` flag instead of `BackdropIndex == 0`. | No. It fixes a logic defect: the original took the last match and logged a false failure when the valid match was at index 0. | No. **Behavior change:** if a state has duplicate backdrop entries, the first one now wins instead of the last. Check against retail `campaign.ini` that no state has more than one entry. |

## Conclusion
None of the six needs a `RENEGADE_VITA_PORT`/`__vita__` guard. The script patch already has the right (host-ABI) guard. The patch to watch is the backdrop selection change: it alters last-match behavior and should be checked against the retail data.
