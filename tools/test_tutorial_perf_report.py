"""Pure-Python tests for tools/tutorial_perf_report.py (no compiler, no device).

Fixtures are synthetic: hand-built lines in the runtime's formats, plus lines
synthesized from the emitters' printf format strings read out of port/ so a
format change in the runtime breaks these tests instead of silently
producing empty reports.
"""
from __future__ import annotations

import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools import tutorial_perf_report as tpr

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_CPP = ROOT / "port/platform/vita/a31_vita_runtime.cpp"
PROFILE_CPP = ROOT / "port/platform/vita/renegade_vita_frame_profile.cpp"
RENDERER_CPP = ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp"
FFP_CPP = ROOT / "port/renderer/vita/ww3d_vita_ffp_program_warm.cpp"
GAMEPLAY_CPP = ROOT / "port/platform/a31_gameplay_boundary.cpp"
ASYNC_LOG_H = ROOT / "port/platform/renegade_async_log.h"
PLATFORM_CPP = ROOT / "port/platform/vita/vita_platform.cpp"
MISSION00_CPP = ROOT / "staging/scripts/Mission00.cpp"


# ---------------------------------------------------------------------------
# Synthetic line builders (runtime formats as of A3.5-dev240)
# ---------------------------------------------------------------------------
def perf(frames, avg_fps, p50, p95, p99, high, slow50=0, slow33=0, low=8000, sim=10000, render=20000,
         rolling=120):
    return (f"A3.5 perf: frames={frames} rolling_samples={rolling} avg_fps={avg_fps:.3f} "
            f"frame_us min/p50/p95/p99/max={low}/{p50}/{p95}/{p99}/{high} slow_over_16_7ms={slow33} "
            f"slow_over_20ms={slow33} slow_over_33ms={slow33} slow_over_50ms={slow50} "
            f"stage_us sync/sim/render=1/{sim}/{render} draws meshes=100 triangles=2000 "
            f"textures req/decode/upload/bind/missing=1/1/1/10/0 state_changes=5 backend_errors=0")


def progress(frame, active="none", status="3/3/3/3/3/3"):
    count = 0 if active == "none" else 1
    return (f"A3.5 mission progress: frame={frame} star/control=1/1 objectives=6 status_1_6={status} "
            f"active_conversations={count} active={active} id/state/action/remark/count=-1/-1/-1/-1/-1 "
            f"text/sound/str/def=-1/-1/0/0 next_seconds=0.000 player=(1.000,2.000,3.000)")


def crumb(subsystem, body, seq=1):
    return f"[A3.5-dev240 {subsystem} {seq:03d}] {body}"


ROUTE = (
    ("logan", "MTU_LOGAN_START", None),
    ("sydney", "MTU_SYDNEY_START", "1/3/3/3/3/3"),
    ("gunner", "MTU_GUNNER_START", "1/1/3/3/3/3"),
    ("vehicles", "MTU_HOTWIRE_INTRO", "1/1/1/3/3/3"),
    ("mobius", "MTU_MOBIUS_REFINERY", "1/1/1/1/3/3"),
    ("base", "MTU_PETROVA_POWER", "1/1/1/1/1/3"),
    ("end", None, "1/1/1/1/1/1"),
)


def tutorial_log(segment_ms=None, windows=3, jitter=(1.0, 1.04, 0.97), extra=None):
    """A complete synthetic tutorial session; ``segment_ms`` maps segment -> mean frame ms."""
    segment_ms = segment_ms or {}
    lines = ["[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev240",
             "Runtime identity: candidate=A3.5-dev240 display=Renegade Vita path=x",
             crumb("vertex-array", "version=1 enabled=1 default=1 acceptance=unassessed"),
             "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0 mix_valid=1",
             "A4 campaign preload: original mission dependency list return archive=M00_Tutorial.mix elapsed_ms=9324",
             "A3.1 breadcrumb: first original render frame PASS meshes=1 vertices=2 triangles=3",
             progress(0)]
    frames, total_us, status = 0, 0.0, "3/3/3/3/3/3"
    slow50, highest = 0, 0
    for segment, conversation, new_status in ROUTE:
        status = new_status or status
        lines.append(progress(frames + 1, conversation or "none", status))
        mean_ms = segment_ms.get(segment, 30.0)
        for index in range(windows):
            mean_us = mean_ms * 1000.0 * jitter[index % len(jitter)]
            frames += 120
            total_us += mean_us * 120
            over = 6 if mean_us * 1.8 > 50000 else 0
            slow50 += over
            high = int(mean_us * 2.2)
            highest = max(highest, high)
            lines.append(perf(frames, frames * 1e6 / total_us, int(mean_us * 0.95), int(mean_us * 1.4),
                              int(mean_us * 1.8), highest, slow50=slow50, slow33=slow50,
                              sim=int(mean_us * 0.3), render=int(mean_us * 0.6)))
            lines.append(f"A3.5 breadcrumb: {frames}-frame checkpoint PASS")
    lines.append(f"A3.5 mission completion: original Combat event observed success=1 frame={frames + 3}")
    lines.append("A4 main menu: Display entry instance=0x0")
    if extra:
        lines.extend(extra)
    return "\n".join(lines) + "\n"


