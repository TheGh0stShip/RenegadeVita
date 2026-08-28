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
            "void Set_Texture_Owner(IDirect3DTexture8 *texture, UINT level);",
            "HRESULT Upload_Texture_Owner();",
            "IDirect3DTexture8 *OwnerTexture;",
            "UINT OwnerTextureLevel;",
            "DWORD LockFlags;",
            "bool Locked;",
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
        self.assertIn("SurfaceLevels[level]->UnlockRect()", unlock_method)
        self.assertNotIn("Upload_Texture_Level_From_Surface(this, level)", unlock_method)

        surface_unlock = boundary[
            boundary.index("HRESULT IDirect3DSurface8::UnlockRect"):
            boundary.index("void IDirect3DSurface8::Set_Texture_Owner")
        ]
        owner_upload = boundary[
            boundary.index("HRESULT IDirect3DSurface8::Upload_Texture_Owner"):
            boundary.index("HRESULT IDirect3DDevice8::CopyRects")
        ]
        self.assertIn("return Upload_Texture_Owner();", surface_unlock)
        self.assertIn("Upload_Texture_Level_From_Surface(OwnerTexture, OwnerTextureLevel)", owner_upload)
        self.assertIn("RenegadeVitaRenderer::Record_Texture_Upload_Failure();", owner_upload)

    def test_copy_rects_keeps_original_render2d_surface_copy_live(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        render_sentence = (ROOT / "staging/ww3d2/render2dsentence.cpp").read_text(
            encoding="utf-8"
        )
        method = boundary[
            boundary.index("HRESULT IDirect3DDevice8::CopyRects"):
            boundary.index("HRESULT D3DXLoadSurfaceFromSurface")
        ]

        self.assertIn("DX8Wrapper::_Copy_DX8_Rects", render_sentence)
        self.assertIn("curr_surface->Peek_D3D_Surface", render_sentence)
        self.assertIn("texture_surface->Peek_D3D_Surface", render_sentence)
        self.assertGreater(
            len(method.splitlines()),
            40,
            "CopyRects must not collapse back to a one-line invalid-call stub",
        )
        self.assertIn("source_description.Format != destination_description.Format", method)
        self.assertIn("Validate_Surface_Copy_Rect", method)
        self.assertIn("Validate_Surface_Destination_Rect", method)
        self.assertIn("Copy_Surface_Rect_Bytes", method)
        self.assertIn("destination->Upload_Texture_Owner()", method)
        self.assertIn("memmove(", boundary)

    def test_texture_surface_owner_is_attached_and_detached_at_lifetime_edges(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )

        self.assertIn("surface->Set_Texture_Owner(texture, level);", boundary)
        self.assertIn("copy->Set_Texture_Owner(texture, level);", boundary)
        self.assertIn("texture->SurfaceLevels[level]->Set_Texture_Owner(NULL, 0U);", boundary)
        self.assertIn("OwnerTexture->SurfaceLevels[OwnerTextureLevel] != this", boundary)

    def test_d3dx_surface_copy_and_filter_boundary_is_available(self):
        header = (ROOT / "port/renderer/vita/D3dx8core.h").read_text(
            encoding="utf-8"
        )
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        load_method = boundary[
            boundary.index("HRESULT D3DXLoadSurfaceFromSurface"):
            boundary.index("HRESULT D3DXFilterTexture")
        ]
        filter_method = boundary[
            boundary.index("HRESULT D3DXFilterTexture"):
            boundary.index("HRESULT IDirect3DDevice8::SetTransform")
        ]

        for needle in (
            "D3DX_FILTER_NONE",
            "D3DX_FILTER_POINT",
            "D3DX_FILTER_LINEAR",
            "D3DX_FILTER_TRIANGLE",
            "D3DX_FILTER_BOX",
            "HRESULT D3DXLoadSurfaceFromSurface(IDirect3DSurface8 *destination,",
            "HRESULT D3DXFilterTexture(IDirect3DTexture8 *texture,",
        ):
            self.assertIn(needle, header)
        self.assertIn("destination_palette != NULL", load_method)
        self.assertIn("source_palette != NULL", load_method)
        self.assertIn("color_key != 0U", load_method)
        self.assertIn("Load_Surface_Rect_Filtered", load_method)
        self.assertIn("destination->Upload_Texture_Owner()", load_method)
        self.assertIn("D3DXLoadSurfaceFromSurface(", filter_method)
        self.assertIn("texture->SurfaceLevels[level - 1U]", filter_method)

    def test_dds_loaded_textures_retain_decoded_surface_levels(self):
        boundary = (ROOT / "port/renderer/vita/ww3d_dx8_boundary.cpp").read_text(
            encoding="utf-8"
        )
        method = boundary[
            boundary.index("IDirect3DTexture8 *Load_DDS_Texture"):
            boundary.index("IDirect3DTexture8 *Load_Targa_Texture")
        ]

        self.assertIn("texture->SourceFormat = WW3DFormat_To_D3DFormat(dds.Get_Format());", method)
        self.assertIn("Allocate_Texture_Surface_Levels(texture)", method)
        self.assertIn("new (std::nothrow) IDirect3DSurface8(", method)
        self.assertIn("width, height, D3DFMT_A8R8G8B8,", method)
        self.assertIn("RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At", method)
        self.assertNotIn("Store_RGBA_From_ARGB_Flipped(argb,", method)
        self.assertIn("Write_RGBA_To_Surface_Pixel(D3DFMT_A8R8G8B8,", method)
        self.assertIn("surface->Set_Texture_Owner(texture, level);", method)
        self.assertIn("texture->SurfaceLevels[level] = surface;", method)
        self.assertIn("Destroy_Texture_Surface_Levels(texture);", method)

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
