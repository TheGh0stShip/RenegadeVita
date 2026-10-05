// Host contract: cached retail case resolution matches a direct scan.
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

#include "renegade_paths.h"

namespace {

void Touch(const std::string &path)
{
	FILE *file = fopen(path.c_str(), "wb");
	assert(file != NULL);
	fclose(file);
}

std::string Resolve(const RenegadePathRoots &roots, const char *logical,
	RenegadePathAccess access, bool *matched = NULL, bool *missing = NULL)
{
	const RenegadeResolvedPath result = Renegade_Resolve_Path(roots, logical, access);
	assert(result.success);
	if (matched != NULL) *matched = result.existing_case_matched;
	if (missing != NULL) *missing = result.confirmed_missing;
	return result.physical;
}

} // namespace

int main()
{
	char base[] = "/tmp/renegade-paths-XXXXXX";
	assert(mkdtemp(base) != NULL);
	const std::string root(base);
	const std::string retail = root + "/retail", user = root + "/user";
	mkdir(retail.c_str(), 0777);
	mkdir((retail + "/Data").c_str(), 0777);
	mkdir(user.c_str(), 0777);
	mkdir((user + "/config").c_str(), 0777);
	Touch(retail + "/Data/Always.dat");
	Touch(retail + "/Data/M13.mix");
	Touch(retail + "/Data/m13.MIX");
	const std::string cache = root + "/cache", mods = root + "/mods";
	const RenegadePathRoots stable = {retail.c_str(), user.c_str(), cache.c_str(),
		mods.c_str()};

	for (unsigned pass = 0; pass < 3; ++pass) {
		bool matched = false, missing = true;
		// Case-insensitive resolution of every component.
		assert(Resolve(stable, "data/always.DAT", RENEGADE_PATH_READ, &matched, &missing) ==
			retail + "/Data/Always.dat");
		assert(matched && !missing);
		// An exact name wins over an earlier case-insensitive candidate.
		assert(Resolve(stable, "data/m13.MIX", RENEGADE_PATH_READ) == retail + "/Data/m13.MIX");
		assert(Resolve(stable, "Data\\M13.mix", RENEGADE_PATH_READ) == retail + "/Data/M13.mix");
		// Confirmed absence, including below a missing directory.
		assert(Resolve(stable, "data/absent.dds", RENEGADE_PATH_READ, &matched, &missing) ==
			retail + "/Data/absent.dds");
		assert(!matched && missing);
		assert(Resolve(stable, "nothere/deeper/file.w3d", RENEGADE_PATH_READ, &matched, &missing) ==
			retail + "/nothere/deeper/file.w3d");
		assert(!matched && missing);
	}

	// Writable namespaces are never cached: a file created after a lookup is
	// found on the next lookup with its on-disk case.
	bool matched = true;
	(void)Resolve(stable, "user/config/Late.flag", RENEGADE_PATH_READ, &matched);
	assert(!matched);
	Touch(user + "/config/Late.flag");
	assert(Resolve(stable, "user/config/late.FLAG", RENEGADE_PATH_READ, &matched) ==
		user + "/config/Late.flag");
	assert(matched);

	// Concurrent readers share the cache safely.
	std::vector<std::thread> threads;
	for (unsigned index = 0; index < 4; ++index) {
		threads.emplace_back([&stable, &retail]() {
			for (unsigned i = 0; i < 2000; ++i) {
				assert(Resolve(stable, "DATA/ALWAYS.DAT", RENEGADE_PATH_READ) ==
					retail + "/Data/Always.dat");
			}
		});
	}
	for (std::thread &thread : threads) thread.join();
	std::puts("Renegade path cache host contract PASS");
	return 0;
}