class TempLogs:
    def __init__(self, test: unittest.TestCase):
        self.temp = tempfile.TemporaryDirectory()
        test.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, name: str, text: str | bytes) -> Path:
        path = self.root / name
        if isinstance(text, bytes):
            path.write_bytes(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path


def segment(report, name):
    return next(item for item in report["segments"] if item["segment"] == name)


# ---------------------------------------------------------------------------
# Field parsing and statistics
# ---------------------------------------------------------------------------
class FieldParsingTests(unittest.TestCase):
    def test_grouped_keys_take_bare_prefix_and_names_values_expand(self):
        fields = tpr.parse_fields("frames=240 frame_us min/p50/p95/p99/max=1/2/3/4/5 stage_us sync/sim/render=7/8/9 "
                                  "loaded_dds/tga=2/0 pcm_live=bytes/high/largest:10/20/30 avg_fps=25.629 "
                                  "draws meshes=4 player=(1,2,3)")
        self.assertEqual(fields["frames"], 240)
        self.assertEqual([fields[f"frame_us.{k}"] for k in ("min", "p50", "p95", "p99", "max")], [1, 2, 3, 4, 5])
        self.assertEqual(fields["stage_us.sim"], 8)
        self.assertEqual((fields["loaded_dds"], fields["tga"]), (2, 0))
        self.assertEqual(fields["pcm_live.high"], 20)
        self.assertEqual(fields["avg_fps"], 25.629)
        self.assertEqual(fields["meshes"], 4)
        self.assertEqual(fields["player"], "(1,2,3)")

    def test_duplicate_keys_keep_first_and_mismatched_groups_stay_whole(self):
        fields = tpr.parse_fields("estimated_total_us=5 estimated_total_us=7 a/b=1/2/3 status_1_6=1/0/3")
        self.assertEqual(fields["estimated_total_us"], 5)
        self.assertEqual(fields["estimated_total_us#2"], 7)
        self.assertEqual(fields["a/b"], "1/2/3")
        self.assertEqual(tpr._triplet(fields["status_1_6"]), [1, 0, 3])

    def test_conversation_rules_follow_original_route(self):
        expected = {"MTU_LOGAN_START": "logan", "MTU_GDI_POKE": "logan", "MTU_LOGAN_KEYCARDS": "logan",
                    "MTU_SYDNEY_RADAR": "sydney", "MTU_LOGAN_PREPARE_INFANTRY": "gunner",
                    "MTU_LOGAN_INTRODUCE_BARRACKS": "gunner", "MTU_GUNNER_ION": "gunner",
                    "MTU_LOGAN_INTRODUCE_WEAP": "vehicles", "MTU_HOTWIRE_SQUISH": "vehicles",
                    "MTU_LOGAN_WHATSNEXT": "mobius", "MTU_MOBIUS_REFINERY": "mobius",
                    "MTU_LOGAN_PREPARE_POWER": "base", "MTU_PETROVA_POWER_END": "base",
                    "MTU_LOGAN_OUTRO": "base", "MTU_LIEUTENANT_MCT": "base",
                    "M00TFEA_009IN_NEMG_SND": None, "IDS_MTU_CONVERSATION_01": None}
        for name, segment_name in expected.items():
            self.assertEqual(tpr.conversation_segment(name), segment_name, name)

    def test_every_mission00_conversation_name_is_classified(self):
        names = set(re.findall(r'conv_name = \("(MTU_[A-Z0-9_]+)"\)', MISSION00_CPP.read_text(errors="replace")))
        self.assertGreater(len(names), 40)
        unclassified = sorted(name for name in names if tpr.conversation_segment(name) is None)
        self.assertEqual(unclassified, [])

    def test_objective_mapping_matches_mission00_accomplish_sites(self):
        text = MISSION00_CPP.read_text(errors="replace")
        for objective, conversation in ((1, "MTU_SYDNEY_START"), (2, "MTU_GUNNER_START"),
                                        (3, "MTU_HOTWIRE_INTRO"), (4, "MTU_MOBIUS_REFINERY"),
                                        (5, "MTU_PETROVA_POWER")):
            site = text.index(f"Set_Objective_Status (MTU_OBJECTIVE_0{objective}, OBJECTIVE_STATUS_ACCOMPLISHED)")
            following = text[site:site + 400]
            first = re.search(r'conv_name = \("([A-Z0-9_]+)"\)', following)
            if first and first.group(1) == conversation:
                pass
            else:  # HOTWIRE_INTRO sets the radar marker before its conversation name
                self.assertIn(conversation.replace("MTU_", "MTU_SPEECH_"), text[site - 400:site])
            self.assertEqual(tpr.OBJECTIVE_SEGMENTS[objective], tpr.conversation_segment(conversation))


class QuantileTests(unittest.TestCase):
    def test_single_window_reproduces_logged_percentiles(self):
        anchors = tpr.window_anchors(8000, 30000, 45000, 70000, 120000)
        for q, value in ((0.5, 30000), (0.95, 45000), (0.99, 70000)):
            self.assertAlmostEqual(tpr.mixture_quantile([(120, anchors)], q), value, delta=0.01)

    def test_identical_windows_pool_to_same_values_and_mixture_is_between(self):
        fast = tpr.window_anchors(8000, 16000, 17000, 20000, 25000)
        slow = tpr.window_anchors(8000, 40000, 60000, 80000, 90000)
        self.assertAlmostEqual(tpr.mixture_quantile([(120, fast), (120, fast)], 0.95), 17000, delta=0.01)
        pooled = tpr.mixture_quantile([(120, fast), (120, slow)], 0.5)
        self.assertGreater(pooled, 16000)
        self.assertLess(pooled, 40000)
        self.assertGreater(tpr.mixture_quantile([(120, fast), (120, slow)], 0.95),
                           tpr.mixture_quantile([(120, fast), (120, slow)], 0.5))

    def test_flat_and_missing_anchors(self):
        anchors = tpr.window_anchors(None, 20000, 20000, None, None)
        self.assertEqual(anchors[0], (0.0, 20000.0))
        self.assertAlmostEqual(tpr.mixture_quantile([(10, anchors)], 0.99), 20000, delta=0.01)
        self.assertIsNone(tpr.mixture_quantile([], 0.5))
        self.assertIsNone(tpr.mixture_quantile([(0, anchors)], 0.5))


# ---------------------------------------------------------------------------
# Session analysis
# ---------------------------------------------------------------------------
class PerfAndSegmentTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_window_fps_from_cumulative_average_and_slow_deltas(self):
        log = self.logs.write("perf.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), progress(5, "MTU_LOGAN_START"),
            perf(120, 30.0, 30000, 40000, 50000, 60000, slow50=1, slow33=4, sim=10000, render=20000),
            perf(240, 24.0, 40000, 60000, 70000, 90000, slow50=3, slow33=10, sim=13000, render=25000),
        ]) + "\n")
        report = tpr.analyze_log(log)
        logan = segment(report, "logan")
        self.assertEqual(logan["frames"], 240)
        self.assertAlmostEqual(logan["time_s"], 10.0, places=2)
        self.assertAlmostEqual(logan["fps"], 24.0, places=2)
        self.assertEqual(logan["slow_frames"]["over_50ms"], 3)
        self.assertEqual(logan["slow_frames"]["over_33ms"], 10)
        self.assertAlmostEqual(logan["stage_avg_ms"]["sim"], 13.0, places=2)
        self.assertEqual(logan["window_mean_ms"], [33.333333333333336, 50.0])
        self.assertEqual(logan["worst_ms"], 90.0)
        self.assertEqual(logan["worst_source"], "perf-max")

    def test_full_route_segments_in_original_order(self):
        report = tpr.analyze_log(self.logs.write("route.log", tutorial_log({"gunner": 45.0})))
        names = [t["segment"] for t in report["transitions"]]
        self.assertEqual(names, ["load", "spawn", "logan", "sydney", "gunner", "vehicles", "mobius", "base",
                                 "end", "post"])
        triggers = {t["segment"]: t["trigger"] for t in report["transitions"]}
        self.assertEqual(triggers["sydney"], "conversation MTU_SYDNEY_START")
        self.assertEqual(triggers["end"], "objective 6 accomplished")
        self.assertTrue(triggers["post"].startswith("mission completion"))
        self.assertEqual(report["level"], "M00_Tutorial.mix")
        self.assertTrue(report["tutorial"])
        self.assertEqual(report["integrity"]["tutorial_segments_missing"], [])
        gunner, sydney = segment(report, "gunner"), segment(report, "sydney")
        self.assertAlmostEqual(gunner["mean_frame_ms"], 45.0 * (1.0 + 1.04 + 0.97) / 3, delta=0.05)
        self.assertLess(gunner["fps"], sydney["fps"])
        self.assertGreater(gunner["p95_ms"], gunner["p50_ms"])
        self.assertEqual(report["configuration"]["vertex-array"], "enabled=1 default=1")
        self.assertEqual(report["candidate"], "A3.5-dev240")

    def test_segments_only_move_forward_and_unshown_objectives_do_not_count(self):
        log = self.logs.write("forward.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0, status="-1/-1/-1/-1/-1/-1"),
            progress(2, status="1/1/1/1/1/1"),  # -1 -> 1: not an accomplishment
            progress(10, "MTU_GUNNER_START"),
            progress(20, "MTU_SYDNEY_SHOOT_AGAIN"),  # back-track is a breadcrumb only
            perf(120, 30.0, 30000, 40000, 50000, 60000),
        ]) + "\n")
        report = tpr.analyze_log(log)
        self.assertEqual([t["segment"] for t in report["transitions"]], ["load", "spawn", "gunner"])
        labels = [b["label"] for b in report["breadcrumbs"]]
        self.assertIn("MTU_SYDNEY_SHOOT_AGAIN", labels)
        self.assertNotIn("objective 1 accomplished", labels)
        self.assertIn("log ends inside segment 'gunner' (run incomplete or log pulled mid-run)",
                      report["integrity"]["notes"])
        self.assertEqual(report["integrity"]["tutorial_segments_missing"],
                         ["logan", "sydney", "vehicles", "mobius", "base", "end"])

    def test_non_tutorial_level_is_one_gameplay_segment(self):
        log = self.logs.write("m13.log", "\n".join([
            "A4 campaign: original selection source=M13.mix archive=M13.mix save=0",
            progress(0, "MX0INTRO002"), perf(120, 30.0, 30000, 40000, 50000, 60000)]) + "\n")
        report = tpr.analyze_log(log)
        self.assertEqual([item["segment"] for item in report["segments"]], ["boot", "load", "gameplay"])
        self.assertEqual(report["integrity"]["tutorial_segments_missing"], [])
        self.assertFalse(report["tutorial"])

    def test_tutorial_then_next_mission_keeps_tutorial_identity(self):
        follow_on = ["A4 campaign: original selection source=M01.mix archive=M01.mix save=0",
                     progress(0, "M01_INTRO"), perf(120, 20.0, 50000, 60000, 70000, 80000)]
        report = tpr.analyze_log(self.logs.write("chain.log", tutorial_log(extra=follow_on)))
        self.assertEqual(report["levels"], ["M00_Tutorial.mix", "M01.mix"])
        self.assertEqual(report["level"], "M00_Tutorial.mix")
        self.assertTrue(report["tutorial"])
        self.assertEqual(segment(report, "gameplay")["frames"], 120)
        self.assertEqual(report["integrity"]["tutorial_segments_missing"], [])
        self.assertTrue(any(note.startswith("levels in session:") for note in report["integrity"]["notes"]))

    def test_profile_scopes_aggregate_per_segment(self):
        head = ("A3.6 frame-profile: version=2 window={w} frames=120 avg_frame_us={avg} worst_frame_us={worst} "
                "worst_frame_index=7 scopes_per_frame=900 timed_per_frame=60 exact_calls=2 sample=1/16 clock_ns=250 "
                "est_clock_us=30 overflow=0 inclusive=1 top avg_us/calls_per_frame:")
        log = self.logs.write("profile.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), progress(3, "MTU_LOGAN_START"),
            head.format(w=0, avg=30000, worst=40000) + " Scene=12000/1.0 Soldier_Think=3000/9.5 Bullets=100/2.0",
            perf(120, 33.3, 30000, 35000, 38000, 40000),
            head.format(w=1, avg=34000, worst=45000) + " Scene=14000/1.0 Soldier_Think=5000/10.5",
            perf(240, 31.5, 33000, 40000, 44000, 45000),
        ]) + "\n")
        report = tpr.analyze_log(log, top_scopes=2)
        profile = segment(report, "logan")["profile"]
        self.assertEqual(profile["windows"], 2)
        self.assertAlmostEqual(profile["avg_frame_ms"], 32.0)
        self.assertEqual([s["scope"] for s in profile["top_scopes"]], ["Scene", "Soldier_Think"])
        self.assertEqual(profile["top_scopes"][0]["avg_us_per_frame"], 13000.0)
        self.assertEqual(profile["top_scopes"][1]["calls_per_frame"], 10.0)
        self.assertEqual(profile["scopes_seen"], 3)
        self.assertEqual(report["integrity"]["profile_windows_aligned"], {"checked": 2, "aligned": 2})


class HitchTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_slow_frame_profile_worst_merge_and_window_remainder(self):
        log = self.logs.write("hitch.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), progress(10, "MTU_GUNNER_START"),
            "A4 slow frame: frame=50 total_us=620000 sync_us=1 simulation_us=500000 render_us=119999",
            progress(60, "MTU_GUNNER_RETICULE"),
            "A3.6 frame-profile-worst: window=0 frame_index=49 frame_us=620000 scope_us: Scene=400000 Bullets=9000",
            perf(120, 20.0, 40000, 60000, 90000, 620000, slow50=4),
            "A3.6 frame-profile-worst: window=1 frame_index=9 frame_us=81000 scope_us: Vita_Render_Submit_Mesh=50000",
            perf(240, 20.5, 40000, 55000, 81000, 620000, slow50=6),
        ]) + "\n")
        report = tpr.analyze_log(log)
        hitches = report["hitches"]
        merged = next(h for h in hitches if h["source"] == "slow-frame+profile")
        self.assertEqual(merged["frame"], 50)
        self.assertEqual(merged["scopes_us"]["Scene"], 400000)
        self.assertEqual(merged["breadcrumb"]["label"], "MTU_GUNNER_START")
        self.assertEqual(merged["breadcrumb"]["frames_before_hitch"], 40)
        worst = next(h for h in hitches if h["source"] == "profile-worst")
        self.assertEqual(worst["frame"], 130)
        self.assertTrue(worst["frame_is_approximate"])
        self.assertEqual(worst["breadcrumb"]["label"], "MTU_GUNNER_RETICULE")
        windows = [h for h in hitches if h["source"] == "window"]
        self.assertEqual([w["count_over_threshold"] for w in windows], [3, 1])
        self.assertFalse(windows[0]["exact"])  # window max is the listed slow frame
        self.assertEqual(windows[0]["frame_us"], 90000)
        self.assertEqual(report["hitch_count_individual"], 2)
        self.assertEqual(hitches[0]["frame_ms"], 620.0)

    def test_hitch_threshold_option_and_top_limit(self):
        log = self.logs.write("threshold.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), "A4 slow frame: frame=5 total_us=700000 sync_us=1 simulation_us=1 render_us=1",
            "A4 slow frame: frame=9 total_us=800000 sync_us=1 simulation_us=1 render_us=1"]) + "\n")
        self.assertEqual(len(tpr.analyze_log(log, hitch_ms=750.0)["hitches"]), 1)
        self.assertEqual(len(tpr.analyze_log(log, top_hitches=1)["hitches"]), 1)
        self.assertEqual(tpr.analyze_log(log, top_hitches=1)["hitches_total_listed"], 2)


class CounterTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_memory_pools_caches_audio_and_renderer_counters(self):
        log = self.logs.write("counters.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), progress(2, "MTU_LOGAN_START"),
            crumb("vitagl-pools", "version=1 frame=120 frames=120 immediate_peak=1000 immediate_avg=500 "
                  "immediate_capacity=4096 immediate_overruns=0 circular_peak=2000 circular_slice=8192 "
                  "circular_overruns=1 cpu=0"),
            crumb("vitagl-pools", "version=1 frame=240 frames=120 immediate_peak=3000 immediate_avg=500 "
                  "immediate_capacity=4096 immediate_overruns=2 circular_peak=1500 circular_slice=8192 "
                  "circular_overruns=0 cpu=0"),
            crumb("static-mesh-cache", "frame=120 enabled=1 entries=10 bytes=1048576 hits=1200 builds=10 "
                  "rebuilds=0 ineligible=0 volatile=0 evictions=0 invalidations=0 allocation_failures=0 "
                  "batches=5 triangles=6"),
            crumb("static-mesh-cache", "frame=240 enabled=1 entries=12 bytes=2097152 hits=3600 builds=12 "
                  "rebuilds=1 ineligible=0 volatile=0 evictions=0 invalidations=0 allocation_failures=1 "
                  "batches=5 triangles=6"),
            crumb("static-mesh-cache", "thrash frame=240 rebuild_counts=0 max_frame_builds=4 "
                  "max_frame_upload_bytes=4096 upload_bytes=10000"),
            crumb("gl-state-shadow", "version=1 frame=240 window=120 enabled=1 raster_calls=300 raster_skips=100 "
                  "transform_loads=10 transform_skips=5 texture_matrix_loads=0 texture_matrix_skips=0"),
            crumb("texture-state", "version=1 frame=240 sampler_updates=50 sampler_skips=150 sampler_deferrals=0 "
                  "texenv_writes=1 texenv_skips=2 binds=10 bind_skips=3"),
            crumb("ffp-program-cache", "window: version=1 frame=240 window=120 compiles=2/3 compile_ms=45.500 "
                  "disk_loads=1/0 disk_ms=0.100 rejects=0 mask_changes=5 repatches=1/1 resident=10/12 "
                  "total_compiles=5 total_compile_ms=45 max_compile_ms=30.250"),
            crumb("frame-vblank", "version=1 frame=240 window=120 missed_vblanks=60 max_delta=4 vcount=999"),
            "A3.5 heap: reason=checkpoint frame=240 arena=50000000 in_use=40000000 free=10000000 top_free=1",
            "A3.5 heap: reason=checkpoint frame=360 arena=50000000 in_use=42000000 free=8000000 top_free=1",
            "A3.5 audio: reason=checkpoint frame=240 output_start=1/1/0 output_written/fail/starved=10/0/0 "
            "sample_file=4/3/1 sample_3d=2/2/0 stream=1/1/0 pcm=decodes/hits/evictions/entries/bytes:1/2/3/4/5000 "
            "pcm_live=bytes/high/largest:100/3145728/50 allocated/active/streams=32/1/0 volumes_dialog/cinematic="
            "1.000/1.000 last_error=WAVE decode allocation failed",
            "A4 combat casts: frames=240 window=120 combat_avg_us=4000 soldiers_awake/hibernating_per_frame=6.0/2.0 "
            "per_frame ray_cull/ray_region/aabox_cull/aabox_region/obbox_cull/obbox_region=10.0/1.0/2.0/0.0/0.0/0.0",
            "A4 campaign pacing: frames=120 avg_us time/input/path/control/network/combat/other=10/90/5/20/300/4000/1 "
            "clock_real/sim/drift_ms=4000/3000/1000",
            "A4 campaign pacing: frames=240 avg_us time/input/path/control/network/combat/other=10/89/5/20/300/5000/1 "
            "clock_real/sim/drift_ms=9000/7500/1500",
            "A3.6 vis-census: frame=240 vis_enabled=1 inverted=0 sector=3 missing=0 fallback=0 pvs_true=10/20 "
            "static total/ws/in_frustum/pvs_hidden/vis_saved/collected=100/50/40/30/20/20 "
            "dynamic total/in_frustum/pvs_hidden/vis_saved/collected=10/8/2/1/7 census_us=150",
        ]) + "\n")
        logan = segment(tpr.analyze_log(log), "logan")
        mx, mn, ct = logan["maxima"], logan["minima"], logan["counters"]
        self.assertEqual(mx["vitagl_pools.immediate_peak"], 3000)
        self.assertEqual(mx["vitagl_pools.circular_peak"], 2000)
        self.assertEqual(ct["vitagl_pools.immediate_overruns"], 2)
        self.assertEqual(ct["vitagl_pools.circular_overruns"], 1)
        self.assertEqual(mx["static_mesh_cache.bytes"], 2097152)
        self.assertEqual(ct["static_mesh_cache.hits"], 3600)  # first observation counts from boot
        self.assertEqual(ct["static_mesh_cache.allocation_failures"], 1)
        self.assertEqual(logan["renderer_frames"]["static-mesh-cache"], 240)
        self.assertEqual(mx["static_mesh_cache.max_frame_builds"], 4)
        self.assertEqual(ct["gl_state_shadow.raster_skips"], 100)
        self.assertEqual(ct["texture_state.sampler_skips"], 150)
        self.assertEqual(ct["ffp_programs.compiles"], 5)
        self.assertEqual(ct["ffp_programs.compile_ms"], 45.5)
        self.assertEqual(mx["ffp_programs.max_compile_ms"], 30.25)
        self.assertEqual(ct["vblank.missed"], 60)
        self.assertEqual(mx["heap.in_use_bytes"], 42000000)
        self.assertEqual(mn["heap.free_bytes"], 8000000)
        self.assertEqual(mx["audio.pcm_live_high_bytes"], 3145728)
        self.assertEqual(mx["audio.allocated_samples"], 32)
        self.assertEqual(ct["audio.sample_file_failures"], 1)
        self.assertEqual(logan["audio_errors"][0]["error"], "WAVE decode allocation failed")
        self.assertEqual(logan["combat_casts"]["combat_avg_us"], 4000.0)
        self.assertEqual(logan["combat_casts"]["soldiers_awake"], 6.0)
        self.assertEqual(logan["combat_casts"]["per_frame.ray_cull"], 10.0)
        # 89 x 240 dips below 90 x 120 + 89 x 120 by truncation: signed, not a reset.
        self.assertAlmostEqual(logan["pacing_avg_us"]["input"], 89.0, places=1)
        self.assertAlmostEqual(logan["pacing_avg_us"]["combat"], 5000.0, places=1)
        self.assertEqual(logan["pacing_drift_ms"], 1500.0)
        self.assertEqual(logan["vis_census_avg"]["static.collected"], 20.0)

    def test_markdown_tables_render_counters(self):
        report = tpr.build_report([self.logs.write("route.log", tutorial_log())])
        markdown = tpr.render_markdown(report["reports"], report["comparison"])
        for heading in ("## Segments (A: A)", "### Top profiler scopes (A)", "### Memory and pools high-water (A)",
                        "### Renderer and simulation counters (A)", "### Hitches over 50 ms (A)",
                        "### Level-load milestones (A)", "## Method"):
            self.assertIn(heading, markdown)
        self.assertIn("| gunner | 360 |", markdown)
        self.assertIn("mission dependency preload return — 9324 ms", markdown)


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_truncated_tail_nul_bytes_markers_and_unknown_lines(self):
        text = tutorial_log()
        cut = text[:text.rindex("A3.5 perf:") + 40]  # final perf line cut mid-field
        data = (cut.replace("A3.5 breadcrumb: 120-frame checkpoint PASS",
                            "[runtime-log] dropped lines while the writer was behind: 7\n"
                            "some unknown line = 3\n[runtime-log] TRUNCATED: session log cap reached; "
                            "only priority lines follow\n[runtime-log] suppressed lines past session cap: 12")
                .encode() + b"\x00\x00\x00")
        report = tpr.analyze_log(self.logs.write("cut.log", data))
        integrity = report["integrity"]
        self.assertEqual(integrity["dropped_lines"], 7)
        self.assertEqual(integrity["suppressed_lines"], 12)
        self.assertIsNotNone(integrity["truncated_at_line"])
        self.assertGreaterEqual(integrity["unknown_lines"], 1)
        self.assertGreaterEqual(integrity["unparsed_records"], 1)
        self.assertFalse(integrity["final_line_complete"])
        notes = " ".join(integrity["notes"])
        for phrase in ("session log cap", "dropped by the async log writer", "final line is incomplete",
                       "NUL byte"):
            self.assertIn(phrase, notes)

    def test_empty_and_binary_garbage_logs_do_not_raise(self):
        empty = tpr.analyze_log(self.logs.write("empty.log", ""))
        self.assertEqual(empty["segments"], [])
        self.assertIn("no 'A3.5 perf' windows found: frame-time statistics unavailable", empty["integrity"]["notes"])
        garbage = tpr.analyze_log(self.logs.write("garbage.log", bytes(range(256)) * 4))
        self.assertEqual(garbage["integrity"]["perf_windows"], 0)
        tpr.render_markdown([empty, garbage], tpr.compare(empty, garbage))

    def test_counter_reset_starts_a_new_baseline(self):
        log = self.logs.write("reset.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), perf(240, 30.0, 30000, 40000, 50000, 60000),
            perf(120, 20.0, 50000, 60000, 70000, 80000)]) + "\n")
        report = tpr.analyze_log(log)
        spawn = segment(report, "spawn")
        self.assertEqual(spawn["frames"], 360)
        self.assertEqual(report["integrity"]["counter_resets"], 1)

    def test_sessions_auto_selects_tutorial_and_index_override(self):
        first = tutorial_log()
        second = "[LIFECYCLE] START status=begin mode=append candidate=A3.5-dev240\nA3.5 startup: x startup_ms=5\n"
        log = self.logs.write("two.log", first + second)
        auto = tpr.analyze_log(log)
        self.assertEqual(auto["integrity"]["sessions_found"], 2)
        self.assertEqual(auto["integrity"]["session_analyzed"], 0)
        last = tpr.analyze_log(log, session="-1")
        self.assertEqual(last["integrity"]["session_analyzed"], 1)
        with self.assertRaises(ValueError):
            tpr.analyze_log(log, session="5")

    def test_one_appended_log_compares_two_sessions(self):
        log = self.logs.write("appended.log", tutorial_log({"gunner": 45.0}) + tutorial_log({"gunner": 30.0}))
        report = tpr.build_report([log, log], sessions=["0", "1"])
        self.assertEqual([r["integrity"]["session_analyzed"] for r in report["reports"]], [0, 1])
        rows = {row["segment"]: row for row in report["comparison"]["rows"]}
        self.assertEqual(rows["gunner"]["noise"]["verdict"], "B faster")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(tpr.main([str(log), str(log), "--session", "0", "--session", "1"]), 0)
        self.assertIn("B faster", stdout.getvalue())


class ABTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_faster_segment_detected_and_identical_segments_within_noise(self):
        a = self.logs.write("a.log", tutorial_log({"gunner": 45.0}))
        b = self.logs.write("b.log", tutorial_log({"gunner": 30.0}).replace(
            "version=1 enabled=1 default=1", "version=1 enabled=0 default=1"))
        report = tpr.build_report([a, b], labels=["dev240", "RVVA1-0"])
        rows = {row["segment"]: row for row in report["comparison"]["rows"]}
        self.assertEqual(rows["gunner"]["noise"]["verdict"], "B faster")
        self.assertLess(rows["gunner"]["mean_frame_ms"]["delta"], -14.0)
        self.assertGreater(rows["gunner"]["fps"]["percent"], 40.0)
        self.assertEqual(rows["sydney"]["noise"]["verdict"], "within noise")
        self.assertEqual(rows["sydney"]["fps"]["delta"], 0.0)
        self.assertNotIn("boot", rows)
        self.assertEqual(report["comparison"]["configuration_differences"],
                         [{"switch": "vertex-array", "a": "enabled=1 default=1", "b": "enabled=0 default=1"}])
        markdown = tpr.render_markdown(report["reports"], report["comparison"])
        self.assertIn("## A/B delta (B minus A)", markdown)
        self.assertIn("`vertex-array` enabled=1 default=1→enabled=0 default=1", markdown)

    def test_noise_verdict_needs_two_windows_and_flags_route_mismatch(self):
        self.assertEqual(tpr.noise_verdict({"window_mean_ms": [30.0]}, {"window_mean_ms": [20.0, 21.0]})["verdict"],
                         "insufficient windows (need >=2 per arm)")
        verdict = tpr.noise_verdict({"window_mean_ms": [30.0, 31.0], "mean_frame_ms": 30.5, "frames": 240},
                                    {"window_mean_ms": [30.0, 31.0, 30.5, 30.2, 30.1], "mean_frame_ms": 30.4,
                                     "frames": 600})
        self.assertEqual(verdict["verdict"], "within noise")
        self.assertIn("route_note", verdict)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.logs = TempLogs(self)

    def test_cli_writes_markdown_and_json(self):
        log = self.logs.write("route.log", tutorial_log())
        md, js = self.logs.root / "out.md", self.logs.root / "out.json"
        self.assertEqual(tpr.main([str(log), "--out-md", str(md), "--out-json", str(js)]), 0)
        data = json.loads(js.read_text())
        self.assertEqual(data["schema_version"], tpr.SCHEMA_VERSION)
        self.assertIsNone(data["comparison"])
        self.assertTrue(md.read_text().startswith("# Tutorial performance report"))

    def test_cli_stdout_and_errors(self):
        log = self.logs.write("route.log", tutorial_log())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(tpr.main([str(log), str(log)]), 0)
        self.assertIn("## A/B delta", stdout.getvalue())
        with redirect_stderr(io.StringIO()):
            self.assertEqual(tpr.main([str(self.logs.root / "missing.log")]), 2)
            with self.assertRaises(SystemExit):
                tpr.main([str(log), str(log), str(log)])


