import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.analyze_script_lookups import KINDS, analyze_lookups
from tools.renegade_patch_inventory import load_inventory
from tools.original_owner_source_replay import replay_to_patch

ROOT = Path(__file__).resolve().parents[1]


def capture(enabled=True):
    return {'candidate': 'synthetic', 'archive': 'M13.mix', 'frames_recorded': 0,
            'lookup_diagnostics': {'schema': 1, 'snapshot_available': True, 'enabled': enabled,
                                   'collection_active': enabled, 'frame': 0, 'phase': 'level_load',
                                   'capacity_per_kind': 16, 'name_capacity': 96,
                                   'retention': 'first_samples', 'kinds': [
                                       {'kind': kind, 'attempts': 0, 'returned': 0, 'absent': 0,
                                        'sentinel_absent': 0, 'unretained_absent': 0,
                                        'lossy_absent': 0, 'saturated': False, 'samples': []}
                                       for kind in KINDS]}}


def sample(object_id=100389, name='', **values):
    return {'object_id': object_id, 'name': name, 'count': 1, 'first_frame': 0, 'last_frame': 0,
            'first_phase': 'level_load', 'last_phase': 'level_load', 'key_lossy': False, **values}


class LookupObservationTests(unittest.TestCase):
    def setUp(self):
        self.summary = capture()
        self.data = self.summary['lookup_diagnostics']
        self.objects = self.data['kinds'][1]

    def analyze(self):
        return analyze_lookups(self.summary, expected_candidate='synthetic', archive='M13.mix')

    def test_legacy_capture_reports_not_recorded(self):
        del self.summary['lookup_diagnostics']
        self.assertEqual(self.analyze()['status'], 'not_recorded')

    def test_disabled_capture_is_distinct_from_enabled_without_misses(self):
        self.assertEqual(self.analyze()['status'], 'captured')
        self.summary = capture(False)
        self.assertEqual(self.analyze()['status'], 'disabled')

    def test_load_only_miss_is_not_physical_or_completion_evidence(self):
        self.objects.update(attempts=1, absent=1, samples=[sample()])
        report = self.analyze()
        self.assertEqual(report['kinds'][1]['samples'][0]['object_id'], 100389)
        self.assertIn('provenance unverified', report['evidence_class'])
        self.assertNotIn('route_milestones', report)
        self.assertNotIn('timing', report)

    def test_strict_timing_validator_still_rejects_zero_frame_bundle(self):
        from tools.validate_campaign_flight_bundle import BundleError, validate_bundle
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'campaign-flight-summary.json').write_text(json.dumps(self.summary))
            (root / 'campaign-flight-frames.csv').write_text('candidate,frame\n')
            with self.assertRaisesRegex(BundleError, 'empty'):
                validate_bundle(root, 'synthetic')

    def test_busy_and_error_snapshot_have_no_stale_counts(self):
        for status in ('busy', 'error'):
            self.summary['lookup_diagnostics'] = {'schema': 1, 'snapshot_available': False,
                                                   'snapshot_status': status}
            self.assertEqual(self.analyze()['status'], 'snapshot_' + status)
        self.summary['lookup_diagnostics']['kinds'] = []
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.analyze()

    def test_counts_reconcile_sentinels_retention_and_duplicates(self):
        self.objects.update(attempts=10, returned=2, absent=8, sentinel_absent=1,
                            samples=[sample(count=7)])
        self.assertEqual(self.analyze()['kinds'][1]['retained_samples'], 1)
        self.objects['samples'][0]['count'] = 6
        with self.assertRaisesRegex(ValueError, 'reconcile'):
            self.analyze()

    def test_all_four_kinds_and_unique_keys_required(self):
        self.data['kinds'][0]['kind'] = 'object'
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.analyze()
        self.data['kinds'][0]['kind'] = 'script_factory'
        self.objects.update(attempts=2, absent=2, samples=[sample(), sample()])
        with self.assertRaisesRegex(ValueError, 'duplicate exact'):
            self.analyze()

    def test_capacity_and_unretained_attempts_are_explicit(self):
        self.objects.update(attempts=20, absent=20, unretained_absent=4,
                            samples=[sample(object_id=i) for i in range(1, 17)])
        self.assertEqual(self.analyze()['kinds'][1]['unretained_absent'], 4)
        self.objects['samples'].append(sample(object_id=17))
        with self.assertRaisesRegex(ValueError, 'capacity'):
            self.analyze()
        self.objects.update(attempts=2, absent=2, unretained_absent=1, samples=[sample()])
        with self.assertRaisesRegex(ValueError, 'full first-sample'):
            self.analyze()

    def test_lossy_same_prefix_remains_separate_observations(self):
        files = self.data['kinds'][3]
        truncated = sample(object_id=0, name='x' * 95, key_lossy=True)
        files.update(attempts=2, absent=2, lossy_absent=2, samples=[truncated, copy.deepcopy(truncated)])
        self.assertEqual(self.analyze()['kinds'][3]['retained_samples'], 2)
        files.update(attempts=3, absent=3, lossy_absent=3)
        files['samples'][0]['count'] = 2
        with self.assertRaisesRegex(ValueError, 'deduplicated'):
            self.analyze()

    def test_phase_frame_order_and_inflight_frame_context(self):
        self.data.update(frame=1, phase='gameplay')
        self.objects.update(attempts=2, absent=2, samples=[
            sample(count=2, last_frame=1, last_phase='gameplay')])
        self.assertEqual(self.analyze()['attempted_frame'], 1)
        self.objects['samples'][0]['last_frame'] = 2
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.analyze()
        self.data.update(frame=2, phase='level_load')
        with self.assertRaisesRegex(ValueError, 'context'):
            self.analyze()

    def test_saturated_counters_are_lower_bounds_not_exact_totals(self):
        self.objects.update(attempts=(1 << 32) - 1, returned=(1 << 32) - 1,
                            absent=1, samples=[sample()], saturated=True)
        self.assertTrue(self.analyze()['kinds'][1]['counters_are_lower_bounds'])
        self.objects.update(attempts=1, returned=0)
        with self.assertRaisesRegex(ValueError, 'saturated counter'):
            self.analyze()

    def test_no_boolean_or_wide_disk_id_coercion(self):
        self.objects['attempts'] = True
        with self.assertRaisesRegex(ValueError, 'uint32'):
            self.analyze()
        self.objects.update(attempts=1, absent=1, samples=[sample(object_id=1 << 32)])
        with self.assertRaisesRegex(ValueError, 'int32'):
            self.analyze()

    def test_sentinel_and_name_roles_are_not_interchangeable(self):
        for bad in (sample(object_id=0), sample(name='unexpected')):
            self.objects.update(attempts=1, absent=1, samples=[bad])
            with self.assertRaisesRegex(ValueError, 'roles'):
                self.analyze()

    def test_disabled_capture_cannot_inherit_previous_session(self):
        self.summary = capture(False)
        self.summary['lookup_diagnostics']['kinds'][0].update(attempts=1, returned=1)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            self.analyze()

    def test_candidate_archive_schema_and_printable_name_are_checked(self):
        for field, value in (('candidate', 'other'), ('archive', 'M01.mix')):
            old = self.summary[field]
            self.summary[field] = value
            with self.assertRaises(ValueError):
                self.analyze()
            self.summary[field] = old
        self.data['schema'] = True
        with self.assertRaisesRegex(ValueError, 'schema'):
            self.analyze()
        self.data['schema'] = 1
        self.data['kinds'][0].update(attempts=1, absent=1, samples=[sample(object_id=0, name='bad\n')])
        with self.assertRaisesRegex(ValueError, 'ASCII'):
            self.analyze()

    def test_cli_keeps_details_private_and_stdout_counts_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'build') as directory:
            root = Path(directory)
            summary_path = root / 'summary.json'
            self.data['kinds'][0].update(attempts=1, absent=1,
                                       samples=[sample(object_id=0, name='private_sample_name')])
            summary_path.write_text(json.dumps(self.summary))
            command = [sys.executable, str(ROOT / 'tools/analyze_script_lookups.py'), str(summary_path),
                       '--candidate', 'synthetic', '--archive', 'M13.mix', '--output']
            result = subprocess.run(command + [str(root / 'report.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('private_sample_name', result.stdout)
            self.assertIn('private_sample_name', (root / 'report.json').read_text())
            result = subprocess.run(command + [str(ROOT / 'reports/forbidden.json')],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('private build/', result.stderr)
            self.assertFalse((ROOT / 'reports/forbidden.json').exists())


class LookupSourceBoundaryTests(unittest.TestCase):
    def test_patch_is_registered_after_hash_anchored_patches(self):
        stage = (ROOT / 'tools/stage_sources.sh').read_text()
        self.assertLess(stage.index('ww3d-a35-original-sorting-lifecycle.patch'),
                        stage.index('combat-a35-script-lookup-telemetry.patch'))
        self.assertLess(stage.index('combat-a35-script-lookup-telemetry.patch'),
                        stage.index('# Compare final patched contents'))
        inventory = load_inventory(ROOT)
        self.assertIn('combat-a35-script-lookup-telemetry.patch', str(inventory))

    def test_staged_hook_dry_run_is_zero_fuzz_and_preserves_owners(self):
        # Replay pristine owners in registry order; never reverse active staging.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'scriptcommands.cpp'
            before, result = replay_to_patch(directory, 'combat', ('scriptcommands.cpp',),
                'combat-a35-script-lookup-telemetry.patch')
            text = before['scriptcommands.cpp']
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            patched = target.read_text()
            self.assertIn('return object;', patched)
            self.assertEqual(patched.count('GameObjManager::Find_ScriptableGameObj( obj_id )'), 1)
            self.assertIn('ConversationMgrClass::Create_New_Conversation( conversation )', patched)
            self.assertEqual(patched.count('REF_PTR_RELEASE( conversation )'),
                             text.count('REF_PTR_RELEASE( conversation )'))
            self.assertIn('Renegade_Ui_Pointer_To_Token(file)', patched)
            self.assertIn('return (int)( file );', patched)
            self.assertFalse(list(Path(directory).glob('*.orig')))
            self.assertFalse(list(Path(directory).glob('*.rej')))

    def test_reset_before_original_load_and_not_at_gameplay_start(self):
        source = (ROOT / 'port/platform/vita/a31_vita_runtime.cpp').read_text()
        self.assertEqual(source.count('A35_Campaign_Flight_Reset('), 1)
        reset = source.index('A35_Campaign_Flight_Reset(')
        self.assertLess(reset, source.index('CombatManager::Pre_Load_Level(true)'))
        self.assertLess(reset, source.index('CombatManager::Load_Level_Threaded('))
        self.assertIn('user/config/script-coverage.flag', source)
        context = source.index('A35_Script_Lookup_Set_Context(A35_LOOKUP_GAMEPLAY')
        self.assertLess(context, source.index('A31_Interactive_Run_Simulation_Frame();', context))
        self.assertIn('"interactive_session_ready", result.frames, sceKernelGetProcessTimeWide()', source)

    def test_worker_hooks_use_fixed_collector_not_flight_recorder(self):
        source = (ROOT / 'port/developer/a35_script_lookup_telemetry.cpp').read_text()
        for forbidden in ('fopen(', 'malloc(', 'new ', 'A35_Campaign_Flight_', 'static_cast<int>(name)'):
            self.assertNotIn(forbidden, source)
        self.assertIn('pthread_mutex_trylock', source)
        self.assertIn('epoch != gLookupEpoch.load()', source)
        self.assertIn('gLookupEpoch.store(0U)', source)
        self.assertIn('value != UINT32_MAX', source)
        self.assertIn('ATOMIC_INT_LOCK_FREE == 2', source)
        self.assertIn('sizeof(A35ScriptLookupSnapshot) <= 10240U', source)

    def test_actual_native_host_and_prepared_probe_source_selection(self):
        native = (ROOT / 'CMakeLists.txt').read_text()
        host = (ROOT / 'tools/host_a30_definitions/CMakeLists.txt').read_text()
        name = 'port/developer/a35_script_lookup_telemetry.cpp'
        self.assertIn(name, native[native.index('set(RENEGADE_A30_PORT_SOURCES'):])
        interactive = host[host.index('add_executable(a31_interactive_runtime'):]
        self.assertIn(name, interactive[:interactive.index('set_target_properties')])
        self.assertIn('add_executable(a35_script_lookup_selftest', host)
        for path in ('tools/build.sh', 'tools/build_fast_candidate.sh'):
            self.assertIn('tools.test_script_lookup_telemetry', (ROOT / path).read_text())


if __name__ == '__main__':
    unittest.main()
