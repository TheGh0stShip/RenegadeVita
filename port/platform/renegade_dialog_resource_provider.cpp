#include "renegade_dialog_resource_provider.h"
#include "win32_compat.h"

#include <string.h>

#include <renegade_dialog_templates.inc>

HINSTANCE ProgramInstance = NULL;
// Vita has no desktop HWND. WWUI keeps this original application-handle ABI,
// while its Vita IME boundary intentionally consumes the handle without using
// a Win32 window.
HWND MainWindow = NULL;

namespace RenegadeDialogResources {

const unsigned char *Find_Dialog(uint16_t resource_id, size_t *byte_count)
{
	if (byte_count != NULL) *byte_count = 0;
	for (size_t index = 0; index < kRenegadeDialogTemplateCount; ++index) {
		if (kRenegadeDialogTemplates[index].Id == resource_id) {
			if (byte_count != NULL) *byte_count = kRenegadeDialogTemplates[index].Size;
			return kRenegadeDialogTemplates[index].Bytes;
		}
	}
	return NULL;
}

const char *Last_Error()
{
	return "original chat.rc has no generated RT_DIALOG record for this id";
}

}  // namespace RenegadeDialogResources

HRSRC FindResource(HINSTANCE, LPCTSTR name, LPCTSTR type)
{
	const uintptr_t type_ordinal = reinterpret_cast<uintptr_t>(type);
	const uintptr_t resource_ordinal = reinterpret_cast<uintptr_t>(name);
	if (type_ordinal != 5U || resource_ordinal > 0xffffU) return NULL;
	return const_cast<unsigned char *>(RenegadeDialogResources::Find_Dialog(
		static_cast<uint16_t>(resource_ordinal), NULL));
}
HGLOBAL LoadResource(HINSTANCE, HRSRC resource) { return resource; }
LPVOID LockResource(HGLOBAL resource) { return resource; }
