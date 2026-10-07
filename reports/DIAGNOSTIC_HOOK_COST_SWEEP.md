# Diagnostic hook cost sweep (post-budget work)

Scope: `port/patches/*diagnostic*.patch` (11 files), static-analysis only; no build.
Question: does any budgeted hook still compute (clock reads, math, string/heap
work) after its log budget is exhausted?

## Still doing work before/regardless of budget

| Patch | Hunk | Post-budget cost | Severity |
|---|---|---|---|
| `wwui-a35-dialog-template-vita-diagnostics.patch` | `@@ -262,13 +315,45 @@` (per dialog control) | `WideStringClass vita_untranslated_text = text_buffer;` (heap copy) and `vita_ascii_string_id = ascii_string_id;` run for every control even after `g_vita_dialog_template_logs >= 96`. | Medium (per-object heap alloc on every dialog build; not per-frame) |
| `wwui-a35-dialog-template-vita-diagnostics.patch` | `@@ -193,10 +209,23 @@` (dialog title) | `WideStringClass untranslated_title = dlg_title->Peek_Buffer();` copied unconditionally before budget check. | Low |
| `combat-a35-target-box-diagnostics.patch` | `@@ -1822,6 +1822,11 @@` / `@@ -1834,6 +1839,10 @@` (`Target_Update`, per frame) | `projected_top/bottom` Vector2 copies plus an out-of-line call to `Log_Vita_Target_Box_Diagnostics` every frame; budget (64) checked inside callee. Heavy work (resolution query, camera aspect, printf) is correctly after the check. | Low (call overhead only) |

## Checked and acceptable (budget gated before real work)

- `combat-a35-logan-path-diagnostics.patch` Goto `Act()` / `Notify_Completed` / `Request_Action`: only `Get_Action_Obj()->Get_ID()` precedes the `< 128U` check; `logan_calls` modulo counter increments only while under budget (short-circuit). Position/printf after check.
- `combat-a35-transition-action-diagnostics.patch` `TransitionManager::Check`: `logged_action_checks < 24U` checked before `Get_Position`/log; later hunks gated by `log_action_check`.
- `ww3d2-a35-render2d-text-atlas-vita-diagnostics.patch`: surface lock + alpha scan fully inside `g_vita_render2d_text_atlas_logs < 64U`.
- `combat-a35-vehicle-proximity-diagnostics.patch`: recently fixed example; not re-flagged.
- Remaining patches (conversation, observer-load, save-phase, cinematic-filename, static-object-load) have no static budget counters in per-frame/per-object hooks (one-shot load/event logs).

## Suggested fixes (not applied)

1. Dialog control hunk: guard the snapshot with `const bool vita_log = g_vita_dialog_template_logs < 96U;` and only copy `text_buffer`/`ascii_string_id` when `vita_log`. Translation-copy/truncation logic (`Vita_Dialog_Copy_Translation`) is a correctness fix and must stay unconditional.
2. Dialog title hunk: same pattern for `untranslated_title`.
3. Target box: inline the `>= 64U` check at the call site (or make the counter check a `static inline` wrapper).
