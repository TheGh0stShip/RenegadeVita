// Host test for port/renderer/vita/ww3d_vita_ffp_program_keys.h.
#include "ww3d_vita_ffp_program_keys.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>

using namespace RenegadeVitaFfpProgramKeys;

static int g_failures = 0;
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "%s:%d: CHECK(%s)\n", __FILE__, __LINE__, #x); ++g_failures; } } while (0)

static const char *kTag = "6e7fe40-m28-w0-p0123456789ab";

static std::string Serialize_String(const KeySet &set, const char *tag = kTag)
{
	static char buffer[kMaxFileBytes];
	const size_t size = Serialize(set, tag, buffer, sizeof(buffer));
	return std::string(buffer, size);
}

static bool Parse_String(const std::string &text, KeySet &set, const char *tag = kTag)
{
	return Parse(text.data(), text.size(), tag, set);
}

static KeySet *New_Set()
{
	KeySet *set = static_cast<KeySet *>(calloc(1, sizeof(KeySet)));
	Clear(*set);
	return set;
}

static void Test_Round_Trip()
{
	KeySet *set = New_Set();
	const uint32_t vertex[] = { 0x80000008U, 0x00000038U, 0x00000038U, 0x1234ABCDU };
	const uint32_t fragment[] = {
		0x00000101U, 0x00000000U, 0x00000000U,
		0x80000307U, 0xDEADBEEFU, 0x00C0FFEEU,
		0x00000101U, 0x00000000U, 0x00000000U, // duplicate
		0x00000101U, 0x00000001U, 0x00000000U  // distinct combiner
	};
	CHECK(Merge(*set, vertex, 4U, fragment, 4U) == 6U);
	CHECK(set->vertex_count == 3U && set->fragment_count == 3U);
	CHECK(set->vertex[0] == 0x80000008U && set->vertex[2] == 0x1234ABCDU);
	const std::string text = Serialize_String(*set);
	CHECK(text ==
		"renegade-vgl-ffp-keys 1\n"
		"tag 6e7fe40-m28-w0-p0123456789ab\n"
		"v 80000008\nv 00000038\nv 1234ABCD\n"
		"f 00000101 00000000 00000000\n"
		"f 80000307 DEADBEEF 00C0FFEE\n"
		"f 00000101 00000001 00000000\n"
		"end 3 3\n");
	KeySet *parsed = New_Set();
	CHECK(Parse_String(text, *parsed));
	CHECK(parsed->vertex_count == 3U && parsed->fragment_count == 3U);
	CHECK(memcmp(parsed->vertex, set->vertex, 3U * sizeof(uint32_t)) == 0);
	for (unsigned i = 0U; i < 3U; ++i) {
		CHECK(parsed->fragment[i].mask == set->fragment[i].mask);
		CHECK(parsed->fragment[i].combiner_low == set->fragment[i].combiner_low);
		CHECK(parsed->fragment[i].combiner_high == set->fragment[i].combiner_high);
	}
	// Merging the same keys again adds nothing and keeps the order.
	CHECK(Merge(*parsed, vertex, 4U, fragment, 4U) == 0U);
	CHECK(Serialize_String(*parsed) == text);
	// Lower-case hex parses to the same keys.
	std::string lower = text;
	const size_t at = lower.find("DEADBEEF");
	lower.replace(at, 8U, "deadbeef");
	CHECK(Parse_String(lower, *parsed) && parsed->fragment[1].combiner_low == 0xDEADBEEFU);
	// Empty record round-trips.
	KeySet *empty = New_Set();
	const std::string empty_text = Serialize_String(*empty);
	CHECK(empty_text == "renegade-vgl-ffp-keys 1\ntag 6e7fe40-m28-w0-p0123456789ab\nend 0 0\n");
	CHECK(Parse_String(empty_text, *parsed) && parsed->vertex_count == 0U && parsed->fragment_count == 0U);
	free(set);
	free(parsed);
	free(empty);
}

static void Expect_Rejected(const std::string &text, const char *tag = kTag)
{
	KeySet *set = New_Set();
	set->vertex_count = 7U;
	CHECK(!Parse_String(text, *set, tag));
	CHECK(set->vertex_count == 0U && set->fragment_count == 0U);
	free(set);
}

