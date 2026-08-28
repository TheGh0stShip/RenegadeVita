#!/usr/bin/env python3
"""Validate one bounded A3.5 physical session without inferring visuals."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


START_RE = re.compile(r"^\[LIFECYCLE\] START .*candidate=(A3\.5-dev(?:[6-9]|1[0-3]))\b")
COMPLETE_RE = re.compile(
    r"A3\.1 interactive: complete ready=(\d+) transport=(\d+) level=(\d+) "
    r"player=(\d+) commando=(\d+) frames=(\d+) exit=(\d+) render_error=(\d+) "
    r"teardown=(\d+) pause/resume=(\d+)/(\d+) paused_input_frames=(\d+)"
)
PAUSE_RE = re.compile(
    r"A3\.5 pause: original Combat suspended frame=(\d+) "
    r"player=\(([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)\)"
)
RESUME_RE = re.compile(
    r"A3\.5 pause: original Combat resumed frame=(\d+) paused_input_frames=(\d+) "
    r"player=\(([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)\)"
)
EFFECT_RE = re.compile(
    r"A3\.5 effects: reason=(\S+) frame=(\d+) .*?"
    r"position=\(([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)\) "
    r"velocity=\(([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)\) .*?"
    r"physics=(\d+) grounded=(\d+) .*?rounds=(-?\d+)/(-?\d+) "
    r"fired_total=(\d+) .*?action_count/active/busy=(\d+)/(\d+)/(\d+)"
)
INPUT_RE = re.compile(r"A3\.5 input: .* buttons=([0-9A-Fa-f]{8})")
SCRIPTS_RE = re.compile(
    r"A3\.5 scripts: provider_active=(\d+) registered=(\d+) active=(\d+)"
)
MISSION_TERMINAL_RE = re.compile(
    r"start_exit=(\d+) mission_complete/success/star=(\d+)/(\d+)/(\d+)"
)
MISSION_PROGRESS_RE = re.compile(
	r"A3\.5 mission progress: frame=(\d+) star/control=(\d+)/(\d+) "
	r"objectives=(\d+) status_1_6=(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+)/(-?\d+) "
	r"active_conversations=(\d+).*? player=\(([-+0-9.eE]+),([-+0-9.eE]+),([-+0-9.eE]+)\)"
)
TUTORIAL_CONTROL_MARKER = (
    "A3.5 mission progress: objective 1 pending and original player control available"
)


def distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def latest_session(text: str, candidate: str) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if (match := START_RE.match(line)) and match.group(1) == candidate]
    if not starts:
        return ""
    return "\n".join(lines[starts[-1] :]) + "\n"


def check(name: str, passed: bool, detail: object) -> dict[str, object]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, choices=("A3.5-dev6", "A3.5-dev7", "A3.5-dev8", "A3.5-dev9", "A3.5-dev10", "A3.5-dev11", "A3.5-dev12", "A3.5-dev13"))
    parser.add_argument("--mode", required=True, choices=("pause", "effects", "scripts", "completion-smoke", "progress-smoke"))
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()

    session = latest_session(args.log.read_text(encoding="utf-8", errors="replace"), args.candidate)
    checks: list[dict[str, object]] = []
    checks.append(check("candidate_session_present", bool(session), args.candidate))
    checks.append(check("runtime_identity", f"Runtime identity: candidate={args.candidate}" in session, args.candidate))
    ready_marker = (
        "original player/session ready; original mission completion or START exits"
        if args.candidate in ("A3.5-dev10", "A3.5-dev11", "A3.5-dev12", "A3.5-dev13")
        else "original player/session ready; START exits"
    )
    checks.append(check("player_session_ready", ready_marker in session, "original owner breadcrumb"))
    checks.append(check("first_visible_frame", "first original render frame PASS" in session, "log evidence only"))

    complete_matches = list(COMPLETE_RE.finditer(session))
    complete = complete_matches[-1] if complete_matches else None
    checks.append(check("completion_record_present", complete is not None, "A3.1 interactive completion"))
    if complete:
        values = tuple(int(value) for value in complete.groups())
        ready, transport, level, player, commando, frames, clean_exit, render_error, teardown, pause_seen, resume_seen, paused_frames = values
        checks.extend(
            (
                check("original_runtime_ready", (ready, transport, level, player, commando) == (1, 1, 1, 1, 1), values[:5]),
                check("rendered_frames", frames >= 120, frames),
                check("clean_exit", clean_exit == 1, clean_exit),
                check("render_error_clear", render_error == 0, render_error),
                check("teardown_complete", teardown == 1, teardown),
            )
        )
    else:
        pause_seen = resume_seen = paused_frames = 0

    checks.append(check("lifecycle_clean", f"[LIFECYCLE] END status=clean candidate={args.candidate}" in session, args.candidate))

    state = None
    if args.state:
        state = json.loads(args.state.read_text(encoding="utf-8"))
        checks.extend(
            (
                check("capture_candidate", state.get("milestone") == args.candidate, state.get("milestone")),
                check("capture_phase", state.get("phase") == "interactive-player-owned", state.get("phase")),
                check("capture_player_present", state.get("player", {}).get("present") is True, state.get("player", {}).get("present")),
                check("capture_renderer_clean", state.get("renderer", {}).get("backend_errors") == 0, state.get("renderer", {}).get("backend_errors")),
            )
        )

    observations: dict[str, object] = {}
    if args.mode == "pause":
        pause_matches = list(PAUSE_RE.finditer(session))
        resume_matches = list(RESUME_RE.finditer(session))
        checks.extend(
            (
                check("pause_transition", pause_seen == 1 and bool(pause_matches), {"summary": pause_seen, "records": len(pause_matches)}),
                check("resume_transition", resume_seen == 1 and bool(resume_matches), {"summary": resume_seen, "records": len(resume_matches)}),
                check("paused_input_serviced", paused_frames > 0, paused_frames),
            )
        )
        if pause_matches and resume_matches:
            # START can enter the original menu/suspended state immediately
            # before the bounded clean-exit path. Pair the latest resume with
            # its immediately preceding suspend instead of an unmatched,
            # trailing suspend emitted during teardown.
            paired_resume = resume_matches[-1]
            preceding_pauses = [match for match in pause_matches if match.start() < paired_resume.start()]
            paired_pause = preceding_pauses[-1] if preceding_pauses else None
            checks.append(check("suspend_precedes_resume", paired_pause is not None, len(preceding_pauses)))
        else:
            paired_pause = paired_resume = None
        if paired_pause and paired_resume:
            paused_position = tuple(float(value) for value in paired_pause.groups()[1:4])
            resumed_position = tuple(float(value) for value in paired_resume.groups()[2:5])
            pause_drift = distance(paused_position, resumed_position)
            observations.update(paused_position=paused_position, resumed_position=resumed_position, pause_position_delta=pause_drift)
            checks.append(check("position_stable_while_paused", pause_drift <= 0.05, pause_drift))
            if state:
                final_values = state.get("player", {}).get("position")
                valid_final = isinstance(final_values, list) and len(final_values) == 3 and all(isinstance(value, (int, float)) for value in final_values)
                checks.append(check("post_resume_capture_position", valid_final, final_values))
                if valid_final:
                    final_position = tuple(float(value) for value in final_values)
                    resumed_movement = distance(resumed_position, final_position)
                    observations.update(final_position=final_position, post_resume_position_delta=resumed_movement)
                    checks.append(check("post_resume_walk_observed", resumed_movement >= 0.25, resumed_movement))
    elif args.mode == "effects":
        effects = []
        for match in EFFECT_RE.finditer(session):
            groups = match.groups()
            effects.append(
                {
                    "reason": groups[0],
                    "frame": int(groups[1]),
                    "position": tuple(float(value) for value in groups[2:5]),
                    "velocity": tuple(float(value) for value in groups[5:8]),
                    "physics": int(groups[8]),
                    "grounded": int(groups[9]),
                    "clip_rounds": int(groups[10]),
                    "total_rounds": int(groups[11]),
                    "fired_total": int(groups[12]),
                    "action_count": int(groups[13]),
                    "action_active": int(groups[14]),
                    "action_busy": int(groups[15]),
                }
            )
        button_masks = [int(match.group(1), 16) for match in INPUT_RE.finditer(session)]
        position_span = max((distance(effects[0]["position"], effect["position"]) for effect in effects[1:]), default=0.0) if effects else 0.0
        fired_span = (max(effect["fired_total"] for effect in effects) - min(effect["fired_total"] for effect in effects)) if effects else 0
        observations.update(effect_records=len(effects), position_span=position_span, fired_rounds_delta=fired_span, square_input_sampled=any(mask & 0x8000 for mask in button_masks))
        checks.extend(
            (
                check("bounded_effect_records", len(effects) >= 2, len(effects)),
                check("original_physics_registered", bool(effects) and all(effect["physics"] == 1 for effect in effects), [effect["physics"] for effect in effects]),
                check("ground_contact_observed", any(effect["grounded"] == 1 for effect in effects), [effect["grounded"] for effect in effects]),
                check("walk_position_changed", position_span >= 0.25, position_span),
                check("weapon_fire_effect", fired_span > 0, fired_span),
                check("square_action_input_sampled", any(mask & 0x8000 for mask in button_masks), [f"{mask:08X}" for mask in button_masks]),
            )
        )
    else:
        scripts_matches = list(SCRIPTS_RE.finditer(session))
        script_values = tuple(int(value) for value in scripts_matches[-1].groups()) if scripts_matches else ()
        provider_active, registered_scripts, active_scripts = script_values if script_values else (0, 0, 0)
        observations.update(
            provider_active=provider_active,
            registered_scripts=registered_scripts,
            active_scripts=active_scripts,
        )
        registration_check = (
            check("m00_direct_script_closure_registered", registered_scripts == 37, registered_scripts)
            if args.candidate in ("A3.5-dev9", "A3.5-dev10", "A3.5-dev11", "A3.5-dev12", "A3.5-dev13")
            else check("mission_scripts_registered", registered_scripts > 0, registered_scripts)
        )
        checks.extend(
            (
                check("script_provider_record_present", bool(scripts_matches), len(scripts_matches)),
                check("script_provider_active", provider_active == 1, provider_active),
                registration_check,
                check("mission_scripts_attached", active_scripts > 0, active_scripts),
            )
        )
        if state:
            checks.append(
                check(
                    "capture_scripts_active",
                    state.get("runtime", {}).get("scripts_active") is True,
                    state.get("runtime", {}).get("scripts_active"),
                )
            )
        if args.mode in ("completion-smoke", "progress-smoke"):
            terminal_matches = list(MISSION_TERMINAL_RE.finditer(session))
            terminal_values = tuple(int(value) for value in terminal_matches[-1].groups()) if terminal_matches else ()
            start_exit, mission_complete, mission_success, star_killed = terminal_values if terminal_values else (0, 0, 0, 0)
            observations.update(
                start_exit=start_exit,
                mission_completion_observed=mission_complete,
                mission_succeeded=mission_success,
                star_killed_observed=star_killed,
            )
            checks.extend(
                (
                    check("completion_observer_summary_present", bool(terminal_matches), len(terminal_matches)),
                    check("smoke_exit_owned_by_start", start_exit == 1, start_exit),
                    check("smoke_does_not_claim_mission_completion", (mission_complete, mission_success, star_killed) == (0, 0, 0), terminal_values[1:] if terminal_values else ()),
                )
            )
        if args.mode == "progress-smoke":
            progress_matches = list(MISSION_PROGRESS_RE.finditer(session))
            progress_records = []
            for match in progress_matches:
                values = match.groups()
                progress_records.append(
                    {
                        "frame": int(values[0]),
                        "star_available": int(values[1]),
                        "player_control_enabled": int(values[2]),
                        "objective_count": int(values[3]),
                        "objective_status_1_6": tuple(int(value) for value in values[4:10]),
                        "active_conversation_count": int(values[10]),
                    }
                )
            control_handoff_records = [
                record
                for record in progress_records
                if record["star_available"] == 1
                and record["player_control_enabled"] == 1
                and record["objective_status_1_6"][0] == 0
            ]
            observations.update(
                mission_progress_records=len(progress_records),
                tutorial_control_handoff_records=len(control_handoff_records),
                latest_mission_progress=progress_records[-1] if progress_records else None,
            )
            checks.extend(
                (
                    check("mission_progress_record_present", bool(progress_records), len(progress_records)),
                    check("objective_1_pending_with_original_control", bool(control_handoff_records), len(control_handoff_records)),
                    check("tutorial_control_handoff_marker", TUTORIAL_CONTROL_MARKER in session, TUTORIAL_CONTROL_MARKER),
                )
            )

    passed = all(item["passed"] for item in checks)
    result = {
        "schema_version": 1,
        "candidate": args.candidate,
        "mode": args.mode,
        "status": "PASS" if passed else "FAIL",
        "claim_boundary": (
            "mission progress observer smoke only; log/state telemetry does not prove mission completion, visual correctness, or environmental action success"
            if args.mode in ("completion-smoke", "progress-smoke")
            else "log/state telemetry only; no visual correctness or environmental action success inferred"
        ),
        "observations": observations,
        "checks": checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
