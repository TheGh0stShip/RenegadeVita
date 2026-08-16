#pragma once

#include <stdint.h>

// Native replacement for the Win32 GDI rasterization hidden beneath the
// original FontCharsClass.  The caller retains FontCharsClass' original glyph
// cache, layout and alpha-4444 storage; this boundary only obtains glyph
// coverage from user-supplied retail font resources through FileFactory.
bool RenegadeVita_Font_Measure_Glyph(const char *family, int point_size,
	bool bold, uint16_t character, int *width, int *height);
bool RenegadeVita_Font_Rasterize_Glyph(const char *family, int point_size,
	bool bold, uint16_t character, uint16_t *pixels, int width, int height);
int RenegadeVita_Font_Height(const char *family, int point_size, bool bold);
void RenegadeVita_Font_Shutdown(void);
