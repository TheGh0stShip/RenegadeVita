import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMBAT = ROOT / "upstream/CnC_Renegade/Code/Combat"
PATCH = ROOT / "port/patches/combat-a35-explosion-effect-recycler.patch"
FILES = ("explosion.h", "explosion.cpp", "effectrecycler.h",
         "effectrecycler.cpp", "combat.cpp")


class ExplosionEffectRecyclerPatchTests(unittest.TestCase):
    def test_zero_fuzz_patch_reconstructs_campaign_effect_recycler(self):
        with tempfile.TemporaryDirectory(prefix="renegade-effect-recycler-") as temp:
            stage = Path(temp)
            for name in FILES:
                shutil.copy2(COMBAT / name, stage / name)
            subprocess.run(
                ["patch", "--batch", "--forward", "--fuzz=0", "-p1",
                 "-i", str(PATCH)], cwd=stage, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            explosion = (stage / "explosion.cpp").read_text()
            recycler = (stage / "effectrecycler.cpp").read_text()
            header = (stage / "explosion.h").read_text()
            combat = (stage / "combat.cpp").read_text()
            self.assertIn("ExplosionManager::Prepare_Explosion_Render_Objects", explosion)
            self.assertIn("_ExplosionEffectRecycler.Spawn_Effect", explosion)
            self.assertIn("_ExplosionEffectRecycler.Reset()", explosion)
            self.assertIn("EffectRecyclerClass::Preload_Effect", recycler)
            self.assertIn("Prepare_Explosion_Render_Objects", header)
            self.assertIn("ExplosionManager::Shutdown();", combat)


if __name__ == "__main__":
    unittest.main()
