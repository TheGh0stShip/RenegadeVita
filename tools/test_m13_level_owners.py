import struct
import unittest

from tools.audit_m13_level_owners import chunks, definitions, level_records, microchunks, u32


def chunk(kind, payload, children=False):
    return struct.pack("<II", kind, len(payload) | (0x80000000 if children else 0)) + payload


def micro(kind, payload):
    return bytes((kind, len(payload))) + payload


def integer(value):
    return struct.pack("<I", value)


def definition(factory, identity, body):
    base = chunk(0x200, chunk(0x100, micro(1, integer(identity)) + micro(3, b"Preset\0")), True)
    payload = chunk(0x100100, integer(0x87654321)) + chunk(0x100101, base + body, True)
    return chunk(0x101, chunk(0x101, chunk(factory, payload, True), True), True)


class M13LevelOwnersTests(unittest.TestCase):
    def test_combat_start_and_respawn_are_script_roots_without_placed_owner(self):
        variables = chunk(916991715, micro(4, b'MTU_Commando_Startup\0') +
                          micro(5, b'MTU_Commando\0'))
        combat = chunk(916991655, variables, True)
        result = level_records(chunks(chunk(0x40000, combat, True)))
        self.assertEqual([row['name'] for row in result['script_records']],
                         ['MTU_Commando_Startup', 'MTU_Commando'])
        self.assertEqual([row['binding_kind'] for row in result['script_records']],
                         ['combat_start_script', 'combat_respawn_script'])
        for row in result['script_records']:
            self.assertIsNone(row['owner'])
            self.assertIsNone(row['parameters'])

    def test_unanchored_combat_variables_do_not_supply_roots(self):
        variables = chunk(916991715, micro(4, b'MTU_Commando_Startup\0'))
        for payload in (variables, chunk(916991655, variables, True),
                        chunk(0x40000, chunk(99, variables, True), True)):
            self.assertEqual(level_records(chunks(payload))['script_records'], [])

    def test_empty_combat_script_is_not_an_unknown_registration(self):
        combat = chunk(916991655, chunk(916991715, micro(4, b'\0')), True)
        self.assertEqual(level_records(chunks(chunk(0x40000, combat, True)))['script_records'], [])

    def test_ambiguous_combat_fields_or_variables_rejected(self):
        duplicate = chunk(916991655, b'', True) + chunk(916991655, b'', True)
        with self.assertRaises(ValueError):
            level_records(chunks(chunk(0x40000, duplicate, True)))
        for payload in (chunk(916991715, micro(4, b'A\0') + micro(4, b'B\0')),
                        chunk(916991715, b'') + chunk(916991715, b''),
                        chunk(916991715, micro(4, b'no terminator'))):
            with self.assertRaises(ValueError):
                level_records(chunks(chunk(0x40000, chunk(916991655, payload, True), True)))

    def test_physics_only_root_uses_definition_field_not_pointer_token(self):
        body = micro(0, integer(0xfedcba98)) + micro(6, integer(123))
        result = level_records(chunks(chunk(0x00660055, body)))
        self.assertEqual(result["physics"], [{"definition_id": 123, "offset": 0}])
        with self.assertRaises(ValueError):
            level_records(chunks(chunk(0x00660055, micro(6, b"12345678"))))

    def test_serialized_script_and_object_tokens_are_unsigned_32bit(self):
        script = chunk(131001135, micro(1, b"M03_SAM_Site_Logic\0") + micro(4, integer(0xfedcba98)))
        obj = chunk(910991407, micro(2, integer(12345)) + micro(3, integer(1500001)))
        result = level_records(chunks(chunk(900, script + obj, True)))
        self.assertEqual(result["script_records"][0]["owner_token"], 0xfedcba98)
        self.assertEqual(result["objects"][0]["definition_id"], 12345)

    def test_rejects_truncated_or_out_of_parent_records(self):
        for data in (b"x", struct.pack("<II", 1, 100), chunk(1, b"x", True)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                chunks(data)
        for data in (b"x", b"\x01\x08abc"):
            with self.assertRaises(ValueError):
                microchunks(data)
        with self.assertRaises(ValueError):
            u32(b"\0" * 8)

    def test_conversation_category_is_not_guessed_as_a_chunk(self):
        result = level_records(chunks(chunk(0x40700, b"\x01\0\0\0opaque category", True)))
        self.assertEqual(len(result["skipped_subsystems"]), 1)
        self.assertEqual(result["script_records"], [])

    def test_definition_scripts_preserve_repeated_microchunk_ids(self):
        body = chunk(627001057, micro(2, b"First\0") + micro(3, b"params\0") + micro(2, b"Second\0"))
        result = definitions(chunks(definition(0x40123, 123, body)))
        self.assertEqual(result[123]["scripts"], ["First", "Second"])

    def test_twiddler_choices_exclude_base_identity(self):
        body = chunk(0x100, micro(1, integer(44)) + micro(1, integer(55)))
        result = definitions(chunks(definition(0x102, 123, body)))
        self.assertEqual(result[123]["definition_references"], [44, 55])
        self.assertEqual([r['id'] for r in result[123]['definition_reference_provenance']], [44, 55])

    def test_reference_provenance_preserves_repeated_choices_and_null(self):
        body = chunk(0x100, micro(1, integer(44)) + micro(1, integer(44)) + micro(1, integer(0)))
        row = definitions(chunks(definition(0x102, 123, body)))[123]
        self.assertEqual(row['definition_references'], [44])
        self.assertEqual([r['id'] for r in row['definition_reference_provenance']], [44, 44, 0])

    def test_named_typed_reference_retains_field_and_owner_container(self):
        schema = {(500, 501): {1: 'SyntheticMuzzleFlashDefID'}}
        body = chunk(500, b'', True) + chunk(501, micro(1, integer(777)))
        row = definitions(chunks(definition(0x40123, 123, body)), schema)[123]
        reference = row['definition_reference_provenance'][0]
        self.assertEqual(reference['id'], 777)
        self.assertEqual(reference['field_name'], 'SyntheticMuzzleFlashDefID')
        self.assertEqual((reference['parent_chunk'], reference['variable_chunk'], reference['field_id']),
                         (500, 501, 1))

    def test_typed_reference_factory_scope_prevents_reused_layout_confusion(self):
        body = chunk(900, b'') + chunk(901, micro(2, integer(44)))
        schema = {(1234, 900, 901): {2: 'GeneralSound'}}
        general = definitions(chunks(definition(1234, 1, body)), schema)[1]
        hud = definitions(chunks(definition(1235, 2, body)), schema)[2]
        self.assertEqual(general['definition_references'], [44])
        self.assertEqual(hud['definition_references'], [])

    def test_typed_reference_requires_matching_sibling_parent(self):
        schema = {(500, 501): {1}}
        body = chunk(500, b"", True) + chunk(501, micro(1, integer(777)))
        result = definitions(chunks(definition(0x40123, 123, body)), schema)
        self.assertEqual(result[123]["definition_references"], [777])
        other = chunk(600, b"", True) + chunk(501, micro(1, integer(777)))
        result = definitions(chunks(definition(0x40123, 123, other)), schema)
        self.assertEqual(result[123]["definition_references"], [])

    def test_spawner_definition_and_attached_scripts(self):
        body = chunk(1014991054, micro(3, integer(73)) + micro(10, b"SpawnScript\0"))
        result = level_records(chunks(body))
        self.assertEqual(result["spawners"][0]["definition_id"], 73)
        self.assertEqual(result["script_records"][0]["name"], "SpawnScript")

    def test_script_owner_resolves_by_disk_token_not_record_order(self):
        script = chunk(131001135, micro(1, b"M03_SAM_Site_Logic\0") + micro(4, integer(0xfedcba98)))
        obj = chunk(910991407, micro(2, integer(82080057)) + micro(3, integer(1500015)))
        factory = chunk(0x40123, chunk(0x100100, integer(0xfedcba98)) +
                        chunk(0x100101, obj, True), True)
        result = level_records(chunks(script + factory))
        self.assertEqual(result["script_records"][0]["owner"],
                         {"instance_id": 1500015, "definition_id": 82080057})

    def test_parameters_and_spawner_ids_do_not_replace_owner_tokens(self):
        script = chunk(131001135, micro(1, b"Bound\0") + micro(2, b"100,sequence.txt,\0") +
                       micro(4, integer(0xffffffff)))
        spawner = chunk(1014991054, micro(1, integer(0xfedcba98)) + micro(3, integer(73)) +
                        micro(10, b"First\0") + micro(10, b"Second\0") +
                        micro(11, b"a.txt\0") + micro(11, b"b.txt\0"))
        result = level_records(chunks(script + spawner))
        self.assertEqual(result["script_records"][0]["parameters"], "100,sequence.txt,")
        self.assertEqual(result["script_records"][0]["owner_token"], 0xffffffff)
        self.assertEqual(result["spawners"][0]["instance_id"], 0xfedcba98)
        self.assertEqual([r["parameters"] for r in result["script_records"][1:]], ["a.txt", "b.txt"])
        self.assertEqual(result["script_binding_issues"], [])

    def test_mismatched_parallel_lists_retain_unpaired_values_and_block_closure(self):
        for body, unpaired in [(micro(10, b"First\0"), []),
                              (micro(11, b"orphan.txt\0"), ["orphan.txt"])]:
            data = chunk(1014991054, micro(1, integer(7)) + micro(3, integer(73)) + body)
            result = level_records(chunks(data))
            self.assertEqual(len(result["script_binding_issues"]), 1)
            self.assertEqual(result["script_binding_issues"][0]["unpaired_parameters"], unpaired)

    def test_definition_pairing_uses_loader_ordinals_and_keeps_empty_values(self):
        body = chunk(627001057, micro(2, b"First\0") + micro(3, b"\0") +
                     micro(2, b"Second\0") + micro(3, b"a,b,c\0"))
        result = definitions(chunks(definition(0x40123, 123, body)))[123]
        self.assertEqual(result["script_bindings"], [{"name": "First", "parameters": ""},
                         {"name": "Second", "parameters": "a,b,c"}])
        self.assertEqual(result["script_binding_issues"], [])

    def test_spawner_id_must_have_original_four_byte_width(self):
        data = chunk(1014991054, micro(1, b"12345678") + micro(3, integer(73)))
        with self.assertRaises(ValueError):
            level_records(chunks(data))


if __name__ == "__main__":
    unittest.main()
