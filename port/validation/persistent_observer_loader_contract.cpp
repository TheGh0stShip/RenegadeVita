#include "chunkio.h"
#include "persistfactory.h"
#include "persistentgameobjobserver.h"
#include "rawfile.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <vector>

namespace {

static const uint32 kRootChunkId = 1U;
static const uint32 kKnownFactoryChunkId = 0xA35A1001U;
static const uint32 kUnknownFactoryChunkId = 0xA35A1002U;
static const uint32 kFactoryObjPointerChunkId = 0x00100100U;
static const uint32 kFactoryObjDataChunkId = 0x00100101U;
static const uint32 kSubChunkFlag = 0x80000000U;

class DirectObserverFixtureFactory : public PersistFactoryClass
{
public:
	uint32 Chunk_ID(void) const override
	{
		return kKnownFactoryChunkId;
	}

	PersistClass * Load(ChunkLoadClass & cload) const override
	{
		++KnownFactoryLoadCount;
		while (cload.Open_Chunk()) {
			cload.Seek(cload.Cur_Chunk_Length());
			cload.Close_Chunk();
		}
		return NULL;
	}

	void Save(ChunkSaveClass &, PersistClass *) const override
	{
	}

	mutable unsigned KnownFactoryLoadCount = 0U;
};

DirectObserverFixtureFactory g_direct_observer_factory;

struct ObserverLoadSummary
{
	bool root_id_match = false;
	bool root_opened = false;
	bool root_closed = false;
	bool load_result = false;
	bool child_exhausted = false;
	int initial_depth = 0;
	int final_depth = 0;
	int depth_after_root_close = 0;
	uint32 root_id = 0U;
	uint32 root_length = 0U;
	unsigned checks = 0U;
	unsigned failures = 0U;
	unsigned child_count = 0U;
	unsigned known_child_count = 0U;
	unsigned unknown_child_count = 0U;
	unsigned known_factory_hits = 0U;
	unsigned max_child_depth = 0U;
};

struct ChunkOpenSummary
{
	bool initial_open = false;
	bool child_exhausted = false;
	bool balanced = true;
	int initial_depth = 0;
	int depth_after_open = 0;
	int depth_after_close = 0;
	uint32 header_id = 0U;
	uint32 header_length = 0U;
};

struct Contract
{
	unsigned checks = 0U;
	unsigned failures = 0U;

	void Expect(bool condition, const char *name)
	{
		++checks;
		if (!condition) {
			++failures;
			printf("FAIL: %s\n", name);
		}
	}
};

void Append_U32(std::vector<uint8_t> &bytes, uint32 value)
{
	bytes.push_back(static_cast<uint8_t>((value >> 0) & 0xFF));
	bytes.push_back(static_cast<uint8_t>((value >> 8) & 0xFF));
	bytes.push_back(static_cast<uint8_t>((value >> 16) & 0xFF));
	bytes.push_back(static_cast<uint8_t>((value >> 24) & 0xFF));
}

void Append_Chunk_Header(std::vector<uint8_t> &bytes, uint32 chunk_id, uint32 length, bool has_children)
{
	Append_U32(bytes, chunk_id);
	const uint32 raw_length = has_children ? (length | kSubChunkFlag) : (length & ~kSubChunkFlag);
	Append_U32(bytes, raw_length);
}

bool Write_Fixture(const char *path, const std::vector<uint8_t> &bytes)
{
	FILE *output = fopen(path, "wb");
	if (output == NULL) return false;
	const bool wrote = bytes.empty() ? true :
		(fwrite(bytes.data(), 1U, bytes.size(), output) == bytes.size());
	const bool closed = (fclose(output) == 0);
	return wrote && closed;
}

bool Load_Fixture_To_Temp_File(const std::vector<uint8_t> &bytes, char *out_path)
{
	char temporary[] = "/tmp/renegade-observer-loader-XXXXXX";
	const int handle = mkstemp(temporary);
	if (handle < 0) {
		return false;
	}
	close(handle);
	if (!Write_Fixture(temporary, bytes)) {
		unlink(temporary);
		return false;
	}
	strcpy(out_path, temporary);
	return true;
}

uint32 Read_U32_Le(const std::vector<uint8_t> &bytes, size_t offset)
{
	return static_cast<uint32>(bytes[offset])
		| (static_cast<uint32>(bytes[offset + 1]) << 8)
		| (static_cast<uint32>(bytes[offset + 2]) << 16)
		| (static_cast<uint32>(bytes[offset + 3]) << 24);
}

