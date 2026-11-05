// Exercise the staged original subtitle parser and storage owners with UTF-16
// fixtures only. No game loop, renderer, retail assets or device calls run here.
#include "subtitleparser.h"
#include "subtitle.h"
#include "straw.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

static_assert(sizeof(wchar_t) == 2, "exercise the original engine UTF-16 ABI");
static_assert(sizeof(SubTitleClass::Alignment) == 1,
    "exercise the Vita engine short-enum ABI");

// Read_Line and wcstrim retain their original libc spelling. The native port
// supplies this exact UTF-16 operation in a31_miscutil_boundary.cpp; this small
// host fixture cannot use glibc's four-byte wchar_t implementation instead.
extern "C" size_t wcslen(const wchar_t* text) noexcept
{
    return rv_utf16_length(text);
}

namespace {

unsigned Checks = 0;

void Check(bool condition, const char* label)
{
    ++Checks;
    if (!condition) {
        fprintf(stderr, "subtitle parser check failed: %s\n", label);
        abort();
    }
}

std::vector<uint8_t> Encode(const wchar_t* text, bool bom = true)
{
    std::vector<uint8_t> bytes;
    if (bom) {
        bytes.push_back(0xff);
        bytes.push_back(0xfe);
    }
    for (; *text != 0; ++text) {
        bytes.push_back(static_cast<uint8_t>(*text & 0xff));
        bytes.push_back(static_cast<uint8_t>(*text >> 8));
    }
    return bytes;
}

std::vector<uint8_t> Encode_Ascii(const std::string& text)
{
    std::vector<uint8_t> bytes{0xff, 0xfe};
    for (unsigned char ch : text) {
        bytes.push_back(ch);
        bytes.push_back(0);
    }
    return bytes;
}

class MemoryStraw : public Straw
{
public:
    explicit MemoryStraw(std::vector<uint8_t> bytes) : Bytes(bytes), Cursor(0), Calls(0) {}

    int Get(void* buffer, int length) override
    {
        // Make an EOF-loop regression fail immediately instead of relying on
        // the runner's timeout to kill an unbounded parser.
        if (++Calls > Bytes.size() + 16U) {
            fprintf(stderr, "subtitle parser exceeded bounded EOF reads\n");
            abort();
        }
        const size_t available = Bytes.size() - Cursor;
        const size_t count = available < static_cast<size_t>(length) ?
            available : static_cast<size_t>(length);
        if (count != 0) memcpy(buffer, Bytes.data() + Cursor, count);
        Cursor += count;
        return static_cast<int>(count);
    }

private:
    std::vector<uint8_t> Bytes;
    size_t Cursor;
    size_t Calls;
};

class Titles
{
public:
    Titles(std::vector<uint8_t> bytes, const char* movie) : Input(bytes), Parser(Input),
        Collection(Parser.Get_Sub_Titles(movie)) {}

    ~Titles()
    {
        if (Collection == NULL) return;
        for (int index = 0; index < Collection->Count(); ++index) {
            delete (*Collection)[index];
        }
        delete Collection;
    }

