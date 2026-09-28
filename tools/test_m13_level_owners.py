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


if __name__ == "__main__":
    unittest.main()
