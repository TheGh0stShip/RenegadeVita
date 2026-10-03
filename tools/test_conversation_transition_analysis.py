import json
import unittest
from tools.analyze_conversation_transitions import analyze


def event(name='remark_scheduled', detail=None, **extra):
    return {'candidate': 'test', 'archive': 'M13.mix', 'load_source': 'M13.mix',
            'category': 'conversation', 'name': name,
            'detail': detail or 'instance=1 conversation_id=2 action=7 remark=0 text_id=100 next_seconds=0 reason=0',
            **extra}


class TransitionAnalysis(unittest.TestCase):
    def test_logical_configuration_and_hearing_are_distinct_not_delivery(self):
        rows = [event('configured_before_scene_add', 'sound_id=8 type=400004 receiver_id=0 creator_id=100 observers_active=0', category='logical_stimulus'),
                event('hearing_callback_entry', 'sound_id=8 type=400004 receiver_id=200 creator_id=100 observers_active=1', category='logical_stimulus')]
        report = analyze(rows)
        self.assertEqual(len(report['logical_stimuli']), 2)
        self.assertEqual(report['logical_stimuli'][1]['receiver_id'], 200)
        self.assertFalse(report['logical_stimuli'][1]['observer_callback_delivery_proven'])
        self.assertFalse(report['callback_delivery_verified'])

    def test_logical_malformed_width_type_boolean_and_creation_shape(self):
        base = 'sound_id=8 type=400004 receiver_id=200 creator_id=100 observers_active=1'
        invalid = ['bad', base + ' extra=1', 'x' * 224,
                   base.replace('observers_active=1', 'observers_active=2'),
                   base.replace('type=400004', 'type=77')]
        for field, value in (('sound_id', 8), ('type', 400004), ('receiver_id', 200), ('creator_id', 100)):
            for bad in (2147483648, -2147483649):
                invalid.append(base.replace(f'{field}={value}', f'{field}={bad}'))
        for detail in invalid:
            with self.subTest(detail=detail), self.assertRaises(ValueError):
                analyze([event('hearing_callback_entry', detail, category='logical_stimulus')])
        with self.assertRaises(ValueError):
            analyze([event('configured_before_scene_add', base, category='logical_stimulus')])

    def test_logical_repetitions_inactive_observers_and_shared_loss_retained(self):
        row = event('hearing_callback_entry', 'sound_id=8 type=400005 receiver_id=200 creator_id=0 observers_active=0', category='logical_stimulus')
        report = analyze([row, row, event('queue_overflow', 'unretained=4')])
        self.assertEqual(len(report['logical_stimuli']), 2)
        self.assertEqual(report['queue_unretained'], 4)
        self.assertEqual(report['findings'][0]['kind'], 'observers_inactive_at_hearing_entry')
        self.assertFalse(report['complete_progression_verified'])

    def test_logical_identity_and_future_events_do_not_create_false_pairs(self):
        row = event('hearing_callback_entry', 'sound_id=8 type=400005 receiver_id=200 creator_id=0 observers_active=1', category='logical_stimulus')
        for field in ('candidate', 'archive', 'load_source'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'mixed'):
                analyze([event(), {**row, field: 'different'}])
        report = analyze([event('future_event', 'unknown', category='logical_stimulus')])
        self.assertEqual(report['logical_stimuli'], [])
        self.assertEqual(report['findings'][0]['kind'], 'unrecognized_logical_stimulus_event')

    def test_action_miss_is_not_delivery_or_mission_failure(self):
        report = analyze([event('observer_absent_at_completion',
                                'object_id=100 observer_id=9 action_id=-1 reason=3', category='script_action')])
        self.assertEqual(report['action_misses'][0]['reason'], 3)
        self.assertEqual(report['action_misses'][0]['action_id'], -1)
        self.assertFalse(report['callback_delivery_verified'])
        self.assertFalse(report['complete_progression_verified'])

    def test_action_malformed_and_all_fields_width_checked(self):
        base = 'object_id=100 observer_id=9 action_id=8 reason=3'
        invalid = ['bad', base + ' extra=4', 'x' * 224]
        for field, value in (('object_id', 100), ('observer_id', 9), ('action_id', 8), ('reason', 3)):
            invalid.append(base.replace(f'{field}={value}', f'{field}=2147483648'))
            invalid.append(base.replace(f'{field}={value}', f'{field}=-2147483649'))
        for detail in invalid:
            with self.subTest(detail=detail), self.assertRaises(ValueError):
                analyze([event('observer_absent_at_completion', detail, category='script_action')])

    def test_action_identity_must_match_other_types(self):
        for changed in ('candidate', 'archive', 'load_source'):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'mixed'):
                analyze([event(), event('observer_absent_at_completion',
                                       'object_id=1 observer_id=2 action_id=3 reason=4',
                                       category='script_action', **{changed: 'different'})])

    def test_action_unknown_event_not_interpreted_as_miss(self):
        report = analyze([event('future_event', 'unknown', category='script_action')])
        self.assertEqual(report['action_misses'], [])
        self.assertEqual(report['findings'][0]['kind'], 'unrecognized_action_event')

    def test_repeated_action_ids_are_not_paired_or_deduplicated(self):
        row = event('observer_absent_at_completion', 'object_id=1 observer_id=2 action_id=3 reason=4',
                    category='script_action')
        report = analyze([row, row, event('queue_overflow', 'unretained=3')])
        self.assertEqual(len(report['action_misses']), 2)
        self.assertEqual(report['queue_unretained'], 3)

    def test_timer_miss_is_not_a_mission_failure_verdict(self):
        report = analyze([event('observer_absent_at_expiry',
                                'object_id=100 observer_id=9 timer_id=-1', category='script_timer')])
        self.assertEqual(report['timer_misses'][0]['timer_id'], -1)
        self.assertFalse(report['complete_progression_verified'])

    def test_timer_bad_shape_and_width_rejected(self):
        for detail in ('bad', 'object_id=100 observer_id=9 timer_id=2147483648'):
            with self.assertRaises(ValueError):
                analyze([event('observer_absent_at_expiry', detail, category='script_timer')])

    def test_timer_and_conversation_identity_must_match(self):
        with self.assertRaisesRegex(ValueError, 'mixed'):
            analyze([event(), event('observer_absent_at_expiry', 'object_id=1 observer_id=2 timer_id=3',
                                   category='script_timer', candidate='different')])
    def test_monitor_attempt_is_not_callback_delivery(self):
        detail = 'instance=1 conversation_id=2 action=7 object_id=100 observer_index=0 reason=3'
        report = analyze([event('observer_call_attempted', detail)])
        self.assertEqual(report['monitor_events'][0]['object_id'], 100)
        self.assertEqual(report['monitor_events'][0]['reason'], 3)
        self.assertFalse(report['callback_delivery_verified'])

    def test_capacity_rejection_is_explicit_finding(self):
        detail = 'instance=1 conversation_id=2 action=7 object_id=100 observer_index=-1 reason=0'
        report = analyze([event('monitor_capacity_rejected', detail)])
        self.assertEqual(report['findings'][0]['kind'], 'monitor_capacity_rejected')

    def test_monitor_bad_shape_and_numeric_width_rejected(self):
        for detail in ('bad', 'instance=1 conversation_id=2 action=7 object_id=2147483648 observer_index=-1 reason=0'):
            with self.assertRaises(ValueError):
                analyze([event('monitor_inserted', detail)])

    def test_zero_duration_is_observation_not_callback_or_progression_proof(self):
        row = analyze([event(), event('owner_finished')])
        self.assertEqual(row['nonpositive_remark_timers'], 1)
        self.assertFalse(row['callback_delivery_verified'])
        self.assertFalse(row['complete_progression_verified'])

    def test_queue_loss_keeps_count(self):
        self.assertEqual(analyze([event('queue_overflow', 'unretained=8')])['queue_unretained'], 8)

    def test_unknown_instance_is_not_deduplicated(self):
        row = event(detail='instance=0 conversation_id=2 action=7 remark=0 text_id=0 next_seconds=1 reason=0')
        report = analyze([row, row])
        self.assertEqual(report['unknown_instance_records'], 2)
        self.assertEqual(len(report['transitions']), 2)

    def test_same_engine_id_different_tokens_remain_separate(self):
        a = event()
        b = event(detail=a['detail'].replace('instance=1', 'instance=2'))
        self.assertEqual([r['instance'] for r in analyze([a, b])['transitions']], [1, 2])

    def test_nonfinite_timer_is_json_safe_finding(self):
        report = analyze([event(detail=event()['detail'].replace('seconds=0', 'seconds=nan'))])
        self.assertEqual(report['findings'][0]['kind'], 'nonfinite_timer')
        json.dumps(report, allow_nan=False)

    def test_malformed_overlong_and_width_exceeded_rejected(self):
        for detail in ('bad', 'x' * 224, event()['detail'].replace('instance=1', 'instance=18446744073709551616'),
                       event()['detail'].replace('reason=0', 'reason=2147483648'), 'unretained=0'):
            with self.subTest(detail=detail):
                with self.assertRaises(ValueError):
                    analyze([event('queue_overflow' if detail.startswith('unretained') else 'remark_scheduled', detail)])

    def test_mixed_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, 'mixed'):
            analyze([event(), event(candidate='other')])

    def test_unrelated_events_are_not_conversation_evidence(self):
        self.assertEqual(analyze([event(category='mission')])['transitions'], [])


if __name__ == '__main__':
    unittest.main()
