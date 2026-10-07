// Host contract: write-only rooted files staged in memory produce exactly the
// bytes, return values and cursor positions of direct BufferedFileClass
// writes, including original ChunkSaveClass output, and reach the card in one
// write at Close (or at destruction).
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

#include "bufffile.h"
#include "chunkio.h"
#include "renegade_file_factory.h"

namespace {

#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
	std::abort(); } } while (0)

std::string Read_All(const std::string &path)
{
	std::string contents;
	FILE *file = std::fopen(path.c_str(), "rb");
	if (file == NULL) return contents;
	char buffer[4096];
	size_t count = 0;
	while ((count = std::fread(buffer, 1, sizeof(buffer), file)) != 0) contents.append(buffer, count);
	std::fclose(file);
	return contents;
}

struct Random {
	unsigned state;
	unsigned Next() { state = state * 1103515245U + 12345U; return state >> 8; }
};

void Random_Operations(FileClass &file, unsigned seed, std::vector<int> &results)
{
	Random random = {seed};
	unsigned char data[700];
	const unsigned operations = 1U + random.Next() % 400U;
	for (unsigned op = 0; op < operations; ++op) {
		const unsigned pick = random.Next() % 10U;
		if (pick < 5U) {
			const unsigned limit = random.Next() % 8U == 0U ? 700U : 40U;
			const int size = static_cast<int>(random.Next() % limit);
			for (int i = 0; i < size; ++i) data[i] = static_cast<unsigned char>(random.Next());
			results.push_back(file.Write(data, size));
		} else if (pick < 7U) {
			results.push_back(file.Seek(static_cast<int>(random.Next() % 300U) - 100, SEEK_CUR));
		} else if (pick < 8U) {
			results.push_back(file.Seek(static_cast<int>(random.Next() % 3000U), SEEK_SET));
		} else if (pick < 9U) {
			results.push_back(file.Seek(-static_cast<int>(random.Next() % 200U), SEEK_END));
		} else {
			results.push_back(file.Tell());
		}
	}
}

void Write_Chunks(FileClass &file, unsigned seed)
{
	Random random = {seed};
	ChunkSaveClass save(&file);
	for (unsigned chunk = 0; chunk < 40U; ++chunk) {
		save.Begin_Chunk(0x100U + chunk);
		for (unsigned inner = 0; inner < random.Next() % 6U; ++inner) {
			save.Begin_Chunk(0x200U + inner);
			for (unsigned micro = 0; micro < random.Next() % 9U; ++micro) {
				unsigned char payload[64];
				const unsigned size = random.Next() % sizeof(payload);
				for (unsigned i = 0; i < size; ++i) payload[i] = static_cast<unsigned char>(random.Next());
				save.Begin_Micro_Chunk(micro + 1U);
				save.Write(payload, size);
				save.End_Micro_Chunk();
			}
			save.End_Chunk();
		}
		const unsigned value = random.Next();
		save.Write(&value, sizeof(value));
		save.End_Chunk();
	}
}

} // namespace