# ---------------------------------------------------------------------------
# Emitter contract: synthesize lines from the runtime's own format strings
# ---------------------------------------------------------------------------
CONVERSION_RE = re.compile(r"%([-+ #0]*)(\d+)?(?:\.(\d+))?(ll|l|z|hh|h)?([diuxXfsp%])")


def emitter_format(path: Path, anchor: str) -> str:
    """Join the adjacent C string literals that start right after ``anchor``."""
    text = path.read_text(errors="replace")
    match = re.search(anchor, text)
    if match is None:
        raise AssertionError(f"emitter anchor not found in {path.name}: {anchor}")
    position = match.end() - 1
    parts = []
    while True:
        literal = re.match(r'"((?:[^"\\]|\\.)*)"', text[position:])
        if literal is None:
            raise AssertionError(f"no string literal after anchor {anchor}")
        parts.append(literal.group(1))
        position += literal.end()
        position += len(re.match(r"\s*", text[position:]).group(0))
        if not text.startswith('"', position):
            break
    return "".join(parts).replace("\\n", "")


def synthesize(fmt: str, start: int = 1000) -> str:
    counter = [start]

    def replace(match: re.Match) -> str:
        flags, width, precision, _, kind = match.groups()
        if kind == "%":
            return "%"
        counter[0] += 7
        value = counter[0]
        if kind in "diu":
            return str(value).zfill(int(width)) if width and "0" in (flags or "") else str(value)
        if kind in "xX":
            return f"{value:0{int(width or 1)}X}"
        if kind == "f":
            return f"{value + 0.5:.{int(precision) if precision else 6}f}"
        if kind == "p":
            return f"0x{value:08x}"
        return f"NAME{value}"

    return CONVERSION_RE.sub(replace, fmt)


