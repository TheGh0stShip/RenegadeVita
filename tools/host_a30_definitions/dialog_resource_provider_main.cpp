#include "renegade_dialog_resource_provider.h"
#include "win32_compat.h"
#include <stdio.h>

namespace {
uint16_t U16(const unsigned char *p) { return uint16_t(p[0]) | (uint16_t(p[1]) << 8U); }
uint32_t U32(const unsigned char *p) { return uint32_t(p[0]) | (uint32_t(p[1]) << 8U) | (uint32_t(p[2]) << 16U) | (uint32_t(p[3]) << 24U); }
bool Need(bool value, const char *what) { if (!value) fprintf(stderr, "A4_DIALOG_RESOURCE_CONTRACT_FAIL %s\n", what); return value; }
bool Field(const unsigned char *data, size_t size, size_t *at) {
 *at=(*at+1U)&~size_t(1);
 if (*at+2U>size) return false;
 const uint16_t v=U16(data+*at); *at+=2U;
 if (v==0) return true;
 if (v==0xffffU) { *at+=2U; return *at<=size; }
 while (*at+2U<=size && U16(data+*at)!=0) { *at+=2U; }
 if (*at+2U>size) return false;
 *at+=2U;
 return true;
}
bool Template(const unsigned char *data, size_t size) {
 if (size<sizeof(DLGTEMPLATE) || (U32(data)&DS_SETFONT)==0U) return false;
 size_t at=sizeof(DLGTEMPLATE); if (!Field(data,size,&at)||!Field(data,size,&at)||!Field(data,size,&at)) return false;
 if (at+2U>size) return false;
 at+=2U;
 if (!Field(data,size,&at)) return false;
 const uint16_t controls=U16(data+8); for (uint16_t i=0;i<controls;++i) { at=(at+3U)&~size_t(3); if (at+sizeof(DLGITEMTEMPLATE)>size) return false; at+=sizeof(DLGITEMTEMPLATE); if (!Field(data,size,&at)||!Field(data,size,&at)||at+2U>size) return false; const uint16_t extra=U16(data+at); at+=2U+extra; if (at>size) return false; }
 return true;
}
bool MainMenuTransitionIDs(const unsigned char *data, size_t size) {
 const uint16_t expected[] = {11000U, 11029U, 11030U, 1563U, 11003U, 11018U};
 if (size < sizeof(DLGTEMPLATE) || U16(data + 8) < sizeof(expected) / sizeof(expected[0])) return false;
 size_t at = sizeof(DLGTEMPLATE);
 if (!Field(data,size,&at) || !Field(data,size,&at) || !Field(data,size,&at) || at + 2U > size) return false;
 at += 2U;
 if (!Field(data,size,&at)) return false;
 for (size_t i = 0; i < sizeof(expected) / sizeof(expected[0]); ++i) {
  at = (at + 3U) & ~size_t(3);
  if (at + sizeof(DLGITEMTEMPLATE) > size) return false;
  const DLGITEMTEMPLATE *item = reinterpret_cast<const DLGITEMTEMPLATE *>(data + at);
  if (item->id != expected[i]) return false;
  at += sizeof(DLGITEMTEMPLATE);
  if (!Field(data,size,&at) || !Field(data,size,&at) || at + 2U > size) return false;
  const uint16_t extra = U16(data + at);
  at += 2U + extra;
  if (at > size) return false;
 }
 return true;
}
bool SourceFont(const unsigned char *data, size_t size) {
 if (size<sizeof(DLGTEMPLATE)) return false;
 size_t at=sizeof(DLGTEMPLATE);
 if (!Field(data,size,&at)||!Field(data,size,&at)||!Field(data,size,&at)||at+6U>size) return false;
 return U16(data+at)==8U && U16(data+at+2U)=='M' && U16(data+at+4U)=='S';
}
}

int main()
{
	size_t bytes = 0;
	const unsigned char *main_menu = RenegadeDialogResources::Find_Dialog(128, &bytes);
	if (!Need(main_menu != NULL, "main menu source record") ||
		!Need(bytes >= sizeof(DLGTEMPLATE), "main menu complete") ||
		!Need(Template(main_menu, bytes), "main menu DialogParser template walk") ||
		!Need(MainMenuTransitionIDs(main_menu, bytes), "main menu original transition IDs") ||
		!Need(SourceFont(main_menu, bytes), "main menu original FONT 8 MS Sans Serif") ||
		!Need(U16(main_menu + 14) == 400 && U16(main_menu + 16) == 300, "main menu 400x300") ||
		!Need(U16(main_menu + 8) > 0 && U16(main_menu + 8) < 64, "main menu original control count")) return 1;
	const uint16_t frontend_ids[] = {128, 130, 131, 255, 256};
	for (const uint16_t id : frontend_ids) {
		size_t template_bytes = 0;
		const unsigned char *dialog = RenegadeDialogResources::Find_Dialog(id, &template_bytes);
		if (!Need(dialog != NULL, "canonical frontend dialog record")) return 1;
		if (!Template(dialog, template_bytes)) {
			fprintf(stderr, "A4_DIALOG_RESOURCE_CONTRACT_FAIL id=%u DialogParser walk\n", unsigned(id));
			return 1;
		}
		if (!Need(U16(dialog + 14) == 400 && U16(dialog + 16) == 300,
			"canonical frontend dialog 400x300")) return 1;
	}
	for (uint16_t id = 146; id <= 153; ++id) {
		size_t template_bytes = 0;
		const unsigned char *dialog = RenegadeDialogResources::Find_Dialog(id, &template_bytes);
		if (!Need(dialog != NULL, "original EVA shell/child resource") ||
			!Need(Template(dialog, template_bytes), "original EVA template walk") ||
			!Need(SourceFont(dialog, template_bytes), "original EVA font") ||
			!Need(U16(dialog + 8) > 0, "original EVA controls present") ||
			!Need(U16(dialog + 14) == (id == 153 ? 400 : 265) &&
				U16(dialog + 16) == (id == 153 ? 300 : 205), "original EVA dimensions")) return 1;
		if (id == 153 && !Need(U16(dialog + 8) == 10, "original EVA shell control count")) return 1;
	}
	const unsigned char *splash = RenegadeDialogResources::Find_Dialog(255, &bytes);
	HRSRC handle = FindResource(NULL, MAKEINTRESOURCE(128), RT_DIALOG);
	if (!Need(splash != NULL, "splash source record") ||
		!Need(handle == main_menu && LoadResource(NULL, handle) == handle && LockResource(handle) == main_menu, "resource ABI") ||
		!Need(FindResource(NULL, MAKEINTRESOURCE(999), RT_DIALOG) == NULL, "no synthetic dialog")) return 1;
	fprintf(stdout, "A4_DIALOG_RESOURCE_CONTRACT PASS main=128 controls=%u splash=255\n", unsigned(U16(main_menu + 8)));
	return 0;
}