static void Test_Rejections()
{
	const std::string good =
		"renegade-vgl-ffp-keys 1\n"
		"tag 6e7fe40-m28-w0-p0123456789ab\n"
		"v 80000008\n"
		"f 00000101 00000000 00000000\n"
		"end 1 1\n";
	KeySet *set = New_Set();
	CHECK(Parse_String(good, *set));
	free(set);
	Expect_Rejected(good, "6e7fe40-m28-w0-pffffffffffff");          // stale patch digest
	Expect_Rejected(good, "6e7fe40-m29-w0-p0123456789ab");          // other FFP magic
	Expect_Rejected(good, "");                                        // invalid expected tag
	Expect_Rejected(good, "has space");
	Expect_Rejected("renegade-vgl-ffp-keys 2" + good.substr(23));   // other version
	Expect_Rejected(good.substr(0, good.size() - 1U));                // unterminated trailer
	Expect_Rejected(good.substr(0, good.size() - 8U));                // missing trailer
	Expect_Rejected(good.substr(0, 60U));                             // truncated mid-record
	Expect_Rejected(good + "v 00000001\n");                           // data after trailer
	Expect_Rejected(good + "\n");                                     // blank line after trailer
	std::string text = good;
	text.replace(text.find("end 1 1"), 7U, "end 2 1");
	Expect_Rejected(text);                                            // count mismatch
	text = good;
	text.replace(text.find("end 1 1"), 7U, "end 1 x");
	Expect_Rejected(text);
	text = good;
	text.replace(text.find("end 1 1"), 7U, "end 11");
	Expect_Rejected(text);
	text = good;
	text.insert(text.find("f "), "v 80000008\n");
	Expect_Rejected(text);                                            // duplicate key
	text = good;
	text.replace(text.find("v 80000008"), 10U, "v 8000000G");
	Expect_Rejected(text);                                            // bad hex
	text = good;
	text.replace(text.find("v 80000008"), 10U, "v 800000081");
	Expect_Rejected(text);                                            // long key
	text = good;
	text.replace(text.find("v 80000008\n"), 11U, "v 80000008\r\n");
	Expect_Rejected(text);                                            // CRLF
	text = good;
	text.replace(text.find("f 00000101 00000000"), 19U, "f 00000101-00000000");
	Expect_Rejected(text);
	Expect_Rejected("");
	Expect_Rejected(std::string(kMaxFileBytes + 1U, 'v'));
	// Over-bound vertex keys are rejected as a whole.
	std::string many = "renegade-vgl-ffp-keys 1\ntag 6e7fe40-m28-w0-p0123456789ab\n";
	char line[32];
	for (unsigned i = 0U; i <= kMaxVertexKeys; ++i) {
		snprintf(line, sizeof(line), "v %08X\n", i);
		many += line;
	}
	snprintf(line, sizeof(line), "end %u 0\n", kMaxVertexKeys + 1U);
	many += line;
	Expect_Rejected(many);
}

static void Test_Bounds()
{
	KeySet *set = New_Set();
	uint32_t vertex[kMaxVertexKeys + 10];
	for (unsigned i = 0U; i < kMaxVertexKeys + 10U; ++i) vertex[i] = i * 8U;
	static uint32_t fragment[(kMaxFragmentKeys + 10) * 3];
	for (unsigned i = 0U; i < kMaxFragmentKeys + 10U; ++i) {
		fragment[i * 3U] = i;
		fragment[i * 3U + 1U] = ~i;
		fragment[i * 3U + 2U] = i << 16;
	}
	CHECK(Merge(*set, vertex, kMaxVertexKeys + 10U, fragment, kMaxFragmentKeys + 10U) ==
		kMaxVertexKeys + kMaxFragmentKeys);
	CHECK(set->vertex_count == kMaxVertexKeys && set->fragment_count == kMaxFragmentKeys);
	CHECK(set->vertex[kMaxVertexKeys - 1U] == (kMaxVertexKeys - 1U) * 8U);
	CHECK(!Add_Vertex(*set, 0xFFFFFFF0U));
	const std::string text = Serialize_String(*set);
	CHECK(!text.empty() && text.size() <= kMaxFileBytes);
	KeySet *parsed = New_Set();
	CHECK(Parse_String(text, *parsed));
	CHECK(parsed->vertex_count == kMaxVertexKeys && parsed->fragment_count == kMaxFragmentKeys);
	CHECK(parsed->fragment[kMaxFragmentKeys - 1U].combiner_low == ~(kMaxFragmentKeys - 1U));
	// A too-small output buffer fails without a partial success.
	char small[64];
	CHECK(Serialize(*set, kTag, small, sizeof(small)) == 0U);
	CHECK(Serialize(*set, "bad tag", small, sizeof(small)) == 0U);
	CHECK(Serialize(*set, NULL, small, sizeof(small)) == 0U);
	free(set);
	free(parsed);
}

int main()
{
	Test_Round_Trip();
	Test_Rejections();
	Test_Bounds();
	if (g_failures != 0) {
		fprintf(stderr, "%d failure(s)\n", g_failures);
		return 1;
	}
	puts("vita_ffp_program_keys_test: OK");
	return 0;
}
