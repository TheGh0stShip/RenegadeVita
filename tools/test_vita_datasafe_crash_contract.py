import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VitaDataSafeCrashContract(unittest.TestCase):
    def test_invalid_handle_guard_is_deterministically_staged(self):
        stage = (ROOT / "tools" / "stage_sources.sh").read_text(encoding="utf-8")
        patch = ROOT / "port" / "patches" / "commando-a35-datasafe-invalid-handle-guard.patch"
        self.assertTrue(patch.exists())
        self.assertIn(patch.name, stage)

    def test_get_entry_returns_null_before_list_dereference(self):
        source = (ROOT / "staging" / "commando" / "datasafe.cpp").read_text(encoding="utf-8")
        start = source.index("DataSafeEntryClass *GenericDataSafeClass::Get_Entry(DataSafeHandleClass handle)")
        end = source.index("DataSafeEntryClass *entry_ptr = Safe[list]->SafeList;", start)
        block = source[start:end]
        self.assertIn("list < 0 || list >= NumLists || Safe[list] == NULL", block)
        self.assertIn("return(NULL);", block)

    def test_other_raw_datasafe_queries_fail_closed(self):
        source = (ROOT / "staging" / "commando" / "datasafe.cpp").read_text(encoding="utf-8")
        type_start = source.index("int GenericDataSafeClass::Get_Entry_Type(DataSafeHandleClass handle)")
        type_end = source.index("return(Safe[list]->EntryType);", type_start)
        type_block = source[type_start:type_end]
        self.assertIn("list < 0 || list >= NumLists || Safe[list] == NULL", type_block)
        self.assertIn("return(-1);", type_block)

        index_start = source.index("DataSafeEntryClass *GenericDataSafeClass::Get_Entry_By_Index")
        index_end = source.index("DataSafeEntryClass *entry_ptr = Safe[list]->SafeList;", index_start)
        index_block = source[index_start:index_end]
        self.assertIn("list < 0 || list >= NumLists || Safe[list] == NULL", index_block)
        self.assertIn("return(NULL);", index_block)


if __name__ == "__main__":
    unittest.main()
