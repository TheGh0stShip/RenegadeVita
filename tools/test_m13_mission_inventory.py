import struct
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.check_m13_mission_inventory import runtime_cycles
from tools.renegade_cinematic_dependency_scan import level_asset_dependencies


class FakeArchive:
    path = Path("M13.mix")

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read_binary(self, name: str) -> bytes:
        if name != "m13.dep":
            raise KeyError(name)
        return self.payload


class M13MissionInventoryTests(unittest.TestCase):
    def test_original_asset_dependency_microchunks(self) -> None:
        records = b"\x01\x09Tank.w3d\0\x01\x05.w3d"
        records += b"\0"
        payload = struct.pack("<II", 0x04020527, len(records)) + records
        result = level_asset_dependencies(FakeArchive(payload))
        self.assertEqual(result["files"], ["Tank.w3d", ".w3d"])
        self.assertEqual(result["suffix_counts"], {".w3d": 1, "": 1})

    def test_asset_dependency_chunk_rejects_invalid_length(self) -> None:
        archive = FakeArchive(struct.pack("<II", 0x04020527, 999) + b"\x01\x02X\0")
        with self.assertRaisesRegex(ValueError, "invalid Westwood"):
            level_asset_dependencies(archive)

    def test_runtime_census_rejects_incomplete_cycle(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "runtime.log"
            path.write_text("m13.object\t1\t2\t3\tPreset\tModel\t0\t0\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                runtime_cycles(path)


if __name__ == "__main__":
    unittest.main()