def runtime_line(path: Path, anchor: str, start: int = 1000) -> str:
    return synthesize(emitter_format(path, anchor), start)


def breadcrumb_line(path: Path, subsystem: str, lookahead: str, start: int = 1000) -> str:
    anchor = rf'Vita_Append_A22_Runtime_Breadcrumb\("{re.escape(subsystem)}",\s*"(?={lookahead})'
    return f"[A3.5-dev240 {subsystem} 042] " + runtime_line(path, anchor, start)


class EmitterContractTests(unittest.TestCase):
    def test_breadcrumb_wrapper_format_matches_parser(self):
        fmt = emitter_format(PLATFORM_CPP, r'snprintf\(queued, sizeof\(queued\),\s*"')
        self.assertEqual(fmt, "[%s %s %03u] %s")
        self.assertIsNotNone(tpr.RE_BREADCRUMB.match("[A3.5-dev240 vitagl-pools 1042] version=1 frame=1"))

    def test_async_log_markers_match_parser(self):
        text = ASYNC_LOG_H.read_text()
        self.assertIn('"[runtime-log] dropped lines while the writer was behind: "', text)
        self.assertIn('"[runtime-log] TRUNCATED: session log cap reached; only priority lines follow\\n"', text)
        self.assertIn('"[runtime-log] suppressed lines past session cap: "', text)

    def test_runtime_emitters_parse(self):
        perf_line = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 perf: )')
        fields = tpr.parse_fields(tpr.RE_PERF.match(perf_line).group("body"))
        for key in ("frames", "rolling_samples", "avg_fps", "frame_us.min", "frame_us.p50", "frame_us.p95",
                    "frame_us.p99", "frame_us.max", "slow_over_16_7ms", "slow_over_20ms", "slow_over_33ms",
                    "slow_over_50ms", "stage_us.sync", "stage_us.sim", "stage_us.render"):
            self.assertIn(key, fields, key)
        self.assertIsInstance(fields["avg_fps"], float)
        slow = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 slow frame: )')
        self.assertEqual(len([g for g in tpr.RE_SLOW.match(slow).groups() if g is not None]), 5)
        pacing = tpr.parse_fields(tpr.RE_PACING.match(
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 campaign pacing: )')).group("body"))
        self.assertIn("avg_us.combat", pacing)
        self.assertIn("drift_ms", pacing)
        casts = tpr.parse_fields(tpr.RE_CASTS.match(
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 combat casts: )')).group("body"))
        for key in ("window", "combat_avg_us", "soldiers_awake", "per_frame.ray_cull", "per_frame.obbox_region"):
            self.assertIn(key, casts)
        heap = tpr.parse_fields(tpr.RE_HEAP.match(
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 heap: )')).group("body"))
        self.assertTrue({"arena", "in_use", "free"} <= set(heap))
        audio_line = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 audio: reason=%s frame=%u output_start)')
        audio = tpr.parse_fields(tpr.RE_AUDIO.match(audio_line).group("body"))
        for key in ("pcm_live.high", "pcm.bytes", "allocated", "fail", "starved"):
            self.assertIn(key, audio)
        for key in ("sample_file", "sample_3d", "stream"):
            self.assertEqual(len(tpr._triplet(audio[key])), 3, key)
        self.assertIsNotNone(tpr.RE_LAST_ERROR.search(audio_line))
        progress_line = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 mission progress: frame=)')
        match = tpr.RE_PROGRESS.match(progress_line)
        body = tpr.parse_fields(match.group("body"))
        self.assertEqual(len(tpr._triplet(body["status_1_6"])), 6)
        self.assertTrue(body["active"].startswith("NAME"))
        control = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 mission progress: original player control)')
        self.assertIsNotNone(tpr.RE_CONTROL.match(control))
        checkpoint = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 breadcrumb: %u-frame checkpoint)')
        self.assertIsNotNone(tpr.RE_CHECKPOINT.match(checkpoint))
        first = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.1 breadcrumb: first original render frame)')
        self.assertIsNotNone(tpr.RE_FIRST_FRAME.match(first))
        complete = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.1 interactive: complete )')
        self.assertIn("perf_fps", tpr.parse_fields(tpr.RE_INTERACTIVE_COMPLETE.match(complete).group("body")))
        residual = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=\[LIFECYCLE\] SESSION residual )')
        self.assertIsNotNone(tpr.RE_SESSION_RESIDUAL.match(residual))
        preload = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 %s round-4 preload: )')
        self.assertIsNotNone(tpr.RE_PRELOAD.match(preload))
        selection = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 campaign: original selection source=)')
        self.assertIsNotNone(tpr.RE_LEVEL_SELECT.match(selection))
        completion = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 mission completion: original Combat event)')
        self.assertIsNotNone(tpr.RE_COMPLETION.match(completion))
        killed = runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 mission completion: original Combat star-killed)')
        self.assertIsNone(tpr.RE_COMPLETION.match(killed))
        log = TempLogs(self).write("killed.log", "\n".join([
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            progress(0), progress(5, "MTU_LOGAN_START"), killed]) + "\n")
        report = tpr.analyze_log(log)
        self.assertEqual(report["load_milestones"][-1]["label"], "player killed")
        self.assertEqual(report["transitions"][-1]["segment"], "logan")

    def test_profiler_emitters_parse(self):
        head = runtime_line(PROFILE_CPP, r'"(?=A3\.6 frame-profile: version=2 )')
        self.assertTrue(head.endswith("top avg_us/calls_per_frame:"))
        line = head + " CombatManager::Think=5000/1.0 Soldier_Think=900/12.5"
        body = tpr.RE_PROFILE.match(line).group("body")
        fields = tpr.parse_fields(body.partition(" top avg_us/calls_per_frame:")[0])
        for key in ("window", "frames", "avg_frame_us", "worst_frame_us", "worst_frame_index", "est_clock_us",
                    "overflow"):
            self.assertIn(key, fields)
        self.assertEqual(len(tpr.SCOPE_RE.findall(body.partition(":")[2])), 2)
        worst = runtime_line(PROFILE_CPP, r'"(?=A3\.6 frame-profile-worst: )') + " Scene=4000 Bullets=10"
        self.assertEqual(tpr.WORST_SCOPE_RE.findall(tpr.RE_PROFILE_WORST.match(worst).group("scopes")),
                         [("Scene", "4000"), ("Bullets", "10")])
        clock = runtime_line(PROFILE_CPP, r'A30_Vita_Log\("(?=A3\.6 frame-profile: clock-cost )')
        self.assertIsNotNone(tpr.RE_PROFILE_CLOCK.match(clock))
        configured = runtime_line(PROFILE_CPP, r'A30_Vita_Log\("(?=A3\.6 frame-profile: configured )')
        self.assertIn("enabled", tpr.parse_fields(tpr.RE_PROFILE_CONFIG.match(configured).group("body")))

    def test_renderer_breadcrumbs_parse(self):
        cases = (
            (RENDERER_CPP, "vitagl-pools", "version=1 frame=",
             ("immediate_peak", "immediate_capacity", "immediate_overruns", "circular_peak", "circular_overruns")),
            (RENDERER_CPP, "static-mesh-cache", "frame=%u enabled",
             ("frame", "bytes", "entries", "hits", "builds", "rebuilds", "allocation_failures")),
            (RENDERER_CPP, "static-mesh-cache", "thrash ",
             ("max_frame_builds", "max_frame_upload_bytes", "upload_bytes")),
            (RENDERER_CPP, "skin-deform-cache", "frame=", ("bytes", "hits", "misses", "allocation_failures")),
            (RENDERER_CPP, "vertex-array", "frame=", ("batches", "scratch_bytes")),
            (RENDERER_CPP, "gl-state-shadow", "version=1 frame=",
             ("raster_calls", "raster_skips", "transform_loads", "transform_skips")),
            (RENDERER_CPP, "texture-state", "version=1 frame=",
             ("sampler_updates", "sampler_skips", "texenv_writes", "binds", "bind_skips")),
            (RENDERER_CPP, "frame-vblank", "version=1 frame=", ("missed_vblanks", "max_delta")),
            (FFP_CPP, "ffp-program-cache", "window: ", ("compiles", "compile_ms", "disk_loads", "max_compile_ms")),
        )
        for path, subsystem, lookahead, keys in cases:
            line = breadcrumb_line(path, subsystem, lookahead)
            match = tpr.RE_BREADCRUMB.match(line)
            self.assertIsNotNone(match, line)
            body = match.group("body")
            labelled = tpr.BREADCRUMB_LABEL_RE.match(body)
            payload = labelled.group(2) if labelled else body.replace("thrash ", "", 1)
            fields = tpr.parse_fields(payload)
            for key in keys:
                self.assertIn(key, fields, f"{subsystem}: {key}")
        for subsystem, lookahead in (("vertex-array", "version=1 enabled"), ("gl-state-shadow", "version=1 enabled"),
                                     ("static-mesh-cache", "version=1 enabled"),
                                     ("skin-deform-cache", "version=1 enabled")):
            fields = tpr.parse_fields(breadcrumb_line(RENDERER_CPP, subsystem, lookahead).split("] ", 1)[1])
            self.assertEqual(fields.get("version"), 1)
            self.assertIn("enabled", fields)
            self.assertNotIn("frame", fields)

    def test_vis_census_concatenated_format_parses(self):
        line = runtime_line(GAMEPLAY_CPP, r'A30_Vita_Log\("(?=A3\.6 vis-census: )')
        fields = tpr.parse_fields(tpr.RE_VIS.match(line).group("body"))
        for key in ("static.collected", "dynamic.collected", "static.vis_saved", "census_us"):
            self.assertIn(key, fields)

    def test_synthesized_emitter_log_feeds_every_aggregate(self):
        lines = [
            "A4 campaign: original selection source=M00_Tutorial.mix archive=M00_Tutorial.mix save=0",
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.1 breadcrumb: first original render frame)'),
            progress(0), progress(4, "MTU_LOGAN_START"),
            runtime_line(PROFILE_CPP, r'"(?=A3\.6 frame-profile: version=2 )') + " Scene=5000/1.0",
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 perf: )'),
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 campaign pacing: )'),
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A4 combat casts: )'),
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 heap: )'),
            runtime_line(RUNTIME_CPP, r'A30_Vita_Log\("(?=A3\.5 audio: reason=%s frame=%u output_start)'),
            runtime_line(GAMEPLAY_CPP, r'A30_Vita_Log\("(?=A3\.6 vis-census: )'),
            breadcrumb_line(RENDERER_CPP, "vitagl-pools", "version=1 frame="),
            breadcrumb_line(RENDERER_CPP, "static-mesh-cache", "frame=%u enabled"),
            breadcrumb_line(RENDERER_CPP, "vertex-array", "frame="),
            breadcrumb_line(RENDERER_CPP, "gl-state-shadow", "version=1 frame="),
            breadcrumb_line(RENDERER_CPP, "texture-state", "version=1 frame="),
            breadcrumb_line(RENDERER_CPP, "frame-vblank", "version=1 frame="),
            breadcrumb_line(FFP_CPP, "ffp-program-cache", "window: "),
        ]
        report = tpr.analyze_log(TempLogs(self).write("emitters.log", "\n".join(lines) + "\n"))
        logan = segment(report, "logan")
        self.assertEqual(logan["perf_windows"], 1)
        self.assertIsNotNone(logan["fps"])
        self.assertEqual(logan["profile"]["windows"], 1)
        self.assertTrue(logan["pacing_avg_us"])
        self.assertTrue(logan["combat_casts"])
        self.assertTrue(logan["vis_census_avg"])
        for key in ("heap.in_use_bytes", "audio.pcm_live_high_bytes", "vitagl_pools.immediate_peak",
                    "static_mesh_cache.bytes", "vertex_array.scratch_bytes"):
            self.assertIn(key, logan["maxima"], key)
        for key in ("gl_state_shadow.raster_calls", "texture_state.sampler_updates", "vblank.missed",
                    "ffp_programs.compiles"):
            self.assertIn(key, logan["counters"], key)
        self.assertEqual(report["integrity"]["unparsed_records"], 0)


if __name__ == "__main__":
    unittest.main()