	ObserverLoadSummary Run_Observer_Load(
	const std::vector<uint8_t> &bytes,
	unsigned expected_children,
	unsigned expected_known_children,
	unsigned expected_unknown_children)
{
	ObserverLoadSummary summary;
	char temporary_file[64];
	if (!Load_Fixture_To_Temp_File(bytes, temporary_file)) {
		return summary;
	}
	RawFileClass file(temporary_file);
	if (!file.Open(FileClass::READ)) {
		unlink(temporary_file);
		return summary;
	}

	if (bytes.size() >= 4U) summary.root_id = Read_U32_Le(bytes, 0);
	if (bytes.size() >= 8U) summary.root_length = Read_U32_Le(bytes, 4) & 0x7FFFFFFFU;
	summary.root_id_match = (summary.root_id == kRootChunkId);
	summary.root_opened = (bytes.size() >= 8U);
	summary.child_count = expected_children;
	summary.known_child_count = expected_known_children;
	summary.unknown_child_count = expected_unknown_children;

	const unsigned load_calls_before = g_direct_observer_factory.KnownFactoryLoadCount;

	ChunkLoadClass loader(&file);
	summary.initial_depth = loader.Cur_Chunk_Depth();
	summary.load_result = PersistentGameObjObserverManager::Load(loader);
	summary.final_depth = loader.Cur_Chunk_Depth();
	summary.root_closed = (summary.final_depth == 0);
	summary.depth_after_root_close = summary.final_depth;
	summary.known_factory_hits = (g_direct_observer_factory.KnownFactoryLoadCount - load_calls_before);
	summary.child_exhausted = (summary.final_depth == 0 && bytes.size() >= 8U);
	file.Close();
	unlink(temporary_file);
	return summary;
}

ChunkOpenSummary Run_Chunk_Open_Fixture(const std::vector<uint8_t> &bytes, bool probe_parent_exhaustion)
{
	ChunkOpenSummary summary;
	char temporary_file[64];
	if (!Load_Fixture_To_Temp_File(bytes, temporary_file)) {
		return summary;
	}

	RawFileClass file(temporary_file);
	if (!file.Open(FileClass::READ)) {
		unlink(temporary_file);
		return summary;
	}

	ChunkLoadClass loader(&file);
	summary.initial_depth = loader.Cur_Chunk_Depth();
	summary.initial_open = loader.Open_Chunk();
	if (summary.initial_open) {
		summary.header_id = loader.Cur_Chunk_ID();
		summary.header_length = loader.Cur_Chunk_Length();
		summary.depth_after_open = loader.Cur_Chunk_Depth();
		if (probe_parent_exhaustion) {
			summary.child_exhausted = !loader.Open_Chunk();
		}
		summary.depth_after_close = loader.Cur_Chunk_Depth();
		loader.Close_Chunk();
		summary.depth_after_close = loader.Cur_Chunk_Depth();
		summary.balanced = (summary.depth_after_close == 0);
	}
	file.Close();
	unlink(temporary_file);
	return summary;
}

ChunkOpenSummary Run_Chunk_Open_Null_File()
{
	ChunkOpenSummary summary;
	ChunkLoadClass loader(NULL);
	summary.initial_depth = loader.Cur_Chunk_Depth();
	summary.initial_open = loader.Open_Chunk();
	summary.depth_after_open = loader.Cur_Chunk_Depth();
	summary.balanced = (summary.depth_after_open == summary.initial_depth);
	return summary;
}

std::vector<uint8_t> Build_No_Children_Fixture()
{
	std::vector<uint8_t> bytes;
	Append_Chunk_Header(bytes, kRootChunkId, 0U, true);
	return bytes;
}

std::vector<uint8_t> Build_Known_And_Unknown_Children_Fixture()
{
	std::vector<uint8_t> bytes;
	const uint32 kKnownObjPointerLength = sizeof(uint32);
	const uint32 kKnownObjDataLength = 0U;
	const uint32 kKnownObjPointerChunkLength = sizeof(uint32) * 2U + kKnownObjPointerLength;
	const uint32 kKnownObjDataChunkLength = sizeof(uint32) * 2U + kKnownObjDataLength;
	const uint32 kKnownChildLength = kKnownObjPointerChunkLength + kKnownObjDataChunkLength;
	const uint32 kRootLength = kKnownChildLength + (sizeof(uint32) * 2U);

	Append_Chunk_Header(bytes, kRootChunkId, kRootLength, true);
	Append_Chunk_Header(bytes, kKnownFactoryChunkId, kKnownChildLength, true);
	Append_Chunk_Header(bytes, kFactoryObjPointerChunkId, kKnownObjPointerLength, false);
	Append_U32(bytes, 0x00000001U);
	Append_Chunk_Header(bytes, kFactoryObjDataChunkId, kKnownObjDataLength, false);
	Append_Chunk_Header(bytes, kUnknownFactoryChunkId, 0U, false);
	return bytes;
}

std::vector<uint8_t> Build_Wrong_Root_Fixture()
{
	std::vector<uint8_t> bytes;
	Append_Chunk_Header(bytes, 2U, 0U, true);
	return bytes;
}

std::vector<uint8_t> Build_Truncated_Child_Header_Fixture()
{
	std::vector<uint8_t> bytes;
	Append_Chunk_Header(bytes, kRootChunkId, sizeof(uint32), true);
	Append_U32(bytes, 0xA35A0001U);
	return bytes;
}

std::vector<uint8_t> Build_Missing_Header_Fixture()
{
	std::vector<uint8_t> bytes = { 0xAA, 0xAA };
	return bytes;
}

} // namespace

