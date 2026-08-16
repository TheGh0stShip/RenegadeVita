#include "wwbitpack_selftest.h"

#include "BitPacker.h"
#include "bitstream.h"

#include <math.h>
#include <string.h>

namespace {

struct TestState
{
	unsigned checks;
	unsigned failures;
	const char *first_failure;
};

void Expect(TestState &state, bool condition, const char *name)
{
	++state.checks;
	if (!condition) {
		++state.failures;
		if (state.first_failure == 0) {
			state.first_failure = name;
		}
	}
}

void Test_Bit_Packer(TestState &state)
{
	struct Case {
		ULONG value;
		UINT bits;
	};

	static const Case cases[] = {
		{ 0x1UL, 1U },
		{ 0x5UL, 3U },
		{ 0xA5UL, 8U },
		{ 0xABCUL, 12U },
		{ 0x55AAUL, 16U },
		{ 0x1234567UL, 28U },
		{ 0x89ABCDEFUL, 32U },
	};

	cBitPacker packer;
	for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
		packer.Add_Bits(cases[i].value, cases[i].bits);
	}

	Expect(state, packer.Get_Bit_Write_Position() == 100U, "bit position");
	for (unsigned i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
		ULONG decoded = 0;
		packer.Get_Bits(decoded, cases[i].bits);
		Expect(state, decoded == cases[i].value, "bit round-trip");
	}
	Expect(state, packer.Is_Flushed(), "bitstream consumed");
}

void Test_Uncompressed_Stream(TestState &state)
{
	cEncoderList::Set_Compression_Enabled(false);
	BitStreamClass stream;
	const bool bool_in = true;
	const BYTE byte_in = 0xA5U;
	const USHORT short_in = 0xBEEFU;
	const UINT uint_in = 0x12345678U;
	const int int_in = -1234567;
	const float float_in = -13.25f;

	stream.Add(bool_in);
	stream.Add(byte_in);
	stream.Add(short_in);
	stream.Add(uint_in);
	stream.Add(int_in);
	stream.Add(float_in);

	bool bool_out = false;
	BYTE byte_out = 0;
	USHORT short_out = 0;
	UINT uint_out = 0;
	int int_out = 0;
	float float_out = 0.0f;
	stream.Get(bool_out);
	stream.Get(byte_out);
	stream.Get(short_out);
	stream.Get(uint_out);
	stream.Get(int_out);
	stream.Get(float_out);

	Expect(state, bool_out == bool_in, "raw bool");
	Expect(state, byte_out == byte_in, "raw byte");
	Expect(state, short_out == short_in, "raw ushort");
	Expect(state, uint_out == uint_in, "raw uint");
	Expect(state, int_out == int_in, "raw int");
	Expect(state, memcmp(&float_out, &float_in, sizeof(float_in)) == 0, "raw float");
}

void Test_Encoded_Stream(TestState &state)
{
	const int encoder_type = 7;
	cEncoderList::Clear_Entries();
	cEncoderList::Set_Compression_Enabled(true);
	const float maximum_error = cEncoderList::Set_Precision<float>(
		encoder_type, -10.0f, 10.0f, 0.25f);

	BitStreamClass stream;
	const float input = 3.25f;
	stream.Add(input, encoder_type);
	float output = 0.0f;
	stream.Get(output, encoder_type);
	Expect(state, fabsf(output - input) <= maximum_error + 0.0001f, "encoded float");
	Expect(state, stream.Get_Compressed_Size_Bytes() < stream.Get_Uncompressed_Size_Bytes(),
		"compression reduces size");
}

void Test_Strings(TestState &state)
{
	cEncoderList::Set_Compression_Enabled(true);
	BitStreamClass stream;
	const char text[] = "Westwood";
	const WCHAR wide_text[] = { 'V', 'i', 't', 'a', 0 };
	stream.Add_Terminated_String(text);
	stream.Add_Wide_Terminated_String(wide_text);

	char text_out[16] = {};
	WCHAR wide_out[8] = {};
	stream.Get_Terminated_String(text_out, sizeof(text_out));
	stream.Get_Wide_Terminated_String(wide_out, sizeof(wide_out) / sizeof(wide_out[0]));
	Expect(state, strcmp(text_out, text) == 0, "narrow string");
	Expect(state, memcmp(wide_out, wide_text, sizeof(wide_text)) == 0, "UTF-16 string");
}

} // namespace

WestwoodSelfTestResult Run_Westwood_Bitpack_Self_Test()
{
	TestState state = { 0, 0, 0 };
	Test_Bit_Packer(state);
	Test_Uncompressed_Stream(state);
	Test_Encoded_Stream(state);
	Test_Strings(state);
	cEncoderList::Set_Compression_Enabled(true);

	WestwoodSelfTestResult result = {
		state.failures == 0,
		state.checks,
		state.failures,
		state.first_failure == 0 ? "none" : state.first_failure,
	};
	return result;
}

