#include "renegade_freetype_font_provider.h"

#include "ffactory.h"
#include "wwfile.h"

#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_SYNTHESIS_H

#include <algorithm>
#include <cctype>
#include <cstring>
#include <vector>

namespace {

struct FontFace {
	char family[64];
	std::vector<unsigned char> data;
	FT_Face face = nullptr;
};

struct FontCandidateList {
	const char *files[8];
	size_t count;
};

FT_Library g_library = nullptr;
std::vector<FontFace> g_faces;
constexpr FT_Int32 kVitaFontGlyphLoadFlags =
	FT_LOAD_NO_HINTING | FT_LOAD_NO_AUTOHINT;

bool Equal_No_Case(const char *left, const char *right)
{
	if (left == nullptr || right == nullptr) return false;
	for (; *left != '\0' && *right != '\0'; ++left, ++right) {
		if (std::tolower(static_cast<unsigned char>(*left)) !=
			std::tolower(static_cast<unsigned char>(*right))) return false;
	}
	return *left == *right;
}

FontCandidateList Retail_Font_Files(const char *family)
{
	FontCandidateList result = {};
	if (Equal_No_Case(family, "Regatta Condensed LET") ||
		Equal_No_Case(family, "Regatta Condensed") ||
		Equal_No_Case(family, "Regatta") ||
		Equal_No_Case(family, "54251___")) {
		const char *files[] = {
			"54251___.TTF",
			"Data\\54251___.TTF",
			"DATA\\54251___.TTF",
			"Fonts\\54251___.TTF",
			"FONTS\\54251___.TTF"
		};
		result.count = sizeof(files) / sizeof(files[0]);
		for (size_t index = 0; index < result.count; ++index) {
			result.files[index] = files[index];
		}
		return result;
	}
	if (Equal_No_Case(family, "Arial MT") ||
		Equal_No_Case(family, "Arial") ||
		Equal_No_Case(family, "ArialMT") ||
		Equal_No_Case(family, "ARI_____")) {
		const char *files[] = {
			"ARI_____.TTF",
			"Data\\ARI_____.TTF",
			"DATA\\ARI_____.TTF",
			"Fonts\\ARI_____.TTF",
			"FONTS\\ARI_____.TTF",
			"ARIAL.TTF"
		};
		result.count = sizeof(files) / sizeof(files[0]);
		for (size_t index = 0; index < result.count; ++index) {
			result.files[index] = files[index];
		}
		return result;
	}
	return result;
}

bool Read_Retail_Font(const char *filename, std::vector<unsigned char> *data)
{
	if (filename == nullptr || data == nullptr || _TheFileFactory == nullptr) return false;
	FileClass *file = _TheFileFactory->Get_File(filename);
	if (file == nullptr) return false;
	bool read = false;
	if (file->Is_Available() && file->Open(FileClass::READ)) {
		const int size = file->Size();
		if (size > 0) {
			data->resize(static_cast<size_t>(size));
			read = file->Read(data->data(), size) == size;
		}
		file->Close();
	}
	_TheFileFactory->Return_File(file);
	if (!read) data->clear();
	return read;
}

FontFace *Find_Face(const char *family)
{
	const FontCandidateList candidates = Retail_Font_Files(family);
	if (candidates.count == 0U) return nullptr;
	for (FontFace &entry : g_faces) {
		if (Equal_No_Case(entry.family, family)) return &entry;
	}
	if (g_library == nullptr && FT_Init_FreeType(&g_library) != 0) return nullptr;
	FontFace entry;
	bool loaded = false;
	for (size_t index = 0; index < candidates.count; ++index) {
		entry.data.clear();
		if (Read_Retail_Font(candidates.files[index], &entry.data) &&
			FT_New_Memory_Face(g_library, entry.data.data(),
				static_cast<FT_Long>(entry.data.size()), 0, &entry.face) == 0) {
			loaded = true;
			break;
		}
		if (entry.face != nullptr) {
			FT_Done_Face(entry.face);
			entry.face = nullptr;
		}
	}
	if (!loaded) {
		return nullptr;
	}
	if (FT_Select_Charmap(entry.face, FT_ENCODING_UNICODE) != 0 &&
		entry.face->charmap == nullptr) {
		FT_Done_Face(entry.face);
		return nullptr;
	}
	std::strncpy(entry.family, family, sizeof(entry.family) - 1);
	entry.family[sizeof(entry.family) - 1] = '\0';
	g_faces.push_back(std::move(entry));
	return &g_faces.back();
}

bool Select_Size(FontFace *font, int point_size)
{
	if (font == nullptr || font->face == nullptr || point_size <= 0) return false;
	// Original GDI chose a 96-DPI logical font. Keep that point-to-pixel
	// contract independent of Vita's physical display density.
	return FT_Set_Char_Size(font->face, 0, point_size * 64, 96, 96) == 0;
}

int Rounded_26_6(FT_Pos value)
{
	return static_cast<int>((value + 32) >> 6);
}

bool Load_Glyph(FontFace *font, uint16_t character, bool bold)
{
	if (font == nullptr || font->face == nullptr ||
		FT_Load_Char(font->face, character, kVitaFontGlyphLoadFlags) != 0) return false;
	if (bold) FT_GlyphSlot_Embolden(font->face->glyph);
	return FT_Render_Glyph(font->face->glyph, FT_RENDER_MODE_NORMAL) == 0;
}

} // namespace

