#include "texture_upload_contract.h"

#include <stdio.h>

namespace {
void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) { ++failures; fprintf(stderr, "Texture upload contract failed: %s\n", name); }
}
}

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	unsigned char rgba[4] = {};
	RenegadeVitaTextureUpload::Store_RGBA_From_ARGB(0x80402010U, rgba);
	Check(rgba[0] == 0x40U && rgba[1] == 0x20U && rgba[2] == 0x10U && rgba[3] == 0x80U,
		"ARGB decoder output is uploaded as RGBA with alpha intact", checks, failures);
	unsigned char checkerboard[16] = {};
	RenegadeVitaTextureUpload::Build_Checkerboard_RGBA(checkerboard);
	Check(checkerboard[0] == 0xffU && checkerboard[1] == 0U &&
		checkerboard[2] == 0xffU && checkerboard[3] == 0xffU,
		"diagnostic checkerboard starts opaque magenta", checks, failures);
	Check(checkerboard[4] == 0U && checkerboard[5] == 0U &&
		checkerboard[6] == 0U && checkerboard[7] == 0xffU &&
		checkerboard[12] == 0xffU && checkerboard[14] == 0xffU,
		"diagnostic checkerboard alternates opaque black and magenta", checks, failures);
	unsigned char multicolor[16] = {};
	RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At(0xffff0000U,
		0U, 0U, 2U, multicolor); // source top-left red -> destination top-left
	RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At(0xff00ff00U,
		1U, 0U, 2U, multicolor); // source top-right green -> destination top-right
	RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At(0xff0000ffU,
		0U, 1U, 2U, multicolor); // source bottom-left blue -> destination bottom-left
	RenegadeVitaTextureUpload::Store_RGBA_From_ARGB_At(0xffffffffU,
		1U, 1U, 2U, multicolor); // source bottom-right white -> destination bottom-right
	Check(multicolor[0] == 0xffU && multicolor[1] == 0U &&
		multicolor[4] == 0U && multicolor[5] == 0xffU &&
		multicolor[8] == 0U && multicolor[10] == 0xffU &&
		multicolor[12] == 0xffU && multicolor[13] == 0xffU,
		"multicolor DDS rows preserve retail top-down orientation",
		checks, failures);
	printf("A3.2 texture upload contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
