#ifndef RENEGADE_EXPERIMENT_HUD_FONT_ATLAS_PROBE_H
#define RENEGADE_EXPERIMENT_HUD_FONT_ATLAS_PROBE_H

#include "font3d.h"
#include "formconv.h"
#include "surfaceclass.h"
#include "texture.h"
#include "targa.h"
#include <stdio.h>

// Call only after original FileFactory/WW3D initialization. This compares CPU
// atlas bytes, not GPU sampling, framebuffer output or physical rendering.
inline bool Probe_Original_HUD_Digit_Atlas(Font3DInstanceClass *font,
    const char *filename)
{
    if (font == NULL || font->Peek_Texture() == NULL) return false;
    Targa diagnostic_tga;
    const int tga_open = diagnostic_tga.Open(filename, TGA_READMODE);
    int tga_load = -1;
    if (tga_open == 0) {
        diagnostic_tga.Header.ImageDescriptor ^= TGAIDF_YORIGIN;
        tga_load = diagnostic_tga.Load(filename, TGAF_IMAGE, false);
    }
    printf("HUD_DIGIT_TGA font=%s open=%d load=%d width=%u height=%u depth=%u image=%d\n",
        filename, tga_open, tga_load, static_cast<unsigned>(diagnostic_tga.Header.Width),
        static_cast<unsigned>(diagnostic_tga.Header.Height),
        static_cast<unsigned>(diagnostic_tga.Header.PixelDepth),
        diagnostic_tga.GetImage() != NULL ? 1 : 0);
    SurfaceClass *source = NEW_REF(SurfaceClass, (filename));
    SurfaceClass *atlas = font->Peek_Texture()->Get_Surface_Level(0);
    if (source == NULL || atlas == NULL) {
        REF_PTR_RELEASE(source);
        REF_PTR_RELEASE(atlas);
        return false;
    }
    SurfaceClass::SurfaceDescription source_desc = {};
    SurfaceClass::SurfaceDescription atlas_desc = {};
    source->Get_Description(source_desc);
    atlas->Get_Description(atlas_desc);
    bool passed = source_desc.Format == WW3D_FORMAT_A8R8G8B8 &&
        atlas_desc.Format == WW3D_FORMAT_A4R4G4B4 &&
        source_desc.Width > 0 && source_desc.Height > 0 &&
        source_desc.Width % 16 == 0 && source_desc.Height % 16 == 0 &&
        atlas_desc.Width > 0 && atlas_desc.Height > 0;
    int source_pitch = 0;
    int atlas_pitch = 0;
    const unsigned char *source_pixels = passed ?
        static_cast<const unsigned char *>(source->Lock(&source_pitch)) : NULL;
    const unsigned char *atlas_pixels = passed ?
        static_cast<const unsigned char *>(atlas->Lock(&atlas_pitch)) : NULL;
    passed = passed && source_pixels != NULL && atlas_pixels != NULL &&
        source_pitch >= static_cast<int>(source_desc.Width * 4) &&
        atlas_pitch >= static_cast<int>(atlas_desc.Width * 2);
    printf("HUD_DIGIT_ATLAS_SURFACES font=%s source=%ux%u/%d pitch=%d pixels=%d atlas=%ux%u/%d pitch=%d pixels=%d ready=%d\n",
        filename, source_desc.Width, source_desc.Height, static_cast<int>(source_desc.Format),
        source_pitch, source_pixels != NULL ? 1 : 0, atlas_desc.Width, atlas_desc.Height,
        static_cast<int>(atlas_desc.Format), atlas_pitch, atlas_pixels != NULL ? 1 : 0,
        passed ? 1 : 0);
    unsigned compared_pixels = 0;
    unsigned mismatch_pixels = 0;
    unsigned compared_digits = 0;
    const unsigned cell_width = source_desc.Width / 16;
    const unsigned cell_height = source_desc.Height / 16;
    for (unsigned digit = '0'; passed && digit <= '9'; ++digit) {
        const unsigned cell_x = (digit % 16) * cell_width;
        const unsigned cell_y = (digit / 16) * cell_height;
        unsigned left = cell_width;
        unsigned right = 0;
        bool visible = false;
        for (unsigned y = 0; y < cell_height; ++y) {
            for (unsigned x = 0; x < cell_width; ++x) {
                const unsigned char *pixel = source_pixels +
                    (cell_y + y) * source_pitch + (cell_x + x) * 4;
                if (pixel[3] != 0) {
                    if (x < left) left = x;
                    if (x > right) right = x;
                    visible = true;
                }
            }
        }
        if (!visible) { passed = false; break; }
        const unsigned width = right - left + 1;
        const RectClass uv = font->Char_UV(static_cast<WCHAR>(digit));
        printf("HUD_DIGIT_ATLAS_GLYPH code=%u source_width=%u source_height=%u font_width=%.3f font_height=%.3f uv=%.5f,%.5f,%.5f,%.5f\n",
            digit, width, cell_height, font->Char_Width(static_cast<WCHAR>(digit)),
            font->Char_Height(), uv.Left, uv.Top, uv.Right, uv.Bottom);
        passed = uv.Left >= 0 && uv.Top >= 0 && uv.Right <= 1 &&
            uv.Bottom <= 1 && uv.Right > uv.Left && uv.Bottom > uv.Top &&
            font->Char_Width(static_cast<WCHAR>(digit)) == width &&
            font->Char_Height() == cell_height;
        if (!passed) break;
        const unsigned atlas_x = static_cast<unsigned>(uv.Left * atlas_desc.Width + 0.5f);
        const unsigned atlas_y = static_cast<unsigned>(uv.Top * atlas_desc.Height + 0.5f);
        if (atlas_x + width > atlas_desc.Width ||
            atlas_y + cell_height > atlas_desc.Height) { passed = false; break; }
        for (unsigned y = 0; y < cell_height; ++y) {
            for (unsigned x = 0; x < width; ++x) {
                const unsigned char *src = source_pixels +
                    (cell_y + y) * source_pitch + (cell_x + left + x) * 4;
                const unsigned char *dst = atlas_pixels +
                    (atlas_y + y) * atlas_pitch + (atlas_x + x) * 2;
                const unsigned low = (src[0] >> 4) | (src[1] & 0xf0);
                const unsigned high = (src[2] >> 4) | (src[3] & 0xf0);
                ++compared_pixels;
                if (dst[0] != low || dst[1] != high) ++mismatch_pixels;
            }
        }
        ++compared_digits;
    }
    if (source_pixels != NULL) source->Unlock();
    if (atlas_pixels != NULL) atlas->Unlock();
    REF_PTR_RELEASE(atlas);
    REF_PTR_RELEASE(source);
    passed = passed && compared_digits == 10 && mismatch_pixels == 0;
    printf("HUD_DIGIT_ATLAS font=%s digits=%u pixels=%u mismatches=%u result=%s cpu_only=1\n",
        filename, compared_digits, compared_pixels, mismatch_pixels,
        passed ? "PASS" : "FAIL");
    return passed;
}

#endif
