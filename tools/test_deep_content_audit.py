"""Asset-free negative controls for deep read-only content discovery."""
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.deep_content_dependencies import DeepContentDependencies, literal_presets
from tools.audit_deep_saved_content import conversations, raw_chunks
from tools.audit_m13_level_owners import chunks
from tools.test_m13_level_owners import chunk, micro, integer
from tools.check_m13_script_coverage import script_dependencies
from tools.check_deep_audit_receipts import blockers
from tools.audit_w3d_loader_coverage import root_types


class FakeArchive:
    def __init__(self,name,entries):
        self.path=Path(name);self.entries=entries
    def read_binary(self,name):
        return self.entries[name].encode('ascii')


class DeepContentAuditTests(unittest.TestCase):
    def test_w3d_loader_requirements_are_actual_root_chunks(self):
        self.assertEqual(root_types(chunk(0x500,b'payload')+chunk(0x742,b'ring')),[0x500,0x742])
        self.assertEqual(root_types(chunk(0x100,chunk(0x500,b''))),[0x100])
        with self.assertRaises(ValueError):
            root_types(struct.pack('<II',0x500,0x80000040))

    def test_empty_audit_cannot_pass(self):
        result=blockers([],{'routes':[]},{'network_factories':{'factories':[]}})
        self.assertEqual(result[0]['kind'],'missing_map_receipts')

    def test_unbuilt_script_and_missing_ui_are_separate_blockers(self):
        maps=[{'map':n,'missing_owners':{},'missing_linked_scripts':['Helper'],
               'unresolved_scripts':[],'missing_factory_owners':[], 'missing_factory_load_methods':[],
               'unmapped_factory_types':[],'missing_commands':[],'unresolved_texts':[]}
              for n in ['M00_Tutorial.mix','Skirmish00.mix','M13.mix','M01.mix']]
        ui={'routes':[{'area':'options','name':'Options','selected_by_full_port_generator':False,
                       'present_in_existing_generated_templates':False}]}
        result=blockers(maps,ui,{'network_factories':{'factories':[]}})
        self.assertEqual([r['kind'] for r in result].count('missing_linked_scripts'),4)
        self.assertEqual([r['kind'] for r in result].count('missing_ui_template'),1)

    def test_at_bone_and_powerup_use_second_argument(self):
        code='Commands->Create_Object_At_Bone(host, "Trooper", "Bone"); Commands->Give_PowerUp(obj, "Rifle", false); Commands->Create_Explosion("Blast", pos, 0);'
        self.assertEqual(literal_presets(code),{'Trooper','Rifle','Blast'})

    def test_global_cinematic_recursion_retains_scripts_and_game_presets(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/'always.dat').touch()
            global_data=FakeArchive('always.dat',{'root.txt':'0 Create_Object, 1, "Model"\n0 Attach_Script, 1, "Test_Cinematic", "child.txt"',
                'child.txt':'0 Create_Real_Object, 2, "Trooper"\n0 Attach_Script, 2, "Helper"\n0 Attach_Script, 2, "Test_Cinematic", "root.txt"'})
            with patch('tools.deep_content_dependencies.MixArchive',return_value=global_data):
                scanner=DeepContentDependencies(path,FakeArchive('M.mix',{}))
            presets,scripts=scanner.from_source('Commands->Attach_Script(obj,"Test_Cinematic","root.txt");','Root')
            self.assertEqual(presets,{'Trooper'})
            self.assertEqual(scripts,{'Helper','Test_Cinematic'})
            self.assertEqual(len(scanner.receipt()['text_members']),2)

    def test_missing_cinematic_is_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            scanner=DeepContentDependencies(Path(temp),FakeArchive('M.mix',{}))
            scanner.from_source('"missing.txt"','Root')
            self.assertEqual(scanner.receipt()['missing_text_names'],['missing.txt'])

    def test_multiplayer_without_prefix_does_not_seed_other_missions(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);(p/'Scripts.cpp').write_text('DECLARE_SCRIPT(MX0_Start, "") {}; DECLARE_SCRIPT(Base, "") {};')
            result=script_dependencies(p,['Base'],prefixes=())
            self.assertEqual([s['name'] for s in result['required_scripts']],['Base'])

    def test_conversation_local_ids_and_original_category_width(self):
        variables=chunk(0x08090316,micro(0,b'Greeting\0')+micro(1,integer(42)))
        conversation=chunk(0x08090319,variables,True)
        for prefix,width in [(integer(1),4),(b'\1',1)]:
            data=chunk(0x40700,chunk(0x08090318,prefix+conversation,True),True)
            result=conversations(chunks(data))
            self.assertEqual(result[0]['name'],'Greeting')
            self.assertEqual(result[0]['category_bytes'],width)
            self.assertEqual(result[0]['id'],42)

    def test_invalid_conversation_category_is_rejected(self):
        for prefix in [integer(2),b'\1\1\0\0',b'']:
            data=chunk(0x40700,chunk(0x08090318,prefix,True),True)
            with self.assertRaises(ValueError):
                conversations(chunks(data))

    def test_raw_chunk_bounds_are_enforced(self):
        for value in [b'abc',struct.pack('<II',1,100)]:
            with self.assertRaises(ValueError):
                list(raw_chunks(value))


if __name__=='__main__':
    unittest.main()
