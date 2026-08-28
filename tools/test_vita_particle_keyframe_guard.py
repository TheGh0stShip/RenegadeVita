import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaParticleKeyframeGuardTests(unittest.TestCase):
    def test_size_reset_uses_bounded_keyframe_count_before_deref(self):
        source = (ROOT / "staging/ww3d2/part_buf.cpp").read_text(encoding="utf-8", errors="replace")
        self.assertIn("MAX_PARTICLE_SIZE_KEYFRAMES = 4096U", source)
        self.assertIn("Usable_Size_Keyframe_Count", source)
        self.assertIn("Is_Usable_Particle_Size_Keyframe_Pointer(props.KeyTimes)", source)
        self.assertIn("Is_Usable_Particle_Size_Keyframe_Pointer(props.Values)", source)
        self.assertIn("const unsigned int usable_size_keyframes = Usable_Size_Keyframe_Count(new_props);", source)
        self.assertIn("for (skey = 0; skey < usable_size_keyframes; skey++)", source)
        self.assertIn("bool size_constant_at_end = (skey == usable_size_keyframes);", source)

    def test_emitter_property_copy_refuses_null_keyframe_arrays(self):
        header = (ROOT / "staging/ww3d2/part_emt.h").read_text(encoding="utf-8", errors="replace")
        self.assertIn("if (src.KeyTimes == NULL || src.Values == NULL)", header)
        self.assertIn("dest.NumKeyFrames = 0;", header)
        self.assertLess(
            header.index("if (src.KeyTimes == NULL || src.Values == NULL)"),
            header.index("::memcpy (dest.KeyTimes, src.KeyTimes"),
        )

    def test_staging_patch_is_registered_for_zero_fuzz_rebuilds(self):
        patch = ROOT / "port/patches/ww3d2-a35-particle-size-keyframe-guard.patch"
        self.assertTrue(patch.exists())
        script = (ROOT / "tools/stage_sources.sh").read_text(encoding="utf-8")
        self.assertIn(str(patch.name), script)


if __name__ == "__main__":
    unittest.main()
