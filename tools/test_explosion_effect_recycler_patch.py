import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "tools/stage_sources.sh"
RUNTIME = ROOT / "port/platform/vita/a31_vita_runtime.cpp"


class ExplosionEffectRecyclerPatchTests(unittest.TestCase):
    def test_campaign_effects_keep_original_spawn_and_fresh_emitter_paths(self):
        stage = STAGE.read_text()
        runtime = RUNTIME.read_text()
        self.assertNotIn("combat-a35-prepared-effect-cache.patch", stage)
        self.assertNotIn("combat-a35-explosion-effect-recycler.patch", stage)
        self.assertNotIn("Prepare_Explosion_Render_Objects", runtime)
        self.assertIn("original_spawn_path=1", runtime)


if __name__ == "__main__":
    unittest.main()
