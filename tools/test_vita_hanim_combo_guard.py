import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def function_body(source, function_name):
    start = source.index(f"\n{function_name}") + 1
    open_brace = source.index("{", start)
    depth = 0
    for offset, character in enumerate(source[open_brace:], start=open_brace):
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[open_brace:offset + 1]
    raise AssertionError(f"function body not closed: {function_name}")


class VitaHAnimComboGuardTests(unittest.TestCase):
    def test_null_combo_animation_assignment_falls_back_to_base_pose(self):
        source = (ROOT / "staging/ww3d2/animobj.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("ModeCombo.AnimCombo = anim_combo;", source)
        self.assertIn("CurMotionMode = (anim_combo != NULL) ? MULTIPLE_ANIM : BASE_POSE;", source)
        self.assertNotIn("CurMotionMode = MULTIPLE_ANIM;\n\tModeCombo.AnimCombo = anim_combo;", source)

    def test_htree_combo_update_falls_back_to_base_pose_for_null_combo(self):
        source = (ROOT / "staging/ww3d2/htree.cpp").read_text(encoding="utf-8", errors="replace")
        combo_body = function_body(source, "void HTreeClass::Combo_Update")
        base_body = function_body(source, "void HTreeClass::Base_Update")
        guard_offset = combo_body.index("if (anim == NULL)")
        pivot_offset = combo_body.index("PivotClass *pivot;")
        self.assertLess(guard_offset, pivot_offset)
        self.assertIn("Base_Update(root);", combo_body[guard_offset:pivot_offset])
        self.assertNotIn("if (anim == NULL)", base_body)

    def test_combo_update_skips_empty_motion_channels_before_pivot_count(self):
        source = (ROOT / "staging/ww3d2/htree.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("HAnimClass *motion = anim->Peek_Motion( anim_num );", source)
        self.assertIn("if ( motion != NULL )", source)
        self.assertIn("motion->Get_Num_Pivots()", source)
        self.assertNotIn("anim->Peek_Motion( anim_num )->Get_Num_Pivots()", source)

    def test_normalize_weights_skips_empty_motion_channels_before_pivot_count(self):
        source = (ROOT / "staging/ww3d2/hanim.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("HAnimClass *motion = Peek_Motion(anim_idx);", source)
        self.assertIn("if (motion != NULL)", source)
        self.assertIn("motion->Get_Num_Pivots()", source)
        self.assertNotIn("Peek_Motion(anim_idx)->Get_Num_Pivots()", source)

    def test_staging_patch_is_registered_for_zero_fuzz_rebuilds(self):
        patch = ROOT / "port/patches/ww3d2-a35-hanim-combo-null-motion-guard.patch"
        self.assertTrue(patch.exists())
        patch_source = patch.read_text(encoding="utf-8", errors="replace")
        self.assertIn("void HTreeClass::Combo_Update", patch_source)
        self.assertIn("+\tif (anim == NULL)", patch_source)
        script = (ROOT / "tools/stage_sources.sh").read_text(encoding="utf-8")
        self.assertIn(str(patch.name), script)


if __name__ == "__main__":
    unittest.main()
