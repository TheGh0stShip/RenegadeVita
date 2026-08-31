#include "win32_compat.h"

#include <stdio.h>

BYTE RenegadeVitaWWUIKeyState[256] = {};

namespace {

void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "listctrl sort check failed: %s\n", name);
	}
}

} // namespace

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	const WCHAR alpha[] = { 'A', 'l', 'p', 'h', 'a', 0 };
	const WCHAR alpha_case[] = { 'a', 'L', 'P', 'H', 'A', 0 };
	const WCHAR bravo[] = { 'B', 'r', 'a', 'v', 'o', 0 };
	const WCHAR prefix[] = { 'A', 'l', 'p', 'h', 'a', 'x', 0 };
	const WCHAR number[] = { ' ', '-', '4', '2', 0 };
	const WCHAR saturated[] = { '9', '9', '9', '9', '9', '9', '9', '9', '9', '9', 0 };
	const WCHAR tag[] = { 'B', 'o', 'L', 'd', '>', 0 };
	const WCHAR tag_name[] = { 'b', 'O', 'l', 'D', 0 };
	const WCHAR markup[] = { '<', 'c', 'o', 'l', 'o', 'r', '=', '1', ',', '2', ',', '3', '>', 'H', 'i', 0 };
	WCHAR copy_buffer[8] = {};
	Check(CompareStringW(LOCALE_USER_DEFAULT, NORM_IGNORECASE, alpha, -1,
		alpha_case, -1) == 2, "case-insensitive equality", checks, failures);
	Check(CompareStringW(LOCALE_USER_DEFAULT, NORM_IGNORECASE, alpha, -1,
		bravo, -1) == 1, "ascending order", checks, failures);
	Check(CompareStringW(LOCALE_USER_DEFAULT, NORM_IGNORECASE, bravo, -1,
		alpha, -1) == 3, "descending order", checks, failures);
	Check(CompareStringW(LOCALE_USER_DEFAULT, 0U, alpha, 5,
		prefix, 5) == 2, "explicit length", checks, failures);
	Check(CompareStringW(LOCALE_USER_DEFAULT, 0U, NULL, -1,
		alpha, -1) == 0, "invalid input", checks, failures);
	Check(_wtoi(number) == -42, "utf16 signed integer", checks, failures);
	Check(_wtoi(saturated) == INT_MAX, "utf16 integer saturation", checks, failures);
	Check(_wcsnicmp(tag, tag_name, 4U) == 0, "utf16 bounded tag comparison", checks, failures);
	Check(rv_utf16_n_compare(alpha, prefix, 5U) == 0, "utf16 bounded equality", checks, failures);
	Check(rv_utf16_n_compare(alpha, prefix, 6U) < 0, "utf16 bounded order", checks, failures);
	Check(rv_utf16_n_copy(copy_buffer, alpha, 8U) == copy_buffer &&
		rv_utf16_compare(copy_buffer, alpha) == 0, "utf16 bounded copy", checks, failures);
	Check(rv_utf16_chr(markup, ',') == markup + 8, "utf16 character search", checks, failures);
	Check(rv_utf16_strstr(markup, tag_name) == NULL, "utf16 case-sensitive substring miss", checks, failures);
	const WCHAR color[] = { 'c', 'o', 'l', 'o', 'r', 0 };
	Check(rv_utf16_strstr(markup, color) == markup + 1, "utf16 substring search", checks, failures);
	RenegadeVitaWWUIKeyState[VK_CONTROL] = 0x80U;
	Check(GetAsyncKeyState(VK_CONTROL) < 0, "WWUI modifier high-bit query", checks, failures);
	RenegadeVitaWWUIKeyState[VK_CONTROL] = 0U;
	Check(GetAsyncKeyState(VK_CONTROL) == 0, "WWUI modifier release query", checks, failures);
	printf("A4 ListCtrl sort contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
