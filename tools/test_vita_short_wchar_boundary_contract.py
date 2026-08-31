import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VitaShortWcharBoundaryContractTests(unittest.TestCase):
    def test_utf16_helpers_cover_frontend_dialogue_and_hud_call_surface(self):
        compat = (ROOT / "port" / "compatibility" / "include" / "win32_compat.h").read_text(
            encoding="utf-8"
        )
        boundary = (ROOT / "port" / "platform" / "a31_miscutil_boundary.cpp").read_text(
            encoding="utf-8"
        )

        for helper in (
            "rv_utf16_n_compare",
            "rv_utf16_n_copy",
            "rv_utf16_chr",
            "rv_utf16_strstr",
        ):
            self.assertIn(helper, compat)
            self.assertIn(helper, boundary)

        for symbol in (
            'extern "C" size_t wcslen',
            'extern "C" int wcscmp',
            'extern "C" int wcsncmp',
            'extern "C" wchar_t *wcscpy',
            'extern "C" wchar_t *wcsncpy',
            'extern "C" wchar_t *wcschr',
            'extern "C" wchar_t *wcsrchr',
            'extern "C" wchar_t *wcsstr',
        ):
            self.assertIn(symbol, boundary)

        self.assertIn("#if defined(RENEGADE_SHORT_WCHAR_ABI) && !defined(RENEGADE_HOST_ABI_TEST)", boundary)
        self.assertIn("#if !defined(RENEGADE_SHORT_WCHAR_ABI)", compat)

    def test_original_frontend_wide_text_callers_are_not_left_to_libc(self):
        caller_files = {
            "staging/wwui/dialogparser.cpp": ("::wcsstr", "::wcscpy"),
            "staging/wwui/textmarqueectrl.cpp": ("wcsncpy", "::wcschr"),
            "staging/commando/renegadedialogmgr.cpp": ("::wcsncpy",),
            "staging/commando/dlgmpingamechat.cpp": ("::wcschr",),
            "staging/commando/WOLBuddyMgr.cpp": ("wcsncmp", "wcsstr"),
        }
        for relative, needles in caller_files.items():
            source = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
            for needle in needles:
                self.assertIn(needle, source)

        boundary = (ROOT / "port" / "platform" / "a31_miscutil_boundary.cpp").read_text(
            encoding="utf-8"
        )
        self.assertIn("rv_utf16_n_compare(left, right, count)", boundary)
        self.assertIn("rv_utf16_n_copy(destination, source, count)", boundary)
        self.assertIn("rv_utf16_chr(text, character)", boundary)
        self.assertIn("rv_utf16_strstr(text, pattern)", boundary)


if __name__ == "__main__":
    unittest.main()
