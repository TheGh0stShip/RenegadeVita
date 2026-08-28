#!/usr/bin/env python3

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VitaRouteSessionRunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = (ROOT / "tools" / "run_a35_vita_route_session.sh").read_text(encoding="utf-8")

    def test_candidate_and_predecessor_are_exactly_hash_guarded(self):
        self.assertIn("candidate=A3.5-dev48", self.runner)
        self.assertIn(
            "expected_self=0e61044df081b36b1a74da88c6157149cc27e818fca26f7bde537d00f710ec23",
            self.runner,
        )
        self.assertIn(
            "expected_elf=a4416e16a4678c645e492c91f55c4fc0decae095fb4589d947d9559ee1dc63bd",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev46=bb42fa9fbbf80e6eb90add5d3ae1bed708f1a9847f61ddc3d3fa441b4a10b244",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev45=950950e04e6ae541ef076a9ae017f47af846ebaab169879621c2b7ea54d741b5",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev44=e24e6b7a4b27dc749a1e59ffae7276406fbeea0794c5891c066b75db3055e016",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev43=c81cf891597d97720190b997d79cb67b56fe12911349f31b7ae9e3dfffaba935",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev42=c964465bffe52ab14f2399c2518b2cbb4c8cf76d2b5780f24c20b4c3b43a2cfe",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev41=cc6bd37485ba25b60f7e78f90c5b4845afb85102f82e02ed7760b861d65e9309",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev40=f59209cdecd00dcc398e8c8a13b7af96e2a2c75ad6d737c2ec33b80069ae9461",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev39=ccd306883de8d18f6dd72c2d247e905727c970f31ad095aa52c8b19dde435d0f",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev38=d8293dc331ee4460f5ee4527f08d05085aed263fbfb9846550cf35b575b1184b",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev37=f4d05d0c79d0a63ec9c24a94e875f9a46555d8e813aa6272ec3eb50f20e23bce",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev36=4451964aeefd1c0e5f690852e7111986f28006dc45900aff292b06d8cdb9e636",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev35=1dbb00a3191b1cb11272ee1faf0ca083e480284b9e6d78d7c1c94a287ea3ec56",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev34=72aa828d090d3e74180b03582378c73c25a737b0ea7ffdc728c80564c35260ef",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev33=3f3f0519c16280137ab656d2761f7c659e54170cebeed00a09d316db0d515465",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev32=a45d2a8b54c48e89327eab498bf9a439f497093e85719ffbce76de664a3eef12",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev31=8375f3f30fe57e309bcf2b68b25a1e5f4a3a99f24953bbd36bd940cc2005c424",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev30=c3810e776f21ce7937c6a261893aed92ed3e5e0cafadf99e15020cb91094c52b",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev29=899df03c98153d8888d00192cf7ef40875901f77aaca96b7c7a2434883cd53f0",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev28=5d1226557ac8b2ce5d66c0f9ae8b59977af3fa3bc16fbb2b18ffbc39802b5aed",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev27=aa37b69ed826d4fbf5ad93506727a5aba4426bbddb16741afe48dfdc5bf9806d",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev26=8b2ff768f64d2f6d1ac0e79061eb734bb6c9cfa77246bdaebb82924a44de5b6f",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev25=08cdf12864c0eb67d0675983f61bc7543085f4713d89975015847189f5684d4c",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev24=1738526a3d556d56a02a077fc92ba115021d44144f4bdf1cbb0e673a0f251e30",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev23=9dbfbce006634472aec5ce13b300d3924f14e6d24fde6e6cd3730acbe22a12cd",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev22=528e1e87b97a88047c0b5ab65f1d7bba6d0f03a9edb37a1bca16b04bc3900bcf",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev21=93ad509992d1f2e286dbcb56648da1bf8fe966911d6fe0707a9ca7f07b9b66ec",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev20=5e4cc4a4ac44173158b5b897a733de6d46fb33390d7233641b760f83a86ce24f",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev19=901fd5a0d7cb137a782ee42c666a91e9d9ca56a7f95397703468b3044f92e125",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev18=058a10a594a8038833d8cced9a4b7a5207a4100079da44beef5c645a7ca69278",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev17=6df5bc65e1c3846b65e1c659e7d355acc17b090ec22985215f94f02a7280d3ec",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev16=4dd1f7fd4a10ee26605986c58c1aad9e63986fbbf5c91e48326c9d4a0c81169f",
            self.runner,
        )
        self.assertIn(
            "expected_prior_dev7=7367b04a3fd19121e5360a0bfc8dd088d377c1063f060811a282056bbefeefd5",
            self.runner,
        )
        self.assertIn('expected_prior_hashes=("$expected_prior_dev46" "$expected_prior_dev45" "$expected_prior_dev44" "$expected_prior_dev43" "$expected_prior_dev42" "$expected_prior_dev41" "$expected_prior_dev40" "$expected_prior_dev39" "$expected_prior_dev38" "$expected_prior_dev37" "$expected_prior_dev36" "$expected_prior_dev35" "$expected_prior_dev34" "$expected_prior_dev33" "$expected_prior_dev32" "$expected_prior_dev31" "$expected_prior_dev30" "$expected_prior_dev29" "$expected_prior_dev28" "$expected_prior_dev27" "$expected_prior_dev26" "$expected_prior_dev25" "$expected_prior_dev24" "$expected_prior_dev23" "$expected_prior_dev22" "$expected_prior_dev21" "$expected_prior_dev20" "$expected_prior_dev19" "$expected_prior_dev18" "$expected_prior_dev17" "$expected_prior_dev16" "$expected_prior_dev7")', self.runner)
        self.assertIn('hash_is_admitted_prior "$prior_hash"', self.runner)
        self.assertIn('fs hash --vdb1 "$remote_executable"', self.runner)
        self.assertIn('fs pull --vdb1 "$remote_executable" "$backup_file"', self.runner)
        self.assertIn('--destination-sha256 "$prior_hash"', self.runner)
        self.assertIn("a35-dev48-runtime.log", self.runner)
        self.assertNotIn("dev15", self.runner)

    def test_crash_collection_is_baselined_and_candidate_symbol_aware(self):
        self.assertIn("collect_crash_baseline()", self.runner)
        self.assertIn("crash-prelaunch-snapshot.json", self.runner)
        self.assertIn("debug crash collect", self.runner)
        self.assertIn("--crash-root ux0:/data", self.runner)
        self.assertIn("--snapshot-only", self.runner)
        self.assertIn("collect_postrun_crashes()", self.runner)
        self.assertIn("vdb_crash_snapshot_delta.py", self.runner)
        self.assertIn("crash-$label-snapshot.json", self.runner)
        self.assertIn("crash-$label-delta.json", self.runner)
        self.assertIn('fs pull --vdb1 "$remote_path" "$local_dump"', self.runner)
        self.assertIn("debug crash report", self.runner)
        self.assertIn("--core-sha256 \"$dump_sha\"", self.runner)
        self.assertIn("--elf \"$candidate_elf\"", self.runner)
        self.assertIn("--elf-sha256 \"$expected_elf\"", self.runner)
        self.assertIn("--module-name RenegadeVitaA31", self.runner)
        self.assertNotIn("--since" + "-bundle", self.runner)
        self.assertNotIn("baseline" + "-manifest-sha256", self.runner)
        self.assertIn("collect_postrun_crashes nonclean-exit", self.runner)
        self.assertIn("collect_postrun_crashes failure", self.runner)
        self.assertLess(
            self.runner.index("collect_crash_baseline"),
            self.runner.index("launch_requested=1"),
        )

    def test_record_and_replay_use_only_bounded_one_shot_markers(self):
        self.assertIn("input-record-once.flag", self.runner)
        self.assertIn("input-replay-once.flag", self.runner)
        self.assertIn("input-route-v1.bin", self.runner)
        self.assertIn('[[ $session_mode == record || $session_mode == replay ]]', self.runner)
        self.assertIn('python3 "$validator" --reject-truncated', self.runner)
        self.assertIn('[[ $route_hash == "$replay_route_hash" ]]', self.runner)
        self.assertIn("RENEGADE_ROUTE_FILE", self.runner)
        self.assertIn("RENEGADE_MIN_REPLAY_SAMPLES", self.runner)
        self.assertIn("minimum_replay_samples=${RENEGADE_MIN_REPLAY_SAMPLES:-4000}", self.runner)
        self.assertIn('python3 "$validator" --reject-truncated "$route_source"', self.runner)
        self.assertIn("source_sample_count", self.runner)
        self.assertIn("replay_sample_count", self.runner)
        self.assertIn("selected replay route has only %u samples", self.runner)
        self.assertIn("admitted replay route has only %u samples", self.runner)
        self.assertIn('write_push replay-route-source-upload "$route_source" "$remote_route"', self.runner)
        self.assertIn('app launch --wait-running --timeout 45', self.runner)
        self.assertIn("launch_app_bounded", self.runner)
        self.assertIn('rg -Fq "replay complete: injecting clean exit" "$evidence_root/latest-session.log"', self.runner)
        self.assertIn('rg -Fq "START exit request detected" "$evidence_root/latest-session.log"', self.runner)
        self.assertIn("for attempt in 1 2 3", self.runner)

    def test_corrected_dialogue_candidate_rejects_stale_pre_dialogue_route(self):
        self.assertIn(
            "stale_pre_dialogue_route=5ef2ee8f2ed5d4f301ec20ef95c73fe7aea9956a32e9cc41aecf84999191e895",
            self.runner,
        )
        self.assertIn(
            'replay route is stale for %s: it predates the TranslateDB dialogue-timing fix; run record to create a fresh route',
            self.runner,
        )
        self.assertLess(
            self.runner.index("stale_pre_dialogue_route"),
            self.runner.index("launch_requested=1"),
        )
        self.assertLess(
            self.runner.index("launch_requested=1"),
            self.runner.rindex("launch_app_bounded"),
        )

    def test_human_recording_waits_for_original_control_and_clean_exit(self):
        first_render = self.runner.index("first original render frame PASS")
        tutorial_control = self.runner.index('wait_for_log_marker "star/control=1/1"')
        prelaunch_notice = self.runner.index("PRELAUNCH_USER_NOTICE")
        loading_gate = self.runner.index("LOADING_SCREEN_VISUAL_GATE")
        user_ready = self.runner.index("TELEMETRY_READY")
        gameplay_activation = self.runner.index("gameplay activation: active=1")
        app_wait = self.runner.index('app wait --exit-or-crash --timeout 600')
        no_pull_message = self.runner.index("continuing so an active player is not pulled out of the game")
        self.assertLess(prelaunch_notice, first_render)
        self.assertLess(prelaunch_notice, loading_gate)
        self.assertLess(loading_gate, first_render)
        self.assertLess(first_render, tutorial_control)
        self.assertLess(tutorial_control, gameplay_activation)
        self.assertLess(gameplay_activation, no_pull_message)
        self.assertLess(no_pull_message, user_ready)
        self.assertLess(user_ready, app_wait)
        self.assertNotIn("candidate did not arm the input route at original player control", self.runner)
        self.assertIn("Press Select once, then START to finish", self.runner)
        self.assertIn("wait about 10 seconds for original control to return", self.runner)
        self.assertIn("background_upright_fullscreen_text_bar_aligned_progress_moving", self.runner)
        self.assertIn("No log-only result will be treated as visual acceptance", self.runner)

    def test_route_gate_requires_skin_deformation_and_unchanged_retail(self):
        self.assertIn("Capture: PASS candidate=$candidate phase=original-loading-screen reason=level-ready", self.runner)
        self.assertIn("original-loading-screen-level-ready", self.runner)
        self.assertIn('loading-screen-frame.bmp', self.runner)
        self.assertIn('loading-screen-state.json', self.runner)
        self.assertIn('loading_validator=$project_root/tools/validate_vita_loading_capture.py', self.runner)
        self.assertIn('python3 "$loading_validator"', self.runner)
        self.assertIn('loading-screen-validation.json', self.runner)
        self.assertIn('loading_screen_capture_path:$loading_capture', self.runner)
        self.assertLess(
            self.runner.index('python3 "$loading_validator"'),
            self.runner.index("new_route_retained=1"),
        )
        self.assertLess(
            self.runner.index('[[ $(json_hash "$evidence_root/retail-after-hash.json") == "$retail_hash" ]]'),
            self.runner.index("new_route_retained=1"),
        )
        self.assertIn("first original deformed skin submission", self.runner)
        self.assertIn("deformation_failures=0", self.runner)
        self.assertIn('fs hash --vdb1 "$remote_retail"', self.runner)
        self.assertIn('[[ $(json_hash "$evidence_root/retail-after-hash.json") == "$retail_hash" ]]', self.runner)
        self.assertIn('loading_screen_visual_gate:"schema-v4 metadata, native BMP, and broad full-frame content extent validated; operator observation still required before visual acceptance"', self.runner)
        self.assertIn("visual correctness requires physical user observation", self.runner)

    def test_route_gate_requires_indexed_sky_state_execution(self):
        self.assertIn("A3\\.5 indexed: submissions=[1-9]", self.runner)
        self.assertIn("state_applications=[1-9]", self.runner)
        self.assertIn("rejected=0", self.runner)

    def test_route_gate_requires_weapon_progression(self):
        self.assertIn("route did not reach original weapon/pistol progression", self.runner)
        self.assertIn("A3\\.5 effects:.* weapon=Weapon_Pistol_Player/[1-9][0-9]* .*fired_total=[1-9][0-9]*", self.runner)
        self.assertLess(
            self.runner.index('python3 "$validator" --reject-truncated "$evidence_root/input-route-v1.bin"'),
            self.runner.index("route did not reach original weapon/pistol progression"),
        )
        self.assertLess(
            self.runner.index("route did not reach original weapon/pistol progression"),
            self.runner.rindex("new_route_retained=1"),
        )

    def test_vdb_input_and_transport_negotiation_are_explicit(self):
        self.assertIn("capabilities --with-debugger", self.runner)
        self.assertIn('index("file.write.v1")', self.runner)
        self.assertIn('index("file.replace.v1")', self.runner)
        self.assertIn("write_transport=vitacompanion-ftp", self.runner)
        self.assertIn('install -m 0600 /dev/null "$marker_file"', self.runner)
        self.assertIn('fs push "$marker_file" "$path"', self.runner)
        self.assertIn("input release all", self.runner)

    def test_runner_pulls_candidate_log_before_killing_failed_session(self):
        self.assertIn("pull_candidate_log()", self.runner)
        self.assertIn("failure-before-kill", self.runner)
        self.assertIn("failure-after-kill", self.runner)
        self.assertLess(
            self.runner.index("pull_candidate_log failure-before-kill"),
            self.runner.index("cleanup-app-status"),
        )

    def test_runner_parses_and_rolls_back_every_failed_deployment(self):
        subprocess.run(
            ["bash", "-n", str(ROOT / "tools" / "run_a35_vita_route_session.sh")],
            check=True,
        )
        self.assertIn("if ((status != 0 && deployed)); then", self.runner)
        self.assertIn("route_source_uploaded=0", self.runner)
        self.assertIn('[[ $session_mode == record || $route_source_uploaded == 1 ]]', self.runner)
        self.assertIn("rollback-uploaded-route", self.runner)
        self.assertNotIn("status != 0 && deployed && !readiness_reached", self.runner)
        self.assertIn("failed session executable rollback_status=%d", self.runner)


if __name__ == "__main__":
    unittest.main()
