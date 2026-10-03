import json
import unittest
from tools.analyze_conversation_transitions import analyze


def event(name='remark_scheduled', detail=None, **extra):
    return {'candidate': 'test', 'archive': 'M13.mix', 'load_source': 'M13.mix',
            'category': 'conversation', 'name': name,
            'detail': detail or 'instance=1 conversation_id=2 action=7 remark=0 text_id=100 next_seconds=0 reason=0',
            **extra}


class TransitionAnalysis(unittest.TestCase):
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
