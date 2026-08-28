import hashlib
import pathlib
import tempfile
import unittest
import zipfile

from tools.audit_tt_reference import audit_reference


ROOT = pathlib.Path(__file__).resolve().parents[1]


class TiberianTechnologiesReferenceAuditTests(unittest.TestCase):
    def test_pinned_official_reference_audit_is_read_only_and_semantic(self):
        with tempfile.TemporaryDirectory() as temporary:
            temp = pathlib.Path(temporary)
            local = temp / "local"
            (local / "staging/wwlib").mkdir(parents=True)
            (local / "staging/wwaudio").mkdir(parents=True)
            (local / "upstream/CnC_Renegade/Code/WWMath").mkdir(parents=True)
            (local / "upstream/CnC_Renegade/Code/wwlib").mkdir(parents=True)
            (local / "staging/wwlib/chunkio.cpp").write_text(
                "File->Seek(csize - pos,SEEK_CUR);\n"
                "PositionStack[StackIndex-1] += csize - pos;\n"
            )
            (local / "upstream/CnC_Renegade/Code/WWMath/lineseg.cpp").write_text(
                "Transform_Vector(tm,that.P0,&P0);\n"
                "Rotate_Vector(tm,that.Dir,&Dir);\n"
                "Length = that.Length;\n"
            )
            (local / "upstream/CnC_Renegade/Code/wwlib/systimer.h").write_text(
                "return time - StartTime; return time + WrapAdd;\n"
            )
            (local / "staging/wwaudio/AudioEvents.h").write_text(
                "this->Add ( AUDIO_CALLBACK_STRUCT<T> (pointer, user_data));\n"
                "return this->Vector[index].callback_ptr;\n"
                "this->Delete (index);\n"
            )
            (local / "staging/wwaudio/AudibleSound.cpp").write_text(
                "CHUNKID_VARIABLES = 0x00000100,\n"
                "CHUNKID_BASE_CLASS = 0x00000200,\n"
                "VARID_UNUSED1 = 0x01, VARID_UNUSED2, VARID_PRIORITY,\n"
                "WRITE_MICRO_CHUNK (csave, VARID_PRIORITY, m_Priority)\n"
                "READ_MICRO_CHUNK (cload, VARID_VIRTUAL_CHANNEL, m_VirtualChannel)\n"
            )

            archive_path = temp / "source.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(
                    "source/scripts/AudioCallbackListClass.h",
                    "Add(callbackStruct); return (*this)[index].callback; Remove(index);\n",
                )
                archive.writestr(
                    "source/scripts/AudibleSoundDefinitionClass.cpp",
                    "csave.Begin_Chunk(0x100); csave.Begin_Chunk(0x200);\n"
                    "WRITE_MICRO_CHUNK(csave,3,m_Priority);\n"
                    "READ_MICRO_CHUNK(cload,22,m_VirtualChannel);\n",
                )
                archive.writestr(
                    "source/scripts/COPYING",
                    "GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n",
                )
                archive.writestr(
                    "source/scripts/ChunkClasses.cpp",
                    "either version 2, or (at your option) any later\n"
                    "MCHeader.ChunkSize - MicroChunkPosition;\n"
                    "PositionStack[StackIndex-1] += value;\n",
                )
                archive.writestr(
                    "source/scripts/LineSegClass.cpp",
                    "Transform_Vector(transform, object.P0, &P0);\n"
                    "Rotate_Vector(transform, object.Dir, &Dir);\n"
                    "Length = object.Length;\n",
                )
                archive.writestr(
                    "source/scripts/SysTimeClass.cpp", "return uTimeInitNeg + u;\n"
                )
                archive.writestr(
                    "source/scripts/WWAudioClass.h",
                    "Get_Active_Sound_Page(void) { m_CurrPage; }\n",
                )
            diff_path = temp / "source.diff"
            diff_path.write_text(
                "diff -urN sourceold/scripts/A.h source/scripts/A.h\n"
            )
            archive_md5 = hashlib.md5(archive_path.read_bytes()).hexdigest()
            diff_md5 = hashlib.md5(diff_path.read_bytes()).hexdigest()
            archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            diff_sha256 = hashlib.sha256(diff_path.read_bytes()).hexdigest()
            result = audit_reference(
                archive_path,
                diff_path,
                local,
                archive_md5,
                diff_md5,
                archive_sha256,
                diff_sha256,
            )
            self.assertEqual(result["result"], "PASSED_NO_UNJUSTIFIED_SOURCE_IMPORT")
            self.assertEqual(result["release_diff"]["changed_files"], ["scripts/A.h"])
            self.assertEqual(
                result["active_vita_blocker_inventory"]["update_diff_matches"], []
            )
            self.assertTrue(
                all(
                    item["local_semantics_present"]
                    for item in result["portable_correctness_patterns"]
                )
            )
            self.assertEqual(len(result["portable_correctness_patterns"]), 5)
            self.assertTrue(
                all(item["observed"] for item in result["known_reference_hazards"])
            )

    def test_fetch_wrapper_pins_official_release_outside_the_tree(self):
        wrapper = (ROOT / "tools/fetch_tt_484_reference.sh").read_text()
        self.assertIn("/tmp/renegade-vita-tt-reference/4.8.4-r9000", wrapper)
        self.assertIn("5bf9acce0663514ea5e84ff5e0c16fb1", wrapper)
        self.assertIn("c746d12f7bbe06b99e3a15b6856ab3f4", wrapper)
        self.assertIn("8d3c2df2af0b2a7bb49b4e1a0353947b49fc2b228f849024e1a7bf18a0fddfcd", wrapper)
        self.assertIn("6a73ca645b1591b3c0456bb34c859d8b4644a64401503ae0f30a8ee68d1e314b", wrapper)
        self.assertNotIn("port/patches", wrapper)


if __name__ == "__main__":
    unittest.main()
