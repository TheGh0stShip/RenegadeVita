"""Guard the original precomputed-visibility (PVS) and culling ownership.

The Vita runtime must keep PhysicsSceneClass's original vis/frustum culling:
vis enabled by default, no port code or staging patch toggling it, the PVS
passed to both culling systems, and the sampled vis census staying a
read-only observer placed before any camera mutation of the frame.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "upstream/CnC_Renegade/Code/wwphys"

VIS_TOGGLES = (
    "Enable_Vis(", "Invert_Vis(", "Reset_Vis(", "Set_Vis_Quick_And_Dirty(",
    "Enable_Vis_Sector_Fallback(", "Lock_Vis_Sample_Point(",
    "Enable_Hierarchical_Vis_Culling(",
)
PRISTINE_VIS_FILES = (
    "pscene_vis.cpp", "staticaabtreecull.cpp", "staticaabtreecull.h",
    "dynamicaabtreecull.cpp", "physaabtreecull.cpp", "physaabtreecull.h",
    "physgridcull.cpp", "vistable.cpp", "vistable.h", "vistablemgr.cpp",
    "vistablemgr.h",
)


def read(rel):
    return (ROOT / rel).read_text(errors="replace")


class VisCullingContractTests(unittest.TestCase):
    def test_original_vis_defaults(self):
        pscene = read("staging/wwphys/pscene.cpp")
        for token in ("VisEnabled(true)", "VisInverted(false)",
                      "VisResetNeeded(false)", "VisSectorFallbackEnabled(true)"):
            self.assertIn(token, pscene)
        self.assertIn("_HierarchicalVisCullingEnabled = true",
                      read("staging/wwphys/physaabtreecull.cpp"))
        self.assertIn("#define UMBRASUPPORT\t\t0",
                      read("staging/wwphys/umbrasupport.h"))

    def test_pre_render_passes_pvs_to_both_culling_systems(self):
        pscene = read("staging/wwphys/pscene.cpp")
        body = pscene.split("void PhysicsSceneClass::Pre_Render_Processing", 1)[1]
        body = body.split("void PhysicsSceneClass::Post_Render_Processing", 1)[0]
        self.assertIn("VisTableClass * pvs = Get_Vis_Table_For_Rendering(camera);", body)
        self.assertIn("StaticCullingSystem->Collect_Visible_Objects(camera.Get_Frustum(),pvs,", body)
        self.assertIn("DynamicCullingSystem->Collect_Visible_Objects(camera.Get_Frustum(),pvs,", body)
        self.assertIn("Optimize_LODs(camera,", body)

    def test_no_port_code_or_patch_toggles_vis(self):
        offenders = []
        for patch in sorted((ROOT / "port/patches").glob("*.patch")):
            for line in patch.read_text(errors="replace").splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    if any(t in line for t in VIS_TOGGLES):
                        offenders.append(f"{patch.name}: {line.strip()}")
        for src in sorted((ROOT / "port").rglob("*")):
            if src.suffix not in (".cpp", ".h", ".c", ".inl"):
                continue
            text = src.read_text(errors="replace")
            for t in VIS_TOGGLES:
                if re.search(r"(->|\.)" + re.escape(t), text):
                    offenders.append(f"{src.relative_to(ROOT)}: {t}")
        self.assertEqual(offenders, [])

    def test_vis_census_is_read_only_and_precedes_camera_mutation(self):
        source = read("port/platform/a31_gameplay_boundary.cpp")
        census = source.split("static void Sample_Original_Visibility_Census", 1)[1]
        census = census.split("A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame", 1)[0]
        self.assertIn("Get_Vis_Table_For_Rendering(camera)", census)
        self.assertIn("REF_PTR_RELEASE(pvs);", census)
        self.assertIn("census_logs >= 1024U", census)
        for forbidden in ("Get_Vis_Table_Count", "Get_Vis_Table_Size",
                          "Internal_Vis_Reset", "Update_Vis") + VIS_TOGGLES:
            self.assertNotIn(forbidden, census)
        frame = source.split("A31InteractiveRenderTrace A31_Interactive_Run_Render_Frame", 1)[1]
        pre = frame.index("scene->Pre_Render_Processing(*camera);")
        sample = frame.index("Sample_Original_Visibility_Census(*scene, *camera);")
        begin = frame.index("WW3D::Begin_Render(")
        combat = frame.index("CombatManager::Render();")
        self.assertLess(pre, sample)
        # Camera shakes are applied inside CombatManager::Render; the census
        # must see the exact camera Pre_Render_Processing used.
        self.assertLess(sample, begin)
        self.assertLess(sample, combat)
        between = frame[pre:sample]
        self.assertNotIn("camera->", between.replace("*camera", ""))

    @unittest.skipUnless((UPSTREAM / "pscene_vis.cpp").exists(),
                         "upstream source not present")
    def test_vis_sources_match_upstream(self):
        for name in PRISTINE_VIS_FILES:
            up = (UPSTREAM / name).read_bytes().replace(b"\r", b"")
            st = (ROOT / "staging/wwphys" / name).read_bytes().replace(b"\r", b"")
            self.assertEqual(up, st, name)


if __name__ == "__main__":
    unittest.main()