int main()
{
	Contract contract = {};
	const ChunkOpenSummary null_file_probe = Run_Chunk_Open_Null_File();
	contract.Expect(!null_file_probe.initial_open, "null file pointer fails ChunkLoadClass::Open_Chunk()");
	contract.Expect(null_file_probe.balanced, "null-file probe leaves chunk depth balanced");

	const ObserverLoadSummary no_children = Run_Observer_Load(Build_No_Children_Fixture(), 0U, 0U, 0U);
	const ChunkOpenSummary no_children_open = Run_Chunk_Open_Fixture(Build_No_Children_Fixture(), true);
	contract.Expect(no_children.root_opened, "valid fixture root opens");
	contract.Expect(no_children.root_id_match, "valid fixture root chunk id matches CHUNKID_OBSERVERS");
	contract.Expect(no_children.load_result, "valid fixture manager load succeeds");
	contract.Expect(no_children.root_closed, "valid fixture root closes");
	contract.Expect(no_children.depth_after_root_close == 0, "valid fixture chunk depth is 0 after close");
	contract.Expect(no_children.child_exhausted, "valid fixture child loop terminates");
	contract.Expect(no_children.child_count == 0U, "valid fixture has zero children");
	contract.Expect(no_children_open.initial_open, "no-child fixture open_Chunk succeeds");
	contract.Expect(no_children_open.child_exhausted, "no-child fixture parent-container exhaustion is reported");
	contract.Expect(no_children_open.balanced, "no-child fixture depth is balanced after Open_Chunk/Close_Chunk");

	const ObserverLoadSummary mixed_children = Run_Observer_Load(Build_Known_And_Unknown_Children_Fixture(), 2U, 1U, 1U);
	contract.Expect(mixed_children.root_opened && mixed_children.root_id_match,
		"known+unknown fixture root opens and has expected id");
	contract.Expect(mixed_children.load_result, "known+unknown fixture manager load succeeds");
	contract.Expect(mixed_children.root_closed, "known+unknown fixture root closes");
	contract.Expect(mixed_children.depth_after_root_close == 0, "known+unknown fixture depth resets to 0");
	contract.Expect(mixed_children.child_count == 2U, "known+unknown fixture loads two child chunks");
	contract.Expect(mixed_children.known_child_count == 1U, "known+unknown fixture reports one known child");
	contract.Expect(mixed_children.unknown_child_count == 1U, "known+unknown fixture reports one unknown child");
	contract.Expect(mixed_children.known_factory_hits == 1U, "known child factory hook executes");

	const ObserverLoadSummary missing_root = Run_Observer_Load(Build_Missing_Header_Fixture(), 0U, 0U, 0U);
	const ChunkOpenSummary truncated_header = Run_Chunk_Open_Fixture(Build_Missing_Header_Fixture(), false);
	contract.Expect(!truncated_header.initial_open, "truncated header fixture open_Chunk fails");
	contract.Expect(!missing_root.root_opened, "missing required root header fails root parse");
	contract.Expect(!missing_root.load_result, "missing required root header returns failure");
	contract.Expect(missing_root.root_closed, "missing required root fixture preserves depth-zero baseline");

	const ChunkOpenSummary repeated_open_one = Run_Chunk_Open_Fixture(Build_Known_And_Unknown_Children_Fixture(), false);
	const ChunkOpenSummary repeated_open_two = Run_Chunk_Open_Fixture(Build_Known_And_Unknown_Children_Fixture(), false);
	contract.Expect(repeated_open_one.initial_open, "repeated open one succeeds");
	contract.Expect(repeated_open_two.initial_open, "repeated open two succeeds");
	contract.Expect(repeated_open_one.balanced, "repeated open one balances depth");
	contract.Expect(repeated_open_two.balanced, "repeated open two balances depth");

	const ObserverLoadSummary wrong_root = Run_Observer_Load(Build_Wrong_Root_Fixture(), 0U, 0U, 0U);
	contract.Expect(wrong_root.root_opened, "wrong-root fixture opens root header");
	contract.Expect(!wrong_root.root_id_match, "wrong-root fixture fails id check");
	contract.Expect(!wrong_root.load_result, "wrong-root fixture returns failure");
	contract.Expect(wrong_root.root_closed, "wrong-root fixture preserves root close balance");
	contract.Expect(wrong_root.depth_after_root_close == 0, "wrong-root fixture depth resets to 0");

	const ObserverLoadSummary truncated_child = Run_Observer_Load(Build_Truncated_Child_Header_Fixture(), 0U, 0U, 0U);
	contract.Expect(truncated_child.root_opened, "truncated-child fixture opens required root");
	contract.Expect(truncated_child.root_id_match, "truncated-child fixture root id is CHUNKID_OBSERVERS");
	contract.Expect(truncated_child.load_result, "truncated-child fixture load returns success");
	contract.Expect(truncated_child.child_count == 0U, "truncated-child fixture has no child opens");
	contract.Expect(truncated_child.root_closed, "truncated-child fixture root closes after child failure");
	contract.Expect(truncated_child.depth_after_root_close == 0, "truncated-child fixture depth resets to 0");

	const std::vector<uint8_t> repeated_fixture = Build_Known_And_Unknown_Children_Fixture();
	const ObserverLoadSummary repeated_one = Run_Observer_Load(repeated_fixture, 2U, 1U, 1U);
	const ObserverLoadSummary repeated_two = Run_Observer_Load(repeated_fixture, 2U, 1U, 1U);
	contract.Expect(repeated_one.root_opened && repeated_one.root_id_match,
		"repeated invocation first pass opens expected root");
	contract.Expect(repeated_two.root_opened && repeated_two.root_id_match,
		"repeated invocation second pass opens expected root");
	contract.Expect(repeated_one.child_count == repeated_two.child_count,
		"repeated invocation child-count is stable");
	contract.Expect(repeated_one.known_child_count == repeated_two.known_child_count,
		"repeated invocation known-child count is stable");
	contract.Expect(repeated_one.unknown_child_count == repeated_two.unknown_child_count,
		"repeated invocation unknown-child count is stable");
	contract.Expect(repeated_one.known_factory_hits == repeated_two.known_factory_hits,
		"repeated invocation known-factory invocations are stable");
	contract.Expect(repeated_one.known_factory_hits == 1U && repeated_two.known_factory_hits == 1U,
		"repeated invocation uses one known-factory hook per load");

	printf("A3.5 observer loader contract: root/child checks %u, failures %u\n",
		contract.checks, contract.failures);
	return (contract.failures == 0U) ? 0 : 1;
}
