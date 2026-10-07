#!/usr/bin/env python3
"""Pure-Python checks for the RVTB1 fixed tutorial benchmark.

No compiler, device or emulator: this mirrors the percentile / mean / FNV /
modal-tuple / flag rules of port/platform/renegade_vita_tutorial_bench.h,
validates its viewpoint table against M00 world data recorded in the
TUT_R1_TUTORIAL_BENCHMARK report, checks the CSV/log formats against
tools/compare_tutorial_bench.py, and pins the hook placement contracts
(original camera seam, DirectInput boundary, native frame loop, staging patch).
"""
import contextlib
import csv
import importlib.util
import io
import math
from pathlib import Path
import random
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "port/platform/renegade_vita_tutorial_bench.h"
HOOKS = ROOT / "port/compatibility/include/renegade_vita_bench_hooks.h"
CAMERA = ROOT / "port/compatibility/include/renegade_vita_bench_camera.h"
PATCH = ROOT / "port/patches/combat-tut1-bench-camera.patch"
STAGED_COMBAT = ROOT / "staging/combat/combat.cpp"
STAGE_SCRIPT = ROOT / "tools/stage_sources.sh"
RUNTIME = ROOT / "port/platform/vita/a31_vita_runtime.cpp"
DIRECTINPUT = ROOT / "port/platform/renegade_directinput.cpp"
COMPARE = ROOT / "tools/compare_tutorial_bench.py"

# Union of all 133 mesh bounds in retail M00_Tutorial.mix tut_lm015.w3d.
TERRAIN_MIN = (-110.0, -109.4, -1.5)
TERRAIN_MAX = (121.5, 119.0, 39.3)
# Player feet positions from the physical Dev134 M00 runtime log, used as the
# walkable anchors of the interior viewpoints (eye height above them).
WALKABLE_INTERIOR = {
    "sydney_agt_interior": (-11.898, 25.130, -9.979),
    "mobius_refinery_interior": (22.966, 16.947, -9.981),
    "petrova_power_interior": (-45.612, 19.478, -7.981),
}