int main()
{
	char base[] = "/tmp/renegade-staging-XXXXXX";
	CHECK(mkdtemp(base) != NULL);
	const std::string root(base);
	const std::string retail = root + "/retail", user = root + "/user";
	const std::string cache = root + "/cache", mods = root + "/mods";
	mkdir(retail.c_str(), 0777);
	mkdir(user.c_str(), 0777);
	// Bare .sav names resolve into the writable save namespace, as in game.
	mkdir((user + "/save").c_str(), 0777);
	const RenegadePathRoots roots = {retail.c_str(), user.c_str(), cache.c_str(), mods.c_str()};
	const std::string reference_path = root + "/reference.bin";
	Renegade_File_Factory_Reset_Statistics();

	// Random write/seek/tell sequences: identical returns and bytes.
	for (unsigned seed = 1; seed <= 600U; ++seed) {
		std::vector<int> expected, actual;
		{
			BufferedFileClass reference(reference_path.c_str());
			CHECK(reference.Open(FileClass::WRITE));
			Random_Operations(reference, seed, expected);
			reference.Close();
		}
		{
			RenegadeRootedFileClass staged(roots, "staged.bin");
			CHECK(staged.Open(FileClass::WRITE));
			Random_Operations(staged, seed, actual);
			staged.Close();
		}
		if (expected != actual || Read_All(reference_path) != Read_All(user + "/staged.bin")) {
			std::fprintf(stderr, "staged write mismatch for seed %u\n", seed);
			return 1;
		}
	}

	// Original ChunkSaveClass output (header back-patching) is byte-identical.
	for (unsigned seed = 1; seed <= 40U; ++seed) {
		{
			BufferedFileClass reference(reference_path.c_str());
			CHECK(reference.Open(FileClass::WRITE));
			Write_Chunks(reference, seed);
			reference.Close();
		}
		{
			RenegadeRootedFileClass staged(roots, "save.sav");
			CHECK(staged.Open(FileClass::WRITE));
			Write_Chunks(staged, seed);
			staged.Close();
		}
		const std::string expected = Read_All(reference_path);
		CHECK(!expected.empty() && expected == Read_All(user + "/save/save.sav"));
		// Every overwrite replaces the slot and leaves no sibling behind.
		struct stat status;
		CHECK(stat((user + "/save/save.sav.pending").c_str(), &status) != 0);
		CHECK(stat((user + "/save/save.sav.previous").c_str(), &status) != 0);
	}

	// Nothing reaches the card before Close; Size and Tell use the staged view.
	{
		RenegadeRootedFileClass staged(roots, "pending.bin");
		CHECK(staged.Open(FileClass::WRITE));
		std::vector<unsigned char> big(3U * 1024U * 1024U + 17U);
		for (size_t i = 0; i < big.size(); ++i) big[i] = static_cast<unsigned char>(i * 31U);
		CHECK(staged.Write(big.data(), static_cast<int>(big.size())) == static_cast<int>(big.size()));
		CHECK(staged.Size() == static_cast<int>(big.size()));
		CHECK(Read_All(user + "/pending.bin").empty());
		CHECK(staged.Seek(10, SEEK_SET) == 10 && staged.Tell() == 10);
		// Destruction without Close still writes the file.
	}
	CHECK(Read_All(user + "/pending.bin").size() == 3U * 1024U * 1024U + 17U);

	// Reopening for writing writes out the previous staged contents first.
	{
		RenegadeRootedFileClass staged(roots, "first.bin");
		CHECK(staged.Open(FileClass::WRITE));
		CHECK(staged.Write("abc", 3) == 3);
		CHECK(staged.Open("second.bin", FileClass::WRITE));
		CHECK(Read_All(user + "/first.bin") == "abc");
		CHECK(staged.Write("de", 2) == 2);
		staged.Close();
		CHECK(Read_All(user + "/second.bin") == "de");
	}

	// A write session leaves the previous slot untouched until Close, then
	// replaces it whole, also over an existing file.
	{
		{
			RenegadeRootedFileClass first(roots, "slot.sav");
			CHECK(first.Open(FileClass::WRITE));
			CHECK(first.Write("old-save", 8) == 8);
			first.Close();
		}
		CHECK(Read_All(user + "/save/slot.sav") == "old-save");
		RenegadeRootedFileClass second(roots, "slot.sav");
		CHECK(second.Open(FileClass::WRITE));
		CHECK(second.Write("new", 3) == 3);
		CHECK(Read_All(user + "/save/slot.sav") == "old-save");
		second.Close();
		CHECK(Read_All(user + "/save/slot.sav") == "new");
		struct stat status;
		CHECK(stat((user + "/save/slot.sav.pending").c_str(), &status) != 0);
		CHECK(stat((user + "/save/slot.sav.previous").c_str(), &status) != 0);
	}

	// An interruption between the two renames leaves only "<slot>.previous";
	// the next access to the slot restores it. A finished replace with a
	// leftover aside copy only removes the copy.
	{
		CHECK(rename((user + "/save/slot.sav").c_str(),
			(user + "/save/slot.sav.previous").c_str()) == 0);
		RenegadeRootedFileClass reader(roots, "slot.sav");
		CHECK(reader.Is_Available());
		CHECK(Read_All(user + "/save/slot.sav") == "new");
		struct stat status;
		CHECK(stat((user + "/save/slot.sav.previous").c_str(), &status) != 0);
		FILE *stale = std::fopen((user + "/save/slot.sav.previous").c_str(), "wb");
		CHECK(stale != NULL && std::fputs("stale", stale) >= 0 && std::fclose(stale) == 0);
		RenegadeRootedFileClass second_reader(roots, "slot.sav");
		CHECK(second_reader.Is_Available());
		CHECK(Read_All(user + "/save/slot.sav") == "new");
		CHECK(stat((user + "/save/slot.sav.previous").c_str(), &status) != 0);
	}

	// A crash mid-write leaves a stale, longer "<slot>.pending"; the next
	// write-only session truncates and overwrites it, then replaces the slot.
	{
		FILE *stale = std::fopen((user + "/save/slot.sav.pending").c_str(), "wb");
		CHECK(stale != NULL && std::fputs("stale-partial-save", stale) >= 0 && std::fclose(stale) == 0);
		RenegadeRootedFileClass writer(roots, "slot.sav");
		CHECK(writer.Open(FileClass::WRITE));
		CHECK(writer.Write("ok", 2) == 2);
		writer.Close();
		CHECK(Read_All(user + "/save/slot.sav") == "ok");
		struct stat status;
		CHECK(stat((user + "/save/slot.sav.pending").c_str(), &status) != 0);
	}

	const RenegadeFileFactoryStatistics statistics = Renegade_File_Factory_Get_Statistics();
	CHECK(statistics.staged_write_files == 600U + 40U + 3U + 3U);
	CHECK(statistics.staged_write_fallbacks == 0U && statistics.staged_write_bytes != 0U);
	std::printf("rooted file factory write staging PASS files=%u bytes=%u\n",
		statistics.staged_write_files, statistics.staged_write_bytes);
	return 0;
}
