"""TUT-R1 PHYSICS_COLLISION_COST: port query audit and physics-cost log analyzer.

Pure Python; reads sources and synthetic log text only (no compiler, no game,
no device logs).
"""
from pathlib import Path
import re
import tempfile
import unittest

from tools import analyze_physics_cost as cost
from tools import audit_physics_scene_queries as audit

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'port/platform/vita/a31_vita_runtime.cpp'
BOUNDARY = ROOT / 'port/platform/a31_gameplay_boundary.cpp'
PROFILER = ROOT / 'port/platform/vita/renegade_vita_frame_profile.cpp'


def c_format(path: Path, prefix: str) -> str:
    """Return the (adjacent-literal concatenated) C format string starting with prefix."""
    source = path.read_text(encoding='utf-8')
    start = source.index('"' + prefix)
    parts = []
    index = start
    while index < len(source) and source[index] == '"':
        index += 1
        literal = []
        while source[index] != '"':
            if source[index] == '\\':
                literal.append(source[index:index + 2])
                index += 2
                continue
            literal.append(source[index])
            index += 1
        parts.append(''.join(literal))
        index += 1
        while index < len(source) and source[index] in ' \t\r\n':
            index += 1
    return ''.join(parts)


def render(fmt: str) -> str:
    """Fill printf conversions with plausible sample values."""
    def value(match):
        conversion = match.group(0)[-1]
        if conversion in 'f':
            return '1.5'
        if conversion == 's':
            return 'sample'
        if conversion == 'p':
            return '0x1'
        return '7'
    text = re.sub(r'%[-+ #0]*\d*(?:\.\d+)?(?:ll|l|h|hh|z)?[diuxXfsp]', value, fmt)
    return text.replace('\\n', '').replace('%%', '%')


