import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaTextureSurfaceContractTests(unittest.TestCase):
    def test_dx8_texture_handles_expose_lockable_surface_levels(self):
        header = (ROOT / "port/renderer/vita/d3d8.h").read_text(
            encoding="utf-8"
        )
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )

        for needle in (
            "IDirect3DSurface8 **SurfaceLevels;",
            "DWORD *SurfaceLockFlags;",
            "DWORD Priority;",
            "UINT LockedSurfaceCount;",
            "bool *SurfaceLocked;",
            "bool TextureLocked;",
            "HRESULT LockRect(UINT level, D3DLOCKED_RECT *locked, const RECT *rectangle,",
            "HRESULT UnlockRect(UINT level);",
        ):
            self.assertIn(needle, header)

        self.assertIn("IDirect3DTexture8 *DX8Wrapper::_Create_DX8_Texture(unsigned int width,", boundary)
        self.assertIn("Calculate_Texture_Mip_Count(width, height,", boundary)
        self.assertIn("Allocate_Texture_Surface_Levels(texture)", boundary)
        self.assertIn("Upload_Texture_Level_From_Surface(texture, level)", boundary)
        self.assertIn("Destroy_Texture_Surface_Levels(static_cast<IDirect3DTexture8 *>(this));", boundary)

    def test_get_surface_level_returns_valid_refcounted_surface_not_invalid_call(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        method = boundary[
            boundary.index("HRESULT IDirect3DTexture8::GetSurfaceLevel"):
            boundary.index("HRESULT IDirect3DTexture8::LockRect")
        ]

        self.assertIn("SurfaceLevels[level]->AddRef();", method)
        self.assertIn("*surface = SurfaceLevels[level];", method)
        self.assertIn("new (std::nothrow) IDirect3DSurface8(", method)
        self.assertIn("*surface = descriptor_surface;", method)
        self.assertNotEqual(
            method.count("return static_cast<HRESULT>(D3DERR_INVALIDCALL);"),
            1,
            "GetSurfaceLevel must not collapse back to a single invalid-call stub",
        )

    def test_texture_lock_unlock_uploads_writable_surface_storage(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        lock_method = boundary[
            boundary.index("HRESULT IDirect3DTexture8::LockRect"):
            boundary.index("HRESULT IDirect3DTexture8::UnlockRect")
        ]
        unlock_method = boundary[
            boundary.index("HRESULT IDirect3DTexture8::UnlockRect"):
            boundary.index("DWORD IDirect3DTexture8::GetPriority")
        ]

        self.assertIn("SurfaceLevels[level]->LockRect(locked, rectangle, flags)", lock_method)
        self.assertIn("SurfaceLocked[level] = true;", lock_method)
        self.assertIn("SurfaceLockFlags[level] = flags;", lock_method)
        self.assertIn("++LockedSurfaceCount;", lock_method)
        self.assertIn("TextureLocked = true;", lock_method)
        self.assertNotIn("|| TextureLocked ||", lock_method)
        self.assertIn("!SurfaceLocked[level]", unlock_method)
        self.assertIn("const DWORD flags = SurfaceLockFlags[level];", unlock_method)
        self.assertIn("SurfaceLocked[level] = false;", unlock_method)
        self.assertIn("SurfaceLockFlags[level] = 0U;", unlock_method)
        self.assertIn("TextureLocked = LockedSurfaceCount != 0U;", unlock_method)
        self.assertIn("(flags & D3DLOCK_READONLY) != 0U", unlock_method)
        self.assertIn("Upload_Texture_Level_From_Surface(this, level)", unlock_method)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Upload_Failure();", unlock_method)

    def test_lock_state_supports_original_multi_level_texture_loader_pattern(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        texture_loader = (ROOT / "staging/ww3d2/textureloader.cpp").read_text(
            encoding="utf-8"
        )
        lock_method = boundary[
            boundary.index("HRESULT IDirect3DTexture8::LockRect"):
            boundary.index("HRESULT IDirect3DTexture8::UnlockRect")
        ]

        self.assertIn("for (level=0;level<sysmem_texture->GetLevelCount();++level)", texture_loader)
        self.assertIn("sysmem_texture->LockRect(", texture_loader)
        self.assertIn("SurfaceLocked[level]", lock_method)
        self.assertNotIn("TextureLocked ||", lock_method)

    def test_surface_wrapper_matches_original_attach_reference_ownership(self):
        surface_boundary = (ROOT / "port/renderer/vita/surface_boundary.cpp").read_text(
            encoding="utf-8"
        )
        constructor = surface_boundary[
            surface_boundary.index("SurfaceClass::SurfaceClass(IDirect3DSurface8 *surface)"):
            surface_boundary.index("SurfaceClass::~SurfaceClass")
        ]

        self.assertIn("D3DSurface->AddRef();", constructor)
        self.assertIn("Get_Description(description);", constructor)
        self.assertIn("SurfaceFormat = description.Format;", constructor)


if __name__ == "__main__":
    unittest.main()