    int Count() const { return Collection != NULL ? Collection->Count() : 0; }
    const SubTitleClass& operator[](int index) const { return *(*Collection)[index]; }

private:
    MemoryStraw Input;
    SubTitleParserClass Parser;
    DynamicVectorClass<SubTitleClass*>* Collection;
};

bool Caption_Is(const SubTitleClass& title, const wchar_t* expected)
{
    return title.Get_Caption() != NULL &&
        rv_utf16_compare(title.Get_Caption(), expected) == 0;
}

void Check_Valid_Fields()
{
    Titles titles(Encode(
        L"; fixture comment\r\n\r\n"
        L"BeginMovie\tTestMovie\r\n"
        L"<Time=00:00:01:99,Duration=00:00:02:50,Position=0x2:Right,"
        L"Color=1:127:255,Text=\"Havoc, = \u00e9 \u03a9 \u4e2d \U0001f642\">\r\n"
        L"<Text=\"Default\">\r\n"
        L"<Time=00:01:60:100,Duration=00:00:00:00,Position=Left,"
        L"Text=\"Rollover\">\r\n"
        L"eNdMoViE\r\n"), "tEsTmOvIe");
    Check(titles.Count() == 3, "all valid entries retained in authored order");
    Check(titles[0].Get_Display_Time() == 119, "hundredths floor to 60-Hz ticks");
    Check(titles[0].Get_Display_Duration() == 150, "two and a half seconds duration");
    Check(titles[0].Get_Line_Position() == 2, "original base-zero position syntax");
    Check(titles[0].Get_Alignment() == SubTitleClass::Right, "right alignment");
    Check(titles[0].Get_RGB_Color() == 0x017fff, "RGB components retained");
    Check(Caption_Is(titles[0], L"Havoc, = \u00e9 \u03a9 \u4e2d \U0001f642"),
        "UTF-16 caption, surrogate pair and quoted punctuation copied intact");
    Check(titles[1].Get_Display_Time() == 0, "default time");
    Check(titles[1].Get_Display_Duration() == 1200, "original 20-second default duration");
    Check(titles[1].Get_Line_Position() == 15, "default bottom line");
    Check(titles[1].Get_Alignment() == SubTitleClass::Center, "default center alignment");
    Check(titles[1].Get_RGB_Color() == 0xffffff, "default white color");
    Check(titles[2].Get_Display_Time() == 7260, "original decimal time-field rollover");
    Check(titles[2].Get_Display_Duration() == 1200, "zero duration retains original default");
    Check(titles[2].Get_Alignment() == SubTitleClass::Left, "alignment-only position");
}

void Check_EOF_And_Movie_Boundaries()
{
    Titles eof(Encode(L"BeginMovie fixture\n<Text=\"retained\">"), "fixture");
    Check(eof.Count() == 1 && Caption_Is(eof[0], L"retained"),
        "EOF without EndMovie terminates and retains complete entries");
    Titles next(Encode(L"BeginMovie first\n<Text=\"first\">\n"
        L"BeginMovie second\n<Text=\"second\">\nEndMovie\n"), "first");
    Check(next.Count() == 1 && Caption_Is(next[0], L"first"),
        "unterminated movie cannot consume next movie's captions");
    Titles empty(Encode(L"BeginMovie fixture\nEndMovie\n"), "fixture");
    Check(empty.Count() == 0, "empty movie returns no collection");
    Titles missing(Encode(L"BeginMovie fixture\nEndMovie\n"), "absent");
    Check(missing.Count() == 0, "missing movie safely exhausts input");
    Titles null_name(Encode(L"BeginMovie fixture\nEndMovie\n"), NULL);
    Check(null_name.Count() == 0, "null movie rejected");
    Titles blank_name(Encode(L"BeginMovie fixture\nEndMovie\n"), "");
    Check(blank_name.Count() == 0, "empty movie name rejected");
}

void Check_Malformed_Fields()
{
    const char* bad_fields[] = {
        "Time=1", "Time=00:00:", "Time=00:00:x:00", "Time=-1:00:00:00",
        "Time=00:00:00:", "Time=00:00:00:00:00", "Time=4294967296:00:00:00",
        "Time=19885:00:00:00", "Time=00:00:00:4294967296", "Duration=invalid",
        "Color=255", "Color=1:2", "Color=1:2:3:4", "Color=256:2:3",
        "Color=-1:2:3", "Color=1:2:x", "Position=0:Left", "Position=16:Right",
        "Position=9999999999999999999999999999999:Center", "Position=:Left"
    };
    for (const char* field : bad_fields) {
        const std::string text = std::string("BeginMovie fixture\n<") + field +
            ",Text=\"invalid\">\n<Text=\"valid\">\nEndMovie\n";
        Titles titles(Encode_Ascii(text), "fixture");
        Check(titles.Count() == 1 && Caption_Is(titles[0], L"valid"), field);
    }
    Titles malformed(Encode(L"BeginMovie fixture\n"
        L"<Time=00:00:00:00>\n"
        L"<Text=\"unterminated>\n"
        L"<Text>\n<>\n"
        L"<Text=\"\",Time=00:00:00:50>\n"
        L"<Text=\"old\",Text=\"new\",Unknown=ignored>\nEndMovie\n"), "fixture");
    Check(malformed.Count() == 2, "bad syntax and missing caption rejected independently");
    Check(Caption_Is(malformed[0], L""), "explicit empty caption remains valid");
    Check(malformed[0].Get_Display_Time() == 30, "empty caption still carries time");
    Check(Caption_Is(malformed[1], L"new"), "replacement caption owns its own copy");
}

void Check_Input_Encoding_And_Bounds()
{
    const std::vector<std::vector<uint8_t>> bad_boms = {
        {}, {0xff}, {0xfe, 0xff}, {0, 0},
        Encode(L"BeginMovie fixture\n<Text=\"bad\">\nEndMovie\n", false)
    };
    for (const auto& bytes : bad_boms) {
        Titles titles(bytes, "fixture");
        Check(titles.Count() == 0, "invalid or incomplete UTF-16LE BOM rejected");
    }
    auto truncated = Encode(L"BeginMovie fixture\n<Text=\"complete\">\n<");
    truncated.push_back(0x41);
    Titles odd(truncated, "fixture");
    Check(odd.Count() == 1 && Caption_Is(odd[0], L"complete"),
        "odd final UTF-16 byte cannot hang or expose uninitialized data");

    const std::string long_name(80, 'm');
    Titles long_movie(Encode_Ascii("BeginMovie " + long_name +
        "\n<Text=\"long name\">\nEndMovie\n"), long_name.c_str());
    Check(long_movie.Count() == 1, "movie names longer than original 31-char buffer");
    const std::string excessive_name(2048, 'x');
    Titles excessive(Encode(L"BeginMovie fixture\nEndMovie\n"), excessive_name.c_str());
    Check(excessive.Count() == 0, "oversized movie name rejected without truncation");

    Titles long_line(Encode_Ascii("BeginMovie fixture\n<Text=\"" +
        std::string(2048, 'x') + "\">\n<Text=\"next line\">\nEndMovie\n"), "fixture");
    Check(long_line.Count() == 1 && Caption_Is(long_line[0], L"next line"),
        "oversized line drains through original reader before following entry");
}

} // namespace

int main()
{
    Check_Valid_Fields();
    Check_EOF_And_Movie_Boundaries();
    Check_Malformed_Fields();
    Check_Input_Encoding_And_Bounds();
    printf("original subtitle parser PASS checks=%u wchar_bytes=%zu enum_bytes=%zu\n",
        Checks, sizeof(wchar_t), sizeof(SubTitleClass::Alignment));
}
