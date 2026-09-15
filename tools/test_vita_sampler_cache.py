"""Execute the production Vita sampler functions against an object-state GL fake."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def build_contract(directory: Path, source: Path, sanitize: bool = False) -> Path:
    renderer = source.read_text()

    def section(start: str, end: str) -> str:
        offset = renderer.index(start)
        return renderer[offset:renderer.index(end, offset)]

    # Compile the actual __vita__ bodies, not a second implementation of the cache.
    parts = [
        section("struct NativeTextureStageCache {", "struct NativeRenderStateCache {"),
        "NativeTextureStageCache g_texture_stage_cache[2] = {};\n",
        section("unsigned g_render_work_cache_mode =", "VitaIndexedMeshBatch g_indexed_mesh_batch;"),
        section("struct NativeTextureObjectSampler {", "void Read_Render_Work_Cache_Mode()"),
        section("bool Set_Texture_Stage_Enabled(", "bool Render_State_Cache_Matches("),
        section("void Invalidate_Texture_State_Cache()", "bool Build_Indexed_Transform_Matrices("),
        section("bool Bind_Texture(uint32_t", "bool Apply_DX8_Texture_Stage_State("),
        section("void Release_Texture(uint32_t", "void Submit_Mesh("),
    ]
    (directory / "sampler-production.inc").write_text("\n".join(parts))
    executable = directory / "sampler-cache-test"
    command = ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
               "-D__vita__=1", "-include", "initializer_list", f"-I{directory}",
               str(ROOT / "tools/vita_sampler_cache_test.cpp"), "-o", str(executable)]
    if sanitize:
        command[2:3] = ["-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Production sampler harness compilation failed:\n" + result.stderr)
    return executable


class VitaSamplerCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="renegade-sampler-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.executable = build_contract(
            Path(cls.temporary.name),
            Path(os.environ.get("RENEGADE_SAMPLER_SOURCE", str(
                ROOT / "port/renderer/vita/ww3d_vita_renderer.cpp"))),
            sanitize=os.environ.get("RENEGADE_SAMPLER_SANITIZE") == "1")

    def run_case(self, name):
        for mode in ("0", "1"):
            with self.subTest(mode=mode):
                result = subprocess.run([str(self.executable), name, mode], check=True,
                                        capture_output=True, text=True)
                self.assertIn(f"sampler_cache={name} PASS", result.stdout)

    def test_shared_object(self): self.run_case("shared-object")
    def test_binding_restoration(self): self.run_case("binding-restoration")
    def test_redundant_bind(self): self.run_case("redundant-bind")
    def test_failed_write(self): self.run_case("failed-write")
    def test_failed_alias_write(self): self.run_case("failed-alias-write")
    def test_unrelated_object(self): self.run_case("unrelated-object")
    def test_delete_reuse(self): self.run_case("delete-reuse")
    def test_external_invalidation(self): self.run_case("external-invalidation")
    def test_invalid_stage(self): self.run_case("invalid-stage")
    def test_filter_translation(self): self.run_case("filter-translation")


if __name__ == "__main__":
    unittest.main()
