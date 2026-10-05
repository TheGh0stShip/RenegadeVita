// Host contract: retail availability probes are answered from memory after the
// first successful native probe; forced probes, writable roots and failures
// still reach native I/O.
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

#include "renegade_file_factory.h"

std::atomic<unsigned> g_native_availability_probes(0U);

namespace {

#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
	std::abort(); } } while (0)

void Touch(const std::string &path)
{
	FILE *file = std::fopen(path.c_str(), "wb");
	CHECK(file != NULL);
	std::fclose(file);
}

bool Available(const RenegadePathRoots &roots, const char *logical, bool forced = false)
{
	RenegadeRootedFileClass file(roots, logical);
	return file.Is_Available(forced);
}

} // namespace

int main()
{
	char base[] = "/tmp/renegade-factory-XXXXXX";
	CHECK(mkdtemp(base) != NULL);
	const std::string root(base);
	const std::string retail = root + "/retail", user = root + "/user";
	const std::string cache = root + "/cache", mods = root + "/mods";
	mkdir(retail.c_str(), 0777);
	mkdir((retail + "/Data").c_str(), 0777);
	mkdir(user.c_str(), 0777);
	mkdir((user + "/config").c_str(), 0777);
	Touch(retail + "/Data/M01.mix");
	Touch(retail + "/Data/Gone.mix");
	Touch(user + "/config/options.ini");
	const RenegadePathRoots roots = {retail.c_str(), user.c_str(), cache.c_str(), mods.c_str()};
	Renegade_File_Factory_Reset_Statistics();

	// The first retail probe is native; repeats (any case) are answered from memory.
	CHECK(Available(roots, "Data/M01.mix"));
	CHECK(g_native_availability_probes == 1U);
	CHECK(Available(roots, "data\\m01.MIX"));
	CHECK(Available(roots, "Data/M01.mix"));
	CHECK(g_native_availability_probes == 1U);
	CHECK(Renegade_File_Factory_Get_Statistics().readonly_availability_hits == 2U);

	// Forced probes always reach native I/O.
	CHECK(Available(roots, "Data/M01.mix", true));
	CHECK(g_native_availability_probes == 2U);

	// Writable roots are probed every time.
	CHECK(Available(roots, "user/config/options.ini"));
	CHECK(Available(roots, "user/config/options.ini"));
	CHECK(g_native_availability_probes == 4U);

	// A confirmed retail miss is still skipped without native I/O.
	CHECK(!Available(roots, "Data/Missing.mix"));
	CHECK(g_native_availability_probes == 4U);
	// A listed file whose native probe fails is never remembered as available.
	CHECK(unlink((retail + "/Data/Gone.mix").c_str()) == 0);
	CHECK(!Available(roots, "Data/Gone.mix"));
	CHECK(!Available(roots, "Data/Gone.mix"));
	CHECK(g_native_availability_probes == 6U);

	// Concurrent lookups (loader threads) share the cache safely.
	std::vector<std::thread> threads;
	for (unsigned thread = 0; thread < 4U; ++thread) {
		threads.emplace_back([&roots, thread]() {
			char name[64];
			for (unsigned round = 0; round < 200U; ++round) {
				std::snprintf(name, sizeof(name), round % 2U ? "Data/M01.mix" : "Data/T%u.mix",
					(thread + round) % 8U);
				(void)Available(roots, name);
			}
		});
	}
	for (std::thread &thread : threads) thread.join();
	CHECK(Available(roots, "Data/M01.mix"));
	std::printf("rooted file factory availability cache PASS native=%u hits=%u\n",
		g_native_availability_probes.load(),
		Renegade_File_Factory_Get_Statistics().readonly_availability_hits);
	return 0;
}