def load_compare():
    spec = importlib.util.spec_from_file_location("compare_tutorial_bench", COMPARE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CMP = load_compare()
HEADER_TEXT = HEADER.read_text()


def header_constant(name):
    match = re.search(rf"\b{name} = (\d+)U", HEADER_TEXT)
    if match is None:
        raise AssertionError(f"constant {name} missing")
    return int(match.group(1))


def viewpoints():
    table = HEADER_TEXT[HEADER_TEXT.index("kViewpoints[] = {"):]
    table = table[:table.index("};")]
    rows = []
    for name, position, target in re.findall(
            r'\{"(\w+)",\s*\{([^}]*)\},\s*\{([^}]*)\}\}', table):
        parse = lambda text: tuple(float(value.strip().rstrip("f")) for value in text.split(","))
        rows.append((name, parse(position), parse(target)))
    return rows


def c_strings(text):
    """Concatenate adjacent C string literals."""
    return "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', text)).replace("\\n", "\n")


def call_literals(marker, occurrence=0):
    """String literals of the call starting at the given marker."""
    start = -1
    for _ in range(occurrence + 1):
        start = HEADER_TEXT.index(marker, start + 1)
    end = HEADER_TEXT.index(");", start)
    return c_strings(HEADER_TEXT[start:end])


def emit_format(prefix):
    match = re.search(r'Emitf\("(' + re.escape(prefix) + r'[^"]*)"', HEADER_TEXT)
    if match is None:
        raise AssertionError(f"Emitf format {prefix!r} missing")
    return match.group(1)


def python_format(c_format):
    return re.sub(r"%(0?\d*)u", r"%\1d", c_format)


CONVERSION = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[a-zA-Z]")


def independent_nearest_rank(values, percentile):
    ordered = sorted(values)
    if not ordered:
        return 0
    rank = math.ceil(percentile * len(ordered) / 100.0)
    return ordered[min(max(rank, 1), len(ordered)) - 1]


def fnv1a_bytes(data, value=CMP.FNV_OFFSET):
    for byte in data:
        value ^= byte
        value = (value * CMP.FNV_PRIME) & 0xFFFFFFFF
    return value


def parse_flag(data):
    """Mirror of Parse_Flag: (status, passes, capture)."""
    if len(data) != 8 or not data.startswith(b"RVTB1 ") or data[7:8] != b"\n":
        return ("rejected", 0, False)
    value = data[6:7]
    if value == b"0":
        return ("off", 0, False)
    if b"1" <= value <= b"5":
        return ("on", int(value), False)
    if value == b"C":
        return ("on", 1, True)
    return ("rejected", 0, False)


class PercentileMirror(unittest.TestCase):
    def test_header_uses_nearest_rank_rule(self):
        self.assertIn("rank = (percentile * count + 99U) / 100U;", HEADER_TEXT)
        self.assertIn("if (rank == 0U) rank = 1U;", HEADER_TEXT)
        self.assertIn("if (rank > count) rank = count;", HEADER_TEXT)
        self.assertIn("return sorted[rank - 1U];", HEADER_TEXT)

    def test_known_values(self):
        values = list(range(1, 121))
        self.assertEqual(CMP.nearest_rank(values, 50), 60)
        self.assertEqual(CMP.nearest_rank(values, 95), 114)
        self.assertEqual(CMP.nearest_rank(values, 99), 119)
        self.assertEqual(CMP.nearest_rank(values, 100), 120)
        self.assertEqual(CMP.nearest_rank(values, 0), 1)
        self.assertEqual(CMP.nearest_rank([7], 99), 7)
        self.assertEqual(CMP.nearest_rank([], 50), 0)

    def test_matches_independent_definition(self):
        generator = random.Random(1234)
        for _ in range(400):
            count = generator.randint(1, 1320)
            values = sorted(generator.randint(8000, 120000) for _ in range(count))
            for percentile in (1, 50, 95, 99, 100):
                self.assertEqual(CMP.nearest_rank(values, percentile),
                                 independent_nearest_rank(values, percentile))

    def test_monotonic_in_percentile(self):
        generator = random.Random(99)
        values = sorted(generator.randint(1, 10 ** 6) for _ in range(120))
        results = [CMP.nearest_rank(values, p) for p in range(0, 101)]
        self.assertEqual(results, sorted(results))

    def test_rounded_mean(self):
        self.assertEqual(CMP.rounded_mean([1, 2]), 2)
        self.assertEqual(CMP.rounded_mean([1, 1, 2]), 1)
        self.assertEqual(CMP.rounded_mean([]), 0)
        self.assertIn("(total + count / 2U) / count", HEADER_TEXT)

    def test_distribution_fields(self):
        result = CMP.distribution([16667] * 118 + [33333, 50000])
        self.assertEqual(result, {"p50": 16667, "p95": 16667, "p99": 33333,
                                  "worst": 50000, "mean": 17084})


class FingerprintMirror(unittest.TestCase):
    def test_fnv_reference_vectors(self):
        self.assertEqual(fnv1a_bytes(b""), 0x811C9DC5)
        self.assertEqual(fnv1a_bytes(b"a"), 0xE40C292C)
        self.assertEqual(header_constant("FNV_OFFSET"), 2166136261)
        self.assertEqual(header_constant("FNV_PRIME"), 16777619)

    def test_word_hash_is_little_endian_bytes(self):
        generator = random.Random(7)
        for _ in range(200):
            seed = generator.getrandbits(32)
            word = generator.getrandbits(32)
            self.assertEqual(CMP.fnv1a_word(seed, word),
                             fnv1a_bytes(word.to_bytes(4, "little"), seed))

    def test_fingerprint_composition_matches_header(self):
        body = HEADER_TEXT[HEADER_TEXT.index("inline unsigned Viewpoint_Fingerprint"):]
        body = body[:body.index("\n}\n")]
        order = [body.index(token) for token in
                 ("Fnv1a_Word(FNV_OFFSET, VERSION)", "Fnv1a_Word(hash, viewpoint)",
                  "Fnv1a_Word(hash, pose_crc)", "Fnv1a_Word(hash, mode[index])")]
        self.assertEqual(order, sorted(order))
        self.assertEqual(header_constant("VERSION"), CMP.BENCH_VERSION)
        self.assertEqual(header_constant("FINGERPRINT_COUNTERS"), 4)
        value = CMP.viewpoint_fingerprint(3, 0x89ABCDEF, (412, 38000, 21000, 600))
        expected = fnv1a_bytes(b"".join(word.to_bytes(4, "little") for word in
                                        (1, 3, 0x89ABCDEF, 412, 38000, 21000, 600)))
        self.assertEqual(value, expected)

    def test_modal_tuple_tie_break(self):
        self.assertEqual(CMP.modal_tuple([]), ((0, 0, 0, 0), 0))
        tuples = [(5, 1, 1, 1)] * 3 + [(4, 9, 9, 9)] * 3 + [(6, 0, 0, 0)]
        self.assertEqual(CMP.modal_tuple(tuples), ((4, 9, 9, 9), 3))
        self.assertEqual(CMP.modal_tuple(list(reversed(tuples))), ((4, 9, 9, 9), 3))
        self.assertIn("better = samples[candidate].counters[index] < mode[index];", HEADER_TEXT)


class FlagContract(unittest.TestCase):
    def test_mirror_table(self):
        self.assertEqual(parse_flag(b"RVTB1 0\n"), ("off", 0, False))
        self.assertEqual(parse_flag(b"RVTB1 1\n"), ("on", 1, False))
        self.assertEqual(parse_flag(b"RVTB1 5\n"), ("on", 5, False))
        self.assertEqual(parse_flag(b"RVTB1 C\n"), ("on", 1, True))
        for rejected in (b"RVTB1 6\n", b"RVTB1 c\n", b"RVTB1 1", b"RVTB1 1\r\n",
                         b"RVTB2 1\n", b"", b"RVTB1 11\n"):
            self.assertEqual(parse_flag(rejected)[0], "rejected", rejected)

    def test_header_flag_rules(self):
        self.assertIn('"ux0:data/renegade/user/config/tutorial-bench-v1.flag"', HEADER_TEXT)
        self.assertIn('size != 8U || memcmp(bytes, "RVTB1 ", 6U) != 0 || bytes[7] != \'\\n\'',
                      HEADER_TEXT)
        self.assertEqual(header_constant("MAX_PASSES"), 5)
        self.assertIn("value == 'C'", HEADER_TEXT)

    def test_absent_or_off_flag_is_inert(self):
        configure = HEADER_TEXT[HEADER_TEXT.index("void Configure("):]
        configure = configure[:configure.index("bool Enabled()")]
        early_return = configure.index(
            "if (flag.status == FLAG_STATUS_ABSENT || flag.status == FLAG_STATUS_OFF) return;")
        self.assertLess(early_return, configure.index("state_ = STATE_WAITING;"))
        self.assertLess(early_return, configure.index("Emit("))
        self.assertIn("if (state_ != STATE_RUNNING) return;", HEADER_TEXT)


class ViewpointTable(unittest.TestCase):
    def test_route_shape(self):
        rows = viewpoints()
        self.assertEqual(len(rows), 11)
        names = [row[0] for row in rows]
        self.assertEqual(len(set(names)), len(names))
        for required in ("spawn_course_start", "logan_course_overlook", "gunner_range_lane",
                         "mobius_refinery_interior", "base_overview_elevated",
                         "refinery_tib_dump_east", "hotwire_vehicle_yard"):
            self.assertIn(required, names)
        self.assertEqual(header_constant("SETTLE_FRAMES"), 30)
        self.assertEqual(header_constant("MEASURE_FRAMES"), 120)

    def test_positions_inside_m00_terrain(self):
        for name, position, target in viewpoints():
            for axis in range(3):
                self.assertGreaterEqual(position[axis], TERRAIN_MIN[axis] - 12.0, name)
                self.assertLessEqual(position[axis], TERRAIN_MAX[axis], name)
                self.assertGreaterEqual(target[axis], TERRAIN_MIN[axis] - 12.0, name)
                self.assertLessEqual(target[axis], TERRAIN_MAX[axis], name)
            distance = math.dist(position, target)
            self.assertGreater(distance, 2.0, name)
            self.assertLess(distance, 120.0, name)
            # Look_At needs a horizontal component to define yaw.
            self.assertGreater(math.hypot(target[0] - position[0], target[1] - position[1]), 1.0, name)

    def test_interiors_stand_on_recorded_walkable_positions(self):
        table = {name: position for name, position, _ in viewpoints()}
        for name, feet in WALKABLE_INTERIOR.items():
            camera = table[name]
            self.assertLess(math.hypot(camera[0] - feet[0], camera[1] - feet[1]), 0.1, name)
            self.assertGreater(camera[2] - feet[2], 1.4, name)
            self.assertLess(camera[2] - feet[2], 1.8, name)

    def test_fixed_projection_matches_original_defaults(self):
        self.assertIn("kHorizontalFovRadians = 1.30899694f", HEADER_TEXT)
        self.assertAlmostEqual(math.radians(75.0), 1.30899694, places=7)
        self.assertIn("kNearClip = 0.26f", HEADER_TEXT)
        self.assertIn("kFarClip = 300.0f", HEADER_TEXT)


class OutputFormats(unittest.TestCase):
    def summary_columns(self):
        return call_literals('fprintf(summary, "candidate').strip().split(",")

    def frames_columns(self):
        return call_literals('fprintf(frames, "candidate').strip().split(",")

    def test_summary_rows_match_header(self):
        columns = self.summary_columns()
        self.assertEqual(len(columns), 40)
        row_format = call_literals('fprintf(file, "%s,%s,%u,%u,%s').strip()
        self.assertEqual(len(row_format.split(",")), len(columns))
        self.assertEqual(len(CONVERSION.findall(row_format)), len(columns))
        all_format = call_literals('fprintf(file, "%s,%s,%u,ALL').strip()
        self.assertEqual(len(all_format.split(",")), len(columns))
        for field in ("interval_p50_us", "interval_p95_us", "interval_p99_us",
                      "interval_worst_us", "fingerprint", "pose_crc", "mode_frames"):
            self.assertIn(field, columns)

    def test_frames_rows_match_header(self):
        columns = self.frames_columns()
        self.assertEqual(len(columns), 19)
        row_format = call_literals('fprintf(file, "%s,%s,%u,%u,%u,%d').strip()
        self.assertEqual(len(row_format.split(",")), len(columns))
        self.assertEqual(len(CONVERSION.findall(row_format)), len(columns))
        for field in CMP.COUNTER_FIELDS:
            self.assertIn(field, columns)

    def test_runtime_log_lines_round_trip(self):
        start = python_format(emit_format("A4 tutorial-bench: start v=")) % (
            1, "r03", "A3.5-dev240", 900, 1, 11, 1, 420, "fresh", 1,
            "ux0:data/renegade/user/logs/tutorial-bench-A3.5-dev240-r03.csv", 1)
        line = python_format(emit_format("A4 tutorial-bench: run=")) % (
            "r03", 1, 1, 4, 11, "gunner_range_lane", 1, 120, 0, 0x20,
            16667, 17012, 18334, 21001, 16801, 15000, 15900, 16000, 7000, 8000,
            412, 38000, 21000, 600, 90, 1800, 300, 2500, 118, 120,
            0x1A2B3C4D, 0x89ABCDEF, 40000, -34.0, 76.0, 2.65, -0.024, -0.999, -0.035,
            1.309, 1234)
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "runtime.log"
            log.write_text("noise\n" + start + "\n" + line + "\n")
            parsed = CMP.parse_log(log)
        self.assertEqual(parsed["candidate"], "A3.5-dev240")
        self.assertEqual(parsed["source"], "fresh")
        self.assertEqual(parsed["first_person"], 1)
        row = parsed["rows"][0]
        self.assertEqual((row["vp"], row["name"], row["p95"], row["worst"]),
                         (4, "gunner_range_lane", 17012, 21001))
        self.assertEqual((row["meshes"], row["state_changes"], row["mode_frames"]),
                         (412, 2500, 118))
        self.assertEqual((row["fingerprint"], row["pose_crc"]), ("1A2B3C4D", "89ABCDEF"))


def synthetic_run(directory, label, scale=1.0, mesh_shift=0, invalid_vp=None,
                  tamper_vp=None):
    """Write summary + frames CSVs with internally consistent fingerprints."""
    summary_columns = call_literals('fprintf(summary, "candidate').strip().split(",")
    frame_columns = call_literals('fprintf(frames, "candidate').strip().split(",")
    summary_path = Path(directory) / f"tutorial-bench-{label}-r01.csv"
    frames_path = Path(directory) / f"tutorial-bench-{label}-r01-frames.csv"
    generator = random.Random(42)
    with summary_path.open("w", newline="") as summary_stream, \
            frames_path.open("w", newline="") as frames_stream:
        summary = csv.DictWriter(summary_stream, summary_columns)
        frames = csv.DictWriter(frames_stream, frame_columns)
        summary.writeheader()
        frames.writeheader()
        for vp, (name, _, _) in enumerate(viewpoints()):
            pose_crc = 0x10000000 + vp
            measured = []
            for hold in range(150):
                interval = int((16000 + vp * 900 + generator.randint(0, 1500)) * scale)
                counters = (400 + vp * 10 + mesh_shift, 30000 + vp, 20000 + vp, 600,
                            80, 1500, 300, 2400)
                if hold == 140:
                    counters = (counters[0] + 3,) + counters[1:]
                flags = 1 if (vp == invalid_vp and hold == 100) else 0
                frames.writerow(dict(zip(frame_columns, (
                    label, "r01", 1, vp, hold, 1 if hold >= 30 else 0, interval,
                    interval - 500, 6000, 9000) + counters + (flags,))))
                if hold >= 30:
                    measured.append((interval, flags, counters))
            mode, mode_frames = CMP.modal_tuple([c[:4] for _, _, c in measured])
            fingerprint = CMP.viewpoint_fingerprint(vp, pose_crc, mode)
            if vp == tamper_vp:
                fingerprint ^= 1
            stats = CMP.distribution([interval for interval, _, _ in measured])
            row = dict.fromkeys(summary_columns, 0)
            row.update({"candidate": label, "run": "r01", "pass": 1, "viewpoint": vp,
                        "name": name, "valid": 0 if vp == invalid_vp else 1, "frames": 120,
                        "invalid_frames": 1 if vp == invalid_vp else 0,
                        "flags": 1 if vp == invalid_vp else 0,
                        "mode_frames": mode_frames, "fingerprint": f"{fingerprint:08X}",
                        "pose_crc": f"{pose_crc:08X}", "source": "fresh", "quiet_start": 1})
            for field in CMP.TIMING_FIELDS:
                row[f"interval_{field}_us"] = stats[field]
            for field, value in zip(CMP.COUNTER_FIELDS, mode + (80, 1500, 300, 2400)):
                row[field] = value
            summary.writerow(row)
        route = dict.fromkeys(summary_columns, 0)
        route.update({"candidate": label, "run": "r01", "pass": 1, "viewpoint": "ALL",
                      "name": "route", "valid": 0 if invalid_vp is not None else 1,
                      "fingerprint": "00000000", "pose_crc": "00000000",
                      "source": "fresh", "quiet_start": 1})
        summary.writerow(route)
    return summary_path


def synthetic_log(path, first_person=1, scale=1.0):
    start = python_format(emit_format("A4 tutorial-bench: start v=")) % (
        1, "r01", path.stem, 900, 1, 11, 1, 420, "fresh", first_person,
        f"ux0:data/renegade/user/logs/tutorial-bench-{path.stem}-r01.csv", 1)
    lines = ["unrelated runtime line", start]
    for vp, (name, position, _) in enumerate(viewpoints()):
        timing = [int(value * scale) for value in (16667, 17012, 18334, 21001, 16801)]
        lines.append(python_format(emit_format("A4 tutorial-bench: run=")) % tuple(
            ["r01", 1, 1, vp, 11, name, 1, 120, 0, 0] + timing +
            [15000, 15900, 16000, 7000, 8000, 412 + vp, 38000, 21000, 600, 90, 1800,
             300, 2500, 118, 120, 0x1A2B3C00 + vp, 0x89ABCD00 + vp, 40000] +
            list(position) + [0.0, -1.0, 0.0, 1.309, 2000 + vp * 150]))
    route = [int(value * scale) for value in (17000, 19000, 21000, 24000, 17300)]
    lines.append(python_format(emit_format("A4 tutorial-bench: summary v=")) % tuple(
        [1, "r01", 1, 1, path.stem, 0, 11, 11, 11, 1320] + route + [0xCAFEF00D, "fresh", 1]))
    path.write_text("\n".join(lines) + "\n")
    return path


class CompareTool(unittest.TestCase):
    def test_runtime_logs_compare_and_check_camera_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            base = synthetic_log(Path(directory) / "base.log")
            fast = synthetic_log(Path(directory) / "fast.log", scale=0.9)
            third = synthetic_log(Path(directory) / "third.log", first_person=0)
            result = CMP.compare(CMP.load(base), CMP.load(fast), 3.0)
            self.assertEqual(result["status"], 0, result["problems"])
            self.assertEqual({row["verdict"] for row in result["rows"]}, {"faster"})
            self.assertEqual(result["route"]["baseline"]["p95"], 19000)
            self.assertAlmostEqual(result["route"]["delta_percent"]["p95"], -10.0, places=3)
            result = CMP.compare(CMP.load(base), CMP.load(third), 3.0)
            self.assertEqual(result["status"], 1)
            self.assertTrue(any("first/third-person" in problem for problem in result["problems"]))

    def run_compare(self, **candidate_options):
        with tempfile.TemporaryDirectory() as directory:
            baseline = synthetic_run(directory, "base")
            candidate = synthetic_run(directory, "cand", **candidate_options)
            return CMP.compare(CMP.load(baseline), CMP.load(candidate), 3.0)

    def test_identical_content_is_comparable(self):
        result = self.run_compare()
        self.assertEqual(result["status"], 0, result["problems"])
        self.assertTrue(all(row["fingerprint_match"] for row in result["rows"]))
        self.assertTrue(all(row["verdict"] == "neutral" for row in result["rows"]))
        self.assertEqual(result["route"]["delta_percent"]["p50"], 0.0)

    def test_faster_candidate_is_reported(self):
        result = self.run_compare(scale=0.85)
        self.assertEqual(result["status"], 0)
        self.assertTrue(all(row["verdict"] == "faster" for row in result["rows"]))
        self.assertTrue(all(row["delta_percent"]["p50"] < -10.0 for row in result["rows"]))

    def test_changed_render_content_is_a_fingerprint_mismatch(self):
        result = self.run_compare(mesh_shift=1)
        self.assertEqual(result["status"], 2)
        self.assertEqual(len(result["fingerprint_mismatches"]), 11)

    def test_disturbed_viewpoint_invalidates_comparison(self):
        result = self.run_compare(invalid_vp=5)
        self.assertEqual(result["status"], 1)
        self.assertTrue(any("viewpoint 5" in problem for problem in result["problems"]))

    def test_summary_fingerprint_must_match_raw_frames(self):
        result = self.run_compare(tamper_vp=2)
        self.assertEqual(result["status"], 1)
        self.assertTrue(any("does not match raw frames" in problem
                            for problem in result["problems"]))

    def test_command_line_exit_status(self):
        with tempfile.TemporaryDirectory() as directory:
            baseline = synthetic_run(directory, "base")
            candidate = synthetic_run(directory, "cand", mesh_shift=2)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = CMP.main([str(baseline), str(candidate), "--json"])
            self.assertEqual(status, 2)
            self.assertIn('"fingerprint_mismatches"', output.getvalue())


class HookContracts(unittest.TestCase):
    def test_hooks_are_shared_and_inert_by_default(self):
        hooks = HOOKS.read_text()
        self.assertIn("inline RenegadeVitaBenchHooks g_renegade_vita_bench_hooks = {};", hooks)
        camera = CAMERA.read_text()
        body = camera[camera.index("inline void Renegade_Vita_Bench_Apply_Camera"):]
        self.assertLess(body.index("if (!hooks.camera_armed) return;"),
                        body.index("camera.Set_Transform(transform);"))
        for call in ("transform.Look_At(", "camera.Set_View_Plane(hooks.camera_horizontal_fov);",
                     "camera.Set_Clip_Planes(hooks.camera_near_clip, hooks.camera_far_clip);"):
            self.assertIn(call, body)

    def test_staged_combat_calls_hook_after_original_camera_update(self):
        text = STAGED_COMBAT.read_text()
        think = text[text.index("void 	CombatManager::Think()"):]
        think = think[:think.index("GameObjManager::Post_Think();")]
        branch = think[think.index("if ( !MainCamera->Is_Using_Host_Model() ) {"):]
        self.assertLess(branch.index("MainCamera->Update();"),
                        branch.index("Renegade_Vita_Bench_Apply_Camera( *MainCamera );"))
        self.assertLess(branch.index("Renegade_Vita_Bench_Apply_Camera( *MainCamera );"),
                        branch.index("}"))
        self.assertIn('#include "renegade_vita_bench_camera.h"', text)

    def test_patch_is_registered_last_in_combat_list(self):
        script = STAGE_SCRIPT.read_text()
        combat_lines = [line for line in script.splitlines()
                        if '-d "$rv_stage/combat"' in line]
        self.assertIn("combat-tut1-bench-camera.patch", combat_lines[-1])
        self.assertEqual(script.count("combat-tut1-bench-camera.patch"), 1)

    @unittest.skipIf(shutil.which("patch") is None, "patch(1) unavailable")
    def test_tracked_staging_already_contains_patch(self):
        with tempfile.TemporaryDirectory() as directory:
            shutil.copy(STAGED_COMBAT, Path(directory) / "combat.cpp")
            result = subprocess.run(
                ["patch", "--dry-run", "--batch", "-R", "--fuzz=0", "-p1",
                 "-d", directory, "-i", str(PATCH)],
                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("fuzz", result.stdout.lower())

    def test_runtime_arms_only_around_one_simulation_call(self):
        text = RUNTIME.read_text()
        arm = text.index("tutorial_bench.Arm_Simulation(bench_counters);")
        simulation = text.index("A31_Interactive_Run_Simulation_Frame();", arm)
        release = text.index("RenegadeVitaTutorialBench::Controller::Release_Hooks();", arm)
        self.assertLess(simulation, release)
        self.assertEqual(text[simulation:release].count(";"), 1)
        profile_end = text.index(
            "Renegade_Frame_Profile_End_Frame(static_cast<uint32_t>(frame_end - frame_begin));")
        self.assertLess(profile_end, text.index("tutorial_bench.End_Frame(bench_frame);"))
        guard = text.index("RenegadeVitaTutorialBench::Session_Guard tutorial_bench_guard(")
        self.assertLess(guard, text.index("while (true) {", guard))
        self.assertLess(guard, arm)

    def test_directinput_neutralizes_before_route_record_and_keeps_start(self):
        text = DIRECTINPUT.read_text()
        suppress = text.index("if (bench_input_suppressed) {")
        self.assertLess(suppress, text.index("Record_Sample(controller);", suppress))
        block = text[suppress:text.index("Record_Sample(controller);", suppress)]
        self.assertIn("controller.buttons &= SCE_CTRL_START;", block)
        self.assertIn("= 128U;", block)
        self.assertIn("if (bench_input_suppressed) front_touch.down = back_touch.down = false;",
                      text)


if __name__ == "__main__":
    unittest.main()
