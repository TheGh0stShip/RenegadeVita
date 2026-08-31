#include "miscutil.h"

#include "win32_compat.h"

#include "ffactory.h"
#include "wwfile.h"

/* Vita libc uses four-byte wchar_t values, whereas the original serialized
** WideStringClass contract is UTF-16.  These C-linkage definitions resolve
** the small standard wide-string surface used by the original runtime before
** libc archive members and preserve 16-bit storage semantics. */
#if defined(RENEGADE_SHORT_WCHAR_ABI) && !defined(RENEGADE_HOST_ABI_TEST)
extern "C" size_t wcslen(const wchar_t *text)
{
	return rv_utf16_length(text);
}

extern "C" int wcscmp(const wchar_t *left, const wchar_t *right)
{
	return rv_utf16_compare(left, right);
}

extern "C" int wcsncmp(const wchar_t *left, const wchar_t *right, size_t count)
{
	return rv_utf16_n_compare(left, right, count);
}

extern "C" wchar_t *wcscpy(wchar_t *destination, const wchar_t *source)
{
	return rv_utf16_copy(destination, source);
}

extern "C" wchar_t *wcsncpy(wchar_t *destination, const wchar_t *source,
	size_t count)
{
	return rv_utf16_n_copy(destination, source, count);
}

extern "C" wchar_t *wcschr(const wchar_t *text, wchar_t character)
{
	return const_cast<wchar_t *>(rv_utf16_chr(text, character));
}

extern "C" wchar_t *wcsrchr(const wchar_t *text, wchar_t character)
{
	return const_cast<wchar_t *>(rv_utf16_rchr(text, character));
}

extern "C" wchar_t *wcsstr(const wchar_t *text, const wchar_t *pattern)
{
	return const_cast<wchar_t *>(rv_utf16_strstr(text, pattern));
}
#endif

void cMiscUtil::Seconds_To_Hms(float seconds, int &hours, int &minutes, int &whole_seconds)
{
	if (seconds < 0.0f) {
		seconds = 0.0f;
	}
	hours = (int)(seconds / 3600.0f);
	seconds -= (float)hours * 3600.0f;
	minutes = (int)(seconds / 60.0f);
	seconds -= (float)minutes * 60.0f;
	whole_seconds = (int)seconds;
}

bool cMiscUtil::Is_String_Different(LPCSTR left, LPCSTR right)
{
	return stricmp(left ? left : "", right ? right : "") != 0;
}

bool cMiscUtil::File_Exists(LPCSTR filename)
{
	if (filename == NULL || _TheFileFactory == NULL) {
		return false;
	}
	FileClass *file = _TheFileFactory->Get_File(filename);
	const bool available = file != NULL && file->Is_Available();
	if (file != NULL) {
		_TheFileFactory->Return_File(file);
	}
	return available;
}
