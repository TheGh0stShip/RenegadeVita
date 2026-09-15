#include "renegade_file_factory.h"

#include "wwfile.h"

#include <stdio.h>
#include <string.h>

#include <sys/stat.h>
#include <unistd.h>

namespace {

struct Contract
{
	unsigned checks;
	unsigned failures;

	void Expect(bool condition, const char *name)
	{
		++checks;
		if (!condition) {
			++failures;
			printf("FAIL: %s\n", name);
		}
	}
};

bool Make_Directory(const char *path)
{
	return mkdir(path, 0700) == 0;
}

bool Write_File(const char *path, const char *contents)
{
	FILE *output = fopen(path, "wb");
	if (output == NULL) return false;
	const bool written = fputs(contents, output) >= 0;
	return fclose(output) == 0 && written;
}

} // namespace

int main()
{
	char temporary[] = "/tmp/renegade-file-factory-telemetry-XXXXXX";
	char *root = mkdtemp(temporary);
	if (root == NULL) return 2;
	char retail[512] = {};
	char user[512] = {};
	char cache[512] = {};
	char mods[512] = {};
	char data[640] = {};
	char sample[768] = {};
	snprintf(retail, sizeof(retail), "%s/retail", root);
	snprintf(user, sizeof(user), "%s/user", root);
	snprintf(cache, sizeof(cache), "%s/cache", root);
	snprintf(mods, sizeof(mods), "%s/mods", root);
	snprintf(data, sizeof(data), "%s/Data", retail);
	snprintf(sample, sizeof(sample), "%s/sample.bin", data);
	if (!Make_Directory(retail) || !Make_Directory(user) || !Make_Directory(cache) ||
		!Make_Directory(mods) || !Make_Directory(data) || !Write_File(sample, "RV")) {
		return 2;
	}

	const RenegadePathRoots roots = {retail, user, cache, mods};
	RenegadeRootedFileFactoryClass factory(roots);
	Contract contract = {};
	Renegade_File_Factory_Reset_Statistics();

	FileClass *valid = factory.Get_File("Data\\sample.bin");
	contract.Expect(valid != NULL && valid->Is_Available(), "valid file available");
	char bytes[2] = {};
	contract.Expect(valid != NULL && valid->Open(FileClass::READ) &&
		valid->Read(bytes, sizeof(bytes)) == static_cast<int>(sizeof(bytes)) &&
		memcmp(bytes, "RV", sizeof(bytes)) == 0, "valid file reads through original FileClass");
	if (valid != NULL) valid->Close();
	factory.Return_File(valid);

	FileClass *invalid = factory.Get_File("../blocked.bin");
	contract.Expect(invalid != NULL && !invalid->Open(FileClass::READ),
		"traversing file is rejected at rooted boundary");
	factory.Return_File(invalid);

	FileClass *writable = factory.Get_File("user/factory-telemetry.tmp");
	contract.Expect(writable != NULL && writable->Create(),
		"writable file is routed outside retail");
	if (writable != NULL) writable->Close();
	contract.Expect(writable != NULL && writable->Delete(), "writable file can be removed");
	factory.Return_File(writable);

	const RenegadeFileFactoryStatistics statistics =
		Renegade_File_Factory_Get_Statistics();
	contract.Expect(statistics.get_file_calls == 3U && statistics.return_file_calls == 3U,
		"factory get and return calls counted");
	contract.Expect(statistics.resolution_attempts >= 5U &&
		statistics.read_resolution_attempts >= 4U &&
		statistics.write_resolution_attempts >= 1U,
		"read and write resolutions counted");
	contract.Expect(statistics.resolution_failures >= 2U,
		"invalid logical path resolution failures counted");
	contract.Expect(statistics.resolution_cache_hits >= 3U,
		"prepared resolution cache hits counted");
	/* BufferedFileClass::Create may internally use the virtual Open path. That
	 * is original file semantics, so require the observed lower bound rather
	 * than asserting an implementation-specific exact total. */
	contract.Expect(statistics.open_attempts >= 2U && statistics.open_failures >= 1U,
		"open attempts and failures counted");
	contract.Expect(statistics.availability_attempts >= 1U &&
		statistics.availability_failures == 0U, "availability counted");
	contract.Expect(statistics.create_attempts == 1U && statistics.create_failures == 0U &&
		statistics.delete_attempts == 1U && statistics.delete_failures == 0U,
		"write lifecycle counted");
	contract.Expect(statistics.read_calls == 1U && statistics.read_bytes == 2U &&
		statistics.write_calls == 0U && statistics.write_bytes == 0U,
		"read/write byte totals counted without payload retention");

	printf("A3.6 rooted file-factory telemetry contract: %u checks, %u failures; get/return=%u/%u resolve=%u fail=%u cache_hit=%u open=%u fail=%u read=%u/%uB write=%u/%uB\n",
		contract.checks, contract.failures, statistics.get_file_calls,
		statistics.return_file_calls, statistics.resolution_attempts,
		statistics.resolution_failures, statistics.resolution_cache_hits,
		statistics.open_attempts, statistics.open_failures, statistics.read_calls,
		statistics.read_bytes, statistics.write_calls, statistics.write_bytes);
	FileClass *missing = factory.Get_File("Data/no-such-directory/absent.bin");
	contract.Expect(missing != NULL && !missing->Is_Available() &&
		!missing->Open(FileClass::READ), "confirmed absent retail probes preserve failure");
	factory.Return_File(missing);
	const RenegadeFileFactoryStatistics miss_statistics = Renegade_File_Factory_Get_Statistics();
	contract.Expect(miss_statistics.readonly_availability_skips >= 1U &&
		miss_statistics.readonly_open_skips >= 1U, "confirmed retail misses avoid native file probes");

	char late_path[768] = {};
	snprintf(late_path, sizeof(late_path), "%s/late.bin", data);
	FileClass *late = factory.Get_File("Data/late.bin");
	contract.Expect(late != NULL && !late->Is_Available(), "late retail file initially absent");
	contract.Expect(Write_File(late_path, "RV"), "create host-only late-file fixture");
	contract.Expect(late != NULL && late->Is_Available(true), "forced probe bypasses confirmed-miss shortcut");
	contract.Expect(late != NULL && late->Is_Available() && late->Open(FileClass::READ),
		"successful forced probe clears the negative observation");
	if (late != NULL) late->Close();
	factory.Return_File(late);

	char state_path[768] = {};
	snprintf(state_path, sizeof(state_path), "%s/late-state.tmp", user);
	FileClass *state = factory.Get_File("user/late-state.tmp");
	contract.Expect(state != NULL && !state->Is_Available(), "writable namespace initially absent");
	contract.Expect(Write_File(state_path, "RV"), "create host-only writable-state fixture");
	contract.Expect(state != NULL && state->Open(FileClass::READ),
		"writable namespace observes files created after initial lookup");
	if (state != NULL) state->Close();
	factory.Return_File(state);
	printf("A3.6 readonly miss-probe extension: total=%u failures=%u avoided availability/open=%u/%u\n",
		contract.checks, contract.failures, miss_statistics.readonly_availability_skips,
		miss_statistics.readonly_open_skips);
	return contract.failures == 0U ? 0 : 1;
}
