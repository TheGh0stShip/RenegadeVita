import tempfile
import unittest
from pathlib import Path

from tools import audit_campaign_script_closure as closure


SOURCE_A = '''
#define EV_PING 1001
#define EV_PONG 1002
enum { EV_RANGE_LOW = 2000, EV_RANGE_HIGH = 2010 };
DECLARE_SCRIPT(Alpha_Script, "Zone:int,Name:string")
{
	void Created(GameObject *obj) {
		int zone = Get_Int_Parameter("Zone");
		const char *extra = Get_Parameter(5);
		Commands->Send_Custom_Event(obj, obj, EV_PING, 0, 0);
		Commands->Send_Custom_Event(obj, obj, 3333, 0, 0);
		Commands->Attach_Script(obj, "Beta_Script", "1");
		Commands->Attach_Script(obj, "Missing_Script", "1");
	}
	void Custom(GameObject *obj, int type, int param, GameObject *sender) {
		if (type == EV_PONG) { }
		if (type >= EV_RANGE_LOW && type <= EV_RANGE_HIGH) { }
		switch (type) { case 7: break; }
	}
};
DECLARE_SCRIPT(Beta_Script, "")
{
	void Custom(GameObject *obj, int type, int param, GameObject *sender) {
		if (type == EV_PING) { }
	}
};
#if 0
DECLARE_SCRIPT(Disabled_Script, "")
#endif
'''
SOURCE_B = '''
DECLARE_SCRIPT(alpha_script, "")
{
};
DECLARE_SCRIPT(Gamma_Script, "A:int")
{
};
'''


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / 'Mission01.cpp').write_text(SOURCE_A)
        (self.dir / 'Other.cpp').write_text(SOURCE_B)
        self.rows = closure.scan_registrations(self.dir, {'Mission01.cpp'})

    def tearDown(self):
        self.tmp.cleanup()

    def test_registrations_skip_disabled_code_and_record_selection(self):
        names = {row['name']: row['compiled'] for row in self.rows}
        self.assertNotIn('Disabled_Script', names)
        self.assertTrue(names['Alpha_Script'])
        self.assertFalse(names['Gamma_Script'])
        self.assertEqual(next(r for r in self.rows if r['name'] == 'Alpha_Script')['descriptor'],
                         'Zone:int,Name:string')

    def test_collisions_are_case_insensitive_and_severity_tracks_compilation(self):
        findings, registry = closure.registry_findings(self.rows)
        self.assertEqual([f['name'] for f in findings], ['alpha_script'])
        self.assertEqual(findings[0]['severity'], 'retail-identical')  # only one copy is compiled
        self.assertEqual(len(registry['alpha_script']), 2)
        both = closure.scan_registrations(self.dir, {'Mission01.cpp', 'Other.cpp'})
        self.assertEqual(closure.registry_findings(both)[0][0]['severity'], 'blocks completion')

    def test_binding_classification(self):
        _, registry = closure.registry_findings(self.rows)
        dll = {'alpha_script'}

        def kinds(name, parameters, placed=True, dll_names=dll):
            group = registry.get(name.lower(), [])
            return {(f['kind'], f['severity']) for f in closure.classify_binding(
                {'name': name, 'parameters': parameters}, group, dll_names, placed)}

        self.assertEqual(kinds('Nope_Script', '', dll_names=set()),
                         {('unregistered_script', 'retail-identical')})
        self.assertEqual(kinds('Nope_Script', '', dll_names={'nope_script'}),
                         {('unregistered_script', 'blocks completion')})
        self.assertEqual(kinds('Nope_Script', '', placed=False, dll_names={'nope_script'}),
                         {('unregistered_script', 'cosmetic')})
        self.assertEqual(kinds('Gamma_Script', '1', dll_names={'gamma_script'}),
                         {('registered_in_uncompiled_unit', 'blocks completion')})
        found = kinds('Alpha_Script', '')
        self.assertIn(('fewer_supplied_values', 'retail-identical'), found)
        self.assertIn(('read_beyond_supplied_values', 'retail-identical'), found)
        self.assertIn(('read_index_beyond_descriptor', 'retail-identical'), found)
        self.assertIn(('excess_supplied_values', 'retail-identical'), kinds('Beta_Script', '1,2'))

    def test_events_and_literal_attachments(self):
        senders, receivers, names, attachments = closure.scan_events(self.dir, self.rows)
        self.assertEqual({r['value'] for r in senders}, {1001, 3333})
        alpha = next(r for r in receivers if r['script'] == 'Alpha_Script')
        self.assertEqual(alpha['exact'], [7, 1002])
        self.assertEqual(alpha['range'], (2000, 2010))
        compiled = {'Mission01.cpp'}
        found, summary = closure.event_findings(senders, receivers, names, compiled, {2005, 9999})
        values = {(f['kind'], f['value']) for f in found}
        self.assertIn(('sender_without_receiver', 3333), values)
        self.assertNotIn(('sender_without_receiver', 1001), values)
        self.assertIn(('cinematic_send_custom_without_receiver', 9999), values)
        self.assertNotIn(('cinematic_send_custom_without_receiver', 2005), values)
        self.assertEqual(summary['per_unit']['Mission01.cpp']['senders_literal'], 2)
        # A receiver living only in an unselected unit is a port-side gap.
        found, _ = closure.event_findings(senders, receivers, names, set(), set())
        self.assertEqual(found, [])
        _, registry = closure.registry_findings(self.rows)
        attach = closure.attachment_findings(registry, attachments, compiled)
        self.assertEqual([(f['target'], f['severity']) for f in attach], [('Missing_Script', 'retail-identical')])

    def test_receiver_only_in_unselected_unit_blocks(self):
        senders = [{'owner': 'A.cpp', 'script': 'S', 'expression': '5', 'value': 5}]
        receivers = [{'owner': 'B.cpp', 'script': 'R', 'exact': [5], 'range': None, 'computed': []}]
        found, _ = closure.event_findings(senders, receivers, {}, {'A.cpp'}, set())
        self.assertEqual([(f['kind'], f['severity']) for f in found],
                         [('receiver_only_in_uncompiled_unit', 'blocks completion')])

    def test_named_parameter_event_identity_pairs_type_zero_senders(self):
        # Mission01-style: Send_Custom_Event(obj, to, 0, NAMED_CONSTANT, 0) and receivers testing `param`.
        (self.dir / 'Mission01.cpp').write_text('''
#define M01_GO 77
DECLARE_SCRIPT(Sender_S, "")
{ void Created(GameObject *o) { Commands->Send_Custom_Event(o, o, 0, M01_GO, 0); } };
DECLARE_SCRIPT(Receiver_S, "")
{ void Custom(GameObject *o, int type, int param, GameObject *s) { if (param == M01_GO) { } } };
''')
        rows = closure.scan_registrations(self.dir, {'Mission01.cpp'})
        senders, receivers, names, _ = closure.scan_events(self.dir, rows)
        self.assertEqual((senders[0]['value'], senders[0]['param_value']), (0, 77))
        self.assertEqual(receivers[-1]['param_exact'], [77])
        found, summary = closure.event_findings(senders, receivers, names, {'Mission01.cpp'}, set())
        self.assertEqual(found, [])
        self.assertEqual(summary['per_unit']['Mission01.cpp']['receiver_values_without_literal_sender'], 0)

    def test_cinematic_attachment_parser_uses_original_loader_rules(self):
        records, _ = closure.parse_payload(b'1.0 Attach_Script, 3, Alpha_Script, "1,2"\n2.0 Destroy_Object 3\n'
                                           b'3.0 Send_Custom, 1, 40, 0\n')
        sends = set()
        rows = closure.cinematic_attachments('x.txt', records, 'M01.mix', sends)
        self.assertEqual([(r['name'], r['location']) for r in rows], [('Alpha_Script', 'M01.mix:x.txt:1')])
        self.assertEqual(sends, {40})

    def test_dll_membership_requires_a_supplied_dll(self):
        self.assertIsNone(closure.dll_script_names([]))
        path = self.dir / 'x.dll'
        path.write_bytes(b'\0\0Some_Script_Name\0junk\0ab\0')
        self.assertIn('some_script_name', closure.dll_script_names([path]))


if __name__ == '__main__':
    unittest.main()
