// Host contract: ConversationMgr's legacy one-byte category probe peeks at a
// misaligned "header" inside a retail CONVERSATION_CATEGORY chunk. That peek
// must report "no chunk" without setting the sticky ChunkLoadClass error, so
// the standard 32-bit category path and the following conversation load.
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "chunkio.h"
#include "rawfile.h"

#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
	std::abort(); } } while (0)

namespace {

void Put32(std::vector<unsigned char> &out, uint32_t value)
{
	for (int i = 0; i < 4; ++i) out.push_back(static_cast<unsigned char>(value >> (8 * i)));
}

std::vector<unsigned char> Chunk(uint32_t id, const std::vector<unsigned char> &payload, bool children)
{
	std::vector<unsigned char> out;
	Put32(out, id);
	Put32(out, static_cast<uint32_t>(payload.size()) | (children ? 0x80000000U : 0U));
	out.insert(out.end(), payload.begin(), payload.end());
	return out;
}

} // namespace

int main(int argc, char **argv)
{
	CHECK(argc == 2);
	// Retail CONV10.CDB layout: manager { variables, category { uint32 0, conversation {...} } }.
	std::vector<unsigned char> conversation_vars(12, 0x5A);
	std::vector<unsigned char> conversation = Chunk(0x08090319U,
		Chunk(0x08090316U, conversation_vars, false), true);
	std::vector<unsigned char> category;
	Put32(category, 0U);
	category.insert(category.end(), conversation.begin(), conversation.end());
	std::vector<unsigned char> manager = Chunk(0x08090315U, std::vector<unsigned char>(12, 0), false);
	std::vector<unsigned char> category_chunk = Chunk(0x08090318U, category, true);
	manager.insert(manager.end(), category_chunk.begin(), category_chunk.end());
	std::vector<unsigned char> file_bytes = Chunk(0x00040700U, manager, true);

	FILE *out = std::fopen(argv[1], "wb");
	CHECK(out != NULL);
	CHECK(std::fwrite(file_bytes.data(), 1, file_bytes.size(), out) == file_bytes.size());
	std::fclose(out);

	RawFileClass file(argv[1]);
	CHECK(file.Open(FileClass::READ));
	ChunkLoadClass cload(&file);
	CHECK(cload.Open_Chunk() && cload.Cur_Chunk_ID() == 0x00040700U);
	CHECK(cload.Open_Chunk() && cload.Cur_Chunk_ID() == 0x08090315U);
	CHECK(cload.Close_Chunk());
	CHECK(cload.Open_Chunk() && cload.Cur_Chunk_ID() == 0x08090318U);

	// Same order as Read_Conversation_Category: byte, speculative peek, padding.
	uint8_t category_byte = 0xFF;
	CHECK(cload.Read(&category_byte, 1) == 1 && category_byte == 0);
	uint32_t next_id = 0, next_size = 0;
	const bool peeked = cload.Peek_Next_Chunk(&next_id, &next_size);
	CHECK(!(peeked && next_id == 0x08090319U));
	CHECK(!cload.Has_Error());
	uint8_t padding[3] = { 1, 1, 1 };
	CHECK(cload.Read(padding, 3) == 3 && padding[0] == 0 && padding[1] == 0 && padding[2] == 0);

	// The real conversation still opens; an exact peek still works.
	CHECK(cload.Peek_Next_Chunk(&next_id, &next_size) && next_id == 0x08090319U);
	CHECK(cload.Open_Chunk() && cload.Cur_Chunk_ID() == 0x08090319U);
	CHECK(cload.Close_Chunk());
	CHECK(!cload.Open_Chunk());
	CHECK(cload.Close_Chunk());
	CHECK(cload.Close_Chunk());
	CHECK(!cload.Has_Error());
	file.Close();
	std::printf("chunk peek speculative PASS\n");
	return 0;
}