int RenegadeVita_Font_Height(const char *family, int point_size, bool)
{
	FontFace *font = Find_Face(family);
	if (!Select_Size(font, point_size)) return 0;
	const int height = Rounded_26_6(font->face->size->metrics.height);
	return std::max(height, 1);
}

bool RenegadeVita_Font_Measure_Glyph(const char *family, int point_size,
	bool bold, uint16_t character, int *width, int *height)
{
	if (width == nullptr || height == nullptr) return false;
	*width = 0;
	*height = 0;
	FontFace *font = Find_Face(family);
	if (!Select_Size(font, point_size) || !Load_Glyph(font, character, bold)) return false;
	*width = std::max(Rounded_26_6(font->face->glyph->advance.x),
		static_cast<int>(font->face->glyph->bitmap.width));
	*height = RenegadeVita_Font_Height(family, point_size, bold);
	return *height > 0;
}

bool RenegadeVita_Font_Rasterize_Glyph(const char *family, int point_size,
	bool bold, uint16_t character, uint16_t *pixels, int width, int height)
{
	if (pixels == nullptr || width < 0 || height <= 0) return false;
	FontFace *font = Find_Face(family);
	if (!Select_Size(font, point_size) || !Load_Glyph(font, character, bold)) return false;
	std::memset(pixels, 0, static_cast<size_t>(width) * static_cast<size_t>(height) * sizeof(*pixels));
	FT_GlyphSlot glyph = font->face->glyph;
	const FT_Bitmap &bitmap = glyph->bitmap;
	const int baseline = Rounded_26_6(font->face->size->metrics.ascender);
	const int top = std::max(0, baseline - glyph->bitmap_top);
	const int left = std::max(0, glyph->bitmap_left);
	for (unsigned int row = 0; row < bitmap.rows && top + static_cast<int>(row) < height; ++row) {
		const unsigned char *source = bitmap.buffer + static_cast<size_t>(row) * bitmap.pitch;
		for (unsigned int column = 0; column < bitmap.width && left + static_cast<int>(column) < width; ++column) {
			const uint16_t alpha = static_cast<uint16_t>(source[column] >> 4);
			pixels[(top + static_cast<int>(row)) * width + left + static_cast<int>(column)] =
				alpha == 0 ? 0 : static_cast<uint16_t>(0x0FFF | (alpha << 12));
		}
	}
	return true;
}

void RenegadeVita_Font_Shutdown(void)
{
	for (FontFace &entry : g_faces) {
		if (entry.face != nullptr) FT_Done_Face(entry.face);
	}
	g_faces.clear();
	if (g_library != nullptr) FT_Done_FreeType(g_library);
	g_library = nullptr;
}