class PortQueryAuditTests(unittest.TestCase):
    def test_repository_has_only_registered_port_queries(self):
        result = audit.classify(audit.collect(ROOT))
        self.assertEqual(result['unregistered'], [])
        self.assertEqual(result['count_mismatch'], [])
        self.assertEqual(result['stale_registrations'], [])
        self.assertTrue(result['passed'])
        self.assertEqual([(h['path'], h['api']) for h in result['hits']],
                         [('port/platform/a31_gameplay_boundary.cpp',
                           'Get_Vis_Table_For_Rendering')])

    def test_registered_census_query_stays_sampled_and_bounded(self):
        source = BOUNDARY.read_text(encoding='utf-8')
        start = source.index('static void Sample_Original_Visibility_Census(')
        body = source[start:source.index('\n}\n', start)]
        guard = body.index('% 120U != 0U || census_logs >= 1024U) return;')
        self.assertLess(guard, body.index('Get_Vis_Table_For_Rendering(camera)'))
        # The census runs after the frame's own Pre_Render_Processing.
        frame = source[source.index('A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame('):]
        self.assertLess(frame.index('scene->Pre_Render_Processing(*camera);'),
                        frame.index('Sample_Original_Visibility_Census(*scene, *camera);'))

    def test_source_scan_ignores_comments_strings_math_and_accessors(self):
        code = audit.strip_comments_and_strings(
            '// scene->Cast_Ray(test);\n'
            '/* Get_Vis_Table(point)\n   Cast_AABox(box) */\n'
            'Log("Cast_OBBox(x)");\n'
            'CollisionMath::Intersection_Test(box, tri);\n'
            'int id = pvs->Get_Vis_Sector_ID();\n'
            'scene->Cast_Ray(raytest);\n'
            'int s = culling->Get_Vis_Sector_ID(point);\n'
            'scene->Get_Vis_Table_Size();\n')
        self.assertEqual(audit.find_queries(code),
                         [(7, 'Cast_Ray'), (8, 'Get_Vis_Sector_ID')])

    def test_patch_scan_reports_added_lines_with_new_file_numbers(self):
        patch = (
            '--- a/thing.cpp\n'
            '+++ b/thing.cpp\n'
            '@@ -10,4 +10,8 @@\n'
            ' void f()\n'
            ' {\n'
            '+\t/* a comment that mentions\n'
            '+\t   COMBAT_SCENE->Cast_Ray(raytest) */\n'
            '+\tCOMBAT_SCENE->Cast_AABox(boxtest);\n'
            '-\told();\n'
            '+\tCollisionMath::Overlap_Test(box, point);\n'
            ' \tPhysicsSceneClass::Get_Instance()->Cast_Ray(raytest);\n'
            '+\tnew_call();\n'
            ' }\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'combat-x.patch'
            path.write_text(patch)
            hits = audit.scan_patch(path, 'port/patches/combat-x.patch')
        self.assertEqual([(h['line'], h['api'], h['target']) for h in hits],
                         [(14, 'Cast_AABox', 'thing.cpp')])

    def test_classify_flags_unregistered_stale_and_count_changes(self):
        registered = ({'path': 'p.cpp', 'api': 'Cast_Ray', 'count': 1},
                      {'path': 'gone.cpp', 'api': 'Find_Vis_Tile', 'count': 1})
        hits = [{'path': 'p.cpp', 'line': 1, 'api': 'Cast_Ray'},
                {'path': 'p.cpp', 'line': 9, 'api': 'Cast_Ray'},
                {'path': 'new.cpp', 'line': 3, 'api': 'Cast_OBBox'}]
        result = audit.classify(hits, registered)
        self.assertFalse(result['passed'])
        self.assertEqual([h['path'] for h in result['unregistered']], ['new.cpp'])
        self.assertEqual(result['count_mismatch'],
                         [{'path': 'p.cpp', 'api': 'Cast_Ray', 'expected': 1, 'found': 2}])
        self.assertEqual([e['path'] for e in result['stale_registrations']], ['gone.cpp'])

    def test_per_frame_diagnostic_query_requires_a_flag(self):
        hits = [{'path': 'd.cpp', 'line': 4, 'api': 'Cast_Ray'}]
        unflagged = ({'path': 'd.cpp', 'api': 'Cast_Ray', 'count': 1, 'kind': 'diagnostic',
                      'per_frame': True, 'flag': None},)
        self.assertFalse(audit.classify(hits, unflagged)['passed'])
        flagged = ({'path': 'd.cpp', 'api': 'Cast_Ray', 'count': 1, 'kind': 'diagnostic',
                    'per_frame': True, 'flag': 'physics-cost-v1.flag RVPH1'},)
        self.assertTrue(audit.classify(hits, flagged)['passed'])
        self.assertEqual(audit.classify(audit.collect(ROOT))['policy_violations'], [])


class AnalyzerFormatContractTests(unittest.TestCase):
    """The analyzer must parse the exact lines the current runtime prints."""

    def test_pacing_casts_and_perf_formats(self):
        pacing = render(c_format(RUNTIME, 'A4 campaign pacing:'))
        casts = render(c_format(RUNTIME, 'A4 combat casts:'))
        perf = render(c_format(RUNTIME, 'A3.5 perf:'))
        parsed = cost.parse_log('\n'.join([pacing, casts, perf]))
        self.assertEqual(len(parsed['pacing']), 1)
        self.assertEqual(parsed['pacing'][0]['combat'], 7)
        self.assertEqual(len(parsed['casts']), 1)
        self.assertEqual(parsed['casts'][0]['obbox_region'], 1.5)
        self.assertEqual(parsed['casts'][0]['awake'], 1.5)
        self.assertEqual(len(parsed['perf']), 1)
        self.assertEqual(parsed['perf'][0]['render_us'], 7)

    def test_vis_census_format(self):
        line = render(c_format(BOUNDARY, 'A3.6 vis-census:'))
        parsed = cost.parse_log(line)
        self.assertEqual(len(parsed['census']), 1)
        self.assertEqual(parsed['census'][0]['census_us'], 7)

    def test_frame_profile_format(self):
        header = render(c_format(PROFILER, 'A3.6 frame-profile: version=2'))
        # Append_Name maps ' ', '=' and '/' to '_'; values are "%llu/%.1f".
        line = header + ' PhysicsScene::Update=812/1.0 Combat_Render_FG=9000/1.0 Cast_Ray=40/6.5'
        parsed = cost.parse_log(line)
        self.assertEqual(len(parsed['profile']), 1)
        summary = cost.summarise(parsed)
        self.assertEqual(sorted(summary['profile_scopes']), ['Cast_Ray', 'PhysicsScene::Update'])
        self.assertEqual(summary['profile_scopes']['Cast_Ray']['calls_median'], 6.5)


def pacing_line(frames, combat, network=300):
    return (f'A4 campaign pacing: frames={frames} avg_us '
            f'time/input/path/control/network/combat/other=10/100/5/20/{network}/{combat}/1 '
            f'clock_real/sim/drift_ms=1/1/0')


def casts_line(frames, window, combat, awake=3.0):
    return (f'A4 combat casts: frames={frames} window={window} combat_avg_us={combat} '
            f'soldiers_awake/hibernating_per_frame={awake:.1f}/0.0 per_frame '
            'ray_cull/ray_region/aabox_cull/aabox_region/obbox_cull/obbox_region='
            '6.0/0.0/12.5/0.0/1.0/0.0')


def perf_line(frames, fps=30.0, p50=33000):
    return (f'A3.5 perf: frames={frames} rolling_samples=120 avg_fps={fps:.3f} '
            f'frame_us min/p50/p95/p99/max=10000/{p50}/40000/50000/90000 slow_over_16_7ms=1 '
            'stage_us sync/sim/render=2/4000/26000 draws meshes=1')


class AnalyzerWindowTests(unittest.TestCase):
    def test_cumulative_pacing_becomes_windows_and_sessions(self):
        parsed = cost.parse_log('\n'.join([
            pacing_line(120, 2000), pacing_line(240, 3000), pacing_line(360, 2000),
            pacing_line(120, 5000)]))  # frames drop: new session
        windows = cost.pacing_windows(parsed['pacing'])
        self.assertEqual([(w['session'], w['start'], w['end']) for w in windows],
                         [(0, 0, 120), (0, 120, 240), (0, 240, 360), (1, 0, 120)])
        self.assertEqual([w['combat_us'] for w in windows], [2000, 4000, 0, 5000])
        self.assertFalse(any(w['exact'] for w in windows))

    def test_exact_combat_casts_and_perf_attach_by_checkpoint(self):
        text = '\n'.join([pacing_line(120, 2000), casts_line(120, 120, 2100),
                          perf_line(120), perf_line(120),  # printed twice
                          pacing_line(240, 3000), casts_line(240, 100, 9999),
                          perf_line(240, fps=25.0)])
        parsed = cost.parse_log(text)
        self.assertEqual(len(parsed['perf']), 2)
        windows = cost.merge_windows(parsed)
        self.assertTrue(windows[0]['exact'])
        self.assertEqual(windows[0]['combat_us'], 2100)
        self.assertEqual(windows[0]['casts_per_frame'], 19.5)
        # A casts window that does not span the pacing window keeps the derived value.
        self.assertFalse(windows[1]['exact'])
        self.assertEqual(windows[1]['combat_us'], 4000)
        self.assertEqual(windows[1]['avg_fps'], 25.0)

    def test_bursts_merge_adjacent_hot_windows_only(self):
        windows = [{'session': 0, 'start': s, 'end': s + 120, 'combat_us': c}
                   for s, c in ((0, 9000), (120, 12000), (240, 1000), (360, 8000))]
        windows.append({'session': 1, 'start': 0, 'end': 120, 'combat_us': 8500})
        bursts = cost.find_bursts(windows, 8000)
        self.assertEqual([(b['session'], b['start'], b['end'], b['windows'], b['peak_combat_us'])
                          for b in bursts],
                         [(0, 0, 240, 2, 12000), (0, 360, 480, 1, 8000), (1, 0, 120, 1, 8500)])

    def test_summary_and_compare(self):
        a = cost.summarise(cost.parse_log('\n'.join([
            pacing_line(120, 2000), casts_line(120, 120, 2000), perf_line(120),
            pacing_line(240, 6000), casts_line(240, 120, 10000), perf_line(240)])))
        b = cost.summarise(cost.parse_log('\n'.join([
            pacing_line(120, 2000), casts_line(120, 120, 2000, awake=2.0), perf_line(120),
            pacing_line(240, 3000), casts_line(240, 120, 4000, awake=2.0), perf_line(240)])))
        self.assertEqual(a['combat_us']['median'], 6000)
        self.assertEqual(len(a['bursts']), 1)
        self.assertEqual(a['frame_us_median'], 33333)
        self.assertEqual(a['combat_share_of_frame'], 0.18)
        delta = cost.compare(a, b)
        self.assertEqual(delta['combat_us_median'], {'a': 6000, 'b': 3000, 'delta': -3000})
        self.assertEqual(delta['awake_median']['delta'], -1.0)
        self.assertEqual(delta['bursts']['delta'], -1)


if __name__ == '__main__':
    unittest.main()
