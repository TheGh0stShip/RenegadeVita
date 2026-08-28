#!/usr/bin/env python3

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "tools" / "validate_a35_physical_gate.py"


def state(candidate: str, position: list[float], scripts_active: bool = False) -> dict:
    return {
        "milestone": candidate,
        "phase": "interactive-player-owned",
        "player": {"present": True, "position": position},
        "renderer": {"backend_errors": 0},
        "runtime": {"scripts_active": scripts_active},
    }


class PhysicalGateValidatorTests(unittest.TestCase):
    def run_fixture(
        self,
        candidate: str,
        mode: str,
        log: str,
        state_data: dict,
        check_process: bool = True,
    ) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log_file = root / "runtime.log"
            state_file = root / "state.json"
            log_file.write_text(log, encoding="utf-8")
            state_file.write_text(json.dumps(state_data), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(VALIDATOR), "--candidate", candidate, "--mode", mode, "--log", str(log_file), "--state", str(state_file)],
                check=check_process,
                capture_output=True,
                text=True,
            )
            return json.loads(completed.stdout)

    def test_pause_session_requires_stable_pause_and_post_resume_walk(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev6 log_path=x
Runtime identity: candidate=A3.5-dev6 display=x path=x
A3.1 breadcrumb: original player/session ready; START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 pause: original Combat suspended frame=140 player=(1.000,2.000,3.000)
A3.5 pause: original Combat resumed frame=260 paused_input_frames=120 player=(1.000,2.000,3.000)
A3.5 pause: original Combat suspended frame=600 player=(2.000,2.000,3.000)
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=600 exit=1 render_error=0 teardown=1 pause/resume=1/1 paused_input_frames=120 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev6
"""
        result = self.run_fixture("A3.5-dev6", "pause", log, state("A3.5-dev6", [2.0, 2.0, 3.0]))
        self.assertEqual("PASS", result["status"])
        self.assertGreaterEqual(result["observations"]["post_resume_position_delta"], 0.25)

    def test_effects_session_separates_square_delivery_from_environment_claim(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev7 log_path=x
Runtime identity: candidate=A3.5-dev7 display=x path=x
A3.1 breadcrumb: original player/session ready; START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 effects: reason=first frame=1 player=1 definition=x state=UPRIGHT position=(0,0,0) velocity=(0,0,0) health=100 physics=1 grounded=1 weapon=x/1 rounds=10/20 fired_total=0 weapon_state=0 triggered/fired=0/0 action_count/active/busy=0/0/0
A3.5 input: samples=1 raw lx/ly/rx/ry=0/0/0/0 normalized=0/0/0/0 logical=0/0/0/0 mouse_delta=0/0 dt=0 buttons=00008000
A3.5 effects: reason=checkpoint frame=120 player=1 definition=x state=UPRIGHT position=(1,0,0) velocity=(1,0,0) health=100 physics=1 grounded=1 weapon=x/1 rounds=8/18 fired_total=2 weapon_state=1 triggered/fired=1/1 action_count/active/busy=0/0/0
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=600 exit=1 render_error=0 teardown=1 pause/resume=0/0 paused_input_frames=0 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev7
"""
        result = self.run_fixture("A3.5-dev7", "effects", log, state("A3.5-dev7", [1.0, 0.0, 0.0]))
        self.assertEqual("PASS", result["status"])
        self.assertIn("no visual correctness or environmental action success inferred", result["claim_boundary"])

    def test_scripts_session_requires_registered_and_attached_original_scripts(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev8 log_path=x
Runtime identity: candidate=A3.5-dev8 display=x path=x
A3.1 breadcrumb: original player/session ready; START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 scripts: provider_active=1 registered=41 active=12
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=600 exit=1 render_error=0 teardown=1 pause/resume=0/0 paused_input_frames=0 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev8
"""
        result = self.run_fixture("A3.5-dev8", "scripts", log, state("A3.5-dev8", [1.0, 0.0, 0.0], True))
        self.assertEqual("PASS", result["status"])
        self.assertEqual(41, result["observations"]["registered_scripts"])
        self.assertEqual(12, result["observations"]["active_scripts"])

        runner = (ROOT / "tools" / "run_a35_vita_physical_gate.sh").read_text(
            encoding="utf-8"
        )
        dev8_branch = runner.split(
            "elif [[ $phase == dev8-scripts || $phase == dev9-m00-closure ]]", 1
        )[1].split(
            "fi\n\nrun_json()", 1
        )[0]
        self.assertIn("RENEGADE_DEV6_GATE_RECEIPT", dev8_branch)
        self.assertIn("RENEGADE_DEV7_GATE_RECEIPT", dev8_branch)
        self.assertIn('candidate == "A3.5-dev6"', dev8_branch)
        self.assertIn('candidate == "A3.5-dev7"', dev8_branch)

    def test_dev9_requires_exact_direct_m00_registration_closure(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev9 log_path=x
Runtime identity: candidate=A3.5-dev9 display=x path=x
A3.1 breadcrumb: original player/session ready; START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 scripts: provider_active=1 registered=37 active=12
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=600 exit=1 render_error=0 teardown=1 pause/resume=0/0 paused_input_frames=0 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev9
"""
        result = self.run_fixture(
            "A3.5-dev9",
            "scripts",
            log,
            state("A3.5-dev9", [1.0, 0.0, 0.0], True),
        )
        self.assertEqual("PASS", result["status"])
        closure_check = next(
            check
            for check in result["checks"]
            if check["name"] == "m00_direct_script_closure_registered"
        )
        self.assertTrue(closure_check["passed"])
        self.assertEqual(37, closure_check["detail"])

        incomplete = self.run_fixture(
            "A3.5-dev9",
            "scripts",
            log.replace("registered=37", "registered=36"),
            state("A3.5-dev9", [1.0, 0.0, 0.0], True),
            check_process=False,
        )
        self.assertEqual("FAIL", incomplete["status"])
        incomplete_closure = next(
            check
            for check in incomplete["checks"]
            if check["name"] == "m00_direct_script_closure_registered"
        )
        self.assertFalse(incomplete_closure["passed"])

        runner = (ROOT / "tools" / "run_a35_vita_physical_gate.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("dev9-m00-closure", runner)
        self.assertIn("candidate=A3.5-dev9", runner)
        self.assertIn(
            "expected_self=231fa510a9d39219df93aa2e4b442fe1cd0c9489c1f09f3596df63eea0bf0d88",
            runner,
        )
        self.assertIn(
            "expected_prior_alternate=7d944a8f0fe0425007cbb22b3ea039f8c173b64c4f8f6c4dce71a5670ee02c20",
            runner,
        )
        self.assertIn('--destination-sha256 "$prior_hash"', runner)
        self.assertIn("$phase == dev8-scripts || $phase == dev9-m00-closure", runner)

    def test_dev10_completion_observer_smoke_is_not_mission_completion(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev10 log_path=x
Runtime identity: candidate=A3.5-dev10 display=x path=x
A3.1 breadcrumb: original player/session ready; original mission completion or START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 scripts: provider_active=1 registered=37 active=12
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=600 exit=1 render_error=0 teardown=1 pause/resume=0/0 paused_input_frames=0 start_exit=1 mission_complete/success/star=0/0/0 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev10
"""
        result = self.run_fixture(
            "A3.5-dev10",
            "completion-smoke",
            log,
            state("A3.5-dev10", [1.0, 0.0, 0.0], True),
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["observations"]["start_exit"])
        self.assertEqual(0, result["observations"]["mission_completion_observed"])
        self.assertIn("does not prove mission completion", result["claim_boundary"])

        false_completion = self.run_fixture(
            "A3.5-dev10",
            "completion-smoke",
            log.replace(
                "start_exit=1 mission_complete/success/star=0/0/0",
                "start_exit=0 mission_complete/success/star=1/1/0",
            ),
            state("A3.5-dev10", [1.0, 0.0, 0.0], True),
            check_process=False,
        )
        self.assertEqual("FAIL", false_completion["status"])

        runner = (ROOT / "tools" / "run_a35_vita_physical_gate.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("dev10-completion-smoke", runner)
        self.assertIn("candidate=A3.5-dev10", runner)
        self.assertIn(
            "expected_self=32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339",
            runner,
        )
        dev10_branch = runner.split(
            "elif [[ $phase == dev10-completion-smoke || $phase == dev11-progress-smoke ]]", 1
        )[1].split("fi\n\nrun_json()", 1)[0]
        self.assertIn("RENEGADE_DEV9_GATE_RECEIPT", dev10_branch)
        self.assertIn('candidate == "A3.5-dev9"', dev10_branch)
        self.assertIn('mode == "scripts"', dev10_branch)
        self.assertIn("readiness 15 3", runner)

    def test_dev11_waits_for_original_tutorial_control_before_interaction(self):
        log = """[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev11 log_path=x
Runtime identity: candidate=A3.5-dev11 display=x path=x
A3.1 breadcrumb: original player/session ready; original mission completion or START exits
A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=3 triangles=1
A3.5 scripts: provider_active=1 registered=37 active=12
A3.5 mission progress: frame=420 star/control=1/1 objectives=6 status_1_6=0/-1/-1/-1/-1/-1 active_conversations=0 player=(1.000,2.000,3.000)
A3.5 mission progress: objective 1 pending and original player control available frame=420
A3.1 interactive: complete ready=1 transport=1 level=1 player=1 commando=1 frames=900 exit=1 render_error=0 teardown=1 pause/resume=0/0 paused_input_frames=0 start_exit=1 mission_complete/success/star=0/0/0 perf_fps=60 p50/p95/worst_us=1/2/3
[LIFECYCLE] END status=clean candidate=A3.5-dev11
"""
        result = self.run_fixture(
            "A3.5-dev11",
            "progress-smoke",
            log,
            state("A3.5-dev11", [1.0, 2.0, 3.0], True),
        )
        self.assertEqual("PASS", result["status"])
        self.assertEqual(1, result["observations"]["tutorial_control_handoff_records"])
        self.assertEqual(0, result["observations"]["mission_completion_observed"])
        self.assertIn("does not prove mission completion", result["claim_boundary"])

        no_marker = self.run_fixture(
            "A3.5-dev11",
            "progress-smoke",
            log.replace(
                "A3.5 mission progress: objective 1 pending and original player control available frame=420\n",
                "",
            ),
            state("A3.5-dev11", [1.0, 2.0, 3.0], True),
            check_process=False,
        )
        self.assertEqual("FAIL", no_marker["status"])

        control_locked = self.run_fixture(
            "A3.5-dev11",
            "progress-smoke",
            log.replace("star/control=1/1", "star/control=1/0"),
            state("A3.5-dev11", [1.0, 2.0, 3.0], True),
            check_process=False,
        )
        self.assertEqual("FAIL", control_locked["status"])

        runner = (ROOT / "tools" / "run_a35_vita_physical_gate.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("dev11-progress-smoke", runner)
        self.assertIn("candidate=A3.5-dev11", runner)
        self.assertIn(
            "expected_self=ceb491c609c92657f63cf3cd978d4f7674f41d360cda86b657929210441681ad",
            runner,
        )
        self.assertIn(
            "expected_prior_alternate=32eac8d6471d4a60689678dae854b1850682a700161a2e36c61301cfdff0d339",
            runner,
        )
        self.assertIn(
            "objective 1 pending and original player control available",
            runner,
        )
        self.assertIn("tutorial-control 30 2", runner)

    def test_runner_fallback_keeps_vitacompanion_writes_hash_guarded(self):
        runner = (ROOT / "tools" / "run_a35_vita_physical_gate.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn('write_transport=vitacompanion-ftp', runner)
        self.assertIn('index("file.write.v1")', runner)
        self.assertIn('index("file.rename.v1")', runner)
        self.assertIn('candidate-network-prior-hash.json', runner)
        self.assertIn('fs hash --vdb1 "$remote_executable"', runner)
        self.assertIn('fs push "$candidate_eboot" "$remote_executable"', runner)
        self.assertIn('fs pull --vdb1 "$remote_executable" "$backup_file"', runner)
        self.assertIn('rollback-network-push.json', runner)
        self.assertIn('installed-candidate-hash.json', runner)
        self.assertIn("s#^ux0:data/#ux0:/data/#", runner)
        self.assertIn("rg 'pre-clean-exit'", runner)
        self.assertIn('state_capture/state.json', runner)
        fire_index = runner.index("hold_button_with_refresh fire r")
        analog_index = runner.index('walk-look-forward-press.json" input press left-stick')
        self.assertLess(fire_index, analog_index)
        self.assertIn("hold_button_with_refresh fire r", runner)
        self.assertIn('for refresh in $(seq 1 8)', runner)
        self.assertIn('$name-refresh-$refresh.json', runner)
        status_index = runner.index('preflight-app-status-before.json')
        kill_index = runner.index('preflight-app-kill.json')
        self.assertLess(status_index, kill_index)
        self.assertIn("if jq -e '.result.running == true'", runner[status_index:kill_index])


if __name__ == "__main__":
    unittest.main()
